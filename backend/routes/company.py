"""Company settings routes."""
from fastapi import APIRouter, Depends
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.company import CompanySettings, CompanySettingsUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/company", tags=["company"])


@router.get("/settings", response_model=CompanySettings)
async def get_company_settings(user: dict = Depends(get_current_user)):
    """Get company settings for current user."""
    settings = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not settings:
        # Return empty settings
        return CompanySettings(
            user_id=user["user_id"],
            business_name=user.get("name", ""),
            email=user.get("email", "")
        )
    
    return CompanySettings(**settings)


@router.put("/settings", response_model=CompanySettings)
async def update_company_settings(
    settings_data: CompanySettingsUpdate,
    user: dict = Depends(get_current_user)
):
    """Update company settings — full overwrite to prevent stale data."""
    existing = await db.company_settings.find_one(
        {"user_id": user["user_id"]}
    )
    
    now = datetime.now(timezone.utc)
    
    # Build the full update dict — include ALL fields (even empty strings)
    # to ensure we overwrite any stale/demo data completely
    raw = settings_data.model_dump()
    update_dict = {}
    for k, v in raw.items():
        if k in ("bank_details", "bank_accounts", "figure_aziendali"):
            continue  # handled below
        if v is not None:
            update_dict[k] = v
        elif k in ("business_name", "partita_iva", "codice_fiscale",
                    "address", "cap", "city", "province", "phone",
                    "email", "pec"):
            # Core identity fields: write empty string to clear stale data
            update_dict[k] = ""
    
    # Handle nested objects
    if settings_data.bank_details:
        update_dict["bank_details"] = settings_data.bank_details.model_dump()
    if settings_data.bank_accounts is not None:
        update_dict["bank_accounts"] = settings_data.bank_accounts
    if settings_data.figure_aziendali is not None:
        update_dict["figure_aziendali"] = settings_data.figure_aziendali
    
    update_dict["updated_at"] = now
    
    if existing:
        await db.company_settings.update_one(
            {"user_id": user["user_id"]},
            {"$set": update_dict}
        )
    else:
        settings_id = f"settings_{uuid.uuid4().hex[:12]}"
        settings_doc = {
            "settings_id": settings_id,
            "user_id": user["user_id"],
            **update_dict,
        }
        await db.company_settings.insert_one(settings_doc)
    
    updated = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    logger.info(f"Company settings FULL SAVE for user {user['user_id']}: business_name='{updated.get('business_name', '')}'")
    return CompanySettings(**updated)


@router.get("/settings/diagnostics")
async def company_settings_diagnostics(user: dict = Depends(get_current_user)):
    """Diagnostic endpoint — shows exactly what data is stored for the current user."""
    uid = user["user_id"]
    
    # 1. Count all company_settings documents
    total_count = await db.company_settings.count_documents({})
    
    # 2. Get all distinct user_ids
    all_user_ids = await db.company_settings.distinct("user_id")
    
    # 3. Count docs for THIS user
    user_count = await db.company_settings.count_documents({"user_id": uid})
    
    # 4. Get the actual document for this user
    user_doc = await db.company_settings.find_one({"user_id": uid}, {"_id": 0})
    
    # 5. Check legacy 'settings' collection
    legacy_doc = await db.settings.find_one({"type": "company"}, {"_id": 0})
    
    # 6. If multiple docs exist, get first one (what find_one({}) returns)
    first_doc = await db.company_settings.find_one({}, {"_id": 0})
    first_doc_user_id = first_doc.get("user_id") if first_doc else None
    first_doc_business_name = first_doc.get("business_name") if first_doc else None
    
    return {
        "current_user_id": uid,
        "total_company_settings_docs": total_count,
        "all_user_ids_in_collection": all_user_ids,
        "docs_for_current_user": user_count,
        "current_user_document": {
            "business_name": user_doc.get("business_name") if user_doc else None,
            "partita_iva": user_doc.get("partita_iva") if user_doc else None,
            "address": user_doc.get("address") if user_doc else None,
            "city": user_doc.get("city") if user_doc else None,
            "email": user_doc.get("email") if user_doc else None,
            "phone": user_doc.get("phone") if user_doc else None,
            "settings_id": user_doc.get("settings_id") if user_doc else None,
            "updated_at": str(user_doc.get("updated_at")) if user_doc else None,
        } if user_doc else None,
        "first_doc_in_collection": {
            "user_id": first_doc_user_id,
            "business_name": first_doc_business_name,
        },
        "legacy_settings_collection": {
            "exists": legacy_doc is not None,
            "ragione_sociale": legacy_doc.get("ragione_sociale") if legacy_doc else None,
        },
        "warnings": _build_diagnostics_warnings(uid, total_count, user_count, user_doc, first_doc_user_id, legacy_doc),
    }


def _build_diagnostics_warnings(uid, total, user_count, user_doc, first_uid, legacy_doc):
    warnings = []
    if user_count == 0:
        warnings.append("NESSUN DOCUMENTO company_settings trovato per il tuo user_id. Salva le Impostazioni per crearlo.")
    if user_count > 1:
        warnings.append(f"DUPLICATI: trovati {user_count} documenti per il tuo user_id. Dovrebbe essercene solo 1.")
    if total > 1 and first_uid and first_uid != uid:
        warnings.append(f"ATTENZIONE: il primo documento nella collezione appartiene a user_id='{first_uid}', non al tuo. Query senza filtro user_id restituirebbero dati sbagliati.")
    if user_doc and not user_doc.get("business_name"):
        warnings.append("business_name e' vuoto nel tuo documento. I PDF mostreranno intestazione vuota.")
    if legacy_doc:
        warnings.append(f"Esiste un documento legacy nella collezione 'settings' con ragione_sociale='{legacy_doc.get('ragione_sociale', '')}'. Alcuni moduli potrebbero usarlo.")
    return warnings

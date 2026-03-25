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

# ── Suspicious values that indicate test/demo data ──
_SUSPECT_NAMES = {
    "carpenteria rossi", "carpenteria metallica rossi",
    "test company", "officina metallo", "test steel",
    "demo company", "test sdi company", "test company firma",
    "test company cl", "ui test company", "test company iter",
}


def _is_suspicious(business_name: str) -> bool:
    """Check if a business name looks like test/demo data."""
    if not business_name:
        return False
    lower = business_name.lower().strip()
    return any(s in lower for s in _SUSPECT_NAMES)


@router.get("/settings", response_model=CompanySettings)
async def get_company_settings(user: dict = Depends(get_current_user)):
    """Get company settings for current user."""
    settings = await db.company_settings.find_one(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not settings:
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
    """Update company settings — full overwrite to prevent stale data.
    Includes audit trail (before/after snapshot)."""
    uid = user["user_id"]
    tid = user["tenant_id"]

    # ── Snapshot BEFORE ──
    existing = await db.company_settings.find_one({"user_id": uid, "tenant_id": tid}, {"_id": 0})
    before_snapshot = {
        "business_name": (existing or {}).get("business_name"),
        "partita_iva": (existing or {}).get("partita_iva"),
        "email": (existing or {}).get("email"),
        "address": (existing or {}).get("address"),
    } if existing else None

    now = datetime.now(timezone.utc)

    # Build the full update dict
    raw = settings_data.model_dump()
    update_dict = {}
    for k, v in raw.items():
        if k in ("bank_details", "bank_accounts", "figure_aziendali"):
            continue
        if v is not None:
            update_dict[k] = v
        elif k in ("business_name", "partita_iva", "codice_fiscale",
                    "address", "cap", "city", "province", "phone",
                    "email", "pec"):
            update_dict[k] = ""

    if settings_data.bank_details:
        update_dict["bank_details"] = settings_data.bank_details.model_dump()
    if settings_data.bank_accounts is not None:
        update_dict["bank_accounts"] = settings_data.bank_accounts
    if settings_data.figure_aziendali is not None:
        update_dict["figure_aziendali"] = settings_data.figure_aziendali

    update_dict["updated_at"] = now

    if existing:
        await db.company_settings.update_one(
            {"user_id": uid, "tenant_id": tid}, {"$set": update_dict}
        )
    else:
        settings_id = f"settings_{uuid.uuid4().hex[:12]}"
        settings_doc = {"settings_id": settings_id, "user_id": uid, "tenant_id": tid, **update_dict}
        await db.company_settings.insert_one(settings_doc)

    updated = await db.company_settings.find_one({"user_id": uid, "tenant_id": tid}, {"_id": 0})

    # ── Snapshot AFTER + Audit log ──
    after_snapshot = {
        "business_name": updated.get("business_name"),
        "partita_iva": updated.get("partita_iva"),
        "email": updated.get("email"),
        "address": updated.get("address"),
    }

    await db.company_settings_audit.insert_one({
        "audit_id": f"cs_audit_{uuid.uuid4().hex[:12]}",
        "user_id": uid, "tenant_id": tid,
        "user_email": user.get("email", ""),
        "action": "update" if existing else "create",
        "before": before_snapshot,
        "after": after_snapshot,
        "changed_fields": [k for k in after_snapshot if before_snapshot and after_snapshot.get(k) != before_snapshot.get(k)],
        "timestamp": now,
    })

    logger.info(f"[AUDIT] company_settings saved by {uid}: "
                f"'{before_snapshot.get('business_name') if before_snapshot else '(new)'}' -> '{after_snapshot['business_name']}'")

    return CompanySettings(**updated)


@router.get("/settings/diagnostics")
async def company_settings_diagnostics(user: dict = Depends(get_current_user)):
    """Diagnostic endpoint — shows exactly what data is stored for the current user."""
    uid = user["user_id"]
    tid = user["tenant_id"]

    total_count = await db.company_settings.count_documents({})
    all_user_ids = await db.company_settings.distinct("user_id")
    user_count = await db.company_settings.count_documents({"user_id": uid, "tenant_id": tid})
    user_doc = await db.company_settings.find_one({"user_id": uid, "tenant_id": tid}, {"_id": 0})
    legacy_doc = await db.settings.find_one({"type": "company"}, {"_id": 0})
    first_doc = await db.company_settings.find_one({}, {"_id": 0})
    first_doc_user_id = first_doc.get("user_id") if first_doc else None
    first_doc_business_name = first_doc.get("business_name") if first_doc else None

    # Fetch last 5 audit entries for this user
    audit_entries = []
    async for a in db.company_settings_audit.find(
        {"user_id": uid, "tenant_id": tid}, {"_id": 0}
    ).sort("timestamp", -1).limit(5):
        a["timestamp"] = str(a["timestamp"])
        audit_entries.append(a)

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
            "is_suspicious": _is_suspicious(user_doc.get("business_name", "")) if user_doc else False,
        } if user_doc else None,
        "first_doc_in_collection": {
            "user_id": first_doc_user_id,
            "business_name": first_doc_business_name,
        },
        "legacy_settings_collection": {
            "exists": legacy_doc is not None,
            "ragione_sociale": legacy_doc.get("ragione_sociale") if legacy_doc else None,
        },
        "recent_audit_log": audit_entries,
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
    if user_doc and _is_suspicious(user_doc.get("business_name", "")):
        warnings.append(f"SOSPETTO: il business_name '{user_doc.get('business_name')}' sembra un dato di test/demo. Verifica e aggiorna nelle Impostazioni.")
    if legacy_doc:
        warnings.append(f"Esiste un documento legacy nella collezione 'settings' con ragione_sociale='{legacy_doc.get('ragione_sociale', '')}'. Alcuni moduli potrebbero usarlo.")
    return warnings

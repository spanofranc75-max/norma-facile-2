"""Tenant CRUD service for multi-tenant management."""
import uuid
from datetime import datetime, timezone
from core.database import db
import logging

logger = logging.getLogger(__name__)

COLLECTION = "tenants"

PIANI_DISPONIBILI = {
    "pilot": {"max_utenti": 3, "max_commesse": 50, "label": "Pilot"},
    "pro": {"max_utenti": 10, "max_commesse": 500, "label": "Professional"},
    "enterprise": {"max_utenti": -1, "max_commesse": -1, "label": "Enterprise"},
}


async def create_tenant(
    nome_azienda: str,
    admin_user_id: str,
    piano: str = "pilot",
    partita_iva: str = "",
    email_contatto: str = "",
) -> dict:
    """Create a new tenant and link the admin user to it."""
    tenant_id = f"ten_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    limits = PIANI_DISPONIBILI.get(piano, PIANI_DISPONIBILI["pilot"])

    tenant_doc = {
        "tenant_id": tenant_id,
        "nome_azienda": nome_azienda,
        "piano": piano,
        "partita_iva": partita_iva,
        "email_contatto": email_contatto,
        "attivo": True,
        "admin_user_id": admin_user_id,
        "max_utenti": limits["max_utenti"],
        "max_commesse": limits["max_commesse"],
        "creato_il": now,
        "aggiornato_il": now,
    }

    await db[COLLECTION].insert_one(tenant_doc)
    tenant_doc.pop("_id", None)

    # Link admin user to this tenant
    await db.users.update_one(
        {"user_id": admin_user_id},
        {"$set": {"tenant_id": tenant_id, "updated_at": now}},
    )

    # Also update all existing sessions for this user
    await db.user_sessions.update_many(
        {"user_id": admin_user_id},
        {"$set": {"tenant_id": tenant_id}},
    )

    logger.info(f"Tenant created: {tenant_id} ({nome_azienda}) admin={admin_user_id}")
    return tenant_doc


async def get_tenant(tenant_id: str) -> dict | None:
    """Get a single tenant by ID."""
    doc = await db[COLLECTION].find_one({"tenant_id": tenant_id}, {"_id": 0})
    return doc


async def get_tenant_for_user(user_id: str) -> dict | None:
    """Get the tenant associated with a user."""
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "tenant_id": 1})
    if not user or not user.get("tenant_id") or user["tenant_id"] == "default":
        return None
    return await get_tenant(user["tenant_id"])


async def update_tenant(tenant_id: str, updates: dict) -> dict | None:
    """Update tenant fields. Returns updated doc."""
    safe_fields = {"nome_azienda", "piano", "partita_iva", "email_contatto", "attivo", "max_utenti", "max_commesse"}
    filtered = {k: v for k, v in updates.items() if k in safe_fields}
    if not filtered:
        return await get_tenant(tenant_id)

    # If plan changes, update limits
    if "piano" in filtered:
        limits = PIANI_DISPONIBILI.get(filtered["piano"], {})
        if limits:
            filtered["max_utenti"] = limits["max_utenti"]
            filtered["max_commesse"] = limits["max_commesse"]

    filtered["aggiornato_il"] = datetime.now(timezone.utc).isoformat()

    await db[COLLECTION].update_one(
        {"tenant_id": tenant_id},
        {"$set": filtered},
    )
    return await get_tenant(tenant_id)


async def deactivate_tenant(tenant_id: str) -> bool:
    """Soft-delete: set attivo=False."""
    result = await db[COLLECTION].update_one(
        {"tenant_id": tenant_id},
        {"$set": {"attivo": False, "aggiornato_il": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count > 0


async def list_tenants(only_active: bool = True) -> list:
    """List all tenants (admin function)."""
    query = {"attivo": True} if only_active else {}
    docs = await db[COLLECTION].find(query, {"_id": 0}).sort("creato_il", -1).to_list(500)

    # Enrich with user count
    for doc in docs:
        doc["utenti_count"] = await db.users.count_documents({"tenant_id": doc["tenant_id"]})
        doc["commesse_count"] = await db.commesse.count_documents({"tenant_id": doc["tenant_id"]})

    return docs


async def get_tenant_stats(tenant_id: str) -> dict:
    """Get usage stats for a tenant."""
    return {
        "utenti": await db.users.count_documents({"tenant_id": tenant_id}),
        "commesse": await db.commesse.count_documents({"tenant_id": tenant_id}),
        "fatture": await db.invoices.count_documents({"tenant_id": tenant_id}),
        "preventivi": await db.preventivi.count_documents({"tenant_id": tenant_id}),
        "clienti": await db.clients.count_documents({"tenant_id": tenant_id}),
    }


async def ensure_tenant_for_user(user_id: str, email: str, name: str) -> str:
    """Auto-onboarding: ensure a tenant exists for an admin user.
    
    Called during first login. If user has no tenant (or tenant_id='default'),
    create one automatically using their name as company name.
    Returns the tenant_id.
    """
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return "default"

    current_tid = user.get("tenant_id", "default")

    # Already has a real tenant
    if current_tid and current_tid != "default":
        tenant = await get_tenant(current_tid)
        if tenant and tenant.get("attivo"):
            return current_tid

    # Only auto-create for admin users
    if user.get("role") != "admin":
        return current_tid

    # Create a new tenant
    company_name = name or email.split("@")[0]
    tenant = await create_tenant(
        nome_azienda=company_name,
        admin_user_id=user_id,
        piano="pilot",
        email_contatto=email,
    )
    logger.info(f"Auto-created tenant {tenant['tenant_id']} for admin {email}")
    return tenant["tenant_id"]

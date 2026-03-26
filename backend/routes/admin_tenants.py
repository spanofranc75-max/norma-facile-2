"""Admin routes for multi-tenant management."""
from fastapi import APIRouter, Depends
from core.security import get_current_user, tenant_match
from core.rbac import require_role
from services.tenant_service import (
    create_tenant,
    get_tenant,
    update_tenant,
    deactivate_tenant,
    list_tenants,
    get_tenant_stats,
)

router = APIRouter(prefix="/api/admin/tenants", tags=["admin-tenants"])


@router.get("/")
async def api_list_tenants(
    active_only: bool = True,
    user: dict = Depends(require_role("admin")),
):
    """List all tenants (super-admin only)."""
    tenants = await list_tenants(only_active=active_only)
    return {"tenants": tenants, "total": len(tenants)}


@router.post("/")
async def api_create_tenant(
    body: dict,
    user: dict = Depends(require_role("admin")),
):
    """Create a new tenant manually."""
    nome = body.get("nome_azienda", "").strip()
    if not nome:
        return {"error": "nome_azienda obbligatorio"}, 400

    tenant = await create_tenant(
        nome_azienda=nome,
        admin_user_id=user["user_id"],
        piano=body.get("piano", "pilot"),
        partita_iva=body.get("partita_iva", ""),
        email_contatto=body.get("email_contatto", user.get("email", "")),
    )
    return {"tenant": tenant, "message": "Tenant creato con successo"}


@router.get("/my")
async def api_my_tenant(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico", "officina"))):
    """Get the current user's tenant info."""
    tid = tenant_match(user)
    tenant = await get_tenant(tid)
    if not tenant:
        return {"tenant": None, "message": "Nessun tenant associato"}

    stats = await get_tenant_stats(tid)
    return {"tenant": tenant, "stats": stats}


@router.get("/{tenant_id}")
async def api_get_tenant(
    tenant_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Get a specific tenant."""
    tenant = await get_tenant(tenant_id)
    if not tenant:
        return {"error": "Tenant non trovato"}, 404

    stats = await get_tenant_stats(tenant_id)
    return {"tenant": tenant, "stats": stats}


@router.put("/{tenant_id}")
async def api_update_tenant(
    tenant_id: str,
    body: dict,
    user: dict = Depends(require_role("admin")),
):
    """Update a tenant's details."""
    updated = await update_tenant(tenant_id, body)
    if not updated:
        return {"error": "Tenant non trovato"}, 404
    return {"tenant": updated, "message": "Tenant aggiornato"}


@router.delete("/{tenant_id}")
async def api_deactivate_tenant(
    tenant_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Deactivate a tenant (soft-delete)."""
    success = await deactivate_tenant(tenant_id)
    if not success:
        return {"error": "Tenant non trovato o gia disattivato"}, 404
    return {"message": "Tenant disattivato", "tenant_id": tenant_id}

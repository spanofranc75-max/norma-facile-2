"""Routes — Profili Documentali per Committente (D6)."""

from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user, tenant_match
from core.rbac import require_role
from services.profili_committente_service import (
    crea_profilo, crea_profilo_da_pacchetto, get_profilo,
    list_profili, update_profilo, delete_profilo,
    applica_profilo, suggerisci_profilo,
)
from services.audit_trail import log_activity

router = APIRouter(prefix="/profili-committente", tags=["Profili Committente D6"])


@router.get("")
async def api_list_profili(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    return await list_profili(user["user_id"], tenant_id=tenant_match(user))


@router.post("")
async def api_crea_profilo(data: dict, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    result = await crea_profilo(user["user_id"], data, tenant_id=tenant_match(user))
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "create", "profilo_committente", result["profile_id"],
                       label=result.get("client_name", ""),
                       details={"n_rules": len(result.get("rules", []))})
    return result


@router.post("/da-pacchetto/{pack_id}")
async def api_crea_da_pacchetto(
    pack_id: str,
    data: dict,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico")),
):
    """Create profile from an existing package (semi-automatic)."""
    result = await crea_profilo_da_pacchetto(
        user["user_id"], pack_id,
        client_name=data.get("client_name", ""),
        description=data.get("description", ""),
        tenant_id=tenant_match(user),
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "create", "profilo_committente", result["profile_id"],
                       label=f"{result.get('client_name', '')} (da pacchetto)",
                       details={"source_pack_id": pack_id, "n_rules": len(result.get("rules", []))})
    return result


@router.get("/suggest/{commessa_id}")
async def api_suggest_profilo(commessa_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Suggest a profile matching the client of a commessa."""
    profilo = await suggerisci_profilo(user["user_id"], commessa_id, tenant_id=tenant_match(user))
    return {"suggested_profile": profilo}


@router.get("/{profile_id}")
async def api_get_profilo(profile_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    profilo = await get_profilo(profile_id, user["user_id"], tenant_id=tenant_match(user))
    if not profilo:
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    return profilo


@router.put("/{profile_id}")
async def api_update_profilo(profile_id: str, data: dict, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    result = await update_profilo(profile_id, user["user_id"], data, tenant_id=tenant_match(user))
    if not result:
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    await log_activity(user, "update", "profilo_committente", profile_id,
                       label=result.get("client_name", ""),
                       details={"fields": list(data.keys())})
    return result


@router.delete("/{profile_id}")
async def api_delete_profilo(profile_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    profilo = await get_profilo(profile_id, user["user_id"], tenant_id=tenant_match(user))
    if not await delete_profilo(profile_id, user["user_id"], tenant_id=tenant_match(user)):
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    await log_activity(user, "delete", "profilo_committente", profile_id,
                       label=(profilo or {}).get("client_name", ""))
    return {"deleted": True}


@router.post("/{profile_id}/applica")
async def api_applica_profilo(
    profile_id: str,
    data: dict,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico")),
):
    """Apply profile to create a new document package for a commessa."""
    result = await applica_profilo(
        user["user_id"], profile_id,
        commessa_id=data.get("commessa_id", ""),
        cantiere_id=data.get("cantiere_id", ""),
        label=data.get("label", ""),
        tenant_id=tenant_match(user),
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    pack = result.get("pack", {})
    profilo = result.get("profile", {})
    await log_activity(user, "create", "pacchetto_documentale", pack.get("pack_id", ""),
                       label=f"Da profilo: {profilo.get('client_name', '')}",
                       commessa_id=data.get("commessa_id", ""),
                       details={"profile_id": profile_id, "n_items": len(pack.get("items", []))})
    return result

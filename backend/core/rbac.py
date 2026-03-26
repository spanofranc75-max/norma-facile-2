"""
Centralized RBAC (Role-Based Access Control) for NormaFacile 2.0.

Usage in routes:
    from core.rbac import require_role

    @router.get("/invoices/")
    async def list_invoices(user: dict = Depends(require_role("admin", "amministrazione"))):
        ...

Roles: admin, ufficio_tecnico, officina, amministrazione, guest
- admin: full access to everything
- ufficio_tecnico: technical operations, certifications, surveys
- officina: production floor only
- amministrazione: financial, clients, invoicing
- guest: read-only (no CRUD)
"""
import logging
from fastapi import Depends, HTTPException
from core.security import get_current_user

logger = logging.getLogger(__name__)

# Role → allowed route groups mapping (for reference/documentation)
ROLE_ACCESS = {
    "admin": ["*"],
    "ufficio_tecnico": [
        "operativo", "certificazioni", "perizie",
        "impostazioni", "commesse", "preventivi", "clienti",
    ],
    "officina": ["operativo", "commesse"],
    "amministrazione": [
        "acquisti", "impostazioni", "commesse",
        "preventivi", "clienti", "fatture", "ddt",
    ],
    "guest": [],
}


def require_role(*allowed_roles: str):
    """FastAPI dependency that enforces role-based access.

    Usage:
        user = Depends(require_role("admin", "amministrazione"))

    - admin always passes (wildcard).
    - If user's role is not in allowed_roles → 403.
    - Logs unauthorized attempts with tenant_id and user_id.
    """
    async def _check(user: dict = Depends(get_current_user)):
        role = user.get("role", "guest")

        # admin always passes
        if role == "admin":
            return user

        if role not in allowed_roles:
            logger.warning(
                "RBAC DENIED: user=%s tenant=%s role=%s attempted=%s allowed=%s",
                user.get("user_id"),
                user.get("tenant_id", "?"),
                role,
                allowed_roles,
                ROLE_ACCESS.get(role, []),
            )
            raise HTTPException(
                status_code=403,
                detail=f"Accesso negato. Il ruolo '{role}' non ha i permessi per questa operazione.",
            )
        return user

    return _check

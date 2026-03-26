"""Team & Role Management — Invite users, assign roles, permission checks.

Roles:
- admin: Full access to everything
- ufficio_tecnico: Commesse, FPC, welders, quality, production, tracciabilità
- officina: Production phases only (start/complete), no financials
- amministrazione: Invoices, costs, clients, DDT — no technical WPS/FPC editing
- guest: No data access, pending admin approval
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user, tenant_match

router = APIRouter(prefix="/team", tags=["team"])
logger = logging.getLogger(__name__)

VALID_ROLES = ["admin", "ufficio_tecnico", "officina", "amministrazione", "guest"]

# Role display labels (Italian)
ROLE_LABELS = {
    "admin": "Amministratore",
    "ufficio_tecnico": "Ufficio Tecnico",
    "officina": "Officina",
    "amministrazione": "Amministrazione",
    "guest": "In Attesa",
}

# Which sidebar groups each role can see
ROLE_PERMISSIONS = {
    "admin": ["*"],  # Everything
    "ufficio_tecnico": [
        "operativo", "certificazioni", "perizie", "impostazioni",
        "/dashboard", "/commesse", "/preventivi", "/clienti",
    ],
    "officina": [
        "operativo",
        "/dashboard", "/commesse",
    ],
    "amministrazione": [
        "acquisti", "impostazioni",
        "/dashboard", "/commesse", "/preventivi", "/clienti",
        "/fatture", "/ddt",
    ],
    "guest": [],
}


class InviteRequest(BaseModel):
    email: str
    role: str = "officina"
    name: Optional[str] = ""


class UpdateRoleRequest(BaseModel):
    role: str


# ── Helpers ──────────────────────────────────────────────────────

async def _get_admin_id(user: dict) -> str:
    """Get the admin user_id for the current user's team.
    Every user belongs to an admin's team. The admin's user_id is the 'team owner'.
    """
    role = user.get("role", "admin")
    if role == "admin":
        return user["user_id"]
    # Non-admin: find which admin invited them
    return user.get("team_owner_id", user["user_id"])


async def _ensure_admin(user: dict):
    """Raise 403 if user is not admin."""
    if user.get("role", "admin") != "admin":
        raise HTTPException(403, "Solo l'amministratore può gestire il team")


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/members")
async def list_team_members(user: dict = Depends(get_current_user)):
    """List all team members (invited + active)."""
    admin_id = await _get_admin_id(user)

    # Active members
    members = await db.users.find(
        {"$or": [{"user_id": admin_id}, {"team_owner_id": admin_id}], "tenant_id": tenant_match(user)},
        {"_id": 0, "user_id": 1, "email": 1, "name": 1, "picture": 1, "role": 1, "created_at": 1, "last_login": 1},
    ).to_list(50)

    # Pending invites (not yet logged in)
    invites = await db.team_invites.find(
        {"admin_id": admin_id, "status": "pending", "tenant_id": tenant_match(user)},
        {"_id": 0},
    ).to_list(50)

    return {
        "members": members,
        "invites": invites,
        "roles": ROLE_LABELS,
    }


@router.post("/invite")
async def invite_member(data: InviteRequest, user: dict = Depends(get_current_user)):
    """Pre-authorize an email with a specific role."""
    await _ensure_admin(user)

    if data.role not in VALID_ROLES or data.role == "admin":
        raise HTTPException(400, f"Ruolo non valido. Opzioni: {', '.join(r for r in VALID_ROLES if r != 'admin')}")

    email = data.email.strip().lower()
    admin_id = user["user_id"]

    # Check if already invited or already a member
    existing_invite = await db.team_invites.find_one({"admin_id": admin_id, "email": email, "status": "pending", "tenant_id": tenant_match(user)})
    if existing_invite:
        raise HTTPException(400, "Questo utente è già stato invitato")

    existing_user = await db.users.find_one({"email": email, "team_owner_id": admin_id, "tenant_id": tenant_match(user)})
    if existing_user:
        raise HTTPException(400, "Questo utente fa già parte del team")

    invite = {
        "invite_id": f"inv_{uuid.uuid4().hex[:10]}",
        "admin_id": admin_id,
        "email": email,
        "name": data.name or "",
        "role": data.role,
        "status": "pending",
        "tenant_id": tenant_match(user),
        "created_at": datetime.now(timezone.utc),
    }
    await db.team_invites.insert_one(invite)

    return {
        "message": f"Invito inviato a {email} con ruolo {ROLE_LABELS.get(data.role, data.role)}",
        "invite": {k: v for k, v in invite.items() if k != "_id"},
    }


@router.put("/members/{member_user_id}/role")
async def update_member_role(member_user_id: str, data: UpdateRoleRequest, user: dict = Depends(get_current_user)):
    """Change a team member's role."""
    await _ensure_admin(user)

    if data.role not in VALID_ROLES:
        raise HTTPException(400, "Ruolo non valido")

    if member_user_id == user["user_id"]:
        raise HTTPException(400, "Non puoi cambiare il tuo stesso ruolo")

    result = await db.users.update_one(
        {"user_id": member_user_id, "team_owner_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {"role": data.role, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Membro non trovato")

    return {"message": f"Ruolo aggiornato a {ROLE_LABELS.get(data.role, data.role)}"}


@router.delete("/members/{member_user_id}")
async def remove_member(member_user_id: str, user: dict = Depends(get_current_user)):
    """Remove a team member."""
    await _ensure_admin(user)

    if member_user_id == user["user_id"]:
        raise HTTPException(400, "Non puoi rimuovere te stesso")

    result = await db.users.delete_one({"user_id": member_user_id, "team_owner_id": user["user_id"], "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Membro non trovato")

    # Clean up sessions
    await db.user_sessions.delete_many({"user_id": member_user_id})

    return {"message": "Membro rimosso dal team"}


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: str, user: dict = Depends(get_current_user)):
    """Revoke a pending invite."""
    await _ensure_admin(user)

    result = await db.team_invites.delete_one({"invite_id": invite_id, "admin_id": user["user_id"], "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Invito non trovato")

    return {"message": "Invito revocato"}


@router.get("/my-role")
async def get_my_role(user: dict = Depends(get_current_user)):
    """Get current user's role and permissions."""
    role = user.get("role", "admin")
    return {
        "role": role,
        "label": ROLE_LABELS.get(role, role),
        "permissions": ROLE_PERMISSIONS.get(role, []),
    }

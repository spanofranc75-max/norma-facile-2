"""Routes — Notifiche Smart In-App (N1/N2)."""

from fastapi import APIRouter, Depends, Query
from core.security import get_current_user
from services.notifiche_smart_service import (
    list_notifiche, count_unread, mark_read, mark_all_read, archive_notification,
)

router = APIRouter(prefix="/notifiche-smart", tags=["Notifiche Smart"])


@router.get("")
async def api_list_notifiche(
    status: str = Query("", description="unread|read|archived or empty for all"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    return await list_notifiche(user["user_id"], status=status, limit=limit, skip=skip)


@router.get("/count")
async def api_count_unread(user: dict = Depends(get_current_user)):
    count = await count_unread(user["user_id"])
    return {"unread": count}


@router.post("/{notification_id}/read")
async def api_mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    ok = await mark_read(notification_id, user["user_id"])
    return {"marked": ok}


@router.post("/read-all")
async def api_mark_all_read(user: dict = Depends(get_current_user)):
    count = await mark_all_read(user["user_id"])
    return {"marked": count}


@router.post("/{notification_id}/archive")
async def api_archive(notification_id: str, user: dict = Depends(get_current_user)):
    ok = await archive_notification(notification_id, user["user_id"])
    return {"archived": ok}

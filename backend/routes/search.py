"""Global search across commesse, preventivi, clienti, DDT."""

from fastapi import APIRouter, Depends, Query

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def global_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    regex = {"$regex": q, "$options": "i"}
    results = []

    # Commesse
    commesse = await db.commesse.find(
        {"user_id": uid, "$or": [
            {"numero": regex}, {"title": regex}, {"client_name": regex},
        ]},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1, "stato": 1},
    ).limit(limit).to_list(limit)
    for c in commesse:
        results.append({
            "type": "commessa",
            "id": c["commessa_id"],
            "label": c.get("numero", ""),
            "subtitle": c.get("title", ""),
            "extra": c.get("client_name", ""),
            "stato": c.get("stato", ""),
            "url": f"/commesse/{c['commessa_id']}",
        })

    # Preventivi
    preventivi = await db.preventivi.find(
        {"user_id": uid, "$or": [
            {"number": regex}, {"subject": regex}, {"client_name": regex},
        ]},
        {"_id": 0, "preventivo_id": 1, "number": 1, "subject": 1, "client_name": 1, "status": 1},
    ).limit(limit).to_list(limit)
    for p in preventivi:
        results.append({
            "type": "preventivo",
            "id": p["preventivo_id"],
            "label": p.get("number", ""),
            "subtitle": p.get("subject", ""),
            "extra": p.get("client_name", ""),
            "stato": p.get("status", ""),
            "url": f"/preventivi/{p['preventivo_id']}",
        })

    # Clienti
    clienti = await db.clients.find(
        {"user_id": uid, "$or": [
            {"business_name": regex}, {"email": regex}, {"fiscal_code": regex},
        ]},
        {"_id": 0, "client_id": 1, "business_name": 1, "email": 1},
    ).limit(limit).to_list(limit)
    for cl in clienti:
        results.append({
            "type": "cliente",
            "id": cl["client_id"],
            "label": cl.get("business_name", ""),
            "subtitle": cl.get("email", ""),
            "extra": "",
            "stato": "",
            "url": f"/clienti/{cl['client_id']}",
        })

    # DDT
    ddt_docs = await db.ddt_documents.find(
        {"user_id": uid, "$or": [
            {"number": regex}, {"client_name": regex}, {"subject": regex},
        ]},
        {"_id": 0, "ddt_id": 1, "number": 1, "client_name": 1, "subject": 1},
    ).limit(limit).to_list(limit)
    for d in ddt_docs:
        results.append({
            "type": "ddt",
            "id": d["ddt_id"],
            "label": d.get("number", ""),
            "subtitle": d.get("subject", d.get("client_name", "")),
            "extra": d.get("client_name", ""),
            "stato": "",
            "url": f"/ddt/{d['ddt_id']}",
        })

    # Sort: commesse first, then preventivi, then rest
    type_order = {"commessa": 0, "preventivo": 1, "ddt": 2, "cliente": 3}
    results.sort(key=lambda r: type_order.get(r["type"], 99))

    return {"results": results[:limit], "total": len(results)}

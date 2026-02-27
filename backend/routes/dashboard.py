"""Dashboard stats routes for the Workshop Dashboard (Cruscotto Officina)."""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from services.profiles_data import calculate_bars_needed

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Ferro in Lavorazione: sum weight from active distinte (bozza, confermata, ordinata)
    active_statuses = ["bozza", "confermata", "ordinata"]
    pipeline_weight = [
        {"$match": {"user_id": uid, "status": {"$in": active_statuses}}},
        {"$group": {"_id": None, "total_weight": {"$sum": "$total_weight_kg"}, "count": {"$sum": 1}}},
    ]
    weight_result = await db.distinte.aggregate(pipeline_weight).to_list(1)
    ferro_kg = weight_result[0]["total_weight"] if weight_result else 0
    distinte_attive = weight_result[0]["count"] if weight_result else 0

    # 2. Cantieri Attivi: POS with status bozza or completo
    cantieri_attivi = await db.pos_documents.count_documents(
        {"user_id": uid, "status": {"$in": ["bozza", "completo"]}}
    )

    # 3. POS Generati questo mese
    pos_mese = await db.pos_documents.count_documents(
        {"user_id": uid, "created_at": {"$gte": month_start}}
    )

    # 4. Fatturato Mese: sum of emessa/pagata invoices this month
    pipeline_fatturato = [
        {"$match": {"user_id": uid, "status": {"$in": ["emessa", "pagata", "inviata_sdi", "accettata"]}, "created_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "total": {"$sum": "$totals.total_document"}}},
    ]
    fatt_result = await db.invoices.aggregate(pipeline_fatturato).to_list(1)
    fatturato_mese = fatt_result[0]["total"] if fatt_result else 0

    # 5. Prossime Scadenze: POS with start_date in the future
    scadenze_cursor = db.pos_documents.find(
        {"user_id": uid, "status": {"$in": ["bozza", "completo"]}},
        {"_id": 0, "pos_id": 1, "project_name": 1, "cantiere": 1, "status": 1}
    ).sort("cantiere.start_date", 1).limit(5)
    scadenze_raw = await scadenze_cursor.to_list(5)
    scadenze = []
    for s in scadenze_raw:
        cantiere = s.get("cantiere", {})
        start = cantiere.get("start_date", "")
        duration = cantiere.get("duration_days", 30)
        if start:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                from datetime import timedelta
                end_dt = start_dt + timedelta(days=int(duration))
                scadenze.append({
                    "pos_id": s["pos_id"],
                    "project_name": s["project_name"],
                    "deadline": end_dt.strftime("%d/%m/%Y"),
                    "city": cantiere.get("city", ""),
                })
            except (ValueError, TypeError):
                pass

    # 6. Materiale da Ordinare: aggregate items from active distinte
    active_distinte = await db.distinte.find(
        {"user_id": uid, "status": {"$in": active_statuses}},
        {"_id": 0, "items": 1}
    ).to_list(100)

    all_items = []
    for d in active_distinte:
        all_items.extend(d.get("items", []))

    materiale = []
    if all_items:
        bar_results = calculate_bars_needed(all_items)
        materiale = [
            {"profile": r["profile_label"], "bars": r["bars_needed"], "total_m": r["total_length_m"]}
            for r in bar_results if r["bars_needed"] > 0
        ][:8]

    # 7. Documenti recenti (last 5 invoices)
    recent_inv_cursor = db.invoices.find(
        {"user_id": uid}, {"_id": 0, "invoice_id": 1, "document_number": 1, "client_name": 1, "status": 1, "issue_date": 1, "totals": 1}
    ).sort("created_at", -1).limit(5)
    recent_invoices = await recent_inv_cursor.to_list(5)
    for inv in recent_invoices:
        if "issue_date" in inv and inv["issue_date"]:
            inv["issue_date"] = str(inv["issue_date"])

    return {
        "ferro_kg": round(ferro_kg, 1),
        "distinte_attive": distinte_attive,
        "cantieri_attivi": cantieri_attivi,
        "pos_mese": pos_mese,
        "fatturato_mese": round(fatturato_mese, 2),
        "scadenze": scadenze,
        "materiale": materiale,
        "recent_invoices": recent_invoices,
    }

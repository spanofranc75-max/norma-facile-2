"""Dashboard stats routes for the Workshop Dashboard (Cruscotto Officina)."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
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

    # 8. Fatturato Mensile — last 6 months for chart
    fatturato_mensile = []
    mesi_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    for i in range(5, -1, -1):
        m_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)
        pipeline_m = [
            {"$match": {
                "user_id": uid,
                "status": {"$in": ["emessa", "pagata", "inviata_sdi", "accettata"]},
                "created_at": {"$gte": m_start, "$lt": m_end},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$totals.total_document"}, "count": {"$sum": 1}}},
        ]
        m_result = await db.invoices.aggregate(pipeline_m).to_list(1)
        fatturato_mensile.append({
            "mese": f"{mesi_it[m_start.month - 1]} {m_start.year}",
            "mese_short": mesi_it[m_start.month - 1],
            "importo": round(m_result[0]["total"], 2) if m_result else 0,
            "documenti": m_result[0]["count"] if m_result else 0,
        })

    return {
        "ferro_kg": round(ferro_kg, 1),
        "distinte_attive": distinte_attive,
        "cantieri_attivi": cantieri_attivi,
        "pos_mese": pos_mese,
        "fatturato_mese": round(fatturato_mese, 2),
        "scadenze": scadenze,
        "materiale": materiale,
        "recent_invoices": recent_invoices,
        "fatturato_mensile": fatturato_mensile,
    }


@router.get("/fascicolo/{client_id}")
async def get_fascicolo_cantiere(client_id: str, user: dict = Depends(get_current_user)):
    """Aggregate all documents for a client into a 'Fascicolo Cantiere' (Project Dossier)."""
    uid = user["user_id"]

    # Client info
    client = await db.clients.find_one(
        {"client_id": client_id, "user_id": uid}, {"_id": 0}
    )
    if not client:
        raise HTTPException(404, "Cliente non trovato")

    # Rilievi
    rilievi = await db.rilievi.find(
        {"user_id": uid, "client_id": client_id},
        {"_id": 0, "rilievo_id": 1, "project_name": 1, "status": 1, "location": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)

    # Distinte
    distinte = await db.distinte.find(
        {"user_id": uid, "client_id": client_id},
        {"_id": 0, "distinta_id": 1, "name": 1, "status": 1, "totals": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)

    # Preventivi
    preventivi = await db.preventivi.find(
        {"user_id": uid, "client_id": client_id},
        {"_id": 0, "preventivo_id": 1, "number": 1, "subject": 1, "status": 1, "totals": 1, "compliance_status": 1, "converted_to_invoice_id": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)

    # Fatture
    invoices = await db.invoices.find(
        {"user_id": uid, "client_id": client_id},
        {"_id": 0, "invoice_id": 1, "document_number": 1, "document_type": 1, "status": 1, "totals": 1, "issue_date": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)
    for inv in invoices:
        if "issue_date" in inv and inv["issue_date"]:
            inv["issue_date"] = str(inv["issue_date"])

    # Certificazioni
    certs = await db.certificazioni.find(
        {"user_id": uid, "client_id": client_id},
        {"_id": 0, "cert_id": 1, "project_name": 1, "standard": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)

    # POS — fetched for context but currently not client-filtered
    # (POS are project-based, not always linked to a client_id)
    _ = await db.pos_documents.find(
        {"user_id": uid},
        {"_id": 0, "pos_id": 1, "project_name": 1, "status": 1, "cantiere": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(50)

    # Build timeline events sorted by date
    timeline = []
    for r in rilievi:
        timeline.append({
            "type": "rilievo", "id": r["rilievo_id"],
            "title": r.get("project_name", "Rilievo"),
            "status": r.get("status", "bozza"),
            "date": str(r.get("created_at", "")),
            "link": f"/rilievi/{r['rilievo_id']}",
        })
    for d in distinte:
        timeline.append({
            "type": "distinta", "id": d["distinta_id"],
            "title": d.get("name", "Distinta"),
            "status": d.get("status", "bozza"),
            "date": str(d.get("created_at", "")),
            "link": f"/distinte/{d['distinta_id']}",
            "extra": f"{d.get('totals', {}).get('total_weight_kg', 0):.1f} kg",
        })
    for p in preventivi:
        timeline.append({
            "type": "preventivo", "id": p["preventivo_id"],
            "title": f"PRV {p.get('number', '')}",
            "status": p.get("status", "bozza"),
            "date": str(p.get("created_at", "")),
            "link": f"/preventivi/{p['preventivo_id']}",
            "extra": f"{p.get('totals', {}).get('total', 0):.2f}",
        })
    for inv in invoices:
        timeline.append({
            "type": "fattura", "id": inv["invoice_id"],
            "title": inv.get("document_number", "Fattura"),
            "status": inv.get("status", "bozza"),
            "date": str(inv.get("created_at", "")),
            "link": f"/invoices/{inv['invoice_id']}",
            "extra": f"{inv.get('totals', {}).get('total_document', 0):.2f}",
        })
    for c in certs:
        timeline.append({
            "type": "certificazione", "id": c["cert_id"],
            "title": c.get("project_name", "Certificazione CE"),
            "status": c.get("status", "bozza"),
            "date": str(c.get("created_at", "")),
            "link": f"/certificazioni/{c['cert_id']}",
        })

    timeline.sort(key=lambda x: x["date"], reverse=True)

    # Document counts
    documents = {
        "rilievi": len(rilievi),
        "distinte": len(distinte),
        "preventivi": len(preventivi),
        "fatture": len(invoices),
        "certificazioni": len(certs),
    }

    return {
        "client": client,
        "timeline": timeline,
        "documents": documents,
        "rilievi": rilievi,
        "distinte": distinte,
        "preventivi": preventivi,
        "invoices": invoices,
        "certificazioni": certs,
    }

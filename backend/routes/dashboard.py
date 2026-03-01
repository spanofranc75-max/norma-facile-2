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
        # Precise month calculation using month arithmetic
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        m_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
        if target_month == 12:
            m_end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            m_end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
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


@router.get("/compliance-en1090")
async def get_compliance_overview(user: dict = Depends(get_current_user)):
    """Dashboard widget: EN 1090 compliance status for all commesse with fascicolo tecnico data."""
    uid = user["user_id"]
    # Include all states except draft — any commessa that has been worked on
    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$nin": ["bozza"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1,
         "client_id": 1, "fascicolo_tecnico": 1, "fasi_produzione": 1,
         "classe_esecuzione": 1}
    ).sort("created_at", -1).to_list(50)

    # Filter: only commesse that have fascicolo_tecnico data OR classe_esecuzione set
    en1090_commesse = []
    for c in commesse:
        ft = c.get("fascicolo_tecnico", {})
        has_ft_data = any(v for k, v in ft.items() if k != "_id" and v) if ft else False
        has_classe = bool(c.get("classe_esecuzione"))
        if has_ft_data or has_classe:
            en1090_commesse.append(c)

    commesse = en1090_commesse

    # Required doc fields per document type
    shared_auto = ["client_name", "commessa_numero", "commessa_title"]
    doc_reqs = {
        "DOP": ["certificato_numero", "ente_notificato", "firmatario", "luogo_data_firma", "ddt_riferimento"],
        "CE": ["certificato_numero", "ente_notificato", "ente_numero", "disegno_riferimento"],
        "Piano Ctrl": ["disegno_numero"],
        "Rapporto VT": ["report_numero", "report_data", "processo_saldatura", "materiale"],
        "Reg. Saldatura": ["data_emissione", "firma_cs"],
        "Riesame": [],
    }

    results = []
    for c in commesse:
        ft = c.get("fascicolo_tecnico", {})
        # Count completed docs
        docs_status = {}
        total_filled = 0
        total_fields = 0
        for doc_name, req_fields in doc_reqs.items():
            all_fields = shared_auto + req_fields
            filled = sum(1 for f in all_fields if ft.get(f) and str(ft[f]).strip())
            total_filled += filled
            total_fields += len(all_fields)
            docs_status[doc_name] = {"filled": filled, "total": len(all_fields), "complete": filled == len(all_fields)}

        # Production progress
        fasi = c.get("fasi_produzione", [])
        prod_done = sum(1 for f in fasi if f.get("stato") == "completato")
        prod_total = len(fasi) if fasi else 0

        # Client name
        cl_name = ""
        if c.get("client_id"):
            cl = await db.clients.find_one({"client_id": c["client_id"]}, {"_id": 0, "name": 1})
            cl_name = cl.get("name", "") if cl else ""

        pct = round((total_filled / total_fields * 100)) if total_fields else 0
        results.append({
            "commessa_id": c["commessa_id"],
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "stato": c.get("stato", ""),
            "client_name": cl_name,
            "classe_esecuzione": c.get("classe_esecuzione", ""),
            "compliance_pct": pct,
            "docs": docs_status,
            "prod_progress": {"done": prod_done, "total": prod_total},
        })

    # Sort: incomplete first
    results.sort(key=lambda x: x["compliance_pct"])
    return {"commesse": results, "total": len(results)}



# ── Officina Quality Score (SRA) ────────────────────────────────

@router.get("/quality-score")
async def get_quality_score(user: dict = Depends(get_current_user)):
    """Calculate Officina Quality Score (0-100) — adaptive based on user's actual workflow."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    insights = []

    # ── Count base entities ──
    total_rilievi = await db.rilievi.count_documents({"user_id": uid})
    total_pos = await db.pos_documents.count_documents({"user_id": uid})
    total_invoices = await db.invoices.count_documents({"user_id": uid})
    total_certs = await db.certificazioni.count_documents({"user_id": uid})
    total_prev = await db.preventivi.count_documents({"user_id": uid})
    total_distinte = await db.distinte.count_documents({"user_id": uid})
    total_commesse = await db.commesse.count_documents({"user_id": uid, "stato": {"$nin": ["bozza"]}})
    total_ddt = await db.ddt_documents.count_documents({"user_id": uid})

    # Quality Hub data
    total_welders = await db.welders.count_documents({"is_active": True})
    total_instruments = await db.instruments.count_documents({"status": {"$nin": ["fuori_uso"]}})
    total_audits = await db.audits.count_documents({"user_id": uid})
    open_ncs = await db.non_conformities.count_documents({"user_id": uid, "status": {"$ne": "chiusa"}})

    # Check if user has EN 1090 commesse (with fascicolo tecnico data)
    en1090_count = 0
    ft_ce_count = 0  # Commesse with CE/DoP data in fascicolo tecnico
    async for c in db.commesse.find({"user_id": uid, "stato": {"$nin": ["bozza"]}}, {"_id": 0, "fascicolo_tecnico": 1, "classe_esecuzione": 1}).limit(50):
        ft = c.get("fascicolo_tecnico", {})
        has_ft = any(v for k, v in ft.items() if k != "_id" and v) if ft else False
        if has_ft or c.get("classe_esecuzione"):
            en1090_count += 1
            # Check if CE/DoP fields are filled in the fascicolo tecnico
            ce_fields = ["certificato_numero", "ente_notificato", "dop_numero"]
            if any(ft.get(f) for f in ce_fields):
                ft_ce_count += 1

    # Total CE: standalone certificazioni + commesse with CE in fascicolo tecnico
    total_ce_effective = total_certs + ft_ce_count

    # ── Build adaptive categories ──
    # Each category: (key, label, calculator, relevance_check)
    categories = []

    # 1. Commesse & Produzione — always relevant if user has commesse
    if total_commesse > 0 or total_prev > 0:
        commesse_score = 0
        max_pts = 0
        # Has commesse: up to 10 pts
        if total_commesse > 0:
            commesse_score += min(total_commesse, 5) * 2  # max 10
            max_pts += 10
        # Has DDT: up to 5 pts
        if total_commesse > 0:
            ddt_ratio = min(total_ddt / max(total_commesse, 1), 1.0)
            commesse_score += round(ddt_ratio * 5)
            max_pts += 5
        categories.append(("production", "Commesse & Produzione", min(commesse_score, max_pts), max_pts))

    # 2. Documentazione — always relevant
    doc_items = sum(1 for x in [total_prev, total_distinte, total_invoices, total_commesse, total_ddt] if x > 0)
    doc_max = 5
    doc_score = round((doc_items / doc_max) * 15)
    categories.append(("documentation", "Documentazione", min(doc_score, 15), 15))

    # 3. Certificazioni CE — only if user does EN 1090 work
    if en1090_count > 0 or total_ce_effective > 0:
        if en1090_count > 0:
            ce_ratio = min(total_ce_effective / max(en1090_count, 1), 1.0)
            ce_score = round(ce_ratio * 20)
        else:
            ce_score = 5 if total_ce_effective > 0 else 0
        categories.append(("ce", "Certificazioni CE", min(ce_score, 20), 20))
        if total_ce_effective == 0:
            insights.append({
                "type": "warning",
                "text": "Nessuna certificazione CE emessa. Genera il fascicolo tecnico per i tuoi prodotti!",
                "action": "/certificazioni",
                "points": 15,
            })

    # 4. Sicurezza — only if user does rilievi/POS
    if total_rilievi > 0 or total_pos > 0:
        if total_rilievi > 0:
            safety_pct = min(total_pos / total_rilievi, 1.0)
            safety_score = round(safety_pct * 15)
        else:
            safety_score = 10 if total_pos > 0 else 0
        categories.append(("safety", "Sicurezza Cantieri", min(safety_score, 15), 15))
        missing_pos = max(total_rilievi - total_pos, 0)
        if missing_pos > 0:
            insights.append({
                "type": "warning",
                "text": f"{missing_pos} cantier{'e' if missing_pos == 1 else 'i'} senza POS.",
                "action": "/sicurezza",
                "points": min(missing_pos * 3, 10),
            })

    # 5. Qualità (Registro Saldatori, Strumenti, Audit) — relevant if user has any
    if total_welders > 0 or total_instruments > 0 or total_audits > 0:
        quality_items = sum(1 for x in [total_welders, total_instruments, total_audits] if x > 0)
        quality_score = round((quality_items / 3) * 10)
        # Bonus for closed NCs
        if total_audits > 0 and open_ncs == 0:
            quality_score = min(quality_score + 5, 15)
        categories.append(("quality", "Sistema Qualità", min(quality_score, 15), 15))
        if open_ncs > 0:
            insights.append({
                "type": "warning",
                "text": f"{open_ncs} non conformità aperte da risolvere.",
                "action": "/audit",
                "points": min(open_ncs * 3, 10),
            })

    # 6. Attività Recente — always relevant
    week_ago = now - timedelta(days=7)
    recent_sessions = await db.user_sessions.count_documents({"user_id": uid, "created_at": {"$gte": week_ago}})
    recent_docs = 0
    for coll_name in ["invoices", "preventivi", "rilievi", "distinte", "ddt_documents"]:
        recent_docs += await db[coll_name].count_documents({"user_id": uid, "created_at": {"$gte": week_ago}})
    activity_raw = min(recent_sessions, 7) + min(recent_docs, 8)
    activity_score = round(min(activity_raw / 15, 1.0) * 10)
    categories.append(("activity", "Attività Recente", min(activity_score, 10), 10))

    # ── Adaptive scoring: normalize to 100 ──
    raw_total = sum(c[2] for c in categories)
    raw_max = sum(c[3] for c in categories)
    total_score = round((raw_total / raw_max) * 100) if raw_max > 0 else 0
    total_score = min(total_score, 100)

    # Add onboarding insights if very few items
    if total_prev == 0:
        insights.append({
            "type": "info",
            "text": "Crea il tuo primo preventivo per iniziare a tracciare le commesse.",
            "action": "/preventivi",
            "points": 5,
        })

    # Sort insights by points (highest first), keep top 3
    insights.sort(key=lambda x: x.get("points", 0), reverse=True)
    insights = insights[:3]

    # Level
    if total_score >= 80:
        level = "Maestro Artigiano"
        level_color = "emerald"
    elif total_score >= 60:
        level = "Artigiano Esperto"
        level_color = "blue"
    elif total_score >= 40:
        level = "Artigiano in Crescita"
        level_color = "amber"
    else:
        level = "Apprendista"
        level_color = "slate"

    # Build breakdown from categories (normalized to display)
    breakdown = {}
    for key, label, score, max_pts in categories:
        # Scale each category proportionally to 100
        display_max = round((max_pts / raw_max) * 100) if raw_max > 0 else 0
        display_score = round((score / raw_max) * 100) if raw_max > 0 else 0
        breakdown[key] = {"score": display_score, "max": display_max, "label": label}

    return {
        "total_score": total_score,
        "level": level,
        "level_color": level_color,
        "breakdown": breakdown,
        "insights": insights,
        "stats": {
            "total_rilievi": total_rilievi,
            "total_pos": total_pos,
            "total_certs": total_certs,
            "total_invoices": total_invoices,
            "total_prev": total_prev,
            "total_distinte": total_distinte,
            "total_commesse": total_commesse,
            "total_welders": total_welders,
            "total_instruments": total_instruments,
        },
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



# ── EBITDA / Financial Analysis ─────────────────────────────────

@router.get("/ebitda")
async def get_ebitda(
    year: int = None,
    user: dict = Depends(get_current_user)
):
    """Get EBITDA financial analysis: Revenue vs Costs by month."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    year = year or now.year

    mesi_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
               "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    monthly = []
    ytd_revenue = 0
    ytd_costs = 0

    for month in range(1, 13):
        m_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            m_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            m_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Revenue: emitted invoices (fatture emesse)
        rev_pipeline = [
            {"$match": {
                "user_id": uid,
                "status": {"$in": ["emessa", "pagata", "inviata_sdi", "accettata"]},
                "created_at": {"$gte": m_start, "$lt": m_end},
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$totals.total_document"},
                "count": {"$sum": 1}
            }},
        ]
        rev_result = await db.invoices.aggregate(rev_pipeline).to_list(1)
        revenue = round(rev_result[0]["total"], 2) if rev_result else 0
        rev_count = rev_result[0]["count"] if rev_result else 0

        # Costs: received invoices (fatture ricevute)
        cost_pipeline = [
            {"$match": {
                "user_id": uid,
                "created_at": {"$gte": m_start, "$lt": m_end},
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$totale_documento"},
                "count": {"$sum": 1}
            }},
        ]
        cost_result = await db.fatture_ricevute.aggregate(cost_pipeline).to_list(1)
        costs = round(cost_result[0]["total"], 2) if cost_result else 0
        cost_count = cost_result[0]["count"] if cost_result else 0

        margin = round(revenue - costs, 2)
        margin_pct = round((margin / revenue * 100), 1) if revenue > 0 else 0

        # Only accumulate for months up to current
        if year == now.year and month <= now.month:
            ytd_revenue += revenue
            ytd_costs += costs
        elif year < now.year:
            ytd_revenue += revenue
            ytd_costs += costs

        monthly.append({
            "month": month,
            "month_label": mesi_it[month - 1],
            "revenue": revenue,
            "costs": costs,
            "margin": margin,
            "margin_pct": margin_pct,
            "rev_count": rev_count,
            "cost_count": cost_count,
        })

    ytd_margin = round(ytd_revenue - ytd_costs, 2)
    ytd_margin_pct = round((ytd_margin / ytd_revenue * 100), 1) if ytd_revenue > 0 else 0

    # Top expense categories from fatture ricevute
    cat_pipeline = [
        {"$match": {"user_id": uid, "created_at": {
            "$gte": datetime(year, 1, 1, tzinfo=timezone.utc),
            "$lt": datetime(year + 1, 1, 1, tzinfo=timezone.utc),
        }}},
        {"$group": {
            "_id": "$fornitore_nome",
            "total": {"$sum": "$totale_documento"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"total": -1}},
        {"$limit": 10},
    ]
    top_suppliers = await db.fatture_ricevute.aggregate(cat_pipeline).to_list(10)
    top_suppliers = [
        {"supplier": s["_id"] or "Non specificato", "total": round(s["total"], 2), "count": s["count"]}
        for s in top_suppliers
    ]

    # Payment status breakdown
    paid_pipeline = [
        {"$match": {
            "user_id": uid,
            "status": {"$in": ["emessa", "pagata", "inviata_sdi", "accettata"]},
            "created_at": {
                "$gte": datetime(year, 1, 1, tzinfo=timezone.utc),
                "$lt": datetime(year + 1, 1, 1, tzinfo=timezone.utc),
            },
        }},
        {"$group": {
            "_id": "$payment_status",
            "total": {"$sum": "$totals.total_document"},
            "count": {"$sum": 1},
        }},
    ]
    payment_breakdown = await db.invoices.aggregate(paid_pipeline).to_list(10)
    incassato = sum(p["total"] for p in payment_breakdown if p["_id"] == "pagata")
    da_incassare = sum(p["total"] for p in payment_breakdown if p["_id"] in [None, "non_pagata", "parzialmente_pagata"])

    return {
        "year": year,
        "monthly": monthly,
        "ytd": {
            "revenue": round(ytd_revenue, 2),
            "costs": round(ytd_costs, 2),
            "margin": ytd_margin,
            "margin_pct": ytd_margin_pct,
        },
        "incassato": round(incassato, 2),
        "da_incassare": round(da_incassare, 2),
        "top_suppliers": top_suppliers,
    }

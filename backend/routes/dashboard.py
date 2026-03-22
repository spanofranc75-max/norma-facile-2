"""Dashboard stats routes for the Workshop Dashboard (Cruscotto Officina)."""
import io
import os
import zipfile
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta, date
from core.security import get_current_user
from core.database import db
from services.profiles_data import calculate_bars_needed

logger = logging.getLogger(__name__)
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


@router.get("/compliance-docs")
async def get_compliance_docs_status(user: dict = Depends(get_current_user)):
    """Stato conformita documenti aziendali + allegati POS con previsione 30 giorni."""
    from models.company_doc import GLOBAL_DOC_TYPES, ALLEGATI_POS_TYPES
    today = date.today()

    # Global docs
    global_docs = await db.company_documents.find(
        {"category": "sicurezza_globale"}, {"_id": 0}
    ).to_list(50)
    global_map = {}
    for d in global_docs:
        tag = (d.get("tags", []) or [None])[0]
        if tag:
            global_map[tag] = d

    docs_status = []
    for dtype, meta in GLOBAL_DOC_TYPES.items():
        d = global_map.get(dtype)
        if d:
            scadenza = d.get("scadenza", "")
            days_left = None
            status = "valido"
            if scadenza:
                try:
                    exp = date.fromisoformat(scadenza)
                    days_left = (exp - today).days
                    if days_left <= 0:
                        status = "scaduto"
                    elif days_left <= 15:
                        status = "critico"
                    elif days_left <= 30:
                        status = "in_scadenza"
                except (ValueError, TypeError):
                    pass
            else:
                status = "no_scadenza"
            docs_status.append({
                "tipo": dtype, "label": meta["label"],
                "presente": True, "scadenza": scadenza,
                "days_left": days_left, "status": status,
            })
        else:
            docs_status.append({
                "tipo": dtype, "label": meta["label"],
                "presente": False, "scadenza": None,
                "days_left": None, "status": "mancante",
            })

    # Allegati POS
    pos_docs = await db.company_documents.find(
        {"category": "allegati_pos"}, {"_id": 0}
    ).to_list(50)
    pos_map = {}
    for d in pos_docs:
        tag = (d.get("tags", []) or [None])[0]
        if tag:
            pos_map[tag] = d

    allegati_status = []
    for dtype, meta in ALLEGATI_POS_TYPES.items():
        d = pos_map.get(dtype)
        allegati_status.append({
            "tipo": dtype, "label": meta["label"],
            "presente": d is not None,
            "includi_pos": d.get("includi_pos", True) if d else True,
        })

    # Aggregate
    total_global = len(GLOBAL_DOC_TYPES)
    caricati_global = sum(1 for s in docs_status if s["presente"])
    scaduti = [s for s in docs_status if s["status"] == "scaduto"]
    critici = [s for s in docs_status if s["status"] == "critico"]
    in_scadenza = [s for s in docs_status if s["status"] == "in_scadenza"]
    mancanti = [s for s in docs_status if s["status"] == "mancante"]

    total_pos = len(ALLEGATI_POS_TYPES)
    caricati_pos = sum(1 for s in allegati_status if s["presente"])

    # Conformita % for commesse
    commesse_attive = await db.commesse.find(
        {"user_id": user["user_id"], "stato": {"$nin": ["chiuso", "sospesa"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1,
         "deadline": 1, "cantiere": 1}
    ).sort("created_at", -1).to_list(50)

    commesse_compliance = []
    for c in commesse_attive:
        # Stima durata dalla deadline o dal cantiere
        deadline_str = c.get("deadline") or ""
        cantiere_data = c.get("cantiere", {})
        if isinstance(cantiere_data, dict):
            deadline_str = deadline_str or cantiere_data.get("end_date", "")
        end_date = None
        if deadline_str:
            try:
                end_date = date.fromisoformat(str(deadline_str)[:10])
            except (ValueError, TypeError):
                pass

        # Calcola quanti documenti saranno validi per la durata della commessa
        validi_per_commessa = 0
        problemi = []
        for s in docs_status:
            if not s["presente"]:
                problemi.append(f"{s['label']}: mancante")
                continue
            if s["status"] == "scaduto":
                problemi.append(f"{s['label']}: scaduto")
                continue
            if end_date and s["days_left"] is not None:
                remaining_at_end = s["days_left"] - (end_date - today).days
                if remaining_at_end < 0:
                    problemi.append(f"{s['label']}: scade prima della fine lavori")
                    continue
            validi_per_commessa += 1

        pct = round(validi_per_commessa / total_global * 100) if total_global > 0 else 0
        commesse_compliance.append({
            "commessa_id": c["commessa_id"],
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "client_name": c.get("client_name", ""),
            "deadline": str(deadline_str) if deadline_str else None,
            "pct_conforme": pct,
            "problemi": problemi,
        })

    return {
        "documenti": docs_status,
        "allegati_pos": allegati_status,
        "riepilogo": {
            "totale_globali": total_global,
            "caricati_globali": caricati_global,
            "totale_pos": total_pos,
            "caricati_pos": caricati_pos,
            "scaduti": len(scaduti),
            "critici": len(critici),
            "in_scadenza_30gg": len(in_scadenza),
            "mancanti": len(mancanti),
        },
        "alert_30gg": [s for s in docs_status if s["status"] in ("in_scadenza", "critico", "scaduto")],
        "commesse_compliance": commesse_compliance,
    }


@router.get("/fascicolo-aziendale")
async def download_fascicolo_aziendale(user: dict = Depends(get_current_user)):
    """Scarica ZIP con tutti i documenti aziendali globali (DURC, Visura, DVR, etc.)."""
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "company_docs")
    global_docs = await db.company_documents.find(
        {"category": {"$in": ["sicurezza_globale", "allegati_pos"]}},
        {"_id": 0}
    ).to_list(50)

    if not global_docs:
        raise HTTPException(404, "Nessun documento aziendale caricato")

    zip_buffer = io.BytesIO()
    files_added = 0
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in global_docs:
            safe_fn = doc.get("safe_filename", "")
            fpath = os.path.join(upload_dir, safe_fn)
            if safe_fn and os.path.exists(fpath):
                cat = doc.get("category", "")
                folder = "01_DOCUMENTI_AZIENDA" if cat == "sicurezza_globale" else "02_ALLEGATI_POS"
                label = doc.get("title", "").upper().replace(" ", "_")
                filename = doc.get("filename", safe_fn)
                with open(fpath, "rb") as f:
                    zf.writestr(f"{folder}/{label}_{filename}", f.read())
                files_added += 1

        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        zf.writestr("INFO.txt", f"Fascicolo Aziendale — Steel Project Design\nGenerato: {now_str}\nDocumenti inclusi: {files_added}\n")

    if files_added == 0:
        raise HTTPException(404, "Nessun file trovato su disco")

    zip_buffer.seek(0)
    fname = f"Fascicolo_Aziendale_{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buffer, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/commessa-compliance/{commessa_id}")
async def check_commessa_compliance(commessa_id: str, user: dict = Depends(get_current_user)):
    """Validazione preventiva: i documenti aziendali coprono la durata della commessa?"""
    from models.company_doc import GLOBAL_DOC_TYPES

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "deadline": 1, "cantiere": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    today = date.today()
    deadline_str = commessa.get("deadline") or ""
    cantiere_data = commessa.get("cantiere", {})
    if isinstance(cantiere_data, dict):
        deadline_str = deadline_str or cantiere_data.get("end_date", "")
    end_date = None
    if deadline_str:
        try:
            end_date = date.fromisoformat(str(deadline_str)[:10])
        except (ValueError, TypeError):
            pass

    global_docs = await db.company_documents.find(
        {"category": "sicurezza_globale"}, {"_id": 0}
    ).to_list(50)
    gmap = {}
    for d in global_docs:
        tag = (d.get("tags", []) or [None])[0]
        if tag:
            gmap[tag] = d

    checks = []
    bloccanti = []
    for dtype, meta in GLOBAL_DOC_TYPES.items():
        d = gmap.get(dtype)
        if not d:
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "mancante", "messaggio": f"{meta['label']} non caricato"})
            bloccanti.append(f"{meta['label']}: mancante")
            continue

        scadenza = d.get("scadenza", "")
        if not scadenza:
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "no_scadenza", "messaggio": f"{meta['label']} caricato, scadenza non impostata"})
            continue

        try:
            exp = date.fromisoformat(scadenza)
            days_left = (exp - today).days
        except (ValueError, TypeError):
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "errore", "messaggio": "Data scadenza non valida"})
            continue

        if days_left <= 0:
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "scaduto", "messaggio": f"{meta['label']} scaduto il {scadenza}"})
            bloccanti.append(f"{meta['label']}: scaduto il {scadenza}")
        elif end_date and (exp < end_date):
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "insufficiente",
                           "messaggio": f"{meta['label']} scade il {scadenza}, prima della fine lavori ({end_date.isoformat()})"})
            bloccanti.append(f"{meta['label']}: scade prima della fine lavori")
        else:
            checks.append({"tipo": dtype, "label": meta["label"], "esito": "ok", "messaggio": f"Valido (scade {scadenza}, {days_left}gg)"})

    conforme = len(bloccanti) == 0
    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "conforme": conforme,
        "bloccanti": bloccanti,
        "checks": checks,
    }
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


@router.get("/semaforo")
async def get_commesse_semaforo(user: dict = Depends(get_current_user)):
    """Traffic light view of active commesse: green/yellow/red based on deadline proximity."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    today = now.date()

    # Fetch active commesse (not chiuso)
    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$nin": ["chiuso"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1,
         "client_name": 1, "deadline": 1, "priority": 1, "value": 1,
         "fasi_produzione": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(100)

    items = []
    counts = {"green": 0, "yellow": 0, "red": 0}

    for c in commesse:
        # Production progress
        fasi = c.get("fasi_produzione", [])
        prod_done = sum(1 for f in fasi if f.get("stato") == "completato")
        prod_total = len(fasi) if fasi else 0

        # Calculate per-phase delays
        fasi_in_ritardo = 0
        for f in fasi:
            if f.get("stato") == "completato":
                continue
            dp = f.get("data_prevista")
            if dp:
                try:
                    dp_date = datetime.strptime(dp, "%Y-%m-%d").date()
                    if dp_date < today:
                        fasi_in_ritardo += 1
                except (ValueError, TypeError):
                    pass

        # Calculate traffic light
        deadline_str = c.get("deadline")
        semaforo = "green"
        days_left = None

        if deadline_str:
            try:
                deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                days_left = (deadline_date - today).days
                if days_left < 0:
                    semaforo = "red"
                elif days_left <= 7:
                    semaforo = "yellow"
                else:
                    semaforo = "green"
            except (ValueError, TypeError):
                pass

        # Override: phase delays bump to yellow minimum
        if fasi_in_ritardo > 0 and semaforo == "green":
            semaforo = "yellow"

        if c.get("stato") == "sospesa":
            semaforo = "yellow"

        counts[semaforo] += 1
        items.append({
            "commessa_id": c["commessa_id"],
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "stato": c.get("stato", ""),
            "client_name": c.get("client_name", ""),
            "deadline": deadline_str,
            "days_left": days_left,
            "priority": c.get("priority", "media"),
            "value": c.get("value", 0),
            "semaforo": semaforo,
            "prod_done": prod_done,
            "prod_total": prod_total,
            "fasi_in_ritardo": fasi_in_ritardo,
        })

    # Sort: red first, then yellow, then green
    order = {"red": 0, "yellow": 1, "green": 2}
    items.sort(key=lambda x: (order.get(x["semaforo"], 3), x.get("days_left") or 999))

    return {"items": items, "counts": counts, "total": len(items)}


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



# ── CRUSCOTTO FINANZIARIO ARTIGIANO ──────────────────────────────

IVA_QUARTERS = [
    {"q": 1, "label": "Q1 (Gen-Mar)", "months": [1, 2, 3], "f24_scadenza": "16 Maggio"},
    {"q": 2, "label": "Q2 (Apr-Giu)", "months": [4, 5, 6], "f24_scadenza": "20 Agosto"},
    {"q": 3, "label": "Q3 (Lug-Set)", "months": [7, 8, 9], "f24_scadenza": "16 Novembre"},
    {"q": 4, "label": "Q4 (Ott-Dic)", "months": [10, 11, 12], "f24_scadenza": "16 Marzo anno succ."},
]


@router.get("/cruscotto-finanziario")
async def get_cruscotto_finanziario(
    year: int = None,
    user: dict = Depends(get_current_user)
):
    """
    Torre di Controllo Finanziaria — Ciclo Attivo + Passivo integrati.
    Usa campi corretti: imposta (non totale_iva), data_scadenza_pagamento,
    payment_status, data_documento (stringhe ISO).
    """
    from services.financial_service import (
        get_active_invoices_summary, get_passive_invoices_summary,
        get_monthly_cashflow, get_receivables_aging, get_payables_aging,
        get_cashflow_forecast,
    )

    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    year = year or now.year
    today_iso = now.date().isoformat()

    # ─── 1. IVA TRIMESTRALE (ciclo attivo + passivo) ─────────────

    iva_trimestri = []
    for qt in IVA_QUARTERS:
        first_m = qt["months"][0]
        last_m = qt["months"][-1]
        q_start = f"{year}-{first_m:02d}-01"
        q_end = f"{year}-{last_m + 1:02d}-01" if last_m < 12 else f"{year + 1}-01-01"

        attivo = await get_active_invoices_summary(uid, q_start, q_end)
        passivo = await get_passive_invoices_summary(uid, q_start, q_end)

        iva_da_versare = round(attivo["iva"] - passivo["iva"], 2)

        iva_trimestri.append({
            "trimestre": qt["q"],
            "label": qt["label"],
            "f24_scadenza": qt["f24_scadenza"],
            "iva_debito": attivo["iva"],
            "iva_credito": passivo["iva"],
            "iva_da_versare": iva_da_versare,
            "fatturato_attivo": attivo["totale"],
            "fatturato_passivo": passivo["totale"],
            "n_fatture_emesse": attivo["count"],
            "n_fatture_ricevute": passivo["count"],
        })

    # ─── 2. SEMAFORO LIQUIDITÀ (mese corrente — reale) ───────────

    cashflow_mese = await get_monthly_cashflow(uid, now.year, now.month)

    current_q = (now.month - 1) // 3
    iva_prossima = max(iva_trimestri[current_q]["iva_da_versare"], 0) if current_q < len(iva_trimestri) else 0

    entrate = cashflow_mese["incassi"] + cashflow_mese["da_incassare"]
    uscite = cashflow_mese["pagati"] + cashflow_mese["da_pagare"] + iva_prossima
    saldo = round(entrate - uscite, 2)

    if saldo > 0 and entrate > uscite * 1.2:
        semaforo = "verde"
        semaforo_msg = "Liquidità sufficiente per coprire le spese del mese"
    elif saldo >= 0:
        semaforo = "giallo"
        semaforo_msg = "Margine risicato — monitora gli incassi attentamente"
    else:
        semaforo = "rosso"
        semaforo_msg = f"Deficit previsto di {abs(saldo):.2f}€ — intervieni subito"

    liquidita = {
        "incassi_mese": cashflow_mese["incassi"],
        "da_incassare_mese": cashflow_mese["da_incassare"],
        "pagamenti_effettuati": cashflow_mese["pagati"],
        "da_pagare_fornitori": cashflow_mese["da_pagare"],
        "iva_prossima": iva_prossima,
        "entrate_previste": round(entrate, 2),
        "uscite_previste": round(uscite, 2),
        "saldo_operativo": saldo,
        "saldo_reale": cashflow_mese["saldo_reale"],
        "semaforo": semaforo,
        "semaforo_msg": semaforo_msg,
        "n_incassi": cashflow_mese["n_incassi"],
        "n_pagamenti": cashflow_mese["n_pagati"],
    }

    # ─── 3. SCADENZARIO CLIENTI (aging) ──────────────────────────

    receivables = await get_receivables_aging(uid, today_iso)

    # ─── 4. SCADENZARIO FORNITORI (aging) ────────────────────────

    payables = await get_payables_aging(uid, today_iso)

    # ─── 5. CASH FLOW PREVISIONALE (30/60/90 gg) ────────────────

    cashflow_preview = await get_cashflow_forecast(uid, today_iso)

    # ─── 6. FLUSSO DI CASSA REALE (ultimi 6 mesi) ───────────────

    flusso_reale = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        cf = await get_monthly_cashflow(uid, y, m)
        mese_label = datetime(y, m, 1).strftime("%b %Y").capitalize()
        flusso_reale.append({
            "mese": mese_label,
            "entrate": cf["incassi"],
            "uscite": cf["pagati"],
            "saldo": cf["saldo_reale"],
        })

    # ─── 7. MARGINALITÀ PER COMMESSA ────────────────────────────

    commesse_margin = []
    commesse_list = await db.commesse.find(
        {"user_id": uid},
        {"_id": 0, "commessa_id": 1, "title": 1, "value": 1,
         "moduli.preventivo_id": 1, "client_name": 1}
    ).to_list(100)

    for comm in commesse_list:
        ricavo = comm.get("value", 0) or 0
        prev_id = comm.get("moduli", {}).get("preventivo_id")
        costi = 0
        if prev_id:
            rdp = await db.rdp.find_one(
                {"preventivo_id": prev_id, "user_id": uid},
                {"_id": 0, "risposte": 1}
            )
            if rdp and rdp.get("risposte"):
                for risp in rdp["risposte"]:
                    if risp.get("selezionato"):
                        costi += risp.get("prezzo_totale", 0)

        margine = round(ricavo - costi, 2)
        margine_pct = round((margine / ricavo * 100), 1) if ricavo > 0 else 0

        if ricavo > 0 or costi > 0:
            commesse_margin.append({
                "commessa_id": comm["commessa_id"],
                "title": comm.get("title", ""),
                "client_name": comm.get("client_name", ""),
                "ricavo": round(ricavo, 2),
                "costi": round(costi, 2),
                "margine": margine,
                "margine_pct": margine_pct,
            })

    commesse_margin.sort(key=lambda x: x["margine"], reverse=True)
    top_margin = commesse_margin[:5]
    bottom_margin = sorted(commesse_margin, key=lambda x: x["margine"])[:5] if len(commesse_margin) > 5 else []

    # ─── 8. DSO / DPO ────────────────────────────────────────────
    year_start = f"{year}-01-01"
    year_end = f"{year + 1}-01-01"

    # DSO = (Crediti aperti / Fatturato attivo annuale) * 365
    fatturato_attivo_anno = sum(q["fatturato_attivo"] for q in iva_trimestri)
    dso = round((receivables["total"] / fatturato_attivo_anno) * 365, 1) if fatturato_attivo_anno > 0 else 0

    # DPO = (Debiti aperti / Acquisti passivi annuali) * 365
    fatturato_passivo_anno = sum(q["fatturato_passivo"] for q in iva_trimestri)
    dpo = round((payables["total"] / fatturato_passivo_anno) * 365, 1) if fatturato_passivo_anno > 0 else 0

    # ─── 9. FATTURATO PER CLIENTE (top 10) ────────────────────────
    pipeline_client = [
        {"$match": {"user_id": uid, "issue_date": {"$gte": year_start, "$lt": year_end},
                     "status": {"$nin": ["bozza", "annullata"]}}},
        {"$group": {"_id": "$client_id", "totale": {"$sum": "$totals.total_document"}, "n": {"$sum": 1}}},
        {"$sort": {"totale": -1}},
        {"$limit": 10},
    ]
    client_fat = await db.invoices.aggregate(pipeline_client).to_list(10)
    fatturato_per_cliente = []
    for cf in client_fat:
        cl = await db.clients.find_one({"client_id": cf["_id"]}, {"_id": 0, "business_name": 1}) if cf["_id"] else None
        fatturato_per_cliente.append({
            "client_id": cf["_id"] or "",
            "nome": cl.get("business_name", "N/D") if cl else "N/D",
            "totale": round(cf["totale"] or 0, 2),
            "n_fatture": cf["n"],
        })

    # ─── 10. FATTURATO PER TIPOLOGIA COMMESSA ─────────────────────
    pipeline_tipo = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": "$normativa_tipo", "totale": {"$sum": "$value"}, "n": {"$sum": 1}}},
        {"$sort": {"totale": -1}},
    ]
    tipo_fat = await db.commesse.aggregate(pipeline_tipo).to_list(20)
    fatturato_per_tipologia = [
        {"tipologia": t["_id"] or "Non specificata", "totale": round(t["totale"] or 0, 2), "n_commesse": t["n"]}
        for t in tipo_fat
    ]

    return {
        "year": year,
        "iva_trimestri": iva_trimestri,
        "liquidita": liquidita,
        "aging_clienti": receivables["aging"],
        "scadenzario_clienti": receivables["detail"],
        "totale_crediti": receivables["total"],
        "aging_fornitori": payables["aging"],
        "scadenzario_fornitori": payables["detail"],
        "totale_debiti": payables["total"],
        "fornitori_scaduti": payables["scadute"],
        "fornitori_scadenza_mese": payables["scadenza_mese"],
        "cashflow_preview": cashflow_preview,
        "flusso_reale": flusso_reale,
        "top_margin": top_margin,
        "bottom_margin": bottom_margin,
        "iva_annuale": {
            "totale_debito": round(sum(q["iva_debito"] for q in iva_trimestri), 2),
            "totale_credito": round(sum(q["iva_credito"] for q in iva_trimestri), 2),
            "totale_versare": round(sum(q["iva_da_versare"] for q in iva_trimestri), 2),
        },
        "dso": dso,
        "dpo": dpo,
        "fatturato_per_cliente": fatturato_per_cliente,
        "fatturato_per_tipologia": fatturato_per_tipologia,
    }



@router.get("/morning-briefing")
async def morning_briefing(user: dict = Depends(get_current_user)):
    """Morning Briefing: scadenze oggi/domani, pagamenti in ritardo, commesse in allarme, azioni da fare."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # ── Card 1: Scadenze oggi e domani ──
    scadenze_oggi_domani = []

    # Fatture passive (ricevute) con scadenze pagamento
    fatture_passive = await db.fatture_ricevute.find(
        {"user_id": uid, "payment_status": {"$nin": ["pagata"]}},
        {"_id": 0, "fr_id": 1, "fornitore_nome": 1, "numero_documento": 1,
         "scadenze_pagamento": 1, "data_scadenza_pagamento": 1, "totale_documento": 1}
    ).to_list(500)

    for f in fatture_passive:
        scadenze = f.get("scadenze_pagamento") or []
        if scadenze:
            for s in scadenze:
                if s.get("pagata"):
                    continue
                ds = str(s.get("data_scadenza", ""))[:10]
                if ds in (today, tomorrow):
                    scadenze_oggi_domani.append({
                        "tipo": "passiva",
                        "fornitore_cliente": f.get("fornitore_nome", ""),
                        "numero": f.get("numero_documento", ""),
                        "importo": s.get("importo", 0),
                        "data": ds,
                        "is_oggi": ds == today,
                    })
        else:
            ds = str(f.get("data_scadenza_pagamento", ""))[:10]
            if ds in (today, tomorrow):
                scadenze_oggi_domani.append({
                    "tipo": "passiva",
                    "fornitore_cliente": f.get("fornitore_nome", ""),
                    "numero": f.get("numero_documento", ""),
                    "importo": f.get("totale_documento", 0),
                    "data": ds,
                    "is_oggi": ds == today,
                })

    # Fatture attive con scadenze
    fatture_attive = await db.invoices.find(
        {"user_id": uid, "payment_status": {"$nin": ["pagata", "paid"]}},
        {"_id": 0, "invoice_id": 1, "client_name": 1, "document_number": 1,
         "scadenze_pagamento": 1, "totals": 1}
    ).to_list(500)

    for inv in fatture_attive:
        scadenze = inv.get("scadenze_pagamento") or []
        for s in scadenze:
            if s.get("pagata"):
                continue
            ds = str(s.get("data_scadenza", ""))[:10]
            if ds in (today, tomorrow):
                scadenze_oggi_domani.append({
                    "tipo": "attiva",
                    "fornitore_cliente": inv.get("client_name", ""),
                    "numero": inv.get("document_number", ""),
                    "importo": s.get("importo", 0),
                    "data": ds,
                    "is_oggi": ds == today,
                })

    scadenze_oggi_domani.sort(key=lambda x: (0 if x["is_oggi"] else 1, x["data"]))

    # ── Card 2: Pagamenti in ritardo (clienti) ──
    pagamenti_ritardo = []
    for inv in fatture_attive:
        scadenze = inv.get("scadenze_pagamento") or []
        for s in scadenze:
            if s.get("pagata"):
                continue
            ds = str(s.get("data_scadenza", ""))[:10]
            if ds and ds < today:
                try:
                    days_late = (now - datetime.fromisoformat(ds).replace(tzinfo=timezone.utc)).days
                except Exception:
                    days_late = 0
                pagamenti_ritardo.append({
                    "cliente": inv.get("client_name", ""),
                    "numero": inv.get("document_number", ""),
                    "importo": s.get("importo", 0),
                    "data_scadenza": ds,
                    "giorni_ritardo": days_late,
                })

    pagamenti_ritardo.sort(key=lambda x: -x["giorni_ritardo"])

    # ── Card 3: Commesse in allarme (>7gg senza aggiornamenti) ──
    commesse_allarme = []
    seven_days_ago = now - timedelta(days=7)
    commesse_attive = await db.commesse.find(
        {"user_id": uid, "stato": {"$in": ["in_lavorazione", "lavorazione"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1,
         "updated_at": 1, "deadline": 1}
    ).to_list(200)

    for c in commesse_attive:
        updated = c.get("updated_at")
        if isinstance(updated, str):
            try:
                updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except Exception:
                updated = None
        if updated and updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if updated and updated < seven_days_ago:
            days_stale = (now - updated).days
            commesse_allarme.append({
                "commessa_id": c["commessa_id"],
                "numero": c.get("numero", ""),
                "title": c.get("title", ""),
                "client_name": c.get("client_name", ""),
                "giorni_fermo": days_stale,
                "deadline": c.get("deadline"),
            })

    commesse_allarme.sort(key=lambda x: -x["giorni_fermo"])

    # ── Card 4: Da fare oggi ──
    # Preventivi accettati senza commessa
    prev_accettati = await db.preventivi.find(
        {"user_id": uid, "status": "accettato", "hidden_from_planning": {"$ne": True}},
        {"_id": 0, "preventivo_id": 1}
    ).to_list(200)
    prev_ids = [p["preventivo_id"] for p in prev_accettati]
    linked_count = 0
    if prev_ids:
        linked_count = await db.commesse.count_documents({
            "user_id": uid,
            "$or": [
                {"moduli.preventivo_id": {"$in": prev_ids}},
                {"linked_preventivo_id": {"$in": prev_ids}},
            ]
        })
    preventivi_senza_commessa = max(0, len(prev_ids) - linked_count)

    # DDT non fatturati da >30gg
    thirty_days_ago = now - timedelta(days=30)
    ddt_non_fatturati = await db.ddt_documents.count_documents({
        "user_id": uid,
        "status": {"$ne": "fatturato"},
        "created_at": {"$lt": thirty_days_ago},
    })

    # Fatture passive scadute non pagate
    fatture_scadute_count = 0
    for f in fatture_passive:
        scadenze = f.get("scadenze_pagamento") or []
        if scadenze:
            for s in scadenze:
                if not s.get("pagata") and str(s.get("data_scadenza", ""))[:10] < today:
                    fatture_scadute_count += 1
        else:
            ds = str(f.get("data_scadenza_pagamento", ""))[:10]
            if ds and ds < today:
                fatture_scadute_count += 1

    return {
        "scadenze_oggi_domani": scadenze_oggi_domani[:15],
        "totale_scadenze_oggi": sum(1 for s in scadenze_oggi_domani if s["is_oggi"]),
        "totale_scadenze_domani": sum(1 for s in scadenze_oggi_domani if not s["is_oggi"]),
        "pagamenti_ritardo": pagamenti_ritardo[:15],
        "totale_importo_ritardo": round(sum(p["importo"] for p in pagamenti_ritardo), 2),
        "commesse_allarme": commesse_allarme[:10],
        "da_fare": {
            "preventivi_da_convertire": preventivi_senza_commessa,
            "ddt_non_fatturati": ddt_non_fatturati,
            "fatture_scadute": fatture_scadute_count,
        },
    }


# ── Executive Dashboard Multi-Normativa ─────────────────────────
@router.get("/executive")
async def get_executive_dashboard(user: dict = Depends(get_current_user)):
    """Dashboard Executive: vista aggregata multi-normativa (1090 / 13241 / Generico).
    Ogni commessa viene classificata per le normative presenti nelle sue voci_lavoro.
    Una commessa mista appare in piu settori."""
    uid = user["user_id"]
    today = date.today()

    # ── 1. Fetch all active commesse ──
    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$nin": ["chiuso"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1,
         "normativa_tipo": 1, "client_name": 1, "value": 1, "deadline": 1,
         "classe_esecuzione": 1, "fasi_produzione": 1}
    ).sort("created_at", -1).to_list(200)

    cid_list = [c["commessa_id"] for c in commesse]

    # ── 2. Fetch voci_lavoro to detect per-line normativa ──
    voci = await db.voci_lavoro.find(
        {"user_id": uid, "commessa_id": {"$in": cid_list}},
        {"_id": 0, "commessa_id": 1, "normativa_tipo": 1}
    ).to_list(2000)

    # Build map: commessa_id -> set of normative
    norm_map: dict[str, set] = {}
    for v in voci:
        cid = v.get("commessa_id", "")
        nt = v.get("normativa_tipo", "")
        norm_map.setdefault(cid, set())
        if nt:
            norm_map[cid].add(nt)

    # Fallback: use commessa-level normativa_tipo if no voci
    for c in commesse:
        cid = c["commessa_id"]
        if cid not in norm_map or not norm_map[cid]:
            nt = c.get("normativa_tipo", "") or ""
            norm_map[cid] = {nt} if nt else {"GENERICA"}

    # ── 3. Fetch audit data in bulk ──
    riesami = {r["commessa_id"]: r async for r in db.riesami_tecnici.find(
        {"commessa_id": {"$in": cid_list}},
        {"_id": 0, "commessa_id": 1, "approvato": 1, "n_ok": 1, "n_totale": 1}
    )}
    ctrl_finali = {r["commessa_id"]: r async for r in db.controlli_finali.find(
        {"commessa_id": {"$in": cid_list}},
        {"_id": 0, "commessa_id": 1, "approvato": 1}
    )}
    report_isp = {r["commessa_id"]: r async for r in db.report_ispezioni.find(
        {"user_id": uid, "commessa_id": {"$in": cid_list}},
        {"_id": 0, "commessa_id": 1, "approvato": 1}
    )}
    dop_counts: dict[str, int] = {}
    async for d in db.dop_frazionate.find(
        {"commessa_id": {"$in": cid_list}, "user_id": uid},
        {"_id": 0, "commessa_id": 1}
    ):
        dop_counts[d["commessa_id"]] = dop_counts.get(d["commessa_id"], 0) + 1

    # ── 4. Build per-commessa cards ──
    def build_card(c):
        cid = c["commessa_id"]
        normative = sorted(norm_map.get(cid, set()))
        is_mista = len(normative) > 1

        # Production progress
        fasi = c.get("fasi_produzione", [])
        prod_done = sum(1 for f in fasi if f.get("stato") == "completato")
        prod_total = len(fasi) if fasi else 0

        # Deadline
        deadline = c.get("deadline")
        days_left = None
        if deadline:
            try:
                dl = datetime.strptime(deadline, "%Y-%m-%d").date()
                days_left = (dl - today).days
            except (ValueError, TypeError):
                pass

        # Audit status (only for normed commesse)
        has_norma = any(n in normative for n in ["EN_1090", "EN_13241"])
        ries = riesami.get(cid, {})
        ctrl = ctrl_finali.get(cid, {})
        risp = report_isp.get(cid, {})

        audit = None
        if has_norma:
            audit = {
                "riesame_ok": bool(ries.get("approvato")),
                "riesame_pct": round(ries["n_ok"] / ries["n_totale"] * 100) if ries.get("n_totale") else 0,
                "ispezioni_ok": bool(risp.get("approvato")),
                "controllo_ok": bool(ctrl.get("approvato")),
                "dop_count": dop_counts.get(cid, 0),
            }

        return {
            "commessa_id": cid,
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "stato": c.get("stato", ""),
            "client_name": c.get("client_name", ""),
            "value": c.get("value", 0),
            "deadline": deadline,
            "days_left": days_left,
            "normative_presenti": normative,
            "mista": is_mista,
            "classe_esecuzione": c.get("classe_esecuzione", ""),
            "prod_done": prod_done,
            "prod_total": prod_total,
            "audit": audit,
        }

    cards = [build_card(c) for c in commesse]

    # ── 5. Classify into sectors ──
    settori = {
        "EN_1090": {"label": "EN 1090 — Strutture", "commesse": [], "stats": {}},
        "EN_13241": {"label": "EN 13241 — Chiusure", "commesse": [], "stats": {}},
        "GENERICA": {"label": "Generica — Senza Marcatura", "commesse": [], "stats": {}},
    }

    for card in cards:
        placed = False
        for nt in card["normative_presenti"]:
            key = nt if nt in settori else "GENERICA"
            settori[key]["commesse"].append(card)
            placed = True
        if not placed:
            settori["GENERICA"]["commesse"].append(card)

    # ── 6. Per-sector stats ──
    for key, s in settori.items():
        cc = s["commesse"]
        s["stats"] = {
            "totale_commesse": len(cc),
            "valore_totale": sum(c.get("value", 0) or 0 for c in cc),
            "in_ritardo": sum(1 for c in cc if c.get("days_left") is not None and c["days_left"] < 0),
            "in_produzione": sum(1 for c in cc if c["stato"] in ("produzione", "in_corso")),
        }
        if key != "GENERICA":
            audited = [c for c in cc if c.get("audit")]
            s["stats"]["audit_ready"] = sum(1 for c in audited
                                            if c["audit"]["riesame_ok"] and c["audit"]["ispezioni_ok"]
                                            and c["audit"]["controllo_ok"])
            s["stats"]["riesame_approvati"] = sum(1 for c in audited if c["audit"]["riesame_ok"])
            s["stats"]["dop_generate"] = sum(1 for c in audited if c["audit"]["dop_count"] > 0)
            total_pct = sum(c["audit"]["riesame_pct"] for c in audited)
            s["stats"]["indice_rischio"] = round(100 - (total_pct / len(audited))) if audited else 0
        else:
            # Efficienza produttiva per generiche
            prod_cc = [c for c in cc if c["prod_total"] > 0]
            total_done = sum(c["prod_done"] for c in prod_cc)
            total_phases = sum(c["prod_total"] for c in prod_cc)
            s["stats"]["efficienza_produttiva"] = round(total_done / total_phases * 100) if total_phases else 0

    # ── 7. Scadenze aggregate ──
    scadenze = []

    # Instruments
    async for inst in db.instruments.find({}, {"_id": 0, "name": 1, "next_calibration_date": 1}):
        nc = inst.get("next_calibration_date", "")
        if nc:
            try:
                delta = (date.fromisoformat(nc[:10]) - today).days
                if delta <= 30:
                    scadenze.append({"tipo": "taratura", "nome": inst["name"],
                                     "scadenza": nc, "giorni": delta,
                                     "settore": "EN_1090"})
            except (ValueError, TypeError):
                pass

    # Welders
    async for w in db.welders.find({"user_id": uid}, {"_id": 0, "name": 1, "qualifications": 1}):
        for q in w.get("qualifications", []):
            exp = q.get("expiry_date", "")
            if exp:
                try:
                    delta = (date.fromisoformat(exp[:10]) - today).days
                    if delta <= 30:
                        scadenze.append({"tipo": "patentino", "nome": f"{w['name']} — {q.get('process', '')}",
                                         "scadenza": exp, "giorni": delta,
                                         "settore": "EN_1090"})
                except (ValueError, TypeError):
                    pass

    # ITT
    async for itt in db.verbali_itt.find({"user_id": uid}, {"_id": 0, "processo": 1, "data_scadenza": 1}):
        ds = itt.get("data_scadenza", "")
        if ds:
            try:
                delta = (date.fromisoformat(ds[:10]) - today).days
                if delta <= 30:
                    proc = itt.get("processo", "").replace("_", " ").title()
                    scadenze.append({"tipo": "itt", "nome": f"ITT {proc}",
                                     "scadenza": ds, "giorni": delta,
                                     "settore": "EN_1090"})
            except (ValueError, TypeError):
                pass

    scadenze.sort(key=lambda x: x.get("giorni", 999))

    # ── 8. CAM Safety Gate — aggregate recycled content across active commesse ──
    cam_safety = {"level": "info", "message": "Nessun dato CAM", "commesse": []}
    try:
        all_batches = await db.material_batches.find(
            {"commessa_id": {"$in": cid_list}, "user_id": uid, "percentuale_riciclato": {"$ne": None}},
            {"_id": 0, "commessa_id": 1, "peso_kg": 1, "percentuale_riciclato": 1, "metodo_produttivo": 1}
        ).to_list(1000)

        if all_batches:
            peso_tot = sum(b.get("peso_kg", 0) or 0 for b in all_batches)
            peso_ric = sum((b.get("peso_kg", 0) or 0) * (b.get("percentuale_riciclato", 0) or 0) / 100 for b in all_batches)
            perc_glob = round(peso_ric / peso_tot * 100, 1) if peso_tot > 0 else 0
            soglia = 75

            # Per-commessa breakdown
            cam_per_com = {}
            for b in all_batches:
                cid_b = b["commessa_id"]
                if cid_b not in cam_per_com:
                    cam_per_com[cid_b] = {"peso": 0, "peso_ric": 0}
                cam_per_com[cid_b]["peso"] += b.get("peso_kg", 0) or 0
                cam_per_com[cid_b]["peso_ric"] += (b.get("peso_kg", 0) or 0) * (b.get("percentuale_riciclato", 0) or 0) / 100

            cam_commesse = []
            for cid_b, v in cam_per_com.items():
                perc_c = round(v["peso_ric"] / v["peso"] * 100, 1) if v["peso"] > 0 else 0
                # Find commessa numero
                numero = next((c["numero"] for c in commesse if c["commessa_id"] == cid_b), cid_b)
                cam_commesse.append({
                    "commessa_id": cid_b, "numero": numero,
                    "percentuale_riciclato": perc_c,
                    "peso_kg": round(v["peso"], 1),
                    "conforme": perc_c >= soglia,
                })

            n_non_conf = sum(1 for c in cam_commesse if not c["conforme"])
            level = "success" if n_non_conf == 0 else "danger"
            cam_safety = {
                "level": level,
                "percentuale_globale": perc_glob,
                "soglia": soglia,
                "peso_totale_kg": round(peso_tot, 1),
                "n_commesse_cam": len(cam_commesse),
                "n_non_conformi": n_non_conf,
                "message": f"CAM {'OK' if n_non_conf == 0 else 'ATTENZIONE'}: {perc_glob:.1f}% riciclato globale — {n_non_conf} commesse non conformi" if n_non_conf else f"CAM CONFORME: {perc_glob:.1f}% riciclato globale",
                "commesse": sorted(cam_commesse, key=lambda x: x["percentuale_riciclato"]),
            }
    except Exception as e:
        logger.warning(f"CAM Safety Gate error: {e}")

    return {
        "settori": settori,
        "scadenze_imminenti": scadenze,
        "totale_commesse": len(commesse),
        "totale_valore": sum((c.get("value") or 0) for c in commesse),
        "cam_safety_gate": cam_safety,
    }

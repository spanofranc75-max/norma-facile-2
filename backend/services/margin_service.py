"""
Margin Analysis Service — Aggregatore completo dei costi commessa.

Fonti di costo:
1. costi_reali (manuali sulla commessa)
2. Fatture ricevute imputate alla commessa
3. DDT conto lavoro (verniciatura, zincatura, ecc.)
4. Ore lavorate × costo orario pieno

Fonti di ricavo:
1. commessa.value (valore del preventivo)
2. Fatture emesse collegate alla commessa
"""
from core.database import db
import logging

logger = logging.getLogger(__name__)


async def get_costo_orario(uid: str) -> float:
    """Fetch company's full hourly cost."""
    cc = await db.company_costs.find_one({"user_id": uid}, {"_id": 0, "costo_orario_pieno": 1})
    return float(cc.get("costo_orario_pieno", 0)) if cc else 0


async def get_commessa_margin_full(commessa_id: str, uid: str) -> dict:
    """Full margin analysis for a single commessa, aggregating ALL cost sources."""

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1,
         "value": 1, "costi_reali": 1, "ore_lavorate": 1, "stato": 1,
         "data_consegna": 1, "created_at": 1}
    )
    if not commessa:
        return None

    costo_orario = await get_costo_orario(uid)
    valore = float(commessa.get("value", 0) or 0)
    ore = float(commessa.get("ore_lavorate", 0) or 0)

    # 1. Costi manuali (costi_reali)
    costi_manuali = commessa.get("costi_reali", [])
    materiali_manuali = sum(float(x.get("importo", 0) or 0) for x in costi_manuali)
    by_tipo = {}
    for c in costi_manuali:
        t = c.get("tipo", "materiali")
        by_tipo[t] = by_tipo.get(t, 0) + float(c.get("importo", 0) or 0)

    # 2. Fatture ricevute imputate alla commessa
    fatture_imputate = 0
    fr_detail = []
    async for fr in db.fatture_ricevute.find(
        {"user_id": uid, "imputazione.target_id": commessa_id},
        {"_id": 0, "fr_id": 1, "fornitore_nome": 1, "totale_documento": 1,
         "numero_documento": 1, "imputazione": 1}
    ):
        imp = fr.get("imputazione", {})
        if imp.get("target_id") == commessa_id:
            importo = float(fr.get("totale_documento", 0) or 0)
            fatture_imputate += importo
            fr_detail.append({
                "fr_id": fr.get("fr_id"),
                "fornitore": fr.get("fornitore_nome", ""),
                "numero": fr.get("numero_documento", ""),
                "importo": round(importo, 2),
            })
        elif imp.get("destinazione") == "multi":
            for r in imp.get("righe", []):
                if r.get("target_type") == "commessa" and r.get("target_id") == commessa_id:
                    importo = float(fr.get("totale_documento", 0) or 0)
                    fatture_imputate += importo
                    fr_detail.append({
                        "fr_id": fr.get("fr_id"),
                        "fornitore": fr.get("fornitore_nome", ""),
                        "numero": fr.get("numero_documento", ""),
                        "importo": round(importo, 2),
                    })
                    break

    # 3. DDT conto lavoro + OdA costs from approvvigionamento
    costo_esterni = 0
    costo_oda = 0
    cl_detail = []
    oda_detail = []
    comm_full = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid},
        {"_id": 0, "conto_lavoro": 1, "approvvigionamento": 1}
    )
    if comm_full:
        for item in comm_full.get("conto_lavoro", []):
            importo = float(item.get("costo_totale", 0) or 0)
            costo_esterni += importo
            cl_detail.append({
                "tipo": item.get("tipo_lavorazione", ""),
                "fornitore": item.get("fornitore_nome", ""),
                "importo": round(importo, 2),
            })
        # OdA (ordini di acquisto) from approvvigionamento
        approv = comm_full.get("approvvigionamento", {})
        for oda in approv.get("ordini", []):
            importo = float(oda.get("importo_totale", 0) or 0)
            if importo > 0:
                costo_oda += importo
                oda_detail.append({
                    "ordine_id": oda.get("ordine_id", ""),
                    "fornitore": oda.get("fornitore_nome", ""),
                    "importo": round(importo, 2),
                    "stato": oda.get("stato", ""),
                })

    # 4. Fatture emesse collegate
    fatturato = 0
    async for inv in db.invoices.find(
        {"user_id": uid, "commessa_id": commessa_id,
         "status": {"$in": ["emessa", "inviata_sdi", "accettata", "pagata"]}},
        {"_id": 0, "totals.total_document": 1}
    ):
        fatturato += float(inv.get("totals", {}).get("total_document", 0) or 0)

    # Calcoli
    costo_personale = round(ore * costo_orario, 2)
    costo_materiali_totale = round(materiali_manuali + fatture_imputate, 2)
    costo_totale = round(costo_materiali_totale + costo_personale + costo_esterni + costo_oda, 2)
    ricavo = max(valore, fatturato)
    margine = round(ricavo - costo_totale, 2)
    margine_pct = round((margine / ricavo * 100) if ricavo > 0 else 0, 1)

    if margine_pct < 0:
        alert = "rosso"
    elif margine_pct < 10:
        alert = "arancione"
    elif margine_pct < 20:
        alert = "giallo"
    else:
        alert = "verde"

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "title": commessa.get("title", ""),
        "client_name": commessa.get("client_name", ""),
        "stato": commessa.get("stato", ""),
        "data_consegna": commessa.get("data_consegna"),
        # Ricavi
        "valore_preventivo": round(valore, 2),
        "fatturato": round(fatturato, 2),
        "ricavo": round(ricavo, 2),
        # Costi
        "costi_materiali_manuali": round(materiali_manuali, 2),
        "costi_fatture_imputate": round(fatture_imputate, 2),
        "costi_esterni": round(costo_esterni, 2),
        "costi_oda": round(costo_oda, 2),
        "costo_materiali_totale": costo_materiali_totale,
        "costo_personale": costo_personale,
        "ore_lavorate": ore,
        "costo_orario": costo_orario,
        "costo_totale": costo_totale,
        # Margine
        "margine": margine,
        "margine_pct": margine_pct,
        "alert": alert,
        # Dettagli
        "costi_per_tipo": {k: round(v, 2) for k, v in by_tipo.items()},
        "fatture_imputate_detail": fr_detail,
        "conto_lavoro_detail": cl_detail,
        "oda_detail": oda_detail,
        "num_voci_manuali": len(costi_manuali),
    }


async def get_all_margins(uid: str) -> dict:
    """Full margin analysis for ALL commesse (not just ones with costs)."""
    costo_orario = await get_costo_orario(uid)

    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$nin": ["bozza"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1,
         "value": 1, "costi_reali": 1, "ore_lavorate": 1, "stato": 1,
         "approvvigionamento.ordini.importo_totale": 1,
         "conto_lavoro.costo_totale": 1}
    ).sort("numero", -1).to_list(300)

    # Pre-fetch fatture imputate per commessa
    fr_by_commessa = {}
    async for fr in db.fatture_ricevute.find(
        {"user_id": uid, "imputazione": {"$exists": True}},
        {"_id": 0, "totale_documento": 1, "imputazione": 1}
    ):
        imp = fr.get("imputazione", {})
        tid = imp.get("target_id")
        if tid and imp.get("target_type", "commessa") == "commessa":
            fr_by_commessa[tid] = fr_by_commessa.get(tid, 0) + float(fr.get("totale_documento", 0) or 0)
        elif imp.get("destinazione") == "multi":
            for r in imp.get("righe", []):
                if r.get("target_type") == "commessa" and r.get("target_id"):
                    rtid = r["target_id"]
                    fr_by_commessa[rtid] = fr_by_commessa.get(rtid, 0) + float(fr.get("totale_documento", 0) or 0)

    results = []
    totale_ricavi = 0
    totale_costi = 0

    for c in commesse:
        cid = c["commessa_id"]
        valore = float(c.get("value", 0) or 0)
        ore = float(c.get("ore_lavorate", 0) or 0)
        costi_manuali = sum(float(x.get("importo", 0) or 0) for x in c.get("costi_reali", []))
        costi_fr = fr_by_commessa.get(cid, 0)
        # OdA costs from approvvigionamento
        costi_oda = sum(float(o.get("importo_totale", 0) or 0) for o in c.get("approvvigionamento", {}).get("ordini", []))
        # Conto lavoro costs
        costi_cl = sum(float(cl.get("costo_totale", 0) or 0) for cl in c.get("conto_lavoro", []))

        costo_personale = round(ore * costo_orario, 2)
        costo_totale = round(costi_manuali + costi_fr + costi_oda + costi_cl + costo_personale, 2)
        margine = round(valore - costo_totale, 2)
        margine_pct = round((margine / valore * 100) if valore > 0 else 0, 1)

        if margine_pct < 0:
            alert = "rosso"
        elif margine_pct < 10:
            alert = "arancione"
        elif margine_pct < 20:
            alert = "giallo"
        else:
            alert = "verde"

        totale_ricavi += valore
        totale_costi += costo_totale

        results.append({
            "commessa_id": cid,
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "client_name": c.get("client_name", ""),
            "stato": c.get("stato", ""),
            "valore": round(valore, 2),
            "costi_materiali": round(costi_manuali + costi_fr + costi_oda + costi_cl, 2),
            "costo_personale": costo_personale,
            "ore": ore,
            "costo_totale": costo_totale,
            "margine": margine,
            "margine_pct": margine_pct,
            "alert": alert,
        })

    margine_medio = round(
        sum(r["margine_pct"] for r in results if r["valore"] > 0) /
        max(len([r for r in results if r["valore"] > 0]), 1), 1
    )

    return {
        "commesse": results,
        "total": len(results),
        "costo_orario": costo_orario,
        "totale_ricavi": round(totale_ricavi, 2),
        "totale_costi": round(totale_costi, 2),
        "margine_totale": round(totale_ricavi - totale_costi, 2),
        "margine_medio_pct": margine_medio,
    }


async def predict_margin(commessa_id: str, uid: str) -> dict:
    """AI-style margin prediction based on historical commesse data.
    Compares the current commessa against completed ones to predict final margin."""

    current = await get_commessa_margin_full(commessa_id, uid)
    if not current:
        return None

    # Get completed commesse with costs for comparison
    completed = await db.commesse.find(
        {"user_id": uid, "stato": {"$in": ["chiuso", "fatturato", "completato"]},
         "value": {"$gt": 0}},
        {"_id": 0, "commessa_id": 1, "value": 1, "costi_reali": 1,
         "ore_lavorate": 1, "numero": 1, "title": 1}
    ).to_list(100)

    if not completed:
        return {
            **current,
            "prediction": None,
            "prediction_msg": "Dati storici insufficienti. Completa almeno 3 commesse per attivare la previsione.",
        }

    costo_orario = await get_costo_orario(uid)

    # Calculate historical margins
    historical = []
    for c in completed:
        val = float(c.get("value", 0) or 0)
        if val <= 0:
            continue
        costi = sum(float(x.get("importo", 0) or 0) for x in c.get("costi_reali", []))
        ore = float(c.get("ore_lavorate", 0) or 0)
        costo_tot = costi + (ore * costo_orario)
        m_pct = round((val - costo_tot) / val * 100, 1) if val > 0 else 0
        historical.append({
            "numero": c.get("numero"),
            "value": val,
            "costo": round(costo_tot, 2),
            "margine_pct": m_pct,
            "ore_per_euro": round(ore / val * 1000, 2) if val > 0 else 0,
            "costi_pct": round(costi / val * 100, 1) if val > 0 else 0,
        })

    if len(historical) < 2:
        return {
            **current,
            "prediction": None,
            "prediction_msg": "Dati storici insufficienti. Servono almeno 2 commesse completate.",
        }

    # Statistical analysis
    avg_margin = sum(h["margine_pct"] for h in historical) / len(historical)
    avg_ore_per_k = sum(h["ore_per_euro"] for h in historical) / len(historical)
    avg_costi_pct = sum(h["costi_pct"] for h in historical) / len(historical)

    # Predict based on current progress
    valore = current["ricavo"]
    ore_stimate = round(avg_ore_per_k * valore / 1000, 1) if valore > 0 else 0
    costi_mat_stimati = round(valore * avg_costi_pct / 100, 2)

    costo_pers_stimato = round(ore_stimate * costo_orario, 2)
    costo_tot_stimato = round(costi_mat_stimati + costo_pers_stimato, 2)
    margine_stimato = round(valore - costo_tot_stimato, 2)
    margine_stimato_pct = round((margine_stimato / valore * 100) if valore > 0 else 0, 1)

    # Compare actual progress vs prediction
    progress_costi = round(current["costo_totale"] / costo_tot_stimato * 100, 1) if costo_tot_stimato > 0 else 0
    progress_ore = round(current["ore_lavorate"] / ore_stimate * 100, 1) if ore_stimate > 0 else 0

    # Risk assessment
    if current["costo_totale"] > costo_tot_stimato * 0.9 and current["ore_lavorate"] < ore_stimate * 0.7:
        risk = "alto"
        risk_msg = f"Attenzione: hai già speso il {progress_costi:.0f}% del budget stimato con solo {progress_ore:.0f}% delle ore. Rischio sforamento."
    elif current["margine_pct"] < avg_margin - 10:
        risk = "medio"
        risk_msg = f"Margine attuale ({current['margine_pct']}%) sotto la media storica ({avg_margin:.1f}%). Monitora i costi."
    else:
        risk = "basso"
        risk_msg = f"Andamento in linea con le commesse storiche (media margine: {avg_margin:.1f}%)."

    return {
        **current,
        "prediction": {
            "margine_stimato": margine_stimato,
            "margine_stimato_pct": margine_stimato_pct,
            "ore_stimate": ore_stimate,
            "costi_mat_stimati": costi_mat_stimati,
            "costo_pers_stimato": costo_pers_stimato,
            "costo_tot_stimato": costo_tot_stimato,
            "progress_costi_pct": progress_costi,
            "progress_ore_pct": progress_ore,
            "avg_margin_storico": round(avg_margin, 1),
            "num_commesse_confronto": len(historical),
            "risk": risk,
            "risk_msg": risk_msg,
        },
    }

"""
KPI Dashboard — Confidence Score & Analytics.

GET /api/kpi/accuracy-score          — Score globale accuratezza AI
GET /api/kpi/commesse-confronto      — Confronto preventivo vs consuntivo per commessa
GET /api/kpi/trend-accuracy          — Trend accuratezza nel tempo
GET /api/kpi/marginalita             — Marginalita reale per commessa
GET /api/kpi/ritardi-fornitori       — Ritardi C/L per fornitore
GET /api/kpi/tempi-medi              — Tempi medi lavorazione per tipologia
GET /api/kpi/overview                — Dashboard overview (tutti i KPI in una chiamata)
"""
import logging
from datetime import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends

from core.database import db
from core.security import get_current_user
from core.rbac import require_role

router = APIRouter(prefix="/kpi", tags=["kpi"])
logger = logging.getLogger(__name__)


async def _get_uid(user: dict) -> str:
    return user.get("team_owner_id", user["user_id"]) if user.get("role") != "admin" else user["user_id"]


@router.get("/accuracy-score")
async def accuracy_score(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """
    Calcola l'Accuracy Score globale del sistema predittivo.
    Confronta ore/costi preventivati vs reali su commesse chiuse.
    """
    uid = await _get_uid(user)

    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$in": ["chiuso", "fatturato", "consegnato"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1,
         "ore_preventivate": 1, "importo_totale": 1, "value": 1,
         "budget": 1, "predittivo": 1, "created_at": 1}
    ).to_list(500)

    confronti = []
    tot_accuracy_ore = 0
    tot_accuracy_costi = 0
    n_with_ore = 0
    n_with_costi = 0

    for c in commesse:
        cid = c.get("commessa_id")
        ore_prev = c.get("ore_preventivate", 0) or 0

        # Ore reali dal diario
        entries = await db.diario_produzione.find(
            {"commessa_id": cid}, {"_id": 0, "ore_totali": 1}
        ).to_list(1000)
        ore_reali = sum(e.get("ore_totali", 0) for e in entries)

        # Costi reali da fatture acquisto collegate
        fatture = await db.invoices.find(
            {"user_id": uid, "riferimento_commessa": cid, "document_type": "fattura_acquisto"},
            {"_id": 0, "totals": 1}
        ).to_list(100)
        costo_reale = sum((f.get("totals") or {}).get("subtotal", 0) for f in fatture)

        budget = c.get("budget", {})
        costo_prev = budget.get("materiali", 0) if budget else 0
        importo = c.get("importo_totale") or c.get("value", 0)

        # Accuracy ore
        accuracy_ore = None
        if ore_prev > 0 and ore_reali > 0:
            scostamento = abs(ore_reali - ore_prev) / ore_prev
            accuracy_ore = round(max(0, (1 - scostamento)) * 100, 1)
            tot_accuracy_ore += accuracy_ore
            n_with_ore += 1

        # Accuracy costi
        accuracy_costi = None
        if costo_prev > 0 and costo_reale > 0:
            scostamento = abs(costo_reale - costo_prev) / costo_prev
            accuracy_costi = round(max(0, (1 - scostamento)) * 100, 1)
            tot_accuracy_costi += accuracy_costi
            n_with_costi += 1

        # Marginalita reale
        marginalita = None
        if importo > 0 and (ore_reali > 0 or costo_reale > 0):
            costo_totale_reale = costo_reale
            # Add labor cost (use company hourly rate)
            cost_doc = await db.company_costs.find_one({"user_id": uid}, {"_id": 0})
            costo_orario = (cost_doc or {}).get("costo_orario_pieno", 35)
            costo_totale_reale += ore_reali * costo_orario
            marginalita = round((importo - costo_totale_reale) / importo * 100, 1) if importo > 0 else 0

        confronti.append({
            "commessa_id": cid,
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "ore_preventivate": ore_prev,
            "ore_reali": round(ore_reali, 1),
            "accuracy_ore": accuracy_ore,
            "costo_preventivato": costo_prev,
            "costo_reale": round(costo_reale, 2),
            "accuracy_costi": accuracy_costi,
            "importo": importo,
            "marginalita_pct": marginalita,
            "is_predittivo": c.get("predittivo", False) or bool(budget),
        })

    # Score globale
    score_ore = round(tot_accuracy_ore / n_with_ore, 1) if n_with_ore > 0 else None
    score_costi = round(tot_accuracy_costi / n_with_costi, 1) if n_with_costi > 0 else None

    if score_ore is not None and score_costi is not None:
        score_globale = round(score_ore * 0.6 + score_costi * 0.4, 1)
    elif score_ore is not None:
        score_globale = score_ore
    elif score_costi is not None:
        score_costi
        score_globale = score_costi
    else:
        score_globale = None

    # Top scostamenti (worst accuracy)
    sorted_by_accuracy = sorted(
        [c for c in confronti if c.get("accuracy_ore") is not None],
        key=lambda x: x["accuracy_ore"]
    )
    top_scostamenti = sorted_by_accuracy[:3]

    return {
        "score_globale": score_globale,
        "score_ore": score_ore,
        "score_costi": score_costi,
        "commesse_analizzate": len(confronti),
        "commesse_con_dati_ore": n_with_ore,
        "commesse_con_dati_costi": n_with_costi,
        "top_scostamenti": top_scostamenti,
        "confronti": confronti,
    }


@router.get("/trend-accuracy")
async def trend_accuracy(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Trend dell'accuratezza nel tempo (per mese)."""
    uid = await _get_uid(user)

    commesse = await db.commesse.find(
        {"user_id": uid, "stato": {"$in": ["chiuso", "fatturato", "consegnato"]}},
        {"_id": 0, "commessa_id": 1, "ore_preventivate": 1, "created_at": 1}
    ).sort("created_at", 1).to_list(500)

    monthly = defaultdict(lambda: {"ore_prev_sum": 0, "ore_real_sum": 0, "count": 0})

    for c in commesse:
        cid = c.get("commessa_id")
        ore_prev = c.get("ore_preventivate", 0) or 0
        if ore_prev <= 0:
            continue

        entries = await db.diario_produzione.find(
            {"commessa_id": cid}, {"_id": 0, "ore_totali": 1}
        ).to_list(1000)
        ore_reali = sum(e.get("ore_totali", 0) for e in entries)
        if ore_reali <= 0:
            continue

        created = c.get("created_at")
        if isinstance(created, str):
            month_key = created[:7]
        elif isinstance(created, datetime):
            month_key = created.strftime("%Y-%m")
        else:
            continue

        monthly[month_key]["ore_prev_sum"] += ore_prev
        monthly[month_key]["ore_real_sum"] += ore_reali
        monthly[month_key]["count"] += 1

    trend = []
    for month, data in sorted(monthly.items()):
        if data["ore_prev_sum"] > 0:
            scostamento = abs(data["ore_real_sum"] - data["ore_prev_sum"]) / data["ore_prev_sum"]
            accuracy = round(max(0, (1 - scostamento)) * 100, 1)
        else:
            accuracy = 0
        trend.append({
            "mese": month,
            "accuracy": accuracy,
            "commesse": data["count"],
        })

    return {"trend": trend}


@router.get("/marginalita")
async def marginalita(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Marginalita reale per commessa."""
    uid = await _get_uid(user)
    cost_doc = await db.company_costs.find_one({"user_id": uid}, {"_id": 0})
    costo_orario = (cost_doc or {}).get("costo_orario_pieno", 35)

    commesse = await db.commesse.find(
        {"user_id": uid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1,
         "importo_totale": 1, "value": 1, "status": 1, "stato": 1}
    ).sort("created_at", -1).limit(50).to_list(50)

    result = []
    for c in commesse:
        cid = c.get("commessa_id")
        importo = c.get("importo_totale") or c.get("value", 0) or 0

        # Ore reali
        entries = await db.diario_produzione.find(
            {"commessa_id": cid}, {"_id": 0, "ore_totali": 1}
        ).to_list(1000)
        ore_reali = sum(e.get("ore_totali", 0) for e in entries)
        costo_mano = round(ore_reali * costo_orario, 2)

        # Costi materiali
        fatture = await db.invoices.find(
            {"user_id": uid, "riferimento_commessa": cid, "document_type": "fattura_acquisto"},
            {"_id": 0, "totals": 1}
        ).to_list(100)
        costo_mat = sum((f.get("totals") or {}).get("subtotal", 0) for f in fatture)

        costo_totale = round(costo_mano + costo_mat, 2)
        margine = round(importo - costo_totale, 2) if importo > 0 else 0
        margine_pct = round(margine / importo * 100, 1) if importo > 0 else 0

        result.append({
            "commessa_id": cid,
            "numero": c.get("numero", ""),
            "title": c.get("title", ""),
            "stato": c.get("stato", c.get("status", "")),
            "importo": importo,
            "costo_manodopera": costo_mano,
            "costo_materiali": costo_mat,
            "costo_totale": costo_totale,
            "margine": margine,
            "margine_pct": margine_pct,
            "ore_lavorate": round(ore_reali, 1),
        })

    return {"commesse": result}


@router.get("/ritardi-fornitori")
async def ritardi_fornitori(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Analisi ritardi conto lavoro per fornitore."""
    uid = await _get_uid(user)

    all_ops = await db.commesse_ops.find(
        {"user_id": uid, "conto_lavoro": {"$exists": True, "$ne": []}},
        {"_id": 0, "commessa_id": 1, "conto_lavoro": 1}
    ).to_list(200)

    fornitori_stats = defaultdict(lambda: {
        "totali": 0, "rientrati": 0, "in_corso": 0,
        "giorni_medi": 0, "giorni_list": [], "tipi": set()
    })

    for ops in all_ops:
        for cl in (ops.get("conto_lavoro") or []):
            fornitore = cl.get("fornitore_nome", "Sconosciuto")
            fornitori_stats[fornitore]["totali"] += 1
            fornitori_stats[fornitore]["tipi"].add(cl.get("tipo", "altro"))

            if cl.get("stato") in ("rientrato", "verificato"):
                fornitori_stats[fornitore]["rientrati"] += 1
                if cl.get("data_invio") and cl.get("data_rientro"):
                    try:
                        d_inv = datetime.fromisoformat(cl["data_invio"].replace("Z", "+00:00"))
                        d_rien = datetime.fromisoformat(cl["data_rientro"].replace("Z", "+00:00"))
                        giorni = (d_rien - d_inv).days
                        fornitori_stats[fornitore]["giorni_list"].append(giorni)
                    except (ValueError, TypeError):
                        pass
            else:
                fornitori_stats[fornitore]["in_corso"] += 1

    result = []
    for nome, stats in sorted(fornitori_stats.items(), key=lambda x: -x[1]["totali"]):
        giorni_list = stats["giorni_list"]
        media_giorni = round(sum(giorni_list) / len(giorni_list), 1) if giorni_list else None
        result.append({
            "fornitore": nome,
            "totali": stats["totali"],
            "rientrati": stats["rientrati"],
            "in_corso": stats["in_corso"],
            "giorni_medi": media_giorni,
            "tipi": list(stats["tipi"]),
        })

    return {"fornitori": result}


@router.get("/tempi-medi")
async def tempi_medi(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Tempi medi lavorazione per tipologia struttura (h/ton)."""
    uid = await _get_uid(user)

    commesse = await db.commesse.find(
        {"user_id": uid, "peso_totale_kg": {"$gt": 0}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "peso_totale_kg": 1,
         "normativa_tipo": 1, "classe_exc": 1}
    ).to_list(500)

    tipologie = defaultdict(lambda: {"ore": 0, "peso_kg": 0, "count": 0, "commesse": []})

    for c in commesse:
        cid = c.get("commessa_id")
        peso = c.get("peso_totale_kg", 0)
        if peso <= 0:
            continue

        entries = await db.diario_produzione.find(
            {"commessa_id": cid}, {"_id": 0, "ore_totali": 1}
        ).to_list(1000)
        ore = sum(e.get("ore_totali", 0) for e in entries)
        if ore <= 0:
            continue

        # Determine tipologia from weight/class
        classe = c.get("classe_exc", "EXC2")
        if classe in ("EXC3", "EXC4"):
            tip = "complessa"
        elif peso < 2000:
            tip = "leggera"
        elif peso < 10000:
            tip = "media"
        else:
            tip = "complessa"

        tipologie[tip]["ore"] += ore
        tipologie[tip]["peso_kg"] += peso
        tipologie[tip]["count"] += 1
        tipologie[tip]["commesse"].append({
            "numero": c.get("numero", ""),
            "peso_kg": peso,
            "ore": round(ore, 1),
            "ore_per_ton": round(ore / (peso / 1000), 1),
        })

    result = {}
    for tip, data in tipologie.items():
        if data["peso_kg"] > 0:
            result[tip] = {
                "ore_per_ton": round(data["ore"] / (data["peso_kg"] / 1000), 1),
                "commesse_count": data["count"],
                "ore_totali": round(data["ore"], 1),
                "peso_totale_kg": round(data["peso_kg"], 1),
                "dettaglio": data["commesse"][:10],
            }

    return {"tipologie": result}


@router.get("/overview")
async def kpi_overview(user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Overview rapida di tutti i KPI principali."""
    uid = await _get_uid(user)

    # Counts
    n_commesse = await db.commesse.count_documents({"user_id": uid})
    n_chiuse = await db.commesse.count_documents({"user_id": uid, "stato": {"$in": ["chiuso", "fatturato", "consegnato"]}})
    n_preventivi = await db.preventivi.count_documents({"user_id": uid})
    n_predittivi = await db.preventivi.count_documents({"user_id": uid, "predittivo": True})
    n_fatture = await db.invoices.count_documents({"user_id": uid, "document_type": {"$ne": "fattura_acquisto"}})

    # Total revenue
    fatture = await db.invoices.find(
        {"user_id": uid, "document_type": {"$ne": "fattura_acquisto"}},
        {"_id": 0, "totals.total_document": 1}
    ).to_list(1000)
    fatturato = sum((f.get("totals") or {}).get("total_document", 0) for f in fatture)

    # Active C/L
    ops_with_cl = await db.commesse_ops.find(
        {"user_id": uid, "conto_lavoro": {"$exists": True}},
        {"_id": 0, "conto_lavoro": 1}
    ).to_list(200)
    cl_attivi = 0
    cl_totali = 0
    for ops in ops_with_cl:
        for cl in (ops.get("conto_lavoro") or []):
            cl_totali += 1
            if cl.get("stato") not in ("rientrato", "verificato"):
                cl_attivi += 1

    return {
        "commesse_totali": n_commesse,
        "commesse_chiuse": n_chiuse,
        "preventivi_totali": n_preventivi,
        "preventivi_predittivi": n_predittivi,
        "fatture_emesse": n_fatture,
        "fatturato_totale": round(fatturato, 2),
        "cl_attivi": cl_attivi,
        "cl_totali": cl_totali,
    }

"""
Servizio ML di Calibrazione per il Preventivatore Predittivo.

Analizza i progetti completati per calcolare fattori correttivi
basati su peso, classe antisismica, nodi strutturali e tipologia.
Applica regressione pesata per migliorare le stime future.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _safe_ratio(actual: float, estimated: float) -> float:
    """Calcola il rapporto reale/stimato evitando divisioni per zero."""
    if not estimated or estimated == 0:
        return 1.0
    return actual / estimated


def _similarity_score(proj: dict, target: dict) -> float:
    """
    Calcola un punteggio di similarita (0-1) tra un progetto storico e il target.
    Piu il progetto e' simile, piu pesa nella calibrazione.
    """
    score = 0.0
    total_weight = 0.0

    # Peso (50% della similarita)
    w_peso = 0.50
    p_peso = proj.get('peso_kg', 0)
    t_peso = target.get('peso_kg', 0)
    if t_peso > 0 and p_peso > 0:
        ratio = min(p_peso, t_peso) / max(p_peso, t_peso)
        score += w_peso * ratio
    total_weight += w_peso

    # Classe antisismica (25%)
    w_classe = 0.25
    p_classe = proj.get('classe_antisismica', 0)
    t_classe = target.get('classe_antisismica', 0)
    if p_classe == t_classe:
        score += w_classe * 1.0
    elif abs(p_classe - t_classe) == 1:
        score += w_classe * 0.5
    total_weight += w_classe

    # Nodi strutturali (15%)
    w_nodi = 0.15
    p_nodi = proj.get('nodi_strutturali', 0)
    t_nodi = target.get('nodi_strutturali', 0)
    if t_nodi > 0 and p_nodi > 0:
        ratio = min(p_nodi, t_nodi) / max(p_nodi, t_nodi)
        score += w_nodi * ratio
    elif p_nodi == 0 and t_nodi == 0:
        score += w_nodi * 1.0
    total_weight += w_nodi

    # Tipologia (10%)
    w_tipo = 0.10
    if proj.get('tipologia') == target.get('tipologia'):
        score += w_tipo * 1.0
    total_weight += w_tipo

    return score / total_weight if total_weight > 0 else 0.0


async def calcola_calibrazione(db, user_id: str, target: Optional[dict] = None) -> dict:
    """
    Calcola i fattori correttivi basati sui progetti completati.
    Se target e' specificato, usa regressione pesata per similarita.
    """
    projects = await db.progetti_completati.find(
        {"user_id": user_id, "status": "completato"},
        {"_id": 0}
    ).to_list(100)

    if len(projects) < 3:
        return {
            "calibrato": False,
            "motivo": f"Servono almeno 3 progetti completati (trovati: {len(projects)})",
            "fattori": _fattori_default(),
            "n_progetti": len(projects),
            "accuracy": None,
        }

    # Calculate correction factors with weighted regression
    fattori_ore = []
    fattori_mat = []
    fattori_mano = []
    fattori_cl = []
    weights = []

    for p in projects:
        w = _similarity_score(p, target) if target else 1.0
        if w < 0.1:
            continue

        weights.append(w)
        fattori_ore.append(_safe_ratio(p.get('ore_reali', 0), p.get('ore_stimate', 0)))
        fattori_mat.append(_safe_ratio(p.get('costo_materiali_reale', 0), p.get('costo_materiali_stimato', 0)))
        fattori_mano.append(_safe_ratio(p.get('costo_manodopera_reale', 0), p.get('costo_manodopera_stimato', 0)))
        fattori_cl.append(_safe_ratio(p.get('costo_cl_reale', 0), p.get('costo_cl_reale', 0)))

    if not weights:
        return {
            "calibrato": False,
            "motivo": "Nessun progetto simile trovato",
            "fattori": _fattori_default(),
            "n_progetti": 0,
            "accuracy": None,
        }

    # Weighted averages
    total_w = sum(weights)
    f_ore = sum(f * w for f, w in zip(fattori_ore, weights)) / total_w
    f_mat = sum(f * w for f, w in zip(fattori_mat, weights)) / total_w
    f_mano = sum(f * w for f, w in zip(fattori_mano, weights)) / total_w
    f_cl = sum(f * w for f, w in zip(fattori_cl, weights)) / total_w

    # Calculate accuracy metrics
    errori_pct = []
    for p in projects:
        if p.get('ore_stimate') and p.get('ore_reali'):
            ore_corretto = p['ore_stimate'] * f_ore
            errore = abs(ore_corretto - p['ore_reali']) / p['ore_reali'] * 100
            errori_pct.append(errore)

    accuracy = round(100 - (sum(errori_pct) / len(errori_pct)), 1) if errori_pct else None

    # Clamp factors to reasonable range [0.5, 2.0]
    def clamp(v):
        return round(max(0.5, min(2.0, v)), 4)

    fattori = {
        "ore": clamp(f_ore),
        "materiali": clamp(f_mat),
        "manodopera": clamp(f_mano),
        "conto_lavoro": clamp(f_cl),
    }

    # Store calibration result
    await db.calibrazione_ml.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "fattori": fattori,
            "n_progetti": len(weights),
            "accuracy": accuracy,
            "target_usato": target is not None,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )

    return {
        "calibrato": True,
        "fattori": fattori,
        "n_progetti": len(weights),
        "accuracy": accuracy,
        "progetti_usati": len(weights),
        "similarita_media": round(sum(weights) / len(weights), 3) if weights else 0,
    }


async def applica_calibrazione(db, user_id: str, stima: dict, target_params: dict) -> dict:
    """
    Applica i fattori di calibrazione a una stima grezza.
    Returns stima calibrata con delta rispetto alla stima originale.
    """
    cal = await calcola_calibrazione(db, user_id, target_params)

    if not cal["calibrato"]:
        return {
            "calibrata": False,
            "motivo": cal["motivo"],
            "stima_originale": stima,
            "stima_calibrata": stima,
            "fattori": cal["fattori"],
        }

    f = cal["fattori"]

    ore_orig = stima.get("ore_totali", 0)
    mat_orig = stima.get("costo_materiali", 0)
    mano_orig = stima.get("costo_manodopera", 0)
    cl_orig = stima.get("costo_cl", 0)

    ore_cal = round(ore_orig * f["ore"], 1)
    mat_cal = round(mat_orig * f["materiali"], 2)
    mano_cal = round(mano_orig * f["manodopera"], 2)
    cl_cal = round(cl_orig * f["conto_lavoro"], 2)

    return {
        "calibrata": True,
        "stima_originale": {
            "ore_totali": ore_orig,
            "costo_materiali": mat_orig,
            "costo_manodopera": mano_orig,
            "costo_cl": cl_orig,
            "totale": round(mat_orig + mano_orig + cl_orig, 2),
        },
        "stima_calibrata": {
            "ore_totali": ore_cal,
            "costo_materiali": mat_cal,
            "costo_manodopera": mano_cal,
            "costo_cl": cl_cal,
            "totale": round(mat_cal + mano_cal + cl_cal, 2),
        },
        "delta": {
            "ore": round(ore_cal - ore_orig, 1),
            "materiali": round(mat_cal - mat_orig, 2),
            "manodopera": round(mano_cal - mano_orig, 2),
            "conto_lavoro": round(cl_cal - cl_orig, 2),
        },
        "fattori": f,
        "n_progetti": cal["n_progetti"],
        "accuracy": cal["accuracy"],
    }


async def registra_progetto_completato(db, user_id: str, data: dict) -> dict:
    """
    Registra un nuovo progetto completato per il training.
    Ricalcola i fattori di calibrazione.
    """
    project_id = f"hist_proj_{data.get('commessa_id', 'unknown')}"

    await db.progetti_completati.update_one(
        {"project_id": project_id},
        {"$set": {
            "project_id": project_id,
            "user_id": user_id,
            "commessa_id": data.get("commessa_id"),
            "title": data.get("title", ""),
            "peso_kg": data.get("peso_kg", 0),
            "classe_antisismica": data.get("classe_antisismica", 0),
            "nodi_strutturali": data.get("nodi_strutturali", 0),
            "tipologia": data.get("tipologia", "media"),
            "ore_stimate": data.get("ore_stimate", 0),
            "ore_reali": data.get("ore_reali", 0),
            "costo_materiali_stimato": data.get("costo_materiali_stimato", 0),
            "costo_materiali_reale": data.get("costo_materiali_reale", 0),
            "costo_manodopera_stimato": data.get("costo_manodopera_stimato", 0),
            "costo_manodopera_reale": data.get("costo_manodopera_reale", 0),
            "costo_cl_stimato": data.get("costo_cl_stimato", 0),
            "costo_cl_reale": data.get("costo_cl_reale", 0),
            "status": "completato",
            "completato_il": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )

    # Recalculate calibration
    cal = await calcola_calibrazione(db, user_id)

    return {
        "message": f"Progetto '{data.get('title', project_id)}' registrato",
        "project_id": project_id,
        "calibrazione_aggiornata": cal["calibrato"],
        "n_progetti_totali": cal["n_progetti"],
        "nuova_accuracy": cal["accuracy"],
    }


async def get_training_stats(db, user_id: str) -> dict:
    """Restituisce statistiche sul dataset di training e performance del modello."""
    projects = await db.progetti_completati.find(
        {"user_id": user_id, "status": "completato"},
        {"_id": 0}
    ).to_list(200)

    if not projects:
        return {
            "n_progetti": 0,
            "calibrato": False,
            "messaggio": "Nessun progetto completato per il training",
        }

    # Aggregate by tipologia
    by_tipo = {}
    for p in projects:
        tipo = p.get("tipologia", "sconosciuta")
        if tipo not in by_tipo:
            by_tipo[tipo] = {"count": 0, "errore_medio_ore": []}
        by_tipo[tipo]["count"] += 1
        if p.get("ore_stimate") and p.get("ore_reali"):
            err = abs(p["ore_stimate"] - p["ore_reali"]) / p["ore_reali"] * 100
            by_tipo[tipo]["errore_medio_ore"].append(err)

    for t in by_tipo:
        errs = by_tipo[t]["errore_medio_ore"]
        by_tipo[t]["errore_medio_ore"] = round(sum(errs) / len(errs), 1) if errs else 0

    # Overall accuracy before calibration
    errori_pre = []
    for p in projects:
        if p.get("ore_stimate") and p.get("ore_reali"):
            err = abs(p["ore_stimate"] - p["ore_reali"]) / p["ore_reali"] * 100
            errori_pre.append(err)

    accuracy_pre = round(100 - (sum(errori_pre) / len(errori_pre)), 1) if errori_pre else 0

    # Get calibrated accuracy
    cal = await calcola_calibrazione(db, user_id)

    # Build evolution data (projects over time)
    projects_sorted = sorted(projects, key=lambda p: str(p.get("completato_il", "")))
    evoluzione = []
    running_errors_pre = []
    running_errors_post = []
    f = cal["fattori"]

    for i, p in enumerate(projects_sorted):
        if p.get("ore_stimate") and p.get("ore_reali"):
            err_pre = abs(p["ore_stimate"] - p["ore_reali"]) / p["ore_reali"] * 100
            ore_cal = p["ore_stimate"] * f.get("ore", 1.0)
            err_post = abs(ore_cal - p["ore_reali"]) / p["ore_reali"] * 100
            running_errors_pre.append(err_pre)
            running_errors_post.append(err_post)
            evoluzione.append({
                "progetto": p.get("title", "")[:30],
                "accuracy_pre": round(100 - (sum(running_errors_pre) / len(running_errors_pre)), 1),
                "accuracy_post": round(100 - (sum(running_errors_post) / len(running_errors_post)), 1),
                "n": i + 1,
            })

    return {
        "n_progetti": len(projects),
        "calibrato": cal["calibrato"],
        "fattori": cal["fattori"],
        "accuracy_pre_calibrazione": accuracy_pre,
        "accuracy_post_calibrazione": cal.get("accuracy", accuracy_pre),
        "miglioramento_pct": round((cal.get("accuracy", accuracy_pre) - accuracy_pre), 1),
        "distribuzione_tipologia": by_tipo,
        "evoluzione": evoluzione,
    }


def _fattori_default() -> dict:
    return {"ore": 1.0, "materiali": 1.0, "manodopera": 1.0, "conto_lavoro": 1.0}

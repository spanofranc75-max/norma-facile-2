"""
Scadenziario Manutenzioni Unificato — Aggrega instruments + attrezzature
in un'unica timeline con indicatori di impatto sui moduli collegati.

Fili conduttori:
  - instruments → Riesame Tecnico (check strumenti_tarati) + Controllo Finale (dim_strumenti_tarati)
  - attrezzature saldatrici → Riesame Tecnico (check attrezzature_idonee)
  - attrezzature chiavi_dinam → Diario Montaggio (check taratura)
"""
from datetime import date
from fastapi import APIRouter, Depends
from core.security import get_current_user
from core.database import db

router = APIRouter(prefix="/scadenziario-manutenzioni", tags=["manutenzioni"])


def _urgenza(next_date_str: str | None) -> tuple[str, int | None]:
    if not next_date_str:
        return "sconosciuto", None
    try:
        exp = date.fromisoformat(next_date_str[:10])
        delta = (exp - date.today()).days
        if delta < 0:
            return "scaduto", delta
        if delta <= 30:
            return "in_scadenza", delta
        if delta <= 90:
            return "prossimo", delta
        return "ok", delta
    except (ValueError, TypeError):
        return "sconosciuto", None


def _impatto_strumento() -> list[str]:
    return ["Riesame Tecnico (strumenti_tarati)", "Controllo Finale (dim_strumenti_tarati)"]


def _impatto_attrezzatura(tipo: str) -> list[str]:
    if tipo == "saldatrice":
        return ["Riesame Tecnico (attrezzature_idonee)"]
    if tipo == "chiave_dinamometrica":
        return ["Riesame Tecnico (attrezzature_idonee)", "Diario Montaggio (serraggio)"]
    return ["Riesame Tecnico (attrezzature_idonee)"]


URGENZA_ORD = {"scaduto": 0, "in_scadenza": 1, "prossimo": 2, "ok": 3, "sconosciuto": 4}


@router.get("")
async def get_scadenziario(user: dict = Depends(get_current_user)):
    uid = user["user_id"]

    items: list[dict] = []

    # --- Instruments (no user_id filter — same pattern as instruments.py) ---
    instruments_raw = await db.instruments.find({}, {"_id": 0}).to_list(500)
    seen_ids = set()
    for inst in instruments_raw:
        iid = inst.get("instrument_id", "")
        if iid in seen_ids:
            continue
        seen_ids.add(iid)
        next_cal = inst.get("next_calibration_date", "")
        urgenza, giorni = _urgenza(next_cal)
        items.append({
            "id": inst["instrument_id"],
            "fonte": "strumento",
            "nome": inst.get("name", ""),
            "modello": inst.get("manufacturer", ""),
            "serial": inst.get("serial_number", ""),
            "tipo_dettaglio": inst.get("type", "misura"),
            "ultima_manutenzione": inst.get("last_calibration_date", ""),
            "prossima_scadenza": next_cal,
            "intervallo_mesi": inst.get("calibration_interval_months", 12),
            "urgenza": urgenza,
            "giorni_rimasti": giorni,
            "impatto": _impatto_strumento(),
            "soglia": inst.get("soglia_accettabilita"),
            "unita_soglia": inst.get("unita_soglia", "mm"),
        })

    # --- Attrezzature ---
    attrezzature = await db.attrezzature.find(
        {"user_id": uid}, {"_id": 0}
    ).to_list(500)
    for attr in attrezzature:
        next_tar = attr.get("prossima_taratura", "")
        urgenza, giorni = _urgenza(next_tar)
        items.append({
            "id": attr["attr_id"],
            "fonte": "attrezzatura",
            "nome": attr.get("modello", ""),
            "modello": attr.get("marca", ""),
            "serial": attr.get("numero_serie", ""),
            "tipo_dettaglio": attr.get("tipo", "altro"),
            "ultima_manutenzione": attr.get("data_taratura", ""),
            "prossima_scadenza": next_tar,
            "intervallo_mesi": None,
            "urgenza": urgenza,
            "giorni_rimasti": giorni,
            "impatto": _impatto_attrezzatura(attr.get("tipo", "altro")),
            "soglia": None,
            "unita_soglia": None,
        })

    # --- Verbali ITT (qualifica processi) ---
    itt_docs = await db.verbali_itt.find(
        {"user_id": uid}, {"_id": 0}
    ).to_list(200)
    for itt in itt_docs:
        next_scad = itt.get("data_scadenza", "")
        urgenza, giorni = _urgenza(next_scad)
        proc_label = (itt.get("processo", "")).replace("_", " ").title()
        items.append({
            "id": itt.get("itt_id", ""),
            "fonte": "itt",
            "nome": f"ITT {proc_label}",
            "modello": itt.get("macchina", ""),
            "serial": itt.get("materiale", ""),
            "tipo_dettaglio": itt.get("processo", ""),
            "ultima_manutenzione": itt.get("data_prova", ""),
            "prossima_scadenza": next_scad,
            "intervallo_mesi": None,
            "urgenza": urgenza,
            "giorni_rimasti": giorni,
            "impatto": ["Riesame Tecnico (itt_processi_qualificati)"],
            "soglia": None,
            "unita_soglia": None,
        })

    # Sort: scaduti first, then in_scadenza, etc.
    items.sort(key=lambda x: (URGENZA_ORD.get(x["urgenza"], 9), x.get("giorni_rimasti") or 9999))

    # KPI
    scaduti = sum(1 for i in items if i["urgenza"] == "scaduto")
    in_scadenza = sum(1 for i in items if i["urgenza"] == "in_scadenza")
    prossimi = sum(1 for i in items if i["urgenza"] == "prossimo")
    ok_count = sum(1 for i in items if i["urgenza"] == "ok")

    # Blocchi attivi: check if any scaduto/in_scadenza impacts Riesame
    blocchi_riesame = [i for i in items if i["urgenza"] == "scaduto"
                       and any("Riesame" in imp for imp in i["impatto"])]

    return {
        "items": items,
        "kpi": {
            "totale": len(items),
            "scaduti": scaduti,
            "in_scadenza": in_scadenza,
            "prossimi_90gg": prossimi,
            "conformi": ok_count,
        },
        "blocchi_riesame": len(blocchi_riesame),
        "alert_msg": (
            f"{len(blocchi_riesame)} strumenti/attrezzature scaduti bloccano il Riesame Tecnico"
            if blocchi_riesame else None
        ),
    }

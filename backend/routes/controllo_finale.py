"""
Controllo Finale — Checklist pre-spedizione EN 1090-2:2024.
3 macro-aree: Visual Testing (ISO 5817 Livello C), Dimensionale (B6/B8), Compliance (CE/DOP/colate).

GET  /api/controllo-finale/{commessa_id}         — Stato checklist con auto-check
POST /api/controllo-finale/{commessa_id}         — Salva risultati manuali
POST /api/controllo-finale/{commessa_id}/approva — Firma e chiudi controllo
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.database import db
from core.security import get_current_user, tenant_match
from routes.report_ispezioni import VT_CHECKS

router = APIRouter(prefix="/controllo-finale", tags=["controllo-finale"])
logger = logging.getLogger(__name__)

CHECKLIST_DEFINITION = [
    # === VISUAL TESTING ===
    {
        "id": "vt_100_eseguito",
        "area": "Visual Testing",
        "label": "Controllo Visivo 100% eseguito",
        "desc": "VT al 100% su tutte le saldature conforme ISO 5817 Livello C",
        "auto": False,
    },
    {
        "id": "vt_difetti_accettabili",
        "area": "Visual Testing",
        "label": "Difetti entro i limiti ISO 5817-C",
        "desc": "Nessun difetto critico (cricche, inclusioni passanti, mancanza di fusione)",
        "auto": False,
    },
    {
        "id": "vt_saldature_registro",
        "area": "Visual Testing",
        "label": "Tutte le saldature registrate nel Registro Saldatura",
        "desc": "Ogni giunto ha un record con saldatore, WPS e data",
        "auto": True,
    },
    {
        "id": "vt_nc_chiuse",
        "area": "Visual Testing",
        "label": "Report Ispezioni VT approvato",
        "desc": "Rapporto VT con checklist ISO 5817-C firmato e chiuso",
        "auto": True,
    },
    # === DIMENSIONALE ===
    {
        "id": "dim_quote_critiche",
        "area": "Dimensionale",
        "label": "Quote critiche verificate (B6/B8 EN 1090-2:2024)",
        "desc": "Lunghezze, interassi, rettilineita entro le tolleranze prescritte",
        "auto": False,
    },
    {
        "id": "dim_tolleranze_montaggio",
        "area": "Dimensionale",
        "label": "Tolleranze di montaggio rispettate",
        "desc": "Controllo posizioni fori, piastre, squadratura complessiva",
        "auto": False,
    },
    {
        "id": "dim_strumenti_tarati",
        "area": "Dimensionale",
        "label": "Strumenti di misura in taratura valida",
        "desc": "Tutti gli strumenti utilizzati per i controlli risultano tarati",
        "auto": True,
    },
    # === COMPLIANCE ===
    {
        "id": "comp_etichetta_ce",
        "area": "Compliance",
        "label": "Etichetta CE fisica applicata",
        "desc": "Etichetta CE marcata sul prodotto con numero organismo notificato",
        "auto": False,
    },
    {
        "id": "comp_dop_presente",
        "area": "Compliance",
        "label": "Dichiarazione di Prestazione (DOP) compilata",
        "desc": "DOP conforme al Regolamento UE 305/2011 con riferimento EN 1090-1",
        "auto": True,
    },
    {
        "id": "comp_colate_coerenti",
        "area": "Compliance",
        "label": "Numeri di colata coerenti con certificati 3.1",
        "desc": "Ogni colata sul prodotto e rintracciabile al certificato di origine",
        "auto": True,
    },
    {
        "id": "comp_fascicolo_completo",
        "area": "Compliance",
        "label": "Fascicolo Tecnico completo e allegato",
        "desc": "Tutti i documenti richiesti dalla norma sono presenti nel fascicolo",
        "auto": True,
    },
]


async def _run_auto_checks(commessa_id: str, user_id: str) -> dict:
    """Esegue le verifiche automatiche per il controllo finale."""
    results = {}

    # VT: Saldature registrate
    righe_saldatura = await db.registro_saldatura.find(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    ).to_list(500)
    n_registrate = len(righe_saldatura)
    n_conformi = sum(1 for r in righe_saldatura if r.get("esito_vt") == "conforme")
    n_non_conformi = sum(1 for r in righe_saldatura if r.get("esito_vt") == "non_conforme")
    n_da_eseguire = sum(1 for r in righe_saldatura if r.get("esito_vt") == "da_eseguire")
    results["vt_saldature_registro"] = {
        "ok": n_registrate > 0 and n_da_eseguire == 0,
        "valore": f"{n_registrate} giunti ({n_conformi} conformi, {n_non_conformi} NC, {n_da_eseguire} da eseguire)",
        "nota": "Tutti i giunti controllati" if n_da_eseguire == 0 and n_registrate > 0
                else f"{n_da_eseguire} giunti ancora da controllare" if n_da_eseguire > 0
                else "Nessun giunto registrato nel Registro Saldatura",
    }

    # VT: Report Ispezioni VT approvato
    report_isp = await db.report_ispezioni.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    vt_results = {r["check_id"]: r for r in (report_isp or {}).get("ispezioni_vt", [])}
    n_vt_compiled = sum(1 for r in vt_results.values() if r.get("esito") is not None)
    n_vt_ok = sum(1 for r in vt_results.values() if r.get("esito") is True)
    results["vt_nc_chiuse"] = {
        "ok": bool(report_isp) and report_isp.get("approvato", False),
        "valore": f"Report {'approvato' if report_isp and report_isp.get('approvato') else f'{n_vt_compiled}/{len(VT_CHECKS)} compilati' if report_isp else 'non creato'}",
        "nota": "Report Ispezioni VT firmato e approvato" if report_isp and report_isp.get("approvato")
                else f"{n_vt_ok} VT conformi su {n_vt_compiled} compilati" if report_isp
                else "Compilare il Report Ispezioni VT dalla sezione dedicata",
    }

    # DIM: Strumenti tarati
    from datetime import date
    instruments = await db.instruments.find(
        {"user_id": user_id, "type": "misura"}, {"_id": 0}
    ).to_list(100)
    today = date.today()
    scaduti = []
    for inst in instruments:
        nc_date = inst.get("next_calibration_date", "")
        if nc_date:
            try:
                if date.fromisoformat(str(nc_date)[:10]) < today:
                    scaduti.append(inst.get("name", "?"))
            except (ValueError, TypeError):
                pass
    results["dim_strumenti_tarati"] = {
        "ok": len(scaduti) == 0 and len(instruments) > 0,
        "valore": f"{len(instruments)} strumenti misura, {len(scaduti)} scaduti",
        "nota": f"Scaduti: {', '.join(scaduti[:3])}" if scaduti
                else "Tutti gli strumenti in taratura valida" if instruments
                else "Nessuno strumento di misura registrato",
    }

    # COMP: DOP presente
    dop = await db.dop_frazionata.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0, "status": 1}
    )
    gate_cert = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "dop_generated": 1}
    )
    has_dop = bool(dop) or bool(gate_cert and gate_cert.get("dop_generated"))
    results["comp_dop_presente"] = {
        "ok": has_dop,
        "valore": "DOP presente" if has_dop else "DOP non trovata",
        "nota": "Dichiarazione di Prestazione compilata" if has_dop else "Generare la DOP dalla sezione Certificazioni",
    }

    # COMP: Colate coerenti (check material_batches have heat numbers)
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "heat_number": 1, "numero_colata": 1, "batch_id": 1}
    ).to_list(200)
    senza_colata = [b for b in batches if not (b.get("heat_number") or b.get("numero_colata"))]
    results["comp_colate_coerenti"] = {
        "ok": len(batches) > 0 and len(senza_colata) == 0,
        "valore": f"{len(batches)} lotti, {len(senza_colata)} senza colata",
        "nota": f"{len(senza_colata)} lotti senza numero di colata" if senza_colata
                else "Tutte le colate tracciate" if batches
                else "Nessun lotto materiale registrato",
    }

    # COMP: Fascicolo completo (check key documents exist)
    fascicolo = await db.fascicolo_tecnico.find_one(
        {"commessa_id": commessa_id}, {"_id": 0}
    )
    results["comp_fascicolo_completo"] = {
        "ok": bool(fascicolo),
        "valore": "Presente" if fascicolo else "Non trovato",
        "nota": "Fascicolo tecnico compilato" if fascicolo else "Creare il fascicolo tecnico dalla sezione dedicata",
    }

    return results


class ControlloFinaleNote(BaseModel):
    checks_manuali: dict = Field(default_factory=dict)
    note_generali: str = ""
    note_vt: str = ""
    note_dim: str = ""


class ControlloFinaleApprova(BaseModel):
    firma_nome: str
    firma_ruolo: str = "Responsabile Qualita"
    note_approvazione: str = ""


@router.get("/{commessa_id}")
async def get_controllo_finale(commessa_id: str, user: dict = Depends(get_current_user)):
    """Stato della checklist controllo finale con verifiche automatiche."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    auto_results = await _run_auto_checks(commessa_id, user["user_id"])

    saved = await db.controlli_finali.find_one(
        {"commessa_id": commessa_id}, {"_id": 0}
    )

    checks = []
    for ck in CHECKLIST_DEFINITION:
        cid = ck["id"]
        auto_res = auto_results.get(cid, {})
        manual_override = (saved or {}).get("checks_manuali", {}).get(cid)

        if ck["auto"]:
            esito = auto_res.get("ok", False)
            valore = auto_res.get("valore", "")
            nota = auto_res.get("nota", "")
        else:
            esito = manual_override if manual_override is not None else False
            valore = "Confermato" if esito else "Da verificare"
            nota = ""

        checks.append({
            "id": cid,
            "area": ck["area"],
            "label": ck["label"],
            "desc": ck["desc"],
            "auto": ck["auto"],
            "esito": esito,
            "valore": valore,
            "nota": nota,
        })

    superato = all(c["esito"] for c in checks)
    n_ok = sum(1 for c in checks if c["esito"])

    # Stats per area
    areas = {}
    for c in checks:
        a = c["area"]
        if a not in areas:
            areas[a] = {"totale": 0, "ok": 0}
        areas[a]["totale"] += 1
        if c["esito"]:
            areas[a]["ok"] += 1

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "checks": checks,
        "superato": superato,
        "n_ok": n_ok,
        "n_totale": len(checks),
        "areas": areas,
        "approvato": (saved or {}).get("approvato", False),
        "data_approvazione": (saved or {}).get("data_approvazione"),
        "firma": (saved or {}).get("firma"),
        "note_generali": (saved or {}).get("note_generali", ""),
        "note_vt": (saved or {}).get("note_vt", ""),
        "note_dim": (saved or {}).get("note_dim", ""),
        "controllo_id": (saved or {}).get("controllo_id"),
    }


@router.post("/{commessa_id}")
async def save_controllo_finale(commessa_id: str, data: ControlloFinaleNote, user: dict = Depends(get_current_user)):
    """Salva i check manuali e le note."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.controlli_finali.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if saved and saved.get("approvato"):
        raise HTTPException(409, "Controllo finale gia approvato — non modificabile")

    controllo_id = (saved or {}).get("controllo_id") or f"cf_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "controllo_id": controllo_id,
        "commessa_id": commessa_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "checks_manuali": data.checks_manuali,
        "note_generali": data.note_generali,
        "note_vt": data.note_vt,
        "note_dim": data.note_dim,
        "approvato": False,
        "updated_at": now,
    }

    await db.controlli_finali.update_one(
        {"commessa_id": commessa_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"message": "Controllo finale salvato", "controllo_id": controllo_id}


@router.post("/{commessa_id}/approva")
async def approva_controllo_finale(commessa_id: str, data: ControlloFinaleApprova, user: dict = Depends(get_current_user)):
    """Firma e approva il controllo finale. Immutabile dopo approvazione."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.controlli_finali.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if saved and saved.get("approvato"):
        raise HTTPException(409, "Controllo finale gia approvato")

    # Verify all checks pass
    auto_results = await _run_auto_checks(commessa_id, user["user_id"])
    manual_checks = (saved or {}).get("checks_manuali", {})

    for ck in CHECKLIST_DEFINITION:
        cid = ck["id"]
        if ck["auto"]:
            if not auto_results.get(cid, {}).get("ok", False):
                raise HTTPException(400, f"Check '{ck['label']}' non superato. Risolvere prima di approvare.")
        else:
            if not manual_checks.get(cid):
                raise HTTPException(400, f"Check manuale '{ck['label']}' non confermato.")

    now = datetime.now(timezone.utc).isoformat()
    controllo_id = (saved or {}).get("controllo_id") or f"cf_{uuid.uuid4().hex[:12]}"

    await db.controlli_finali.update_one(
        {"commessa_id": commessa_id},
        {"$set": {
            "controllo_id": controllo_id,
            "commessa_id": commessa_id,
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "approvato": True,
            "data_approvazione": now,
            "firma": {
                "nome": data.firma_nome,
                "ruolo": data.firma_ruolo,
                "timestamp": now,
            },
            "note_approvazione": data.note_approvazione,
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    return {
        "message": "Controllo finale approvato e firmato",
        "controllo_id": controllo_id,
        "data_approvazione": now,
    }

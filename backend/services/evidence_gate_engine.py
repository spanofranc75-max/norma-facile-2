"""
Evidence Gate Engine — Fase B1
================================
Motore di valutazione completo per singola emissione documentale.

Livelli di controllo:
  A. Prerequisiti di ramo
  B. Copertura dell'emissione (scope)
  C. Evidenze obbligatorie per normativa (EN 1090, EN 13241, GENERICA)

Output standardizzato:
  - checks[]: lista completa di cio che e stato valutato
  - blockers[]: cio che impedisce emissione
  - warnings[]: anomalie non bloccanti
  - completion_percent: solo su check required (esclusi not_applicable)
  - emittable: bool
"""

import logging
from datetime import datetime, timezone

from core.database import db

logger = logging.getLogger(__name__)

# ─── Evidence States ─────────────────────────────────────────────
# required, not_applicable, missing, linked, uploaded, verified, failed
PASSING_STATES = ("linked", "uploaded", "verified")


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

async def evaluate_gate(emissione: dict, ramo: dict, commessa: dict) -> dict:
    """Valuta l'Evidence Gate per una singola emissione.

    Returns standardized gate result:
    {
        emissione_id, normativa, stato_gate, emittable,
        completion_percent, blockers[], warnings[], checks[],
        updated_at
    }
    """
    normativa = ramo.get("normativa", emissione.get("branch_type", ""))
    checks = []
    blockers = []
    warnings = []

    # A. Common checks
    await _check_common(emissione, ramo, checks, blockers, warnings)

    # C. Normative-specific checks
    if normativa == "EN_1090":
        await _check_en1090(emissione, ramo, commessa, checks, blockers, warnings)
    elif normativa == "EN_13241":
        await _check_en13241(emissione, ramo, commessa, checks, blockers, warnings)
    elif normativa == "GENERICA":
        _check_generica(emissione, ramo, checks, blockers, warnings)

    # Calculate completion_percent (only required checks, exclude not_applicable)
    required_checks = [c for c in checks if c["required"]]
    satisfied = [c for c in required_checks if c["status"] in PASSING_STATES]
    completion = round(len(satisfied) / len(required_checks) * 100) if required_checks else 100

    emittable = len(blockers) == 0
    now = datetime.now(timezone.utc).isoformat()

    # Determine emission state
    stato_gate = _compute_stato(emissione, emittable, blockers)

    return {
        "emissione_id": emissione.get("emissione_id"),
        "codice": emissione.get("codice_emissione"),
        "normativa": normativa,
        "stato_gate": stato_gate,
        "emittable": emittable,
        "completion_percent": completion,
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "updated_at": now,
    }


def _compute_stato(emissione: dict, emittable: bool, blockers: list) -> str:
    """Determina lo stato dell'emissione basato sul gate."""
    current = emissione.get("stato", "draft")
    if current in ("emessa", "annullata"):
        return current
    if emittable:
        return "emettibile"
    if blockers:
        return "bloccata"
    return "in_preparazione"


def _add_check(checks: list, code: str, status: str, required: bool, message: str = ""):
    checks.append({"code": code, "status": status, "required": required, "message": message})


def _add_blocker(blockers: list, code: str, message: str):
    blockers.append({"code": code, "message": message})


def _add_warning(warnings: list, code: str, message: str):
    warnings.append({"code": code, "message": message})


# ═══════════════════════════════════════════════════════════════════
#  A. COMMON CHECKS (tutte le normative)
# ═══════════════════════════════════════════════════════════════════

async def _check_common(emissione: dict, ramo: dict, checks: list, blockers: list, warnings: list):
    """Blocchi comuni a tutte le normative."""

    # B-COM-01 — Scope emissione definito
    scope_fields = ["line_ids", "voce_lavoro_ids", "element_ids", "batch_ids", "ddt_ids"]
    has_scope = any(len(emissione.get(f, [])) > 0 for f in scope_fields)

    if has_scope:
        _add_check(checks, "EMISSION_SCOPE", "verified", True, "Scope emissione definito")
    else:
        _add_check(checks, "EMISSION_SCOPE", "missing", True, "Nessun elemento collegato all'emissione")
        _add_blocker(blockers, "EMISSION_SCOPE_MISSING",
                     "L'emissione non copre nulla di concreto (nessun lotto, DDT, riga, voce o elemento collegato)")

    # B-COM-02 — Ramo normativo pronto
    ramo_status = ramo.get("status", "draft")
    if ramo_status == "active" or ramo_status == "in_lavorazione":
        _add_check(checks, "BRANCH_STATUS", "verified", True, f"Ramo {ramo_status}")
    else:
        _add_check(checks, "BRANCH_STATUS", "failed", True, f"Ramo in stato {ramo_status}")
        _add_blocker(blockers, "BRANCH_NOT_READY",
                     f"Il ramo normativo e in stato '{ramo_status}' — deve essere 'active' o 'in_lavorazione'")

    # B-COM-04 — Emissione gia emessa
    if emissione.get("stato") == "emessa":
        _add_check(checks, "EMISSION_NOT_ISSUED", "failed", True, "Emissione gia emessa")
        _add_blocker(blockers, "EMISSION_ALREADY_ISSUED",
                     "Questa emissione e gia stata emessa. Per riemettere, creare una nuova revisione.")
    else:
        _add_check(checks, "EMISSION_NOT_ISSUED", "verified", True, "Emissione non ancora emessa")


# ═══════════════════════════════════════════════════════════════════
#  EN 1090 CHECKS
# ═══════════════════════════════════════════════════════════════════

def _get_branch_flags(ramo: dict, commessa: dict) -> dict:
    """Estrae flag operativi dal ramo o dalla commessa."""
    flags = ramo.get("branch_flags", {})
    # Fallback su fasi_produzione della commessa
    fasi = commessa.get("fasi_produzione", [])
    fasi_nomi = set()
    for f in fasi:
        if isinstance(f, dict):
            fasi_nomi.add(f.get("nome", "").lower())
            fasi_nomi.add(f.get("name", "").lower())
        elif isinstance(f, str):
            fasi_nomi.add(f.lower())

    return {
        "saldatura_attiva": flags.get("saldatura_attiva", any("sald" in n for n in fasi_nomi)),
        "zincatura_esterna": flags.get("zincatura_esterna", any("zinc" in n for n in fasi_nomi)),
        "montaggio_attivo": flags.get("montaggio_attivo", any("mont" in n for n in fasi_nomi)),
        "has_automation": flags.get("has_automation", False),
        "requires_force_test": flags.get("requires_force_test", False),
        "has_safety_devices": flags.get("has_safety_devices", False),
    }


async def _check_en1090(emissione: dict, ramo: dict, commessa: dict,
                        checks: list, blockers: list, warnings: list):
    """10 regole Evidence Gate per EN 1090."""
    commessa_id = emissione.get("commessa_id")
    user_id = emissione.get("user_id")
    flags = _get_branch_flags(ramo, commessa)

    # ── E1090-02 — Tracciabilita materiale ────────────────────────
    batch_ids = emissione.get("batch_ids", [])
    if batch_ids:
        _add_check(checks, "MATERIAL_BATCHES", "linked", True,
                   f"{len(batch_ids)} lotti materiale collegati")
    else:
        # Check if any voci have materials
        voce_ids = emissione.get("voce_lavoro_ids", [])
        if voce_ids:
            _add_check(checks, "MATERIAL_BATCHES", "missing", True,
                       "Nessun lotto materiale collegato all'emissione")
            _add_blocker(blockers, "MATERIAL_BATCH_MISSING",
                         "L'emissione copre voci di lavoro ma non ha lotti materiale collegati")
        else:
            _add_check(checks, "MATERIAL_BATCHES", "missing", True,
                       "Nessun lotto materiale collegato")
            _add_warning(warnings, "MATERIAL_BATCH_MISSING",
                         "Nessun lotto materiale collegato — verifica se necessario")

    # ── E1090-03 — Certificati 3.1 ───────────────────────────────
    if batch_ids:
        batches = await db.material_batches.find(
            {"batch_id": {"$in": batch_ids}},
            {"_id": 0, "batch_id": 1, "has_certificate": 1, "certificate_base64": 1, "certificate_filename": 1}
        ).to_list(100)
        batch_map = {b["batch_id"]: b for b in batches}

        missing_certs = []
        uploaded_not_verified = []
        for bid in batch_ids:
            b = batch_map.get(bid, {})
            has_cert = b.get("has_certificate", False) or bool(b.get("certificate_base64"))
            if not has_cert:
                missing_certs.append(bid)
            elif not b.get("has_certificate"):
                uploaded_not_verified.append(bid)

        if missing_certs:
            _add_check(checks, "CERT_31", "missing", True,
                       f"Certificati 3.1 mancanti per {len(missing_certs)} lotti")
            _add_blocker(blockers, "MATERIAL_CERT_MISSING",
                         f"Mancano certificati 3.1 per {len(missing_certs)} lotti: {', '.join(missing_certs[:5])}")
        elif uploaded_not_verified:
            _add_check(checks, "CERT_31", "uploaded", True,
                       f"Certificati caricati ma non tutti verificati ({len(uploaded_not_verified)})")
            _add_warning(warnings, "CERT_31_NOT_VERIFIED",
                         f"Certificati 3.1 caricati ma non verificati per {len(uploaded_not_verified)} lotti")
        else:
            _add_check(checks, "CERT_31", "verified", True,
                       f"Certificati 3.1 presenti per tutti i {len(batch_ids)} lotti")
    else:
        _add_check(checks, "CERT_31", "not_applicable", False, "Nessun lotto collegato")

    # ── E1090-04 — WPS/WPQR ──────────────────────────────────────
    if flags["saldatura_attiva"]:
        wps_count = await db.wps_documents.count_documents(
            {"commessa_id": commessa_id, "user_id": user_id}
        )
        if wps_count == 0:
            # Fallback: check wps collection
            wps_count = await db.wps.count_documents({"commessa_id": commessa_id}) if "wps" in await db.list_collection_names() else 0

        if wps_count > 0:
            _add_check(checks, "WPS_WPQR", "linked", True, f"{wps_count} WPS collegate")
        else:
            _add_check(checks, "WPS_WPQR", "missing", True, "Nessuna WPS presente")
            _add_blocker(blockers, "WPS_MISSING",
                         "Saldatura attiva ma nessuna WPS/WPQR collegata alla commessa")
    else:
        _add_check(checks, "WPS_WPQR", "not_applicable", False, "Saldatura non attiva")

    # ── E1090-05 — Saldatori qualificati ─────────────────────────
    if flags["saldatura_attiva"]:
        welders = await db.welders.find(
            {"user_id": user_id, "is_active": True},
            {"_id": 0, "welder_id": 1, "qualifications": 1}
        ).to_list(50)
        qualified = [w for w in welders if w.get("qualifications") and len(w["qualifications"]) > 0]

        if qualified:
            _add_check(checks, "WELDER_QUALIFICATION", "verified", True,
                       f"{len(qualified)} saldatori qualificati attivi")
        else:
            _add_check(checks, "WELDER_QUALIFICATION", "missing", True,
                       "Nessun saldatore qualificato attivo")
            _add_blocker(blockers, "WELDER_QUALIFICATION_MISSING",
                         "Saldatura attiva ma nessun saldatore con qualifiche valide trovato")
    else:
        _add_check(checks, "WELDER_QUALIFICATION", "not_applicable", False, "Saldatura non attiva")

    # ── E1090-06 — Registro saldatura ────────────────────────────
    if flags["saldatura_attiva"]:
        reg_count = await db.registro_saldatura.count_documents({"commessa_id": commessa_id})
        if reg_count > 0:
            _add_check(checks, "WELDING_REGISTER", "linked", True,
                       f"{reg_count} registrazioni saldatura presenti")
        else:
            _add_check(checks, "WELDING_REGISTER", "missing", True,
                       "Registro saldatura vuoto")
            _add_warning(warnings, "WELDING_REGISTER_MISSING",
                         "Saldatura attiva ma nessuna registrazione nel registro saldatura")
    else:
        _add_check(checks, "WELDING_REGISTER", "not_applicable", False, "Saldatura non attiva")

    # ── E1090-07 — VT (controllo visivo) ─────────────────────────
    vt_reports = await db.report_ispezioni.find(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "approvato": 1, "ispezioni_vt": 1}
    ).to_list(20)

    has_vt_items = any(r.get("ispezioni_vt") and len(r["ispezioni_vt"]) > 0 for r in vt_reports)
    vt_approved = any(r.get("approvato", False) for r in vt_reports if r.get("ispezioni_vt"))

    if vt_reports and has_vt_items:
        if vt_approved:
            _add_check(checks, "VT_INSPECTION", "verified", True, "Controllo VT completato e approvato")
        else:
            _add_check(checks, "VT_INSPECTION", "uploaded", True, "Controllo VT presente ma non approvato")
            _add_warning(warnings, "VT_NOT_APPROVED",
                         "Rapporto VT presente ma non approvato")
    else:
        _add_check(checks, "VT_INSPECTION", "missing", True, "Nessun controllo VT")
        _add_warning(warnings, "VT_NOT_COMPLETED",
                     "Nessun rapporto di ispezione VT trovato per questa commessa")

    # ── E1090-08 — Controllo dimensionale / finale ───────────────
    ctrl_finale = await db.controlli_finali.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "approvato": 1}
    )

    if ctrl_finale:
        if ctrl_finale.get("approvato"):
            _add_check(checks, "FINAL_CONTROL", "verified", True, "Controllo Finale approvato")
        else:
            _add_check(checks, "FINAL_CONTROL", "uploaded", True, "Controllo Finale presente ma non approvato")
            _add_warning(warnings, "FINAL_CONTROL_NOT_APPROVED",
                         "Controllo Finale compilato ma non approvato")
    else:
        _add_check(checks, "FINAL_CONTROL", "missing", True, "Nessun Controllo Finale")
        _add_blocker(blockers, "FINAL_CONTROL_NOT_COMPLETED",
                     "Controllo Finale non completato — obbligatorio per emissione DoP EN 1090")

    # ── Riesame Tecnico (prerequisito ramo EN 1090) ──────────────
    riesame = await db.riesami_tecnici.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "approvato": 1}
    )

    if riesame:
        if riesame.get("approvato"):
            _add_check(checks, "TECHNICAL_REVIEW", "verified", True, "Riesame Tecnico approvato")
        else:
            _add_check(checks, "TECHNICAL_REVIEW", "uploaded", True, "Riesame Tecnico presente ma non approvato")
            _add_warning(warnings, "TECHNICAL_REVIEW_NOT_APPROVED",
                         "Riesame Tecnico compilato ma non approvato")
    else:
        _add_check(checks, "TECHNICAL_REVIEW", "missing", True, "Nessun Riesame Tecnico")
        _add_blocker(blockers, "TECHNICAL_REVIEW_MISSING",
                     "Riesame Tecnico non presente — obbligatorio per emissione DoP EN 1090")

    # ── E1090-09 — Zincatura / Terzista ──────────────────────────
    if flags["zincatura_esterna"]:
        # Check for subcontractor documents
        terzista_docs = await db.commessa_documents.count_documents({
            "commessa_id": commessa_id, "user_id": user_id,
            "$or": [
                {"tipo": {"$in": ["terzista", "zincatura", "trattamento_esterno"]}},
                {"metadata_estratti.tipo": {"$in": ["terzista", "zincatura"]}},
            ]
        })
        if terzista_docs > 0:
            _add_check(checks, "SUBCONTRACT_DOC", "uploaded", True,
                       f"{terzista_docs} documenti terzista/zincatura presenti")
            _add_warning(warnings, "SUBCONTRACT_DOC_NOT_VERIFIED",
                         "Documentazione terzista caricata — verificare completezza")
        else:
            _add_check(checks, "SUBCONTRACT_DOC", "missing", True,
                       "Nessun documento terzista/zincatura")
            _add_blocker(blockers, "SUBCONTRACT_DOC_MISSING",
                         "Zincatura esterna attiva ma nessuna evidenza/documento del trattamento presente")
    else:
        _add_check(checks, "SUBCONTRACT_DOC", "not_applicable", False, "Zincatura esterna non attiva")

    # ── E1090-10 — Strumenti / ITT bloccanti ─────────────────────
    expired_instruments = await db.instruments.count_documents({
        "user_id": user_id,
        "stato": "scaduto"
    })
    open_itt = await db.verbali_itt.count_documents({
        "commessa_id": commessa_id,
        "stato": {"$in": ["aperto", "bloccante"]}
    })

    if expired_instruments > 0 or open_itt > 0:
        msg_parts = []
        if expired_instruments:
            msg_parts.append(f"{expired_instruments} strumenti scaduti")
        if open_itt:
            msg_parts.append(f"{open_itt} ITT bloccanti aperti")
        _add_check(checks, "TOOLING_STATUS", "failed", False, "; ".join(msg_parts))
        _add_warning(warnings, "TOOLING_BLOCK_ACTIVE", "; ".join(msg_parts))
    else:
        _add_check(checks, "TOOLING_STATUS", "verified", False, "Nessun blocco strumenti/ITT")


# ═══════════════════════════════════════════════════════════════════
#  EN 13241 CHECKS
# ═══════════════════════════════════════════════════════════════════

async def _check_en13241(emissione: dict, ramo: dict, commessa: dict,
                         checks: list, blockers: list, warnings: list):
    """6 regole Evidence Gate per EN 13241."""
    commessa_id = emissione.get("commessa_id")
    user_id = emissione.get("user_id")
    flags = _get_branch_flags(ramo, commessa)

    # ── E13241-02 — Identificazione prodotto ─────────────────────
    has_desc = bool(emissione.get("descrizione", "").strip())
    voce_ids = emissione.get("voce_lavoro_ids", [])
    line_ids = emissione.get("line_ids", [])

    if has_desc or voce_ids or line_ids:
        _add_check(checks, "PRODUCT_IDENTIFICATION", "verified", True,
                   "Prodotto/chiusura identificato")
    else:
        _add_check(checks, "PRODUCT_IDENTIFICATION", "missing", True,
                   "Nessuna identificazione del prodotto")
        _add_blocker(blockers, "PRODUCT_IDENTIFICATION_MISSING",
                     "L'emissione non identifica chiaramente il prodotto/chiusura coperto")

    # ── E13241-03 — Manuale uso e manutenzione ──────────────────
    manual_docs = await db.commessa_documents.count_documents({
        "commessa_id": commessa_id, "user_id": user_id,
        "$or": [
            {"tipo": {"$in": ["manuale", "manuale_uso", "manual"]}},
            {"metadata_estratti.tipo": "manuale"},
            {"nome_file": {"$regex": "manual", "$options": "i"}},
        ]
    })

    if manual_docs > 0:
        _add_check(checks, "USER_MANUAL", "uploaded", True,
                   f"{manual_docs} documenti manuale presenti")
    else:
        _add_check(checks, "USER_MANUAL", "missing", True,
                   "Manuale uso e manutenzione mancante")
        _add_blocker(blockers, "USER_MANUAL_MISSING",
                     "Manuale d'Uso e Manutenzione non presente — obbligatorio per certificazione EN 13241")

    # ── E13241-04 — Collaudo / prove ─────────────────────────────
    if flags["requires_force_test"] or flags["has_automation"] or flags["has_safety_devices"]:
        # Check for test reports
        collaudo_docs = await db.commessa_documents.count_documents({
            "commessa_id": commessa_id, "user_id": user_id,
            "$or": [
                {"tipo": {"$in": ["collaudo", "prova_forze", "test_funzionale", "verbale_collaudo"]}},
                {"metadata_estratti.tipo": {"$in": ["collaudo", "prova"]}},
                {"nome_file": {"$regex": "collaudo|prova|test", "$options": "i"}},
            ]
        })

        if collaudo_docs > 0:
            _add_check(checks, "TEST_EVIDENCE", "uploaded", True,
                       f"{collaudo_docs} evidenze di collaudo/prova presenti")
        else:
            _add_check(checks, "TEST_EVIDENCE", "missing", True,
                       "Nessuna evidenza di collaudo/prova")
            _add_blocker(blockers, "FORCE_TEST_MISSING",
                         "Collaudo/prova forze richiesto ma nessuna evidenza presente")
    else:
        _add_check(checks, "TEST_EVIDENCE", "not_applicable", False,
                   "Nessun collaudo specifico richiesto dal profilo")

    # ── E13241-05 — Documenti dispositivi/componenti ─────────────
    if flags["has_automation"] or flags["has_safety_devices"]:
        device_docs = await db.commessa_documents.count_documents({
            "commessa_id": commessa_id, "user_id": user_id,
            "$or": [
                {"tipo": {"$in": ["automazione", "dispositivo_sicurezza", "componente", "scheda_tecnica"]}},
                {"nome_file": {"$regex": "autom|sicur|dispositiv|compon", "$options": "i"}},
            ]
        })

        if device_docs > 0:
            _add_check(checks, "SAFETY_DEVICE_DOC", "uploaded", True,
                       f"{device_docs} documenti dispositivi presenti")
            _add_warning(warnings, "SAFETY_DEVICE_DOC_NOT_VERIFIED",
                         "Documentazione dispositivi caricata — verificare completezza")
        else:
            _add_check(checks, "SAFETY_DEVICE_DOC", "missing", True,
                       "Nessun documento dispositivi sicurezza/automazione")
            _add_blocker(blockers, "SAFETY_DEVICE_DOC_MISSING",
                         "Automazione/dispositivi sicurezza attivi ma nessuna documentazione presente")
    else:
        _add_check(checks, "SAFETY_DEVICE_DOC", "not_applicable", False,
                   "Nessuna automazione/dispositivo sicurezza")

    # ── E13241-06 — Evidenza posa/installazione ──────────────────
    if flags["montaggio_attivo"]:
        posa_count = await db.verbali_posa.count_documents({"commessa_id": commessa_id})
        install_docs = await db.commessa_documents.count_documents({
            "commessa_id": commessa_id, "user_id": user_id,
            "$or": [
                {"tipo": {"$in": ["posa", "installazione", "collaudo_opera"]}},
                {"nome_file": {"$regex": "posa|install|collaudo.opera", "$options": "i"}},
            ]
        })

        if posa_count > 0 or install_docs > 0:
            _add_check(checks, "INSTALLATION_EVIDENCE", "linked", True,
                       f"{posa_count} verbali posa + {install_docs} documenti installazione")
        else:
            _add_check(checks, "INSTALLATION_EVIDENCE", "missing", True,
                       "Nessuna evidenza di posa/installazione")
            _add_blocker(blockers, "INSTALLATION_EVIDENCE_MISSING",
                         "Montaggio attivo ma nessun verbale di posa o evidenza di installazione presente")
    else:
        _add_check(checks, "INSTALLATION_EVIDENCE", "not_applicable", False,
                   "Montaggio non attivo")


# ═══════════════════════════════════════════════════════════════════
#  GENERICA CHECKS
# ═══════════════════════════════════════════════════════════════════

def _check_generica(emissione: dict, ramo: dict,
                    checks: list, blockers: list, warnings: list):
    """Gate minimo per commesse generiche. No DoP/CE."""
    # Solo check scope (gia fatto nei common)
    _add_check(checks, "NO_NORMATIVE_REQUIRED", "verified", False,
               "Commessa generica — nessun requisito normativo per DoP/CE")
    _add_warning(warnings, "GENERIC_NO_DOP_CE",
                 "Ramo GENERICA: non e prevista emissione DoP o CE")

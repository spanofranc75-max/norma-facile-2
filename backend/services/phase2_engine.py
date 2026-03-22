"""
Phase 2 — Commessa Pre-Istruita Revisionata
=============================================
Genera una commessa pre-compilata dalla conferma istruttoria.
Attivata SOLO quando tutti i criteri di eleggibilità sono soddisfatti.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def check_eligibility(istruttoria: dict) -> dict:
    """Verifica se l'istruttoria è eleggibile per la Phase 2.
    NB: i campi dell'istruttoria sono al livello root (classificazione, estrazione_tecnica, etc.)
    """
    reasons = []
    warnings = []
    checks = {}

    classif = istruttoria.get("classificazione", {})
    risposte = istruttoria.get("risposte_utente", {}) or {}
    domande_base = istruttoria.get("domande_residue", []) or []
    domande_ctx = istruttoria.get("domande_contestuali", []) or []
    applic = istruttoria.get("applicabilita", {}) or {}
    segm = istruttoria.get("segmentazione_proposta")
    official_seg = istruttoria.get("official_segmentation")
    est = istruttoria.get("estrazione_tecnica", {}) or {}

    # ─── 1. Istruttoria confermata ───
    confermata = istruttoria.get("confermata", False)
    checks["istruttoria_confermata"] = confermata
    if not confermata:
        reasons.append("L'istruttoria non e ancora confermata dall'utente")

    # ─── 2. Classificazione pura (non MISTA/INCERTA) ───
    normativa = classif.get("normativa_proposta", "")
    is_pure = normativa in ("EN_1090", "EN_13241", "GENERICA")
    checks["classificazione_pura"] = is_pure
    if not is_pure:
        reasons.append(f"La classificazione e '{normativa}' — Phase 2 richiede normativa pura (EN_1090, EN_13241 o GENERICA)")

    # ─── 3. Confidenza alta ───
    confidenza = classif.get("confidenza", "")
    conf_ok = confidenza in ("alta",)
    checks["confidenza_alta"] = conf_ok
    if not conf_ok:
        reasons.append(f"La confidenza della classificazione e '{confidenza}' — serve confidenza 'alta'")

    # ─── 4. Nessuna segmentazione necessaria o non confermata ───
    segm_ok = True
    if segm and segm.get("enabled"):
        if not official_seg or not official_seg.get("confirmed"):
            segm_ok = False
            reasons.append("La segmentazione e attiva ma non confermata")
        for la in (official_seg or {}).get("line_assignments", []):
            if la.get("normativa") == "INCERTA":
                segm_ok = False
                reasons.append("Ci sono righe con normativa INCERTA nella segmentazione")
                break
    checks["segmentazione_ok"] = segm_ok

    # ─── 5. Domande ad alto impatto risposte ───
    alto_aperte = 0
    for i, q in enumerate(domande_base):
        if q.get("impatto") == "alto":
            q_id = str(i)
            if q_id not in risposte:
                alto_aperte += 1
    for q in domande_ctx:
        if q.get("impatto") == "alto" and q.get("stato") == "active" and not q.get("risposta"):
            alto_aperte += 1
    checks["domande_alto_risposte"] = alto_aperte == 0
    if alto_aperte > 0:
        reasons.append(f"{alto_aperte} domande ad alto impatto ancora aperte")

    # ─── 6. Nessun blocco strutturale ───
    blocchi = applic.get("blocchi_conferma", []) or []
    blocchi_attivi = [b for b in blocchi if b.get("bloccante")]
    checks["nessun_blocco"] = len(blocchi_attivi) == 0
    if blocchi_attivi:
        reasons.append(f"Blocco strutturale attivo: {blocchi_attivi[0].get('messaggio', 'sconosciuto')}")

    # ─── 7. Campi critici presenti per normativa ───
    sald = est.get("saldature", {}) or {}
    tratt = est.get("trattamenti_superficiali", {}) or {}
    mont = est.get("montaggio_posa", {}) or {}

    critical_ok = True
    if normativa == "EN_1090":
        if sald.get("stato") in ("mancante", None) and sald.get("presenti") is None:
            critical_ok = False
            reasons.append("Stato saldatura non determinato (richiesto per EN 1090)")
        if not est.get("elementi_strutturali"):
            critical_ok = False
            reasons.append("Nessun elemento strutturale rilevato")
    elif normativa == "EN_13241":
        if not est.get("elementi_strutturali"):
            critical_ok = False
            reasons.append("Nessun manufatto (cancello/portone) rilevato")
    checks["campi_critici"] = critical_ok

    # ─── Non-blocking warnings ───
    if tratt.get("stato") in ("mancante", "incerto"):
        warnings.append("Trattamento superficiale non determinato — da completare manualmente")
    if mont.get("tipo") == "incerto":
        warnings.append("Tipo montaggio incerto — da verificare")

    allowed = len(reasons) == 0
    return {
        "allowed": allowed,
        "reasons": reasons,
        "warnings": warnings,
        "checks": checks,
    }


def generate_preistruita(istruttoria: dict) -> dict:
    """Genera la commessa pre-istruita revisionata dall'istruttoria confermata.
    NB: legge direttamente dai campi root dell'istruttoria.
    """
    classif = istruttoria.get("classificazione", {})
    est = istruttoria.get("estrazione_tecnica", {}) or {}
    profilo = istruttoria.get("profilo_tecnico", {})
    applic = istruttoria.get("applicabilita", {}) or {}

    normativa = classif.get("normativa_proposta", "")

    # ─── Build work items from extracted elements ───
    voci_lavoro = []
    for elem in est.get("elementi_strutturali", []) or []:
        voci_lavoro.append({
            "descrizione": elem.get("descrizione", ""),
            "profilo": elem.get("profilo"),
            "materiale": elem.get("materiale_base"),
            "quantita": elem.get("quantita", 1),
            "stato": "precompilato",
            "fonte": "istruttoria_ai",
        })

    # ─── Build controls ───
    controlli = []
    for ctrl in istruttoria.get("controlli_richiesti", []) or []:
        controlli.append({
            "tipo": ctrl.get("tipo", ""),
            "descrizione": ctrl.get("descrizione", ""),
            "fase": ctrl.get("fase", ""),
            "obbligatorio": True,
            "stato": "da_programmare",
            "fonte": "istruttoria_ai",
        })

    # ─── Build document list ───
    documenti = []
    for doc in istruttoria.get("documenti_richiesti", []) or []:
        documenti.append({
            "documento": doc.get("documento", ""),
            "obbligatorio": doc.get("obbligatorio", True),
            "stato": "da_raccogliere",
            "fonte": "istruttoria_ai",
        })

    # ─── Active branches ───
    sald = est.get("saldature", {}) or {}
    tratt = est.get("trattamenti_superficiali", {}) or {}
    mont = est.get("montaggio_posa", {}) or {}
    prereq_sald = istruttoria.get("prerequisiti_saldatura", {}) or {}
    prereq_tracc = istruttoria.get("prerequisiti_tracciabilita", {}) or {}

    rami_attivi = {
        "saldatura": {
            "attivo": sald.get("presenti", False),
            "wps_necessarie": prereq_sald.get("wps_necessarie", False),
            "qualifica_saldatori": prereq_sald.get("qualifica_saldatori", False),
            "stato": "precompilato" if sald.get("presenti") else "non_applicabile",
        },
        "zincatura": {
            "attivo": tratt.get("tipo") in ("zincatura_caldo",),
            "esecuzione": tratt.get("esecuzione", "incerto"),
            "stato": "precompilato" if tratt.get("tipo") == "zincatura_caldo" else "non_applicabile",
        },
        "montaggio": {
            "attivo": mont.get("previsto", False),
            "tipo": mont.get("tipo", "incerto"),
            "stato": "precompilato" if mont.get("previsto") else "non_applicabile",
        },
    }

    # ─── Build materials requirements ───
    materiali = []
    for elem in est.get("elementi_strutturali", []) or []:
        mat = elem.get("materiale_base")
        if mat:
            materiali.append({
                "materiale": mat,
                "certificato_31": prereq_tracc.get("certificati_31_richiesti", False),
                "tracciabilita_colata": prereq_tracc.get("tracciabilita_colata", False),
                "stato": "da_approvvigionare",
            })

    # ─── Items to complete ───
    da_completare = []
    for item in applic.get("items_condizionali", []) or []:
        da_completare.append({
            "descrizione": item.get("descrizione", ""),
            "motivo": item.get("motivo", ""),
            "stato": "da_completare",
        })

    commessa_id = f"comm_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    return {
        "commessa_id": commessa_id,
        "status": "draft_preistruita",
        "normativa": normativa,
        "profilo_tecnico": profilo,
        "istruttoria_id": istruttoria.get("istruttoria_id"),
        "preventivo_id": istruttoria.get("preventivo_id"),
        "preventivo_number": istruttoria.get("preventivo_number", ""),
        "voci_lavoro": voci_lavoro,
        "controlli": controlli,
        "documenti": documenti,
        "materiali": materiali,
        "rami_attivi": rami_attivi,
        "da_completare": da_completare,
        "etichette": {
            "precompilato": len(voci_lavoro) + len(controlli) + len(documenti),
            "da_completare": len(da_completare),
            "non_emettibile": ["DOP", "Etichetta CE", "Dichiarazione prestazione"],
        },
        "created_at": now.isoformat(),
        "created_by": istruttoria.get("confermata_da", ""),
    }

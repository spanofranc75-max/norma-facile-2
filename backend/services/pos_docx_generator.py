"""
POS DOCX Generator — S4
========================
Genera bozza POS (Piano Operativo di Sicurezza) in formato DOCX
seguendo la struttura dell'Allegato XV D.Lgs. 81/2008.

Macroaree: A (Copertina), B (Impresa), C (Cantiere), D (Prevenzione/DPI),
           E (Valutazione Rischi), F (Emergenza/Dichiarazione)
"""

import io
import logging
from datetime import datetime, timezone
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT

from core.database import db

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  STYLES & HELPERS
# ═══════════════════════════════════════════════════════════════

BLUE = RGBColor(0, 0x55, 0xFF)
DARK = RGBColor(0x1E, 0x29, 0x3B)
GRAY = RGBColor(0x64, 0x74, 0x8B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _set_cell_shading(cell, color_hex: str):
    """Set cell background color."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color_hex)
    shading.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading)


def _add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = DARK
    return h


def _add_para(doc, text, bold=False, size=10, align=None, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if align:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p


def _add_table(doc, headers, rows, col_widths=None):
    """Add a formatted table."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = WHITE
        _set_cell_shading(cell, "1E293B")

    # Data rows
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val) if val else ""
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

    doc.add_paragraph()
    return table


def _soggetto_by_ruolo(soggetti: list, ruolo: str) -> dict:
    for s in soggetti:
        if s.get("ruolo") == ruolo:
            return s
    return {}


def _fmt_date(d):
    if not d:
        return "_______________"
    if isinstance(d, str) and len(d) >= 10:
        return d[:10]
    return str(d)


# ═══════════════════════════════════════════════════════════════
#  SECTION GENERATORS
# ═══════════════════════════════════════════════════════════════

def _gen_copertina(doc, company, cantiere, dc):
    """A.1 — Copertina."""
    doc.add_paragraph()
    _add_para(doc, "PIANO OPERATIVO DI SICUREZZA", bold=True, size=20,
              align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_para(doc, "ai sensi dell'art. 89 comma 1 lettera h) e art. 96",
              size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_para(doc, "del D.Lgs. 81/2008 e s.m.i.",
              size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

    # Company info
    rows = [
        ["Azienda", company.get("business_name", "")],
        ["Sede", company.get("address", "")],
        ["Attivita", company.get("attivita_ateco", "Costruzione di strutture metalliche")],
    ]
    _add_table(doc, ["", ""], rows, col_widths=[5, 12])

    # Cantiere info
    _add_para(doc, f"Cantiere: {dc.get('attivita_cantiere', '')}", bold=True, size=12,
              align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    # Revision table
    revs = cantiere.get("revisioni", [{"rev": "00", "motivazione": "Prima emissione"}])
    rows = [[r.get("rev", "00"), r.get("motivazione", ""), _fmt_date(r.get("data"))] for r in revs]
    _add_table(doc, ["Rev.", "Motivazione", "Data"], rows, col_widths=[2, 10, 5])

    doc.add_page_break()


def _gen_intro(doc):
    """B.3 — Introduzione normativa."""
    _add_heading(doc, "1. INTRODUZIONE", level=1)
    _add_para(doc,
        "Il presente Piano Operativo di Sicurezza (POS) e redatto ai sensi dell'art. 96 "
        "del D.Lgs. 81/2008 e s.m.i. e contiene le informazioni relative alla gestione "
        "della sicurezza e della salute dei lavoratori durante le attivita di cantiere. "
        "Il POS e parte integrante della documentazione di sicurezza del cantiere e deve "
        "essere conservato in cantiere e reso disponibile alle autorita competenti.")


def _gen_documenti_cantiere(doc):
    """B.4 — Elenco documenti da conservare."""
    _add_heading(doc, "2. DOCUMENTAZIONE DA CONSERVARE IN CANTIERE", level=1)
    docs = [
        "Patente a Crediti / Qualificazione impresa",
        "Piano Operativo di Sicurezza (POS)",
        "Comunicazione UNILAV / libro unico",
        "Denuncia INAIL apertura cantiere",
        "DURC in corso di validita",
        "Attestati di formazione sicurezza lavoratori",
        "Idoneita sanitaria lavoratori",
        "Libretti d'uso e manutenzione macchine e attrezzature",
        "Schede di sicurezza sostanze chimiche",
        "Verbali di verifica periodica apparecchiature",
        "Polizza RC e infortuni",
    ]
    for d in docs:
        _add_para(doc, f"- {d}", size=10, space_after=2)


def _gen_anagrafica(doc, company, soggetti):
    """B.6 — Anagrafica aziendale."""
    _add_heading(doc, "3. ANAGRAFICA AZIENDALE", level=1)

    ddl = _soggetto_by_ruolo(soggetti, "DATORE_LAVORO")
    rspp = _soggetto_by_ruolo(soggetti, "RSPP")
    mc = _soggetto_by_ruolo(soggetti, "MEDICO_COMPETENTE")

    rows = [
        ["Impresa", company.get("business_name", "")],
        ["Sede Legale", company.get("address", "")],
        ["Telefono", company.get("phone", "")],
        ["Email / PEC", company.get("email", "")],
        ["P.IVA / C.F.", company.get("partita_iva", "")],
        ["Datore di Lavoro", ddl.get("nome", "")],
        ["RSPP", rspp.get("nome", "")],
        ["Medico Competente", mc.get("nome", "")],
    ]
    _add_table(doc, ["Campo", "Valore"], rows, col_widths=[5, 12])


def _gen_mansionario(doc, lavoratori):
    """C.7 — Mansionario lavoratori."""
    _add_heading(doc, "4. MANSIONARIO LAVORATORI", level=1)
    if not lavoratori:
        _add_para(doc, "Nessun lavoratore assegnato al cantiere.", size=10)
        return

    rows = []
    for lav in lavoratori:
        rows.append([
            lav.get("nominativo", ""),
            lav.get("mansione", ""),
            "Si" if lav.get("addetto_primo_soccorso") else "No",
            "Si" if lav.get("addetto_antincendio") else "No",
        ])
    _add_table(doc, ["Nominativo", "Mansione", "Primo Soccorso", "Antincendio"], rows,
               col_widths=[5, 5, 3.5, 3.5])


def _gen_dati_cantiere(doc, dc):
    """C.8 — Dati cantiere."""
    _add_heading(doc, "5. DATI RELATIVI AL CANTIERE", level=1)
    rows = [
        ["Attivita", dc.get("attivita_cantiere", "")],
        ["Data inizio lavori", _fmt_date(dc.get("data_inizio_lavori"))],
        ["Data presunta fine lavori", _fmt_date(dc.get("data_fine_prevista"))],
        ["Indirizzo cantiere", dc.get("indirizzo_cantiere", "")],
        ["Citta", dc.get("citta_cantiere", "")],
        ["Provincia", dc.get("provincia_cantiere", "")],
    ]
    _add_table(doc, ["Campo", "Valore"], rows, col_widths=[6, 11])


def _gen_soggetti(doc, soggetti):
    """C.9 — Soggetti di riferimento."""
    _add_heading(doc, "6. SOGGETTI DI RIFERIMENTO", level=1)

    mapping = [
        ("COMMITTENTE", "Committente"),
        ("REFERENTE_COMMITTENTE", "Referente Committente"),
        ("RESPONSABILE_LAVORI", "Responsabile dei Lavori"),
        ("DIRETTORE_LAVORI", "Direttore dei Lavori"),
        ("CSP", "Coordinatore Sicurezza Progettazione"),
        ("CSE", "Coordinatore Sicurezza Esecuzione"),
        ("PROGETTISTA", "Progettista"),
        ("STRUTTURISTA", "Strutturista"),
        ("COLLAUDATORE", "Collaudatore"),
    ]
    rows = []
    for ruolo, label in mapping:
        s = _soggetto_by_ruolo(soggetti, ruolo)
        nome = s.get("nome", "")
        if nome:
            rows.append([label, nome, s.get("telefono", ""), s.get("email", "")])
    if rows:
        _add_table(doc, ["Ruolo", "Nominativo", "Telefono", "Email"], rows,
                   col_widths=[5, 5, 3.5, 3.5])
    else:
        _add_para(doc, "Nessun soggetto di riferimento indicato.")


def _gen_turni(doc, turni):
    """C.10 — Turni di lavoro."""
    _add_heading(doc, "7. TURNI DI LAVORO", level=2)
    matt = turni.get("mattina", "08:00 - 13:00") if turni else "08:00 - 13:00"
    pom = turni.get("pomeriggio", "14:00 - 17:00") if turni else "14:00 - 17:00"
    _add_table(doc, ["Turno", "Orario"], [
        ["Mattina", matt],
        ["Pomeriggio", pom],
    ], col_widths=[6, 11])


def _gen_subappalti(doc, subappalti):
    """C.11 — Lavorazioni in subappalto."""
    _add_heading(doc, "8. LAVORAZIONI IN SUBAPPALTO", level=2)
    if not subappalti:
        _add_para(doc, "Non sono previste lavorazioni in subappalto.")
        return
    rows = [[s.get("lavorazione", ""), s.get("impresa", ""), s.get("durata_prevista", "")] for s in subappalti]
    _add_table(doc, ["Lavorazione", "Impresa / Lav. Autonomo", "Durata prevista"], rows,
               col_widths=[6, 6, 5])


def _gen_misure_prevenzione(doc):
    """C.12 — Misure di prevenzione generali (testo fisso sintetico)."""
    _add_heading(doc, "9. PRINCIPALI MISURE DI PREVENZIONE E PROTEZIONE", level=1)
    _add_para(doc,
        "Le principali misure di prevenzione adottate dall'impresa per la tutela della "
        "sicurezza e salute dei lavoratori sono conformi a quanto prescritto dal D.Lgs. 81/2008 "
        "e comprendono:", size=10, space_after=4)
    items = [
        "Obblighi generali dei lavoratori (Art. 20)",
        "Prevenzione rischio investimento e caduta materiali",
        "Prevenzione scivolamenti, cadute a livello",
        "Protezione dall'esposizione al rumore (D.Lgs. 81/2008 Titolo VIII Capo II)",
        "Protezione da tagli, punture, abrasioni",
        "Prevenzione cesoiamento e schiacciamento",
        "Misure per lavori in elevazione e caduta dall'alto",
        "Uso corretto di scale portatili (Art. 113)",
        "Precauzioni per uso vernici e solventi",
        "Movimentazione manuale dei carichi (Titolo VI)",
        "Protezione da polveri e agenti chimici",
        "Sorveglianza sanitaria (Art. 41)",
    ]
    for item in items:
        _add_para(doc, f"- {item}", size=10, space_after=2)


def _gen_dpi_section(doc, dpi_calcolati, dpi_lib_map):
    """D.15 — DPI."""
    _add_heading(doc, "10. DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI)", level=1)
    _add_para(doc,
        "I seguenti DPI sono stati individuati in base all'analisi dei rischi "
        "specifici del cantiere e delle fasi operative previste:")

    if not dpi_calcolati:
        _add_para(doc, "Nessun DPI specifico aggiuntivo individuato.")
        return

    rows = []
    for d in dpi_calcolati:
        codice = d.get("codice", "")
        lib = dpi_lib_map.get(codice, {})
        if lib.get("tipo") != "dpi":
            continue
        rows.append([
            lib.get("nome", codice),
            lib.get("norma_riferimento", ""),
            ", ".join(d.get("da_rischi", [])[:3]),
        ])
    if rows:
        _add_table(doc, ["DPI", "Norma UNI EN", "Rischi collegati"], rows,
                   col_widths=[6, 4, 7])


def _gen_macchine(doc, macchine):
    """D.17 — Macchine e attrezzature."""
    _add_heading(doc, "11. MACCHINE / ATTREZZATURE / IMPIANTI", level=1)
    if not macchine:
        _add_para(doc, "Nessuna macchina/attrezzatura specifica indicata per il cantiere.")
        return
    rows = [[m.get("nome", ""),
             "Si" if m.get("marcata_ce") else "No",
             "Si" if m.get("verifiche_periodiche") else "No"]
            for m in macchine]
    _add_table(doc, ["Macchina / Attrezzatura", "Marcata CE", "Verifiche periodiche"], rows,
               col_widths=[7, 4.5, 5.5])


def _gen_valutazione_intro(doc):
    """E.22-E.23 — Metodologia valutazione rischi."""
    _add_heading(doc, "12. VALUTAZIONE DEI RISCHI", level=1)
    _add_heading(doc, "12.1 Obiettivo della valutazione", level=2)
    _add_para(doc,
        "La valutazione dei rischi e stata condotta secondo quanto previsto dagli artt. 28 e 29 "
        "del D.Lgs. 81/2008, con l'obiettivo di individuare i pericoli presenti nell'ambiente "
        "di lavoro e stimare il rischio residuo dopo l'applicazione delle misure di prevenzione.")
    _add_heading(doc, "12.2 Criteri adottati", level=2)
    _add_para(doc,
        "Il metodo adottato si basa sulla formula: R = P x D\n"
        "dove P = Probabilita (1-4), D = Entita del Danno (1-4).\n"
        "Classificazione: R 1-2 = Basso, R 3-4 = Medio, R 6-8 = Alto, R 9-16 = Molto Alto.")


def _gen_schede_rischio(doc, fasi, rischi_lib_map, dpi_lib_map):
    """E.30 — Schede rischio per fase di lavoro (CORE)."""
    _add_heading(doc, "13. SCHEDE RISCHIO PER FASE DI LAVORO", level=1)
    _add_para(doc,
        "Di seguito le schede di valutazione rischi per ciascuna fase lavorativa "
        "individuata per il presente cantiere.", bold=True)

    for idx, fase in enumerate(fasi, 1):
        codice = fase.get("fase_codice", "")
        confidence = fase.get("confidence", "dedotto")

        # Get fase name from library or use code
        fase_name = codice
        rischi_att = fase.get("rischi_attivati", [])

        _add_heading(doc, f"13.{idx} — {codice}", level=2)

        conf_label = {"confermato": "Confermata", "dedotto": "Dedotta dall'AI", "incerto": "Da verificare"}.get(confidence, confidence)
        _add_para(doc, f"Confidenza: {conf_label}", size=9, space_after=4)
        if fase.get("reasoning"):
            _add_para(doc, f"Motivazione: {fase['reasoning']}", size=9, space_after=4)

        if not rischi_att:
            _add_para(doc, "Nessun rischio specifico attivato per questa fase.")
            continue

        # Rischi table
        risk_rows = []
        dpi_for_fase = set()
        misure_for_fase = []

        for ra in rischi_att:
            rc = ra.get("rischio_codice", "")
            lib = rischi_lib_map.get(rc, {})
            vd = lib.get("valutazione_default", {})
            risk_rows.append([
                lib.get("nome", rc),
                vd.get("probabilita", ""),
                vd.get("entita_danno", ""),
                vd.get("classe", ""),
            ])
            for d in lib.get("dpi_ids", []):
                dpi_for_fase.add(d)
            for m in lib.get("misure_ids", []):
                mlib = dpi_lib_map.get(m, {})
                if mlib.get("nome"):
                    misure_for_fase.append(mlib["nome"])

        _add_para(doc, "Rischi individuati:", bold=True, size=10, space_after=2)
        _add_table(doc, ["Rischio", "Probabilita", "Danno", "Classe"], risk_rows,
                   col_widths=[6, 3.5, 3.5, 4])

        # DPI for this phase
        if dpi_for_fase:
            _add_para(doc, "DPI richiesti:", bold=True, size=10, space_after=2)
            dpi_rows = []
            for d_code in sorted(dpi_for_fase):
                dlib = dpi_lib_map.get(d_code, {})
                dpi_rows.append([
                    dlib.get("nome", d_code),
                    dlib.get("norma_riferimento", ""),
                ])
            _add_table(doc, ["DPI", "Norma"], dpi_rows, col_widths=[9, 8])

        # Misure
        if misure_for_fase:
            _add_para(doc, "Misure di prevenzione:", bold=True, size=10, space_after=2)
            for m in sorted(set(misure_for_fase)):
                _add_para(doc, f"- {m}", size=10, space_after=2)


def _gen_emergenza(doc, numeri_utili):
    """F.31-F.33 — Emergenza e numeri utili."""
    _add_heading(doc, "14. GESTIONE DELLE EMERGENZE", level=1)
    _add_para(doc,
        "In caso di emergenza, i lavoratori devono seguire le procedure aziendali "
        "e contattare immediatamente i servizi di soccorso. Il preposto di cantiere "
        "coordina le operazioni di evacuazione.")

    _add_heading(doc, "14.1 Numeri utili", level=2)
    default_numeri = [
        {"servizio": "Vigili del Fuoco", "numero": "115"},
        {"servizio": "Pronto Soccorso", "numero": "118"},
        {"servizio": "Carabinieri", "numero": "112"},
        {"servizio": "Polizia di Stato", "numero": "113"},
    ]
    nums = numeri_utili if numeri_utili else default_numeri
    rows = [[n.get("servizio", ""), n.get("numero", "")] for n in nums]
    _add_table(doc, ["Servizio", "Numero"], rows, col_widths=[9, 8])


def _gen_dichiarazione(doc, company, soggetti, data_dich):
    """F.34 — Dichiarazione finale."""
    doc.add_page_break()
    _add_heading(doc, "15. DICHIARAZIONE", level=1)
    _add_para(doc,
        "Il sottoscritto Datore di Lavoro dichiara che il presente Piano Operativo di Sicurezza "
        "e stato redatto ai sensi dell'art. 96 del D.Lgs. 81/2008 e che le informazioni in esso "
        "contenute corrispondono alla reale organizzazione del cantiere.")

    ddl = _soggetto_by_ruolo(soggetti, "DATORE_LAVORO")
    rspp = _soggetto_by_ruolo(soggetti, "RSPP")

    _add_para(doc, f"Data: {_fmt_date(data_dich)}", size=10, space_after=12)
    _add_para(doc, "")
    rows = [
        ["Il Datore di Lavoro", ddl.get("nome", ""), "_________________________"],
        ["Il RSPP", rspp.get("nome", ""), "_________________________"],
    ]
    _add_table(doc, ["Ruolo", "Nominativo", "Firma"], rows, col_widths=[5, 6, 6])


# ═══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

async def genera_pos_docx(cantiere_id: str, user_id: str) -> dict:
    """Generate POS DOCX from confirmed cantiere data.
    Returns: {"success": bool, "file_bytes": bytes, "filename": str, ...} or {"error": str}
    """

    # 1. Load cantiere
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return {"error": "Cantiere non trovato"}

    # 2. Check gate
    gate = cantiere.get("gate_pos_status", {})
    completezza = gate.get("completezza_percentuale", 0)

    # 3. Load company settings
    company = await db.company_settings.find_one({"user_id": user_id}, {"_id": 0}) or {}

    # 4. Load library data for enrichment
    rischi_lib_map = {}
    async for r in db.lib_rischi_sicurezza.find({"user_id": user_id, "active": True}, {"_id": 0}):
        rischi_lib_map[r["codice"]] = r

    dpi_lib_map = {}
    async for d in db.lib_dpi_misure.find({"user_id": user_id, "active": True}, {"_id": 0}):
        dpi_lib_map[d["codice"]] = d

    # 5. Extract data
    dc = cantiere.get("dati_cantiere", {})
    soggetti = cantiere.get("soggetti", [])
    lavoratori = cantiere.get("lavoratori_coinvolti", [])
    fasi = cantiere.get("fasi_lavoro_selezionate", [])
    dpi_calcolati = cantiere.get("dpi_calcolati", [])
    macchine = cantiere.get("macchine_attrezzature", [])
    numeri_utili = cantiere.get("numeri_utili", [])
    turni = cantiere.get("turni_lavoro", {})
    subappalti = cantiere.get("subappalti", [])

    # 6. Build document
    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(10)

    # Set margins
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # Generate sections
    _gen_copertina(doc, company, cantiere, dc)
    _gen_intro(doc)
    _gen_documenti_cantiere(doc)
    _gen_anagrafica(doc, company, soggetti)
    _gen_mansionario(doc, lavoratori)
    _gen_dati_cantiere(doc, dc)
    _gen_soggetti(doc, soggetti)
    _gen_turni(doc, turni)
    _gen_subappalti(doc, subappalti)
    _gen_misure_prevenzione(doc)
    _gen_dpi_section(doc, dpi_calcolati, dpi_lib_map)
    _gen_macchine(doc, macchine)
    _gen_valutazione_intro(doc)
    _gen_schede_rischio(doc, fasi, rischi_lib_map, dpi_lib_map)
    _gen_emergenza(doc, numeri_utili)
    _gen_dichiarazione(doc, company, soggetti,
                       cantiere.get("data_dichiarazione"))

    # 7. Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # 8. Record generation metadata
    now = datetime.now(timezone.utc).isoformat()
    gen_meta = {
        "timestamp": now,
        "completezza_al_momento": completezza,
        "n_fasi": len(fasi),
        "n_rischi": sum(len(f.get("rischi_attivati", [])) for f in fasi),
        "n_pagine_stimate": 15 + len(fasi) * 2,
        "versione": (cantiere.get("pos_generazioni", [{}])[-1].get("versione", 0) + 1)
            if cantiere.get("pos_generazioni") else 1,
    }

    await db.cantieri_sicurezza.update_one(
        {"cantiere_id": cantiere_id, "user_id": user_id},
        {
            "$push": {"pos_generazioni": gen_meta},
            "$set": {"ultima_generazione_pos": now, "updated_at": now},
        }
    )

    attivita = dc.get("attivita_cantiere", "cantiere")[:40].replace(" ", "_")
    filename = f"POS_{attivita}_{now[:10]}.docx"

    return {
        "success": True,
        "file_bytes": buffer.getvalue(),
        "filename": filename,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "generazione": gen_meta,
        "gate_completezza": completezza,
    }

"""POS (Piano Operativo di Sicurezza) PDF generator."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, ListFlowable, ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime

BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
RED = colors.HexColor("#DC2626")


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T", parent=styles["Heading1"], fontSize=20, textColor=DARK, alignment=TA_CENTER, spaceAfter=8 * mm),
        "h1": ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, textColor=DARK, spaceBefore=10 * mm, spaceAfter=4 * mm),
        "h2": ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=BLUE, spaceBefore=6 * mm, spaceAfter=3 * mm),
        "h3": ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11, textColor=DARK, spaceBefore=4 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14, alignment=TA_JUSTIFY),
        "body_bold": ParagraphStyle("BB", parent=styles["Normal"], fontSize=10, leading=14, fontName="Helvetica-Bold"),
        "small": ParagraphStyle("S", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        "center": ParagraphStyle("C", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER),
        "red": ParagraphStyle("R", parent=styles["Normal"], fontSize=10, textColor=RED, fontName="Helvetica-Bold"),
    }


def generate_pos_pdf(pos: dict, company: dict = None, risk_assessment_text: str = None) -> BytesIO:
    """Generate POS (Piano Operativo di Sicurezza) PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    s = _build_styles()
    cantiere = pos.get("cantiere", {})
    company_name = (company or {}).get("business_name", "[Ragione Sociale]")
    company_addr = (company or {}).get("address", "[Indirizzo]")
    company_vat = (company or {}).get("vat_number", "")
    now = datetime.now().strftime("%d/%m/%Y")

    elements = []

    # ═══════════ COVER PAGE ═══════════
    elements.append(Spacer(1, 30 * mm))
    elements.append(Paragraph("PIANO OPERATIVO DI SICUREZZA", s["title"]))
    elements.append(Paragraph("ai sensi del D.Lgs. 81/2008 e s.m.i.", s["center"]))
    elements.append(Spacer(1, 15 * mm))

    cover_data = [
        ["CANTIERE:", cantiere.get("address", "-") + " - " + cantiere.get("city", "")],
        ["COMMITTENTE:", cantiere.get("committente", "-")],
        ["IMPRESA:", company_name],
        ["PROGETTO:", pos.get("project_name", "-")],
        ["DATA:", now],
    ]
    ct = Table(cover_data, colWidths=[45 * mm, 120 * mm])
    ct.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), BLUE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(ct)

    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph("DOCUMENTO RISERVATO - COPIA CONTROLLATA", s["red"]))

    # ═══════════ PAGE 2: DATI IMPRESA ═══════════
    elements.append(PageBreak())
    elements.append(Paragraph("1. DATI IDENTIFICATIVI DELL'IMPRESA", s["h1"]))

    imp_data = [
        ["Ragione Sociale:", company_name],
        ["Sede Legale:", company_addr],
        ["P.IVA:", company_vat or "-"],
        ["Datore di Lavoro:", company_name],
        ["RSPP:", company_name],
        ["RLS:", "Da nominare"],
        ["Medico Competente:", "Da nominare"],
    ]
    it = Table(imp_data, colWidths=[50 * mm, 120 * mm])
    it.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(it)

    # ═══════════ DATI CANTIERE ═══════════
    elements.append(Paragraph("2. DATI DEL CANTIERE", s["h1"]))

    cant_data = [
        ["Indirizzo Cantiere:", cantiere.get("address", "-")],
        ["Citta':", cantiere.get("city", "-")],
        ["Committente:", cantiere.get("committente", "-")],
        ["Resp. dei Lavori:", cantiere.get("responsabile_lavori", "-")],
        ["Coord. Sicurezza:", cantiere.get("coordinatore_sicurezza", "-")],
        ["Durata Prevista:", f"{cantiere.get('duration_days', 30)} giorni"],
        ["Data Inizio:", cantiere.get("start_date", "-")],
    ]
    ctt = Table(cant_data, colWidths=[50 * mm, 120 * mm])
    ctt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(ctt)

    # ═══════════ LAVORAZIONI E RISCHI ═══════════
    elements.append(PageBreak())
    elements.append(Paragraph("3. DESCRIZIONE DELLE LAVORAZIONI PREVISTE", s["h1"]))

    from models.sicurezza import RISCHI_LAVORAZIONI
    selected = pos.get("selected_risks", [])
    if selected:
        risk_items = []
        for r in RISCHI_LAVORAZIONI:
            if r["id"] in selected:
                risk_items.append(ListItem(Paragraph(f"<b>{r['label']}</b> ({r['category']})", s["body"])))
        if risk_items:
            elements.append(ListFlowable(risk_items, bulletType="bullet", start="circle"))
    else:
        elements.append(Paragraph("Nessuna lavorazione specifica selezionata.", s["body"]))

    # ═══════════ MACCHINE ═══════════
    elements.append(Paragraph("4. MACCHINE E ATTREZZATURE UTILIZZATE", s["h1"]))

    from models.sicurezza import MACCHINE_ATTREZZATURE
    sel_machines = pos.get("selected_machines", [])
    if sel_machines:
        mach_header = ["Attrezzatura", "Categoria", "Conforme CE"]
        mach_data = [mach_header]
        for m in MACCHINE_ATTREZZATURE:
            if m["id"] in sel_machines:
                mach_data.append([m["label"], m["category"], "Si'"])
        mt = Table(mach_data, colWidths=[75 * mm, 50 * mm, 35 * mm], repeatRows=1)
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(mt)
    else:
        elements.append(Paragraph("Nessuna macchina selezionata.", s["body"]))

    # ═══════════ DPI ═══════════
    elements.append(Paragraph("5. DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI)", s["h1"]))

    from models.sicurezza import DPI_LIST
    sel_dpi = pos.get("selected_dpi", [])
    if sel_dpi:
        dpi_header = ["DPI", "Protezione", "Norma"]
        dpi_data = [dpi_header]
        norme_map = {
            "Testa": "EN 397", "Occhi": "EN 166", "Udito": "EN 352",
            "Mani": "EN 388/407", "Piedi": "EN ISO 20345", "Anticaduta": "EN 361/362",
            "Corpo": "EN ISO 11611", "Vie respiratorie": "EN 149",
        }
        for d in DPI_LIST:
            if d["id"] in sel_dpi:
                dpi_data.append([d["label"], d["category"], norme_map.get(d["category"], "-")])
        dt = Table(dpi_data, colWidths=[75 * mm, 40 * mm, 40 * mm], repeatRows=1)
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(dt)
    else:
        elements.append(Paragraph("Nessun DPI selezionato.", s["body"]))

    # ═══════════ VALUTAZIONE RISCHI (AI) ═══════════
    elements.append(PageBreak())
    elements.append(Paragraph("6. VALUTAZIONE DEI RISCHI SPECIFICI", s["h1"]))

    ai_text = risk_assessment_text or pos.get("ai_risk_assessment", "")
    if ai_text:
        for para in ai_text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if para.startswith("###") or para.startswith("**") or para.upper() == para:
                elements.append(Paragraph(para.replace("###", "").replace("**", "").strip(), s["h2"]))
            else:
                elements.append(Paragraph(para.replace("\n", "<br/>"), s["body"]))
                elements.append(Spacer(1, 2 * mm))
    else:
        elements.append(Paragraph(
            "La valutazione dei rischi specifici verra' completata dopo la generazione tramite AI. "
            "Utilizzare il pulsante 'Genera Valutazione Rischi (AI)' nell'applicazione.",
            s["body"],
        ))

    # ═══════════ EMERGENZE ═══════════
    elements.append(PageBreak())
    elements.append(Paragraph("7. GESTIONE DELLE EMERGENZE", s["h1"]))
    elements.append(Paragraph("7.1 Numeri di Emergenza", s["h2"]))

    emer_data = [
        ["Servizio", "Numero"],
        ["Emergenza Sanitaria (118)", "118"],
        ["Vigili del Fuoco", "115"],
        ["Carabinieri", "112"],
        ["Polizia", "113"],
        ["Pronto Soccorso piu' vicino", "Da compilare"],
    ]
    et = Table(emer_data, colWidths=[80 * mm, 80 * mm])
    et.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(et)

    elements.append(Paragraph("7.2 Presidi di Primo Soccorso", s["h2"]))
    elements.append(Paragraph(
        "In cantiere e' presente una cassetta di primo soccorso conforme al D.M. 388/2003. "
        "Il contenuto viene verificato periodicamente e reintegrato dopo ogni utilizzo.",
        s["body"],
    ))

    elements.append(Paragraph("7.3 Mezzi Antincendio", s["h2"]))
    elements.append(Paragraph(
        "In cantiere sono presenti estintori a polvere ABC e CO2, posizionati in prossimita' "
        "delle zone di saldatura e taglio. La verifica semestrale e' documentata.",
        s["body"],
    ))

    # ═══════════ SIGNATURE ═══════════
    elements.append(PageBreak())
    elements.append(Paragraph("8. FIRME", s["h1"]))
    elements.append(Spacer(1, 10 * mm))

    sig_data = [
        ["Datore di Lavoro", "RSPP", "RLS"],
        ["", "", ""],
        ["", "", ""],
        ["_________________", "_________________", "_________________"],
        [f"({company_name})", "(Nome e Cognome)", "(Nome e Cognome)"],
    ]
    st = Table(sig_data, colWidths=[55 * mm, 55 * mm, 55 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(st)

    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph(f"Data: {now}", s["body"]))
    elements.append(Paragraph(f"Luogo: {cantiere.get('city', '_____________')}", s["body"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

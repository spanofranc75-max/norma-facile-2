"""PDF service for Perizia Sinistro (Damage Assessment)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from io import BytesIO

BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT = colors.HexColor("#F8FAFC")
RED = colors.HexColor("#DC2626")

TIPO_LABELS = {
    "strutturale": "DANNO STRUTTURALE (EN 1090)",
    "estetico": "DANNO ESTETICO",
    "automatismi": "DANNO AUTOMATISMI (EN 12453)",
}


def generate_perizia_pdf(doc: dict, company: dict = None) -> BytesIO:
    buffer = BytesIO()
    page_doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    usable_w = A4[0] - 30 * mm
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=16, textColor=DARK, spaceAfter=3 * mm)
    section_style = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=12, textColor=BLUE, spaceBefore=6 * mm, spaceAfter=3 * mm)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13, alignment=TA_JUSTIFY)
    small_style = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    bold_style = ParagraphStyle("B", parent=styles["Normal"], fontSize=9, leading=13, fontName="Helvetica-Bold")

    elements = []

    # ── Header ──
    co = company or {}
    if co.get("company_name"):
        elements.append(Paragraph(co["company_name"], ParagraphStyle("Co", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold", textColor=DARK)))
        if co.get("address"):
            elements.append(Paragraph(co["address"], small_style))
        if co.get("vat_number"):
            elements.append(Paragraph(f"P.IVA: {co['vat_number']}", small_style))
        elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("PERIZIA TECNICA ESTIMATIVA", title_style))

    # Info block
    tipo = doc.get("tipo_danno", "strutturale")
    loc = doc.get("localizzazione", {})
    info_data = [
        ["N. Perizia:", doc.get("number", "-"), "Data:", doc.get("created_at", "").strftime("%d/%m/%Y") if hasattr(doc.get("created_at", ""), "strftime") else str(doc.get("created_at", "-"))[:10]],
        ["Tipo Danno:", TIPO_LABELS.get(tipo, tipo), "Cliente:", doc.get("client_name", "-")],
        ["Localizzazione:", loc.get("indirizzo", "-"), "", ""],
    ]
    it = Table(info_data, colWidths=[25 * mm, (usable_w - 50 * mm) / 2, 18 * mm, (usable_w - 50 * mm) / 2 + 7 * mm])
    it.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    elements.append(it)
    elements.append(Spacer(1, 4 * mm))

    # ── Sezione 1: Stato di Fatto ──
    elements.append(Paragraph("1. DESCRIZIONE DELLO STATO DI FATTO", section_style))
    stato = doc.get("stato_di_fatto", "")
    if stato:
        for para in stato.split("\n"):
            if para.strip():
                elements.append(Paragraph(para.strip(), body_style))
                elements.append(Spacer(1, 1.5 * mm))
    else:
        elements.append(Paragraph("(Analisi non ancora effettuata)", small_style))

    # ── Moduli danneggiati ──
    moduli = doc.get("moduli", [])
    if moduli:
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph("Moduli coinvolti:", bold_style))
        mod_header = ["#", "Descrizione", "Lunghezza (ml)", "Altezza (m)", "Note"]
        mod_data = [mod_header]
        total_ml = 0
        for i, m in enumerate(moduli):
            ml = float(m.get("lunghezza_ml", 0))
            total_ml += ml
            mod_data.append([
                str(i + 1),
                m.get("descrizione", "-"),
                f"{ml:.2f}",
                f"{float(m.get('altezza_m', 0)):.2f}",
                m.get("note", ""),
            ])
        mod_data.append(["", "TOTALE", f"{total_ml:.2f}", "", ""])

        mt = Table(mod_data, colWidths=[8 * mm, usable_w - 80 * mm, 22 * mm, 22 * mm, 28 * mm])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.85, 0.85, 0.85)),
            ("ALIGN", (2, 0), (3, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEABOVE", (0, -1), (-1, -1), 1, DARK),
        ]))
        elements.append(mt)

    # ── Sezione 2: Tabella Costi ──
    elements.append(Paragraph("2. COMPUTO METRICO ESTIMATIVO", section_style))
    voci = doc.get("voci_costo", [])
    if voci:
        cost_header = ["Cod.", "Descrizione", "U.M.", "Q.ta", "Prezzo Unit.", "Totale"]
        cost_data = [cost_header]
        for v in voci:
            cost_data.append([
                v.get("codice", ""),
                Paragraph(v.get("descrizione", ""), ParagraphStyle("CD", parent=styles["Normal"], fontSize=7.5, leading=10)),
                v.get("unita", ""),
                f"{float(v.get('quantita', 0)):.1f}",
                f"{float(v.get('prezzo_unitario', 0)):.2f}",
                f"{float(v.get('totale', 0)):.2f}",
            ])

        # Total row — breakdown with subtotal, maggiorazioni, sconto
        # Separate normal voci from adjustment voci
        voci_lavoro = [v for v in voci if v.get("codice", "") not in ("ACC.01", "SCO.01")]
        voce_accesso = next((v for v in voci if v.get("codice") == "ACC.01"), None)
        voce_sconto = next((v for v in voci if v.get("codice") == "SCO.01"), None)

        subtotale_lavori = sum(v.get("totale", 0) for v in voci_lavoro)
        total_perizia = sum(v.get("totale", 0) for v in voci)

        # Subtotale lavori
        cost_data.append(["", "", "", "", "Subtotale lavori:", f"{subtotale_lavori:.2f}"])
        if voce_accesso:
            cost_data.append(["", "", "", "", "Magg. accesso difficile (+15%):", f"{voce_accesso['totale']:.2f}"])
        if voce_sconto:
            cost_data.append(["", "", "", "", "Sconto cortesia:", f"{voce_sconto['totale']:.2f}"])
        cost_data.append(["", "", "", "", "TOTALE PERIZIA:", f"{total_perizia:.2f} EUR"])

        # Calculate row styling offsets
        num_summary_rows = 2 + (1 if voce_accesso else 0) + (1 if voce_sconto else 0)

        ct = Table(cost_data, colWidths=[12 * mm, usable_w - 88 * mm, 14 * mm, 14 * mm, 24 * mm, 24 * mm])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -(num_summary_rows + 1)), 0.4, colors.Color(0.85, 0.85, 0.85)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -(num_summary_rows + 1)), [colors.white, LIGHT]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            # Summary rows
            ("LINEABOVE", (0, -num_summary_rows), (-1, -num_summary_rows), 0.8, colors.Color(0.7, 0.7, 0.7)),
            ("FONTNAME", (4, -num_summary_rows), (5, -1), "Helvetica-Bold"),
            # Grand total row
            ("FONTSIZE", (0, -1), (-1, -1), 10),
            ("TEXTCOLOR", (5, -1), (5, -1), BLUE),
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, DARK),
            ("TOPPADDING", (0, -1), (-1, -1), 4),
        ]
        ct.setStyle(TableStyle(style_cmds))
        elements.append(ct)
    else:
        elements.append(Paragraph("(Nessuna voce di costo inserita)", small_style))

    # ── Sezione 3: Nota Tecnica ──
    nota = doc.get("nota_tecnica", "")
    if nota:
        elements.append(Paragraph("3. NOTA TECNICA PER IL PERITO", section_style))
        for para in nota.split("\n"):
            if para.strip():
                elements.append(Paragraph(para.strip(), body_style))
                elements.append(Spacer(1, 1.5 * mm))

    # ── Notes ──
    if doc.get("notes"):
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph("NOTE AGGIUNTIVE", section_style))
        elements.append(Paragraph(doc["notes"], body_style))

    # ── Lettera di Accompagnamento ──
    lettera = doc.get("lettera_accompagnamento", "")
    if lettera:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("LETTERA DI ACCOMPAGNAMENTO TECNICA", title_style))
        elements.append(Spacer(1, 2 * mm))
        for para in lettera.split("\n"):
            txt = para.strip()
            if not txt:
                elements.append(Spacer(1, 2 * mm))
                continue
            # Detect section headers (all caps or numbered)
            if txt.isupper() or (len(txt) < 100 and (txt.startswith("1.") or txt.startswith("2.") or txt.startswith("3.") or txt.startswith("Oggetto:"))):
                elements.append(Paragraph(txt, bold_style))
            else:
                elements.append(Paragraph(txt, body_style))
            elements.append(Spacer(1, 1 * mm))

    # ── Signature block ──
    elements.append(Spacer(1, 12 * mm))
    sig_data = [
        ["Data: ____________________", "", "Firma del Perito: ____________________"],
    ]
    sig_t = Table(sig_data, colWidths=[usable_w * 0.4, usable_w * 0.2, usable_w * 0.4])
    sig_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig_t)

    # ── Footer ──
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        "Documento generato da Norma Facile 2.0 - Perizia Tecnica Estimativa",
        ParagraphStyle("Foot", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    ))

    page_doc.build(elements)
    buffer.seek(0)
    return buffer

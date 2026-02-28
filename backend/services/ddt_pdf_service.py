"""PDF service for DDT (Documento di Trasporto)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT = colors.HexColor("#F8FAFC")

DDT_TYPE_TITLES = {
    "vendita": "DOCUMENTO DI TRASPORTO",
    "conto_lavoro": "DDT CONTO LAVORO",
    "rientro_conto_lavoro": "DDT RIENTRO CONTO LAVORO",
}


def generate_ddt_pdf(doc: dict, company: dict = None) -> BytesIO:
    company = company or {}
    buffer = BytesIO()
    page_doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    usable_w = A4[0] - 24 * mm
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=14, textColor=DARK, spaceAfter=2 * mm)
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    section = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=10, textColor=BLUE, spaceBefore=4 * mm, spaceAfter=2 * mm)
    small = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8)

    elements = []

    # ── Logo ──
    logo_url = company.get('logo_url', '')
    if logo_url and logo_url.startswith('data:image'):
        try:
            import base64
            header_part, b64_data = logo_url.split(',', 1)
            img_bytes = base64.b64decode(b64_data)
            logo_buf = BytesIO(img_bytes)
            logo_img = Image(logo_buf, width=40 * mm, height=15 * mm)
            logo_img.hAlign = 'LEFT'
            elements.append(logo_img)
            elements.append(Spacer(1, 3 * mm))
        except Exception as e:
            logger.warning(f"Could not render logo in DDT: {e}")

    # ── Header ──
    ddt_type = doc.get("ddt_type", "vendita")
    title_text = DDT_TYPE_TITLES.get(ddt_type, "DOCUMENTO DI TRASPORTO")
    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(
        f"N. {doc.get('number', '-')} &nbsp;|&nbsp; Data: {doc.get('data_ora_trasporto', '-')} &nbsp;|&nbsp; "
        f"Cliente: {doc.get('client_name', '-')}",
        sub_style,
    ))
    elements.append(Spacer(1, 3 * mm))

    # ── Destinazione ──
    dest = doc.get("destinazione", {})
    if dest and dest.get("ragione_sociale"):
        dest_data = [
            ["Destinazione Merce:", ""],
            ["Rag. Sociale:", dest.get("ragione_sociale", "")],
            ["Indirizzo:", dest.get("indirizzo", "")],
            ["Località:", f"{dest.get('cap', '')} {dest.get('localita', '')} ({dest.get('provincia', '')})"],
        ]
        dt = Table(dest_data, colWidths=[28 * mm, usable_w - 28 * mm])
        dt.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (0, -1), BLUE),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        elements.append(dt)
        elements.append(Spacer(1, 2 * mm))

    # ── Transport Info ──
    transport_data = [
        ["Causale:", doc.get("causale_trasporto", "-"), "Porto:", doc.get("porto", "-")],
        ["Vettore:", doc.get("vettore", "-"), "Mezzo:", doc.get("mezzo_trasporto", "-")],
        ["Colli:", str(doc.get("num_colli", 0)), "Peso Lordo:", f"{doc.get('peso_lordo_kg', 0)} kg"],
        ["Aspetto:", doc.get("aspetto_beni", "-"), "Peso Netto:", f"{doc.get('peso_netto_kg', 0)} kg"],
    ]
    tt = Table(transport_data, colWidths=[20 * mm, (usable_w - 40 * mm) / 2, 22 * mm, (usable_w - 40 * mm) / 2])
    tt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.9, 0.9, 0.9)),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 3 * mm))

    # ── Lines Table ──
    lines = doc.get("lines", [])
    show_prices = doc.get("stampa_prezzi", True)

    if show_prices:
        header = ["#", "Cod.", "Descrizione", "UdM", "Q.tà", "Prezzo", "Sc.%", "Totale", "IVA"]
        cw = [8 * mm, 18 * mm, usable_w - 120 * mm, 12 * mm, 14 * mm, 20 * mm, 14 * mm, 22 * mm, 12 * mm]
    else:
        header = ["#", "Cod.", "Descrizione", "UdM", "Q.tà"]
        cw = [10 * mm, 25 * mm, usable_w - 65 * mm, 15 * mm, 15 * mm]

    line_data = [header]
    for i, line in enumerate(lines):
        s1 = float(line.get("sconto_1", 0))
        s2 = float(line.get("sconto_2", 0))
        sc_str = ""
        if s1:
            sc_str = f"{s1}"
        if s2:
            sc_str += f"+{s2}" if sc_str else f"{s2}"

        row = [
            str(i + 1),
            line.get("codice_articolo", ""),
            Paragraph(line.get("description", ""), small),
            line.get("unit", "pz"),
            f"{float(line.get('quantity', 0)):.1f}",
        ]
        if show_prices:
            row.extend([
                f"{float(line.get('unit_price', 0)):.2f}",
                sc_str or "-",
                f"{float(line.get('line_total', 0)):.2f}",
                f"{line.get('vat_rate', '22')}%",
            ])
        line_data.append(row)

    lt = Table(line_data, colWidths=cw, repeatRows=1)
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.85, 0.85, 0.85)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(lt)

    # ── Totals ──
    if show_prices:
        elements.append(Spacer(1, 3 * mm))
        totals = doc.get("totals", {})
        tot_data = [
            ["Imponibile:", f"{totals.get('imponibile', 0):.2f} EUR"],
            ["Totale IVA:", f"{totals.get('total_vat', 0):.2f} EUR"],
            ["TOTALE:", f"{totals.get('total', 0):.2f} EUR"],
        ]
        if totals.get("acconto", 0) > 0:
            tot_data.append(["Acconto:", f"-{totals.get('acconto', 0):.2f} EUR"])
            tot_data.append(["Da Pagare:", f"{totals.get('da_pagare', 0):.2f} EUR"])

        tot_t = Table(tot_data, colWidths=[usable_w - 45 * mm, 45 * mm])
        tot_t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 11),
            ("TEXTCOLOR", (1, 2), (1, 2), BLUE),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(tot_t)

    # ── Notes ──
    if doc.get("notes"):
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph("Note:", section))
        elements.append(Paragraph(doc["notes"], small))

    # ── Condizioni di Vendita ──
    condizioni = company.get('condizioni_vendita', '')
    if condizioni:
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph("CONDIZIONI DI VENDITA", section))
        for line in condizioni.split('\n'):
            if line.strip():
                elements.append(Paragraph(line.strip(), small))

    # ── Footer ──
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        "Generato da Norma Facile 2.0",
        ParagraphStyle("Foot", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    ))

    page_doc.build(elements)
    buffer.seek(0)
    return buffer

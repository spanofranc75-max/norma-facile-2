"""Generatore PDF Foglio Lavoro per commessa.

Produce un PDF stampabile con:
- Intestazione aziendale
- Info commessa (numero, cliente, descrizione)
- QR code che porta al modulo Registra Lavoro
- Tabella fasi di produzione con righe vuote compilabili a mano
- Spazio firma e note
"""
import io
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Standard production phases
FASI_STANDARD = [
    "Taglio",
    "Foratura",
    "Piegatura",
    "Saldatura",
    "Molatura",
    "Sabbiatura",
    "Verniciatura",
    "Zincatura",
    "Pre-montaggio",
    "Montaggio",
    "Controllo qualità",
]

RIGHE_PER_FASE = 3  # Multiple rows per phase (for multi-day work)


def _make_qr(url: str, size: int = 120) -> Image:
    """Generate a QR code image for ReportLab."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size, height=size)


def generate_foglio_lavoro(commessa: dict, company: dict, app_base_url: str) -> bytes:
    """Generate the Foglio Lavoro PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FLTitle", parent=styles["Heading1"],
        fontSize=16, alignment=TA_CENTER, spaceAfter=2 * mm,
    )
    subtitle_style = ParagraphStyle(
        "FLSubtitle", parent=styles["Normal"],
        fontSize=10, alignment=TA_CENTER, textColor=colors.grey,
    )
    info_style = ParagraphStyle(
        "FLInfo", parent=styles["Normal"],
        fontSize=10, spaceAfter=1 * mm,
    )
    small_style = ParagraphStyle(
        "FLSmall", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey,
    )

    elements = []

    # --- HEADER: Company + QR Code ---
    ragione = company.get("ragione_sociale", company.get("nome_azienda", ""))
    commessa_id = commessa.get("commessa_id", "")
    numero = commessa.get("numero", commessa_id)

    # QR code pointing to Registra Lavoro (not commessa detail for privacy)
    qr_url = f"{app_base_url}/commesse/{commessa_id}?tab=produzione"
    qr_img = _make_qr(qr_url, size=80)

    header_data = [
        [
            Paragraph(f"<b>{ragione}</b>", info_style),
            qr_img,
        ],
        [
            Paragraph(f"Commessa: <b>{numero}</b>", info_style),
            "",
        ],
    ]
    header_table = Table(header_data, colWidths=[140 * mm, 40 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (1, 0), (1, 1)),
        ("ALIGN", (1, 0), (1, 1), "RIGHT"),
    ]))
    elements.append(header_table)

    # --- TITLE ---
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("FOGLIO LAVORO", title_style))
    elements.append(Paragraph(f"Commessa {numero}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # --- COMMESSA INFO ---
    client_name = commessa.get("client_name", "")
    oggetto = commessa.get("oggetto", commessa.get("description", commessa.get("title", "")))

    info_data = [
        ["Cliente:", client_name],
        ["Descrizione:", oggetto[:120] if oggetto else ""],
        ["Normativa:", commessa.get("normativa_tipo", "")],
        ["Classe:", commessa.get("classe_esecuzione", "")],
    ]
    info_table = Table(info_data, colWidths=[30 * mm, 150 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5 * mm))

    # --- PRODUCTION PHASES TABLE ---
    elements.append(Paragraph("<b>REGISTRO FASI DI PRODUZIONE</b>", info_style))
    elements.append(Spacer(1, 3 * mm))

    # Header row
    col_widths = [35 * mm, 35 * mm, 22 * mm, 15 * mm, 73 * mm]
    table_data = [["Fase", "Operatore", "Data", "Ore", "Note"]]

    # Build rows: each phase gets RIGHE_PER_FASE rows
    for fase in FASI_STANDARD:
        for i in range(RIGHE_PER_FASE):
            if i == 0:
                table_data.append([fase, "", "__/__/____", "", ""])
            else:
                table_data.append(["", "", "__/__/____", "", ""])

    phase_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    phase_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHTS", (0, 1), (-1, -1), 8 * mm),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        # Alternating colors for phase groups
        ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor("#AAAAAA")),
    ]))

    # Color alternating phase groups
    row = 1
    for idx, _ in enumerate(FASI_STANDARD):
        bg = colors.HexColor("#F8F9FA") if idx % 2 == 0 else colors.white
        for r in range(RIGHE_PER_FASE):
            phase_table.setStyle(TableStyle([
                ("BACKGROUND", (0, row), (-1, row), bg),
            ]))
            row += 1

    elements.append(phase_table)

    # --- FOOTER: Signature + Notes ---
    elements.append(Spacer(1, 8 * mm))

    footer_data = [
        [
            Paragraph("<b>Note generali:</b>", info_style),
            "",
            Paragraph("<b>Firma responsabile:</b>", info_style),
        ],
        ["", "", ""],
        ["", "", "________________________"],
    ]
    footer_table = Table(footer_data, colWidths=[80 * mm, 20 * mm, 80 * mm])
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWHEIGHTS", (0, 1), (-1, 1), 15 * mm),
        ("LINEBELOW", (0, 0), (0, 1), 0.5, colors.HexColor("#DDDDDD")),
        ("ALIGN", (2, 2), (2, 2), "CENTER"),
    ]))
    elements.append(footer_table)

    # QR code explanation
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(
        "Scansiona il QR code con il telefono per registrare le ore direttamente nell'app.",
        small_style
    ))

    doc.build(elements)
    return buf.getvalue()

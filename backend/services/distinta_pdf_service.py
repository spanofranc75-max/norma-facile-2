"""PDF service for Distinta Materiali - Lista Taglio (Cutting List)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime


BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT_BLUE = colors.HexColor("#EFF6FF")


def generate_cutting_list_pdf(distinta: dict, bar_results: list = None) -> BytesIO:
    """Generate a cutting list PDF for the workshop."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, textColor=DARK, spaceAfter=4 * mm)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, textColor=BLUE, spaceBefore=6 * mm, spaceAfter=3 * mm)
    normal = ParagraphStyle("Norm", parent=styles["Normal"], fontSize=9)

    elements = []

    # Header
    elements.append(Paragraph("LISTA TAGLIO", title_style))
    elements.append(Paragraph(f"Distinta: {distinta.get('name', '-')}", subtitle_style))
    elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", subtitle_style))
    elements.append(Spacer(1, 6 * mm))

    # Main cutting table
    items = distinta.get("items", [])
    if items:
        elements.append(Paragraph("Dettaglio Tagli", section_style))

        header = ["#", "Profilo", "Lunghezza (mm)", "Q.ta", "Peso Riga (kg)", "Superficie (mq)"]
        data = [header]

        for i, item in enumerate(items, 1):
            length_mm = item.get("length_mm", 0)
            qty = item.get("quantity", 1)
            data.append([
                str(i),
                item.get("profile_label", item.get("name", "-")),
                f"{length_mm:.0f}",
                f"{qty:.0f}",
                f"{item.get('total_weight', 0):.2f}",
                f"{item.get('total_surface', 0):.3f}",
            ])

        # Totals row
        totals = distinta.get("totals", {})
        data.append([
            "", "TOTALE", "", "",
            f"{totals.get('total_weight_kg', 0):.2f}",
            f"{totals.get('total_surface_mq', 0):.3f}",
        ])

        col_widths = [8 * mm, 65 * mm, 30 * mm, 15 * mm, 28 * mm, 28 * mm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BLUE]),
            ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BLUE),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)

    # Bar optimization section
    if bar_results:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("Calcolo Barre (6m)", section_style))

        bar_header = ["Profilo", "Lung. Tot. (m)", "Barre da 6m", "Sfrido (mm)", "Sfrido (%)"]
        bar_data = [bar_header]

        for br in bar_results:
            bar_data.append([
                br["profile_label"],
                f"{br['total_length_m']:.2f}",
                str(br["bars_needed"]),
                f"{br['waste_mm']:.0f}",
                f"{br['waste_percent']:.1f}%",
            ])

        col_widths_b = [65 * mm, 28 * mm, 25 * mm, 25 * mm, 22 * mm]
        tb = Table(bar_data, colWidths=col_widths_b, repeatRows=1)
        tb.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(tb)

    # Footer summary
    elements.append(Spacer(1, 10 * mm))
    totals = distinta.get("totals", {})
    summary_data = [
        ["Peso Totale:", f"{totals.get('total_weight_kg', 0):.2f} kg"],
        ["Superficie Totale:", f"{totals.get('total_surface_mq', 0):.3f} mq"],
        ["N. Articoli:", str(totals.get("total_items", 0))],
    ]
    st = Table(summary_data, colWidths=[40 * mm, 40 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (1, 0), (1, -1), BLUE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(st)

    doc.build(elements)
    buffer.seek(0)
    return buffer

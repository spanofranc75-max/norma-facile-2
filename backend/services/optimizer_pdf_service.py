"""PDF service for Ottimizzatore di Taglio — Scheda Taglio Ottimizzata."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect, String
from io import BytesIO
from datetime import datetime


BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#16A34A")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D97706")

# Colors for bar visualization
BAR_BG = colors.HexColor("#E2E8F0")
CUT_COLORS = [
    colors.HexColor("#3B82F6"),
    colors.HexColor("#10B981"),
    colors.HexColor("#F59E0B"),
    colors.HexColor("#EF4444"),
    colors.HexColor("#8B5CF6"),
    colors.HexColor("#EC4899"),
    colors.HexColor("#06B6D4"),
    colors.HexColor("#84CC16"),
]


def generate_optimizer_pdf(distinta: dict, optimizer_result: dict) -> BytesIO:
    """Generate the optimized cutting plan PDF."""
    buffer = BytesIO()
    page_w = A4[0]
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    usable_w = page_w - 24 * mm

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=16, textColor=DARK, spaceAfter=2 * mm,
    )
    subtitle_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=10, textColor=colors.grey,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontSize=12, textColor=BLUE, spaceBefore=5 * mm, spaceAfter=2 * mm,
    )
    small = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=8,
    )

    elements = []

    # ── Header ──
    elements.append(Paragraph("SCHEDA TAGLIO OTTIMIZZATA", title_style))
    elements.append(Paragraph(
        f"Distinta: {distinta.get('name', '-')} &nbsp;|&nbsp; "
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;|&nbsp; "
        f"Barra: {optimizer_result.get('bar_length_mm', 6000)} mm &nbsp;|&nbsp; "
        f"Lama: {optimizer_result.get('kerf_mm', 3)} mm",
        subtitle_style,
    ))
    elements.append(Spacer(1, 4 * mm))

    # ── Summary Box ──
    summary = optimizer_result.get("summary", {})
    summary_data = [
        ["Barre Totali", "Tagli Totali", "Utilizzato (m)", "Sfrido (m)", "Sfrido (%)"],
        [
            str(summary.get("total_bars", 0)),
            str(summary.get("total_cuts", 0)),
            f"{summary.get('total_used_mm', 0) / 1000:.2f}",
            f"{summary.get('total_waste_mm', 0) / 1000:.2f}",
            f"{summary.get('waste_percent', 0):.1f}%",
        ],
    ]
    cw = usable_w / 5
    st = Table(summary_data, colWidths=[cw] * 5)
    waste_pct = summary.get("waste_percent", 0)
    waste_color = GREEN if waste_pct < 10 else (AMBER if waste_pct < 20 else RED)
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("TEXTCOLOR", (0, 1), (0, 1), BLUE),
        ("TEXTCOLOR", (4, 1), (4, 1), waste_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 5 * mm))

    # ── Per-Profile Sections ──
    for profile in optimizer_result.get("profiles", []):
        section_elements = []
        section_elements.append(Paragraph(
            f"{profile['profile_label']} — "
            f"{profile['bars_needed']} barre, "
            f"{profile['total_cuts']} tagli, "
            f"sfrido {profile['waste_percent']:.1f}%",
            section_style,
        ))

        # Table of bars
        bar_header = ["Barra #", "Tagli (mm)", "Usato", "Sfrido", "%"]
        bar_data = [bar_header]
        for bar in profile.get("bars", []):
            cuts_str = ", ".join(f"{c['length_mm']:.0f}" for c in bar["cuts"])
            bar_data.append([
                str(bar["bar_index"]),
                Paragraph(cuts_str, small),
                f"{bar['used_mm']:.0f} mm",
                f"{bar['waste_mm']:.0f} mm",
                f"{bar['waste_percent']:.1f}%",
            ])

        bcw = [14 * mm, usable_w - 14 * mm - 22 * mm - 22 * mm - 16 * mm, 22 * mm, 22 * mm, 16 * mm]
        bt = Table(bar_data, colWidths=bcw, repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.85, 0.85, 0.85)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        section_elements.append(bt)

        # Visual bar drawings (max 8 bars per profile to save space)
        bars_to_draw = profile.get("bars", [])[:8]
        if bars_to_draw:
            section_elements.append(Spacer(1, 2 * mm))
            drawing_h = len(bars_to_draw) * 14 + 4
            bar_drawing_w = float(usable_w)
            d = Drawing(bar_drawing_w, drawing_h)
            scale = (bar_drawing_w - 30) / profile.get("bar_length_mm", 6000)

            for bi, bar in enumerate(bars_to_draw):
                y = drawing_h - (bi + 1) * 14 + 2
                # Bar background
                d.add(Rect(25, y, bar_drawing_w - 30, 10, fillColor=BAR_BG, strokeColor=colors.Color(0.7, 0.7, 0.7), strokeWidth=0.3))
                # Bar label
                d.add(String(2, y + 2, f"B{bar['bar_index']}", fontSize=6, fillColor=DARK))
                # Cuts
                for ci, cut in enumerate(bar["cuts"]):
                    cx = 25 + cut["offset_mm"] * scale
                    cw = cut["length_mm"] * scale
                    fill = CUT_COLORS[ci % len(CUT_COLORS)]
                    d.add(Rect(cx, y + 1, max(cw, 1), 8, fillColor=fill, strokeColor=colors.white, strokeWidth=0.3))
                    if cw > 18:
                        d.add(String(cx + 2, y + 2.5, f"{cut['length_mm']:.0f}", fontSize=5, fillColor=colors.white))

            section_elements.append(d)

        elements.append(KeepTogether(section_elements))

    # ── Footer ──
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        "Generato da Norma Facile 2.0 — Ottimizzatore di Taglio Avanzato",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer

"""Professional Invoice PDF generator — ReportLab, Blue Professional theme.

Style: clean minimal, reference Fattura 7/2026.
- Logo left, company details right, single navy divider
- Client box: white bg with left blue accent bar
- Items table: navy header, white rows, subtle gray borders
- Totals: white subtotals, navy grand total only
- Payment: plain text, no colored box
- No red banner — due date in payment section
"""
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.platypus.flowables import PageBreak

# ── Color Palette ──
COL_NAVY        = colors.HexColor("#1E3A5F")
COL_ACCENT      = colors.HexColor("#0055FF")
COL_ACCENT_DARK = colors.HexColor("#1E3A5F")
COL_DARK        = colors.HexColor("#1a1a2e")
COL_GRAY        = colors.HexColor("#64748b")
COL_BORDER      = colors.HexColor("#CBD5E1")
COL_ROW_BORDER  = colors.HexColor("#E2E8F0")
COL_WHITE       = colors.white

DOC_TYPE_NAMES = {
    "FT": "FATTURA",
    "PRV": "PREVENTIVO",
    "DDT": "DOCUMENTO DI TRASPORTO",
    "NC": "NOTA DI CREDITO",
}

PAYMENT_METHOD_NAMES = {
    "bonifico": "Bonifico Bancario",
    "contanti": "Contanti",
    "carta": "Carta di Credito",
    "assegno": "Assegno",
    "riba": "RiBa",
    "altro": "Altro",
}

PAGE_W = A4[0] - 32*mm


def _fmt(n) -> str:
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _s(val) -> str:
    return str(val or "")


def _date(d) -> str:
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            return d
    return ""


def _styles():
    S = {}
    S['company_name'] = ParagraphStyle(
        'company_name', fontSize=13, fontName='Helvetica-Bold',
        textColor=COL_ACCENT_DARK, alignment=TA_RIGHT, spaceAfter=2
    )
    S['company_detail'] = ParagraphStyle(
        'company_detail', fontSize=8, fontName='Helvetica',
        textColor=COL_GRAY, alignment=TA_RIGHT, leading=13
    )
    S['doc_type'] = ParagraphStyle(
        'doc_type', fontSize=8, fontName='Helvetica-Bold',
        textColor=COL_ACCENT, spaceAfter=1, leading=10
    )
    S['doc_number'] = ParagraphStyle(
        'doc_number', fontSize=26, fontName='Helvetica-Bold',
        textColor=COL_ACCENT_DARK, spaceAfter=2, leading=30
    )
    S['meta_label'] = ParagraphStyle(
        'meta_label', fontSize=8, fontName='Helvetica-Bold',
        textColor=COL_GRAY, alignment=TA_RIGHT, leading=14
    )
    S['meta_value'] = ParagraphStyle(
        'meta_value', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT, leading=14
    )
    S['client_label'] = ParagraphStyle(
        'client_label', fontSize=7, fontName='Helvetica-Bold',
        textColor=COL_ACCENT, spaceAfter=2, leading=10
    )
    S['client_name'] = ParagraphStyle(
        'client_name', fontSize=11, fontName='Helvetica-Bold',
        textColor=COL_ACCENT_DARK, spaceAfter=2
    )
    S['client_detail'] = ParagraphStyle(
        'client_detail', fontSize=8, fontName='Helvetica',
        textColor=colors.HexColor("#475569"), leading=13
    )
    S['th'] = ParagraphStyle(
        'th', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_WHITE, alignment=TA_LEFT
    )
    S['th_r'] = ParagraphStyle(
        'th_r', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_WHITE, alignment=TA_RIGHT
    )
    S['th_c'] = ParagraphStyle(
        'th_c', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_WHITE, alignment=TA_CENTER
    )
    S['td'] = ParagraphStyle(
        'td', fontSize=8.5, fontName='Helvetica',
        textColor=COL_DARK, leading=12
    )
    S['td_r'] = ParagraphStyle(
        'td_r', fontSize=8.5, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT, leading=12
    )
    S['td_c'] = ParagraphStyle(
        'td_c', fontSize=8.5, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_CENTER, leading=12
    )
    S['total_label'] = ParagraphStyle(
        'total_label', fontSize=8.5, fontName='Helvetica',
        textColor=COL_GRAY, alignment=TA_RIGHT
    )
    S['total_value'] = ParagraphStyle(
        'total_value', fontSize=8.5, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT
    )
    S['grand_label'] = ParagraphStyle(
        'grand_label', fontSize=11, fontName='Helvetica-Bold',
        textColor=COL_WHITE
    )
    S['grand_value'] = ParagraphStyle(
        'grand_value', fontSize=13, fontName='Helvetica-Bold',
        textColor=COL_WHITE, alignment=TA_RIGHT
    )
    S['payment_title'] = ParagraphStyle(
        'payment_title', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_ACCENT, spaceAfter=4
    )
    S['payment_detail'] = ParagraphStyle(
        'payment_detail', fontSize=8.5, fontName='Helvetica',
        textColor=colors.HexColor("#334155"), leading=15
    )
    S['notes_title'] = ParagraphStyle(
        'notes_title', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_ACCENT, spaceAfter=2
    )
    S['notes_text'] = ParagraphStyle(
        'notes_text', fontSize=8.5, fontName='Helvetica',
        textColor=colors.HexColor("#475569"), leading=13
    )
    S['legal'] = ParagraphStyle(
        'legal', fontSize=6.5, fontName='Helvetica',
        textColor=COL_GRAY, leading=10
    )
    S['reg_footer'] = ParagraphStyle(
        'reg_footer', fontSize=7.5, fontName='Helvetica-Bold',
        textColor=COL_ACCENT, alignment=TA_CENTER
    )
    return S


def generate_modern_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16*mm, rightMargin=16*mm,
        topMargin=14*mm, bottomMargin=16*mm,
    )

    S = _styles()
    co = company or {}
    cl = client or {}
    story = []

    # ── HEADER: logo left, company right ──
    company_name = _s(co.get("business_name"))
    addr = _s(co.get("address"))
    cap = _s(co.get("cap"))
    city = _s(co.get("city"))
    prov = _s(co.get("province"))
    piva = _s(co.get("partita_iva"))
    cf = _s(co.get("codice_fiscale"))
    phone = _s(co.get("phone") or co.get("tel"))
    email = _s(co.get("email") or co.get("contact_email"))

    addr_parts = []
    if addr: addr_parts.append(addr)
    loc = " ".join(p for p in [cap, city, f"({prov})" if prov else ""] if p)
    if loc: addr_parts.append(loc)
    if piva: addr_parts.append(f"P.IVA {piva}")
    if cf and cf != piva: addr_parts.append(f"C.F. {cf}")
    if phone: addr_parts.append(f"Tel: {phone}")
    if email: addr_parts.append(email)

    logo_cell = Spacer(1, 1)
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        try:
            import base64
            from reportlab.platypus import Image as RLImage
            from io import BytesIO as BIO
            parts = logo_url.split(",", 1)
            if len(parts) == 2:
                img_data = base64.b64decode(parts[1])
                logo_cell = RLImage(BIO(img_data), width=50*mm, height=20*mm, kind='proportional')
        except Exception:
            pass

    company_right = Table([
        [Paragraph(company_name, S['company_name'])],
        [Paragraph("<br/>".join(addr_parts), S['company_detail'])],
    ], colWidths=[90*mm], style=TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    header_table = Table([[logo_cell, company_right]], colWidths=[80*mm, 90*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4*mm))

    # Single clean navy divider
    story.append(HRFlowable(width="100%", thickness=2, color=COL_NAVY, spaceAfter=4*mm))

    # ── TITLE ROW ──
    doc_type = invoice.get("document_type", "FT")
    doc_title = DOC_TYPE_NAMES.get(doc_type, "DOCUMENTO")
    doc_number = _s(invoice.get("document_number", ""))
    display_num = doc_number.replace("FT-", "").replace("NC-", "")
    issue_date = _date(invoice.get("issue_date", ""))
    due_date = invoice.get("due_date")
    payment_label = invoice.get("payment_terms") or PAYMENT_METHOD_NAMES.get(
        invoice.get("payment_method", ""), invoice.get("payment_method", "")
    )

    meta_rows = [
        [Paragraph("Data:", S['meta_label']), Paragraph(issue_date, S['meta_value'])],
        [Paragraph("Pagamento:", S['meta_label']), Paragraph(_s(payment_label), S['meta_value'])],
    ]
    if due_date:
        meta_rows.append([
            Paragraph("Scadenza:", S['meta_label']),
            Paragraph(_date(due_date), S['meta_value']),
        ])

    title_left = Table([
        [Paragraph(doc_title, S['doc_type'])],
        [Paragraph(display_num, S['doc_number'])],
    ], colWidths=[80*mm], style=TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    meta_right = Table(meta_rows, colWidths=[32*mm, 58*mm], style=TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    title_row = Table([[title_left, meta_right]], colWidths=[80*mm, 90*mm])
    title_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(title_row)
    story.append(Spacer(1, 5*mm))

    # ── CLIENT BOX: white bg, left blue accent bar ──
    cl_name = _s(cl.get("business_name"))
    cl_parts = []
    cl_addr = _s(cl.get("address"))
    cl_cap = _s(cl.get("cap"))
    cl_city = _s(cl.get("city"))
    cl_prov = _s(cl.get("province"))
    if cl_addr: cl_parts.append(cl_addr)
    loc2 = " ".join(p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p)
    if loc2: cl_parts.append(loc2)
    cl_piva = _s(cl.get("partita_iva"))
    cl_cf = _s(cl.get("codice_fiscale"))
    cl_sdi = _s(cl.get("codice_sdi"))
    cl_pec = _s(cl.get("pec"))
    if cl_piva: cl_parts.append(f"P.IVA {cl_piva}")
    if cl_cf: cl_parts.append(f"C.F. {cl_cf}")
    if cl_sdi: cl_parts.append(f"Cod. SDI {cl_sdi}")
    if cl_pec: cl_parts.append(f"PEC {cl_pec}")

    accent_bar = Table([['']], colWidths=[3*mm], style=TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COL_ACCENT),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    client_inner = Table([
        [Paragraph("SPETTABILE CLIENTE", S['client_label'])],
        [Paragraph(cl_name, S['client_name'])],
        [Paragraph("<br/>".join(cl_parts), S['client_detail'])],
    ], colWidths=[PAGE_W - 5*mm], style=TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COL_WHITE),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (0,0), 6),
        ('TOPPADDING', (0,1), (-1,-1), 2),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-2), 1),
    ]))

    client_table = Table([[accent_bar, client_inner]], colWidths=[3*mm, PAGE_W - 3*mm])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('BOX', (0,0), (-1,-1), 0.5, COL_BORDER),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 5*mm))

    # ── ITEMS TABLE ──
    lines = invoice.get("lines", [])

    table_data = [[
        Paragraph("Descrizione", S['th']),
        Paragraph("Q.tà", S['th_r']),
        Paragraph("Prezzo Unit.", S['th_r']),
        Paragraph("Sconto", S['th_c']),
        Paragraph("IVA", S['th_c']),
        Paragraph("Importo", S['th_r']),
    ]]

    for i, ln in enumerate(lines):
        desc = _s(ln.get("description") or "").replace("\n", "<br/>")
        qty = _fmt(ln.get("quantity", 0))
        price = _fmt(ln.get("unit_price", 0))
        disc = float(ln.get("discount_percent") or ln.get("sconto_1") or 0)
        disc2 = float(ln.get("sconto_2") or 0)
        disc_str = f"{_fmt(disc)}%" if disc > 0 else ""
        if disc2 > 0:
            disc_str += f" + {_fmt(disc2)}%" if disc_str else f"{_fmt(disc2)}%"
        vat = _s(str(ln.get("vat_rate", "22")))
        total = _fmt(ln.get("line_total", 0))

        table_data.append([
            Paragraph(desc, S['td']),
            Paragraph(qty, S['td_r']),
            Paragraph(price, S['td_r']),
            Paragraph(disc_str, S['td_c']),
            Paragraph(f"{vat}%", S['td_c']),
            Paragraph(f"<b>{total}</b>", S['td_r']),
        ])

    cw = [PAGE_W*0.44, PAGE_W*0.08, PAGE_W*0.14, PAGE_W*0.10, PAGE_W*0.08, PAGE_W*0.16]
    items_table = Table(table_data, colWidths=cw, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COL_NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), COL_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7.5),
        ('TOPPADDING', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 9),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,1), (-1,-1), COL_WHITE),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, COL_ROW_BORDER),
        ('LINEBELOW', (0,-1), (-1,-1), 2, COL_NAVY),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4*mm))

    # ── NOTES ──
    if invoice.get("notes"):
        notes_table = Table([
            [Paragraph("NOTE", S['notes_title'])],
            [Paragraph(_s(invoice["notes"]).replace("\n", "<br/>"), S['notes_text'])],
        ], colWidths=[PAGE_W], style=TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LINEABOVE', (0,0), (-1,0), 1, COL_BORDER),
            ('LINEBELOW', (0,-1), (-1,-1), 1, COL_BORDER),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 4*mm))

    # ── TOTALS ──
    from services.pdf_template import compute_iva_groups
    iva_data = compute_iva_groups(lines)
    totals = invoice.get("totals", {})
    ritenuta = float(totals.get("ritenuta", 0) or 0)

    subtotals_rows = [
        [Paragraph("Imponibile:", S['total_label']), Paragraph(_fmt(iva_data['imponibile']), S['total_value'])],
    ]
    for rate_str, grp in sorted(iva_data["groups"].items()):
        subtotals_rows.append([
            Paragraph(f"IVA {rate_str}% su {_fmt(grp['base'])}", S['total_label']),
            Paragraph(_fmt(grp['tax']), S['total_value']),
        ])
    subtotals_rows.append([
        Paragraph("Totale IVA:", S['total_label']),
        Paragraph(_fmt(iva_data['total_vat']), S['total_value']),
    ])

    subtotals_table = Table(subtotals_rows, colWidths=[55*mm, 30*mm])
    subtotals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,-1), COL_WHITE),
        ('LINEBELOW', (0,0), (-1,-2), 0.3, COL_ROW_BORDER),
        ('LINEBELOW', (0,-1), (-1,-1), 1, COL_BORDER),
    ]))

    grand_rows = [[
        Paragraph("TOTALE", S['grand_label']),
        Paragraph(f"{_fmt(iva_data['total'])} €", S['grand_value']),
    ]]
    if ritenuta > 0:
        netto = iva_data["total"] - ritenuta
        grand_rows.append([
            Paragraph("Ritenuta d'acconto", S['grand_label']),
            Paragraph(f"-{_fmt(ritenuta)} €", S['grand_value']),
        ])
        grand_rows.append([
            Paragraph("NETTO A PAGARE", S['grand_label']),
            Paragraph(f"{_fmt(netto)} €", S['grand_value']),
        ])

    grand_table = Table(grand_rows, colWidths=[55*mm, 30*mm])
    grand_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COL_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))

    totals_col = Table([
        [subtotals_table],
        [grand_table],
    ], colWidths=[85*mm], style=TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # ── PAYMENT: plain text, no colored box ──
    bank = co.get("bank_details", {}) or {}
    bank_name = _s(bank.get("bank_name", ""))
    bank_iban = _s(bank.get("iban", ""))
    bank_bic = _s(bank.get("bic_swift", ""))
    payment_type_label = _s(invoice.get("payment_type_label", "")) or _s(payment_label)

    payment_lines = []
    if payment_type_label:
        payment_lines.append(f"<b>Condizioni:</b> {payment_type_label}")
    if due_date:
        payment_lines.append(f"<b>Scadenza:</b> {_date(due_date)}")
    if bank_name:
        payment_lines.append(f"<b>Banca:</b> {bank_name}")
    if bank_iban:
        payment_lines.append(f"<b>IBAN:</b> {bank_iban}")
    if bank_bic:
        payment_lines.append(f"<b>BIC/SWIFT:</b> {bank_bic}")

    payment_col = Table([
        [Paragraph("DATI PAGAMENTO", S['payment_title'])],
        [Paragraph("<br/>".join(payment_lines) if payment_lines else "", S['payment_detail'])],
    ], colWidths=[80*mm], style=TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,0), (-1,0), 1, COL_BORDER),
    ]))

    footer_row = Table([[payment_col, Spacer(1,1), totals_col]], colWidths=[80*mm, 5*mm, 85*mm])
    footer_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(footer_row)

    # ── LEGAL FOOTER ──
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COL_BORDER))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph(
        "Condizioni Generali di Vendita: Riserva di proprietà ex art. 1523 C.C. — "
        "Interessi moratori ex D.Lgs 231/02 — Foro competente esclusivo quello della sede legale del venditore.",
        S['legal']
    ))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph(
        "Azienda Certificata EN 1090-1 EXC3  •  ISO 3834-2  •  Centro di Trasformazione Acciaio",
        S['reg_footer']
    ))

    # ── CONDITIONS PAGE (solo Preventivi) ──
    condizioni = co.get("condizioni_vendita", "") or ""
    if condizioni.strip() and doc_type == "PRV":
        story.append(PageBreak())
        story.append(Paragraph("CONDIZIONI GENERALI DI VENDITA", ParagraphStyle(
            'ct', fontSize=11, fontName='Helvetica-Bold',
            textColor=COL_ACCENT_DARK, alignment=TA_CENTER, spaceAfter=8
        )))
        story.append(Paragraph(condizioni.replace("\n", "<br/>"), ParagraphStyle(
            'ctext', fontSize=7.5, fontName='Helvetica', leading=11, alignment=4
        )))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

"""Professional Invoice PDF generator — ReportLab implementation.

Replaces WeasyPrint with ReportLab for zero system-dependency PDF generation.
Layout: header with company info, client section, items table, totals, bank info.
"""
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import PageBreak

# ── Colors ──
COL_DARK = colors.HexColor("#0F172A")
COL_BLUE = colors.HexColor("#0055FF")
COL_GRAY = colors.HexColor("#64748b")
COL_LIGHT = colors.HexColor("#f8fafc")
COL_BORDER = colors.HexColor("#e2e8f0")
COL_RED_BG = colors.HexColor("#fef2f2")
COL_RED = colors.HexColor("#b91c1c")
COL_WHITE = colors.white

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
    base = getSampleStyleSheet()
    styles = {}

    styles['company_name'] = ParagraphStyle(
        'company_name', fontSize=13, fontName='Helvetica-Bold',
        textColor=COL_DARK, alignment=TA_RIGHT, spaceAfter=2
    )
    styles['company_detail'] = ParagraphStyle(
        'company_detail', fontSize=8, fontName='Helvetica',
        textColor=COL_GRAY, alignment=TA_RIGHT, leading=12
    )
    styles['doc_type'] = ParagraphStyle(
        'doc_type', fontSize=8, fontName='Helvetica-Bold',
        textColor=COL_GRAY, spaceAfter=2, leading=10
    )
    styles['doc_number'] = ParagraphStyle(
        'doc_number', fontSize=22, fontName='Helvetica-Bold',
        textColor=COL_DARK, spaceAfter=2, leading=26
    )
    styles['meta_label'] = ParagraphStyle(
        'meta_label', fontSize=8, fontName='Helvetica-Bold',
        textColor=COL_GRAY, alignment=TA_RIGHT, leading=14
    )
    styles['meta_value'] = ParagraphStyle(
        'meta_value', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT, leading=14
    )
    styles['client_label'] = ParagraphStyle(
        'client_label', fontSize=7, fontName='Helvetica-Bold',
        textColor=COL_GRAY, spaceAfter=2
    )
    styles['client_name'] = ParagraphStyle(
        'client_name', fontSize=12, fontName='Helvetica-Bold',
        textColor=COL_DARK, spaceAfter=2
    )
    styles['client_detail'] = ParagraphStyle(
        'client_detail', fontSize=8, fontName='Helvetica',
        textColor=colors.HexColor("#475569"), leading=12
    )
    styles['table_header'] = ParagraphStyle(
        'table_header', fontSize=7, fontName='Helvetica-Bold',
        textColor=COL_WHITE
    )
    styles['table_cell'] = ParagraphStyle(
        'table_cell', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, leading=11
    )
    styles['table_cell_right'] = ParagraphStyle(
        'table_cell_right', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT, leading=11
    )
    styles['table_cell_center'] = ParagraphStyle(
        'table_cell_center', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_CENTER, leading=11
    )
    styles['total_label'] = ParagraphStyle(
        'total_label', fontSize=8, fontName='Helvetica',
        textColor=COL_GRAY, alignment=TA_LEFT
    )
    styles['total_value'] = ParagraphStyle(
        'total_value', fontSize=8, fontName='Helvetica',
        textColor=COL_DARK, alignment=TA_RIGHT
    )
    styles['grand_label'] = ParagraphStyle(
        'grand_label', fontSize=12, fontName='Helvetica-Bold',
        textColor=COL_DARK, alignment=TA_LEFT
    )
    styles['grand_value'] = ParagraphStyle(
        'grand_value', fontSize=14, fontName='Helvetica-Bold',
        textColor=COL_DARK, alignment=TA_RIGHT
    )
    styles['bank_title'] = ParagraphStyle(
        'bank_title', fontSize=7, fontName='Helvetica-Bold',
        textColor=COL_GRAY, spaceAfter=3
    )
    styles['bank_detail'] = ParagraphStyle(
        'bank_detail', fontSize=8, fontName='Helvetica',
        textColor=colors.HexColor("#475569"), leading=13
    )
    styles['notes_title'] = ParagraphStyle(
        'notes_title', fontSize=7, fontName='Helvetica-Bold',
        textColor=COL_GRAY, spaceAfter=2
    )
    styles['notes_text'] = ParagraphStyle(
        'notes_text', fontSize=8, fontName='Helvetica',
        textColor=colors.HexColor("#475569"), leading=12
    )
    styles['legal'] = ParagraphStyle(
        'legal', fontSize=6.5, fontName='Helvetica',
        textColor=COL_GRAY, leading=10
    )
    styles['due_label'] = ParagraphStyle(
        'due_label', fontSize=8, fontName='Helvetica-Bold',
        textColor=COL_RED
    )
    styles['due_value'] = ParagraphStyle(
        'due_value', fontSize=10, fontName='Helvetica-Bold',
        textColor=colors.HexColor("#991b1b")
    )
    return styles


def generate_modern_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
    """Generate a professional invoice PDF using ReportLab."""

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16*mm, rightMargin=16*mm,
        topMargin=14*mm, bottomMargin=16*mm,
    )

    S = _styles()
    co = company or {}
    cl = client or {}
    story = []

    # ── HEADER: Logo left, Company right ──
    company_name = _s(co.get("business_name"))
    addr = _s(co.get("address"))
    cap = _s(co.get("cap"))
    city = _s(co.get("city"))
    prov = _s(co.get("province"))
    piva = _s(co.get("partita_iva"))
    cf = _s(co.get("codice_fiscale"))
    phone = _s(co.get("phone") or co.get("tel"))
    email = _s(co.get("email") or co.get("contact_email"))

    addr_parts = [addr]
    loc = " ".join(p for p in [cap, city, f"({prov})" if prov else ""] if p)
    if loc:
        addr_parts.append(loc)
    if piva:
        addr_parts.append(f"P.IVA {piva}")
    if cf:
        addr_parts.append(f"C.F. {cf}")
    if phone:
        addr_parts.append(f"Tel {phone}")
    if email:
        addr_parts.append(email)

    company_detail_text = "<br/>".join(addr_parts)

    header_data = [[
        Paragraph("", S['company_name']),  # logo placeholder
        Table([
            [Paragraph(company_name, S['company_name'])],
            [Paragraph(company_detail_text, S['company_detail'])],
        ], colWidths=[None], style=TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
    ]]

    # Try to add logo if available
    logo_url = co.get("logo_url", "")
    logo_cell = Paragraph("", S['company_name'])
    if logo_url and logo_url.startswith("data:image"):
        try:
            import base64
            from reportlab.platypus import Image as RLImage
            from io import BytesIO as BIO
            header_data2 = logo_url.split(",", 1)
            if len(header_data2) == 2:
                img_data = base64.b64decode(header_data2[1])
                img_buf = BIO(img_data)
                logo_cell = RLImage(img_buf, width=45*mm, height=18*mm, kind='proportional')
        except Exception:
            pass

    header_table = Table([
        [logo_cell, Table([
            [Paragraph(company_name, S['company_name'])],
            [Paragraph(company_detail_text, S['company_detail'])],
        ], colWidths=[85*mm], style=TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))]
    ], colWidths=[85*mm, 85*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=3, color=COL_DARK))
    story.append(Spacer(1, 4*mm))

    # ── TITLE + META ──
    doc_type = invoice.get("document_type", "FT")
    doc_title = DOC_TYPE_NAMES.get(doc_type, "DOCUMENTO")
    doc_number = _s(invoice.get("document_number", ""))
    display_num = doc_number.replace("FT-", "").replace("NC-", "")
    issue_date = _date(invoice.get("issue_date", ""))
    due_date = invoice.get("due_date")
    payment_label = invoice.get("payment_terms") or PAYMENT_METHOD_NAMES.get(
        invoice.get("payment_method", ""), invoice.get("payment_method", "")
    )

    title_left = Table([
        [Paragraph(doc_title, S['doc_type'])],
        [Paragraph(display_num, S['doc_number'])],
    ], colWidths=[85*mm], style=TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    meta_right = Table([
        [Paragraph("Data:", S['meta_label']), Paragraph(issue_date, S['meta_value'])],
        [Paragraph("Pagamento:", S['meta_label']), Paragraph(_s(payment_label), S['meta_value'])],
    ], colWidths=[30*mm, 55*mm], style=TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    title_row = Table([[title_left, meta_right]], colWidths=[85*mm, 85*mm])
    title_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(title_row)
    story.append(Spacer(1, 4*mm))

    # ── CLIENT ──
    cl_name = _s(cl.get("business_name"))
    cl_addr = _s(cl.get("address"))
    cl_cap = _s(cl.get("cap"))
    cl_city = _s(cl.get("city"))
    cl_prov = _s(cl.get("province"))
    cl_piva = _s(cl.get("partita_iva"))
    cl_cf = _s(cl.get("codice_fiscale"))
    cl_sdi = _s(cl.get("codice_sdi"))
    cl_pec = _s(cl.get("pec"))

    cl_parts = []
    if cl_addr:
        cl_parts.append(cl_addr)
    loc2 = " ".join(p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p)
    if loc2:
        cl_parts.append(loc2)
    if cl_piva:
        cl_parts.append(f"P.IVA {cl_piva}")
    if cl_cf:
        cl_parts.append(f"C.F. {cl_cf}")
    if cl_sdi:
        cl_parts.append(f"Cod. SDI {cl_sdi}")
    if cl_pec:
        cl_parts.append(f"PEC {cl_pec}")

    story.append(Paragraph("SPETTABILE CLIENTE", S['client_label']))
    story.append(Paragraph(cl_name, S['client_name']))
    if cl_parts:
        story.append(Paragraph("<br/>".join(cl_parts), S['client_detail']))
    story.append(Spacer(1, 4*mm))

    # ── ITEMS TABLE ──
    lines = invoice.get("lines", [])
    th = S['table_header']
    tc = S['table_cell']
    tcr = S['table_cell_right']
    tcc = S['table_cell_center']

    table_data = [[
        Paragraph("Descrizione", th),
        Paragraph("Q.tà", th),
        Paragraph("Prezzo Unit.", th),
        Paragraph("Sconto", th),
        Paragraph("IVA", th),
        Paragraph("Importo", th),
    ]]

    for ln in lines:
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
            Paragraph(desc, tc),
            Paragraph(qty, tcr),
            Paragraph(price, tcr),
            Paragraph(disc_str, tcc),
            Paragraph(f"{vat}%", tcc),
            Paragraph(f"<b>{total}</b>", tcr),
        ])

    col_w = [170*0.44*mm, 170*0.08*mm, 170*0.14*mm, 170*0.10*mm, 170*0.08*mm, 170*0.16*mm]
    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0,0), (-1,0), COL_DARK),
        ('TEXTCOLOR', (0,0), (-1,0), COL_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        # Body
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('TOPPADDING', (0,1), (-1,-1), 7),
        ('BOTTOMPADDING', (0,1), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('ALIGN', (3,1), (4,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [COL_WHITE, COL_LIGHT]),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, COL_BORDER),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 3*mm))

    # ── NOTES ──
    if invoice.get("notes"):
        notes_table = Table([
            [Paragraph("NOTE", S['notes_title'])],
            [Paragraph(_s(invoice["notes"]).replace("\n", "<br/>"), S['notes_text'])],
        ], colWidths=[170*mm], style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COL_LIGHT),
            ('BOX', (0,0), (-1,-1), 0.5, COL_BORDER),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 3*mm))

    # ── TOTALS ──
    from services.pdf_template import compute_iva_groups
    iva_data = compute_iva_groups(lines)
    totals = invoice.get("totals", {})
    ritenuta = float(totals.get("ritenuta", 0) or 0)

    totals_rows = [
        [Paragraph("Imponibile:", S['total_label']), Paragraph(_fmt(iva_data['imponibile']), S['total_value'])],
    ]
    for rate_str, grp in sorted(iva_data["groups"].items()):
        totals_rows.append([
            Paragraph(f"IVA {rate_str}% su {_fmt(grp['base'])}", S['total_label']),
            Paragraph(_fmt(grp['tax']), S['total_value']),
        ])
    totals_rows.append([
        Paragraph("Totale IVA:", S['total_label']),
        Paragraph(_fmt(iva_data['total_vat']), S['total_value']),
    ])
    totals_rows.append([
        Paragraph("TOTALE", S['grand_label']),
        Paragraph(f"{_fmt(iva_data['total'])} €", S['grand_value']),
    ])
    if ritenuta > 0:
        netto = iva_data["total"] - ritenuta
        totals_rows.append([
            Paragraph("Ritenuta d'acconto:", S['total_label']),
            Paragraph(f"-{_fmt(ritenuta)}", S['total_value']),
        ])
        totals_rows.append([
            Paragraph("NETTO A PAGARE:", S['grand_label']),
            Paragraph(f"{_fmt(netto)} €", S['grand_value']),
        ])

    # ── DUE DATE ──
    due_cell_content = [Spacer(1, 1*mm)]
    if due_date:
        due_inner = Table([
            [Paragraph("Scadenza Pagamento:", S['due_label'])],
            [Paragraph(_date(due_date), S['due_value'])],
        ], colWidths=[80*mm], style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COL_RED_BG),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#fca5a5")),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        due_cell_content.append(due_inner)

    # ── BANK INFO ──
    bank = co.get("bank_details", {}) or {}
    bank_name = _s(bank.get("bank_name", ""))
    bank_iban = _s(bank.get("iban", ""))
    bank_bic = _s(bank.get("bic_swift", ""))
    payment_type_label = _s(invoice.get("payment_type_label", "")) or _s(payment_label)

    bank_lines = [f"<b>Condizioni:</b> {payment_type_label}"]
    if bank_name:
        bank_lines.append(f"<b>Banca:</b> {bank_name}")
    if bank_iban:
        bank_lines.append(f"<b>IBAN:</b> {bank_iban}")
    if bank_bic:
        bank_lines.append(f"<b>BIC/SWIFT:</b> {bank_bic}")

    bank_inner = Table([
        [Paragraph("DATI PAGAMENTO", S['bank_title'])],
        [Paragraph("<br/>".join(bank_lines), S['bank_detail'])],
    ], colWidths=[80*mm], style=TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, COL_BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,0), 0.5, COL_BORDER),
    ]))

    totals_n = len(totals_rows)
    ts = TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0, totals_n-1-(1 if ritenuta > 0 else 0)), (-1, totals_n-1-(1 if ritenuta > 0 else 0)), 2, COL_DARK),
    ])
    # separator before grand total
    sep_idx = 3  # after IVA rows
    ts.add('LINEABOVE', (0, sep_idx), (-1, sep_idx), 0.5, COL_BORDER)

    totals_table = Table(totals_rows, colWidths=[55*mm, 30*mm])
    totals_table.setStyle(ts)

    footer_row = Table([
        [bank_inner, Spacer(1,1), totals_table],
    ], colWidths=[82*mm, 6*mm, 82*mm])
    footer_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(footer_row)

    if due_date:
        story.append(Spacer(1, 2*mm))
        due_inner2 = Table([
            [Paragraph("Scadenza Pagamento:", S['due_label']),
             Paragraph(_date(due_date), S['due_value'])],
        ], colWidths=[55*mm, 115*mm], style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COL_RED_BG),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#fca5a5")),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(due_inner2)

    # ── LEGAL FOOTER ──
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COL_BORDER))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        "Condizioni Generali di Vendita: Riserva di proprietà ex art. 1523 C.C. — "
        "Interessi moratori ex D.Lgs 231/02 — Foro competente esclusivo quello della sede legale del venditore.",
        S['legal']
    ))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        "Azienda Certificata EN 1090-1 EXC2  •  ISO 3834-2  •  Centro di Trasformazione Acciaio",
        ParagraphStyle('reg', fontSize=7, fontName='Helvetica-Bold', textColor=COL_GRAY,
                       alignment=TA_CENTER)
    ))

    # ── CONDITIONS PAGE (solo Preventivi) ──
    condizioni = co.get("condizioni_vendita", "") or ""
    if condizioni.strip() and doc_type == "PRV":
        story.append(PageBreak())
        story.append(Paragraph("CONDIZIONI GENERALI DI VENDITA",
            ParagraphStyle('ct', fontSize=11, fontName='Helvetica-Bold',
                           alignment=TA_CENTER, spaceAfter=8)))
        story.append(Paragraph(condizioni.replace("\n", "<br/>"),
            ParagraphStyle('ctext', fontSize=7.5, fontName='Helvetica',
                           leading=11, alignment=4)))  # justified

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

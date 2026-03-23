"""PDF Invoice/Preventivo generator - parametri esatti Emergent originale.

Layout Fattura 7/2026 (27/02/2026):
- Logo sx, azienda dx
- Linea blu separatrice
- FATTURA N. X/XXXX centrata grande
- DATA FATTURA | TIPO affiancati
- Cliente con bordo sinistro blu
- Tabella articoli: header navy, 5 colonne
- Totali destra con box navy per TOTALE
- Coordinate bancarie bordo blu
- Scadenza pagamenti bordo blu
- Footer doppio
"""
from io import BytesIO
from datetime import datetime, date
import logging
import os
import base64

logger = logging.getLogger(__name__)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = 'Helvetica'
FONT_BOLD    = 'Helvetica-Bold'

_LIBERATION_PATHS = [
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
]
for _p in _LIBERATION_PATHS:
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont('LiberationSans', _p))
            pdfmetrics.registerFont(TTFont('LiberationSans-Bold',
                _p.replace('Regular', 'Bold')))
            FONT_REGULAR = 'LiberationSans'
            FONT_BOLD    = 'LiberationSans-Bold'
            break
        except Exception:
            pass

NAVY        = colors.HexColor('#E8E8E8')   # Header tabella (grigio chiaro)
BLUE        = colors.HexColor('#AAAAAA')   # Bordi/accenti (grigio medio)
GREY_BG     = colors.HexColor('#F7F7F7')   # Sfondo box meta
GREY_TEXT   = colors.HexColor('#888888')   # Testo secondario
GREY_BORDER = colors.HexColor('#D5D5D5')   # Bordi sottili
DARK_TEXT   = colors.HexColor('#555555')   # Testo principale
SEC_TEXT    = colors.HexColor('#777777')   # Testo dettagli
ZEBRA       = colors.HexColor('#F9F9F9')   # Righe alternate
WHITE       = colors.white

LEFT_MARGIN   = 16 * mm
RIGHT_MARGIN  = 16 * mm
TOP_MARGIN    = 14 * mm
BOTTOM_MARGIN = 22 * mm

PAGE_W   = A4[0]
PAGE_H   = A4[1]
USABLE_W = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN

COL_DESC  = USABLE_W * 0.44
COL_QTY   = USABLE_W * 0.10
COL_PRICE = USABLE_W * 0.18
COL_VAT   = USABLE_W * 0.10
COL_TOTAL = USABLE_W * 0.18


def _fmt(n):
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return '0,00'
    s = f'{val:,.2f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def _s(val):
    return str(val or '')


def _date(d):
    if not d:
        return ''
    if isinstance(d, (date, datetime)):
        return d.strftime('%d/%m/%Y')
    try:
        return datetime.fromisoformat(str(d)[:10]).strftime('%d/%m/%Y')
    except Exception:
        return str(d)[:10]


def _load_logo(logo_url):
    if not logo_url:
        return None
    try:
        if logo_url.startswith('data:'):
            b64 = logo_url.split('base64,')[1]
            stream = BytesIO(base64.b64decode(b64))
        else:
            import urllib.request
            with urllib.request.urlopen(logo_url, timeout=5) as r:
                stream = BytesIO(r.read())
        # Ridimensionamento proporzionale
        raw = stream.read()
        stream.seek(0)
        max_w, max_h = 120, 60
        img_w, img_h = max_w, max_h
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.open(BytesIO(raw))
            ow, oh = pil_img.size
            ratio = min(max_w / ow, max_h / oh)
            img_w = ow * ratio
            img_h = oh * ratio
        except Exception:
            pass
        img = Image(stream, width=img_w, height=img_h)
        img.hAlign = 'LEFT'
        return img
    except Exception as e:
        logger.warning(f'Logo load failed: {e}')
        return None


def _sty(**kw):
    base = dict(fontName=FONT_REGULAR, fontSize=8, leading=11,
                textColor=DARK_TEXT, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle('_', **base)


S = {
    'co_name':     _sty(fontName=FONT_BOLD, fontSize=13, leading=16, textColor=DARK_TEXT),
    'co_detail':   _sty(fontSize=7.5, leading=11, textColor=SEC_TEXT),
    'doc_title':   _sty(fontName=FONT_BOLD, fontSize=18, leading=22,
                        textColor=colors.HexColor('#666666'), alignment=TA_CENTER),
    'meta_label':  _sty(fontName=FONT_BOLD, fontSize=7, leading=10, textColor=GREY_TEXT),
    'meta_value':  _sty(fontName=FONT_BOLD, fontSize=9, leading=12, textColor=DARK_TEXT),
    'cl_spett':    _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT),
    'cl_name':     _sty(fontName=FONT_BOLD, fontSize=11, leading=14, textColor=DARK_TEXT),
    'cl_detail':   _sty(fontSize=8, leading=11.5, textColor=SEC_TEXT),
    'th':          _sty(fontName=FONT_BOLD, fontSize=7, leading=9,
                        textColor=colors.HexColor('#666666'), alignment=TA_LEFT),
    'th_c':        _sty(fontName=FONT_BOLD, fontSize=7, leading=9,
                        textColor=colors.HexColor('#666666'), alignment=TA_CENTER),
    'th_r':        _sty(fontName=FONT_BOLD, fontSize=7, leading=9,
                        textColor=colors.HexColor('#666666'), alignment=TA_RIGHT),
    'td':          _sty(fontSize=8, leading=11),
    'td_r':        _sty(fontSize=8, leading=11, alignment=TA_RIGHT),
    'td_c':        _sty(fontSize=8, leading=11, alignment=TA_CENTER),
    'td_b':        _sty(fontName=FONT_BOLD, fontSize=8, leading=11, alignment=TA_RIGHT),
    'tot_label':   _sty(fontSize=8.5, leading=12, textColor=GREY_TEXT),
    'tot_value':   _sty(fontName=FONT_BOLD, fontSize=8.5, leading=12,
                        textColor=DARK_TEXT, alignment=TA_RIGHT),
    'grand_label': _sty(fontName=FONT_BOLD, fontSize=11, leading=14,
                        textColor=colors.HexColor('#555555')),
    'grand_value': _sty(fontName=FONT_BOLD, fontSize=14, leading=17,
                        textColor=colors.HexColor('#555555'), alignment=TA_RIGHT),
    'sec_title':   _sty(fontName=FONT_BOLD, fontSize=7.5, leading=10, textColor=GREY_TEXT),
    'sec_text':    _sty(fontSize=8, leading=11.5, textColor=DARK_TEXT),
    'sec_bold':    _sty(fontName=FONT_BOLD, fontSize=8, leading=11.5, textColor=DARK_TEXT),
    'note':        _sty(fontSize=7.5, leading=10.5, textColor=SEC_TEXT),
}

PAYMENT_METHOD_NAMES = {
    'bonifico': 'Bonifico Bancario', 'contanti': 'Contanti',
    'carta': 'Carta di Credito', 'assegno': 'Assegno',
    'riba': 'RiBa', 'altro': 'Altro',
}

DOC_TYPE_DISPLAY = {
    'FT': 'FATTURA', 'PRV': 'PREVENTIVO',
    'NC': 'NOTA DI CREDITO', 'ND': 'NOTA DI DEBITO',
    'DDT': 'DOCUMENTO DI TRASPORTO',
}


def _box_section(content_rows, title=''):
    rows = []
    if title:
        rows.append([Paragraph(title, S['sec_title'])])
    for row in content_rows:
        rows.append([row if isinstance(row, Paragraph)
                     else Paragraph(_s(row), S['sec_text'])])
    t = Table(rows, colWidths=[USABLE_W - 8 * mm])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBEFORE',    (0, 0), (0, -1),  2.5, BLUE),
        ('BACKGROUND',    (0, 0), (-1, -1), WHITE),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _footer_canvas(canvas, doc):
    canvas.saveState()
    co = getattr(doc, '_company', {}) or {}
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    co_name = co.get('business_name', '') or ''
    cert = co.get('certificazioni') or (
        'Azienda Certificata EN 1090-1 EXC3 • ISO 3834-2 • '
        'Centro di Trasformazione Acciaio'
    )
    page_num = canvas.getPageNumber()
    y_base = BOTTOM_MARGIN - 14 * mm
    canvas.setStrokeColor(GREY_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_MARGIN, y_base + 10 * mm,
                PAGE_W - RIGHT_MARGIN, y_base + 10 * mm)
    canvas.setFont(FONT_REGULAR, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawString(LEFT_MARGIN, y_base + 6 * mm,
                      f'Generato da {co_name} - NormaFacile')
    canvas.drawRightString(PAGE_W - RIGHT_MARGIN, y_base + 6 * mm,
                           f'Documento generato il {now_str}')
    canvas.setFont(FONT_BOLD, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawCentredString(PAGE_W / 2, y_base + 2 * mm, cert)
    canvas.setFont(FONT_REGULAR, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawCentredString(PAGE_W / 2, y_base - 2 * mm,
                             f'Pagina {page_num} di 1')
    canvas.restoreState()


def generate_modern_invoice_pdf(invoice, client, company):
    """Genera PDF fattura/preventivo con layout Emergent originale."""
    inv = invoice or {}
    cl  = client  or {}
    co  = company or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
                            topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN)
    doc._company = co
    doc._invoice = inv
    story = []

    # 1. HEADER — Logo+Azienda a SINISTRA, Cliente a DESTRA (stessa riga)
    logo = _load_logo(co.get('logo_url', ''))
    co_name  = co.get('business_name', '') or ''
    co_addr  = co.get('address', '') or ''
    co_cap   = co.get('cap', '') or ''
    co_city  = co.get('city', '') or ''
    co_prov  = co.get('province', '') or ''
    co_piva  = co.get('partita_iva', '') or ''
    co_cf    = co.get('codice_fiscale', '') or ''
    co_phone = co.get('phone') or co.get('tel', '') or ''
    co_email = co.get('email') or co.get('contact_email', '') or ''
    loc_parts = [p for p in [co_cap, co_city,
                              f'({co_prov})' if co_prov else ''] if p]

    # Colonna sinistra: logo + azienda
    left_col = []
    if logo:
        left_col.append(logo)
        left_col.append(Spacer(1, 2 * mm))
    left_col.append(Paragraph(co_name, S['co_name']))
    if co_addr.strip():
        left_col.append(Paragraph(co_addr, S['co_detail']))
    if loc_parts:
        left_col.append(Paragraph(' '.join(loc_parts), S['co_detail']))
    if co_piva:
        left_col.append(Paragraph(f'P.IVA: {co_piva}', S['co_detail']))
    if co_cf and co_cf != co_piva:
        left_col.append(Paragraph(f'Cod. Fisc.: {co_cf}', S['co_detail']))
    if co_phone:
        left_col.append(Paragraph(f'Tel: {co_phone}', S['co_detail']))
    if co_email:
        left_col.append(Paragraph(f'Email: {co_email}', S['co_detail']))

    # Colonna destra: cliente
    cl_name = cl.get('business_name', '') or ''
    cl_addr = cl.get('address', '') or ''
    cl_cap  = cl.get('cap', '') or ''
    cl_city = cl.get('city', '') or ''
    cl_prov = cl.get('province', '') or ''
    cl_piva = cl.get('partita_iva', '') or ''
    cl_cf   = cl.get('codice_fiscale', '') or ''
    cl_sdi  = cl.get('codice_sdi') or cl.get('codice_destinatario', '') or ''
    cl_pec  = cl.get('pec', '') or ''
    right_col = []
    right_col.append(Paragraph('Spett.le', S['cl_spett']))
    right_col.append(Paragraph(cl_name, S['cl_name']))
    addr_parts = [p for p in [cl_addr, cl_cap, cl_city,
                               f'({cl_prov})' if cl_prov else ''] if p]
    if addr_parts:
        right_col.append(Paragraph(' '.join(addr_parts), S['cl_detail']))
    if cl_piva:
        right_col.append(Paragraph(f'P.IVA {cl_piva}', S['cl_detail']))
    if cl_cf and cl_cf != cl_piva:
        right_col.append(Paragraph(f'C.F. {cl_cf}', S['cl_detail']))
    if cl_sdi:
        right_col.append(Paragraph(f'Cod. SDI {cl_sdi}', S['cl_detail']))
    if cl_pec:
        right_col.append(Paragraph(f'PEC: {cl_pec}', S['cl_detail']))

    hdr = Table([[left_col, right_col]],
                colWidths=[USABLE_W * 0.55, USABLE_W * 0.45])
    hdr.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width=USABLE_W, thickness=1,
                            color=BLUE, spaceAfter=4 * mm))

    # 2. TITOLO
    doc_type  = inv.get('document_type') or inv.get('doc_type', 'FT')
    doc_label = DOC_TYPE_DISPLAY.get(doc_type, 'FATTURA')
    doc_num   = inv.get('document_number') or inv.get('number', '')
    disp_num  = doc_num
    for pfx in ('FT-', 'NC-', 'PRV-', 'DDT-'):
        if disp_num.startswith(pfx):
            disp_num = disp_num[len(pfx):]
            break
    title_text = f'{doc_label} N. {disp_num}' if disp_num else doc_label
    story.append(Paragraph(title_text, S['doc_title']))
    story.append(Spacer(1, 4 * mm))

    # 3. META BOX
    issue_date = _date(inv.get('issue_date') or inv.get('created_at'))
    inv_type   = (inv.get('invoice_type_label') or
                  inv.get('tipo_label') or 'COMPLETA')
    meta = Table([[
        Table([[Paragraph('DATA FATTURA', S['meta_label'])],
               [Paragraph(issue_date, S['meta_value'])]],
              colWidths=[USABLE_W * 0.5 - 2 * mm]),
        Table([[Paragraph('TIPO', S['meta_label'])],
               [Paragraph(_s(inv_type).upper(), S['meta_value'])]],
              colWidths=[USABLE_W * 0.5 - 2 * mm]),
    ]], colWidths=[USABLE_W * 0.5, USABLE_W * 0.5])
    meta.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GREY_BG),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEAFTER',     (0, 0), (0, -1),  0.5, GREY_BORDER),
        ('BOX',           (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(meta)
    story.append(Spacer(1, 4 * mm))

    # 4. (CLIENTE ora nell'header — rimosso da qui)

    # 5. TABELLA ARTICOLI
    lines = inv.get('lines', []) or inv.get('items', []) or []
    table_data = [[
        Paragraph('Descrizione',  S['th']),
        Paragraph('Q.tà',    S['th_c']),
        Paragraph('Prezzo Unit.', S['th_r']),
        Paragraph('IVA',          S['th_c']),
        Paragraph('Totale',       S['th_r']),
    ]]
    for i, ln in enumerate(lines):
        desc  = _s(ln.get('description') or '').replace('\n', '<br/>')
        qty   = _fmt(ln.get('quantity', 0))
        price = _fmt(ln.get('unit_price', 0))
        disc  = float(ln.get('discount_percent') or ln.get('sconto_1') or 0)
        disc2 = float(ln.get('sconto_2') or 0)
        vat_r = ln.get('vat_rate') or ln.get('aliquota_iva') or '22'
        vat_s = (f'{float(vat_r):.0f}%'
                 if str(vat_r).replace('.', '').isdigit() else str(vat_r))
        total = _fmt(ln.get('line_total') or ln.get('total') or
                     float(ln.get('quantity', 1)) * float(ln.get('unit_price', 0)))
        if disc > 0:
            desc += (f"<br/><font size='7' color='#888888'>"
                     f"Sconto {_fmt(disc)}%")
            if disc2 > 0:
                desc += f' + {_fmt(disc2)}%'
            desc += '</font>'
        table_data.append([
            Paragraph(desc,                    S['td']),
            Paragraph(qty,                     S['td_c']),
            Paragraph(f'€ {price}',       S['td_r']),
            Paragraph(vat_s,                   S['td_c']),
            Paragraph(f'€ {total}',       S['td_b']),
        ])
    it = Table(table_data,
               colWidths=[COL_DESC, COL_QTY, COL_PRICE, COL_VAT, COL_TOTAL],
               repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.HexColor('#666666')),
        ('TOPPADDING',    (0, 0), (-1, 0),  6),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ('ALIGN',         (1, 1), (1, -1),  'CENTER'),
        ('ALIGN',         (2, 1), (2, -1),  'RIGHT'),
        ('ALIGN',         (3, 1), (3, -1),  'CENTER'),
        ('ALIGN',         (4, 1), (4, -1),  'RIGHT'),
    ])
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0, i), (-1, i), ZEBRA)
    it.setStyle(ts)
    story.append(it)
    story.append(Spacer(1, 4 * mm))

    # 6. TOTALI
    sconto_globale = float(inv.get('sconto_globale') or 0)
    imponibile = 0.0; total_iva = 0.0
    for ln in lines:
        lt = float(ln.get('line_total') or ln.get('total') or float(ln.get('quantity',1))*float(ln.get('unit_price',0)))
        try: vat_pct = float(str(ln.get('vat_rate') or ln.get('aliquota_iva') or '0').replace('%',''))/100
        except: vat_pct = 0.0
        if sconto_globale > 0: lt = lt*(1-sconto_globale/100)
        imponibile += lt; total_iva += round(lt*vat_pct,2)
    imponibile = round(imponibile,2); total_iva = round(total_iva,2); grand_total = round(imponibile+total_iva,2)
    ritenuta    = float((inv.get('totals') or {}).get('ritenuta', 0) or 0)
    sub_rows = [
        [Paragraph('Imponibile:', S['tot_label']),
         Paragraph(f'€ {_fmt(imponibile)}', S['tot_value'])],
        [Paragraph('IVA:', S['tot_label']),
         Paragraph(f'€ {_fmt(total_iva)}', S['tot_value'])],
    ]
    if ritenuta > 0:
        netto = grand_total - ritenuta
        sub_rows.append([
            Paragraph("Ritenuta d'acconto:", S['tot_label']),
            Paragraph(f'-€ {_fmt(ritenuta)}', S['tot_value'])])
        sub_rows.append([
            Paragraph('NETTO A PAGARE:', S['tot_label']),
            Paragraph(f'€ {_fmt(netto)}', S['tot_value'])])
    sub_t = Table(sub_rows, colWidths=[45 * mm, 35 * mm])
    sub_t.setStyle(TableStyle([
        ('ALIGN',         (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 2),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
    ]))
    grand_t = Table(
        [[Paragraph('TOTALE:', S['grand_label']),
          Paragraph(f'€ {_fmt(grand_total)}', S['grand_value'])]],
        colWidths=[45 * mm, 35 * mm])
    grand_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('ALIGN',         (1, 0), (1, -1),  'RIGHT'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX',           (0, 0), (-1, -1), 0.5, GREY_BORDER),
    ]))
    wrapper = Table(
        [[Spacer(1, 1), sub_t],
         [Spacer(1, 1), grand_t]],
        colWidths=[USABLE_W - 80 * mm, 80 * mm])
    wrapper.setStyle(TableStyle([
        ('ALIGN',         (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(wrapper)
    story.append(Spacer(1, 5 * mm))

    # 6b. CUP / CIG / CUC
    cup = _s(inv.get('cup') or '')
    cig = _s(inv.get('cig') or '')
    cuc = _s(inv.get('cuc') or '')
    codes = []
    if cup.strip():
        codes.append(f'<b>CUP:</b> {cup}')
    if cig.strip():
        codes.append(f'<b>CIG:</b> {cig}')
    if cuc.strip():
        codes.append(f'<b>CUC:</b> {cuc}')
    if codes:
        codes_text = '&nbsp;&nbsp;&nbsp;&nbsp;'.join(codes)
        story.append(_box_section([Paragraph(codes_text, S['sec_text'])], 'RIFERIMENTI'))
        story.append(Spacer(1, 3 * mm))

    # 7. NOTE
    note_text = _s(inv.get('notes') or inv.get('note') or '')
    rif_text  = _s(inv.get('riferimento') or inv.get('subject') or '')
    if note_text.strip() or rif_text.strip():
        nc = []
        if rif_text.strip():
            nc.append(Paragraph(f'Rif. {rif_text}', S['note']))
        if note_text.strip():
            nc.append(Paragraph(note_text.replace('\n', '<br/>'), S['note']))
        story.append(_box_section(nc, 'NOTE'))
        story.append(Spacer(1, 3 * mm))

    # 8. BANCA
    bank_name = _s(inv.get('banca') or '')
    bank_iban = _s(inv.get('iban') or '')
    if not bank_name and not bank_iban:
        bank_d    = co.get('bank_details', {}) or {}
        bank_accs = co.get('bank_accounts', []) or []
        if bank_accs:
            bank_name = _s(bank_accs[0].get('bank_name', ''))
            bank_iban = _s(bank_accs[0].get('iban', ''))
        else:
            bank_name = _s(bank_d.get('bank_name', ''))
            bank_iban = _s(bank_d.get('iban', ''))
    if bank_name or bank_iban:
        bt = (f'{bank_name} - IBAN {bank_iban}'
              if bank_name and bank_iban
              else bank_name or f'IBAN {bank_iban}')
        story.append(_box_section(
            [Paragraph(f'<b>Coordinate Bancarie:</b> {bt}', S['sec_text'])]))
        story.append(Spacer(1, 3 * mm))

    # 9. SCADENZE
    scadenze = inv.get('scadenze_pagamento') or inv.get('scadenze') or []
    payment_label = _s(
        inv.get('payment_type_label') or
        PAYMENT_METHOD_NAMES.get(inv.get('payment_method', ''), '') or
        inv.get('payment_terms', ''))
    if scadenze or payment_label:
        sc_rows = []
        if payment_label:
            sc_rows.append(
                Paragraph(f'<b>Condizioni:</b> {payment_label}', S['sec_text']))
        for sc in scadenze:
            d_sc = _date(sc.get('data_scadenza') or sc.get('due_date'))
            imp  = _fmt(sc.get('importo') or sc.get('amount') or 0)
            pag  = ' (PAGATA)' if (sc.get('pagata') or sc.get('paid')) else ''
            sc_rows.append(Paragraph(
                f'<b>Scadenza:</b> {d_sc} &mdash; € {imp}{pag}',
                S['sec_text']))
        if not scadenze and inv.get('due_date'):
            sc_rows.append(Paragraph(
                f'<b>Scadenza:</b> {_date(inv["due_date"])}', S['sec_text']))
        story.append(_box_section(sc_rows, 'SCADENZA PAGAMENTI'))
        story.append(Spacer(1, 3 * mm))

    # 10. CONDIZIONI (solo PRV)
    if doc_type == 'PRV':
        cond = _s(co.get('condizioni_vendita', '') or
                  inv.get('condizioni_vendita', ''))
        if cond.strip():
            import re as _re
            story.append(PageBreak())
            story.append(Paragraph('CONDIZIONI GENERALI DI VENDITA',
                                   S['sec_title']))
            story.append(Spacer(1, 3 * mm))
            story.append(HRFlowable(width=USABLE_W, thickness=1,
                                    color=GREY_BORDER, spaceAfter=3 * mm))
            for line in cond.split('\n'):
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 2 * mm))
                    continue
                if _re.match(r'^\d+[.-)]', line):
                    story.append(Paragraph(line, S['sec_bold']))
                else:
                    story.append(Paragraph(line, S['sec_text']))

    doc.build(story,
              onFirstPage=_footer_canvas,
              onLaterPages=_footer_canvas)
    buf.seek(0)
    return buf.getvalue()

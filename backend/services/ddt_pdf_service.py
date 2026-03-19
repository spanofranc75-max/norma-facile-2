"""PDF service for DDT (Documento di Trasporto) — ReportLab diretto.

Stessa struttura delle fatture/preventivi:
- Logo+Azienda a sinistra, Cliente a destra (stessa riga)
- Titolo + Numero DDT centrato
- Tabella articoli con header grigio chiaro
- Dati trasporto compatti
- Firme
- Layout ottimizzato per pagina singola
"""
from io import BytesIO
from datetime import datetime
import logging
import base64
import os

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# ── Font ──
FONT_R = 'Helvetica'
FONT_B = 'Helvetica-Bold'
_LIB_PATHS = [
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/liberation/LiberationSans-Regular.ttf',
]
for _p in _LIB_PATHS:
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont('LiberationSans', _p))
            pdfmetrics.registerFont(TTFont('LiberationSans-Bold',
                _p.replace('Regular', 'Bold')))
            FONT_R = 'LiberationSans'
            FONT_B = 'LiberationSans-Bold'
            break
        except Exception:
            pass

# ── Colors (stessi della fattura) ──
ACCENT    = HexColor('#AAAAAA')
HEADER_BG = HexColor('#E8E8E8')
GREY_BG   = HexColor('#F7F7F7')
GREY_TEXT = HexColor('#888888')
GREY_BORDER = HexColor('#D5D5D5')
BODY_TEXT = HexColor('#555555')
TITLE_CLR = HexColor('#666666')
TOTALE_BG = HexColor('#E0E0E0')

PAGE_W, PAGE_H = A4
LEFT_M, RIGHT_M, TOP_M, BOTTOM_M = 18*mm, 18*mm, 15*mm, 20*mm
UW = PAGE_W - LEFT_M - RIGHT_M


def _sty(**kw):
    base = dict(fontName=FONT_R, fontSize=8, leading=11, textColor=BODY_TEXT)
    base.update(kw)
    return ParagraphStyle('_', **base)


def _fmt(val):
    try:
        val = float(val)
    except (TypeError, ValueError):
        return '0,00'
    s = f'{val:,.2f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def _date(d):
    if not d:
        return ''
    if isinstance(d, datetime):
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
    except Exception:
        return None


DDT_TYPE_TITLES = {
    "vendita": "DOCUMENTO DI TRASPORTO",
    "conto_lavoro": "DDT CONTO LAVORO",
    "rientro_conto_lavoro": "DDT RIENTRO CONTO LAVORO",
}


def _footer_canvas(canvas, doc):
    canvas.saveState()
    co = getattr(doc, '_company', {}) or {}
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    co_name = co.get('business_name', '') or ''
    cert = co.get('certificazioni') or (
        'Azienda Certificata EN 1090-1 EXC3 \u2022 ISO 3834-2 \u2022 '
        'Centro di Trasformazione Acciaio'
    )
    y_base = BOTTOM_M - 14 * mm
    canvas.setStrokeColor(GREY_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_M, y_base + 10 * mm, PAGE_W - RIGHT_M, y_base + 10 * mm)
    canvas.setFont(FONT_R, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawString(LEFT_M, y_base + 6 * mm,
                      f'Generato da {co_name} - NormaFacile')
    canvas.drawRightString(PAGE_W - RIGHT_M, y_base + 6 * mm,
                           f'Documento generato il {now_str}')
    canvas.setFont(FONT_B, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawCentredString(PAGE_W / 2, y_base + 2 * mm, cert)
    canvas.restoreState()


def generate_ddt_pdf(doc: dict, company: dict = None) -> BytesIO:
    """Genera DDT PDF con layout identico a fattura/preventivo."""
    d = doc or {}
    co = company or {}

    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=LEFT_M, rightMargin=RIGHT_M,
                            topMargin=TOP_M, bottomMargin=BOTTOM_M)
    pdf._company = co
    story = []

    # ═══════════════════════════════════════════════════════════
    # 1. HEADER — Logo+Azienda SINISTRA | Cliente DESTRA
    # ═══════════════════════════════════════════════════════════
    logo = _load_logo(co.get('logo_url', ''))

    left_col = []
    if logo:
        left_col.append(logo)
        left_col.append(Spacer(1, 2 * mm))
    left_col.append(Paragraph(co.get('business_name', ''),
                    _sty(fontName=FONT_B, fontSize=13, leading=16, textColor=BODY_TEXT)))
    addr = co.get('address', '')
    cap_city = ' '.join(p for p in [co.get('cap', ''), co.get('city', ''),
                f'({co.get("province", "")})' if co.get('province') else ''] if p)
    if addr:
        left_col.append(Paragraph(addr, _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    if cap_city:
        left_col.append(Paragraph(cap_city, _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    if co.get('partita_iva'):
        left_col.append(Paragraph(f'P.IVA: {co["partita_iva"]}',
                        _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    co_cf = co.get('codice_fiscale', '')
    if co_cf and co_cf != co.get('partita_iva', ''):
        left_col.append(Paragraph(f'Cod. Fisc.: {co_cf}',
                        _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    if co.get('email') or co.get('contact_email'):
        left_col.append(Paragraph(f'Email: {co.get("email") or co.get("contact_email")}',
                        _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))

    # Cliente
    right_col = []
    right_col.append(Paragraph('Spett.le',
                     _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    right_col.append(Paragraph(d.get('client_name', ''),
                     _sty(fontName=FONT_B, fontSize=11, leading=14, textColor=BODY_TEXT)))
    cl_addr_parts = [p for p in [
        d.get('client_address', ''),
        d.get('client_cap', ''),
        d.get('client_city', ''),
        f'({d.get("client_province", "")})' if d.get('client_province') else '',
    ] if p]
    if cl_addr_parts:
        right_col.append(Paragraph(' '.join(cl_addr_parts),
                         _sty(fontSize=8, leading=11.5, textColor=BODY_TEXT)))
    if d.get('client_piva'):
        right_col.append(Paragraph(f'P.IVA {d["client_piva"]}',
                         _sty(fontSize=8, leading=11.5, textColor=BODY_TEXT)))
    if d.get('client_cf'):
        right_col.append(Paragraph(f'C.F. {d["client_cf"]}',
                         _sty(fontSize=8, leading=11.5, textColor=BODY_TEXT)))
    if d.get('client_pec'):
        right_col.append(Paragraph(f'PEC: {d["client_pec"]}',
                         _sty(fontSize=8, leading=11.5, textColor=BODY_TEXT)))
    if d.get('client_sdi'):
        right_col.append(Paragraph(f'Cod. SDI {d["client_sdi"]}',
                         _sty(fontSize=8, leading=11.5, textColor=BODY_TEXT)))

    hdr = Table([[left_col, right_col]], colWidths=[UW * 0.55, UW * 0.45])
    hdr.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width=UW, thickness=1, color=ACCENT, spaceAfter=3 * mm))

    # ═══════════════════════════════════════════════════════════
    # 2. TITOLO + NUMERO DDT
    # ═══════════════════════════════════════════════════════════
    ddt_type = d.get('ddt_type', 'vendita')
    title = DDT_TYPE_TITLES.get(ddt_type, 'DOCUMENTO DI TRASPORTO')
    doc_number = d.get('number', '')
    disp_num = doc_number.replace('DDT-', '') if doc_number else ''
    title_text = f'{title} N. {disp_num}' if disp_num else title
    story.append(Paragraph(title_text,
                 _sty(fontName=FONT_B, fontSize=16, leading=20,
                      textColor=TITLE_CLR, alignment=TA_CENTER)))
    story.append(Spacer(1, 3 * mm))

    # ═══════════════════════════════════════════════════════════
    # 3. META — Data + Tipo DDT (compatto)
    # ═══════════════════════════════════════════════════════════
    doc_date = _date(d.get('data_ora_trasporto') or d.get('created_at', ''))
    meta = Table([
        [Paragraph('DATA:', _sty(fontName=FONT_B, fontSize=7.5, textColor=GREY_TEXT)),
         Paragraph(doc_date, _sty(fontSize=8.5, textColor=BODY_TEXT)),
         Paragraph('TIPO DDT:', _sty(fontName=FONT_B, fontSize=7.5, textColor=GREY_TEXT)),
         Paragraph(ddt_type.replace('_', ' ').title(), _sty(fontSize=8.5, textColor=BODY_TEXT))],
    ], colWidths=[UW*0.12, UW*0.38, UW*0.12, UW*0.38])
    meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GREY_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta)
    story.append(Spacer(1, 3 * mm))

    # ═══════════════════════════════════════════════════════════
    # 4. DESTINAZIONE MERCE (se presente)
    # ═══════════════════════════════════════════════════════════
    dest = d.get('destinazione', {}) or {}
    if dest.get('ragione_sociale'):
        dest_parts = [dest.get('ragione_sociale', '')]
        addr_line = ' '.join(p for p in [
            dest.get('indirizzo', ''), dest.get('cap', ''),
            dest.get('localita', ''), f'({dest.get("provincia", "")})' if dest.get('provincia') else ''
        ] if p)
        if addr_line:
            dest_parts.append(addr_line)
        dest_rows = [[Paragraph('DESTINAZIONE MERCE',
                      _sty(fontName=FONT_B, fontSize=7.5, textColor=GREY_TEXT))]]
        for dp in dest_parts:
            dest_rows.append([Paragraph(dp, _sty(fontSize=8, textColor=BODY_TEXT))])
        dest_t = Table(dest_rows, colWidths=[UW])
        dest_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREY_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(dest_t)
        story.append(Spacer(1, 2 * mm))

    # ═══════════════════════════════════════════════════════════
    # 5. TABELLA ARTICOLI
    # ═══════════════════════════════════════════════════════════
    lines = d.get('lines', [])
    show_prices = d.get('stampa_prezzi', True)

    if show_prices:
        headers = ['Codice', 'Descrizione', 'u.m.', 'Q.t\u00e0', 'Prezzo', 'Importo', 'IVA']
        col_w = [UW*0.08, UW*0.38, UW*0.07, UW*0.09, UW*0.13, UW*0.14, UW*0.08]
    else:
        headers = ['Codice', 'Descrizione', 'u.m.', 'Q.t\u00e0']
        col_w = [UW*0.10, UW*0.55, UW*0.15, UW*0.20]

    th_style = _sty(fontName=FONT_B, fontSize=7, leading=9, textColor=TITLE_CLR, alignment=TA_CENTER)
    table_data = [[Paragraph(h, th_style) for h in headers]]

    for ln in lines:
        code = str(ln.get('codice_articolo') or '')
        desc = str(ln.get('description') or '').replace('\n', '<br/>')
        um = str(ln.get('unit', 'pz'))
        qty = _fmt(ln.get('quantity', 0))

        if show_prices:
            price = _fmt(ln.get('unit_price', 0))
            total = _fmt(ln.get('line_total', 0))
            vat = str(ln.get('vat_rate', '22'))
            table_data.append([
                Paragraph(code, _sty(fontSize=7.5, alignment=TA_CENTER)),
                Paragraph(desc, _sty(fontSize=8, leading=11)),
                Paragraph(um, _sty(fontSize=7.5, alignment=TA_CENTER)),
                Paragraph(qty, _sty(fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f'\u20ac {price}', _sty(fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f'\u20ac {total}', _sty(fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f'{vat}%', _sty(fontSize=7.5, alignment=TA_CENTER)),
            ])
        else:
            table_data.append([
                Paragraph(code, _sty(fontSize=7.5, alignment=TA_CENTER)),
                Paragraph(desc, _sty(fontSize=8, leading=11)),
                Paragraph(um, _sty(fontSize=7.5, alignment=TA_CENTER)),
                Paragraph(qty, _sty(fontSize=8, alignment=TA_RIGHT)),
            ])

    t = Table(table_data, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), TITLE_CLR),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, 0), 1, GREY_BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GREY_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    # Zebra
    for i in range(2, len(table_data), 2):
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F9F9F9')))
    # Row separators
    for i in range(1, len(table_data)):
        style_cmds.append(('LINEBELOW', (0, i), (-1, i), 0.3, GREY_BORDER))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 2 * mm))

    # ═══════════════════════════════════════════════════════════
    # 6. NOTE
    # ═══════════════════════════════════════════════════════════
    if d.get('notes'):
        notes_t = Table([[
            Paragraph(f'<b>Note:</b> {str(d["notes"])}',
                      _sty(fontSize=7.5, leading=10, textColor=BODY_TEXT))
        ]], colWidths=[UW])
        notes_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREY_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(notes_t)
        story.append(Spacer(1, 2 * mm))

    # ═══════════════════════════════════════════════════════════
    # 7. TOTALI (solo se prezzi visibili)
    # ═══════════════════════════════════════════════════════════
    if show_prices and lines:
        # Calcola totali per aliquota IVA
        iva_groups = {}
        for ln in lines:
            rate = str(ln.get('vat_rate', '22'))
            total = float(ln.get('line_total', 0))
            iva_groups.setdefault(rate, 0)
            iva_groups[rate] += total

        tot_rows = []
        grand_imponibile = 0
        grand_iva = 0
        for rate, imponibile in sorted(iva_groups.items()):
            iva_val = imponibile * float(rate) / 100
            grand_imponibile += imponibile
            grand_iva += iva_val
            tot_rows.append([
                Paragraph(f'Imponibile IVA {rate}%', _sty(fontSize=8, textColor=GREY_TEXT, alignment=TA_RIGHT)),
                Paragraph(_fmt(imponibile), _sty(fontName=FONT_B, fontSize=8, alignment=TA_RIGHT)),
            ])
            tot_rows.append([
                Paragraph(f'IVA {rate}%', _sty(fontSize=8, textColor=GREY_TEXT, alignment=TA_RIGHT)),
                Paragraph(_fmt(iva_val), _sty(fontName=FONT_B, fontSize=8, alignment=TA_RIGHT)),
            ])

        grand_total = grand_imponibile + grand_iva
        tot_rows.append([
            Paragraph('TOTALE', _sty(fontName=FONT_B, fontSize=11, textColor=TITLE_CLR, alignment=TA_RIGHT)),
            Paragraph(f'EUR {_fmt(grand_total)}', _sty(fontName=FONT_B, fontSize=13, textColor=BODY_TEXT, alignment=TA_RIGHT)),
        ])

        tot_t = Table(tot_rows, colWidths=[UW * 0.7, UW * 0.3])
        cmds = [
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, -2), (-1, -2), 0.5, GREY_BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), TOTALE_BG),
            ('BOX', (0, -1), (-1, -1), 0.5, GREY_BORDER),
            ('TOPPADDING', (0, -1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 5),
        ]
        tot_t.setStyle(TableStyle(cmds))
        story.append(tot_t)
        story.append(Spacer(1, 3 * mm))

    # ═══════════════════════════════════════════════════════════
    # 8. DATI TRASPORTO (compatto, griglia 2x4)
    # ═══════════════════════════════════════════════════════════
    lbl_s = _sty(fontName=FONT_B, fontSize=7.5, leading=10, textColor=GREY_TEXT)
    val_s = _sty(fontSize=8, leading=11, textColor=BODY_TEXT)

    transport_rows = [
        [Paragraph('Causale:', lbl_s), Paragraph(str(d.get('causale_trasporto', '-')), val_s),
         Paragraph('Porto:', lbl_s), Paragraph(str(d.get('porto', '-')), val_s)],
        [Paragraph('Vettore:', lbl_s), Paragraph(str(d.get('vettore', '-')), val_s),
         Paragraph('Mezzo:', lbl_s), Paragraph(str(d.get('mezzo_trasporto', '-')), val_s)],
        [Paragraph('N. Colli:', lbl_s), Paragraph(str(d.get('num_colli', 0)), val_s),
         Paragraph('Peso Lordo:', lbl_s), Paragraph(f'{d.get("peso_lordo_kg", 0)} kg', val_s)],
        [Paragraph('Aspetto:', lbl_s), Paragraph(str(d.get('aspetto_beni', '-')), val_s),
         Paragraph('Peso Netto:', lbl_s), Paragraph(f'{d.get("peso_netto_kg", 0)} kg', val_s)],
    ]
    tr_t = Table(transport_rows, colWidths=[UW*0.15, UW*0.35, UW*0.15, UW*0.35])
    tr_t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
        ('BACKGROUND', (2, 0), (2, -1), GREY_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(Paragraph('DATI TRASPORTO',
                 _sty(fontName=FONT_B, fontSize=7.5, leading=10, textColor=GREY_TEXT)))
    story.append(Spacer(1, 1 * mm))
    story.append(tr_t)
    story.append(Spacer(1, 6 * mm))

    # ═══════════════════════════════════════════════════════════
    # 9. FIRME
    # ═══════════════════════════════════════════════════════════
    sig_data = [[
        Paragraph('', _sty(fontSize=1)),
        Paragraph('', _sty(fontSize=1)),
        Paragraph('', _sty(fontSize=1)),
    ], [
        Paragraph('Firma mittente', _sty(fontSize=7.5, textColor=GREY_TEXT, alignment=TA_CENTER)),
        Paragraph('Firma vettore', _sty(fontSize=7.5, textColor=GREY_TEXT, alignment=TA_CENTER)),
        Paragraph('Firma destinatario', _sty(fontSize=7.5, textColor=GREY_TEXT, alignment=TA_CENTER)),
    ]]
    sig_t = Table(sig_data, colWidths=[UW/3]*3, rowHeights=[20*mm, None])
    sig_t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(sig_t)

    # Build
    pdf.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    buf.seek(0)
    return buf

"""Shared PDF template utilities — ReportLab only.

Layout replicato dall'originale NormaFacile:
- Monocromatico (nero/blu scuro)
- Logo in alto a sinistra
- Azienda a sinistra, Cliente a destra
- Tabella con header scuro
- Totali con box grigio per TOTALE
- Footer: "Generato da NormaFacile" + "Pag. X/Y"
- Pagina condizioni per preventivi
"""
from io import BytesIO
from datetime import datetime, timezone
import html as html_mod
import logging
import re
import base64

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

logger = logging.getLogger(__name__)
_esc = html_mod.escape

# ── Font registration ──
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

# ── Colors (monocromatico) ──
DARK = HexColor('#1E293B')
BORDER = HexColor('#94A3B8')
LIGHT_BG = HexColor('#F1F5F9')
TEXT_MAIN = HexColor('#1a1a2e')
TEXT_SEC = HexColor('#475569')
TEXT_GREY = HexColor('#64748B')
ZEBRA_BG = HexColor('#F8FAFC')

# ── Page ──
PAGE_W, PAGE_H = A4
LM = 16 * mm
RM = 16 * mm
TM = 14 * mm
BM = 22 * mm
UW = PAGE_W - LM - RM


def fmt_it(n) -> str:
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def safe(val) -> str:
    return _esc(str(val or ""))


def strip_html(text: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html_mod.unescape(text).strip()


COMMON_CSS = ""


def format_date(date_str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(date_str)[:10] if date_str else ""


def _sty(**kw):
    base = dict(fontName=FONT_R, fontSize=8, leading=11, textColor=TEXT_MAIN)
    base.update(kw)
    return ParagraphStyle('_', **base)


def _load_logo(logo_url):
    if not logo_url:
        return None
    try:
        if logo_url.startswith('data:'):
            b64 = logo_url.split('base64,')[1]
            stream = BytesIO(base64.b64decode(b64))
        elif logo_url.startswith('http'):
            import urllib.request
            with urllib.request.urlopen(logo_url, timeout=5) as r:
                stream = BytesIO(r.read())
        else:
            return None
        try:
            from reportlab.lib.utils import ImageReader
            ir = ImageReader(stream)
            iw, ih = ir.getSize()
            stream.seek(0)
            max_w = 5.0 * cm
            ratio = ih / iw if iw > 0 else 0.33
            img = Image(stream, width=max_w, height=max_w * ratio)
        except Exception:
            stream.seek(0)
            img = Image(stream, width=5.0 * cm, height=1.6 * cm)
        img.hAlign = 'LEFT'
        return img
    except Exception as e:
        logger.warning(f'Logo load failed: {e}')
        return None


# ── Shared functions for route generators ──

def build_header_html(company: dict, client: dict, no_client_border: bool = False) -> str:
    co = company or {}
    cl = client or {}
    lines = []
    lines.append(f"AZIENDA:{safe(co.get('business_name', ''))}")
    addr_parts = [safe(co.get('address', ''))]
    loc = [p for p in [safe(co.get('cap', '')), safe(co.get('city', '')),
           f"({safe(co.get('province', ''))})" if co.get('province') else ""] if p]
    if loc:
        addr_parts.append(' '.join(loc))
    lines.append(' - '.join([p for p in addr_parts if p]))
    if co.get('partita_iva'):
        lines.append(f"P.IVA: {safe(co['partita_iva'])}")
    if co.get('codice_fiscale'):
        lines.append(f"Cod.Fisc.: {safe(co['codice_fiscale'])}")
    if co.get('phone') or co.get('tel'):
        lines.append(f"Tel: {safe(co.get('phone') or co.get('tel'))}")
    if co.get('email') or co.get('contact_email'):
        lines.append(f"Email: {safe(co.get('email') or co.get('contact_email'))}")
    lines.append("---")
    lines.append(f"CLIENTE:{safe(cl.get('business_name', ''))}")
    cl_addr_parts = [safe(cl.get('address', ''))]
    cl_loc = [p for p in [safe(cl.get('cap', '')), safe(cl.get('city', '')),
              f"({safe(cl.get('province', ''))})" if cl.get('province') else ""] if p]
    if cl_loc:
        cl_addr_parts.append(' '.join(cl_loc))
    lines.append(' - '.join([p for p in cl_addr_parts if p]))
    if cl.get('partita_iva'):
        lines.append(f"P.IVA: {safe(cl['partita_iva'])}")
    if cl.get('codice_fiscale'):
        lines.append(f"Cod.Fisc.: {safe(cl['codice_fiscale'])}")
    if cl.get('codice_sdi'):
        lines.append(f"Cod.SDI: {safe(cl['codice_sdi'])}")
    if cl.get('pec'):
        lines.append(f"PEC: {safe(cl['pec'])}")
    elif cl.get('email'):
        lines.append(f"Email: {safe(cl['email'])}")
    return '\n'.join(lines)


def compute_iva_groups(lines: list, sconto_globale: float = 0) -> dict:
    subtotal = sum(float(ln.get("line_total") or 0) for ln in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)
    groups = {}
    for ln in lines:
        rate_str = str(ln.get("vat_rate", "22"))
        base = float(ln.get("line_total") or 0)
        if sconto_globale and subtotal > 0:
            base = base * (1 - sconto_globale / 100)
        groups.setdefault(rate_str, {"base": 0.0, "iva": 0.0})
        try:
            rate = float(rate_str) / 100
        except (ValueError, TypeError):
            rate = 0.0
        groups[rate_str]["base"] += round(base, 2)
        groups[rate_str]["iva"] += round(base * rate, 2)
    total_iva = sum(g["iva"] for g in groups.values())
    total_imponibile = sum(g["base"] for g in groups.values())
    total_doc = round(total_imponibile + total_iva, 2)
    return {
        "subtotal": subtotal, "sconto_val": sconto_val,
        "imponibile": imponibile, "groups": groups,
        "total_iva": round(total_iva, 2),
        "total_imponibile": round(total_imponibile, 2),
        "total_doc": total_doc,
    }


def build_totals_html(iva_data: dict, acconto: float = 0) -> str:
    groups = iva_data.get("groups", {})
    sconto_val = iva_data.get("sconto_val", 0)
    subtotal = iva_data.get("subtotal", 0)
    total_doc = iva_data.get("total_doc", 0)
    saldo = total_doc - acconto
    lines = []
    if sconto_val:
        lines.append(f"Imponibile lordo: {fmt_it(subtotal)}")
        lines.append(f"Sconto: - {fmt_it(sconto_val)}")
    for rate_str, g in sorted(groups.items()):
        lines.append(f"Imponibile IVA {rate_str}%: {fmt_it(g['base'])}")
        lines.append(f"IVA {rate_str}%: {fmt_it(g['iva'])}")
    lines.append(f"TOTALE DOCUMENTO: EUR {fmt_it(total_doc)}")
    if acconto:
        lines.append(f"Acconto: - {fmt_it(acconto)}")
        lines.append(f"SALDO: EUR {fmt_it(saldo)}")
    return "\n".join(lines)


def build_conditions_html(company: dict, doc_number: str) -> str:
    return '<div style="page-break-before:always">CONDITIONS</div>'


# ══════════════════════════════════════════════════════════════
# render_pdf — converte HTML strutturato in PDF professionale
# ══════════════════════════════════════════════════════════════

def _footer_cb(canvas, doc):
    """Footer semplice: 'Generato da NormaFacile' + 'Pag. X'."""
    canvas.saveState()
    co = getattr(doc, '_company', {}) or {}
    co_name = co.get('business_name', '') or ''
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    y = BM - 8 * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.3)
    canvas.line(LM, y + 4 * mm, PAGE_W - RM, y + 4 * mm)
    canvas.setFont(FONT_R, 6.5)
    canvas.setFillColor(TEXT_GREY)
    canvas.drawString(LM, y, f'Generato da NormaFacile')
    canvas.drawRightString(PAGE_W - RM, y, f'Pag. {canvas.getPageNumber()}')
    canvas.restoreState()


def render_pdf(html_content: str, company: dict = None, doc_title: str = '') -> BytesIO:
    """Render PDF dal contenuto HTML generato dai route handlers."""
    co = company or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=LM, rightMargin=RM,
                            topMargin=TM, bottomMargin=BM)
    doc._company = co
    story = []

    sections = _parse_sections(html_content)

    # 1. Header con logo
    _add_header(story, sections, co)

    # 2. Separatore
    story.append(HRFlowable(width=UW, thickness=1, color=DARK,
                            spaceBefore=1*mm, spaceAfter=3*mm))

    # 3. Titolo
    if sections.get('title'):
        story.append(Paragraph(sections['title'],
                     _sty(fontName=FONT_B, fontSize=14, leading=18, textColor=DARK)))
        story.append(Spacer(1, 3*mm))

    # 4. Meta
    if sections.get('meta_rows'):
        _add_meta(story, sections['meta_rows'])

    # 5. Note/Rif
    for note in sections.get('ref_notes', []):
        story.append(Paragraph(f'<b>Note:</b> {note}', _sty(fontSize=7.5, textColor=TEXT_SEC)))
        story.append(Spacer(1, 2*mm))

    # 6. Tabella articoli
    if sections.get('table_headers') and sections.get('table_rows'):
        _add_items_table(story, sections['table_headers'], sections['table_rows'])

    # 7. Note tecniche
    if sections.get('tech_notes'):
        story.append(Paragraph(f'<b>Note:</b> {sections["tech_notes"]}',
                     _sty(fontSize=7.5, textColor=TEXT_SEC)))
        story.append(Spacer(1, 2*mm))

    # 8. Totali
    if sections.get('totals_text'):
        _add_totals(story, sections['totals_text'])

    # 9. Banca
    if sections.get('bank_info'):
        story.append(Paragraph(sections['bank_info'], _sty(fontSize=8, textColor=TEXT_SEC)))
        story.append(Spacer(1, 3*mm))

    # 10. Trasporto (DDT)
    if sections.get('transport_rows'):
        _add_transport(story, sections['transport_rows'])

    # 11. Destinazione (DDT)
    if sections.get('destination'):
        story.append(Paragraph(f'<b>Destinazione:</b> {sections["destination"]}',
                     _sty(fontSize=8)))
        story.append(Spacer(1, 3*mm))

    # 12. Firme (DDT)
    if sections.get('signatures'):
        _add_signatures(story)

    # 13. Condizioni vendita
    if sections.get('has_conditions'):
        _add_conditions(story, co)

    if not story:
        story.append(Paragraph("Documento generato da NormaFacile", _sty(alignment=TA_CENTER)))

    doc.build(story, onFirstPage=_footer_cb, onLaterPages=_footer_cb)
    buf.seek(0)
    return buf


# ── Parsing HTML ──

def _parse_sections(html: str) -> dict:
    r = {'header_text': '', 'title': '', 'meta_rows': [], 'ref_notes': [],
         'table_headers': [], 'table_rows': [], 'tech_notes': '',
         'totals_text': '', 'bank_info': '', 'transport_rows': [],
         'destination': '', 'signatures': False, 'has_conditions': False}

    # Header
    hdr = re.search(r'^(.*?)(?:<div\s+class="doc-title"|<h1>)', html, re.DOTALL)
    if hdr:
        r['header_text'] = strip_html(hdr.group(1))

    # Titolo
    t = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if t:
        r['title'] = strip_html(t.group(1))

    # Meta
    m = re.search(r'<table\s+class="meta-table">(.*?)</table>', html, re.DOTALL)
    if m:
        rows = re.findall(r'<tr>(.*?)</tr>', m.group(1), re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 2:
                label = strip_html(cells[0]).strip()
                value = strip_html(cells[1]).strip()
                if label and value:
                    r['meta_rows'].append((label, value))

    # Ref notes
    for rn in re.findall(r'<p\s+class="ref-note">(.*?)</p>', html, re.DOTALL):
        clean = strip_html(rn).replace('Note:', '').strip()
        if clean:
            r['ref_notes'].append(clean)

    # Items table
    it = re.search(r'<table\s+class="items-table">(.*?)</table>', html, re.DOTALL)
    if it:
        table = it.group(1)
        thead = re.search(r'<thead>(.*?)</thead>', table, re.DOTALL)
        if thead:
            r['table_headers'] = [html_mod.unescape(strip_html(h))
                                  for h in re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL)]
        tbody = re.search(r'<tbody>(.*?)</tbody>', table, re.DOTALL)
        if tbody:
            for row in re.findall(r'<tr>(.*?)</tr>', tbody.group(1), re.DOTALL):
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                r['table_rows'].append([html_mod.unescape(strip_html(c)) for c in cells])

    # Tech notes
    ib = re.findall(r'<div\s+class="info-box">(.*?)</div>', html, re.DOTALL)
    for box in ib:
        clean = strip_html(box).replace('Note:', '').strip()
        if clean:
            r['tech_notes'] = clean

    # Totals
    tp = re.search(r'(?:</table>.*?)((?:Imponibile|TOTALE|IVA|Sconto|SALDO|Acconto).*?)(?:<div|$)',
                   html, re.DOTALL)
    if tp:
        r['totals_text'] = strip_html(tp.group(1))

    # Bank
    bk = re.search(r'<div\s+class="bank-info">(.*?)</div>', html, re.DOTALL)
    if bk:
        r['bank_info'] = strip_html(bk.group(1))

    # Transport
    tr = re.search(r'<table\s+class="transport-table">(.*?)</table>', html, re.DOTALL)
    if tr:
        for row in re.findall(r'<tr>(.*?)</tr>', tr.group(1), re.DOTALL):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            pairs = []
            for i in range(0, len(cells) - 1, 2):
                pairs.append((strip_html(cells[i]), strip_html(cells[i+1]) if i+1 < len(cells) else ''))
            if pairs:
                r['transport_rows'].append(pairs)

    # Destination
    dm = re.search(r'DESTINAZIONE MERCE.*?</div>', html, re.DOTALL)
    if dm:
        r['destination'] = strip_html(dm.group(0)).replace('DESTINAZIONE MERCE', '').strip()

    # Signatures
    if 'signatures-row' in html or 'Firma mittente' in html:
        r['signatures'] = True

    # Conditions
    if 'page-break-before' in html or 'CONDITIONS' in html:
        r['has_conditions'] = True

    return r


# ── Builders ──

def _add_header(story, sections, co):
    parts = sections.get('header_text', '').split('---')
    co_text = parts[0].strip() if parts else ''
    cl_text = parts[1].strip() if len(parts) > 1 else ''

    logo = _load_logo(co.get('logo_url', ''))

    # Colonna sinistra: logo + azienda
    left = []
    if logo:
        left.append(logo)
        left.append(Spacer(1, 2*mm))
    for line in co_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('AZIENDA:'):
            name = line.replace('AZIENDA:', '').strip()
            left.append(Paragraph(name, _sty(fontName=FONT_B, fontSize=11, leading=14, textColor=DARK)))
        else:
            left.append(Paragraph(line, _sty(fontSize=7.5, leading=10, textColor=TEXT_SEC)))

    # Colonna destra: cliente
    right = []
    for line in cl_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('CLIENTE:'):
            name = line.replace('CLIENTE:', '').strip()
            right.append(Paragraph('Cliente', _sty(fontSize=7, leading=9, textColor=TEXT_GREY)))
            right.append(Paragraph(name, _sty(fontName=FONT_B, fontSize=10, leading=13, textColor=DARK)))
        else:
            right.append(Paragraph(line, _sty(fontSize=7.5, leading=10, textColor=TEXT_SEC)))

    hdr = Table([[left, right]], colWidths=[UW * 0.55, UW * 0.45])
    hdr.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 2*mm))


def _add_meta(story, meta_rows):
    rows = []
    for label, value in meta_rows:
        rows.append([
            Paragraph(label, _sty(fontName=FONT_B, fontSize=7.5, leading=10, textColor=DARK)),
            Paragraph(value, _sty(fontSize=8, leading=11, textColor=TEXT_MAIN)),
        ])
    t = Table(rows, colWidths=[UW * 0.25, UW * 0.75])
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, DARK),
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 4*mm))


def _add_items_table(story, headers, rows):
    n = len(headers)
    # Header
    th = [Paragraph(h, _sty(fontName=FONT_B, fontSize=7, leading=9, textColor=white,
          alignment=TA_CENTER if h.lower() in ('codice','u.m.','iva','sconti') else
                    TA_RIGHT if h.lower() in ('prezzo','importo','totale','quantit\u00e0','q.t\u00e0') else TA_LEFT))
          for h in headers]
    data = [th]
    for row in rows:
        cells = []
        for i, cell in enumerate(row[:n]):
            h = headers[i].lower() if i < len(headers) else ''
            al = (TA_CENTER if h in ('codice','u.m.','iva','sconti') else
                  TA_RIGHT if h in ('prezzo','importo','totale','quantit\u00e0','q.t\u00e0') else TA_LEFT)
            cells.append(Paragraph(cell, _sty(fontSize=7.5, leading=10, alignment=al)))
        while len(cells) < n:
            cells.append(Paragraph('', _sty()))
        data.append(cells)

    if n == 8:
        cw = [UW*w for w in [0.08, 0.34, 0.06, 0.08, 0.12, 0.08, 0.12, 0.08]]
    elif n == 5:
        cw = [UW*w for w in [0.44, 0.10, 0.18, 0.10, 0.18]]
    elif n == 4:
        cw = [UW*w for w in [0.10, 0.55, 0.15, 0.20]]
    else:
        cw = [UW/n]*n

    t = Table(data, colWidths=cw, repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER),
        ('BOX', (0, 0), (-1, -1), 0.5, DARK),
        ('INNERGRID', (0, 0), (-1, 0), 0.3, HexColor('#475569')),
    ])
    for i in range(2, len(data), 2):
        ts.add('BACKGROUND', (0, i), (-1, i), ZEBRA_BG)
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 4*mm))


def _add_totals(story, totals_text):
    lines = [l.strip() for l in totals_text.strip().split('\n') if l.strip()]
    sub_rows = []
    grand = None
    saldo = None
    for line in lines:
        if line.startswith('TOTALE DOCUMENTO:') or line.startswith('TOTALE:'):
            grand = line
        elif line.startswith('SALDO:'):
            saldo = line
        else:
            parts = line.split(':', 1)
            if len(parts) == 2:
                sub_rows.append((parts[0].strip(), parts[1].strip()))

    tw = 75 * mm
    inner = [tw * 0.55, tw * 0.45]

    all_rows = []
    for label, val in sub_rows:
        all_rows.append([
            Paragraph(label, _sty(fontSize=8, textColor=TEXT_GREY, alignment=TA_RIGHT)),
            Paragraph(val, _sty(fontName=FONT_B, fontSize=8, alignment=TA_RIGHT)),
        ])

    if grand:
        val = grand.split(':', 1)[1].strip() if ':' in grand else ''
        all_rows.append([
            Paragraph('TOTALE', _sty(fontName=FONT_B, fontSize=10, alignment=TA_RIGHT)),
            Paragraph(val, _sty(fontName=FONT_B, fontSize=10, alignment=TA_RIGHT)),
        ])

    if saldo:
        val = saldo.split(':', 1)[1].strip() if ':' in saldo else ''
        all_rows.append([
            Paragraph('SALDO', _sty(fontName=FONT_B, fontSize=10, alignment=TA_RIGHT)),
            Paragraph(val, _sty(fontName=FONT_B, fontSize=10, alignment=TA_RIGHT)),
        ])

    if all_rows:
        t = Table(all_rows, colWidths=inner)
        cmds = [
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER),
        ]
        # Box grigio per TOTALE (ultima o penultima riga)
        grand_idx = len(all_rows) - 1 if not saldo else len(all_rows) - 2
        if grand_idx >= 0:
            cmds.append(('BACKGROUND', (0, grand_idx), (-1, grand_idx), LIGHT_BG))
            cmds.append(('BOX', (0, grand_idx), (-1, grand_idx), 0.5, DARK))
        if saldo:
            cmds.append(('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG))
            cmds.append(('BOX', (0, -1), (-1, -1), 0.5, DARK))
        t.setStyle(TableStyle(cmds))

        wrapper = Table([[Spacer(1, 1), t]], colWidths=[UW - tw, tw])
        wrapper.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(wrapper)
        story.append(Spacer(1, 4*mm))


def _add_transport(story, transport_rows):
    story.append(Paragraph('DATI TRASPORTO',
                 _sty(fontName=FONT_B, fontSize=8, leading=11, textColor=DARK)))
    story.append(Spacer(1, 2*mm))
    rows = []
    for pairs in transport_rows:
        row = []
        for label, val in pairs:
            row.append(Paragraph(f'<b>{label}</b>', _sty(fontSize=7.5)))
            row.append(Paragraph(val, _sty(fontSize=7.5)))
        rows.append(row)
    if rows:
        nc = max(len(r) for r in rows)
        t = Table(rows, colWidths=[UW/nc]*nc)
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, DARK),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 3*mm))


def _add_signatures(story):
    story.append(Spacer(1, 10*mm))
    t = Table(
        [[Paragraph('<b>Firma mittente</b>', _sty(alignment=TA_CENTER)),
          Paragraph('<b>Firma vettore</b>', _sty(alignment=TA_CENTER)),
          Paragraph('<b>Firma destinatario</b>', _sty(alignment=TA_CENTER))]],
        colWidths=[UW/3]*3)
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(t)


def _add_conditions(story, co):
    """Pagina condizioni generali di vendita."""
    story.append(PageBreak())
    story.append(Paragraph('CONDIZIONI GENERALI DI FORNITURA',
                 _sty(fontName=FONT_B, fontSize=14, leading=18, textColor=DARK, alignment=TA_CENTER)))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=UW, thickness=0.5, color=DARK, spaceAfter=4*mm))

    cond = co.get('condizioni_vendita', '') or ''
    if cond.strip():
        for line in cond.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 2*mm))
            elif re.match(r'^\d+[\s.)-]', line):
                story.append(Paragraph(line, _sty(fontName=FONT_B, fontSize=8, leading=11)))
            else:
                story.append(Paragraph(line, _sty(fontSize=7.5, leading=10)))
    else:
        defaults = [
            ("1 - Premessa",
             "Le presenti condizioni si applicano a tutti i contratti di fornitura."),
            ("2 - Condizioni di fornitura",
             "I prezzi si intendono per merce resa franco partenza. "
             "Il termine di consegna decorre dalla data di conferma ordine."),
            ("3 - Pagamenti",
             "Il pagamento deve avvenire nei termini indicati nel documento."),
            ("4 - Garanzia",
             "La garanzia copre i difetti di fabbricazione per 12 mesi dalla consegna."),
            ("5 - Foro competente",
             "Per qualsiasi controversia e' competente il Foro della sede del fornitore."),
        ]
        for title, text in defaults:
            story.append(Paragraph(title, _sty(fontName=FONT_B, fontSize=8, leading=11)))
            story.append(Paragraph(text, _sty(fontSize=7.5, leading=10)))
            story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph('<b>Firma e timbro per accettazione</b>',
                 _sty(fontSize=8, leading=11)))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=180, thickness=0.5, color=DARK))
    story.append(Paragraph('Data ___/___/___  (legale rappresentante)',
                 _sty(fontSize=7, leading=9, textColor=TEXT_GREY)))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        "Ai sensi e per gli effetti dell'Art. 1341 e segg. del Codice Civile, "
        "il sottoscritto Acquirente dichiara di aver preso specifica, precisa e "
        "dettagliata visione di tutte le disposizioni del contratto e di approvarle "
        "integralmente senza alcuna riserva.",
        _sty(fontSize=7, leading=9.5, textColor=TEXT_GREY)))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph('_____________________, li ______________________',
                 _sty(fontSize=8)))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=180, thickness=0.5, color=DARK))
    story.append(Paragraph('Firma e timbro (il legale rappresentante)',
                 _sty(fontSize=7, leading=9, textColor=TEXT_GREY)))

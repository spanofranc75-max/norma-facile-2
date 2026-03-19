"""Shared PDF template utilities - ReportLab only, no system deps."""
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
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

logger = logging.getLogger(__name__)
_esc = html_mod.escape

# ── Font registration ──
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

_LIBERATION_PATHS = [
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/liberation/LiberationSans-Regular.ttf',
]
for _p in _LIBERATION_PATHS:
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont('LiberationSans', _p))
            pdfmetrics.registerFont(TTFont('LiberationSans-Bold',
                _p.replace('Regular', 'Bold')))
            FONT_REGULAR = 'LiberationSans'
            FONT_BOLD = 'LiberationSans-Bold'
            break
        except Exception:
            pass

# ── Colors ──
NAVY = HexColor('#0F172A')
BLUE = HexColor('#2563EB')
GREY_BG = HexColor('#F1F5F9')
GREY_TEXT = HexColor('#64748B')
GREY_BORDER = HexColor('#CBD5E1')
DARK_TEXT = HexColor('#1a1a2e')
SEC_TEXT = HexColor('#475569')
ZEBRA = HexColor('#F8FAFC')

# ── Page setup ──
PAGE_W, PAGE_H = A4
L_MARGIN = 16 * mm
R_MARGIN = 16 * mm
T_MARGIN = 14 * mm
B_MARGIN = 22 * mm
USABLE_W = PAGE_W - L_MARGIN - R_MARGIN


def fmt_it(n) -> str:
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def safe(val) -> str:
    return _esc(str(val or ""))


COMMON_CSS = ""


def strip_html(text: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html_mod.unescape(text).strip()


def build_header_html(company: dict, client: dict, no_client_border: bool = False) -> str:
    co = company or {}
    cl = client or {}
    company_name = safe(co.get("business_name", ""))
    addr = safe(co.get("address", ""))
    cap = safe(co.get("cap", ""))
    city = safe(co.get("city", ""))
    prov = safe(co.get("province", ""))
    full_addr = addr
    if cap or city:
        parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
        full_addr += f" {' '.join(parts)}"
    piva = safe(co.get("partita_iva", ""))
    cf = safe(co.get("codice_fiscale", ""))
    phone = safe(co.get("phone") or co.get("tel", ""))
    email = safe(co.get("email") or co.get("contact_email", ""))
    cl_name = safe(cl.get("business_name", ""))
    cl_addr = safe(cl.get("address", ""))
    cl_cap = safe(cl.get("cap", ""))
    cl_city = safe(cl.get("city", ""))
    cl_prov = safe(cl.get("province", ""))
    cl_full = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full += f" {' '.join(parts)}"
    cl_piva = safe(cl.get("partita_iva", ""))
    cl_cf = safe(cl.get("codice_fiscale", ""))
    cl_sdi = safe(cl.get("codice_sdi", ""))
    cl_pec = safe(cl.get("pec", ""))
    cl_email = safe(cl.get("email", ""))
    lines = [
        f"AZIENDA: {company_name}",
        f"Indirizzo: {full_addr}",
    ]
    if piva:
        lines.append(f"P.IVA: {piva}")
    if cf:
        lines.append(f"Cod.Fisc.: {cf}")
    if phone:
        lines.append(f"Tel: {phone}")
    if email:
        lines.append(f"Email: {email}")
    lines.append("---")
    lines.append(f"Spett.le: {cl_name}")
    lines.append(f"Indirizzo: {cl_full}")
    if cl_piva:
        lines.append(f"P.IVA: {cl_piva}")
    if cl_cf:
        lines.append(f"Cod.Fisc.: {cl_cf}")
    if cl_sdi:
        lines.append(f"Cod.SDI: {cl_sdi}")
    if cl_pec:
        lines.append(f"PEC: {cl_pec}")
    elif cl_email:
        lines.append(f"Email: {cl_email}")
    return "\n".join(lines)


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
        "subtotal": subtotal,
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "groups": groups,
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


def format_date(date_str: str) -> str:
    """Format date string to Italian format dd/mm/yyyy."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(date_str)[:10] if date_str else ""


def build_conditions_html(company: dict, doc_number: str) -> str:
    """Build conditions page HTML for preventivo PDF."""
    company_name = safe(company.get('business_name', ''))
    return (
        '<div style="page-break-before: always; padding: 40px; font-family: Arial, sans-serif; font-size: 11px;">'
        '<h2 style="color: #1E293B; border-bottom: 2px solid #0055FF; padding-bottom: 8px;">'
        'CONDIZIONI GENERALI DI FORNITURA'
        '</h2>'
        '<p><strong>Documento:</strong> ' + safe(doc_number) + '</p>'
        '<p><strong>Azienda:</strong> ' + company_name + '</p>'
        '<div style="margin-top: 20px; line-height: 1.8;">'
        '<p><strong>1. VALIDIT&#192; DELL&#39;OFFERTA</strong><br>'
        'Il presente preventivo ha validit&#224; come indicato nel documento dalla data di emissione.</p>'
        '<p><strong>2. PREZZI</strong><br>'
        'I prezzi indicati si intendono IVA esclusa salvo diversa indicazione esplicita.</p>'
        '<p><strong>3. TEMPI DI CONSEGNA</strong><br>'
        'I tempi di consegna decorrono dalla data di conferma dell&#39;ordine e ricevimento dell&#39;acconto eventualmente previsto.</p>'
        '<p><strong>4. PAGAMENTO</strong><br>'
        'Il pagamento dovr&#224; avvenire secondo le modalit&#224; indicate nel preventivo.</p>'
        '<p><strong>5. TRASPORTO</strong><br>'
        'La merce viaggia a rischio e pericolo del committente salvo diversa indicazione.</p>'
        '<p><strong>6. FORO COMPETENTE</strong><br>'
        'Per qualsiasi controversia &#232; competente il Foro del luogo ove ha sede il fornitore.</p>'
        '</div>'
        '</div>'
    )


def _load_logo(logo_url):
    """Carica logo da base64 data URI o URL HTTP."""
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
        # Calcola proporzioni reali
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


def _sty(**kw):
    base = dict(fontName=FONT_REGULAR, fontSize=8, leading=11,
                textColor=DARK_TEXT, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle('_', **base)


# Stili condivisi
S_TITLE = _sty(fontName=FONT_BOLD, fontSize=16, leading=20, textColor=NAVY, alignment=TA_CENTER)
S_META_L = _sty(fontName=FONT_BOLD, fontSize=7.5, leading=10, textColor=GREY_TEXT)
S_META_V = _sty(fontName=FONT_BOLD, fontSize=9, leading=12, textColor=DARK_TEXT)
S_TH = _sty(fontName=FONT_BOLD, fontSize=7, leading=9, textColor=white)
S_TH_R = _sty(fontName=FONT_BOLD, fontSize=7, leading=9, textColor=white, alignment=TA_RIGHT)
S_TH_C = _sty(fontName=FONT_BOLD, fontSize=7, leading=9, textColor=white, alignment=TA_CENTER)
S_TD = _sty(fontSize=7.5, leading=10)
S_TD_R = _sty(fontSize=7.5, leading=10, alignment=TA_RIGHT)
S_TD_C = _sty(fontSize=7.5, leading=10, alignment=TA_CENTER)
S_CO_NAME = _sty(fontName=FONT_BOLD, fontSize=12, leading=15, textColor=BLUE)
S_CO_DET = _sty(fontSize=7.5, leading=10, textColor=SEC_TEXT)
S_CL_SPETT = _sty(fontSize=7.5, leading=10, textColor=GREY_TEXT)
S_CL_NAME = _sty(fontName=FONT_BOLD, fontSize=10, leading=13, textColor=DARK_TEXT)
S_CL_DET = _sty(fontSize=7.5, leading=10, textColor=SEC_TEXT)
S_SEC_TITLE = _sty(fontName=FONT_BOLD, fontSize=7.5, leading=10, textColor=BLUE)
S_SEC_TEXT = _sty(fontSize=8, leading=11, textColor=DARK_TEXT)
S_TOT_L = _sty(fontSize=8.5, leading=12, textColor=GREY_TEXT)
S_TOT_V = _sty(fontName=FONT_BOLD, fontSize=8.5, leading=12, textColor=DARK_TEXT, alignment=TA_RIGHT)
S_GRAND_L = _sty(fontName=FONT_BOLD, fontSize=11, leading=14, textColor=white)
S_GRAND_V = _sty(fontName=FONT_BOLD, fontSize=14, leading=17, textColor=white, alignment=TA_RIGHT)
S_NOTE = _sty(fontSize=7.5, leading=10, textColor=SEC_TEXT)
S_COND_TITLE = _sty(fontName=FONT_BOLD, fontSize=14, leading=18, textColor=NAVY, alignment=TA_CENTER)
S_COND_HEAD = _sty(fontName=FONT_BOLD, fontSize=8, leading=11, textColor=DARK_TEXT)
S_COND_TEXT = _sty(fontSize=7.5, leading=10, textColor=DARK_TEXT)
S_COND_LEGAL = _sty(fontSize=7, leading=9.5, textColor=SEC_TEXT)
S_FOOTER = _sty(fontSize=6.5, leading=9, textColor=GREY_TEXT, alignment=TA_CENTER)


def _blue_box(rows_content, title=''):
    """Crea un box con bordo sinistro blu."""
    rows = []
    if title:
        rows.append([Paragraph(title, S_SEC_TITLE)])
    for r in rows_content:
        if isinstance(r, Paragraph):
            rows.append([r])
        else:
            rows.append([Paragraph(str(r), S_SEC_TEXT)])
    t = Table(rows, colWidths=[USABLE_W - 8 * mm])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBEFORE', (0, 0), (0, -1), 2.5, BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _footer_canvas(canvas, doc):
    """Footer professionale su ogni pagina."""
    canvas.saveState()
    co = getattr(doc, '_company', {}) or {}
    co_name = co.get('business_name', '') or ''
    cert = co.get('certificazioni') or (
        'Azienda Certificata EN 1090-1 EXC3 \u2022 ISO 3834-2 \u2022 '
        'Centro di Trasformazione Acciaio'
    )
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    y_base = B_MARGIN - 14 * mm
    canvas.setStrokeColor(GREY_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(L_MARGIN, y_base + 10 * mm, PAGE_W - R_MARGIN, y_base + 10 * mm)
    canvas.setFont(FONT_REGULAR, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawString(L_MARGIN, y_base + 6 * mm,
                      f'Generato da {co_name} - NormaFacile')
    canvas.drawRightString(PAGE_W - R_MARGIN, y_base + 6 * mm,
                           f'Documento generato il {now_str}')
    canvas.setFont(FONT_BOLD, 6.5)
    canvas.setFillColor(BLUE)
    canvas.drawCentredString(PAGE_W / 2, y_base + 2 * mm, cert)
    canvas.setFont(FONT_REGULAR, 6.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawCentredString(PAGE_W / 2, y_base - 2 * mm,
                             f'Pagina {canvas.getPageNumber()}')
    canvas.restoreState()


def render_pdf(html_content: str, company: dict = None, doc_title: str = '') -> BytesIO:
    """Render PDF professionale da contenuto HTML strutturato.

    Parsing intelligente: rileva header azienda/cliente, meta-table, items-table,
    totali, note, condizioni e li rende con ReportLab diretto.
    """
    co = company or {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN, bottomMargin=B_MARGIN,
    )
    doc._company = co

    story = []
    clean = strip_html(html_content)
    if not clean.strip():
        story.append(Paragraph("Documento generato da Norma Facile 2.0",
                               _sty(alignment=TA_CENTER)))
        doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
        buffer.seek(0)
        return buffer

    # ── Parse strutturato ──
    sections = _parse_html_sections(html_content)

    # 1. HEADER (azienda + cliente)
    if sections.get('header_text'):
        _build_header_section(story, sections['header_text'], co)

    # 2. Separatore blu
    story.append(HRFlowable(width=USABLE_W, thickness=1.5, color=BLUE,
                            spaceBefore=2*mm, spaceAfter=3*mm))

    # 3. Titolo documento
    if sections.get('title'):
        story.append(Paragraph(sections['title'], S_TITLE))
        if sections.get('doc_num'):
            story.append(Paragraph(sections['doc_num'],
                         _sty(fontSize=10, leading=13, textColor=GREY_TEXT, alignment=TA_CENTER)))
        story.append(Spacer(1, 3*mm))

    # 4. Meta table
    if sections.get('meta_rows'):
        _build_meta_section(story, sections['meta_rows'])

    # 5. Note/riferimenti (prima della tabella)
    if sections.get('ref_notes'):
        for note in sections['ref_notes']:
            story.append(_blue_box([Paragraph(note, S_NOTE)], 'NOTE'))
            story.append(Spacer(1, 2*mm))

    # 6. Tabella articoli
    if sections.get('table_headers') and sections.get('table_rows'):
        _build_items_table(story, sections['table_headers'], sections['table_rows'])

    # 7. Note tecniche
    if sections.get('tech_notes'):
        story.append(_blue_box([Paragraph(sections['tech_notes'], S_NOTE)], 'NOTE'))
        story.append(Spacer(1, 2*mm))

    # 8. Totali
    if sections.get('totals_text'):
        _build_totals_section(story, sections['totals_text'])

    # 9. Banca
    if sections.get('bank_info'):
        story.append(_blue_box(
            [Paragraph(sections['bank_info'], S_SEC_TEXT)], 'COORDINATE BANCARIE'))
        story.append(Spacer(1, 2*mm))

    # 10. Trasporto (DDT)
    if sections.get('transport_rows'):
        _build_transport_section(story, sections['transport_rows'])

    # 11. Destinazione (DDT)
    if sections.get('destination'):
        story.append(_blue_box(
            [Paragraph(sections['destination'], S_SEC_TEXT)], 'DESTINAZIONE MERCE'))
        story.append(Spacer(1, 2*mm))

    # 12. Firme (DDT)
    if sections.get('signatures'):
        _build_signatures(story)

    # 13. Condizioni (Preventivi)
    if sections.get('conditions'):
        _build_conditions_page(story, sections['conditions'], co)

    if not story:
        story.append(Paragraph("Documento generato da Norma Facile 2.0",
                               _sty(alignment=TA_CENTER)))

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    buffer.seek(0)
    return buffer


def _parse_html_sections(html_content: str) -> dict:
    """Parsing intelligente dell'HTML generato dai vari generatori."""
    result = {
        'header_text': '', 'title': '', 'doc_num': '',
        'meta_rows': [], 'ref_notes': [], 'table_headers': [],
        'table_rows': [], 'tech_notes': '', 'totals_text': '',
        'bank_info': '', 'transport_rows': [], 'destination': '',
        'signatures': False, 'conditions': '',
    }

    # Header (testo prima del doc-title)
    header_match = re.search(r'^(.*?)(?:<div\s+class="doc-title"|<h1>)', html_content, re.DOTALL)
    if header_match:
        result['header_text'] = strip_html(header_match.group(1))

    # Titolo
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
    if title_match:
        result['title'] = strip_html(title_match.group(1))

    # Doc num
    num_match = re.search(r'<div\s+class="doc-num">(.*?)</div>', html_content, re.DOTALL)
    if num_match:
        result['doc_num'] = strip_html(num_match.group(1))

    # Meta table
    meta_match = re.search(r'<table\s+class="meta-table">(.*?)</table>', html_content, re.DOTALL)
    if meta_match:
        rows = re.findall(r'<tr>(.*?)</tr>', meta_match.group(1), re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 2:
                label = strip_html(cells[0])
                value = strip_html(cells[1])
                if label and value:
                    result['meta_rows'].append((label, value))

    # Ref/note prima della tabella
    ref_notes = re.findall(r'<p\s+class="ref-note">(.*?)</p>', html_content, re.DOTALL)
    for rn in ref_notes:
        clean = strip_html(rn)
        if clean:
            result['ref_notes'].append(clean)

    # Items table
    items_match = re.search(r'<table\s+class="items-table">(.*?)</table>', html_content, re.DOTALL)
    if items_match:
        table_html = items_match.group(1)
        # Headers
        thead_match = re.search(r'<thead>(.*?)</thead>', table_html, re.DOTALL)
        if thead_match:
            ths = re.findall(r'<th[^>]*>(.*?)</th>', thead_match.group(1), re.DOTALL)
            result['table_headers'] = [html_mod.unescape(strip_html(h)) for h in ths]
        # Body rows
        tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL)
        if tbody_match:
            rows = re.findall(r'<tr>(.*?)</tr>', tbody_match.group(1), re.DOTALL)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                result['table_rows'].append(
                    [html_mod.unescape(strip_html(c)) for c in cells])

    # Tech notes / info-box
    info_boxes = re.findall(r'<div\s+class="info-box">(.*?)</div>', html_content, re.DOTALL)
    for box in info_boxes:
        clean = strip_html(box)
        if 'Note:' in clean or 'note:' in clean:
            result['tech_notes'] = clean

    # Totals (testo dopo la tabella articoli, prima di bank/condizioni)
    totals_pattern = re.search(
        r'(?:</table>.*?)((?:Imponibile|TOTALE|IVA|Sconto|SALDO|Acconto).*?)(?:<div|$)',
        html_content, re.DOTALL)
    if totals_pattern:
        result['totals_text'] = strip_html(totals_pattern.group(1))

    # Bank
    bank_match = re.search(r'<div\s+class="bank-info">(.*?)</div>', html_content, re.DOTALL)
    if bank_match:
        result['bank_info'] = strip_html(bank_match.group(1))

    # Transport table
    transport_match = re.search(r'<table\s+class="transport-table">(.*?)</table>',
                                html_content, re.DOTALL)
    if transport_match:
        rows = re.findall(r'<tr>(.*?)</tr>', transport_match.group(1), re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            pairs = []
            for i in range(0, len(cells) - 1, 2):
                label = strip_html(cells[i])
                value = strip_html(cells[i+1]) if i+1 < len(cells) else ''
                pairs.append((label, value))
            if pairs:
                result['transport_rows'].append(pairs)

    # Destination
    dest_match = re.search(r'DESTINAZIONE MERCE.*?</div>', html_content, re.DOTALL)
    if dest_match:
        result['destination'] = strip_html(dest_match.group(0)).replace('DESTINAZIONE MERCE', '').strip()

    # Signatures
    if 'signatures-row' in html_content or 'Firma mittente' in html_content:
        result['signatures'] = True

    # Conditions page
    cond_match = re.search(r'page-break-before.*?$', html_content, re.DOTALL)
    if cond_match:
        result['conditions'] = cond_match.group(0)

    return result


def _build_header_section(story, header_text, company):
    """Costruisce header con logo + azienda a sx, cliente a dx."""
    parts = header_text.split('---')
    co_text = parts[0].strip() if parts else ''
    cl_text = parts[1].strip() if len(parts) > 1 else ''

    # Logo
    logo = _load_logo(company.get('logo_url', ''))

    # Colonna azienda
    co_paras = []
    for line in co_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('AZIENDA:'):
            co_paras.append(Paragraph(line.replace('AZIENDA: ', ''), S_CO_NAME))
        else:
            co_paras.append(Paragraph(line, S_CO_DET))

    # Colonna cliente
    cl_paras = []
    for line in cl_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('Spett.le:'):
            cl_paras.append(Paragraph('Spett.le', S_CL_SPETT))
            name = line.replace('Spett.le: ', '').strip()
            if name:
                cl_paras.append(Paragraph(name, S_CL_NAME))
        else:
            cl_paras.append(Paragraph(line, S_CL_DET))

    # Layout: [Logo + Azienda] a sx | [Cliente] a dx
    left_content = []
    if logo:
        left_content.append(logo)
        left_content.append(Spacer(1, 2*mm))
    left_content.extend(co_paras)

    right_content = cl_paras

    hdr = Table(
        [[left_content, right_content]],
        colWidths=[USABLE_W * 0.55, USABLE_W * 0.45]
    )
    hdr.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 2*mm))


def _build_meta_section(story, meta_rows):
    """Costruisce box meta (DATA, Pagamento, ecc.) con sfondo grigio."""
    rows = []
    for label, value in meta_rows:
        rows.append([
            Paragraph(label, S_META_L),
            Paragraph(value, S_META_V),
        ])
    if rows:
        meta = Table(rows, colWidths=[USABLE_W * 0.30, USABLE_W * 0.70])
        meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREY_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, GREY_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta)
        story.append(Spacer(1, 4*mm))


def _build_items_table(story, headers, rows):
    """Costruisce tabella articoli con header navy e zebra striping."""
    n_cols = len(headers)
    # Header row
    th_styles = []
    for i, h in enumerate(headers):
        if h.lower() in ('codice', 'u.m.', 'iva', 'sconti'):
            th_styles.append(Paragraph(h, S_TH_C))
        elif h.lower() in ('prezzo', 'importo', 'totale'):
            th_styles.append(Paragraph(h, S_TH_R))
        elif h.lower() in ('quantit\u00e0', 'q.t\u00e0'):
            th_styles.append(Paragraph(h, S_TH_R))
        else:
            th_styles.append(Paragraph(h, S_TH))

    table_data = [th_styles]

    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < n_cols:
                h = headers[i].lower() if i < len(headers) else ''
                if h in ('prezzo', 'importo', 'totale', 'quantit\u00e0', 'q.t\u00e0'):
                    cells.append(Paragraph(cell, S_TD_R))
                elif h in ('codice', 'u.m.', 'iva', 'sconti'):
                    cells.append(Paragraph(cell, S_TD_C))
                else:
                    cells.append(Paragraph(cell, S_TD))
        # Pad se serve
        while len(cells) < n_cols:
            cells.append(Paragraph('', S_TD))
        table_data.append(cells)

    # Calcola larghezze colonne
    if n_cols == 8:
        col_widths = [USABLE_W * w for w in [0.08, 0.34, 0.06, 0.08, 0.12, 0.08, 0.12, 0.08]]
    elif n_cols == 5:
        col_widths = [USABLE_W * w for w in [0.44, 0.10, 0.18, 0.10, 0.18]]
    elif n_cols == 4:
        col_widths = [USABLE_W * w for w in [0.10, 0.55, 0.15, 0.20]]
    else:
        col_widths = [USABLE_W / n_cols] * n_cols

    it = Table(table_data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, GREY_BORDER),
    ])
    for i in range(2, len(table_data), 2):
        ts.add('BACKGROUND', (0, i), (-1, i), ZEBRA)
    it.setStyle(ts)
    story.append(it)
    story.append(Spacer(1, 4*mm))


def _build_totals_section(story, totals_text):
    """Costruisce sezione totali con box navy per TOTALE."""
    lines = [l.strip() for l in totals_text.strip().split('\n') if l.strip()]
    sub_rows = []
    grand_total_line = None
    saldo_line = None

    for line in lines:
        if line.startswith('TOTALE DOCUMENTO:') or line.startswith('TOTALE:'):
            grand_total_line = line
        elif line.startswith('SALDO:'):
            saldo_line = line
        else:
            parts = line.split(':', 1)
            if len(parts) == 2:
                sub_rows.append([
                    Paragraph(parts[0].strip() + ':', S_TOT_L),
                    Paragraph(parts[1].strip(), S_TOT_V),
                ])

    tw = 80 * mm
    if sub_rows:
        sub_t = Table(sub_rows, colWidths=[tw * 0.55, tw * 0.45])
        sub_t.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]))
        wrapper_rows = [[Spacer(1, 1), sub_t]]
    else:
        wrapper_rows = []

    if grand_total_line:
        val = grand_total_line.split(':', 1)[1].strip() if ':' in grand_total_line else ''
        grand_t = Table(
            [[Paragraph('TOTALE:', S_GRAND_L), Paragraph(val, S_GRAND_V)]],
            colWidths=[tw * 0.55, tw * 0.45])
        grand_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        wrapper_rows.append([Spacer(1, 1), grand_t])

    if saldo_line:
        val = saldo_line.split(':', 1)[1].strip() if ':' in saldo_line else ''
        saldo_t = Table(
            [[Paragraph('SALDO:', S_GRAND_L), Paragraph(val, S_GRAND_V)]],
            colWidths=[tw * 0.55, tw * 0.45])
        saldo_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        wrapper_rows.append([Spacer(1, 1), saldo_t])

    if wrapper_rows:
        wrapper = Table(wrapper_rows, colWidths=[USABLE_W - tw, tw])
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


def _build_transport_section(story, transport_rows):
    """Sezione trasporto per DDT."""
    story.append(Paragraph('DATI TRASPORTO', S_SEC_TITLE))
    story.append(Spacer(1, 2*mm))
    rows = []
    for pair_list in transport_rows:
        row = []
        for label, value in pair_list:
            row.append(Paragraph(f'<b>{label}</b>', S_TD))
            row.append(Paragraph(value, S_TD))
        rows.append(row)
    if rows:
        n_cols = max(len(r) for r in rows)
        col_w = USABLE_W / n_cols
        t = Table(rows, colWidths=[col_w] * n_cols)
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, GREY_BORDER),
            ('BACKGROUND', (0, 0), (-1, -1), GREY_BG),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 3*mm))


def _build_signatures(story):
    """Sezione firme per DDT."""
    story.append(Spacer(1, 10*mm))
    sigs = Table(
        [[Paragraph('<b>Firma mittente</b>', _sty(alignment=TA_CENTER)),
          Paragraph('<b>Firma vettore</b>', _sty(alignment=TA_CENTER)),
          Paragraph('<b>Firma destinatario</b>', _sty(alignment=TA_CENTER))]],
        colWidths=[USABLE_W/3]*3,
    )
    sigs.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(sigs)


def _build_conditions_page(story, conditions_html, company):
    """Pagina condizioni generali di vendita per preventivi."""
    story.append(PageBreak())
    story.append(Paragraph('CONDIZIONI GENERALI DI FORNITURA', S_COND_TITLE))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=USABLE_W, thickness=1, color=BLUE, spaceAfter=4*mm))

    co_name = company.get('business_name', '') or ''
    # Custom condizioni from company settings
    cond_text = company.get('condizioni_vendita', '') or ''
    if cond_text.strip():
        for line in cond_text.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 2*mm))
            elif re.match(r'^\d+[.)-]', line):
                story.append(Paragraph(line, S_COND_HEAD))
            else:
                story.append(Paragraph(line, S_COND_TEXT))
        story.append(Spacer(1, 4*mm))
    else:
        # Condizioni standard dal HTML
        clean = strip_html(conditions_html)
        for line in clean.split('\n'):
            line = line.strip()
            if not line or 'page-break' in line:
                continue
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                story.append(Paragraph(line, S_COND_HEAD))
            elif 'CONDIZIONI' in line:
                continue  # Skip duplicated title
            else:
                story.append(Paragraph(line, S_COND_TEXT))
        story.append(Spacer(1, 4*mm))

    # Sezione firma
    story.append(Paragraph('<b>Firma e timbro per accettazione</b>', S_COND_TEXT))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=180, thickness=0.5, color=GREY_BORDER))
    story.append(Paragraph('Data di accettazione ___/___/___', S_COND_LEGAL))
    story.append(Paragraph('(legale rappresentante)', S_COND_LEGAL))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        "Ai sensi e per gli effetti dell'Art. 1341 e segg. del Codice Civile, "
        "il sottoscritto Acquirente dichiara di aver preso specifica, precisa e "
        "dettagliata visione di tutte le disposizioni del contratto e di approvarle "
        "integralmente senza alcuna riserva.",
        S_COND_LEGAL,
    ))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('_____________________, l\u00ec ______________________', S_COND_TEXT))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=180, thickness=0.5, color=GREY_BORDER))
    story.append(Paragraph('Firma e timbro (il legale rappresentante)', S_COND_LEGAL))

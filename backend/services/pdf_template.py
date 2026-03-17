"""PDF Template - NormaFacile 2.0 - HTML/CSS con xhtml2pdf"""
from io import BytesIO


def fmt_it(n) -> str:
    try:
        return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(n or "0,00")


def safe(val) -> str:
    if val is None:
        return ""
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_html(text: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', text or '')


def format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(date_str)[:10] if date_str else ""


CSS = """
@page {
    size: A4;
    margin: 15mm 18mm 18mm 18mm;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9.5px;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}
.header-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
}
.company-box {
    width: 50%;
    vertical-align: top;
    padding-right: 10px;
}
.client-box {
    width: 50%;
    vertical-align: top;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 8px 10px;
    border-radius: 3px;
}
.company-name {
    font-size: 13px;
    font-weight: bold;
    color: #1a56db;
    margin-bottom: 3px;
}
.company-detail {
    font-size: 8.5px;
    color: #555;
    line-height: 1.5;
}
.piva-bold {
    font-weight: bold;
    font-size: 9px;
}
.client-label {
    font-size: 8px;
    color: #888;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.client-name {
    font-size: 11px;
    font-weight: bold;
    color: #1E293B;
}
.client-detail {
    font-size: 8.5px;
    color: #555;
    line-height: 1.5;
}
.doc-title-bar {
    background: #1a56db;
    color: white;
    padding: 6px 12px;
    margin-bottom: 10px;
    display: table;
    width: 100%;
    box-sizing: border-box;
}
.doc-title {
    font-size: 13px;
    font-weight: bold;
    display: table-cell;
    vertical-align: middle;
}
.doc-number {
    font-size: 13px;
    font-weight: bold;
    display: table-cell;
    text-align: right;
    vertical-align: middle;
}
.meta-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 8.5px;
}
.meta-table td {
    padding: 2px 6px;
    vertical-align: top;
}
.meta-label {
    font-weight: bold;
    color: #555;
    width: 100px;
}
.lines-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 8.5px;
}
.lines-table th {
    background: #1E293B;
    color: white;
    padding: 4px 5px;
    text-align: left;
    font-size: 8px;
    font-weight: bold;
}
.lines-table th.tr { text-align: right; }
.lines-table th.tc { text-align: center; }
.lines-table td {
    padding: 4px 5px;
    border-bottom: 1px solid #e9ecef;
    vertical-align: top;
}
.lines-table tr:nth-child(even) td { background: #f8f9fa; }
.tc { text-align: center; }
.tr { text-align: right; }
.desc-cell { max-width: 200px; }
.totals-table {
    width: 220px;
    margin-left: auto;
    border-collapse: collapse;
    font-size: 9px;
    margin-bottom: 10px;
}
.totals-table td {
    padding: 2px 5px;
}
.totals-table .label { color: #555; }
.totals-table .value { text-align: right; font-family: monospace; }
.total-final {
    font-size: 11px;
    font-weight: bold;
    color: #1a56db;
    border-top: 2px solid #1a56db;
    padding-top: 3px;
}
.notes-box {
    background: #f8f9fa;
    border-left: 3px solid #1a56db;
    padding: 6px 10px;
    font-size: 8.5px;
    margin-bottom: 10px;
    color: #444;
}
.bank-box {
    background: #f0f4ff;
    border: 1px solid #c7d7ff;
    padding: 6px 10px;
    font-size: 8.5px;
    margin-bottom: 10px;
    border-radius: 3px;
}
.section-title {
    font-size: 9px;
    font-weight: bold;
    color: #1a56db;
    text-transform: uppercase;
    margin-bottom: 3px;
}
"""


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

    return f"""
    <table class="header-table" style="width:100%; border-collapse:collapse; margin-bottom:12px;">
      <tr>
        <td class="company-box" style="width:50%; vertical-align:top; padding-right:10px;">
          {"<img src='" + safe(co.get('logo_url','')) + "' style='max-height:50px; max-width:120px; margin-bottom:6px;'><br>" if co.get('logo_url') else ""}
                    {co.get('logo_url','').__len__() > 0 and '<img src="' + co.get('logo_url','') + '" style="max-height:50px; max-width:120px; margin-bottom:4px; display:block;">' or ''}
          <div class="company-name" style="font-size:13px; font-weight:bold; color:#1a56db; margin-bottom:3px;">{company_name}</div>
          <div class="company-detail" style="font-size:8.5px; color:#555; line-height:1.5;">
            {full_addr}<br>
            {"<b>P.IVA: " + piva + "</b><br>" if piva else ""}
            {"Cod.Fisc.: " + cf + "<br>" if cf else ""}
            {"Tel: " + phone + "<br>" if phone else ""}
            {"Email: " + email if email else ""}
          </div>
        </td>
        <td class="client-box" style="width:50%; vertical-align:top; background:#f8f9fa; border:1px solid #dee2e6; padding:8px 10px;">
          <div style="font-size:8px; color:#888; text-transform:uppercase; margin-bottom:4px;">Spett.le</div>
          <div class="client-name" style="font-size:11px; font-weight:bold; color:#1E293B;">{cl_name}</div>
          <div class="client-detail" style="font-size:8.5px; color:#555; line-height:1.5;">
            {cl_full}<br>
            {"<b>P.IVA: " + cl_piva + "</b><br>" if cl_piva else ""}
            {"Cod.Fisc.: " + cl_cf + "<br>" if cl_cf else ""}
            {"Cod.SDI: " + cl_sdi + "<br>" if cl_sdi else ""}
            {"PEC: " + cl_pec if cl_pec else ("Email: " + cl_email if cl_email else "")}
          </div>
        </td>
      </tr>
    </table>
    """


def compute_iva_groups(lines: list, sconto_globale: float = 0) -> dict:
    subtotal = sum(float(ln.get("line_total") or 0) for ln in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)
    groups = {}
    for ln in lines:
        rate_str = str(ln.get("vat_rate", "22"))
        base = float(ln.get("line_total") or 0)
        if sconto_globale and subtotal > 0:
            base = round(base * (1 - sconto_globale / 100), 2)
        if rate_str not in groups:
            groups[rate_str] = {"base": 0, "iva": 0}
        groups[rate_str]["base"] = round(groups[rate_str]["base"] + base, 2)
        groups[rate_str]["iva"] = round(groups[rate_str]["iva"] + base * float(rate_str) / 100, 2)
    return {
        "groups": groups,
        "subtotal": subtotal,
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "total_iva": round(sum(g["iva"] for g in groups.values()), 2),
        "total": round(imponibile + sum(g["iva"] for g in groups.values()), 2),
    }


def build_totals_html(iva_data: dict, acconto: float = 0) -> str:
    rows = ""
    if iva_data.get("sconto_val", 0) > 0:
        rows += f'<tr><td class="label">Totale senza IVA</td><td class="value">{fmt_it(iva_data["subtotal"])} &euro;</td></tr>'
        rows += f'<tr><td class="label">Sconto</td><td class="value">- {fmt_it(iva_data["sconto_val"])} &euro;</td></tr>'
    rows += f'<tr><td class="label">Imponibile</td><td class="value">{fmt_it(iva_data["imponibile"])} &euro;</td></tr>'
    for rate, g in iva_data.get("groups", {}).items():
        rows += f'<tr><td class="label">IVA {rate}%</td><td class="value">{fmt_it(g["iva"])} &euro;</td></tr>'
    rows += f'<tr><td class="label total-final">TOTALE</td><td class="value total-final">{fmt_it(iva_data["total"])} &euro;</td></tr>'
    if acconto:
        da_pagare = round(iva_data["total"] - acconto, 2)
        rows += f'<tr><td class="label">Acconto</td><td class="value">- {fmt_it(acconto)} &euro;</td></tr>'
        rows += f'<tr><td class="label total-final">DA PAGARE</td><td class="value total-final">{fmt_it(da_pagare)} &euro;</td></tr>'
    return f'<table class="totals-table">{rows}</table>'


def build_conditions_html(company: dict, doc_number: str) -> str:
    """Condizioni di fornitura reali dalle impostazioni aziendali."""
    company_name = safe((company or {}).get('business_name', ''))
    condizioni = (company or {}).get('condizioni_vendita', '').strip()
    
    def fix_encoding(text):
        """Corregge caratteri mal codificati."""
        return (text
            .replace('\u00e2\u0080\u0099', "'")
            .replace('\u00e2\u0080\u009c', '"')
            .replace('\u00e2\u0080\u009d', '"')
            .replace('\u00e0', 'Ã ').replace('\u00e8', 'Ã¨')
            .replace('\u00e9', 'Ã©').replace('\u00ec', 'Ã¬')
            .replace('\u00f2', 'Ã²').replace('\u00f9', 'Ã¹')
            .replace('\u00c0', 'Ã').replace('\u00c8', 'Ã')
            .replace('Ã ', 'Ã ').replace('ÃÂ¨', 'Ã¨').replace('ÃÂ©', 'Ã©')
            .replace('ÃÂ¬', 'Ã¬').replace('ÃÂ²', 'Ã²').replace('ÃÂ¹', 'Ã¹')
            .replace('Ã¢\x80\x99', "'").replace('Ã¢\x80\x9c', '"')
            .replace('Ã¢\x80\x9d', '"').replace('Ã¢\x80\x93', 'â')
            .replace('\u2013', 'â').replace('\u2014', 'â')
        )
    
    if condizioni:
        condizioni = fix_encoding(condizioni)
        lines_html = ''
        for line in condizioni.split('\n'):
            line = line.strip()
            if not line:
                lines_html += '<p style="margin:2px 0">&nbsp;</p>'
            else:
                lines_html += f'<p style="margin:2px 0">{safe(line)}</p>'
    else:
        lines_html = '<p>Le condizioni di vendita non sono state configurate nelle Impostazioni.</p>'
    
    return f"""<div style="page-break-before: always; padding: 10px; font-size: 9px; font-family: Helvetica, Arial, sans-serif;">
        <h3 style="color: #1a56db; border-bottom: 2px solid #1a56db; padding-bottom: 5px; margin-bottom: 8px;">CONDIZIONI GENERALI DI FORNITURA</h3>
        <p style="font-size:8px; color:#888; margin-bottom:8px">Documento: {safe(doc_number)} &mdash; Azienda: {company_name}</p>
        <div style="line-height: 1.6;">{lines_html}</div>
    </div>"""


def render_pdf(html_content: str) -> BytesIO:
    import io
    import base64
    import re
    from lxml import html as lxml_html
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

    def decode_base64_image(base64_string):
        try:
            if "base64," in base64_string:
                base64_string = base64_string.split("base64,")[1]
            img_data = base64.b64decode(base64_string)
            return BytesIO(img_data)
        except Exception:
            return None

    def fix_text(t):
        t = str(t or '')
        return (t
            .replace('\u00e2\u0080\u0099', "'")
            .replace('\u00e0', 'à').replace('\u00e8', 'è').replace('\u00e9', 'é')
            .replace('\u00ec', 'ì').replace('\u00f2', 'ò').replace('\u00f9', 'ù')
            .replace('Ã ', 'à').replace('Ã¨', 'è').replace('Ã©', 'é')
            .replace('Ã¬', 'ì').replace('Ã²', 'ò').replace('Ã¹', 'ù')
            .replace('â\x80\x99', "'").replace('â\x80\x93', '–')
            .replace('&agrave;', 'à').replace('&egrave;', 'è').replace('&igrave;', 'ì')
            .replace('&ograve;', 'ò').replace('&ugrave;', 'ù').replace('&amp;', '&')
            .replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
            .replace('&mdash;', '—').replace('&ndash;', '–').strip()
        )

    def get_text(el):
        if el is None: return ''
        return fix_text(' '.join(el.itertext()))

    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')

    tree = lxml_html.fromstring(f'<html><body>{html_content}</body></html>')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=18*cm/10, leftMargin=18*cm/10,
        topMargin=15*cm/10, bottomMargin=20*cm/10)

    BLUE  = colors.HexColor('#1a56db')
    DARK  = colors.HexColor('#1E293B')
    GRAY  = colors.HexColor('#F8F9FA')
    BORDER= colors.HexColor('#DEE2E6')
    WHITE = colors.white
    GTXT  = colors.HexColor('#6B7280')
    W = A4[0] - 36*cm/10

    styles = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    N   = S('N',   fontSize=9,  leading=13)
    B   = S('B',   fontSize=9,  leading=13, fontName='Helvetica-Bold')
    SM  = S('SM',  fontSize=8,  leading=11, textColor=GTXT)
    SMB = S('SMB', fontSize=8,  leading=11, fontName='Helvetica-Bold', textColor=GTXT)
    CO  = S('CO',  fontSize=12, leading=15, fontName='Helvetica-Bold', textColor=BLUE)
    CL  = S('CL',  fontSize=11, leading=14, fontName='Helvetica-Bold', textColor=DARK)
    BIG = S('BIG', fontSize=18, leading=22, fontName='Helvetica-Bold', textColor=BLUE, alignment=TA_CENTER)
    TH  = S('TH',  fontSize=8,  leading=11, fontName='Helvetica-Bold', textColor=WHITE)
    THR = S('THR', fontSize=8,  leading=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT)
    THC = S('THC', fontSize=8,  leading=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    TD  = S('TD',  fontSize=8.5, leading=12)
    TDR = S('TDR', fontSize=8.5, leading=12, alignment=TA_RIGHT)
    TDC = S('TDC', fontSize=8.5, leading=12, alignment=TA_CENTER)
    TL  = S('TL',  fontSize=9,  leading=13, textColor=GTXT)
    TV  = S('TV',  fontSize=9,  leading=13, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    GL  = S('GL',  fontSize=11, leading=14, fontName='Helvetica-Bold', textColor=WHITE)
    GV  = S('GV',  fontSize=11, leading=14, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT)
    MLB = S('MLB', fontSize=8,  leading=10, fontName='Helvetica-Bold', textColor=GTXT)
    BLB = S('BLB', fontSize=10, leading=13, fontName='Helvetica-Bold', textColor=BLUE)

    from reportlab.platypus import HRFlowable
    elements = []

    # 1. HEADER
    img_tags = tree.xpath('//img/@src')
    logo_el = None
    if img_tags:
        img_stream = decode_base64_image(img_tags[0])
        if img_stream:
            try:
                logo_el = Image(img_stream, width=3*cm, height=1.5*cm)
                logo_el.hAlign = 'LEFT'
            except Exception:
                logo_el = None

    co_name_els = tree.xpath("//div[@class='company-name']")
    co_name = get_text(co_name_els[0]) if co_name_els else ''
    co_det_els = tree.xpath("//div[@class='company-detail']")
    co_detail_lines = []
    if co_det_els:
        for br in co_det_els[0].findall('.//br'):
            br.tail = '\n' + (br.tail or '')
        raw = fix_text('\n'.join(co_det_els[0].itertext()))
        co_detail_lines = [l.strip() for l in raw.split('\n') if l.strip()]

    cl_name_els = tree.xpath("//div[@class='client-name']")
    cl_name = get_text(cl_name_els[0]) if cl_name_els else ''
    cl_det_els = tree.xpath("//div[@class='client-detail']")
    cl_detail_lines = []
    if cl_det_els:
        for br in cl_det_els[0].findall('.//br'):
            br.tail = '\n' + (br.tail or '')
        raw = fix_text('\n'.join(cl_det_els[0].itertext()))
        cl_detail_lines = [l.strip() for l in raw.split('\n') if l.strip()]

    co_col = []
    if logo_el: co_col.append(logo_el)
    if co_name: co_col.append(Paragraph(co_name, CO))
    for line in co_detail_lines:
        co_col.append(Paragraph(line, B if ('P.IVA' in line or 'Cod.Fisc' in line) else SM))

    cl_col = [Paragraph('Spett.le', SMB)]
    if cl_name: cl_col.append(Paragraph(cl_name, CL))
    for line in cl_detail_lines:
        cl_col.append(Paragraph(line, B if ('P.IVA' in line or 'Cod.Fisc' in line) else SM))

    hdr = Table([[co_col, cl_col]], colWidths=[W*0.55, W*0.43])
    hdr.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (0,0),   0),
        ('RIGHTPADDING', (0,0), (0,0),   6),
        ('LEFTPADDING',  (1,0), (1,0),   10),
        ('TOPPADDING',   (1,0), (1,0),   6),
        ('BOTTOMPADDING',(1,0), (1,0),   6),
        ('BACKGROUND',   (1,0), (1,0),   GRAY),
        ('BOX',          (1,0), (1,0),   0.5, BORDER),
    ]))
    elements.append(hdr)
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=6))

    # 2. TITOLO
    title_div = tree.xpath("//div[@class='doc-title']")
    if title_div:
        all_txt = [fix_text(t) for t in title_div[0].itertext() if fix_text(t).strip()]
        title_text = '  '.join(all_txt).strip()
        if title_text:
            elements.append(Paragraph(title_text, BIG))
            elements.append(Spacer(1, 4))

    # 3. META TABLE
    meta_rows = tree.xpath("//table[@class='meta-table']//tr")
    meta_data = []
    for tr in meta_rows:
        tds = tr.xpath('./td')
        if len(tds) >= 2:
            meta_data.append([Paragraph(fix_text(tds[0].text_content()), MLB),
                               Paragraph(fix_text(tds[1].text_content()), N)])
    if meta_data:
        half = (len(meta_data)+1)//2
        left, right = meta_data[:half], meta_data[half:]
        while len(right) < len(left): right.append([Paragraph('',N), Paragraph('',N)])
        rows = [left[i] + [Spacer(4,1)] + right[i] for i in range(len(left))]
        mt = Table(rows, colWidths=[W*0.17, W*0.30, W*0.06, W*0.17, W*0.30])
        mt.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), GRAY),
            ('BOX',          (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING',   (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
            ('LEFTPADDING',  (0,0), (-1,-1), 5),
        ]))
        elements.append(mt)
        elements.append(Spacer(1, 6))

    # 4. REF NOTE
    ref_els = tree.xpath("//*[contains(@class,'ref-note')]")
    if ref_els:
        elements.append(Paragraph(fix_text(ref_els[0].text_content()), N))
        elements.append(Spacer(1, 4))

    # 5. TABELLA RIGHE
    items_tbl = tree.xpath("//table[@class='items-table']")
    if items_tbl:
        thead = items_tbl[0].xpath('.//thead/tr/th')
        tbody = items_tbl[0].xpath('.//tbody/tr')
        n = len(thead) if thead else 8
        col_w = [W*0.08, W*0.36, W*0.06, W*0.08, W*0.12, W*0.08, W*0.12, W*0.08][:n]
        while len(col_w) < n: col_w.append(W*0.10)
        th_styles = [TH, TH, THC, THR, THR, THC, THR, THC]
        table_data = [[Paragraph(fix_text(th.text_content()), th_styles[i] if i < len(th_styles) else TH) for i, th in enumerate(thead)]] if thead else []
        for tr in tbody:
            tds = tr.xpath('./td')
            row = []
            for j, td in enumerate(tds):
                txt = fix_text(td.text_content())
                if   j == 1: row.append(Paragraph(txt, TD))
                elif j in (3,4,6): row.append(Paragraph(txt, TDR))
                elif j in (2,5,7): row.append(Paragraph(txt, TDC))
                else: row.append(Paragraph(txt, TD))
            while len(row) < n: row.append(Paragraph('', TD))
            table_data.append(row[:n])
        if table_data:
            it = Table(table_data, colWidths=col_w)
            ts = TableStyle([
                ('BACKGROUND',   (0,0),  (-1,0),  DARK),
                ('TEXTCOLOR',    (0,0),  (-1,0),  WHITE),
                ('TOPPADDING',   (0,0),  (-1,0),  5),
                ('BOTTOMPADDING',(0,0),  (-1,0),  5),
                ('TOPPADDING',   (0,1),  (-1,-1), 3),
                ('BOTTOMPADDING',(0,1),  (-1,-1), 3),
                ('LEFTPADDING',  (0,0),  (-1,-1), 4),
                ('RIGHTPADDING', (0,0),  (-1,-1), 4),
                ('VALIGN',       (0,0),  (-1,-1), 'TOP'),
                ('LINEBELOW',    (0,1),  (-1,-1), 0.3, BORDER),
            ])
            for i in range(1, len(table_data), 2):
                ts.add('BACKGROUND', (0,i), (-1,i), GRAY)
            it.setStyle(ts)
            elements.append(it)
            elements.append(Spacer(1, 6))

    # 6. INFO BOX
    for info_el in tree.xpath("//*[contains(@class,'info-box')]"):
        txt = fix_text(info_el.text_content())
        ib = Table([[Paragraph(txt, N)]], colWidths=[W])
        ib.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (0,0), GRAY),
            ('LINEBEFORE',   (0,0), (0,-1), 3, BLUE),
            ('LEFTPADDING',  (0,0), (0,0), 10),
            ('TOPPADDING',   (0,0), (0,0), 6),
            ('BOTTOMPADDING',(0,0), (0,0), 6),
        ]))
        elements.append(ib)
        elements.append(Spacer(1, 4))

    # 7. TOTALI
    tot_rows = []
    grand = None
    for tr in tree.xpath('.//tr'):
        tds = tr.xpath('./td')
        if len(tds) >= 2:
            label = fix_text(tds[0].text_content()).strip()
            val   = fix_text(tds[-1].text_content()).strip()
            if not label or not val: continue
            if 'TOTALE' in label.upper() and 'IVA' not in label.upper():
                grand = (label, val)
            elif any(k in label for k in ('Imponibile','IVA','Acconto','Da pagare','Sconto')):
                tot_rows.append((label, val))
    if tot_rows:
        data = [[Paragraph('', N), Paragraph(lbl, TL), Paragraph(v, TV)] for lbl, v in tot_rows]
        tt = Table(data, colWidths=[W*0.35, W*0.40, W*0.23])
        tt.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('ALIGN',(2,0),(2,-1),'RIGHT')]))
        elements.append(tt)
    if grand:
        gt = Table([[Paragraph('', N), Paragraph(grand[0], GL), Paragraph(grand[1], GV)]], colWidths=[W*0.35, W*0.40, W*0.23])
        gt.setStyle(TableStyle([('BACKGROUND',(1,0),(2,0),BLUE),('TOPPADDING',(1,0),(2,0),6),('BOTTOMPADDING',(1,0),(2,0),6),('LEFTPADDING',(1,0),(1,0),8),('RIGHTPADDING',(2,0),(2,0),8)]))
        elements.append(Spacer(1, 2))
        elements.append(gt)
    elements.append(Spacer(1, 8))

    # 8. BANCA
    bank_els = tree.xpath("//*[contains(@class,'bank-info')]")
    if bank_els:
        for br in bank_els[0].findall('.//br'):
            br.tail = '\n' + (br.tail or '')
        lines_b = [fix_text(l) for l in bank_els[0].text_content().split('\n') if fix_text(l)]
        bt = Table([[Paragraph('  '.join(lines_b), B)]], colWidths=[W])
        bt.setStyle(TableStyle([('LINEBEFORE',(0,0),(0,-1),3,BLUE),('BACKGROUND',(0,0),(0,0),GRAY),('LEFTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(0,0),6),('BOTTOMPADDING',(0,0),(0,0),6)]))
        elements.append(bt)
        elements.append(Spacer(1, 6))

    # 9. CONDIZIONI
    cond_els = tree.xpath("//*[contains(@style,'page-break')]")
    if not cond_els:
        cond_els = tree.xpath("//*[contains(@class,'conditions-page')]")
    if cond_els:
        elements.append(PageBreak())
        elements.append(Paragraph('CONDIZIONI GENERALI DI FORNITURA', BLB))
        elements.append(HRFlowable(width='100%', thickness=1, color=BLUE, spaceAfter=6))
        import re as _re
        for line in fix_text(cond_els[0].text_content()).split('\n'):
            line = line.strip()
            if not line or 'CONDIZIONI GENERALI' in line.upper(): continue
            if _re.match(r'^\d+', line):
                elements.append(Spacer(1, 3))
                elements.append(Paragraph(line, B))
            else:
                elements.append(Paragraph(line, N))

    doc.build(elements)
    buffer.seek(0)
    return buffer

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
    color: #0055FF;
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
    background: #0055FF;
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
    color: #0055FF;
    border-top: 2px solid #0055FF;
    padding-top: 3px;
}
.notes-box {
    background: #f8f9fa;
    border-left: 3px solid #0055FF;
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
    color: #0055FF;
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
    <table class="header-table">
      <tr>
        <td class="company-box">
          <div class="company-name">{company_name}</div>
          <div class="company-detail">
            {full_addr}<br>
            {"<span class='piva-bold'>P.IVA: " + piva + "</span><br>" if piva else ""}
            {"Cod.Fisc.: " + cf + "<br>" if cf else ""}
            {"Tel: " + phone + "<br>" if phone else ""}
            {"Email: " + email if email else ""}
          </div>
        </td>
        <td class="client-box">
          <div class="client-label">Destinatario</div>
          <div class="client-name">{cl_name}</div>
          <div class="client-detail">
            {cl_full}<br>
            {"<span class='piva-bold'>P.IVA: " + cl_piva + "</span><br>" if cl_piva else ""}
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
    company_name = safe((company or {}).get('business_name', ''))
    return f"""
    <div style="page-break-before: always; padding: 10px; font-size: 9px;">
        <h3 style="color: #0055FF; border-bottom: 2px solid #0055FF; padding-bottom: 5px;">CONDIZIONI GENERALI DI FORNITURA</h3>
        <p><strong>Documento:</strong> {safe(doc_number)} &nbsp;&nbsp; <strong>Azienda:</strong> {company_name}</p>
        <p><strong>1. VALIDIT&Agrave; DELL&#39;OFFERTA</strong><br>Il presente preventivo ha validit&agrave; come indicato nel documento dalla data di emissione.</p>
        <p><strong>2. PREZZI</strong><br>I prezzi indicati si intendono IVA esclusa salvo diversa indicazione esplicita.</p>
        <p><strong>3. TEMPI DI CONSEGNA</strong><br>I tempi di consegna decorrono dalla data di conferma dell&#39;ordine e ricevimento dell&#39;acconto.</p>
        <p><strong>4. PAGAMENTO</strong><br>Il pagamento dovr&agrave; avvenire secondo le modalit&agrave; indicate nel preventivo.</p>
        <p><strong>5. TRASPORTO</strong><br>La merce viaggia a rischio e pericolo del committente salvo diversa indicazione.</p>
        <p><strong>6. FORO COMPETENTE</strong><br>Per qualsiasi controversia &egrave; competente il Foro del luogo ove ha sede il fornitore.</p>
    </div>
    """


def render_pdf(html_content: str) -> BytesIO:
    """Render PDF con ReportLab - layout professionale NormaFacile."""
    import re
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

    BLUE = colors.HexColor('#0055FF')
    DARK = colors.HexColor('#1E293B')
    GRAY_BG = colors.HexColor('#F8F9FA')
    LIGHT_BORDER = colors.HexColor('#DEE2E6')
    WHITE = colors.white
    TEXT = colors.HexColor('#1a1a1a')
    GRAY_TEXT = colors.HexColor('#555555')

    W = A4[0] - 36*mm  # larghezza utile

    def clean(text):
        t = str(text or '')
        t = re.sub(r'<br\s*/?>', '\n', t, flags=re.IGNORECASE)
        t = re.sub(r'<b>(.*?)</b>', r'<b>\1</b>', t)
        t = re.sub(r'<[^>]+>', '', t)
        return (t.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
                 .replace('&euro;','€').replace('&#39;',"'").replace('&nbsp;',' '))

    styles = getSampleStyleSheet()
    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    N = sty('N', fontSize=9, leading=13, textColor=TEXT)
    B = sty('B', fontSize=9, leading=13, fontName='Helvetica-Bold', textColor=TEXT)
    SM = sty('SM', fontSize=8, leading=11, textColor=GRAY_TEXT)
    BLUE_LABEL = sty('BL', fontSize=8, leading=10, fontName='Helvetica-Bold',
                     textColor=BLUE, spaceAfter=2)
    BIG_TITLE = sty('BT', fontSize=18, leading=22, fontName='Helvetica-Bold',
                    textColor=BLUE, alignment=TA_CENTER, spaceBefore=6, spaceAfter=6)
    TH = sty('TH', fontSize=8.5, leading=11, fontName='Helvetica-Bold',
             textColor=WHITE)
    TD = sty('TD', fontSize=8.5, leading=12, textColor=TEXT)
    TD_R = sty('TDR', fontSize=8.5, leading=12, textColor=TEXT, alignment=TA_RIGHT)
    TOTAL_LABEL = sty('TL', fontSize=9, leading=13, textColor=GRAY_TEXT)
    TOTAL_VALUE = sty('TV', fontSize=9, leading=13, textColor=TEXT,
                      alignment=TA_RIGHT, fontName='Helvetica-Bold')
    GRAND_LABEL = sty('GL', fontSize=11, leading=14, fontName='Helvetica-Bold',
                      textColor=WHITE)
    GRAND_VALUE = sty('GV', fontSize=11, leading=14, fontName='Helvetica-Bold',
                      textColor=WHITE, alignment=TA_RIGHT)

    story = []
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=20*mm)

    # ── Parse sezioni HTML ──────────────────────────────────────────
    # Estrai blocchi chiave dal HTML
    text = html_content

    def extract_between(html, start_marker, end_marker=None):
        idx = html.find(start_marker)
        if idx < 0: return ''
        start = idx + len(start_marker)
        if end_marker:
            end = html.find(end_marker, start)
            return html[start:end] if end >= 0 else html[start:]
        return html[start:]

    # Usa i dati già strutturati nelle sezioni HTML
    lines_raw = [clean(l) for l in re.split(r'<br\s*/?>', re.sub(r'<[^>]+>', '\n', text))]
    lines_clean = [l.strip() for l in '\n'.join(lines_raw).split('\n') if l.strip()]

    # ── Header: azienda + cliente ───────────────────────────────────
    company_lines = []
    client_lines = []
    in_client = False
    header_done = False
    doc_title = ''
    meta_rows = []
    line_rows = []
    total_rows = []
    bank_lines = []
    payment_lines = []
    notes_lines = []
    footer_lines = []

    mode = 'company'
    for line in lines_clean:
        if line.startswith('---'):
            mode = 'client'
            continue
        if mode == 'company' and not header_done:
            if any(line.startswith(k) for k in ('PREVENTIVO','FATTURA','DDT','DOCUMENTO')):
                doc_title = line
                mode = 'meta'
                continue
            company_lines.append(line)
        elif mode == 'client':
            if any(line.startswith(k) for k in ('PREVENTIVO','FATTURA','DDT','DOCUMENTO')):
                doc_title = line
                mode = 'meta'
                continue
            client_lines.append(line)
        elif mode == 'meta':
            if re.match(r'^(DATA|TIPO|N\.|NUMERO|PRV|DDT)', line, re.IGNORECASE):
                meta_rows.append(line)
            elif re.match(r'^\d{4}-\d{4}|^PRV|^DDT|^FAT', line):
                meta_rows.append(line)
            elif line == 'lines_start':
                mode = 'lines'
            elif re.match(r'^[A-Z0-9]{3,}.*€', line) or re.match(r'^\d+,\d+.*€', line):
                mode = 'lines'
                line_rows.append(line)
            else:
                meta_rows.append(line)
            if len(meta_rows) >= 6:
                mode = 'lines'
        elif mode == 'lines':
            if line.startswith('Imponibile') or line.startswith('Totale IVA') or line.startswith('TOTALE') or line.startswith('IVA:'):
                mode = 'totals'
                total_rows.append(line)
            else:
                line_rows.append(line)
        elif mode == 'totals':
            if line.startswith('Coordinate') or line.startswith('IBAN') or line.startswith('Monte') or line.startswith('Banca'):
                mode = 'bank'
                bank_lines.append(line)
            elif line.startswith('SCADENZA') or line.startswith('Condizioni') or line.startswith('Scadenza'):
                mode = 'payment'
                payment_lines.append(line)
            else:
                total_rows.append(line)
        elif mode == 'bank':
            if line.startswith('SCADENZA') or line.startswith('Condizioni'):
                mode = 'payment'
                payment_lines.append(line)
            else:
                bank_lines.append(line)
        elif mode == 'payment':
            payment_lines.append(line)

    # ── 1. HEADER TABLE ─────────────────────────────────────────────
    co_paras = []
    for i, l in enumerate(company_lines[:8]):
        if i == 0:
            co_paras.append(Paragraph(l, sty('CN', fontSize=12, leading=15,
                fontName='Helvetica-Bold', textColor=BLUE)))
        elif 'P.IVA' in l or 'Cod.Fisc' in l:
            co_paras.append(Paragraph(l, B))
        else:
            co_paras.append(Paragraph(l, SM))

    cl_paras = [Paragraph('Spett.le', SM)]
    for i, l in enumerate(client_lines[:8]):
        if i == 0:
            cl_paras.append(Paragraph(l, sty('CLN', fontSize=11, leading=14,
                fontName='Helvetica-Bold', textColor=DARK)))
        elif 'P.IVA' in l or 'Cod.Fisc' in l:
            cl_paras.append(Paragraph(l, B))
        else:
            cl_paras.append(Paragraph(l, SM))

    header_data = [[co_paras, cl_paras]]
    header_table = Table(header_data, colWidths=[W*0.55, W*0.43])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (0,0), 0),
        ('RIGHTPADDING', (0,0), (0,0), 6),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (1,0), (1,0), 8),
        ('TOPPADDING', (1,0), (1,0), 6),
        ('BOTTOMPADDING', (1,0), (1,0), 6),
        ('BACKGROUND', (1,0), (1,0), GRAY_BG),
        ('BOX', (1,0), (1,0), 0.5, LIGHT_BORDER),
        ('ROUNDEDCORNERS', [3,3,3,3]),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_BORDER, spaceAfter=8))

    # ── 2. TITOLO DOCUMENTO ─────────────────────────────────────────
    if doc_title:
        story.append(Paragraph(doc_title, BIG_TITLE))

    # ── 3. META TABLE ───────────────────────────────────────────────
    if meta_rows:
        pairs = []
        for mr in meta_rows[:6]:
            parts = mr.split(':', 1) if ':' in mr else [mr, '']
            pairs.append([Paragraph(parts[0].strip(), sty('ML', fontSize=8,
                fontName='Helvetica-Bold', textColor=GRAY_TEXT)),
                Paragraph(parts[1].strip() if len(parts)>1 else '', N)])
        # Organizza in 2 colonne
        half = (len(pairs)+1)//2
        left = pairs[:half]
        right = pairs[half:]
        while len(right) < len(left): right.append(['',''])
        meta_data = []
        for i in range(len(left)):
            row = left[i] + ['  '] + right[i] if i < len(right) else left[i] + ['  ','','']
            meta_data.append(row)
        meta_table = Table(meta_data, colWidths=[W*0.18, W*0.30, W*0.04, W*0.18, W*0.30])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), GRAY_BG),
            ('BOX', (0,0), (-1,-1), 0.5, LIGHT_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6))

    # ── 4. TABELLA RIGHE ────────────────────────────────────────────
    headers_row = [
        Paragraph('Descrizione', TH),
        Paragraph('Q.tà', TH),
        Paragraph('Prezzo Unit.', TH),
        Paragraph('IVA', TH),
        Paragraph('Totale', TH),
    ]
    table_data = [headers_row]
    for lr in line_rows:
        parts = re.split(r'\s{2,}|\t', lr)
        if len(parts) >= 2:
            row = [Paragraph(clean(parts[0]), TD)] + [Paragraph(clean(p), TD_R) for p in parts[1:5]]
            while len(row) < 5: row.append(Paragraph('', TD))
            table_data.append(row[:5])
        elif lr.strip():
            table_data.append([Paragraph(clean(lr), TD), '', '', '', ''])

    lines_table = Table(table_data, colWidths=[W*0.50, W*0.10, W*0.15, W*0.10, W*0.15])
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('TOPPADDING', (0,0), (-1,0), 5),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('LINEBELOW', (0,1), (-1,-2), 0.3, LIGHT_BORDER),
    ])
    for i in range(1, len(table_data), 2):
        ts.add('BACKGROUND', (0,i), (-1,i), GRAY_BG)
    lines_table.setStyle(ts)
    story.append(lines_table)
    story.append(Spacer(1, 6))

    # ── 5. TOTALI ───────────────────────────────────────────────────
    totals_data = []
    grand_total = None
    for tr in total_rows:
        parts = tr.rsplit(':', 1) if ':' in tr else tr.rsplit(' ', 1)
        label = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else ''
        if 'TOTALE' in label.upper() and 'IVA' not in label.upper():
            grand_total = (label, value)
        else:
            totals_data.append([Paragraph(label, TOTAL_LABEL),
                               Paragraph(value, sty('TV2', fontSize=9, alignment=TA_RIGHT))])

    if totals_data:
        tot_table = Table(totals_data, colWidths=[W*0.65, W*0.33], hAlign='RIGHT')
        tot_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEABOVE', (0,-1), (-1,-1), 0.5, LIGHT_BORDER),
        ]))
        story.append(tot_table)

    if grand_total:
        gt_table = Table([[Paragraph(grand_total[0], GRAND_LABEL),
                           Paragraph(grand_total[1], GRAND_VALUE)]],
                          colWidths=[W*0.65, W*0.33], hAlign='RIGHT')
        gt_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BLUE),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(Spacer(1, 2))
        story.append(gt_table)

    story.append(Spacer(1, 8))

    # ── 6. COORDINATE BANCARIE ──────────────────────────────────────
    if bank_lines:
        bank_text = ' '.join(bank_lines)
        bank_table = Table([[Paragraph(bank_text, B)]],
                           colWidths=[W])
        bank_table.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (0,0), 10),
            ('TOPPADDING', (0,0), (0,0), 6),
            ('BOTTOMPADDING', (0,0), (0,0), 6),
            ('LINEBEFORE', (0,0), (0,0), 3, BLUE),
            ('BACKGROUND', (0,0), (0,0), GRAY_BG),
        ]))
        story.append(bank_table)
        story.append(Spacer(1, 6))

    # ── 7. SCADENZA PAGAMENTI ────────────────────────────────────────
    if payment_lines:
        pay_paras = [Paragraph('SCADENZA PAGAMENTI', BLUE_LABEL)]
        for pl in payment_lines:
            if pl.startswith('SCADENZA'): continue
            pay_paras.append(Paragraph(pl, N))
        pay_table = Table([[[p for p in pay_paras]]], colWidths=[W])
        pay_table.setStyle(TableStyle([
            ('BOX', (0,0), (0,0), 0.5, LIGHT_BORDER),
            ('LEFTPADDING', (0,0), (0,0), 8),
            ('TOPPADDING', (0,0), (0,0), 6),
            ('BOTTOMPADDING', (0,0), (0,0), 6),
        ]))
        story.append(pay_table)

    # ── BUILD ────────────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)
    return buffer

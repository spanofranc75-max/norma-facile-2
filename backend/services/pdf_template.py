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
    """Render PDF usando ReportLab con layout professionale."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    import re

    # Pulisci HTML - estrai testo con struttura
    def clean(text):
        text = str(text or '')
        text = re.sub(r'<brs*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&euro;', '€').replace('&#39;', "'")
        return text.strip()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=18*mm)

    BLUE = colors.HexColor('#0055FF')
    DARK = colors.HexColor('#1E293B')
    GRAY = colors.HexColor('#F8F9FA')
    LIGHT = colors.HexColor('#E9ECEF')

    styles = getSampleStyleSheet()
    story = []

    # Parse HTML in blocchi
    lines = html_content.split('\n')
    clean_lines = [clean(l) for l in lines if clean(l)]

    normal = ParagraphStyle('N', parent=styles['Normal'], fontSize=9, leading=13)
    bold = ParagraphStyle('B', parent=styles['Normal'], fontSize=9, leading=13, fontName='Helvetica-Bold')
    title = ParagraphStyle('T', parent=styles['Normal'], fontSize=14, leading=18, fontName='Helvetica-Bold', textColor=BLUE)
    small = ParagraphStyle('S', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#555555'))

    for line in clean_lines:
        if not line:
            story.append(Spacer(1, 3*mm))
        elif line.startswith('AZIENDA:'):
            story.append(Paragraph(line.replace('AZIENDA:', '<b>').strip() + '</b>', title))
        elif line.startswith('P.IVA:') or line.startswith('Cod.Fisc:') or line.startswith('Cod.SDI:'):
            story.append(Paragraph(line, bold))
        elif line.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=1, color=LIGHT))
            story.append(Spacer(1, 3*mm))
        elif line.startswith('Spett.le:'):
            story.append(Paragraph(line.replace('Spett.le:', '<b>Spett.le:</b>'), bold))
        elif line in ('PREVENTIVO', 'FATTURA', 'DDT', 'DOCUMENTO DI TRASPORTO'):
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(line, title))
        else:
            story.append(Paragraph(line, normal))

    doc.build(story)
    buffer.seek(0)
    return buffer

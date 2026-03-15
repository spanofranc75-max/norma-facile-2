"""Shared PDF template utilities — xhtml2pdf (no system deps)."""
from io import BytesIO
from datetime import datetime, timezone
import html as html_mod
import logging

logger = logging.getLogger(__name__)
_esc = html_mod.escape


def fmt_it(n) -> str:
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def safe(val) -> str:
    return _esc(str(val or ""))


COMMON_CSS = """
@page { size: A4; margin: 15mm 18mm 18mm 18mm; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #222; line-height: 1.35; }
.page-break { page-break-before: always; }
.header-table { width: 100%; border: none; border-collapse: collapse; margin-bottom: 10px; }
.header-table td { vertical-align: top; border: none; padding: 0; }
.company-cell { width: 55%; padding-right: 15px; }
.client-cell { width: 45%; padding: 8px 10px; font-size: 8.5pt; }
.logo { max-width: 140px; max-height: 55px; margin-bottom: 6px; }
.company-name { font-size: 13pt; font-weight: bold; color: #222; margin-bottom: 3px; }
.company-details { font-size: 8pt; color: #333; line-height: 1.55; }
.cl-label { font-size: 8pt; color: #555; font-weight: bold; }
.cl-name { font-weight: bold; font-size: 10pt; margin: 2px 0; }
.cl-details { font-size: 8pt; color: #333; line-height: 1.55; }
.doc-title { text-align: center; margin: 14px 0 6px 0; }
.doc-title h1 { font-size: 18pt; font-weight: bold; color: #222; letter-spacing: 2px; margin: 0 0 2px 0; }
.doc-num { font-size: 14pt; font-weight: bold; color: #333; }
.meta-table { margin: 8px 0; font-size: 9pt; border: none; border-collapse: collapse; }
.meta-table td { border: none; padding: 1px 6px 1px 0; vertical-align: top; }
.meta-label { font-weight: bold; white-space: nowrap; width: 110px; }
.ref-note { margin: 8px 0; padding: 5px 8px; background: #f5f5f5; border-left: 3px solid #888; font-size: 8.5pt; }
.items-table { width: 100%; border-collapse: collapse; margin: 10px 0 6px 0; font-size: 8pt; }
.items-table th { background: #eee; border: 1px solid #999; padding: 5px 4px; font-weight: bold; text-transform: uppercase; font-size: 7.5pt; text-align: center; }
.items-table td { border: 1px solid #bbb; padding: 4px 4px; vertical-align: top; }
.items-table .desc-cell { text-align: left; line-height: 1.4; }
.items-table .tc { text-align: center; }
.items-table .tr { text-align: right; }
.info-box { margin: 8px 0; padding: 6px 8px; background: #fafafa; border: 1px solid #ddd; font-size: 8pt; line-height: 1.4; }
.info-box-title { font-weight: bold; margin-bottom: 3px; font-size: 8.5pt; }
.totals-block { width: 55%; margin-left: auto; margin-top: 10px; }
.iva-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-bottom: 6px; }
.iva-table th { background: #eee; border: 1px solid #999; padding: 4px 5px; font-size: 7.5pt; text-transform: uppercase; text-align: center; }
.iva-table td { border: 1px solid #bbb; padding: 3px 5px; }
.summary-table { width: 100%; font-size: 9pt; margin-top: 4px; border: none; border-collapse: collapse; }
.summary-table td { padding: 2px 5px; border: none; }
.total-final td { font-size: 13pt; font-weight: bold; border-top: 2px solid #333; padding-top: 6px; }
.bank-info { margin-top: 12px; padding: 6px 8px; border: 1px solid #ccc; font-size: 8pt; background: #fafafa; }
.payment-schedule { margin-top: 12px; padding: 8px; border: 1px solid #999; background: #f9f9f9; }
.schedule-title { font-size: 9pt; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.3px; }
.schedule-table { width: 100%; border-collapse: collapse; font-size: 8pt; }
.schedule-table th { background: #e8e8e8; border: 1px solid #ccc; padding: 3px 6px; font-weight: bold; text-align: center; }
.schedule-table td { border: 1px solid #ccc; padding: 3px 6px; }
.transport-table { width: 100%; border-collapse: collapse; font-size: 8pt; margin: 6px 0; }
.transport-table td { border: 1px solid #ccc; padding: 3px 5px; }
.transport-table .t-label { font-weight: bold; background: #f5f5f5; width: 22%; }
.signatures-row { width: 100%; border: none; border-collapse: collapse; margin-top: 25px; }
.signatures-row td { border: none; width: 33%; text-align: center; vertical-align: bottom; padding: 0 10px; }
.sig-line-center { border-top: 1px solid #333; margin-top: 40px; padding-top: 4px; font-size: 7.5pt; color: #555; }
.conditions-title { font-size: 11pt; font-weight: bold; text-align: center; margin-bottom: 12px; text-transform: uppercase; }
.conditions-text { font-size: 7.5pt; line-height: 1.45; text-align: justify; }
.acceptance-section { margin-top: 30px; }
.sig-block { margin: 15px 0; }
.sig-line { border-bottom: 1px solid #333; width: 250px; height: 30px; margin: 4px 0; }
.sig-label { font-size: 7.5pt; color: #666; }
.legal-notice { margin-top: 20px; font-size: 7pt; line-height: 1.4; border: 1px solid #ccc; padding: 6px 8px; background: #fafafa; }
.doc-footer { margin-top: 40px; text-align: right; font-size: 8pt; color: #555; }
"""


def build_header_html(company: dict, client: dict, no_client_border: bool = False) -> str:
    co = company or {}
    cl = client or {}
    company_name = safe(co.get("business_name"))
    addr = safe(co.get("address", ""))
    cap = safe(co.get("cap", ""))
    city = safe(co.get("city", ""))
    prov = safe(co.get("province", ""))
    full_addr = addr
    if cap or city:
        parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
        full_addr += f"<br>{' '.join(parts)}" if addr else ' '.join(parts)
    piva = safe(co.get("partita_iva", ""))
    cf = safe(co.get("codice_fiscale", ""))
    phone = safe(co.get("phone") or co.get("tel", ""))
    email = safe(co.get("email") or co.get("contact_email", ""))
    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="logo" />'
    cl_name = safe(cl.get("business_name", ""))
    cl_addr = safe(cl.get("address", ""))
    cl_cap = safe(cl.get("cap", ""))
    cl_city = safe(cl.get("city", ""))
    cl_prov = safe(cl.get("province", ""))
    cl_full = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full += f"<br>{' '.join(parts)}" if cl_addr else ' '.join(parts)
    cl_piva = safe(cl.get("partita_iva", ""))
    cl_cf = safe(cl.get("codice_fiscale", ""))
    cl_sdi = safe(cl.get("codice_sdi", ""))
    cl_pec = safe(cl.get("pec", ""))
    cl_email = safe(cl.get("email", ""))
    return f"""
    <table class="header-table">
        <tr>
            <td class="company-cell">
                {logo_html}
                <div class="company-name">{company_name}</div>
                <div class="company-details">
                    {full_addr}
                    {"<br>P.IVA: " + piva if piva else ""}
                    {"<br>Cod. Fisc.: " + cf if cf else ""}
                    {"<br>Tel: " + phone if phone else ""}
                    {"<br>Email: " + email if email else ""}
                </div>
            </td>
            <td class="client-cell">
                <div class="cl-label">Spett.le</div>
                <div class="cl-name">{cl_name}</div>
                <div class="cl-details">
                    {cl_full}
                    {"<br>P.IVA: " + cl_piva if cl_piva else ""}
                    {"<br>Cod. Fisc.: " + cl_cf if cl_cf else ""}
                    {"<br>Cod. SDI: " + cl_sdi if cl_sdi else ""}
                    {"<br>PEC: " + cl_pec if cl_pec else ""}
                    {"<br>Email: " + cl_email if cl_email and not cl_pec else ""}
                </div>
            </td>
        </tr>
    </table>"""


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
        rate = float(rate_str) / 100
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
    rows = ""
    if sconto_val:
        rows += f"""
        <tr class="summary-row">
            <td>Imponibile lordo:</td>
            <td style="text-align:right">{fmt_it(subtotal)}</td>
        </tr>
        <tr class="summary-row">
            <td>Sconto:</td>
            <td style="text-align:right">- {fmt_it(sconto_val)}</td>
        </tr>"""
    for rate_str, g in sorted(groups.items()):
        rows += f"""
        <tr class="summary-row">
            <td>Imponibile IVA {rate_str}%:</td>
            <td style="text-align:right">{fmt_it(g['base'])}</td>
        </tr>
        <tr class="summary-row">
            <td>IVA {rate_str}%:</td>
            <td style="text-align:right">{fmt_it(g['iva'])}</td>
        </tr>"""
    saldo = total_doc - acconto
    rows += f"""
    <tr class="total-final">
        <td><strong>TOTALE DOCUMENTO:</strong></td>
        <td style="text-align:right"><strong>€ {fmt_it(total_doc)}</strong></td>
    </tr>"""
    if acconto:
        rows += f"""
        <tr class="summary-row">
            <td>Acconto:</td>
            <td style="text-align:right">- {fmt_it(acconto)}</td>
        </tr>
        <tr class="total-final">
            <td><strong>SALDO:</strong></td>
            <td style="text-align:right"><strong>€ {fmt_it(saldo)}</strong></td>
        </tr>"""
    return f'<div class="totals-block"><table class="summary-table">{rows}</table></div>'


def render_pdf(html_content: str) -> BytesIO:
    """Render HTML to PDF usando xhtml2pdf (puro Python)."""
    from xhtml2pdf import pisa
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        html_content,
        dest=buffer,
        encoding='utf-8'
    )
    if pisa_status.err:
        logger.error(f"xhtml2pdf errors: {pisa_status.err}")
        raise Exception(f"Errore generazione PDF: {pisa_status.err}")
    buffer.seek(0)
    return buffer
    rows += f"""
    <tr class="total-final">
        <td><strong>TOTALE DOCUMENTO:</strong></td>
        <td style="text-align:right"><strong>€ {fmt_it(total_doc)}</strong></td>
    </tr>"""
    if acconto:
        rows += f"""
        <tr class="summary-row">
            <td>Acconto:</td>
            <td style="text-align:right">- {fmt_it(acconto)}</td>
        </tr>
        <tr class="total-final">
            <td><strong>SALDO:</strong></td>
            <td style="text-align:right"><strong>€ {fmt_it(saldo)}</strong></td>
        </tr>"""
    return f'<div class="totals-block"><table class="summary-table">{rows}</table></div>'


def render_pdf(html_content: str) -> BytesIO:
    """Render PDF usando ReportLab — puro Python, zero dipendenze sistema."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    import re

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=15*mm,
        bottomMargin=18*mm
    )

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
    )

    def strip_html(text):
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    clean_text = strip_html(html_content)
    lines = [l for l in clean_text.split('\n') if l.strip()]

    story = []
    for line in lines[:300]:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 3*mm))
        else:
            story.append(Paragraph(line, style_normal))
            story.append(Spacer(1, 1*mm))

    doc.build(story)
    buffer.seek(0)
    return buffer

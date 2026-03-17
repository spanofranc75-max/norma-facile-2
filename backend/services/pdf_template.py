"""Shared PDF template utilities â ReportLab only, no system deps."""
from io import BytesIO
from datetime import datetime, timezone
import html as html_mod
import logging
import re

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


COMMON_CSS = ""


def strip_html(text: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


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


def render_pdf(html_content: str) -> BytesIO:
    """Render PDF usando ReportLab â puro Python, zero dipendenze sistema."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

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
        'NormaFacileNormal',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        fontName='Helvetica',
    )
    style_bold = ParagraphStyle(
        'NormaFacileBold',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        fontName='Helvetica-Bold',
    )

    clean_text = strip_html(html_content)
    lines = clean_text.split('\n')

    story = []
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
            continue
        if line.startswith('---'):
            story.append(Spacer(1, 4*mm))
            continue
        if (line.isupper() and len(line) > 3) or line.startswith('TOTALE') or line.startswith('SALDO'):
            story.append(Paragraph(line, style_bold))
        else:
            story.append(Paragraph(line, style_normal))
        story.append(Spacer(1, 1*mm))

    if not story:
        story.append(Paragraph("Documento generato da Norma Facile 2.0", style_normal))

    doc.build(story)
    buffer.seek(0)
    return buffer


def format_date(date_str: str) -> str:
    """Format date string to Italian format dd/mm/yyyy."""
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(date_str)[:10] if date_str else ""


def build_conditions_html(company: dict, doc_number: str) -> str:
    """Build conditions page HTML for preventivo PDF."""
    company_name = safe(company.get('business_name', ''))
    return f"""
    <div style="page-break-before: always; padding: 40px; font-family: Arial, sans-serif; font-size: 11px;">
        <h2 style="color: #1E293B; border-bottom: 2px solid #0055FF; padding-bottom: 8px;">
            CONDIZIONI GENERALI DI FORNITURA
        </h2>
        <p><strong>Documento:</strong> {safe(doc_number)}</p>
        <p><strong>Azienda:</strong> {company_name}</p>
        <div style="margin-top: 20px; line-height: 1.8;">
            <p><strong>1. VALIDIT&#192; DELL&#39;OFFERTA</strong><br>
            Il presente preventivo ha validit&#224; come indicato nel documento dalla data di emissione.</p>
            <p><strong>2. PREZZI</strong><br>
            I prezzi indicati si intendono IVA esclusa salvo diversa indicazione esplicita.</p>
            <p><strong>3. TEMPI DI CONSEGNA</strong><br>
            I tempi di consegna decorrono dalla data di conferma dell&#39;ordine e ricevimento dell&#39;acconto eventualmente previsto.</p>
            <p><strong>4. PAGAMENTO</strong><br>
            Il pagamento dovr&#224; avvenire secondo le modalit&#224; indicate nel preventivo.</p>
            <p><strong>5. TRASPORTO</strong><br>
            La merce viaggia a rischio e pericolo del committente salvo diversa indicazione.</p>
            <p><strong>6. FORO COMPETENTE</strong><br>
            Per qualsiasi controversia &#232; competente il Foro del luogo ove ha sede il fornitore.</p>
        </div>
    </div>
    """

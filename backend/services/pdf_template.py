"""Shared PDF template utilities Ã¢ÂÂ ReportLab only, no system deps."""
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
    """Render PDF usando xhtml2pdf - supporta HTML/CSS completo."""
    from xhtml2pdf import pisa
    
    buffer = BytesIO()
    
    # Aggiungi CSS base se non presente
    if '<html' not in html_content.lower():
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10px; margin: 0; padding: 0; }}
  @page {{ size: A4; margin: 15mm 18mm 18mm 18mm; }}
</style>
</head>
<body>{html_content}</body>
</html>"""
    
    pisa_status = pisa.CreatePDF(html_content, dest=buffer, encoding='utf-8')
    
    if pisa_status.err:
        # Fallback: ritorna buffer anche con errori minori
        pass
    
    buffer.seek(0)
    return buffer

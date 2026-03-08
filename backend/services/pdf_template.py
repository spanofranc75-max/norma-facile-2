"""Shared PDF template utilities for all document types.

Provides consistent HTML/CSS styling, header layout, and helpers
for Preventivi, Fatture, and DDT using WeasyPrint.
"""
from io import BytesIO
from datetime import datetime, timezone
import html as html_mod
import logging

logger = logging.getLogger(__name__)

_esc = html_mod.escape


def fmt_it(n) -> str:
    """Format number Italian style: 1.234,56"""
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def safe(val) -> str:
    """Escape a value that might be None."""
    return _esc(str(val or ""))


# ── Common CSS ──────────────────────────────────────────────────

COMMON_CSS = """
@page {
    size: A4;
    margin: 15mm 18mm 18mm 18mm;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: Arial, Helvetica, "Liberation Sans", sans-serif;
    font-size: 9pt;
    color: #222;
    line-height: 1.35;
}
.page-break { page-break-before: always; }

/* ── HEADER TABLE ── */
.header-table {
    width: 100%;
    border: none;
    border-collapse: collapse;
    margin-bottom: 10px;
}
.header-table td {
    vertical-align: top;
    border: none;
    padding: 0;
}
.company-cell {
    width: 55%;
    padding-right: 15px;
}
.client-cell {
    width: 45%;
    padding: 8px 10px !important;
    font-size: 8.5pt;
}
.logo {
    max-width: 140px;
    max-height: 55px;
    margin-bottom: 6px;
}
.company-name {
    font-size: 13pt;
    font-weight: bold;
    color: #222;
    margin-bottom: 3px;
}
.company-details {
    font-size: 8pt;
    color: #333;
    line-height: 1.55;
}
.cl-label {
    font-size: 8pt;
    color: #555;
    font-weight: bold;
}
.cl-name {
    font-weight: bold;
    font-size: 10pt;
    margin: 2px 0;
}
.cl-details {
    font-size: 8pt;
    color: #333;
    line-height: 1.55;
}

/* ── TITLE ── */
.doc-title {
    text-align: center;
    margin: 14px 0 6px 0;
}
.doc-title h1 {
    font-size: 18pt;
    font-weight: bold;
    color: #222;
    letter-spacing: 2px;
    margin: 0 0 2px 0;
}
.doc-num {
    font-size: 14pt;
    font-weight: bold;
    color: #333;
}

/* ── META TABLE ── */
.meta-table {
    margin: 8px 0;
    font-size: 9pt;
    border: none;
    border-collapse: collapse;
}
.meta-table td {
    border: none;
    padding: 1px 6px 1px 0;
    vertical-align: top;
}
.meta-label {
    font-weight: bold;
    white-space: nowrap;
    width: 110px;
}
.ref-note {
    margin: 8px 0;
    padding: 5px 8px;
    background: #f5f5f5;
    border-left: 3px solid #888;
    font-size: 8.5pt;
}

/* ── ITEMS TABLE ── */
.items-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 6px 0;
    font-size: 8pt;
}
.items-table th {
    background: #eee;
    border: 1px solid #999;
    padding: 5px 4px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 7.5pt;
    text-align: center;
}
.items-table td {
    border: 1px solid #bbb;
    padding: 4px 4px;
    vertical-align: top;
}
.items-table .desc-cell {
    text-align: left;
    line-height: 1.4;
}
.items-table .tc { text-align: center; }
.items-table .tr { text-align: right; }

/* ── NOTES / INFO BOXES ── */
.info-box {
    margin: 8px 0;
    padding: 6px 8px;
    background: #fafafa;
    border: 1px solid #ddd;
    font-size: 8pt;
    line-height: 1.4;
}
.info-box-title {
    font-weight: bold;
    margin-bottom: 3px;
    font-size: 8.5pt;
}

/* ── TOTALS ── */
.totals-block {
    width: 55%;
    margin-left: auto;
    margin-top: 10px;
}
.iva-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-bottom: 6px;
}
.iva-table th {
    background: #eee;
    border: 1px solid #999;
    padding: 4px 5px;
    font-size: 7.5pt;
    text-transform: uppercase;
    text-align: center;
}
.iva-table td {
    border: 1px solid #bbb;
    padding: 3px 5px;
}
.summary-table {
    width: 100%;
    font-size: 9pt;
    margin-top: 4px;
    border: none;
    border-collapse: collapse;
}
.summary-table td {
    padding: 2px 5px;
    border: none;
}
.summary-row td { font-size: 9pt; }
.total-final td {
    font-size: 13pt;
    font-weight: bold;
    border-top: 2px solid #333;
    padding-top: 6px;
}

/* ── BANK / PAYMENT INFO ── */
.bank-info {
    margin-top: 12px;
    padding: 6px 8px;
    border: 1px solid #ccc;
    font-size: 8pt;
    background: #fafafa;
}

/* ── PAYMENT SCHEDULE ── */
.payment-schedule {
    margin-top: 12px;
    padding: 8px;
    border: 1px solid #999;
    background: #f9f9f9;
}
.schedule-title {
    font-size: 9pt;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.schedule-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
}
.schedule-table th {
    background: #e8e8e8;
    border: 1px solid #ccc;
    padding: 3px 6px;
    font-weight: bold;
    text-align: center;
}
.schedule-table td {
    border: 1px solid #ccc;
    padding: 3px 6px;
}

/* ── TRANSPORT INFO (DDT) ── */
.transport-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 6px 0;
}
.transport-table td {
    border: 1px solid #ccc;
    padding: 3px 5px;
}
.transport-table .t-label {
    font-weight: bold;
    background: #f5f5f5;
    width: 22%;
}

/* ── SIGNATURE BLOCKS ── */
.signatures-row {
    width: 100%;
    border: none;
    border-collapse: collapse;
    margin-top: 25px;
}
.signatures-row td {
    border: none;
    width: 33%;
    text-align: center;
    vertical-align: bottom;
    padding: 0 10px;
}
.sig-line-center {
    border-top: 1px solid #333;
    margin-top: 40px;
    padding-top: 4px;
    font-size: 7.5pt;
    color: #555;
}

/* ── CONDITIONS (PAGE 2) ── */
.conditions-title {
    font-size: 11pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 12px;
    text-transform: uppercase;
}
.conditions-text {
    font-size: 7.5pt;
    line-height: 1.45;
    text-align: justify;
}
.acceptance-section { margin-top: 30px; }
.sig-block { margin: 15px 0; }
.sig-line {
    border-bottom: 1px solid #333;
    width: 250px;
    height: 30px;
    margin: 4px 0;
}
.sig-label { font-size: 7.5pt; color: #666; }
.legal-notice {
    margin-top: 20px;
    font-size: 7pt;
    line-height: 1.4;
    border: 1px solid #ccc;
    padding: 6px 8px;
    background: #fafafa;
}
.doc-footer {
    margin-top: 40px;
    text-align: right;
    font-size: 8pt;
    color: #555;
}
"""


# ── Header builder ──────────────────────────────────────────────

def build_header_html(company: dict, client: dict, no_client_border: bool = False) -> str:
    """Build the two-column header (company left, client right)."""
    co = company or {}
    cl = client or {}

    # Company
    company_name = safe(co.get("business_name"))
    addr = safe(co.get("address"))
    cap = safe(co.get("cap"))
    city = safe(co.get("city"))
    prov = safe(co.get("province"))
    full_addr = addr
    if cap or city:
        parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
        full_addr += f"<br>{' '.join(parts)}" if addr else ' '.join(parts)
    piva = safe(co.get("partita_iva"))
    cf = safe(co.get("codice_fiscale"))
    phone = safe(co.get("phone") or co.get("tel"))
    email = safe(co.get("email") or co.get("contact_email"))

    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="logo" />'

    # Client
    cl_name = safe(cl.get("business_name"))
    cl_addr = safe(cl.get("address"))
    cl_cap = safe(cl.get("cap"))
    cl_city = safe(cl.get("city"))
    cl_prov = safe(cl.get("province"))
    cl_full = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full += f"<br>{' '.join(parts)}" if cl_addr else ' '.join(parts)
    cl_piva = safe(cl.get("partita_iva"))
    cl_cf = safe(cl.get("codice_fiscale"))
    cl_sdi = safe(cl.get("codice_sdi"))
    cl_pec = safe(cl.get("pec"))
    cl_email = safe(cl.get("email"))

    cl_border = "" if no_client_border else "border: 1px solid #999 !important; padding: 8px 10px !important;"
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
            <td class="client-cell" style="{cl_border}">
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


# ── IVA / Totals builder ───────────────────────────────────────

def compute_iva_groups(lines: list, sconto_globale: float = 0) -> dict:
    """Compute IVA breakdown from line items."""
    subtotal = sum(float(ln.get("line_total") or 0) for ln in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)

    groups = {}
    for ln in lines:
        rate_str = str(ln.get("vat_rate", "22"))
        base = float(ln.get("line_total") or 0)
        if sconto_globale and subtotal > 0:
            base = base * (1 - sconto_globale / 100)
        groups.setdefault(rate_str, {"base": 0.0, "tax": 0.0})
        groups[rate_str]["base"] += base

    total_vat = 0.0
    for rate_str, grp in groups.items():
        try:
            pct = float(rate_str)
            tax = round(grp["base"] * pct / 100, 2)
        except ValueError:
            tax = 0
        grp["tax"] = tax
        total_vat += tax

    return {
        "subtotal": round(subtotal, 2),
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "groups": groups,
        "total_vat": round(total_vat, 2),
        "total": round(imponibile + total_vat, 2),
    }


def build_totals_html(iva_data: dict, sconto_globale: float = 0, extra_rows: str = "") -> str:
    """Build the right-aligned totals block with IVA breakdown."""
    iva_rows = ""
    for rate_str, grp in sorted(iva_data["groups"].items()):
        iva_rows += f"""<tr>
            <td>IVA {rate_str}%</td>
            <td class="tr">{fmt_it(grp['base'])}</td>
            <td class="tc">{rate_str}%</td>
            <td class="tr">{fmt_it(grp['tax'])}</td>
        </tr>"""

    sconto_row = ""
    if sconto_globale > 0:
        sconto_row = f"""<tr class="summary-row">
            <td>Sconto globale ({fmt_it(sconto_globale)}%):</td>
            <td class="tr">-{fmt_it(iva_data['sconto_val'])}</td>
        </tr>"""

    return f"""
    <div class="totals-block">
        <table class="iva-table">
            <thead><tr>
                <th>Dettaglio IVA</th><th>Imponibile</th><th>% IVA</th><th>Imposta</th>
            </tr></thead>
            <tbody>{iva_rows}</tbody>
        </table>
        <table class="summary-table">
            {sconto_row}
            <tr class="summary-row">
                <td><strong>TOTALE IMPONIBILE:</strong></td>
                <td class="tr">{fmt_it(iva_data['imponibile'])}</td>
            </tr>
            <tr class="summary-row">
                <td><strong>Totale IVA:</strong></td>
                <td class="tr">{fmt_it(iva_data['total_vat'])}</td>
            </tr>
            {extra_rows}
            <tr class="total-final">
                <td><strong>Totale:</strong></td>
                <td class="tr"><strong>{fmt_it(iva_data['total'])} &euro;</strong></td>
            </tr>
        </table>
    </div>"""


# ── Conditions page builder ─────────────────────────────────────

def build_conditions_html(company: dict, doc_number: str) -> str:
    """Build the conditions page with acceptance section."""
    co = company or {}
    condizioni = co.get("condizioni_vendita", "") or ""
    if not condizioni.strip():
        return ""

    company_name = safe(co.get("business_name"))
    return f"""
    <div class="page-break"></div>
    <h2 class="conditions-title">CONDIZIONI GENERALI DI VENDITA</h2>
    <div class="conditions-text">{_esc(condizioni).replace(chr(10), "<br>")}</div>
    <div class="acceptance-section">
        <div class="sig-block">
            <p>Firma e timbro per accettazione</p>
            <div class="sig-line"></div>
            <p class="sig-label">Data di accettazione</p>
            <p class="sig-label">(legale rappresentante)</p>
        </div>
        <div class="legal-notice">
            <p>Ai sensi e per gli effetti dell'Art. 1341 e segg. Del Codice Civile,
            il sottoscritto Acquirente dichiara di aver preso specifica, precisa e
            dettagliata visione di tutte le disposizioni del contratto e di approvarle
            integralmente senza alcuna riserva.</p>
        </div>
        <div class="sig-block" style="margin-top: 20px;">
            <p>li _______________</p>
            <div class="sig-line"></div>
            <p class="sig-label">Firma e timbro (il legale rappresentante)</p>
        </div>
    </div>
    <div class="doc-footer">
        <p>{company_name}</p>
        <p>Documento {safe(doc_number)}</p>
    </div>"""


# ── Render to PDF ───────────────────────────────────────────────

def render_pdf(body_html: str) -> BytesIO:
    """Wrap body HTML with common CSS and render to PDF via WeasyPrint."""
    from weasyprint import HTML

    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{COMMON_CSS}</style>
</head><body>{body_html}</body></html>"""

    buf = BytesIO()
    HTML(string=full_html).write_pdf(buf)
    buf.seek(0)
    return buf


def format_date(d) -> str:
    """Format a date value to dd-mm-yyyy."""
    if isinstance(d, datetime):
        return d.strftime("%d-%m-%Y")
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%d-%m-%Y")
        except Exception:
            return d
    return datetime.now().strftime("%d-%m-%Y")

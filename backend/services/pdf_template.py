"""Shared PDF template utilities for all document types.

Provides consistent HTML/CSS styling, header layout, and helpers
for Preventivi, Fatture, and DDT using WeasyPrint.
"""
from io import BytesIO
from datetime import datetime
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
    background: white;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: Arial, Helvetica, "Liberation Sans", sans-serif;
    font-size: 9pt;
    color: #111;
    line-height: 1.35;
    background-color: #ffffff;
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
    max-width: 120px;
    max-height: 60px;
    margin-bottom: 6px;
}
.company-name {
    font-size: 13pt;
    font-weight: bold;
    color: #111;
    margin-bottom: 3px;
}
.company-details {
    font-size: 8pt;
    color: #444;
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
    color: #111;
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
    border-top: 1px solid #ccc;
    padding-top: 12px;
}
.doc-title h1 {
    font-size: 16pt;
    font-weight: bold;
    color: #111;
    letter-spacing: 2px;
    margin: 0 0 2px 0;
}
.doc-num {
    font-size: 13pt;
    font-weight: bold;
    color: #222;
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
    color: #222;
}
.meta-label {
    font-weight: bold;
    white-space: nowrap;
    width: 110px;
    color: #444;
}
.ref-note {
    margin: 8px 0;
    padding: 5px 8px;
    background: #f7f7f7;
    border-left: 3px solid #4A90D9;
    font-size: 8.5pt;
    color: #222;
}

/* ── ITEMS TABLE ── */
.items-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 6px 0;
    font-size: 8pt;
}
.items-table th {
    background: #F2F4F7;
    border: 1px solid #ccc;
    padding: 5px 4px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 7.5pt;
    text-align: center;
    color: #111;
}
.items-table td {
    border: 1px solid #ddd;
    padding: 4px 4px;
    vertical-align: top;
    color: #111;
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
    background: #f7f7f7;
    border: 1px solid #ddd;
    font-size: 8pt;
    line-height: 1.4;
    color: #222;
}
.info-box-title {
    font-weight: bold;
    margin-bottom: 3px;
    font-size: 8.5pt;
    color: #111;
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
    background: #F2F4F7;
    border: 1px solid #ccc;
    padding: 4px 5px;
    font-size: 7.5pt;
    text-transform: uppercase;
    text-align: center;
    color: #111;
}
.iva-table td {
    border: 1px solid #ddd;
    padding: 3px 5px;
    color: #111;
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
    color: #111;
}
.summary-row td { font-size: 9pt; }
.total-final td {
    font-size: 13pt;
    font-weight: bold;
    border-top: 1px solid #ccc;
    padding-top: 6px;
    color: #111;
    background: #F2F4F7;
}

/* ── BANK / PAYMENT INFO ── */
.bank-info {
    margin-top: 12px;
    padding: 6px 8px;
    border: 1px solid #ddd;
    font-size: 8pt;
    background: #f7f7f7;
    color: #222;
}

/* ── PAYMENT SCHEDULE ── */
.payment-schedule {
    margin-top: 12px;
    padding: 8px;
    border: 1px solid #ccc;
    background: #FAFBFC;
}
.schedule-title {
    font-size: 9pt;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #333;
}
.schedule-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
}
.schedule-table th {
    background: #F2F4F7;
    border: 1px solid #ccc;
    padding: 3px 6px;
    font-weight: bold;
    text-align: center;
    color: #111;
}
.schedule-table td {
    border: 1px solid #ddd;
    padding: 3px 6px;
    color: #111;
}

/* ── TRANSPORT INFO (DDT) ── */
.transport-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 6px 0;
}
.transport-table td {
    border: 1px solid #ddd;
    padding: 3px 5px;
    color: #111;
}
.transport-table .t-label {
    font-weight: bold;
    background: #FFFFFF;
    width: 22%;
    color: #333;
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
    border-top: 1px solid #4A90D9;
    margin-top: 40px;
    padding-top: 4px;
    font-size: 7.5pt;
    color: #444;
}

/* ── CONDITIONS (PAGE 2) ── */
.conditions-title {
    font-size: 10pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 8px;
    text-transform: uppercase;
    color: #111;
}
.conditions-text {
    font-size: 7pt;
    line-height: 1.3;
    text-align: justify;
    color: #222;
}
.acceptance-section { margin-top: 14px; }
.sig-block { margin: 8px 0; }
.sig-line {
    border-bottom: 1px solid #4A90D9;
    width: 250px;
    height: 22px;
    margin: 3px 0;
}
.sig-label { font-size: 7pt; color: #444; }
.legal-notice {
    margin-top: 10px;
    font-size: 6.5pt;
    line-height: 1.35;
    border: 1px solid #ddd;
    padding: 5px 7px;
    background: #ffffff;
    color: #333;
}
.doc-footer {
    margin-top: 14px;
    text-align: right;
    font-size: 7.5pt;
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

    cl_border = ""
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

def build_conditions_html(company: dict, doc_number: str, preventivo: dict = None) -> str:
    """Build the conditions page with acceptance section.
    
    If `preventivo` is provided, dynamic values (payment, validity, delivery, 
    company address) replace hardcoded text in the conditions.
    """
    import re
    co = company or {}
    prev = preventivo or {}
    condizioni = (co.get("condizioni_vendita", "") or "").strip().strip('"').strip()
    if not condizioni:
        return ""

    # ── Typo fixes ──
    condizioni = condizioni.replace("se no nespressamente", "se non espressamente")
    condizioni = condizioni.replace("materiali incantiere", "materiali in cantiere")
    condizioni = condizioni.replace("fatto salvonell\u2019area di cantiere nonci sia", "fatto salvo nell\u2019area di cantiere non ci sia")
    condizioni = condizioni.replace("fatto salvonell'area di cantiere nonci sia", "fatto salvo nell'area di cantiere non ci sia")
    condizioni = condizioni.replace("Oneri pe reventuali", "Oneri per eventuali")

    # ── Dynamic company address ──
    co_addr = safe(co.get("address") or "")
    co_cap = safe(co.get("cap") or "")
    co_city = safe(co.get("city") or "")
    co_prov = safe(co.get("province") or "")
    dynamic_address = ""
    if co_addr or co_city:
        full_address_parts = [co_addr]
        if co_cap:
            full_address_parts.append(co_cap)
        if co_city:
            city_str = co_city
            if co_prov:
                city_str += f" ({co_prov})"
            full_address_parts.append(city_str)
        dynamic_address = " - ".join(p for p in full_address_parts if p)
        # Replace known hardcoded addresses
        condizioni = condizioni.replace("via dei Pioppi n. 11 - 40010 Padulle BO", dynamic_address)
        condizioni = condizioni.replace("via dei Pioppi n. 11 - 40010 Padulle (BO)", dynamic_address)
        condizioni = condizioni.replace("via dei Pioppi n.11 - 40010 Padulle BO", dynamic_address)

    # ── Dynamic preventivo values (legacy regex fallback) ──
    if prev:
        # Payment (punto 2f)
        payment_label = prev.get("payment_type_label") or ""
        if payment_label:
            condizioni = re.sub(
                r"(Pagamento\s*:\s*)Acconto del 40%[^\n]*",
                r"\g<1>" + payment_label,
                condizioni
            )

        # Validity (punto 2g)
        validity = prev.get("validity_days") or 30
        condizioni = re.sub(
            r"(\d+)\s*giorni dalla data di emissione",
            f"{validity} giorni dalla data di emissione",
            condizioni
        )

        # Delivery (punto 2c)
        consegna = prev.get("consegna") or ""
        if consegna:
            condizioni = re.sub(
                r"(Consegna\s*:\s*)\d+/\d+\s*giorni dalla data di accettazione",
                r"\g<1>" + consegna,
                condizioni
            )

    # ── Template placeholders ──
    # Users can write {pagamento}, {validita}, etc. in their conditions text.
    # These get replaced with actual values at render time.
    from datetime import datetime as _dt
    _payment = (prev.get("payment_type_label") or "") if prev else ""
    _validity = str(prev.get("validity_days") or 30) if prev else "30"
    _consegna = (prev.get("consegna") or "Da concordare") if prev else "Da concordare"
    _doc_date = ""
    if prev:
        _raw_date = prev.get("created_at", "")
        if isinstance(_raw_date, _dt):
            _doc_date = _raw_date.strftime("%d/%m/%Y")
        elif isinstance(_raw_date, str) and _raw_date:
            try:
                _doc_date = _dt.fromisoformat(_raw_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
            except Exception:
                _doc_date = _raw_date

    _full_addr = dynamic_address if (co_addr or co_city) else safe(co.get("address") or "")

    placeholders = {
        "ragione_sociale": safe(co.get("business_name") or ""),
        "indirizzo": _full_addr,
        "partita_iva": safe(co.get("partita_iva") or ""),
        "codice_fiscale": safe(co.get("codice_fiscale") or ""),
        "pec": safe(co.get("pec") or ""),
        "telefono": safe(co.get("phone") or co.get("tel") or ""),
        "email_azienda": safe(co.get("email") or co.get("contact_email") or ""),
        "pagamento": _payment,
        "validita": _validity,
        "consegna": _consegna,
        "numero_documento": safe(doc_number),
        "data_documento": _doc_date,
    }
    for key, val in placeholders.items():
        condizioni = condizioni.replace("{" + key + "}", val)

    company_name = safe(co.get("business_name"))
    
    # Se il testo condizioni contiene già la sezione firma, non duplicarla
    has_signature = "firma e timbro" in condizioni.lower()
    
    acceptance_html = ""
    if not has_signature:
        acceptance_html = """
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
    </div>"""

    return f"""
    <div class="page-break"></div>
    <h2 class="conditions-title">CONDIZIONI GENERALI DI VENDITA</h2>
    <div class="conditions-text">{_esc(condizioni).replace(chr(10), "<br>")}</div>
    {acceptance_html}
    <div class="doc-footer">
        <p>{company_name}</p>
        <p>Documento {safe(doc_number)}</p>
    </div>"""


# ── Render to PDF ───────────────────────────────────────────────

def render_pdf(body_html: str) -> BytesIO:
    """Wrap body HTML with common CSS and render to PDF via WeasyPrint."""
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError(
            f"WeasyPrint non disponibile. Verifica le librerie di sistema (libcairo2, libpango). Dettaglio: {e}"
        )

    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{COMMON_CSS}</style>
</head><body>{body_html}</body></html>"""

    buf = BytesIO()
    try:
        HTML(string=full_html).write_pdf(buf)
    except Exception as e:
        raise RuntimeError(f"Errore generazione PDF WeasyPrint: {e}")
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

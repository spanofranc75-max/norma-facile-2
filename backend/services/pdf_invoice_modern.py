"""Professional Invoice PDF generator — clean, modern design.

Replaces the old 'receipt-like' layout with a proper business invoice:
- Spacious header with logo + right-aligned company info
- Client section WITHOUT box borders
- Generous table padding with zebra rows
- Prominent due date near totals
- Modern sans-serif typography (Helvetica/Liberation Sans)
"""
from io import BytesIO
from datetime import datetime, timezone
import html as html_mod
import logging

logger = logging.getLogger(__name__)

_esc = html_mod.escape


def _fmt(n) -> str:
    """Format number Italian style: 1.234,56"""
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _s(val) -> str:
    return _esc(str(val or ""))


def _date(d) -> str:
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            return d
    return ""


# ═══════════════════════════════════════════════════════════════════
# CSS — Professional invoice design
# ═══════════════════════════════════════════════════════════════════

INVOICE_CSS = """
@page {
    size: A4;
    margin: 14mm 16mm 16mm 16mm;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: Helvetica, "Liberation Sans", Arial, sans-serif;
    font-size: 9pt;
    color: #1a1a2e;
    line-height: 1.4;
}

/* ── HEADER ── */
.inv-header {
    display: table;
    width: 100%;
    margin-bottom: 6mm;
}
.inv-header-left {
    display: table-cell;
    width: 50%;
    vertical-align: top;
}
.inv-header-right {
    display: table-cell;
    width: 50%;
    vertical-align: top;
    text-align: right;
}
.inv-logo img {
    max-width: 180px;
    max-height: 60px;
    margin-bottom: 4px;
}
.inv-company-name {
    font-size: 14pt;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 2px;
}
.inv-company-details {
    font-size: 8pt;
    color: #64748b;
    line-height: 1.6;
}

/* ── DIVIDER ── */
.inv-divider {
    height: 3px;
    background: #0F172A;
    margin: 3mm 0 5mm;
    border-radius: 1px;
}

/* ── TITLE + META ── */
.inv-title-row {
    display: table;
    width: 100%;
    margin-bottom: 5mm;
}
.inv-title-left {
    display: table-cell;
    width: 50%;
    vertical-align: top;
}
.inv-title-right {
    display: table-cell;
    width: 50%;
    vertical-align: top;
    text-align: right;
}
.inv-doc-type {
    font-size: 9pt;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 1px;
}
.inv-doc-number {
    font-size: 22pt;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
}
.inv-meta {
    font-size: 8.5pt;
    color: #475569;
    line-height: 1.8;
}
.inv-meta-label {
    display: inline-block;
    width: 70px;
    font-weight: 600;
    color: #64748b;
}

/* ── CLIENT ── */
.inv-client {
    margin-bottom: 5mm;
    padding: 3mm 0;
}
.inv-client-label {
    font-size: 7.5pt;
    font-weight: 600;
    color: #94a3b8;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.inv-client-name {
    font-size: 12pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 2px;
}
.inv-client-details {
    font-size: 8.5pt;
    color: #475569;
    line-height: 1.6;
}

/* ── ITEMS TABLE ── */
.inv-items {
    width: 100%;
    border-collapse: collapse;
    margin: 3mm 0 4mm;
    font-size: 8.5pt;
}
.inv-items thead th {
    background: #0F172A;
    border-bottom: 2px solid #0F172A;
    padding: 10px 10px;
    font-weight: 700;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #ffffff;
}
.inv-items thead th.al { text-align: left; }
.inv-items thead th.ar { text-align: right; }
.inv-items thead th.ac { text-align: center; }
.inv-items tbody td {
    padding: 10px 10px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}
.inv-items tbody tr:last-child td {
    border-bottom: 2px solid #cbd5e1;
}
.inv-items .desc {
    text-align: left;
    line-height: 1.45;
}
.inv-items .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}
.inv-items .cen {
    text-align: center;
}

/* ── FOOTER AREA: Bank + Totals side by side ── */
.inv-footer-row {
    display: table;
    width: 100%;
    margin-top: 4mm;
}
.inv-footer-left {
    display: table-cell;
    width: 48%;
    vertical-align: top;
    padding-right: 4mm;
}
.inv-footer-right {
    display: table-cell;
    width: 52%;
    vertical-align: top;
}

/* ── BANK INFO ── */
.inv-bank {
    padding: 3mm;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    background: #f8fafc;
    font-size: 8pt;
    color: #475569;
    line-height: 1.7;
}
.inv-bank-title {
    font-size: 7.5pt;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 2px;
    padding-bottom: 2px;
    border-bottom: 1px solid #e2e8f0;
}
.inv-bank-label {
    font-weight: 600;
    color: #334155;
}

/* ── TOTALS ── */
.inv-totals {
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
}
.inv-totals td {
    padding: 4px 8px;
    border: none;
}
.inv-totals .lbl {
    color: #64748b;
    font-weight: 500;
}
.inv-totals .val {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #1a1a2e;
}
.inv-totals .sep td {
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
}
.inv-totals .grand td {
    border-top: 2px solid #0F172A;
    padding-top: 8px;
    padding-bottom: 8px;
}
.inv-totals .grand .lbl {
    font-size: 12pt;
    font-weight: 800;
    color: #0F172A;
}
.inv-totals .grand .val {
    font-size: 18pt;
    font-weight: 800;
    color: #0F172A;
}

/* ── DUE DATE ── */
.inv-due {
    margin-top: 3mm;
    padding: 3mm 4mm;
    background: #fef2f2;
    border: 1px solid #fca5a5;
    border-radius: 4px;
    font-size: 9pt;
}
.inv-due-label {
    font-weight: 600;
    color: #b91c1c;
}
.inv-due-date {
    font-weight: 800;
    color: #991b1b;
    font-size: 11pt;
}

/* ── NOTES ── */
.inv-notes {
    margin-top: 4mm;
    padding: 3mm 4mm;
    background: #fafafa;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    font-size: 8pt;
    color: #475569;
    line-height: 1.5;
}
.inv-notes-title {
    font-weight: 700;
    font-size: 7.5pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}

/* ── PAGE 2: CONDITIONS ── */
.page-break { page-break-before: always; }

/* ── LEGAL FOOTER ── */
.inv-legal-notes {
    margin-top: 5mm;
    padding: 2mm 3mm;
    font-size: 7pt;
    color: #94a3b8;
    line-height: 1.4;
    border-top: 1px solid #e2e8f0;
}
.inv-regulatory-footer {
    margin-top: 2mm;
    padding: 2mm 3mm;
    text-align: center;
    font-size: 7.5pt;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.5px;
}

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


# ═══════════════════════════════════════════════════════════════════
# Generator
# ═══════════════════════════════════════════════════════════════════

DOC_TYPE_NAMES = {
    "FT": "FATTURA",
    "PRV": "PREVENTIVO",
    "DDT": "DOCUMENTO DI TRASPORTO",
    "NC": "NOTA DI CREDITO",
}

PAYMENT_METHOD_NAMES = {
    "bonifico": "Bonifico Bancario",
    "contanti": "Contanti",
    "carta": "Carta di Credito",
    "assegno": "Assegno",
    "riba": "RiBa",
    "altro": "Altro",
}


def generate_modern_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
    """Generate a professional, modern invoice PDF."""
    from weasyprint import HTML

    co = company or {}
    cl = client or {}

    # ── Company info ──
    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<div class="inv-logo"><img src="{logo_url}" /></div>'

    company_name = _s(co.get("business_name"))
    addr = _s(co.get("address"))
    cap = _s(co.get("cap"))
    city = _s(co.get("city"))
    prov = _s(co.get("province"))
    addr_line = addr
    if cap or city:
        parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
        addr_line += "<br>" + " ".join(parts) if addr else " ".join(parts)

    piva = _s(co.get("partita_iva"))
    cf = _s(co.get("codice_fiscale"))
    phone = _s(co.get("phone") or co.get("tel"))
    email = _s(co.get("email") or co.get("contact_email"))

    company_right = f"""
    <div class="inv-company-name">{company_name}</div>
    <div class="inv-company-details">
        {addr_line}
        {"<br>P.IVA " + piva if piva else ""}
        {"<br>C.F. " + cf if cf else ""}
        {"<br>Tel " + phone if phone else ""}
        {"<br>" + email if email else ""}
    </div>"""

    # ── Document info ──
    doc_type = invoice.get("document_type", "FT")
    doc_title = DOC_TYPE_NAMES.get(doc_type, "DOCUMENTO")
    doc_number = _s(invoice.get("document_number", ""))
    display_num = doc_number.replace("FT-", "").replace("NC-", "")
    issue_date = _date(invoice.get("issue_date", ""))
    due_date = invoice.get("due_date")
    payment_label = invoice.get("payment_terms") or PAYMENT_METHOD_NAMES.get(
        invoice.get("payment_method", ""), invoice.get("payment_method", "")
    )

    meta_html = f"""
    <div class="inv-meta">
        <span class="inv-meta-label">Data:</span> {issue_date}<br>
        <span class="inv-meta-label">Pagamento:</span> {_s(payment_label)}
    </div>"""

    # ── Client ──
    cl_name = _s(cl.get("business_name"))
    cl_addr = _s(cl.get("address"))
    cl_cap = _s(cl.get("cap"))
    cl_city = _s(cl.get("city"))
    cl_prov = _s(cl.get("province"))
    cl_full = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full += "<br>" + " ".join(parts) if cl_addr else " ".join(parts)
    cl_piva = _s(cl.get("partita_iva"))
    cl_cf = _s(cl.get("codice_fiscale"))
    cl_sdi = _s(cl.get("codice_sdi"))
    cl_pec = _s(cl.get("pec"))

    client_html = f"""
    <div class="inv-client">
        <div class="inv-client-label">Spettabile Cliente</div>
        <div class="inv-client-name">{cl_name}</div>
        <div class="inv-client-details">
            {cl_full}
            {"<br>P.IVA " + cl_piva if cl_piva else ""}
            {"<br>C.F. " + cl_cf if cl_cf else ""}
            {"<br>Cod. SDI " + cl_sdi if cl_sdi else ""}
            {"<br>PEC " + cl_pec if cl_pec else ""}
        </div>
    </div>"""

    # ── Line items ──
    lines = invoice.get("lines", [])
    rows_html = ""
    for ln in lines:
        desc = _s(ln.get("description") or "").replace("\n", "<br>")
        qty = _fmt(ln.get("quantity", 0))
        price = _fmt(ln.get("unit_price", 0))
        disc = float(ln.get("discount_percent") or ln.get("sconto_1") or 0)
        disc2 = float(ln.get("sconto_2") or 0)
        disc_str = f"{_fmt(disc)}%" if disc > 0 else ""
        if disc2 > 0:
            disc_str += f" + {_fmt(disc2)}%" if disc_str else f"{_fmt(disc2)}%"
        vat = _s(str(ln.get("vat_rate", "22")))
        total = _fmt(ln.get("line_total", 0))

        rows_html += f"""<tr>
            <td class="desc">{desc}</td>
            <td class="num">{qty}</td>
            <td class="num">{price}</td>
            <td class="cen">{disc_str}</td>
            <td class="cen">{vat}%</td>
            <td class="num"><strong>{total}</strong></td>
        </tr>"""

    # ── Compute IVA ──
    from services.pdf_template import compute_iva_groups
    iva_data = compute_iva_groups(lines)

    # IVA breakdown rows
    iva_rows = ""
    for rate_str, grp in sorted(iva_data["groups"].items()):
        iva_rows += f"""<tr>
            <td class="lbl">IVA {rate_str}% su {_fmt(grp['base'])}</td>
            <td class="val">{_fmt(grp['tax'])}</td>
        </tr>"""

    # Extra rows for ritenuta
    totals = invoice.get("totals", {})
    ritenuta = float(totals.get("ritenuta", 0) or 0)
    ritenuta_rows = ""
    if ritenuta > 0:
        netto = iva_data["total"] - ritenuta
        ritenuta_rows = f"""<tr>
            <td class="lbl">Ritenuta d'acconto:</td>
            <td class="val">-{_fmt(ritenuta)}</td>
        </tr>
        <tr class="grand">
            <td class="lbl">NETTO A PAGARE:</td>
            <td class="val">{_fmt(netto)} &euro;</td>
        </tr>"""

    totals_html = f"""
    <table class="inv-totals">
        <tr>
            <td class="lbl">Imponibile:</td>
            <td class="val">{_fmt(iva_data['imponibile'])}</td>
        </tr>
        {iva_rows}
        <tr class="sep">
            <td class="lbl">Totale IVA:</td>
            <td class="val">{_fmt(iva_data['total_vat'])}</td>
        </tr>
        <tr class="grand">
            <td class="lbl">TOTALE</td>
            <td class="val">{_fmt(iva_data['total'])} &euro;</td>
        </tr>
        {ritenuta_rows}
    </table>"""

    # ── Due date (prominent) ──
    due_html = ""
    if due_date:
        due_html = f"""
        <div class="inv-due">
            <span class="inv-due-label">Scadenza Pagamento:</span>
            <span class="inv-due-date">{_date(due_date)}</span>
        </div>"""

    # ── Bank info + Payment Conditions ──
    bank_html = ""
    bank = co.get("bank_details", {}) or {}
    bank_name = _s(bank.get("bank_name", ""))
    bank_iban = _s(bank.get("iban", ""))
    bank_bic = _s(bank.get("bic_swift", ""))

    # Build payment conditions label
    payment_cond_label = _s(payment_label)
    payment_type_label = _s(invoice.get("payment_type_label", ""))
    if payment_type_label:
        payment_cond_label = payment_type_label

    bank_lines = []
    bank_lines.append(f'<span class="inv-bank-label">Condizioni di Pagamento:</span> {payment_cond_label}<br>')
    if bank_name:
        bank_lines.append(f'<span class="inv-bank-label">Banca:</span> {bank_name}<br>')
    if bank_iban:
        bank_lines.append(f'<span class="inv-bank-label">IBAN:</span> {bank_iban}<br>')
    if bank_bic:
        bank_lines.append(f'<span class="inv-bank-label">BIC/SWIFT:</span> {bank_bic}')

    bank_html = f"""
        <div class="inv-bank">
            <div class="inv-bank-title">Dati Pagamento</div>
            {''.join(bank_lines)}
        </div>"""

    # ── Notes ──
    notes_html = ""
    if invoice.get("notes"):
        notes_html = f"""
        <div class="inv-notes">
            <div class="inv-notes-title">Note</div>
            {_s(invoice["notes"]).replace(chr(10), "<br>")}
        </div>"""

    # ── Conditions page (SOLO per Preventivi, NON per Fatture) ──
    conditions_html = ""
    condizioni = co.get("condizioni_vendita", "") or ""
    if condizioni.strip() and doc_type == "PRV":
        conditions_html = f"""
        <div class="page-break"></div>
        <h2 class="conditions-title">CONDIZIONI GENERALI DI VENDITA</h2>
        <div class="conditions-text">{_esc(condizioni).replace(chr(10), "<br>")}</div>
        <div class="acceptance-section">
            <div class="sig-block">
                <p>Firma e timbro per accettazione</p>
                <div class="sig-line"></div>
                <p class="sig-label">Data di accettazione (legale rappresentante)</p>
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
            <p>Documento {display_num}</p>
        </div>"""

    # ── Legal + Regulatory footer ──
    legal_html = """
    <div class="inv-legal-notes">
        Condizioni Generali di Vendita: Riserva di propriet&agrave; ex art. 1523 C.C. &mdash;
        Interessi moratori ex D.Lgs 231/02 &mdash; Foro competente esclusivo quello della sede legale del venditore.
    </div>
    <div class="inv-regulatory-footer">
        Azienda Certificata EN 1090-1 EXC2 &bull; ISO 3834-2 &bull; Centro di Trasformazione Acciaio
    </div>"""

    # ── Assemble full HTML ──
    full_html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<style>{INVOICE_CSS}</style>
</head><body>

    <!-- HEADER -->
    <div class="inv-header">
        <div class="inv-header-left">{logo_html}</div>
        <div class="inv-header-right">{company_right}</div>
    </div>

    <div class="inv-divider"></div>

    <!-- TITLE + META -->
    <div class="inv-title-row">
        <div class="inv-title-left">
            <div class="inv-doc-type">{doc_title}</div>
            <div class="inv-doc-number">{display_num}</div>
        </div>
        <div class="inv-title-right">{meta_html}</div>
    </div>

    <!-- CLIENT -->
    {client_html}

    <!-- ITEMS TABLE -->
    <table class="inv-items">
        <colgroup>
            <col style="width:44%"><col style="width:8%"><col style="width:14%">
            <col style="width:10%"><col style="width:8%"><col style="width:16%">
        </colgroup>
        <thead><tr>
            <th class="al">Descrizione</th>
            <th class="ar">Q.ta'</th>
            <th class="ar">Prezzo Unit.</th>
            <th class="ac">Sconto</th>
            <th class="ac">IVA</th>
            <th class="ar">Importo</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>

    {notes_html}

    <!-- FOOTER: Bank + Totals -->
    <div class="inv-footer-row">
        <div class="inv-footer-left">{bank_html}</div>
        <div class="inv-footer-right">
            {totals_html}
            {due_html}
        </div>
    </div>

    <!-- LEGAL + REGULATORY FOOTER -->
    {legal_html}

    {conditions_html}

</body></html>"""

    buf = BytesIO()
    HTML(string=full_html).write_pdf(buf)
    buf.seek(0)
    return buf.getvalue()

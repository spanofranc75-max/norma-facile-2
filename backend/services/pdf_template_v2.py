"""
PDF Template V2 - Unified professional document format.
Based on Steel Project Design Srls style.
Used for: RdP, OdA, Fatture, DDT, Preventivi
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available - PDF generation disabled")


# ══════════════════════════════════════════════════════════════════
#  UNIFIED CSS TEMPLATE
# ══════════════════════════════════════════════════════════════════

UNIFIED_CSS = """
@page {
    size: A4;
    margin: 15mm 12mm;
}
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 10pt;
    color: #1a1a1a;
    line-height: 1.4;
    margin: 0;
    padding: 0;
}

/* Header Section */
.header-section {
    display: table;
    width: 100%;
    margin-bottom: 8px;
}
.header-left, .header-right {
    display: table-cell;
    vertical-align: top;
    width: 50%;
}
.header-right {
    text-align: right;
}
.company-logo {
    max-width: 80px;
    max-height: 50px;
    margin-bottom: 5px;
}
.company-name {
    color: #1e3a5f;
    font-size: 14pt;
    font-weight: 600;
    margin: 0 0 3px 0;
}
.company-details {
    font-size: 9pt;
    color: #444;
    line-height: 1.5;
}
.spettabile-label {
    font-size: 8pt;
    color: #888;
    font-style: italic;
    margin-bottom: 2px;
}
.dest-name {
    font-size: 12pt;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 3px;
}
.dest-details {
    font-size: 9pt;
    color: #444;
    line-height: 1.5;
}

/* Blue separator line */
.blue-separator {
    border-top: 2px solid #1e3a5f;
    margin: 12px 0 20px 0;
}

/* Document Title */
.doc-title {
    text-align: center;
    font-size: 14pt;
    font-weight: 700;
    color: #1e3a5f;
    margin: 0 0 20px 0;
    letter-spacing: 0.5px;
}

/* Info boxes (DATA | RIF. COMMESSA) */
.info-boxes {
    display: table;
    width: 100%;
    margin-bottom: 15px;
    border: 1px solid #d0d0d0;
    border-collapse: collapse;
}
.info-box {
    display: table-cell;
    width: 50%;
    padding: 8px 12px;
    border: 1px solid #d0d0d0;
}
.info-label {
    font-size: 8pt;
    color: #1e3a5f;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.info-value {
    font-size: 11pt;
    color: #1a1a1a;
}

/* Oggetto line */
.oggetto-line {
    margin-bottom: 15px;
    font-size: 10pt;
}
.oggetto-label {
    font-weight: 600;
}

/* Main table */
.items-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 15px;
}
.items-table thead tr {
    background: #1e3a5f;
    color: white;
}
.items-table th {
    padding: 10px 8px;
    text-align: left;
    font-size: 9pt;
    font-weight: 600;
}
.items-table th.tc { text-align: center; }
.items-table th.tr { text-align: right; }
.items-table td {
    padding: 8px;
    border-bottom: 1px solid #e0e0e0;
    font-size: 9pt;
}
.items-table td.tc { text-align: center; }
.items-table td.tr { text-align: right; }
.items-table tbody tr:nth-child(even) {
    background: #f8f9fa;
}
.items-table tbody tr:last-child td {
    border-bottom: 2px solid #1e3a5f;
}

/* Total row */
.total-row {
    background: #e8f0f7 !important;
}
.total-row td {
    font-weight: 600;
    font-size: 10pt;
    padding: 10px 8px;
}

/* Alert/Info boxes */
.alert-box {
    padding: 10px 12px;
    margin-bottom: 10px;
    border-left: 4px solid;
    font-size: 9pt;
}
.alert-box.warning {
    background: #fff3cd;
    border-color: #ffc107;
}
.alert-box.info {
    background: #fff8e1;
    border-color: #ffb300;
}
.alert-box.success {
    background: #d4edda;
    border-color: #28a745;
}
.alert-label {
    font-weight: 600;
    margin-right: 5px;
}

/* Footer section */
.footer-section {
    margin-top: 30px;
    text-align: center;
}
.footer-greeting {
    font-style: italic;
    color: #555;
    margin-bottom: 15px;
}
.footer-company {
    font-weight: 600;
    color: #1e3a5f;
    font-size: 11pt;
    text-decoration: underline;
    margin-bottom: 5px;
}
.footer-contacts {
    font-size: 9pt;
    color: #555;
}

/* Utility classes */
.text-center { text-align: center; }
.text-right { text-align: right; }
.font-mono { font-family: 'Consolas', monospace; }
.bold { font-weight: 600; }
.small { font-size: 8pt; }
"""


def safe(val: Any) -> str:
    """Escape HTML and handle None."""
    if val is None:
        return ""
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_it(val: float) -> str:
    """Format number Italian style (1.234,56)."""
    try:
        v = float(val)
        formatted = f"{v:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(val)


def fmt_date(date_str: str) -> str:
    """Format date to DD/MM/YYYY or YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        return date_str[:10]
    except (ValueError, AttributeError):
        return date_str[:10] if date_str else datetime.now().strftime("%Y-%m-%d")


def build_header(company: Dict, dest_name: str, dest_address: str = "", dest_piva: str = "") -> str:
    """Build the two-column header section."""
    # Logo
    logo_html = ""
    logo_url = company.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="company-logo" /><br/>'
    
    company_name = safe(company.get("business_name", ""))
    address = safe(company.get("address", ""))
    city = safe(company.get("city", ""))
    province = safe(company.get("province", ""))
    cap = safe(company.get("cap", ""))
    piva = safe(company.get("vat_number", ""))
    phone = safe(company.get("phone", ""))
    email = safe(company.get("email", ""))
    
    full_address = f"{address}"
    if cap or city:
        full_address += f"<br/>{cap} {city}"
        if province:
            full_address += f" ({province})"
    
    return f"""
    <div class="header-section">
        <div class="header-left">
            {logo_html}
            <div class="company-name">{company_name}</div>
            <div class="company-details">
                {full_address}<br/>
                P.IVA: {piva}<br/>
                Tel: {phone} | Email:<br/>
                {email}
            </div>
        </div>
        <div class="header-right">
            <div class="spettabile-label">Spett.le</div>
            <div class="dest-name">{safe(dest_name)}</div>
            <div class="dest-details">
                {safe(dest_address)}
                {f'<br/>P.IVA: {safe(dest_piva)}' if dest_piva else ''}
            </div>
        </div>
    </div>
    <div class="blue-separator"></div>
    """


def build_info_boxes(left_label: str, left_value: str, right_label: str, right_value: str) -> str:
    """Build the two-cell info boxes (DATA | RIF. COMMESSA)."""
    return f"""
    <div class="info-boxes">
        <div class="info-box">
            <div class="info-label">{safe(left_label)}</div>
            <div class="info-value">{safe(left_value)}</div>
        </div>
        <div class="info-box">
            <div class="info-label">{safe(right_label)}</div>
            <div class="info-value">{safe(right_value)}</div>
        </div>
    </div>
    """


def build_footer(company: Dict) -> str:
    """Build the footer with greeting and contacts."""
    company_name = safe(company.get("business_name", ""))
    phone = safe(company.get("phone", ""))
    email = safe(company.get("email", ""))
    
    return f"""
    <div class="footer-section">
        <div class="footer-greeting">In attesa di Vs. cortese riscontro, porgiamo distinti saluti.</div>
        <div class="footer-company">{company_name}</div>
        <div class="footer-contacts">{phone} - {email}</div>
    </div>
    """


# ══════════════════════════════════════════════════════════════════
#  DOCUMENT GENERATORS
# ══════════════════════════════════════════════════════════════════

def generate_rdp_pdf_v2(
    rdp: Dict,
    commessa: Dict,
    company: Dict,
    fornitore: Optional[Dict] = None,
) -> bytes:
    """Generate PDF for Richiesta di Preventivo (RdP) - V2 format."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    # Extract data
    rdp_id = rdp.get("rdp_id", "")
    fornitore_nome = rdp.get("fornitore_nome", "N/D")
    righe = rdp.get("righe", [])
    note = rdp.get("note", "")
    data_richiesta = rdp.get("data_richiesta", "")
    
    commessa_numero = commessa.get("numero", "N/D")
    
    # Get fornitore address if available
    fornitore_address = ""
    fornitore_piva = ""
    if fornitore:
        fornitore_address = f"{fornitore.get('address', '')}<br/>{fornitore.get('cap', '')} {fornitore.get('city', '')}"
        fornitore_piva = fornitore.get('vat_number', '')
    
    # Build header
    header_html = build_header(company, fornitore_nome, fornitore_address, fornitore_piva)
    
    # Document title
    doc_number = f"RDA-{commessa_numero}-{rdp_id[-4:]}" if rdp_id else f"RDA-{commessa_numero}"
    title_html = f'<h1 class="doc-title">RICHIESTA DI PREVENTIVO N. {safe(doc_number)}</h1>'
    
    # Info boxes
    info_html = build_info_boxes(
        "DATA", fmt_date(data_richiesta),
        "RIF. COMMESSA", commessa_numero
    )
    
    # Oggetto
    oggetto_html = f'<p class="oggetto-line"><span class="oggetto-label">Oggetto:</span> Fornitura materiali {commessa_numero}</p>'
    
    # Build table rows
    rows_html = ""
    has_cert_31 = False
    for riga in righe:
        desc = safe(riga.get("descrizione", ""))
        qty = fmt_it(riga.get("quantita", 1))
        um = safe(riga.get("unita_misura", "pz"))
        cert = riga.get("richiede_cert_31", False)
        if cert:
            has_cert_31 = True
        note_riga = "Cert. 3.1" if cert else ""
        
        rows_html += f"""
        <tr>
            <td>{desc}</td>
            <td class="tc">{qty}</td>
            <td class="tc">{um}</td>
            <td>{note_riga}</td>
        </tr>
        """
    
    table_html = f"""
    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 55%;">Descrizione Materiale</th>
                <th class="tc" style="width: 15%;">Quantità</th>
                <th class="tc" style="width: 10%;">U.M.</th>
                <th style="width: 20%;">Note</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    
    # Certificate alert box
    cert_html = ""
    if has_cert_31:
        cert_html = """
        <div class="alert-box warning">
            <span class="alert-label">CERTIFICATO RICHIESTO:</span>
            Si richiede certificato materiale tipo 3.1 (EN 10204)
        </div>
        """
    
    # Notes box
    notes_html = ""
    if note:
        notes_html = f"""
        <div class="alert-box info">
            <span class="alert-label">Note:</span> {safe(note)}
        </div>
        """
    
    # Footer
    footer_html = build_footer(company)
    
    # Assemble HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>{UNIFIED_CSS}</style>
    </head>
    <body>
        {header_html}
        {title_html}
        {info_html}
        {oggetto_html}
        {table_html}
        {cert_html}
        {notes_html}
        {footer_html}
    </body>
    </html>
    """
    
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()


def generate_oda_pdf_v2(
    oda: Dict,
    commessa: Dict,
    company: Dict,
    fornitore: Optional[Dict] = None,
) -> bytes:
    """Generate PDF for Ordine di Acquisto (OdA) - V2 format."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    # Extract data
    ordine_id = oda.get("ordine_id", "")
    fornitore_nome = oda.get("fornitore_nome", "N/D")
    righe = oda.get("righe", [])
    note = oda.get("note", "")
    importo_totale = oda.get("importo_totale", 0)
    data_ordine = oda.get("data_ordine", "")
    
    commessa_numero = commessa.get("numero", "N/D")
    
    # Get fornitore address if available
    fornitore_address = ""
    fornitore_piva = ""
    if fornitore:
        fornitore_address = f"{fornitore.get('address', '')}<br/>{fornitore.get('cap', '')} {fornitore.get('city', '')}"
        fornitore_piva = fornitore.get('vat_number', '')
    
    # Build header
    header_html = build_header(company, fornitore_nome, fornitore_address, fornitore_piva)
    
    # Document title
    doc_number = f"ODA-{commessa_numero}-{ordine_id[-4:]}" if ordine_id else f"ODA-{commessa_numero}"
    title_html = f'<h1 class="doc-title">ORDINE DI ACQUISTO N. {safe(doc_number)}</h1>'
    
    # Info boxes
    info_html = build_info_boxes(
        "DATA", fmt_date(data_ordine),
        "RIF. COMMESSA", commessa_numero
    )
    
    # Oggetto
    oggetto_html = f'<p class="oggetto-line"><span class="oggetto-label">Oggetto:</span> Ordine materiali {commessa_numero}</p>'
    
    # Build table rows
    rows_html = ""
    has_cert_31 = False
    subtotal = 0
    for riga in righe:
        desc = safe(riga.get("descrizione", ""))
        qty = float(riga.get("quantita", 1))
        um = safe(riga.get("unita_misura", "pz"))
        prezzo = float(riga.get("prezzo_unitario", 0))
        importo = qty * prezzo
        subtotal += importo
        cert = riga.get("richiede_cert_31", False)
        if cert:
            has_cert_31 = True
        note_riga = "3.1" if cert else ""
        
        rows_html += f"""
        <tr>
            <td>{desc}</td>
            <td class="tc">{fmt_it(qty)}</td>
            <td class="tc">{um}</td>
            <td class="tr">{fmt_it(prezzo)}</td>
            <td class="tr">{fmt_it(importo)}</td>
            <td class="tc">{note_riga}</td>
        </tr>
        """
    
    # Total row
    total_display = importo_totale if importo_totale else subtotal
    rows_html += f"""
    <tr class="total-row">
        <td colspan="4" class="text-right bold">TOTALE ORDINE:</td>
        <td class="tr bold">€ {fmt_it(total_display)}</td>
        <td></td>
    </tr>
    """
    
    table_html = f"""
    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 40%;">Descrizione Materiale</th>
                <th class="tc" style="width: 10%;">Q.tà</th>
                <th class="tc" style="width: 8%;">U.M.</th>
                <th class="tr" style="width: 15%;">Prezzo €</th>
                <th class="tr" style="width: 15%;">Importo €</th>
                <th class="tc" style="width: 12%;">Cert.</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    
    # Certificate alert box
    cert_html = ""
    if has_cert_31:
        cert_html = """
        <div class="alert-box warning">
            <span class="alert-label">CERTIFICATO RICHIESTO:</span>
            Si richiede certificato materiale tipo 3.1 (EN 10204)
        </div>
        """
    
    # Notes box
    notes_html = ""
    if note:
        notes_html = f"""
        <div class="alert-box info">
            <span class="alert-label">Note:</span> {safe(note)}
        </div>
        """
    
    # Footer
    footer_html = build_footer(company)
    
    # Assemble HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>{UNIFIED_CSS}</style>
    </head>
    <body>
        {header_html}
        {title_html}
        {info_html}
        {oggetto_html}
        {table_html}
        {cert_html}
        {notes_html}
        {footer_html}
    </body>
    </html>
    """
    
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

"""
PDF Generator for Procurement Documents (RdP, OdA)
Uses WeasyPrint with shared template utilities.
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Optional, List
from services.pdf_template import COMMON_CSS, fmt_it, safe

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available - PDF generation disabled")


# Additional CSS for procurement documents
PROCUREMENT_CSS = """
.procurement-header {
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid #0055FF;
}
.procurement-title {
    font-size: 20pt;
    font-weight: bold;
    color: #0055FF;
    margin: 0;
}
.procurement-subtitle {
    font-size: 10pt;
    color: #666;
    margin-top: 4px;
}
.ref-box {
    background: #f0f4ff;
    border-left: 4px solid #0055FF;
    padding: 10px 15px;
    margin: 15px 0;
    font-size: 9pt;
}
.ref-label {
    color: #666;
    font-size: 8pt;
}
.ref-value {
    font-weight: bold;
    color: #222;
}
.supplier-box {
    border: 1px solid #ddd;
    padding: 15px;
    margin: 15px 0;
    background: #fafafa;
}
.supplier-label {
    font-size: 8pt;
    color: #666;
    text-transform: uppercase;
    margin-bottom: 5px;
}
.supplier-name {
    font-size: 12pt;
    font-weight: bold;
    color: #222;
}
.cert-badge {
    display: inline-block;
    background: #059669;
    color: white;
    font-size: 7pt;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: bold;
}
.notes-section {
    margin-top: 20px;
    padding: 12px;
    background: #fffbeb;
    border: 1px solid #fcd34d;
    font-size: 9pt;
}
.notes-title {
    font-weight: bold;
    color: #92400e;
    margin-bottom: 5px;
}
.footer-info {
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
    font-size: 8pt;
    color: #666;
}
"""


def generate_rdp_pdf(
    rdp: dict,
    commessa: dict,
    company: dict,
    fornitore: Optional[dict] = None,
) -> bytes:
    """Generate PDF for Richiesta di Preventivo (RdP) to supplier."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    # Data extraction
    rdp_id = rdp.get("rdp_id", "")
    fornitore_nome = rdp.get("fornitore_nome", "N/D")
    righe = rdp.get("righe", [])
    note = rdp.get("note", "")
    data_richiesta = rdp.get("data_richiesta", "")
    
    commessa_numero = commessa.get("numero", "N/D")
    cantiere = commessa.get("cantiere", {})
    cantiere_str = f"{cantiere.get('indirizzo', '')} - {cantiere.get('citta', '')}" if cantiere else ""
    
    # Company info with logo
    company_name = company.get("business_name", "")
    company_address = f"{company.get('address', '')}, {company.get('city', '')} ({company.get('province', '')})"
    company_piva = company.get("vat_number", "")
    company_phone = company.get("phone", "")
    company_email = company.get("email", "")
    
    # Logo handling
    logo_html = ""
    logo_url = company.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="logo" style="max-width: 140px; max-height: 55px; margin-bottom: 6px;" />'
    
    # Format date
    try:
        dt = datetime.fromisoformat(data_richiesta.replace("Z", "+00:00"))
        data_fmt = dt.strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        data_fmt = data_richiesta[:10] if data_richiesta else datetime.now().strftime("%d/%m/%Y")

    # Build table rows
    rows_html = ""
    for i, riga in enumerate(righe, 1):
        desc = safe(riga.get("descrizione", ""))
        qty = riga.get("quantita", 1)
        um = safe(riga.get("unita_misura", "pz"))
        cert = riga.get("richiede_cert_31", False)
        cert_badge = '<span class="cert-badge">CERT. 3.1</span>' if cert else ""
        
        rows_html += f"""
        <tr>
            <td class="tc">{i}</td>
            <td class="desc-cell">{desc} {cert_badge}</td>
            <td class="tc">{fmt_it(qty)}</td>
            <td class="tc">{um}</td>
        </tr>
        """

    # Notes section
    notes_html = ""
    if note:
        notes_html = f"""
        <div class="notes-section">
            <div class="notes-title">NOTE E SPECIFICHE:</div>
            <div>{safe(note)}</div>
        </div>
        """

    # Build full HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            {COMMON_CSS}
            {PROCUREMENT_CSS}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="procurement-header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 class="procurement-title">RICHIESTA DI PREVENTIVO</h1>
                    <p class="procurement-subtitle">Rif. {safe(rdp_id)}</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 9pt; color: #666;">Data richiesta</div>
                    <div style="font-size: 14pt; font-weight: bold;">{data_fmt}</div>
                </div>
            </div>
        </div>

        <!-- Two column layout: Company | Supplier -->
        <table class="header-table">
            <tr>
                <td class="company-cell">
                    {logo_html}
                    <div class="company-name">{safe(company_name)}</div>
                    <div class="company-details">
                        {safe(company_address)}<br/>
                        P.IVA: {safe(company_piva)}<br/>
                        Tel: {safe(company_phone)}<br/>
                        Email: {safe(company_email)}
                    </div>
                </td>
                <td class="client-cell">
                    <div class="cl-label">SPETT.LE</div>
                    <div class="cl-name">{safe(fornitore_nome)}</div>
                </td>
            </tr>
        </table>

        <!-- Commessa reference -->
        <div class="ref-box">
            <span class="ref-label">RIFERIMENTO COMMESSA:</span>
            <span class="ref-value">{safe(commessa_numero)}</span>
            {f'<br/><span class="ref-label">CANTIERE:</span> <span class="ref-value">{safe(cantiere_str)}</span>' if cantiere_str.strip(' -') else ''}
        </div>

        <!-- Items table -->
        <p style="font-weight: bold; margin: 15px 0 8px 0; font-size: 10pt;">
            Si richiede cortesemente preventivo per i seguenti materiali:
        </p>
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 8%;">#</th>
                    <th style="width: 62%;">DESCRIZIONE</th>
                    <th style="width: 15%;">QUANTITÀ</th>
                    <th style="width: 15%;">U.M.</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        {notes_html}

        <!-- Footer -->
        <div class="footer-info">
            <p>Si prega di rispondere indicando:</p>
            <ul style="margin: 5px 0 0 20px;">
                <li>Prezzo unitario e totale per ogni voce</li>
                <li>Tempi di consegna previsti</li>
                <li>Eventuali costi di trasporto</li>
                <li>Disponibilità certificati 3.1 ove richiesti</li>
            </ul>
            <p style="margin-top: 15px;">
                In attesa di cortese riscontro, porgiamo distinti saluti.<br/>
                <strong>{safe(company_name)}</strong>
            </p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()


def generate_oda_pdf(
    oda: dict,
    commessa: dict,
    company: dict,
    fornitore: Optional[dict] = None,
) -> bytes:
    """Generate PDF for Ordine di Acquisto (OdA) to supplier."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    # Data extraction
    ordine_id = oda.get("ordine_id", "")
    fornitore_nome = oda.get("fornitore_nome", "N/D")
    righe = oda.get("righe", [])
    note = oda.get("note", "")
    importo_totale = oda.get("importo_totale", 0)
    data_ordine = oda.get("data_ordine", "")
    
    commessa_numero = commessa.get("numero", "N/D")
    cantiere = commessa.get("cantiere", {})
    cantiere_str = f"{cantiere.get('indirizzo', '')} - {cantiere.get('citta', '')}" if cantiere else ""
    
    # Company info
    company_name = company.get("business_name", "")
    company_address = f"{company.get('address', '')}, {company.get('city', '')} ({company.get('province', '')})"
    company_piva = company.get("vat_number", "")
    company_phone = company.get("phone", "")
    company_email = company.get("email", "")
    
    # Format date
    try:
        dt = datetime.fromisoformat(data_ordine.replace("Z", "+00:00"))
        data_fmt = dt.strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        data_fmt = data_ordine[:10] if data_ordine else datetime.now().strftime("%d/%m/%Y")

    # Build table rows
    rows_html = ""
    subtotal = 0
    for i, riga in enumerate(righe, 1):
        desc = safe(riga.get("descrizione", ""))
        qty = float(riga.get("quantita", 1))
        um = safe(riga.get("unita_misura", "pz"))
        prezzo = float(riga.get("prezzo_unitario", 0))
        importo = qty * prezzo
        subtotal += importo
        cert = riga.get("richiede_cert_31", False)
        cert_badge = '<span class="cert-badge">3.1</span>' if cert else ""
        
        rows_html += f"""
        <tr>
            <td class="tc">{i}</td>
            <td class="desc-cell">{desc} {cert_badge}</td>
            <td class="tc">{fmt_it(qty)}</td>
            <td class="tc">{um}</td>
            <td class="tr">{fmt_it(prezzo)}</td>
            <td class="tr"><strong>{fmt_it(importo)}</strong></td>
        </tr>
        """

    # Use calculated subtotal or provided total
    total_display = importo_totale if importo_totale else subtotal

    # Notes section
    notes_html = ""
    if note:
        notes_html = f"""
        <div class="notes-section">
            <div class="notes-title">NOTE:</div>
            <div>{safe(note)}</div>
        </div>
        """

    # Build full HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            {COMMON_CSS}
            {PROCUREMENT_CSS}
            .total-row {{
                background: #f0f4ff;
                font-size: 11pt;
            }}
            .total-row td {{
                padding: 10px 4px !important;
            }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="procurement-header" style="border-color: #059669;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 class="procurement-title" style="color: #059669;">ORDINE DI ACQUISTO</h1>
                    <p class="procurement-subtitle">N. {safe(ordine_id)}</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 9pt; color: #666;">Data ordine</div>
                    <div style="font-size: 14pt; font-weight: bold;">{data_fmt}</div>
                </div>
            </div>
        </div>

        <!-- Two column layout: Company | Supplier -->
        <table class="header-table">
            <tr>
                <td class="company-cell">
                    <div class="company-name">{safe(company_name)}</div>
                    <div class="company-details">
                        {safe(company_address)}<br/>
                        P.IVA: {safe(company_piva)}<br/>
                        Tel: {safe(company_phone)}<br/>
                        Email: {safe(company_email)}
                    </div>
                </td>
                <td class="client-cell">
                    <div class="cl-label">SPETT.LE FORNITORE</div>
                    <div class="cl-name">{safe(fornitore_nome)}</div>
                </td>
            </tr>
        </table>

        <!-- Commessa reference -->
        <div class="ref-box" style="border-color: #059669; background: #f0fdf4;">
            <span class="ref-label">RIFERIMENTO COMMESSA:</span>
            <span class="ref-value">{safe(commessa_numero)}</span>
            {f'<br/><span class="ref-label">CANTIERE:</span> <span class="ref-value">{safe(cantiere_str)}</span>' if cantiere_str.strip(' -') else ''}
        </div>

        <!-- Items table -->
        <p style="font-weight: bold; margin: 15px 0 8px 0; font-size: 10pt;">
            Con la presente si ordina quanto segue:
        </p>
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 6%;">#</th>
                    <th style="width: 42%;">DESCRIZIONE</th>
                    <th style="width: 12%;">Q.TÀ</th>
                    <th style="width: 10%;">U.M.</th>
                    <th style="width: 15%;">PREZZO €</th>
                    <th style="width: 15%;">IMPORTO €</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
                <tr class="total-row">
                    <td colspan="5" style="text-align: right; font-weight: bold;">TOTALE ORDINE:</td>
                    <td class="tr" style="font-weight: bold; color: #059669; font-size: 12pt;">€ {fmt_it(total_display)}</td>
                </tr>
            </tbody>
        </table>

        {notes_html}

        <!-- Footer -->
        <div class="footer-info">
            <p><strong>CONDIZIONI:</strong></p>
            <ul style="margin: 5px 0 0 20px;">
                <li>Consegna: Franco destino nostro magazzino</li>
                <li>Allegare certificati 3.1 ove richiesti</li>
                <li>Comunicare data consegna prevista</li>
            </ul>
            <p style="margin-top: 20px;">
                Distinti saluti,<br/>
                <strong>{safe(company_name)}</strong>
            </p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

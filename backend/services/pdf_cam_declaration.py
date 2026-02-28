"""
PDF Generator for CAM (Criteri Ambientali Minimi) Declaration.
DM 23 giugno 2022 n. 256 - Edilizia
Generates the official compliance declaration document.
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from services.pdf_template_v2 import UNIFIED_CSS, safe, fmt_it, build_header


CAM_EXTRA_CSS = """
.cam-summary {
    display: table;
    width: 100%;
    margin: 15px 0;
    border: 2px solid #1e3a5f;
    border-collapse: collapse;
}
.cam-summary-cell {
    display: table-cell;
    width: 25%;
    padding: 12px;
    text-align: center;
    border: 1px solid #d0d0d0;
}
.cam-summary-label {
    font-size: 8pt;
    color: #555;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.cam-summary-value {
    font-size: 16pt;
    font-weight: 700;
}
.cam-conforme { color: #28a745; }
.cam-non-conforme { color: #dc3545; }
.result-box {
    padding: 15px;
    margin: 15px 0;
    text-align: center;
    font-size: 14pt;
    font-weight: 700;
    border: 3px solid;
}
.result-box.conforme {
    background: #d4edda;
    border-color: #28a745;
    color: #155724;
}
.result-box.non-conforme {
    background: #f8d7da;
    border-color: #dc3545;
    color: #721c24;
}
.normativa-ref {
    background: #f8f9fa;
    padding: 10px 12px;
    margin: 15px 0;
    border-left: 4px solid #1e3a5f;
    font-size: 9pt;
    color: #333;
}
.firma-section {
    margin-top: 40px;
    display: table;
    width: 100%;
}
.firma-cell {
    display: table-cell;
    width: 50%;
    padding: 10px;
}
.firma-line {
    border-bottom: 1px solid #333;
    width: 80%;
    margin: 30px auto 5px auto;
}
.firma-label {
    text-align: center;
    font-size: 9pt;
    color: #555;
}
"""


def generate_cam_declaration_pdf(
    calcolo: Dict,
    commessa: Dict,
    company: Dict,
    cliente: Dict = None,
) -> bytes:
    """Generate CAM compliance declaration PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    commessa_numero = safe(commessa.get("numero", "N/D"))
    commessa_title = safe(commessa.get("title", ""))
    cliente_nome = safe((cliente or {}).get("business_name", commessa.get("client_name", "")))
    cliente_address = ""
    if cliente:
        cliente_address = f"{safe(cliente.get('address', ''))}<br/>{safe(cliente.get('cap', ''))} {safe(cliente.get('city', ''))}"

    # Header
    header_html = build_header(company, cliente_nome, cliente_address)

    # Title
    title_html = f"""
    <h1 class="doc-title">DICHIARAZIONE DI CONFORMITÀ CAM</h1>
    <p style="text-align: center; font-size: 9pt; color: #555; margin-top: -15px; margin-bottom: 15px;">
        ai sensi del DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi per l'Edilizia
    </p>
    """

    # Commessa info
    info_html = f"""
    <div class="info-boxes">
        <div class="info-box">
            <div class="info-label">COMMESSA</div>
            <div class="info-value">{commessa_numero}</div>
        </div>
        <div class="info-box">
            <div class="info-label">DATA DICHIARAZIONE</div>
            <div class="info-value">{datetime.now(timezone.utc).strftime('%d/%m/%Y')}</div>
        </div>
    </div>
    """

    if commessa_title:
        info_html += f'<p class="oggetto-line"><span class="oggetto-label">Oggetto:</span> {commessa_title}</p>'

    # Summary boxes
    peso_totale = calcolo.get("peso_totale_kg", 0)
    peso_riciclato = calcolo.get("peso_riciclato_kg", 0)
    perc_totale = calcolo.get("percentuale_riciclato_totale", 0)
    soglia = calcolo.get("soglia_minima_richiesta", 0)
    conforme = calcolo.get("conforme_cam", False)

    conf_class = "cam-conforme" if conforme else "cam-non-conforme"

    summary_html = f"""
    <div class="cam-summary">
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Peso Totale</div>
            <div class="cam-summary-value" style="color: #1e3a5f;">{fmt_it(peso_totale)} kg</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Peso Riciclato</div>
            <div class="cam-summary-value" style="color: #1e3a5f;">{fmt_it(peso_riciclato)} kg</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">% Riciclato</div>
            <div class="cam-summary-value {conf_class}">{fmt_it(perc_totale)}%</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Soglia Minima</div>
            <div class="cam-summary-value" style="color: #555;">{fmt_it(soglia)}%</div>
        </div>
    </div>
    """

    # Result box
    if conforme:
        result_html = """
        <div class="result-box conforme">
            CONFORME AI CRITERI AMBIENTALI MINIMI
        </div>
        """
    else:
        result_html = """
        <div class="result-box non-conforme">
            NON CONFORME AI CRITERI AMBIENTALI MINIMI
        </div>
        """

    # Materials table
    righe = calcolo.get("righe", [])
    rows_html = ""
    for i, r in enumerate(righe, 1):
        conf_badge = '<span style="color:#28a745;font-weight:600;">SI</span>' if r.get("conforme_cam") else '<span style="color:#dc3545;font-weight:600;">NO</span>'
        metodo_label = {
            "forno_elettrico_non_legato": "Forno El. (non legato)",
            "forno_elettrico_legato": "Forno El. (legato)",
            "ciclo_integrale": "Ciclo Integrale",
            "sconosciuto": "Sconosciuto",
        }.get(r.get("metodo_produttivo", ""), r.get("metodo_produttivo", ""))

        cert_label = {
            "epd": "EPD",
            "remade_in_italy": "ReMade in Italy",
            "dichiarazione_produttore": "Dich. Produttore",
            "altra_accreditata": "Altra",
            "nessuna": "-",
        }.get(r.get("certificazione", ""), r.get("certificazione", ""))

        rows_html += f"""
        <tr>
            <td class="tc">{i}</td>
            <td>{safe(r.get('descrizione', ''))}</td>
            <td class="tr">{fmt_it(r.get('peso_kg', 0))}</td>
            <td class="tc">{fmt_it(r.get('percentuale_riciclato', 0))}%</td>
            <td class="tr">{fmt_it(r.get('peso_riciclato_kg', 0))}</td>
            <td>{metodo_label}</td>
            <td>{cert_label}</td>
            <td class="tc">{fmt_it(r.get('soglia_minima', 0))}%</td>
            <td class="tc">{conf_badge}</td>
        </tr>
        """

    table_html = f"""
    <h3 style="color: #1e3a5f; font-size: 11pt; margin: 20px 0 10px 0;">DETTAGLIO MATERIALI</h3>
    <table class="items-table">
        <thead>
            <tr>
                <th class="tc" style="width:5%;">N.</th>
                <th style="width:20%;">Descrizione</th>
                <th class="tr" style="width:10%;">Peso (kg)</th>
                <th class="tc" style="width:10%;">% Ric.</th>
                <th class="tr" style="width:10%;">Peso Ric.</th>
                <th style="width:15%;">Metodo</th>
                <th style="width:12%;">Cert.</th>
                <th class="tc" style="width:8%;">Soglia</th>
                <th class="tc" style="width:10%;">Conf.</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    # Normativa reference
    normativa_html = """
    <div class="normativa-ref">
        <strong>Riferimento normativo:</strong> DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi per l'affidamento 
        del servizio di progettazione di interventi edilizi, per l'affidamento dei lavori per interventi edilizi e per 
        l'affidamento congiunto di progettazione e lavori per interventi edilizi.<br/><br/>
        <strong>Requisiti acciaio strutturale:</strong> Il contenuto di materia recuperata o riciclata deve essere 
        almeno pari al 75% per acciaio non legato da forno elettrico, 60% per acciaio legato da forno elettrico,
        12% per acciaio da ciclo integrale (altoforno).
    </div>
    """

    # Signature section
    firma_html = f"""
    <div class="firma-section">
        <div class="firma-cell">
            <div class="firma-label">Luogo e Data</div>
            <div class="firma-line"></div>
            <div class="firma-label" style="margin-top: 5px;">_________________, {datetime.now(timezone.utc).strftime('%d/%m/%Y')}</div>
        </div>
        <div class="firma-cell">
            <div class="firma-label">Timbro e Firma</div>
            <div class="firma-line"></div>
            <div class="firma-label" style="margin-top: 5px;">{safe(company.get('business_name', ''))}</div>
        </div>
    </div>
    """

    # Assemble
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>{UNIFIED_CSS}{CAM_EXTRA_CSS}</style>
    </head>
    <body>
        {header_html}
        {title_html}
        {info_html}
        {summary_html}
        {result_html}
        {table_html}
        {normativa_html}
        {firma_html}
    </body>
    </html>
    """

    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

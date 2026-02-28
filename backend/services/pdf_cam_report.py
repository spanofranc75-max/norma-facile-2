"""
PDF Generator for CAM Multi-Commessa Sustainability Report.
Bilancio di Sostenibilità Ambientale aziendale.
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

from services.pdf_template_v2 import UNIFIED_CSS, safe, fmt_it


REPORT_CSS = """
.report-hero {
    text-align: center;
    padding: 30px 20px;
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8e 100%);
    color: white;
    border-radius: 8px;
    margin-bottom: 25px;
}
.report-hero h1 {
    font-size: 20pt;
    font-weight: 700;
    margin: 0 0 5px 0;
    letter-spacing: 1px;
}
.report-hero .subtitle {
    font-size: 11pt;
    opacity: 0.85;
}
.report-hero .anno {
    font-size: 28pt;
    font-weight: 800;
    margin: 10px 0;
}
.kpi-grid {
    display: table;
    width: 100%;
    margin: 20px 0;
    border-collapse: collapse;
}
.kpi-cell {
    display: table-cell;
    width: 25%;
    padding: 15px 10px;
    text-align: center;
    border: 1px solid #e0e0e0;
    background: #f8f9fa;
}
.kpi-label {
    font-size: 8pt;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}
.kpi-value {
    font-size: 18pt;
    font-weight: 700;
    color: #1e3a5f;
}
.kpi-value.green { color: #28a745; }
.kpi-value.blue { color: #0055ff; }
.co2-box {
    background: #e8f5e9;
    border: 2px solid #4caf50;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin: 20px 0;
}
.co2-title {
    font-size: 10pt;
    color: #2e7d32;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}
.co2-value {
    font-size: 28pt;
    font-weight: 800;
    color: #1b5e20;
}
.co2-unit {
    font-size: 12pt;
    color: #388e3c;
}
.co2-detail {
    font-size: 9pt;
    color: #555;
    margin-top: 8px;
}
.section-title {
    color: #1e3a5f;
    font-size: 13pt;
    font-weight: 700;
    margin: 25px 0 12px 0;
    padding-bottom: 5px;
    border-bottom: 2px solid #1e3a5f;
}
.conf-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 8pt;
    font-weight: 600;
}
.conf-badge.si { background: #d4edda; color: #155724; }
.conf-badge.no { background: #f8d7da; color: #721c24; }
.footer-note {
    margin-top: 30px;
    padding: 12px;
    background: #f8f9fa;
    border-left: 4px solid #1e3a5f;
    font-size: 8pt;
    color: #555;
    line-height: 1.6;
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
    width: 70%;
    margin: 30px auto 5px auto;
}
.firma-label {
    text-align: center;
    font-size: 9pt;
    color: #555;
}
"""


def generate_cam_report_pdf(report: Dict, company: Dict) -> bytes:
    """Generate the multi-commessa CAM sustainability report PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    anno = report.get("anno", datetime.now().year)
    company_name = safe(company.get("business_name", "Azienda"))
    
    # Logo
    logo_html = ""
    logo_url = company.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" style="max-width:100px;max-height:60px;margin-bottom:10px;" /><br/>'

    # Hero section
    hero_html = f"""
    <div class="report-hero">
        {logo_html}
        <h1>BILANCIO DI SOSTENIBILIT&Agrave; AMBIENTALE</h1>
        <div class="subtitle">Criteri Ambientali Minimi — DM 23 giugno 2022 n. 256</div>
        <div class="anno">{anno}</div>
        <div class="subtitle">{safe(company_name)}</div>
    </div>
    """

    # KPI Grid
    peso_totale = report.get("peso_totale_kg", 0)
    peso_riciclato = report.get("peso_riciclato_kg", 0)
    perc_media = report.get("percentuale_riciclato_media", 0)
    n_commesse = report.get("commesse_totali", 0)
    n_conformi = report.get("commesse_conformi", 0)

    kpi_html = f"""
    <div class="kpi-grid">
        <div class="kpi-cell">
            <div class="kpi-label">Acciaio Totale</div>
            <div class="kpi-value">{fmt_it(peso_totale / 1000)} t</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-label">Acciaio Riciclato</div>
            <div class="kpi-value green">{fmt_it(peso_riciclato / 1000)} t</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-label">% Riciclato Media</div>
            <div class="kpi-value blue">{fmt_it(perc_media)}%</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-label">Commesse Conformi</div>
            <div class="kpi-value green">{n_conformi}/{n_commesse}</div>
        </div>
    </div>
    """

    # CO2 Box
    co2 = report.get("co2", {})
    co2_risparmiata = co2.get("co2_risparmiata_t", 0)
    co2_riduzione = co2.get("riduzione_percentuale", 0)
    co2_effettiva = co2.get("co2_effettiva_t", 0)

    co2_html = f"""
    <div class="co2-box">
        <div class="co2-title">CO2 Risparmiata grazie all'acciaio riciclato</div>
        <div class="co2-value">{fmt_it(co2_risparmiata)}</div>
        <div class="co2-unit">tonnellate di CO2 equivalente</div>
        <div class="co2-detail">
            Riduzione del {fmt_it(co2_riduzione)}% rispetto all'uso esclusivo di acciaio primario<br/>
            Emissioni effettive: {fmt_it(co2_effettiva)} tCO2e | Fonte: World Steel Association, 2023
        </div>
    </div>
    """

    # Commesse table
    commesse = report.get("commesse", [])
    comm_rows = ""
    for i, c in enumerate(commesse, 1):
        conf = '<span class="conf-badge si">CONFORME</span>' if c.get("conforme") else '<span class="conf-badge no">NON CONF.</span>'
        comm_rows += f"""
        <tr>
            <td class="tc">{i}</td>
            <td>{safe(c.get('numero', ''))}</td>
            <td>{safe(c.get('titolo', ''))}</td>
            <td>{safe(c.get('cliente', ''))}</td>
            <td class="tr">{fmt_it(c.get('peso_kg', 0))}</td>
            <td class="tr">{fmt_it(c.get('peso_riciclato_kg', 0))}</td>
            <td class="tc">{fmt_it(c.get('percentuale_riciclato', 0))}%</td>
            <td class="tc">{conf}</td>
        </tr>
        """

    comm_html = f"""
    <h2 class="section-title">DETTAGLIO PER COMMESSA</h2>
    <table class="items-table">
        <thead>
            <tr>
                <th class="tc" style="width:4%;">N.</th>
                <th style="width:12%;">Numero</th>
                <th style="width:20%;">Titolo</th>
                <th style="width:15%;">Cliente</th>
                <th class="tr" style="width:12%;">Peso (kg)</th>
                <th class="tr" style="width:12%;">Ric. (kg)</th>
                <th class="tc" style="width:10%;">% Ric.</th>
                <th class="tc" style="width:15%;">Stato</th>
            </tr>
        </thead>
        <tbody>{comm_rows}</tbody>
    </table>
    """

    # Fornitori table
    fornitori = report.get("fornitori", [])
    forn_rows = ""
    for f in fornitori:
        forn_rows += f"""
        <tr>
            <td>{safe(f.get('fornitore', ''))}</td>
            <td class="tr">{fmt_it(f.get('peso_kg', 0))}</td>
            <td class="tr">{fmt_it(f.get('peso_riciclato_kg', 0))}</td>
            <td class="tc">{fmt_it(f.get('percentuale_riciclato', 0))}%</td>
            <td class="tc">{f.get('lotti', 0)}</td>
        </tr>
        """

    forn_html = f"""
    <h2 class="section-title">BREAKDOWN PER FORNITORE</h2>
    <table class="items-table">
        <thead>
            <tr>
                <th style="width:30%;">Fornitore / Acciaieria</th>
                <th class="tr" style="width:18%;">Peso Totale (kg)</th>
                <th class="tr" style="width:18%;">Peso Ric. (kg)</th>
                <th class="tc" style="width:15%;">% Riciclato</th>
                <th class="tc" style="width:12%;">N. Lotti</th>
            </tr>
        </thead>
        <tbody>{forn_rows}</tbody>
    </table>
    """

    # Metodi produttivi breakdown
    metodi = report.get("metodi_produttivi", {})
    metodi_labels = {
        "forno_elettrico_non_legato": "Forno Elettrico (non legato)",
        "forno_elettrico_legato": "Forno Elettrico (legato)",
        "ciclo_integrale": "Ciclo Integrale (altoforno)",
        "sconosciuto": "Non specificato",
    }
    metodi_rows = ""
    for m, data in metodi.items():
        metodi_rows += f"""
        <tr>
            <td>{metodi_labels.get(m, m)}</td>
            <td class="tr">{fmt_it(data.get('peso_kg', 0))}</td>
            <td class="tc">{data.get('lotti', 0)}</td>
        </tr>
        """

    metodi_html = f"""
    <h2 class="section-title">METODI PRODUTTIVI</h2>
    <table class="items-table">
        <thead>
            <tr>
                <th style="width:50%;">Metodo Produttivo</th>
                <th class="tr" style="width:25%;">Peso (kg)</th>
                <th class="tc" style="width:25%;">N. Lotti</th>
            </tr>
        </thead>
        <tbody>{metodi_rows}</tbody>
    </table>
    """

    # Footer note
    footer_html = f"""
    <div class="footer-note">
        <strong>Riferimento normativo:</strong> DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi per l'Edilizia.<br/>
        <strong>Calcolo CO2:</strong> Basato sui fattori di emissione del World Steel Association (2023):
        acciaio da forno elettrico (EAF) = 0,67 tCO2/t; acciaio da ciclo integrale (BOF) = 2,33 tCO2/t.<br/>
        <strong>Data generazione:</strong> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC
    </div>
    <div class="firma-section">
        <div class="firma-cell">
            <div class="firma-label">Luogo e Data</div>
            <div class="firma-line"></div>
        </div>
        <div class="firma-cell">
            <div class="firma-label">Timbro e Firma</div>
            <div class="firma-line"></div>
            <div class="firma-label" style="margin-top:5px;">{safe(company_name)}</div>
        </div>
    </div>
    """

    # Assemble
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>{UNIFIED_CSS}{REPORT_CSS}</style>
    </head>
    <body>
        {hero_html}
        {kpi_html}
        {co2_html}
        {comm_html}
        {forn_html}
        {metodi_html}
        {footer_html}
    </body>
    </html>
    """

    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

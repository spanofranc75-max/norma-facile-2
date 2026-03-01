"""
Green Certificate PDF Generator
Generates a branded sustainability certificate for a single commessa.
Shows CO2 savings, recycled steel %, equivalent trees, and CAM compliance.
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from services.pdf_template_v2 import safe, fmt_it


GREEN_CSS = """
@page {
    size: A4;
    margin: 12mm;
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
.cert-border {
    border: 3px solid #059669;
    border-radius: 12px;
    padding: 30px 35px;
    min-height: 100%;
}
.cert-header {
    text-align: center;
    margin-bottom: 25px;
}
.cert-logo {
    max-width: 100px;
    max-height: 60px;
    margin-bottom: 10px;
}
.cert-title {
    font-size: 22pt;
    font-weight: 700;
    color: #059669;
    letter-spacing: 1px;
    margin: 8px 0 4px 0;
}
.cert-subtitle {
    font-size: 10pt;
    color: #64748b;
    font-style: italic;
}
.company-name-big {
    font-size: 13pt;
    font-weight: 600;
    color: #1e3a5f;
    margin-top: 6px;
}

/* Green separator */
.green-line { border-top: 2px solid #059669; margin: 20px 0; }
.green-line-thin { border-top: 1px solid #d1fae5; margin: 15px 0; }

/* Commessa info */
.commessa-info {
    display: table;
    width: 100%;
    margin-bottom: 20px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 12px 15px;
}
.commessa-info-row {
    display: table-row;
}
.commessa-info-label {
    display: table-cell;
    font-size: 8pt;
    color: #059669;
    font-weight: 600;
    text-transform: uppercase;
    padding: 3px 15px 3px 0;
    width: 30%;
}
.commessa-info-value {
    display: table-cell;
    font-size: 10pt;
    color: #1a1a1a;
    padding: 3px 0;
}

/* KPI Grid */
.kpi-grid {
    display: table;
    width: 100%;
    margin: 20px 0;
    border-collapse: separate;
    border-spacing: 8px;
}
.kpi-row { display: table-row; }
.kpi-cell {
    display: table-cell;
    width: 50%;
    text-align: center;
    padding: 18px 12px;
    border-radius: 8px;
    vertical-align: top;
}
.kpi-co2 {
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    border: 1px solid #a7f3d0;
}
.kpi-trees {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 1px solid #bbf7d0;
}
.kpi-steel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}
.kpi-index {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}
.kpi-label {
    font-size: 8pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 24pt;
    font-weight: 800;
}
.kpi-value-green { color: #059669; }
.kpi-value-dark { color: #1e293b; }
.kpi-unit {
    font-size: 10pt;
    font-weight: 600;
    color: #64748b;
}
.kpi-note {
    font-size: 7pt;
    color: #94a3b8;
    margin-top: 4px;
}

/* Materials table */
.mat-table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 9pt;
}
.mat-table th {
    background: #059669;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    font-size: 8pt;
    text-transform: uppercase;
}
.mat-table th.tr { text-align: right; }
.mat-table th.tc { text-align: center; }
.mat-table td {
    padding: 7px 10px;
    border-bottom: 1px solid #e2e8f0;
}
.mat-table td.tr { text-align: right; font-family: monospace; }
.mat-table td.tc { text-align: center; }
.mat-table tr:nth-child(even) { background: #f8fafc; }
.badge-conforme {
    display: inline-block;
    background: #d1fae5;
    color: #059669;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 600;
}
.badge-non-conforme {
    display: inline-block;
    background: #fee2e2;
    color: #dc2626;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 600;
}

/* Footer */
.cert-footer {
    margin-top: 25px;
    text-align: center;
    font-size: 7pt;
    color: #94a3b8;
    line-height: 1.6;
}
.cert-footer strong { color: #64748b; }
.signature-area {
    margin-top: 30px;
    display: table;
    width: 100%;
}
.sig-cell {
    display: table-cell;
    width: 50%;
    padding: 0 15px;
}
.sig-line {
    border-top: 1px solid #94a3b8;
    margin-top: 40px;
    padding-top: 5px;
    font-size: 8pt;
    color: #64748b;
    text-align: center;
}
"""

KG_CO2_PER_ALBERO = 22.0


def generate_green_certificate(
    company: Dict[str, Any],
    commessa: Dict[str, Any],
    lotti: list,
    co2_data: Dict[str, Any],
) -> BytesIO:
    """Generate a branded Green Certificate PDF for a commessa."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    # Company info
    logo_html = ""
    logo_url = company.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="cert-logo" /><br/>'

    company_name = safe(company.get("business_name", ""))
    company_addr = safe(company.get("address", ""))
    company_city = safe(company.get("city", ""))
    company_piva = safe(company.get("vat_number", ""))

    # Commessa info
    numero = safe(commessa.get("numero", ""))
    titolo = safe(commessa.get("title", ""))
    cliente = safe(commessa.get("client_name", ""))
    cantiere = commessa.get("cantiere", {})
    cantiere_addr = safe(cantiere.get("indirizzo", "")) if cantiere else ""

    # CO2 calculations
    co2_saved_kg = co2_data.get("co2_risparmiata_kg", 0)
    reduction_pct = co2_data.get("riduzione_percentuale", 0)

    # Totals from lotti
    peso_totale = sum(lot.get("peso_kg", 0) for lot in lotti)
    peso_riciclato = sum(lot.get("peso_kg", 0) * lot.get("percentuale_riciclato", 0) / 100 for lot in lotti)
    perc_media = round(peso_riciclato / peso_totale * 100, 1) if peso_totale > 0 else 0
    alberi = round(co2_saved_kg / KG_CO2_PER_ALBERO, 1) if co2_saved_kg > 0 else 0

    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    # Materials rows
    mat_rows = ""
    for lot in lotti:
        peso = lot.get("peso_kg", 0)
        perc = lot.get("percentuale_riciclato", 0)
        conforme = lot.get("conforme_cam", False)
        badge = '<span class="badge-conforme">CONFORME</span>' if conforme else '<span class="badge-non-conforme">NON CONF.</span>'
        mat_rows += f"""
        <tr>
            <td>{safe(l.get('descrizione', ''))}</td>
            <td>{safe(l.get('fornitore', '-'))}</td>
            <td class="tr">{fmt_it(peso)} kg</td>
            <td class="tc">{perc}%</td>
            <td class="tc">{badge}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><style>{GREEN_CSS}</style></head>
<body>
<div class="cert-border">
    <!-- Header -->
    <div class="cert-header">
        {logo_html}
        <div class="cert-title">GREEN CERTIFICATE</div>
        <div class="cert-subtitle">Certificato di Sostenibilita Ambientale</div>
        <div class="company-name-big">{company_name}</div>
    </div>

    <div class="green-line"></div>

    <!-- Commessa Info -->
    <div class="commessa-info">
        <div class="commessa-info-row">
            <div class="commessa-info-label">Commessa</div>
            <div class="commessa-info-value"><strong>{numero}</strong> {f'— {titolo}' if titolo else ''}</div>
        </div>
        <div class="commessa-info-row">
            <div class="commessa-info-label">Cliente</div>
            <div class="commessa-info-value">{cliente}</div>
        </div>
        {f'<div class="commessa-info-row"><div class="commessa-info-label">Cantiere</div><div class="commessa-info-value">{cantiere_addr}</div></div>' if cantiere_addr else ''}
        <div class="commessa-info-row">
            <div class="commessa-info-label">Data Certificato</div>
            <div class="commessa-info-value">{today}</div>
        </div>
    </div>

    <!-- KPI Grid -->
    <div class="kpi-grid">
        <div class="kpi-row">
            <div class="kpi-cell kpi-co2">
                <div class="kpi-label">CO2 Risparmiata</div>
                <div class="kpi-value kpi-value-green">{fmt_it(co2_saved_kg)}</div>
                <div class="kpi-unit">kg CO2e</div>
                <div class="kpi-note">-{fmt_it(reduction_pct)}% vs acciaio primario</div>
            </div>
            <div class="kpi-cell kpi-trees">
                <div class="kpi-label">Effetto Foresta</div>
                <div class="kpi-value kpi-value-green">{fmt_it(alberi)}</div>
                <div class="kpi-unit">alberi equivalenti</div>
                <div class="kpi-note">1 albero = ~22 kg CO2/anno (EEA)</div>
            </div>
        </div>
        <div class="kpi-row">
            <div class="kpi-cell kpi-steel">
                <div class="kpi-label">Acciaio Riciclato</div>
                <div class="kpi-value kpi-value-dark">{fmt_it(peso_riciclato)}</div>
                <div class="kpi-unit">kg su {fmt_it(peso_totale)} kg totali</div>
            </div>
            <div class="kpi-cell kpi-index">
                <div class="kpi-label">Indice Economia Circolare</div>
                <div class="kpi-value kpi-value-dark">{fmt_it(perc_media)}%</div>
                <div class="kpi-unit">contenuto riciclato medio</div>
            </div>
        </div>
    </div>

    <div class="green-line-thin"></div>

    <!-- Materials Detail -->
    <p style="font-size: 9pt; font-weight: 600; color: #1e293b; margin-bottom: 5px;">Dettaglio Materiali Tracciati</p>
    <table class="mat-table">
        <thead>
            <tr>
                <th>Materiale</th>
                <th>Fornitore</th>
                <th class="tr">Peso</th>
                <th class="tc">% Ric.</th>
                <th class="tc">CAM</th>
            </tr>
        </thead>
        <tbody>
            {mat_rows if mat_rows else '<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:15px;">Nessun materiale tracciato</td></tr>'}
        </tbody>
    </table>

    <!-- Signature -->
    <div class="signature-area">
        <div class="sig-cell">
            <div class="sig-line">Timbro e Firma dell\'Azienda</div>
        </div>
        <div class="sig-cell">
            <div class="sig-line">Data: {today}</div>
        </div>
    </div>

    <!-- Footer -->
    <div class="cert-footer">
        <div class="green-line-thin"></div>
        Certificato generato da <strong>{company_name}</strong>
        {f' — {company_addr}, {company_city}' if company_addr else ''}
        {f' — P.IVA {company_piva}' if company_piva else ''}<br/>
        Fattori emissione: <strong>World Steel Association, 2023</strong> — EAF: 0,67 tCO2/t | BOF: 2,33 tCO2/t<br/>
        Conformita ambientale secondo <strong>DM 23 giugno 2022 n. 256</strong> — Criteri Ambientali Minimi
    </div>
</div>
</body></html>"""

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    buf.seek(0)
    return buf

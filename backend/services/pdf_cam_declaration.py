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
    padding: 18px 15px;
    margin: 15px 0;
    text-align: center;
    font-weight: 800;
    border: 3px solid;
    position: relative;
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
.result-box .verdict {
    font-size: 18pt;
    letter-spacing: 2px;
    display: block;
    margin-bottom: 4px;
}
.result-box .verdict-sub {
    font-size: 9pt;
    font-weight: 600;
    opacity: 0.85;
}
.result-box .stamp {
    position: absolute;
    top: -10px;
    right: 15px;
    background: #1e3a5f;
    color: #fff;
    font-size: 7pt;
    font-weight: 700;
    padding: 3px 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
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
@page {
    size: A4;
    margin: 18mm 14mm 22mm 14mm;
    @bottom-left {
        content: "Dichiarazione CAM — DM 23/06/2022";
        font-size: 7pt; color: #999; font-family: Helvetica, Arial, sans-serif;
    }
    @bottom-right {
        content: "Pag. " counter(page) " di " counter(pages);
        font-size: 7pt; color: #777; font-family: Helvetica, Arial, sans-serif;
    }
}
"""


def generate_cam_declaration_pdf(
    calcolo: Dict,
    commessa: Dict,
    company: Dict,
    cliente: Dict = None,
) -> bytes:
    """Generate professional CAM compliance declaration PDF — DM 23/06/2022 for PNRR."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint not available")

    commessa_numero = safe(commessa.get("numero", "N/D"))
    commessa_title = safe(commessa.get("title", ""))
    cliente_nome = safe((cliente or {}).get("business_name", commessa.get("client_name", "")))
    cliente_address = ""
    if cliente:
        cliente_address = f"{safe(cliente.get('address', ''))}<br/>{safe(cliente.get('cap', ''))} {safe(cliente.get('city', ''))}"

    # Company info
    biz = safe(company.get("business_name", ""))
    addr = safe(company.get("address", ""))
    cap_city = safe(f"{company.get('cap', '')} {company.get('city', '')}".strip())
    piva = safe(company.get("partita_iva", company.get("vat_number", "")))
    phone = safe(company.get("phone", company.get("telefono", "")))
    resp = safe(company.get("responsabile_nome", ""))
    ruolo = safe(company.get("ruolo_firmatario", "Legale Rappresentante"))
    logo = company.get("logo_url", "")
    firma = company.get("firma_digitale", "")
    city = safe(company.get("city", ""))

    # Header
    logo_html = f'<img src="{logo}" style="max-height:45px;max-width:180px;margin-right:12px;vertical-align:middle;" />' if logo else ""
    firma_html = f'<img src="{firma}" style="max-height:40px;max-width:150px;" />' if firma else ""

    # Title
    title_html = f"""
    <div class="header-bar">
        <table><tr>
            <td style="width:60%;vertical-align:middle;">
                {logo_html}
                <span style="font-size:13pt;font-weight:800;vertical-align:middle;">{biz}</span>
            </td>
            <td style="width:40%;text-align:right;font-size:8pt;line-height:1.6;">
                {addr}{f"<br/>{cap_city}" if cap_city else ""}
                {f"<br/>P.IVA: {piva}" if piva else ""}
                {f"<br/>Tel: {phone}" if phone else ""}
            </td>
        </tr></table>
    </div>

    <h1 class="doc-title" style="font-size:15pt;margin-top:14px;">
        DICHIARAZIONE DI CONFORMITA CAM
    </h1>
    <p style="text-align:center;font-size:9pt;color:#555;margin-top:-10px;margin-bottom:8px;">
        ai sensi del DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi per l'Edilizia
    </p>
    <div style="text-align:center;margin-bottom:14px;">
        <span style="display:inline-block;background:#f8f4e8;border:2px solid #d4a017;padding:4px 14px;font-size:8.5pt;font-weight:700;color:#8B6914;">
            DOCUMENTAZIONE PNRR — Art. 57, D.Lgs. 36/2023
        </span>
    </div>
    """

    # Commessa/Client info
    info_html = f"""
    <table>
        <tr><td class="lbl" style="width:30%;">Commessa</td><td><strong>{commessa_numero}</strong> — {commessa_title}</td></tr>
        <tr><td class="lbl">Committente</td><td>{cliente_nome}</td></tr>
        {f'<tr><td class="lbl">Indirizzo Committente</td><td>{cliente_address}</td></tr>' if cliente_address else ''}
        <tr><td class="lbl">Data Dichiarazione</td><td>{datetime.now(timezone.utc).strftime('%d/%m/%Y')}</td></tr>
    </table>
    """

    # Summary boxes
    peso_totale = calcolo.get("peso_totale_kg", 0)
    peso_riciclato = calcolo.get("peso_riciclato_kg", 0)
    perc_totale = calcolo.get("percentuale_riciclato_totale", 0)
    soglia = calcolo.get("soglia_minima_richiesta", 0)
    conforme = calcolo.get("conforme_cam", False)

    conf_color = "#276749" if conforme else "#c53030"
    conf_class = "conforme" if conforme else "non-conforme"
    conf_verdict = "CONFORME" if conforme else "NON CONFORME"
    conf_sub = "ai Criteri Ambientali Minimi — DM 23/06/2022" if conforme else "ATTENZIONE — Contenuto riciclato insufficiente"

    summary_html = f"""
    <div class="cam-summary">
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Peso Totale Acciaio</div>
            <div class="cam-summary-value" style="color: #1e3a5f;">{fmt_it(peso_totale)} kg</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Peso Riciclato</div>
            <div class="cam-summary-value" style="color: #1e3a5f;">{fmt_it(peso_riciclato)} kg</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">% Riciclato Ponderata</div>
            <div class="cam-summary-value" style="color:{conf_color};">{fmt_it(perc_totale)}%</div>
        </div>
        <div class="cam-summary-cell">
            <div class="cam-summary-label">Soglia Minima (DM 256)</div>
            <div class="cam-summary-value" style="color: #555;">{fmt_it(soglia)}%</div>
        </div>
    </div>

    <div class="result-box {conf_class}">
        <span class="stamp">ESITO VERIFICA</span>
        <span class="verdict">{conf_verdict}</span>
        <span class="verdict-sub">{conf_sub}</span>
    </div>
    """

    # Materials table — enriched
    righe = calcolo.get("righe", [])
    rows_html = ""
    for i, r in enumerate(righe, 1):
        conf_badge = '<span style="color:#276749;font-weight:700;">SI</span>' if r.get("conforme_cam") else '<span style="color:#c53030;font-weight:700;">NO</span>'
        metodo_label = {
            "forno_elettrico_non_legato": "EAF (non legato)",
            "forno_elettrico_legato": "EAF (legato)",
            "ciclo_integrale": "BOF/BF (integrale)",
            "sconosciuto": "N/D",
        }.get(r.get("metodo_produttivo", ""), r.get("metodo_produttivo", ""))

        cert_label = {
            "epd": "EPD (ISO 14025)",
            "remade_in_italy": "ReMade in Italy",
            "dichiarazione_produttore": "Dich. Produttore",
            "altra_accreditata": "Altra Accreditata",
            "nessuna": "-",
        }.get(r.get("certificazione", ""), r.get("certificazione", ""))

        dist_val = r.get("distanza_trasporto_km")
        dist_str = f"{dist_val:.0f} km" if dist_val else "—"

        rows_html += f"""
        <tr>
            <td class="tc">{i}</td>
            <td>{safe(r.get('descrizione', ''))}</td>
            <td>{safe(r.get('fornitore', ''))}</td>
            <td style="font-family:monospace;font-weight:700;">{safe(r.get('numero_colata', ''))}</td>
            <td class="tr">{fmt_it(r.get('peso_kg', 0))}</td>
            <td class="tc" style="font-weight:700;color:{conf_color};">{fmt_it(r.get('percentuale_riciclato', 0))}%</td>
            <td class="tr">{fmt_it(r.get('peso_riciclato_kg', 0))}</td>
            <td>{metodo_label}</td>
            <td>{cert_label}</td>
            <td class="tc">{dist_str}</td>
            <td class="tc">{fmt_it(r.get('soglia_minima', 0))}%</td>
            <td class="tc">{conf_badge}</td>
        </tr>
        """

    table_html = f"""
    <h3 style="color: #1e3a5f; font-size: 11pt; margin: 20px 0 8px 0;">DETTAGLIO MATERIALI — Dati Estratti da Certificati 3.1 (EN 10204)</h3>
    <table class="items-table">
        <thead>
            <tr>
                <th class="tc" style="width:4%;">N.</th>
                <th style="width:12%;">Materiale</th>
                <th style="width:10%;">Fornitore</th>
                <th style="width:9%;">N. Colata</th>
                <th class="tr" style="width:8%;">Peso</th>
                <th class="tc" style="width:7%;">% Ric.</th>
                <th class="tr" style="width:8%;">Peso Ric.</th>
                <th style="width:11%;">Metodo</th>
                <th style="width:10%;">Certificaz.</th>
                <th class="tc" style="width:7%;">Distanza</th>
                <th class="tc" style="width:6%;">Soglia</th>
                <th class="tc" style="width:6%;">Conf.</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    # Normativa reference (enriched for PNRR — DM 23/06/2022)
    normativa_html = """
    <h3 style="color:#1e3a5f;font-size:11pt;margin:20px 0 8px 0;border-bottom:2px solid #1e3a5f;padding-bottom:4px;">
        QUADRO NORMATIVO DI RIFERIMENTO
    </h3>
    <div class="normativa-ref">
        <strong>DM 23 giugno 2022, n. 256</strong> — <em>Criteri Ambientali Minimi per l'affidamento
        del servizio di progettazione di interventi edilizi, per l'affidamento dei lavori per
        interventi edilizi e per l'affidamento congiunto di progettazione e lavori per
        interventi edilizi.</em><br/><br/>
        <strong>Pubblicazione:</strong> Gazzetta Ufficiale n. 183 del 06/08/2022<br/>
        <strong>Entrata in vigore:</strong> 04/12/2022<br/><br/>
        <strong>Art. 57, D.Lgs. 36/2023 (Codice dei Contratti Pubblici):</strong><br/>
        Obbligo di applicazione al 100% dei CAM negli appalti pubblici, con particolare
        rilevanza per opere finanziate PNRR/PNC.
    </div>
    <div class="normativa-ref" style="border-left-color: #d4a017;">
        <strong>Requisiti specifici acciaio strutturale (Allegato, par. 2.5.4):</strong><br/>
        Contenuto minimo di materia recuperata o riciclata:
        <ul style="margin:4px 0 4px 16px;padding:0;">
            <li><strong>75%</strong> — Acciaio non legato da forno elettrico (EAF)</li>
            <li><strong>60%</strong> — Acciaio legato da forno elettrico (EAF)</li>
            <li><strong>12%</strong> — Acciaio da ciclo integrale (BOF/BF)</li>
        </ul>
        <strong>Mezzi di verifica ammessi:</strong> Certificati di colata EN 10204 3.1,
        EPD (ISO 14025 / EN 15804), certificazione ReMade in Italy,
        dichiarazione del produttore sotto propria responsabilita.
    </div>
    """

    # Signature section
    firma_section = f"""
    <div class="firma-section" style="margin-top:30px;">
        <table style="border:none;width:100%;">
            <tr style="border:none;">
                <td style="border:none;width:50%;vertical-align:bottom;">
                    <p style="font-size:9pt;margin-bottom:4px;"><strong>{resp}</strong></p>
                    <p style="font-size:8pt;color:#555;margin:0;">{ruolo}</p>
                    {firma_html}
                    <div style="border-bottom:1px solid #333;width:220px;margin-top:10px;"></div>
                    <p style="font-size:7.5pt;color:#888;margin-top:2px;">Firma e Timbro</p>
                </td>
                <td style="border:none;width:50%;text-align:right;vertical-align:bottom;">
                    <p style="font-size:9pt;">{city}, {datetime.now(timezone.utc).strftime('%d/%m/%Y')}</p>
                </td>
            </tr>
        </table>
    </div>
    """

    # Assemble
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        {UNIFIED_CSS}
        {CAM_EXTRA_CSS}
        .header-bar {{
            background: #1a3a6b; color: #fff; padding: 10px 14px; margin-bottom: 12px;
        }}
        .header-bar table {{ margin: 0; width: 100%; border-collapse: collapse; }}
        .header-bar td {{ border: none; padding: 2px 6px; color: #fff; }}
        .lbl {{
            font-weight: 700; background: #f0f4f8; width: 30%; color: #1a3a6b; font-size: 8.5pt;
        }}
        table {{ border-collapse: collapse; }}
        td, th {{ border: 1px solid #bbb; }}
        </style>
    </head>
    <body>
        {title_html}
        {info_html}
        {summary_html}
        {table_html}
        {normativa_html}
        {firma_section}
    </body>
    </html>
    """

    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()

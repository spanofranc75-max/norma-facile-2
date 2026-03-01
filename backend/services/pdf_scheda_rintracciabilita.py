"""PDF Generator for Scheda Rintracciabilità Materiali (MOD. 07) — EN 1090."""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

CSS = """
@page {
    size: A4 landscape;
    margin: 10mm 8mm;
}
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 9pt;
    color: #1a1a1a;
    line-height: 1.3;
    margin: 0; padding: 0;
}
.header-bar {
    display: table;
    width: 100%;
    margin-bottom: 6px;
    border-bottom: 2px solid #1e3a5f;
    padding-bottom: 6px;
}
.header-left { display: table-cell; vertical-align: middle; width: 35%; }
.header-center { display: table-cell; vertical-align: middle; width: 30%; text-align: center; }
.header-right { display: table-cell; vertical-align: middle; width: 35%; text-align: right; }
.company-name { font-size: 14pt; font-weight: 700; color: #1e3a5f; }
.company-sub { font-size: 7pt; color: #666; }
.doc-title { font-size: 13pt; font-weight: 700; color: #1e3a5f; text-transform: uppercase; }
.doc-mod { font-size: 7pt; color: #888; }

.info-table { width: 100%; margin-bottom: 8px; border-collapse: collapse; }
.info-table td { padding: 3px 6px; font-size: 9pt; }
.info-label { font-weight: 600; color: #1e3a5f; width: 100px; }
.info-val { border-bottom: 1px solid #ddd; }
.section-title { font-size: 11pt; font-weight: 700; color: #1e3a5f; margin: 6px 0 4px 0; }

table.materials {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
}
table.materials th {
    background: #1e3a5f;
    color: white;
    padding: 5px 4px;
    font-size: 8pt;
    font-weight: 600;
    text-align: center;
    border: 1px solid #1e3a5f;
}
table.materials td {
    padding: 4px;
    font-size: 8.5pt;
    border: 1px solid #ccc;
    text-align: center;
}
table.materials tr:nth-child(even) { background: #f8f9fa; }
table.materials tr:hover { background: #e8f0fe; }
.footer-bar {
    margin-top: 10px;
    padding-top: 4px;
    border-top: 1px solid #ccc;
    font-size: 7pt;
    color: #888;
    text-align: center;
}
"""


def generate_scheda_rintracciabilita_pdf(
    company: Dict[str, Any],
    commessa: Dict[str, Any],
    preventivo: Optional[Dict[str, Any]],
    batches: List[Dict[str, Any]],
    client_name: str = "",
    ordini: List[Dict[str, Any]] = None,
) -> BytesIO:
    """Generate the EN 1090 Materials Traceability Sheet PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint non disponibile")

    biz = company.get("business_name", "")
    piva = company.get("partita_iva", "")
    addr = f"{company.get('address', '')} {company.get('city', '')} {company.get('cap', '')}".strip()
    phone = company.get("phone", "")
    email = company.get("email", "")
    logo = company.get("logo_url", "")
    firma = company.get("firma_digitale", "")

    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "")

    disegno = ""
    ingegnere = ""
    if preventivo:
        disegno = preventivo.get("numero_disegno", "") or ""
        ingegnere = preventivo.get("ingegnere_disegno", "") or ""
        if not classe_exec:
            classe_exec = preventivo.get("classe_esecuzione", "") or ""

    # Build fornitore lookup from OdA
    oda_fornitore_map = {}
    if ordini:
        for oda in ordini:
            fn = oda.get("fornitore_nome", "")
            for riga in oda.get("righe", []):
                desc_lower = (riga.get("descrizione", "") or "").lower()
                oda_fornitore_map[desc_lower] = fn

    # Build rows
    rows_html = ""
    for i, b in enumerate(batches, 1):
        pos = b.get("posizione", "") or str(i)
        n_pezzi = b.get("n_pezzi", "") or ""
        desc = b.get("dimensions", "") or b.get("material_type", "")
        mat_type = b.get("material_type", "")
        n_cert = b.get("numero_certificato", "") or ""
        colata = b.get("heat_number", "")
        # Fornitore: from batch, then try OdA match
        fornitore = b.get("supplier_name", "")
        if not fornitore:
            desc_lower = desc.lower()
            for key, fn in oda_fornitore_map.items():
                if key in desc_lower or desc_lower in key:
                    fornitore = fn
                    break
        ddt = b.get("ddt_numero", "") or ""
        dis = b.get("disegno_numero", "") or disegno
        acciaieria = b.get("acciaieria", "") or ""

        rows_html += f"""
        <tr>
            <td>{dis}</td>
            <td>{pos}</td>
            <td>{n_pezzi}</td>
            <td style="text-align:left; padding-left:6px;">{desc}</td>
            <td>{mat_type}</td>
            <td>{n_cert}</td>
            <td>{colata}</td>
            <td style="text-align:left; padding-left:4px;">{fornitore}</td>
            <td>{ddt}</td>
            <td style="text-align:left; padding-left:4px;">{acciaieria}</td>
        </tr>"""

    if not batches:
        rows_html = '<tr><td colspan="10" style="padding:12px; color:#888;">Nessun materiale tracciato</td></tr>'

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html>
<html><head><style>{CSS}</style></head><body>
<div class="header-bar">
    <div class="header-left">
        <div class="company-name">{biz}</div>
        <div class="company-sub">{addr}</div>
        <div class="company-sub">P.IVA: {piva} | Tel: {phone}</div>
    </div>
    <div class="header-center">
        <div class="doc-title">Scheda Rintracciabilit&agrave; Materiali</div>
        <div class="doc-mod">MOD. 07 — EN 1090</div>
    </div>
    <div class="header-right">
        <div style="font-size:8pt; color:#666;">Data: {now_str}</div>
    </div>
</div>

<table class="info-table">
    <tr>
        <td class="info-label">Cliente:</td>
        <td class="info-val">{client_name}</td>
        <td class="info-label">Commessa:</td>
        <td class="info-val">{comm_num}</td>
    </tr>
    <tr>
        <td class="info-label">Oggetto:</td>
        <td class="info-val">{comm_title}</td>
        <td class="info-label">Classe Esec.:</td>
        <td class="info-val">{classe_exec}</td>
    </tr>
    <tr>
        <td class="info-label">N. Disegno:</td>
        <td class="info-val">{disegno}</td>
        <td class="info-label">Redatto da:</td>
        <td class="info-val">{ingegnere}</td>
    </tr>
</table>

<div class="section-title">{comm_title.upper() if comm_title else 'MATERIALI'}</div>

<table class="materials">
    <thead>
        <tr>
            <th style="width:7%">Disegno N.</th>
            <th style="width:4%">Pos.</th>
            <th style="width:4%">N. Pezzi</th>
            <th style="width:15%">Descrizione</th>
            <th style="width:8%">Tipo Mat.</th>
            <th style="width:8%">N. Certificato</th>
            <th style="width:10%">N. Colata</th>
            <th style="width:14%">Fornitore</th>
            <th style="width:10%">DDT N.</th>
            <th style="width:14%">Acciaieria</th>
        </tr>
    </thead>
    <tbody>
        {rows_html}
    </tbody>
</table>

<div class="footer-bar">
    {biz} | {email} | Documento generato automaticamente da NormaFacile 2.0
</div>
</body></html>"""

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    buf.seek(0)
    return buf

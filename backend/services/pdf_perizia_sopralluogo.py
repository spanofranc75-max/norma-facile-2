"""PDF generation for Sopralluogo & Perizia Messa a Norma."""
import base64
import logging
from io import BytesIO
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available")


PERIZIA_CSS = """
@page {
    size: A4;
    margin: 12mm 12mm 18mm 12mm;
    @bottom-center {
        content: "Pag. " counter(page) " di " counter(pages);
        font-size: 8pt; color: #888;
    }
}
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 9.5pt; color: #1a1a1a; line-height: 1.45; margin: 0; padding: 0;
}
.header { display: table; width: 100%; margin-bottom: 10px; }
.header-left, .header-right { display: table-cell; vertical-align: top; width: 50%; }
.header-right { text-align: right; }
.company-name { color: #1e3a5f; font-size: 14pt; font-weight: 700; }
.company-info { font-size: 8pt; color: #555; }
.doc-title { font-size: 16pt; font-weight: 700; color: #1e3a5f; margin: 12px 0 6px; border-bottom: 3px solid #1e3a5f; padding-bottom: 4px; }
.doc-subtitle { font-size: 10pt; color: #666; margin-bottom: 12px; }
.info-grid { display: table; width: 100%; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 4px; }
.info-row { display: table-row; }
.info-label { display: table-cell; padding: 5px 8px; background: #f5f7fa; font-weight: 600; font-size: 8.5pt; color: #555; width: 28%; border-bottom: 1px solid #eee; }
.info-value { display: table-cell; padding: 5px 8px; font-size: 9pt; border-bottom: 1px solid #eee; }

.section-title { font-size: 12pt; font-weight: 700; color: #1e3a5f; margin: 14px 0 6px; padding-bottom: 3px; border-bottom: 2px solid #e2e8f0; }
.section-subtitle { font-size: 10pt; font-weight: 600; color: #374151; margin: 10px 0 4px; }

.conformity-box { text-align: center; padding: 10px; margin: 10px 0; border: 2px solid; border-radius: 6px; }
.conformity-red { border-color: #dc2626; background: #fef2f2; }
.conformity-amber { border-color: #d97706; background: #fffbeb; }
.conformity-green { border-color: #16a34a; background: #f0fdf4; }
.conformity-pct { font-size: 28pt; font-weight: 800; }
.conformity-pct-red { color: #dc2626; }
.conformity-pct-amber { color: #d97706; }
.conformity-pct-green { color: #16a34a; }

.photos-grid { display: table; width: 100%; }
.photo-row { display: table-row; }
.photo-cell { display: table-cell; width: 50%; padding: 4px; vertical-align: top; }
.photo-wrapper { border: 1px solid #ddd; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }
.photo-img { width: 100%; max-height: 200px; display: block; }
.photo-label { background: #f5f7fa; padding: 3px 6px; font-size: 8pt; font-weight: 600; color: #555; text-transform: uppercase; }

.risk-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9pt; }
.risk-table th { background: #1e3a5f; color: white; padding: 6px 8px; text-align: left; font-size: 8.5pt; }
.risk-table td { padding: 5px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
.risk-table tr:nth-child(even) { background: #f9fafb; }

.badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 7.5pt; font-weight: 700; text-transform: uppercase; }
.badge-alta { background: #fecaca; color: #991b1b; }
.badge-media { background: #fef3c7; color: #92400e; }
.badge-bassa { background: #dbeafe; color: #1e40af; }
.badge-obbl { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
.badge-cons { background: #e0e7ff; color: #3730a3; border: 1px solid #a5b4fc; }

.devices-grid { display: table; width: 100%; margin-bottom: 10px; }
.devices-col { display: table-cell; width: 50%; vertical-align: top; padding-right: 8px; }
.devices-col:last-child { padding-right: 0; padding-left: 8px; }
.device-present { color: #16a34a; font-size: 9pt; margin: 2px 0; }
.device-missing { color: #dc2626; font-size: 9pt; margin: 2px 0; }

.materials-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9pt; }
.materials-table th { background: #78350f; color: white; padding: 5px 8px; text-align: left; font-size: 8.5pt; }
.materials-table td { padding: 4px 8px; border-bottom: 1px solid #e5e7eb; }
.materials-table tr:nth-child(even) { background: #fffbeb; }

.notes-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 4px; padding: 8px 10px; font-size: 9pt; margin: 8px 0; }
.signature-area { margin-top: 30px; display: table; width: 100%; }
.signature-col { display: table-cell; width: 50%; padding: 0 10px; }
.signature-line { border-top: 1px solid #333; margin-top: 50px; padding-top: 4px; font-size: 8.5pt; color: #555; }
.footer-note { font-size: 7.5pt; color: #999; text-align: center; margin-top: 15px; }
"""


def _esc(text):
    """HTML-escape text."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _conformity_class(pct):
    if pct < 40:
        return "red"
    elif pct < 70:
        return "amber"
    return "green"


def generate_perizia_pdf(sopralluogo: dict, company: dict, photos_b64: list = None) -> bytes:
    """Generate a PDF perizia report.
    
    Args:
        sopralluogo: Full sopralluogo document from DB
        company: Company settings
        photos_b64: List of {"base64": str, "mime_type": str, "label": str}
    
    Returns:
        PDF bytes
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint non disponibile")

    analisi = sopralluogo.get("analisi_ai") or {}
    conformita = analisi.get("conformita_percentuale", 0)
    c_class = _conformity_class(conformita)
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    # ── Company Header ──
    company_name = _esc(company.get("company_name", ""))
    company_addr = _esc(f"{company.get('address', '')} - {company.get('cap', '')} {company.get('city', '')} ({company.get('province', '')})")
    company_piva = _esc(company.get("partita_iva", ""))
    company_phone = _esc(company.get("phone", ""))
    company_email = _esc(company.get("email", ""))

    # ── Sopralluogo info ──
    doc_number = _esc(sopralluogo.get("document_number", ""))
    client_name = _esc(sopralluogo.get("client_name", ""))
    indirizzo = _esc(sopralluogo.get("indirizzo", ""))
    comune = _esc(sopralluogo.get("comune", ""))
    provincia = _esc(sopralluogo.get("provincia", ""))
    desc_utente = _esc(sopralluogo.get("descrizione_utente", ""))
    tipo_int = _esc(sopralluogo.get("tipo_intervento", "").replace("_", " ").title())
    created = sopralluogo.get("created_at", "")[:10]

    # ── Photos HTML ──
    photos_html = ""
    if photos_b64:
        rows = []
        for i in range(0, len(photos_b64), 2):
            cells = []
            for j in range(2):
                idx = i + j
                if idx < len(photos_b64):
                    p = photos_b64[idx]
                    mime = p.get("mime_type", "image/jpeg")
                    label = _esc(p.get("label", f"Foto {idx+1}"))
                    cells.append(f"""
                    <div class="photo-cell">
                        <div class="photo-wrapper">
                            <img class="photo-img" src="data:{mime};base64,{p['base64']}" />
                            <div class="photo-label">{label}</div>
                        </div>
                    </div>""")
                else:
                    cells.append('<div class="photo-cell"></div>')
            rows.append(f'<div class="photo-row">{"".join(cells)}</div>')
        photos_html = f"""
        <div class="section-title">Documentazione Fotografica</div>
        <div class="photos-grid">{"".join(rows)}</div>"""

    # ── Risks table ──
    rischi = analisi.get("rischi", [])
    risks_html = ""
    if rischi:
        risk_rows = ""
        for r in rischi:
            g = r.get("gravita", "media")
            risk_rows += f"""
            <tr>
                <td><span class="badge badge-{g}">{_esc(g)}</span></td>
                <td><strong>{_esc(r.get('zona', ''))}</strong></td>
                <td>{_esc(r.get('problema', ''))}</td>
                <td><em>{_esc(r.get('norma_riferimento', ''))}</em></td>
                <td>{_esc(r.get('soluzione', ''))}</td>
            </tr>"""
        risks_html = f"""
        <div class="section-title">Criticità Riscontrate</div>
        <table class="risk-table">
            <tr><th>Gravità</th><th>Zona</th><th>Problema</th><th>Norma</th><th>Soluzione</th></tr>
            {risk_rows}
        </table>"""

    # ── Devices ──
    presenti = analisi.get("dispositivi_presenti", [])
    mancanti = analisi.get("dispositivi_mancanti", [])
    devices_html = ""
    if presenti or mancanti:
        p_items = "".join(f'<div class="device-present">✓ {_esc(d)}</div>' for d in presenti) or '<div style="color:#999;">Nessuno rilevato</div>'
        m_items = "".join(f'<div class="device-missing">✗ {_esc(d)}</div>' for d in mancanti) or '<div style="color:#999;">Nessuno</div>'
        devices_html = f"""
        <div class="section-title">Dispositivi di Sicurezza</div>
        <div class="devices-grid">
            <div class="devices-col">
                <div class="section-subtitle" style="color:#16a34a;">Presenti</div>
                {p_items}
            </div>
            <div class="devices-col">
                <div class="section-subtitle" style="color:#dc2626;">Mancanti / Non Verificabili</div>
                {m_items}
            </div>
        </div>"""

    # ── Materials ──
    materiali = analisi.get("materiali_suggeriti", [])
    materials_html = ""
    if materiali:
        mat_rows = ""
        for m in materiali:
            pri = m.get("priorita", "consigliato")
            badge_cls = "badge-obbl" if pri == "obbligatorio" else "badge-cons"
            desc = _esc(m.get("descrizione_catalogo") or m.get("descrizione", ""))
            prezzo = m.get("prezzo", 0)
            qty = m.get("quantita", 1)
            tot = prezzo * qty
            mat_rows += f"""
            <tr>
                <td>{desc}</td>
                <td style="text-align:center;">{qty}</td>
                <td style="text-align:center;"><span class="badge {badge_cls}">{_esc(pri)}</span></td>
                <td style="text-align:right;">{prezzo:.2f} €</td>
                <td style="text-align:right;"><strong>{tot:.2f} €</strong></td>
            </tr>"""
        total_mat = sum(m.get("prezzo", 0) * m.get("quantita", 1) for m in materiali)
        mat_rows += f'<tr><td colspan="4" style="text-align:right;font-weight:700;">Totale Materiali (IVA escl.)</td><td style="text-align:right;font-weight:700;">{total_mat:.2f} €</td></tr>'
        materials_html = f"""
        <div class="section-title">Materiali e Interventi Suggeriti</div>
        <table class="materials-table">
            <tr><th>Descrizione</th><th style="text-align:center;">Q.tà</th><th style="text-align:center;">Priorità</th><th style="text-align:right;">Prezzo Unit.</th><th style="text-align:right;">Totale</th></tr>
            {mat_rows}
        </table>"""

    # ── Notes ──
    notes_html = ""
    note_tec = analisi.get("note_tecniche", "")
    note_utente = sopralluogo.get("note_tecnico", "")
    if note_tec or note_utente:
        parts = []
        if note_tec:
            parts.append(f"<strong>Analisi AI:</strong> {_esc(note_tec)}")
        if note_utente:
            parts.append(f"<strong>Note Tecnico:</strong> {_esc(note_utente)}")
        notes_html = f'<div class="notes-box">{"<br/>".join(parts)}</div>'

    # ── Full HTML ──
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{PERIZIA_CSS}</style></head>
<body>
    <div class="header">
        <div class="header-left">
            <div class="company-name">{company_name}</div>
            <div class="company-info">{company_addr}<br/>P.IVA: {company_piva}<br/>Tel: {company_phone} | {company_email}</div>
        </div>
        <div class="header-right">
            <div style="font-size:9pt; color:#888;">Documento n.</div>
            <div style="font-size:14pt; font-weight:700; color:#1e3a5f;">{doc_number}</div>
            <div style="font-size:9pt; color:#888; margin-top:4px;">Data: {created}</div>
        </div>
    </div>

    <div class="doc-title">PERIZIA TECNICA — MESSA A NORMA</div>
    <div class="doc-subtitle">Sopralluogo e analisi conformità UNI EN 12453 / EN 13241</div>

    <div class="info-grid">
        <div class="info-row"><div class="info-label">Cliente</div><div class="info-value"><strong>{client_name}</strong></div></div>
        <div class="info-row"><div class="info-label">Indirizzo Sopralluogo</div><div class="info-value">{indirizzo}, {comune} ({provincia})</div></div>
        <div class="info-row"><div class="info-label">Tipo Intervento</div><div class="info-value">{tipo_int}</div></div>
        <div class="info-row"><div class="info-label">Tipo Chiusura</div><div class="info-value"><strong>{_esc(analisi.get('tipo_chiusura', 'Non determinato').replace('_',' ').title())}</strong></div></div>
        <div class="info-row"><div class="info-label">Descrizione</div><div class="info-value">{_esc(analisi.get('descrizione_generale', desc_utente))}</div></div>
    </div>

    <div class="conformity-box conformity-{c_class}">
        <div style="font-size:9pt; font-weight:600; text-transform:uppercase; letter-spacing:1px;">Indice di Conformità</div>
        <div class="conformity-pct conformity-pct-{c_class}">{conformita}%</div>
        <div style="font-size:8.5pt; color:#666;">{"NON CONFORME — Intervento obbligatorio" if conformita < 40 else "PARZIALMENTE CONFORME — Intervento consigliato" if conformita < 70 else "CONFORME — Manutenzione ordinaria"}</div>
    </div>

    {photos_html}
    {risks_html}
    {devices_html}
    {materials_html}
    {notes_html}

    <div class="signature-area">
        <div class="signature-col">
            <div class="signature-line">Il Tecnico</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">Il Cliente (per presa visione)</div>
        </div>
    </div>

    <div class="footer-note">
        Documento generato automaticamente da Norma Facile 2.0 — {now}<br/>
        L'analisi è stata eseguita con supporto di Intelligenza Artificiale e deve essere validata dal tecnico responsabile.
    </div>
</body></html>"""

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes

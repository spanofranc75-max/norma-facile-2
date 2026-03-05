"""PDF Perizia Professionale — Design Ingegneristico Moderno.

Layout:
- COPERTINA: Logo + titolo + foto principale + indice conformità (semaforo)
- SEZIONE 1: Dati sopralluogo
- SEZIONE 2: Documentazione fotografica (griglia 2 colonne con didascalie)
- SEZIONE 3: Schede criticità (box dedicato per ogni rischio con icona + norma)
- SEZIONE 4: Dispositivi sicurezza (presenti vs mancanti)
- SEZIONE 5: Tabella materiali/interventi con prezzi
- SEZIONE 6: Note e firme
"""
import base64
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False

# ── Brand colors ──
NAVY = "#0B1F3A"
BLUE_ACCENT = "#0055FF"
LIGHT_BG = "#F4F6FA"
RED_RISK = "#DC2626"
AMBER_RISK = "#D97706"
GREEN_OK = "#16A34A"


def _esc(t):
    if t is None: return ""
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


CSS = f"""
@page {{
    size: A4;
    margin: 0;
    @bottom-center {{
        content: "";
    }}
}}
@page :first {{
    margin: 0;
}}
@page content {{
    margin: 14mm 14mm 20mm 14mm;
    @bottom-center {{
        content: "Pag. " counter(page) " di " counter(pages);
        font-size: 7.5pt; color: #999;
    }}
    @bottom-left {{
        content: "Norma Facile 2.0 — Perizia Tecnica";
        font-size: 7pt; color: #bbb;
    }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 9pt; color: #1a1a1a; line-height: 1.5; }}

/* ── COVER PAGE ── */
.cover {{ width: 210mm; height: 297mm; position: relative; overflow: hidden; page-break-after: always; }}
.cover-bg {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(160deg, {NAVY} 0%, #162d50 50%, #1e3a5f 100%); }}
.cover-top-bar {{ position: absolute; top: 0; left: 0; width: 100%; height: 6mm; background: {BLUE_ACCENT}; }}
.cover-content {{ position: relative; z-index: 1; padding: 20mm 18mm; color: white; }}
.cover-logo {{ margin-bottom: 6mm; }}
.cover-logo img {{ height: 20mm; }}
.cover-company {{ font-size: 9pt; color: rgba(255,255,255,0.7); margin-bottom: 20mm; }}
.cover-title {{ font-size: 22pt; font-weight: 800; letter-spacing: 0.5px; line-height: 1.2; margin-bottom: 3mm; }}
.cover-subtitle {{ font-size: 11pt; color: rgba(255,255,255,0.8); margin-bottom: 15mm; font-weight: 300; }}
.cover-doc-number {{ font-size: 10pt; color: {BLUE_ACCENT}; font-weight: 700; background: rgba(255,255,255,0.1); display: inline-block; padding: 2mm 4mm; border-radius: 2mm; margin-bottom: 10mm; }}
.cover-info-grid {{ display: table; width: 100%; margin-bottom: 12mm; }}
.cover-info-row {{ display: table-row; }}
.cover-info-label {{ display: table-cell; padding: 2mm 0; color: rgba(255,255,255,0.5); font-size: 8pt; width: 30%; text-transform: uppercase; letter-spacing: 0.5px; }}
.cover-info-value {{ display: table-cell; padding: 2mm 0; color: white; font-size: 10pt; font-weight: 500; }}
.cover-conformity {{ text-align: center; padding: 8mm 0; margin-top: 8mm; border-top: 1px solid rgba(255,255,255,0.15); }}
.cover-conf-label {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.5); margin-bottom: 3mm; }}
.cover-conf-pct {{ font-size: 48pt; font-weight: 900; line-height: 1; }}
.cover-conf-pct-red {{ color: #f87171; }}
.cover-conf-pct-amber {{ color: #fbbf24; }}
.cover-conf-pct-green {{ color: #4ade80; }}
.cover-conf-status {{ font-size: 10pt; margin-top: 2mm; font-weight: 600; }}
.cover-photo {{ position: absolute; bottom: 0; right: 0; width: 55%; height: 45%; overflow: hidden; }}
.cover-photo img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.35; }}
.cover-photo-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to right, {NAVY} 0%, transparent 40%); }}
.cover-footer {{ position: absolute; bottom: 8mm; left: 18mm; z-index: 2; }}
.cover-footer-text {{ font-size: 7pt; color: rgba(255,255,255,0.35); }}

/* ── CONTENT PAGES ── */
.content-page {{ page: content; }}
.section {{ margin-bottom: 8mm; }}
.section-header {{ background: {NAVY}; color: white; padding: 2.5mm 4mm; font-size: 10pt; font-weight: 700; letter-spacing: 0.3px; margin-bottom: 4mm; border-radius: 1.5mm; }}
.section-header-icon {{ display: inline-block; width: 5mm; text-align: center; margin-right: 2mm; }}

/* Info table */
.info-table {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; margin-bottom: 5mm; }}
.info-table td {{ padding: 2.5mm 4mm; font-size: 9pt; border-bottom: 1px solid #f1f5f9; }}
.info-table .label {{ background: {LIGHT_BG}; font-weight: 600; color: #475569; width: 32%; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.3px; }}

/* Photos */
.photos-grid {{ width: 100%; }}
.photos-row {{ display: flex; gap: 3mm; margin-bottom: 3mm; }}
.photo-card {{ flex: 1; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; background: white; }}
.photo-card img {{ width: 100%; height: 48mm; display: block; }}
.photo-card-label {{ padding: 1.5mm 3mm; font-size: 7.5pt; font-weight: 700; color: #475569; background: {LIGHT_BG}; text-transform: uppercase; letter-spacing: 0.5px; border-top: 2px solid {BLUE_ACCENT}; }}

/* Risk cards */
.risk-card {{ border: 1px solid #e2e8f0; border-radius: 2mm; margin-bottom: 4mm; overflow: hidden; page-break-inside: avoid; }}
.risk-card-header {{ display: table; width: 100%; }}
.risk-card-header-left {{ display: table-cell; width: 8mm; vertical-align: middle; text-align: center; color: white; font-size: 14pt; font-weight: 900; }}
.risk-card-header-left-alta {{ background: {RED_RISK}; }}
.risk-card-header-left-media {{ background: {AMBER_RISK}; }}
.risk-card-header-left-bassa {{ background: {BLUE_ACCENT}; }}
.risk-card-header-right {{ display: table-cell; padding: 2.5mm 4mm; }}
.risk-card-zona {{ font-weight: 700; font-size: 10pt; color: #1e293b; }}
.risk-card-norma {{ display: inline-block; background: #f1f5f9; border: 1px solid #e2e8f0; padding: 0.5mm 2mm; border-radius: 1mm; font-size: 7pt; font-weight: 600; color: #64748b; margin-left: 2mm; font-family: 'Courier New', monospace; }}
.risk-card-body {{ padding: 2.5mm 4mm 3mm 4mm; border-top: 1px solid #f1f5f9; }}
.risk-card-body table {{ width: 100%; font-size: 8.5pt; }}
.risk-card-body .rlabel {{ color: #94a3b8; font-weight: 600; width: 18%; padding: 1mm 0; vertical-align: top; }}
.risk-card-body .rvalue {{ padding: 1mm 0; }}
.risk-card-soluzione {{ background: #f0fdf4; border-top: 1px solid #bbf7d0; padding: 2mm 4mm; font-size: 8.5pt; color: #166534; }}
.risk-card-soluzione strong {{ color: #15803d; }}

/* Devices */
.devices-container {{ display: table; width: 100%; }}
.devices-col {{ display: table-cell; width: 50%; vertical-align: top; padding: 3mm; }}
.devices-col-title {{ font-size: 9pt; font-weight: 700; margin-bottom: 2mm; padding-bottom: 1.5mm; border-bottom: 2px solid; }}
.devices-col-title-ok {{ color: {GREEN_OK}; border-color: {GREEN_OK}; }}
.devices-col-title-ko {{ color: {RED_RISK}; border-color: {RED_RISK}; }}
.device-item {{ font-size: 8.5pt; padding: 1mm 0; padding-left: 4mm; }}
.device-ok {{ color: #166534; }}
.device-ko {{ color: #991b1b; font-weight: 500; }}

/* Materials table */
.mat-table {{ width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; }}
.mat-table th {{ background: {NAVY}; color: white; padding: 2.5mm 4mm; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.3px; text-align: left; }}
.mat-table th:nth-child(3), .mat-table th:nth-child(4), .mat-table th:nth-child(5) {{ text-align: right; }}
.mat-table td {{ padding: 2mm 4mm; font-size: 8.5pt; border-bottom: 1px solid #f1f5f9; }}
.mat-table td:nth-child(3), .mat-table td:nth-child(4), .mat-table td:nth-child(5) {{ text-align: right; font-family: 'Courier New', monospace; }}
.mat-table tr:last-child td {{ border-bottom: none; }}
.mat-total {{ background: {LIGHT_BG}; font-weight: 700; }}
.badge-pri {{ display: inline-block; padding: 0.5mm 2mm; border-radius: 1mm; font-size: 7pt; font-weight: 700; text-transform: uppercase; }}
.badge-obbligatorio {{ background: #fee2e2; color: #991b1b; }}
.badge-consigliato {{ background: #dbeafe; color: #1e40af; }}

/* Signature */
.signature-area {{ margin-top: 12mm; display: table; width: 100%; }}
.signature-col {{ display: table-cell; width: 45%; vertical-align: bottom; }}
.signature-col:first-child {{ padding-right: 10%; }}
.signature-label {{ font-size: 8pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16mm; }}
.signature-line {{ border-top: 1px solid {NAVY}; padding-top: 1.5mm; font-size: 8.5pt; font-weight: 600; color: #475569; }}

/* Notes */
.notes-box {{ background: {LIGHT_BG}; border-left: 3px solid {BLUE_ACCENT}; padding: 3mm 4mm; margin: 4mm 0; font-size: 8.5pt; border-radius: 0 1.5mm 1.5mm 0; }}
.notes-box strong {{ color: {NAVY}; }}

/* Disclaimer */
.disclaimer {{ text-align: center; font-size: 7pt; color: #94a3b8; margin-top: 8mm; padding-top: 3mm; border-top: 1px solid #e2e8f0; }}
"""


def generate_perizia_pdf(sopralluogo: dict, company: dict, photos_b64: list = None) -> bytes:
    if not WEASYPRINT_OK:
        raise RuntimeError("WeasyPrint non disponibile")

    analisi = sopralluogo.get("analisi_ai") or {}
    conformita = analisi.get("conformita_percentuale", 0)
    c_cls = "red" if conformita < 40 else "amber" if conformita < 70 else "green"
    c_status = ("NON CONFORME — Intervento obbligatorio" if conformita < 40
                else "PARZIALMENTE CONFORME — Intervento consigliato" if conformita < 70
                else "CONFORME — Manutenzione ordinaria")

    # Company info
    c_name = _esc(company.get("company_name", ""))
    c_addr = _esc(f'{company.get("address","")} — {company.get("cap","")} {company.get("city","")} ({company.get("province","")})')
    c_piva = _esc(company.get("partita_iva", ""))
    c_phone = _esc(company.get("phone", ""))
    c_email = _esc(company.get("email", ""))
    logo_url = company.get("logo_url", "")

    # Sopralluogo info
    doc_num = _esc(sopralluogo.get("document_number", ""))
    client_name = _esc(sopralluogo.get("client_name", ""))
    indirizzo = _esc(sopralluogo.get("indirizzo", ""))
    comune = _esc(sopralluogo.get("comune", ""))
    provincia = _esc(sopralluogo.get("provincia", ""))
    tipo_int = _esc(sopralluogo.get("tipo_intervento", "").replace("_", " ").title())
    tipo_chiusura = _esc(analisi.get("tipo_chiusura", "").replace("_", " ").title())
    desc_gen = _esc(analisi.get("descrizione_generale", sopralluogo.get("descrizione_utente", "")))
    created = sopralluogo.get("created_at", "")[:10]
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    # ═══ COVER PAGE ═══
    logo_html = f'<img src="{logo_url}" />' if logo_url else f'<div style="font-size:16pt;font-weight:900;color:white;">{c_name}</div>'

    cover_photo = ""
    if photos_b64:
        p = photos_b64[0]
        cover_photo = f"""
        <div class="cover-photo">
            <img src="data:{p['mime_type']};base64,{p['base64']}" />
            <div class="cover-photo-overlay"></div>
        </div>"""

    cover = f"""
    <div class="cover">
        <div class="cover-bg"></div>
        <div class="cover-top-bar"></div>
        {cover_photo}
        <div class="cover-content">
            <div class="cover-logo">{logo_html}</div>
            <div class="cover-company">{c_addr} | P.IVA {c_piva}</div>
            <div class="cover-doc-number">{doc_num}</div>
            <div class="cover-title">PERIZIA TECNICA<br/>MESSA A NORMA</div>
            <div class="cover-subtitle">Analisi conformità UNI EN 12453 / EN 13241</div>
            <div class="cover-info-grid">
                <div class="cover-info-row"><div class="cover-info-label">Cliente</div><div class="cover-info-value">{client_name}</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Località</div><div class="cover-info-value">{indirizzo}, {comune} ({provincia})</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Tipo Chiusura</div><div class="cover-info-value">{tipo_chiusura}</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Data Sopralluogo</div><div class="cover-info-value">{created}</div></div>
            </div>
            <div class="cover-conformity">
                <div class="cover-conf-label">Indice di Conformità</div>
                <div class="cover-conf-pct cover-conf-pct-{c_cls}">{conformita}%</div>
                <div class="cover-conf-status" style="color:{'#f87171' if c_cls == 'red' else '#fbbf24' if c_cls == 'amber' else '#4ade80'};">{c_status}</div>
            </div>
        </div>
        <div class="cover-footer"><div class="cover-footer-text">Generato da Norma Facile 2.0 — {now_str}</div></div>
    </div>"""

    # ═══ CONTENT PAGES ═══

    # Photos section
    photos_html = ""
    if photos_b64:
        rows = []
        for i in range(0, len(photos_b64), 2):
            cards = []
            for j in range(2):
                idx = i + j
                if idx < len(photos_b64):
                    p = photos_b64[idx]
                    lbl = _esc(p.get("label", f"Foto {idx+1}")).upper()
                    cards.append(f'<div class="photo-card"><img src="data:{p["mime_type"]};base64,{p["base64"]}" /><div class="photo-card-label">{lbl}</div></div>')
                else:
                    cards.append('<div class="photo-card" style="border:none;"></div>')
            rows.append(f'<div class="photos-row">{"".join(cards)}</div>')
        photos_html = f"""
        <div class="section">
            <div class="section-header"><span class="section-header-icon"></span> DOCUMENTAZIONE FOTOGRAFICA</div>
            {"".join(rows)}
        </div>"""

    # Risks section
    rischi = [r for r in analisi.get("rischi", []) if r.get("confermato", True)]
    risks_html = ""
    if rischi:
        cards = []
        for r in rischi:
            g = r.get("gravita", "media")
            icon = "!" if g == "alta" else "~" if g == "media" else "i"
            cards.append(f"""
            <div class="risk-card">
                <div class="risk-card-header">
                    <div class="risk-card-header-left risk-card-header-left-{g}">{icon}</div>
                    <div class="risk-card-header-right">
                        <span class="risk-card-zona">{_esc(r.get('zona',''))}</span>
                        <span class="risk-card-norma">{_esc(r.get('norma_riferimento',''))}</span>
                    </div>
                </div>
                <div class="risk-card-body">
                    <table>
                        <tr><td class="rlabel">Tipo Rischio</td><td class="rvalue">{_esc(r.get('tipo_rischio','').replace('_',' ').title())}</td></tr>
                        <tr><td class="rlabel">Problema</td><td class="rvalue">{_esc(r.get('problema',''))}</td></tr>
                    </table>
                </div>
                <div class="risk-card-soluzione"><strong>Soluzione:</strong> {_esc(r.get('soluzione',''))}</div>
            </div>""")
        risks_html = f"""
        <div class="section">
            <div class="section-header"><span class="section-header-icon"></span> CRITICITA RISCONTRATE ({len(rischi)})</div>
            {"".join(cards)}
        </div>"""

    # Devices section
    presenti = analisi.get("dispositivi_presenti", [])
    mancanti = analisi.get("dispositivi_mancanti", [])
    devices_html = ""
    if presenti or mancanti:
        p_items = "".join(f'<div class="device-item device-ok">+ {_esc(d)}</div>' for d in presenti) or '<div class="device-item" style="color:#999;">Nessuno rilevato</div>'
        m_items = "".join(f'<div class="device-item device-ko">- {_esc(d)}</div>' for d in mancanti) or '<div class="device-item" style="color:#999;">Nessuno</div>'
        devices_html = f"""
        <div class="section">
            <div class="section-header"><span class="section-header-icon"></span> DISPOSITIVI DI SICUREZZA</div>
            <div class="devices-container">
                <div class="devices-col"><div class="devices-col-title devices-col-title-ok">Presenti</div>{p_items}</div>
                <div class="devices-col"><div class="devices-col-title devices-col-title-ko">Mancanti / Non Verificabili</div>{m_items}</div>
            </div>
        </div>"""

    # Materials section
    materiali = analisi.get("materiali_suggeriti", [])
    materials_html = ""
    if materiali:
        mat_rows = ""
        for m in materiali:
            desc = _esc(m.get("descrizione_catalogo") or m.get("descrizione", ""))
            qty = m.get("quantita", 1)
            prezzo = m.get("prezzo", 0)
            pri = m.get("priorita", "consigliato")
            tot = prezzo * qty
            mat_rows += f"""
            <tr>
                <td>{desc}</td>
                <td><span class="badge-pri badge-{pri}">{_esc(pri)}</span></td>
                <td>{qty}</td>
                <td>{prezzo:.2f} &euro;</td>
                <td><strong>{tot:.2f} &euro;</strong></td>
            </tr>"""
        total_mat = sum(m.get("prezzo", 0) * m.get("quantita", 1) for m in materiali)
        mat_rows += f'<tr class="mat-total"><td colspan="4" style="text-align:right;">TOTALE MATERIALI (IVA escl.)</td><td><strong>{total_mat:.2f} &euro;</strong></td></tr>'
        materials_html = f"""
        <div class="section">
            <div class="section-header"><span class="section-header-icon"></span> MATERIALI E INTERVENTI</div>
            <table class="mat-table">
                <tr><th>Descrizione</th><th>Priorità</th><th>Q.tà</th><th>Prezzo Unit.</th><th>Totale</th></tr>
                {mat_rows}
            </table>
        </div>"""

    # Notes
    notes_html = ""
    note_tec = analisi.get("note_tecniche", "")
    note_utente = sopralluogo.get("note_tecnico", "")
    if note_tec or note_utente:
        parts = []
        if note_tec: parts.append(f"<strong>Note Analisi:</strong> {_esc(note_tec)}")
        if note_utente: parts.append(f"<strong>Note Tecnico:</strong> {_esc(note_utente)}")
        notes_html = f'<div class="notes-box">{"<br/><br/>".join(parts)}</div>'

    # Signatures
    signature_html = f"""
    <div class="signature-area">
        <div class="signature-col">
            <div class="signature-label">Il Tecnico Incaricato</div>
            <div class="signature-line">Data e Firma</div>
        </div>
        <div class="signature-col">
            <div class="signature-label">Il Cliente (per presa visione)</div>
            <div class="signature-line">Data e Firma</div>
        </div>
    </div>"""

    disclaimer = f"""
    <div class="disclaimer">
        Documento generato da Norma Facile 2.0 — {now_str}<br/>
        L'analisi è stata eseguita con supporto di Intelligenza Artificiale e deve essere validata dal tecnico responsabile.<br/>
        Riferimenti normativi: UNI EN 12453, UNI EN 13241, Direttiva Macchine 2006/42/CE
    </div>"""

    # ═══ ASSEMBLE ═══
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
    {cover}
    <div class="content-page">
        {photos_html}
        {risks_html}
        {devices_html}
        {materials_html}
        {notes_html}
        {signature_html}
        {disclaimer}
    </div>
    </body></html>"""

    return HTML(string=html).write_pdf()

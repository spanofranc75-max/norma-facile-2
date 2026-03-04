"""Super Fascicolo Tecnico Unico — Aggregation of all EN 1090 + CAM documents.

Generates a single comprehensive PDF organized as:
  Cap 1: Dati Generali (Dossier Commessa)
  Cap 2: Riesame Tecnico & ITT
  Cap 3: Tracciabilità Materiali & Sostenibilità (CAM + Green Cert + Cert 3.1)
  Cap 4: Processo di Saldatura (PCQ + Registro + VT)
  Cap 5: Marcatura CE (DoP + Etichetta CE)

Operates in READ-ONLY mode — no business logic changes.
"""
from io import BytesIO
from datetime import datetime, timezone
import base64
import logging
from typing import Dict, Any, List, Optional

from pypdf import PdfWriter, PdfReader

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from models.cam import calcola_co2_risparmiata

# ══════════════════════════════════════════════════════════════
# SHARED CSS — coerente con documenti originali
# ══════════════════════════════════════════════════════════════
PAGE_CSS = """
@page {
    size: A4; margin: 14mm 16mm 18mm 16mm;
    @bottom-center {
        content: counter(page);
        font-size: 8pt; color: #777;
    }
}
* { box-sizing: border-box; }
body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111; line-height: 1.45; margin: 0; padding: 0; }
h1 { font-size: 16pt; color: #1a3a6b; margin: 0 0 6px; }
h2 { font-size: 13pt; color: #1a3a6b; margin: 18px 0 6px; border-bottom: 2px solid #1a3a6b; padding-bottom: 3px; }
h3 { font-size: 11pt; color: #333; margin: 12px 0 4px; }
.header-bar { display: table; width: 100%; border-bottom: 2px solid #1a3a6b; padding-bottom: 6px; margin-bottom: 10px; }
.header-logo { display: table-cell; width: 30%; vertical-align: middle; }
.header-title { display: table-cell; width: 40%; text-align: center; vertical-align: middle; font-size: 12pt; font-weight: 700; color: #1a3a6b; }
.header-meta { display: table-cell; width: 30%; text-align: right; vertical-align: middle; font-size: 8pt; color: #555; }
table.info { width: 100%; border-collapse: collapse; margin: 6px 0; }
table.info td { padding: 4px 7px; font-size: 9pt; border: 1px solid #999; }
table.info .lbl { font-weight: 700; background: #f0f4f8; width: 22%; }
table.data { width: 100%; border-collapse: collapse; margin: 6px 0; }
table.data th { background: #1a3a6b; color: #fff; padding: 5px 4px; font-size: 8pt; text-align: center; border: 1px solid #1a3a6b; }
table.data td { padding: 4px 5px; font-size: 8.5pt; border: 1px solid #bbb; }
.chk-yes { color: #000; font-size: 11pt; }
.chk-no { color: #ccc; font-size: 11pt; }
.sign-area { display: table; width: 100%; margin-top: 16px; }
.sign-box { display: table-cell; width: 50%; padding: 8px; vertical-align: top; }
.sign-label { font-size: 9pt; font-weight: 600; margin-bottom: 2px; }
.sign-line { border-bottom: 1px solid #000; height: 30px; margin: 8px 0; }
.note-box { background: #fff8e6; border: 1px solid #e6c84c; border-radius: 4px; padding: 6px 10px; font-size: 8.5pt; margin: 6px 0; }
.page-break { page-break-before: always; }
.footer-doc { font-size: 7.5pt; color: #777; margin-top: 8px; }
"""

LANDSCAPE_CSS = PAGE_CSS.replace("size: A4;", "size: A4 landscape;")


def _s(val):
    """Safe string."""
    if val is None:
        return ""
    return str(val).replace("<", "&lt;").replace(">", "&gt;")


def _chk(val):
    return '<span class="chk-yes">&#9746;</span>' if val else '<span class="chk-no">&#9744;</span>'


def _render(html_str: str, landscape: bool = False) -> bytes:
    css = LANDSCAPE_CSS if landscape else PAGE_CSS
    full = f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{html_str}</body></html>"
    buf = BytesIO()
    HTML(string=full).write_pdf(buf)
    return buf.getvalue()


def _header(logo_url: str, biz: str, comm_num: str, chapter: str) -> str:
    logo_html = f'<img src="{logo_url}" style="max-height:35px;max-width:140px;" />' if logo_url else ""
    return f"""<div class="header-bar">
        <div class="header-logo">{logo_html}<br/><span style="font-size:9pt;font-weight:700;color:#1a3a6b;">{_s(biz)}</span></div>
        <div class="header-title">{chapter}</div>
        <div class="header-meta">Commessa: {_s(comm_num)}</div>
    </div>"""


def _firma_img(firma_b64: str) -> str:
    if firma_b64:
        return f'<img src="{firma_b64}" style="max-height:35px;max-width:120px;" />'
    return ""


# ══════════════════════════════════════════════════════════════
# COVER + INDEX (Template-based professional cover page)
# ══════════════════════════════════════════════════════════════
def _build_cover(ctx: dict) -> bytes:
    """Generate professional cover page from Jinja2-style HTML template."""
    import os
    co = ctx["company"]
    comm = ctx["commessa"]
    now = datetime.now(timezone.utc)

    # Load template
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates", "pdf", "cover_page.html"
    )
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        logger.warning("Cover template not found, using fallback")
        return _build_cover_fallback(ctx)

    # Count content for dynamic index
    n_certificati = len(ctx.get("cert_documents", []))
    n_welders = len(ctx.get("assigned_welders", []))
    has_materials = bool(ctx.get("batches") or ctx.get("cam_lotti"))

    # Simple template rendering (Jinja2-like variable replacement)
    replacements = {
        "{{ logo_url }}": co.get("logo_url", ""),
        "{{ business_name }}": _s(co.get("business_name", "")),
        "{{ exc_class }}": _s(comm.get("classe_esecuzione", "EXC2")),
        "{{ numero_commessa }}": _s(comm.get("numero", "")),
        "{{ cliente }}": _s(ctx.get("client_name", "")),
        "{{ oggetto }}": _s(comm.get("title", "")),
        "{{ certificato_en1090 }}": _s(co.get("certificato_en1090_numero", "")),
        "{{ data_emissione }}": now.strftime("%d/%m/%Y"),
        "{{ generation_datetime }}": now.strftime("%d/%m/%Y alle %H:%M"),
        "{{ partita_iva }}": _s(co.get("partita_iva", "")),
        "{{ responsabile_nome }}": _s(co.get("responsabile_nome", "")),
        "{{ firma_url }}": co.get("firma_base64", ""),
        "{{ n_certificati }}": str(n_certificati),
        "{{ n_welders }}": str(n_welders),
    }
    html = template
    for key, val in replacements.items():
        html = html.replace(key, val)

    # Handle conditional blocks {% if ... %} ... {% endif %}
    def _toggle_block(html_str, condition_name, show):
        """Remove or keep conditional blocks."""
        import re
        pattern = r'\{%\s*if\s+' + re.escape(condition_name) + r'\s*%\}(.*?)\{%\s*endif\s*%\}'
        if show:
            return re.sub(pattern, r'\1', html_str, flags=re.DOTALL)
        else:
            return re.sub(pattern, '', html_str, flags=re.DOTALL)

    html = _toggle_block(html, "logo_url", bool(co.get("logo_url")))
    html = _toggle_block(html, "certificato_en1090", bool(co.get("certificato_en1090_numero")))
    html = _toggle_block(html, "has_materials", has_materials)
    html = _toggle_block(html, "n_certificati > 0", n_certificati > 0)
    html = _toggle_block(html, "n_welders > 0", n_welders > 0)
    html = _toggle_block(html, "firma_url", bool(co.get("firma_base64")))

    # Handle singular/plural in index text
    html = html.replace(
        "{{ 'o' if n_certificati == 1 else 'i' }}",
        "o" if n_certificati == 1 else "i"
    )
    html = html.replace(
        "{{ 'o' if n_welders == 1 else 'i' }}",
        "o" if n_welders == 1 else "i"
    )

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    return buf.getvalue()


def _build_cover_fallback(ctx: dict) -> bytes:
    """Fallback cover page if template is missing."""
    co = ctx["company"]
    comm = ctx["commessa"]
    now = datetime.now(timezone.utc)
    biz = _s(co.get("business_name", ""))
    comm_num = _s(comm.get("numero", ""))
    html = f"""
    <div style="text-align:center; padding-top:100px;">
        <div style="font-size:14pt; color:#555; margin-bottom:10px;">{biz}</div>
        <div style="border-top:3px solid #1a3a6b; width:70%; margin:20px auto;"></div>
        <h1 style="font-size:28pt; font-weight:800; color:#1a3a6b;">FASCICOLO TECNICO</h1>
        <h2 style="font-size:16pt; color:#333; border:none;">Commessa {comm_num}</h2>
        <div style="font-size:11pt; color:#444; margin-top:12px;">{_s(comm.get('title',''))}</div>
        <div style="font-size:10pt; color:#555; margin-top:6px;">Cliente: <strong>{_s(ctx.get('client_name',''))}</strong></div>
    </div>
    <div style="position:fixed; bottom:25px; left:0; right:0; text-align:center; font-size:8pt; color:#999;">
        Generato il {now.strftime('%d/%m/%Y')} — Conforme EN 1090-1:2009+A1:2011
    </div>
    """
    return _render(html)


# ══════════════════════════════════════════════════════════════
# CAP 1: DATI GENERALI (Dossier Commessa)
# ══════════════════════════════════════════════════════════════
def _safe_date(val, fmt: str = "%d/%m/%Y") -> str:
    """Safely convert datetime or string to date string."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime(fmt)
    s = str(val)
    # If ISO format string, extract date part
    if len(s) >= 10 and (s[4] == '-' or s[2] == '/'):
        return s[:10]
    return s


def _build_cap1(ctx: dict) -> bytes:
    co = ctx["company"]
    comm = ctx["commessa"]
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 1 — Dati Generali della Commessa")
    fasi = comm.get("fasi_produzione", [])
    fasi_rows = ""
    for f in fasi:
        stato = f.get("stato", "")
        color = "#059669" if stato in ("completata", "completato") else "#CA8A04" if stato == "in_corso" else "#999"
        data_compl = _safe_date(f.get("completed_at") or f.get("data_completamento") or f.get("data_fine", ""))
        data_inizio = _safe_date(f.get("started_at") or f.get("data_inizio", ""))
        operator = _s(f.get("operator_name", ""))
        fasi_rows += f'<tr><td>{_s(f.get("label","") or f.get("nome",""))}</td><td style="text-align:center;color:{color};font-weight:600;">{_s(stato)}</td><td style="text-align:center;">{data_inizio}</td><td style="text-align:center;">{data_compl}</td><td style="text-align:center;font-size:8pt;">{operator}</td></tr>'

    created_at = _safe_date(comm.get('created_at'))

    html = f"""{hdr}
    <h2>1.1 Dati Commessa</h2>
    <table class="info">
        <tr><td class="lbl">Numero Commessa:</td><td>{_s(comm.get('numero'))}</td><td class="lbl">Data Creazione:</td><td>{created_at}</td></tr>
        <tr><td class="lbl">Descrizione Lavoro:</td><td colspan="3">{_s(comm.get('title'))}</td></tr>
        <tr><td class="lbl">Cliente:</td><td>{_s(ctx.get('client_name'))}</td><td class="lbl">Classe Esecuzione:</td><td>{_s(comm.get('classe_esecuzione','EXC2'))}</td></tr>
        <tr><td class="lbl">Stato:</td><td>{_s(comm.get('stato','in_corso'))}</td><td class="lbl">Tipologia:</td><td>{_s(comm.get('tipologia_chiusura',''))}</td></tr>
    </table>
    <h2>1.2 Dati Fabbricante</h2>
    <table class="info">
        <tr><td class="lbl">Ragione Sociale:</td><td>{_s(co.get('business_name'))}</td></tr>
        <tr><td class="lbl">Sede:</td><td>{_s(co.get('address',''))} {_s(co.get('city',''))} {_s(co.get('cap',''))}</td></tr>
        <tr><td class="lbl">P.IVA:</td><td>{_s(co.get('partita_iva'))}</td></tr>
        <tr><td class="lbl">Certificato EN 1090:</td><td>{_s(co.get('certificato_en1090_numero'))}</td></tr>
        <tr><td class="lbl">Ente Certificatore:</td><td>{_s(co.get('ente_certificatore'))} n. {_s(co.get('ente_certificatore_numero'))}</td></tr>
    </table>
    {"<h2>1.3 Fasi di Produzione</h2><table class='data'><thead><tr><th>Fase</th><th>Stato</th><th>Inizio</th><th>Fine</th><th>Operatore</th></tr></thead><tbody>" + fasi_rows + "</tbody></table>" if fasi_rows else ""}
    """
    return _render(html)


# ══════════════════════════════════════════════════════════════
# CAP 2: RIESAME TECNICO & ITT
# ══════════════════════════════════════════════════════════════
def _build_cap2(ctx: dict) -> bytes:
    from services.pdf_fascicolo_tecnico import DEFAULT_REQUISITI, DEFAULT_ITT
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 2 — Riesame Tecnico & ITT")

    requisiti = ft.get("requisiti", [])
    if not requisiti:
        requisiti = [{"requisito": r["requisito"], "risposta": "si", "note": r["note_default"]} for r in DEFAULT_REQUISITI]
    req_rows = ""
    for r in requisiti:
        risp = r.get("risposta", "")
        req_rows += f'<tr><td style="text-align:left;font-size:8.5pt;">{_s(r.get("requisito",""))}</td><td style="text-align:center;">{_chk(risp=="si")}</td><td style="text-align:center;">{_chk(risp=="no")}</td><td style="text-align:center;">{_chk(risp=="na")}</td><td style="font-size:8pt;">{_s(r.get("note",""))}</td></tr>'

    itt_items = ft.get("itt", [])
    if not itt_items:
        itt_items = [dict(c) for c in DEFAULT_ITT]
    itt_rows = ""
    for item in itt_items:
        itt_rows += f'<tr><td style="text-align:left;">{_s(item.get("caratteristica",""))}</td><td style="font-size:8pt;">{_s(item.get("metodo",""))}</td><td style="text-align:center;">{_s(item.get("esito_conformita",""))}</td><td style="font-size:8pt;">{_s(item.get("criterio",""))}</td></tr>'

    html = f"""{hdr}
    <h2>2.1 Riesame Tecnico (MOD. 01)</h2>
    <table class="info">
        <tr><td class="lbl">Cliente:</td><td>{_s(ctx.get('client_name'))}</td><td class="lbl">Commessa:</td><td>{_s(comm.get('numero'))}</td></tr>
        <tr><td class="lbl">Classe Esecuzione:</td><td>{_s(comm.get('classe_esecuzione','EXC2'))}</td><td class="lbl">Redatto da:</td><td>{_s(ft.get('redatto_da',''))}</td></tr>
    </table>
    <table class="data" style="margin-top:6px;">
        <thead><tr><th style="width:40%;text-align:left;padding-left:4px;">Requisito</th><th style="width:5%">Si</th><th style="width:5%">No</th><th style="width:5%">N.A.</th><th style="width:45%;text-align:left;">Note</th></tr></thead>
        <tbody>{req_rows}</tbody>
    </table>

    <div class="page-break"></div>
    {_header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 2 — ITT di Commessa")}
    <h2>2.2 Ispezioni, Test e Prove (ITT)</h2>
    <table class="data">
        <thead><tr><th style="width:22%;text-align:left;">Caratteristica</th><th style="width:30%;text-align:left;">Metodo</th><th style="width:18%;">Esito</th><th style="width:30%;text-align:left;">Criterio</th></tr></thead>
        <tbody>{itt_rows}</tbody>
    </table>
    """
    return _render(html)


# ══════════════════════════════════════════════════════════════
# CAP 3: MATERIALI & SOSTENIBILITA'
# ══════════════════════════════════════════════════════════════
def _build_cap3_materials(ctx: dict) -> bytes:
    co = ctx["company"]
    comm = ctx["commessa"]
    batches = ctx.get("batches", [])
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 3 — Tracciabilita' Materiali")

    rows = ""
    for i, b in enumerate(batches, 1):
        rows += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_s(b.get('heat_number',''))}</td>
            <td>{_s(b.get('material_type',''))}</td>
            <td>{_s(b.get('dimensions',''))}</td>
            <td>{_s(b.get('supplier_name',''))}</td>
            <td>{_s(b.get('acciaieria',''))}</td>
            <td style="text-align:center;">{'Si' if b.get('has_certificate') or b.get('certificate_base64') else 'No'}</td>
        </tr>"""
    if not batches:
        rows = '<tr><td colspan="7" style="text-align:center;color:#999;padding:8px;">Nessun lotto materiale registrato</td></tr>'

    html = f"""{hdr}
    <h2>3.1 Riepilogo Lotti Materiale</h2>
    <table class="data">
        <thead><tr><th>#</th><th>N. Colata</th><th>Materiale</th><th>Dimensioni</th><th>Fornitore</th><th>Acciaieria</th><th>Cert 3.1</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    return _render(html)


def _build_cap3_cam(ctx: dict) -> bytes:
    """CAM Declaration section."""
    co = ctx["company"]
    comm = ctx["commessa"]
    cam_lotti = ctx.get("cam_lotti", [])
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 3 — Dichiarazione CAM")

    if not cam_lotti:
        html = f"""{hdr}
        <h2>3.2 Dichiarazione di Conformita' CAM</h2>
        <div class="note-box">Nessun dato CAM disponibile per questa commessa. La sezione verra' completata quando i lotti materiale verranno registrati nel modulo CAM.</div>
        """
        return _render(html)

    peso_tot = sum(l.get("peso_kg", 0) for l in cam_lotti)
    peso_ric = sum(l.get("peso_kg", 0) * l.get("percentuale_riciclato", 0) / 100 for l in cam_lotti)
    perc_media = round(peso_ric / peso_tot * 100, 1) if peso_tot > 0 else 0
    conforme = all(l.get("conforme_cam", False) for l in cam_lotti)

    rows = ""
    for l in cam_lotti:
        perc = l.get("percentuale_riciclato", 0)
        nota_stima = ""
        if l.get("tipo_certificazione") == "nessuna" and perc > 0:
            nota_stima = ' <span style="color:#c06000;font-size:7pt;">*stimato</span>'
        conf_txt = '<span style="color:#059669;font-weight:700;">CONFORME</span>' if l.get("conforme_cam") else '<span style="color:#DC2626;font-weight:700;">NON CONFORME</span>'
        rows += f"""<tr>
            <td>{_s(l.get('descrizione',''))}</td>
            <td>{_s(l.get('numero_colata',''))}</td>
            <td style="text-align:right;">{l.get('peso_kg',0):.1f}</td>
            <td style="text-align:center;">{perc:.0f}%{nota_stima}</td>
            <td style="text-align:center;">{_s(l.get('metodo_produttivo',''))}</td>
            <td style="text-align:center;">{conf_txt}</td>
        </tr>"""

    verdict_color = "#059669" if conforme else "#DC2626"
    verdict_text = "CONFORME" if conforme else "NON CONFORME"

    html = f"""{hdr}
    <h2>3.2 Dichiarazione di Conformita' CAM</h2>
    <p style="font-size:9pt;">ai sensi del DM 23 giugno 2022 n. 256 — Criteri Ambientali Minimi per l'edilizia</p>
    <table class="data">
        <thead><tr><th>Materiale</th><th>Colata</th><th>Peso (kg)</th><th>% Riciclato</th><th>Metodo</th><th>Conformita'</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <table class="info" style="margin-top:10px;">
        <tr><td class="lbl">Peso Totale:</td><td>{peso_tot:.1f} kg</td><td class="lbl">% Riciclato Media:</td><td>{perc_media:.1f}%</td></tr>
        <tr><td class="lbl">Esito Complessivo:</td><td colspan="3" style="font-weight:700;font-size:12pt;color:{verdict_color};">{verdict_text}</td></tr>
    </table>
    <div class="note-box">* I valori contrassegnati "stimato" utilizzano dati di letteratura (es. 80% per forno elettrico non legato) in assenza di certificazione specifica del produttore.</div>
    """
    return _render(html)


def _build_cap3_green(ctx: dict) -> bytes:
    """Green Certificate section."""
    co = ctx["company"]
    comm = ctx["commessa"]
    cam_lotti = ctx.get("cam_lotti", [])
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 3 — Green Certificate")

    if not cam_lotti:
        html = f"""{hdr}
        <h2>3.3 Certificato Verde</h2>
        <div class="note-box">Green Certificate non disponibile — nessun dato CAM per questa commessa.</div>"""
        return _render(html)

    peso_tot = sum(l.get("peso_kg", 0) for l in cam_lotti)
    peso_ric = sum(l.get("peso_kg", 0) * l.get("percentuale_riciclato", 0) / 100 for l in cam_lotti)
    co2 = calcola_co2_risparmiata(peso_tot, peso_ric)
    alberi = round(co2["co2_risparmiata_kg"] / 22, 1)

    html = f"""{hdr}
    <h2>3.3 Certificato Verde — Risparmio CO2</h2>
    <div style="text-align:center;margin:20px 0;padding:20px;border:2px solid #059669;border-radius:8px;background:#f0fdf4;">
        <div style="font-size:14pt;font-weight:700;color:#059669;">Risparmio CO2 stimato</div>
        <div style="font-size:28pt;font-weight:800;color:#059669;margin:8px 0;">{co2['co2_risparmiata_kg']:.0f} kg CO2</div>
        <div style="font-size:10pt;color:#555;">Equivalente a <strong>{alberi:.0f} alberi</strong> in un anno</div>
    </div>
    <table class="info">
        <tr><td class="lbl">Peso acciaio totale:</td><td>{peso_tot:.1f} kg</td></tr>
        <tr><td class="lbl">Peso riciclato:</td><td>{peso_ric:.1f} kg</td></tr>
        <tr><td class="lbl">CO2 produzione da riciclo:</td><td>{co2.get('co2_riciclato_kg',0):.1f} kg</td></tr>
        <tr><td class="lbl">CO2 produzione vergine equiv.:</td><td>{co2.get('co2_vergine_kg',0):.1f} kg</td></tr>
        <tr><td class="lbl">CO2 risparmiata:</td><td style="font-weight:700;color:#059669;">{co2['co2_risparmiata_kg']:.1f} kg</td></tr>
    </table>
    <div class="footer-doc">Calcolo basato su fattori di emissione World Steel Association: acciaio da forno elettrico = 0.4 t CO2/t, acciaio da ciclo integrale = 1.8 t CO2/t</div>
    """
    return _render(html)


# ══════════════════════════════════════════════════════════════
# CAP 4: PROCESSO DI SALDATURA
# ══════════════════════════════════════════════════════════════
def _build_cap4_pcq(ctx: dict) -> bytes:
    """Piano di Controllo Qualità — landscape."""
    from services.pdf_fascicolo_tecnico import DEFAULT_PHASES, _co, _header_html, _firma_img_html, BASE_CSS
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    biz, addr, piva, phone, email, logo, firma = _co(co)
    disegno = ft.get("disegno_numero", "")
    ordine_num = ft.get("ordine_numero", comm.get("numero",""))
    redatto_da = ft.get("redatto_da", "")
    classe_exec = comm.get("classe_esecuzione", "EXC2")
    fasi = ft.get("fasi", [])
    if not fasi:
        fasi = [dict(f) for f in DEFAULT_PHASES]

    rows = ""
    for i, f in enumerate(fasi, 1):
        fase = f.get("fase", "")
        doc_rif = f.get("doc_rif", "").replace("{disegno}", disegno)
        applicabile = f.get("applicabile", True)
        bg = 'style="background:#f5f5f5;"' if not applicabile else ''
        esito_html = '<span style="color:#999;">N/A</span>' if not applicabile else f'{_chk(False)} Pos {_chk(False)} Neg'
        periodo = ""
        if f.get("completed_at") or f.get("data_fine"):
            periodo = _safe_date(f.get("completed_at") or f.get("data_fine", ""))
        rows += f'<tr {bg}><td style="text-align:center;">{i}</td><td style="text-align:left;">{fase}</td><td style="font-size:7pt;">{doc_rif}</td><td style="text-align:center;font-size:7pt;">{periodo}</td><td style="text-align:center;"></td><td style="text-align:center;">{esito_html}</td><td style="text-align:center;"></td></tr>'

    header_html = _header_html(biz, addr, piva, phone, email, "Piano di Controllo Qualita'", 'MOD. 02', logo)
    css = BASE_CSS.replace("size: A4;", "size: A4 landscape;").replace("margin: 12mm 15mm;", "margin: 10mm 8mm;")
    full_html = f"""<!DOCTYPE html><html><head><style>{css}</style></head><body>
    {header_html}
    <table class="info-table" style="margin-top:4px;">
        <tr><td class="info-lbl">Cliente:</td><td>{_s(ctx.get('client_name',''))}</td><td class="info-lbl">Commessa N.:</td><td>{_s(comm.get('numero',''))}</td></tr>
        <tr><td class="info-lbl">Descrizione Lavoro:</td><td>{_s(comm.get('title',''))}</td><td class="info-lbl">Ordine N.:</td><td>{ordine_num}</td></tr>
        <tr><td class="info-lbl">Classe Esecuzione:</td><td>{classe_exec}</td><td class="info-lbl">Redatto da:</td><td>{redatto_da}</td></tr>
    </table>
    <table class="main"><thead><tr><th style="width:4%">N.</th><th style="width:22%">Fase</th><th style="width:22%">Documenti Rif.</th><th style="width:10%">Periodo</th><th style="width:10%">Ctrl Verb.</th><th style="width:14%">Esito</th><th style="width:18%">Data/Firma</th></tr></thead><tbody>{rows}</tbody></table>
    <div class="sign-area"><div class="sign-box"><div class="sign-label">Emissione</div>{_firma_img_html(firma)}<div class="sign-line"></div></div><div class="sign-box"><div class="sign-label">Approvazione</div><div class="sign-line"></div></div></div>
    </body></html>"""
    buf = BytesIO()
    HTML(string=full_html).write_pdf(buf)
    return buf.getvalue()


def _build_cap4_registro(ctx: dict) -> bytes:
    """Registro di Saldatura — use existing generator."""
    from services.pdf_fascicolo_tecnico import generate_registro_saldatura_pdf
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    buf = generate_registro_saldatura_pdf(co, comm, ctx.get("client_name",""), ft)
    return buf.getvalue()


def _build_cap4_vt(ctx: dict) -> bytes:
    """Rapporto VT — use existing generator."""
    from services.pdf_fascicolo_tecnico import generate_rapporto_vt_pdf
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    buf = generate_rapporto_vt_pdf(co, comm, ctx.get("client_name",""), ft)
    return buf.getvalue()


def _build_cap4_welder(ctx: dict) -> bytes:
    """Welder qualification summary — lists all welders assigned to this commessa."""
    co = ctx["company"]
    comm = ctx["commessa"]
    assigned_welders = ctx.get("assigned_welders", [])
    hdr = _header(co.get("logo_url",""), co.get("business_name",""), comm.get("numero",""), "Cap. 4 — Patentini Saldatori")

    if not assigned_welders:
        html = f"""{hdr}
        <h2>4.4 Appendice B — Patentini Saldatori</h2>
        <div class="note-box">Nessun saldatore assegnato dalla sezione Registro Saldatura di questa commessa.</div>"""
        return _render(html)

    rows = ""
    for w in assigned_welders:
        quals = w.get("qualifications", [])
        valid_quals = [q for q in quals if q.get("status") == "attivo" or q.get("status") == "in_scadenza"]
        qual_list = ""
        for q in valid_quals:
            exp = _s(q.get("expiry_date", ""))
            st_color = "#059669" if q.get("status") == "attivo" else "#ea580c"
            has_pdf = "PDF allegato" if q.get("has_file") else "Nessun PDF"
            qual_list += f'<div style="font-size:8pt;margin:1px 0;"><span style="color:{st_color};font-weight:700;">&#9679;</span> {_s(q.get("standard",""))} — {_s(q.get("process",""))} (scad. {exp}) — <em style="color:#777;">{has_pdf}</em></div>'
        if not qual_list:
            qual_list = '<span style="color:#999;font-size:8pt;">Nessuna qualifica valida</span>'

        status_label = {"ok": "Valido", "warning": "Attenzione", "expired": "Scaduto", "no_qual": "N/A"}.get(w.get("overall_status"), "")
        status_color = {"ok": "#059669", "warning": "#ea580c", "expired": "#dc2626", "no_qual": "#999"}.get(w.get("overall_status"), "#999")

        rows += f"""<tr>
            <td style="font-weight:700;">{_s(w.get('name',''))}</td>
            <td style="text-align:center;font-family:monospace;">{_s(w.get('stamp_id',''))}</td>
            <td style="text-align:center;"><span style="color:{status_color};font-weight:700;">{status_label}</span></td>
            <td>{qual_list}</td>
        </tr>"""

    n_pdfs = sum(1 for w in assigned_welders for q in w.get("qualifications", []) if q.get("has_file") and q.get("status") in ("attivo", "in_scadenza"))
    note = f'<div class="note-box" style="margin-top:8px;">Le copie dei {n_pdfs} patentini PDF validi sono allegate nelle pagine successive.</div>' if n_pdfs > 0 else ""

    html = f"""{hdr}
    <h2>4.4 Appendice B — Patentini Saldatori</h2>
    <p style="font-size:9pt;color:#555;margin-bottom:6px;">Saldatori assegnati alla commessa {_s(comm.get('numero',''))} con le rispettive qualifiche valide.</p>
    <table class="data">
        <thead><tr><th style="text-align:left;">Saldatore</th><th>Punzone</th><th>Stato</th><th style="text-align:left;">Qualifiche</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    {note}
    """
    return _render(html)


# ══════════════════════════════════════════════════════════════
# CAP 5: MARCATURA CE (DoP + Etichetta)
# ══════════════════════════════════════════════════════════════
def _build_cap5_dop(ctx: dict) -> bytes:
    """DoP — use existing generator."""
    from services.pdf_fascicolo_tecnico import generate_dop_pdf
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    buf = generate_dop_pdf(co, comm, ctx.get("client_name",""), ft)
    return buf.getvalue()


def _build_cap5_ce(ctx: dict) -> bytes:
    """CE Label — use existing generator."""
    from services.pdf_fascicolo_tecnico import generate_ce_pdf
    co = ctx["company"]
    comm = ctx["commessa"]
    ft = ctx.get("ft", {})
    buf = generate_ce_pdf(co, comm, ctx.get("client_name",""), ft)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════
# MERGE ALL — PDF orchestrator
# ══════════════════════════════════════════════════════════════
def _add_pdf(merger: PdfWriter, pdf_bytes: bytes, label: str = ""):
    """Safely add a PDF section to the merger."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            merger.add_page(page)
    except Exception as e:
        logger.warning(f"Failed to add section '{label}': {e}")


def _decode_cert(b64: str) -> bytes:
    """Decode base64 PDF (handles data URI)."""
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)


async def generate_super_fascicolo(commessa_id: str, user_id: str) -> BytesIO:
    """Main entry point — gathers all data and generates the unified PDF."""
    from core.database import db

    # ── 1. Load all data (read-only) ──
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    if not commessa:
        raise ValueError("Commessa non trovata")

    company = await db.company_settings.find_one(
        {"user_id": user_id}, {"_id": 0}
    ) or {}

    # Client name
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one(
            {"client_id": commessa["client_id"]}, {"_id": 0, "business_name": 1, "name": 1}
        )
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")

    # Preventivo (for extra data)
    prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
    if prev_id:
        prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
        if prev:
            if not client_name and prev.get("client_id"):
                cl_p = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1, "name": 1})
                if cl_p:
                    client_name = cl_p.get("business_name") or cl_p.get("name", "")
            if not commessa.get("classe_esecuzione") and prev.get("classe_esecuzione"):
                commessa["classe_esecuzione"] = prev["classe_esecuzione"]
    if not commessa.get("classe_esecuzione") and company.get("classe_esecuzione_default"):
        commessa["classe_esecuzione"] = company["classe_esecuzione_default"]

    # Fascicolo tecnico data
    ft = commessa.get("fascicolo_tecnico", {})
    # Auto-fill some fields
    if not ft.get("redatto_da"):
        ft["redatto_da"] = company.get("responsabile_nome", "")
    if not ft.get("mandatario"):
        ft["mandatario"] = client_name

    # Material batches
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    ).to_list(200)

    # CAM lotti
    cam_lotti = await db.lotti_cam.find(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    ).to_list(200)

    # FPC project (if exists)
    fpc_project = await db.fpc_projects.find_one(
        {"user_id": user_id, "$or": [
            {"preventivo_id": prev_id} if prev_id else {"_never_match_": True},
        ]}, {"_id": 0}
    ) if prev_id else None

    # Welders — find all assigned via Smart Assign in fascicolo_tecnico.saldature
    assigned_welders = []
    saldature = ft.get("saldature", [])
    seen_welder_ids = set()
    for s in saldature:
        wid = s.get("_source_welder_id")
        if wid and wid not in seen_welder_ids:
            seen_welder_ids.add(wid)
    
    # Also check FPC project welder
    if fpc_project and fpc_project.get("fpc_data", {}).get("welder_id"):
        fpc_wid = fpc_project["fpc_data"]["welder_id"]
        if fpc_wid not in seen_welder_ids:
            seen_welder_ids.add(fpc_wid)

    if seen_welder_ids:
        from datetime import date as _date, timedelta
        today_str = _date.today().isoformat()
        threshold_str = (_date.today() + timedelta(days=30)).isoformat()
        for wid in seen_welder_ids:
            w_doc = await db.welders.find_one({"welder_id": wid}, {"_id": 0})
            if not w_doc:
                continue
            quals = w_doc.get("qualifications", [])
            enriched_quals = []
            has_expired = False
            has_expiring = False
            for q in quals:
                exp = q.get("expiry_date", "")
                status = "attivo"
                if exp and exp < today_str:
                    status = "scaduto"
                    has_expired = True
                elif exp and exp <= threshold_str:
                    status = "in_scadenza"
                    has_expiring = True
                enriched_quals.append({
                    "qual_id": q.get("qual_id", ""),
                    "standard": q.get("standard", ""),
                    "process": q.get("process", ""),
                    "expiry_date": exp,
                    "status": status,
                    "has_file": bool(q.get("safe_filename")),
                    "safe_filename": q.get("safe_filename", ""),
                })
            overall = "ok"
            if not quals:
                overall = "no_qual"
            elif has_expired and not any(q["status"] == "attivo" for q in enriched_quals):
                overall = "expired"
            elif has_expired or has_expiring:
                overall = "warning"
            assigned_welders.append({
                "welder_id": wid,
                "name": w_doc.get("name", ""),
                "stamp_id": w_doc.get("stamp_id", ""),
                "overall_status": overall,
                "qualifications": enriched_quals,
            })

    # Conto Lavoro items (for certificates from subcontractors)
    conto_lavoro = commessa.get("conto_lavoro", [])

    # ── Load certificate PDFs from commessa_documents (Repository) ──
    cert_documents = []
    async for doc in db.commessa_documents.find(
        {"commessa_id": commessa_id, "user_id": user_id, "tipo": {"$in": ["certificato_31", "certificato_materiale", "certificato"]}},
        {"_id": 0, "doc_id": 1, "filename": 1, "file_base64": 1, "tipo": 1, "note": 1}
    ):
        if doc.get("file_base64"):
            cert_documents.append(doc)

    # Build context dict
    ctx = {
        "commessa": commessa,
        "company": company,
        "client_name": client_name,
        "ft": ft,
        "batches": batches,
        "cam_lotti": cam_lotti,
        "fpc_project": fpc_project,
        "assigned_welders": assigned_welders,
        "conto_lavoro": conto_lavoro,
        "cert_documents": cert_documents,
    }

    # ── 2. Generate each section ──
    merger = PdfWriter()

    # Cover + Index
    _add_pdf(merger, _build_cover(ctx), "Copertina")

    # Cap 1: Dati Generali
    _add_pdf(merger, _build_cap1(ctx), "Cap 1 - Dati Generali")

    # Cap 2: Riesame & ITT
    _add_pdf(merger, _build_cap2(ctx), "Cap 2 - Riesame & ITT")

    # Cap 3: Materiali & Sostenibilità
    _add_pdf(merger, _build_cap3_materials(ctx), "Cap 3.1 - Materiali")
    _add_pdf(merger, _build_cap3_cam(ctx), "Cap 3.2 - CAM")
    _add_pdf(merger, _build_cap3_green(ctx), "Cap 3.3 - Green Certificate")

    # Appendice A: Certificati 3.1 originali (merge PDF dal Repository Documenti)
    certs_added = 0
    for cert_doc in ctx.get("cert_documents", []):
        cert_b64 = cert_doc.get("file_base64", "")
        if cert_b64:
            try:
                cert_bytes = _decode_cert(cert_b64)
                reader = PdfReader(BytesIO(cert_bytes))
                for page in reader.pages:
                    merger.add_page(page)
                certs_added += 1
            except Exception as e:
                logger.warning(f"Could not merge cert from repo '{cert_doc.get('filename','?')}': {e}")

    # Fallback: merge certificates from material_batches if none found in repo
    if certs_added == 0:
        for b in batches:
            cert_b64 = b.get("certificate_base64")
            if cert_b64:
                try:
                    cert_bytes = _decode_cert(cert_b64)
                    reader = PdfReader(BytesIO(cert_bytes))
                    for page in reader.pages:
                        merger.add_page(page)
                    certs_added += 1
                except Exception as e:
                    logger.warning(f"Could not merge batch cert for {b.get('heat_number','?')}: {e}")

    # Appendice A.2: Certificati Conto Lavoro (rientro subcontractor)
    for cl_item in conto_lavoro:
        cl_cert_b64 = cl_item.get("certificato_rientro_base64")
        if cl_cert_b64:
            try:
                cert_bytes = _decode_cert(cl_cert_b64)
                reader = PdfReader(BytesIO(cert_bytes))
                for page in reader.pages:
                    merger.add_page(page)
            except Exception as e:
                logger.warning(f"Could not merge CL cert for {cl_item.get('tipo','?')}: {e}")

    # Cap 4: Saldatura
    _add_pdf(merger, _build_cap4_pcq(ctx), "Cap 4.1 - PCQ")
    _add_pdf(merger, _build_cap4_registro(ctx), "Cap 4.2 - Registro Saldatura")
    _add_pdf(merger, _build_cap4_vt(ctx), "Cap 4.3 - Rapporto VT")
    _add_pdf(merger, _build_cap4_welder(ctx), "Cap 4.4 - Patentino")

    # Appendice B: Patentini Saldatori PDF originali
    import os
    welder_certs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "welder_certs")
    for w in assigned_welders:
        for q in w.get("qualifications", []):
            if q.get("has_file") and q.get("status") in ("attivo", "in_scadenza") and q.get("safe_filename"):
                cert_path = os.path.join(welder_certs_dir, q["safe_filename"])
                if os.path.isfile(cert_path):
                    try:
                        with open(cert_path, "rb") as f:
                            cert_bytes = f.read()
                        reader = PdfReader(BytesIO(cert_bytes))
                        for page in reader.pages:
                            merger.add_page(page)
                    except Exception as e:
                        logger.warning(f"Could not merge welder cert {q['safe_filename']} for {w.get('name','?')}: {e}")

    # Cap 5: Marcatura CE
    _add_pdf(merger, _build_cap5_dop(ctx), "Cap 5.1 - DoP")
    _add_pdf(merger, _build_cap5_ce(ctx), "Cap 5.2 - Etichetta CE")

    # ── 3. Output ──
    output = BytesIO()
    merger.write(output)
    output.seek(0)
    return output

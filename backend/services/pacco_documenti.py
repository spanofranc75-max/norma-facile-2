"""
Pacco Documenti Cantiere — "Pulsante Magico"

Genera un PDF unificato per l'intera commessa (Cantiere Misto / Matrioska).
Struttura:
  - Copertina + Indice
  - PARTE A: Strutture EN 1090   (se presenti)
  - PARTE B: Cancelli EN 13241   (se presenti)
  - PARTE C: Lavorazioni Generiche (se presenti)

Ogni parte include: dati voce, documenti/foto pertinenti, verbale collaudo
(auto-compilato da checklist officina), riepilogo ore.

Regole:
  - Filtro Beltrami: pesca solo documenti legati alla voce (via metadata_estratti.voce_id)
  - Automazione: checklist tutti OK → verbale "CONFORME" (firmato tecnicamente)
  - Minimalismo: non genera parti per categorie non presenti
  - Ordine: A (1090) → B (13241) → C (Generiche)
"""
import logging
import base64
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Dict, Any
import html as html_mod

from pypdf import PdfWriter

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available")


# ══════════════════════════════════════════════════════════════
#  CSS — Stile professionale coerente col progetto
# ══════════════════════════════════════════════════════════════

PACCO_CSS = """
@page {
    size: A4;
    margin: 15mm 16mm 20mm 16mm;
    @bottom-left  { content: "Pacco Documenti Cantiere"; font-size: 7.5pt; color: #999; }
    @bottom-right { content: "Pag. " counter(page); font-size: 7.5pt; color: #777; }
}
* { box-sizing: border-box; }
body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111; line-height: 1.45; margin: 0; padding: 0; }
h1 { font-size: 18pt; color: #1a3a6b; margin: 0 0 8px; }
h2 { font-size: 14pt; color: #1a3a6b; margin: 24px 0 6px; border-bottom: 2.5px solid #1a3a6b; padding-bottom: 4px; }
h3 { font-size: 11pt; color: #333; margin: 14px 0 4px; }
h4 { font-size: 10pt; color: #555; margin: 10px 0 3px; }
.page-break { page-break-before: always; }
table.info { width: 100%; border-collapse: collapse; margin: 6px 0; }
table.info td { padding: 4px 7px; font-size: 9pt; border: 1px solid #bbb; }
table.info .lbl { font-weight: 700; background: #f0f4f8; width: 28%; }
table.data { width: 100%; border-collapse: collapse; margin: 8px 0; }
table.data th { background: #1a3a6b; color: #fff; padding: 5px 6px; font-size: 8.5pt; text-align: left; border: 1px solid #1a3a6b; }
table.data td { padding: 4px 6px; font-size: 9pt; border: 1px solid #bbb; }
table.data tr:nth-child(even) { background: #f8f9fb; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 8pt; font-weight: 700; }
.badge-ok { background: #d1fae5; color: #065f46; }
.badge-nok { background: #fee2e2; color: #991b1b; }
.badge-na { background: #f1f5f9; color: #64748b; }
.badge-1090 { background: #dbeafe; color: #1e40af; }
.badge-13241 { background: #fef3c7; color: #92400e; }
.badge-gen { background: #f1f5f9; color: #475569; }
.sign-area { display: table; width: 100%; margin-top: 18px; }
.sign-box { display: table-cell; width: 50%; padding: 8px; vertical-align: top; }
.sign-label { font-size: 9pt; font-weight: 600; margin-bottom: 2px; }
.sign-line { border-bottom: 1px solid #000; height: 35px; margin: 10px 0 2px; }
.sign-disclaimer { font-size: 7.5pt; color: #888; font-style: italic; margin-top: 3px; }
.photo-grid { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
.photo-grid img { max-width: 180px; max-height: 140px; border: 1px solid #ccc; border-radius: 3px; object-fit: cover; }
.note { background: #fffbeb; border: 1px solid #fbbf24; border-radius: 4px; padding: 6px 10px; font-size: 8.5pt; margin: 6px 0; }
.cover-center { text-align: center; padding-top: 60px; }
.cover-numero { font-size: 28pt; color: #1a3a6b; font-weight: 800; margin: 8px 0; }
.cover-title { font-size: 14pt; color: #444; margin: 4px 0; }
.cover-meta { font-size: 10pt; color: #666; margin: 3px 0; }
.indice { margin: 20px 0; }
.indice li { font-size: 10pt; margin: 4px 0; }
.indice li .parte { font-weight: 700; color: #1a3a6b; }
"""

_esc = html_mod.escape


def _s(val):
    if val is None:
        return ""
    return _esc(str(val))


def _render_pdf(html_body: str) -> bytes:
    full = f"<!DOCTYPE html><html><head><style>{PACCO_CSS}</style></head><body>{html_body}</body></html>"
    buf = BytesIO()
    HTML(string=full).write_pdf(buf)
    return buf.getvalue()


def _fmt_ore(minutes_or_hours, is_minutes=False):
    if is_minutes:
        h = round(minutes_or_hours / 60, 1)
    else:
        h = round(float(minutes_or_hours or 0), 1)
    return f"{h}h"


def _foto_html(docs: List[Dict], max_photos: int = 12) -> str:
    """Render photo thumbnails from base64-encoded documents."""
    photos = [d for d in docs if d.get("content_type", "").startswith("image/")][:max_photos]
    if not photos:
        return "<p style='font-size:9pt;color:#888;font-style:italic;'>Nessuna foto disponibile.</p>"
    html = '<div class="photo-grid">'
    for p in photos:
        b64 = p.get("file_base64", "")
        ct = p.get("content_type", "image/jpeg")
        nome = _s(p.get("nome_file", ""))
        if b64:
            src = f"data:{ct};base64,{b64}"
            html += f'<img src="{src}" title="{nome}" />'
    html += '</div>'
    return html


# ══════════════════════════════════════════════════════════════
#  COVER + INDEX
# ══════════════════════════════════════════════════════════════

def _build_cover(commessa: dict, company: dict, client_name: str, parti: list) -> str:
    biz = _s(company.get("business_name", ""))
    logo_url = company.get("logo_url", "")
    logo_html = f'<img src="{logo_url}" style="max-height:50px;max-width:200px;margin-bottom:8px;" />' if logo_url else ""
    numero = _s(commessa.get("numero", ""))
    title = _s(commessa.get("title", commessa.get("oggetto", "")))
    now = datetime.now(timezone.utc)

    indice_items = ""
    for p in parti:
        indice_items += f'<li><span class="parte">{_s(p["lettera"])}. {_s(p["titolo"])}</span> — {_s(p["subtitle"])}</li>'

    return f"""
    <div class="cover-center">
        {logo_html}
        <div style="font-size:12pt;color:#555;margin-bottom:6px;">{biz}</div>
        <div style="border-top:3px solid #1a3a6b;width:70%;margin:12px auto;"></div>
        <h1 style="font-size:24pt;margin:10px 0;">PACCO DOCUMENTI CANTIERE</h1>
        <div class="cover-numero">{numero}</div>
        <div class="cover-title">{title}</div>
        <div class="cover-meta">Cliente: {_s(client_name)}</div>
        <div class="cover-meta">Data emissione: {now.strftime('%d/%m/%Y')}</div>
    </div>
    <div style="margin-top:40px;">
        <h2 style="text-align:center;border-bottom:none;">INDICE</h2>
        <ol class="indice">{indice_items}</ol>
    </div>
    """


# ══════════════════════════════════════════════════════════════
#  PARTE A — STRUTTURE EN 1090
# ══════════════════════════════════════════════════════════════

def _build_parte_a(voci_1090: list, data: dict) -> str:
    """Build Part A: EN 1090 structural documents."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-1090">EN 1090</span> PARTE A: STRUTTURE</h2>'

    for i, voce in enumerate(voci_1090):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Lavorazione strutturale"))
        exc = _s(voce.get("classe_exc", "EXC2"))

        if i > 0:
            html += '<div class="page-break"></div>'

        html += f'<h3>A.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>EN 1090 — Strutture in acciaio</td></tr>
            <tr><td class="lbl">Classe di Esecuzione</td><td>{exc}</td></tr>
        </table>
        """

        # A.x.1 — Certificati Materiali 3.1
        cert_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("tipo") == "certificato_31"]
        html += f'<h4>A.{i + 1}.1 — Certificati Materiali 3.1 ({len(cert_docs)} doc.)</h4>'
        if cert_docs:
            html += '<table class="data"><tr><th>Nome File</th><th>N. Colata</th><th>Caricato</th></tr>'
            for d in cert_docs:
                colata = _s((d.get("metadata_estratti") or {}).get("numero_colata", "—"))
                nome = _s(d.get("nome_file", ""))
                data_up = _s(d.get("uploaded_at", "")[:10])
                html += f'<tr><td>{nome}</td><td>{colata}</td><td>{data_up}</td></tr>'
            html += '</table>'
        else:
            html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessun certificato 3.1 caricato per questa voce.</p>'

        # A.x.2 — Foto Lavorazione
        foto_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("content_type", "").startswith("image/")]
        html += f'<h4>A.{i + 1}.2 — Foto Lavorazione ({len(foto_docs)})</h4>'
        html += _foto_html(foto_docs)

        # A.x.3 — Verbale Collaudo Qualità
        html += f'<h4>A.{i + 1}.3 — Verbale Collaudo Qualita\'</h4>'
        html += _build_verbale(vid, data, "EN_1090")

        # A.x.4 — Riepilogo Ore
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>A.{i + 1}.4 — Riepilogo Ore Lavorate</h4>'
        html += _build_riepilogo_ore(ore_entries)

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE B — CANCELLI EN 13241
# ══════════════════════════════════════════════════════════════

def _build_parte_b(voci_13241: list, data: dict) -> str:
    """Build Part B: EN 13241 gate documents."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-13241">EN 13241</span> PARTE B: SICUREZZA CANCELLI</h2>'

    for i, voce in enumerate(voci_13241):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Cancello"))
        tipo_ch = _s(voce.get("tipologia_chiusura", ""))

        if i > 0:
            html += '<div class="page-break"></div>'

        html += f'<h3>B.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>EN 13241 — Chiusure industriali</td></tr>
            {"<tr><td class='lbl'>Tipologia</td><td>" + tipo_ch + "</td></tr>" if tipo_ch else ""}
        </table>
        """

        # B.x.1 — Foto Kit Sicurezza
        foto_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("content_type", "").startswith("image/")]
        html += f'<h4>B.{i + 1}.1 — Foto Kit Sicurezza ({len(foto_docs)})</h4>'
        html += _foto_html(foto_docs)

        # B.x.2 — Verbale Collaudo
        html += f'<h4>B.{i + 1}.2 — Verbale Collaudo</h4>'
        html += _build_verbale(vid, data, "EN_13241")

        # B.x.3 — Riepilogo Ore
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>B.{i + 1}.3 — Riepilogo Ore Lavorate</h4>'
        html += _build_riepilogo_ore(ore_entries)

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE C — LAVORAZIONI GENERICHE
# ══════════════════════════════════════════════════════════════

def _build_parte_c(voci_gen: list, data: dict) -> str:
    """Build Part C: Generic work summary."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-gen">GENERICA</span> PARTE C: RIEPILOGO LAVORAZIONI</h2>'

    for i, voce in enumerate(voci_gen):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Lavorazione generica"))

        html += f'<h3>C.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>Nessuna marcatura CE</td></tr>
        </table>
        """

        # C.x.1 — Riepilogo Ore e Materiali
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>C.{i + 1}.1 — Riepilogo Ore e Materiali</h4>'
        html += _build_riepilogo_ore(ore_entries)

    return html


# ══════════════════════════════════════════════════════════════
#  VERBALE COLLAUDO (auto-compilato da checklist officina)
# ══════════════════════════════════════════════════════════════

def _build_verbale(voce_id: str, data: dict, normativa: str) -> str:
    """Build the inspection report, auto-populated from officina checklists."""
    checklists = [c for c in data.get("checklists", [])
                  if c.get("voce_id", "") == voce_id or
                  (voce_id == "__principale__" and not c.get("voce_id"))]

    if not checklists:
        return '<p style="font-size:9pt;color:#888;font-style:italic;">Nessun controllo qualita\' eseguito per questa voce.</p>'

    # Use the latest checklist
    latest = sorted(checklists, key=lambda c: c.get("submitted_at", ""), reverse=True)[0]
    all_ok = latest.get("all_ok", False)
    op_nome = _s(latest.get("operatore_nome", ""))
    data_check = latest.get("submitted_at", "")[:10]

    esito_badge = '<span class="badge badge-ok">CONFORME</span>' if all_ok else '<span class="badge badge-nok">NON CONFORME</span>'

    html = f"""
    <table class="info">
        <tr><td class="lbl">Data Controllo</td><td>{_s(data_check)}</td></tr>
        <tr><td class="lbl">Eseguito da</td><td>{op_nome}</td></tr>
        <tr><td class="lbl">Esito Generale</td><td>{esito_badge}</td></tr>
    </table>
    <table class="data">
        <tr><th>Controllo</th><th>Esito</th></tr>
    """
    for item in latest.get("items", []):
        codice = _s(item.get("codice", "")).replace("_", " ").title()
        esito = item.get("esito", False)
        badge = '<span class="badge badge-ok">OK</span>' if esito else '<span class="badge badge-nok">NOK</span>'
        html += f'<tr><td>{codice}</td><td>{badge}</td></tr>'
    html += '</table>'

    if not all_ok:
        html += '<div class="note">ATTENZIONE: Uno o piu\' controlli NON superati. Verificare le azioni correttive.</div>'

    # Firma tecnica
    html += _build_firma(data.get("company", {}))

    return html


# ══════════════════════════════════════════════════════════════
#  FIRMA TECNICA
# ══════════════════════════════════════════════════════════════

def _build_firma(company: dict) -> str:
    resp = _s(company.get("responsabile_nome", ""))
    firma_b64 = company.get("firma_base64", "")
    firma_img = f'<img src="{firma_b64}" style="max-height:35px;max-width:120px;" />' if firma_b64 else ""

    return f"""
    <div class="sign-area">
        <div class="sign-box">
            <div class="sign-label">Responsabile Qualita'</div>
            <div>{_s(resp)}</div>
            {firma_img}
            <div class="sign-line"></div>
            <div class="sign-disclaimer">Documentazione generata automaticamente dal sistema di controllo produzione.</div>
        </div>
        <div class="sign-box">
            <div class="sign-label">Firma Digitale / Manuale</div>
            <div class="sign-line"></div>
            <div class="sign-disclaimer">Data: ________________</div>
        </div>
    </div>
    """


# ══════════════════════════════════════════════════════════════
#  RIEPILOGO ORE
# ══════════════════════════════════════════════════════════════

def _build_riepilogo_ore(entries: list) -> str:
    if not entries:
        return '<p style="font-size:9pt;color:#888;font-style:italic;">Nessuna sessione di lavoro registrata.</p>'

    totale_ore = sum(e.get("ore_totali", e.get("ore", 0)) for e in entries)
    # Group by operator
    op_map = {}
    for e in entries:
        for op in e.get("operatori", []):
            nome = op.get("nome", "Anonimo")
            op_map[nome] = op_map.get(nome, 0) + e.get("ore", 0)

    html = '<table class="data"><tr><th>Operatore</th><th>Ore</th></tr>'
    for nome, ore in sorted(op_map.items()):
        html += f'<tr><td>{_s(nome)}</td><td>{_fmt_ore(ore)}</td></tr>'
    html += f'<tr style="font-weight:700;background:#e2e8f0;"><td>TOTALE ORE PERSONA</td><td>{_fmt_ore(totale_ore)}</td></tr>'
    html += '</table>'
    return html


# ══════════════════════════════════════════════════════════════
#  MATCHING HELPERS — Filtro Beltrami
# ══════════════════════════════════════════════════════════════

def _doc_matches_voce(doc: dict, voce_id: str) -> bool:
    """Check if a document belongs to a specific voce di lavoro."""
    meta = doc.get("metadata_estratti") or {}
    doc_voce = meta.get("voce_id", "")
    # If doc has a specific voce_id, match it
    if doc_voce:
        return doc_voce == voce_id
    # If doc has no voce_id, it belongs to the principal voce
    if voce_id == "__principale__":
        return True
    # Untagged docs don't match specific voci
    return False


def _diario_matches_voce(entry: dict, voce_id: str) -> bool:
    """Check if a diary entry belongs to a specific voce."""
    entry_voce = entry.get("voce_id", "")
    if entry_voce:
        return entry_voce == voce_id
    if voce_id == "__principale__":
        return True
    return False


# ══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ══════════════════════════════════════════════════════════════

async def generate_pacco_documenti(commessa_id: str, user_id: str) -> BytesIO:
    """
    Main entry point — Genera il Pacco Documenti Cantiere.
    Returns a BytesIO PDF buffer.
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint non disponibile")

    from core.database import db

    # ── 1. RACCOLTA DATI ──

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
            {"client_id": commessa["client_id"]},
            {"_id": 0, "business_name": 1, "name": 1}
        )
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")

    # Voci di Lavoro
    voci = await db.voci_lavoro.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).sort("ordine", 1).to_list(50)

    # Build effective voce list (principal + children)
    all_voci = []
    norm_principale = commessa.get("normativa_tipo", "GENERICA")
    all_voci.append({
        "voce_id": "__principale__",
        "descrizione": commessa.get("title") or commessa.get("oggetto") or f"Commessa {commessa.get('numero', '')}",
        "normativa_tipo": norm_principale,
        "classe_exc": commessa.get("classe_esecuzione", "EXC2"),
        "tipologia_chiusura": commessa.get("tipologia_chiusura", ""),
    })
    for v in voci:
        all_voci.append(v)

    # Split by category
    voci_1090 = [v for v in all_voci if v.get("normativa_tipo") == "EN_1090"]
    voci_13241 = [v for v in all_voci if v.get("normativa_tipo") == "EN_13241"]
    voci_gen = [v for v in all_voci if v.get("normativa_tipo") == "GENERICA"]

    # Documents (with base64 for photos)
    docs = await db.commessa_documents.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(500)

    # Diario produzione
    diario = await db.diario_produzione.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(500)

    # Officina checklists
    checklists = await db.officina_checklist.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(100)

    # Shared data context
    ctx = {
        "docs": docs,
        "diario": diario,
        "checklists": checklists,
        "company": company,
    }

    # ── 2. BUILD INDEX (which parts to include) ──

    parti = []
    if voci_1090:
        parti.append({
            "lettera": "A",
            "titolo": "STRUTTURE (EN 1090)",
            "subtitle": f"{len(voci_1090)} voce/i strutturale/i",
        })
    if voci_13241:
        parti.append({
            "lettera": "B",
            "titolo": "SICUREZZA CANCELLI (EN 13241)",
            "subtitle": f"{len(voci_13241)} voce/i cancello",
        })
    if voci_gen:
        parti.append({
            "lettera": "C",
            "titolo": "LAVORAZIONI GENERICHE",
            "subtitle": f"{len(voci_gen)} voce/i generica/e",
        })

    # ── 3. GENERATE HTML ──

    html_body = _build_cover(commessa, company, client_name, parti)

    if voci_1090:
        html_body += _build_parte_a(voci_1090, ctx)
    if voci_13241:
        html_body += _build_parte_b(voci_13241, ctx)
    if voci_gen:
        html_body += _build_parte_c(voci_gen, ctx)

    # ── 4. RENDER PDF ──

    pdf_bytes = _render_pdf(html_body)

    logger.info(
        f"[PACCO] Generato per commessa {commessa.get('numero', commessa_id)}: "
        f"A={len(voci_1090)} B={len(voci_13241)} C={len(voci_gen)} "
        f"docs={len(docs)} diario={len(diario)} checklists={len(checklists)} "
        f"size={len(pdf_bytes)} bytes"
    )

    buf = BytesIO(pdf_bytes)
    buf.seek(0)
    return buf

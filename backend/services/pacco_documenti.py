"""
Pacco Documenti Cantiere — "Pulsante Magico"

Genera un PDF unificato per l'intera commessa (Cantiere Misto / Matrioska).
Struttura:
  - Copertina + Indice
  - CAP. 1: Strutture EN 1090   (se presenti) — DoP, Certificati 3.1, WPS, Foto
  - CAP. 2: Cancelli EN 13241   (se presenti) — Dichiarazione Conformità, Foto Sicurezze, Manuale
  - CAP. 3: Relazione Tecnica                  — Riepilogo ore e materiali

Regole:
  - Filtro Beltrami: pesca solo documenti/pagine legati alla voce (via metadata + doc_page_index)
  - Automazione: checklist tutti OK → ESITO POSITIVO / con NOK → ESITO NEGATIVO
  - Consumabili: filo ≥1.0mm → EN 1090, <1.0mm → EN 13241, gas → EN 1090
  - Minimalismo: non genera capitoli per categorie non presenti
  - Ordine: CAP. 1 (1090) → CAP. 2 (13241) → CAP. 3 (Relazione Tecnica)
"""
import logging
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Dict
import html as html_mod


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
    """Build CAP. 1: EN 1090 structural documents."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-1090">EN 1090</span> CAP. 1: STRUTTURE</h2>'

    for i, voce in enumerate(voci_1090):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Lavorazione strutturale"))
        exc = _s(voce.get("classe_exc", "EXC2"))

        if i > 0:
            html += '<div class="page-break"></div>'

        html += f'<h3>1.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>EN 1090 — Strutture in acciaio</td></tr>
            <tr><td class="lbl">Classe di Esecuzione</td><td>{exc}</td></tr>
        </table>
        """

        # 1.x.1 — Certificati Materiali 3.1 (con Filtro Beltrami dall'indice pagine)
        cert_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("tipo") == "certificato_31"]
        # Include anche pagine indicizzate dallo Smistatore Intelligente
        indexed_pages = [p for p in data.get("page_index", [])
                         if _page_matches_voce(p, vid, "EN_1090")]
        html += f'<h4>1.{i + 1}.1 — Certificati Materiali 3.1 ({len(cert_docs)} doc. + {len(indexed_pages)} pag. indicizzate)</h4>'
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

        # Show indexed pages from Smistatore
        if indexed_pages:
            html += '<table class="data"><tr><th>Pag.</th><th>N. Colata</th><th>Materiale</th><th>Dimensioni</th><th>Acciaieria</th></tr>'
            for p in indexed_pages:
                html += f'<tr><td>{p.get("pagina", "")}</td><td>{_s(p.get("numero_colata", ""))}</td><td>{_s(p.get("tipo_materiale", ""))}</td><td>{_s(p.get("dimensioni", ""))}</td><td>{_s(p.get("acciaieria", ""))}</td></tr>'
            html += '</table>'

        # 1.x.2 — Foto Lavorazione
        foto_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("content_type", "").startswith("image/")]
        html += f'<h4>1.{i + 1}.2 — Foto Lavorazione ({len(foto_docs)})</h4>'
        html += _foto_html(foto_docs)

        # 1.x.3 — Verbale Collaudo Qualità
        html += f'<h4>1.{i + 1}.3 — Verbale Collaudo Qualita\'</h4>'
        html += _build_verbale(vid, data, "EN_1090")

        # 1.x.4 — Riepilogo Ore
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>1.{i + 1}.4 — Riepilogo Ore Lavorate</h4>'
        html += _build_riepilogo_ore(ore_entries)

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE B — CANCELLI EN 13241
# ══════════════════════════════════════════════════════════════

def _build_parte_b(voci_13241: list, data: dict) -> str:
    """Build CAP. 2: EN 13241 gate documents."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-13241">EN 13241</span> CAP. 2: SICUREZZA CANCELLI</h2>'

    for i, voce in enumerate(voci_13241):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Cancello"))
        tipo_ch = _s(voce.get("tipologia_chiusura", ""))

        if i > 0:
            html += '<div class="page-break"></div>'

        html += f'<h3>2.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>EN 13241 — Chiusure industriali</td></tr>
            {"<tr><td class='lbl'>Tipologia</td><td>" + tipo_ch + "</td></tr>" if tipo_ch else ""}
        </table>
        """

        # 2.x.1 — Foto Kit Sicurezza
        foto_docs = [d for d in data.get("docs", [])
                     if _doc_matches_voce(d, vid)
                     and d.get("content_type", "").startswith("image/")]
        html += f'<h4>2.{i + 1}.1 — Foto Kit Sicurezza ({len(foto_docs)})</h4>'
        html += _foto_html(foto_docs)

        # 2.x.2 — Verbale Collaudo
        html += f'<h4>2.{i + 1}.2 — Verbale Collaudo</h4>'
        html += _build_verbale(vid, data, "EN_13241")

        # 2.x.3 — Riepilogo Ore
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>2.{i + 1}.3 — Riepilogo Ore Lavorate</h4>'
        html += _build_riepilogo_ore(ore_entries)

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE C — LAVORAZIONI GENERICHE
# ══════════════════════════════════════════════════════════════

def _build_parte_c(voci_gen: list, data: dict) -> str:
    """Build CAP. 3: Technical report — hours and materials summary."""
    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-gen">RELAZIONE</span> CAP. 3: RELAZIONE TECNICA</h2>'

    for i, voce in enumerate(voci_gen):
        vid = voce.get("voce_id", "__principale__")
        desc = _s(voce.get("descrizione", "Lavorazione generica"))

        html += f'<h3>3.{i + 1} — {desc}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Voce di Lavoro</td><td>{desc}</td></tr>
            <tr><td class="lbl">Normativa</td><td>Nessuna marcatura CE</td></tr>
        </table>
        """

        # 3.x.1 — Riepilogo Ore e Materiali
        ore_entries = [e for e in data.get("diario", []) if _diario_matches_voce(e, vid)]
        html += f'<h4>3.{i + 1}.1 — Riepilogo Ore e Materiali</h4>'
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

    esito_badge = '<span class="badge badge-ok">ESITO POSITIVO</span>' if all_ok else '<span class="badge badge-nok">ESITO NEGATIVO</span>'

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
#  PARTE D — RELAZIONE DI MONTAGGIO (Fase 4)
# ══════════════════════════════════════════════════════════════

def _build_parte_d(commessa_id: str, voci_all: list, data: dict) -> str:
    """Build CAP. 4: Assembly Report — bolts used, torque values, photos, client signature."""
    montaggio_entries = data.get("montaggio", [])
    ddt_entries = data.get("bulloneria_ddt", [])

    if not montaggio_entries and not ddt_entries:
        return ""  # No assembly data, skip this chapter

    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-1090">MONTAGGIO</span> CAP. 4: RELAZIONE DI MONTAGGIO</h2>'

    # 4.1 — Tabella Bulloni Usati (da DDT)
    html += '<h3>4.1 — Bulloneria Utilizzata (dati da DDT)</h3>'
    if ddt_entries:
        html += '<table class="data"><tr><th>Fornitore</th><th>DDT N.</th><th>Diametro</th><th>Classe</th><th>Lotto</th><th>Quantita\'</th><th>Coppia (Nm)</th></tr>'
        for ddt in ddt_entries:
            fornitore = _s(ddt.get("fornitore", ""))
            n_ddt = _s(ddt.get("numero_ddt", ""))
            for b in ddt.get("bulloni", []):
                html += f'<tr><td>{fornitore}</td><td>{n_ddt}</td><td><strong>{_s(b.get("diametro", ""))}</strong></td><td>{_s(b.get("classe", ""))}</td><td>{_s(b.get("lotto", ""))}</td><td>{_s(b.get("quantita", ""))}</td><td style="text-align:right;font-weight:700;">{b.get("coppia_nm", "—")}</td></tr>'
        html += '</table>'
    else:
        html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessun DDT bulloneria registrato.</p>'

    # 4.2 — Serraggi Applicati
    html += '<h3>4.2 — Coppie di Serraggio Applicate</h3>'
    has_serraggi = False
    for entry in montaggio_entries:
        serraggi = entry.get("serraggi", [])
        if serraggi:
            has_serraggi = True
            op_nome = _s(entry.get("operatore_nome", ""))
            html += f'<h4>Operatore: {op_nome}</h4>'
            html += '<table class="data"><tr><th>Diametro</th><th>Classe</th><th>Coppia Prescritta (Nm)</th><th>Confermato</th><th>Chiave Dinamometrica</th></tr>'
            for s in serraggi:
                conf_badge = '<span class="badge badge-ok">SI</span>' if s.get("confermato") else '<span class="badge badge-nok">NO</span>'
                chiave_badge = '<span class="badge badge-ok">SI</span>' if s.get("chiave_dinamometrica") else '<span class="badge badge-nok">NO</span>'
                html += f'<tr><td><strong>{_s(s.get("diametro", ""))}</strong></td><td>{_s(s.get("classe", ""))}</td><td style="text-align:right;font-weight:700;">{s.get("coppia_nm", "—")}</td><td>{conf_badge}</td><td>{chiave_badge}</td></tr>'
            html += '</table>'

    if not has_serraggi:
        html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessun serraggio registrato.</p>'

    # 4.3 — Controllo Fondazioni
    html += '<h3>4.3 — Controllo Fondazioni / Appoggi</h3>'
    fondazioni_registrate = False
    for entry in montaggio_entries:
        fond = entry.get("fondazioni_ok")
        if fond is not None:
            fondazioni_registrate = True
            op_nome = _s(entry.get("operatore_nome", ""))
            badge = '<span class="badge badge-ok">IDONEO</span>' if fond else '<span class="badge badge-nok">NON IDONEO</span>'
            html += f'<table class="info"><tr><td class="lbl">Operatore</td><td>{op_nome}</td></tr><tr><td class="lbl">Esito</td><td>{badge}</td></tr></table>'
            if not fond:
                html += '<div class="note">ATTENZIONE: Fondazioni/appoggi giudicati NON IDONEI dall\'operatore.</div>'

    if not fondazioni_registrate:
        html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessun controllo fondazioni registrato.</p>'

    # 4.4 — Foto Montaggio
    foto_montaggio = [d for d in data.get("docs", [])
                      if (d.get("metadata_estratti") or {}).get("source") == "montaggio"]
    foto_giunti = [d for d in foto_montaggio if (d.get("metadata_estratti") or {}).get("tipo_foto") == "giunti"]
    foto_ancoraggi = [d for d in foto_montaggio if (d.get("metadata_estratti") or {}).get("tipo_foto") == "ancoraggi"]

    html += f'<h3>4.4 — Foto Giunti Serrati ({len(foto_giunti)})</h3>'
    html += _foto_html(foto_giunti)

    html += f'<h3>4.5 — Foto Ancoraggi ({len(foto_ancoraggi)})</h3>'
    html += _foto_html(foto_ancoraggi)

    # 4.6 — Note di Variante (evidenziate)
    varianti = data.get("varianti", [])
    html += f'<h3>4.6 — Note di Variante ({len(varianti)})</h3>'
    if varianti:
        for var in varianti:
            html += f"""
            <div class="note" style="border-left:4px solid #e67e22; background:#fef9f0; padding:10px; margin-bottom:8px;">
                <p style="font-weight:700; color:#e67e22; margin-bottom:4px;">VARIANTE</p>
                <p style="font-size:10pt; margin-bottom:4px;">{_s(var.get("descrizione", ""))}</p>
                <p style="font-size:8pt; color:#888;">Operatore: {_s(var.get("operatore_nome", ""))} — {_s(var.get("created_at", "")[:10])}</p>
            </div>"""
            # Include variant photo if available
            foto_id = var.get("foto_doc_id", "")
            if foto_id:
                foto_docs = [d for d in data.get("docs", []) if d.get("doc_id") == foto_id]
                if foto_docs:
                    html += _foto_html(foto_docs)
    else:
        html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessuna variante registrata.</p>'

    # 4.7 — Firma Cliente (Verbale Fine Lavori)
    html += '<h3>4.7 — Verbale di Fine Lavori — Firma Cliente</h3>'
    firma_trovata = False
    for entry in montaggio_entries:
        firma_b64 = entry.get("firma_cliente_base64", "")
        firma_nome = entry.get("firma_cliente_nome", "")
        firma_data = entry.get("firma_cliente_data", "")
        if firma_b64 and firma_nome:
            firma_trovata = True
            html += f"""
            <table class="info">
                <tr><td class="lbl">Cliente</td><td><strong>{_s(firma_nome)}</strong></td></tr>
                <tr><td class="lbl">Data Firma</td><td>{_s(firma_data[:10] if firma_data else "")}</td></tr>
                <tr><td class="lbl">Firma</td><td><img src="{firma_b64}" style="max-height:60px;max-width:250px;" /></td></tr>
            </table>
            <div class="sign-area">
                <div class="sign-box">
                    <div class="sign-label">Il Cliente dichiara di accettare i lavori eseguiti.</div>
                    <div class="sign-disclaimer">Firma apposta digitalmente su dispositivo mobile.</div>
                </div>
            </div>
            """
    if not firma_trovata:
        html += '<p style="font-size:9pt;color:#888;font-style:italic;">Nessuna firma cliente registrata.</p>'

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE E — SOSTENIBILITÀ E DNSH (CAP. 5)
# ══════════════════════════════════════════════════════════════

def _build_parte_e(commessa_id: str, data: dict) -> str:
    """Build CAP. 5: Sustainability and DNSH compliance data from AI analysis."""
    dnsh = data.get("dnsh_data", [])
    if not dnsh:
        return ""

    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-ok">DNSH</span> CAP. 5: SOSTENIBILITÀ E REQUISITI AMBIENTALI</h2>'

    html += '<h3>5.1 — Dati DNSH Estratti</h3>'
    html += '<table class="data"><tr><th>Voce</th><th>Riciclato</th><th>Certificazioni</th><th>CAM</th><th>Note</th></tr>'

    for d in dnsh:
        certs = ", ".join(d.get("certificazioni_ambientali", [])) or "—"
        riciclato = _s(d.get("percentuale_riciclato", "")) or "—"
        cam = '<span class="badge badge-ok">SI</span>' if d.get("conformita_cam") else '<span class="badge badge-nok">NO</span>'
        note = _s(d.get("note", ""))[:100]
        html += f'<tr><td>{_s(d.get("voce_id", "Principale"))}</td><td style="font-weight:700;">{riciclato}</td><td>{certs}</td><td>{cam}</td><td style="font-size:8pt;">{note}</td></tr>'

    html += '</table>'

    # Summary of sustainability keywords found
    all_diciture = []
    for d in dnsh:
        all_diciture.extend(d.get("diciture_sostenibilita", []))
    if all_diciture:
        html += '<h3>5.2 — Diciture di Sostenibilità Rilevate</h3>'
        html += '<ul style="font-size:10pt;">'
        for dic in set(all_diciture):
            html += f'<li>{_s(dic)}</li>'
        html += '</ul>'

    # Sicurezza cantiere data
    sic_data = data.get("sicurezza_cantiere", [])
    if sic_data:
        html += '<h3>5.3 — Checklist Sicurezza Cantiere</h3>'
        for sc in sic_data:
            op = _s(sc.get("operatore_nome", ""))
            data_str = _s(sc.get("created_at", "")[:10])
            html += f'<p style="font-size:9pt; font-weight:700;">Operatore: {op} — {data_str}</p>'
            html += '<table class="data"><tr><th>Controllo</th><th>Esito</th></tr>'
            for item in sc.get("checklist", []):
                esito = '<span class="badge badge-ok">OK</span>' if item.get("esito") else '<span class="badge badge-nok">NOK</span>'
                html += f'<tr><td>{_s(item.get("label", item.get("codice", "")))}</td><td>{esito}</td></tr>'
            html += '</table>'

    return html


# ══════════════════════════════════════════════════════════════
#  PARTE F — TRATTAMENTI SUPERFICIALI (Conto Lavoro)
# ══════════════════════════════════════════════════════════════

def _build_parte_f_trattamenti(commessa_id: str, data: dict) -> str:
    """Build chapter: Surface treatments from Conto Lavoro entries."""
    cl_items = data.get("conto_lavoro", [])
    if not cl_items:
        return ""

    html = '<div class="page-break"></div>'
    html += '<h2><span class="badge badge-1090">TRATTAMENTI</span> TRATTAMENTI SUPERFICIALI</h2>'

    tipo_labels = {
        "verniciatura": "Verniciatura",
        "zincatura": "Zincatura a Caldo",
        "sabbiatura": "Sabbiatura",
        "galvanica": "Trattamento Galvanico",
    }

    for i, cl in enumerate(cl_items):
        tipo = cl.get("tipo", "altro")
        label = tipo_labels.get(tipo, tipo.capitalize())
        fornitore = _s(cl.get("fornitore_nome", ""))
        stato = cl.get("stato", "da_inviare")
        ral = _s(cl.get("ral", ""))

        stato_badges = {
            "da_inviare": '<span class="badge badge-na">Da Inviare</span>',
            "inviato": '<span class="badge" style="background:#fef3c7;color:#92400e;">Inviato</span>',
            "in_lavorazione": '<span class="badge" style="background:#dbeafe;color:#1e40af;">In Lavorazione</span>',
            "rientrato": '<span class="badge badge-ok">Rientrato</span>',
            "verificato": '<span class="badge badge-ok">Verificato</span>',
        }

        if i > 0:
            html += '<div style="margin-top:12px;border-top:1px solid #ddd;padding-top:8px;"></div>'

        html += f'<h3>Trattamento {i + 1}: {label}</h3>'
        html += f"""
        <table class="info">
            <tr><td class="lbl">Tipo Trattamento</td><td>{label}</td></tr>
            <tr><td class="lbl">Fornitore</td><td>{fornitore}</td></tr>
            <tr><td class="lbl">Stato</td><td>{stato_badges.get(stato, stato)}</td></tr>
            {"<tr><td class='lbl'>Colore RAL</td><td>" + ral + "</td></tr>" if ral else ""}
            {"<tr><td class='lbl'>Data Invio</td><td>" + _s(cl.get('data_invio', '')[:10]) + "</td></tr>" if cl.get('data_invio') else ""}
            {"<tr><td class='lbl'>Data Rientro</td><td>" + _s(cl.get('data_rientro', '')[:10]) + "</td></tr>" if cl.get('data_rientro') else ""}
        </table>
        """

        # Materiali inviati
        righe = cl.get("righe", [])
        if righe:
            html += '<h4>Materiali Inviati</h4>'
            html += '<table class="data"><tr><th>Descrizione</th><th>Qta</th><th>Peso (kg)</th></tr>'
            for r in righe:
                html += f'<tr><td>{_s(r.get("descrizione", r.get("description", "")))}</td><td>{r.get("quantita", r.get("quantity", ""))}</td><td>{r.get("peso_kg", "")}</td></tr>'
            html += '</table>'

        # Esito QC al rientro
        if cl.get("esito_qc"):
            esito = cl["esito_qc"]
            esito_badge = '<span class="badge badge-ok">CONFORME</span>' if esito == "conforme" else '<span class="badge badge-nok">NON CONFORME</span>'
            html += f"""
            <h4>Esito Controllo Qualita al Rientro</h4>
            <table class="info">
                <tr><td class="lbl">Esito QC</td><td>{esito_badge}</td></tr>
                <tr><td class="lbl">DDT Fornitore</td><td>{_s(cl.get('ddt_fornitore_numero', ''))}</td></tr>
                <tr><td class="lbl">Peso Rientrato</td><td>{cl.get('peso_rientrato_kg', '')} kg</td></tr>
            </table>
            """
            if esito == "non_conforme" and cl.get("motivo_non_conformita"):
                html += f'<div class="note">MOTIVO NC: {_s(cl["motivo_non_conformita"])}</div>'

        # Certificato di trattamento (se caricato)
        if cl.get("certificato_rientro_filename"):
            html += f"""
            <h4>Certificato di Trattamento</h4>
            <table class="info">
                <tr><td class="lbl">File</td><td>{_s(cl.get('certificato_rientro_filename', ''))}</td></tr>
                <tr><td class="lbl">Tipo</td><td>Certificato {label}</td></tr>
            </table>
            <p style="font-size:8pt;color:#666;font-style:italic;">
                Il certificato di trattamento e' stato allegato al repository documenti della commessa
                e sara' incluso nella documentazione finale.
            </p>
            """

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


def _page_matches_voce(page: dict, voce_id: str, normativa: str) -> bool:
    """
    Filtro Beltrami: check if an indexed certificate page is relevant to a voce.
    Used by the Pulsante Magico to include only pertinent pages.
    """
    # Direct match to this voce
    if page.get("matched_to_voce") == voce_id:
        return True
    # Consumable auto-assigned to this normativa
    if page.get("matching_status") == "consumabile_auto":
        return page.get("consumabile_target", "") == normativa
    # Unmatched pages for the principal voce
    if voce_id == "__principale__" and page.get("matching_status") == "matched" and not page.get("matched_to_voce"):
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

    # ── BLOCCO CONTROLLI VISIVI: verifica che siano stati completati ──
    voci_che_richiedono_ctrl = [v for v in all_voci if v.get("normativa_tipo") in ("EN_1090", "EN_13241")]
    if voci_che_richiedono_ctrl:
        controlli = await db.controlli_visivi.find(
            {"commessa_id": commessa_id}, {"_id": 0}
        ).to_list(200)

        mancanti = []
        for voce_req in voci_che_richiedono_ctrl:
            vid = voce_req["voce_id"]
            voce_ctrls = [c for c in controlli if c.get("voce_id", "") == vid or
                          (vid == "__principale__" and not c.get("voce_id"))]
            if not voce_ctrls:
                desc = voce_req.get("descrizione", vid)
                mancanti.append(desc)
        if mancanti:
            raise ValueError(
                f"Controllo Visivo mancante per: {', '.join(mancanti)}. "
                "Completare tutti i controlli visivi obbligatori prima di generare il Pacco Documenti."
            )

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

    # Page index from Smistatore Intelligente (certificate page-level metadata)
    page_index = await db.doc_page_index.find(
        {"commessa_id": commessa_id},
        {"_id": 0, "page_pdf_b64": 0}
    ).to_list(500)

    # Montaggio data (Fase 4)
    montaggio = await db.diario_montaggio.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(100)

    bulloneria_ddt = await db.bulloneria_ddt.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(100)

    varianti = await db.varianti_montaggio.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(100)

    dnsh_data = await db.dnsh_data.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(50)

    sicurezza_cantiere = await db.sicurezza_cantiere.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(20)

    # Conto Lavoro (trattamenti superficiali)
    comm_ops = await db.commesse_ops.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "conto_lavoro": 1}
    )
    conto_lavoro = (comm_ops or {}).get("conto_lavoro", [])

    # Shared data context
    ctx = {
        "docs": docs,
        "diario": diario,
        "checklists": checklists,
        "company": company,
        "page_index": page_index,
        "montaggio": montaggio,
        "bulloneria_ddt": bulloneria_ddt,
        "varianti": varianti,
        "dnsh_data": dnsh_data,
        "sicurezza_cantiere": sicurezza_cantiere,
        "conto_lavoro": conto_lavoro,
    }

    # ── 2. BUILD INDEX (which parts to include) ──

    parti = []
    if voci_1090:
        parti.append({
            "lettera": "CAP. 1",
            "titolo": "STRUTTURE (EN 1090)",
            "subtitle": f"DoP, Certificati 3.1, WPS, Foto — {len(voci_1090)} voce/i",
        })
    if voci_13241:
        parti.append({
            "lettera": "CAP. 2",
            "titolo": "CANCELLI (EN 13241)",
            "subtitle": f"Dichiarazione Conformita', Foto Sicurezze, Manuale — {len(voci_13241)} voce/i",
        })
    if voci_gen or voci_1090 or voci_13241:
        parti.append({
            "lettera": "CAP. 3",
            "titolo": "RELAZIONE TECNICA",
            "subtitle": "Riepilogo ore e materiali",
        })
    if montaggio or bulloneria_ddt or varianti:
        parti.append({
            "lettera": "CAP. 4",
            "titolo": "RELAZIONE DI MONTAGGIO",
            "subtitle": "Bulloneria, serraggi, varianti, foto cantiere, firma cliente",
        })
    if dnsh_data:
        parti.append({
            "lettera": "CAP. 5",
            "titolo": "SOSTENIBILITÀ E DNSH",
            "subtitle": "Requisiti ambientali PNRR, materiale riciclato, certificazioni",
        })
    if conto_lavoro:
        cl_tipi = ", ".join(set(cl.get("tipo", "").capitalize() for cl in conto_lavoro if cl.get("tipo")))
        parti.append({
            "lettera": f"CAP. {len(parti) + 1}",
            "titolo": "TRATTAMENTI SUPERFICIALI",
            "subtitle": f"Conto lavoro: {cl_tipi or 'Lavorazioni esterne'} — certificati trattamento",
        })

    # ── 3. GENERATE HTML ──

    html_body = _build_cover(commessa, company, client_name, parti)

    if voci_1090:
        html_body += _build_parte_a(voci_1090, ctx)
    if voci_13241:
        html_body += _build_parte_b(voci_13241, ctx)
    # CAP. 3: Relazione Tecnica — includes generiche + riepilogo globale
    all_voci_for_relazione = voci_gen if voci_gen else []
    if all_voci_for_relazione or voci_1090 or voci_13241:
        html_body += _build_parte_c(all_voci_for_relazione, ctx)

    # CAP. 4: Relazione di Montaggio
    if montaggio or bulloneria_ddt or varianti:
        html_body += _build_parte_d(commessa_id, all_voci, ctx)

    # CAP. 5: Sostenibilità e DNSH
    if dnsh_data:
        html_body += _build_parte_e(commessa_id, ctx)

    # CAP. 6 (or 5): Trattamenti Superficiali (Conto Lavoro)
    cl_data = ctx.get("conto_lavoro", [])
    if cl_data:
        html_body += _build_parte_f_trattamenti(commessa_id, ctx)

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

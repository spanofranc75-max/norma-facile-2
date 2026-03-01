"""PDF Generators for EN 1090 Technical Dossier documents.
DOP (Dichiarazione di Prestazione), CE Marking, Piano di Controllo, Rapporto VT.
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# ══════════════════════════════════════════════════════════════
# SHARED CSS
# ══════════════════════════════════════════════════════════════
BASE_CSS = """
@page { size: A4; margin: 12mm 10mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 9.5pt; color: #1a1a1a; line-height: 1.35; margin: 0; padding: 0; }
.hdr { display: table; width: 100%; margin-bottom: 6px; border-bottom: 2px solid #1e3a5f; padding-bottom: 5px; }
.hdr-l { display: table-cell; vertical-align: middle; width: 40%; }
.hdr-r { display: table-cell; vertical-align: middle; width: 60%; text-align: right; }
.co-name { font-size: 13pt; font-weight: 700; color: #1e3a5f; }
.co-sub { font-size: 7.5pt; color: #666; }
.doc-title { font-size: 14pt; font-weight: 700; color: #1e3a5f; text-align: center; margin: 8px 0; text-transform: uppercase; }
.doc-mod { font-size: 7pt; color: #888; text-align: center; margin-bottom: 6px; }
.info td { padding: 2px 5px; font-size: 9pt; }
.info .lbl { font-weight: 600; color: #1e3a5f; width: 130px; }
.info .val { border-bottom: 1px dotted #ccc; }
table.main { width: 100%; border-collapse: collapse; margin-top: 6px; }
table.main th { background: #1e3a5f; color: white; padding: 4px 3px; font-size: 7.5pt; font-weight: 600; text-align: center; border: 1px solid #1e3a5f; }
table.main td { padding: 3px 4px; font-size: 8pt; border: 1px solid #ccc; }
table.main tr:nth-child(even) { background: #f8f9fa; }
.chk { font-size: 10pt; }
.footer { margin-top: 10px; padding-top: 3px; border-top: 1px solid #ccc; font-size: 7pt; color: #888; text-align: center; }
.sign-area { display: table; width: 100%; margin-top: 14px; }
.sign-box { display: table-cell; width: 50%; padding: 6px; vertical-align: top; }
.sign-label { font-size: 8pt; font-weight: 600; color: #1e3a5f; border-bottom: 1px solid #1e3a5f; padding-bottom: 2px; margin-bottom: 4px; }
.sign-line { border-bottom: 1px dotted #999; height: 24px; margin: 6px 0; }
.section-title { font-size: 10pt; font-weight: 700; color: #1e3a5f; margin: 8px 0 4px 0; border-bottom: 1px solid #1e3a5f; padding-bottom: 2px; }
"""

def _header_html(biz, addr, piva, phone, email):
    return f"""<div class="hdr">
    <div class="hdr-l"><div class="co-name">{biz}</div><div class="co-sub">{addr}</div><div class="co-sub">P.IVA: {piva} | Tel: {phone}</div></div>
    <div class="hdr-r"><div class="co-sub">{email}</div></div></div>"""

def _co(company):
    return (company.get("business_name",""), f"{company.get('address','')} {company.get('city','')} {company.get('cap','')}".strip(),
            company.get("partita_iva",""), company.get("phone",""), company.get("email",""))

def _render(html_str):
    buf = BytesIO()
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════
# 1. DOP — Dichiarazione di Prestazione
# ══════════════════════════════════════════════════════════════
def generate_dop_pdf(company: dict, commessa: dict, client_name: str, dop_data: dict) -> BytesIO:
    biz, addr, piva, phone, email = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    ddt_ref = dop_data.get("ddt_riferimento", "")
    ddt_data = dop_data.get("ddt_data", "")
    mandatario = dop_data.get("mandatario", client_name)
    firmatario = dop_data.get("firmatario", "")
    ruolo = dop_data.get("ruolo_firmatario", "Legale Rappresentante")
    luogo_data = dop_data.get("luogo_data_firma", "")
    cert_num = dop_data.get("certificato_numero", "")
    ente = dop_data.get("ente_notificato", "")
    materiali_str = dop_data.get("materiali_saldabilita", "S355JR - S275JR in accordo alla EN 10025-2")
    resilienza = dop_data.get("resilienza", "27 Joule a +/- 20 C")

    # Build performance table
    chars = [
        ("4.2 / 5.3", "Tolleranza delle dimensioni e della forma", "EN 1090-2:2024"),
        ("4.3 / 5.3", "Saldabilita", materiali_str),
        ("4.4 / 4.8 / 5.10", "Resistenza alla rottura / Resistenza agli urti", resilienza),
        ("4.5.1 / 4.5.2 / 5.6.2", "Capacita portante", "NPD"),
        ("4.5.5", "Deformazione di utilizzo allo stato limite", "NPD"),
        ("4.5.1 / 4.5.3 / 5.6.2", "Resistenza alla fatica", "NPD"),
        ("4.5.1 / 4.5.4 / 5.7", "Resistenza al fuoco", "NPD"),
        ("4.6 / 5.8", "Reazione al fuoco", "Classe A1"),
        ("4.7 / 5.9", "Rilascio di cadmio e suoi composti", "NPD"),
        ("4.7 / 5.9", "Emissione di radioattivita", "NPD"),
        ("4.9 / 5.11", "Durabilita", "NPD"),
    ]
    rows = "".join(f'<tr><td style="text-align:center;font-size:7pt;">{r}</td><td>{c}</td><td style="text-align:center;">{p}</td></tr>' for r, c, p in chars)

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}</style></head><body>
    {_header_html(biz, addr, piva, phone, email)}
    <div class="doc-title">Dichiarazione di Prestazione N. {comm_num}</div>
    <div class="doc-mod">(Secondo Regolamento UE 574/2014) — All. 4 Rev. 0</div>
    <table class="info" style="width:100%;border-collapse:collapse;">
        <tr><td class="lbl">1. Codice prodotto-tipo:</td><td class="val">{comm_num}</td></tr>
        <tr><td class="lbl">2. Usi previsti:</td><td class="val">{comm_title} — Rif. DDT n. {ddt_ref} del {ddt_data}</td></tr>
        <tr><td class="lbl">3. Fabbricante:</td><td class="val">{biz} — {addr}</td></tr>
        <tr><td class="lbl">4. Mandatario:</td><td class="val">{mandatario}</td></tr>
        <tr><td class="lbl">5. Sistema valutazione:</td><td class="val">Sistema 2+ — {ente}</td></tr>
        <tr><td class="lbl">6. Norma armonizzata:</td><td class="val">UNI EN 1090-1 — Certificato n. {cert_num}</td></tr>
    </table>
    <div class="section-title">7. Prestazione Dichiarata — EN 1090-2:2024 Appendice B6, B8</div>
    <table class="main">
        <thead><tr><th style="width:15%">UNI EN 1090-1</th><th style="width:50%">Caratteristiche Essenziali</th><th style="width:35%">Prestazione Dichiarata</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="font-size:8pt;margin-top:8px;">8. Documentazione tecnica appropriata: Requisiti soddisfatti dal prodotto.</p>
    <p style="font-size:8pt;">9. La prestazione del prodotto sopra identificato e conforme all'insieme delle prestazioni dichiarate. La presente dichiarazione viene emessa sotto la responsabilita del fabbricante sopra identificato.</p>
    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Nome e Cognome</div><div style="font-size:9pt;">{firmatario}</div><div class="sign-label" style="margin-top:6px;">Posizione</div><div style="font-size:9pt;">{ruolo}</div></div>
        <div class="sign-box"><div class="sign-label">Luogo e data</div><div style="font-size:9pt;">{luogo_data}</div><div class="sign-line"></div></div>
    </div>
    <div class="footer">{biz} | {email} | Generato da NormaFacile 2.0</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 2. CE — Marcatura CE
# ══════════════════════════════════════════════════════════════
def generate_ce_pdf(company: dict, commessa: dict, client_name: str, ce_data: dict) -> BytesIO:
    biz, addr, piva, phone, email = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")
    cert_num = ce_data.get("certificato_numero", "")
    ente = ce_data.get("ente_notificato", "")
    ente_num = ce_data.get("ente_numero", "")
    dop_num = ce_data.get("dop_numero", comm_num)
    disegno = ce_data.get("disegno_riferimento", "")
    materiali = ce_data.get("materiali", "S355JR - S275JR in accordo alla EN 10025-2")
    resilienza = ce_data.get("resilienza", "27 Joule a +/- 20 C")

    chars = [
        ("Tolleranze geometriche", "EN 1090-2:2024"),
        ("Saldabilita", materiali),
        ("Resistenza alla rottura", resilienza),
        ("Capacita di carico", "NPD"),
        ("Resistenza alla fatica", "NPD"),
        ("Resistenza al fuoco", "NPD"),
        ("Reazione al fuoco", "Materiale classificato A1"),
        ("Sostanze pericolose", "NPD"),
        ("Durabilita", "NPD"),
    ]
    rows = "".join(f'<tr><td>{c}</td><td style="text-align:center;">{v}</td></tr>' for c, v in chars)

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    .ce-mark {{ text-align:center; font-size:36pt; font-weight:900; color:#1e3a5f; margin:10px 0; letter-spacing:6px; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email)}
    <div class="ce-mark">CE</div>
    <div class="doc-mod">Progettazione effettuata dal committente — All. 5 Rev. 0</div>
    <table class="info" style="width:100%;border-collapse:collapse;">
        <tr><td class="lbl">Ente notificato:</td><td class="val">{ente} n. {ente_num}</td></tr>
        <tr><td class="lbl">Produttore:</td><td class="val">{biz} — {addr}</td></tr>
        <tr><td class="lbl">Commessa:</td><td class="val">{comm_num}</td></tr>
        <tr><td class="lbl">Certificato n.:</td><td class="val">{cert_num}</td></tr>
        <tr><td class="lbl">DOP N.:</td><td class="val">{dop_num}</td></tr>
        <tr><td class="lbl">Descrizione prodotto:</td><td class="val">{comm_title}</td></tr>
        <tr><td class="lbl">Classe di esecuzione:</td><td class="val">{classe_exec}</td></tr>
        <tr><td class="lbl">Disegno riferimento:</td><td class="val">{disegno}</td></tr>
    </table>
    <table class="main" style="margin-top:10px;">
        <thead><tr><th style="width:55%">Caratteristica</th><th style="width:45%">Prestazione</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <div class="footer">{biz} | {email} | Generato da NormaFacile 2.0</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 3. Piano di Controllo Qualita (MOD. 02)
# ══════════════════════════════════════════════════════════════
DEFAULT_PHASES = [
    {"fase": "Ricezione materiali e certificati", "doc_rif": "Ordini d'Acquisto / DDT / Certificati Marcatura CE IO 02", "applicabile": True},
    {"fase": "Movimentazione e stoccaggio", "doc_rif": "PRO 06 UNI EN 1090-2 (prosp. 8)", "applicabile": True},
    {"fase": "Taglio - Foratura (a freddo sega/trapano)", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": True},
    {"fase": "Taglio - Foratura lamiere/profili grigliati", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": False},
    {"fase": "Piegatura a freddo", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": False},
    {"fase": "Preparazione lembi di saldatura", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2", "applicabile": True},
    {"fase": "Puntatura lembi ed attacchi temporanei", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2", "applicabile": True},
    {"fase": "Esecuzione ed accettabilita saldatura", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2 Registro Saldatura", "applicabile": True},
    {"fase": "Controllo visivo saldature", "doc_rif": "Disegno n.{disegno} IO 02 IO 03 WPS Norma 3834-2 Registro Saldatura", "applicabile": True},
    {"fase": "Controlli CND", "doc_rif": "Disegno n.{disegno} IO 02 WPS Norma 3834-2 Registro Saldatura", "applicabile": False},
    {"fase": "Controllo dimensionale e tolleranze", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": True},
    {"fase": "Preparazione superficiale per finiture", "doc_rif": "Specifica Cliente IO 02 EN ISO 8501-3", "applicabile": False},
    {"fase": "Zincatura", "doc_rif": "Specifica Cliente IO 02 EN ISO 1461 DDT", "applicabile": False},
    {"fase": "Sabbiatura e verniciatura", "doc_rif": "Specifica Cliente IO 02 EN ISO 12944 DDT N.", "applicabile": False},
    {"fase": "Imballaggio / Spedizione prodotto", "doc_rif": "Disegno n.{disegno} IO 02 UNI EN 1090-1 DDT", "applicabile": True},
    {"fase": "Montaggio in cantiere (serraggio bulloni)", "doc_rif": "Disegno n.{disegno} IO 04", "applicabile": False},
]

def generate_piano_controllo_pdf(company: dict, commessa: dict, client_name: str, pc_data: dict) -> BytesIO:
    biz, addr, piva, phone, email = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    disegno = pc_data.get("disegno_numero", "")
    ordine_num = pc_data.get("ordine_numero", comm_num)
    fasi = pc_data.get("fasi", [])

    rows = ""
    for f in fasi:
        fase = f.get("fase", "")
        doc_rif = f.get("doc_rif", "").replace("{disegno}", disegno)
        applicabile = f.get("applicabile", True)
        periodo = f.get("periodo_pianificato", "") if applicabile else "Non Applicabile"
        ctrl_verb = f.get("controllo_verbale", "") if applicabile else ""
        esito = f.get("esito", "")  # "positivo", "negativo", ""
        data_firma = f.get("data_effettiva", "") if applicabile else ""

        esito_html = ""
        if not applicabile:
            esito_html = '<span style="color:#999;">N/A</span>'
        elif esito == "positivo":
            esito_html = '<span class="chk" style="color:green;">&#9745;</span> Pos <span class="chk" style="color:#ccc;">&#9744;</span> Neg'
        elif esito == "negativo":
            esito_html = '<span class="chk" style="color:#ccc;">&#9744;</span> Pos <span class="chk" style="color:red;">&#9745;</span> Neg'
        else:
            esito_html = '<span class="chk">&#9744;</span> Pos <span class="chk">&#9744;</span> Neg'

        bg = "" if applicabile else 'style="background:#f5f5f5; color:#999;"'
        rows += f'<tr {bg}><td style="text-align:left;font-size:7.5pt;">{fase}</td><td style="font-size:7pt;">{doc_rif}</td><td style="text-align:center;">{periodo}</td><td style="text-align:center;">{ctrl_verb}</td><td style="text-align:center;">{esito_html}</td><td style="text-align:center;">{data_firma}</td></tr>'

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    @page {{ size: A4 landscape; margin: 10mm 8mm; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email)}
    <div class="doc-title">Piano di Controllo Qualita</div>
    <div class="doc-mod">MOD. 02 Rev. 00 — EN 1090</div>
    <table class="info" style="width:100%;border-collapse:collapse;">
        <tr><td class="lbl">Cliente:</td><td class="val">{client_name}</td><td class="lbl">Commessa N.:</td><td class="val">{comm_num}</td></tr>
        <tr><td class="lbl">Descrizione Lavoro:</td><td class="val">{comm_title}</td><td class="lbl">Ordine N.:</td><td class="val">{ordine_num}</td></tr>
    </table>
    <table class="main">
        <thead><tr>
            <th style="width:22%">Fase da Controllare</th>
            <th style="width:25%">Documenti di Riferimento</th>
            <th style="width:10%">Periodo Pianif.</th>
            <th style="width:10%">Controllo Verb. N.</th>
            <th style="width:13%">Esito</th>
            <th style="width:20%">Data Effettiva / Firma</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Data e Firma per Emissione</div><div class="sign-line"></div></div>
        <div class="sign-box"><div class="sign-label">Data e Firma per Approvazione</div><div class="sign-line"></div></div>
    </div>
    <div class="footer">{biz} | {email} | Generato da NormaFacile 2.0</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 4. Rapporto VT — Esame Visivo Dimensionale (MOD. 06)
# ══════════════════════════════════════════════════════════════
def generate_rapporto_vt_pdf(company: dict, commessa: dict, client_name: str, vt_data: dict) -> BytesIO:
    biz, addr, piva, phone, email = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    disegno = vt_data.get("disegno_numero", "")
    report_num = vt_data.get("report_numero", comm_num)
    report_data = vt_data.get("report_data", "")
    processo_saldatura = vt_data.get("processo_saldatura", "135")
    norma_procedura = vt_data.get("norma_procedura", "UNI EN ISO 17637 - IO 03")
    accettabilita = vt_data.get("accettabilita", "ISO 5817 livello C")
    materiale = vt_data.get("materiale", "")
    temp_pezzo = vt_data.get("temperatura_pezzo", "")
    profilato = vt_data.get("profilato", "")
    spessore = vt_data.get("spessore", "")

    def chk(val, key): return '<span style="color:green;">&#9745;</span>' if val.get(key) else '<span style="color:#ccc;">&#9744;</span>'

    visione = vt_data.get("condizioni_visione", {})
    superficie = vt_data.get("stato_superficie", {})
    ispezione = vt_data.get("tipo_ispezione", {})
    attrezzatura = vt_data.get("attrezzatura", {})
    dist_max = vt_data.get("distanza_max_mm", "600")
    angolo_min = vt_data.get("angolo_min_gradi", "30")
    tipo_illuminatore = vt_data.get("tipo_illuminatore", "LUX")
    calibro_info = vt_data.get("calibro_info", "")

    # Controlled objects table
    oggetti = vt_data.get("oggetti_controllati", [])
    ogg_rows = ""
    for o in oggetti:
        esito_color = "green" if o.get("esito", "").lower() == "positivo" else ("red" if o.get("esito", "").lower() == "negativo" else "#333")
        ogg_rows += f'<tr><td>{o.get("numero","")}</td><td>{o.get("disegno","")}</td><td>{o.get("marca","")}</td><td>{o.get("dimensioni","")}</td><td style="text-align:center;">{o.get("estensione_controllo","100")}%</td><td style="text-align:center;color:{esito_color};font-weight:600;">{o.get("esito","")}</td></tr>'
    if not oggetti:
        ogg_rows = '<tr><td colspan="6" style="text-align:center;color:#999;">Nessun oggetto controllato</td></tr>'

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    .params {{ width:100%; border-collapse:collapse; margin:4px 0; }}
    .params td {{ padding:2px 4px; font-size:8pt; border:1px solid #eee; }}
    .params .plbl {{ font-weight:600; color:#1e3a5f; background:#f0f4f8; width:25%; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email)}
    <div class="doc-title">Rapporto di Esame Visivo - Dimensionale</div>
    <div class="doc-mod">MOD. 06 Rev. 0 — Report VT N. {report_num} — Data: {report_data}</div>

    <table class="params">
        <tr><td class="plbl">Cliente:</td><td>{client_name}</td><td class="plbl">Commessa / Ordine:</td><td>{comm_num}</td></tr>
        <tr><td class="plbl">DWG N.:</td><td>{disegno}</td><td class="plbl">PCQ N.:</td><td>{comm_num}</td></tr>
        <tr><td class="plbl">Oggetto:</td><td colspan="3">{comm_title}</td></tr>
        <tr><td class="plbl">Processo saldatura:</td><td>{processo_saldatura}</td><td class="plbl">Norma / Procedura:</td><td>{norma_procedura}</td></tr>
        <tr><td class="plbl">Accettabilita:</td><td>{accettabilita}</td><td class="plbl">Materiale:</td><td>{materiale}</td></tr>
        <tr><td class="plbl">Temp. pezzo:</td><td>{temp_pezzo}</td><td class="plbl">Profilato:</td><td>{profilato}</td></tr>
        <tr><td class="plbl">Spessore:</td><td>{spessore}</td><td class="plbl"></td><td></td></tr>
    </table>

    <table class="params">
        <tr><td class="plbl">Condizioni di visione:</td>
            <td>{chk(visione,'naturale')} Naturale {chk(visione,'artificiale')} Artificiale {chk(visione,'lampada_wood')} Lamp. Wood</td>
            <td class="plbl">Tipo illuminatore:</td><td>{tipo_illuminatore}</td></tr>
        <tr><td class="plbl">Stato superficie:</td>
            <td colspan="3">{chk(superficie,'come_saldato')} Come saldato {chk(superficie,'molato')} Molato {chk(superficie,'spazzolato')} Spazzolato {chk(superficie,'lavorato_macchina')} Lav. macchina {chk(superficie,'come_laminato')} Come laminato {chk(superficie,'verniciato')} Verniciato</td></tr>
        <tr><td class="plbl">Tipo ispezione:</td>
            <td>{chk(ispezione,'diretto')} Diretto {chk(ispezione,'remoto')} Remoto {chk(ispezione,'generale')} Generale {chk(ispezione,'locale')} Locale</td>
            <td class="plbl">Dist. max / Angolo min:</td><td>{dist_max} mm / {angolo_min} gradi</td></tr>
        <tr><td class="plbl">Attrezzatura:</td>
            <td colspan="3">{chk(attrezzatura,'calibro')} Calibro {chk(attrezzatura,'specchio')} Specchio {chk(attrezzatura,'lente')} Lente {chk(attrezzatura,'endoscopio')} Endoscopio {chk(attrezzatura,'fotocamera')} Fotocamera {chk(attrezzatura,'videocamera')} Videocamera</td></tr>
        <tr><td class="plbl">Marca/Modello/Matricola:</td><td colspan="3">{calibro_info}</td></tr>
    </table>

    <div class="section-title">Oggetto Controllato</div>
    <table class="main">
        <thead><tr><th>N.</th><th>Disegno</th><th>Marca</th><th>Dimensioni</th><th>Estens. Ctrl (%)</th><th>Esito</th></tr></thead>
        <tbody>{ogg_rows}</tbody>
    </table>

    <table class="params" style="margin-top:8px;">
        <tr><td class="plbl">Note:</td><td colspan="3">{vt_data.get('note','')}</td></tr>
    </table>

    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Resp. Controllo VT</div><div class="sign-line"></div></div>
        <div class="sign-box"><div class="sign-label">Coordinatore della Saldatura</div><div class="sign-line"></div></div>
    </div>
    <div class="footer">{biz} | {email} | Generato da NormaFacile 2.0</div>
    </body></html>"""
    return _render(html)

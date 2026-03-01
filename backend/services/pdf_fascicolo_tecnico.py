"""PDF Generators for EN 1090 Technical Dossier documents.
DOP, CE Marking, Piano di Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico.
Struttura identica ai modelli originali forniti dall'utente.
"""
from io import BytesIO
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# ══════════════════════════════════════════════════════════════
# SHARED CSS — Stile fedele ai documenti originali
# ══════════════════════════════════════════════════════════════
BASE_CSS = """
@page { size: A4; margin: 12mm 15mm; }
* { box-sizing: border-box; }
body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #000; line-height: 1.4; margin: 0; padding: 0; }
.header-table { width: 100%; border-collapse: collapse; border: 2px solid #000; margin-bottom: 0; }
.header-table td { padding: 4px 8px; vertical-align: middle; }
.logo-cell { width: 25%; text-align: center; border-right: 1px solid #000; }
.title-cell { width: 50%; text-align: center; font-size: 14pt; font-weight: 700; text-transform: uppercase; }
.meta-cell { width: 25%; border-left: 1px solid #000; font-size: 8pt; }
.co-name { font-size: 12pt; font-weight: 700; color: #1a3a6b; }
.co-sub { font-size: 7.5pt; color: #444; }
.info-table { width: 100%; border-collapse: collapse; margin-top: 4px; border: 1px solid #000; }
.info-table td { padding: 3px 6px; font-size: 9pt; border: 1px solid #000; }
.info-lbl { font-weight: 700; background: #f0f0f0; width: 20%; }
table.main { width: 100%; border-collapse: collapse; margin-top: 6px; }
table.main th { background: #f0f0f0; color: #000; padding: 4px 3px; font-size: 8pt; font-weight: 700; text-align: center; border: 1px solid #000; }
table.main td { padding: 3px 4px; font-size: 8pt; border: 1px solid #000; }
.chk { font-size: 11pt; }
.chk-yes { color: #000; }
.chk-no { color: #ccc; }
.footer-mod { font-size: 7.5pt; color: #555; margin-top: 8px; }
.sign-area { display: table; width: 100%; margin-top: 16px; }
.sign-box { display: table-cell; width: 50%; padding: 8px; vertical-align: top; }
.sign-label { font-size: 9pt; font-weight: 600; margin-bottom: 2px; }
.sign-line { border-bottom: 1px solid #000; height: 30px; margin: 8px 0; }
.section-title { font-size: 10pt; font-weight: 700; margin: 10px 0 4px 0; border-bottom: 1px solid #000; padding-bottom: 2px; }
"""

def _header_html(biz, addr, piva, phone, email, title, mod_text="", logo_url=""):
    logo_html = f'<img src="{logo_url}" style="max-height:40px;max-width:100%;" /><br/>' if logo_url else ""
    return f"""<table class="header-table">
    <tr>
        <td class="logo-cell">{logo_html}<div class="co-name">{biz}</div><div class="co-sub">{addr}</div></td>
        <td class="title-cell">{title}</td>
        <td class="meta-cell">{mod_text}<br/><span style="font-size:7pt;">P.IVA: {piva}</span></td>
    </tr></table>"""

def _firma_img_html(firma_b64):
    """Returns an <img> tag for the firma digitale if available."""
    if firma_b64:
        return f'<img src="{firma_b64}" style="max-height:40px;max-width:140px;margin-top:2px;" />'
    return ""

def _co(company):
    return (company.get("business_name",""), 
            f"{company.get('address','')} {company.get('city','')} {company.get('cap','')}".strip(),
            company.get("partita_iva",""), company.get("phone",""), company.get("email",""),
            company.get("logo_url",""), company.get("firma_digitale",""))

def _render(html_str):
    buf = BytesIO()
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)
    return buf

def _chk(val):
    return '<span class="chk chk-yes">&#9746;</span>' if val else '<span class="chk chk-no">&#9744;</span>'

# ══════════════════════════════════════════════════════════════
# 1. DOP — Dichiarazione di Prestazione
# ══════════════════════════════════════════════════════════════
def generate_dop_pdf(company: dict, commessa: dict, client_name: str, dop_data: dict) -> BytesIO:
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    redatto_da = dop_data.get("redatto_da", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")
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

    chars = [
        ("4.2 / 5.3", "Tolleranza delle dimensioni e della forma", "EN 1090-2:2024"),
        ("4.3 / 5.3", "Saldabilita'", materiali_str),
        ("4.4 / 4.8 / 5.10", "Resistenza alla rottura / Resistenza agli urti", resilienza),
        ("4.5.1 / 4.5.2 / 5.6.2", "Capacita' portante", "NPD"),
        ("4.5.5", "Deformazione di utilizzo allo stato limite", "NPD"),
        ("4.5.1 / 4.5.3 / 5.6.2", "Resistenza alla fatica", "NPD"),
        ("4.5.1 / 4.5.4 / 5.7", "Resistenza al fuoco", "NPD"),
        ("4.6 / 5.8", "Reazione al fuoco", "Classe A1"),
        ("4.7 / 5.9", "Rilascio di cadmio e suoi composti", "NPD"),
        ("4.7 / 5.9", "Emissione di radioattivita'", "NPD"),
        ("4.9 / 5.11", "Durabilita'", "NPD"),
    ]
    rows = "".join(f'<tr><td style="text-align:center;width:18%;">{r}</td><td style="width:45%;">{c}</td><td style="text-align:center;width:37%;">{p}</td></tr>' for r, c, p in chars)

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}</style></head><body>
    {_header_html(biz, addr, piva, phone, email, 'Dichiarazione di Prestazione', 'All. 4 Rev. 0', logo)}
    <p style="text-align:center;font-size:9pt;margin:6px 0;">(Secondo Regolamento UE 574/2014)</p>
    <table class="info-table">
        <tr><td class="info-lbl">1. Codice prodotto-tipo:</td><td>{comm_num}</td></tr>
        <tr><td class="info-lbl">2. Usi previsti:</td><td>{comm_title} — Rif. DDT n. {ddt_ref} del {ddt_data}</td></tr>
        <tr><td class="info-lbl">3. Fabbricante:</td><td>{biz} — {addr}</td></tr>
        <tr><td class="info-lbl">4. Mandatario:</td><td>{mandatario}</td></tr>
        <tr><td class="info-lbl">5. Sistema valutazione:</td><td>Sistema 2+ — {ente}</td></tr>
        <tr><td class="info-lbl">6. Norma armonizzata:</td><td>UNI EN 1090-1 — Certificato n. {cert_num}</td></tr>
        <tr><td class="info-lbl">Classe di esecuzione:</td><td>{classe_exec}</td></tr>
        <tr><td class="info-lbl">Redatto da:</td><td>{redatto_da}</td></tr>
    </table>
    <div class="section-title">7. Prestazione Dichiarata — EN 1090-2:2024 Appendice B6, B8</div>
    <table class="main">
        <thead><tr><th style="width:18%">UNI EN 1090-1</th><th style="width:45%">Caratteristiche Essenziali</th><th style="width:37%">Prestazione Dichiarata</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="font-size:8.5pt;margin-top:8px;">8. Documentazione tecnica appropriata: Requisiti soddisfatti dal prodotto.</p>
    <p style="font-size:8.5pt;">9. La prestazione del prodotto sopra identificato e' conforme all'insieme delle prestazioni dichiarate. La presente dichiarazione viene emessa sotto la responsabilita' del fabbricante sopra identificato.</p>
    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Nome e Cognome: {firmatario}</div><div class="sign-label" style="margin-top:4px;">Posizione: {ruolo}</div></div>
        <div class="sign-box"><div class="sign-label">Luogo e data: {luogo_data}</div><div class="sign-label" style="margin-top:6px;">Firma:</div>{_firma_img_html(firma)}<div class="sign-line"></div></div>
    </div>
    <div class="footer-mod">All. 4 Rev. 0 | {biz}</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 2. CE — Marcatura CE (etichetta identica all'originale)
# ══════════════════════════════════════════════════════════════
def generate_ce_pdf(company: dict, commessa: dict, client_name: str, ce_data: dict) -> BytesIO:
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")
    cert_num = ce_data.get("certificato_numero", "")
    ente = ce_data.get("ente_notificato", "")
    ente_num = ce_data.get("ente_numero", "")
    dop_num = ce_data.get("dop_numero", comm_num)
    disegno = ce_data.get("disegno_riferimento", "")
    materiali = ce_data.get("materiali_saldabilita", ce_data.get("materiali", "S355JR - S275JR in accordo alla EN 10025-2"))
    resilienza = ce_data.get("resilienza", "27 Joule a +/- 20 C")

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: A4; margin: 20mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Calibri, Arial, sans-serif; font-size: 10pt; color: #000; margin: 0; padding: 0; }}
    .ce-box {{ border: 2px solid #000; padding: 20px 25px; max-width: 100%; }}
    .ce-top {{ font-size: 9pt; margin-bottom: 8px; }}
    .ce-mark {{ text-align: center; font-size: 48pt; font-weight: 900; margin: 12px 0; letter-spacing: 8px; font-family: 'Times New Roman', serif; }}
    .ce-field {{ margin: 3px 0; font-size: 9.5pt; line-height: 1.5; }}
    .ce-field b {{ font-weight: 700; }}
    .ce-chars {{ margin-top: 10px; }}
    .ce-char {{ margin: 2px 0; font-size: 9.5pt; }}
    .footer-text {{ font-size: 7.5pt; color: #555; margin-top: 12px; }}
    </style></head><body>
    <div class="ce-box">
        <div class="ce-top">Progettazione effettuata dal committente</div>
        <div class="ce-mark">CE</div>
        <div class="ce-field"><b>Numero identificativo dell'ente notificato:</b> {ente} n. {ente_num}</div>
        <div class="ce-field"><b>Produttore:</b> {biz}, {addr}</div>
        <div class="ce-field"><b>Commessa di riferimento:</b> {comm_num}</div>
        <div class="ce-field"><b>Certificato n.:</b> {cert_num}</div>
        <div class="ce-field"><b>EN 1090-1:2009 + A1:2011</b></div>
        <div class="ce-field"><b>DOP N.:</b> {dop_num}</div>
        <div class="ce-field"><b>Descrizione del prodotto:</b> {comm_title}</div>
        <div class="ce-chars">
            <div class="ce-char"><b>Tolleranze geometriche:</b> EN 1090-2:2024</div>
            <div class="ce-char"><b>Saldabilita':</b> ({materiali})</div>
            <div class="ce-char"><b>Resistenza alla rottura:</b> ({resilienza})</div>
            <div class="ce-char"><b>Capacita' di carico:</b> NPD</div>
            <div class="ce-char"><b>Resistenza alla fatica:</b> NPD</div>
            <div class="ce-char"><b>Resistenza al fuoco:</b> NPD</div>
            <div class="ce-char"><b>Reazione al fuoco:</b> (materiale classificato A1)</div>
            <div class="ce-char"><b>Sostanze pericolose:</b> NPD</div>
            <div class="ce-char"><b>Durabilita':</b> NPD</div>
            <div class="ce-char"><b>Caratteristiche strutturali:</b> Disegni Forniti dal committente TAV. {disegno}</div>
            <div class="ce-char"><b>Costruzione:</b> in accordo alla specifica del cliente disegno {disegno}, EN 1090-2</div>
            <div class="ce-char"><b>Classe di esecuzione:</b> {classe_exec}</div>
        </div>
    </div>
    <div class="footer-text">All. 5 Rev. 0</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 3. Piano di Controllo Qualita' (MOD. 02)
# ══════════════════════════════════════════════════════════════
DEFAULT_PHASES = [
    {"fase": "Ricezione materiali e certificati", "doc_rif": "Ordini d'Acquisto / DDT / Certificati Marcatura CE IO 02", "applicabile": True},
    {"fase": "Movimentazione e stoccaggio", "doc_rif": "PRO 06 UNI EN 1090-2 (prosp. 8)", "applicabile": True},
    {"fase": "Taglio - Foratura (a freddo sega/trapano)", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": True},
    {"fase": "Taglio - Foratura lamiere/profili grigliati", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": False},
    {"fase": "Piegatura a freddo", "doc_rif": "Disegno n.{disegno} IO 02", "applicabile": False},
    {"fase": "Preparazione lembi di saldatura", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2", "applicabile": True},
    {"fase": "Puntatura lembi ed attacchi temporanei", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2", "applicabile": True},
    {"fase": "Esecuzione ed accettabilita' saldatura", "doc_rif": "Disegno n.{disegno} IO 02 WPS N. Norma 3834-2 Registro Saldatura", "applicabile": True},
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
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")
    disegno = pc_data.get("disegno_numero", "")
    ordine_num = pc_data.get("ordine_numero", comm_num)
    redatto_da = pc_data.get("redatto_da", "")
    fasi = pc_data.get("fasi", [])

    rows = ""
    for i, f in enumerate(fasi, 1):
        fase = f.get("fase", "")
        doc_rif = f.get("doc_rif", "").replace("{disegno}", disegno)
        applicabile = f.get("applicabile", True)
        periodo = f.get("periodo_pianificato", "") if applicabile else ""
        ctrl_verb = f.get("controllo_verbale", "") if applicabile else ""
        esito = f.get("esito", "")
        data_firma = f.get("data_effettiva", "") if applicabile else ""

        if not applicabile:
            esito_html = '<span style="color:#999;">N/A</span>'
        elif esito == "positivo":
            esito_html = f'{_chk(True)} Pos {_chk(False)} Neg'
        elif esito == "negativo":
            esito_html = f'{_chk(False)} Pos {_chk(True)} Neg'
        else:
            esito_html = f'{_chk(False)} Pos {_chk(False)} Neg'

        bg = 'style="background:#f5f5f5;"' if not applicabile else ''
        rows += f'<tr {bg}><td style="text-align:center;width:4%;">{i}</td><td style="text-align:left;width:22%;">{fase}</td><td style="font-size:7pt;width:22%;">{doc_rif}</td><td style="text-align:center;width:10%;">{periodo}</td><td style="text-align:center;width:10%;">{ctrl_verb}</td><td style="text-align:center;width:14%;">{esito_html}</td><td style="text-align:center;width:18%;">{data_firma}</td></tr>'

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    @page {{ size: A4 landscape; margin: 10mm 8mm; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email, "Piano di Controllo Qualita'", 'MOD. 02 Rev. 00', logo)}
    <table class="info-table" style="margin-top:4px;">
        <tr><td class="info-lbl">Cliente:</td><td>{client_name}</td><td class="info-lbl">Commessa N.:</td><td>{comm_num}</td></tr>
        <tr><td class="info-lbl">Descrizione Lavoro:</td><td>{comm_title}</td><td class="info-lbl">Ordine N.:</td><td>{ordine_num}</td></tr>
        <tr><td class="info-lbl">Classe Esecuzione:</td><td>{classe_exec}</td><td class="info-lbl">Redatto da:</td><td>{redatto_da}</td></tr>
    </table>
    <table class="main">
        <thead><tr>
            <th style="width:4%">N.</th>
            <th style="width:22%">Fase da Controllare</th>
            <th style="width:22%">Documenti di Riferimento</th>
            <th style="width:10%">Periodo Pianif.</th>
            <th style="width:10%">Controllo Verb. N.</th>
            <th style="width:14%">Esito</th>
            <th style="width:18%">Data Effettiva / Firma</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Data e Firma per Emissione</div>{_firma_img_html(firma)}<div class="sign-line"></div></div>
        <div class="sign-box"><div class="sign-label">Data e Firma per Approvazione</div><div class="sign-line"></div></div>
    </div>
    <div class="footer-mod">MOD. 02 Rev. 00 | {biz}</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 4. Rapporto VT — Esame Visivo Dimensionale (MOD. 06)
# ══════════════════════════════════════════════════════════════
def generate_rapporto_vt_pdf(company: dict, commessa: dict, client_name: str, vt_data: dict) -> BytesIO:
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")
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

    visione = vt_data.get("condizioni_visione", {})
    superficie = vt_data.get("stato_superficie", {})
    ispezione = vt_data.get("tipo_ispezione", {})
    attrezzatura = vt_data.get("attrezzatura", {})
    dist_max = vt_data.get("distanza_max_mm", "600")
    angolo_min = vt_data.get("angolo_min_gradi", "30")
    tipo_illuminatore = vt_data.get("tipo_illuminatore", "LUX")
    calibro_info = vt_data.get("calibro_info", "")

    oggetti = vt_data.get("oggetti_controllati", [])
    ogg_rows = ""
    for o in oggetti:
        esito_str = o.get("esito", "")
        ogg_rows += f'<tr><td style="text-align:center;">{o.get("numero","")}</td><td>{o.get("disegno","")}</td><td>{o.get("marca","")}</td><td>{o.get("dimensioni","")}</td><td style="text-align:center;">{o.get("estensione_controllo","100")}%</td><td style="text-align:center;font-weight:600;">{esito_str}</td></tr>'
    if not oggetti:
        ogg_rows = '<tr><td colspan="6" style="text-align:center;color:#999;padding:8px;">Nessun oggetto controllato — compilare manualmente</td></tr>'

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    .params {{ width:100%; border-collapse:collapse; margin:4px 0; }}
    .params td {{ padding:3px 6px; font-size:8.5pt; border:1px solid #000; }}
    .params .plbl {{ font-weight:700; background:#f0f0f0; width:22%; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email, 'Rapporto di Esame Visivo - Dimensionale', 'MOD. 06 Rev. 0', logo)}
    <p style="text-align:center;font-size:8pt;margin:2px 0;">Report VT N. {report_num} — Data: {report_data}</p>

    <table class="params">
        <tr><td class="plbl">Cliente:</td><td>{client_name}</td><td class="plbl">Commessa / Ordine:</td><td>{comm_num}</td></tr>
        <tr><td class="plbl">DWG N.:</td><td>{disegno}</td><td class="plbl">Classe Esecuzione:</td><td>{classe_exec}</td></tr>
        <tr><td class="plbl">Oggetto:</td><td colspan="3">{comm_title}</td></tr>
        <tr><td class="plbl">Processo saldatura:</td><td>{processo_saldatura}</td><td class="plbl">Norma / Procedura:</td><td>{norma_procedura}</td></tr>
        <tr><td class="plbl">Accettabilita':</td><td>{accettabilita}</td><td class="plbl">Materiale:</td><td>{materiale}</td></tr>
        <tr><td class="plbl">Temp. pezzo:</td><td>{temp_pezzo}</td><td class="plbl">Profilato:</td><td>{profilato}</td></tr>
        <tr><td class="plbl">Spessore:</td><td>{spessore}</td><td class="plbl"></td><td></td></tr>
    </table>

    <table class="params">
        <tr><td class="plbl">Condizioni di visione:</td>
            <td>{_chk(visione.get('naturale'))} Naturale {_chk(visione.get('artificiale'))} Artificiale {_chk(visione.get('lampada_wood'))} Lamp. Wood</td>
            <td class="plbl">Tipo illuminatore:</td><td>{tipo_illuminatore}</td></tr>
        <tr><td class="plbl">Stato superficie:</td>
            <td colspan="3">{_chk(superficie.get('come_saldato'))} Come saldato {_chk(superficie.get('molato'))} Molato {_chk(superficie.get('spazzolato'))} Spazzolato {_chk(superficie.get('lavorato_macchina'))} Lav. macchina {_chk(superficie.get('come_laminato'))} Come laminato {_chk(superficie.get('verniciato'))} Verniciato</td></tr>
        <tr><td class="plbl">Tipo ispezione:</td>
            <td>{_chk(ispezione.get('diretto'))} Diretto {_chk(ispezione.get('remoto'))} Remoto {_chk(ispezione.get('generale'))} Generale {_chk(ispezione.get('locale'))} Locale</td>
            <td class="plbl">Dist. max / Angolo min:</td><td>{dist_max} mm / {angolo_min}&deg;</td></tr>
        <tr><td class="plbl">Attrezzatura:</td>
            <td colspan="3">{_chk(attrezzatura.get('calibro'))} Calibro {_chk(attrezzatura.get('specchio'))} Specchio {_chk(attrezzatura.get('lente'))} Lente {_chk(attrezzatura.get('endoscopio'))} Endoscopio {_chk(attrezzatura.get('fotocamera'))} Fotocamera {_chk(attrezzatura.get('videocamera'))} Videocamera</td></tr>
        <tr><td class="plbl">Marca/Modello/Matricola:</td><td colspan="3">{calibro_info}</td></tr>
    </table>

    <div class="section-title">Oggetto Controllato</div>
    <table class="main">
        <thead><tr><th>N.</th><th>Disegno</th><th>Marca</th><th>Dimensioni</th><th>Estens. Ctrl (%)</th><th>Esito</th></tr></thead>
        <tbody>{ogg_rows}</tbody>
    </table>

    <table class="params" style="margin-top:6px;">
        <tr><td class="plbl">Note:</td><td colspan="3">{vt_data.get('note','')}</td></tr>
    </table>

    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Resp. Controllo VT</div>{_firma_img_html(firma)}<div class="sign-line"></div></div>
        <div class="sign-box"><div class="sign-label">Coordinatore della Saldatura</div><div class="sign-line"></div></div>
    </div>
    <div class="footer-mod">MOD. 06 Rev. 0 | {biz}</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 5. Registro di Saldatura (MOD. 04) — Fedele all'originale
# ══════════════════════════════════════════════════════════════
DEFAULT_SALDATURE = []

def generate_registro_saldatura_pdf(company: dict, commessa: dict, client_name: str, rs_data: dict) -> BytesIO:
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    data_emissione = rs_data.get("data_emissione", "")
    firma_cs = rs_data.get("firma_cs", "")
    perc_vt = rs_data.get("perc_vt", "100")
    perc_mt_pt = rs_data.get("perc_mt_pt", "0")
    perc_rx_ut = rs_data.get("perc_rx_ut", "0")
    saldature = rs_data.get("saldature", [])

    rows = ""
    for s in saldature:
        vt_esito = s.get("vt_esito", "")
        rows += f"""<tr>
            <td>{s.get('numero_disegno','')}</td>
            <td style="font-size:6.5pt;text-align:left;padding-left:2px;">{s.get('numero_saldatura','')}</td>
            <td>{s.get('periodo','')}</td>
            <td>{s.get('saldatore','')}</td>
            <td>{s.get('punzone','')}</td>
            <td>{s.get('diametro','')}</td>
            <td>{s.get('spessore','')}</td>
            <td>{s.get('materiale_base','')}</td>
            <td>{s.get('wps_numero','')}</td>
            <td>{vt_esito}</td>
            <td>{s.get('vt_data','')}</td>
            <td>{s.get('vt_firma','')}</td>
            <td>{s.get('cnd_tipo','')}</td>
            <td>{s.get('cnd_rapporto','')}</td>
            <td>{s.get('cnd_data','')}</td>
            <td>{s.get('cnd_firma','')}</td>
            <td>{s.get('cnd_tratto','')}</td>
            <td>{s.get('rip_rapporto','')}</td>
            <td>{s.get('rip_esito','')}</td>
            <td>{s.get('rip_data','')}</td>
        </tr>"""

    if not saldature:
        # Aggiungi righe vuote editabili
        for _ in range(10):
            rows += '<tr>' + '<td style="height:20px;">&nbsp;</td>' * 20 + '</tr>'

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: A4 landscape; margin: 8mm 6mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Calibri, Arial, sans-serif; font-size: 9pt; color: #000; margin: 0; padding: 0; }}
    .header-table {{ width: 100%; border-collapse: collapse; border: 2px solid #000; }}
    .header-table td {{ padding: 4px 8px; vertical-align: middle; }}
    .logo-cell {{ width: 25%; text-align: center; border-right: 1px solid #000; }}
    .title-cell {{ width: 50%; text-align: center; font-size: 14pt; font-weight: 700; text-transform: uppercase; }}
    .meta-cell {{ width: 25%; border-left: 1px solid #000; font-size: 8pt; }}
    .co-name {{ font-size: 11pt; font-weight: 700; color: #1a3a6b; }}
    .co-sub {{ font-size: 7pt; color: #444; }}
    .info-row {{ width: 100%; border-collapse: collapse; border: 1px solid #000; margin-top: 0; border-top: 0; }}
    .info-row td {{ padding: 3px 6px; font-size: 8.5pt; border: 1px solid #000; }}
    .info-lbl {{ font-weight: 700; background: #f0f0f0; }}
    .perc-box {{ display: inline-block; border: 1px solid #000; padding: 1px 8px; margin: 0 6px; font-weight: 700; font-size: 8.5pt; }}
    table.rs {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
    table.rs th {{ font-size: 6.5pt; padding: 2px 1px; font-weight: 700; text-align: center; border: 1px solid #000; background: #f0f0f0; }}
    table.rs td {{ font-size: 7pt; padding: 2px 2px; text-align: center; border: 1px solid #000; }}
    .group-header {{ background: #d9d9d9 !important; font-weight: 700; }}
    .footer-mod {{ font-size: 7pt; color: #555; margin-top: 4px; }}
    </style></head><body>
    <table class="header-table">
        <tr>
            <td class="logo-cell">{'<img src="' + logo + '" style="max-height:35px;max-width:100%;" /><br/>' if logo else ''}<div class="co-name">{biz}</div><div class="co-sub">{addr}</div></td>
            <td class="title-cell">Registro di Saldatura</td>
            <td class="meta-cell">Data di emissione: {data_emissione}<br/>Firma CS: {firma_cs}{_firma_img_html(firma)}</td>
        </tr>
    </table>
    <table class="info-row">
        <tr><td class="info-lbl" style="width:10%;">COMMESSA</td><td style="width:15%;">{comm_num}</td>
            <td class="info-lbl" style="width:8%;">CLIENTE</td><td style="width:27%;">{client_name}</td>
            <td class="info-lbl" style="width:15%;">DESCRIZIONE LAVORO</td><td style="width:25%;">{comm_title}</td></tr>
    </table>
    <div style="margin:4px 0;font-size:8.5pt;border:1px solid #000;padding:3px 6px;">
        % CONTROLLI: <span class="perc-box">VT {perc_vt}%</span> <span class="perc-box">MT/PT {perc_mt_pt}%</span> <span class="perc-box">RX-RY/UT {perc_rx_ut}%</span>
    </div>
    <table class="rs">
        <thead>
        <tr>
            <th rowspan="2" style="width:5%;">NUMERO<br/>DISEGNO</th>
            <th rowspan="2" style="width:8%;">NUMERO<br/>SALDATURA</th>
            <th rowspan="2" style="width:4%;">PERIOD</th>
            <th rowspan="2" style="width:6%;">SALDATORE</th>
            <th rowspan="2" style="width:4%;">Punzone</th>
            <th rowspan="2" style="width:3%;">DIAM.</th>
            <th rowspan="2" style="width:3%;">SPESS.</th>
            <th rowspan="2" style="width:6%;">Tipo<br/>Materiale<br/>Base</th>
            <th rowspan="2" style="width:4%;">WPS<br/>N&deg;</th>
            <th colspan="3" class="group-header" style="width:12%;">VISUAL TEST</th>
            <th colspan="5" class="group-header" style="width:18%;">CND</th>
            <th colspan="3" class="group-header" style="width:12%;">RIPARAZIONE</th>
        </tr>
        <tr>
            <th>ESITO</th><th>Data</th><th>Firma</th>
            <th>Tipo</th><th>Rapporto N.</th><th>Data</th><th>Firma</th><th>Tratto</th>
            <th>Rapporto N.</th><th>ESITO</th><th>Data</th>
        </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <div class="footer-mod">MOD. 04 Rev. 0 | {biz} | Pagina 1</div>
    </body></html>"""
    return _render(html)


# ══════════════════════════════════════════════════════════════
# 6. Riesame Tecnico (MOD. 01) — Fedele all'originale (3 pagine)
# ══════════════════════════════════════════════════════════════
DEFAULT_REQUISITI = [
    {"requisito": "E' stata definita, in accordo con il Cliente, la classe di esecuzione della commessa?", "note_default": ""},
    {"requisito": "L'officina, per attrezzature e capacita' di lavoro, e' idonea per la commessa?", "note_default": ""},
    {"requisito": "E' stato definito il materiale base per la commessa?", "note_default": ""},
    {"requisito": "Sono state definite le tolleranze da applicare secondo la norma UNI EN 1090-2?", "note_default": "Tolleranza secondo UNI 1090-2 B6 Taglio - B8 Foratura"},
    {"requisito": "Sono definite le caratteristiche del giunto saldato?", "note_default": ""},
    {"requisito": "Sono definiti requisiti per i criteri di accettabilita' delle saldature?", "note_default": ""},
    {"requisito": "E' definita la posizione delle saldature?", "note_default": ""},
    {"requisito": "E' definita la sequenza delle saldature?", "note_default": ""},
    {"requisito": "E' definita l'accessibilita' delle saldature, inclusa l'accessibilita' per le ispezioni e CND?", "note_default": ""},
    {"requisito": "Le WPQR coprono le caratteristiche delle saldature di questa commessa?", "note_default": ""},
    {"requisito": "Sono disponibili le procedure per i CND?", "note_default": ""},
    {"requisito": "Sono disponibili procedure per il trattamento termico?", "note_default": ""},
    {"requisito": "La qualifica del personale copre le caratteristiche delle saldature di questa commessa?", "note_default": "Elenco Saldatori"},
    {"requisito": "Le WPS emesse coprono le caratteristiche di questa commessa?", "note_default": ""},
    {"requisito": "E' prevista la registrazione della rintracciabilita' di materiali e saldature?", "note_default": "Registro di saldatura - scheda rintracciabilita'"},
    {"requisito": "E' previsto l'intervento di ente terzo?", "note_default": ""},
    {"requisito": "Sono previsti sub-fornitori nel processo? (CND, zincatura, trattamento termico)", "note_default": ""},
    {"requisito": "Sono previsti CND supplementari in accordo al prospetto 24 della ISO 1090-2?", "note_default": ""},
    {"requisito": "E' stato emesso un PCQ specifico?", "note_default": ""},
    {"requisito": "Sono previsti trattamenti termici dopo la saldatura?", "note_default": ""},
    {"requisito": "Sono previsti trattamenti superficiali? (specificare spessore se verniciatura)", "note_default": ""},
    {"requisito": "E' stato definito il grado di preparazione della superficie e quindi la durabilita'?", "note_default": ""},
    {"requisito": "Sono presenti altri requisiti per la saldatura?", "note_default": ""},
    {"requisito": "Sono previsti metodi particolari per la saldatura?", "note_default": ""},
    {"requisito": "Sono definiti dimensioni e dettagli della preparazione dei giunti saldati?", "note_default": ""},
    {"requisito": "Le saldature sono fatte tutte in officina?", "note_default": ""},
    {"requisito": "Le condizioni ambientali di saldatura sono accettabili?", "note_default": ""},
    {"requisito": "E' prevista la registrazione e gestione delle Non Conformita' e riparazioni?", "note_default": "Procedure Pro 07"},
]

DEFAULT_ITT = [
    {"caratteristica": "Tolleranza delle dimensioni e della forma", "metodo": "Appendice B UNI EN 1090-2 e disegni", "criterio": "EN 1090-1:2012 secondo 5.3"},
    {"caratteristica": "Saldabilita'", "metodo": "Certificati materiale base 3.1", "criterio": "EN 1090-1:2012 secondo 5.4"},
    {"caratteristica": "Resistenza alla rottura / Resistenza all'urto", "metodo": "Certificati materiale base 3.1", "criterio": "EN 1090-1:2012 secondo 5.5 e 5.10"},
    {"caratteristica": "Capacita' portante", "metodo": "Progetto esecutivo fornito dal Cliente", "criterio": ""},
    {"caratteristica": "Deformazione allo stato limite di esercizio", "metodo": "Progetto esecutivo fornito dal Cliente", "criterio": ""},
    {"caratteristica": "Resistenza alla fatica", "metodo": "Progetto esecutivo fornito dal Cliente", "criterio": ""},
    {"caratteristica": "Resistenza al fuoco", "metodo": "Progetto esecutivo fornito dal Cliente", "criterio": ""},
    {"caratteristica": "Reazione al fuoco", "metodo": "Certificati materiale base 3.1", "criterio": "EN 1090-1:2012 secondo 5.8"},
    {"caratteristica": "Sostanze pericolose", "metodo": "", "criterio": ""},
    {"caratteristica": "Durabilita'", "metodo": "Grado di finitura EN 1090-2 appendice F", "criterio": "EN 1090-1:2012 secondo 5.11"},
]

def generate_riesame_tecnico_pdf(company: dict, commessa: dict, client_name: str, rt_data: dict) -> BytesIO:
    biz, addr, piva, phone, email, logo, firma = _co(company)
    comm_num = commessa.get("numero", "")
    comm_title = commessa.get("title", "")
    classe_exec = commessa.get("classe_esecuzione", "EXC2")

    requisiti = rt_data.get("requisiti", [])
    if not requisiti:
        requisiti = [{"requisito": r["requisito"], "risposta": "si", "note": r["note_default"]} for r in DEFAULT_REQUISITI]

    req_rows = ""
    for r in requisiti:
        risp = r.get("risposta", "")
        si_chk = _chk(risp == "si")
        no_chk = _chk(risp == "no")
        na_chk = _chk(risp == "na")
        req_rows += f'<tr><td style="text-align:left;font-size:8pt;padding:3px 4px;">{r.get("requisito","")}</td><td style="text-align:center;">{si_chk}</td><td style="text-align:center;">{no_chk}</td><td style="text-align:center;">{na_chk}</td><td style="text-align:left;font-size:7.5pt;">{r.get("note","")}</td></tr>'

    # ITT table
    itt_items = rt_data.get("itt", [])
    if not itt_items:
        itt_items = [dict(c) for c in DEFAULT_ITT]
    itt_rows = ""
    for item in itt_items:
        esito = item.get("esito_conformita", "")
        itt_rows += f'<tr><td style="text-align:left;">{item.get("caratteristica","")}</td><td style="text-align:left;font-size:7.5pt;">{item.get("metodo","")}</td><td style="text-align:center;">{esito}</td><td style="font-size:7.5pt;">{item.get("criterio","")}</td></tr>'

    decisione = rt_data.get("decisione", "procedere")
    proc_chk = _chk(decisione == "procedere")
    non_proc_chk = _chk(decisione == "non_procedere")

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}
    @page {{ size: A4; margin: 10mm 12mm; }}
    </style></head><body>
    {_header_html(biz, addr, piva, phone, email, 'Riesame Tecnico', 'MOD. 01 Rev. 00', logo)}
    <table class="info-table" style="margin-top:4px;">
        <tr><td class="info-lbl">Cliente:</td><td>{client_name}</td><td class="info-lbl">Commessa:</td><td>{comm_num}</td></tr>
        <tr><td class="info-lbl">Descrizione del Lavoro:</td><td colspan="3">{comm_title}</td></tr>
        <tr><td class="info-lbl">Classe Esecuzione:</td><td>{classe_exec}</td><td class="info-lbl">Redatto da:</td><td>{rt_data.get('redatto_da','')}</td></tr>
    </table>
    <table class="main" style="margin-top:4px;">
        <thead><tr>
            <th style="width:42%;text-align:left;padding-left:4px;">Requisiti</th>
            <th style="width:5%">Si</th><th style="width:5%">No</th><th style="width:5%">N.A.</th>
            <th style="width:43%;text-align:left;padding-left:4px;">Note / Riferimenti documentali</th>
        </tr></thead>
        <tbody>{req_rows}</tbody>
    </table>

    <div style="margin:12px 0;padding:8px 12px;border:2px solid #000;">
        <p style="font-size:10pt;font-weight:700;margin:0 0 6px 0;">Analisi di Fattibilita' Tecnica</p>
        <p style="font-size:9pt;margin:2px 0;">Sulla base dell'analisi di cui sopra si decide di:</p>
        <p style="font-size:11pt;margin:6px 0;">{proc_chk} <strong>PROCEDERE</strong> &nbsp;&nbsp;&nbsp;&nbsp; {non_proc_chk} <strong>NON PROCEDERE</strong></p>
        <p style="font-size:9pt;margin:2px 0;">alla Pianificazione delle lavorazioni dell'Officina.</p>
        <div class="sign-area" style="margin-top:8px;">
            <div class="sign-box"><div class="sign-label">Data</div><div class="sign-line"></div></div>
            <div class="sign-box"><div class="sign-label">Firma CS</div><div class="sign-line"></div></div>
        </div>
    </div>

    <div style="page-break-before:always;"></div>
    {_header_html(biz, addr, piva, phone, email, 'ITT di Commessa', 'MOD. 01 Rev. 00')}
    <table class="info-table" style="margin-top:4px;">
        <tr><td class="info-lbl">Commessa:</td><td>{comm_num}</td><td class="info-lbl">Cliente:</td><td>{client_name}</td></tr>
    </table>
    <table class="main" style="margin-top:6px;">
        <thead><tr>
            <th style="width:22%;text-align:left;padding-left:4px;">CARATTERISTICA ESSENZIALE</th>
            <th style="width:28%;text-align:left;padding-left:4px;">METODO DI PROVA</th>
            <th style="width:22%;text-align:left;padding-left:4px;">ESITO DI CONFORMITA'</th>
            <th style="width:28%;text-align:left;padding-left:4px;">CRITERIO DI CONFORMITA'</th>
        </tr></thead>
        <tbody>{itt_rows}</tbody>
    </table>
    <p style="font-size:7.5pt;color:#555;margin-top:6px;">Note: Allegare report delle prove dimensionali, scheda rintracciabilita' materiali e relativi certificati dei materiali</p>
    
    <div style="margin-top:12px;border:1px solid #000;padding:6px;">
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="width:20%;font-weight:700;border:1px solid #000;padding:4px;text-align:center;">Esito PROVE ITT</td>
                <td style="width:15%;border:1px solid #000;padding:4px;text-align:center;">C (Conforme)</td>
                <td style="width:15%;border:1px solid #000;padding:4px;text-align:center;">NC (Non Conforme)</td>
                <td style="width:25%;border:1px solid #000;padding:4px;">Firma:</td>
                <td style="width:25%;border:1px solid #000;padding:4px;">Data:</td>
            </tr>
        </table>
    </div>
    <div class="footer-mod">MOD. 01 Rev. 00 | {biz}</div>
    </body></html>"""
    return _render(html)

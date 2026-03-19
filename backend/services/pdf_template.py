"""PDF Template - NormaFacile 2.0 - HTML/CSS con xhtml2pdf"""
from io import BytesIO


def fmt_it(n) -> str:
    try:
        return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(n or "0,00")


def safe(val) -> str:
    if val is None:
        return ""
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_html(text: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', text or '')


def format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(date_str)[:10] if date_str else ""


CSS = """
@page {
    size: A4;
    margin: 15mm 18mm 18mm 18mm;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9.5px;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}
.header-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
}
.company-box {
    width: 50%;
    vertical-align: top;
    padding-right: 10px;
}
.client-box {
    width: 50%;
    vertical-align: top;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 8px 10px;
    border-radius: 3px;
}
.company-name {
    font-size: 13px;
    font-weight: bold;
    color: #1a56db;
    margin-bottom: 3px;
}
.company-detail {
    font-size: 8.5px;
    color: #555;
    line-height: 1.5;
}
.piva-bold {
    font-weight: bold;
    font-size: 9px;
}
.client-label {
    font-size: 8px;
    color: #888;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.client-name {
    font-size: 11px;
    font-weight: bold;
    color: #1E293B;
}
.client-detail {
    font-size: 8.5px;
    color: #555;
    line-height: 1.5;
}
.doc-title-bar {
    background: #1a56db;
    color: white;
    padding: 6px 12px;
    margin-bottom: 10px;
    display: table;
    width: 100%;
    box-sizing: border-box;
}
.doc-title {
    font-size: 13px;
    font-weight: bold;
    display: table-cell;
    vertical-align: middle;
}
.doc-number {
    font-size: 13px;
    font-weight: bold;
    display: table-cell;
    text-align: right;
    vertical-align: middle;
}
.meta-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 8.5px;
}
.meta-table td {
    padding: 2px 6px;
    vertical-align: top;
}
.meta-label {
    font-weight: bold;
    color: #555;
    width: 100px;
}
.lines-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 8.5px;
}
.lines-table th {
    background: #1E293B;
    color: white;
    padding: 4px 5px;
    text-align: left;
    font-size: 8px;
    font-weight: bold;
}
.lines-table th.tr { text-align: right; }
.lines-table th.tc { text-align: center; }
.lines-table td {
    padding: 4px 5px;
    border-bottom: 1px solid #e9ecef;
    vertical-align: top;
}
.lines-table tr:nth-child(even) td { background: #f8f9fa; }
.tc { text-align: center; }
.tr { text-align: right; }
.desc-cell { max-width: 200px; }
.totals-table {
    width: 220px;
    margin-left: auto;
    border-collapse: collapse;
    font-size: 9px;
    margin-bottom: 10px;
}
.totals-table td {
    padding: 2px 5px;
}
.totals-table .label { color: #555; }
.totals-table .value { text-align: right; font-family: monospace; }
.total-final {
    font-size: 11px;
    font-weight: bold;
    color: #1a56db;
    border-top: 2px solid #1a56db;
    padding-top: 3px;
}
.notes-box {
    background: #f8f9fa;
    border-left: 3px solid #1a56db;
    padding: 6px 10px;
    font-size: 8.5px;
    margin-bottom: 10px;
    color: #444;
}
.bank-box {
    background: #f0f4ff;
    border: 1px solid #c7d7ff;
    padding: 6px 10px;
    font-size: 8.5px;
    margin-bottom: 10px;
    border-radius: 3px;
}
.section-title {
    font-size: 9px;
    font-weight: bold;
    color: #1a56db;
    text-transform: uppercase;
    margin-bottom: 3px;
}
"""


def build_header_html(company: dict, client: dict, no_client_border: bool = False) -> str:
    co = company or {}
    cl = client or {}

    company_name = safe(co.get("business_name", ""))
    addr = safe(co.get("address", ""))
    cap = safe(co.get("cap", ""))
    city = safe(co.get("city", ""))
    prov = safe(co.get("province", ""))
    full_addr = addr
    if cap or city:
        parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
        full_addr += f" {' '.join(parts)}"
    piva = safe(co.get("partita_iva", ""))
    cf = safe(co.get("codice_fiscale", ""))
    phone = safe(co.get("phone") or co.get("tel", ""))
    email = safe(co.get("email") or co.get("contact_email", ""))

    cl_name = safe(cl.get("business_name", ""))
    cl_addr = safe(cl.get("address", ""))
    cl_cap = safe(cl.get("cap", ""))
    cl_city = safe(cl.get("city", ""))
    cl_prov = safe(cl.get("province", ""))
    cl_full = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full += f" {' '.join(parts)}"
    cl_piva = safe(cl.get("partita_iva", ""))
    cl_cf = safe(cl.get("codice_fiscale", ""))
    cl_sdi = safe(cl.get("codice_sdi", ""))
    cl_pec = safe(cl.get("pec", ""))
    cl_email = safe(cl.get("email", ""))

    return f"""
    <table class="header-table" style="width:100%; border-collapse:collapse; margin-bottom:12px;">
      <tr>
        <td class="company-box" style="width:50%; vertical-align:top; padding-right:10px;">
          {"<img src='" + safe(co.get('logo_url','')) + "' style='max-height:70px; max-width:180px; margin-bottom:6px;'><br>" if co.get('logo_url') else ""}
                    {co.get('logo_url','').__len__() > 0 and '<img src="' + co.get('logo_url','') + '" style="max-height:70px; max-width:180px; margin-bottom:4px; display:block;">' or ''}
          <div class="company-name" style="font-size:13px; font-weight:bold; color:#1a56db; margin-bottom:3px;">{company_name}</div>
          <div class="company-detail" style="font-size:8.5px; color:#555; line-height:1.5;">
            {full_addr}<br>
            {"<b>P.IVA: " + piva + "</b><br>" if piva else ""}
            {"Cod.Fisc.: " + cf + "<br>" if cf else ""}
            {"Tel: " + phone + "<br>" if phone else ""}
            {"Email: " + email if email else ""}
          </div>
        </td>
        <td class="client-box" style="width:50%; vertical-align:top; background:#f8f9fa; border:1px solid #dee2e6; padding:8px 10px;">
          <div style="font-size:8px; color:#888; text-transform:uppercase; margin-bottom:4px;">Spett.le</div>
          <div class="client-name" style="font-size:11px; font-weight:bold; color:#1E293B;"><strong>{cl_name}</strong></div>
          <div class="client-detail" style="font-size:8.5px; color:#555; line-height:1.5;">
            {cl_full}<br>
            {"<b>P.IVA: " + cl_piva + "</b><br>" if cl_piva else ""}
            {"Cod.Fisc.: " + cl_cf + "<br>" if cl_cf else ""}
            {"Cod.SDI: " + cl_sdi + "<br>" if cl_sdi else ""}
            {"PEC: " + cl_pec if cl_pec else ("Email: " + cl_email if cl_email else "")}
          </div>
        </td>
      </tr>
    </table>
    """


def compute_iva_groups(lines: list, sconto_globale: float = 0) -> dict:
    subtotal = sum(float(ln.get("line_total") or 0) for ln in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)
    groups = {}
    for ln in lines:
        rate_str = str(ln.get("vat_rate", "22"))
        base = float(ln.get("line_total") or 0)
        if sconto_globale and subtotal > 0:
            base = round(base * (1 - sconto_globale / 100), 2)
        if rate_str not in groups:
            groups[rate_str] = {"base": 0, "iva": 0}
        groups[rate_str]["base"] = round(groups[rate_str]["base"] + base, 2)
        groups[rate_str]["iva"] = round(groups[rate_str]["iva"] + base * float(rate_str) / 100, 2)
    return {
        "groups": groups,
        "subtotal": subtotal,
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "total_iva": round(sum(g["iva"] for g in groups.values()), 2),
        "total": round(imponibile + sum(g["iva"] for g in groups.values()), 2),
    }


def build_totals_html(iva_data: dict, acconto: float = 0) -> str:
    rows = ""
    if iva_data.get("sconto_val", 0) > 0:
        rows += f'<tr><td class="label">Totale senza IVA</td><td class="value">{fmt_it(iva_data["subtotal"])} &euro;</td></tr>'
        rows += f'<tr><td class="label">Sconto</td><td class="value">- {fmt_it(iva_data["sconto_val"])} &euro;</td></tr>'
    rows += f'<tr><td class="label">Imponibile</td><td class="value">{fmt_it(iva_data["imponibile"])} &euro;</td></tr>'
    for rate, g in iva_data.get("groups", {}).items():
        rows += f'<tr><td class="label">IVA {rate}%</td><td class="value">{fmt_it(g["iva"])} &euro;</td></tr>'
    rows += f'<tr><td class="label total-final">TOTALE</td><td class="value total-final">{fmt_it(iva_data["total"])} &euro;</td></tr>'
    if acconto:
        da_pagare = round(iva_data["total"] - acconto, 2)
        rows += f'<tr><td class="label">Acconto</td><td class="value">- {fmt_it(acconto)} &euro;</td></tr>'
        rows += f'<tr><td class="label total-final">DA PAGARE</td><td class="value total-final">{fmt_it(da_pagare)} &euro;</td></tr>'
    return f'<table class="totals-table">{rows}</table>'


def build_conditions_html(company: dict, doc_number: str) -> str:
    """Condizioni generali di fornitura - HTML hardcoded stile Invoicex."""
    company_name = (company or {}).get('business_name', 'Steel Project Design Srls')

    return (
        "<div style='page-break-before:always; font-family:Arial,sans-serif;"
        " font-size:9pt; color:#222; margin:0; padding:10px 15px;'>"
        "<h2 style='font-size:11pt; font-weight:bold; border-bottom:1px solid #ccc;"
        " padding-bottom:3px; margin-top:8px; margin-bottom:6px;'>"
        "CONDIZIONI GENERALI DI FORNITURA</h2>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>1 - Premessa</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal; text-align:justify;'>"
        "Ai fini del presente contratto i termini elencati qui di seguito avranno il seguente significato: "
        "Steel Project Design Srls: Steel Project Design Srls con sede legale in via dei Pioppi n. 11 - "
        "40010 Padulle BO). Acquirente: ogni persona fisica o giuridica o altro ente che acquisti o si "
        "impegni ad acquistare dalla Steel Project Design Srls i propri prodotti. Prodotti: ogni bene "
        "che sia commercializzato dalla Steel Project Design Srls.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>2 - Condizioni di fornitura</h3>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>a) Merce resa f.co Vs. cantiere/abitazione</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>b) Posa in opera: come descritto</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>c) Consegna: 75/90 giorni dalla data di accettazione.</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>d) I tempi di consegna sono indicativi e la mancata "
        "consegna non potr&agrave; dar luogo a rivalsa, n&eacute; diritto ad esigere indennizzi.</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>e) Finitura: come descritto</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>f) Pagamento: Acconto del 40% all&#39;ordine - "
        "saldo a fine lavori entro 7 giorni.</p>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>g) Validit&agrave; offerta: 15 giorni dalla "
        "data di emissione per l&#39;intero importo dei lavori (no frazionati)</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>3 - Oneri a carico del cliente</h3>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>a) Verifica dettagliata dei prodotti offerti</p>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>b) Verifica presso gli enti di competenza "
        "della necessit&agrave; di autorizzazione per l&#39;installazione</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>4 - Esclusioni dal preventivo</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>Sono da ritenersi escluse: Trasporto se non "
        "espressamente indicato, Scarico e smistamento, Opere murarie, Modifiche successive alla conferma "
        "d&#39;ordine, Impalcature e ponteggi, Energia elettrica, Agibilit&agrave; nella zona di lavoro, "
        "Oneri per suolo pubblico, Custodia materiali, Pulizia infissi, Smaltimento imballi.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>5 - Pagamenti</h3>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>a) La mancata effettuazione di un pagamento "
        "autorizza la Steel Project Design Srls a sospendere ogni consegna.</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>b) Il mancato rispetto dei termini di pagamento "
        "determiner&agrave; l&#39;automatica risoluzione del contratto.</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>c) In caso di pagamento dilazionato, la merce "
        "si intende di propriet&agrave; della Ditta venditrice sino al completo pagamento (art. 1523 C.C.).</p>"
        "<p style='margin:2px 0 2px 0; font-weight:normal;'>d) In caso di ritardo l&#39;Acquirente "
        "riconoscer&agrave; gli interessi (Direttiva Europea n. 2000/35 - D.L. n. 231/2002).</p>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>e) Se per responsabilit&agrave; del cliente "
        "la merce non verr&agrave; ritirata entro 5 gg saranno addebitati euro 15,00 +IVA a bancale/giorno.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>6 - Garanzia</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>&Egrave; esclusa la garanzia per i vizi dei "
        "prodotti venduti. Eventuali contestazioni vanno comunicate per iscritto entro otto giorni dal "
        "ricevimento/montaggio della merce.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>7 - Varianti in corso d&#39;opera</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>Le varianti richieste in corso d&#39;opera "
        "verranno preventivate ed eseguite dopo conferma scritta del Committente.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>8 - Controversie</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>Luogo dell&#39;adempimento &egrave; sempre "
        "la sede della Steel Project Design Srls.</p>"

        "<h3 style='font-size:9.5pt; font-weight:bold; margin-top:10px; margin-bottom:2px;'>9 - Foro competente</h3>"
        "<p style='margin:2px 0 6px 0; font-weight:normal;'>Foro competente Bologna (BO)</p>"

        "<div style='margin-top:25px; border-top:1px solid #aaa; padding-top:12px;'>"
        "<p style='font-weight:normal; margin-bottom:20px;'>Firma e timbro per accettazione"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; data di accettazione ___/___/___</p>"
        "<p style='font-weight:normal;'>(legale rappresentante)</p>"
        "<p style='font-weight:normal; margin-top:5px;'>__________________________</p>"
        "</div>"

        "<div style='margin-top:20px; border:1px solid #ccc; padding:8px; background:#f9f9f9;"
        " font-size:8.5pt; font-style:italic; font-weight:normal;'>"
        "Ai sensi e per gli effetti dell&#39;Art. 1341 e segg. del Codice Civile, il sottoscritto "
        "Acquirente dichiara di aver preso specifica, precisa e dettagliata visione di tutte le "
        "disposizioni del contratto: 1 Premessa; 2 Condizioni di fornitura; 3 Oneri a carico del "
        "cliente; 4 Esclusioni dal preventivo; 5 Pagamenti; 6 Garanzia; 7 Varianti in corso "
        "d&#39;opera; 8 Controversie e di approvarle integralmente senza alcuna riserva."
        "</div>"

        "<p style='margin-top:20px; font-weight:normal;'>_____________________, l&igrave; ______________________</p>"
        "<p style='font-weight:normal; margin-top:5px;'><strong>Firma e timbro (il legale rappresentante)</strong></p>"
        "<p style='font-weight:normal; margin-top:5px;'>_____________________________</p>"
        "</div>"
    )


def render_pdf(html_content: str) -> BytesIO:
    """Render PDF Invoicex - v6 con fix duplicati header e totali."""
    import base64 as _b64, re as _re
    import html as _hmod
    from copy import deepcopy
    from lxml import html as _lhtml
    from reportlab.lib import colors as _col
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image, PageBreak, HRFlowable)
    from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

    def _di(s):
        try:
            if "base64," in s: s = s.split("base64,")[1]
            return BytesIO(_b64.b64decode(s))
        except: return None

    def _c(t):
        t = str(t or '')
        for a,b in [
            ('\u00e2\u0080\u0099',"'"),('\u00e2\u0080\u009c','"'),('\u00e2\u0080\u009d','"'),
            ('\u00e2\u0080\u0093','\u2013'),('\u00e2\u0080\u0094','\u2014'),
            ('\u00c3\u00a0','\u00e0'),('\u00c3\u00a8','\u00e8'),('\u00c3\u00a9','\u00e9'),
            ('\u00c3\u00ac','\u00ec'),('\u00c3\u00b2','\u00f2'),('\u00c3\u00b9','\u00f9'),
            ('&amp;','&'),('&nbsp;',' '),('&lt;','<'),('&gt;','>'),
        ]: t = t.replace(a,b)
        return _hmod.unescape(t).strip()

    def _tx(el):
        if el is None: return ''
        return _c(' '.join(el.itertext()))

    def _bl(el):
        if el is None: return []
        el2 = deepcopy(el)
        for br in el2.iter('br'): br.tail = '\n'+(br.tail or '')
        return [_c(l) for l in '\n'.join(el2.itertext()).split('\n') if _c(l)]

    def P(t,s):
        t=_c(str(t or ''))
        return Paragraph(t.replace('\n','<br/>'),s) if t else Spacer(1,1)

    def f1(el,xp):
        r=el.xpath(xp); return r[0] if r else None

    if isinstance(html_content,bytes): html_content=html_content.decode('utf-8')
    root=_lhtml.fromstring('<div class="nr">'+html_content+'</div>')

    BLUE=_col.HexColor('#1a56db'); LGRAY=_col.HexColor('#f3f4f6')
    BRD=_col.HexColor('#d1d5db'); WHITE=_col.white; BLACK=_col.black; GTXT=_col.HexColor('#6B7280')
    W=A4[0]-3.0*cm
    ss=getSampleStyleSheet()
    def S(n,**k): return ParagraphStyle(n,parent=ss['Normal'],**k)
    N   =S('N',  fontSize=8.5,leading=11)
    B   =S('B',  fontSize=8.5,leading=11,fontName='Helvetica-Bold')
    SM  =S('SM', fontSize=7.5,leading=10,textColor=GTXT)
    CO  =S('CO', fontSize=11, leading=14,fontName='Helvetica-Bold')
    CL  =S('CL', fontSize=10, leading=13,fontName='Helvetica-Bold')
    BIG =S('BIG',fontSize=15, leading=19,fontName='Helvetica-Bold')
    TH  =S('TH', fontSize=8,  leading=10,fontName='Helvetica-BoldOblique',textColor=BLACK)
    THR =S('THR',fontSize=8,  leading=10,fontName='Helvetica-BoldOblique',textColor=BLACK,alignment=TA_RIGHT)
    TD  =S('TD', fontSize=8.5,leading=11)
    TDR =S('TDR',fontSize=8.5,leading=11,alignment=TA_RIGHT)
    TDC =S('TDC',fontSize=8.5,leading=11,alignment=TA_CENTER)
    TL  =S('TL', fontSize=8.5,leading=11,textColor=GTXT)
    TV  =S('TV', fontSize=8.5,leading=11,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    GL  =S('GL', fontSize=10, leading=13,fontName='Helvetica-Bold')
    GV  =S('GV', fontSize=10, leading=13,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    ML  =S('ML', fontSize=7.5,leading=10,fontName='Helvetica-Bold',textColor=GTXT)
    MV  =S('MV', fontSize=8.5,leading=11)
    CLI =S('CLI',fontSize=8,  leading=10,fontName='Helvetica-Oblique',textColor=GTXT)
    FT  =S('FT', fontSize=7,  leading=9, textColor=GTXT)
    FTR =S('FTR',fontSize=7,  leading=9, textColor=GTXT,alignment=TA_RIGHT)
    BLB =S('BLB',fontSize=9,  leading=12,fontName='Helvetica-Bold',textColor=BLUE)
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=1.5*cm,leftMargin=1.5*cm,topMargin=1.5*cm,bottomMargin=2.0*cm)
    els=[]

    # 1 HEADER - prende SOLO il primo company-box e client-box
    co_box=f1(root,".//td[@class='company-box']")
    cl_box=f1(root,".//td[@class='client-box']")
    logo=None
    if co_box is not None:
        srcs=co_box.xpath('.//img/@src')
        if srcs:
            s=_di(srcs[0])
            if s:
                try: _ir = ImageReader(s); _iw, _ih = _ir.getSize(); s.seek(0)
                    _tw = 5.0*cm; _th = _tw * _ih / _iw
                    logo = Image(s, width=_tw, height=_th)
                except: pass
    co_col=[]
    if logo: co_col.append(logo)
    if co_box is not None:
        cn=f1(co_box,".//div[@class='company-name']"); cd=f1(co_box,".//div[@class='company-detail']")
        if cn: co_col.append(Paragraph(_tx(cn),CO))
        if cd:
            for l in _bl(cd): co_col.append(Paragraph(l,B if('P.IVA' in l or 'Cod.Fisc' in l) else SM))
    if not co_col: co_col=[Spacer(1,1)]
    cl_col=[Paragraph('Cliente',CLI)]
    if cl_box is not None:
        cn=f1(cl_box,".//div[@class='client-name']"); cd=f1(cl_box,".//div[@class='client-detail']")
        if cn: cl_col.append(Paragraph(_tx(cn),CL))
        if cd:
            for l in _bl(cd): cl_col.append(Paragraph(l,B if('P.IVA' in l or 'Cod.Fisc' in l) else SM))
    hdr=Table([[co_col,cl_col]],colWidths=[W*0.52,W*0.46])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),
        ('RIGHTPADDING',(0,0),(0,0),6),('LEFTPADDING',(1,0),(1,0),8),('TOPPADDING',(1,0),(1,0),6),
        ('BOTTOMPADDING',(1,0),(1,0),6),('BACKGROUND',(1,0),(1,0),LGRAY),('BOX',(1,0),(1,0),0.5,BRD)]))
    els+=[hdr,Spacer(1,8)]

    # 2 META - prende SOLO la prima meta-table e il primo doc-title
    td=f1(root,".//div[@class='doc-title']"); dt=''; dn=''
    if td:
        h1=f1(td,'.//h1'); dnx=f1(td,".//*[@class='doc-num']")
        if h1: dt=_tx(h1)
        if dnx: dn=_tx(dnx)
    mt=f1(root,".//table[@class='meta-table']"); mv={}
    if mt:
        for tr in mt.xpath('.//tr'):
            tds=tr.xpath('./td'); i=0
            while i<len(tds)-1:
                k=_tx(tds[i]).rstrip(':').strip(); v=_tx(tds[i+1]).strip()
                if k and v: mv[k]=v
                i+=2
    cl_piva=''
    if cl_box is not None:
        cd=f1(cl_box,".//div[@class='client-detail']")
        if cd:
            for l in _bl(cd):
                if 'P.IVA' in l or 'Cod.Fisc' in l: cl_piva=l; break
    g1=Table([[Paragraph((dt+'  '+dn).strip(),BIG),Paragraph('DATA  '+mv.get('DATA',''),ML),Paragraph(cl_piva,SM)]],colWidths=[W*0.35,W*0.30,W*0.33])
    g1.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('BACKGROUND',(0,0),(0,0),LGRAY),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),6),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    els.append(g1)
    extra=[(k,v) for k,v in mv.items() if k!='DATA']
    for i in range(0,len(extra),2):
        k1,v1=extra[i]; k2,v2=extra[i+1] if i+1<len(extra) else ('','')
        g2=Table([[Paragraph(k1+':',ML),Paragraph(v1,MV),Paragraph(k2+':' if k2 else '',ML),Paragraph(v2,MV)]],colWidths=[W*0.18,W*0.30,W*0.18,W*0.32])
        g2.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),6),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8)]))
        els.append(g2)
    els.append(Spacer(1,8))

    # 3 REF NOTE
    rn=root.xpath(".//*[contains(@class,'ref-note')]")
    if rn: els+=[Paragraph(_tx(rn[0]),N),Spacer(1,4)]

    # 4 TABELLA ARTICOLI - SOLO la prima items-table
    itx=f1(root,".//table[@class='items-table']")
    if itx is not None:
        thead=f1(itx,'.//thead'); tbody=f1(itx,'.//tbody')
        ths=thead.xpath('.//th') if thead is not None else []
        n=len(ths) if ths else 8
        cw=[W*0.08,W*0.35,W*0.06,W*0.08,W*0.12,W*0.08,W*0.12,W*0.08][:n]
        while len(cw)<n: cw.append(W*0.09)
        ths_=[TH,TH,TH,THR,THR,TH,THR,TH]
        td_d=[[Paragraph(_tx(h),ths_[i] if i<len(ths_) else TH) for i,h in enumerate(ths)]] if ths else []
        if tbody is not None:
            for tr in tbody.xpath('./tr'):
                tds=tr.xpath('./td'); row=[]
                for j,td in enumerate(tds):
                    txt=_c('\n'.join(_bl(td)))
                    if j==1: row.append(Paragraph(txt.replace('\n','<br/>'),TD))
                    elif j in(3,4,6): row.append(Paragraph(txt,TDR))
                    elif j in(2,5,7): row.append(Paragraph(txt,TDC))
                    else: row.append(Paragraph(txt,TD))
                while len(row)<n: row.append(Paragraph('',TD))
                td_d.append(row[:n])
        if td_d:
            it=Table(td_d,colWidths=cw)
            ts=TableStyle([('LINEBELOW',(0,0),(-1,0),0.8,BLACK),('FONTNAME',(0,0),(-1,0),'Helvetica-BoldOblique'),
                ('GRID',(0,1),(-1,-1),0.2,BRD),('ALIGN',(3,0),(-1,-1),'RIGHT'),
                ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8)])
            it.setStyle(ts); els+=[it,Spacer(1,6)]

    # 5 INFO BOX
    ibs=root.xpath(".//*[contains(@class,'info-box')]")
    if ibs:
        t=_tx(ibs[0])
        if t: els+=[Paragraph(t,SM),Spacer(1,4)]

    # 6 TOTALI - salta tr dentro items-table/meta-table/header-table
    tr_l=[]; gr=None
    SKIP={'items-table','meta-table','header-table'}
    for tr in root.xpath('.//tr'):
        skip=False; p=tr.getparent()
        while p is not None:
            if p.get('class','') in SKIP: skip=True; break
            p=p.getparent()
        if skip: continue
        tds=tr.xpath('./td')
        if len(tds)>=2:
            lb=_tx(tds[0]).strip(); vl=_tx(tds[-1]).strip()
            if not lb or not vl: continue
            if 'TOTALE' in lb.upper() and 'IVA' not in lb.upper(): gr=(lb,vl)
            elif any(k in lb for k in ('Imponibile','IVA','Acconto','Da pagare','Sconto')):
                if not any(r[0]==lb for r in tr_l): tr_l.append((lb,vl))
    if tr_l or gr:
        bl=Table([['Sconti','Spese di trasporto','Spese di incasso','Bolli']],colWidths=[W*0.15,W*0.22,W*0.18,W*0.12])
        bl.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('FONTSIZE',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),4)]))
        iva_r=[['Codice','Descrizione','Imponibile','% IVA','Imposta']]
        for lb,vl in tr_l:
            if 'IVA' in lb.upper():
                m=_re.search(r'(\d+)\s*%',lb); aliq=m.group(1) if m else '22'
                imp=''.join(v for k,v in tr_l if 'Imponibile' in k)
                iva_r.append([aliq,f'Iva {aliq}%',imp.replace('\u20ac','').strip(),aliq,vl.replace('\u20ac','').strip()])
        iv=Table(iva_r,colWidths=[W*0.08,W*0.18,W*0.14,W*0.08,W*0.12])
        iv.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),7.5),('GRID',(0,0),(-1,-1),0.3,BRD),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),3)]))
        tot_d=[[Paragraph(lb.upper(),TL),Paragraph(vl,TV)] for lb,vl in tr_l]
        if gr: tot_d.append([Paragraph(gr[0].upper(),GL),Paragraph(gr[1],GV)])
        ts2=[('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('ALIGN',(1,0),(1,-1),'RIGHT'),('GRID',(0,0),(-1,-1),0.3,BRD)]
        if gr and tot_d: ts2+=[('FONTNAME',(0,len(tot_d)-1),(-1,len(tot_d)-1),'Helvetica-Bold'),('FONTSIZE',(0,len(tot_d)-1),(-1,len(tot_d)-1),10),('LINEABOVE',(0,len(tot_d)-1),(-1,len(tot_d)-1),0.8,BLACK)]
        tt=Table(tot_d,colWidths=[W*0.22,W*0.18]); tt.setStyle(TableStyle(ts2))
        bot=Table([[iv,tt]],colWidths=[W*0.62,W*0.40]); bot.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
        els+=[bl,bot,Spacer(1,8)]

    # 7 BANCA
    bk=f1(root,".//*[@class='bank-info']")
    if bk:
        lb=[l for l in _bl(bk) if l]
        if lb:
            bt=Table([[Paragraph('  '.join(lb),SM)]],colWidths=[W])
            bt.setStyle(TableStyle([('GRID',(0,0),(0,0),0.3,BRD),('LEFTPADDING',(0,0),(0,0),6),('TOPPADDING',(0,0),(0,0),4),('BOTTOMPADDING',(0,0),(0,0),4)]))
            els+=[bt,Spacer(1,6)]

    # 8 FOOTER
    ft=Table([[Paragraph('Generato da NormaFacile',FT),Paragraph('Pag. 1/1',FTR)]],colWidths=[W*0.6,W*0.4])
    ft.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),0.3,BRD),('TOPPADDING',(0,0),(-1,0),4)]))
    els+=[Spacer(1,10),ft]

    # 9 CONDIZIONI
    ce=None
    for el in root.iter():
        if 'page-break' in el.get('style','') or 'conditions-page' in el.get('class',''): ce=el; break
    if ce:
        els.append(PageBreak())
        els+=[Paragraph('CONDIZIONI GENERALI DI FORNITURA',BLB),HRFlowable(width='100%',thickness=1,color=BLUE,spaceAfter=6)]
        for ln in _c(ce.text_content() if hasattr(ce,'text_content') else '\n'.join(ce.itertext())).split('\n'):
            ln=ln.strip()
            if not ln or 'CONDIZIONI GENERALI' in ln.upper(): continue
            if _re.match(r'^\d+',ln): els+=[Spacer(1,4),Paragraph(ln,B)]
            else: els.append(Paragraph(ln,N))

    doc.build(els); buf.seek(0); return buf

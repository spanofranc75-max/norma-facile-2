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
          {"<img src='" + safe(co.get('logo_url','')) + "' style='max-height:50px; max-width:120px; margin-bottom:6px;'><br>" if co.get('logo_url') else ""}
                    {co.get('logo_url','').__len__() > 0 and '<img src="' + co.get('logo_url','') + '" style="max-height:50px; max-width:120px; margin-bottom:4px; display:block;">' or ''}
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
          <div class="client-name" style="font-size:11px; font-weight:bold; color:#1E293B;">{cl_name}</div>
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
    """Condizioni di fornitura reali dalle impostazioni aziendali."""
    company_name = safe((company or {}).get('business_name', ''))
    condizioni = (company or {}).get('condizioni_vendita', '').strip()
    
    def fix_encoding(text):
        """Corregge caratteri mal codificati."""
        return (text
            .replace('\u00e2\u0080\u0099', "'")
            .replace('\u00e2\u0080\u009c', '"')
            .replace('\u00e2\u0080\u009d', '"')
            .replace('\u00e0', 'ÃÂÃÂÃÂÃÂ ').replace('\u00e8', 'ÃÂÃÂÃÂÃÂ¨')
            .replace('\u00e9', 'ÃÂÃÂÃÂÃÂ©').replace('\u00ec', 'ÃÂÃÂÃÂÃÂ¬')
            .replace('\u00f2', 'ÃÂÃÂÃÂÃÂ²').replace('\u00f9', 'ÃÂÃÂÃÂÃÂ¹')
            .replace('\u00c0', 'ÃÂÃÂÃÂÃÂ').replace('\u00c8', 'ÃÂÃÂÃÂÃÂ')
            .replace('ÃÂÃÂÃÂÃÂ ', 'ÃÂÃÂÃÂÃÂ ').replace('ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨', 'ÃÂÃÂÃÂÃÂ¨').replace('ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ©', 'ÃÂÃÂÃÂÃÂ©')
            .replace('ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¬', 'ÃÂÃÂÃÂÃÂ¬').replace('ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ²', 'ÃÂÃÂÃÂÃÂ²').replace('ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹', 'ÃÂÃÂÃÂÃÂ¹')
            .replace('ÃÂÃÂÃÂÃÂ¢\x80\x99', "'").replace('ÃÂÃÂÃÂÃÂ¢\x80\x9c', '"')
            .replace('ÃÂÃÂÃÂÃÂ¢\x80\x9d', '"').replace('ÃÂÃÂÃÂÃÂ¢\x80\x93', 'ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ')
            .replace('\u2013', 'ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ').replace('\u2014', 'ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ')
        )
    
    if condizioni:
        condizioni = fix_encoding(condizioni)
        lines_html = ''
        for line in condizioni.split('\n'):
            line = line.strip()
            if not line:
                lines_html += '<p style="margin:2px 0">&nbsp;</p>'
            else:
                lines_html += f'<p style="margin:2px 0">{safe(line)}</p>'
    else:
        lines_html = '<p>Le condizioni di vendita non sono state configurate nelle Impostazioni.</p>'
    
    return f"""<div style="page-break-before: always; padding: 10px; font-size: 9px; font-family: Helvetica, Arial, sans-serif;">
        <h3 style="color: #1a56db; border-bottom: 2px solid #1a56db; padding-bottom: 5px; margin-bottom: 8px;">CONDIZIONI GENERALI DI FORNITURA</h3>
        <p style="font-size:8px; color:#888; margin-bottom:8px">Documento: {safe(doc_number)} &mdash; Azienda: {company_name}</p>
        <div style="line-height: 1.6;">{lines_html}</div>
    </div>"""


def render_pdf(html_content: str) -> BytesIO:
    """Render PDF stile Invoicex - layout professionale pulito."""
    import base64 as _b64, re as _re
    from lxml import html as _lhtml
    from reportlab.lib import colors as _col
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image, PageBreak, HRFlowable)
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

    def _img(s):
        try:
            if "base64," in s: s = s.split("base64,")[1]
            return BytesIO(_b64.b64decode(s))
        except: return None

    def _fix(t):
        t = str(t or '')
        for a, b in [('\u00e0','\u00e0'),('\u00e8','\u00e8'),('\u00e9','\u00e9'),('\u00ec','\u00ec'),('\u00f2','\u00f2'),('\u00f9','\u00f9'),
            ('\u00c3\u00a0','\u00e0'),('\u00c3\u00a8','\u00e8'),('\u00c3\u00a9','\u00e9'),('\u00c3\u00ac','\u00ec'),('\u00c3\u00b2','\u00f2'),('\u00c3\u00b9','\u00f9'),
            ('\u00e2\x80\x99',"'"),('\u00e2\x80\x93','\u2013'),('&agrave;','\u00e0'),('&egrave;','\u00e8'),
            ('&amp;','&'),('&nbsp;',' '),('&mdash;','\u2014'),('&lt;','<'),('&gt;','>'),]: t = t.replace(a, b)
        return t.strip()

    def _t(el):
        if el is None: return ''
        return _fix(' '.join(el.itertext()))

    def _br_lines(el):
        if el is None: return []
        for br in el.findall('.//br'): br.tail = '\n' + (br.tail or '')
        return [_fix(l) for l in '\n'.join(el.itertext()).split('\n') if _fix(l)]

    def P(text, sty):
        t = _fix(str(text or ''))
        return Paragraph(t.replace('\n','<br/>'), sty) if t else Spacer(1,1)

    if isinstance(html_content, bytes): html_content = html_content.decode('utf-8')
    tree = _lhtml.fromstring('<div id="root">' + html_content + '</div>')
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=2.0*cm)
    BLUE=_col.HexColor('#1a56db'); DARK=_col.HexColor('#1E293B'); LGRAY=_col.HexColor('#f3f4f6')
    BRD=_col.HexColor('#d1d5db'); WHITE=_col.white; BLACK=_col.black; GTXT=_col.HexColor('#6B7280')
    W = A4[0] - 3.0*cm
    ss = getSampleStyleSheet()
    def S(n,**k): return ParagraphStyle(n,parent=ss['Normal'],**k)
    N   =S('N',  fontSize=8.5,leading=11)
    B   =S('B',  fontSize=8.5,leading=11,fontName='Helvetica-Bold')
    SM  =S('SM', fontSize=7.5,leading=10,textColor=GTXT)
    CO  =S('CO', fontSize=11, leading=14,fontName='Helvetica-Bold')
    CL  =S('CL', fontSize=10, leading=13,fontName='Helvetica-Bold')
    BIG =S('BIG',fontSize=14, leading=18,fontName='Helvetica-Bold')
    TH  =S('TH', fontSize=8,  leading=10,fontName='Helvetica-BoldOblique',textColor=BLACK)
    THR =S('THR',fontSize=8,  leading=10,fontName='Helvetica-BoldOblique',textColor=BLACK,alignment=TA_RIGHT)
    TD  =S('TD', fontSize=8.5,leading=11)
    TDR =S('TDR',fontSize=8.5,leading=11,alignment=TA_RIGHT)
    TDC =S('TDC',fontSize=8.5,leading=11,alignment=TA_CENTER)
    TL  =S('TL', fontSize=8.5,leading=11,textColor=GTXT)
    TV  =S('TV', fontSize=8.5,leading=11,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    GL  =S('GL', fontSize=10, leading=13,fontName='Helvetica-Bold')
    GV  =S('GV', fontSize=10, leading=13,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    MLAB=S('MLAB',fontSize=7.5,leading=10,fontName='Helvetica-Bold',textColor=GTXT)
    MVAL=S('MVAL',fontSize=8.5,leading=11)
    FOOT=S('FOOT',fontSize=7,  leading=9, textColor=GTXT)
    FOOTR=S('FOOTR',fontSize=7,leading=9, textColor=GTXT,alignment=TA_RIGHT)
    BLB =S('BLB',fontSize=9,  leading=12,fontName='Helvetica-Bold',textColor=BLUE)
    els=[]

    # 1 HEADER
    co_boxes=tree.xpath("//div[@class='company-box']"); cl_boxes=tree.xpath("//div[@class='client-box']")
    co_box=co_boxes[0] if co_boxes else None; cl_box=cl_boxes[0] if cl_boxes else None
    imgs=tree.xpath('//img/@src'); logo=None
    if imgs:
        s=_img(imgs[0])
        if s:
            try: logo=Image(s,width=2.0*cm,height=1.0*cm)
            except: pass
    co_col=[]
    if logo: co_col.append(logo)
    if co_box is not None:
        c_n=co_box.xpath(".//div[@class='company-name']"); c_d=co_box.xpath(".//div[@class='company-detail']")
        if c_n: co_col.append(Paragraph(_t(c_n[0]),CO))
        if c_d:
            for line in _br_lines(c_d[0]): co_col.append(Paragraph(line,B if('P.IVA' in line or 'Cod.Fisc' in line) else SM))
    CLI=S('CLI',fontSize=8,leading=10,fontName='Helvetica-Oblique',textColor=GTXT)
    cl_paras=[Paragraph('Cliente',CLI)]
    if cl_box is not None:
        c_n=cl_box.xpath(".//div[@class='client-name']"); c_d=cl_box.xpath(".//div[@class='client-detail']")
        if c_n: cl_paras.append(Paragraph(_t(c_n[0]),CL))
        if c_d:
            for line in _br_lines(c_d[0]): cl_paras.append(Paragraph(line,B if('P.IVA' in line or 'Cod.Fisc' in line) else SM))
    hdr=Table([[co_col,cl_paras]],colWidths=[W*0.52,W*0.46])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),
        ('RIGHTPADDING',(0,0),(0,0),6),('LEFTPADDING',(1,0),(1,0),8),('TOPPADDING',(1,0),(1,0),6),
        ('BOTTOMPADDING',(1,0),(1,0),6),('BACKGROUND',(1,0),(1,0),LGRAY),('BOX',(1,0),(1,0),0.5,BRD)]))
    els+=[hdr,Spacer(1,8)]

    # 2 GRIGLIA META
    title_div=tree.xpath("//div[@class='doc-title']")
    meta_rows=tree.xpath("//table[@class='meta-table']//tr")
    doc_title=''; doc_num=''
    if title_div:
        h1=title_div[0].xpath('.//h1'); dn=title_div[0].xpath(".//*[@class='doc-num']")
        doc_title=_fix(h1[0].text_content()) if h1 else ''; doc_num=_fix(dn[0].text_content()) if dn else ''
    meta_vals={}
    for tr in meta_rows:
        tds=tr.xpath('./td')
        for i in range(0,len(tds)-1,2):
            k=_fix(tds[i].text_content()).rstrip(':').strip(); v=_fix(tds[i+1].text_content()).strip()
            if k and v: meta_vals[k]=v
    cl_piva=''
    if cl_box is not None:
        c_d=cl_box.xpath(".//div[@class='client-detail']")
        if c_d:
            for line in _br_lines(c_d[0]):
                if 'P.IVA' in line or 'Cod.Fisc' in line: cl_piva=line; break
    grid=Table([[Paragraph(doc_title+' '+doc_num,BIG),Paragraph('DATA '+meta_vals.get('DATA',''),MLAB),Paragraph(cl_piva or '',MLAB)]],colWidths=[W*0.35,W*0.30,W*0.33])
    grid.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('BACKGROUND',(0,0),(0,0),LGRAY),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),6),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    els.append(grid)
    pag=meta_vals.get('Pagamento','')
    if pag:
        g2=Table([[Paragraph('Pagamento',MLAB),Paragraph(pag,MVAL),Paragraph('',N)]],colWidths=[W*0.20,W*0.45,W*0.33])
        g2.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),6),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold')]))
        els.append(g2)
    els.append(Spacer(1,8))

    # 3 REF NOTE
    for e in tree.xpath("//*[contains(@class,'ref-note')]"):
        els+=[Paragraph(_fix(e.text_content()),N),Spacer(1,4)]

    # 4 TABELLA ARTICOLI
    it_tbl=tree.xpath("//table[@class='items-table']")
    if it_tbl:
        ths=it_tbl[0].xpath('.//thead/tr/th'); trs=it_tbl[0].xpath('.//tbody/tr')
        n=len(ths) if ths else 8
        cw=[W*0.08,W*0.35,W*0.06,W*0.08,W*0.12,W*0.08,W*0.12,W*0.08][:n]
        while len(cw)<n: cw.append(W*0.09)
        th_s=[TH,TH,TH,THR,THR,TH,THR,TH]
        td_data=[[Paragraph(_fix(h.text_content()),th_s[i] if i<len(th_s) else TH) for i,h in enumerate(ths)]] if ths else []
        for tr in trs:
            tds=tr.xpath('./td'); row=[]
            for j,td in enumerate(tds):
                for br in td.findall('.//br'): br.tail='\n'+(br.tail or '')
                txt=_fix(td.text_content())
                if j==1: row.append(Paragraph(txt.replace('\n','<br/>'),TD))
                elif j in(3,4,6): row.append(Paragraph(txt,TDR))
                elif j in(2,5,7): row.append(Paragraph(txt,TDC))
                else: row.append(Paragraph(txt,TD))
            while len(row)<n: row.append(Paragraph('',TD))
            td_data.append(row[:n])
        if td_data:
            it=Table(td_data,colWidths=cw)
            ts=TableStyle([('LINEBELOW',(0,0),(-1,0),0.8,BLACK),('FONTNAME',(0,0),(-1,0),'Helvetica-BoldOblique'),
                ('GRID',(0,1),(-1,-1),0.2,BRD),('ALIGN',(3,0),(-1,-1),'RIGHT'),
                ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8)])
            it.setStyle(ts); els+=[it,Spacer(1,6)]

    # 5 INFO BOX
    for e in tree.xpath("//*[contains(@class,'info-box')]"):
        txt=_fix(e.text_content())
        if txt: els+=[Paragraph(txt,SM),Spacer(1,4)]

    # 6 TOTALI stile Invoicex
    tr_list=[]; gr=None
    for tr in tree.xpath('.//tr'):
        tds=tr.xpath('./td')
        if len(tds)>=2:
            lb=_fix(tds[0].text_content()).strip(); vl=_fix(tds[-1].text_content()).strip()
            if not lb or not vl: continue
            if 'TOTALE' in lb.upper() and 'IVA' not in lb.upper(): gr=(lb,vl)
            elif any(k in lb for k in ('Imponibile','IVA','Acconto','Da pagare','Sconto')): tr_list.append((lb,vl))
    if tr_list or gr:
        bl=Table([['Sconti','Spese di trasporto','Spese di incasso','Bolli']],colWidths=[W*0.15,W*0.20,W*0.15,W*0.12])
        bl.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,BRD),('FONTSIZE',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),4)]))
        iva_rows=[['Codice','Descrizione','Imponibile','% IVA','Imposta']]
        for lb,vl in tr_list:
            if 'IVA' in lb.upper(): iva_rows.append(['22','Iva 22%','',lb.split('%')[0].split()[-1] if '%' in lb else '22',vl.replace('\u20ac','').strip()])
        iva_t=Table(iva_rows,colWidths=[W*0.08,W*0.18,W*0.12,W*0.08,W*0.12])
        iva_t.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),7.5),('GRID',(0,0),(-1,-1),0.3,BRD),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),3)]))
        tot_d=[[Paragraph(lb.upper(),MLAB),Paragraph(vl,TV)] for lb,vl in tr_list]
        if gr: tot_d.append([Paragraph(gr[0].upper(),GL),Paragraph(gr[1],GV)])
        tot_t=Table(tot_d,colWidths=[W*0.20,W*0.18])
        ts2=[('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),6),
            ('RIGHTPADDING',(0,0),(-1,-1),6),('ALIGN',(1,0),(1,-1),'RIGHT'),('GRID',(0,0),(-1,-1),0.3,BRD)]
        if gr: ts2+=[('FONTNAME',(0,len(tot_d)-1),(-1,len(tot_d)-1),'Helvetica-Bold'),('LINEABOVE',(0,len(tot_d)-1),(-1,len(tot_d)-1),0.8,BLACK)]
        tot_t.setStyle(TableStyle(ts2))
        bottom=Table([[iva_t,tot_t]],colWidths=[W*0.62,W*0.38])
        bottom.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
        els+=[bl,bottom,Spacer(1,8)]

    # 7 BANCA
    bk=tree.xpath("//*[contains(@class,'bank-info')]")
    if bk:
        for br in bk[0].findall('.//br'): br.tail='\n'+(br.tail or '')
        lb=[_fix(l) for l in bk[0].text_content().split('\n') if _fix(l)]
        if lb:
            bt=Table([[Paragraph('  '.join(lb),SM)]],colWidths=[W])
            bt.setStyle(TableStyle([('GRID',(0,0),(0,0),0.3,BRD),('LEFTPADDING',(0,0),(0,0),6),('TOPPADDING',(0,0),(0,0),4),('BOTTOMPADDING',(0,0),(0,0),4)]))
            els+=[bt,Spacer(1,6)]

    # 8 FOOTER
    ft=Table([[Paragraph('Generato da NormaFacile',FOOT),Paragraph('Pag. 1/1',FOOTR)]],colWidths=[W*0.6,W*0.4])
    ft.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),0.3,BRD),('TOPPADDING',(0,0),(-1,0),4)]))
    els+=[Spacer(1,10),ft]

    # 9 CONDIZIONI
    ce=(tree.xpath("//*[contains(@style,'page-break')]") or tree.xpath("//*[contains(@class,'conditions-page')]"))
    if ce:
        els.append(PageBreak())
        els+=[Paragraph('CONDIZIONI GENERALI DI FORNITURA',BLB),HRFlowable(width='100%',thickness=1,color=BLUE,spaceAfter=6)]
        for ln in _fix(ce[0].text_content()).split('\n'):
            ln=ln.strip()
            if not ln or 'CONDIZIONI GENERALI' in ln.upper(): continue
            if _re.match(r'^\d+',ln): els+=[Spacer(1,4),Paragraph(ln,B)]
            else: els.append(Paragraph(ln,N))

    doc.build(els)
    buf.seek(0)
    return buf

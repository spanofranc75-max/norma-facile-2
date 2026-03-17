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
            .replace('\u00e0', 'ÃÂ ').replace('\u00e8', 'ÃÂ¨')
            .replace('\u00e9', 'ÃÂ©').replace('\u00ec', 'ÃÂ¬')
            .replace('\u00f2', 'ÃÂ²').replace('\u00f9', 'ÃÂ¹')
            .replace('\u00c0', 'ÃÂ').replace('\u00c8', 'ÃÂ')
            .replace('ÃÂ ', 'ÃÂ ').replace('ÃÂÃÂ¨', 'ÃÂ¨').replace('ÃÂÃÂ©', 'ÃÂ©')
            .replace('ÃÂÃÂ¬', 'ÃÂ¬').replace('ÃÂÃÂ²', 'ÃÂ²').replace('ÃÂÃÂ¹', 'ÃÂ¹')
            .replace('ÃÂ¢\x80\x99', "'").replace('ÃÂ¢\x80\x9c', '"')
            .replace('ÃÂ¢\x80\x9d', '"').replace('ÃÂ¢\x80\x93', 'Ã¢ÂÂ')
            .replace('\u2013', 'Ã¢ÂÂ').replace('\u2014', 'Ã¢ÂÂ')
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
    import base64 as _b64, re as _re
    from lxml import html as _lhtml
    from reportlab.lib import colors as _col
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image, PageBreak, HRFlowable)
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER

    def _img(s):
        try:
            if "base64," in s: s = s.split("base64,")[1]
            return BytesIO(_b64.b64decode(s))
        except: return None

    def _fix(t):
        t = str(t or '')
        for a,b in [('\u00e0','à'),('\u00e8','è'),('\u00e9','é'),('\u00ec','ì'),('\u00f2','ò'),('\u00f9','ù'),
                    ('Ã ','à'),('Ã¨','è'),('Ã©','é'),('Ã¬','ì'),('Ã²','ò'),('Ã¹','ù'),
                    ('â\x80\x99',"'"),('â\x80\x93','–'),('&agrave;','à'),('&egrave;','è'),
                    ('&igrave;','ì'),('&ograve;','ò'),('&ugrave;','ù'),('&amp;','&'),
                    ('&nbsp;',' '),('&mdash;','—'),('&lt;','<'),('&gt;','>')]:
            t = t.replace(a, b)
        return t.strip()

    def _gt(el):
        if el is None: return ''
        return _fix(' '.join(el.itertext()))

    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')

    tree = _lhtml.fromstring('<html><body>' + html_content + '</body></html>')
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm, topMargin=1.5*cm, bottomMargin=2.0*cm)

    BLUE = _col.HexColor('#1a56db'); DARK = _col.HexColor('#1E293B')
    GRAY = _col.HexColor('#F8F9FA'); BRD  = _col.HexColor('#DEE2E6')
    WHITE= _col.white; GTXT = _col.HexColor('#6B7280')
    W = A4[0] - 3.6*cm
    ss = getSampleStyleSheet()
    def S(n,**k): return ParagraphStyle(n, parent=ss['Normal'], **k)
    N  =S('N', fontSize=9, leading=13)
    B  =S('B', fontSize=9, leading=13, fontName='Helvetica-Bold')
    SM =S('SM',fontSize=8, leading=11, textColor=GTXT)
    SMB=S('SMB',fontSize=8,leading=11,fontName='Helvetica-Bold',textColor=GTXT)
    CO =S('CO',fontSize=12,leading=15,fontName='Helvetica-Bold',textColor=BLUE)
    CL =S('CL',fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=DARK)
    BIG=S('BIG',fontSize=18,leading=22,fontName='Helvetica-Bold',textColor=BLUE,alignment=TA_CENTER)
    TH =S('TH', fontSize=8, leading=11,fontName='Helvetica-Bold',textColor=WHITE)
    THR=S('THR',fontSize=8, leading=11,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_RIGHT)
    THC=S('THC',fontSize=8, leading=11,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_CENTER)
    TD =S('TD', fontSize=8.5,leading=12)
    TDR=S('TDR',fontSize=8.5,leading=12,alignment=TA_RIGHT)
    TDC=S('TDC',fontSize=8.5,leading=12,alignment=TA_CENTER)
    TL =S('TL', fontSize=9, leading=13,textColor=GTXT)
    TV =S('TV', fontSize=9, leading=13,fontName='Helvetica-Bold',alignment=TA_RIGHT)
    GL =S('GL', fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=WHITE)
    GV =S('GV', fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_RIGHT)
    MLB=S('MLB',fontSize=8, leading=10,fontName='Helvetica-Bold',textColor=GTXT)
    BLB=S('BLB',fontSize=10,leading=13,fontName='Helvetica-Bold',textColor=BLUE)
    els = []

    # 1 HEADER
    imgs = tree.xpath('//img/@src')
    logo = None
    if imgs:
        s = _img(imgs[0])
        if s:
            try: logo = Image(s, width=3*cm, height=1.5*cm)
            except: pass
    co_n = tree.xpath("//div[@class='company-name']")
    co_d = tree.xpath("//div[@class='company-detail']")
    cl_n = tree.xpath("//div[@class='client-name']")
    cl_d = tree.xpath("//div[@class='client-detail']")
    def _br_lines(el):
        if el is None: return []
        for br in el.findall('.//br'): br.tail = '\n'+(br.tail or '')
        return [_fix(l) for l in '\n'.join(el.itertext()).split('\n') if _fix(l)]
    co_col = []
    if logo: co_col.append(logo)
    if co_n: co_col.append(Paragraph(_gt(co_n[0]), CO))
    for l in _br_lines(co_d[0] if co_d else None):
        co_col.append(Paragraph(l, B if ('P.IVA' in l or 'Cod.Fisc' in l) else SM))
    cl_col = [Paragraph('Spett.le', SMB)]
    if cl_n: cl_col.append(Paragraph(_gt(cl_n[0]), CL))
    for l in _br_lines(cl_d[0] if cl_d else None):
        cl_col.append(Paragraph(l, B if ('P.IVA' in l or 'Cod.Fisc' in l) else SM))
    hdr = Table([[co_col, cl_col]], colWidths=[W*0.55, W*0.43])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),
        ('RIGHTPADDING',(0,0),(0,0),6),('LEFTPADDING',(1,0),(1,0),10),
        ('TOPPADDING',(1,0),(1,0),6),('BOTTOMPADDING',(1,0),(1,0),6),
        ('BACKGROUND',(1,0),(1,0),GRAY),('BOX',(1,0),(1,0),0.5,BRD)]))
    els.append(hdr)
    els.append(HRFlowable(width='100%',thickness=0.5,color=BRD,spaceAfter=6))

    # 2 TITOLO
    td = tree.xpath("//div[@class='doc-title']")
    if td:
        tt = [_fix(t) for t in td[0].itertext() if _fix(t).strip()]
        if tt: els += [Paragraph('  '.join(tt), BIG), Spacer(1,4)]

    # 3 META
    mrows = tree.xpath("//table[@class='meta-table']//tr")
    md = []
    for tr in mrows:
        tds = tr.xpath('./td')
        if len(tds)>=2: md.append([Paragraph(_fix(tds[0].text_content()),MLB), Paragraph(_fix(tds[1].text_content()),N)])
    if md:
        h2=(len(md)+1)//2; L,R=md[:h2],md[h2:]
        while len(R)<len(L): R.append([Paragraph('',N),Paragraph('',N)])
        rws=[L[i]+[Spacer(4,1)]+R[i] for i in range(len(L))]
        mt=Table(rws,colWidths=[W*0.17,W*0.30,W*0.06,W*0.17,W*0.30])
        mt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRAY),('BOX',(0,0),(-1,-1),0.5,BRD),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),5)]))
        els += [mt, Spacer(1,6)]

    # 4 REF
    for e in tree.xpath("//*[contains(@class,'ref-note')]"):
        els += [Paragraph(_fix(e.text_content()),N), Spacer(1,4)]

    # 5 RIGHE
    it_tbl = tree.xpath("//table[@class='items-table']")
    if it_tbl:
        ths = it_tbl[0].xpath('.//thead/tr/th')
        trs = it_tbl[0].xpath('.//tbody/tr')
        n = len(ths) if ths else 8
        cw = [W*0.08,W*0.36,W*0.06,W*0.08,W*0.12,W*0.08,W*0.12,W*0.08][:n]
        while len(cw)<n: cw.append(W*0.10)
        ths_s=[TH,TH,THC,THR,THR,THC,THR,THC]
        td_data=[[Paragraph(_fix(h.text_content()),ths_s[i] if i<len(ths_s) else TH) for i,h in enumerate(ths)]] if ths else []
        for tr in trs:
            tds=tr.xpath('./td'); row=[]
            for j,td in enumerate(tds):
                t=_fix(td.text_content())
                if j==1: row.append(Paragraph(t,TD))
                elif j in(3,4,6): row.append(Paragraph(t,TDR))
                elif j in(2,5,7): row.append(Paragraph(t,TDC))
                else: row.append(Paragraph(t,TD))
            while len(row)<n: row.append(Paragraph('',TD))
            td_data.append(row[:n])
        if td_data:
            it=Table(td_data,colWidths=cw)
            ts=TableStyle([('BACKGROUND',(0,0),(-1,0),DARK),('TEXTCOLOR',(0,0),(-1,0),WHITE),
                ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
                ('TOPPADDING',(0,1),(-1,-1),3),('BOTTOMPADDING',(0,1),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,1),(-1,-1),0.3,BRD)])
            for i in range(1,len(td_data),2): ts.add('BACKGROUND',(0,i),(-1,i),GRAY)
            it.setStyle(ts); els += [it, Spacer(1,6)]

    # 6 INFO BOX
    for e in tree.xpath("//*[contains(@class,'info-box')]"):
        ib=Table([[Paragraph(_fix(e.text_content()),N)]],colWidths=[W])
        ib.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),GRAY),('LINEBEFORE',(0,0),(0,-1),3,BLUE),
            ('LEFTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(0,0),6),('BOTTOMPADDING',(0,0),(0,0),6)]))
        els += [ib, Spacer(1,4)]

    # 7 TOTALI
    tr_list=[]; gr=None
    for tr in tree.xpath('.//tr'):
        tds=tr.xpath('./td')
        if len(tds)>=2:
            lb=_fix(tds[0].text_content()).strip(); vl=_fix(tds[-1].text_content()).strip()
            if not lb or not vl: continue
            if 'TOTALE' in lb.upper() and 'IVA' not in lb.upper(): gr=(lb,vl)
            elif any(k in lb for k in ('Imponibile','IVA','Acconto','Da pagare','Sconto')): tr_list.append((lb,vl))
    if tr_list:
        dt=[[Paragraph('',N),Paragraph(lb,TL),Paragraph(vl,TV)] for lb,vl in tr_list]
        tt=Table(dt,colWidths=[W*0.35,W*0.40,W*0.23])
        tt.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('ALIGN',(2,0),(2,-1),'RIGHT')]))
        els.append(tt)
    if gr:
        gt=Table([[Paragraph('',N),Paragraph(gr[0],GL),Paragraph(gr[1],GV)]],colWidths=[W*0.35,W*0.40,W*0.23])
        gt.setStyle(TableStyle([('BACKGROUND',(1,0),(2,0),BLUE),('TOPPADDING',(1,0),(2,0),6),
            ('BOTTOMPADDING',(1,0),(2,0),6),('LEFTPADDING',(1,0),(1,0),8),('RIGHTPADDING',(2,0),(2,0),8)]))
        els += [Spacer(1,2), gt]
    els.append(Spacer(1,8))

    # 8 BANCA
    bk = tree.xpath("//*[contains(@class,'bank-info')]")
    if bk:
        for br in bk[0].findall('.//br'): br.tail='\n'+(br.tail or '')
        lb=[_fix(l) for l in bk[0].text_content().split('\n') if _fix(l)]
        bt=Table([[Paragraph('  '.join(lb),B)]],colWidths=[W])
        bt.setStyle(TableStyle([('LINEBEFORE',(0,0),(0,-1),3,BLUE),('BACKGROUND',(0,0),(0,0),GRAY),
            ('LEFTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(0,0),6),('BOTTOMPADDING',(0,0),(0,0),6)]))
        els += [bt, Spacer(1,6)]

    # 9 CONDIZIONI
    ce=tree.xpath("//*[contains(@style,'page-break')]") or tree.xpath("//*[contains(@class,'conditions-page')]")
    if ce:
        els.append(PageBreak())
        els += [Paragraph('CONDIZIONI GENERALI DI FORNITURA',BLB),
                HRFlowable(width='100%',thickness=1,color=BLUE,spaceAfter=6)]
        for ln in _fix(ce[0].text_content()).split('\n'):
            ln=ln.strip()
            if not ln or 'CONDIZIONI GENERALI' in ln.upper(): continue
            if _re.match(r'^\d+',ln): els += [Spacer(1,3), Paragraph(ln,B)]
            else: els.append(Paragraph(ln,N))

    doc.build(els)
    buf.seek(0)
    return buf

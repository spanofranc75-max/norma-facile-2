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
    color: #0055FF;
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
    background: #0055FF;
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
    color: #0055FF;
    border-top: 2px solid #0055FF;
    padding-top: 3px;
}
.notes-box {
    background: #f8f9fa;
    border-left: 3px solid #0055FF;
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
    color: #0055FF;
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
    <table class="header-table">
      <tr>
        <td class="company-box">
          <div class="company-name">{company_name}</div>
          <div class="company-detail">
            {full_addr}<br>
            {"<span class='piva-bold'>P.IVA: " + piva + "</span><br>" if piva else ""}
            {"Cod.Fisc.: " + cf + "<br>" if cf else ""}
            {"Tel: " + phone + "<br>" if phone else ""}
            {"Email: " + email if email else ""}
          </div>
        </td>
        <td class="client-box">
          <div class="client-label">Destinatario</div>
          <div class="client-name">{cl_name}</div>
          <div class="client-detail">
            {cl_full}<br>
            {"<span class='piva-bold'>P.IVA: " + cl_piva + "</span><br>" if cl_piva else ""}
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
    company_name = safe((company or {}).get('business_name', ''))
    return f"""
    <div style="page-break-before: always; padding: 10px; font-size: 9px;">
        <h3 style="color: #0055FF; border-bottom: 2px solid #0055FF; padding-bottom: 5px;">CONDIZIONI GENERALI DI FORNITURA</h3>
        <p><strong>Documento:</strong> {safe(doc_number)} &nbsp;&nbsp; <strong>Azienda:</strong> {company_name}</p>
        <p><strong>1. VALIDIT&Agrave; DELL&#39;OFFERTA</strong><br>Il presente preventivo ha validit&agrave; come indicato nel documento dalla data di emissione.</p>
        <p><strong>2. PREZZI</strong><br>I prezzi indicati si intendono IVA esclusa salvo diversa indicazione esplicita.</p>
        <p><strong>3. TEMPI DI CONSEGNA</strong><br>I tempi di consegna decorrono dalla data di conferma dell&#39;ordine e ricevimento dell&#39;acconto.</p>
        <p><strong>4. PAGAMENTO</strong><br>Il pagamento dovr&agrave; avvenire secondo le modalit&agrave; indicate nel preventivo.</p>
        <p><strong>5. TRASPORTO</strong><br>La merce viaggia a rischio e pericolo del committente salvo diversa indicazione.</p>
        <p><strong>6. FORO COMPETENTE</strong><br>Per qualsiasi controversia &egrave; competente il Foro del luogo ove ha sede il fornitore.</p>
    </div>
    """


def render_pdf(html_content: str) -> BytesIO:
    from bs4 import BeautifulSoup
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    import re

    BLUE=colors.HexColor('#0055FF'); DARK=colors.HexColor('#1E293B')
    GRAY=colors.HexColor('#F8F9FA'); BORDER=colors.HexColor('#DEE2E6')
    WHITE=colors.white; GRAY_TXT=colors.HexColor('#6B7280')
    W=A4[0]-36*mm

    styles=getSampleStyleSheet()
    def S(name,**kw): return ParagraphStyle(name,parent=styles['Normal'],**kw)
    def cl(tag):
        if tag is None: return ''
        txt=tag.get_text(separator='\n') if hasattr(tag,'get_text') else str(tag)
        return txt.strip()
    def P(text,style):
        t=(text or '').strip().replace('\n','<br/>')
        return Paragraph(t,style) if t else Spacer(1,1)

    N=S('N',fontSize=9,leading=13); B=S('B',fontSize=9,leading=13,fontName='Helvetica-Bold')
    SM=S('SM',fontSize=8,leading=11,textColor=GRAY_TXT)
    SMB=S('SMB',fontSize=8,leading=11,fontName='Helvetica-Bold',textColor=GRAY_TXT)
    CO=S('CO',fontSize=12,leading=15,fontName='Helvetica-Bold',textColor=BLUE)
    CL=S('CL',fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=DARK)
    BIG=S('BIG',fontSize=18,leading=22,fontName='Helvetica-Bold',textColor=BLUE,alignment=TA_CENTER)
    TH=S('TH',fontSize=8.5,leading=11,fontName='Helvetica-Bold',textColor=WHITE)
    THR=S('THR',fontSize=8.5,leading=11,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_RIGHT)
    THC=S('THC',fontSize=8.5,leading=11,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_CENTER)
    TD=S('TD',fontSize=8.5,leading=12); TDR=S('TDR',fontSize=8.5,leading=12,alignment=TA_RIGHT)
    TDC=S('TDC',fontSize=8.5,leading=12,alignment=TA_CENTER)
    TL=S('TL',fontSize=9,leading=13,textColor=GRAY_TXT)
    TV=S('TV',fontSize=9,leading=13,alignment=TA_RIGHT,fontName='Helvetica-Bold')
    GL=S('GL',fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=WHITE)
    GV=S('GV',fontSize=11,leading=14,fontName='Helvetica-Bold',textColor=WHITE,alignment=TA_RIGHT)
    BLB=S('BLB',fontSize=10,leading=13,fontName='Helvetica-Bold',textColor=BLUE)

    soup=BeautifulSoup(html_content,'lxml')
    story=[]; buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=20*mm)

    # 1. HEADER
    co_box=soup.find(class_='company-box'); cl_box=soup.find(class_='client-box')
    if co_box or cl_box:
        def parse_co(box):
            paras=[]
            if not box: return [Paragraph('',N)]
            name=box.find(class_='company-name')
            if name: paras.append(Paragraph(cl(name),CO))
            detail=box.find(class_='company-detail')
            if detail:
                for line in cl(detail).split('\n'):
                    line=line.strip()
                    if not line: continue
                    paras.append(Paragraph(line,B if 'P.IVA' in line or 'Cod.Fisc' in line else SM))
            return paras or [Paragraph('',N)]
        def parse_cl(box):
            paras=[Paragraph('Spett.le',SMB)]
            if not box: return paras
            name=box.find(class_='client-name')
            if name: paras.append(Paragraph(cl(name),CL))
            detail=box.find(class_='client-detail')
            if detail:
                for line in cl(detail).split('\n'):
                    line=line.strip()
                    if not line: continue
                    paras.append(Paragraph(line,B if 'P.IVA' in line or 'Cod.Fisc' in line else SM))
            return paras
        hdr=Table([[parse_co(co_box),parse_cl(cl_box)]],colWidths=[W*0.55,W*0.43])
        hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),
            ('RIGHTPADDING',(0,0),(0,0),6),('LEFTPADDING',(1,0),(1,0),10),
            ('TOPPADDING',(1,0),(1,0),6),('BOTTOMPADDING',(1,0),(1,0),6),
            ('BACKGROUND',(1,0),(1,0),GRAY),('BOX',(1,0),(1,0),0.5,BORDER)]))
        story.append(hdr)
        story.append(HRFlowable(width='100%',thickness=0.5,color=BORDER,spaceAfter=6))

    # 2. TITOLO
    doc_title=soup.find(class_='doc-title')
    if doc_title:
        h1=doc_title.find('h1'); num=doc_title.find(class_='doc-num')
        title_txt=cl(h1) if h1 else ''; num_txt=cl(num) if num else ''
        if title_txt:
            story.append(Paragraph(f"{title_txt}  {num_txt}".strip(),BIG))
            story.append(Spacer(1,4))

    # 3. META TABLE
    meta_tbl=soup.find('table',class_='meta-table')
    if meta_tbl:
        meta_data=[]
        for row in meta_tbl.find_all('tr'):
            cells=row.find_all('td')
            if len(cells)>=2:
                meta_data.append([Paragraph(cl(cells[0]),SMB),Paragraph(cl(cells[1]),N)])
        if meta_data:
            half=(len(meta_data)+1)//2
            left=meta_data[:half]; right=meta_data[half:]
            while len(right)<len(left): right.append([Paragraph('',N),Paragraph('',N)])
            rows=[left[i]+[Spacer(4,1)]+right[i] for i in range(len(left))]
            mt=Table(rows,colWidths=[W*0.17,W*0.30,W*0.06,W*0.17,W*0.30])
            mt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRAY),('BOX',(0,0),(-1,-1),0.5,BORDER),
                ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),5)]))
            story.append(mt); story.append(Spacer(1,6))

    # 4. REF NOTE
    ref_note=soup.find(class_='ref-note')
    if ref_note: story.append(Paragraph(cl(ref_note),N)); story.append(Spacer(1,4))

    # 5. TABELLA RIGHE
    items_tbl=soup.find('table',class_='items-table')
    if items_tbl:
        thead=items_tbl.find('thead'); tbody=items_tbl.find('tbody')
        th_tags=thead.find_all('th') if thead else []
        n=len(th_tags) if th_tags else 8
        col_w=[W*0.08,W*0.36,W*0.06,W*0.08,W*0.12,W*0.08,W*0.12,W*0.08]
        while len(col_w)<n: col_w.append(W*0.10)
        col_w=col_w[:n]
        th_styles=[TH,TH,THC,THR,THR,THC,THR,THC]
        while len(th_styles)<n: th_styles.append(TH)
        table_data=[[Paragraph(cl(th),th_styles[i]) for i,th in enumerate(th_tags)]] if th_tags else []
        if tbody:
            for tr in tbody.find_all('tr'):
                cells=tr.find_all('td'); row=[]
                for j,cell in enumerate(cells):
                    txt=cl(cell).replace('\n','<br/>')
                    if j==1: row.append(Paragraph(txt,TD))
                    elif j in(3,4,6): row.append(Paragraph(txt,TDR))
                    elif j in(2,5,7): row.append(Paragraph(txt,TDC))
                    else: row.append(Paragraph(txt,TD))
                while len(row)<n: row.append(Paragraph('',TD))
                table_data.append(row[:n])
        if table_data:
            it=Table(table_data,colWidths=col_w)
            it.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),DARK),('TEXTCOLOR',(0,0),(-1,0),WHITE),
                ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
                ('TOPPADDING',(0,1),(-1,-1),3),('BOTTOMPADDING',(0,1),(-1,-1),3),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,1),(-1,-1),0.3,BORDER),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,GRAY])]))
            story.append(it); story.append(Spacer(1,6))

    # 6. INFO BOX
    info_box=soup.find(class_='info-box')
    if info_box:
        ib=Table([[Paragraph(cl(info_box),N)]],colWidths=[W])
        ib.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),GRAY),('LINEBEFORE',(0,0),(0,0),3,BLUE),
            ('LEFTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(0,0),6),('BOTTOMPADDING',(0,0),(0,0),6)]))
        story.append(ib); story.append(Spacer(1,4))

    # 7. TOTALI
    totals_tbl=(soup.find(class_='totals-block') or soup.find('table',class_='totals-table') or soup.find(class_='totals-table'))
    tot_data=[]; grand=None
    if totals_tbl:
        for tr in totals_tbl.find_all('tr'):
            cells=tr.find_all('td')
            if len(cells)>=2:
                label=cl(cells[0]).strip(); value=cl(cells[-1]).strip()
                if not label: continue
                if 'TOTALE' in label.upper() and 'IVA' not in label.upper(): grand=(label,value)
                else: tot_data.append([Paragraph(label,TL),Paragraph(value,TV)])
    if not tot_data and not grand:
        for m in re.finditer(r'(Imponibile|Totale senza IVA|IVA\s*\d+%|TOTALE|Acconto|Da pagare)[^<\n]*?([\d.,]+\s*€?)',html_content,re.IGNORECASE):
            label,value=m.group(1).strip(),m.group(2).strip()
            if 'TOTALE' in label.upper() and 'IVA' not in label.upper(): grand=(label,value+' €')
            else: tot_data.append([Paragraph(label,TL),Paragraph(value+' €',TV)])
    if tot_data:
        tt=Table(tot_data,colWidths=[W*0.65,W*0.33],hAlign='RIGHT')
        tt.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'RIGHT'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
        story.append(tt)
    if grand:
        gt=Table([[Paragraph(grand[0],GL),Paragraph(grand[1],GV)]],colWidths=[W*0.65,W*0.33],hAlign='RIGHT')
        gt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),BLUE),('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]))
        story.append(Spacer(1,2)); story.append(gt)
    story.append(Spacer(1,8))

    # 8. BANCA
    bank_div=soup.find(class_='bank-info')
    if bank_div:
        bank_txt='  '.join([l.strip() for l in cl(bank_div).split('\n') if l.strip()])
        bt=Table([[Paragraph(bank_txt,B)]],colWidths=[W])
        bt.setStyle(TableStyle([('LINEBEFORE',(0,0),(0,0),3,BLUE),('BACKGROUND',(0,0),(0,0),GRAY),
            ('LEFTPADDING',(0,0),(0,0),10),('TOPPADDING',(0,0),(0,0),6),('BOTTOMPADDING',(0,0),(0,0),6)]))
        story.append(bt); story.append(Spacer(1,6))

    # 9. CONDIZIONI
    cond_div=soup.find(style=lambda s: s and 'page-break' in s)
    if cond_div:
        story.append(PageBreak())
        story.append(Paragraph('CONDIZIONI GENERALI DI FORNITURA',BLB))
        story.append(HRFlowable(width='100%',thickness=1,color=BLUE,spaceAfter=6))
        for line in cl(cond_div).split('\n'):
            line=line.strip()
            if not line or 'CONDIZIONI GENERALI' in line.upper(): continue
            if re.match(r'^\d+\.',line): story.append(Spacer(1,3)); story.append(Paragraph(line,B))
            else: story.append(Paragraph(line,N))

    doc.build(story); buf.seek(0)
    return buf

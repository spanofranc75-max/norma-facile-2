"""NCR (Non-Conformity Report) PDF generator for Conto Lavoro."""
from io import BytesIO
from datetime import datetime, timezone

try:
    from services.pdf_template import render_pdf
except ImportError:
    pass


def generate_ncr_pdf(company: dict, commessa: dict, cl: dict) -> BytesIO:
    biz = company.get("business_name", "")
    logo = company.get("logo_url", "")
    comm_num = commessa.get("numero", "")
    logo_html = f'<img src="{logo}" style="max-height:40px;" />' if logo else ""
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    peso_inviato = sum(float(r.get("peso_kg", 0)) for r in (cl.get("righe") or []))
    materiali = ", ".join(r.get("descrizione", "") for r in (cl.get("righe") or []))

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: A4; margin: 15mm; }}
    body {{ font-family: Calibri, Arial, sans-serif; font-size: 10pt; color: #111; }}
    h1 {{ color: #DC2626; font-size: 18pt; text-align: center; margin: 0 0 6px; }}
    h2 {{ color: #1a3a6b; font-size: 12pt; border-bottom: 2px solid #1a3a6b; padding-bottom: 3px; margin: 14px 0 6px; }}
    .header {{ display: table; width: 100%; border-bottom: 2px solid #DC2626; padding-bottom: 6px; margin-bottom: 10px; }}
    .header-left {{ display: table-cell; width: 30%; vertical-align: middle; }}
    .header-center {{ display: table-cell; width: 40%; text-align: center; vertical-align: middle; }}
    .header-right {{ display: table-cell; width: 30%; text-align: right; vertical-align: middle; font-size: 8pt; color: #555; }}
    table.info {{ width: 100%; border-collapse: collapse; margin: 6px 0; }}
    table.info td {{ padding: 4px 8px; font-size: 9pt; border: 1px solid #999; }}
    table.info .lbl {{ font-weight: 700; background: #fef2f2; width: 25%; }}
    .motivo {{ background: #fef2f2; border: 2px solid #DC2626; border-radius: 6px; padding: 10px 14px; margin: 10px 0; }}
    .motivo-title {{ font-weight: 700; color: #DC2626; font-size: 11pt; margin-bottom: 4px; }}
    .sign-area {{ display: table; width: 100%; margin-top: 20px; }}
    .sign-box {{ display: table-cell; width: 50%; padding: 8px; vertical-align: top; }}
    .sign-label {{ font-size: 9pt; font-weight: 600; margin-bottom: 2px; }}
    .sign-line {{ border-bottom: 1px solid #000; height: 35px; margin: 8px 0; }}
    .footer {{ font-size: 7.5pt; color: #777; margin-top: 16px; text-align: center; }}
    </style></head><body>
    <div class="header">
        <div class="header-left">{logo_html}<br/><span style="font-size:9pt;font-weight:700;">{biz}</span></div>
        <div class="header-center"><h1>RAPPORTO DI NON CONFORMITA'</h1><div style="font-size:9pt;color:#DC2626;font-weight:600;">NCR â Non Conformity Report</div></div>
        <div class="header-right">Commessa: {comm_num}<br/>Data: {now}<br/>NCR N.: {cl.get('cl_id','')}</div>
    </div>

    <h2>1. Dati Fornitore / Lavorazione</h2>
    <table class="info">
        <tr><td class="lbl">Fornitore:</td><td>{cl.get('fornitore_nome','')}</td><td class="lbl">Tipo Lavorazione:</td><td style="text-transform:capitalize;">{cl.get('tipo','')}</td></tr>
        <tr><td class="lbl">Commessa:</td><td>{comm_num} â {commessa.get('title','')}</td><td class="lbl">Data Invio:</td><td>{cl.get('data_invio','')}</td></tr>
        <tr><td class="lbl">Materiali:</td><td colspan="3">{materiali}</td></tr>
    </table>

    <h2>2. Dati Rientro</h2>
    <table class="info">
        <tr><td class="lbl">Data Rientro:</td><td>{cl.get('data_rientro','')}</td><td class="lbl">DDT Fornitore N.:</td><td>{cl.get('ddt_fornitore_numero','')}</td></tr>
        <tr><td class="lbl">Peso Inviato:</td><td>{peso_inviato:.1f} kg</td><td class="lbl">Peso Rientrato:</td><td>{cl.get('peso_rientrato_kg',0):.1f} kg</td></tr>
        <tr><td class="lbl">Esito Controllo QC:</td><td colspan="3" style="color:#DC2626;font-weight:700;font-size:12pt;">NON CONFORME</td></tr>
    </table>

    <h2>3. Descrizione Non Conformita'</h2>
    <div class="motivo">
        <div class="motivo-title">Motivo della Non Conformita':</div>
        <div style="min-height:40px;font-size:10pt;">{cl.get('motivo_non_conformita','Da specificare')}</div>
    </div>

    <h2>4. Azioni Richieste</h2>
    <table class="info">
        <tr><td class="lbl">Azione Correttiva:</td><td style="min-height:30px;"></td></tr>
        <tr><td class="lbl">Responsabile:</td><td></td></tr>
        <tr><td class="lbl">Data Prevista:</td><td></td></tr>
    </table>

    <h2>5. Disposizione Materiale</h2>
    <table class="info">
        <tr><td class="lbl">Rilavorazione:</td><td style="width:8%;text-align:center;">&#9744;</td><td class="lbl">Reso al Fornitore:</td><td style="width:8%;text-align:center;">&#9744;</td></tr>
        <tr><td class="lbl">Accettazione in Deroga:</td><td style="text-align:center;">&#9744;</td><td class="lbl">Scarto:</td><td style="text-align:center;">&#9744;</td></tr>
    </table>

    <div class="sign-area">
        <div class="sign-box"><div class="sign-label">Emesso da (QC)</div><div class="sign-line"></div></div>
        <div class="sign-box"><div class="sign-label">Approvato da (Resp. Produzione)</div><div class="sign-line"></div></div>
    </div>
    <div class="footer">Documento generato automaticamente da Norma Facile 2.0 â {now}</div>
    </body></html>"""

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    buf.seek(0)
    return buf

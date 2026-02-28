"""Commessa Dossier Generator — Unified PDF for a single commessa.

Aggregates: Anagrafica, Timeline eventi, Preventivo, Fatture, DDT,
Certificazioni CE, FPC, Sicurezza into a single branded PDF.
"""
import logging
from io import BytesIO
from datetime import datetime
import html as html_mod

logger = logging.getLogger(__name__)

_esc = html_mod.escape


def fmt_it(n) -> str:
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def safe(val) -> str:
    return _esc(str(val or ""))


DOSSIER_CSS = """
@page {
    size: A4;
    margin: 15mm 18mm 18mm 18mm;
    @bottom-center {
        content: "Pagina " counter(page) " di " counter(pages);
        font-size: 8pt; color: #888;
    }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #1E293B; line-height: 1.4; }
h1 { font-size: 18pt; color: #0055FF; margin-bottom: 6mm; }
h2 { font-size: 13pt; color: #1E293B; border-bottom: 2px solid #0055FF; padding-bottom: 2mm; margin: 8mm 0 4mm 0; }
h3 { font-size: 11pt; color: #334155; margin: 4mm 0 2mm 0; }
.cover { text-align: center; padding-top: 60mm; }
.cover .numero { font-size: 28pt; color: #0055FF; font-weight: 700; margin: 6mm 0; }
.cover .title { font-size: 16pt; color: #334155; }
.cover .company { font-size: 11pt; color: #64748B; margin-top: 20mm; }
.section { page-break-before: always; }
.section:first-of-type { page-break-before: auto; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; }
th { background: #F1F5F9; font-weight: 700; text-align: left; padding: 2mm 3mm; font-size: 9pt; border-bottom: 1px solid #CBD5E1; }
td { padding: 2mm 3mm; font-size: 9pt; border-bottom: 1px solid #E2E8F0; }
.mono { font-family: "Courier New", monospace; }
.right { text-align: right; }
.badge { display: inline-block; padding: 1mm 3mm; border-radius: 2mm; font-size: 8pt; font-weight: 700; }
.badge-blue { background: #DBEAFE; color: #1E40AF; }
.badge-green { background: #D1FAE5; color: #065F46; }
.badge-amber { background: #FEF3C7; color: #92400E; }
.badge-red { background: #FEE2E2; color: #991B1B; }
.badge-slate { background: #F1F5F9; color: #475569; }
.timeline-item { padding: 2mm 0 2mm 5mm; border-left: 2px solid #CBD5E1; margin-left: 3mm; }
.timeline-item .time { font-size: 8pt; color: #94A3B8; }
.timeline-item .tipo { font-weight: 700; color: #0055FF; }
.kv { display: flex; margin: 1mm 0; }
.kv .k { width: 40%; font-weight: 600; color: #475569; }
.kv .v { width: 60%; }
.total-row td { font-weight: 700; background: #F8FAFC; }
.page-break { page-break-before: always; }
"""


def _format_date(val):
    if not val:
        return "-"
    if isinstance(val, datetime):
        return val.strftime("%d/%m/%Y %H:%M")
    s = str(val)[:16].replace("T", " ")
    try:
        return datetime.fromisoformat(s.replace("Z", "")).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s


STATO_BADGE = {
    "richiesta": "badge-amber", "bozza": "badge-slate", "rilievo_completato": "badge-amber",
    "firmato": "badge-blue", "in_produzione": "badge-blue", "fatturato": "badge-green",
    "chiuso": "badge-slate", "sospesa": "badge-red",
}


def build_cover(commessa, company):
    c = commessa
    comp_name = safe(company.get("business_name", ""))
    comp_addr = safe(company.get("address", ""))
    comp_piva = safe(company.get("piva", ""))
    return f"""
    <div class="cover">
        <p style="font-size: 12pt; color: #64748B; letter-spacing: 2mm;">DOSSIER COMMESSA</p>
        <p class="numero">{safe(c.get('numero', c.get('commessa_id', '')))}</p>
        <p class="title">{safe(c.get('title', ''))}</p>
        <p style="font-size: 11pt; color: #475569; margin-top: 4mm;">
            Cliente: <strong>{safe(c.get('client_name', '-'))}</strong>
        </p>
        <p style="font-size: 10pt; color: #94A3B8; margin-top: 2mm;">
            Stato: <span class="badge {STATO_BADGE.get(c.get('stato', ''), 'badge-slate')}">{safe(c.get('stato', '').upper())}</span>
        </p>
        <div class="company">
            <p><strong>{comp_name}</strong></p>
            <p>{comp_addr}</p>
            <p>P.IVA: {comp_piva}</p>
        </div>
        <p style="margin-top: 15mm; font-size: 9pt; color: #94A3B8;">
            Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
        </p>
    </div>
    """


def build_anagrafica(commessa):
    c = commessa
    cant = c.get("cantiere", {})
    rows = [
        ("Numero Commessa", c.get("numero", c.get("commessa_id", ""))),
        ("Titolo", c.get("title", "")),
        ("Cliente", c.get("client_name", "-")),
        ("Riferimento", c.get("riferimento", "-")),
        ("Valore", f"EUR {fmt_it(c.get('value', 0))}"),
        ("Priorita'", c.get("priority", "-")),
        ("Scadenza", c.get("deadline", "-")),
    ]
    if cant:
        rows.append(("Cantiere — Indirizzo", cant.get("indirizzo", "-")))
        rows.append(("Cantiere — Citta'", f"{cant.get('citta', '')} {cant.get('cap', '')}".strip() or "-"))
        rows.append(("Cantiere — Contesto", cant.get("contesto", "-")))
        rows.append(("Cantiere — Ambiente", cant.get("ambiente", "-")))

    kv_html = "".join(f'<div class="kv"><div class="k">{safe(k)}</div><div class="v">{safe(v)}</div></div>' for k, v in rows)
    return f'<div class="section"><h2>1. Anagrafica Commessa</h2>{kv_html}</div>'


def build_timeline(commessa):
    eventi = commessa.get("eventi", [])
    if not eventi:
        return '<div class="section"><h2>2. Timeline Eventi</h2><p>Nessun evento registrato.</p></div>'

    items = ""
    for ev in eventi:
        items += f"""
        <div class="timeline-item">
            <span class="time">{_format_date(ev.get('data'))}</span>
            &mdash; <span class="tipo">{safe(ev.get('tipo', ''))}</span>
            <br/><span style="font-size: 9pt; color: #475569;">{safe(ev.get('note', ''))}</span>
            <span style="font-size: 8pt; color: #94A3B8;"> &mdash; {safe(ev.get('operatore_nome', ''))}</span>
        </div>
        """
    return f'<div class="section"><h2>2. Timeline Eventi ({len(eventi)})</h2>{items}</div>'


def build_preventivo_section(prev):
    if not prev:
        return ""
    lines_html = ""
    for ln in prev.get("lines", []):
        lines_html += f"""<tr>
            <td>{safe(ln.get('codice_articolo', ''))}</td>
            <td>{safe(ln.get('description', ''))}</td>
            <td class="right">{safe(ln.get('quantity', ''))}</td>
            <td class="right mono">{fmt_it(ln.get('unit_price') or ln.get('prezzo_netto', 0))}</td>
            <td class="right mono">{fmt_it(ln.get('line_total', 0))}</td>
        </tr>"""

    totals = prev.get("totals", {})
    return f"""
    <div class="section"><h2>3. Preventivo</h2>
    <div class="kv"><div class="k">Numero</div><div class="v mono">{safe(prev.get('number', ''))}</div></div>
    <div class="kv"><div class="k">Oggetto</div><div class="v">{safe(prev.get('subject', ''))}</div></div>
    <div class="kv"><div class="k">Stato</div><div class="v">{safe(prev.get('status', ''))}</div></div>
    <table>
        <tr><th>Codice</th><th>Descrizione</th><th class="right">Qta</th><th class="right">Prezzo</th><th class="right">Importo</th></tr>
        {lines_html}
        <tr class="total-row"><td colspan="4" class="right">TOTALE</td><td class="right mono">EUR {fmt_it(totals.get('total', 0))}</td></tr>
    </table>
    </div>
    """


def build_fatture_section(fatture):
    if not fatture:
        return ""
    rows = ""
    for f in fatture:
        badge_cls = "badge-green" if f.get("status") == "pagata" else "badge-amber" if f.get("status") == "emessa" else "badge-slate"
        rows += f"""<tr>
            <td class="mono">{safe(f.get('document_number', ''))}</td>
            <td>{safe(f.get('issue_date', ''))}</td>
            <td><span class="badge {badge_cls}">{safe(f.get('status', ''))}</span></td>
            <td>{safe(f.get('progressive_type', '-'))}</td>
            <td class="right mono">EUR {fmt_it(f.get('totals', {}).get('total_document', 0))}</td>
        </tr>"""

    return f"""
    <div class="section"><h2>4. Fatturazione</h2>
    <table>
        <tr><th>Numero</th><th>Data</th><th>Stato</th><th>Tipo</th><th class="right">Totale</th></tr>
        {rows}
    </table>
    </div>
    """


def build_ddt_section(ddts):
    if not ddts:
        return ""
    rows = ""
    for d in ddts:
        rows += f"""<tr>
            <td class="mono">{safe(d.get('document_number', ''))}</td>
            <td>{safe(d.get('transport_date', ''))}</td>
            <td>{safe(d.get('ddt_type', ''))}</td>
        </tr>"""
    return f"""
    <div class="section"><h2>5. DDT (Documenti di Trasporto)</h2>
    <table><tr><th>Numero</th><th>Data</th><th>Tipo</th></tr>{rows}</table>
    </div>
    """


def build_fpc_section(fpc):
    if not fpc:
        return ""
    fpc_data = fpc.get("fpc_data", {})
    controls_html = ""
    for ctrl in fpc_data.get("controls", []):
        icon = "&#10003;" if ctrl.get("checked") else "&#10007;"
        color = "color: #065F46;" if ctrl.get("checked") else "color: #991B1B;"
        controls_html += f'<tr><td style="{color} font-weight:700;">{icon}</td><td>{safe(ctrl.get("label", ""))}</td></tr>'

    return f"""
    <div class="section"><h2>6. Progetto FPC EN 1090</h2>
    <div class="kv"><div class="k">Classe Esecuzione</div><div class="v"><span class="badge badge-blue">{safe(fpc_data.get('execution_class', ''))}</span></div></div>
    <div class="kv"><div class="k">WPS</div><div class="v">{safe(fpc_data.get('wps_id', '-'))}</div></div>
    <div class="kv"><div class="k">Saldatore</div><div class="v">{safe(fpc_data.get('welder_name', '-'))}</div></div>
    <div class="kv"><div class="k">CE Generata</div><div class="v">{'Si' if fpc_data.get('ce_label_generated') else 'No'}</div></div>
    <h3>Controlli FPC</h3>
    <table>{controls_html}</table>
    </div>
    """


def build_certificazione_section(cert):
    if not cert:
        return ""
    return f"""
    <div class="section"><h2>7. Certificazione CE</h2>
    <div class="kv"><div class="k">Tipo</div><div class="v">{safe(cert.get('product_type', ''))}</div></div>
    <div class="kv"><div class="k">Normativa</div><div class="v">{safe(cert.get('standard', ''))}</div></div>
    <div class="kv"><div class="k">Stato</div><div class="v">{safe(cert.get('status', ''))}</div></div>
    </div>
    """


async def generate_commessa_dossier_pdf(hub_data, company):
    """Generate a complete dossier PDF from hub data."""
    from services.pdf_template import render_pdf

    commessa = hub_data.get("commessa", {})
    moduli = hub_data.get("moduli_dettaglio", {})

    sections = [
        build_cover(commessa, company),
        build_anagrafica(commessa),
        build_timeline(commessa),
    ]

    if moduli.get("preventivo"):
        sections.append(build_preventivo_section(moduli["preventivo"]))
    if moduli.get("fatture"):
        sections.append(build_fatture_section(moduli["fatture"]))
    if moduli.get("ddt"):
        sections.append(build_ddt_section(moduli["ddt"]))
    if moduli.get("fpc_project"):
        sections.append(build_fpc_section(moduli["fpc_project"]))
    if moduli.get("certificazione"):
        sections.append(build_certificazione_section(moduli["certificazione"]))

    # Disclaimer
    sections.append(f"""
    <div class="page-break">
        <h2>Note e Disclaimer</h2>
        <p style="font-size: 9pt; color: #64748B; margin-top: 4mm;">
            Questo dossier e' stato generato automaticamente dal sistema NormaFacile 2.0
            il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}.
            I dati contenuti provengono dalla commessa <strong>{safe(commessa.get('numero', ''))}</strong>
            e dai relativi moduli collegati. Per qualsiasi chiarimento contattare l'ufficio tecnico.
        </p>
    </div>
    """)

    body = f"""<!DOCTYPE html>
    <html><head><meta charset="utf-8"><style>{DOSSIER_CSS}</style></head>
    <body>{''.join(sections)}</body></html>"""

    output = render_pdf(body)
    return output

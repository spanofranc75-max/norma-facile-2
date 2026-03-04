"""PDF service for DDT (Documento di Trasporto) — WeasyPrint unified template."""
from io import BytesIO
from datetime import datetime
import logging
from services.pdf_template import (
    fmt_it, safe, build_header_html, compute_iva_groups,
    build_totals_html, render_pdf, format_date, COMMON_CSS,
)

logger = logging.getLogger(__name__)

DDT_TYPE_TITLES = {
    "vendita": "DOCUMENTO DI TRASPORTO",
    "conto_lavoro": "DDT CONTO LAVORO",
    "rientro_conto_lavoro": "DDT RIENTRO CONTO LAVORO",
}


def generate_ddt_pdf(doc: dict, company: dict = None) -> BytesIO:
    """Generate DDT PDF with unified template."""
    co = company or {}

    # ── Client from embedded fields (full data) ──
    cl = {
        "business_name": doc.get("client_name", ""),
        "address": doc.get("client_address", ""),
        "cap": doc.get("client_cap", ""),
        "city": doc.get("client_city", ""),
        "province": doc.get("client_province", ""),
        "partita_iva": doc.get("client_piva", ""),
        "codice_fiscale": doc.get("client_cf", ""),
        "pec": doc.get("client_pec", ""),
        "codice_sdi": doc.get("client_sdi", ""),
    }

    header = build_header_html(co, cl, no_client_border=True)

    # ── Title ──
    ddt_type = doc.get("ddt_type", "vendita")
    title = DDT_TYPE_TITLES.get(ddt_type, "DOCUMENTO DI TRASPORTO")
    doc_number = safe(doc.get("number", ""))
    display_num = doc_number.replace("DDT-", "")
    doc_date = format_date(doc.get("data_ora_trasporto") or doc.get("created_at", ""))

    # ── Transport info (DDT-specific) ──
    dest = doc.get("destinazione", {}) or {}
    dest_html = ""
    if dest.get("ragione_sociale"):
        dest_html = f"""
        <div class="info-box">
            <div class="info-box-title">DESTINAZIONE MERCE</div>
            <p><strong>Rag. Sociale:</strong> {safe(dest.get("ragione_sociale"))}</p>
            <p><strong>Indirizzo:</strong> {safe(dest.get("indirizzo"))}
            {safe(dest.get("cap"))} {safe(dest.get("localita"))} ({safe(dest.get("provincia"))})</p>
        </div>"""

    transport_html = f"""
    <table class="transport-table">
        <tr>
            <td class="t-label">Causale trasporto:</td>
            <td>{safe(doc.get("causale_trasporto", "-"))}</td>
            <td class="t-label">Porto:</td>
            <td>{safe(doc.get("porto", "-"))}</td>
        </tr>
        <tr>
            <td class="t-label">Vettore:</td>
            <td>{safe(doc.get("vettore", "-"))}</td>
            <td class="t-label">Mezzo:</td>
            <td>{safe(doc.get("mezzo_trasporto", "-"))}</td>
        </tr>
        <tr>
            <td class="t-label">N. Colli:</td>
            <td>{doc.get("num_colli", 0)}</td>
            <td class="t-label">Peso Lordo:</td>
            <td>{doc.get("peso_lordo_kg", 0)} kg</td>
        </tr>
        <tr>
            <td class="t-label">Aspetto beni:</td>
            <td>{safe(doc.get("aspetto_beni", "-"))}</td>
            <td class="t-label">Peso Netto:</td>
            <td>{doc.get("peso_netto_kg", 0)} kg</td>
        </tr>
    </table>"""

    # ── Line items ──
    lines = doc.get("lines", [])
    show_prices = doc.get("stampa_prezzi", True)

    if show_prices:
        colgroup = """<colgroup>
            <col style="width:8%"><col style="width:35%"><col style="width:7%">
            <col style="width:8%"><col style="width:12%"><col style="width:8%">
            <col style="width:12%"><col style="width:8%">
        </colgroup>"""
        thead = """<tr>
            <th>Codice</th><th>Descrizione</th><th>u.m.</th>
            <th>Q.t&agrave;</th><th>Prezzo</th><th>Sconti</th>
            <th>Importo</th><th>IVA</th>
        </tr>"""
    else:
        colgroup = """<colgroup>
            <col style="width:10%"><col style="width:55%"><col style="width:15%">
            <col style="width:20%">
        </colgroup>"""
        thead = "<tr><th>Codice</th><th>Descrizione</th><th>u.m.</th><th>Q.t&agrave;</th></tr>"

    lines_html = ""
    for ln in lines:
        code = safe(ln.get("codice_articolo") or "")
        desc = safe(ln.get("description") or "").replace("\n", "<br>")
        um = safe(ln.get("unit", "pz"))
        qty = fmt_it(ln.get("quantity", 0))

        if show_prices:
            price = fmt_it(ln.get("unit_price", 0))
            s1 = float(ln.get("sconto_1") or 0)
            s2 = float(ln.get("sconto_2") or 0)
            sc = ""
            if s1 > 0 and s2 > 0:
                sc = f"{fmt_it(s1)}%+{fmt_it(s2)}%"
            elif s1 > 0:
                sc = f"{fmt_it(s1)}%"
            elif s2 > 0:
                sc = f"{fmt_it(s2)}%"
            total = fmt_it(ln.get("line_total", 0))
            vat = safe(str(ln.get("vat_rate", "22")))
            lines_html += f"""<tr>
                <td class="tc">{code}</td><td class="desc-cell">{desc}</td>
                <td class="tc">{um}</td><td class="tr">{qty}</td>
                <td class="tr">{price}</td><td class="tc">{sc}</td>
                <td class="tr">{total}</td><td class="tc">{vat}%</td>
            </tr>"""
        else:
            lines_html += f"""<tr>
                <td class="tc">{code}</td><td class="desc-cell">{desc}</td>
                <td class="tc">{um}</td><td class="tr">{qty}</td>
            </tr>"""

    # ── Totals (only if prices shown) ──
    totals_html = ""
    if show_prices and lines:
        sconto_glob = float(doc.get("sconto_globale") or 0)
        iva_data = compute_iva_groups(lines, sconto_glob)
        totals_html = build_totals_html(iva_data, sconto_glob)

    # ── Notes ──
    notes_html = ""
    if doc.get("notes"):
        notes_html = f'<div class="info-box"><strong>Note:</strong> {safe(doc["notes"]).replace(chr(10), "<br>")}</div>'

    # ── DDT-specific signature section ──
    signatures_html = """
    <table class="signatures-row">
        <tr>
            <td><div class="sig-line-center">Firma mittente</div></td>
            <td><div class="sig-line-center">Firma vettore</div></td>
            <td><div class="sig-line-center">Firma destinatario</div></td>
        </tr>
    </table>"""

    # ── Meta rows ──
    meta_rows = f"""
    <tr><td class="meta-label">DATA:</td><td>{doc_date}</td></tr>
    <tr><td class="meta-label">Tipo DDT:</td><td>{safe(ddt_type.replace("_", " ").title())}</td></tr>"""

    # ── Assemble ──
    body = f"""
    {header}
    <div class="doc-title">
        <h1>{title}</h1>
        <div class="doc-num">{display_num}</div>
    </div>
    <table class="meta-table">{meta_rows}</table>

    {dest_html}
    {transport_html}

    <table class="items-table">
        {colgroup}
        <thead>{thead}</thead>
        <tbody>{lines_html}</tbody>
    </table>

    {notes_html}
    {totals_html}
    {signatures_html}
    """

    return render_pdf(body)

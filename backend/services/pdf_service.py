"""PDF generation service - unified template for all documents."""
from io import BytesIO
from datetime import datetime
from typing import Optional
import logging
from services.pdf_template import (
    fmt_it, safe, build_header_html, compute_iva_groups,
    build_totals_html, build_conditions_html, render_pdf, format_date,
)

logger = logging.getLogger(__name__)

DOC_TYPE_NAMES = {
    "FT": "FATTURA",
    "PRV": "PREVENTIVO",
    "DDT": "DOCUMENTO DI TRASPORTO",
    "NC": "NOTA DI CREDITO",
    "ND": "NOTA DI DEBITO",
}


class PDFService:
    """Generate professional PDFs using unified render_pdf template."""

    @staticmethod
    def format_currency(value: float) -> str:
        return f"\u20ac {fmt_it(value)}"

    @staticmethod
    def format_date(d) -> str:
        return format_date(d)

    @staticmethod
    def generate_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
        """Generate invoice PDF using unified template - same layout as preventivo."""
        co = company or {}
        cl = client or {}

        header = build_header_html(co, cl)

        doc_type = invoice.get("doc_type", "FT")
        doc_name = DOC_TYPE_NAMES.get(doc_type, "FATTURA")
        doc_number = invoice.get("number", "")
        display_num = doc_number.replace("FT-", "").replace("NC-", "").replace("ND-", "").replace("/", "-") if doc_number else ""
        doc_date = format_date(invoice.get("issue_date") or invoice.get("created_at", ""))
        payment_label = safe(invoice.get("payment_type_label") or invoice.get("payment_terms_label", ""))
        doc_type_label = safe(invoice.get("invoice_type_label") or invoice.get("tipo_label") or doc_type)

        # Righe documento
        lines = invoice.get("lines", []) or invoice.get("items", [])
        lines_html = ""
        for ln in lines:
            codice = safe(ln.get("codice_articolo") or ln.get("code") or "")
            desc = safe(ln.get("description") or "").replace("\n", "<br>")
            um = safe(ln.get("unit", "pz"))
            qty = fmt_it(ln.get("quantity", 1))
            price = fmt_it(ln.get("unit_price", 0))
            s1 = float(ln.get("sconto_1") or ln.get("discount", 0) or 0)
            sc = f"{fmt_it(s1)}%" if s1 > 0 else ""
            importo = fmt_it(ln.get("line_total", 0))
            iva = safe(str(ln.get("vat_rate", "22")))
            lines_html += f"""<tr>
                <td class="tc">{codice}</td>
                <td class="desc-cell">{desc}</td>
                <td class="tc">{um}</td>
                <td class="tr">{qty}</td>
                <td class="tr">{price}</td>
                <td class="tc">{sc}</td>
                <td class="tr">{importo}</td>
                <td class="tc">{iva}%</td>
            </tr>"""

        # Totali
        sconto_globale = float(invoice.get("sconto_globale") or 0)
        iva_data = compute_iva_groups(lines, sconto_globale)
        totals_html = build_totals_html(iva_data, sconto_globale)

        # Note
        notes_text = invoice.get("notes", "") or invoice.get("note", "") or ""
        riferimento = safe(invoice.get("riferimento") or invoice.get("rif_ordine") or "")
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {riferimento}</p>' if riferimento else ""
        tech_notes_html = f'<div class="info-box"><strong>Note:</strong> {safe(notes_text).replace(chr(10), "<br>")}</div>' if notes_text.strip() else ""

        # Banca
        bank_name = safe(invoice.get("banca") or "")
        bank_iban = safe(invoice.get("iban") or "")
        if not bank_name and not bank_iban:
            bank = co.get("bank_details", {}) or {}
            bank_accounts = co.get("bank_accounts", []) or []
            if bank_accounts:
                bank_name = safe(bank_accounts[0].get("bank_name", ""))
                bank_iban = safe(bank_accounts[0].get("iban", ""))
            else:
                bank_name = safe(bank.get("bank_name", ""))
                bank_iban = safe(bank.get("iban", ""))
        bank_html = ""
        if bank_name or bank_iban:
            bank_html = '<div class="bank-info">'
            if bank_name: bank_html += f"<p><strong>Banca:</strong> {bank_name}</p>"
            if bank_iban: bank_html += f"<p><strong>IBAN:</strong> {bank_iban}</p>"
            bank_html += "</div>"

        # Scadenze pagamento
        scadenze = invoice.get("scadenze", []) or []
        scadenze_html = ""
        if scadenze:
            rows = "".join(
                f"<tr><td>{safe(s.get('label',''))}</td><td>{format_date(s.get('due_date',''))}</td><td style='text-align:right'>{fmt_it(s.get('amount',0))} \u20ac</td></tr>"
                for s in scadenze
            )
            scadenze_html = f"""<div class="info-box" style="margin-top:6px">
                <strong>Scadenza Pagamenti:</strong>
                <table style="width:100%;margin-top:4px;font-size:8.5px">
                    <tr><th>Tipo</th><th>Data</th><th>Importo</th></tr>
                    {rows}
                </table>
            </div>"""

        # Condizioni
        condizioni_html = build_conditions_html(co, doc_number)

        body = f"""
        {header}
        <div class="doc-title">
            <h1>{doc_name}</h1>
            <div class="doc-num">{safe(display_num)}</div>
        </div>
        <table class="meta-table">
            <tr><td class="meta-label">DATA:</td><td>{doc_date}</td>
                <td class="meta-label">TIPO:</td><td>{doc_type_label}</td></tr>
            <tr><td class="meta-label">Pagamento:</td><td colspan="3">{payment_label}</td></tr>
        </table>

        {ref_note_html}

        <table class="items-table">
            <colgroup>
                <col style="width:8%"><col style="width:38%"><col style="width:6%">
                <col style="width:8%"><col style="width:12%"><col style="width:8%">
                <col style="width:12%"><col style="width:8%">
            </colgroup>
            <thead><tr>
                <th>Codice</th><th>Descrizione</th><th>u.m.</th>
                <th>Quantit&agrave;</th><th>Prezzo</th><th>Sconti</th>
                <th>Importo</th><th>Iva</th>
            </tr></thead>
            <tbody>{lines_html}</tbody>
        </table>

        {tech_notes_html}
        {totals_html}
        {bank_html}
        {scadenze_html}
        {condizioni_html}
        """

        buf = render_pdf(body)
        return buf.getvalue()


pdf_service = PDFService()

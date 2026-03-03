"""PDF generation service for invoices — WeasyPrint unified template."""
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
}

PAYMENT_METHOD_NAMES = {
    "bonifico": "Bonifico Bancario",
    "contanti": "Contanti",
    "carta": "Carta di Credito",
    "assegno": "Assegno",
    "riba": "RiBa",
    "altro": "Altro",
}


class PDFService:
    """Generate professional Italian invoice PDFs via WeasyPrint."""

    @staticmethod
    def format_currency(value: float) -> str:
        return f"\u20ac {fmt_it(value)}"

    @staticmethod
    def format_date(d) -> str:
        return format_date(d)

    @staticmethod
    def generate_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
        co = company or {}
        cl = client or {}

        # ── Title / meta ──
        doc_type = invoice.get("document_type", "FT")
        doc_title = DOC_TYPE_NAMES.get(doc_type, "DOCUMENTO")
        doc_number = safe(invoice.get("document_number", ""))
        display_num = doc_number.replace("FT-", "").replace("NC-", "")
        issue_date = format_date(invoice.get("issue_date", ""))
        due_date = invoice.get("due_date")
        payment_label = invoice.get("payment_terms") or PAYMENT_METHOD_NAMES.get(
            invoice.get("payment_method", ""), invoice.get("payment_method", "")
        )

        header = build_header_html(co, cl)

        # ── Meta rows ──
        meta_rows = f"""
        <tr><td class="meta-label">DATA:</td><td>{issue_date}</td></tr>
        <tr><td class="meta-label">Pagamento:</td><td>{safe(payment_label)}</td></tr>"""
        if due_date:
            meta_rows += f'<tr><td class="meta-label">Scadenza:</td><td>{format_date(due_date)}</td></tr>'

        # ── Line items ──
        lines = invoice.get("lines", [])
        lines_html = ""
        for ln in lines:
            code = safe(ln.get("code") or ln.get("codice_articolo") or "")
            desc = safe(ln.get("description") or "").replace("\n", "<br>")
            qty = fmt_it(ln.get("quantity", 0))
            price = fmt_it(ln.get("unit_price", 0))
            disc = float(ln.get("discount_percent") or 0)
            disc_str = f"{fmt_it(disc)}%" if disc > 0 else ""
            vat = safe(str(ln.get("vat_rate", "22")))
            total = fmt_it(ln.get("line_total", 0))

            lines_html += f"""<tr>
                <td class="tc">{code}</td>
                <td class="desc-cell">{desc}</td>
                <td class="tr">{qty}</td>
                <td class="tr">{price}</td>
                <td class="tc">{disc_str}</td>
                <td class="tc">{vat}%</td>
                <td class="tr">{total}</td>
            </tr>"""

        # ── IVA / totals ──
        # For invoices, use the stored totals if available, otherwise compute
        totals = invoice.get("totals", {})
        stored_vat = totals.get("total_vat", totals.get("vat_total"))

        # Build IVA groups from lines
        iva_data = compute_iva_groups(lines)

        # Extra rows for ritenuta / netto a pagare
        extra_rows = ""
        ritenuta = float(totals.get("ritenuta", 0) or 0)
        if ritenuta > 0:
            netto = iva_data["total"] - ritenuta
            extra_rows = f"""
            <tr class="summary-row">
                <td>Ritenuta d'acconto:</td>
                <td class="tr">-{fmt_it(ritenuta)}</td>
            </tr>
            <tr class="summary-row">
                <td><strong>NETTO A PAGARE:</strong></td>
                <td class="tr"><strong>{fmt_it(netto)} &euro;</strong></td>
            </tr>"""

        totals_html = build_totals_html(iva_data, extra_rows=extra_rows)

        # ── Payment / Bank info (invoice-specific footer) ──
        bank_html = ""
        bank = co.get("bank_details", {}) or {}
        bank_name = safe(bank.get("bank_name", ""))
        bank_iban = safe(bank.get("iban", ""))
        bank_bic = safe(bank.get("bic_swift", ""))

        if bank_name or bank_iban:
            bank_html = f"""
            <div class="bank-info">
                <div class="info-box-title">COORDINATE BANCARIE</div>
                <p><strong>Modalit&agrave; di pagamento:</strong> {safe(payment_label)}</p>
                {"<p><strong>Banca:</strong> " + bank_name + "</p>" if bank_name else ""}
                {"<p><strong>IBAN:</strong> " + bank_iban + "</p>" if bank_iban else ""}
                {"<p><strong>BIC/SWIFT:</strong> " + bank_bic + "</p>" if bank_bic else ""}
            </div>"""

        # ── Notes ──
        notes_html = ""
        if invoice.get("notes"):
            notes_html = f'<div class="info-box"><strong>Note:</strong> {safe(invoice["notes"]).replace(chr(10), "<br>")}</div>'

        # ── Assemble ──
        body = f"""
        {header}
        <div class="doc-title">
            <h1>{doc_title}</h1>
            <div class="doc-num">{display_num}</div>
        </div>
        <table class="meta-table">{meta_rows}</table>

        <table class="items-table">
            <colgroup>
                <col style="width:8%"><col style="width:40%"><col style="width:8%">
                <col style="width:12%"><col style="width:8%"><col style="width:8%"><col style="width:12%">
            </colgroup>
            <thead><tr>
                <th>Codice</th><th>Descrizione</th><th>Q.t&agrave;</th>
                <th>Prezzo</th><th>Sc.%</th><th>IVA</th><th>Importo</th>
            </tr></thead>
            <tbody>{lines_html}</tbody>
        </table>

        {notes_html}
        {totals_html}
        {bank_html}
        """

        buf = render_pdf(body)
        return buf.getvalue()


pdf_service = PDFService()

"""PDF generation service - unified template for all documents."""
from io import BytesIO
from services.pdf_template import (
    fmt_it, safe, build_header_html, compute_iva_groups,
    build_totals_html, render_pdf, format_date,
)

DOC_TYPE_NAMES = {"FT": "FATTURA", "PRV": "PREVENTIVO", "DDT": "DOCUMENTO DI TRASPORTO", "NC": "NOTA DI CREDITO", "ND": "NOTA DI DEBITO"}


class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
        co = company or {}
        cl = client or {}
        header = build_header_html(co, cl)
        doc_type = invoice.get("doc_type", "FT")
        doc_name = DOC_TYPE_NAMES.get(doc_type, "FATTURA")
        doc_number = invoice.get("number", "")
        display_num = doc_number.replace("FT-", "N. ").replace("NC-", "N. ").replace("ND-", "N. ") if doc_number else ""
        doc_date = format_date(invoice.get("issue_date") or invoice.get("created_at", ""))
        payment_label = safe(invoice.get("payment_type_label") or invoice.get("payment_terms_label", ""))
        doc_type_label = safe(invoice.get("invoice_type_label") or invoice.get("tipo_label") or "")
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
            lines_html += f"<tr><td class=\"tc\">{codice}</td><td class=\"desc-cell\">{desc}</td><td class=\"tc\">{um}</td><td class=\"tr\">{qty}</td><td class=\"tr\">{price}</td><td class=\"tc\">{sc}</td><td class=\"tr\">{importo}</td><td class=\"tc\">{iva}%</td></tr>"
        sconto_globale = float(invoice.get("sconto_globale") or 0)
        iva_data = compute_iva_groups(lines, sconto_globale)
        totals_html = build_totals_html(iva_data, sconto_globale)
        notes_text = invoice.get("notes", "") or invoice.get("note", "") or ""
        riferimento = safe(invoice.get("riferimento") or invoice.get("rif_ordine") or "")
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {safe(riferimento)}</p>' if riferimento else ""
        tech_notes_html = f'<p style="margin:4px 0;font-size:9px"><strong>Note:</strong> {safe(notes_text).replace(chr(10), "<br>")}</p>' if notes_text.strip() else ""
        bank_name = safe(invoice.get("banca") or "")
        bank_iban = safe(invoice.get("iban") or "")
        if not bank_name and not bank_iban:
            bank_accounts = co.get("bank_accounts", []) or []
            bank = co.get("bank_details", {}) or {}
            if bank_accounts:
                bank_name = safe(bank_accounts[0].get("bank_name", ""))
                bank_iban = safe(bank_accounts[0].get("iban", ""))
            else:
                bank_name = safe(bank.get("bank_name", ""))
                bank_iban = safe(bank.get("iban", ""))
        bank_parts = []
        if bank_name: bank_parts.append(f"<strong>Banca:</strong> {bank_name}")
        if bank_iban: bank_parts.append(f"<strong>IBAN:</strong> {bank_iban}")
        bank_html = f'<p style="margin:4px 0;font-size:9px">{"  &nbsp;  ".join(bank_parts)}</p>' if bank_parts else ""
        scadenze = invoice.get("scadenze", []) or []
        scadenze_html = ""
        if scadenze:
            rows = "".join(f"<tr><td>{safe(s.get('label',''))}</td><td>{format_date(s.get('due_date',''))}</td><td style='text-align:right'>{fmt_it(s.get('amount',0))} \u20ac</td></tr>" for s in scadenze)
            scadenze_html = f'<p style="margin:6px 0 2px;font-size:9px"><strong>Scadenza Pagamenti:</strong></p><table style="width:60%;margin-left:auto;font-size:8.5px;border-collapse:collapse"><tr style="background:#f0f0f0"><th style="padding:2px 6px;text-align:left">Tipo</th><th style="padding:2px 6px">Data</th><th style="padding:2px 6px;text-align:right">Importo</th></tr>{rows}</table>'
        body = f"""{header}
        <div class="doc-title"><h1>{doc_name}</h1><div class="doc-num">{safe(display_num)}</div></div>
        <table class="meta-table">
            <tr><td class="meta-label">DATA:</td><td>{doc_date}</td><td class="meta-label">TIPO:</td><td>{doc_type_label}</td></tr>
            <tr><td class="meta-label">Pagamento:</td><td colspan="3">{payment_label}</td></tr>
        </table>
        {ref_note_html}
        <table class="items-table">
            <colgroup><col style="width:8%"><col style="width:38%"><col style="width:6%"><col style="width:8%"><col style="width:12%"><col style="width:8%"><col style="width:12%"><col style="width:8%"></colgroup>
            <thead><tr><th>Codice</th><th>Descrizione</th><th>u.m.</th><th>Quantit&agrave;</th><th>Prezzo</th><th>Sconti</th><th>Importo</th><th>Iva</th></tr></thead>
            <tbody>{lines_html}</tbody>
        </table>
        {tech_notes_html}
        {totals_html}
        {bank_html}
        {scadenze_html}"""
        buf = render_pdf(body)
        return buf.getvalue()


pdf_service = PDFService()

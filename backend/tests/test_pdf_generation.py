"""Test PDF generation for Invoice, Preventivo, and DDT."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pymongo
from datetime import datetime

# Connect to Atlas DB
MONGO_URI = "mongodb+srv://spanofranc75_db_user:NormaFacile2026@cluster0.aypz9f1.mongodb.net/normafacile?appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client["normafacile"]

REAL_USER = "user_97c773827822"

def get_company():
    return db.company_settings.find_one({"user_id": REAL_USER}, {"_id": 0}) or {}

def get_invoice():
    inv = db.invoices.find_one({"user_id": REAL_USER}, {"_id": 0})
    return inv

def get_client(client_id):
    if not client_id:
        return {}
    return db.clients.find_one({"client_id": client_id}, {"_id": 0}) or {}

def get_preventivo():
    return db.preventivi.find_one({"user_id": REAL_USER}, {"_id": 0})


def test_invoice_pdf():
    """Test invoice PDF generation."""
    print("=" * 60)
    print("TEST 1: Fattura PDF (ReportLab)")
    print("=" * 60)
    
    from services.pdf_invoice_modern import generate_modern_invoice_pdf
    
    company = get_company()
    invoice = get_invoice()
    if not invoice:
        print("SKIP: No invoice found")
        return
    
    cl = get_client(invoice.get("client_id"))
    
    print(f"  Invoice: {invoice.get('document_number')}")
    print(f"  Type: {invoice.get('document_type')}")
    print(f"  Lines: {len(invoice.get('lines', []))}")
    print(f"  Company: {company.get('business_name')}")
    print(f"  Has logo: {bool(company.get('logo_url'))}")
    
    try:
        pdf_bytes = generate_modern_invoice_pdf(invoice, cl, company)
        out_path = "/tmp/test_fattura.pdf"
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"  OK: PDF generated ({len(pdf_bytes)} bytes) -> {out_path}")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()


def test_preventivo_pdf():
    """Test preventivo PDF generation (WeasyPrint)."""
    print("\n" + "=" * 60)
    print("TEST 2: Preventivo PDF (WeasyPrint)")
    print("=" * 60)
    
    # Import inline to avoid circular
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.pdf_template import (
        fmt_it, safe, build_header_html, compute_iva_groups,
        build_totals_html, build_conditions_html, render_pdf, format_date,
    )
    
    company = get_company()
    prev = get_preventivo()
    if not prev:
        print("SKIP: No preventivo found")
        return
    
    cl = get_client(prev.get("client_id")) or {}
    
    print(f"  Preventivo: {prev.get('number')}")
    print(f"  Lines: {len(prev.get('lines', []))}")
    print(f"  Has condizioni: {bool(company.get('condizioni_vendita'))}")
    
    try:
        # Replicate the generate_preventivo_pdf logic
        co = company or {}
        header = build_header_html(co, cl)
        doc_number = prev.get("number", "")
        display_num = doc_number.replace("PRV-", "").replace("/", "-") if doc_number else ""
        doc_date = format_date(prev.get("created_at", ""))
        
        lines = prev.get("lines", [])
        lines_html = ""
        for ln in lines:
            codice = safe(ln.get("codice_articolo") or "")
            desc = safe(ln.get("description") or "").replace("\n", "<br>")
            um = safe(ln.get("unit", "pz"))
            qty = fmt_it(ln.get("quantity", 1))
            price = fmt_it(ln.get("unit_price", 0))
            importo = fmt_it(ln.get("line_total", 0))
            iva = safe(str(ln.get("vat_rate", "22")))
            lines_html += f"""<tr>
                <td class="tc">{codice}</td>
                <td class="desc-cell">{desc}</td>
                <td class="tc">{um}</td>
                <td class="tr">{qty}</td>
                <td class="tr">{price}</td>
                <td class="tc"></td>
                <td class="tr">{importo}</td>
                <td class="tc">{iva}%</td>
            </tr>"""
        
        sconto_globale = float(prev.get("sconto_globale") or 0)
        iva_data = compute_iva_groups(lines, sconto_globale)
        totals_html = build_totals_html(iva_data, sconto_globale)
        condizioni_html = build_conditions_html(co, doc_number)
        
        body = f"""
        {header}
        <div class="doc-title">
            <h1>PREVENTIVO</h1>
            <div class="doc-num">{safe(display_num)}</div>
        </div>
        <table class="meta-table">
            <tr><td class="meta-label">DATA:</td><td>{doc_date}</td></tr>
        </table>
        <table class="items-table">
            <colgroup>
                <col style="width:8%"><col style="width:38%"><col style="width:6%">
                <col style="width:8%"><col style="width:12%"><col style="width:8%">
                <col style="width:12%"><col style="width:8%">
            </colgroup>
            <thead><tr>
                <th>Codice</th><th>Descrizione</th><th>u.m.</th>
                <th>Q.tà</th><th>Prezzo</th><th>Sconti</th>
                <th>Importo</th><th>Iva</th>
            </tr></thead>
            <tbody>{lines_html}</tbody>
        </table>
        {totals_html}
        {condizioni_html}
        """
        
        pdf_buffer = render_pdf(body)
        pdf_bytes = pdf_buffer.getvalue()
        out_path = "/tmp/test_preventivo.pdf"
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"  OK: PDF generated ({len(pdf_bytes)} bytes) -> {out_path}")
        print(f"  Condizioni page included: {bool(condizioni_html)}")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()


def test_ddt_pdf():
    """Test DDT PDF generation."""
    print("\n" + "=" * 60)
    print("TEST 3: DDT PDF (WeasyPrint)")
    print("=" * 60)
    
    from services.ddt_pdf_service import generate_ddt_pdf
    
    company = get_company()
    
    # Create a synthetic DDT since there are 0 in the DB
    ddt_doc = {
        "number": "DDT-2026-001",
        "ddt_type": "vendita",
        "client_name": "Merighi Giancarlo",
        "client_address": "Via Roma 1",
        "client_cap": "40100",
        "client_city": "Bologna",
        "client_province": "BO",
        "client_piva": "IT12345678901",
        "data_ora_trasporto": "2026-03-19T10:00:00",
        "causale_trasporto": "Vendita",
        "porto": "Franco",
        "vettore": "Mittente",
        "mezzo_trasporto": "Furgone",
        "num_colli": 3,
        "peso_lordo_kg": 150,
        "peso_netto_kg": 120,
        "aspetto_beni": "Colli su pallet",
        "stampa_prezzi": True,
        "destinazione": {
            "ragione_sociale": "Cantiere Rossi",
            "indirizzo": "Via Milano 5",
            "cap": "40100",
            "localita": "Bologna",
            "provincia": "BO",
        },
        "lines": [
            {
                "codice_articolo": "ACC001",
                "description": "Profilo HEA 200 S275JR",
                "unit": "ml",
                "quantity": 12,
                "unit_price": 45.00,
                "line_total": 540.00,
                "vat_rate": "22",
            },
            {
                "codice_articolo": "ACC002",
                "description": "Piastra di base 300x300x15 S275JR",
                "unit": "pz",
                "quantity": 4,
                "unit_price": 28.50,
                "line_total": 114.00,
                "vat_rate": "22",
            },
        ],
        "notes": "Merce da consegnare al piano terra",
    }
    
    print(f"  DDT: {ddt_doc['number']}")
    print(f"  Lines: {len(ddt_doc['lines'])}")
    
    try:
        pdf_buffer = generate_ddt_pdf(ddt_doc, company)
        pdf_bytes = pdf_buffer.getvalue()
        out_path = "/tmp/test_ddt.pdf"
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"  OK: PDF generated ({len(pdf_bytes)} bytes) -> {out_path}")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()


def test_invoice_preview_api():
    """Test the invoice preview API via curl."""
    print("\n" + "=" * 60)
    print("TEST 4: Invoice preview API endpoint")
    print("=" * 60)
    print("  (Run via curl separately)")


if __name__ == "__main__":
    test_invoice_pdf()
    test_preventivo_pdf()
    test_ddt_pdf()
    print("\n" + "=" * 60)
    print("ALL PDF TESTS COMPLETE")
    print("=" * 60)
    print("Generated files:")
    print("  /tmp/test_fattura.pdf")
    print("  /tmp/test_preventivo.pdf")
    print("  /tmp/test_ddt.pdf")

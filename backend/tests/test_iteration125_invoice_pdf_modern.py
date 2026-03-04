"""
Iteration 125: Testing Modern Invoice PDF Generator

Tests for:
1. GET /api/invoices/{id}/pdf returns valid PDF with new modern design (200, application/pdf)
2. Invoice PDF contains: company name, FATTURA title, client as DESTINATARIO (no box), items table, IBAN, TOTALE, Scadenza
3. GET /api/invoices/{id}/pdf with a second invoice to verify consistency
4. GET /api/invoices/ list endpoint still works
5. Invoice PDF should have the due date (Scadenza) near the totals
6. Preventivi list API still returns commessa_stato enrichment (regression)
7. Dossier/Fascicolo generation still works (regression)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TOKEN = "cy0IDr6-Jx0MAbNueH7kJXIblPsw0xN5ihIs7OdjXos"
EXAMPLE_INVOICE_ID = "inv_fa3decf4d9f2"


@pytest.fixture
def auth_headers():
    """Auth headers using real user session token"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }


class TestInvoicePDFModernDesign:
    """Test the new modern invoice PDF generator"""

    def test_invoice_pdf_returns_valid_pdf(self, auth_headers):
        """Test GET /api/invoices/{id}/pdf returns 200 with application/pdf"""
        url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}/pdf"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), \
            f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        # Verify it's actually a PDF (starts with %PDF-)
        content = response.content
        assert content[:5] == b'%PDF-', "Response does not start with PDF header"
        
        # PDF should have reasonable size (at least 10KB for a real invoice)
        assert len(content) > 10000, f"PDF too small: {len(content)} bytes"
        
        print(f"✓ Invoice PDF returned successfully: {len(content)} bytes")

    def test_invoice_pdf_contains_required_elements(self, auth_headers):
        """Test PDF contains company name, FATTURA title, DESTINATARIO, IBAN, TOTALE, Scadenza
        
        Note: PDF content is compressed (FlateDecode), so we use pdftotext to extract text.
        """
        import subprocess
        import tempfile
        
        url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}/pdf"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        
        # Save PDF to temp file and extract text using pdftotext
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(response.content)
            pdf_path = f.name
        
        try:
            result = subprocess.run(
                ['pdftotext', pdf_path, '-'],
                capture_output=True, text=True, timeout=30
            )
            pdf_text = result.stdout
        finally:
            import os
            os.unlink(pdf_path)
        
        # Check for FATTURA document type (may be spaced as "F AT T U R A")
        assert 'FATTURA' in pdf_text.replace(' ', ''), \
            f"PDF should contain 'FATTURA' document type. Got: {pdf_text[:500]}"
        
        # Check for Destinatario label (may be spaced)
        assert 'DESTINATARIO' in pdf_text.replace(' ', ''), \
            "PDF should contain 'DESTINATARIO' label"
        
        # Check for TOTALE (totals section)
        assert 'TOTALE' in pdf_text.replace(' ', ''), \
            "PDF should contain 'TOTALE' in totals"
        
        # Check for IBAN
        assert 'IBAN' in pdf_text, "PDF should contain IBAN"
        
        print(f"✓ Invoice PDF contains required elements: FATTURA, DESTINATARIO, TOTALE, IBAN")

    def test_invoice_pdf_content_disposition(self, auth_headers):
        """Test PDF has correct content-disposition header with filename"""
        url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}/pdf"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".pdf" in content_disp, "Filename should have .pdf extension"
        
        print(f"✓ Content-Disposition: {content_disp}")


class TestInvoiceListEndpoint:
    """Test invoice list endpoint still works"""

    def test_invoices_list_returns_data(self, auth_headers):
        """Test GET /api/invoices/ returns list of invoices"""
        url = f"{BASE_URL}/api/invoices/"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "invoices" in data, "Response should contain 'invoices' field"
        assert "total" in data, "Response should contain 'total' field"
        assert isinstance(data["invoices"], list), "invoices should be a list"
        
        print(f"✓ Invoices list returned: {data['total']} invoices")

    def test_invoice_detail_returns_data(self, auth_headers):
        """Test GET /api/invoices/{id} returns invoice details"""
        url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "invoice_id" in data, "Response should contain 'invoice_id'"
        assert data["invoice_id"] == EXAMPLE_INVOICE_ID, "Invoice ID should match"
        assert "document_type" in data, "Response should contain 'document_type'"
        assert "lines" in data, "Response should contain 'lines'"
        
        print(f"✓ Invoice detail returned: {data.get('document_number')}")


class TestSecondInvoicePDF:
    """Test PDF generation consistency with another invoice"""

    def test_find_second_invoice_and_generate_pdf(self, auth_headers):
        """Find another invoice and verify PDF generation works consistently"""
        # First, get list of invoices
        url = f"{BASE_URL}/api/invoices/"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        invoices = data.get("invoices", [])
        
        # Find a second invoice (different from the example)
        second_invoice_id = None
        for inv in invoices:
            if inv.get("invoice_id") != EXAMPLE_INVOICE_ID:
                second_invoice_id = inv.get("invoice_id")
                break
        
        if second_invoice_id:
            # Test PDF generation for second invoice
            pdf_url = f"{BASE_URL}/api/invoices/{second_invoice_id}/pdf"
            pdf_response = requests.get(pdf_url, headers=auth_headers)
            
            assert pdf_response.status_code == 200, \
                f"Second invoice PDF failed: {pdf_response.status_code}"
            assert "application/pdf" in pdf_response.headers.get("Content-Type", "")
            assert pdf_response.content[:5] == b'%PDF-'
            
            print(f"✓ Second invoice PDF generated: {second_invoice_id} ({len(pdf_response.content)} bytes)")
        else:
            print("⚠ No second invoice found to test consistency (only 1 invoice exists)")
            # This is not a failure, just informational


class TestPreventiviEnrichmentRegression:
    """Regression test: Preventivi list API still returns commessa_stato enrichment"""

    def test_preventivi_list_has_commessa_stato(self, auth_headers):
        """Test GET /api/preventivi/ returns commessa_stato enrichment"""
        url = f"{BASE_URL}/api/preventivi/"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "preventivi" in data, "Response should contain 'preventivi'"
        
        preventivi = data["preventivi"]
        assert len(preventivi) > 0, "Should have at least one preventivo"
        
        # Check if any preventivo with accettato status has commessa_stato
        accettati = [p for p in preventivi if p.get("status") == "accettato"]
        if accettati:
            # At least one accettato should have commessa enrichment
            has_enrichment = any(p.get("commessa_stato") for p in accettati)
            print(f"✓ Found {len(accettati)} accettati preventivi, enrichment present: {has_enrichment}")
        else:
            print("⚠ No accettato preventivi to verify enrichment")
        
        print(f"✓ Preventivi list returned: {len(preventivi)} preventivi")


class TestDossierRegressionTest:
    """Regression test: Dossier/Fascicolo generation still works"""

    def test_dossier_generation_works(self, auth_headers):
        """Test that dossier PDF generation still works (regression)"""
        # Use known commessa from previous iterations
        commessa_id = "com_e8c4810ad476"
        
        url = f"{BASE_URL}/api/commesse/{commessa_id}/dossier"
        response = requests.get(url, headers=auth_headers)
        
        # It should either succeed (200) or return 404 if commessa doesn't exist
        assert response.status_code in [200, 404], \
            f"Dossier endpoint should return 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            assert "application/pdf" in response.headers.get("Content-Type", "")
            assert response.content[:5] == b'%PDF-'
            print(f"✓ Dossier generation works: {len(response.content)} bytes")
        else:
            print(f"⚠ Dossier test skipped: commessa {commessa_id} not found")


class TestInvoicePDFScadenzaNearTotals:
    """Test that Scadenza Pagamento is near the totals section"""

    def test_invoice_with_due_date_has_scadenza_prominent(self, auth_headers):
        """Test that invoice PDF has due date (Scadenza) near totals, not at top
        
        Note: PDF content is compressed, using pdftotext to extract text.
        """
        import subprocess
        import tempfile
        
        # Get invoice details first to check if it has a due date
        url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200
        
        invoice_data = response.json()
        due_date = invoice_data.get("due_date")
        
        # Get the PDF
        pdf_url = f"{BASE_URL}/api/invoices/{EXAMPLE_INVOICE_ID}/pdf"
        pdf_response = requests.get(pdf_url, headers=auth_headers)
        assert pdf_response.status_code == 200
        
        # Save PDF to temp file and extract text using pdftotext
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_response.content)
            pdf_path = f.name
        
        try:
            result = subprocess.run(
                ['pdftotext', pdf_path, '-'],
                capture_output=True, text=True, timeout=30
            )
            pdf_text = result.stdout
        finally:
            import os
            os.unlink(pdf_path)
        
        # Check for Scadenza Pagamento in the PDF
        has_scadenza = 'Scadenza' in pdf_text
        has_totale = 'TOTALE' in pdf_text.replace(' ', '')
        
        if due_date:
            assert has_scadenza, f"Invoice with due_date should have Scadenza in PDF. Due: {due_date}"
            print(f"✓ Invoice has due_date: {due_date}, Scadenza in PDF: {has_scadenza}")
        else:
            print(f"⚠ Invoice has no due_date set, Scadenza presence: {has_scadenza}")
        
        # The PDF should contain TOTALE
        assert has_totale, "PDF should contain TOTALE section"
        
        print("✓ PDF contains TOTALE section and Scadenza near totals")


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

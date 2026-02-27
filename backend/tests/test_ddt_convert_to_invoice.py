"""
DDT Convert to Invoice Feature Tests
- Tests the POST /api/ddt/{ddt_id}/convert-to-invoice endpoint
- Verifies invoice creation from DDT data
- Tests line mapping, totals, status updates
- Tests error cases (404, 409, 422)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('DDT_TEST_SESSION_TOKEN', 'test_session_ddt_convert_' + str(uuid.uuid4().hex[:8]))


@pytest.fixture(scope="module")
def api_client():
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def test_client(api_client):
    """Create a test client for DDT conversion tests."""
    payload = {
        "business_name": "TEST_Convert_Client_SRL",
        "client_type": "cliente",
        "vat_number": f"IT{uuid.uuid4().hex[:11].upper()}",
        "fiscal_code": f"{uuid.uuid4().hex[:16].upper()}",
        "email": "test_convert@example.com",
        "address": "Via Test 123",
        "cap": "20100",
        "city": "Milano",
        "province": "MI"
    }
    response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
    if response.status_code == 201:
        client = response.json()
        yield client
        # Cleanup
        try:
            api_client.delete(f"{BASE_URL}/api/clients/{client['client_id']}")
        except:
            pass
    else:
        pytest.skip(f"Could not create test client: {response.text}")


@pytest.fixture(scope="module")
def cleanup_ids():
    """Track DDT and Invoice IDs for cleanup."""
    ddt_ids = []
    invoice_ids = []
    yield {"ddt": ddt_ids, "invoice": invoice_ids}
    # Cleanup
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    for ddt_id in ddt_ids:
        try:
            session.delete(f"{BASE_URL}/api/ddt/{ddt_id}")
        except:
            pass
    for invoice_id in invoice_ids:
        try:
            session.delete(f"{BASE_URL}/api/invoices/{invoice_id}")
        except:
            pass


class TestConvertDDTToInvoiceBasic:
    """Basic conversion tests - happy path"""
    
    def test_convert_ddt_creates_invoice(self, api_client, test_client, cleanup_ids):
        """POST /api/ddt/{ddt_id}/convert-to-invoice creates a new invoice"""
        # Create DDT with client
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Convert_Basic",
            "payment_type_label": "Bonifico Bancario 30gg",
            "lines": [
                {
                    "codice_articolo": "CONV01",
                    "description": "Profilo IPE 100",
                    "unit": "m",
                    "quantity": 10,
                    "unit_price": 25.0,
                    "sconto_1": 0,
                    "sconto_2": 0,
                    "vat_rate": "22"
                }
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        assert create_resp.status_code == 201, f"Failed to create DDT: {create_resp.text}"
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        # Convert to invoice
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        assert convert_resp.status_code == 200, f"Convert failed: {convert_resp.text}"
        
        result = convert_resp.json()
        assert "invoice_id" in result
        assert "document_number" in result
        assert "message" in result
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        print(f"PASS: DDT converted to invoice {result['document_number']}")
    
    def test_invoice_document_type_is_ft(self, api_client, test_client, cleanup_ids):
        """Created invoice has document_type='FT' (Fattura)"""
        # Create and convert DDT
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_DocType_FT",
            "lines": [{"description": "Doc type test", "quantity": 1, "unit_price": 100, "vat_rate": "22"}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        # Get invoice and verify document_type
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        assert invoice_resp.status_code == 200
        invoice = invoice_resp.json()
        
        assert invoice["document_type"] == "FT", f"Expected FT, got {invoice['document_type']}"
        print(f"PASS: Invoice document_type is 'FT'")
    
    def test_invoice_document_number_format(self, api_client, test_client, cleanup_ids):
        """Invoice document_number follows 'FT-{year}/{seq}' format"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_DocNumber_Format",
            "lines": [{"description": "Number format test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        doc_number = result["document_number"]
        assert doc_number.startswith("FT-"), f"Expected FT- prefix, got {doc_number}"
        assert "/" in doc_number, f"Expected / separator in {doc_number}"
        
        # Extract year and verify
        import re
        match = re.match(r"FT-(\d{4})/(\d+)", doc_number)
        assert match, f"Document number doesn't match pattern FT-YYYY/NNNN: {doc_number}"
        
        from datetime import datetime
        current_year = datetime.now().year
        assert int(match.group(1)) == current_year, f"Year mismatch in {doc_number}"
        
        print(f"PASS: Invoice document_number format correct: {doc_number}")
    
    def test_invoice_status_is_bozza(self, api_client, test_client, cleanup_ids):
        """Created invoice has status='bozza'"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Status_Bozza",
            "lines": [{"description": "Status test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert invoice["status"] == "bozza", f"Expected bozza, got {invoice['status']}"
        print(f"PASS: Invoice status is 'bozza'")


class TestConvertDDTLinesMapping:
    """Tests for invoice lines mapping from DDT lines"""
    
    def test_invoice_lines_mapped_correctly(self, api_client, test_client, cleanup_ids):
        """Invoice lines contain code, description, quantity, unit_price, vat_rate, line_total, vat_amount"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Lines_Mapping",
            "lines": [
                {
                    "codice_articolo": "LMAP01",
                    "description": "Line mapping test item",
                    "unit": "pz",
                    "quantity": 5,
                    "unit_price": 100.0,
                    "sconto_1": 10,  # 10% first discount
                    "sconto_2": 5,   # 5% second discount
                    "vat_rate": "22"
                }
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        # Verify DDT line calculation (for reference)
        ddt_line = ddt["lines"][0]
        # prezzo_netto = 100 * (1-10/100) * (1-5/100) = 100 * 0.9 * 0.95 = 85.5
        assert ddt_line["prezzo_netto"] == 85.5
        # line_total = 5 * 85.5 = 427.5
        assert ddt_line["line_total"] == 427.5
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert len(invoice["lines"]) == 1
        inv_line = invoice["lines"][0]
        
        # Verify mapped fields
        assert inv_line["code"] == "LMAP01"
        assert inv_line["description"] == "Line mapping test item"
        assert inv_line["quantity"] == 5.0
        # unit_price should be prezzo_netto (cascaded discount price)
        assert inv_line["unit_price"] == 85.5, f"Expected 85.5, got {inv_line['unit_price']}"
        assert inv_line["vat_rate"] == "22"
        assert inv_line["line_total"] == 427.5
        # vat_amount = 427.5 * 22% = 94.05
        assert inv_line["vat_amount"] == 94.05, f"Expected 94.05, got {inv_line['vat_amount']}"
        
        print(f"PASS: Invoice lines mapped correctly with cascaded discount price")
    
    def test_multiple_lines_mapped(self, api_client, test_client, cleanup_ids):
        """Multiple DDT lines are all mapped to invoice"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Multi_Lines",
            "lines": [
                {"codice_articolo": "ML01", "description": "Item 1", "quantity": 2, "unit_price": 50, "vat_rate": "22"},
                {"codice_articolo": "ML02", "description": "Item 2", "quantity": 3, "unit_price": 30, "vat_rate": "10"},
                {"codice_articolo": "ML03", "description": "Item 3", "quantity": 1, "unit_price": 100, "vat_rate": "4"}
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert len(invoice["lines"]) == 3, f"Expected 3 lines, got {len(invoice['lines'])}"
        
        codes = [l["code"] for l in invoice["lines"]]
        assert "ML01" in codes
        assert "ML02" in codes
        assert "ML03" in codes
        
        print(f"PASS: All {len(invoice['lines'])} DDT lines mapped to invoice")


class TestConvertDDTTotalsCalculation:
    """Tests for invoice totals calculation"""
    
    def test_invoice_totals_correct(self, api_client, test_client, cleanup_ids):
        """Invoice totals (subtotal, taxable_amount, total_vat, total_document) are correctly computed"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Totals_Calc",
            "sconto_globale": 0,
            "acconto": 0,
            "lines": [
                {"codice_articolo": "TC01", "description": "Item 1", "quantity": 2, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        totals = invoice["totals"]
        # subtotal = 2 * 100 = 200
        assert totals["subtotal"] == 200.0, f"Expected subtotal 200, got {totals['subtotal']}"
        # taxable_amount = 200 (no global discount)
        assert totals["taxable_amount"] == 200.0, f"Expected taxable 200, got {totals['taxable_amount']}"
        # total_vat = 200 * 22% = 44
        assert totals["total_vat"] == 44.0, f"Expected VAT 44, got {totals['total_vat']}"
        # total_document = 200 + 44 = 244
        assert totals["total_document"] == 244.0, f"Expected total 244, got {totals['total_document']}"
        
        print(f"PASS: Invoice totals correctly calculated")
    
    def test_totals_with_global_discount(self, api_client, test_client, cleanup_ids):
        """Global discount from DDT is applied to invoice totals"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Global_Discount",
            "sconto_globale": 10,  # 10% global discount
            "lines": [
                {"codice_articolo": "GD01", "description": "Item", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        totals = invoice["totals"]
        # subtotal = 100
        assert totals["subtotal"] == 100.0
        # taxable_amount = 100 - 10% = 90
        assert totals["taxable_amount"] == 90.0, f"Expected taxable 90, got {totals['taxable_amount']}"
        # total_vat = 22 * 0.9 = 19.8 (VAT also reduced by discount)
        assert abs(totals["total_vat"] - 19.8) < 0.01, f"Expected VAT ~19.8, got {totals['total_vat']}"
        # total_document = 90 + 19.8 = 109.8
        assert abs(totals["total_document"] - 109.8) < 0.01, f"Expected total ~109.8, got {totals['total_document']}"
        
        print(f"PASS: Global discount applied to invoice totals")


class TestConvertDDTStatusUpdate:
    """Tests for DDT status update after conversion"""
    
    def test_ddt_status_updated_to_fatturato(self, api_client, test_client, cleanup_ids):
        """DDT status is updated to 'fatturato' after conversion"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Status_Update",
            "lines": [{"description": "Status update test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        # Verify initial status
        assert ddt["status"] == "non_fatturato"
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        # Get updated DDT
        ddt_resp = api_client.get(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}")
        updated_ddt = ddt_resp.json()
        
        assert updated_ddt["status"] == "fatturato", f"Expected fatturato, got {updated_ddt['status']}"
        print(f"PASS: DDT status updated to 'fatturato'")
    
    def test_ddt_converted_to_field_set(self, api_client, test_client, cleanup_ids):
        """DDT converted_to field is set to the invoice_id after conversion"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Converted_To",
            "lines": [{"description": "Converted to test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        # Get updated DDT
        ddt_resp = api_client.get(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}")
        updated_ddt = ddt_resp.json()
        
        assert updated_ddt.get("converted_to") == result["invoice_id"], \
            f"Expected converted_to={result['invoice_id']}, got {updated_ddt.get('converted_to')}"
        print(f"PASS: DDT converted_to field set to invoice_id")


class TestConvertDDTErrors:
    """Error handling tests"""
    
    def test_duplicate_conversion_returns_409(self, api_client, test_client, cleanup_ids):
        """Attempting to convert already-converted DDT returns 409 Conflict"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Duplicate_Convert",
            "lines": [{"description": "Duplicate test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        # First conversion - should succeed
        convert_resp1 = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        assert convert_resp1.status_code == 200
        result = convert_resp1.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        # Second conversion - should fail with 409
        convert_resp2 = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        assert convert_resp2.status_code == 409, f"Expected 409, got {convert_resp2.status_code}: {convert_resp2.text}"
        
        print(f"PASS: Duplicate conversion returns 409 Conflict")
    
    def test_ddt_without_client_returns_422(self, api_client, cleanup_ids):
        """DDT without client_id returns 422 Unprocessable Entity"""
        ddt_payload = {
            "ddt_type": "vendita",
            "subject": "TEST_No_Client",
            "client_id": None,  # No client
            "lines": [{"description": "No client test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        assert convert_resp.status_code == 422, f"Expected 422, got {convert_resp.status_code}: {convert_resp.text}"
        
        print(f"PASS: DDT without client returns 422")
    
    def test_nonexistent_ddt_returns_404(self, api_client):
        """Converting non-existent DDT returns 404"""
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/nonexistent_ddt_12345/convert-to-invoice")
        assert convert_resp.status_code == 404, f"Expected 404, got {convert_resp.status_code}"
        
        print(f"PASS: Non-existent DDT returns 404")
    
    def test_convert_requires_authentication(self):
        """Convert endpoint requires authentication"""
        # Request without auth token
        response = requests.post(f"{BASE_URL}/api/ddt/some_ddt_id/convert-to-invoice")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"PASS: Convert requires authentication")


class TestConvertDDTInvoiceLink:
    """Tests for invoice-DDT linking"""
    
    def test_invoice_converted_from_field(self, api_client, test_client, cleanup_ids):
        """Created invoice has converted_from field set to ddt_id"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Converted_From",
            "lines": [{"description": "Link test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert invoice.get("converted_from") == ddt["ddt_id"], \
            f"Expected converted_from={ddt['ddt_id']}, got {invoice.get('converted_from')}"
        print(f"PASS: Invoice converted_from field set to ddt_id")
    
    def test_invoice_notes_reference_ddt(self, api_client, test_client, cleanup_ids):
        """Invoice notes contain reference to DDT number"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Notes_Ref",
            "notes": "Original DDT note",
            "lines": [{"description": "Notes test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        # Notes should contain DDT reference
        assert "DDT" in (invoice.get("notes") or ""), f"Notes should reference DDT: {invoice.get('notes')}"
        assert ddt["number"] in (invoice.get("notes") or ""), f"Notes should contain DDT number {ddt['number']}"
        
        print(f"PASS: Invoice notes reference DDT: {invoice.get('notes')}")


class TestConvertDDTPaymentMapping:
    """Tests for payment method/terms mapping"""
    
    def test_payment_method_from_riba(self, api_client, test_client, cleanup_ids):
        """payment_type_label with 'riba' maps to payment_method='riba'"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Payment_Riba",
            "payment_type_label": "RiBa 60 giorni",
            "lines": [{"description": "Payment test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert invoice["payment_method"] == "riba", f"Expected riba, got {invoice['payment_method']}"
        print(f"PASS: Payment method mapped to 'riba'")
    
    def test_payment_terms_from_60gg(self, api_client, test_client, cleanup_ids):
        """payment_type_label with '60' maps to payment_terms='60gg'"""
        ddt_payload = {
            "ddt_type": "vendita",
            "client_id": test_client["client_id"],
            "subject": "TEST_Terms_60gg",
            "payment_type_label": "Bonifico 60 giorni",
            "lines": [{"description": "Terms test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=ddt_payload)
        ddt = create_resp.json()
        cleanup_ids["ddt"].append(ddt["ddt_id"])
        
        convert_resp = api_client.post(f"{BASE_URL}/api/ddt/{ddt['ddt_id']}/convert-to-invoice")
        result = convert_resp.json()
        cleanup_ids["invoice"].append(result["invoice_id"])
        
        invoice_resp = api_client.get(f"{BASE_URL}/api/invoices/{result['invoice_id']}")
        invoice = invoice_resp.json()
        
        assert invoice["payment_terms"] == "60gg", f"Expected 60gg, got {invoice['payment_terms']}"
        print(f"PASS: Payment terms mapped to '60gg'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

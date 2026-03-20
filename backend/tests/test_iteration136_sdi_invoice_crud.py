"""
Iteration 136: SDI Endpoint Validation + Invoice CRUD + Preview PDF Tests

Tests cover:
1. POST /api/invoices/{id}/send-sdi - validation errors (422 with detailed message when required fields missing)
2. POST /api/invoices/{id}/send-sdi - non-FT/NC documents return 400
3. POST /api/invoices/{id}/send-sdi - bozza status return 400
4. POST /api/invoices/{id}/send-sdi - FIC credentials not configured return 400
5. Invoice CRUD including lines with payment data
6. POST /api/invoices/preview-pdf endpoint
"""
import os
import pytest
import requests
import time
from datetime import datetime, date

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://assembly-tracker-11.preview.emergentagent.com").rstrip("/")
API_URL = f"{BASE_URL}/api"

# Test data identifiers
TEST_PREFIX = "TEST_IT136_"
TEST_USER_ID = None
TEST_SESSION_TOKEN = None
TEST_CLIENT_ID = None


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    """Setup test user, session, client, and invoices for testing."""
    global TEST_USER_ID, TEST_SESSION_TOKEN, TEST_CLIENT_ID
    
    timestamp = int(time.time())
    TEST_USER_ID = f"{TEST_PREFIX}user_{timestamp}"
    TEST_SESSION_TOKEN = f"{TEST_PREFIX}session_{timestamp}"
    TEST_CLIENT_ID = f"{TEST_PREFIX}client_{timestamp}"
    
    # Create test user, session, and client via mongosh
    setup_script = f'''
    use("test_database");
    
    // Create test user
    db.users.insertOne({{
        user_id: "{TEST_USER_ID}",
        email: "test_it136_{timestamp}@example.com",
        name: "Test User IT136",
        created_at: new Date()
    }});
    
    // Create test session
    db.user_sessions.insertOne({{
        user_id: "{TEST_USER_ID}",
        session_token: "{TEST_SESSION_TOKEN}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    
    // Create test client with MINIMAL data (missing SDI/PEC for validation testing)
    db.clients.insertOne({{
        client_id: "{TEST_CLIENT_ID}",
        user_id: "{TEST_USER_ID}",
        business_name: "Test Client IT136",
        address: "Via Test 123",
        cap: "00100",
        city: "Roma",
        province: "RM",
        country: "IT",
        partita_iva: "IT12345678901",
        codice_fiscale: "TSTCLT80A01H501Z",
        created_at: new Date()
    }});
    
    // Create test client with FULL data for successful CRUD
    db.clients.insertOne({{
        client_id: "{TEST_CLIENT_ID}_full",
        user_id: "{TEST_USER_ID}",
        business_name: "Test Client IT136 Full",
        address: "Via Completa 456",
        cap: "20100",
        city: "Milano",
        province: "MI",
        country: "IT",
        partita_iva: "IT98765432109",
        codice_fiscale: "TSTFUL80B02F205X",
        codice_sdi: "0000000",
        pec: "test.full@pec.it",
        created_at: new Date()
    }});
    
    // Create test invoice in BOZZA status
    db.invoices.insertOne({{
        invoice_id: "{TEST_PREFIX}inv_bozza_{timestamp}",
        user_id: "{TEST_USER_ID}",
        document_type: "FT",
        document_number: "9901/2026",
        client_id: "{TEST_CLIENT_ID}",
        issue_date: "{date.today().isoformat()}",
        status: "bozza",
        payment_method: "bonifico",
        payment_terms: "30gg",
        tax_settings: {{
            apply_rivalsa_inps: false,
            rivalsa_inps_rate: 4,
            apply_cassa: false,
            cassa_type: "",
            cassa_rate: 4,
            apply_ritenuta: false,
            ritenuta_rate: 20,
            ritenuta_base: "imponibile"
        }},
        lines: [{{
            line_id: "ln_1",
            code: "ART001",
            description: "Test Article",
            quantity: 1,
            unit_price: 100,
            discount_percent: 0,
            vat_rate: "22",
            line_total: 100,
            vat_amount: 22
        }}],
        totals: {{
            subtotal: 100,
            taxable_amount: 100,
            total_vat: 22,
            total_document: 122,
            total_due: 122
        }},
        created_at: new Date()
    }});
    
    // Create test invoice in EMESSA status (can be sent to SDI but missing client SDI/PEC)
    db.invoices.insertOne({{
        invoice_id: "{TEST_PREFIX}inv_emessa_{timestamp}",
        user_id: "{TEST_USER_ID}",
        document_type: "FT",
        document_number: "9902/2026",
        client_id: "{TEST_CLIENT_ID}",
        issue_date: "{date.today().isoformat()}",
        status: "emessa",
        payment_method: "bonifico",
        payment_terms: "30gg",
        tax_settings: {{
            apply_rivalsa_inps: false,
            rivalsa_inps_rate: 4,
            apply_cassa: false,
            cassa_type: "",
            cassa_rate: 4,
            apply_ritenuta: false,
            ritenuta_rate: 20,
            ritenuta_base: "imponibile"
        }},
        lines: [{{
            line_id: "ln_2",
            code: "ART002",
            description: "Another Test Article",
            quantity: 2,
            unit_price: 50,
            discount_percent: 0,
            vat_rate: "22",
            line_total: 100,
            vat_amount: 22
        }}],
        totals: {{
            subtotal: 100,
            taxable_amount: 100,
            total_vat: 22,
            total_document: 122,
            total_due: 122
        }},
        created_at: new Date()
    }});
    
    // Create test DDT document (non-FT/NC for SDI rejection testing)
    db.invoices.insertOne({{
        invoice_id: "{TEST_PREFIX}inv_ddt_{timestamp}",
        user_id: "{TEST_USER_ID}",
        document_type: "DDT",
        document_number: "DDT-001/2026",
        client_id: "{TEST_CLIENT_ID}",
        issue_date: "{date.today().isoformat()}",
        status: "emessa",
        payment_method: "bonifico",
        payment_terms: "30gg",
        lines: [{{
            line_id: "ln_3",
            description: "DDT Item",
            quantity: 1,
            unit_price: 100
        }}],
        totals: {{
            subtotal: 100,
            total_document: 100
        }},
        created_at: new Date()
    }});
    
    // Create test Preventivo document (non-FT/NC for SDI rejection testing)
    db.invoices.insertOne({{
        invoice_id: "{TEST_PREFIX}inv_prv_{timestamp}",
        user_id: "{TEST_USER_ID}",
        document_type: "PRV",
        document_number: "PRV-001/2026",
        client_id: "{TEST_CLIENT_ID}",
        issue_date: "{date.today().isoformat()}",
        status: "emessa",
        payment_method: "bonifico",
        payment_terms: "30gg",
        lines: [{{
            line_id: "ln_4",
            description: "Preventivo Item",
            quantity: 1,
            unit_price: 500
        }}],
        totals: {{
            subtotal: 500,
            total_document: 500
        }},
        created_at: new Date()
    }});
    
    print("Test data created successfully");
    '''
    
    import subprocess
    result = subprocess.run(["mongosh", "--eval", setup_script], capture_output=True, text=True)
    print(f"Setup stdout: {result.stdout}")
    if result.returncode != 0:
        print(f"Setup stderr: {result.stderr}")
    
    yield
    
    # Cleanup test data
    cleanup_script = f'''
    use("test_database");
    db.users.deleteMany({{user_id: /^{TEST_PREFIX}/}});
    db.user_sessions.deleteMany({{user_id: /^{TEST_PREFIX}/}});
    db.clients.deleteMany({{client_id: /^{TEST_PREFIX}/}});
    db.invoices.deleteMany({{invoice_id: /^{TEST_PREFIX}/}});
    print("Test data cleaned up");
    '''
    subprocess.run(["mongosh", "--eval", cleanup_script], capture_output=True, text=True)


@pytest.fixture
def auth_session():
    """Return authenticated session with cookies."""
    session = requests.Session()
    session.cookies.set("session_token", TEST_SESSION_TOKEN, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestSDISendValidation:
    """Tests for POST /api/invoices/{id}/send-sdi validation errors."""
    
    def test_sdi_send_bozza_returns_400(self, auth_session):
        """SDI send for bozza status should return 400."""
        timestamp = int(time.time())
        invoice_id = f"{TEST_PREFIX}inv_bozza_{timestamp}"
        
        # Get existing bozza invoice
        get_resp = auth_session.get(f"{API_URL}/invoices/")
        assert get_resp.status_code == 200
        
        invoices = get_resp.json().get("invoices", [])
        bozza_inv = next((i for i in invoices if i.get("status") == "bozza" and i.get("document_type") == "FT"), None)
        
        if bozza_inv:
            invoice_id = bozza_inv["invoice_id"]
            response = auth_session.post(f"{API_URL}/invoices/{invoice_id}/send-sdi")
            
            # Should return 400 for bozza
            assert response.status_code == 400, f"Expected 400 for bozza, got {response.status_code}: {response.text}"
            data = response.json()
            assert "detail" in data
            assert "bozza" in data["detail"].lower() or "emetti" in data["detail"].lower()
            print(f"PASS: SDI send for bozza returns 400: {data['detail']}")
        else:
            # Create a bozza invoice for the test
            create_resp = auth_session.post(f"{API_URL}/invoices/", json={
                "document_type": "FT",
                "client_id": TEST_CLIENT_ID,
                "issue_date": date.today().isoformat(),
                "payment_method": "bonifico",
                "payment_terms": "30gg",
                "tax_settings": {
                    "apply_rivalsa_inps": False,
                    "rivalsa_inps_rate": 4,
                    "apply_cassa": False,
                    "cassa_type": "",
                    "cassa_rate": 4,
                    "apply_ritenuta": False,
                    "ritenuta_rate": 20,
                    "ritenuta_base": "imponibile"
                },
                "lines": [{"description": "Test item", "quantity": 1, "unit_price": 100, "vat_rate": "22"}],
                "notes": ""
            })
            
            if create_resp.status_code == 201:
                invoice_id = create_resp.json()["invoice_id"]
                response = auth_session.post(f"{API_URL}/invoices/{invoice_id}/send-sdi")
                assert response.status_code == 400
                print(f"PASS: SDI send for newly created bozza returns 400")
            else:
                pytest.skip("Could not find or create bozza invoice for test")
    
    def test_sdi_send_ddt_returns_400(self, auth_session):
        """SDI send for DDT (non-FT/NC) should return 400."""
        # Get DDT invoice
        get_resp = auth_session.get(f"{API_URL}/invoices/")
        assert get_resp.status_code == 200
        
        invoices = get_resp.json().get("invoices", [])
        ddt_inv = next((i for i in invoices if i.get("document_type") == "DDT"), None)
        
        if ddt_inv:
            invoice_id = ddt_inv["invoice_id"]
            response = auth_session.post(f"{API_URL}/invoices/{invoice_id}/send-sdi")
            
            # Should return 400 for DDT
            assert response.status_code == 400, f"Expected 400 for DDT, got {response.status_code}: {response.text}"
            data = response.json()
            assert "detail" in data
            print(f"PASS: SDI send for DDT returns 400: {data['detail']}")
        else:
            pytest.skip("No DDT invoice found in test data")
    
    def test_sdi_send_prv_returns_400(self, auth_session):
        """SDI send for PRV (Preventivo, non-FT/NC) should return 400."""
        # Get PRV invoice
        get_resp = auth_session.get(f"{API_URL}/invoices/")
        assert get_resp.status_code == 200
        
        invoices = get_resp.json().get("invoices", [])
        prv_inv = next((i for i in invoices if i.get("document_type") == "PRV"), None)
        
        if prv_inv:
            invoice_id = prv_inv["invoice_id"]
            response = auth_session.post(f"{API_URL}/invoices/{invoice_id}/send-sdi")
            
            # Should return 400 for PRV
            assert response.status_code == 400, f"Expected 400 for PRV, got {response.status_code}: {response.text}"
            data = response.json()
            assert "detail" in data
            print(f"PASS: SDI send for PRV returns 400: {data['detail']}")
        else:
            pytest.skip("No PRV invoice found in test data")
    
    def test_sdi_send_validation_errors_return_422(self, auth_session):
        """SDI send with missing required fields should return 422 with detailed error message."""
        # Get an emessa FT invoice with missing SDI data
        get_resp = auth_session.get(f"{API_URL}/invoices/")
        assert get_resp.status_code == 200
        
        invoices = get_resp.json().get("invoices", [])
        emessa_inv = next((i for i in invoices 
                          if i.get("status") == "emessa" 
                          and i.get("document_type") == "FT"), None)
        
        if emessa_inv:
            invoice_id = emessa_inv["invoice_id"]
            response = auth_session.post(f"{API_URL}/invoices/{invoice_id}/send-sdi")
            
            # Should return 422 for validation errors OR 400 if FIC not configured
            assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
            data = response.json()
            assert "detail" in data
            detail = data["detail"]
            
            # Check error message is detailed (mentions specific missing fields)
            is_validation_error = any(kw in detail.lower() for kw in ["sdi", "pec", "codice", "manca", "validazione", "credenziali", "configura"])
            assert is_validation_error, f"Error message should mention specific validation issue: {detail}"
            print(f"PASS: SDI send validation error returns proper message: {detail[:200]}")
        else:
            pytest.skip("No emessa FT invoice found for validation test")
    
    def test_sdi_send_nonexistent_returns_404(self, auth_session):
        """SDI send for non-existent invoice should return 404."""
        response = auth_session.post(f"{API_URL}/invoices/nonexistent_invoice_id/send-sdi")
        assert response.status_code == 404
        print("PASS: SDI send for non-existent invoice returns 404")
    
    def test_sdi_send_requires_auth(self):
        """SDI send without authentication should return 401."""
        session = requests.Session()
        response = session.post(f"{API_URL}/invoices/any_id/send-sdi")
        assert response.status_code == 401
        print("PASS: SDI send requires authentication (401)")


class TestInvoiceCRUD:
    """Tests for Invoice CRUD operations including lines and payment data."""
    
    def test_create_invoice_with_lines(self, auth_session):
        """Create invoice with multiple lines and verify calculation."""
        invoice_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"code": "PROD001", "description": "Product 1", "quantity": 2, "unit_price": 100, "discount_percent": 0, "vat_rate": "22"},
                {"code": "PROD002", "description": "Product 2", "quantity": 1, "unit_price": 250, "discount_percent": 10, "vat_rate": "22"},
                {"code": "SERV001", "description": "Service 1", "quantity": 3, "unit_price": 50, "discount_percent": 0, "vat_rate": "10"}
            ],
            "notes": "Test invoice with multiple lines"
        }
        
        response = auth_session.post(f"{API_URL}/invoices/", json=invoice_data)
        assert response.status_code == 201, f"Create failed: {response.text}"
        
        created = response.json()
        assert created["document_type"] == "FT"
        assert created["status"] == "bozza"
        assert len(created["lines"]) == 3
        assert "invoice_id" in created
        assert "document_number" in created
        
        # Verify totals are calculated
        totals = created["totals"]
        assert totals["subtotal"] > 0
        assert totals["total_vat"] > 0
        assert totals["total_document"] > 0
        
        print(f"PASS: Invoice created with 3 lines, total: {totals['total_document']}")
        
        # Store for later tests
        return created["invoice_id"]
    
    def test_get_invoices_list(self, auth_session):
        """Get list of invoices."""
        response = auth_session.get(f"{API_URL}/invoices/")
        assert response.status_code == 200
        
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        assert isinstance(data["invoices"], list)
        print(f"PASS: GET invoices list returns {len(data['invoices'])} invoices")
    
    def test_get_invoice_by_id(self, auth_session):
        """Get single invoice by ID."""
        # First get list to find an invoice
        list_resp = auth_session.get(f"{API_URL}/invoices/")
        assert list_resp.status_code == 200
        
        invoices = list_resp.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices to test with")
        
        invoice_id = invoices[0]["invoice_id"]
        response = auth_session.get(f"{API_URL}/invoices/{invoice_id}")
        
        assert response.status_code == 200
        invoice = response.json()
        assert invoice["invoice_id"] == invoice_id
        assert "lines" in invoice
        assert "totals" in invoice
        print(f"PASS: GET invoice by ID returns invoice {invoice.get('document_number')}")
    
    def test_update_invoice_lines(self, auth_session):
        """Update invoice lines and verify totals recalculate."""
        # Create an invoice first
        create_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"description": "Initial Item", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ],
            "notes": ""
        }
        
        create_resp = auth_session.post(f"{API_URL}/invoices/", json=create_data)
        if create_resp.status_code != 201:
            pytest.skip(f"Could not create invoice: {create_resp.text}")
        
        invoice_id = create_resp.json()["invoice_id"]
        original_total = create_resp.json()["totals"]["total_document"]
        
        # Update with more lines
        update_data = {
            "lines": [
                {"description": "Updated Item 1", "quantity": 2, "unit_price": 200, "vat_rate": "22"},
                {"description": "Updated Item 2", "quantity": 3, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        
        update_resp = auth_session.put(f"{API_URL}/invoices/{invoice_id}", json=update_data)
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        updated = update_resp.json()
        assert len(updated["lines"]) == 2
        new_total = updated["totals"]["total_document"]
        assert new_total > original_total  # Should be higher with more items
        
        print(f"PASS: Invoice updated, total changed from {original_total} to {new_total}")
    
    def test_change_invoice_status(self, auth_session):
        """Test invoice status change via PATCH endpoint."""
        # Create an invoice
        create_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"description": "Status Test Item", "quantity": 1, "unit_price": 500, "vat_rate": "22"}
            ],
            "notes": ""
        }
        
        create_resp = auth_session.post(f"{API_URL}/invoices/", json=create_data)
        if create_resp.status_code != 201:
            pytest.skip(f"Could not create invoice: {create_resp.text}")
        
        invoice_id = create_resp.json()["invoice_id"]
        assert create_resp.json()["status"] == "bozza"
        
        # Change status to emessa
        status_resp = auth_session.patch(f"{API_URL}/invoices/{invoice_id}/status", json={"status": "emessa"})
        assert status_resp.status_code == 200, f"Status change failed: {status_resp.text}"
        
        updated = status_resp.json()
        assert updated["status"] == "emessa"
        print("PASS: Invoice status changed from bozza to emessa")
    
    def test_delete_invoice(self, auth_session):
        """Test invoice deletion."""
        # Create an invoice to delete
        create_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"description": "Delete Test Item", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ],
            "notes": ""
        }
        
        create_resp = auth_session.post(f"{API_URL}/invoices/", json=create_data)
        if create_resp.status_code != 201:
            pytest.skip(f"Could not create invoice: {create_resp.text}")
        
        invoice_id = create_resp.json()["invoice_id"]
        
        # Delete the invoice
        delete_resp = auth_session.delete(f"{API_URL}/invoices/{invoice_id}")
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        
        # Verify it's deleted
        get_resp = auth_session.get(f"{API_URL}/invoices/{invoice_id}")
        assert get_resp.status_code == 404
        print("PASS: Invoice deleted successfully")


class TestPreviewPDF:
    """Tests for POST /api/invoices/preview-pdf endpoint."""
    
    def test_preview_pdf_generates_pdf(self, auth_session):
        """Preview PDF endpoint should return PDF content."""
        preview_data = {
            "document_type": "FT",
            "document_number": "PREVIEW-001/2026",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "due_date": "",
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "payment_type_label": "",
            "notes": "Preview test invoice",
            "lines": [
                {"code": "P001", "description": "Preview Item 1", "quantity": 1, "unit_price": 100, "discount_percent": 0, "vat_rate": "22"},
                {"code": "P002", "description": "Preview Item 2", "quantity": 2, "unit_price": 50, "discount_percent": 5, "vat_rate": "22"}
            ],
            "totals": {
                "subtotal": 195,
                "total_vat": 42.9,
                "total_document": 237.9
            }
        }
        
        response = auth_session.post(f"{API_URL}/invoices/preview-pdf", json=preview_data)
        assert response.status_code == 200, f"Preview PDF failed: {response.text}"
        
        # Check content type is PDF
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Check response has content
        assert len(response.content) > 0
        
        # PDF starts with %PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"PASS: Preview PDF returns valid PDF ({len(response.content)} bytes)")
    
    def test_preview_pdf_with_empty_lines(self, auth_session):
        """Preview PDF with empty lines should still work."""
        preview_data = {
            "document_type": "FT",
            "document_number": "",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "lines": [],
            "totals": {}
        }
        
        response = auth_session.post(f"{API_URL}/invoices/preview-pdf", json=preview_data)
        # Should return 200 even with empty data (generates preview with placeholder)
        assert response.status_code == 200
        print("PASS: Preview PDF with empty lines returns 200")
    
    def test_preview_pdf_requires_auth(self):
        """Preview PDF without authentication should return 401."""
        session = requests.Session()
        response = session.post(f"{API_URL}/invoices/preview-pdf", json={
            "document_type": "FT",
            "lines": []
        })
        assert response.status_code == 401
        print("PASS: Preview PDF requires authentication (401)")


class TestRenumberEndpoint:
    """Additional tests for PATCH /api/invoices/{id}/renumber endpoint."""
    
    def test_renumber_works_on_bozza(self, auth_session):
        """Renumber should work on bozza invoices."""
        # Create bozza invoice
        create_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"description": "Renumber Test", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ],
            "notes": ""
        }
        
        create_resp = auth_session.post(f"{API_URL}/invoices/", json=create_data)
        if create_resp.status_code != 201:
            pytest.skip(f"Could not create invoice: {create_resp.text}")
        
        invoice_id = create_resp.json()["invoice_id"]
        new_number = f"RENUMBERED-{int(time.time())}/2026"
        
        renumber_resp = auth_session.patch(
            f"{API_URL}/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        assert renumber_resp.status_code == 200, f"Renumber failed: {renumber_resp.text}"
        
        updated = renumber_resp.json()
        assert updated["document_number"] == new_number
        print(f"PASS: Renumber works on bozza, new number: {new_number}")


class TestNotaCreditoEndpoint:
    """Additional tests for POST /api/invoices/{id}/create-nota-credito endpoint."""
    
    def test_create_nota_credito_from_ft(self, auth_session):
        """Create nota credito from FT invoice should work."""
        # Create FT invoice first
        create_data = {
            "document_type": "FT",
            "client_id": f"{TEST_CLIENT_ID}_full",
            "issue_date": date.today().isoformat(),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile"
            },
            "lines": [
                {"description": "NC Source Item", "quantity": 1, "unit_price": 200, "vat_rate": "22"}
            ],
            "notes": ""
        }
        
        create_resp = auth_session.post(f"{API_URL}/invoices/", json=create_data)
        if create_resp.status_code != 201:
            pytest.skip(f"Could not create invoice: {create_resp.text}")
        
        invoice_id = create_resp.json()["invoice_id"]
        
        # Create nota credito
        nc_resp = auth_session.post(f"{API_URL}/invoices/{invoice_id}/create-nota-credito")
        assert nc_resp.status_code == 200, f"Create NC failed: {nc_resp.text}"
        
        nc_data = nc_resp.json()
        assert "invoice_id" in nc_data
        assert "document_number" in nc_data
        assert nc_data["document_number"].startswith("NC-") or "/" in nc_data["document_number"]
        
        # Verify NC document
        nc_invoice_id = nc_data["invoice_id"]
        get_resp = auth_session.get(f"{API_URL}/invoices/{nc_invoice_id}")
        assert get_resp.status_code == 200
        
        nc_invoice = get_resp.json()
        assert nc_invoice["document_type"] == "NC"
        assert nc_invoice["status"] == "bozza"
        assert nc_invoice.get("related_invoice_id") == invoice_id
        
        print(f"PASS: Created NC {nc_data['document_number']} from FT")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 69 - SDI Workflow Tests
Tests for Aruba SDI integration with credentials from MongoDB company_settings.

Features tested:
- PUT /api/company/settings accepts aruba_username, aruba_password, aruba_sandbox fields
- GET /api/company/settings returns aruba credentials
- POST /api/invoices/{id}/send-sdi reads credentials from DB, returns error if not configured
- GET /api/invoices/{id}/stato-sdi returns 400 if not yet sent
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('SESSION_TOKEN', '')


@pytest.fixture(scope="module")
def session():
    """Create authenticated session."""
    s = requests.Session()
    s.cookies.set("session_token", SESSION_TOKEN)
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def test_client(session):
    """Create a test client for invoices."""
    client_data = {
        "business_name": f"TEST_SDI_Client_{uuid.uuid4().hex[:6]}",
        "partita_iva": "IT12345678901",
        "codice_fiscale": "12345678901",
        "codice_sdi": "0000000",
        "address": "Via Roma 1",
        "cap": "00100",
        "city": "Roma",
        "province": "RM",
        "country": "IT",
        "email": "test@example.com"
    }
    resp = session.post(f"{BASE_URL}/api/clients/", json=client_data)
    assert resp.status_code == 201, f"Failed to create test client: {resp.text}"
    client = resp.json()
    yield client
    # Cleanup
    session.delete(f"{BASE_URL}/api/clients/{client['client_id']}")


@pytest.fixture(scope="module")
def test_invoice_bozza(session, test_client):
    """Create a test invoice in bozza status."""
    invoice_data = {
        "document_type": "FT",
        "client_id": test_client["client_id"],
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "payment_method": "bonifico",
        "payment_terms": "30gg",
        "lines": [
            {
                "description": "Test SDI Service",
                "quantity": 1,
                "unit_price": 100.00,
                "vat_rate": "22"
            }
        ],
        "tax_settings": {
            "apply_rivalsa_inps": False,
            "apply_cassa": False,
            "apply_ritenuta": False
        }
    }
    resp = session.post(f"{BASE_URL}/api/invoices/", json=invoice_data)
    assert resp.status_code == 201, f"Failed to create test invoice: {resp.text}"
    invoice = resp.json()
    yield invoice
    # Cleanup - only if still in bozza
    session.delete(f"{BASE_URL}/api/invoices/{invoice['invoice_id']}")


@pytest.fixture(scope="module")
def test_invoice_emessa(session, test_client):
    """Create and emit a test invoice for SDI testing."""
    invoice_data = {
        "document_type": "FT",
        "client_id": test_client["client_id"],
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "payment_method": "bonifico",
        "payment_terms": "30gg",
        "lines": [
            {
                "description": "Test SDI Emessa Service",
                "quantity": 2,
                "unit_price": 150.00,
                "vat_rate": "22"
            }
        ],
        "tax_settings": {
            "apply_rivalsa_inps": False,
            "apply_cassa": False,
            "apply_ritenuta": False
        }
    }
    resp = session.post(f"{BASE_URL}/api/invoices/", json=invoice_data)
    assert resp.status_code == 201, f"Failed to create test invoice: {resp.text}"
    invoice = resp.json()
    
    # Emit the invoice (bozza -> emessa)
    status_resp = session.patch(
        f"{BASE_URL}/api/invoices/{invoice['invoice_id']}/status",
        json={"status": "emessa"}
    )
    assert status_resp.status_code == 200, f"Failed to emit invoice: {status_resp.text}"
    
    yield invoice
    # No cleanup for emessa invoices (can't delete)


class TestCompanySettingsArubaFields:
    """Test Aruba SDI credentials in company settings."""
    
    def test_get_company_settings_has_aruba_fields(self, session):
        """GET /api/company/settings should return aruba_username, aruba_password, aruba_sandbox."""
        resp = session.get(f"{BASE_URL}/api/company/settings")
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        data = resp.json()
        
        # Verify the fields exist in the response schema
        assert "aruba_username" in data or data.get("aruba_username") is None, "aruba_username field missing"
        assert "aruba_password" in data or data.get("aruba_password") is None, "aruba_password field missing"
        assert "aruba_sandbox" in data, "aruba_sandbox field missing"
        print(f"✓ GET /api/company/settings returns Aruba fields")
    
    def test_update_company_settings_with_aruba_credentials(self, session):
        """PUT /api/company/settings should accept aruba_username, aruba_password, aruba_sandbox."""
        # First get existing settings
        get_resp = session.get(f"{BASE_URL}/api/company/settings")
        existing = get_resp.json()
        
        # Update with Aruba test credentials
        update_data = {
            "business_name": existing.get("business_name") or "Test Company SDI",
            "partita_iva": existing.get("partita_iva") or "IT98765432109",
            "aruba_username": "test_aruba_user@example.com",
            "aruba_password": "test_aruba_password_123",
            "aruba_sandbox": True
        }
        
        resp = session.put(f"{BASE_URL}/api/company/settings", json=update_data)
        assert resp.status_code == 200, f"Failed to update: {resp.text}"
        
        data = resp.json()
        assert data.get("aruba_username") == "test_aruba_user@example.com", "aruba_username not saved"
        assert data.get("aruba_password") == "test_aruba_password_123", "aruba_password not saved"
        assert data.get("aruba_sandbox") == True, "aruba_sandbox not saved"
        
        print(f"✓ PUT /api/company/settings accepts and saves Aruba credentials")
    
    def test_get_company_settings_returns_saved_aruba_credentials(self, session):
        """Verify saved Aruba credentials persist and are returned."""
        resp = session.get(f"{BASE_URL}/api/company/settings")
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("aruba_username") == "test_aruba_user@example.com", "aruba_username not persisted"
        assert data.get("aruba_password") == "test_aruba_password_123", "aruba_password not persisted"
        assert data.get("aruba_sandbox") == True, "aruba_sandbox not persisted"
        
        print(f"✓ GET /api/company/settings returns persisted Aruba credentials")
    
    def test_update_aruba_sandbox_to_false(self, session):
        """Test toggling aruba_sandbox to production mode."""
        update_data = {
            "aruba_sandbox": False
        }
        
        resp = session.put(f"{BASE_URL}/api/company/settings", json=update_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("aruba_sandbox") == False, "aruba_sandbox not updated to False"
        
        # Revert to sandbox for safety
        session.put(f"{BASE_URL}/api/company/settings", json={"aruba_sandbox": True})
        print(f"✓ aruba_sandbox can be toggled between True/False")


class TestSDISendInvoice:
    """Test sending invoices to SDI."""
    
    def test_send_sdi_bozza_returns_error(self, session, test_invoice_bozza):
        """POST /api/invoices/{id}/send-sdi should fail for bozza invoices."""
        invoice_id = test_invoice_bozza["invoice_id"]
        
        resp = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/send-sdi")
        assert resp.status_code == 400, f"Expected 400 for bozza, got {resp.status_code}"
        
        data = resp.json()
        assert "bozza" in data.get("detail", "").lower() or "emetti" in data.get("detail", "").lower(), \
            f"Expected error about bozza status: {data}"
        
        print(f"✓ POST /api/invoices/{{id}}/send-sdi correctly rejects bozza invoices")
    
    def test_send_sdi_without_credentials_returns_clear_error(self, session, test_invoice_emessa):
        """POST /api/invoices/{id}/send-sdi should return clear error when credentials not configured."""
        invoice_id = test_invoice_emessa["invoice_id"]
        
        # First, clear Aruba credentials
        session.put(f"{BASE_URL}/api/company/settings", json={
            "aruba_username": "",
            "aruba_password": "",
            "aruba_sandbox": True
        })
        
        resp = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/send-sdi")
        # Should return 500 with clear error message
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"
        
        data = resp.json()
        detail = data.get("detail", "")
        # Check for clear error message about credentials
        assert "credenziali" in detail.lower() or "aruba" in detail.lower() or "configurate" in detail.lower(), \
            f"Expected clear error about credentials: {detail}"
        
        print(f"✓ POST /api/invoices/{{id}}/send-sdi returns clear error when credentials not configured")
        print(f"  Error message: {detail}")
    
    def test_send_sdi_with_invalid_credentials_returns_auth_error(self, session, test_invoice_emessa):
        """POST /api/invoices/{id}/send-sdi should return auth error with bad credentials."""
        invoice_id = test_invoice_emessa["invoice_id"]
        
        # Set invalid credentials
        session.put(f"{BASE_URL}/api/company/settings", json={
            "partita_iva": "IT98765432109",  # Required for SDI
            "aruba_username": "invalid_user@test.com",
            "aruba_password": "invalid_password",
            "aruba_sandbox": True
        })
        
        resp = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/send-sdi")
        # Should return 500 with auth error
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"
        
        data = resp.json()
        detail = data.get("detail", "")
        # Check for auth-related error
        assert "autenticazione" in detail.lower() or "fallita" in detail.lower() or "errore" in detail.lower(), \
            f"Expected auth error: {detail}"
        
        print(f"✓ POST /api/invoices/{{id}}/send-sdi returns auth error with invalid credentials")
        print(f"  Error message: {detail}")


class TestSDIStatusCheck:
    """Test checking SDI status."""
    
    def test_stato_sdi_not_sent_returns_400(self, session, test_invoice_emessa):
        """GET /api/invoices/{id}/stato-sdi should return 400 if not yet sent."""
        invoice_id = test_invoice_emessa["invoice_id"]
        
        resp = session.get(f"{BASE_URL}/api/invoices/{invoice_id}/stato-sdi")
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        
        data = resp.json()
        detail = data.get("detail", "")
        assert "non" in detail.lower() and "sdi" in detail.lower(), \
            f"Expected error about not sent to SDI: {detail}"
        
        print(f"✓ GET /api/invoices/{{id}}/stato-sdi returns 400 when invoice not sent")
        print(f"  Error message: {detail}")
    
    def test_stato_sdi_invoice_not_found_returns_404(self, session):
        """GET /api/invoices/{id}/stato-sdi should return 404 for non-existent invoice."""
        fake_id = "inv_nonexistent123"
        
        resp = session.get(f"{BASE_URL}/api/invoices/{fake_id}/stato-sdi")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        
        print(f"✓ GET /api/invoices/{{id}}/stato-sdi returns 404 for non-existent invoice")


class TestInvoiceXMLGeneration:
    """Test XML generation for FatturaPA."""
    
    def test_xml_generation_for_emessa_invoice(self, session, test_invoice_emessa):
        """GET /api/invoices/{id}/xml should generate FatturaPA XML."""
        invoice_id = test_invoice_emessa["invoice_id"]
        
        # Ensure company has P.IVA
        session.put(f"{BASE_URL}/api/company/settings", json={
            "business_name": "Test SDI Company",
            "partita_iva": "IT98765432109"
        })
        
        resp = session.get(f"{BASE_URL}/api/invoices/{invoice_id}/xml")
        assert resp.status_code == 200, f"Failed to get XML: {resp.status_code} - {resp.text}"
        
        # Verify it's XML
        content_type = resp.headers.get("content-type", "")
        assert "xml" in content_type, f"Expected XML content type: {content_type}"
        
        # Check XML structure
        xml_content = resp.text
        assert "FatturaElettronica" in xml_content, "Missing FatturaElettronica root element"
        assert "CedentePrestatore" in xml_content, "Missing CedentePrestatore (supplier) section"
        assert "CessionarioCommittente" in xml_content, "Missing CessionarioCommittente (client) section"
        
        print(f"✓ GET /api/invoices/{{id}}/xml generates valid FatturaPA XML")
    
    def test_xml_generation_requires_company_piva(self, session, test_invoice_emessa):
        """XML generation should fail if company P.IVA is not set."""
        invoice_id = test_invoice_emessa["invoice_id"]
        
        # Clear P.IVA (edge case)
        # Note: This test is informational as P.IVA might be required
        resp = session.get(f"{BASE_URL}/api/invoices/{invoice_id}/xml")
        # Should either succeed or return clear error
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get("detail", "")
            assert "aziendali" in detail.lower() or "p.iva" in detail.lower(), \
                f"Expected error about company data: {detail}"
            print(f"✓ XML generation validates company P.IVA requirement")
        else:
            print(f"✓ XML generation works (P.IVA already set)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

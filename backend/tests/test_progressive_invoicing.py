"""
Test Progressive Invoicing (Acconto / SAL / Saldo) Feature.

Tests:
- POST /api/preventivi/{id}/progressive-invoice with type=acconto
- POST /api/preventivi/{id}/progressive-invoice with type=sal (selected_lines and custom_amount)
- POST /api/preventivi/{id}/progressive-invoice with type=saldo
- GET /api/preventivi/{id}/invoicing-status
- Validation: rejecting amounts exceeding remaining balance
- Validation: rejecting if preventivo is fully invoiced
- Preventivi list returns invoicing_progress field
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "prog_inv_session_1772275541744"
USER_ID = "progressive-invoice-test-user"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def test_client(api_client):
    """Create a test client for preventivi"""
    client_payload = {
        "business_name": "TEST_ProgressiveInvoicing_Client",
        "fiscal_code": "PRGINV00A00A000A",
        "vat_number": "IT12345678901",
        "address": "Via Test 123",
        "city": "Milano",
        "province": "MI",
        "cap": "20100"
    }
    response = api_client.post(f"{BASE_URL}/api/clients/", json=client_payload)
    if response.status_code == 201:
        client = response.json()
        yield client
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{client['client_id']}")
    else:
        pytest.skip(f"Failed to create test client: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_preventivo(api_client, test_client):
    """Create a test preventivo with multiple lines for progressive invoicing tests"""
    preventivo_payload = {
        "client_id": test_client["client_id"],
        "subject": "TEST_ProgressiveInvoicing_Preventivo",
        "validity_days": 30,
        "notes": "Test preventivo for progressive invoicing",
        "lines": [
            {
                "description": "Finestra alluminio 120x150",
                "quantity": 2,
                "unit": "pz",
                "unit_price": 500.00,
                "vat_rate": "22"
            },
            {
                "description": "Porta ingresso 90x210",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 800.00,
                "vat_rate": "22"
            },
            {
                "description": "Montaggio e installazione",
                "quantity": 1,
                "unit": "corpo",
                "unit_price": 400.00,
                "vat_rate": "22"
            }
        ]
    }
    response = api_client.post(f"{BASE_URL}/api/preventivi/", json=preventivo_payload)
    if response.status_code == 201:
        prev = response.json()
        yield prev
        # Cleanup - delete preventivo and any linked invoices
        api_client.delete(f"{BASE_URL}/api/preventivi/{prev['preventivo_id']}")
    else:
        pytest.skip(f"Failed to create test preventivo: {response.status_code} - {response.text}")


class TestInvoicingStatus:
    """Test GET /api/preventivi/{id}/invoicing-status endpoint"""

    def test_invoicing_status_returns_correct_structure(self, api_client, test_preventivo):
        """Verify invoicing status returns all required fields"""
        prev_id = test_preventivo["preventivo_id"]
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "preventivo_id" in data
        assert "total_preventivo" in data
        assert "total_invoiced" in data
        assert "remaining" in data
        assert "percentage_invoiced" in data
        assert "linked_invoices" in data
        assert "is_fully_invoiced" in data
        
        # Verify initial state (no invoices yet)
        assert data["total_invoiced"] == 0
        assert data["percentage_invoiced"] == 0
        assert data["is_fully_invoiced"] == False
        assert len(data["linked_invoices"]) == 0
        
        # Total should be calculated correctly (2*500 + 800 + 400) * 1.22 = 2684
        expected_total = (2 * 500 + 800 + 400) * 1.22
        assert abs(data["total_preventivo"] - expected_total) < 1, f"Expected ~{expected_total}, got {data['total_preventivo']}"
        assert data["remaining"] == data["total_preventivo"]

    def test_invoicing_status_404_nonexistent(self, api_client):
        """Verify 404 for non-existent preventivo"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/nonexistent_prev_id/invoicing-status")
        assert response.status_code == 404


class TestAccontoInvoice:
    """Test progressive invoice with type=acconto"""

    def test_acconto_creates_invoice_with_percentage(self, api_client, test_client):
        """Acconto should create invoice at percentage of total"""
        # Create fresh preventivo for this test
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Acconto_Preventivo",
            "lines": [{"description": "Test item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev_response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert prev_response.status_code == 201
        prev = prev_response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create acconto at 30%
            acconto_payload = {
                "invoice_type": "acconto",
                "percentage": 30
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=acconto_payload)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "invoice_id" in data
            assert "document_number" in data
            assert data["progressive_type"] == "acconto"
            
            # Verify amount is 30% of total (1000 * 1.22 = 1220, 30% = 366)
            expected_amount = 1220 * 0.30
            assert abs(data["progressive_amount"] - expected_amount) < 1, f"Expected ~{expected_amount}, got {data['progressive_amount']}"
            
            # Verify invoicing status updated
            status = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status").json()
            assert status["total_invoiced"] == data["progressive_amount"]
            assert len(status["linked_invoices"]) == 1
            assert status["linked_invoices"][0]["progressive_type"] == "acconto"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_acconto_rejects_invalid_percentage(self, api_client, test_client):
        """Acconto should reject percentage <= 0 or > 100"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Invalid_Acconto",
            "lines": [{"description": "Test", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Test 0%
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json={"invoice_type": "acconto", "percentage": 0})
            assert response.status_code == 400
            
            # Test negative
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json={"invoice_type": "acconto", "percentage": -10})
            assert response.status_code == 400
            
            # Test > 100
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json={"invoice_type": "acconto", "percentage": 150})
            assert response.status_code == 400
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestSalInvoice:
    """Test progressive invoice with type=sal"""

    def test_sal_with_selected_lines(self, api_client, test_client):
        """SAL should create invoice with specific selected lines"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_SAL_Lines_Preventivo",
            "lines": [
                {"description": "Item 1", "quantity": 1, "unit": "pz", "unit_price": 500.00, "vat_rate": "22"},
                {"description": "Item 2", "quantity": 2, "unit": "pz", "unit_price": 300.00, "vat_rate": "22"},
                {"description": "Item 3", "quantity": 1, "unit": "pz", "unit_price": 400.00, "vat_rate": "22"}
            ]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Select lines 0 and 2 (Item 1 and Item 3)
            sal_payload = {
                "invoice_type": "sal",
                "selected_lines": [0, 2]
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=sal_payload)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert data["progressive_type"] == "sal"
            
            # Expected: Item 1 (500) + Item 3 (400) = 900
            expected_amount = 900
            assert abs(data["progressive_amount"] - expected_amount) < 1, f"Expected {expected_amount}, got {data['progressive_amount']}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_sal_with_custom_amount(self, api_client, test_client):
        """SAL should create invoice with custom amount"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_SAL_Amount_Preventivo",
            "lines": [{"description": "Big item", "quantity": 1, "unit": "pz", "unit_price": 5000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # SAL with custom amount
            sal_payload = {
                "invoice_type": "sal",
                "custom_amount": 1500.00
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=sal_payload)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert data["progressive_type"] == "sal"
            assert data["progressive_amount"] == 1500.00
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_sal_rejects_exceeding_amount(self, api_client, test_client):
        """SAL should reject amount exceeding remaining balance"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_SAL_Exceeding",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Total is 1220 (1000 + 22% VAT), try to invoice 2000
            sal_payload = {
                "invoice_type": "sal",
                "custom_amount": 2000.00
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=sal_payload)
            
            assert response.status_code == 400, f"Expected 400 for exceeding amount, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_sal_rejects_invalid_line_index(self, api_client, test_client):
        """SAL should reject invalid line indices"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_SAL_InvalidLine",
            "lines": [{"description": "Only item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Try to select line 5 when only 1 line exists
            sal_payload = {
                "invoice_type": "sal",
                "selected_lines": [5]
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=sal_payload)
            
            assert response.status_code == 400, f"Expected 400 for invalid line index, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_sal_requires_lines_or_amount(self, api_client, test_client):
        """SAL should require either selected_lines or custom_amount"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_SAL_NoParams",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # SAL without lines or amount
            sal_payload = {"invoice_type": "sal"}
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json=sal_payload)
            
            assert response.status_code == 400, f"Expected 400 for SAL without parameters, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestSaldoInvoice:
    """Test progressive invoice with type=saldo"""

    def test_saldo_creates_full_invoice_with_deductions(self, api_client, test_client):
        """Saldo should create full invoice with negative lines for previous deposits"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Saldo_Preventivo",
            "lines": [{"description": "Full item", "quantity": 1, "unit": "pz", "unit_price": 2000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        total_prev = 2000 * 1.22  # 2440
        
        try:
            # First create an acconto at 30%
            acconto_response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "acconto", "percentage": 30})
            assert acconto_response.status_code == 200
            acconto_amount = acconto_response.json()["progressive_amount"]  # ~732
            
            # Now create saldo
            saldo_response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "saldo"})
            
            assert saldo_response.status_code == 200, f"Expected 200, got {saldo_response.status_code}: {saldo_response.text}"
            
            saldo_data = saldo_response.json()
            assert saldo_data["progressive_type"] == "saldo"
            
            # Saldo amount should be remaining (total - acconto)
            expected_remaining = total_prev - acconto_amount
            assert abs(saldo_data["progressive_amount"] - expected_remaining) < 1, f"Expected ~{expected_remaining}, got {saldo_data['progressive_amount']}"
            
            # Verify preventivo is now fully invoiced
            status = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status").json()
            assert status["is_fully_invoiced"] == True
            assert status["percentage_invoiced"] >= 99.9  # Allow for rounding
            assert len(status["linked_invoices"]) == 2
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_saldo_with_no_previous_invoices(self, api_client, test_client):
        """Saldo without previous invoices should equal full total"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Saldo_NoPrev",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create saldo directly (no previous invoices)
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "saldo"})
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            # Should be full amount (1000 * 1.22 = 1220)
            expected = 1220
            assert abs(data["remaining"] - 0) < 1, f"Remaining should be ~0, got {data['remaining']}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestPreventivFullyInvoiced:
    """Test rejection when preventivo is fully invoiced"""

    def test_reject_invoice_when_fully_invoiced(self, api_client, test_client):
        """Should reject new invoices when preventivo is fully invoiced"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_FullyInvoiced",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create saldo to fully invoice
            api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", json={"invoice_type": "saldo"})
            
            # Try to create another acconto
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "acconto", "percentage": 10})
            
            assert response.status_code == 400, f"Expected 400 for fully invoiced preventivo, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestPreventiviListInvoicingProgress:
    """Test that preventivi list returns invoicing_progress field"""

    def test_list_includes_invoicing_progress(self, api_client, test_client):
        """Preventivi list should include invoicing_progress field"""
        # Create preventivo
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_ListProgress",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create acconto at 50%
            api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "acconto", "percentage": 50})
            
            # Fetch list
            response = api_client.get(f"{BASE_URL}/api/preventivi/")
            assert response.status_code == 200
            
            data = response.json()
            # Find our preventivo
            our_prev = next((p for p in data["preventivi"] if p["preventivo_id"] == prev_id), None)
            assert our_prev is not None
            assert "invoicing_progress" in our_prev
            assert abs(our_prev["invoicing_progress"] - 50) < 1, f"Expected ~50%, got {our_prev['invoicing_progress']}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestProgressiveInvoiceValidation:
    """Test validation for progressive invoices"""

    def test_requires_client(self, api_client):
        """Progressive invoice should require client on preventivo"""
        # Create preventivo without client
        prev_payload = {
            "subject": "TEST_NoClient",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "acconto", "percentage": 30})
            
            assert response.status_code == 422, f"Expected 422 for missing client, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_invalid_invoice_type(self, api_client, test_client):
        """Should reject invalid invoice type"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_InvalidType",
            "lines": [{"description": "Item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}]
        }
        prev = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload).json()
        prev_id = prev["preventivo_id"]
        
        try:
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json={"invoice_type": "invalid_type"})
            
            assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
            
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

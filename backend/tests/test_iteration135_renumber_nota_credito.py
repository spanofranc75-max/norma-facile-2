"""
Iteration 135: Renumber Invoice and Create Nota Credito Endpoints Tests

Tests for:
1. PATCH /api/invoices/{id}/renumber - Change document_number on ANY invoice regardless of status
2. POST /api/invoices/{id}/create-nota-credito - Create NC document from FT invoice

Features verified:
- Renumber works on all statuses (bozza, emessa, inviata_sdi, pagata)
- Renumber with empty number returns 400
- Create NC from FT invoice
- NC has document_type='NC', status='bozza', reference to original
- NC copies lines from original
- Create NC fails for non-FT documents (PRV, DDT)
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data prefix for cleanup
TEST_PREFIX = f"TEST_IT135_{int(time.time())}"


@pytest.fixture(scope="module")
def test_setup():
    """Create test user, session, and invoices with various statuses."""
    import subprocess
    
    timestamp = int(time.time() * 1000)
    user_id = f"test-user-{timestamp}"
    session_token = f"test_session_{timestamp}"
    client_id = f"test-client-{timestamp}"
    
    # Create test user, session, client, and test invoices
    mongo_script = f'''
    use('test_database');
    
    // Create test user
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "test.renumber.{timestamp}@example.com",
        name: "Test Renumber User",
        picture: "https://via.placeholder.com/150",
        created_at: new Date()
    }});
    
    // Create session
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    
    // Create test client
    db.clients.insertOne({{
        client_id: "{client_id}",
        user_id: "{user_id}",
        business_name: "Test Client Renumber SRL",
        partita_iva: "IT12345678901",
        codice_fiscale: "12345678901",
        sdi_code: "0000000",
        address: "Via Test 1",
        city: "Milano",
        postal_code: "20100",
        province: "MI",
        country: "IT",
        email: "client@test.com",
        created_at: new Date()
    }});
    
    // Invoice with status 'bozza'
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_bozza",
        user_id: "{user_id}",
        document_type: "FT",
        document_number: "1/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "bozza",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_001",
            description: "Test Item Bozza",
            quantity: 1,
            unit_price: 100,
            vat_rate: "22",
            line_total: 100,
            vat_amount: 22
        }}],
        totals: {{
            subtotal: 100,
            total_vat: 22,
            total_document: 122
        }},
        created_at: new Date()
    }});
    
    // Invoice with status 'emessa'
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_emessa",
        user_id: "{user_id}",
        document_type: "FT",
        document_number: "2/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "emessa",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_002",
            description: "Test Item Emessa",
            quantity: 2,
            unit_price: 200,
            vat_rate: "22",
            line_total: 400,
            vat_amount: 88
        }}],
        totals: {{
            subtotal: 400,
            total_vat: 88,
            total_document: 488
        }},
        created_at: new Date()
    }});
    
    // Invoice with status 'inviata_sdi'
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_inviata",
        user_id: "{user_id}",
        document_type: "FT",
        document_number: "3/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "inviata_sdi",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_003",
            description: "Test Item Inviata SDI",
            quantity: 3,
            unit_price: 300,
            vat_rate: "22",
            line_total: 900,
            vat_amount: 198
        }}],
        totals: {{
            subtotal: 900,
            total_vat: 198,
            total_document: 1098
        }},
        created_at: new Date()
    }});
    
    // Invoice with status 'pagata'
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_pagata",
        user_id: "{user_id}",
        document_type: "FT",
        document_number: "4/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "pagata",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_004",
            description: "Test Item Pagata",
            quantity: 4,
            unit_price: 400,
            vat_rate: "22",
            line_total: 1600,
            vat_amount: 352
        }}],
        totals: {{
            subtotal: 1600,
            total_vat: 352,
            total_document: 1952
        }},
        created_at: new Date()
    }});
    
    // Preventivo (PRV) - for testing create-nota-credito failure case
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_prv",
        user_id: "{user_id}",
        document_type: "PRV",
        document_number: "PRV-1/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "bozza",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_005",
            description: "Test Item PRV",
            quantity: 1,
            unit_price: 500,
            vat_rate: "22",
            line_total: 500,
            vat_amount: 110
        }}],
        totals: {{
            subtotal: 500,
            total_vat: 110,
            total_document: 610
        }},
        created_at: new Date()
    }});
    
    // DDT - for testing create-nota-credito failure case
    db.invoices.insertOne({{
        invoice_id: "inv_{TEST_PREFIX}_ddt",
        user_id: "{user_id}",
        document_type: "DDT",
        document_number: "DDT-1/2026",
        client_id: "{client_id}",
        issue_date: "2026-01-15",
        status: "bozza",
        payment_method: "bonifico",
        lines: [{{
            line_id: "ln_006",
            description: "Test Item DDT",
            quantity: 1,
            unit_price: 600,
            vat_rate: "22",
            line_total: 600,
            vat_amount: 132
        }}],
        totals: {{
            subtotal: 600,
            total_vat: 132,
            total_document: 732
        }},
        created_at: new Date()
    }});
    
    print("Setup complete: user=" + "{user_id}");
    '''
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Mongo setup stderr: {result.stderr}")
        raise Exception(f"Failed to setup test data: {result.stderr}")
    
    print(f"Setup output: {result.stdout}")
    
    yield {
        "user_id": user_id,
        "session_token": session_token,
        "client_id": client_id,
        "invoice_bozza_id": f"inv_{TEST_PREFIX}_bozza",
        "invoice_emessa_id": f"inv_{TEST_PREFIX}_emessa",
        "invoice_inviata_id": f"inv_{TEST_PREFIX}_inviata",
        "invoice_pagata_id": f"inv_{TEST_PREFIX}_pagata",
        "invoice_prv_id": f"inv_{TEST_PREFIX}_prv",
        "invoice_ddt_id": f"inv_{TEST_PREFIX}_ddt",
    }
    
    # Cleanup
    cleanup_script = f'''
    use('test_database');
    db.users.deleteMany({{ user_id: "{user_id}" }});
    db.user_sessions.deleteMany({{ user_id: "{user_id}" }});
    db.clients.deleteMany({{ user_id: "{user_id}" }});
    db.invoices.deleteMany({{ user_id: "{user_id}" }});
    print("Cleanup complete");
    '''
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True, text=True)


@pytest.fixture
def auth_session(test_setup):
    """Return requests session with auth header."""
    session = requests.Session()
    session.cookies.set("session_token", test_setup["session_token"])
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestRenumberInvoice:
    """Test PATCH /api/invoices/{id}/renumber endpoint."""
    
    def test_renumber_bozza_invoice(self, auth_session, test_setup):
        """Renumber should work on bozza status invoice."""
        invoice_id = test_setup["invoice_bozza_id"]
        new_number = f"{TEST_PREFIX}/BOZZA-RENUMBERED"
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("document_number") == new_number, f"Expected {new_number}, got {data.get('document_number')}"
        print(f"✅ Renumber bozza invoice: {new_number}")
    
    def test_renumber_emessa_invoice(self, auth_session, test_setup):
        """Renumber should work on emessa status invoice (not just bozza)."""
        invoice_id = test_setup["invoice_emessa_id"]
        new_number = f"{TEST_PREFIX}/EMESSA-RENUMBERED"
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("document_number") == new_number, f"Expected {new_number}, got {data.get('document_number')}"
        print(f"✅ Renumber emessa invoice: {new_number}")
    
    def test_renumber_inviata_sdi_invoice(self, auth_session, test_setup):
        """Renumber should work on inviata_sdi status invoice."""
        invoice_id = test_setup["invoice_inviata_id"]
        new_number = f"{TEST_PREFIX}/INVIATA-RENUMBERED"
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("document_number") == new_number, f"Expected {new_number}, got {data.get('document_number')}"
        print(f"✅ Renumber inviata_sdi invoice: {new_number}")
    
    def test_renumber_pagata_invoice(self, auth_session, test_setup):
        """Renumber should work on pagata status invoice."""
        invoice_id = test_setup["invoice_pagata_id"]
        new_number = f"{TEST_PREFIX}/PAGATA-RENUMBERED"
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("document_number") == new_number, f"Expected {new_number}, got {data.get('document_number')}"
        print(f"✅ Renumber pagata invoice: {new_number}")
    
    def test_renumber_empty_number_returns_400(self, auth_session, test_setup):
        """Renumber with empty document_number should return 400."""
        invoice_id = test_setup["invoice_bozza_id"]
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": ""}
        )
        
        assert response.status_code == 400, f"Expected 400 for empty number, got {response.status_code}: {response.text}"
        print("✅ Renumber with empty number returns 400")
    
    def test_renumber_whitespace_only_returns_400(self, auth_session, test_setup):
        """Renumber with whitespace-only document_number should return 400."""
        invoice_id = test_setup["invoice_bozza_id"]
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": "   "}
        )
        
        assert response.status_code == 400, f"Expected 400 for whitespace-only, got {response.status_code}: {response.text}"
        print("✅ Renumber with whitespace-only returns 400")
    
    def test_renumber_nonexistent_invoice_returns_404(self, auth_session, test_setup):
        """Renumber on non-existent invoice should return 404."""
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/nonexistent-invoice-id/renumber",
            json={"document_number": "SHOULD-NOT-WORK"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Renumber non-existent invoice returns 404")
    
    def test_renumber_returns_updated_invoice(self, auth_session, test_setup):
        """Renumber should return the full updated invoice object."""
        invoice_id = test_setup["invoice_bozza_id"]
        new_number = f"{TEST_PREFIX}/FULL-RETURN-TEST"
        
        response = auth_session.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/renumber",
            json={"document_number": new_number}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify full invoice structure returned
        assert "invoice_id" in data, "Response should contain invoice_id"
        assert "document_type" in data, "Response should contain document_type"
        assert "status" in data, "Response should contain status"
        assert "document_number" in data, "Response should contain document_number"
        assert data["document_number"] == new_number
        print(f"✅ Renumber returns full updated invoice: invoice_id={data.get('invoice_id')}, doc_num={data.get('document_number')}")


class TestCreateNotaCredito:
    """Test POST /api/invoices/{id}/create-nota-credito endpoint."""
    
    def test_create_nc_from_ft_invoice(self, auth_session, test_setup):
        """Create NC from FT invoice should succeed."""
        invoice_id = test_setup["invoice_emessa_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "invoice_id" in data, "Response should contain new NC invoice_id"
        assert "document_number" in data, "Response should contain NC document_number"
        assert "message" in data, "Response should contain success message"
        
        nc_id = data.get("invoice_id")
        nc_number = data.get("document_number")
        print(f"✅ Created NC from FT: NC id={nc_id}, number={nc_number}")
        
        # Store NC id for cleanup
        test_setup["created_nc_id"] = nc_id
        return nc_id
    
    def test_nc_has_correct_document_type(self, auth_session, test_setup):
        """Created NC should have document_type='NC'."""
        # First create a NC
        invoice_id = test_setup["invoice_bozza_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        nc_id = response.json().get("invoice_id")
        
        # Fetch the NC to verify document_type
        nc_response = auth_session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        assert nc_response.status_code == 200, f"Failed to fetch NC: {nc_response.text}"
        
        nc_data = nc_response.json()
        assert nc_data.get("document_type") == "NC", f"Expected document_type='NC', got {nc_data.get('document_type')}"
        print(f"✅ NC has correct document_type: {nc_data.get('document_type')}")
    
    def test_nc_has_bozza_status(self, auth_session, test_setup):
        """Created NC should have status='bozza'."""
        invoice_id = test_setup["invoice_pagata_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200
        nc_id = response.json().get("invoice_id")
        
        # Fetch the NC to verify status
        nc_response = auth_session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        assert nc_response.status_code == 200
        
        nc_data = nc_response.json()
        assert nc_data.get("status") == "bozza", f"Expected status='bozza', got {nc_data.get('status')}"
        print(f"✅ NC has correct status: {nc_data.get('status')}")
    
    def test_nc_references_original_invoice(self, auth_session, test_setup):
        """Created NC should reference the original invoice."""
        invoice_id = test_setup["invoice_inviata_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200
        nc_id = response.json().get("invoice_id")
        
        # Fetch the NC to verify reference
        nc_response = auth_session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        assert nc_response.status_code == 200
        
        nc_data = nc_response.json()
        assert nc_data.get("related_invoice_id") == invoice_id, f"Expected related_invoice_id={invoice_id}, got {nc_data.get('related_invoice_id')}"
        assert "related_invoice_number" in nc_data, "NC should have related_invoice_number"
        print(f"✅ NC references original: related_invoice_id={nc_data.get('related_invoice_id')}, related_invoice_number={nc_data.get('related_invoice_number')}")
    
    def test_nc_copies_lines_from_original(self, auth_session, test_setup):
        """Created NC should copy lines from the original invoice."""
        invoice_id = test_setup["invoice_emessa_id"]
        
        # First, get the original invoice lines
        original_response = auth_session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        assert original_response.status_code == 200
        original_lines = original_response.json().get("lines", [])
        
        # Create NC
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200
        nc_id = response.json().get("invoice_id")
        
        # Fetch the NC to verify lines
        nc_response = auth_session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        assert nc_response.status_code == 200
        
        nc_data = nc_response.json()
        nc_lines = nc_data.get("lines", [])
        
        assert len(nc_lines) == len(original_lines), f"NC should have same number of lines. Original: {len(original_lines)}, NC: {len(nc_lines)}"
        
        # Verify line content matches (excluding line_id which should be new)
        for i, (orig, nc_line) in enumerate(zip(original_lines, nc_lines)):
            assert nc_line.get("description") == orig.get("description"), f"Line {i} description mismatch"
            assert nc_line.get("quantity") == orig.get("quantity"), f"Line {i} quantity mismatch"
            assert nc_line.get("unit_price") == orig.get("unit_price"), f"Line {i} unit_price mismatch"
            assert nc_line.get("line_id") != orig.get("line_id"), f"Line {i} should have new line_id"
        
        print(f"✅ NC copied {len(nc_lines)} lines from original")
    
    def test_create_nc_from_prv_fails(self, auth_session, test_setup):
        """Create NC from PRV (Preventivo) should fail with 400."""
        invoice_id = test_setup["invoice_prv_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 400, f"Expected 400 for PRV, got {response.status_code}: {response.text}"
        print("✅ Create NC from PRV correctly returns 400")
    
    def test_create_nc_from_ddt_fails(self, auth_session, test_setup):
        """Create NC from DDT should fail with 400."""
        invoice_id = test_setup["invoice_ddt_id"]
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 400, f"Expected 400 for DDT, got {response.status_code}: {response.text}"
        print("✅ Create NC from DDT correctly returns 400")
    
    def test_create_nc_nonexistent_invoice_returns_404(self, auth_session, test_setup):
        """Create NC from non-existent invoice should return 404."""
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/nonexistent-invoice-id/create-nota-credito"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Create NC from non-existent invoice returns 404")
    
    def test_nc_has_storno_note(self, auth_session, test_setup):
        """Created NC should have a note referencing the original invoice."""
        invoice_id = test_setup["invoice_bozza_id"]
        
        # Get original doc number
        original_response = auth_session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        original_doc_num = original_response.json().get("document_number", "")
        
        response = auth_session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/create-nota-credito"
        )
        
        assert response.status_code == 200
        nc_id = response.json().get("invoice_id")
        
        # Fetch the NC to verify notes
        nc_response = auth_session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        nc_data = nc_response.json()
        
        notes = nc_data.get("notes", "")
        assert "storno" in notes.lower() or "credito" in notes.lower(), f"Notes should mention storno or credito: {notes}"
        print(f"✅ NC has storno note: {notes}")


class TestAuthRequired:
    """Test that endpoints require authentication."""
    
    def test_renumber_without_auth_returns_401(self, test_setup):
        """Renumber without auth should return 401."""
        response = requests.patch(
            f"{BASE_URL}/api/invoices/{test_setup['invoice_bozza_id']}/renumber",
            json={"document_number": "SHOULD-FAIL"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Renumber without auth returns 401")
    
    def test_create_nc_without_auth_returns_401(self, test_setup):
        """Create NC without auth should return 401."""
        response = requests.post(
            f"{BASE_URL}/api/invoices/{test_setup['invoice_bozza_id']}/create-nota-credito",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Create NC without auth returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

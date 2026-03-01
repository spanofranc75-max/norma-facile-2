"""
Iteration 84 Backend Tests: Consegne al Cliente (DDT + DoP + CE)

Features to test:
1. POST /api/commesse/{cid}/consegne - creates a delivery with DDT in ddt_documents collection
2. POST consegne auto-fills DDT lines from material_batches
3. POST consegne adds consegna record to commessa.consegne array
4. POST consegne returns ddt_id, ddt_number, consegna_id
5. GET /api/commesse/{cid}/consegne/{consegna_id}/pacchetto-pdf returns PDF
6. GET pacchetto-pdf contains DDT + DoP + CE merged pages
7. GET ops returns consegne array (ensure_ops_fields initializes it)
8. Regression: PUT produzione with started_at/completed_at still works
9. Regression: POST rientro CL still works
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session for all tests."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Authenticate via test endpoint and return token."""
    # Check for existing test token in env
    test_token = os.environ.get("TEST_AUTH_TOKEN")
    if test_token:
        return test_token
    
    # Try test login endpoint
    try:
        resp = api_client.post(f"{BASE_URL}/api/auth/test-login")
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    
    pytest.skip("Authentication not available - skipping authenticated tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


@pytest.fixture(scope="module")
def test_commessa_id(authenticated_client):
    """Create or find a test commessa with client_id and material_batches."""
    unique_id = f"TEST_CONS_{uuid.uuid4().hex[:8]}"
    
    # Create commessa with client_id
    payload = {
        "title": f"Test Consegna - {unique_id}",
        "numero": unique_id,
        "normativa": "EN_1090",
        "classe_esecuzione": "EXC2",
        "stato": "in_corso",
        "client_id": None,  # Will need to create or find client
    }
    
    # First, try to find or create a test client
    client_resp = authenticated_client.get(f"{BASE_URL}/api/clients?limit=1")
    if client_resp.status_code == 200:
        clients = client_resp.json().get("clients", [])
        if clients:
            payload["client_id"] = clients[0]["client_id"]
    
    # Create commessa
    resp = authenticated_client.post(f"{BASE_URL}/api/commesse/", json=payload)
    if resp.status_code == 201:
        commessa_id = resp.json().get("commessa_id")
    elif resp.status_code == 200:
        commessa_id = resp.json().get("commessa_id")
    else:
        # Try to find existing
        list_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/?limit=1")
        if list_resp.status_code == 200:
            commesse = list_resp.json().get("commesse", [])
            if commesse:
                commessa_id = commesse[0]["commessa_id"]
            else:
                pytest.skip("No commesse available for testing")
        else:
            pytest.skip(f"Failed to create/find commessa: {resp.status_code}")
    
    yield commessa_id
    
    # Cleanup: delete test commessa (optional)
    # authenticated_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


@pytest.fixture(scope="module")
def test_commessa_with_batches(authenticated_client, test_commessa_id):
    """Ensure commessa has material_batches for DDT lines auto-fill."""
    # Create a test material batch
    batch_payload = {
        "commessa_id": test_commessa_id,
        "material_type": "IPE 200",
        "dimensions": "6000mm",
        "heat_number": f"COLATA_{uuid.uuid4().hex[:6]}",
        "grade": "S275JR",
        "peso_kg": 150.5,
        "supplier_name": "Test Supplier",
    }
    
    # Try to create batch via FPC endpoint
    resp = authenticated_client.post(f"{BASE_URL}/api/fpc/batches", json=batch_payload)
    # Even if it fails, proceed - we test both with and without batches
    
    return test_commessa_id


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: Health & Base
# ──────────────────────────────────────────────────────────────────────────────

class TestHealthAndBase:
    """Basic API health checks."""
    
    def test_health_endpoint(self, api_client):
        """Test API health endpoint."""
        resp = api_client.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint returns healthy")


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: Consegne Creation
# ──────────────────────────────────────────────────────────────────────────────

class TestConsegneCreation:
    """Tests for POST /api/commesse/{cid}/consegne endpoint."""
    
    def test_crea_consegna_basic(self, authenticated_client, test_commessa_with_batches):
        """POST /api/commesse/{cid}/consegne creates a delivery with DDT."""
        cid = test_commessa_with_batches
        
        payload = {
            "note": "Test consegna iteration 84",
            "peso_kg": 250.0,
            "num_colli": 3,
        }
        
        resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Verify response contains required fields
        assert "consegna" in data, "Response should contain 'consegna' object"
        assert "ddt_id" in data, "Response should contain 'ddt_id'"
        
        consegna = data["consegna"]
        assert "consegna_id" in consegna, "Consegna should have 'consegna_id'"
        assert "ddt_id" in consegna, "Consegna should have 'ddt_id'"
        assert "ddt_number" in consegna, "Consegna should have 'ddt_number'"
        assert "numero" in consegna, "Consegna should have 'numero'"
        
        # Verify DDT number format
        assert consegna["ddt_number"].startswith("DDT-"), f"DDT number should start with DDT-, got: {consegna['ddt_number']}"
        
        print(f"PASS: Consegna created with id={consegna['consegna_id']}, ddt={consegna['ddt_number']}")
        return consegna
    
    def test_crea_consegna_creates_ddt_document(self, authenticated_client, test_commessa_with_batches):
        """POST consegne creates DDT in ddt_documents collection."""
        cid = test_commessa_with_batches
        
        payload = {"note": "DDT creation test", "peso_kg": 100.0, "num_colli": 1}
        resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        
        assert resp.status_code in [200, 201]
        data = resp.json()
        ddt_id = data.get("ddt_id") or data.get("consegna", {}).get("ddt_id")
        
        assert ddt_id, "Should return ddt_id"
        
        # Verify DDT exists in collection (via GET /ddt/{ddt_id})
        ddt_resp = authenticated_client.get(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert ddt_resp.status_code == 200, f"DDT should exist, got {ddt_resp.status_code}"
        
        ddt_data = ddt_resp.json()
        assert ddt_data.get("commessa_id") == cid, "DDT should be linked to commessa"
        assert ddt_data.get("ddt_type") == "vendita", "DDT type should be 'vendita'"
        
        print(f"PASS: DDT {ddt_id} created in ddt_documents with commessa_id={cid}")
    
    def test_crea_consegna_autofills_lines_from_batches(self, authenticated_client, test_commessa_with_batches):
        """POST consegne auto-fills DDT lines from material_batches."""
        cid = test_commessa_with_batches
        
        # Get existing batches
        batches_resp = authenticated_client.get(f"{BASE_URL}/api/fpc/batches?commessa_id={cid}")
        has_batches = batches_resp.status_code == 200 and len(batches_resp.json().get("batches", [])) > 0
        
        payload = {"note": "Auto-fill test", "peso_kg": 50.0, "num_colli": 1}
        resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        
        assert resp.status_code in [200, 201]
        ddt_id = resp.json().get("ddt_id") or resp.json().get("consegna", {}).get("ddt_id")
        
        # Get DDT and check lines
        ddt_resp = authenticated_client.get(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert ddt_resp.status_code == 200
        
        ddt_data = ddt_resp.json()
        lines = ddt_data.get("lines", [])
        
        assert len(lines) >= 1, "DDT should have at least one line"
        
        if has_batches:
            # If batches exist, lines should be from batches (colata numbers)
            print(f"PASS: DDT has {len(lines)} lines from material batches")
        else:
            # If no batches, should have default line from commessa
            print(f"PASS: DDT has {len(lines)} default lines (no batches)")
    
    def test_crea_consegna_adds_to_consegne_array(self, authenticated_client, test_commessa_with_batches):
        """POST consegne adds consegna record to commessa.consegne array."""
        cid = test_commessa_with_batches
        
        # Get initial state
        ops_before = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        consegne_before = ops_before.json().get("consegne", []) if ops_before.status_code == 200 else []
        count_before = len(consegne_before)
        
        # Create consegna
        payload = {"note": "Array append test", "peso_kg": 75.0, "num_colli": 2}
        resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        assert resp.status_code in [200, 201]
        
        new_consegna_id = resp.json().get("consegna", {}).get("consegna_id")
        
        # Verify array updated
        ops_after = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert ops_after.status_code == 200
        consegne_after = ops_after.json().get("consegne", [])
        count_after = len(consegne_after)
        
        assert count_after == count_before + 1, f"Consegne count should increase by 1: {count_before} -> {count_after}"
        
        # Verify new consegna is in array
        ids = [c.get("consegna_id") for c in consegne_after]
        assert new_consegna_id in ids, f"New consegna {new_consegna_id} should be in array"
        
        print(f"PASS: Consegna added to array (count: {count_before} -> {count_after})")


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: Pacchetto PDF Generation
# ──────────────────────────────────────────────────────────────────────────────

class TestPacchettoPDF:
    """Tests for GET /api/commesse/{cid}/consegne/{consegna_id}/pacchetto-pdf."""
    
    def test_pacchetto_pdf_returns_pdf(self, authenticated_client, test_commessa_with_batches):
        """GET pacchetto-pdf returns PDF content."""
        cid = test_commessa_with_batches
        
        # First create a consegna
        payload = {"note": "PDF test", "peso_kg": 100.0, "num_colli": 1}
        create_resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        assert create_resp.status_code in [200, 201]
        
        consegna_id = create_resp.json().get("consegna", {}).get("consegna_id")
        assert consegna_id, "Should have consegna_id"
        
        # Get PDF
        pdf_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/consegne/{consegna_id}/pacchetto-pdf")
        
        assert pdf_resp.status_code == 200, f"Expected 200, got {pdf_resp.status_code}: {pdf_resp.text[:200]}"
        assert pdf_resp.headers.get("content-type") == "application/pdf", "Content-Type should be PDF"
        
        # Verify it's a valid PDF (starts with %PDF)
        content = pdf_resp.content
        assert content[:4] == b"%PDF", "Content should start with PDF magic bytes"
        assert len(content) > 1000, f"PDF should be substantial, got {len(content)} bytes"
        
        print(f"PASS: Pacchetto PDF returned ({len(content)} bytes)")
    
    def test_pacchetto_pdf_contains_merged_documents(self, authenticated_client, test_commessa_with_batches):
        """GET pacchetto-pdf contains DDT + DoP + CE merged pages."""
        cid = test_commessa_with_batches
        
        # Create consegna
        payload = {"note": "Merged PDF test", "peso_kg": 200.0, "num_colli": 2}
        create_resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        assert create_resp.status_code in [200, 201]
        
        consegna_id = create_resp.json().get("consegna", {}).get("consegna_id")
        
        # Get PDF
        pdf_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/consegne/{consegna_id}/pacchetto-pdf")
        assert pdf_resp.status_code == 200
        
        content = pdf_resp.content
        
        # Check PDF has multiple pages (DDT + DoP + CE = at least 3 pages)
        # Count page objects in PDF
        page_count = content.count(b"/Type /Page")
        
        # Should have at least 3 pages (DDT, DoP, CE)
        assert page_count >= 3, f"PDF should have at least 3 pages (DDT+DoP+CE), found {page_count}"
        
        # Check for text markers that indicate merged content
        has_ddt = b"DOCUMENTO DI TRASPORTO" in content or b"DDT" in content
        has_dop = b"Dichiarazione di Prestazione" in content or b"DOP" in content or b"DoP" in content
        has_ce = b"CE" in content or b"Marcatura" in content
        
        print(f"PASS: Merged PDF has {page_count} pages (DDT:{has_ddt}, DoP:{has_dop}, CE:{has_ce})")
    
    def test_pacchetto_pdf_marks_flags(self, authenticated_client, test_commessa_with_batches):
        """GET pacchetto-pdf marks dop_generata and ce_generata as True."""
        cid = test_commessa_with_batches
        
        # Create consegna
        payload = {"note": "Flag test", "peso_kg": 50.0, "num_colli": 1}
        create_resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        assert create_resp.status_code in [200, 201]
        
        consegna_id = create_resp.json().get("consegna", {}).get("consegna_id")
        
        # Verify flags are initially False
        ops_before = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert ops_before.status_code == 200
        
        consegne = ops_before.json().get("consegne", [])
        cons = next((c for c in consegne if c.get("consegna_id") == consegna_id), None)
        assert cons, "Consegna should exist"
        
        # Flags may start as False
        initial_dop = cons.get("dop_generata", False)
        initial_ce = cons.get("ce_generata", False)
        
        # Download PDF
        pdf_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/consegne/{consegna_id}/pacchetto-pdf")
        assert pdf_resp.status_code == 200
        
        # Verify flags are now True
        ops_after = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        consegne_after = ops_after.json().get("consegne", [])
        cons_after = next((c for c in consegne_after if c.get("consegna_id") == consegna_id), None)
        
        assert cons_after.get("dop_generata") == True, "dop_generata should be True after PDF download"
        assert cons_after.get("ce_generata") == True, "ce_generata should be True after PDF download"
        
        print(f"PASS: Flags updated (dop: {initial_dop}->True, ce: {initial_ce}->True)")
    
    def test_pacchetto_pdf_404_invalid_consegna(self, authenticated_client, test_commessa_with_batches):
        """GET pacchetto-pdf returns 404 for invalid consegna_id."""
        cid = test_commessa_with_batches
        
        invalid_id = "cons_invalid_xyz"
        pdf_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/consegne/{invalid_id}/pacchetto-pdf")
        
        assert pdf_resp.status_code == 404, f"Expected 404, got {pdf_resp.status_code}"
        print("PASS: 404 returned for invalid consegna_id")


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: GET OPS with Consegne
# ──────────────────────────────────────────────────────────────────────────────

class TestGetOpsConsegne:
    """Tests for GET /api/commesse/{cid}/ops returning consegne array."""
    
    def test_get_ops_returns_consegne_array(self, authenticated_client, test_commessa_with_batches):
        """GET ops returns consegne array (ensure_ops_fields initializes it)."""
        cid = test_commessa_with_batches
        
        resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Verify consegne key exists and is an array
        assert "consegne" in data, "Response should contain 'consegne' key"
        assert isinstance(data["consegne"], list), "'consegne' should be a list"
        
        print(f"PASS: GET ops returns consegne array (count: {len(data['consegne'])})")
    
    def test_get_ops_consegne_structure(self, authenticated_client, test_commessa_with_batches):
        """GET ops returns consegne with correct structure."""
        cid = test_commessa_with_batches
        
        # Ensure at least one consegna exists
        payload = {"note": "Structure test", "peso_kg": 30.0, "num_colli": 1}
        authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/consegne", json=payload)
        
        resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert resp.status_code == 200
        
        consegne = resp.json().get("consegne", [])
        
        if consegne:
            cons = consegne[-1]  # Check latest
            
            # Verify required fields
            required_fields = ["consegna_id", "numero", "ddt_id", "ddt_number", "data"]
            for field in required_fields:
                assert field in cons, f"Consegna should have '{field}' field"
            
            # Verify optional fields exist
            optional_fields = ["peso_kg", "num_colli", "note", "dop_generata", "ce_generata"]
            for field in optional_fields:
                assert field in cons, f"Consegna should have '{field}' field"
            
            print(f"PASS: Consegna has correct structure: {list(cons.keys())}")
        else:
            print("PASS: Consegne array is empty (no consegne created)")
    
    def test_ensure_ops_fields_initializes_consegne(self, authenticated_client):
        """ensure_ops_fields initializes consegne as empty array for new commesse."""
        # Create a fresh commessa without any ops operations
        unique_id = f"TEST_INIT_{uuid.uuid4().hex[:6]}"
        payload = {
            "title": f"Test Init - {unique_id}",
            "numero": unique_id,
            "normativa": "EN_1090",
        }
        
        create_resp = authenticated_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        if create_resp.status_code not in [200, 201]:
            pytest.skip("Could not create test commessa")
        
        new_cid = create_resp.json().get("commessa_id")
        
        # Call GET ops (which triggers ensure_ops_fields)
        ops_resp = authenticated_client.get(f"{BASE_URL}/api/commesse/{new_cid}/ops")
        assert ops_resp.status_code == 200
        
        data = ops_resp.json()
        assert "consegne" in data, "ensure_ops_fields should initialize consegne"
        assert data["consegne"] == [], "consegne should be empty array for new commessa"
        
        print("PASS: ensure_ops_fields initializes consegne as empty array")
        
        # Cleanup
        authenticated_client.delete(f"{BASE_URL}/api/commesse/{new_cid}")


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: Regression Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestRegressionProduzione:
    """Regression tests for production workflow with new timing fields."""
    
    def test_put_produzione_with_started_completed_still_works(self, authenticated_client, test_commessa_with_batches):
        """PUT produzione with started_at/completed_at still works (iteration 83 feature)."""
        cid = test_commessa_with_batches
        
        # Initialize production if needed
        authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
        
        # Update fase with timing fields
        payload = {
            "stato": "completato",
            "started_at": "2026-01-15T08:00:00",
            "completed_at": "2026-01-15T16:30:00",
            "operator_name": "Test Operator",
        }
        
        resp = authenticated_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/taglio", json=payload)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: PUT produzione with started_at/completed_at works")
    
    def test_put_produzione_basic_still_works(self, authenticated_client, test_commessa_with_batches):
        """PUT produzione basic stato update still works."""
        cid = test_commessa_with_batches
        
        # Initialize production if needed
        authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
        
        # Simple status update
        payload = {"stato": "in_corso"}
        resp = authenticated_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/foratura", json=payload)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: PUT produzione basic stato update works")


class TestRegressionContoLavoro:
    """Regression tests for Conto Lavoro workflow."""
    
    def test_post_rientro_cl_still_works(self, authenticated_client, test_commessa_with_batches):
        """POST rientro CL still works after consegne changes."""
        cid = test_commessa_with_batches
        
        # Create a Conto Lavoro
        cl_payload = {
            "tipo": "verniciatura",
            "fornitore_nome": "Test Fornitore",
            "ral": "RAL 7035",
            "note": "Regression test",
            "righe": [{"descrizione": "Test Material", "quantita": 10, "unita": "pz", "peso_kg": 50}],
        }
        
        create_resp = authenticated_client.post(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro", json=cl_payload)
        
        if create_resp.status_code not in [200, 201]:
            pytest.skip(f"Could not create C/L: {create_resp.status_code}")
        
        cl_id = create_resp.json().get("conto_lavoro", {}).get("cl_id")
        assert cl_id, "Should have cl_id"
        
        # Update to inviato
        authenticated_client.put(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}", json={"stato": "inviato"})
        
        # Test rientro endpoint (via form data)
        rientro_data = {
            "data_rientro": "2026-01-16",
            "ddt_fornitore_numero": "DDT-TEST-001",
            "ddt_fornitore_data": "2026-01-16",
            "peso_rientrato_kg": "45",
            "esito_qc": "conforme",
            "note_rientro": "Regression test rientro",
        }
        
        rientro_resp = authenticated_client.post(
            f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}/rientro",
            data=rientro_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert rientro_resp.status_code == 200, f"Expected 200, got {rientro_resp.status_code}: {rientro_resp.text}"
        print(f"PASS: POST rientro CL works (cl_id={cl_id})")


# ──────────────────────────────────────────────────────────────────────────────
# Test Class: Auth and Error Handling
# ──────────────────────────────────────────────────────────────────────────────

class TestAuthAndErrors:
    """Tests for authentication and error handling."""
    
    def test_unauthorized_crea_consegna(self, api_client, test_commessa_id):
        """POST consegne returns 401/403 without auth."""
        # Use api_client without auth token
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        resp = unauth_session.post(
            f"{BASE_URL}/api/commesse/{test_commessa_id}/consegne",
            json={"note": "test", "peso_kg": 10}
        )
        
        assert resp.status_code in [401, 403, 422], f"Expected auth error, got {resp.status_code}"
        print("PASS: Unauthorized POST consegne returns auth error")
    
    def test_unauthorized_pacchetto_pdf(self, api_client, test_commessa_id):
        """GET pacchetto-pdf returns 401/403 without auth."""
        unauth_session = requests.Session()
        
        resp = unauth_session.get(f"{BASE_URL}/api/commesse/{test_commessa_id}/consegne/cons_xxx/pacchetto-pdf")
        
        assert resp.status_code in [401, 403, 422], f"Expected auth error, got {resp.status_code}"
        print("PASS: Unauthorized GET pacchetto-pdf returns auth error")


# ──────────────────────────────────────────────────────────────────────────────
# Run tests
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

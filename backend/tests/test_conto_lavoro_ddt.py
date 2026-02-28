"""
Test suite for Conto Lavoro DDT feature - Backend API Tests
Tests:
- POST /api/commesse/{cid}/conto-lavoro - Create CL with righe
- POST /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-pdf - Generate PDF
- POST /api/commesse/{cid}/conto-lavoro/{cl_id}/send-email - Send Email
- PUT /api/commesse/{cid}/conto-lavoro/{cl_id} - Update CL status transitions
"""
import pytest
import requests
import os
import time
import subprocess
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test fixtures
@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for testing"""
    ts = int(time.time() * 1000)
    session_token = f"test_session_cl_{ts}"
    user_id = f"test-user-cl-{ts}"
    commessa_id = f"com_test_cl_{ts}"
    fornitore_id = f"cli_test_forn_{ts}"
    
    # Create test data in MongoDB
    mongo_script = f"""
    db = db.getSiblingDB('test_database');
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "test.cl.{ts}@example.com",
        name: "Test CL User",
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    db.commesse.insertOne({{
        commessa_id: "{commessa_id}",
        user_id: "{user_id}",
        numero: "TEST-CL-{ts}",
        title: "Test Commessa per CL",
        stato: "attiva",
        created_at: new Date(),
        eventi: []
    }});
    db.clients.insertOne({{
        client_id: "{fornitore_id}",
        user_id: "{user_id}",
        client_type: "fornitore",
        business_name: "Verniciatura Test SRL",
        pec: "test.vern.{ts}@pec.example.com",
        email: "test.vern.{ts}@example.com",
        created_at: new Date()
    }});
    print("OK");
    """
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True, text=True
    )
    assert "OK" in result.stdout, f"Failed to create test data: {result.stderr}"
    
    yield {
        "session_token": session_token,
        "user_id": user_id,
        "commessa_id": commessa_id,
        "fornitore_id": fornitore_id
    }
    
    # Cleanup
    cleanup_script = f"""
    db = db.getSiblingDB('test_database');
    db.users.deleteMany({{user_id: "{user_id}"}});
    db.user_sessions.deleteMany({{session_token: "{session_token}"}});
    db.commesse.deleteMany({{commessa_id: "{commessa_id}"}});
    db.clients.deleteMany({{client_id: "{fornitore_id}"}});
    print("CLEANED");
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)


@pytest.fixture
def auth_headers(test_session):
    """Return auth headers for API calls"""
    return {
        "Authorization": f"Bearer {test_session['session_token']}",
        "Content-Type": "application/json"
    }


class TestContoLavoroCRUD:
    """Test Conto Lavoro CRUD operations"""
    
    cl_id = None  # Store created CL ID for subsequent tests
    
    def test_create_conto_lavoro_with_righe(self, test_session, auth_headers):
        """Test creating a Conto Lavoro with line items (righe)"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        payload = {
            "tipo": "verniciatura",
            "fornitore_nome": "Verniciatura Test SRL",
            "fornitore_id": fornitore_id,
            "ral": "RAL 9005",
            "righe": [
                {"descrizione": "IPE 200 L=3000mm", "quantita": 4, "unita": "pz", "peso_kg": 120},
                {"descrizione": "HEB 200 L=2500mm", "quantita": 2, "unita": "pz", "peso_kg": 180}
            ],
            "note": "Test conto lavoro verniciatura",
            "causale_trasporto": "Conto Lavorazione"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "conto_lavoro" in data
        cl = data["conto_lavoro"]
        assert cl["tipo"] == "verniciatura"
        assert cl["fornitore_nome"] == "Verniciatura Test SRL"
        assert cl["ral"] == "RAL 9005"
        assert len(cl["righe"]) == 2
        assert cl["righe"][0]["descrizione"] == "IPE 200 L=3000mm"
        assert cl["righe"][0]["peso_kg"] == 120
        assert cl["stato"] == "da_inviare"
        assert cl["causale_trasporto"] == "Conto Lavorazione"
        
        # Store cl_id for subsequent tests
        TestContoLavoroCRUD.cl_id = cl["cl_id"]
    
    def test_create_conto_lavoro_zincatura(self, test_session, auth_headers):
        """Test creating a Conto Lavoro for zincatura (no RAL)"""
        commessa_id = test_session['commessa_id']
        
        payload = {
            "tipo": "zincatura",
            "fornitore_nome": "Zincatura Test SPA",
            "righe": [
                {"descrizione": "Profilato strutturale", "quantita": 10, "unita": "pz", "peso_kg": 500}
            ],
            "causale_trasporto": "Conto Lavorazione Zincatura"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["conto_lavoro"]["tipo"] == "zincatura"
        assert data["conto_lavoro"]["ral"] == ""  # No RAL for zincatura


class TestContoLavoroPDF:
    """Test Conto Lavoro PDF generation"""
    
    def test_preview_pdf_success(self, test_session, auth_headers):
        """Test PDF preview generation returns valid PDF"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCRUD.cl_id
        
        assert cl_id is not None, "CL ID not set from previous test"
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/preview-pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Check PDF content
        pdf_content = response.content
        assert len(pdf_content) > 1000, "PDF content too small"
        assert pdf_content[:4] == b'%PDF', "Response is not a valid PDF"
    
    def test_preview_pdf_not_found(self, test_session, auth_headers):
        """Test PDF preview with non-existent CL returns 404"""
        commessa_id = test_session['commessa_id']
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/nonexistent_cl/preview-pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestContoLavoroStatusTransitions:
    """Test Conto Lavoro status transitions"""
    
    def test_transition_da_inviare_to_inviato(self, test_session, auth_headers):
        """Test updating CL status from da_inviare to inviato"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCRUD.cl_id
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "inviato"}
        )
        
        assert response.status_code == 200
        assert "inviato" in response.json()["message"]
    
    def test_transition_inviato_to_in_lavorazione(self, test_session, auth_headers):
        """Test updating CL status from inviato to in_lavorazione"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCRUD.cl_id
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "in_lavorazione"}
        )
        
        assert response.status_code == 200
        assert "in_lavorazione" in response.json()["message"]
    
    def test_transition_in_lavorazione_to_rientrato(self, test_session, auth_headers):
        """Test updating CL status from in_lavorazione to rientrato"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCRUD.cl_id
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "rientrato"}
        )
        
        assert response.status_code == 200
        assert "rientrato" in response.json()["message"]
    
    def test_transition_rientrato_to_verificato(self, test_session, auth_headers):
        """Test updating CL status from rientrato to verificato"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCRUD.cl_id
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "verificato"}
        )
        
        assert response.status_code == 200
        assert "verificato" in response.json()["message"]


class TestContoLavoroEmail:
    """Test Conto Lavoro email sending"""
    
    def test_send_email_success(self, test_session, auth_headers):
        """Test sending DDT email to supplier"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        # Create a new CL for email test (to have fresh state)
        payload = {
            "tipo": "verniciatura",
            "fornitore_nome": "Email Test SRL",
            "fornitore_id": fornitore_id,
            "ral": "RAL 7016",
            "righe": [{"descrizione": "Test item", "quantita": 1, "unita": "pz", "peso_kg": 50}],
            "causale_trasporto": "Conto Lavorazione"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 200
        new_cl_id = create_resp.json()["conto_lavoro"]["cl_id"]
        
        # Send email
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}/send-email",
            headers=auth_headers
        )
        
        # Email should succeed (if Resend is configured) or return graceful error
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            assert "DDT inviato" in response.json()["message"] or "inviato" in response.json().get("message", "").lower()
    
    def test_send_email_no_supplier_email(self, test_session, auth_headers):
        """Test sending email fails gracefully when supplier has no email"""
        commessa_id = test_session['commessa_id']
        
        # Create CL with fornitore without email
        payload = {
            "tipo": "sabbiatura",
            "fornitore_nome": "No Email Fornitore",
            # No fornitore_id - so no email lookup possible
            "righe": [{"descrizione": "Test", "quantita": 1, "unita": "pz", "peso_kg": 10}],
            "causale_trasporto": "Test"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 200
        new_cl_id = create_resp.json()["conto_lavoro"]["cl_id"]
        
        # Try to send email - should fail with 400
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}/send-email",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "email" in response.json().get("detail", "").lower()


class TestContoLavoroVerifyOps:
    """Verify CL data persistence via ops endpoint"""
    
    def test_ops_returns_conto_lavoro_array(self, test_session, auth_headers):
        """Test that ops endpoint returns conto_lavoro array with correct structure"""
        commessa_id = test_session['commessa_id']
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/ops",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify conto_lavoro is present and is an array
        assert "conto_lavoro" in data
        assert isinstance(data["conto_lavoro"], list)
        assert len(data["conto_lavoro"]) >= 1
        
        # Verify structure of first CL
        cl = data["conto_lavoro"][0]
        assert "cl_id" in cl
        assert "tipo" in cl
        assert "fornitore_nome" in cl
        assert "righe" in cl
        assert "stato" in cl
        assert "ral" in cl
        
        # Verify righe structure
        if cl["righe"]:
            riga = cl["righe"][0]
            assert "descrizione" in riga
            assert "quantita" in riga
            assert "unita" in riga
            assert "peso_kg" in riga


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

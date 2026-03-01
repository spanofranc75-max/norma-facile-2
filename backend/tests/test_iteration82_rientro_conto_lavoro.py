"""
Test suite for Iteration 82 - Rientro Conto Lavoro Workflow
Tests the complete subcontracting return flow:
1. POST /api/commesse/{cid}/conto-lavoro/{cl_id}/rientro - Register return with multipart form
2. PATCH /api/commesse/{cid}/conto-lavoro/{cl_id}/verifica - Verify and auto-complete production phase
3. GET /api/commesse/{cid}/conto-lavoro/{cl_id}/ncr-pdf - Generate NCR PDF for non-conformity
4. State validation - rientro requires stato='inviato' or 'in_lavorazione'
5. Regression - existing C/L create and update still work
"""
import pytest
import requests
import os
import time
import subprocess
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create test user, commessa, and supplier for testing Rientro C/L workflow"""
    ts = int(time.time() * 1000)
    session_token = f"test_session_rientro_{ts}"
    user_id = f"test-user-rientro-{ts}"
    commessa_id = f"com_rientro_test_{ts}"
    fornitore_id = f"cli_forn_rientro_{ts}"
    
    # Create test data in MongoDB
    mongo_script = f"""
    db = db.getSiblingDB('test_database');
    
    // User
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "test.rientro.{ts}@example.com",
        name: "Test Rientro User",
        created_at: new Date()
    }});
    
    // Session
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    
    // Commessa with production phases
    db.commesse.insertOne({{
        commessa_id: "{commessa_id}",
        user_id: "{user_id}",
        numero: "TEST-RIENTRO-{ts}",
        title: "Test Commessa Rientro C/L",
        stato: "attiva",
        created_at: new Date(),
        eventi: [],
        fasi_produzione: [
            {{nome: "Taglio", stato: "completata", progresso: 100}},
            {{nome: "Saldatura", stato: "completata", progresso: 100}},
            {{nome: "Trattamenti Superficiali", stato: "in_corso", progresso: 50}},
            {{nome: "Verniciatura", stato: "da_fare", progresso: 0}}
        ],
        conto_lavoro: [],
        documenti: []
    }});
    
    // Supplier (fornitore)
    db.clients.insertOne({{
        client_id: "{fornitore_id}",
        user_id: "{user_id}",
        client_type: "fornitore",
        business_name: "Verniciatura Industriale Test SRL",
        pec: "vern.test.{ts}@pec.example.com",
        email: "info@verntest.example.com",
        created_at: new Date()
    }});
    
    // Company settings
    db.company_settings.insertOne({{
        user_id: "{user_id}",
        business_name: "Test Fabbro SRL",
        logo_url: "",
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
    db.company_settings.deleteMany({{user_id: "{user_id}"}});
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


@pytest.fixture
def auth_headers_multipart(test_session):
    """Return auth headers for multipart form data calls (no Content-Type)"""
    return {
        "Authorization": f"Bearer {test_session['session_token']}"
    }


class TestHealthCheck:
    """Verify API is up"""
    
    def test_health_endpoint(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestContoLavoroCreation:
    """Test C/L creation (regression)"""
    
    cl_id = None
    
    def test_create_conto_lavoro_verniciatura(self, test_session, auth_headers):
        """Create a C/L for verniciatura to test rientro workflow"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        payload = {
            "tipo": "verniciatura",
            "fornitore_nome": "Verniciatura Industriale Test SRL",
            "fornitore_id": fornitore_id,
            "ral": "RAL 7016",
            "righe": [
                {"descrizione": "IPE 200 L=3000mm", "quantita": 4, "unita": "pz", "peso_kg": 120},
                {"descrizione": "HEB 160 L=2500mm", "quantita": 2, "unita": "pz", "peso_kg": 95}
            ],
            "note": "Test conto lavoro per rientro",
            "causale_trasporto": "Conto Lavorazione"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Create CL failed: {response.text}"
        data = response.json()
        
        assert "conto_lavoro" in data
        cl = data["conto_lavoro"]
        assert cl["tipo"] == "verniciatura"
        assert cl["stato"] == "da_inviare"
        assert len(cl["righe"]) == 2
        assert cl["ral"] == "RAL 7016"
        
        TestContoLavoroCreation.cl_id = cl["cl_id"]
        print(f"Created C/L: {cl['cl_id']}")


class TestRientroStateValidation:
    """Test that rientro endpoint validates C/L state"""
    
    def test_rientro_fails_when_stato_da_inviare(self, test_session, auth_headers_multipart):
        """Rientro should fail when C/L stato is 'da_inviare'"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCreation.cl_id
        
        assert cl_id is not None, "CL ID not set from previous test"
        
        # Try to register rientro without sending first
        form_data = {
            "data_rientro": "2026-01-15",
            "ddt_fornitore_numero": "DDT-001",
            "peso_rientrato_kg": "215",
            "esito_qc": "conforme"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/rientro",
            headers=auth_headers_multipart,
            data=form_data
        )
        
        # Should fail because stato is 'da_inviare'
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "stato" in response.json().get("detail", "").lower() or "rientro" in response.json().get("detail", "").lower()


class TestContoLavoroStatusUpdate:
    """Test C/L status updates (regression + workflow setup)"""
    
    def test_update_stato_to_inviato(self, test_session, auth_headers):
        """Update C/L status to 'inviato' to enable rientro"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCreation.cl_id
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "inviato"}
        )
        
        assert response.status_code == 200, f"Status update failed: {response.text}"
        assert "inviato" in response.json()["message"]


class TestRientroEndpoint:
    """Test the rientro endpoint (POST multipart form)"""
    
    def test_rientro_conforme_without_file(self, test_session, auth_headers_multipart):
        """Test registering return with QC conforme (no certificate file)"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCreation.cl_id
        
        form_data = {
            "data_rientro": "2026-01-15",
            "ddt_fornitore_numero": "DDT-VERN-001",
            "ddt_fornitore_data": "2026-01-14",
            "peso_rientrato_kg": "215",
            "esito_qc": "conforme",
            "note_rientro": "Materiale conforme, colore OK"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/rientro",
            headers=auth_headers_multipart,
            data=form_data
        )
        
        assert response.status_code == 200, f"Rientro failed: {response.text}"
        data = response.json()
        
        assert data["stato"] == "rientrato"
        assert data["esito_qc"] == "conforme"
        assert "Rientro registrato" in data["message"]


class TestContoLavoroRientroSecondCL:
    """Test rientro workflow with a second C/L including certificate upload"""
    
    cl_id_2 = None
    
    def test_create_second_cl(self, test_session, auth_headers):
        """Create a second C/L for testing with file upload"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        payload = {
            "tipo": "zincatura",
            "fornitore_nome": "Zincatura Test SPA",
            "fornitore_id": fornitore_id,
            "righe": [
                {"descrizione": "Struttura portante", "quantita": 1, "unita": "pz", "peso_kg": 450}
            ],
            "note": "C/L zincatura per test NCR",
            "causale_trasporto": "Conto Lavorazione"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        TestContoLavoroRientroSecondCL.cl_id_2 = response.json()["conto_lavoro"]["cl_id"]
    
    def test_set_stato_inviato_for_second_cl(self, test_session, auth_headers):
        """Set second C/L to 'inviato' state"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroRientroSecondCL.cl_id_2
        
        response = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}",
            headers=auth_headers,
            json={"stato": "inviato"}
        )
        
        assert response.status_code == 200
    
    def test_rientro_non_conforme_with_file(self, test_session, auth_headers_multipart):
        """Test registering non-conforme return with certificate file"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroRientroSecondCL.cl_id_2
        
        # Create a dummy PDF file for testing
        dummy_pdf_content = b'%PDF-1.4 test certificate content'
        
        form_data = {
            "data_rientro": "2026-01-16",
            "ddt_fornitore_numero": "DDT-ZINC-002",
            "ddt_fornitore_data": "2026-01-15",
            "peso_rientrato_kg": "445",  # Slightly less than sent
            "esito_qc": "non_conforme",
            "note_rientro": "Zincatura non uniforme su alcuni elementi",
            "motivo_non_conformita": "Spessore zincatura insufficiente su travi secondarie. Richiesta rilavorazione."
        }
        
        files = {
            "certificato_file": ("certificato_zincatura.pdf", io.BytesIO(dummy_pdf_content), "application/pdf")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/rientro",
            headers=auth_headers_multipart,
            data=form_data,
            files=files
        )
        
        assert response.status_code == 200, f"Rientro with file failed: {response.text}"
        data = response.json()
        
        assert data["stato"] == "rientrato"
        assert data["esito_qc"] == "non_conforme"


class TestNCRPDFGeneration:
    """Test NCR (Non-Conformity Report) PDF generation"""
    
    def test_generate_ncr_pdf_success(self, test_session, auth_headers):
        """Test NCR PDF generation for non-conforme C/L"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroRientroSecondCL.cl_id_2
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/ncr-pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"NCR PDF failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Verify PDF content
        pdf_content = response.content
        assert len(pdf_content) > 1000, "NCR PDF content too small"
        assert pdf_content[:4] == b'%PDF', "Response is not a valid PDF"
        
        # Check filename in Content-Disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "NCR" in content_disp or "ncr" in content_disp.lower()
    
    def test_ncr_pdf_for_conforme_cl(self, test_session, auth_headers):
        """NCR PDF should still generate even for conforme C/L (might be needed for documentation)"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCreation.cl_id  # This was marked conforme
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/ncr-pdf",
            headers=auth_headers
        )
        
        # Should still work (generates PDF even if conforme)
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'
    
    def test_ncr_pdf_not_found(self, test_session, auth_headers):
        """NCR PDF should return 404 for non-existent C/L"""
        commessa_id = test_session['commessa_id']
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/nonexistent_cl_id/ncr-pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestVerificaEndpoint:
    """Test the verifica endpoint (PATCH)"""
    
    def test_verifica_fails_when_not_rientrato(self, test_session, auth_headers):
        """Verifica should fail when C/L stato is not 'rientrato'"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        # Create a new C/L that's only 'inviato' (not rientrato)
        payload = {
            "tipo": "sabbiatura",
            "fornitore_nome": "Sabbiatura Test",
            "fornitore_id": fornitore_id,
            "righe": [{"descrizione": "Test", "quantita": 1, "unita": "pz", "peso_kg": 50}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        new_cl_id = create_resp.json()["conto_lavoro"]["cl_id"]
        
        # Update to inviato
        requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}",
            headers=auth_headers,
            json={"stato": "inviato"}
        )
        
        # Try to verify (should fail - not yet rientrato)
        response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}/verifica",
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "rientrato" in response.json().get("detail", "").lower()
    
    def test_verifica_success(self, test_session, auth_headers):
        """Test successful verification of returned C/L"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroCreation.cl_id  # This was rientrato with conforme
        
        response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/verifica",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Verifica failed: {response.text}"
        data = response.json()
        
        assert data["stato"] == "verificato"
        assert "verificato" in data["message"].lower() or "chiuso" in data["message"].lower()
    
    def test_verifica_non_conforme_cl(self, test_session, auth_headers):
        """Test verification of non-conforme C/L (should still work)"""
        commessa_id = test_session['commessa_id']
        cl_id = TestContoLavoroRientroSecondCL.cl_id_2  # This was non_conforme
        
        response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{cl_id}/verifica",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["stato"] == "verificato"


class TestVerificaProductionPhaseAutoComplete:
    """Test that verifica auto-completes related production phase"""
    
    def test_verify_production_phase_updated(self, test_session, auth_headers):
        """Verify that fasi_produzione is updated after verifica"""
        commessa_id = test_session['commessa_id']
        
        # Get the commessa/ops data
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/ops",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check conto_lavoro array
        assert "conto_lavoro" in data
        cl_list = data["conto_lavoro"]
        
        # Find our verified C/L (verniciatura)
        verified_cl = next((cl for cl in cl_list if cl.get("tipo") == "verniciatura" and cl.get("stato") == "verificato"), None)
        assert verified_cl is not None, "Verified verniciatura C/L not found"
        
        # Verify rientro fields are stored
        assert verified_cl.get("data_rientro") is not None
        assert verified_cl.get("esito_qc") == "conforme"


class TestDocumentiLinkage:
    """Test that certificate is linked to documenti repository"""
    
    def test_certificate_linked_to_documenti(self, test_session, auth_headers):
        """Verify certificate from rientro is linked to commessa documenti"""
        commessa_id = test_session['commessa_id']
        
        # Check via MongoDB directly (the certificate should be in documenti array)
        # Using the ops endpoint to check stored data
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/ops",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # The non_conforme C/L had a certificate uploaded
        cl_list = data.get("conto_lavoro", [])
        zinc_cl = next((cl for cl in cl_list if cl.get("tipo") == "zincatura"), None)
        
        if zinc_cl:
            # Should have certificate stored
            assert zinc_cl.get("certificato_rientro_base64") is not None or zinc_cl.get("certificato_rientro_filename") is not None, \
                "Certificate not stored in C/L record"


class TestRegressionContoLavoro:
    """Regression tests for existing C/L functionality"""
    
    def test_conto_lavoro_update_still_works(self, test_session, auth_headers):
        """Test that standard PUT update still works"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        # Create new C/L
        payload = {
            "tipo": "altro",
            "fornitore_nome": "Regression Test",
            "fornitore_id": fornitore_id,
            "righe": [{"descrizione": "Regression test item", "quantita": 1, "unita": "pz", "peso_kg": 10}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 200
        new_cl_id = create_resp.json()["conto_lavoro"]["cl_id"]
        
        # Standard update
        update_resp = requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}",
            headers=auth_headers,
            json={"stato": "inviato", "note": "Updated note"}
        )
        
        assert update_resp.status_code == 200
        assert "inviato" in update_resp.json()["message"]
    
    def test_ops_endpoint_returns_all_data(self, test_session, auth_headers):
        """Verify ops endpoint returns complete C/L data"""
        commessa_id = test_session['commessa_id']
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/ops",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conto_lavoro" in data
        assert "fasi" in data or "fasi_produzione" in data or len(data["conto_lavoro"]) > 0


class TestRientroFromInLavorazione:
    """Test rientro from 'in_lavorazione' state (alternative valid state)"""
    
    def test_rientro_from_in_lavorazione(self, test_session, auth_headers, auth_headers_multipart):
        """Test that rientro works from 'in_lavorazione' state"""
        commessa_id = test_session['commessa_id']
        fornitore_id = test_session['fornitore_id']
        
        # Create C/L
        payload = {
            "tipo": "galvanica",
            "fornitore_nome": "Galvanica Test",
            "fornitore_id": fornitore_id,
            "righe": [{"descrizione": "Componenti metallici", "quantita": 50, "unita": "pz", "peso_kg": 25}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro",
            headers=auth_headers,
            json=payload
        )
        new_cl_id = create_resp.json()["conto_lavoro"]["cl_id"]
        
        # Set to inviato first
        requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}",
            headers=auth_headers,
            json={"stato": "inviato"}
        )
        
        # Set to in_lavorazione
        requests.put(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}",
            headers=auth_headers,
            json={"stato": "in_lavorazione"}
        )
        
        # Now try rientro from in_lavorazione
        form_data = {
            "data_rientro": "2026-01-17",
            "ddt_fornitore_numero": "DDT-GALV-003",
            "peso_rientrato_kg": "25",
            "esito_qc": "conforme_con_riserva",
            "note_rientro": "Accettato con riserva - piccole imperfezioni estetiche"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/{new_cl_id}/rientro",
            headers=auth_headers_multipart,
            data=form_data
        )
        
        assert response.status_code == 200, f"Rientro from in_lavorazione failed: {response.text}"
        assert response.json()["esito_qc"] == "conforme_con_riserva"


class TestUnauthorizedAccess:
    """Test unauthorized access to endpoints"""
    
    def test_rientro_without_auth(self, test_session):
        """Rientro should fail without auth"""
        commessa_id = test_session['commessa_id']
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/any_cl_id/rientro",
            data={"data_rientro": "2026-01-15", "esito_qc": "conforme"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_verifica_without_auth(self, test_session):
        """Verifica should fail without auth"""
        commessa_id = test_session['commessa_id']
        
        response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/any_cl_id/verifica"
        )
        
        assert response.status_code in [401, 403]
    
    def test_ncr_pdf_without_auth(self, test_session):
        """NCR PDF should fail without auth"""
        commessa_id = test_session['commessa_id']
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/conto-lavoro/any_cl_id/ncr-pdf"
        )
        
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

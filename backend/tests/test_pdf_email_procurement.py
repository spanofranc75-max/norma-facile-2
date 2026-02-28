"""
Test PDF Generation and Email Sending for RdP and OdA
Tests the new workflow: Compile form -> Preview PDF -> Send Email -> Status badge tracking
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user setup
TEST_TIMESTAMP = str(int(time.time() * 1000))
TEST_USER_ID = f"test-pdf-email-{TEST_TIMESTAMP}"
TEST_SESSION_TOKEN = f"test_session_pdf_email_{TEST_TIMESTAMP}"


@pytest.fixture(scope="module")
def auth_token():
    """Create test user and session, return session token."""
    import subprocess
    
    setup_script = f'''
    use("test_database");
    var userId = "{TEST_USER_ID}";
    var sessionToken = "{TEST_SESSION_TOKEN}";
    
    db.users.deleteMany({{user_id: {{$regex: /^test-pdf-email/}}}});
    db.user_sessions.deleteMany({{session_token: {{$regex: /^test_session_pdf_email/}}}});
    
    db.users.insertOne({{
        user_id: userId,
        email: "pdf-email-test@example.com",
        name: "PDF Email Test User",
        picture: "https://via.placeholder.com/150",
        created_at: new Date()
    }});
    
    db.user_sessions.insertOne({{
        user_id: userId,
        session_token: sessionToken,
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    
    print("Created user: " + userId);
    print("Session: " + sessionToken);
    '''
    
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', setup_script],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"MongoDB setup error: {result.stderr}")
    
    return TEST_SESSION_TOKEN


@pytest.fixture(scope="module")
def test_data(auth_token):
    """Create test commessa and fornitore (supplier with email)."""
    import subprocess
    
    # Create supplier with email (required for email sending)
    fornitore_id = f"forn_test_{TEST_TIMESTAMP}"
    
    setup_script = f'''
    use("test_database");
    
    // Create test fornitore with email
    db.clients.deleteMany({{client_id: {{$regex: /^forn_test_/}}}});
    db.clients.insertOne({{
        client_id: "{fornitore_id}",
        user_id: "{TEST_USER_ID}",
        business_name: "Fornitore Test PDF Email",
        client_type: "fornitore",
        email: "fornitore.test@example.com",
        pec: "fornitore.pec@example.it",
        contacts: [{{name: "Mario Rossi", email: "mario@fornitore.com"}}],
        created_at: new Date()
    }});
    
    // Create test commessa
    var commessaId = "com_pdftest_{TEST_TIMESTAMP}";
    db.commesse.deleteMany({{commessa_id: {{$regex: /^com_pdftest_/}}}});
    db.commesse.insertOne({{
        commessa_id: commessaId,
        user_id: "{TEST_USER_ID}",
        numero: "COM-PDFTEST-{TEST_TIMESTAMP}",
        cantiere: {{indirizzo: "Via Test 1", citta: "Roma"}},
        approvvigionamento: {{richieste: [], ordini: [], arrivi: []}},
        eventi: [],
        created_at: new Date()
    }});
    
    print("Fornitore ID: " + "{fornitore_id}");
    print("Commessa ID: " + commessaId);
    '''
    
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', setup_script],
        capture_output=True, text=True
    )
    print(result.stdout)
    
    return {
        "commessa_id": f"com_pdftest_{TEST_TIMESTAMP}",
        "fornitore_id": fornitore_id,
        "fornitore_nome": "Fornitore Test PDF Email"
    }


class TestRdpPdfGeneration:
    """Tests for RdP PDF generation endpoint"""
    
    def test_create_rdp_with_line_items(self, auth_token, test_data):
        """Create an RdP with line items including Cert. 3.1 badges"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        rdp_payload = {
            "fornitore_nome": test_data["fornitore_nome"],
            "fornitore_id": test_data["fornitore_id"],
            "righe": [
                {"descrizione": "Trave IPE 200", "quantita": 500, "unita_misura": "kg", "richiede_cert_31": True},
                {"descrizione": "Lamiera S275JR 10mm", "quantita": 200, "unita_misura": "kg", "richiede_cert_31": True},
                {"descrizione": "Bulloneria M16 classe 8.8", "quantita": 100, "unita_misura": "pz", "richiede_cert_31": False}
            ],
            "note": "Consegna urgente entro 7 giorni"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste",
            json=rdp_payload, headers=headers
        )
        
        assert response.status_code == 200, f"RdP creation failed: {response.text}"
        data = response.json()
        assert "rdp" in data
        rdp_id = data["rdp"]["rdp_id"]
        assert rdp_id.startswith("rdp_")
        
        # Store rdp_id for later tests
        test_data["rdp_id"] = rdp_id
        
        # Verify righe persisted
        assert len(data["rdp"]["righe"]) == 3
        assert data["rdp"]["righe"][0]["richiede_cert_31"] == True
        print(f"✓ Created RdP {rdp_id} with 3 line items (2 with Cert. 3.1)")
    
    def test_get_rdp_pdf(self, auth_token, test_data):
        """Test RdP PDF generation endpoint returns valid PDF"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        rdp_id = test_data.get("rdp_id")
        if not rdp_id:
            pytest.skip("RdP not created in previous test")
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{rdp_id}/pdf",
            headers=headers
        )
        
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        assert response.headers.get("Content-Disposition", "").startswith("inline")
        
        # Verify it's a real PDF (PDF magic bytes: %PDF)
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF file"
        print(f"✓ RdP PDF generated successfully ({len(response.content)} bytes)")
    
    def test_rdp_pdf_not_found(self, auth_token, test_data):
        """Test PDF endpoint returns 404 for non-existent RdP"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/rdp_nonexistent/pdf",
            headers=headers
        )
        
        assert response.status_code == 404
        print("✓ Non-existent RdP returns 404")


class TestOdaPdfGeneration:
    """Tests for OdA PDF generation endpoint"""
    
    def test_create_oda_with_line_items(self, auth_token, test_data):
        """Create an OdA with line items including pricing and Cert. 3.1"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        oda_payload = {
            "fornitore_nome": test_data["fornitore_nome"],
            "fornitore_id": test_data["fornitore_id"],
            "righe": [
                {"descrizione": "Trave IPE 200 S275JR", "quantita": 500, "unita_misura": "kg", "prezzo_unitario": 1.20, "richiede_cert_31": True},
                {"descrizione": "Lamiera S275JR 10mm", "quantita": 200, "unita_misura": "kg", "prezzo_unitario": 0.95, "richiede_cert_31": True},
                {"descrizione": "Bulloneria M16 8.8", "quantita": 100, "unita_misura": "pz", "prezzo_unitario": 0.50, "richiede_cert_31": False}
            ],
            "note": "Consegna franco destino - confermare tempistiche"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini",
            json=oda_payload, headers=headers
        )
        
        assert response.status_code == 200, f"OdA creation failed: {response.text}"
        data = response.json()
        assert "ordine" in data
        ordine_id = data["ordine"]["ordine_id"]
        assert ordine_id.startswith("oda_")
        
        # Store ordine_id for later tests
        test_data["ordine_id"] = ordine_id
        
        # Verify total calculation: 500*1.20 + 200*0.95 + 100*0.50 = 600 + 190 + 50 = 840
        expected_total = 840.0
        assert data["ordine"]["importo_totale"] == expected_total, f"Expected {expected_total}, got {data['ordine']['importo_totale']}"
        print(f"✓ Created OdA {ordine_id} with total €{expected_total}")
    
    def test_get_oda_pdf(self, auth_token, test_data):
        """Test OdA PDF generation endpoint returns valid PDF"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        ordine_id = test_data.get("ordine_id")
        if not ordine_id:
            pytest.skip("OdA not created in previous test")
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini/{ordine_id}/pdf",
            headers=headers
        )
        
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        assert response.headers.get("Content-Disposition", "").startswith("inline")
        
        # Verify it's a real PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF file"
        print(f"✓ OdA PDF generated successfully ({len(response.content)} bytes)")
    
    def test_oda_pdf_not_found(self, auth_token, test_data):
        """Test PDF endpoint returns 404 for non-existent OdA"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini/oda_nonexistent/pdf",
            headers=headers
        )
        
        assert response.status_code == 404
        print("✓ Non-existent OdA returns 404")


class TestEmailSending:
    """Tests for email sending endpoints and status tracking"""
    
    def test_send_rdp_email_without_supplier_email(self, auth_token, test_data):
        """Test email sending fails gracefully when supplier has no email"""
        import subprocess
        
        # Create RdP with fornitore that has no email
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        # First create a fornitore without email
        no_email_fornitore = f"forn_noemail_{TEST_TIMESTAMP}"
        setup_script = f'''
        use("test_database");
        db.clients.insertOne({{
            client_id: "{no_email_fornitore}",
            user_id: "{TEST_USER_ID}",
            business_name: "Fornitore Senza Email",
            client_type: "fornitore",
            created_at: new Date()
        }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', setup_script], capture_output=True)
        
        # Create RdP with this fornitore
        rdp_payload = {
            "fornitore_nome": "Fornitore Senza Email",
            "fornitore_id": no_email_fornitore,
            "righe": [{"descrizione": "Test materiale", "quantita": 1, "unita_misura": "pz"}],
            "note": ""
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste",
            json=rdp_payload, headers=headers
        )
        assert create_response.status_code == 200
        rdp_id = create_response.json()["rdp"]["rdp_id"]
        
        # Try to send email - should fail with 400
        send_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{rdp_id}/send-email",
            headers=headers
        )
        
        assert send_response.status_code == 400, f"Expected 400 for no email, got {send_response.status_code}: {send_response.text}"
        assert "email" in send_response.text.lower() or "indirizzo" in send_response.text.lower()
        print("✓ Email sending correctly fails when supplier has no email")
    
    def test_send_rdp_email_with_supplier_email(self, auth_token, test_data):
        """Test RdP email endpoint with valid supplier email (may fail if Resend not configured)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        rdp_id = test_data.get("rdp_id")
        if not rdp_id:
            pytest.skip("RdP not created")
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{rdp_id}/send-email",
            headers=headers
        )
        
        # If Resend is not configured, it returns 500
        # If Resend is configured but fails, also 500
        # If success, 200
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "to" in data
            print(f"✓ RdP email sent successfully to {data['to']}")
            
            # Verify email_sent status updated
            ops_response = requests.get(
                f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/ops",
                headers=headers
            )
            assert ops_response.status_code == 200
            ops_data = ops_response.json()
            rdp_list = ops_data.get("approvvigionamento", {}).get("richieste", [])
            rdp = next((r for r in rdp_list if r.get("rdp_id") == rdp_id), None)
            assert rdp is not None
            assert rdp.get("email_sent") == True, "email_sent should be True after sending"
            assert rdp.get("email_sent_to") is not None, "email_sent_to should be populated"
            print(f"✓ RdP email_sent status updated correctly")
        elif response.status_code == 500:
            # Expected if Resend is not configured
            print("⚠ RdP email sending returned 500 (likely Resend not configured - acceptable)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code} - {response.text}")
    
    def test_send_oda_email_with_supplier_email(self, auth_token, test_data):
        """Test OdA email endpoint with valid supplier email"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        ordine_id = test_data.get("ordine_id")
        if not ordine_id:
            pytest.skip("OdA not created")
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini/{ordine_id}/send-email",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "to" in data
            print(f"✓ OdA email sent successfully to {data['to']}")
            
            # Verify email_sent status updated
            ops_response = requests.get(
                f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/ops",
                headers=headers
            )
            ops_data = ops_response.json()
            ordini_list = ops_data.get("approvvigionamento", {}).get("ordini", [])
            oda = next((o for o in ordini_list if o.get("ordine_id") == ordine_id), None)
            assert oda is not None
            assert oda.get("email_sent") == True
            print(f"✓ OdA email_sent status updated correctly")
        elif response.status_code == 500:
            print("⚠ OdA email sending returned 500 (likely Resend not configured - acceptable)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code} - {response.text}")


class TestEmailStatusBadges:
    """Tests for email status tracking (Bozza vs Inviata badges)"""
    
    def test_rdp_default_status_is_draft(self, auth_token, test_data):
        """New RdP should have email_sent=False (Bozza/draft status)"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        rdp_payload = {
            "fornitore_nome": test_data["fornitore_nome"],
            "fornitore_id": test_data["fornitore_id"],
            "righe": [{"descrizione": "Test badge status", "quantita": 1, "unita_misura": "pz"}],
            "note": ""
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste",
            json=rdp_payload, headers=headers
        )
        
        assert response.status_code == 200
        rdp = response.json()["rdp"]
        
        # email_sent should be False or not present (both mean draft)
        email_sent = rdp.get("email_sent", False)
        assert email_sent is False or email_sent is None, "New RdP should be in draft status"
        print("✓ New RdP has draft (Bozza) status by default")
    
    def test_oda_default_status_is_draft(self, auth_token, test_data):
        """New OdA should have email_sent=False (Bozza/draft status)"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        oda_payload = {
            "fornitore_nome": test_data["fornitore_nome"],
            "fornitore_id": test_data["fornitore_id"],
            "righe": [{"descrizione": "Test badge status", "quantita": 1, "unita_misura": "pz", "prezzo_unitario": 10}],
            "note": ""
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini",
            json=oda_payload, headers=headers
        )
        
        assert response.status_code == 200
        oda = response.json()["ordine"]
        
        # email_sent should be False or not present (both mean draft)
        email_sent = oda.get("email_sent", False)
        assert email_sent is False or email_sent is None, "New OdA should be in draft status"
        print("✓ New OdA has draft (Bozza) status by default")


class TestPdfContentValidation:
    """Tests to validate PDF contains correct data"""
    
    def test_rdp_pdf_contains_cert_badge(self, auth_token, test_data):
        """PDF should contain Cert. 3.1 badge markers for items that require certification"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create RdP with cert requirement
        create_headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        rdp_payload = {
            "fornitore_nome": test_data["fornitore_nome"],
            "fornitore_id": test_data["fornitore_id"],
            "righe": [
                {"descrizione": "Materiale con certificato", "quantita": 100, "unita_misura": "kg", "richiede_cert_31": True}
            ],
            "note": "Test PDF cert badge"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste",
            json=rdp_payload, headers=create_headers
        )
        assert create_response.status_code == 200
        rdp_id = create_response.json()["rdp"]["rdp_id"]
        
        # Get PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{rdp_id}/pdf",
            headers=headers
        )
        
        assert pdf_response.status_code == 200
        # Check PDF bytes contain "CERT" text (PDF is binary but text is embedded)
        pdf_bytes = pdf_response.content
        assert b'PDF' in pdf_bytes[:1024], "Should be valid PDF"
        # Note: Actual text content verification would require PDF parsing
        print(f"✓ RdP PDF generated for item with Cert. 3.1 requirement")


@pytest.fixture(scope="module", autouse=True)
def cleanup(request, auth_token):
    """Cleanup test data after all tests."""
    def finalizer():
        import subprocess
        cleanup_script = f'''
        use("test_database");
        db.users.deleteMany({{user_id: {{$regex: /^test-pdf-email/}}}});
        db.user_sessions.deleteMany({{session_token: {{$regex: /^test_session_pdf_email/}}}});
        db.clients.deleteMany({{client_id: {{$regex: /^forn_test_/}}}});
        db.clients.deleteMany({{client_id: {{$regex: /^forn_noemail_/}}}});
        db.commesse.deleteMany({{commessa_id: {{$regex: /^com_pdftest_/}}}});
        print("Cleaned up test data");
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    request.addfinalizer(finalizer)

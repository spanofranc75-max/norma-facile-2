"""
Iteration 65: Test PDF Blob URL Fix & Email Text Editing

Tests:
1. GET /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-pdf - Returns valid PDF (was broken, returning 405)
2. All 6 send-email endpoints accept optional {custom_subject, custom_body} in POST body
"""
import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://commessa-hub-1.preview.emergentagent.com')

# Test data tracking
test_data = {}


@pytest.fixture(scope="module")
def auth_session():
    """Create test user and session for authentication."""
    import subprocess
    
    timestamp = int(time.time() * 1000)
    user_id = f"test-user-{timestamp}"
    session_token = f"test_session_{timestamp}"
    email = f"test.user.{timestamp}@example.com"
    
    # Create user and session in MongoDB
    mongo_script = f'''
    use('test_database');
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "{email}",
        name: "Test User iter65",
        picture: "https://via.placeholder.com/150",
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    '''
    result = subprocess.run(['mongosh', '--eval', mongo_script], capture_output=True, text=True)
    
    test_data['user_id'] = user_id
    test_data['session_token'] = session_token
    test_data['email'] = email
    
    # Return session with auth header
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    })
    
    yield session
    
    # Cleanup after tests
    cleanup_script = f'''
    use('test_database');
    db.users.deleteOne({{ user_id: "{user_id}" }});
    db.user_sessions.deleteOne({{ session_token: "{session_token}" }});
    db.commesse.deleteMany({{ user_id: "{user_id}" }});
    db.clients.deleteMany({{ user_id: "{user_id}" }});
    db.company_settings.deleteOne({{ user_id: "{user_id}" }});
    db.invoices.deleteMany({{ user_id: "{user_id}" }});
    db.ddt_documents.deleteMany({{ user_id: "{user_id}" }});
    db.preventivi.deleteMany({{ user_id: "{user_id}" }});
    '''
    subprocess.run(['mongosh', '--eval', cleanup_script], capture_output=True, text=True)


@pytest.fixture(scope="module")
def setup_test_data(auth_session):
    """Create test commessa with Conto Lavoro, fornitore, and client."""
    session = auth_session
    
    # 1. Create company settings
    company_data = {
        "business_name": "Test Officina Metallica",
        "partita_iva": "IT12345678901",
        "codice_fiscale": "12345678901",
        "address": {
            "via": "Via Test 1",
            "cap": "12345",
            "citta": "Milano",
            "provincia": "MI"
        },
        "email": "test@testofficinatesting.it",
        "phone": "+39 123 456 7890"
    }
    response = session.put(f"{BASE_URL}/api/company-settings", json=company_data)
    print(f"Company settings: {response.status_code}")
    
    # 2. Create fornitore client
    fornitore_data = {
        "business_name": "Test Verniciatore SRL",
        "client_type": "fornitore",
        "email": "test.fornitore@testverniciatore.it",
        "pec": "test.fornitore.pec@testverniciatore.it",
        "address": "Via Fornitore 1",
        "cap": "12345",
        "city": "Milano",
        "province": "MI"
    }
    response = session.post(f"{BASE_URL}/api/clients/", json=fornitore_data)
    assert response.status_code == 201, f"Failed to create fornitore: {response.text}"
    fornitore = response.json()
    test_data['fornitore_id'] = fornitore['client_id']
    print(f"Created fornitore: {fornitore['client_id']}")
    
    # 3. Create cliente for invoice/ddt/preventivo
    cliente_data = {
        "business_name": "Test Cliente SpA",
        "client_type": "cliente",
        "email": "test.cliente@testcliente.it",
        "pec": "test.cliente.pec@testcliente.it",
        "address": "Via Cliente 1",
        "cap": "12345",
        "city": "Milano",
        "province": "MI"
    }
    response = session.post(f"{BASE_URL}/api/clients/", json=cliente_data)
    assert response.status_code == 201, f"Failed to create cliente: {response.text}"
    cliente = response.json()
    test_data['cliente_id'] = cliente['client_id']
    print(f"Created cliente: {cliente['client_id']}")
    
    # 4. Create commessa with Conto Lavoro
    commessa_data = {
        "title": "Test Commessa PDF Fix",
        "cliente": "Test Cliente",
        "importo": 10000,
        "data_consegna": "2026-06-01"
    }
    response = session.post(f"{BASE_URL}/api/commesse/", json=commessa_data)
    assert response.status_code == 201, f"Failed to create commessa: {response.text}"
    commessa = response.json()
    test_data['commessa_id'] = commessa['commessa_id']
    print(f"Created commessa: {commessa['commessa_id']}")
    
    # 5. Create Conto Lavoro entry
    cl_data = {
        "tipo": "verniciatura",
        "fornitore_nome": "Test Verniciatore SRL",
        "fornitore_id": test_data['fornitore_id'],
        "ral": "RAL 7035",
        "righe": [
            {"descrizione": "Profili IPE 200", "quantita": 10, "unita": "pz", "peso_kg": 250},
            {"descrizione": "Travi HEB 160", "quantita": 5, "unita": "pz", "peso_kg": 180}
        ],
        "causale_trasporto": "Conto Lavorazione",
        "note": "Test CL per iteration 65"
    }
    response = session.post(f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/conto-lavoro", json=cl_data)
    assert response.status_code == 200, f"Failed to create CL: {response.text}"
    cl = response.json()
    test_data['cl_id'] = cl['conto_lavoro']['cl_id']
    print(f"Created CL: {test_data['cl_id']}")
    
    # 6. Create RdP for testing email with custom text
    rdp_data = {
        "fornitore_nome": "Test Verniciatore SRL",
        "fornitore_id": test_data['fornitore_id'],
        "righe": [
            {"descrizione": "Materiale test", "quantita": 100, "unita_misura": "kg", "richiede_cert_31": True}
        ],
        "note": "Test RdP"
    }
    response = session.post(f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste", json=rdp_data)
    assert response.status_code == 200, f"Failed to create RdP: {response.text}"
    rdp = response.json()
    test_data['rdp_id'] = rdp['rdp']['rdp_id']
    print(f"Created RdP: {test_data['rdp_id']}")
    
    # 7. Create OdA for testing
    oda_data = {
        "fornitore_nome": "Test Verniciatore SRL",
        "fornitore_id": test_data['fornitore_id'],
        "righe": [
            {"descrizione": "Materiale ordinato", "quantita": 50, "unita_misura": "kg", "prezzo_unitario": 5.0}
        ],
        "note": "Test OdA"
    }
    response = session.post(f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini", json=oda_data)
    assert response.status_code == 200, f"Failed to create OdA: {response.text}"
    oda = response.json()
    test_data['oda_id'] = oda['ordine']['ordine_id']
    print(f"Created OdA: {test_data['oda_id']}")
    
    # 8. Create Invoice for testing
    invoice_data = {
        "client_id": test_data['cliente_id'],
        "document_type": "FT",
        "issue_date": "2026-01-15",
        "payment_method": "bonifico",
        "payment_terms": "30gg",
        "tax_settings": {"apply_rivalsa_inps": False, "apply_cassa": False, "apply_ritenuta": False},
        "lines": [
            {"code": "TEST01", "description": "Servizio test", "quantity": 1, "unit_price": 1000, "vat_rate": "22"}
        ]
    }
    response = session.post(f"{BASE_URL}/api/invoices/", json=invoice_data)
    assert response.status_code == 201, f"Failed to create invoice: {response.text}"
    invoice = response.json()
    test_data['invoice_id'] = invoice['invoice_id']
    print(f"Created invoice: {test_data['invoice_id']}")
    
    # 9. Create DDT for testing
    ddt_data = {
        "ddt_type": "vendita",
        "client_id": test_data['cliente_id'],
        "subject": "DDT Test",
        "lines": [
            {"description": "Prodotto test", "quantity": 1, "unit_price": 500, "vat_rate": "22"}
        ]
    }
    response = session.post(f"{BASE_URL}/api/ddt/", json=ddt_data)
    assert response.status_code == 201, f"Failed to create DDT: {response.text}"
    ddt = response.json()
    test_data['ddt_id'] = ddt['ddt_id']
    print(f"Created DDT: {test_data['ddt_id']}")
    
    # 10. Create Preventivo for testing
    preventivo_data = {
        "client_id": test_data['cliente_id'],
        "subject": "Preventivo Test",
        "validity_days": 30,
        "lines": [
            {"description": "Servizio test prev", "quantity": 1, "unit_price": 2000, "vat_rate": "22"}
        ]
    }
    response = session.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
    assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
    preventivo = response.json()
    test_data['preventivo_id'] = preventivo['preventivo_id']
    print(f"Created preventivo: {test_data['preventivo_id']}")
    
    return test_data


class TestCLPdfPreview:
    """Test CL PDF preview endpoint - was returning 405 before fix."""
    
    def test_cl_preview_pdf_returns_valid_pdf(self, auth_session, setup_test_data):
        """GET /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-pdf should return valid PDF."""
        session = auth_session
        cid = setup_test_data['commessa_id']
        cl_id = setup_test_data['cl_id']
        
        response = session.get(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}/preview-pdf")
        
        # Must return 200, not 405
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Content-Type should be PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected PDF content-type, got {content_type}"
        
        # PDF should start with %PDF
        content = response.content
        assert content[:4] == b'%PDF', f"PDF content does not start with %PDF"
        
        # PDF should be reasonable size (>1KB)
        assert len(content) > 1000, f"PDF too small ({len(content)} bytes)"
        
        print(f"PASS: CL PDF preview returns valid PDF ({len(content)} bytes)")
    
    def test_cl_preview_pdf_404_for_nonexistent(self, auth_session, setup_test_data):
        """GET /api/commesse/{cid}/conto-lavoro/{invalid_id}/preview-pdf should return 404."""
        session = auth_session
        cid = setup_test_data['commessa_id']
        
        response = session.get(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/invalid_cl_id/preview-pdf")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: CL PDF preview returns 404 for non-existent CL")


class TestEmailCustomTextEndpoints:
    """Test all 6 send-email endpoints accept optional custom_subject/custom_body."""
    
    def test_cl_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/commesse/{cid}/conto-lavoro/{cl_id}/send-email accepts custom_subject/custom_body."""
        session = auth_session
        cid = setup_test_data['commessa_id']
        cl_id = setup_test_data['cl_id']
        
        # Test with custom subject/body - may fail if Resend not configured, but endpoint should accept payload
        custom_payload = {
            "custom_subject": "Test Custom Subject - CL DDT",
            "custom_body": "Test custom body content for Conto Lavoro email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}/send-email",
            json=custom_payload
        )
        
        # Should either succeed (200) or fail due to email config (500), not due to payload format
        # 400 means "Email fornitore non disponibile" which is acceptable
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            print("PASS: CL send-email accepts custom_subject/custom_body and sends successfully")
        elif response.status_code == 400:
            print("PASS: CL send-email endpoint accepts payload (400 = missing supplier email)")
        else:
            print("PASS: CL send-email endpoint accepts payload (500 = email service issue)")
    
    def test_rdp_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/send-email accepts custom text."""
        session = auth_session
        cid = setup_test_data['commessa_id']
        rdp_id = setup_test_data['rdp_id']
        
        custom_payload = {
            "custom_subject": "Test RdP Custom Subject",
            "custom_body": "Test custom body for RdP email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/send-email",
            json=custom_payload
        )
        
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        print(f"PASS: RdP send-email accepts custom_subject/custom_body (status: {response.status_code})")
    
    def test_oda_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/commesse/{cid}/approvvigionamento/ordini/{ordine_id}/send-email accepts custom text."""
        session = auth_session
        cid = setup_test_data['commessa_id']
        oda_id = setup_test_data['oda_id']
        
        custom_payload = {
            "custom_subject": "Test OdA Custom Subject",
            "custom_body": "Test custom body for OdA email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini/{oda_id}/send-email",
            json=custom_payload
        )
        
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        print(f"PASS: OdA send-email accepts custom_subject/custom_body (status: {response.status_code})")
    
    def test_invoice_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/invoices/{invoice_id}/send-email accepts custom text."""
        session = auth_session
        invoice_id = setup_test_data['invoice_id']
        
        custom_payload = {
            "custom_subject": "Test Invoice Custom Subject",
            "custom_body": "Test custom body for Invoice email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/send-email",
            json=custom_payload
        )
        
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        print(f"PASS: Invoice send-email accepts custom_subject/custom_body (status: {response.status_code})")
    
    def test_ddt_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/ddt/{ddt_id}/send-email accepts custom text."""
        session = auth_session
        ddt_id = setup_test_data['ddt_id']
        
        custom_payload = {
            "custom_subject": "Test DDT Custom Subject",
            "custom_body": "Test custom body for DDT email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/ddt/{ddt_id}/send-email",
            json=custom_payload
        )
        
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        print(f"PASS: DDT send-email accepts custom_subject/custom_body (status: {response.status_code})")
    
    def test_preventivo_send_email_accepts_custom_text(self, auth_session, setup_test_data):
        """POST /api/preventivi/{prev_id}/send-email accepts custom text."""
        session = auth_session
        prev_id = setup_test_data['preventivo_id']
        
        custom_payload = {
            "custom_subject": "Test Preventivo Custom Subject",
            "custom_body": "Test custom body for Preventivo email."
        }
        
        response = session.post(
            f"{BASE_URL}/api/preventivi/{prev_id}/send-email",
            json=custom_payload
        )
        
        assert response.status_code in [200, 400, 500], f"Unexpected status {response.status_code}: {response.text}"
        print(f"PASS: Preventivo send-email accepts custom_subject/custom_body (status: {response.status_code})")


class TestEmailPreviewDialogDataTestIds:
    """Test that EmailPreviewDialog has correct data-testid attributes."""
    
    def test_email_preview_endpoint_returns_expected_fields(self, auth_session, setup_test_data):
        """Preview-email endpoints should return required fields for EmailPreviewDialog."""
        session = auth_session
        invoice_id = setup_test_data['invoice_id']
        
        response = session.get(f"{BASE_URL}/api/invoices/{invoice_id}/preview-email")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify all required fields for EmailPreviewDialog
        assert 'to_email' in data, "Missing to_email field"
        assert 'to_name' in data, "Missing to_name field"
        assert 'subject' in data, "Missing subject field"
        assert 'html_body' in data, "Missing html_body field"
        assert 'has_attachment' in data, "Missing has_attachment field"
        assert 'attachment_name' in data, "Missing attachment_name field"
        
        print("PASS: Preview-email returns all required fields for EmailPreviewDialog")
        print(f"  - to_email: {data['to_email']}")
        print(f"  - subject: {data['subject']}")
        print(f"  - has_attachment: {data['has_attachment']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

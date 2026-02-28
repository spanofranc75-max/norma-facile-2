"""
Test Email Preview Endpoints - Testing new email preview feature for ALL email sends.
Tests the 6 new GET preview-email endpoints that were added.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Helper to create test data
def unique_id(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"

@pytest.fixture(scope="module")
def auth_token():
    """Create a test user and session for authenticated requests."""
    from pymongo import MongoClient
    from datetime import timedelta
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = unique_id("user_")
    session_token = unique_id("sess_")
    
    # Create test user
    db.users.insert_one({
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test User Email Preview",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create session with expires_at (required field)
    db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),  # Session valid for 7 days
    })
    
    yield {"token": session_token, "user_id": user_id}
    
    # Cleanup
    db.users.delete_many({"user_id": user_id})
    db.user_sessions.delete_many({"session_token": session_token})
    client.close()

@pytest.fixture(scope="module")
def test_data(auth_token):
    """Create test data: commessa with RdP, OdA, CL; invoice; DDT; preventivo."""
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = auth_token["user_id"]
    commessa_id = unique_id("comm_")
    rdp_id = unique_id("rdp_")
    ordine_id = unique_id("oda_")
    cl_id = unique_id("cl_")
    invoice_id = unique_id("inv_")
    ddt_id = unique_id("ddt_")
    preventivo_id = unique_id("prev_")
    fornitore_id = unique_id("forn_")
    cliente_id = unique_id("clt_")
    
    # Create fornitore with email
    db.clients.insert_one({
        "client_id": fornitore_id,
        "user_id": user_id,
        "business_name": "Test Fornitore Srl",
        "email": "fornitore@test.com",
        "pec": "fornitore@pec.test.com",
        "client_type": "fornitore",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create cliente with email
    db.clients.insert_one({
        "client_id": cliente_id,
        "user_id": user_id,
        "business_name": "Test Cliente Spa",
        "email": "cliente@test.com",
        "pec": "cliente@pec.test.com",
        "client_type": "cliente",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create company settings
    db.company_settings.insert_one({
        "user_id": user_id,
        "business_name": "Test Company",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create commessa with RdP, OdA, CL
    db.commesse.insert_one({
        "commessa_id": commessa_id,
        "user_id": user_id,
        "numero": "TEST-001",
        "title": "Test Commessa",
        "approvvigionamento": {
            "richieste": [{
                "rdp_id": rdp_id,
                "fornitore_nome": "Test Fornitore Srl",
                "fornitore_id": fornitore_id,
                "righe": [{"descrizione": "Test Material", "quantita": 10, "unita_misura": "kg"}],
                "stato": "inviata",
            }],
            "ordini": [{
                "ordine_id": ordine_id,
                "fornitore_nome": "Test Fornitore Srl",
                "fornitore_id": fornitore_id,
                "righe": [{"descrizione": "Test Material", "quantita": 10, "prezzo_unitario": 100}],
                "importo_totale": 1000,
                "stato": "inviato",
            }],
            "arrivi": [],
        },
        "conto_lavoro": [{
            "cl_id": cl_id,
            "tipo": "verniciatura",
            "fornitore_nome": "Test Fornitore Srl",
            "fornitore_id": fornitore_id,
            "ral": "RAL 7035",
            "righe": [{"descrizione": "Profili", "quantita": 5, "peso_kg": 50}],
            "stato": "da_inviare",
        }],
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create invoice
    db.invoices.insert_one({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "document_type": "FT",
        "document_number": "FT-2026/0001",
        "client_id": cliente_id,
        "status": "bozza",
        "totals": {"total_document": 1220.00},
        "lines": [{"description": "Service", "quantity": 1, "unit_price": 1000, "vat_rate": "22"}],
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create DDT
    db.ddt_documents.insert_one({
        "ddt_id": ddt_id,
        "user_id": user_id,
        "number": "DDT-2026-0001",
        "ddt_type": "vendita",
        "client_id": cliente_id,
        "client_name": "Test Cliente Spa",
        "status": "non_fatturato",
        "lines": [{"description": "Product", "quantity": 5}],
        "totals": {"total": 500.00},
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create preventivo
    db.preventivi.insert_one({
        "preventivo_id": preventivo_id,
        "user_id": user_id,
        "number": "PRV-2026-0001",
        "client_id": cliente_id,
        "subject": "Test Quote",
        "status": "bozza",
        "lines": [{"description": "Work", "quantity": 1, "unit_price": 2000}],
        "totals": {"total": 2440.00},
        "created_at": datetime.now(timezone.utc),
    })
    
    yield {
        "user_id": user_id,
        "commessa_id": commessa_id,
        "rdp_id": rdp_id,
        "ordine_id": ordine_id,
        "cl_id": cl_id,
        "invoice_id": invoice_id,
        "ddt_id": ddt_id,
        "preventivo_id": preventivo_id,
        "fornitore_id": fornitore_id,
        "cliente_id": cliente_id,
    }
    
    # Cleanup
    db.commesse.delete_many({"commessa_id": commessa_id})
    db.invoices.delete_many({"invoice_id": invoice_id})
    db.ddt_documents.delete_many({"ddt_id": ddt_id})
    db.preventivi.delete_many({"preventivo_id": preventivo_id})
    db.clients.delete_many({"client_id": {"$in": [fornitore_id, cliente_id]}})
    db.company_settings.delete_many({"user_id": user_id})
    client.close()


class TestEmailPreviewEndpoints:
    """Test all 6 email preview endpoints return correct JSON structure."""
    
    def test_rdp_preview_email(self, auth_token, test_data):
        """GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email"""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{test_data['rdp_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data, "Missing 'to_email' field"
        assert "to_name" in data, "Missing 'to_name' field"
        assert "subject" in data, "Missing 'subject' field"
        assert "html_body" in data, "Missing 'html_body' field"
        assert "has_attachment" in data, "Missing 'has_attachment' field"
        assert "attachment_name" in data, "Missing 'attachment_name' field"
        
        # Verify values
        assert "Richiesta Preventivo" in data["subject"], f"Subject should contain 'Richiesta Preventivo': {data['subject']}"
        assert data["has_attachment"] == True, "RdP should have attachment (PDF)"
        assert ".pdf" in data["attachment_name"].lower(), f"Attachment should be PDF: {data['attachment_name']}"
        assert data["to_email"] != "", "to_email should not be empty since fornitore has email"
        print(f"✓ RdP Preview Email - Subject: {data['subject']}, To: {data['to_email']}")
    
    def test_oda_preview_email(self, auth_token, test_data):
        """GET /api/commesse/{cid}/approvvigionamento/ordini/{ordine_id}/preview-email"""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini/{test_data['ordine_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data
        assert "to_name" in data
        assert "subject" in data
        assert "html_body" in data
        assert "has_attachment" in data
        assert "attachment_name" in data
        
        # Verify values
        assert "Ordine" in data["subject"], f"Subject should contain 'Ordine': {data['subject']}"
        assert data["has_attachment"] == True
        assert ".pdf" in data["attachment_name"].lower()
        print(f"✓ OdA Preview Email - Subject: {data['subject']}, To: {data['to_email']}")
    
    def test_cl_preview_email(self, auth_token, test_data):
        """GET /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-email"""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/conto-lavoro/{test_data['cl_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data
        assert "to_name" in data
        assert "subject" in data
        assert "html_body" in data
        assert "has_attachment" in data
        assert "attachment_name" in data
        
        # Verify values (CL should contain "DDT Conto Lavoro" in subject)
        assert "DDT" in data["subject"] or "Conto Lavoro" in data["subject"], f"Subject should contain 'DDT' or 'Conto Lavoro': {data['subject']}"
        assert data["has_attachment"] == True
        print(f"✓ CL Preview Email - Subject: {data['subject']}, To: {data['to_email']}")
    
    def test_invoice_preview_email(self, auth_token, test_data):
        """GET /api/invoices/{invoice_id}/preview-email"""
        url = f"{BASE_URL}/api/invoices/{test_data['invoice_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data
        assert "to_name" in data
        assert "subject" in data
        assert "html_body" in data
        assert "has_attachment" in data
        assert "attachment_name" in data
        
        # Verify values
        assert "Fattura" in data["subject"], f"Subject should contain 'Fattura': {data['subject']}"
        assert data["has_attachment"] == True
        assert ".pdf" in data["attachment_name"].lower()
        print(f"✓ Invoice Preview Email - Subject: {data['subject']}, To: {data['to_email']}")
    
    def test_ddt_preview_email(self, auth_token, test_data):
        """GET /api/ddt/{ddt_id}/preview-email"""
        url = f"{BASE_URL}/api/ddt/{test_data['ddt_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data
        assert "to_name" in data
        assert "subject" in data
        assert "html_body" in data
        assert "has_attachment" in data
        assert "attachment_name" in data
        
        # Verify values
        assert "DDT" in data["subject"], f"Subject should contain 'DDT': {data['subject']}"
        assert data["has_attachment"] == True
        print(f"✓ DDT Preview Email - Subject: {data['subject']}, To: {data['to_email']}")
    
    def test_preventivo_preview_email(self, auth_token, test_data):
        """GET /api/preventivi/{prev_id}/preview-email"""
        url = f"{BASE_URL}/api/preventivi/{test_data['preventivo_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "to_email" in data
        assert "to_name" in data
        assert "subject" in data
        assert "html_body" in data
        assert "has_attachment" in data
        assert "attachment_name" in data
        
        # Verify values
        assert "Preventivo" in data["subject"], f"Subject should contain 'Preventivo': {data['subject']}"
        assert data["has_attachment"] == True
        print(f"✓ Preventivo Preview Email - Subject: {data['subject']}, To: {data['to_email']}")


class TestEmailPreviewErrorCases:
    """Test error handling for preview endpoints."""
    
    def test_rdp_preview_404(self, auth_token, test_data):
        """GET preview-email should return 404 for non-existent RdP."""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/nonexistent_rdp/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ RdP Preview returns 404 for non-existent ID")
    
    def test_oda_preview_404(self, auth_token, test_data):
        """GET preview-email should return 404 for non-existent OdA."""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/ordini/nonexistent_oda/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ OdA Preview returns 404 for non-existent ID")
    
    def test_cl_preview_404(self, auth_token, test_data):
        """GET preview-email should return 404 for non-existent CL."""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/conto-lavoro/nonexistent_cl/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ CL Preview returns 404 for non-existent ID")
    
    def test_invoice_preview_404(self, auth_token):
        """GET preview-email should return 404 for non-existent invoice."""
        url = f"{BASE_URL}/api/invoices/nonexistent_inv/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invoice Preview returns 404 for non-existent ID")
    
    def test_ddt_preview_404(self, auth_token):
        """GET preview-email should return 404 for non-existent DDT."""
        url = f"{BASE_URL}/api/ddt/nonexistent_ddt/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ DDT Preview returns 404 for non-existent ID")
    
    def test_preventivo_preview_404(self, auth_token):
        """GET preview-email should return 404 for non-existent preventivo."""
        url = f"{BASE_URL}/api/preventivi/nonexistent_prev/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Preventivo Preview returns 404 for non-existent ID")


class TestEmailPreviewHtmlContent:
    """Test that HTML body contains proper NormaFacile styled email content."""
    
    def test_invoice_html_has_styling(self, auth_token, test_data):
        """Invoice preview HTML should contain styling and proper content."""
        url = f"{BASE_URL}/api/invoices/{test_data['invoice_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        html = data["html_body"]
        assert len(html) > 100, "HTML body should have substantial content"
        assert "NormaFacile" in html, "HTML should contain NormaFacile branding"
        # Check for common HTML email elements
        assert "<div" in html, "HTML should contain div elements"
        print(f"✓ Invoice HTML has proper styling - {len(html)} chars")
    
    def test_rdp_html_has_styling(self, auth_token, test_data):
        """RdP preview HTML should contain styled content."""
        url = f"{BASE_URL}/api/commesse/{test_data['commessa_id']}/approvvigionamento/richieste/{test_data['rdp_id']}/preview-email"
        headers = {"Authorization": f"Bearer {auth_token['token']}"}
        
        response = requests.get(url, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        html = data["html_body"]
        assert len(html) > 100
        assert "Richiesta" in html or "Preventivo" in html, "HTML should reference RdP content"
        print(f"✓ RdP HTML has proper styling - {len(html)} chars")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

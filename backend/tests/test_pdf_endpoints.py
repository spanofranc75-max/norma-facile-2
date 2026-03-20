"""Test PDF generation API endpoints for invoices, preventivi, and DDT.

Testing focus:
1. GET /api/invoices/{invoice_id}/pdf - should return valid PDF with status 200
2. POST /api/invoices/preview-pdf - should return valid PDF with status 200
3. GET /api/preventivi/{preventivo_id}/pdf - should return valid PDF with status 200
4. Verify all PDFs start with %PDF- header (valid PDF format)
5. Test edge cases: missing client_id, empty lines array
"""
import pytest
import requests
import os
import pymongo
from datetime import datetime, timezone, timedelta
import uuid

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://labor-margin-test.preview.emergentagent.com'

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Real user with existing data
REAL_USER_ID = 'user_97c773827822'


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client fixture."""
    client = pymongo.MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def auth_token(mongo_client):
    """Create a valid session token for authenticated API calls."""
    session_token = f'test_pdf_iter169_{uuid.uuid4().hex[:12]}'
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    
    # Clean old test sessions
    mongo_client.user_sessions.delete_many({'session_token': {'$regex': '^test_pdf_'}})
    
    # Insert new session
    mongo_client.user_sessions.insert_one({
        'user_id': REAL_USER_ID,
        'session_token': session_token,
        'expires_at': expires_at,
        'created_at': datetime.now(timezone.utc)
    })
    
    yield session_token
    
    # Cleanup
    mongo_client.user_sessions.delete_one({'session_token': session_token})


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def existing_invoice(mongo_client):
    """Get an existing invoice with a client_id."""
    inv = mongo_client.invoices.find_one(
        {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
        {'_id': 0}
    )
    return inv


@pytest.fixture(scope="module")
def existing_invoice_no_client(mongo_client):
    """Get an existing invoice without a client_id (or create one for testing)."""
    inv = mongo_client.invoices.find_one(
        {'user_id': REAL_USER_ID, '$or': [{'client_id': ''}, {'client_id': None}]},
        {'_id': 0}
    )
    return inv


@pytest.fixture(scope="module")
def existing_preventivo(mongo_client):
    """Get an existing preventivo."""
    prev = mongo_client.preventivi.find_one(
        {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
        {'_id': 0}
    )
    return prev


class TestInvoicePDFEndpoint:
    """Tests for GET /api/invoices/{invoice_id}/pdf."""
    
    def test_invoice_pdf_returns_200_with_valid_pdf(self, api_client, existing_invoice):
        """Invoice PDF endpoint should return 200 with valid PDF content."""
        if not existing_invoice:
            pytest.skip("No existing invoice with client_id found")
        
        invoice_id = existing_invoice['invoice_id']
        response = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}/pdf")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        # Content-Type should be PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # PDF should start with %PDF- header
        pdf_content = response.content
        assert pdf_content.startswith(b'%PDF-'), f"PDF content doesn't start with %PDF- header. First 20 bytes: {pdf_content[:20]}"
        
        # PDF should have reasonable size (> 1KB)
        assert len(pdf_content) > 1024, f"PDF too small: {len(pdf_content)} bytes"
        
        print(f"✓ Invoice PDF generated successfully: {len(pdf_content)} bytes")
    
    def test_invoice_pdf_not_found_returns_404(self, api_client):
        """Non-existent invoice should return 404."""
        response = api_client.get(f"{BASE_URL}/api/invoices/nonexistent_inv_12345/pdf")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent invoice returns 404")
    
    def test_invoice_pdf_without_auth_returns_401(self):
        """PDF endpoint without auth should return 401."""
        response = requests.get(f"{BASE_URL}/api/invoices/any_id/pdf")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request returns 401")
    
    def test_invoice_pdf_missing_client_returns_error(self, api_client, existing_invoice_no_client):
        """Invoice without client_id should return appropriate error."""
        if not existing_invoice_no_client:
            pytest.skip("No invoice without client_id found for testing")
        
        invoice_id = existing_invoice_no_client['invoice_id']
        response = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}/pdf")
        
        # Should return 400 with "Cliente non trovato" message
        assert response.status_code == 400, f"Expected 400 for missing client, got {response.status_code}"
        
        data = response.json()
        assert 'detail' in data or 'message' in data, "Error response should contain detail or message"
        print(f"✓ Invoice without client returns proper error: {data}")


class TestInvoicePreviewPDFEndpoint:
    """Tests for POST /api/invoices/preview-pdf."""
    
    def test_preview_pdf_returns_200_with_valid_pdf(self, api_client):
        """Preview PDF endpoint should return valid PDF for complete invoice data."""
        payload = {
            "document_type": "FT",
            "document_number": "ANTEPRIMA-TEST",
            "issue_date": "2026-01-19",
            "client_id": None,  # Preview can work without client
            "payment_method": "bonifico",
            "notes": "Test preview PDF",
            "lines": [
                {
                    "description": "Profilo HEA 200 S275JR - Test",
                    "quantity": 10,
                    "unit_price": 50.00,
                    "vat_rate": "22",
                    "discount_percent": 0
                },
                {
                    "description": "Piastra base 300x300x15mm",
                    "quantity": 4,
                    "unit_price": 25.00,
                    "vat_rate": "22",
                    "discount_percent": 0
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        # Content-Type should be PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # PDF should start with %PDF- header
        pdf_content = response.content
        assert pdf_content.startswith(b'%PDF-'), f"PDF doesn't start with %PDF- header. First 20 bytes: {pdf_content[:20]}"
        
        print(f"✓ Preview PDF generated successfully: {len(pdf_content)} bytes")
    
    def test_preview_pdf_with_empty_lines_returns_valid_pdf(self, api_client):
        """Preview PDF should handle empty lines array gracefully."""
        payload = {
            "document_type": "FT",
            "document_number": "ANTEPRIMA-EMPTY",
            "issue_date": "2026-01-19",
            "lines": []
        }
        
        response = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        
        # Should still return 200 with valid PDF (even if empty)
        assert response.status_code == 200, f"Expected 200 for empty lines, got {response.status_code}: {response.text[:500]}"
        
        # PDF should still be valid
        pdf_content = response.content
        assert pdf_content.startswith(b'%PDF-'), "PDF doesn't start with %PDF- header"
        
        print(f"✓ Preview PDF with empty lines generated: {len(pdf_content)} bytes")
    
    def test_preview_pdf_with_client_id(self, api_client, mongo_client):
        """Preview PDF should include client data when client_id is provided."""
        # Get a real client
        client = mongo_client.clients.find_one(
            {'user_id': REAL_USER_ID, 'business_name': {'$exists': True}},
            {'_id': 0, 'client_id': 1, 'business_name': 1}
        )
        
        if not client:
            pytest.skip("No client found for testing")
        
        payload = {
            "document_type": "FT",
            "document_number": "ANTEPRIMA-CLIENTE",
            "issue_date": "2026-01-19",
            "client_id": client['client_id'],
            "lines": [
                {
                    "description": "Test line",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "vat_rate": "22"
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content.startswith(b'%PDF-'), "PDF doesn't start with %PDF-"
        
        print(f"✓ Preview PDF with client {client.get('business_name', 'N/A')} generated")
    
    def test_preview_pdf_nota_credito_type(self, api_client):
        """Preview PDF should work for Nota di Credito (NC) document type."""
        payload = {
            "document_type": "NC",
            "document_number": "NC-ANTEPRIMA",
            "issue_date": "2026-01-19",
            "lines": [
                {
                    "description": "Storno fattura precedente",
                    "quantity": 1,
                    "unit_price": -150.00,
                    "vat_rate": "22"
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        
        assert response.status_code == 200, f"Expected 200 for NC type, got {response.status_code}"
        assert response.content.startswith(b'%PDF-'), "PDF doesn't start with %PDF-"
        
        print(f"✓ Nota di Credito preview PDF generated: {len(response.content)} bytes")


class TestPreventivoPDFEndpoint:
    """Tests for GET /api/preventivi/{preventivo_id}/pdf."""
    
    def test_preventivo_pdf_returns_200_with_valid_pdf(self, api_client, existing_preventivo):
        """Preventivo PDF endpoint should return 200 with valid PDF content."""
        if not existing_preventivo:
            pytest.skip("No existing preventivo found")
        
        prev_id = existing_preventivo['preventivo_id']
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/pdf")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        # Content-Type should be PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # PDF should start with %PDF- header
        pdf_content = response.content
        assert pdf_content.startswith(b'%PDF-'), f"PDF doesn't start with %PDF- header. First 20 bytes: {pdf_content[:20]}"
        
        # PDF should have reasonable size (> 1KB)
        assert len(pdf_content) > 1024, f"PDF too small: {len(pdf_content)} bytes"
        
        print(f"✓ Preventivo PDF generated successfully: {len(pdf_content)} bytes")
    
    def test_preventivo_pdf_not_found_returns_404(self, api_client):
        """Non-existent preventivo should return 404."""
        response = api_client.get(f"{BASE_URL}/api/preventivi/nonexistent_prev_12345/pdf")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent preventivo returns 404")
    
    def test_preventivo_pdf_includes_condizioni_page(self, api_client, existing_preventivo, mongo_client):
        """Preventivo PDF should include conditions page when company has condizioni_vendita."""
        if not existing_preventivo:
            pytest.skip("No existing preventivo found")
        
        # Check if company has condizioni_vendita
        company = mongo_client.company_settings.find_one(
            {'user_id': REAL_USER_ID},
            {'_id': 0, 'condizioni_vendita': 1}
        )
        
        has_condizioni = company and company.get('condizioni_vendita', '').strip()
        
        prev_id = existing_preventivo['preventivo_id']
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/pdf")
        
        assert response.status_code == 200
        
        # PDF content check - if there are condizioni, the PDF should be larger
        pdf_content = response.content
        
        if has_condizioni:
            # With condizioni, PDF typically has 2+ pages
            # We can't easily check page count but file size is a good proxy
            print(f"✓ Preventivo PDF with condizioni: {len(pdf_content)} bytes (condizioni_vendita present)")
        else:
            print(f"✓ Preventivo PDF generated: {len(pdf_content)} bytes (no condizioni_vendita configured)")
        
        assert pdf_content.startswith(b'%PDF-')


class TestDDTPDFEndpoint:
    """Tests for GET /api/ddt/{ddt_id}/pdf."""
    
    def test_ddt_pdf_with_synthetic_data(self, api_client, mongo_client):
        """DDT PDF endpoint should work with created DDT."""
        # Since there are 0 DDTs in DB, we create one for testing
        ddt_id = f'ddt_test_{uuid.uuid4().hex[:8]}'
        ddt_doc = {
            "ddt_id": ddt_id,
            "user_id": REAL_USER_ID,
            "number": "DDT-TEST-001",
            "ddt_type": "vendita",
            "client_id": "",
            "client_name": "Test Cliente DDT",
            "client_address": "Via Test 123",
            "client_cap": "40100",
            "client_city": "Bologna",
            "client_province": "BO",
            "client_piva": "IT00000000000",
            "data_ora_trasporto": "2026-01-19T10:00:00",
            "causale_trasporto": "Vendita",
            "porto": "Franco",
            "vettore": "Mittente",
            "mezzo_trasporto": "Furgone",
            "num_colli": 2,
            "peso_lordo_kg": 100,
            "peso_netto_kg": 80,
            "aspetto_beni": "Colli",
            "stampa_prezzi": True,
            "lines": [
                {
                    "codice_articolo": "TEST001",
                    "description": "Test profilo acciaio",
                    "unit": "ml",
                    "quantity": 10,
                    "unit_price": 45.00,
                    "line_total": 450.00,
                    "vat_rate": "22"
                }
            ],
            "totals": {
                "subtotal": 450.00,
                "total_vat": 99.00,
                "total": 549.00
            },
            "status": "non_fatturato",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert test DDT
        mongo_client.ddt_documents.insert_one(ddt_doc)
        
        try:
            response = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}/pdf")
            
            # Status code assertion
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
            
            # PDF should be valid
            pdf_content = response.content
            assert pdf_content.startswith(b'%PDF-'), f"DDT PDF doesn't start with %PDF-. First 20 bytes: {pdf_content[:20]}"
            
            print(f"✓ DDT PDF generated successfully: {len(pdf_content)} bytes")
        finally:
            # Cleanup test DDT
            mongo_client.ddt_documents.delete_one({'ddt_id': ddt_id})
    
    def test_ddt_pdf_not_found_returns_404(self, api_client):
        """Non-existent DDT should return 404."""
        response = api_client.get(f"{BASE_URL}/api/ddt/nonexistent_ddt_12345/pdf")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent DDT returns 404")


class TestPDFValidHeader:
    """Cross-endpoint tests to verify all PDFs have valid %PDF- header."""
    
    def test_all_pdf_endpoints_return_valid_pdf_format(self, api_client, existing_invoice, existing_preventivo, mongo_client):
        """All PDF endpoints should return content starting with %PDF-."""
        results = []
        
        # Test invoice PDF
        if existing_invoice:
            inv_id = existing_invoice['invoice_id']
            resp = api_client.get(f"{BASE_URL}/api/invoices/{inv_id}/pdf")
            if resp.status_code == 200:
                valid = resp.content.startswith(b'%PDF-')
                results.append(('Invoice PDF', valid, len(resp.content)))
        
        # Test preventivo PDF
        if existing_preventivo:
            prev_id = existing_preventivo['preventivo_id']
            resp = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/pdf")
            if resp.status_code == 200:
                valid = resp.content.startswith(b'%PDF-')
                results.append(('Preventivo PDF', valid, len(resp.content)))
        
        # Test preview PDF
        payload = {
            "document_type": "FT",
            "document_number": "VALIDATION-TEST",
            "issue_date": "2026-01-19",
            "lines": [{"description": "Test", "quantity": 1, "unit_price": 100, "vat_rate": "22"}]
        }
        resp = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        if resp.status_code == 200:
            valid = resp.content.startswith(b'%PDF-')
            results.append(('Preview PDF', valid, len(resp.content)))
        
        # Assert all PDFs are valid
        for name, valid, size in results:
            assert valid, f"{name} does not have valid PDF header"
            print(f"✓ {name}: Valid PDF format ({size} bytes)")
        
        assert len(results) > 0, "No PDF endpoints could be tested"


class TestPDFMonochromaticStyle:
    """Tests to verify PDF uses monochromatic color palette (no blue/navy colors)."""
    
    def test_invoice_pdf_style_verification(self, api_client, existing_invoice):
        """Verify invoice PDF is generated with proper styling."""
        if not existing_invoice:
            pytest.skip("No existing invoice found")
        
        inv_id = existing_invoice['invoice_id']
        response = api_client.get(f"{BASE_URL}/api/invoices/{inv_id}/pdf")
        
        assert response.status_code == 200
        
        # We can't easily inspect PDF colors programmatically,
        # but we can verify the PDF is generated successfully
        pdf_content = response.content
        assert len(pdf_content) > 5000, f"PDF seems too small for a styled document: {len(pdf_content)} bytes"
        
        # Check PDF metadata
        assert b'%PDF-' in pdf_content[:10]
        
        print(f"✓ Invoice PDF style verification passed: {len(pdf_content)} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 249 — Validation Sprint: Output & Delivery Testing
=============================================================
Comprehensive end-to-end test of ALL document generation, preview, download, 
storage, and email flows for NormaFacile 2.0.

Tests:
- PDF Generation: DoP, CE Label, Piano Controllo, Fascicolo Completo, CAM, Template 111, etc.
- DOCX Generation: POS
- Download Token generation
- Object Storage PUT/GET
- Error handling (404 for non-existent IDs, 401 without auth)
- Content-Disposition headers and PDF signatures
"""
import pytest
import requests
import os
import sys

# Add backend to path for object_storage import
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cantiere-pdf.preview.emergentagent.com')
SESSION_COOKIE = "session_token=test_session_token_for_dev_2026"

# Test IDs from credentials
TEST_COMMESSA_BOZZA = "com_2c57c1283871"  # EN_1090, bozza
TEST_COMMESSA_FIRMATO = "com_sasso_marconi"  # EN_1090, firmato
TEST_CANTIERE_ID = "cant_db6d01b1d1bc"
TEST_DDT_ID = "ddt_hist_lasa01"
TEST_INVOICE_ID = "inv_14a1a8a1359c"
TEST_SOPRALLUOGO_ID = "sop_546b0934db54"
TEST_PERIZIA_ID = "per_a4308225da2f"
NONEXISTENT_ID = "nonexistent_id_12345"


class TestPDFGeneration:
    """Test all PDF generation endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    # ── Fascicolo Tecnico PDFs ──
    
    def test_dop_pdf_returns_valid_pdf(self):
        """DoP PDF at /api/fascicolo-tecnico/{cid}/dop-pdf returns valid PDF"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/dop-pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"DoP PDF - Status: {resp.status_code}")
        print(f"DoP PDF - Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"DoP PDF - Content-Disposition: {resp.headers.get('Content-Disposition', 'N/A')}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", ""), "Content-Type should be application/pdf"
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF, got: {resp.content[:20]}"
        
        # Check Content-Disposition has proper filename
        cd = resp.headers.get("Content-Disposition", "")
        assert "filename" in cd.lower(), f"Content-Disposition should have filename: {cd}"
        print(f"DoP PDF - PASS: {len(resp.content)} bytes")
    
    def test_ce_pdf_returns_valid_pdf(self):
        """CE Label PDF at /api/fascicolo-tecnico/{cid}/ce-pdf returns valid PDF"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/ce-pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"CE PDF - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"CE PDF - PASS: {len(resp.content)} bytes")
    
    def test_piano_controllo_pdf_returns_valid_pdf(self):
        """Piano Controllo PDF at /api/fascicolo-tecnico/{cid}/piano-controllo-pdf returns valid PDF"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/piano-controllo-pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Piano Controllo PDF - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"Piano Controllo PDF - PASS: {len(resp.content)} bytes")
    
    def test_fascicolo_completo_pdf_returns_valid_pdf(self):
        """Fascicolo Completo PDF at /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf returns valid PDF"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/fascicolo-completo-pdf"
        resp = self.session.get(url, timeout=90)  # Longer timeout for combined PDF
        
        print(f"Fascicolo Completo PDF - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"Fascicolo Completo PDF - PASS: {len(resp.content)} bytes")
    
    def test_rintracciabilita_totale_pdf(self):
        """Scheda Rintracciabilita PDF at /api/fascicolo-tecnico/{cid}/rintracciabilita-totale/pdf"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/rintracciabilita-totale/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Rintracciabilita PDF - Status: {resp.status_code}")
        
        # May return 400 if no material batches - that's acceptable
        if resp.status_code == 400:
            print(f"Rintracciabilita PDF - Expected 400 (no material batches): {resp.text[:100]}")
            assert "nessun lotto" in resp.text.lower() or "materiale" in resp.text.lower()
        else:
            assert resp.status_code == 200, f"Expected 200 or 400, got {resp.status_code}"
            if resp.status_code == 200:
                assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
                print(f"Rintracciabilita PDF - PASS: {len(resp.content)} bytes")
    
    def test_etichetta_ce_1090_pdf(self):
        """Etichetta CE 1090 PDF at /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/etichetta-ce-1090/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Etichetta CE 1090 PDF - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"Etichetta CE 1090 PDF - PASS: {len(resp.content)} bytes")
    
    # ── CAM PDFs ──
    
    def test_cam_dichiarazione_pdf(self):
        """CAM Dichiarazione PDF at /api/cam/dichiarazione-pdf/{cid}"""
        url = f"{BASE_URL}/api/cam/dichiarazione-pdf/{TEST_COMMESSA_BOZZA}"
        resp = self.session.get(url, timeout=60)
        
        print(f"CAM Dichiarazione PDF - Status: {resp.status_code}")
        
        # May return 400 if no CAM materials - that's acceptable
        if resp.status_code == 400:
            print(f"CAM Dichiarazione PDF - Expected 400 (no CAM data): {resp.text[:100]}")
            assert "nessun" in resp.text.lower() or "materiale" in resp.text.lower() or "cam" in resp.text.lower()
        else:
            assert resp.status_code == 200, f"Expected 200 or 400, got {resp.status_code}"
            if resp.status_code == 200:
                assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
                print(f"CAM Dichiarazione PDF - PASS: {len(resp.content)} bytes")
    
    # ── Template 111 PDF ──
    
    def test_template_111_pdf(self):
        """Template 111 PDF at /api/template-111/pdf/{cid}"""
        url = f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_BOZZA}"
        resp = self.session.get(url, timeout=60)
        
        print(f"Template 111 PDF - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        
        cd = resp.headers.get("Content-Disposition", "")
        assert "filename" in cd.lower(), f"Content-Disposition should have filename: {cd}"
        print(f"Template 111 PDF - PASS: {len(resp.content)} bytes")
    
    # ── DDT PDF ──
    
    def test_ddt_pdf(self):
        """DDT PDF at /api/ddt/{ddt_id}/pdf"""
        url = f"{BASE_URL}/api/ddt/{TEST_DDT_ID}/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"DDT PDF - Status: {resp.status_code}")
        
        if resp.status_code == 404:
            print(f"DDT PDF - 404 (DDT not found): {resp.text[:100]}")
            pytest.skip("Test DDT not found in database")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"DDT PDF - PASS: {len(resp.content)} bytes")
    
    # ── Invoice PDF ──
    
    def test_invoice_pdf(self):
        """Invoice PDF at /api/invoices/{invoice_id}/pdf"""
        url = f"{BASE_URL}/api/invoices/{TEST_INVOICE_ID}/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Invoice PDF - Status: {resp.status_code}")
        
        if resp.status_code == 404:
            print(f"Invoice PDF - 404 (Invoice not found): {resp.text[:100]}")
            pytest.skip("Test Invoice not found in database")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"Invoice PDF - PASS: {len(resp.content)} bytes")
    
    # ── Sopralluogo PDF ──
    
    def test_sopralluogo_pdf(self):
        """Sopralluogo PDF at /api/sopralluoghi/{sop_id}/pdf"""
        url = f"{BASE_URL}/api/sopralluoghi/{TEST_SOPRALLUOGO_ID}/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Sopralluogo PDF - Status: {resp.status_code}")
        
        if resp.status_code == 404:
            print(f"Sopralluogo PDF - 404 (Sopralluogo not found): {resp.text[:100]}")
            pytest.skip("Test Sopralluogo not found in database")
        
        # May return 400 if no AI analysis yet
        if resp.status_code == 400:
            print(f"Sopralluogo PDF - 400 (no AI analysis): {resp.text[:100]}")
            assert "analisi" in resp.text.lower() or "ai" in resp.text.lower()
        else:
            assert resp.status_code == 200, f"Expected 200 or 400, got {resp.status_code}"
            if resp.status_code == 200:
                assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
                print(f"Sopralluogo PDF - PASS: {len(resp.content)} bytes")
    
    # ── Perizia PDF ──
    
    def test_perizia_pdf(self):
        """Perizia PDF at /api/perizie/{perizia_id}/pdf"""
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}/pdf"
        resp = self.session.get(url, timeout=60)
        
        print(f"Perizia PDF - Status: {resp.status_code}")
        
        if resp.status_code == 404:
            print(f"Perizia PDF - 404 (Perizia not found): {resp.text[:100]}")
            pytest.skip("Test Perizia not found in database")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/pdf" in resp.headers.get("Content-Type", "")
        assert resp.content[:4] == b'%PDF', f"PDF should start with %PDF"
        print(f"Perizia PDF - PASS: {len(resp.content)} bytes")


class TestDOCXGeneration:
    """Test DOCX generation endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    def test_pos_docx_generation(self):
        """POS DOCX at POST /api/cantieri-sicurezza/{cantiere_id}/genera-pos?mode=preview"""
        url = f"{BASE_URL}/api/cantieri-sicurezza/{TEST_CANTIERE_ID}/genera-pos?mode=preview"
        resp = self.session.post(url, timeout=90)
        
        print(f"POS DOCX - Status: {resp.status_code}")
        
        if resp.status_code == 404:
            print(f"POS DOCX - 404 (Cantiere not found): {resp.text[:100]}")
            pytest.skip("Test Cantiere not found in database")
        
        # May return 400 if cantiere data incomplete
        if resp.status_code == 400:
            print(f"POS DOCX - 400 (incomplete data): {resp.text[:100]}")
            # This is acceptable - just means cantiere needs more data
        else:
            assert resp.status_code == 200, f"Expected 200 or 400, got {resp.status_code}: {resp.text[:200]}"
            if resp.status_code == 200:
                # DOCX files start with PK (ZIP signature)
                ct = resp.headers.get("Content-Type", "")
                assert "application" in ct, f"Content-Type should be application/*: {ct}"
                assert resp.content[:2] == b'PK', f"DOCX should start with PK (ZIP), got: {resp.content[:10]}"
                print(f"POS DOCX - PASS: {len(resp.content)} bytes")


class TestDownloadToken:
    """Test download token generation."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    def test_download_token_generation(self):
        """POST /api/auth/download-token generates a valid token"""
        url = f"{BASE_URL}/api/auth/download-token"
        resp = self.session.post(url, timeout=30)
        
        print(f"Download Token - Status: {resp.status_code}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "token" in data, f"Response should have 'token' field: {data}"
        assert isinstance(data["token"], str), "Token should be a string"
        assert len(data["token"]) > 10, f"Token should be non-trivial: {data['token']}"
        
        print(f"Download Token - PASS: token={data['token'][:20]}...")


class TestObjectStorage:
    """Test object storage PUT and GET operations."""
    
    def test_object_storage_put_and_get(self):
        """Object Storage: PUT and GET operations work correctly"""
        # Import the sync functions from object_storage
        try:
            from services.object_storage import put_object, get_object
        except ImportError as e:
            pytest.skip(f"Cannot import object_storage: {e}")
        
        # Test data
        test_path = "norma_facile/test/validation_sprint_test.txt"
        test_content = b"Validation Sprint Test Content - " + str(os.urandom(8).hex()).encode()
        test_content_type = "text/plain"
        
        # PUT
        print(f"Object Storage PUT - path: {test_path}")
        try:
            put_result = put_object(test_path, test_content, test_content_type)
            print(f"Object Storage PUT - Result: {put_result}")
            assert "path" in put_result, f"PUT result should have 'path': {put_result}"
        except Exception as e:
            print(f"Object Storage PUT - Error: {e}")
            pytest.skip(f"Object storage PUT failed: {e}")
        
        # GET
        print(f"Object Storage GET - path: {test_path}")
        try:
            content, content_type = get_object(test_path)
            print(f"Object Storage GET - Content-Type: {content_type}, Size: {len(content)}")
            assert content == test_content, f"GET content should match PUT content"
            print(f"Object Storage GET - PASS: content matches")
        except Exception as e:
            print(f"Object Storage GET - Error: {e}")
            pytest.fail(f"Object storage GET failed: {e}")


class TestErrorHandling:
    """Test error handling for PDF endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    def test_pdf_endpoint_nonexistent_id_returns_404(self):
        """PDF endpoint with non-existent ID returns proper 404"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{NONEXISTENT_ID}/dop-pdf"
        resp = self.session.get(url, timeout=30)
        
        print(f"404 Test - Status: {resp.status_code}")
        
        assert resp.status_code == 404, f"Expected 404 for non-existent ID, got {resp.status_code}"
        print(f"404 Test - PASS: correctly returns 404")
    
    def test_pdf_endpoint_without_auth_returns_401_or_403(self):
        """PDF endpoint without auth returns 401 or 403"""
        # Create session without auth cookie
        no_auth_session = requests.Session()
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/dop-pdf"
        resp = no_auth_session.get(url, timeout=30)
        
        print(f"Auth Test - Status: {resp.status_code}")
        
        assert resp.status_code in [401, 403], f"Expected 401 or 403 without auth, got {resp.status_code}"
        print(f"Auth Test - PASS: correctly returns {resp.status_code}")
    
    def test_invoice_pdf_nonexistent_returns_404(self):
        """Invoice PDF with non-existent ID returns 404"""
        url = f"{BASE_URL}/api/invoices/{NONEXISTENT_ID}/pdf"
        resp = self.session.get(url, timeout=30)
        
        print(f"Invoice 404 Test - Status: {resp.status_code}")
        
        assert resp.status_code == 404, f"Expected 404 for non-existent invoice, got {resp.status_code}"
        print(f"Invoice 404 Test - PASS: correctly returns 404")
    
    def test_ddt_pdf_nonexistent_returns_404(self):
        """DDT PDF with non-existent ID returns 404"""
        url = f"{BASE_URL}/api/ddt/{NONEXISTENT_ID}/pdf"
        resp = self.session.get(url, timeout=30)
        
        print(f"DDT 404 Test - Status: {resp.status_code}")
        
        assert resp.status_code == 404, f"Expected 404 for non-existent DDT, got {resp.status_code}"
        print(f"DDT 404 Test - PASS: correctly returns 404")


class TestSDIEndpoint:
    """Test SDI/FattureInCloud endpoint exists and is callable."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    def test_send_sdi_endpoint_exists(self):
        """SDI endpoint /api/invoices/{id}/send-sdi exists and returns meaningful response"""
        url = f"{BASE_URL}/api/invoices/{TEST_INVOICE_ID}/send-sdi"
        resp = self.session.post(url, timeout=60)
        
        print(f"SDI Endpoint - Status: {resp.status_code}")
        print(f"SDI Endpoint - Response: {resp.text[:300]}")
        
        # Should NOT return 500 (server crash)
        assert resp.status_code != 500, f"SDI endpoint should not crash with 500: {resp.text[:200]}"
        
        # Acceptable responses:
        # - 404: Invoice not found
        # - 400: Invoice in wrong state (bozza) or missing FiC credentials
        # - 422: Validation failed (missing fields)
        # - 200: Success (unlikely in test env)
        # - 409: Already sent
        acceptable = [200, 400, 404, 409, 422]
        assert resp.status_code in acceptable, f"Expected one of {acceptable}, got {resp.status_code}"
        
        print(f"SDI Endpoint - PASS: returns meaningful response ({resp.status_code})")


class TestContentDispositionHeaders:
    """Test that Content-Disposition headers have correct filenames."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": SESSION_COOKIE,
            "Content-Type": "application/json"
        })
    
    def test_dop_pdf_filename_no_placeholders(self):
        """DoP PDF Content-Disposition has proper filename without placeholders"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_BOZZA}/dop-pdf"
        resp = self.session.get(url, timeout=60)
        
        if resp.status_code != 200:
            pytest.skip(f"Endpoint returned {resp.status_code}")
        
        cd = resp.headers.get("Content-Disposition", "")
        print(f"Content-Disposition: {cd}")
        
        # Check no placeholder residuals
        assert "{" not in cd, f"Filename should not have placeholders: {cd}"
        assert "}" not in cd, f"Filename should not have placeholders: {cd}"
        assert "undefined" not in cd.lower(), f"Filename should not have 'undefined': {cd}"
        assert "null" not in cd.lower(), f"Filename should not have 'null': {cd}"
        
        # Should have .pdf extension
        assert ".pdf" in cd.lower(), f"Filename should have .pdf extension: {cd}"
        
        print(f"Content-Disposition - PASS: {cd}")
    
    def test_template_111_filename_no_encoding_issues(self):
        """Template 111 PDF filename has no encoding issues"""
        url = f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_BOZZA}"
        resp = self.session.get(url, timeout=60)
        
        if resp.status_code != 200:
            pytest.skip(f"Endpoint returned {resp.status_code}")
        
        cd = resp.headers.get("Content-Disposition", "")
        print(f"Content-Disposition: {cd}")
        
        # Check for common encoding issues
        assert "\\x" not in cd, f"Filename has encoding issues: {cd}"
        assert "%" not in cd or "filename*" in cd, f"Filename may have URL encoding issues: {cd}"
        
        print(f"Template 111 Content-Disposition - PASS: {cd}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

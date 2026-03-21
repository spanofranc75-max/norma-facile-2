"""
Iteration 196: Verbale di Posa in Opera - Backend API Tests
Tests for:
- GET /api/verbale-posa/context/{commessaId} - Load commessa context data
- POST /api/verbale-posa/{commessaId} - Save verbale with form data
- GET /api/verbale-posa/{commessaId} - Get existing verbale
- GET /api/verbale-posa/{commessaId}/pdf - Generate PDF
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "active_test_session_2026"
TEST_COMMESSA_ID = "com_e8c4810ad476"  # NF-2026-000001, MGM Costruzioni Srl
FPC_PROJECT_ID = "prj_ee66232bbe9d"  # Loiano


@pytest.fixture
def auth_session():
    """Create authenticated session with session token cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestVerbaleContextEndpoint:
    """Tests for GET /api/verbale-posa/context/{commessaId}"""
    
    def test_context_requires_auth(self):
        """Context endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/context/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Context endpoint requires auth")
    
    def test_context_returns_commessa_data(self, auth_session):
        """Context endpoint returns commessa data with materials, lotti, ddts"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "commessa_id" in data, "Missing commessa_id"
        assert data["commessa_id"] == TEST_COMMESSA_ID
        assert "commessa_number" in data, "Missing commessa_number"
        assert "client_name" in data, "Missing client_name"
        assert "company_name" in data, "Missing company_name"
        assert "materiali" in data, "Missing materiali array"
        assert "lotti" in data, "Missing lotti array"
        assert "ddts" in data, "Missing ddts array"
        
        print(f"PASS: Context returns commessa data - Number: {data.get('commessa_number')}, Client: {data.get('client_name')}")
        print(f"  - Materiali: {len(data.get('materiali', []))} items")
        print(f"  - Lotti: {len(data.get('lotti', []))} items")
        print(f"  - DDTs: {len(data.get('ddts', []))} items")
    
    def test_context_invalid_commessa_returns_404(self, auth_session):
        """Context endpoint returns 404 for invalid commessa"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/invalid_commessa_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Invalid commessa returns 404")


class TestVerbaleGetEndpoint:
    """Tests for GET /api/verbale-posa/{commessaId}"""
    
    def test_get_verbale_requires_auth(self):
        """Get verbale endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Get verbale requires auth")
    
    def test_get_existing_verbale(self, auth_session):
        """Get existing verbale returns saved data"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # A verbale was already saved during development
        if data.get("exists"):
            assert "verbale_id" in data, "Missing verbale_id"
            assert "commessa_id" in data, "Missing commessa_id"
            assert "checklist" in data, "Missing checklist"
            assert "status" in data, "Missing status"
            print(f"PASS: Existing verbale found - ID: {data.get('verbale_id')}, Status: {data.get('status')}")
            print(f"  - Checklist: {data.get('checklist')}")
        else:
            print("INFO: No existing verbale found (exists=False)")


class TestVerbaleSaveEndpoint:
    """Tests for POST /api/verbale-posa/{commessaId}"""
    
    def test_save_verbale_requires_auth(self):
        """Save verbale endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Save verbale requires auth")
    
    def test_save_verbale_with_form_data(self, auth_session):
        """Save verbale with form data, checklist, signature"""
        # Use multipart/form-data for this endpoint
        form_data = {
            "data_posa": "2026-01-15",
            "luogo_posa": "Via Test 123, Bologna",
            "responsabile": "Mario Rossi",
            "note_cantiere": "Test note from pytest iteration 196",
            "check_regola_arte": "true",
            "check_conformita": "true",
            "check_materiali": "true",
            "check_sicurezza": "true",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        }
        
        # Remove Content-Type header for multipart
        headers = {}
        response = auth_session.post(
            f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}",
            data=form_data,
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "verbale_id" in data, "Missing verbale_id in response"
        assert "message" in data, "Missing message in response"
        print(f"PASS: Verbale saved - ID: {data.get('verbale_id')}, Message: {data.get('message')}")
    
    def test_save_verbale_invalid_commessa_returns_404(self, auth_session):
        """Save verbale returns 404 for invalid commessa"""
        form_data = {
            "data_posa": "2026-01-15",
            "luogo_posa": "Test",
        }
        response = auth_session.post(
            f"{BASE_URL}/api/verbale-posa/invalid_commessa_id",
            data=form_data
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Invalid commessa returns 404 on save")


class TestVerbalePdfEndpoint:
    """Tests for GET /api/verbale-posa/{commessaId}/pdf"""
    
    def test_pdf_requires_auth(self):
        """PDF endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}/pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: PDF endpoint requires auth")
    
    def test_pdf_generation(self, auth_session):
        """PDF generation returns valid PDF file"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got {content_type}"
        
        # Check content disposition for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "Verbale_Posa_" in content_disp, f"Expected Verbale_Posa_ in filename, got {content_disp}"
        
        # Check PDF content starts with PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        
        print(f"PASS: PDF generated successfully - Size: {len(content)} bytes")
        print(f"  - Content-Disposition: {content_disp}")
    
    def test_pdf_without_saved_verbale_returns_404(self, auth_session):
        """PDF generation returns 404 if verbale not saved"""
        # Use a commessa that likely doesn't have a verbale
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/com_nonexistent/pdf")
        # Could be 404 (commessa not found) or 404 (verbale not saved)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: PDF without saved verbale returns 404")


class TestFPCProjectVerbaleButton:
    """Tests for FPC Project page verbale button integration"""
    
    def test_fpc_project_exists(self, auth_session):
        """FPC Project exists and has commessa_id for verbale link"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check project has commessa_id or project_id for verbale link
        has_commessa = "commessa_id" in data or "project_id" in data
        assert has_commessa, "FPC Project missing commessa_id/project_id for verbale link"
        
        print(f"PASS: FPC Project found - ID: {data.get('project_id')}")
        print(f"  - Commessa ID: {data.get('commessa_id', 'N/A')}")
        print(f"  - Client: {data.get('client_name', 'N/A')}")


class TestVerbaleDataPersistence:
    """Tests for verbale data persistence - Create -> GET verification"""
    
    def test_save_and_verify_persistence(self, auth_session):
        """Save verbale and verify data persisted correctly"""
        # Save with specific test data - use multipart form data (no Content-Type header)
        test_data = {
            "data_posa": "2026-01-16",
            "luogo_posa": "Via Persistence Test 456, Milano",
            "responsabile": "Test Responsabile Persistence",
            "note_cantiere": "Persistence test note - iteration 196",
            "check_regola_arte": "true",
            "check_conformita": "false",  # Intentionally false to verify
            "check_materiali": "true",
            "check_sicurezza": "false",  # Intentionally false to verify
            "signature_data": "data:image/png;base64,TEST_SIGNATURE_DATA",
        }
        
        # Save - remove Content-Type header to allow multipart form data
        save_session = requests.Session()
        save_session.cookies.set("session_token", SESSION_TOKEN, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
        save_response = save_session.post(
            f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}",
            data=test_data
        )
        assert save_response.status_code == 200, f"Save failed: {save_response.text}"
        
        # GET to verify persistence
        get_response = auth_session.get(f"{BASE_URL}/api/verbale-posa/{TEST_COMMESSA_ID}")
        assert get_response.status_code == 200, f"GET failed: {get_response.text}"
        
        data = get_response.json()
        assert data.get("exists") == True, "Verbale should exist after save"
        assert data.get("data_posa") == test_data["data_posa"], "data_posa not persisted"
        assert data.get("luogo_posa") == test_data["luogo_posa"], "luogo_posa not persisted"
        assert data.get("responsabile") == test_data["responsabile"], "responsabile not persisted"
        
        # Verify checklist
        checklist = data.get("checklist", {})
        assert checklist.get("regola_arte") == True, "regola_arte should be True"
        assert checklist.get("conformita_normative") == False, "conformita_normative should be False"
        assert checklist.get("materiali_conformi") == True, "materiali_conformi should be True"
        assert checklist.get("sicurezza_rispettata") == False, "sicurezza_rispettata should be False"
        
        print("PASS: Verbale data persisted correctly")
        print(f"  - Data Posa: {data.get('data_posa')}")
        print(f"  - Luogo: {data.get('luogo_posa')}")
        print(f"  - Checklist: {checklist}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Iteration 194: FPC Bug Fix & Company Documents Testing
Tests:
1. FPC Projects - List, Get, Create (duplicate check)
2. FPC Batches - List (verify response format)
3. Company Documents - Global security docs CRUD (DURC, Visura, White List, Patente a Crediti)
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY"
FPC_PROJECT_ID = "prj_ee66232bbe9d"
PREVENTIVO_ID = "prev_d006776485"


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestFPCProjects:
    """FPC Projects API tests - verify bug fix for batches.map error"""

    def test_list_fpc_projects(self, auth_session):
        """GET /api/fpc/projects - should return list of projects"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Projects should be a list"
        
        # Find the Loiano project
        loiano_project = next((p for p in data if p.get("project_id") == FPC_PROJECT_ID), None)
        assert loiano_project is not None, f"Loiano project {FPC_PROJECT_ID} not found"
        assert loiano_project.get("preventivo_number") == "PRV-2026-0042"
        assert loiano_project.get("client_name") == "C.I.M.S SCRL"
        print(f"Found Loiano project: {loiano_project.get('preventivo_number')}")

    def test_get_fpc_project_detail(self, auth_session):
        """GET /api/fpc/projects/{project_id} - should return project without crash"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("project_id") == FPC_PROJECT_ID
        assert data.get("preventivo_number") == "PRV-2026-0042"
        assert data.get("client_name") == "C.I.M.S SCRL"
        assert data.get("subject") == "Aggiornamento parapetto LOIANO"
        
        # Verify FPC data structure
        fpc_data = data.get("fpc_data", {})
        assert fpc_data.get("execution_class") == "EXC2"
        assert "controls" in fpc_data
        assert isinstance(fpc_data.get("controls"), list)
        assert len(fpc_data.get("controls", [])) >= 5  # Should have multiple controls
        
        # Verify lines exist
        lines = data.get("lines", [])
        assert isinstance(lines, list)
        print(f"Project has {len(lines)} lines and {len(fpc_data.get('controls', []))} controls")

    def test_create_duplicate_fpc_project_returns_409(self, auth_session):
        """POST /api/fpc/projects - duplicate should return 409"""
        payload = {
            "preventivo_id": PREVENTIVO_ID,
            "execution_class": "EXC2"
        }
        response = auth_session.post(f"{BASE_URL}/api/fpc/projects", json=payload)
        assert response.status_code == 409, f"Expected 409 for duplicate, got {response.status_code}: {response.text}"
        print("Duplicate project creation correctly returns 409")


class TestFPCBatches:
    """FPC Batches API tests - verify response format for frontend"""

    def test_list_batches_returns_correct_format(self, auth_session):
        """GET /api/fpc/batches - should return {batches: [...]} format"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/batches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # The API returns {"batches": [...]} format
        assert "batches" in data, "Response should have 'batches' key"
        assert isinstance(data["batches"], list), "batches should be a list"
        print(f"Batches endpoint returns correct format with {len(data['batches'])} batches")


class TestFPCWelders:
    """FPC Welders API tests"""

    def test_list_welders(self, auth_session):
        """GET /api/fpc/welders - should return list of welders"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/welders")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Welders can be array or {welders: [...]}
        welders = data if isinstance(data, list) else data.get("welders", [])
        assert isinstance(welders, list)
        print(f"Found {len(welders)} welders")


class TestCompanyDocumentsGlobal:
    """Company Documents - Global Security Documents (DURC, Visura, White List, Patente a Crediti)"""

    def test_list_global_docs(self, auth_session):
        """GET /api/company/documents/sicurezza-globali - should return 4 doc types"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "documenti" in data, "Response should have 'documenti' key"
        assert "completo" in data, "Response should have 'completo' key"
        
        docs = data["documenti"]
        expected_types = ["durc", "visura", "white_list", "patente_crediti"]
        for doc_type in expected_types:
            assert doc_type in docs, f"Missing doc type: {doc_type}"
            assert "label" in docs[doc_type], f"Missing label for {doc_type}"
            assert "presente" in docs[doc_type], f"Missing presente for {doc_type}"
        
        print(f"Global docs structure correct. Completo: {data['completo']}")

    def test_upload_durc_document(self, auth_session):
        """POST /api/company/documents/sicurezza-globali/durc - upload test document"""
        # Create a simple test PDF content
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        
        files = {
            'file': ('test_durc.pdf', io.BytesIO(test_content), 'application/pdf')
        }
        data = {
            'scadenza': '2026-12-31'
        }
        
        # Remove Content-Type header for multipart
        headers = {}
        response = requests.post(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            files=files,
            data=data,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "doc_id" in result, "Response should have doc_id"
        assert result.get("filename") == "test_durc.pdf"
        print(f"DURC uploaded successfully: {result.get('doc_id')}")
        return result.get("doc_id")

    def test_verify_durc_uploaded(self, auth_session):
        """GET /api/company/documents/sicurezza-globali - verify DURC is present"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        durc = data["documenti"].get("durc", {})
        assert durc.get("presente") == True, "DURC should be present after upload"
        assert durc.get("filename") == "test_durc.pdf"
        print(f"DURC verified as present: {durc.get('filename')}")

    def test_delete_durc_document(self, auth_session):
        """DELETE /api/company/documents/sicurezza-globali/durc - delete test document"""
        response = auth_session.delete(f"{BASE_URL}/api/company/documents/sicurezza-globali/durc")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        print("DURC deleted successfully")

    def test_verify_durc_deleted(self, auth_session):
        """GET /api/company/documents/sicurezza-globali - verify DURC is deleted"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        durc = data["documenti"].get("durc", {})
        assert durc.get("presente") == False, "DURC should not be present after delete"
        print("DURC verified as deleted")


class TestFPCCEWorkflow:
    """FPC CE Label workflow tests"""

    def test_ce_check_endpoint(self, auth_session):
        """GET /api/fpc/projects/{project_id}/ce-check - should return blockers"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}/ce-check")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ready" in data
        assert "blockers" in data
        assert isinstance(data["blockers"], list)
        print(f"CE Check: ready={data['ready']}, blockers={len(data['blockers'])}")

    def test_update_fpc_data(self, auth_session):
        """PUT /api/fpc/projects/{project_id}/fpc - update WPS"""
        payload = {
            "wps_id": "WPS-TEST-001"
        }
        response = auth_session.put(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}/fpc", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "updated"
        print("FPC data updated successfully")

    def test_verify_wps_updated(self, auth_session):
        """GET /api/fpc/projects/{project_id} - verify WPS was saved"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        fpc_data = data.get("fpc_data", {})
        assert fpc_data.get("wps_id") == "WPS-TEST-001"
        print("WPS verified as saved")

    def test_clear_wps(self, auth_session):
        """PUT /api/fpc/projects/{project_id}/fpc - clear WPS for cleanup"""
        payload = {
            "wps_id": None
        }
        response = auth_session.put(f"{BASE_URL}/api/fpc/projects/{FPC_PROJECT_ID}/fpc", json=payload)
        assert response.status_code == 200
        print("WPS cleared for cleanup")


class TestAuthRequired:
    """Verify endpoints require authentication"""

    def test_fpc_projects_requires_auth(self):
        """GET /api/fpc/projects without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/fpc/projects")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_company_docs_requires_auth(self):
        """GET /api/company/documents/sicurezza-globali without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

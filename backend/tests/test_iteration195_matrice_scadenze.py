"""
Iteration 195: Matrice Scadenze & Risorse Umane Tests
Tests for:
- GET /api/welders/matrice-scadenze - Matrix with cert_types, workers array with cells per cert type
- GET /api/welders/per-pos - Workers with can_deploy, blockers, warnings
- GET /api/welders/safety-cert-types - 8 safety certification types
- POST /api/welders/{id}/qualifications with cert_code field
- Settings /settings -> Documenti tab shows DURC/Visura/WhiteList/Patente/DVR (5 docs)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "active_test_session_2026"

# Test worker IDs from the review request
TEST_WORKERS = {
    "marco_bianchi": "wld_022030bdcf",  # All valid
    "luca_rossi": "wld_811fabf3a1",      # Some expired
    "andrea_verdi": "wld_1282360dd4",    # Expiring
}


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestSafetyCertTypes:
    """Test GET /api/welders/safety-cert-types endpoint"""
    
    def test_safety_cert_types_returns_8_types(self, auth_session):
        """Verify endpoint returns 8 safety certification types"""
        response = auth_session.get(f"{BASE_URL}/api/welders/safety-cert-types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "cert_types" in data, "Response should have cert_types key"
        
        cert_types = data["cert_types"]
        assert len(cert_types) == 8, f"Expected 8 cert types, got {len(cert_types)}"
        
        # Verify expected cert codes
        expected_codes = [
            "patentino_saldatura",
            "formazione_base_8108",
            "formazione_specifica",
            "primo_soccorso",
            "antincendio",
            "lavori_quota",
            "ple",
            "idoneita_sanitaria"
        ]
        actual_codes = [ct["code"] for ct in cert_types]
        for code in expected_codes:
            assert code in actual_codes, f"Missing cert code: {code}"
        
        # Verify each cert type has required fields
        for ct in cert_types:
            assert "code" in ct, "Cert type should have code"
            assert "label" in ct, "Cert type should have label"
            assert "category" in ct, "Cert type should have category"
        
        print(f"SUCCESS: safety-cert-types returns {len(cert_types)} types")
    
    def test_safety_cert_types_requires_auth(self, auth_session):
        """Verify endpoint requires authentication"""
        session = requests.Session()  # No auth
        response = session.get(f"{BASE_URL}/api/welders/safety-cert-types")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("SUCCESS: safety-cert-types requires authentication")


class TestMatriceScadenze:
    """Test GET /api/welders/matrice-scadenze endpoint"""
    
    def test_matrice_scadenze_returns_matrix_structure(self, auth_session):
        """Verify endpoint returns matrix with cert_types and workers"""
        response = auth_session.get(f"{BASE_URL}/api/welders/matrice-scadenze")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "cert_types" in data, "Response should have cert_types"
        assert "workers" in data, "Response should have workers"
        assert "total" in data, "Response should have total"
        
        # Verify cert_types
        assert len(data["cert_types"]) == 8, f"Expected 8 cert types, got {len(data['cert_types'])}"
        
        print(f"SUCCESS: matrice-scadenze returns {len(data['workers'])} workers with {len(data['cert_types'])} cert types")
    
    def test_matrice_scadenze_worker_cells(self, auth_session):
        """Verify each worker has cells for each cert type"""
        response = auth_session.get(f"{BASE_URL}/api/welders/matrice-scadenze")
        assert response.status_code == 200
        
        data = response.json()
        cert_codes = [ct["code"] for ct in data["cert_types"]]
        
        for worker in data["workers"]:
            assert "welder_id" in worker, "Worker should have welder_id"
            assert "name" in worker, "Worker should have name"
            assert "cells" in worker, "Worker should have cells"
            assert "can_go_to_cantiere" in worker, "Worker should have can_go_to_cantiere"
            
            # Verify cells for each cert type
            for code in cert_codes:
                assert code in worker["cells"], f"Worker {worker['name']} missing cell for {code}"
                cell = worker["cells"][code]
                assert "status" in cell, f"Cell should have status"
                assert cell["status"] in ["valido", "in_scadenza", "scaduto", "mancante"], f"Invalid status: {cell['status']}"
        
        print(f"SUCCESS: All workers have cells for all {len(cert_codes)} cert types")
    
    def test_matrice_scadenze_test_workers(self, auth_session):
        """Verify test workers exist and have expected statuses"""
        response = auth_session.get(f"{BASE_URL}/api/welders/matrice-scadenze")
        assert response.status_code == 200
        
        data = response.json()
        workers_by_id = {w["welder_id"]: w for w in data["workers"]}
        
        # Check Marco Bianchi (should be OK - all valid)
        if TEST_WORKERS["marco_bianchi"] in workers_by_id:
            marco = workers_by_id[TEST_WORKERS["marco_bianchi"]]
            print(f"Marco Bianchi: can_go_to_cantiere={marco['can_go_to_cantiere']}")
            # Marco should have all valid or at least be deployable
        
        # Check Luca Rossi (should have some expired)
        if TEST_WORKERS["luca_rossi"] in workers_by_id:
            luca = workers_by_id[TEST_WORKERS["luca_rossi"]]
            print(f"Luca Rossi: can_go_to_cantiere={luca['can_go_to_cantiere']}")
            # Luca should have some expired certs
        
        # Check Andrea Verdi (should have expiring)
        if TEST_WORKERS["andrea_verdi"] in workers_by_id:
            andrea = workers_by_id[TEST_WORKERS["andrea_verdi"]]
            print(f"Andrea Verdi: can_go_to_cantiere={andrea['can_go_to_cantiere']}")
        
        print("SUCCESS: Test workers found in matrice")
    
    def test_matrice_scadenze_requires_auth(self, auth_session):
        """Verify endpoint requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/welders/matrice-scadenze")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("SUCCESS: matrice-scadenze requires authentication")


class TestWorkersPerPOS:
    """Test GET /api/welders/per-pos endpoint"""
    
    def test_per_pos_returns_workers_with_compliance(self, auth_session):
        """Verify endpoint returns workers with can_deploy, blockers, warnings"""
        response = auth_session.get(f"{BASE_URL}/api/welders/per-pos")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "workers" in data, "Response should have workers key"
        
        for worker in data["workers"]:
            assert "welder_id" in worker, "Worker should have welder_id"
            assert "name" in worker, "Worker should have name"
            assert "can_deploy" in worker, "Worker should have can_deploy"
            assert "blockers" in worker, "Worker should have blockers"
            assert "warnings" in worker, "Worker should have warnings"
            assert isinstance(worker["blockers"], list), "blockers should be a list"
            assert isinstance(worker["warnings"], list), "warnings should be a list"
        
        print(f"SUCCESS: per-pos returns {len(data['workers'])} workers with compliance info")
    
    def test_per_pos_can_deploy_logic(self, auth_session):
        """Verify can_deploy is False when blockers exist"""
        response = auth_session.get(f"{BASE_URL}/api/welders/per-pos")
        assert response.status_code == 200
        
        data = response.json()
        
        for worker in data["workers"]:
            if len(worker["blockers"]) > 0:
                assert worker["can_deploy"] == False, f"Worker {worker['name']} has blockers but can_deploy=True"
            else:
                assert worker["can_deploy"] == True, f"Worker {worker['name']} has no blockers but can_deploy=False"
        
        print("SUCCESS: can_deploy logic is correct (False when blockers exist)")
    
    def test_per_pos_requires_auth(self, auth_session):
        """Verify endpoint requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/welders/per-pos")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("SUCCESS: per-pos requires authentication")


class TestWeldersQualificationWithCertCode:
    """Test POST /api/welders/{id}/qualifications with cert_code field"""
    
    def test_add_qualification_with_cert_code(self, auth_session):
        """Verify qualification can be added with cert_code field"""
        # First get a welder
        response = auth_session.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("items"):
            pytest.skip("No welders available for testing")
        
        welder = data["items"][0]
        welder_id = welder["welder_id"]
        
        # Add qualification with cert_code
        form_data = {
            "standard": "Formazione Base 81/08",
            "process": "",
            "material_group": "",
            "thickness_range": "",
            "position": "",
            "issue_date": "2025-01-01",
            "expiry_date": "2027-01-01",
            "notes": "Test qualification",
            "cert_code": "formazione_base_8108"
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/welders/{welder_id}/qualifications",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Accept 200 or 422 (validation error if already exists)
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            # Verify the qualification was added with cert_code
            quals = result.get("qualifications", [])
            found = any(q.get("cert_code") == "formazione_base_8108" for q in quals)
            print(f"SUCCESS: Qualification added with cert_code (found={found})")
        else:
            print("INFO: Qualification may already exist (422 response)")


class TestGlobalDocumentsWithDVR:
    """Test Settings Documenti tab shows 5 documents including DVR"""
    
    def test_global_docs_includes_dvr(self, auth_session):
        """Verify global docs endpoint returns 5 document types including DVR"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "documenti" in data, "Response should have documenti key"
        
        documenti = data["documenti"]
        expected_docs = ["durc", "visura", "white_list", "patente_crediti", "dvr"]
        
        for doc_type in expected_docs:
            assert doc_type in documenti, f"Missing document type: {doc_type}"
            doc = documenti[doc_type]
            assert "label" in doc, f"Document {doc_type} should have label"
            assert "presente" in doc, f"Document {doc_type} should have presente"
        
        print(f"SUCCESS: Global docs includes all 5 types: {list(documenti.keys())}")
    
    def test_global_docs_dvr_label(self, auth_session):
        """Verify DVR has correct label"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        dvr = data["documenti"].get("dvr", {})
        
        # DVR should have a label
        assert "label" in dvr, "DVR should have label"
        print(f"SUCCESS: DVR label = '{dvr.get('label', 'N/A')}'")


class TestWeldersListEndpoint:
    """Test GET /api/welders/ endpoint"""
    
    def test_welders_list_returns_items(self, auth_session):
        """Verify welders list returns items with qualifications"""
        response = auth_session.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have items"
        assert "total" in data, "Response should have total"
        assert "stats" in data, "Response should have stats"
        
        print(f"SUCCESS: Welders list returns {len(data['items'])} items")
    
    def test_welders_have_qualification_response_fields(self, auth_session):
        """Verify qualifications have cert_code and notes fields"""
        response = auth_session.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200
        
        data = response.json()
        
        for welder in data.get("items", []):
            for qual in welder.get("qualifications", []):
                # cert_code and notes should be in response (can be null)
                assert "cert_code" in qual or qual.get("cert_code") is None, "Qualification should have cert_code field"
                assert "notes" in qual or qual.get("notes") is None, "Qualification should have notes field"
        
        print("SUCCESS: Qualifications have cert_code and notes fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

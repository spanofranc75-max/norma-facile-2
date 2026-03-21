"""
Iteration 206: DOP Automatica + Etichetta CE EN 1090 Tests
Tests for:
- POST /api/fascicolo-tecnico/{cid}/dop-automatica — Creates automatic DOP
- GET /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf — PDF DOP with verification sections
- GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf — CE Label PDF for EN 1090
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "comm_sasso_marconi"  # EN 1090 commessa


@pytest.fixture
def auth_cookies():
    """Return auth cookies for requests"""
    return {"session_token": SESSION_TOKEN}


@pytest.fixture
def session(auth_cookies):
    """Create a requests session with auth cookies"""
    s = requests.Session()
    s.cookies.update(auth_cookies)
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestDopAutomatica:
    """Tests for POST /api/fascicolo-tecnico/{cid}/dop-automatica endpoint"""

    def test_create_dop_automatica_success(self, session):
        """Test creating an automatic DOP returns 200 with expected structure"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica"
        response = session.post(url)
        
        print(f"DOP Automatica Response Status: {response.status_code}")
        print(f"DOP Automatica Response: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "dop" in data, "Response should contain 'dop' object"
        
        dop = data["dop"]
        # Verify DOP structure
        assert "dop_id" in dop, "DOP should have dop_id"
        assert "dop_numero" in dop, "DOP should have dop_numero"
        assert "commessa_id" in dop, "DOP should have commessa_id"
        assert dop["commessa_id"] == TEST_COMMESSA_ID
        assert "automatica" in dop and dop["automatica"] == True, "DOP should be marked as automatica"
        
        # Verify auto-populated fields
        assert "classe_esecuzione" in dop, "DOP should have classe_esecuzione"
        assert "riesame" in dop, "DOP should have riesame section"
        assert "ispezioni" in dop, "DOP should have ispezioni section"
        assert "controllo_finale" in dop, "DOP should have controllo_finale section"
        
        # Store dop_id for subsequent tests
        pytest.dop_id = dop["dop_id"]
        print(f"Created DOP ID: {pytest.dop_id}")

    def test_dop_automatica_riesame_structure(self, session):
        """Test that riesame section has expected structure"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica"
        response = session.post(url)
        
        assert response.status_code == 200
        dop = response.json()["dop"]
        
        riesame = dop.get("riesame", {})
        assert "approvato" in riesame, "Riesame should have 'approvato' field"
        assert "firma" in riesame, "Riesame should have 'firma' field"
        assert "data_approvazione" in riesame, "Riesame should have 'data_approvazione' field"
        
        pytest.dop_id = dop["dop_id"]

    def test_dop_automatica_ispezioni_structure(self, session):
        """Test that ispezioni section has expected structure"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica"
        response = session.post(url)
        
        assert response.status_code == 200
        dop = response.json()["dop"]
        
        ispezioni = dop.get("ispezioni", {})
        assert "approvato" in ispezioni, "Ispezioni should have 'approvato' field"
        assert "vt_ok" in ispezioni, "Ispezioni should have 'vt_ok' field"
        assert "vt_totale" in ispezioni, "Ispezioni should have 'vt_totale' field"
        assert "dim_ok" in ispezioni, "Ispezioni should have 'dim_ok' field"
        assert "dim_totale" in ispezioni, "Ispezioni should have 'dim_totale' field"
        
        pytest.dop_id = dop["dop_id"]

    def test_dop_automatica_controllo_finale_structure(self, session):
        """Test that controllo_finale section has expected structure"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica"
        response = session.post(url)
        
        assert response.status_code == 200
        dop = response.json()["dop"]
        
        cf = dop.get("controllo_finale", {})
        assert "approvato" in cf, "Controllo finale should have 'approvato' field"
        assert "firma" in cf, "Controllo finale should have 'firma' field"
        assert "data_approvazione" in cf, "Controllo finale should have 'data_approvazione' field"
        
        pytest.dop_id = dop["dop_id"]

    def test_dop_automatica_invalid_commessa(self, session):
        """Test that invalid commessa returns 404"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/invalid_commessa_xyz/dop-automatica"
        response = session.post(url)
        
        assert response.status_code == 404, f"Expected 404 for invalid commessa, got {response.status_code}"


class TestDopPdf:
    """Tests for GET /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf endpoint"""

    def test_dop_pdf_generation(self, session):
        """Test PDF generation for automatic DOP"""
        # First create a DOP
        create_url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica"
        create_response = session.post(create_url)
        
        assert create_response.status_code == 200, f"Failed to create DOP: {create_response.text}"
        dop_id = create_response.json()["dop"]["dop_id"]
        
        # Now get the PDF
        pdf_url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionata/{dop_id}/pdf"
        pdf_response = session.get(pdf_url)
        
        print(f"DOP PDF Response Status: {pdf_response.status_code}")
        print(f"DOP PDF Content-Type: {pdf_response.headers.get('Content-Type', 'N/A')}")
        print(f"DOP PDF Content-Length: {len(pdf_response.content)} bytes")
        
        assert pdf_response.status_code == 200, f"Expected 200, got {pdf_response.status_code}: {pdf_response.text[:200] if pdf_response.text else 'empty'}"
        assert "application/pdf" in pdf_response.headers.get("Content-Type", ""), "Response should be PDF"
        assert len(pdf_response.content) > 5000, f"PDF should be substantial (got {len(pdf_response.content)} bytes)"
        
        # Check Content-Disposition header
        content_disp = pdf_response.headers.get("Content-Disposition", "")
        assert "DoP_" in content_disp or "filename" in content_disp, f"Should have proper filename in Content-Disposition: {content_disp}"

    def test_dop_pdf_invalid_dop_id(self, session):
        """Test that invalid dop_id returns 404"""
        pdf_url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionata/invalid_dop_xyz/pdf"
        pdf_response = session.get(pdf_url)
        
        assert pdf_response.status_code == 404, f"Expected 404 for invalid dop_id, got {pdf_response.status_code}"


class TestEtichettaCE1090:
    """Tests for GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf endpoint"""

    def test_etichetta_ce_pdf_generation(self, session):
        """Test CE Label PDF generation"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/etichetta-ce-1090/pdf"
        response = session.get(url)
        
        print(f"Etichetta CE Response Status: {response.status_code}")
        print(f"Etichetta CE Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"Etichetta CE Content-Length: {len(response.content)} bytes")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200] if response.text else 'empty'}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), "Response should be PDF"
        assert len(response.content) > 3000, f"PDF should be substantial (got {len(response.content)} bytes)"
        
        # Check Content-Disposition header for attachment
        content_disp = response.headers.get("Content-Disposition", "")
        assert "Etichetta_CE_1090" in content_disp or "filename" in content_disp, f"Should have proper filename: {content_disp}"

    def test_etichetta_ce_invalid_commessa(self, session):
        """Test that invalid commessa returns 404"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/invalid_commessa_xyz/etichetta-ce-1090/pdf"
        response = session.get(url)
        
        assert response.status_code == 404, f"Expected 404 for invalid commessa, got {response.status_code}"


class TestDopFrazionateList:
    """Tests for GET /api/fascicolo-tecnico/{cid}/dop-frazionate endpoint"""

    def test_list_dop_frazionate(self, session):
        """Test listing all DOPs for a commessa"""
        url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionate"
        response = session.get(url)
        
        print(f"List DOPs Response Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dop_frazionate" in data, "Response should contain 'dop_frazionate' list"
        assert "total" in data, "Response should contain 'total' count"
        assert isinstance(data["dop_frazionate"], list), "dop_frazionate should be a list"


class TestCommessaHubEndpoint:
    """Test that commessa hub returns normativa_tipo for frontend button visibility"""

    def test_commessa_hub_returns_normativa_tipo(self, session):
        """Test that commessa hub endpoint returns normativa_tipo field"""
        url = f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/hub"
        response = session.get(url)
        
        print(f"Commessa Hub Response Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa" in data, "Response should contain 'commessa' object"
        
        commessa = data["commessa"]
        assert "normativa_tipo" in commessa, "Commessa should have 'normativa_tipo' field"
        
        # For our test commessa, it should be EN_1090
        print(f"Commessa normativa_tipo: {commessa.get('normativa_tipo')}")
        assert commessa.get("normativa_tipo") == "EN_1090", f"Test commessa should be EN_1090, got {commessa.get('normativa_tipo')}"


class TestCleanup:
    """Cleanup test DOPs created during testing"""

    def test_cleanup_test_dops(self, session):
        """Delete test DOPs to avoid accumulation"""
        # List all DOPs
        list_url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionate"
        list_response = session.get(list_url)
        
        if list_response.status_code == 200:
            dops = list_response.json().get("dop_frazionate", [])
            # Delete DOPs that are marked as automatica (test-created)
            for dop in dops:
                if dop.get("automatica"):
                    dop_id = dop.get("dop_id")
                    delete_url = f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionata/{dop_id}"
                    delete_response = session.delete(delete_url)
                    print(f"Deleted test DOP {dop_id}: {delete_response.status_code}")
        
        # This test always passes - cleanup is best effort
        assert True

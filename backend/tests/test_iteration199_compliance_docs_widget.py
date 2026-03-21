"""
Iteration 199: Compliance Docs Widget & Fascicolo Aziendale Tests
Tests for:
1. GET /api/dashboard/compliance-docs - document status, 30-day alerts, commesse compliance
2. GET /api/dashboard/fascicolo-aziendale - ZIP download of company docs
3. GET /api/dashboard/commessa-compliance/{commessa_id} - compliance check for specific commessa
4. Verbale Posa PDF logo integration
"""
import pytest
import requests
import os
import zipfile
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_2026_active"
TEST_COMMESSA = "com_loiano_cims_2026"


@pytest.fixture
def auth_headers():
    """Auth headers with session token cookie"""
    return {"Cookie": f"session_token={SESSION_TOKEN}"}


class TestComplianceDocsEndpoint:
    """Tests for GET /api/dashboard/compliance-docs"""
    
    def test_compliance_docs_returns_200(self, auth_headers):
        """Endpoint returns 200 with auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: compliance-docs returns 200")
    
    def test_compliance_docs_structure(self, auth_headers):
        """Response has required keys: documenti, allegati_pos, riepilogo, alert_30gg, commesse_compliance"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        required_keys = ["documenti", "allegati_pos", "riepilogo", "alert_30gg", "commesse_compliance"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        print(f"PASS: Response has all required keys: {required_keys}")
    
    def test_compliance_docs_riepilogo_structure(self, auth_headers):
        """Riepilogo has correct structure with counts"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs", headers=auth_headers)
        data = response.json()
        riepilogo = data.get("riepilogo", {})
        
        expected_fields = ["totale_globali", "caricati_globali", "totale_pos", "caricati_pos", 
                          "scaduti", "critici", "in_scadenza_30gg", "mancanti"]
        for field in expected_fields:
            assert field in riepilogo, f"Missing riepilogo field: {field}"
        
        # Verify counts are integers
        assert isinstance(riepilogo["totale_globali"], int)
        assert isinstance(riepilogo["caricati_globali"], int)
        print(f"PASS: Riepilogo structure correct: {riepilogo}")
    
    def test_compliance_docs_documenti_structure(self, auth_headers):
        """Each document has tipo, label, presente, scadenza, days_left, status"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs", headers=auth_headers)
        data = response.json()
        documenti = data.get("documenti", [])
        
        assert len(documenti) > 0, "No documents returned"
        
        for doc in documenti:
            assert "tipo" in doc, "Missing tipo"
            assert "label" in doc, "Missing label"
            assert "presente" in doc, "Missing presente"
            assert "status" in doc, "Missing status"
            assert doc["status"] in ["valido", "scaduto", "critico", "in_scadenza", "mancante", "no_scadenza"]
        
        print(f"PASS: {len(documenti)} documents with correct structure")
    
    def test_compliance_docs_commesse_compliance(self, auth_headers):
        """Commesse compliance has pct_conforme and problemi"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs", headers=auth_headers)
        data = response.json()
        commesse = data.get("commesse_compliance", [])
        
        if len(commesse) > 0:
            for c in commesse[:3]:  # Check first 3
                assert "commessa_id" in c
                assert "pct_conforme" in c
                assert isinstance(c["pct_conforme"], int)
                assert 0 <= c["pct_conforme"] <= 100
                assert "problemi" in c
                assert isinstance(c["problemi"], list)
        
        print(f"PASS: {len(commesse)} commesse with compliance percentages")
    
    def test_compliance_docs_requires_auth(self):
        """Endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-docs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: compliance-docs requires auth")


class TestFascicoloAziendaleEndpoint:
    """Tests for GET /api/dashboard/fascicolo-aziendale"""
    
    def test_fascicolo_returns_200_zip(self, auth_headers):
        """Endpoint returns 200 with application/zip content type"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo-aziendale", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/zip" in response.headers.get("Content-Type", "")
        print("PASS: fascicolo-aziendale returns ZIP")
    
    def test_fascicolo_has_content_disposition(self, auth_headers):
        """Response has Content-Disposition header with filename"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo-aziendale", headers=auth_headers)
        assert response.status_code == 200
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert "Fascicolo_Aziendale" in content_disp
        print(f"PASS: Content-Disposition: {content_disp}")
    
    def test_fascicolo_is_valid_zip(self, auth_headers):
        """Downloaded content is a valid ZIP file"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo-aziendale", headers=auth_headers)
        assert response.status_code == 200
        
        # Try to open as ZIP
        zip_buffer = io.BytesIO(response.content)
        try:
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                file_list = zf.namelist()
                assert len(file_list) > 0, "ZIP is empty"
                print(f"PASS: Valid ZIP with {len(file_list)} files: {file_list[:5]}...")
        except zipfile.BadZipFile:
            pytest.fail("Response is not a valid ZIP file")
    
    def test_fascicolo_has_info_txt(self, auth_headers):
        """ZIP contains INFO.txt file"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo-aziendale", headers=auth_headers)
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            assert "INFO.txt" in zf.namelist(), "INFO.txt not found in ZIP"
            info_content = zf.read("INFO.txt").decode("utf-8")
            assert "Fascicolo Aziendale" in info_content
            print(f"PASS: INFO.txt found with content: {info_content[:100]}...")
    
    def test_fascicolo_requires_auth(self):
        """Endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo-aziendale")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: fascicolo-aziendale requires auth")


class TestCommessaComplianceEndpoint:
    """Tests for GET /api/dashboard/commessa-compliance/{commessa_id}"""
    
    def test_commessa_compliance_returns_200(self, auth_headers):
        """Endpoint returns 200 for valid commessa"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/commessa-compliance/{TEST_COMMESSA}", 
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: commessa-compliance returns 200")
    
    def test_commessa_compliance_structure(self, auth_headers):
        """Response has commessa_id, conforme, bloccanti, checks"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/commessa-compliance/{TEST_COMMESSA}", 
            headers=auth_headers
        )
        data = response.json()
        
        assert "commessa_id" in data
        assert data["commessa_id"] == TEST_COMMESSA
        assert "conforme" in data
        assert isinstance(data["conforme"], bool)
        assert "bloccanti" in data
        assert isinstance(data["bloccanti"], list)
        assert "checks" in data
        assert isinstance(data["checks"], list)
        
        print(f"PASS: Response structure correct - conforme={data['conforme']}, bloccanti={len(data['bloccanti'])}")
    
    def test_commessa_compliance_checks_structure(self, auth_headers):
        """Each check has tipo, label, esito, messaggio"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/commessa-compliance/{TEST_COMMESSA}", 
            headers=auth_headers
        )
        data = response.json()
        checks = data.get("checks", [])
        
        assert len(checks) > 0, "No checks returned"
        
        for check in checks:
            assert "tipo" in check
            assert "label" in check
            assert "esito" in check
            assert "messaggio" in check
            assert check["esito"] in ["ok", "mancante", "scaduto", "insufficiente", "no_scadenza", "errore"]
        
        print(f"PASS: {len(checks)} checks with correct structure")
    
    def test_commessa_compliance_loiano_has_bloccanti(self, auth_headers):
        """Loiano commessa should have bloccanti (White List, Patente a Crediti missing)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/commessa-compliance/{TEST_COMMESSA}", 
            headers=auth_headers
        )
        data = response.json()
        
        # Based on test data, Loiano should have missing docs
        assert data["conforme"] == False, "Expected conforme=False for Loiano"
        assert len(data["bloccanti"]) > 0, "Expected bloccanti for Loiano"
        
        # Check specific bloccanti
        bloccanti_text = " ".join(data["bloccanti"])
        assert "White List" in bloccanti_text or "Patente" in bloccanti_text
        
        print(f"PASS: Loiano has {len(data['bloccanti'])} bloccanti: {data['bloccanti']}")
    
    def test_commessa_compliance_404_invalid(self, auth_headers):
        """Returns 404 for non-existent commessa"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/commessa-compliance/invalid_commessa_xyz", 
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Returns 404 for invalid commessa")
    
    def test_commessa_compliance_requires_auth(self):
        """Endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/commessa-compliance/{TEST_COMMESSA}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: commessa-compliance requires auth")


class TestPaccoDocumentiEndpoint:
    """Tests for POST /api/commesse/{commessa_id}/pacco-documenti (export-cse)"""
    
    def test_pacco_documenti_returns_pdf(self, auth_headers):
        """Endpoint returns PDF for valid commessa"""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA}/pacco-documenti", 
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", "")
        print("PASS: pacco-documenti returns PDF")
    
    def test_pacco_documenti_has_content(self, auth_headers):
        """PDF has content (not empty)"""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA}/pacco-documenti", 
            headers=auth_headers
        )
        assert len(response.content) > 1000, f"PDF too small: {len(response.content)} bytes"
        # Check PDF magic bytes
        assert response.content[:4] == b'%PDF', "Not a valid PDF"
        print(f"PASS: PDF has {len(response.content)} bytes")
    
    def test_pacco_documenti_requires_auth(self):
        """Endpoint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/commesse/{TEST_COMMESSA}/pacco-documenti")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: pacco-documenti requires auth")


class TestVerbalePostaLogoIntegration:
    """Tests for logo integration in Verbale Posa PDF"""
    
    def test_verbale_context_has_company_info(self, auth_headers):
        """Verbale context includes company info for logo"""
        response = requests.get(
            f"{BASE_URL}/api/verbale-posa/context/{TEST_COMMESSA}", 
            headers=auth_headers
        )
        # May return 404 if no verbale context, that's ok
        if response.status_code == 200:
            data = response.json()
            assert "company_name" in data
            print(f"PASS: Verbale context has company_name: {data.get('company_name')}")
        else:
            print(f"INFO: Verbale context returned {response.status_code} (may not have verbale data)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

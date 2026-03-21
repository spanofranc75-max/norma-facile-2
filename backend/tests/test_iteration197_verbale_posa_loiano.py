"""
Iteration 197: Verbale di Posa in Opera - Loiano CIMS Commessa Tests
Tests for the specific Loiano commessa with 3 lotti EN 1090 (acciaio + bulloneria)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "active_test_session_2026"
LOIANO_COMMESSA = "com_loiano_cims_2026"
LOIANO_FPC_PROJECT = "prj_ee66232bbe9d"


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestVerbaleContextLoiano:
    """Test GET /api/verbale-posa/context/{commessa_id} for Loiano commessa"""
    
    def test_context_returns_loiano_data(self, auth_session):
        """Context endpoint returns Loiano commessa data with CIMS client"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["commessa_id"] == LOIANO_COMMESSA
        # Client name is "C.I.M.S SCRL" - check for partial match
        client_name = data.get("client_name", "")
        assert "C.I.M.S" in client_name or "CIMS" in client_name, f"Expected CIMS in client_name, got: {client_name}"
        print(f"Client name: {data.get('client_name')}")
    
    def test_context_has_4_materials(self, auth_session):
        """Context should return 4 materials from Loiano commessa"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        materiali = data.get("materiali", [])
        print(f"Materials count: {len(materiali)}")
        for i, m in enumerate(materiali):
            print(f"  Material {i+1}: {m.get('description', '')[:60]}")
        
        assert len(materiali) >= 4, f"Expected at least 4 materials, got {len(materiali)}"
    
    def test_context_has_3_lotti_en1090(self, auth_session):
        """Context should return 3 lotti EN 1090 with heat numbers"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        lotti = data.get("lotti", [])
        print(f"Lotti count: {len(lotti)}")
        
        # Expected heat numbers
        expected_heat_numbers = ["A24-88731", "B24-92145", "F24-00287"]
        found_heat_numbers = [l.get("heat_number") for l in lotti]
        
        for hn in expected_heat_numbers:
            assert hn in found_heat_numbers, f"Expected heat number {hn} not found in {found_heat_numbers}"
        
        for l in lotti:
            print(f"  Lotto: {l.get('heat_number')} - {l.get('material_type')} - Cert: {l.get('cert_31')}")
    
    def test_context_lotti_have_cert_31(self, auth_session):
        """Each lotto should have cert_31 reference"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        lotti = data.get("lotti", [])
        
        for l in lotti:
            cert = l.get("cert_31", "")
            assert cert, f"Lotto {l.get('heat_number')} missing cert_31"
            print(f"  {l.get('heat_number')}: cert_31 = {cert}")
    
    def test_context_lotti_distinguish_acciaio_bulloneria(self, auth_session):
        """Lotti should have material_type distinguishing acciaio vs bulloneria"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        lotti = data.get("lotti", [])
        
        material_types = [l.get("material_type") for l in lotti]
        print(f"Material types: {material_types}")
        
        # Should have both acciaio and bulloneria
        assert "acciaio" in material_types, "Expected at least one acciaio lotto"
        assert "bulloneria" in material_types, "Expected at least one bulloneria lotto"
    
    def test_context_has_exc2_execution_class(self, auth_session):
        """Context should return EXC2 execution class"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        exec_class = data.get("execution_class", "")
        print(f"Execution class: {exec_class}")
        assert exec_class == "EXC2", f"Expected EXC2, got {exec_class}"


class TestVerbaleSaveLoiano:
    """Test POST /api/verbale-posa/{commessa_id} for Loiano commessa"""
    
    def test_save_verbale_success(self, auth_session):
        """Save verbale for Loiano commessa"""
        form_data = {
            "data_posa": "2026-01-15",
            "luogo_posa": "Via Roma 1, Loiano (BO)",
            "responsabile": "Mario Rossi",
            "note_cantiere": "Test note cantiere Loiano",
            "check_regola_arte": "true",
            "check_conformita": "true",
            "check_materiali": "true",
            "check_sicurezza": "true",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/verbale-posa/{LOIANO_COMMESSA}",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "verbale_id" in data
        assert data.get("message") == "Verbale salvato"
        print(f"Verbale saved: {data.get('verbale_id')}")


class TestVerbaleGetLoiano:
    """Test GET /api/verbale-posa/{commessa_id} for Loiano commessa"""
    
    def test_get_saved_verbale(self, auth_session):
        """Get saved verbale returns exists=true"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/{LOIANO_COMMESSA}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("exists") == True, f"Expected exists=true, got {data}"
        print(f"Verbale exists: {data.get('exists')}")
        print(f"Data posa: {data.get('data_posa')}")
        print(f"Luogo: {data.get('luogo_posa')}")


class TestVerbalePDFLoiano:
    """Test GET /api/verbale-posa/{commessa_id}/pdf for Loiano commessa"""
    
    def test_pdf_generation_valid(self, auth_session):
        """PDF generation returns valid PDF starting with %PDF-"""
        response = auth_session.get(f"{BASE_URL}/api/verbale-posa/{LOIANO_COMMESSA}/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        content = response.content
        assert content[:5] == b'%PDF-', f"Expected PDF header, got: {content[:20]}"
        print(f"PDF size: {len(content)} bytes")
        
        # Check content-disposition header
        cd = response.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "Verbale_Posa" in cd
        print(f"Content-Disposition: {cd}")


class TestFPCProjectVerbaleLink:
    """Test FPC Project page shows Verbale button linking to commessa"""
    
    def test_fpc_project_has_commessa_id(self, auth_session):
        """FPC project prj_ee66232bbe9d should have commessa_id linked"""
        response = auth_session.get(f"{BASE_URL}/api/fpc/projects/{LOIANO_FPC_PROJECT}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        commessa_id = data.get("commessa_id")
        print(f"FPC Project commessa_id: {commessa_id}")
        
        assert commessa_id == LOIANO_COMMESSA, f"Expected {LOIANO_COMMESSA}, got {commessa_id}"


class TestSaldatoriRedirect:
    """Test /saldatori redirects to /operai (Risorse Umane)"""
    
    def test_saldatori_endpoint_exists(self, auth_session):
        """Check if saldatori endpoint exists or redirects"""
        # This is a frontend route test - we just verify the backend welders endpoint works
        response = auth_session.get(f"{BASE_URL}/api/fpc/welders")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Welders endpoint accessible")


class TestAuthRequired:
    """Test endpoints require authentication"""
    
    def test_context_requires_auth(self):
        """Context endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/context/{LOIANO_COMMESSA}")
        assert response.status_code == 401
    
    def test_get_requires_auth(self):
        """Get verbale requires auth"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/{LOIANO_COMMESSA}")
        assert response.status_code == 401
    
    def test_pdf_requires_auth(self):
        """PDF generation requires auth"""
        response = requests.get(f"{BASE_URL}/api/verbale-posa/{LOIANO_COMMESSA}/pdf")
        assert response.status_code == 401

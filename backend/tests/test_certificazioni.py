"""
Certificazioni CE (EN 1090 / EN 13241) Module Tests
Tests CRUD operations, PDF generation, and technical specs validation
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session data - will be populated by fixture
TEST_USER_ID = None
TEST_SESSION_TOKEN = None


@pytest.fixture(scope="module")
def setup_test_user():
    """Create test user and session in MongoDB for authenticated testing"""
    import subprocess
    import json
    
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f'test-cert-user-{timestamp}'
    session_token = f'test_cert_session_{timestamp}'
    
    # Create user and session via mongosh
    mongo_script = f'''
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'cert.test.{timestamp}@example.com',
        name: 'Certificazioni Test User',
        picture: 'https://via.placeholder.com/150',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print('CREATED');
    '''
    result = subprocess.run(['mongosh', '--eval', mongo_script], capture_output=True, text=True)
    
    if 'CREATED' not in result.stdout:
        pytest.skip(f"Failed to create test user: {result.stderr}")
    
    global TEST_USER_ID, TEST_SESSION_TOKEN
    TEST_USER_ID = user_id
    TEST_SESSION_TOKEN = session_token
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup after all tests
    cleanup_script = f'''
    use('test_database');
    db.users.deleteOne({{ user_id: '{user_id}' }});
    db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
    db.certificazioni.deleteMany({{ user_id: '{user_id}' }});
    print('CLEANED');
    '''
    subprocess.run(['mongosh', '--eval', cleanup_script], capture_output=True, text=True)


@pytest.fixture
def api_client(setup_test_user):
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {setup_test_user['session_token']}"
    })
    return session


class TestCertificazioniCRUD:
    """Test CRUD operations for Certificazioni CE"""
    
    def test_list_certificazioni_empty(self, api_client):
        """GET /api/certificazioni/ - should return empty list initially"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "certificazioni" in data
        assert "total" in data
        assert isinstance(data["certificazioni"], list)
    
    def test_create_certificazione_en1090(self, api_client):
        """POST /api/certificazioni/ - Create EN 1090-1 certification"""
        payload = {
            "project_name": "TEST_Scala Esterna",
            "standard": "EN 1090-1",
            "product_type": "Scala in acciaio S235",
            "product_description": "Scala esterna per accesso magazzino",
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "Classe C3 (media)",
                "reaction_to_fire": "Classe A1 (non combustibile)",
                "dangerous_substances": "Nessuna"
            },
            "notes": "Test certification"
        }
        
        response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "cert_id" in data
        assert data["project_name"] == "TEST_Scala Esterna"
        assert data["standard"] == "EN 1090-1"
        assert data["product_type"] == "Scala in acciaio S235"
        assert data["status"] == "bozza"
        assert "declaration_number" in data
        assert data["declaration_number"].startswith("DOP-")
        
        # Verify technical specs
        specs = data["technical_specs"]
        assert specs["execution_class"] == "EXC2"
        assert specs["durability"] == "Classe C3 (media)"
        
        return data["cert_id"]
    
    def test_create_certificazione_en13241(self, api_client):
        """POST /api/certificazioni/ - Create EN 13241 gate certification"""
        payload = {
            "project_name": "TEST_Cancello Scorrevole",
            "standard": "EN 13241",
            "product_type": "Cancello scorrevole motorizzato",
            "product_description": "Cancello scorrevole per ingresso industriale",
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "Classe C3 (media)",
                "dangerous_substances": "Nessuna",
                "air_permeability": "Classe 2",
                "water_tightness": "Classe 3A",
                "wind_resistance": "Classe 3",
                "mechanical_resistance": "Conforme",
                "safe_opening": "Conforme"
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["standard"] == "EN 13241"
        assert data["declaration_number"].startswith("DOP-G-")  # Gate-specific prefix
        
        # Verify EN 13241 specific fields
        specs = data["technical_specs"]
        assert specs["air_permeability"] == "Classe 2"
        assert specs["mechanical_resistance"] == "Conforme"
        assert specs["safe_opening"] == "Conforme"
        
        return data["cert_id"]
    
    def test_get_single_certificazione(self, api_client):
        """GET /api/certificazioni/{cert_id} - Get single certification"""
        # First create one
        payload = {
            "project_name": "TEST_GetSingle",
            "standard": "EN 1090-1",
            "product_type": "Test Product",
            "technical_specs": {"execution_class": "EXC3"}
        }
        create_resp = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        cert_id = create_resp.json()["cert_id"]
        
        # Now get it
        response = api_client.get(f"{BASE_URL}/api/certificazioni/{cert_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["cert_id"] == cert_id
        assert data["project_name"] == "TEST_GetSingle"
        assert data["technical_specs"]["execution_class"] == "EXC3"
    
    def test_get_nonexistent_certificazione(self, api_client):
        """GET /api/certificazioni/{cert_id} - Should return 404 for non-existent"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/nonexistent_id_12345")
        assert response.status_code == 404
    
    def test_update_certificazione(self, api_client):
        """PUT /api/certificazioni/{cert_id} - Update certification"""
        # Create first
        payload = {
            "project_name": "TEST_ToUpdate",
            "standard": "EN 1090-1",
            "product_type": "Initial Product",
            "technical_specs": {"execution_class": "EXC2"}
        }
        create_resp = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        cert_id = create_resp.json()["cert_id"]
        
        # Update
        update_payload = {
            "project_name": "TEST_Updated Name",
            "product_type": "Updated Product",
            "status": "emessa",
            "technical_specs": {"execution_class": "EXC3", "durability": "Classe C4 (alta)"}
        }
        
        response = api_client.put(f"{BASE_URL}/api/certificazioni/{cert_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["project_name"] == "TEST_Updated Name"
        assert data["product_type"] == "Updated Product"
        assert data["status"] == "emessa"
        assert data["technical_specs"]["execution_class"] == "EXC3"
        
        # Verify with GET
        get_resp = api_client.get(f"{BASE_URL}/api/certificazioni/{cert_id}")
        assert get_resp.status_code == 200
        verify = get_resp.json()
        assert verify["project_name"] == "TEST_Updated Name"
        assert verify["status"] == "emessa"
    
    def test_delete_certificazione(self, api_client):
        """DELETE /api/certificazioni/{cert_id} - Delete certification"""
        # Create first
        payload = {
            "project_name": "TEST_ToDelete",
            "standard": "EN 1090-1",
            "product_type": "Delete Test"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        cert_id = create_resp.json()["cert_id"]
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/certificazioni/{cert_id}")
        assert response.status_code == 200
        
        # Verify deleted
        get_resp = api_client.get(f"{BASE_URL}/api/certificazioni/{cert_id}")
        assert get_resp.status_code == 404
    
    def test_list_with_status_filter(self, api_client):
        """GET /api/certificazioni/?status=bozza - Filter by status"""
        # Create a draft certification
        payload = {
            "project_name": "TEST_FilterTest",
            "standard": "EN 1090-1",
            "product_type": "Filter Test"
        }
        api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        
        # Query with filter
        response = api_client.get(f"{BASE_URL}/api/certificazioni/?status=bozza")
        assert response.status_code == 200
        
        data = response.json()
        # All returned should be bozza
        for cert in data["certificazioni"]:
            assert cert["status"] == "bozza"


class TestCertificazioniPDF:
    """Test PDF generation for Certificazioni CE"""
    
    def test_generate_fascicolo_pdf_en1090(self, api_client):
        """GET /api/certificazioni/{cert_id}/fascicolo-pdf - Generate DOP + CE Label PDF for EN 1090"""
        # Create a certification first
        payload = {
            "project_name": "TEST_PDF_EN1090",
            "standard": "EN 1090-1",
            "product_type": "Pensilina in acciaio",
            "product_description": "Pensilina copertura parcheggio",
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "Classe C3 (media)",
                "reaction_to_fire": "Classe A1 (non combustibile)",
                "dangerous_substances": "Nessuna"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        assert create_resp.status_code == 201
        cert_id = create_resp.json()["cert_id"]
        
        # Generate PDF
        response = api_client.get(f"{BASE_URL}/api/certificazioni/{cert_id}/fascicolo-pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify content type is PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # Verify content-disposition has filename
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp
        assert '.pdf' in content_disp
        
        # Verify PDF content starts with PDF signature
        assert response.content[:4] == b'%PDF', "Response should be a valid PDF file"
    
    def test_generate_fascicolo_pdf_en13241(self, api_client):
        """GET /api/certificazioni/{cert_id}/fascicolo-pdf - Generate PDF for EN 13241 gate"""
        # Create a gate certification
        payload = {
            "project_name": "TEST_PDF_EN13241",
            "standard": "EN 13241",
            "product_type": "Cancello battente",
            "technical_specs": {
                "mechanical_resistance": "Conforme",
                "safe_opening": "Conforme",
                "air_permeability": "Classe 1",
                "water_tightness": "Classe 2A",
                "wind_resistance": "Classe 2"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        cert_id = create_resp.json()["cert_id"]
        
        # Generate PDF
        response = api_client.get(f"{BASE_URL}/api/certificazioni/{cert_id}/fascicolo-pdf")
        assert response.status_code == 200
        assert 'application/pdf' in response.headers.get('Content-Type', '')
        assert response.content[:4] == b'%PDF'
    
    def test_pdf_nonexistent_certification(self, api_client):
        """GET /api/certificazioni/{cert_id}/fascicolo-pdf - 404 for non-existent"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/nonexistent_id/fascicolo-pdf")
        assert response.status_code == 404


class TestTechnicalSpecsValidation:
    """Test technical specs validation and defaults"""
    
    def test_default_technical_specs(self, api_client):
        """Verify default technical specs are applied"""
        payload = {
            "project_name": "TEST_DefaultSpecs",
            "standard": "EN 1090-1",
            "product_type": "Test"
        }
        
        response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        assert response.status_code == 201
        
        specs = response.json()["technical_specs"]
        # Verify defaults
        assert specs["execution_class"] == "EXC2"
        assert "C3" in specs["durability"]
        assert "A1" in specs["reaction_to_fire"]
        assert specs["dangerous_substances"] == "Nessuna"
    
    def test_execution_class_values(self, api_client):
        """Test all valid execution class values"""
        for exc in ["EXC1", "EXC2", "EXC3", "EXC4"]:
            payload = {
                "project_name": f"TEST_EXC_{exc}",
                "standard": "EN 1090-1",
                "product_type": "Test",
                "technical_specs": {"execution_class": exc}
            }
            
            response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
            assert response.status_code == 201, f"Failed for {exc}: {response.text}"
            assert response.json()["technical_specs"]["execution_class"] == exc


class TestDeclarationNumber:
    """Test declaration number generation"""
    
    def test_dop_number_format_en1090(self, api_client):
        """EN 1090-1 should have DOP- prefix"""
        payload = {
            "project_name": "TEST_DOPFormat1090",
            "standard": "EN 1090-1",
            "product_type": "Test"
        }
        
        response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        decl = response.json()["declaration_number"]
        
        assert decl.startswith("DOP-")
        # Format: DOP-YYYY-XXXXXX
        parts = decl.split("-")
        assert len(parts) == 3
        assert parts[1] == str(datetime.now().year)
    
    def test_dop_number_format_en13241(self, api_client):
        """EN 13241 should have DOP-G- prefix (gates)"""
        payload = {
            "project_name": "TEST_DOPFormat13241",
            "standard": "EN 13241",
            "product_type": "Cancello"
        }
        
        response = api_client.post(f"{BASE_URL}/api/certificazioni/", json=payload)
        decl = response.json()["declaration_number"]
        
        assert decl.startswith("DOP-G-"), f"Expected DOP-G- prefix, got {decl}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Tests for Sicurezza Cantieri (POS Generator) Module
Endpoints tested:
- GET /api/sicurezza/rischi - Public reference data (13 risks, 14 machines, 13 DPI)
- POST /api/sicurezza/ - Create POS
- GET /api/sicurezza/ - List POS documents
- GET /api/sicurezza/{pos_id} - Get single POS
- PUT /api/sicurezza/{pos_id} - Update POS
- DELETE /api/sicurezza/{pos_id} - Delete POS
- POST /api/sicurezza/{pos_id}/genera-rischi - AI risk assessment generation
- GET /api/sicurezza/{pos_id}/pdf - POS PDF download
"""
import pytest
import requests
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_PROJECT_NAME = f"TEST_POS_{uuid.uuid4().hex[:8]}"
TEST_CANTIERE = {
    "address": "Via Test 123",
    "city": "Milano",
    "duration_days": 45,
    "start_date": "2026-02-01",
    "committente": "Test Committente Srl",
    "responsabile_lavori": "Mario Rossi",
    "coordinatore_sicurezza": "Giuseppe Verdi"
}
TEST_RISKS = ["saldatura", "lavoro_quota", "taglio_flessibile"]
TEST_MACHINES = ["saldatrice_mig", "smerigliatrice", "ponteggio"]
TEST_DPI = ["casco", "occhiali", "guanti_pelle", "scarpe_antinfortunistiche", "imbracatura"]


@pytest.fixture(scope="module")
def api_session():
    """Shared requests session for all tests"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_session(api_session):
    """Create a test user and session for authenticated endpoints"""
    import subprocess
    
    timestamp = int(time.time())
    user_id = f"test-sicurezza-user-{timestamp}"
    session_token = f"test_sicurezza_session_{timestamp}"
    
    # Create test user and session in MongoDB
    mongo_script = f'''
    use('test_database');
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "test.sicurezza.{timestamp}@example.com",
        name: "Test Sicurezza User",
        picture: "https://via.placeholder.com/150",
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 24*60*60*1000),
        created_at: new Date()
    }});
    '''
    subprocess.run(["mongosh", "--quiet", "--eval", mongo_script], capture_output=True)
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_script = f'''
    use('test_database');
    db.users.deleteOne({{ user_id: "{user_id}" }});
    db.user_sessions.deleteOne({{ session_token: "{session_token}" }});
    db.pos_documents.deleteMany({{ user_id: "{user_id}" }});
    '''
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)


@pytest.fixture(scope="module")
def auth_session(api_session, test_user_session):
    """Session with authentication header"""
    api_session.headers.update({
        "Authorization": f"Bearer {test_user_session['session_token']}"
    })
    return api_session


class TestRischiEndpoint:
    """Test GET /api/sicurezza/rischi - Public reference data"""
    
    def test_get_rischi_returns_200(self, api_session):
        """Rischi endpoint is public and returns 200"""
        response = api_session.get(f"{BASE_URL}/api/sicurezza/rischi")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/sicurezza/rischi returns 200")
    
    def test_rischi_returns_13_risks(self, api_session):
        """Verify 13 predefined risks for metalworkers"""
        response = api_session.get(f"{BASE_URL}/api/sicurezza/rischi")
        data = response.json()
        
        assert "rischi" in data, "Response should contain 'rischi' key"
        assert len(data["rischi"]) == 13, f"Expected 13 risks, got {len(data['rischi'])}"
        
        # Verify structure
        risk = data["rischi"][0]
        assert "id" in risk, "Risk should have 'id'"
        assert "label" in risk, "Risk should have 'label'"
        assert "category" in risk, "Risk should have 'category'"
        print(f"PASS: Returns 13 risks with correct structure")
    
    def test_rischi_returns_14_machines(self, api_session):
        """Verify 14 machines/tools"""
        response = api_session.get(f"{BASE_URL}/api/sicurezza/rischi")
        data = response.json()
        
        assert "macchine" in data, "Response should contain 'macchine' key"
        assert len(data["macchine"]) == 14, f"Expected 14 machines, got {len(data['macchine'])}"
        print(f"PASS: Returns 14 machines")
    
    def test_rischi_returns_13_dpi(self, api_session):
        """Verify 13 DPI items"""
        response = api_session.get(f"{BASE_URL}/api/sicurezza/rischi")
        data = response.json()
        
        assert "dpi" in data, "Response should contain 'dpi' key"
        assert len(data["dpi"]) == 13, f"Expected 13 DPI, got {len(data['dpi'])}"
        print(f"PASS: Returns 13 DPI items")
    
    def test_rischi_categories(self, api_session):
        """Verify risk categories include expected values"""
        response = api_session.get(f"{BASE_URL}/api/sicurezza/rischi")
        data = response.json()
        
        categories = set(r["category"] for r in data["rischi"])
        expected_categories = {"Lavorazioni a caldo", "Lavorazioni meccaniche", "Rischi specifici", "Rischi chimici"}
        
        assert categories == expected_categories, f"Expected categories {expected_categories}, got {categories}"
        print(f"PASS: Risk categories are correct")


class TestPosCRUD:
    """Test POS CRUD operations - requires authentication"""
    
    created_pos_id = None
    
    def test_create_pos(self, auth_session):
        """Create a new POS"""
        payload = {
            "project_name": TEST_PROJECT_NAME,
            "cantiere": TEST_CANTIERE,
            "selected_risks": TEST_RISKS,
            "selected_machines": TEST_MACHINES,
            "selected_dpi": TEST_DPI,
            "notes": "Test POS document"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/sicurezza/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pos_id" in data, "Response should contain pos_id"
        assert data["project_name"] == TEST_PROJECT_NAME
        assert data["status"] == "bozza"
        assert len(data["selected_risks"]) == 3
        assert len(data["selected_machines"]) == 3
        assert len(data["selected_dpi"]) == 5
        
        # Store for later tests
        TestPosCRUD.created_pos_id = data["pos_id"]
        print(f"PASS: POS created with ID {data['pos_id']}")
    
    def test_get_pos_list(self, auth_session):
        """List all POS documents for user"""
        response = auth_session.get(f"{BASE_URL}/api/sicurezza/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "pos_list" in data, "Response should contain pos_list"
        assert "total" in data, "Response should contain total"
        assert data["total"] >= 1, "Should have at least 1 POS"
        print(f"PASS: POS list returned {data['total']} documents")
    
    def test_get_single_pos(self, auth_session):
        """Get a single POS by ID"""
        assert TestPosCRUD.created_pos_id, "Need created POS ID"
        
        response = auth_session.get(f"{BASE_URL}/api/sicurezza/{TestPosCRUD.created_pos_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["pos_id"] == TestPosCRUD.created_pos_id
        assert data["project_name"] == TEST_PROJECT_NAME
        assert data["cantiere"]["address"] == "Via Test 123"
        assert data["cantiere"]["city"] == "Milano"
        print(f"PASS: Single POS retrieved successfully")
    
    def test_update_pos(self, auth_session):
        """Update POS fields"""
        assert TestPosCRUD.created_pos_id, "Need created POS ID"
        
        update_payload = {
            "project_name": f"{TEST_PROJECT_NAME}_UPDATED",
            "status": "completo",
            "cantiere": {
                **TEST_CANTIERE,
                "city": "Roma"
            }
        }
        
        response = auth_session.put(
            f"{BASE_URL}/api/sicurezza/{TestPosCRUD.created_pos_id}",
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["project_name"] == f"{TEST_PROJECT_NAME}_UPDATED"
        assert data["status"] == "completo"
        assert data["cantiere"]["city"] == "Roma"
        print(f"PASS: POS updated successfully")
    
    def test_get_pos_returns_404_for_invalid_id(self, auth_session):
        """Get POS with invalid ID returns 404"""
        response = auth_session.get(f"{BASE_URL}/api/sicurezza/invalid_pos_id_12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Invalid POS ID returns 404")


class TestAIRiskAssessment:
    """Test AI risk assessment generation - POST /api/sicurezza/{pos_id}/genera-rischi"""
    
    pos_id_for_ai = None
    
    def test_create_pos_for_ai(self, auth_session):
        """Create a POS for AI testing"""
        payload = {
            "project_name": f"TEST_AI_POS_{uuid.uuid4().hex[:8]}",
            "cantiere": TEST_CANTIERE,
            "selected_risks": ["saldatura", "lavoro_quota", "taglio_flessibile"],
            "selected_machines": ["saldatrice_mig", "smerigliatrice"],
            "selected_dpi": ["casco", "occhiali", "guanti_pelle"]
        }
        
        response = auth_session.post(f"{BASE_URL}/api/sicurezza/", json=payload)
        assert response.status_code == 201
        
        TestAIRiskAssessment.pos_id_for_ai = response.json()["pos_id"]
        print(f"PASS: Created POS for AI testing: {TestAIRiskAssessment.pos_id_for_ai}")
    
    def test_generate_risk_assessment(self, auth_session):
        """Generate AI risk assessment with GPT-4o"""
        assert TestAIRiskAssessment.pos_id_for_ai, "Need POS ID for AI test"
        
        response = auth_session.post(
            f"{BASE_URL}/api/sicurezza/{TestAIRiskAssessment.pos_id_for_ai}/genera-rischi"
        )
        
        # AI generation might take time, allow up to 60 seconds
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ai_risk_assessment" in data, "Response should contain ai_risk_assessment"
        assert data["ai_risk_assessment"], "AI risk assessment should not be empty"
        assert len(data["ai_risk_assessment"]) > 100, "AI assessment should be substantial"
        assert data["status"] == "generated"
        print(f"PASS: AI risk assessment generated ({len(data['ai_risk_assessment'])} chars)")
    
    def test_ai_assessment_saved_to_pos(self, auth_session):
        """Verify AI assessment is saved to POS document"""
        assert TestAIRiskAssessment.pos_id_for_ai, "Need POS ID"
        
        response = auth_session.get(f"{BASE_URL}/api/sicurezza/{TestAIRiskAssessment.pos_id_for_ai}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ai_risk_assessment"], "AI assessment should be saved"
        print(f"PASS: AI assessment persisted to database")
    
    def test_generate_requires_risks(self, auth_session):
        """AI generation fails if no risks selected"""
        # Create POS with no risks
        payload = {
            "project_name": f"TEST_NO_RISKS_{uuid.uuid4().hex[:8]}",
            "cantiere": TEST_CANTIERE,
            "selected_risks": [],
            "selected_machines": [],
            "selected_dpi": []
        }
        
        create_response = auth_session.post(f"{BASE_URL}/api/sicurezza/", json=payload)
        assert create_response.status_code == 201
        pos_id = create_response.json()["pos_id"]
        
        # Try to generate AI assessment
        response = auth_session.post(f"{BASE_URL}/api/sicurezza/{pos_id}/genera-rischi")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: AI generation fails with no risks selected")


class TestPosPdfGeneration:
    """Test POS PDF generation - GET /api/sicurezza/{pos_id}/pdf"""
    
    def test_download_pdf(self, auth_session):
        """Download POS PDF"""
        assert TestAIRiskAssessment.pos_id_for_ai, "Need POS ID"
        
        response = auth_session.get(
            f"{BASE_URL}/api/sicurezza/{TestAIRiskAssessment.pos_id_for_ai}/pdf"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, "Should be downloadable attachment"
        assert ".pdf" in content_disposition.lower(), "Should have .pdf extension"
        
        # Verify PDF has content
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"PDF should be substantial, got {pdf_size} bytes"
        print(f"PASS: PDF downloaded successfully ({pdf_size} bytes)")


class TestPosDelete:
    """Test POS deletion"""
    
    def test_delete_pos(self, auth_session):
        """Delete a POS"""
        assert TestPosCRUD.created_pos_id, "Need created POS ID"
        
        response = auth_session.delete(f"{BASE_URL}/api/sicurezza/{TestPosCRUD.created_pos_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: POS deleted")
    
    def test_deleted_pos_returns_404(self, auth_session):
        """Deleted POS returns 404"""
        assert TestPosCRUD.created_pos_id, "Need created POS ID"
        
        response = auth_session.get(f"{BASE_URL}/api/sicurezza/{TestPosCRUD.created_pos_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Deleted POS returns 404")


class TestAuthRequired:
    """Test that authenticated endpoints require auth"""
    
    def test_list_pos_requires_auth(self, api_session):
        """List POS requires authentication"""
        # Remove auth header
        headers_backup = api_session.headers.copy()
        api_session.headers.pop("Authorization", None)
        
        response = api_session.get(f"{BASE_URL}/api/sicurezza/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Restore headers
        api_session.headers.update(headers_backup)
        print(f"PASS: List POS requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

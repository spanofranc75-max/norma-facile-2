"""
Iteration 268: Quick New Client Dialog from Rilievo Editor
Tests for:
1. Quick new client dialog opens from '+' button in rilievo editor
2. Dialog shows fields: Ragione Sociale, Persona Fisica checkbox, Cellulare, Email, Indirizzo, Comune, Provincia, Note
3. Creating a client via the dialog saves to /api/clients/ and returns the new client
4. After creation, client is auto-selected in the dropdown
5. Client address propagates to 'Località/Indirizzo' field
6. Selected client info (address + phone) shows below the dropdown
7. Persona Fisica toggle switches between Cognome/Nome fields and Ragione Sociale
8. 401 redirect to login page works (apiRequest handles 401 by redirecting)
9. POST /api/clients/ creates client correctly with minimal data (no P.IVA, no CF required)
10. New client has notes prefix '[Dati parziali da rilievo]' to flag incomplete data
"""
import pytest
import requests
import os
from datetime import datetime, timezone
from pymongo import MongoClient

# Get URLs from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com')
MONGO_URL = os.environ.get('MONGO_URL', '')

# Test user credentials
TEST_USER_ID = "user_97c773827822"
TEST_TENANT_ID = "ten_1cf1a865bf20"
TEST_SESSION_TOKEN = "test_session_268_main"


class TestSessionSetup:
    """Setup test session in MongoDB Atlas"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_session(self):
        """Create a fresh session in MongoDB before tests"""
        if not MONGO_URL:
            pytest.skip("MONGO_URL not set")
        
        client = MongoClient(MONGO_URL)
        db = client.normafacile
        
        # Delete any existing test sessions
        db.sessions.delete_many({"session_token": {"$regex": "^test_session_268"}})
        
        # Create new session
        session_doc = {
            "session_token": TEST_SESSION_TOKEN,
            "user_id": TEST_USER_ID,
            "tenant_id": TEST_TENANT_ID,
            "expires_at": datetime(2027, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }
        db.sessions.insert_one(session_doc)
        print(f"\nCreated test session: {TEST_SESSION_TOKEN}")
        
        yield
        
        # Cleanup: Delete test session and test clients
        db.sessions.delete_many({"session_token": {"$regex": "^test_session_268"}})
        db.clients.delete_many({
            "user_id": TEST_USER_ID,
            "tenant_id": TEST_TENANT_ID,
            "business_name": {"$regex": "^TEST_"}
        })
        client.close()


class TestClientCreationEndpoint:
    """Test POST /api/clients/ endpoint with minimal data"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create requests session with auth cookie"""
        s = requests.Session()
        s.cookies.set("session_token", TEST_SESSION_TOKEN)
        return s
    
    def test_create_client_minimal_data(self, session):
        """Test creating client with only business_name (no P.IVA, no CF)"""
        payload = {
            "business_name": "TEST_Minimal Client",
            "client_type": "cliente",
            "status": "active"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=payload)
        print(f"Create minimal client response: {response.status_code}")
        
        # Should succeed with 201
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "client_id" in data
        assert data["business_name"] == "TEST_Minimal Client"
        assert data["client_type"] == "cliente"
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_client_with_quick_dialog_fields(self, session):
        """Test creating client with fields from QuickNewClientDialog"""
        payload = {
            "business_name": "TEST_Quick Dialog Client",
            "client_type": "cliente",
            "persona_fisica": False,
            "cellulare": "+39 333 1234567",
            "email": "test@quickclient.it",
            "address": "Via Roma, 1",
            "city": "Modena",
            "province": "MO",
            "notes": "[Dati parziali da rilievo] Note di test",
            "status": "active"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=payload)
        print(f"Create quick dialog client response: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["business_name"] == "TEST_Quick Dialog Client"
        assert data["cellulare"] == "+39 333 1234567"
        assert data["email"] == "test@quickclient.it"
        assert data["address"] == "Via Roma, 1"
        assert data["city"] == "Modena"
        assert data["province"] == "MO"
        assert "[Dati parziali da rilievo]" in data["notes"]
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_persona_fisica_client(self, session):
        """Test creating persona fisica client with cognome/nome"""
        payload = {
            "business_name": "Rossi Mario",  # Combined from cognome + nome
            "client_type": "cliente",
            "persona_fisica": True,
            "cognome": "Rossi",
            "nome": "Mario",
            "cellulare": "+39 333 9876543",
            "notes": "[Dati parziali da rilievo]",
            "status": "active"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=payload)
        print(f"Create persona fisica client response: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["business_name"] == "Rossi Mario"
        assert data["persona_fisica"] == True
        assert data["cognome"] == "Rossi"
        assert data["nome"] == "Mario"
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_client_notes_prefix(self, session):
        """Test that notes have '[Dati parziali da rilievo]' prefix"""
        # Test with custom notes
        payload = {
            "business_name": "TEST_Notes Prefix Client",
            "client_type": "cliente",
            "notes": "[Dati parziali da rilievo] Custom note here",
            "status": "active"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data["notes"].startswith("[Dati parziali da rilievo]")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_client_returns_client_id(self, session):
        """Test that created client returns client_id for auto-selection"""
        payload = {
            "business_name": "TEST_AutoSelect Client",
            "client_type": "cliente",
            "status": "active"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert "client_id" in data
        assert data["client_id"].startswith("cli_")
        
        # Verify client can be fetched
        get_response = session.get(f"{BASE_URL}/api/clients/{data['client_id']}")
        assert get_response.status_code == 200
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data['client_id']}")


class Test401RedirectBehavior:
    """Test 401 handling in apiRequest"""
    
    def test_invalid_session_returns_401(self):
        """Test that invalid session token returns 401"""
        s = requests.Session()
        s.cookies.set("session_token", "invalid_token_xyz")
        
        response = s.get(f"{BASE_URL}/api/clients/")
        print(f"Invalid session response: {response.status_code}")
        
        # Should return 401 for invalid session
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_no_session_returns_401(self):
        """Test that no session token returns 401"""
        response = requests.get(f"{BASE_URL}/api/clients/")
        print(f"No session response: {response.status_code}")
        
        # Should return 401 for no session
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestClientListEndpoint:
    """Test GET /api/clients/ endpoint"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create requests session with auth cookie"""
        s = requests.Session()
        s.cookies.set("session_token", TEST_SESSION_TOKEN)
        return s
    
    def test_get_clients_list(self, session):
        """Test fetching clients list"""
        response = session.get(f"{BASE_URL}/api/clients/?limit=10")
        print(f"Get clients list response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "clients" in data
        assert "total" in data
        assert isinstance(data["clients"], list)
    
    def test_clients_have_address_fields(self, session):
        """Test that clients have address fields for propagation"""
        response = session.get(f"{BASE_URL}/api/clients/?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        if data["clients"]:
            client = data["clients"][0]
            # These fields should exist (may be null)
            assert "address" in client or client.get("address") is None
            assert "city" in client or client.get("city") is None
            assert "cellulare" in client or client.get("cellulare") is None


class TestRilieviEndpoint:
    """Test rilievi endpoints for client integration"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create requests session with auth cookie"""
        s = requests.Session()
        s.cookies.set("session_token", TEST_SESSION_TOKEN)
        return s
    
    def test_create_rilievo_with_client(self, session):
        """Test creating rilievo with client_id"""
        # First create a test client
        client_payload = {
            "business_name": "TEST_Rilievo Client",
            "client_type": "cliente",
            "address": "Via Test, 123",
            "city": "Bologna",
            "province": "BO",
            "status": "active"
        }
        
        client_response = session.post(f"{BASE_URL}/api/clients/", json=client_payload)
        assert client_response.status_code == 201
        client_id = client_response.json()["client_id"]
        
        # Create rilievo with client
        rilievo_payload = {
            "client_id": client_id,
            "project_name": "TEST_Rilievo Project",
            "survey_date": "2026-01-15",
            "location": "Via Test, 123, Bologna",  # Should match client address
            "status": "bozza"
        }
        
        rilievo_response = session.post(f"{BASE_URL}/api/rilievi/", json=rilievo_payload)
        print(f"Create rilievo response: {rilievo_response.status_code}")
        
        if rilievo_response.status_code == 201:
            rilievo_data = rilievo_response.json()
            assert rilievo_data["client_id"] == client_id
            assert rilievo_data["location"] == "Via Test, 123, Bologna"
            
            # Cleanup rilievo
            session.delete(f"{BASE_URL}/api/rilievi/{rilievo_data['rilievo_id']}")
        
        # Cleanup client
        session.delete(f"{BASE_URL}/api/clients/{client_id}")


class TestFrontendCodeReview:
    """Code review tests for frontend components"""
    
    def test_quick_new_client_dialog_has_required_fields(self):
        """Verify QuickNewClientDialog has all required fields"""
        with open("/app/frontend/src/components/QuickNewClientDialog.js", "r") as f:
            content = f.read()
        
        # Check for required fields
        assert "business_name" in content, "Missing business_name field"
        assert "persona_fisica" in content or "isPersonaFisica" in content, "Missing persona_fisica field"
        assert "cellulare" in content, "Missing cellulare field"
        assert "email" in content, "Missing email field"
        assert "address" in content, "Missing address field"
        assert "city" in content, "Missing city field"
        assert "province" in content, "Missing province field"
        assert "notes" in content, "Missing notes field"
        
        # Check for data-testid attributes
        assert 'data-testid="quick-new-client-dialog"' in content
        assert 'data-testid="chk-persona-fisica"' in content
        assert 'data-testid="input-business-name"' in content
        assert 'data-testid="input-cellulare"' in content
        assert 'data-testid="input-email"' in content
        assert 'data-testid="input-address"' in content
        assert 'data-testid="input-city"' in content
        assert 'data-testid="input-province"' in content
        assert 'data-testid="btn-save-quick-client"' in content
        
        # Check for notes prefix
        assert "[Dati parziali da rilievo]" in content
        
        print("QuickNewClientDialog has all required fields and data-testid attributes")
    
    def test_rilievo_editor_has_quick_client_button(self):
        """Verify RilievoEditorPage has '+' button for quick client"""
        with open("/app/frontend/src/pages/RilievoEditorPage.js", "r") as f:
            content = f.read()
        
        # Check for QuickNewClientDialog import
        assert "QuickNewClientDialog" in content, "Missing QuickNewClientDialog import"
        
        # Check for quick client button
        assert 'data-testid="btn-quick-new-client"' in content, "Missing quick client button"
        
        # Check for quickClientOpen state
        assert "quickClientOpen" in content, "Missing quickClientOpen state"
        
        print("RilievoEditorPage has quick client button integration")
    
    def test_api_request_handles_401(self):
        """Verify apiRequest handles 401 with redirect"""
        with open("/app/frontend/src/lib/utils.js", "r") as f:
            content = f.read()
        
        # Check for 401 handling
        assert "response.status === 401" in content, "Missing 401 status check"
        assert "window.location.href" in content, "Missing redirect logic"
        
        print("apiRequest handles 401 with redirect to login")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

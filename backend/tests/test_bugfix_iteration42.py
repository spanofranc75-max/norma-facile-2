"""
Bug Fix Iteration 42 - Testing 3 Critical Bugs Fixed:
1. Client creation not saving (POST /api/clients/)
2. Sales conditions not in documents (PUT /api/company/settings with condizioni_vendita)
3. Company logo missing (logo_url in company settings)

Plus:
- Sidebar logo display verification via API
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_SESSION_TOKEN = "test_session_3fd8f142365c4bca985f687e996cd67c"

@pytest.fixture
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
    })
    return session


class TestAuthVerification:
    """Verify test session token works"""
    
    def test_auth_me_returns_user(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data["user_id"] == "test_user_96e42091"
        print(f"✓ Auth works - User: {data['user_id']}")


class TestBug1ClientCreation:
    """Bug 1 - Client creation was reported as not saving. Testing full CRUD."""
    
    def test_create_client_returns_201(self, api_client):
        """POST /api/clients/ should return 201 with client_id"""
        unique_name = f"TEST_Bug42_Client_{uuid.uuid4().hex[:8]}"
        payload = {"business_name": unique_name}
        
        response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "client_id" in data, "Response missing client_id"
        assert data["business_name"] == unique_name
        print(f"✓ Client created: {data['client_id']}")
        
        # Store for cleanup
        self.__class__.created_client_id = data["client_id"]
        self.__class__.created_client_name = unique_name
    
    def test_get_client_verifies_persistence(self, api_client):
        """GET /api/clients/{{id}} should return the created client"""
        client_id = getattr(self.__class__, 'created_client_id', None)
        if not client_id:
            pytest.skip("No client_id from create test")
        
        response = api_client.get(f"{BASE_URL}/api/clients/{client_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["client_id"] == client_id
        assert data["business_name"] == self.__class__.created_client_name
        print(f"✓ Client persisted and retrievable: {client_id}")
    
    def test_client_appears_in_list(self, api_client):
        """GET /api/clients/ should include the created client"""
        client_name = getattr(self.__class__, 'created_client_name', None)
        if not client_name:
            pytest.skip("No client name from create test")
        
        response = api_client.get(f"{BASE_URL}/api/clients/?search={client_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        
        found = any(c["business_name"] == client_name for c in data["clients"])
        assert found, f"Client {client_name} not found in list"
        print(f"✓ Client appears in list search")
    
    def test_update_client_works(self, api_client):
        """PUT /api/clients/{{id}} should update client"""
        client_id = getattr(self.__class__, 'created_client_id', None)
        if not client_id:
            pytest.skip("No client_id from create test")
        
        new_city = "Roma"
        response = api_client.put(f"{BASE_URL}/api/clients/{client_id}", json={
            "city": new_city,
            "province": "RM"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["city"] == new_city
        print(f"✓ Client updated: city={new_city}")
    
    def test_delete_client_cleanup(self, api_client):
        """DELETE /api/clients/{{id}} for cleanup"""
        client_id = getattr(self.__class__, 'created_client_id', None)
        if not client_id:
            pytest.skip("No client_id to delete")
        
        response = api_client.delete(f"{BASE_URL}/api/clients/{client_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 404, "Client should return 404 after deletion"
        print(f"✓ Client deleted: {client_id}")


class TestBug2SalesConditions:
    """Bug 2 - Sales conditions (condizioni_vendita) not in documents. Testing persistence."""
    
    def test_update_condizioni_vendita(self, api_client):
        """PUT /api/company/settings should update condizioni_vendita"""
        test_condizioni = f"Pagamento a 30gg. Foro competente: Tribunale di Roma. TEST_{uuid.uuid4().hex[:6]}"
        
        response = api_client.put(f"{BASE_URL}/api/company/settings", json={
            "condizioni_vendita": test_condizioni
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["condizioni_vendita"] == test_condizioni, f"condizioni_vendita mismatch"
        print(f"✓ condizioni_vendita updated")
        
        self.__class__.test_condizioni = test_condizioni
    
    def test_get_condizioni_vendita_persisted(self, api_client):
        """GET /api/company/settings should return persisted condizioni_vendita"""
        test_condizioni = getattr(self.__class__, 'test_condizioni', None)
        if not test_condizioni:
            pytest.skip("No condizioni from update test")
        
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert "condizioni_vendita" in data
        assert data["condizioni_vendita"] == test_condizioni
        print(f"✓ condizioni_vendita persisted: {test_condizioni[:40]}...")


class TestBug3CompanyLogo:
    """Bug 3 - Company logo missing. Testing logo_url field."""
    
    def test_logo_url_field_exists_in_settings(self, api_client):
        """GET /api/company/settings should include logo_url field"""
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert "logo_url" in data, "logo_url field missing from company settings"
        print(f"✓ logo_url field exists (value: {'set' if data['logo_url'] else 'empty'})")
    
    def test_update_logo_url(self, api_client):
        """PUT /api/company/settings should update logo_url"""
        # Using a small base64 data URI (1x1 transparent PNG)
        test_logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.put(f"{BASE_URL}/api/company/settings", json={
            "logo_url": test_logo
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["logo_url"] == test_logo
        print(f"✓ logo_url updated with base64 data")
        
        self.__class__.test_logo = test_logo
    
    def test_get_logo_url_persisted(self, api_client):
        """GET /api/company/settings should return persisted logo_url"""
        test_logo = getattr(self.__class__, 'test_logo', None)
        if not test_logo:
            pytest.skip("No logo from update test")
        
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert data["logo_url"] == test_logo
        print(f"✓ logo_url persisted correctly")
    
    def test_clear_logo_url(self, api_client):
        """PUT /api/company/settings with empty logo_url should clear it"""
        response = api_client.put(f"{BASE_URL}/api/company/settings", json={
            "logo_url": ""
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["logo_url"] == ""
        print(f"✓ logo_url cleared")


class TestSidebarLogoAPI:
    """Verify sidebar can fetch logo from company settings"""
    
    def test_company_settings_returns_logo_for_sidebar(self, api_client):
        """GET /api/company/settings should work for sidebar component fetch"""
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        
        assert response.status_code == 200
        data = response.json()
        
        # Sidebar needs: logo_url field in response
        assert "logo_url" in data, "Sidebar needs logo_url field"
        print(f"✓ Sidebar can fetch company settings with logo_url")


class TestClientCreationWithFullData:
    """Test client creation with all optional fields (as user would do in UI)"""
    
    def test_create_client_with_full_data(self, api_client):
        """Create client with business_name, P.IVA, and city"""
        unique_name = f"TEST_Carpenteria_Full_{uuid.uuid4().hex[:6]}"
        payload = {
            "business_name": unique_name,
            "partita_iva": f"IT{uuid.uuid4().hex[:11].upper()}",
            "city": "Milano",
            "province": "MI"
        }
        
        response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["business_name"] == unique_name
        assert data["city"] == "Milano"
        assert data["province"] == "MI"
        assert data["partita_iva"] == payload["partita_iva"]
        print(f"✓ Full client created: {data['client_id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
        print(f"✓ Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

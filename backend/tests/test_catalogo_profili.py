"""
Catalogo Profili Personalizzato (Custom Warehouse) API Tests
Tests CRUD operations, bulk price update, and merged catalog endpoint.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session created via MongoDB for auth
TEST_SESSION_TOKEN = None
TEST_USER_ID = None
CREATED_PROFILE_IDS = []


@pytest.fixture(scope="module", autouse=True)
def setup_test_user():
    """Create test user and session before tests, cleanup after."""
    global TEST_SESSION_TOKEN, TEST_USER_ID
    
    # Create test user via mongosh
    ts = int(time.time() * 1000)
    TEST_USER_ID = f'catalogo-pytest-{ts}'
    TEST_SESSION_TOKEN = f'catalogo_pytest_{ts}'
    
    import subprocess
    subprocess.run([
        "mongosh", "--quiet", "--eval", f"""
        use('test_database');
        db.users.insertOne({{
          user_id: '{TEST_USER_ID}',
          email: 'catalogo.pytest.{ts}@example.com',
          name: 'Catalogo Pytest User',
          picture: 'https://via.placeholder.com/150',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{TEST_USER_ID}',
          session_token: '{TEST_SESSION_TOKEN}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        """
    ], check=True)
    
    yield
    
    # Cleanup: delete test user's profiles
    import subprocess
    subprocess.run([
        "mongosh", "--quiet", "--eval", f"""
        use('test_database');
        db.user_profiles.deleteMany({{user_id: '{TEST_USER_ID}'}});
        db.users.deleteOne({{user_id: '{TEST_USER_ID}'}});
        db.user_sessions.deleteOne({{session_token: '{TEST_SESSION_TOKEN}'}});
        """
    ], check=True)


@pytest.fixture
def api_client():
    """Shared requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
    })
    return session


@pytest.fixture
def unauth_client():
    """Requests session without auth."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCatalogoAuth:
    """Authentication requirement tests"""
    
    def test_list_profiles_requires_auth(self, unauth_client):
        """GET /api/catalogo/ should return 401 without auth"""
        response = unauth_client.get(f"{BASE_URL}/api/catalogo/")
        assert response.status_code == 401
    
    def test_merged_catalog_requires_auth(self, unauth_client):
        """GET /api/catalogo/merged/all should return 401 without auth"""
        response = unauth_client.get(f"{BASE_URL}/api/catalogo/merged/all")
        assert response.status_code == 401


class TestCatalogoCRUD:
    """CRUD operations for custom profiles"""
    
    def test_list_profiles_empty_for_new_user(self, api_client):
        """New user should have empty profile list"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert "total" in data
    
    def test_create_profile(self, api_client):
        """POST /api/catalogo/ creates new custom profile"""
        global CREATED_PROFILE_IDS
        
        payload = {
            "code": "PYTEST-FERRO-01",
            "description": "Pytest Test Iron Profile",
            "category": "ferro",
            "weight_m": 2.5,
            "surface_m": 0.15,
            "price_m": 10.50,
            "supplier": "Test Supplier"
        }
        response = api_client.post(f"{BASE_URL}/api/catalogo/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == payload["code"]
        assert data["description"] == payload["description"]
        assert data["category"] == "ferro"
        assert data["weight_m"] == 2.5
        assert data["surface_m"] == 0.15
        assert data["price_m"] == 10.50
        assert data["supplier"] == "Test Supplier"
        assert "profile_id" in data
        assert data["profile_id"].startswith("up_")
        
        CREATED_PROFILE_IDS.append(data["profile_id"])
    
    def test_create_duplicate_code_rejected(self, api_client):
        """POST /api/catalogo/ with duplicate code returns 409"""
        payload = {
            "code": "PYTEST-FERRO-01",  # Same code as previous test
            "description": "Duplicate profile",
            "category": "ferro"
        }
        response = api_client.post(f"{BASE_URL}/api/catalogo/", json=payload)
        assert response.status_code == 409
    
    def test_get_single_profile(self, api_client):
        """GET /api/catalogo/{profile_id} returns profile"""
        if not CREATED_PROFILE_IDS:
            pytest.skip("No profile created yet")
        
        profile_id = CREATED_PROFILE_IDS[0]
        response = api_client.get(f"{BASE_URL}/api/catalogo/{profile_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["profile_id"] == profile_id
        assert data["code"] == "PYTEST-FERRO-01"
    
    def test_get_nonexistent_profile_returns_404(self, api_client):
        """GET /api/catalogo/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/up_nonexistent123")
        assert response.status_code == 404
    
    def test_update_profile(self, api_client):
        """PUT /api/catalogo/{profile_id} updates fields"""
        if not CREATED_PROFILE_IDS:
            pytest.skip("No profile created yet")
        
        profile_id = CREATED_PROFILE_IDS[0]
        update_payload = {
            "description": "Updated Description",
            "price_m": 12.00
        }
        response = api_client.put(f"{BASE_URL}/api/catalogo/{profile_id}", json=update_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Description"
        assert data["price_m"] == 12.00
        # Original fields unchanged
        assert data["code"] == "PYTEST-FERRO-01"
        
        # Verify via GET
        get_response = api_client.get(f"{BASE_URL}/api/catalogo/{profile_id}")
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "Updated Description"


class TestBulkPriceUpdate:
    """Bulk price update endpoint tests"""
    
    def test_create_profiles_for_bulk_test(self, api_client):
        """Create multiple profiles with prices for bulk update"""
        global CREATED_PROFILE_IDS
        
        profiles = [
            {"code": "PYTEST-BULK-A", "description": "Bulk A", "category": "ferro", "price_m": 20.00},
            {"code": "PYTEST-BULK-B", "description": "Bulk B", "category": "alluminio", "price_m": 30.00},
            {"code": "PYTEST-BULK-C", "description": "Bulk C", "category": "ferro", "price_m": 40.00},
        ]
        
        for p in profiles:
            response = api_client.post(f"{BASE_URL}/api/catalogo/", json=p)
            if response.status_code == 201:
                CREATED_PROFILE_IDS.append(response.json()["profile_id"])
    
    def test_bulk_price_increase_all(self, api_client):
        """POST /api/catalogo/bulk-price-update increases all prices"""
        response = api_client.post(
            f"{BASE_URL}/api/catalogo/bulk-price-update",
            json={"percentage": 10.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data
        assert data["updated_count"] >= 3  # At least our test profiles
    
    def test_bulk_price_update_with_category_filter(self, api_client):
        """POST /api/catalogo/bulk-price-update with category filter"""
        response = api_client.post(
            f"{BASE_URL}/api/catalogo/bulk-price-update",
            json={"percentage": -5.0, "category": "alluminio"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] >= 1


class TestMergedCatalog:
    """Merged catalog (standard + custom) endpoint tests"""
    
    def test_merged_catalog_returns_standard_profiles(self, api_client):
        """GET /api/catalogo/merged/all includes 43 standard profiles"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/merged/all")
        
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert "total" in data
        
        # Should have at least 43 standard profiles
        standard_profiles = [p for p in data["profiles"] if p.get("source") == "standard"]
        assert len(standard_profiles) == 43
    
    def test_merged_catalog_includes_custom_profiles(self, api_client):
        """GET /api/catalogo/merged/all includes user's custom profiles"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/merged/all")
        
        assert response.status_code == 200
        data = response.json()
        
        custom_profiles = [p for p in data["profiles"] if p.get("source") == "custom"]
        # Should include our test profiles
        assert len(custom_profiles) >= 1
    
    def test_standard_profiles_have_correct_source_field(self, api_client):
        """Standard profiles should have source='standard'"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/merged/all")
        
        data = response.json()
        standard = [p for p in data["profiles"] if p["source"] == "standard"]
        
        for p in standard[:5]:  # Check first 5
            assert p["source"] == "standard"
            assert p["price_m"] is None  # Standard profiles have no price
            assert p["supplier"] == "Standard"
    
    def test_custom_profiles_have_correct_source_field(self, api_client):
        """Custom profiles should have source='custom'"""
        response = api_client.get(f"{BASE_URL}/api/catalogo/merged/all")
        
        data = response.json()
        custom = [p for p in data["profiles"] if p["source"] == "custom"]
        
        for p in custom:
            assert p["source"] == "custom"
            # Custom profiles may have price_m


class TestCatalogoDelete:
    """Delete endpoint tests (run last)"""
    
    def test_delete_profile(self, api_client):
        """DELETE /api/catalogo/{profile_id} removes profile"""
        if not CREATED_PROFILE_IDS:
            pytest.skip("No profiles to delete")
        
        profile_id = CREATED_PROFILE_IDS.pop()
        response = api_client.delete(f"{BASE_URL}/api/catalogo/{profile_id}")
        
        assert response.status_code == 200
        
        # Verify deleted (should return 404)
        get_response = api_client.get(f"{BASE_URL}/api/catalogo/{profile_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_returns_404(self, api_client):
        """DELETE /api/catalogo/{invalid_id} returns 404"""
        response = api_client.delete(f"{BASE_URL}/api/catalogo/up_nonexistent999")
        assert response.status_code == 404

"""
Backend tests for P1 Features:
1. Registro DDT - KPI stats and date filtering
2. Quick Fill Fatture - sources endpoint
3. Validazione AI Foto Posa - photo validation endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_1772257377982"

@pytest.fixture
def api_client():
    """Authenticated API client."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestDDTStats:
    """Test DDT Stats/Registro endpoint (Feature 1)"""
    
    def test_ddt_stats_registro_endpoint(self, api_client):
        """GET /api/ddt/stats/registro - should return KPI stats"""
        response = api_client.get(f"{BASE_URL}/api/ddt/stats/registro")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields in response
        assert "year" in data, "Missing 'year' field"
        assert "month" in data, "Missing 'month' field"
        assert "total_all" in data, "Missing 'total_all' field"
        assert "total_month" in data, "Missing 'total_month' field"
        assert "per_type" in data, "Missing 'per_type' field"
        assert "per_status" in data, "Missing 'per_status' field"
        assert "volume_month" in data, "Missing 'volume_month' field"
        assert "top_clients" in data, "Missing 'top_clients' field"
        print(f"DDT stats response: year={data['year']}, month={data['month']}, total_all={data['total_all']}")

    def test_ddt_stats_with_year_month_params(self, api_client):
        """GET /api/ddt/stats/registro with year and month query params"""
        response = api_client.get(f"{BASE_URL}/api/ddt/stats/registro?year=2025&month=12")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["year"] == 2025, f"Expected year=2025, got {data['year']}"
        assert data["month"] == 12, f"Expected month=12, got {data['month']}"
        print(f"DDT stats with params: year={data['year']}, month={data['month']}")

    def test_ddt_list_with_date_filters(self, api_client):
        """GET /api/ddt/ with date_from and date_to query params"""
        response = api_client.get(f"{BASE_URL}/api/ddt/?date_from=2025-01-01&date_to=2025-12-31")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Missing 'items' field"
        assert "total" in data, "Missing 'total' field"
        print(f"DDT list with date filter: {data['total']} items found")


class TestQuickFillSources:
    """Test Quick Fill Sources endpoint (Feature 2)"""
    
    def test_quick_fill_sources_endpoint(self, api_client):
        """GET /api/invoices/quick-fill/sources - should return sources list"""
        response = api_client.get(f"{BASE_URL}/api/invoices/quick-fill/sources")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "sources" in data, "Missing 'sources' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["sources"], list), "sources should be a list"
        print(f"Quick fill sources: {data['total']} sources found")

    def test_quick_fill_sources_filter_preventivo(self, api_client):
        """GET /api/invoices/quick-fill/sources?doc_type=preventivo"""
        response = api_client.get(f"{BASE_URL}/api/invoices/quick-fill/sources?doc_type=preventivo")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # If there are sources, verify they are all preventivi
        for src in data["sources"]:
            assert src["source_type"] == "preventivo", f"Expected preventivo, got {src['source_type']}"
        print(f"Filtered preventivi: {len(data['sources'])} found")

    def test_quick_fill_sources_filter_ddt(self, api_client):
        """GET /api/invoices/quick-fill/sources?doc_type=ddt"""
        response = api_client.get(f"{BASE_URL}/api/invoices/quick-fill/sources?doc_type=ddt")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # If there are sources, verify they are all DDT
        for src in data["sources"]:
            assert src["source_type"] == "ddt", f"Expected ddt, got {src['source_type']}"
        print(f"Filtered DDT: {len(data['sources'])} found")

    def test_quick_fill_sources_search(self, api_client):
        """GET /api/invoices/quick-fill/sources?q=searchterm"""
        response = api_client.get(f"{BASE_URL}/api/invoices/quick-fill/sources?q=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "sources" in data
        print(f"Search results for 'test': {data['total']} found")


class TestAIPhotoValidation:
    """Test AI Photo Validation endpoint (Feature 3)"""
    
    def test_validate_photos_empty_returns_422(self, api_client):
        """POST /api/engine/validate-installation-photos - empty photos should return 422"""
        payload = {
            "product_type": "finestra",
            "description": "Test installation",
            "photos_base64": [],  # Empty photos
            "checklist": [],
            "zona_climatica": "E"
        }
        response = api_client.post(
            f"{BASE_URL}/api/engine/validate-installation-photos",
            json=payload
        )
        assert response.status_code == 422, f"Expected 422 for empty photos, got {response.status_code}: {response.text}"
        print("Empty photos correctly returns 422")

    def test_validate_photos_no_photos_field_returns_422(self, api_client):
        """POST /api/engine/validate-installation-photos - missing photos returns 422"""
        payload = {
            "product_type": "cancello",
            "description": "Test gate installation"
        }
        response = api_client.post(
            f"{BASE_URL}/api/engine/validate-installation-photos",
            json=payload
        )
        # Should return 422 because photos_base64 defaults to empty list
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("Missing photos correctly returns 422")


class TestExistingEndpoints:
    """Verify existing endpoints still work"""
    
    def test_auth_me(self, api_client):
        """GET /api/auth/me - verify authentication works"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth failed: {response.status_code} - {response.text}"
        print("Authentication working")

    def test_ddt_list(self, api_client):
        """GET /api/ddt/ - verify DDT list works"""
        response = api_client.get(f"{BASE_URL}/api/ddt/")
        assert response.status_code == 200, f"DDT list failed: {response.status_code}"
        data = response.json()
        assert "items" in data
        print(f"DDT list working: {data['total']} DDTs")

    def test_invoices_list(self, api_client):
        """GET /api/invoices/ - verify invoices list works"""
        response = api_client.get(f"{BASE_URL}/api/invoices/")
        assert response.status_code == 200, f"Invoices list failed: {response.status_code}"
        data = response.json()
        assert "invoices" in data
        print(f"Invoices list working: {data['total']} invoices")

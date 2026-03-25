"""
Iteration 258 — Multi-Tenant Step 1 Testing
Tests tenant_id field presence in all MongoDB documents, sessions, and CRUD operations.
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tenant-isolation-19.preview.emergentagent.com').rstrip('/')
DEMO_SESSION_TOKEN = "demo_session_token_normafacile"


@pytest.fixture(scope="module")
def session():
    """Create a requests session with demo auth cookie."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Login via demo endpoint
    resp = s.post(f"{BASE_URL}/api/demo/login")
    assert resp.status_code == 200, f"Demo login failed: {resp.text}"
    data = resp.json()
    assert data.get("user", {}).get("tenant_id") == "default", "Demo user should have tenant_id=default"
    return s


class TestHealthAndBasics:
    """Test basic health endpoints."""
    
    def test_health_check(self, session):
        """Health endpoint returns 200."""
        resp = session.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_demo_status(self, session):
        """Demo status shows available."""
        resp = session.get(f"{BASE_URL}/api/demo/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] == True
        print(f"✓ Demo status: {data}")


class TestAuthMeEndpoint:
    """Test /api/auth/me returns user with tenant_id."""
    
    def test_auth_me_returns_tenant_id(self, session):
        """Auth /me endpoint returns user with tenant_id field."""
        resp = session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data, "User response must include tenant_id"
        assert data["tenant_id"] == "default", f"Expected tenant_id='default', got '{data.get('tenant_id')}'"
        assert data["user_id"] == "demo_user"
        print(f"✓ Auth /me returns tenant_id: {data['tenant_id']}")


class TestClientsEndpoint:
    """Test clients CRUD with tenant_id."""
    
    def test_get_clients_returns_tenant_id(self, session):
        """GET /api/clients/ returns data with tenant_id in queries."""
        resp = session.get(f"{BASE_URL}/api/clients/")
        assert resp.status_code == 200
        data = resp.json()
        assert "clients" in data
        # All clients should have tenant_id
        for client in data["clients"]:
            assert "tenant_id" in client, f"Client {client.get('client_id')} missing tenant_id"
            assert client["tenant_id"] == "default"
        print(f"✓ GET /clients/ returned {data['total']} clients, all with tenant_id=default")
    
    def test_create_client_includes_tenant_id(self, session):
        """POST /api/clients/ creates document with tenant_id."""
        payload = {
            "business_name": "TEST_MultiTenant Corp",
            "partita_iva": "IT88888888888",
            "email": "test@multitenant.com"
        }
        resp = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert resp.status_code == 201, f"Create client failed: {resp.text}"
        data = resp.json()
        assert "tenant_id" in data, "Created client must have tenant_id"
        assert data["tenant_id"] == "default"
        assert data["business_name"] == "TEST_MultiTenant Corp"
        print(f"✓ Created client {data['client_id']} with tenant_id={data['tenant_id']}")
        
        # Cleanup
        client_id = data["client_id"]
        del_resp = session.delete(f"{BASE_URL}/api/clients/{client_id}")
        assert del_resp.status_code == 200
        print(f"✓ Cleaned up test client {client_id}")


class TestCommesseEndpoint:
    """Test commesse CRUD with tenant_id."""
    
    def test_get_commesse_returns_data(self, session):
        """GET /api/commesse/ returns data with tenant_id."""
        resp = session.get(f"{BASE_URL}/api/commesse/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        for item in data["items"]:
            assert "tenant_id" in item, f"Commessa {item.get('commessa_id')} missing tenant_id"
            assert item["tenant_id"] == "default"
        print(f"✓ GET /commesse/ returned {data['total']} commesse, all with tenant_id=default")


class TestPreventiviEndpoint:
    """Test preventivi CRUD with tenant_id."""
    
    def test_get_preventivi_returns_data(self, session):
        """GET /api/preventivi/ returns data with tenant_id."""
        resp = session.get(f"{BASE_URL}/api/preventivi/")
        assert resp.status_code == 200
        data = resp.json()
        assert "preventivi" in data
        for prev in data["preventivi"]:
            assert "tenant_id" in prev, f"Preventivo {prev.get('preventivo_id')} missing tenant_id"
            assert prev["tenant_id"] == "default"
        print(f"✓ GET /preventivi/ returned {data['total']} preventivi, all with tenant_id=default")


class TestDashboardEndpoint:
    """Test dashboard stats endpoint."""
    
    def test_dashboard_stats_works(self, session):
        """GET /api/dashboard/stats returns stats."""
        resp = session.get(f"{BASE_URL}/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        # Dashboard should return various stats
        assert "fatturato_mese" in data
        assert "recent_invoices" in data
        print(f"✓ Dashboard stats: fatturato_mese={data['fatturato_mese']}, invoices={len(data['recent_invoices'])}")


class TestArticoliEndpoint:
    """Test articoli CRUD with tenant_id."""
    
    def test_get_articoli_works(self, session):
        """GET /api/articoli/ works."""
        resp = session.get(f"{BASE_URL}/api/articoli/")
        assert resp.status_code == 200
        data = resp.json()
        assert "articoli" in data
        print(f"✓ GET /articoli/ returned {data['total']} articoli")


class TestPaymentTypesEndpoint:
    """Test payment-types CRUD with tenant_id."""
    
    def test_get_payment_types_works(self, session):
        """GET /api/payment-types/ works."""
        resp = session.get(f"{BASE_URL}/api/payment-types/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        print(f"✓ GET /payment-types/ returned {data['total']} payment types")


class TestTenantIsolation:
    """Test that tenant_id is properly used for data isolation."""
    
    def test_clients_filtered_by_tenant(self, session):
        """Verify clients are filtered by tenant_id in queries."""
        # Create a test client
        payload = {
            "business_name": "TEST_TenantIsolation Corp",
            "partita_iva": "IT77777777777",
            "email": "isolation@test.com"
        }
        create_resp = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert create_resp.status_code == 201
        client_id = create_resp.json()["client_id"]
        
        # Verify it appears in list
        list_resp = session.get(f"{BASE_URL}/api/clients/")
        assert list_resp.status_code == 200
        clients = list_resp.json()["clients"]
        found = any(c["client_id"] == client_id for c in clients)
        assert found, "Created client should appear in list"
        
        # Verify GET by ID works
        get_resp = session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["tenant_id"] == "default"
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{client_id}")
        print(f"✓ Tenant isolation test passed for clients")


class TestBackfillVerification:
    """Verify that existing data has been backfilled with tenant_id."""
    
    def test_demo_data_has_tenant_id(self, session):
        """Demo data should have tenant_id=default."""
        # Check clients
        clients_resp = session.get(f"{BASE_URL}/api/clients/")
        assert clients_resp.status_code == 200
        for client in clients_resp.json()["clients"]:
            assert client.get("tenant_id") == "default", f"Client {client['client_id']} missing tenant_id"
        
        # Check commesse
        commesse_resp = session.get(f"{BASE_URL}/api/commesse/")
        assert commesse_resp.status_code == 200
        for comm in commesse_resp.json()["items"]:
            assert comm.get("tenant_id") == "default", f"Commessa {comm['commessa_id']} missing tenant_id"
        
        # Check preventivi
        prev_resp = session.get(f"{BASE_URL}/api/preventivi/")
        assert prev_resp.status_code == 200
        for prev in prev_resp.json()["preventivi"]:
            assert prev.get("tenant_id") == "default", f"Preventivo {prev['preventivo_id']} missing tenant_id"
        
        print("✓ All demo data has tenant_id=default")


class TestSessionTenantId:
    """Test that sessions include tenant_id."""
    
    def test_demo_login_returns_tenant_id(self, session):
        """Demo login should return user with tenant_id."""
        # Re-login to verify
        resp = session.post(f"{BASE_URL}/api/demo/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"].get("tenant_id") == "default"
        print(f"✓ Demo login returns tenant_id in user object")


class TestAdditionalEndpoints:
    """Test additional endpoints that should have tenant_id filtering."""
    
    def test_invoices_endpoint(self, session):
        """GET /api/invoices/ works with tenant filtering."""
        resp = session.get(f"{BASE_URL}/api/invoices/")
        assert resp.status_code == 200
        data = resp.json()
        assert "invoices" in data
        print(f"✓ GET /invoices/ returned {data.get('total', len(data['invoices']))} invoices")
    
    def test_ddt_endpoint(self, session):
        """GET /api/ddt/ works with tenant filtering."""
        resp = session.get(f"{BASE_URL}/api/ddt/")
        assert resp.status_code == 200
        data = resp.json()
        print(f"✓ GET /ddt/ returned data")
    
    def test_rilievi_endpoint(self, session):
        """GET /api/rilievi/ works with tenant filtering."""
        resp = session.get(f"{BASE_URL}/api/rilievi/")
        assert resp.status_code == 200
        data = resp.json()
        print(f"✓ GET /rilievi/ returned data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

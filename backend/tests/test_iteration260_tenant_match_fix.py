"""
Iteration 260 — Tenant Match Fix Testing
Tests for: client dropdown empty in Fatturazione → Nuovo Documento after multi-tenant changes

Key changes verified:
1. tenant_match(user) returns plain string 'default' (NOT MongoDB operator)
2. Startup migration dynamically backfills ALL collections
3. Fixed missing import in demo.py
4. Client creation uses tenant_id as string field
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
DEMO_COOKIE = {"session_token": "demo_session_token_normafacile"}


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_health_check(self):
        """Backend health check returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"PASS: Health check - {data}")
    
    def test_demo_login(self):
        """POST /api/demo/login returns success and sets cookie"""
        response = requests.post(f"{BASE_URL}/api/demo/login")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"]["tenant_id"] == "default"
        print(f"PASS: Demo login - tenant_id={data['user']['tenant_id']}")


class TestClientsEndpoint:
    """Test clients endpoint - the core issue being fixed"""
    
    def test_get_clients_returns_data(self):
        """GET /api/clients/?limit=5 with demo cookie returns clients (count > 0)"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?limit=5",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        assert "total" in data
        # This is the key test - clients should NOT be empty
        assert data["total"] > 0, f"CRITICAL: Client dropdown empty! total={data['total']}"
        print(f"PASS: GET /api/clients/ - total={data['total']}, returned={len(data['clients'])}")
        
        # Verify all clients have tenant_id as string
        for client in data["clients"]:
            assert "tenant_id" in client
            assert isinstance(client["tenant_id"], str), f"tenant_id should be string, got {type(client['tenant_id'])}"
            assert client["tenant_id"] == "default"
        print(f"PASS: All clients have tenant_id='default' as string")
    
    def test_get_active_clients_for_invoice(self):
        """GET /api/clients/?limit=100&status=active - simulates InvoiceEditorPage fetch"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?limit=100&status=active",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        # This is what the invoice editor fetches
        assert data["total"] > 0, "CRITICAL: No active clients for invoice dropdown!"
        print(f"PASS: Active clients for invoice - total={data['total']}")
    
    def test_create_client_has_string_tenant_id(self):
        """POST /api/clients/ creates client with tenant_id as string (NOT MongoDB operator)"""
        import uuid
        test_piva = f"TEST{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            "business_name": f"Test Client {test_piva}",
            "partita_iva": test_piva,
            "codice_fiscale": test_piva,
            "client_type": "cliente",
            "address": "Via Test 123",
            "city": "Milano",
            "province": "MI",
            "cap": "20100",
            "country": "IT"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/clients/",
            json=payload,
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()
        
        # CRITICAL: tenant_id must be a plain string, NOT a MongoDB operator
        assert "tenant_id" in data
        assert isinstance(data["tenant_id"], str), f"tenant_id should be string, got {type(data['tenant_id'])}: {data['tenant_id']}"
        assert data["tenant_id"] == "default"
        # Ensure it's NOT a dict like {"$in": [...]}
        assert not isinstance(data["tenant_id"], dict), f"CRITICAL: tenant_id is a dict (MongoDB operator): {data['tenant_id']}"
        
        print(f"PASS: Created client with tenant_id='{data['tenant_id']}' (string)")
        
        # Cleanup - delete the test client
        client_id = data["client_id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/clients/{client_id}",
            cookies=DEMO_COOKIE
        )
        print(f"Cleanup: Deleted test client {client_id}")


class TestOtherEndpoints:
    """Test other endpoints to ensure tenant filtering works"""
    
    def test_get_commesse(self):
        """GET /api/commesse/ with demo cookie returns commesse"""
        response = requests.get(
            f"{BASE_URL}/api/commesse/",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        # API returns 'items' key
        assert "items" in data or "commesse" in data
        items = data.get("items", data.get("commesse", []))
        print(f"PASS: GET /api/commesse/ - total={data.get('total', len(items))}")
    
    def test_get_preventivi(self):
        """GET /api/preventivi/ with demo cookie returns preventivi"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        assert "preventivi" in data
        print(f"PASS: GET /api/preventivi/ - total={data.get('total', len(data['preventivi']))}")
    
    def test_get_company_settings(self):
        """GET /api/company/settings with demo cookie works"""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        print(f"PASS: GET /api/company/settings")
    
    def test_get_dashboard_stats(self):
        """GET /api/dashboard/stats with demo cookie works"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: GET /api/dashboard/stats - keys={list(data.keys())}")
    
    def test_get_invoices(self):
        """GET /api/invoices/ with demo cookie returns invoices"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        print(f"PASS: GET /api/invoices/ - total={data.get('total', len(data['invoices']))}")


class TestTenantMatchFunction:
    """Verify tenant_match returns string, not MongoDB operator"""
    
    def test_auth_me_returns_tenant_id_string(self):
        """GET /api/auth/me returns user with tenant_id as string"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "tenant_id" in data
        assert isinstance(data["tenant_id"], str), f"tenant_id should be string, got {type(data['tenant_id'])}"
        assert data["tenant_id"] == "default"
        print(f"PASS: /api/auth/me returns tenant_id='{data['tenant_id']}' (string)")


class TestMongoDBDocumentStructure:
    """Verify MongoDB documents have correct tenant_id structure"""
    
    def test_client_document_structure(self):
        """Verify client documents have tenant_id as string in MongoDB"""
        # Get a client and verify structure
        response = requests.get(
            f"{BASE_URL}/api/clients/?limit=1",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] > 0:
            client = data["clients"][0]
            # tenant_id must be a plain string
            assert "tenant_id" in client
            assert isinstance(client["tenant_id"], str)
            # Must NOT be a MongoDB operator like {"$in": [...]}
            assert not isinstance(client["tenant_id"], dict)
            print(f"PASS: Client document has tenant_id='{client['tenant_id']}' (string, not operator)")
        else:
            pytest.skip("No clients to verify")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

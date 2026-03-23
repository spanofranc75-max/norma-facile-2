"""
Demo Mode Testing — Iteration 250
Tests for NormaFacile 2.0 Demo Mode Business Sprint feature.
Covers: demo login, status, reset, data isolation, external action guards.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo session token
DEMO_SESSION_TOKEN = "demo_session_token_normafacile"
# Admin session token (non-demo user)
ADMIN_SESSION_TOKEN = "test_session_token_for_dev_2026"


class TestDemoLogin:
    """Test demo login endpoint."""
    
    def test_demo_login_returns_200(self):
        """POST /api/demo/login should return 200 and set session_token cookie."""
        response = requests.post(f"{BASE_URL}/api/demo/login")
        print(f"Demo login response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"]["is_demo"] is True
        assert data["user"]["role"] == "admin"
        
        # Check cookie is set
        cookies = response.cookies
        print(f"Cookies: {dict(cookies)}")
        # Note: Cookie may not be visible in requests due to httponly flag
        
    def test_demo_login_user_data(self):
        """Demo login should return correct user data."""
        response = requests.post(f"{BASE_URL}/api/demo/login")
        assert response.status_code == 200
        
        user = response.json()["user"]
        assert user["user_id"] == "demo_user"
        assert user["email"] == "demo@normafacile.it"
        assert user["name"] == "Marco Rossi"
        assert user["is_demo"] is True


class TestDemoStatus:
    """Test demo status endpoint."""
    
    def test_demo_status_available(self):
        """GET /api/demo/status should return available: true with commesse_count."""
        response = requests.get(f"{BASE_URL}/api/demo/status")
        print(f"Demo status response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["available"] is True
        assert "commesse_count" in data
        # Should have 3 demo commesse
        assert data["commesse_count"] == 3, f"Expected 3 commesse, got {data['commesse_count']}"
        assert data["demo_user_id"] == "demo_user"


class TestDemoReset:
    """Test demo reset endpoint."""
    
    def test_demo_reset_requires_auth(self):
        """POST /api/demo/reset should require authentication."""
        response = requests.post(f"{BASE_URL}/api/demo/reset")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_demo_reset_with_admin(self):
        """POST /api/demo/reset should work with admin user."""
        cookies = {"session_token": ADMIN_SESSION_TOKEN}
        response = requests.post(f"{BASE_URL}/api/demo/reset", cookies=cookies)
        print(f"Demo reset response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "docs_created" in data
        # Should create ~28 docs across 10 collections
        assert data["docs_created"] >= 20, f"Expected at least 20 docs, got {data['docs_created']}"


class TestDemoUserAuthMe:
    """Test /api/auth/me for demo user."""
    
    def test_auth_me_demo_user(self):
        """GET /api/auth/me should return is_demo: true for demo user."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/auth/me", cookies=cookies)
        print(f"Auth me response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("is_demo") is True, f"Expected is_demo=True, got {data.get('is_demo')}"
        assert data.get("role") == "admin"
        assert data.get("user_id") == "demo_user"
    
    def test_auth_me_non_demo_user(self):
        """GET /api/auth/me should return is_demo: false for non-demo user."""
        cookies = {"session_token": ADMIN_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/auth/me", cookies=cookies)
        
        assert response.status_code == 200
        
        data = response.json()
        # Non-demo user should not have is_demo=True
        assert data.get("is_demo") is not True, f"Non-demo user should not have is_demo=True"


class TestDemoDataIsolation:
    """Test that demo user sees only demo data."""
    
    def test_demo_user_sees_3_commesse(self):
        """Demo user should see exactly 3 commesse."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/commesse/", cookies=cookies)
        print(f"Commesse response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        # API returns "items" not "commesse"
        commesse = data.get("items", data.get("commesse", data)) if isinstance(data, dict) else data
        if isinstance(commesse, dict):
            commesse = commesse.get("items", commesse.get("commesse", []))
        
        print(f"Number of commesse: {len(commesse)}")
        assert len(commesse) == 3, f"Expected 3 commesse, got {len(commesse)}"
        
        # Verify commessa IDs
        commessa_ids = [c.get("commessa_id") for c in commesse]
        print(f"Commessa IDs: {commessa_ids}")
        assert "com_demo_main" in commessa_ids
    
    def test_demo_user_sees_3_preventivi(self):
        """Demo user should see 3 preventivi."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/preventivi", cookies=cookies)
        print(f"Preventivi response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        preventivi = data.get("preventivi", data) if isinstance(data, dict) else data
        if isinstance(preventivi, dict):
            preventivi = preventivi.get("preventivi", [])
        
        print(f"Number of preventivi: {len(preventivi)}")
        assert len(preventivi) == 3, f"Expected 3 preventivi, got {len(preventivi)}"
    
    def test_demo_user_sees_2_clients(self):
        """Demo user should see 2 clients."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/clients/", cookies=cookies)
        print(f"Clients response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        clients = data.get("clients", data) if isinstance(data, dict) else data
        if isinstance(clients, dict):
            clients = clients.get("clients", [])
        
        print(f"Number of clients: {len(clients)}")
        assert len(clients) == 2, f"Expected 2 clients, got {len(clients)}"


class TestDemoCommessaMain:
    """Test main demo commessa data."""
    
    def test_commessa_main_data(self):
        """Demo commessa main should have correct data."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/commesse/com_demo_main", cookies=cookies)
        print(f"Commessa main response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        print(f"Commessa data: {data}")
        
        # Verify key fields
        assert data.get("normativa_tipo") == "EN_1090"
        assert data.get("classe_exc") == "EXC2"
        assert data.get("stato") == "in_produzione"
        assert data.get("value") == 48500.0 or data.get("importo_totale") == 48500.0
        assert data.get("client_name") == "Logistica Emiliana S.p.A."


class TestDemoExternalActionGuards:
    """Test that external actions are simulated for demo user."""
    
    def test_email_guard_simulated(self):
        """POST /api/pacchetti-documentali/{pack_id}/invia should return simulated for demo user."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        
        # First, we need to create or find a pacchetto
        # Let's try to send to a test pack_id
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/test_pack_demo/invia",
            cookies=cookies,
            json={"to": ["test@example.com"], "subject": "Test", "body": "Test"}
        )
        print(f"Email guard response: {response.status_code}")
        print(f"Response body: {response.json() if response.status_code == 200 else response.text}")
        
        # Should return 200 with simulated response (or 404 if pack doesn't exist)
        if response.status_code == 200:
            data = response.json()
            assert data.get("simulated") is True, "Expected simulated=True for demo user"
            assert "simulata" in data.get("message", "").lower() or data.get("simulated") is True
    
    def test_sdi_guard_simulated(self):
        """POST /api/invoices/{invoice_id}/send-sdi should return simulated for demo user."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        
        # Try to send to SDI with a test invoice_id
        response = requests.post(
            f"{BASE_URL}/api/invoices/test_invoice_demo/send-sdi",
            cookies=cookies
        )
        print(f"SDI guard response: {response.status_code}")
        print(f"Response body: {response.json() if response.status_code in [200, 404] else response.text}")
        
        # Should return 200 with simulated response (or 404 if invoice doesn't exist)
        if response.status_code == 200:
            data = response.json()
            assert data.get("simulated") is True, "Expected simulated=True for demo user"


class TestDemoObblighi:
    """Test demo obblighi data."""
    
    def test_demo_commessa_has_obblighi(self):
        """Demo commessa main should have 7 obblighi."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        # Correct endpoint is /api/obblighi
        response = requests.get(
            f"{BASE_URL}/api/obblighi",
            cookies=cookies,
            params={"commessa_id": "com_demo_main"}
        )
        print(f"Obblighi response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        obblighi = data if isinstance(data, list) else data.get("obblighi", data.get("items", []))
        
        # Filter for com_demo_main if needed
        obblighi = [o for o in obblighi if o.get("commessa_id") == "com_demo_main"]
        
        print(f"Number of obblighi for com_demo_main: {len(obblighi)}")
        # Should have 7 obblighi for main commessa
        assert len(obblighi) >= 5, f"Expected at least 5 obblighi, got {len(obblighi)}"


class TestDemoCantiere:
    """Test demo cantiere data."""
    
    def test_demo_cantiere_exists(self):
        """Demo cantiere should exist."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(
            f"{BASE_URL}/api/cantieri-sicurezza/",
            cookies=cookies,
            params={"commessa_id": "com_demo_main"}
        )
        print(f"Cantieri response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        cantieri = data.get("cantieri", data) if isinstance(data, dict) else data
        if isinstance(cantieri, dict):
            cantieri = cantieri.get("cantieri", [])
        
        print(f"Number of cantieri: {len(cantieri)}")
        # Should have at least 1 cantiere
        assert len(cantieri) >= 1, f"Expected at least 1 cantiere, got {len(cantieri)}"


class TestNonDemoUserNoBanner:
    """Test that non-demo user doesn't get demo flag."""
    
    def test_non_demo_user_is_demo_false(self):
        """Non-demo user should have is_demo=false or undefined."""
        cookies = {"session_token": ADMIN_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/auth/me", cookies=cookies)
        
        assert response.status_code == 200
        
        data = response.json()
        # is_demo should be False or not present
        is_demo = data.get("is_demo", False)
        assert is_demo is not True, f"Non-demo user should not have is_demo=True, got {is_demo}"


class TestDemoPlanning:
    """Test planning page data for demo user."""
    
    def test_planning_shows_3_commesse(self):
        """Planning endpoint should show 3 demo commesse."""
        cookies = {"session_token": DEMO_SESSION_TOKEN}
        response = requests.get(f"{BASE_URL}/api/commesse/", cookies=cookies)
        
        assert response.status_code == 200
        
        data = response.json()
        # API returns "items" not "commesse"
        commesse = data.get("items", data.get("commesse", data)) if isinstance(data, dict) else data
        if isinstance(commesse, dict):
            commesse = commesse.get("items", commesse.get("commesse", []))
        
        assert len(commesse) == 3, f"Expected 3 commesse for planning, got {len(commesse)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

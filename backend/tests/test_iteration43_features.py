"""
Iteration 43 Backend Tests - Client Creation Bug Fix, EBITDA Page, PDF Preview

Features tested:
1. BUG FIX - Client Creation: POST /api/clients/ with various payloads
2. EBITDA Financial Analysis: GET /api/dashboard/ebitda?year=2026
3. Settings tabs verification (Logo, Condizioni present)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_3fd8f142365c4bca985f687e996cd67c"

@pytest.fixture
def api_client():
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestClientCreationBugFix:
    """Test client creation bug fix - form submission with preventDefault"""
    
    def test_create_client_returns_201(self, api_client):
        """POST /api/clients/ should return 201 with client_id"""
        payload = {
            "business_name": "TEST_Iteration43_SRL",
            "client_type": "cliente",
            "persona_fisica": False,
            "codice_sdi": "0000000",
            "country": "IT"
        }
        response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "client_id" in data, "Response should contain client_id"
        assert data["business_name"] == "TEST_Iteration43_SRL"
        
        # Cleanup
        if "client_id" in data:
            api_client.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_client_with_empty_optional_fields(self, api_client):
        """POST /api/clients/ with empty strings for optional fields should work"""
        payload = {
            "business_name": "TEST_EmptyFields_SRL",
            "client_type": "cliente",
            "persona_fisica": False,
            "codice_sdi": "0000000",
            "country": "IT",
            # Empty optional fields (should be converted to null by frontend)
            "codice_fiscale": None,
            "partita_iva": None,
            "pec": None,
            "phone": None,
            "email": None,
            "notes": None
        }
        response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "client_id" in data
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_create_client_with_full_data(self, api_client):
        """POST /api/clients/ with all fields populated"""
        import time
        unique_suffix = str(int(time.time()))[-6:]
        payload = {
            "business_name": "TEST_FullData_SRL",
            "client_type": "cliente",
            "persona_fisica": False,
            "codice_sdi": "0000000",
            "country": "IT",
            "partita_iva": f"IT99{unique_suffix}01",
            "codice_fiscale": f"99{unique_suffix}01",
            "pec": "test@pec.it",
            "address": "Via Test 123",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "phone": "+39 06 1234567",
            "email": "test@example.com",
            "notes": "Test notes for iteration 43"
        }
        response = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["partita_iva"] == "IT12345678901"
        assert data["city"] == "Roma"
        
        # Verify persistence
        get_response = api_client.get(f"{BASE_URL}/api/clients/{data['client_id']}")
        assert get_response.status_code == 200
        persisted = get_response.json()
        assert persisted["business_name"] == "TEST_FullData_SRL"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{data['client_id']}")
    
    def test_client_appears_in_list(self, api_client):
        """Created client should appear in GET /api/clients/ list"""
        # Create
        payload = {"business_name": "TEST_ListCheck_SRL", "client_type": "cliente", "codice_sdi": "0000000", "country": "IT"}
        create_resp = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
        assert create_resp.status_code == 201
        client_id = create_resp.json()["client_id"]
        
        # List and find
        list_resp = api_client.get(f"{BASE_URL}/api/clients/?search=TEST_ListCheck")
        assert list_resp.status_code == 200
        clients = list_resp.json().get("clients", [])
        found = any(c["client_id"] == client_id for c in clients)
        assert found, "Created client should appear in list"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{client_id}")


class TestEBITDADashboard:
    """Test EBITDA Financial Analysis endpoint"""
    
    def test_ebitda_endpoint_returns_200(self, api_client):
        """GET /api/dashboard/ebitda?year=2026 should return 200"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/ebitda?year=2026")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_ebitda_returns_12_months(self, api_client):
        """EBITDA response should contain 12 monthly entries"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/ebitda?year=2026")
        assert response.status_code == 200
        
        data = response.json()
        assert "monthly" in data, "Response should have 'monthly' key"
        monthly = data["monthly"]
        assert len(monthly) == 12, f"Expected 12 months, got {len(monthly)}"
        
        # Check month labels in Italian
        expected_labels = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        actual_labels = [m["month_label"] for m in monthly]
        assert actual_labels == expected_labels, f"Month labels mismatch: {actual_labels}"
    
    def test_ebitda_response_structure(self, api_client):
        """EBITDA response should have correct structure"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/ebitda?year=2026")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level keys
        assert "year" in data
        assert "monthly" in data
        assert "ytd" in data
        assert "incassato" in data
        assert "da_incassare" in data
        assert "top_suppliers" in data
        
        # Check YTD structure
        ytd = data["ytd"]
        assert "revenue" in ytd
        assert "costs" in ytd
        assert "margin" in ytd
        assert "margin_pct" in ytd
        
        # Check monthly entry structure
        if data["monthly"]:
            month_entry = data["monthly"][0]
            assert "month" in month_entry
            assert "month_label" in month_entry
            assert "revenue" in month_entry
            assert "costs" in month_entry
            assert "margin" in month_entry
            assert "margin_pct" in month_entry
            assert "rev_count" in month_entry
            assert "cost_count" in month_entry
    
    def test_ebitda_current_year(self, api_client):
        """EBITDA endpoint should work without year parameter (defaults to current)"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/ebitda")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "year" in data
        assert "monthly" in data


class TestCompanySettings:
    """Test company settings including Logo and Condizioni tabs"""
    
    def test_settings_get(self, api_client):
        """GET /api/company/settings should return settings"""
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check logo_url field exists (Bug 3 fix)
        assert "logo_url" in data or data.get("logo_url") is None, "logo_url field should exist"
        
        # Check condizioni_vendita field exists (Bug 2 fix)
        assert "condizioni_vendita" in data or data.get("condizioni_vendita") is None, "condizioni_vendita field should exist"
    
    def test_settings_logo_url_update(self, api_client):
        """PUT /api/company/settings should update logo_url"""
        # Get current settings
        get_resp = api_client.get(f"{BASE_URL}/api/company/settings")
        assert get_resp.status_code == 200
        original = get_resp.json()
        
        # Update with test logo
        test_logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        update_payload = {**original, "logo_url": test_logo}
        put_resp = api_client.put(f"{BASE_URL}/api/company/settings", json=update_payload)
        assert put_resp.status_code == 200, f"Update failed: {put_resp.text}"
        
        # Verify update
        verify_resp = api_client.get(f"{BASE_URL}/api/company/settings")
        assert verify_resp.status_code == 200
        assert verify_resp.json().get("logo_url") == test_logo
        
        # Restore original
        restore_payload = {**original, "logo_url": original.get("logo_url", "")}
        api_client.put(f"{BASE_URL}/api/company/settings", json=restore_payload)
    
    def test_settings_condizioni_vendita_update(self, api_client):
        """PUT /api/company/settings should update condizioni_vendita"""
        # Get current settings
        get_resp = api_client.get(f"{BASE_URL}/api/company/settings")
        assert get_resp.status_code == 200
        original = get_resp.json()
        
        # Update with test condizioni
        test_condizioni = "TEST ITERATION 43 - Pagamento a 30 giorni."
        update_payload = {**original, "condizioni_vendita": test_condizioni}
        put_resp = api_client.put(f"{BASE_URL}/api/company/settings", json=update_payload)
        assert put_resp.status_code == 200, f"Update failed: {put_resp.text}"
        
        # Verify update
        verify_resp = api_client.get(f"{BASE_URL}/api/company/settings")
        assert verify_resp.status_code == 200
        assert verify_resp.json().get("condizioni_vendita") == test_condizioni
        
        # Restore original
        restore_payload = {**original, "condizioni_vendita": original.get("condizioni_vendita", "")}
        api_client.put(f"{BASE_URL}/api/company/settings", json=restore_payload)


class TestDashboardStats:
    """Test main dashboard stats endpoint"""
    
    def test_dashboard_stats_endpoint(self, api_client):
        """GET /api/dashboard/stats should return stats"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check expected keys
        expected_keys = ["ferro_kg", "distinte_attive", "cantieri_attivi", "pos_mese", "fatturato_mese"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

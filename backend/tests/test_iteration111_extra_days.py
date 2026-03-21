"""
Test iteration 111: Extra Days after Fine Mese (FM+N) Payment Terms
Tests the 'End of Month + N Days' payment logic implementation.

Features tested:
1. PaymentTypeBase model has extra_days optional integer field
2. POST /api/payment-types/{id}/simulate calculates dates correctly with extra_days after fine_mese
3. Creating a payment type with fine_mese=true and extra_days=10 saves correctly
4. Simulating scadenze with fine_mese+extra_days gives correct dates
   Example: Invoice 15/01/2026, 30gg FM+10 => 10/03/2026
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://analisi-carpenteria.preview.emergentagent.com"


class TestExtraDaysPaymentTerms:
    """Tests for FM+N (Fine Mese + Extra Days) payment calculation logic"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Create test user and session"""
        import subprocess
        result = subprocess.run([
            'mongosh', '--quiet', '--eval', '''
use('test_database');
var userId = 'test_fm_extradays_' + Date.now();
var sessionToken = 'test_fm_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.fm.extradays.' + Date.now() + '@example.com',
  name: 'Test FM Extra Days',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 24*60*60*1000),
  created_at: new Date()
});
print(sessionToken);
'''
        ], capture_output=True, text=True)
        token = result.stdout.strip().split('\n')[-1]
        yield token
        # Cleanup
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.users.deleteMany({{user_id: /test_fm_extradays_/}});
db.user_sessions.deleteMany({{session_token: /test_fm_session_/}});
db.payment_types.deleteMany({{user_id: /test_fm_extradays_/}});
'''
        ])
    
    @pytest.fixture
    def auth_headers(self, session_token):
        """Return auth headers with session token"""
        return {
            "Cookie": f"session_token={session_token}",
            "Content-Type": "application/json"
        }
    
    def test_create_payment_type_with_extra_days(self, auth_headers):
        """Test creating a payment type with fine_mese=true and extra_days=10"""
        payload = {
            "codice": "TEST_FM10",
            "tipo": "BON",
            "descrizione": "Test Bonifico 30gg FM+10",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()
        
        # Verify extra_days was saved
        assert data.get("fine_mese") == True, "fine_mese should be True"
        assert data.get("extra_days") == 10, "extra_days should be 10"
        assert data.get("codice") == "TEST_FM10"
        assert "payment_type_id" in data
        
        return data["payment_type_id"]
    
    def test_simulate_30gg_fm_plus_10(self, auth_headers):
        """
        Test the exact example from requirements:
        Invoice date 15/01/2026, payment '30gg FM+10': 
        15/01 + 30gg = 14/02, End of month = 28/02, +10 days = 10/03/2026
        """
        # First create the payment type
        payload = {
            "codice": "TEST_30FM10",
            "tipo": "BON",
            "descrizione": "30gg Fine Mese + 10",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 10
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
        pt_id = create_resp.json()["payment_type_id"]
        
        # Now simulate with invoice date 2026-01-15
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200, f"Simulate failed: {sim_resp.text}"
        result = sim_resp.json()
        
        assert "scadenze" in result
        assert len(result["scadenze"]) == 1
        
        # The expected date: 15/01 + 30 days = 14/02, end of month = 28/02, +10 = 10/03/2026
        expected_date = "2026-03-10"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
        assert result["scadenze"][0]["quota_pct"] == 100
        assert result["scadenze"][0]["importo"] == 10000.0
    
    def test_simulate_60gg_fm_plus_15(self, auth_headers):
        """Test 60gg FM+15 with invoice date 2026-02-10"""
        payload = {
            "codice": "TEST_60FM15",
            "tipo": "BON",
            "descrizione": "60gg Fine Mese + 15",
            "codice_fe": "MP05",
            "quote": [{"giorni": 60, "quota": 100}],
            "fine_mese": True,
            "extra_days": 15
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2026-02-10
        # + 60 days = 2026-04-11
        # End of month = 2026-04-30
        # + 15 days = 2026-05-15
        sim_payload = {
            "data_fattura": "2026-02-10",
            "importo": 5000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2026-05-15"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
    
    def test_simulate_fine_mese_without_extra_days(self, auth_headers):
        """Test that fine_mese without extra_days still works (just end of month)"""
        payload = {
            "codice": "TEST_FM_ONLY",
            "tipo": "BON",
            "descrizione": "30gg Fine Mese (no extra)",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": None
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2026-01-15
        # + 30 days = 2026-02-14
        # End of month = 2026-02-28
        # No extra days
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2026-02-28"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
    
    def test_simulate_no_fine_mese(self, auth_headers):
        """Test that without fine_mese, extra_days is ignored"""
        payload = {
            "codice": "TEST_NO_FM",
            "tipo": "BON",
            "descrizione": "30gg (no FM)",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": False,
            "extra_days": 10  # This should be ignored
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2026-01-15
        # + 30 days = 2026-02-14 (no end of month, no extra days)
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2026-02-14"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
    
    def test_update_payment_type_extra_days(self, auth_headers):
        """Test updating an existing payment type to add extra_days"""
        # Create without extra_days
        payload = {
            "codice": "TEST_UPDATE_ED",
            "tipo": "BON",
            "descrizione": "Will add extra_days",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": None
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Update to add extra_days
        update_payload = {
            "extra_days": 5
        }
        
        update_resp = requests.put(
            f"{BASE_URL}/api/payment-types/{pt_id}",
            headers=auth_headers,
            json=update_payload
        )
        
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated.get("extra_days") == 5
        
        # Verify with GET
        get_resp = requests.get(
            f"{BASE_URL}/api/payment-types/{pt_id}",
            headers=auth_headers
        )
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched.get("extra_days") == 5
    
    def test_multiple_installments_with_extra_days(self, auth_headers):
        """Test multiple installments (30/60/90) with FM+10"""
        payload = {
            "codice": "TEST_MULTI_FM10",
            "tipo": "BON",
            "descrizione": "30/60/90gg FM+10",
            "codice_fe": "MP05",
            "quote": [
                {"giorni": 30, "quota": 33.33},
                {"giorni": 60, "quota": 33.33},
                {"giorni": 90, "quota": 33.34}
            ],
            "fine_mese": True,
            "extra_days": 10
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2026-01-15
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 9000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        assert len(result["scadenze"]) == 3
        
        # Rata 1: 15/01 + 30 = 14/02, FM = 28/02, +10 = 10/03
        assert result["scadenze"][0]["data_scadenza"] == "2026-03-10"
        
        # Rata 2: 15/01 + 60 = 16/03, FM = 31/03, +10 = 10/04
        assert result["scadenze"][1]["data_scadenza"] == "2026-04-10"
        
        # Rata 3: 15/01 + 90 = 15/04, FM = 30/04, +10 = 10/05
        assert result["scadenze"][2]["data_scadenza"] == "2026-05-10"
    
    def test_extra_days_zero(self, auth_headers):
        """Test that extra_days=0 is same as no extra_days"""
        payload = {
            "codice": "TEST_FM_ZERO",
            "tipo": "BON",
            "descrizione": "30gg FM+0",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 0
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2026-01-15
        # + 30 days = 2026-02-14
        # End of month = 2026-02-28
        # +0 = 2026-02-28
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2026-02-28"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
    
    def test_get_payment_type_has_extra_days_field(self, auth_headers):
        """Test that GET response includes extra_days field"""
        payload = {
            "codice": "TEST_GET_ED",
            "tipo": "BON",
            "descrizione": "Test GET extra_days",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 20
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # GET and verify field
        get_resp = requests.get(
            f"{BASE_URL}/api/payment-types/{pt_id}",
            headers=auth_headers
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        
        assert "extra_days" in data, "extra_days field should be in response"
        assert data["extra_days"] == 20
    
    def test_list_payment_types_includes_extra_days(self, auth_headers):
        """Test that list endpoint includes extra_days in items"""
        payload = {
            "codice": "TEST_LIST_ED",
            "tipo": "BON",
            "descrizione": "Test LIST extra_days",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 15
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        
        # List and find our item
        list_resp = requests.get(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        
        # Find our test item
        test_item = next((i for i in data["items"] if i["codice"] == "TEST_LIST_ED"), None)
        assert test_item is not None, "Test payment type not found in list"
        assert test_item.get("extra_days") == 15


class TestExtraDaysEdgeCases:
    """Edge case tests for extra_days feature"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Create test user and session"""
        import subprocess
        result = subprocess.run([
            'mongosh', '--quiet', '--eval', '''
use('test_database');
var userId = 'test_ed_edge_' + Date.now();
var sessionToken = 'test_ed_edge_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.ed.edge.' + Date.now() + '@example.com',
  name: 'Test ED Edge Cases',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 24*60*60*1000),
  created_at: new Date()
});
print(sessionToken);
'''
        ], capture_output=True, text=True)
        token = result.stdout.strip().split('\n')[-1]
        yield token
        # Cleanup
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.users.deleteMany({{user_id: /test_ed_edge_/}});
db.user_sessions.deleteMany({{session_token: /test_ed_edge_session_/}});
db.payment_types.deleteMany({{user_id: /test_ed_edge_/}});
'''
        ])
    
    @pytest.fixture
    def auth_headers(self, session_token):
        return {
            "Cookie": f"session_token={session_token}",
            "Content-Type": "application/json"
        }
    
    def test_december_year_rollover(self, auth_headers):
        """Test FM+10 crossing into next year"""
        payload = {
            "codice": "TEST_YEARROLL",
            "tipo": "BON",
            "descrizione": "December Year Rollover",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 10
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2025-12-15
        # + 30 days = 2026-01-14
        # End of month = 2026-01-31
        # + 10 days = 2026-02-10
        sim_payload = {
            "data_fattura": "2025-12-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2026-02-10"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"
    
    def test_leap_year_february(self, auth_headers):
        """Test FM calculation in leap year February (2024 is leap year)"""
        payload = {
            "codice": "TEST_LEAP",
            "tipo": "BON",
            "descrizione": "Leap Year Test",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True,
            "extra_days": 5
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/payment-types/",
            headers=auth_headers,
            json=payload
        )
        assert create_resp.status_code == 201
        pt_id = create_resp.json()["payment_type_id"]
        
        # Invoice date: 2024-01-15 (leap year)
        # + 30 days = 2024-02-14
        # End of month = 2024-02-29 (leap year!)
        # + 5 days = 2024-03-05
        sim_payload = {
            "data_fattura": "2024-01-15",
            "importo": 10000.0
        }
        
        sim_resp = requests.post(
            f"{BASE_URL}/api/payment-types/{pt_id}/simulate",
            headers=auth_headers,
            json=sim_payload
        )
        
        assert sim_resp.status_code == 200
        result = sim_resp.json()
        
        expected_date = "2024-03-05"
        actual_date = result["scadenze"][0]["data_scadenza"]
        
        assert actual_date == expected_date, f"Expected {expected_date}, got {actual_date}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

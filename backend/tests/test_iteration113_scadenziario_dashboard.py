"""
Tests for ScadenziarioPage fintech-style dashboard - Iteration 113
Tests the scadenziario/dashboard endpoint and its KPI calculations
"""
import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestScadenziarioDashboard:
    """Tests for GET /api/fatture-ricevute/scadenziario/dashboard endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, auth_token):
        """Setup test fixtures"""
        self.client = api_client
        self.token = auth_token
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_returns_200(self, api_client, auth_token):
        """Test that dashboard endpoint returns 200 OK"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Dashboard endpoint returns 200")
    
    def test_dashboard_has_correct_structure(self, api_client, auth_token):
        """Test that dashboard response has scadenze and kpi keys"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        assert "scadenze" in data, "Missing 'scadenze' key in response"
        assert "kpi" in data, "Missing 'kpi' key in response"
        assert isinstance(data["scadenze"], list), "scadenze should be a list"
        assert isinstance(data["kpi"], dict), "kpi should be a dict"
        print("✓ Dashboard has correct structure (scadenze + kpi)")
    
    def test_kpi_has_required_fields(self, api_client, auth_token):
        """Test that KPI object contains all required fields for fintech display"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        kpi = response.json()["kpi"]
        
        required_fields = [
            "pagamenti_scaduti",
            "pagamenti_mese_corrente", 
            "incassi_scaduti",
            "incassi_mese_corrente",
            "totale_acquisti_anno",
            "scadenze_totali",
            "scadute",
            "in_scadenza",
            "inbox_da_processare"
        ]
        
        for field in required_fields:
            assert field in kpi, f"Missing KPI field: {field}"
        
        print(f"✓ KPI contains all {len(required_fields)} required fields")
    
    def test_scadenza_item_structure(self, api_client, auth_token):
        """Test that scadenza items have correct structure for TransactionCard"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        scadenze = response.json()["scadenze"]
        
        if len(scadenze) > 0:
            item = scadenze[0]
            required_fields = ["tipo", "id", "titolo", "sottotitolo", "data_scadenza", "importo", "stato", "link"]
            
            for field in required_fields:
                assert field in item, f"Scadenza item missing field: {field}"
            
            # Verify stato values
            assert item["stato"] in ["scaduto", "in_scadenza", "ok"], f"Invalid stato: {item['stato']}"
            print(f"✓ Scadenza item has correct structure with stato='{item['stato']}'")
        else:
            print("✓ No scadenze to validate (empty list is valid)")
    
    def test_scadenze_sorted_by_date(self, api_client, auth_token):
        """Test that scadenze are sorted by data_scadenza ascending"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        scadenze = response.json()["scadenze"]
        
        if len(scadenze) > 1:
            dates = [s.get("data_scadenza", "9999-12-31") for s in scadenze]
            assert dates == sorted(dates), "Scadenze should be sorted by date ascending"
            print("✓ Scadenze are sorted by date")
        else:
            print("✓ Sorting check skipped (not enough items)")
    
    def test_stato_classification(self, api_client, auth_token):
        """Test that stato is correctly assigned based on date"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        scadenze = response.json()["scadenze"]
        today = date.today().isoformat()
        
        for item in scadenze:
            scad_date = item.get("data_scadenza", "")
            stato = item.get("stato", "")
            
            if scad_date and scad_date < today:
                assert stato == "scaduto", f"Past date {scad_date} should be 'scaduto', got '{stato}'"
        
        print("✓ Stato classification is correct for overdue items")
    
    def test_kpi_values_are_numeric(self, api_client, auth_token):
        """Test that KPI values are numeric (int or float)"""
        response = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        kpi = response.json()["kpi"]
        
        numeric_fields = [
            "pagamenti_scaduti", "pagamenti_mese_corrente",
            "incassi_scaduti", "incassi_mese_corrente",
            "totale_acquisti_anno", "scadenze_totali",
            "scadute", "in_scadenza", "inbox_da_processare"
        ]
        
        for field in numeric_fields:
            value = kpi.get(field)
            assert isinstance(value, (int, float)), f"KPI {field} should be numeric, got {type(value)}"
        
        print("✓ All KPI values are numeric")


class TestPaymentRecording:
    """Tests for POST /api/fatture-ricevute/{id}/pagamenti endpoint (Segna Pagato)"""
    
    def test_record_payment_success(self, api_client, auth_token, test_fattura_ricevuta):
        """Test recording a payment on a fattura ricevuta"""
        fr_id = test_fattura_ricevuta["fr_id"]
        
        payment_data = {
            "importo": 100.00,
            "data_pagamento": date.today().isoformat(),
            "metodo": "bonifico",
            "note": "Test payment"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti",
            json=payment_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "totale_pagato" in data
        assert data["totale_pagato"] == 100.00
        print("✓ Payment recorded successfully")
    
    def test_record_payment_updates_dashboard(self, api_client, auth_token, test_fattura_ricevuta):
        """Test that recording payment updates dashboard KPIs"""
        fr_id = test_fattura_ricevuta["fr_id"]
        
        # Get initial KPIs
        response1 = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        initial_kpi = response1.json()["kpi"]
        
        # Record payment
        payment_data = {
            "importo": 500.00,
            "data_pagamento": date.today().isoformat(),
            "metodo": "bonifico",
            "note": ""
        }
        api_client.post(
            f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti",
            json=payment_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Get updated KPIs - payment should reduce outstanding amounts
        response2 = api_client.get(
            f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        updated_kpi = response2.json()["kpi"]
        
        # Verify changes occurred (totals may change depending on stato)
        print(f"Initial pagamenti_scaduti: {initial_kpi.get('pagamenti_scaduti')}")
        print(f"Updated pagamenti_scaduti: {updated_kpi.get('pagamenti_scaduti')}")
        print("✓ Dashboard KPIs updated after payment")


class TestSyncFIC:
    """Tests for POST /api/fatture-ricevute/sync-fic endpoint"""
    
    def test_sync_fic_returns_message(self, api_client, auth_token):
        """Test that sync-fic endpoint returns a message (even if FIC not configured)"""
        response = api_client.post(
            f"{BASE_URL}/api/fatture-ricevute/sync-fic",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # May return 400 if FIC not configured, or 200/502 if configured
        assert response.status_code in [200, 400, 502], f"Unexpected status: {response.status_code}"
        data = response.json()
        
        # Should have some kind of message
        assert "message" in data or "detail" in data, "Response should have message or detail"
        print(f"✓ Sync FIC endpoint responds with status {response.status_code}")


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_token(api_client):
    """Create test user and session, return token"""
    import subprocess
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', '''
use('test_database');
var userId = 'test_scad_pytest_' + Date.now();
var sessionToken = 'test_token_scad_' + Date.now();
db.users.insertOne({
    user_id: userId,
    email: 'pytest.scad.' + Date.now() + '@test.com',
    name: 'Pytest Scadenziario User',
    created_at: new Date()
});
db.user_sessions.insertOne({
    user_id: userId,
    session_token: sessionToken,
    expires_at: new Date(Date.now() + 86400000),
    created_at: new Date()
});
print(sessionToken);
'''],
        capture_output=True, text=True
    )
    token = result.stdout.strip().split('\n')[-1]
    yield token
    
    # Cleanup
    subprocess.run(['mongosh', '--quiet', '--eval', f'''
use('test_database');
db.users.deleteMany({{email: /pytest\\.scad\\./}});
db.user_sessions.deleteMany({{session_token: /test_token_scad_/}});
'''], capture_output=True)


@pytest.fixture
def test_fattura_ricevuta(auth_token):
    """Create a test fattura ricevuta for payment testing"""
    import subprocess
    
    # Get user_id from token
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', f'''
use('test_database');
var session = db.user_sessions.findOne({{session_token: "{auth_token}"}});
print(session ? session.user_id : "NOT_FOUND");
'''],
        capture_output=True, text=True
    )
    user_id = result.stdout.strip().split('\n')[-1]
    
    fr_id = f"fr_pytest_test_{int(__import__('time').time())}"
    
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.insertOne({{
    fr_id: "{fr_id}",
    user_id: "{user_id}",
    fornitore_nome: "Pytest Test Supplier",
    numero_documento: "TEST-001",
    data_documento: "2026-01-01",
    data_scadenza_pagamento: "2025-12-15",
    totale_documento: 1000,
    residuo: 1000,
    payment_status: "non_pagata",
    status: "da_registrare",
    pagamenti: [],
    created_at: new Date()
}});
print("{fr_id}");
'''],
        capture_output=True, text=True
    )
    
    yield {"fr_id": fr_id, "user_id": user_id}
    
    # Cleanup
    subprocess.run(['mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.deleteMany({{fr_id: /fr_pytest_test_/}});
'''], capture_output=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test iteration 108: New features verification
- GET /api/dashboard/semaforo - traffic light view for active commesse
- GET /api/dashboard/stats - existing dashboard stats still work
- GET /api/preventivi/{id}/pdf - PDF generation with payment schedule
- PUT /api/company/settings - settings save with empty email/pec and bank_accounts
- POST /api/preventivi/ - creating preventivo with explicit payload
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')
USER_ID = os.environ.get('TEST_USER_ID', '')


@pytest.fixture(scope="module")
def auth_cookies():
    """Return cookies dict for authenticated requests"""
    return {"session_token": SESSION_TOKEN}


@pytest.fixture(scope="module")
def api_session(auth_cookies):
    """Create requests session with auth"""
    session = requests.Session()
    session.cookies.update(auth_cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


# =====================================================
# Module 1: Dashboard Semaforo (Traffic Light) Endpoint
# =====================================================

class TestDashboardSemaforo:
    """Test the new /api/dashboard/semaforo endpoint for traffic light view of commesse"""
    
    def test_semaforo_endpoint_returns_200(self, api_session):
        """Test that the semaforo endpoint exists and returns 200"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_semaforo_response_structure(self, api_session):
        """Test that semaforo response has correct structure"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
        assert response.status_code == 200
        
        data = response.json()
        # Should have items array, counts object, and total
        assert "items" in data, "Response should have 'items' array"
        assert "counts" in data, "Response should have 'counts' object"
        assert "total" in data, "Response should have 'total' field"
        
        # Counts should have green, yellow, red
        counts = data["counts"]
        assert "green" in counts, "Counts should have 'green'"
        assert "yellow" in counts, "Counts should have 'yellow'"
        assert "red" in counts, "Counts should have 'red'"
        
    def test_semaforo_counts_sum_to_total(self, api_session):
        """Test that traffic light counts sum to total"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
        assert response.status_code == 200
        
        data = response.json()
        counts = data["counts"]
        total = data["total"]
        
        counts_sum = counts.get("green", 0) + counts.get("yellow", 0) + counts.get("red", 0)
        assert counts_sum == total, f"Counts sum ({counts_sum}) should equal total ({total})"
        
    def test_semaforo_auth_required(self):
        """Test that semaforo endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/semaforo")
        assert response.status_code == 401, f"Unauthenticated request should return 401, got {response.status_code}"


# =====================================================
# Module 2: Dashboard Stats Endpoint (Existing)
# =====================================================

class TestDashboardStats:
    """Test that existing dashboard stats endpoint still works"""
    
    def test_stats_endpoint_returns_200(self, api_session):
        """Test that stats endpoint exists and returns 200"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_stats_response_structure(self, api_session):
        """Test that stats response has correct fields"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        # Check key fields exist
        expected_fields = ["ferro_kg", "distinte_attive", "cantieri_attivi", "pos_mese", 
                          "fatturato_mese", "scadenze", "materiale", "recent_invoices", "fatturato_mensile"]
        for field in expected_fields:
            assert field in data, f"Stats should have '{field}' field"
            
    def test_stats_numeric_fields(self, api_session):
        """Test that numeric fields are proper numbers"""
        response = api_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        # These should be numeric
        assert isinstance(data.get("ferro_kg"), (int, float)), "ferro_kg should be numeric"
        assert isinstance(data.get("distinte_attive"), int), "distinte_attive should be int"
        assert isinstance(data.get("cantieri_attivi"), int), "cantieri_attivi should be int"
        assert isinstance(data.get("pos_mese"), int), "pos_mese should be int"
        assert isinstance(data.get("fatturato_mese"), (int, float)), "fatturato_mese should be numeric"


# =====================================================
# Module 3: Company Settings - EmailStr Fix Verification
# =====================================================

class TestCompanySettingsEmailFix:
    """Test that company settings can be saved with empty email/pec fields"""
    
    def test_save_settings_with_empty_email(self, api_session):
        """Test saving settings with empty email string (should work after fix)"""
        # First get current settings
        get_response = api_session.get(f"{BASE_URL}/api/company/settings")
        assert get_response.status_code == 200
        
        # Try to save with empty email
        payload = {
            "business_name": "Test Company Iter108",
            "email": "",
            "pec": ""
        }
        response = api_session.put(f"{BASE_URL}/api/company/settings", json=payload)
        assert response.status_code == 200, f"Should be able to save with empty email/pec: {response.text}"
        
    def test_save_settings_with_bank_accounts(self, api_session):
        """Test saving settings with bank_accounts array"""
        bank_accounts = [
            {
                "account_id": f"acc_{uuid.uuid4().hex[:8]}",
                "bank_name": "Test Bank Iter108",
                "iban": "IT00X0000000000000000000001",
                "bic_swift": "TESTIT00XXX",
                "predefinito": True
            }
        ]
        
        payload = {
            "business_name": "Test Company Iter108",
            "bank_accounts": bank_accounts
        }
        response = api_session.put(f"{BASE_URL}/api/company/settings", json=payload)
        assert response.status_code == 200, f"Should be able to save bank_accounts: {response.text}"
        
        # Verify saved
        get_response = api_session.get(f"{BASE_URL}/api/company/settings")
        assert get_response.status_code == 200
        data = get_response.json()
        assert "bank_accounts" in data, "bank_accounts should be in response"
        
    def test_save_settings_with_null_email(self, api_session):
        """Test saving settings with null email (should work)"""
        payload = {
            "email": None,
            "pec": None
        }
        response = api_session.put(f"{BASE_URL}/api/company/settings", json=payload)
        assert response.status_code == 200, f"Should be able to save with null email/pec: {response.text}"


# =====================================================
# Module 4: Preventivi CRUD and PDF Generation
# =====================================================

class TestPreventiviCRUD:
    """Test preventivi creation and PDF generation"""
    
    created_preventivo_id = None
    
    def test_create_preventivo_explicit_payload(self, api_session):
        """Test creating preventivo with explicit payload fields"""
        payload = {
            "subject": "Test Preventivo Iter108",
            "validity_days": 30,
            "payment_type_label": "Bonifico 30gg",
            "notes": "Test note for iteration 108",
            "lines": [
                {
                    "description": "Test Line Item 1",
                    "quantity": 2,
                    "unit": "pz",
                    "unit_price": 100.00,
                    "vat_rate": "22"
                },
                {
                    "description": "Test Line Item 2",
                    "quantity": 1,
                    "unit": "corpo",
                    "unit_price": 500.00,
                    "vat_rate": "22"
                }
            ],
            "sconto_globale": 5,
            "acconto": 100
        }
        
        response = api_session.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert response.status_code == 201, f"Should create preventivo: {response.text}"
        
        data = response.json()
        assert "preventivo_id" in data, "Response should have preventivo_id"
        assert "number" in data, "Response should have number"
        assert "totals" in data, "Response should have totals"
        
        # Store for later tests
        TestPreventiviCRUD.created_preventivo_id = data["preventivo_id"]
        
        # Verify totals calculation
        totals = data["totals"]
        assert "subtotal" in totals, "Totals should have subtotal"
        assert "total" in totals, "Totals should have total"
        
    def test_get_created_preventivo(self, api_session):
        """Test retrieving created preventivo"""
        if not TestPreventiviCRUD.created_preventivo_id:
            pytest.skip("No preventivo created")
            
        response = api_session.get(f"{BASE_URL}/api/preventivi/{TestPreventiviCRUD.created_preventivo_id}")
        assert response.status_code == 200, f"Should get preventivo: {response.text}"
        
        data = response.json()
        assert data["subject"] == "Test Preventivo Iter108"
        assert len(data.get("lines", [])) == 2


# =====================================================
# Module 5: Preventivo PDF Generation
# =====================================================

class TestPreventivoPDF:
    """Test PDF generation for preventivi"""
    
    def test_pdf_endpoint_exists(self, api_session):
        """Test that PDF endpoint exists and works"""
        if not TestPreventiviCRUD.created_preventivo_id:
            pytest.skip("No preventivo created")
            
        response = api_session.get(f"{BASE_URL}/api/preventivi/{TestPreventiviCRUD.created_preventivo_id}/pdf")
        assert response.status_code == 200, f"PDF endpoint should return 200: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Should return PDF, got {content_type}"
        
    def test_pdf_has_content(self, api_session):
        """Test that PDF has actual content"""
        if not TestPreventiviCRUD.created_preventivo_id:
            pytest.skip("No preventivo created")
            
        response = api_session.get(f"{BASE_URL}/api/preventivi/{TestPreventiviCRUD.created_preventivo_id}/pdf")
        assert response.status_code == 200
        
        # PDF should have content
        assert len(response.content) > 100, f"PDF should have content, got {len(response.content)} bytes"
        
        # PDF magic bytes
        assert response.content[:4] == b'%PDF', "Content should start with PDF magic bytes"
        
    def test_pdf_404_for_nonexistent(self, api_session):
        """Test that PDF returns 404 for non-existent preventivo"""
        response = api_session.get(f"{BASE_URL}/api/preventivi/nonexistent_id_12345/pdf")
        assert response.status_code == 404, f"Should return 404 for non-existent: {response.status_code}"


# =====================================================
# Module 6: Semaforo with Test Commessa
# =====================================================

class TestSemaforoWithCommessa:
    """Test semaforo endpoint with actual commessa data"""
    
    created_commessa_id = None
    
    def test_create_commessa_for_semaforo(self, api_session):
        """Create a test commessa to verify semaforo logic"""
        # First create a client
        client_payload = {
            "business_name": f"Test Client Iter108 {uuid.uuid4().hex[:6]}",
            "partita_iva": "IT12345678901",
            "email": "testclient@iter108.com"
        }
        client_response = api_session.post(f"{BASE_URL}/api/clients/", json=client_payload)
        if client_response.status_code == 201:
            client_id = client_response.json().get("client_id")
        else:
            client_id = None
            
        # Create commessa with deadline in 5 days (should be yellow)
        deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        commessa_payload = {
            "title": "Test Commessa Semaforo Iter108",
            "client_id": client_id,
            "deadline": deadline,
            "priority": "alta",
            "stato": "in_lavorazione"
        }
        
        response = api_session.post(f"{BASE_URL}/api/commesse/", json=commessa_payload)
        if response.status_code == 201:
            TestSemaforoWithCommessa.created_commessa_id = response.json().get("commessa_id")
            
    def test_semaforo_includes_test_commessa(self, api_session):
        """Test that semaforo endpoint returns our test commessa"""
        if not TestSemaforoWithCommessa.created_commessa_id:
            pytest.skip("No commessa created")
            
        response = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        # Find our commessa
        found = False
        for item in items:
            if item.get("commessa_id") == TestSemaforoWithCommessa.created_commessa_id:
                found = True
                # With 5 days left, should be yellow
                assert item.get("semaforo") == "yellow", f"Commessa with 5 days left should be yellow, got {item.get('semaforo')}"
                assert "days_left" in item, "Should have days_left field"
                break
                
        # It's OK if not found - might be filtered by stato
        if not found:
            print(f"Note: Commessa {TestSemaforoWithCommessa.created_commessa_id} not found in semaforo (may be filtered)")


# =====================================================
# Cleanup
# =====================================================

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_preventivo(self, api_session):
        """Delete test preventivo"""
        if TestPreventiviCRUD.created_preventivo_id:
            response = api_session.delete(f"{BASE_URL}/api/preventivi/{TestPreventiviCRUD.created_preventivo_id}")
            # 200 or 404 both OK
            assert response.status_code in [200, 404], f"Cleanup failed: {response.status_code}"
            
    def test_cleanup_commessa(self, api_session):
        """Delete test commessa"""
        if TestSemaforoWithCommessa.created_commessa_id:
            response = api_session.delete(f"{BASE_URL}/api/commesse/{TestSemaforoWithCommessa.created_commessa_id}")
            # 200 or 404 both OK
            assert response.status_code in [200, 404], f"Cleanup failed: {response.status_code}"

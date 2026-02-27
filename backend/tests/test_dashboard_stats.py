"""
Dashboard Stats API Tests - Workshop Dashboard (Cruscotto Officina)
Tests the GET /api/dashboard/stats endpoint which aggregates data from:
- distinte (ferro_kg, distinte_attive, materiale)
- pos_documents (cantieri_attivi, pos_mese, scadenze)
- invoices (fatturato_mese, recent_invoices)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user created via mongosh
TEST_SESSION_TOKEN = "test_session_dashboard_1772194509867"
TEST_USER_ID = "test-dashboard-1772194509867"


class TestDashboardStatsAuth:
    """Test authentication requirements for dashboard stats endpoint"""
    
    def test_dashboard_stats_returns_401_without_auth(self):
        """Dashboard stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "autenticato" in data["detail"].lower() or "unauthorized" in data["detail"].lower()
    
    def test_dashboard_stats_returns_401_with_invalid_token(self):
        """Dashboard stats endpoint rejects invalid tokens"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401


class TestDashboardStatsEndpoint:
    """Test the dashboard stats endpoint with authenticated requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.headers = {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_dashboard_stats_returns_200_with_valid_auth(self):
        """Dashboard stats returns 200 with valid authentication"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        assert response.status_code == 200
    
    def test_dashboard_stats_returns_all_required_fields(self):
        """Dashboard stats returns all required KPI fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields exist
        required_fields = [
            "ferro_kg", "distinte_attive", "cantieri_attivi", 
            "pos_mese", "fatturato_mese", "scadenze", 
            "materiale", "recent_invoices"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_dashboard_stats_ferro_kg_aggregation(self):
        """Dashboard correctly aggregates total weight from active distinte"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have our test distinta with 125.5 kg
        assert data["ferro_kg"] >= 125.5, "ferro_kg should include test distinta weight"
        assert isinstance(data["ferro_kg"], (int, float))
    
    def test_dashboard_stats_distinte_attive_count(self):
        """Dashboard correctly counts active distinte (bozza, confermata, ordinata)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 1 (our test distinta with status 'confermata')
        assert data["distinte_attive"] >= 1, "Should count at least test distinta"
        assert isinstance(data["distinte_attive"], int)
    
    def test_dashboard_stats_cantieri_attivi_count(self):
        """Dashboard correctly counts active POS (bozza or completo status)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 2 (our test POS documents)
        assert data["cantieri_attivi"] >= 2, "Should count at least 2 test POS"
        assert isinstance(data["cantieri_attivi"], int)
    
    def test_dashboard_stats_pos_mese_count(self):
        """Dashboard correctly counts POS created this month"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 2 (our test POS created now)
        assert data["pos_mese"] >= 2, "Should count at least 2 test POS this month"
        assert isinstance(data["pos_mese"], int)
    
    def test_dashboard_stats_fatturato_mese_sum(self):
        """Dashboard correctly sums invoice totals for the month"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 4300 (2500 + 1800 from our test invoices)
        assert data["fatturato_mese"] >= 4300, "Should sum at least test invoice totals"
        assert isinstance(data["fatturato_mese"], (int, float))
    
    def test_dashboard_stats_scadenze_structure(self):
        """Dashboard returns scadenze with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        assert isinstance(data["scadenze"], list)
        
        if len(data["scadenze"]) > 0:
            scadenza = data["scadenze"][0]
            assert "pos_id" in scadenza
            assert "project_name" in scadenza
            assert "deadline" in scadenza
            assert "city" in scadenza
    
    def test_dashboard_stats_scadenze_has_test_data(self):
        """Dashboard scadenze includes our test POS data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 2 scadenze from test data
        assert len(data["scadenze"]) >= 2, "Should have at least 2 scadenze"
        
        # Find our test projects
        project_names = [s["project_name"] for s in data["scadenze"]]
        assert "Test Cantiere Metallico" in project_names or "Test Cantiere Ringhiera" in project_names
    
    def test_dashboard_stats_materiale_structure(self):
        """Dashboard returns materiale (bars needed) with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        assert isinstance(data["materiale"], list)
        
        if len(data["materiale"]) > 0:
            material = data["materiale"][0]
            assert "profile" in material
            assert "bars" in material
            assert "total_m" in material
    
    def test_dashboard_stats_materiale_has_test_data(self):
        """Dashboard materiale includes bar calculations from test distinta"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 2 profile types from our test distinta
        assert len(data["materiale"]) >= 2, "Should have materiale from test distinta"
        
        profiles = [m["profile"] for m in data["materiale"]]
        # Check for our test profiles
        assert any("Tubolare" in p for p in profiles) or any("Angolare" in p for p in profiles)
    
    def test_dashboard_stats_recent_invoices_structure(self):
        """Dashboard returns recent_invoices with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        assert isinstance(data["recent_invoices"], list)
        
        if len(data["recent_invoices"]) > 0:
            inv = data["recent_invoices"][0]
            assert "invoice_id" in inv
            assert "document_number" in inv
            assert "client_name" in inv
            assert "status" in inv
            assert "totals" in inv
    
    def test_dashboard_stats_recent_invoices_has_test_data(self):
        """Dashboard recent_invoices includes our test invoice data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Should have at least 2 invoices from our test data
        assert len(data["recent_invoices"]) >= 2, "Should have at least 2 recent invoices"
        
        # Verify our test invoice numbers
        doc_numbers = [inv["document_number"] for inv in data["recent_invoices"]]
        assert "FT-2026/001" in doc_numbers or "FT-2026/002" in doc_numbers
    
    def test_dashboard_stats_recent_invoices_totals(self):
        """Dashboard recent_invoices includes correct totals structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        for inv in data["recent_invoices"]:
            if inv.get("totals"):
                assert "total_document" in inv["totals"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

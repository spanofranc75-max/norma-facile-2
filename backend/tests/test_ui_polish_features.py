"""
UI/UX Polish Features API Tests
Tests the new dashboard enhancements:
- fatturato_mensile array in GET /api/dashboard/stats (6 months of data)
- GET /api/dashboard/fascicolo/:clientId (project dossier timeline)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - created via mongosh
TEST_SESSION_TOKEN = "test_session_polish_1772202006458"
TEST_USER_ID = "test-polish-1772202006458"
TEST_CLIENT_ID = "test-client-fascicolo-1772202006458"


class TestFatturatoMensile:
    """Test fatturato_mensile array in dashboard stats"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.headers = {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_dashboard_stats_includes_fatturato_mensile(self):
        """Dashboard stats must include fatturato_mensile array"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "fatturato_mensile" in data, "Missing fatturato_mensile field"
        assert isinstance(data["fatturato_mensile"], list), "fatturato_mensile must be a list"
    
    def test_fatturato_mensile_has_6_months(self):
        """fatturato_mensile must have exactly 6 months of data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        assert len(data["fatturato_mensile"]) == 6, "fatturato_mensile must have 6 months"
    
    def test_fatturato_mensile_structure(self):
        """Each month in fatturato_mensile must have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        for month_data in data["fatturato_mensile"]:
            assert "mese" in month_data, "Missing 'mese' field (full month name)"
            assert "mese_short" in month_data, "Missing 'mese_short' field (short month name)"
            assert "importo" in month_data, "Missing 'importo' field (amount)"
            assert "documenti" in month_data, "Missing 'documenti' field (document count)"
            
            # Validate data types
            assert isinstance(month_data["mese"], str), "mese must be string"
            assert isinstance(month_data["mese_short"], str), "mese_short must be string"
            assert isinstance(month_data["importo"], (int, float)), "importo must be numeric"
            assert isinstance(month_data["documenti"], int), "documenti must be integer"
    
    def test_fatturato_mensile_chronological_order(self):
        """fatturato_mensile must be in chronological order (oldest first)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        # Italian months
        mesi_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        months = data["fatturato_mensile"]
        
        # Verify short month names are valid Italian months
        for m in months:
            assert m["mese_short"] in mesi_it, f"Invalid short month name: {m['mese_short']}"
    
    def test_fatturato_mensile_importo_non_negative(self):
        """All importo values must be non-negative"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        data = response.json()
        
        for month_data in data["fatturato_mensile"]:
            assert month_data["importo"] >= 0, f"Negative importo for {month_data['mese']}"
            assert month_data["documenti"] >= 0, f"Negative documenti for {month_data['mese']}"


class TestFascicoloCantiere:
    """Test GET /api/dashboard/fascicolo/:clientId endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.headers = {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_fascicolo_requires_auth(self):
        """Fascicolo endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}")
        assert response.status_code == 401
    
    def test_fascicolo_returns_200_with_valid_auth(self):
        """Fascicolo returns 200 for valid client_id"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        assert response.status_code == 200
    
    def test_fascicolo_returns_404_for_invalid_client(self):
        """Fascicolo returns 404 for non-existent client"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/non-existent-client-id-12345",
            headers=self.headers
        )
        assert response.status_code == 404
    
    def test_fascicolo_returns_client_info(self):
        """Fascicolo returns client information"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        
        assert "client" in data, "Missing client field"
        assert isinstance(data["client"], dict), "client must be an object"
        assert data["client"]["business_name"] == "Test Client for Fascicolo"
        assert data["client"]["client_id"] == TEST_CLIENT_ID
    
    def test_fascicolo_returns_timeline(self):
        """Fascicolo returns timeline array"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        
        assert "timeline" in data, "Missing timeline field"
        assert isinstance(data["timeline"], list), "timeline must be a list"
    
    def test_fascicolo_returns_documents_count(self):
        """Fascicolo returns document counts"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        
        assert "documents" in data, "Missing documents field"
        assert isinstance(data["documents"], dict), "documents must be an object"
        
        # Check required document type counts
        for doc_type in ["rilievi", "distinte", "preventivi", "fatture", "certificazioni"]:
            assert doc_type in data["documents"], f"Missing {doc_type} in documents"
            assert isinstance(data["documents"][doc_type], int), f"{doc_type} count must be integer"
    
    def test_fascicolo_documents_match_test_data(self):
        """Document counts should reflect our test data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        docs = data["documents"]
        
        # We created 1 of each document type for this client
        assert docs["rilievi"] >= 1, "Should have at least 1 rilievo"
        assert docs["distinte"] >= 1, "Should have at least 1 distinta"
        assert docs["preventivi"] >= 1, "Should have at least 1 preventivo"
        assert docs["fatture"] >= 1, "Should have at least 1 fattura"
        assert docs["certificazioni"] >= 1, "Should have at least 1 certificazione"
    
    def test_fascicolo_timeline_structure(self):
        """Each timeline event must have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        
        for event in data["timeline"]:
            assert "type" in event, "Missing type field"
            assert "id" in event, "Missing id field"
            assert "title" in event, "Missing title field"
            assert "status" in event, "Missing status field"
            assert "date" in event, "Missing date field"
            assert "link" in event, "Missing link field"
            
            # Validate type is one of expected values
            valid_types = ["rilievo", "distinta", "preventivo", "fattura", "certificazione"]
            assert event["type"] in valid_types, f"Invalid event type: {event['type']}"
    
    def test_fascicolo_timeline_sorted_by_date(self):
        """Timeline should be sorted by date (newest first)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        timeline = data["timeline"]
        
        if len(timeline) > 1:
            # Verify dates are in descending order
            dates = [event["date"] for event in timeline if event["date"]]
            # Should be sorted descending (newest first)
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "Timeline not sorted descending by date"
    
    def test_fascicolo_includes_raw_document_lists(self):
        """Fascicolo should include raw document lists for detailed views"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/fascicolo/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        data = response.json()
        
        # These lists allow frontend to render document details
        assert "rilievi" in data, "Missing rilievi list"
        assert "distinte" in data, "Missing distinte list"
        assert "preventivi" in data, "Missing preventivi list"
        assert "invoices" in data, "Missing invoices list"
        assert "certificazioni" in data, "Missing certificazioni list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

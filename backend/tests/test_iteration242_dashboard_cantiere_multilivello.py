"""
Test Suite for Dashboard Cantiere Multilivello (Iteration 242)
Tests the GET /api/dashboard/cantiere-multilivello endpoint and related functionality.

Features tested:
- API returns correct structure with commesse array and global_summary
- Each commessa has: semaforo, obblighi, rami, rami_summary, pos, pacchetti, pacchetti_summary, committenza_summary, top_blockers
- Semaphore logic: rosso when bloccanti > 0, giallo when warnings > 0 or aperti > 3, verde otherwise
- Global summary counts match individual commessa data
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "K6fH_AIOSlUNVh8nGj5yAOjYtEyW-Ifsc4X5SFRVQYQ"

@pytest.fixture
def auth_headers():
    """Return headers with session token cookie"""
    return {
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    }

class TestDashboardCantiereMultilivelloAPI:
    """Tests for GET /api/dashboard/cantiere-multilivello endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Test that the endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASSED: Endpoint returns 200 OK")
    
    def test_response_structure(self, auth_headers):
        """Test that response has correct top-level structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level keys
        assert "commesse" in data, "Response missing 'commesse' key"
        assert "global_summary" in data, "Response missing 'global_summary' key"
        assert isinstance(data["commesse"], list), "'commesse' should be a list"
        assert isinstance(data["global_summary"], dict), "'global_summary' should be a dict"
        print(f"PASSED: Response has correct structure with {len(data['commesse'])} commesse")
    
    def test_global_summary_structure(self, auth_headers):
        """Test that global_summary has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["global_summary"]
        required_fields = ["totale", "verdi", "gialli", "rossi", "bloccanti_totali", "aperti_totali"]
        
        for field in required_fields:
            assert field in summary, f"global_summary missing '{field}'"
            assert isinstance(summary[field], int), f"'{field}' should be an integer"
        
        print(f"PASSED: global_summary has all required fields: {summary}")
    
    def test_commessa_structure(self, auth_headers):
        """Test that each commessa has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["commesse"]) == 0:
            pytest.skip("No commesse found to test structure")
        
        commessa = data["commesse"][0]
        
        # Required fields for each commessa
        required_fields = [
            "commessa_id", "numero", "title", "stato", "normativa_tipo",
            "client_name", "value", "deadline", "days_left", "semaforo",
            "obblighi", "top_blockers", "rami", "rami_summary",
            "pos", "pacchetti", "pacchetti_summary",
            "committenza_packages", "committenza_analisi", "committenza_summary"
        ]
        
        for field in required_fields:
            assert field in commessa, f"Commessa missing '{field}'"
        
        print(f"PASSED: Commessa has all required fields. Commessa: {commessa['numero']}")
    
    def test_semaforo_values(self, auth_headers):
        """Test that semaforo values are valid (rosso, giallo, verde)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        valid_semafori = ["rosso", "giallo", "verde"]
        
        for commessa in data["commesse"]:
            assert commessa["semaforo"] in valid_semafori, \
                f"Invalid semaforo '{commessa['semaforo']}' for commessa {commessa['numero']}"
        
        print(f"PASSED: All {len(data['commesse'])} commesse have valid semaforo values")
    
    def test_semaforo_logic_rosso(self, auth_headers):
        """Test that semaforo is rosso when bloccanti > 0"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            obl = commessa.get("obblighi", {})
            bloccanti = obl.get("bloccanti", 0)
            
            if bloccanti > 0:
                assert commessa["semaforo"] == "rosso", \
                    f"Commessa {commessa['numero']} has {bloccanti} bloccanti but semaforo is {commessa['semaforo']}"
        
        print("PASSED: Semaforo logic for rosso (bloccanti > 0) is correct")
    
    def test_semaforo_logic_giallo(self, auth_headers):
        """Test that semaforo is giallo when warnings > 0 or aperti > 3 (and no bloccanti)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            obl = commessa.get("obblighi", {})
            bloccanti = obl.get("bloccanti", 0)
            warnings = obl.get("warnings", 0)
            aperti = obl.get("aperti", 0)
            
            if bloccanti == 0 and (warnings > 0 or aperti > 3):
                assert commessa["semaforo"] == "giallo", \
                    f"Commessa {commessa['numero']} has warnings={warnings}, aperti={aperti} but semaforo is {commessa['semaforo']}"
        
        print("PASSED: Semaforo logic for giallo (warnings > 0 or aperti > 3) is correct")
    
    def test_semaforo_logic_verde(self, auth_headers):
        """Test that semaforo is verde when no bloccanti, no warnings, and aperti <= 3"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            obl = commessa.get("obblighi", {})
            bloccanti = obl.get("bloccanti", 0)
            warnings = obl.get("warnings", 0)
            aperti = obl.get("aperti", 0)
            
            if bloccanti == 0 and warnings == 0 and aperti <= 3:
                assert commessa["semaforo"] == "verde", \
                    f"Commessa {commessa['numero']} should be verde but is {commessa['semaforo']}"
        
        print("PASSED: Semaforo logic for verde is correct")
    
    def test_global_summary_counts_match(self, auth_headers):
        """Test that global_summary counts match individual commessa data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["global_summary"]
        commesse = data["commesse"]
        
        # Count semafori
        verdi = sum(1 for c in commesse if c["semaforo"] == "verde")
        gialli = sum(1 for c in commesse if c["semaforo"] == "giallo")
        rossi = sum(1 for c in commesse if c["semaforo"] == "rosso")
        
        # Count totals
        bloccanti_totali = sum(c.get("obblighi", {}).get("bloccanti", 0) for c in commesse)
        aperti_totali = sum(c.get("obblighi", {}).get("aperti", 0) for c in commesse)
        
        assert summary["totale"] == len(commesse), \
            f"totale mismatch: {summary['totale']} vs {len(commesse)}"
        assert summary["verdi"] == verdi, \
            f"verdi mismatch: {summary['verdi']} vs {verdi}"
        assert summary["gialli"] == gialli, \
            f"gialli mismatch: {summary['gialli']} vs {gialli}"
        assert summary["rossi"] == rossi, \
            f"rossi mismatch: {summary['rossi']} vs {rossi}"
        assert summary["bloccanti_totali"] == bloccanti_totali, \
            f"bloccanti_totali mismatch: {summary['bloccanti_totali']} vs {bloccanti_totali}"
        assert summary["aperti_totali"] == aperti_totali, \
            f"aperti_totali mismatch: {summary['aperti_totali']} vs {aperti_totali}"
        
        print(f"PASSED: Global summary counts match - totale={summary['totale']}, verdi={verdi}, gialli={gialli}, rossi={rossi}")
    
    def test_obblighi_structure(self, auth_headers):
        """Test that obblighi object has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["commesse"]) == 0:
            pytest.skip("No commesse found to test obblighi structure")
        
        for commessa in data["commesse"]:
            obl = commessa.get("obblighi", {})
            
            # Check required fields in obblighi
            required_fields = ["totale", "bloccanti", "aperti", "chiusi", "da_verificare", "warnings", "by_source", "by_severity"]
            for field in required_fields:
                assert field in obl, f"obblighi missing '{field}' for commessa {commessa['numero']}"
        
        print("PASSED: All commesse have correct obblighi structure")
    
    def test_rami_summary_structure(self, auth_headers):
        """Test that rami_summary has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["commesse"]) == 0:
            pytest.skip("No commesse found to test rami_summary structure")
        
        for commessa in data["commesse"]:
            rami_summary = commessa.get("rami_summary", {})
            
            required_fields = ["totale", "pronti", "emissioni_totali", "emissioni_pronte"]
            for field in required_fields:
                assert field in rami_summary, f"rami_summary missing '{field}' for commessa {commessa['numero']}"
        
        print("PASSED: All commesse have correct rami_summary structure")
    
    def test_pacchetti_summary_structure(self, auth_headers):
        """Test that pacchetti_summary has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["commesse"]) == 0:
            pytest.skip("No commesse found to test pacchetti_summary structure")
        
        for commessa in data["commesse"]:
            pacchetti_summary = commessa.get("pacchetti_summary", {})
            
            required_fields = ["totale", "completi", "missing_totali", "expired_totali"]
            for field in required_fields:
                assert field in pacchetti_summary, f"pacchetti_summary missing '{field}' for commessa {commessa['numero']}"
        
        print("PASSED: All commesse have correct pacchetti_summary structure")
    
    def test_committenza_summary_structure(self, auth_headers):
        """Test that committenza_summary has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["commesse"]) == 0:
            pytest.skip("No commesse found to test committenza_summary structure")
        
        for commessa in data["commesse"]:
            committenza_summary = commessa.get("committenza_summary", {})
            
            required_fields = ["pacchetti", "analisi_totali", "analisi_approvate", "analisi_pending", 
                             "obblighi_estratti", "anomalie_totali", "mismatch_totali"]
            for field in required_fields:
                assert field in committenza_summary, f"committenza_summary missing '{field}' for commessa {commessa['numero']}"
        
        print("PASSED: All commesse have correct committenza_summary structure")
    
    def test_top_blockers_structure(self, auth_headers):
        """Test that top_blockers is a list with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            top_blockers = commessa.get("top_blockers", [])
            assert isinstance(top_blockers, list), f"top_blockers should be a list for commessa {commessa['numero']}"
            
            # Check structure of each blocker
            for blocker in top_blockers:
                assert "title" in blocker, "Blocker missing 'title'"
                assert "source_module" in blocker, "Blocker missing 'source_module'"
        
        print("PASSED: All commesse have correct top_blockers structure")
    
    def test_pos_structure_when_present(self, auth_headers):
        """Test that pos object has correct structure when present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            pos = commessa.get("pos")
            if pos is not None:
                required_fields = ["cantiere_id", "nome", "gate_pos_ready", "campi_mancanti", "blockers"]
                for field in required_fields:
                    assert field in pos, f"pos missing '{field}' for commessa {commessa['numero']}"
        
        print("PASSED: POS structure is correct when present")


class TestDashboardCantiereMultilivelloDataIntegrity:
    """Tests for data integrity and consistency"""
    
    def test_rami_list_matches_summary(self, auth_headers):
        """Test that rami list length matches rami_summary.totale"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            rami = commessa.get("rami", [])
            rami_summary = commessa.get("rami_summary", {})
            
            assert len(rami) == rami_summary.get("totale", 0), \
                f"Rami count mismatch for {commessa['numero']}: list={len(rami)}, summary={rami_summary.get('totale')}"
        
        print("PASSED: Rami list matches summary for all commesse")
    
    def test_pacchetti_list_matches_summary(self, auth_headers):
        """Test that pacchetti list length matches pacchetti_summary.totale"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cantiere-multilivello",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data["commesse"]:
            pacchetti = commessa.get("pacchetti", [])
            pacchetti_summary = commessa.get("pacchetti_summary", {})
            
            assert len(pacchetti) == pacchetti_summary.get("totale", 0), \
                f"Pacchetti count mismatch for {commessa['numero']}: list={len(pacchetti)}, summary={pacchetti_summary.get('totale')}"
        
        print("PASSED: Pacchetti list matches summary for all commesse")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

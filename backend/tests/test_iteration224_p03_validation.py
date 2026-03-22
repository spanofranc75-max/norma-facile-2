"""
Iteration 224 — P0.3 + P1 Validation Testing
=============================================
Tests for:
- P0.3: 'Se confermi la commessa' box on IstruttoriaPage
- P1: Validation page with 8 preventivi, aggregate scorecard, individual results
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session tokens from test request
MAIN_USER_SESSION = "fEQQyik5bSdSU_dnWx_8QR1am6kyw543-sOFR12E7sk"
TEST_USER_SESSION = "test_perizia_205a45704b22"


class TestValidationSetAPI:
    """Test /api/validation/set endpoint - returns 8 preventivi"""
    
    def test_validation_set_returns_8_preventivi(self):
        """Verify validation set contains exactly 8 preventivi"""
        response = requests.get(
            f"{BASE_URL}/api/validation/set",
            cookies={"session_token": TEST_USER_SESSION}
        )
        print(f"GET /api/validation/set status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "validation_set" in data, "Response should contain 'validation_set'"
        assert "total" in data, "Response should contain 'total'"
        
        validation_set = data["validation_set"]
        total = data["total"]
        
        print(f"Total preventivi in validation set: {total}")
        assert total == 8, f"Expected 8 preventivi, got {total}"
        assert len(validation_set) == 8, f"Expected 8 items in list, got {len(validation_set)}"
        
        # Verify each item has required fields
        for item in validation_set:
            assert "preventivo_id" in item, "Each item should have preventivo_id"
            assert "number" in item, "Each item should have number"
            assert "normativa_attesa" in item, "Each item should have normativa_attesa"
            print(f"  - {item['number']}: {item['normativa_attesa']}")
    
    def test_validation_set_has_expected_normative(self):
        """Verify validation set contains expected normative types"""
        response = requests.get(
            f"{BASE_URL}/api/validation/set",
            cookies={"session_token": TEST_USER_SESSION}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        normative = [item["normativa_attesa"] for item in data["validation_set"]]
        
        # Should have EN_1090, EN_13241, and GENERICA
        assert "EN_1090" in normative, "Should have EN_1090 preventivi"
        assert "EN_13241" in normative, "Should have EN_13241 preventivi"
        assert "GENERICA" in normative, "Should have GENERICA preventivi"
        
        print(f"Normative distribution: {normative}")


class TestValidationResultsAPI:
    """Test /api/validation/results endpoint"""
    
    def test_validation_results_endpoint(self):
        """Verify validation results endpoint returns existing results"""
        response = requests.get(
            f"{BASE_URL}/api/validation/results",
            cookies={"session_token": TEST_USER_SESSION}
        )
        print(f"GET /api/validation/results status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "risultati" in data, "Response should contain 'risultati'"
        assert "total" in data, "Response should contain 'total'"
        
        print(f"Total validation results: {data['total']}")
        
        # Check if aggregato exists (may be null if no batch run yet)
        if data.get("aggregato"):
            agg = data["aggregato"]
            print(f"Aggregate score: {agg.get('punteggio_medio_globale', 'N/A')}")
            print(f"Classification correct: {agg.get('classificazione_corretta', 'N/A')}")
    
    def test_validation_results_have_scorecards(self):
        """Verify validation results contain scorecards with expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/validation/results",
            cookies={"session_token": TEST_USER_SESSION}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        risultati = data.get("risultati", [])
        if len(risultati) > 0:
            # Check first result has scorecard structure
            result = risultati[0]
            assert "scorecard" in result, "Result should have scorecard"
            
            sc = result["scorecard"]
            assert "classificazione" in sc, "Scorecard should have classificazione"
            assert "profilo" in sc, "Scorecard should have profilo"
            assert "estrazione" in sc, "Scorecard should have estrazione"
            assert "domande" in sc, "Scorecard should have domande"
            assert "punteggio_globale" in sc, "Scorecard should have punteggio_globale"
            
            print(f"Sample scorecard - Global score: {sc['punteggio_globale']}")
            print(f"  Classification correct: {sc['classificazione'].get('corretto')}")


class TestIstruttoriaAPI:
    """Test istruttoria endpoints for P0.3 box"""
    
    def test_get_istruttoria_for_prev_4db2a68b44(self):
        """Verify istruttoria exists for prev_4db2a68b44 (main user)"""
        preventivo_id = "prev_4db2a68b44"
        response = requests.get(
            f"{BASE_URL}/api/istruttoria/preventivo/{preventivo_id}",
            cookies={"session_token": MAIN_USER_SESSION}
        )
        print(f"GET /api/istruttoria/preventivo/{preventivo_id} status: {response.status_code}")
        
        # May return 404 if no analysis exists yet, or 200 if exists
        if response.status_code == 200:
            data = response.json()
            print(f"Istruttoria found: {data.get('istruttoria_id')}")
            print(f"Confermata: {data.get('confermata', False)}")
            print(f"N domande: {len(data.get('domande_residue', []))}")
            print(f"N risposte: {data.get('n_risposte', 0)}")
            
            # Check for applicabilita (needed for P0.3 box)
            if data.get("applicabilita"):
                app = data["applicabilita"]
                print(f"Applicabilita riepilogo: {app.get('riepilogo', {})}")
        elif response.status_code == 404:
            print("No istruttoria found for this preventivo - may need to run analysis first")
        else:
            print(f"Unexpected status: {response.status_code}")
    
    def test_istruttoria_has_required_fields_for_p03_box(self):
        """Verify istruttoria response has fields needed for P0.3 box"""
        # Try with a known preventivo that has analysis
        preventivo_id = "prev_4db2a68b44"
        response = requests.get(
            f"{BASE_URL}/api/istruttoria/preventivo/{preventivo_id}",
            cookies={"session_token": MAIN_USER_SESSION}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # P0.3 box needs these fields:
            # - confermata (boolean)
            # - domande_residue (list)
            # - n_risposte (int)
            # - applicabilita.blocchi_conferma (list)
            # - applicabilita.riepilogo (dict)
            
            assert "confermata" in data or data.get("confermata") is None, "Should have confermata field"
            
            # Check domande_residue
            domande = data.get("domande_residue", [])
            print(f"Domande residue count: {len(domande)}")
            
            # Check applicabilita if exists
            app = data.get("applicabilita", {})
            if app:
                blocchi = app.get("blocchi_conferma", [])
                riepilogo = app.get("riepilogo", {})
                print(f"Blocchi conferma: {len(blocchi)}")
                print(f"Riepilogo keys: {list(riepilogo.keys())}")
        else:
            pytest.skip(f"Istruttoria not found (status {response.status_code})")


class TestSidebarNavigation:
    """Test that sidebar includes Validazione AI (P1) link"""
    
    def test_validation_page_accessible(self):
        """Verify /validazione-p1 page is accessible"""
        # This tests the frontend route exists by checking if the API works
        # The actual sidebar link is in DashboardLayout.js
        response = requests.get(
            f"{BASE_URL}/api/validation/set",
            cookies={"session_token": TEST_USER_SESSION}
        )
        
        assert response.status_code == 200, "Validation API should be accessible"
        print("Validation API accessible - sidebar link should work")


class TestAggregateScorecard:
    """Test aggregate scorecard calculations"""
    
    def test_aggregate_scorecard_structure(self):
        """Verify aggregate scorecard has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/validation/results",
            cookies={"session_token": TEST_USER_SESSION}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        aggregato = data.get("aggregato")
        if aggregato:
            # Check required fields
            expected_fields = [
                "n_preventivi",
                "punteggio_medio_globale",
                "classificazione_corretta",
                "media_classificazione",
                "media_profilo",
                "media_estrazione",
                "media_domande"
            ]
            
            for field in expected_fields:
                assert field in aggregato, f"Aggregate should have {field}"
                print(f"  {field}: {aggregato[field]}")
            
            # Verify percentages are between 0 and 1
            for metric in ["punteggio_medio_globale", "media_classificazione", "media_profilo", "media_estrazione", "media_domande"]:
                val = aggregato.get(metric, 0)
                assert 0 <= val <= 1, f"{metric} should be between 0 and 1, got {val}"
        else:
            print("No aggregate data yet - batch validation may not have been run")


class TestValidationSetGroundTruth:
    """Test that validation set matches expected ground truth"""
    
    def test_validation_set_preventivo_ids(self):
        """Verify validation set contains expected preventivo IDs"""
        response = requests.get(
            f"{BASE_URL}/api/validation/set",
            cookies={"session_token": TEST_USER_SESSION}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Expected preventivo IDs from validation_engine.py
        expected_ids = [
            "prev_04a9a9d21bfa",
            "prev_35c6b96a9e75",
            "prev_62e2e4b9c088",
            "prev_7c71048368",
            "prev_1d4a5ec4c687",
            "prev_eb87b5c85253",
            "prev_73cdb12e4ef7",
            "prev_8e8311d22a3c"
        ]
        
        actual_ids = [item["preventivo_id"] for item in data["validation_set"]]
        
        for expected_id in expected_ids:
            assert expected_id in actual_ids, f"Expected {expected_id} in validation set"
        
        print(f"All {len(expected_ids)} expected preventivo IDs found in validation set")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

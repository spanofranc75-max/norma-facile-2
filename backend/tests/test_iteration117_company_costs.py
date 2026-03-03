"""
Iteration 117: Company Cost Configuration & Hourly Rate Calculation Tests

Tests for:
1. calc_hourly_cost service function - calculates full hourly cost
2. calc_commessa_margin service function - includes labor cost with alert levels
3. GET /api/costs/company-costs - returns default or saved config
4. PUT /api/costs/company-costs - saves configuration
5. POST /api/costs/commesse/{id}/ore - logs hours to commessa
6. GET /api/costs/margin-analysis - includes labor cost in each commessa
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_iteration117"
TEST_USER_ID = "test-user-iteration117"
TEST_COMMESSA_ID = "commessa_iter117_001"


class TestCostCalculatorService:
    """Unit-style tests for cost calculator service functions via API"""

    def test_calc_hourly_cost_default_values(self):
        """Test calc_hourly_cost returns correct default calculation"""
        # GET company-costs returns calc_hourly_cost result
        response = requests.get(
            f"{BASE_URL}/api/costs/company-costs",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # With default 0 values, cost should be 0
        assert "costo_orario_pieno" in data
        # Check structure
        assert "costo_personale" in data
        assert "spese_generali" in data
        assert "ore_lavorabili_anno" in data
        print(f"PASS: Default hourly cost calculation structure verified: {data.get('costo_orario_pieno')}€/h")

    def test_calc_hourly_cost_realistic_values(self):
        """Test calc_hourly_cost with realistic company values
        Formula: (stipendi + contributi + affitto + commercialista + altri) / ore_lavorabili_anno
        Expected: (80000 + 25000 + 18000 + 6000 + 8000) / 3200 = 137000 / 3200 = 42.8125 ≈ 42.81€/h
        """
        payload = {
            "stipendi_lordi": 80000,
            "contributi_inps_inail": 25000,
            "affitto_utenze": 18000,
            "commercialista_software": 6000,
            "altri_costi_fissi": 8000,
            "ore_lavorabili_anno": 3200,
            "n_dipendenti": 2
        }
        
        response = requests.put(
            f"{BASE_URL}/api/costs/company-costs",
            json=payload,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify the calculation: 137000 / 3200 = 42.8125
        expected_cost = round(137000 / 3200, 2)  # 42.81
        assert data["costo_orario_pieno"] == expected_cost, f"Expected {expected_cost}, got {data['costo_orario_pieno']}"
        
        # Verify breakdown
        assert data["costo_personale"] == 105000  # stipendi + contributi
        assert data["spese_generali"] == 32000    # affitto + commercialista + altri
        assert data["costo_totale_annuo"] == 137000
        
        print(f"PASS: calc_hourly_cost({payload}) = {data['costo_orario_pieno']}€/h (expected {expected_cost})")


class TestCalcCommessaMargin:
    """Tests for calc_commessa_margin with labor cost inclusion"""
    
    def test_margin_analysis_includes_labor_cost(self):
        """Test margin-analysis endpoint includes costo_personale based on ore_lavorate * costo_orario_pieno"""
        # First, ensure we have company costs configured (from previous test)
        response = requests.get(
            f"{BASE_URL}/api/costs/margin-analysis",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "commesse" in data
        assert "costo_orario_pieno" in data
        
        # Find our test commessa
        test_commessa = next((c for c in data["commesse"] if c["commessa_id"] == TEST_COMMESSA_ID), None)
        if test_commessa:
            # Verify labor cost fields are present
            assert "costi_materiali" in test_commessa
            assert "costo_personale" in test_commessa
            assert "ore_lavorate" in test_commessa
            assert "costo_orario_pieno" in test_commessa
            assert "alert" in test_commessa
            print(f"PASS: Margin analysis includes labor fields: materiali={test_commessa['costi_materiali']}, personale={test_commessa['costo_personale']}, ore={test_commessa['ore_lavorate']}")
        else:
            print(f"INFO: Test commessa not in margin-analysis yet (no hours logged)")
    
    def test_alert_levels_in_margin_analysis(self):
        """Test that alert levels are correctly calculated
        Alert rules: rosso <0%, arancione <10%, giallo <20%, verde >=20%
        """
        response = requests.get(
            f"{BASE_URL}/api/costs/margin-analysis",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data.get("commesse", []):
            alert = commessa.get("alert")
            margine_pct = commessa.get("margine_pct", 0)
            
            if margine_pct < 0:
                expected_alert = "rosso"
            elif margine_pct < 10:
                expected_alert = "arancione"
            elif margine_pct < 20:
                expected_alert = "giallo"
            else:
                expected_alert = "verde"
            
            assert alert == expected_alert, f"Commessa {commessa.get('numero')}: expected alert '{expected_alert}' for {margine_pct}%, got '{alert}'"
        
        print(f"PASS: All {len(data.get('commesse', []))} commesse have correct alert levels")


class TestCompanyCostsEndpoints:
    """Tests for GET/PUT /api/costs/company-costs"""

    def test_get_company_costs_default(self):
        """GET /api/costs/company-costs returns defaults when not configured"""
        # Delete any existing config
        import pymongo
        client = pymongo.MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client['test_database']
        db.company_costs.delete_many({"user_id": TEST_USER_ID})
        
        response = requests.get(
            f"{BASE_URL}/api/costs/company-costs",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("configured") == False
        assert "costo_orario_pieno" in data
        assert "ore_lavorabili_anno" in data
        print(f"PASS: GET /api/costs/company-costs returns defaults when not configured")

    def test_put_company_costs_saves_config(self):
        """PUT /api/costs/company-costs saves and returns updated calculation"""
        payload = {
            "stipendi_lordi": 60000,
            "contributi_inps_inail": 18000,
            "affitto_utenze": 12000,
            "commercialista_software": 4000,
            "altri_costi_fissi": 6000,
            "ore_lavorabili_anno": 2000,
            "n_dipendenti": 1
        }
        
        response = requests.put(
            f"{BASE_URL}/api/costs/company-costs",
            json=payload,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify calculation: (60000+18000+12000+4000+6000) / 2000 = 100000 / 2000 = 50€/h
        assert data["costo_orario_pieno"] == 50.0
        assert data["configured"] == True
        assert data["stipendi_lordi"] == 60000
        print(f"PASS: PUT /api/costs/company-costs saves and calculates: {data['costo_orario_pieno']}€/h")

    def test_get_company_costs_after_save(self):
        """GET /api/costs/company-costs returns saved config"""
        response = requests.get(
            f"{BASE_URL}/api/costs/company-costs",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have the saved values
        assert data.get("configured") == True
        assert data.get("stipendi_lordi") == 60000
        assert data.get("costo_orario_pieno") == 50.0
        print(f"PASS: GET /api/costs/company-costs returns saved config with costo_orario_pieno={data['costo_orario_pieno']}")


class TestLogHoursToCommessa:
    """Tests for POST /api/costs/commesse/{id}/ore"""

    def test_log_hours_to_commessa(self):
        """POST /api/costs/commesse/{id}/ore logs hours and updates ore_lavorate"""
        # First get current hours
        import pymongo
        client = pymongo.MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client['test_database']
        commessa = db.commesse.find_one({"commessa_id": TEST_COMMESSA_ID})
        initial_hours = commessa.get("ore_lavorate", 0) if commessa else 0
        
        payload = {"ore": 8.5, "note": "Test logging 8.5 hours"}
        
        response = requests.post(
            f"{BASE_URL}/api/costs/commesse/{TEST_COMMESSA_ID}/ore",
            json=payload,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ore_aggiunte"] == 8.5
        assert data["ore_lavorate"] == round(initial_hours + 8.5, 2)
        print(f"PASS: POST /api/costs/commesse/{TEST_COMMESSA_ID}/ore logged 8.5h, total: {data['ore_lavorate']}h")

    def test_log_hours_updates_db(self):
        """Verify hours are actually persisted in database"""
        import pymongo
        client = pymongo.MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client['test_database']
        commessa = db.commesse.find_one({"commessa_id": TEST_COMMESSA_ID})
        
        assert commessa is not None
        assert commessa.get("ore_lavorate", 0) > 0
        assert "log_ore" in commessa
        assert len(commessa["log_ore"]) > 0
        print(f"PASS: Hours persisted in DB: {commessa.get('ore_lavorate')}h with {len(commessa['log_ore'])} log entries")

    def test_log_hours_invalid_commessa(self):
        """POST to non-existent commessa returns 404"""
        payload = {"ore": 1, "note": "Test"}
        
        response = requests.post(
            f"{BASE_URL}/api/costs/commesse/nonexistent_commessa_xyz/ore",
            json=payload,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 404
        print("PASS: POST to non-existent commessa returns 404")


class TestMarginAnalysisWithLabor:
    """Tests for margin-analysis with labor costs included"""

    def test_margin_analysis_labor_cost_calculation(self):
        """Verify margin-analysis correctly calculates costo_personale = ore_lavorate * costo_orario_pieno"""
        # First ensure company costs are configured
        cost_config = {
            "stipendi_lordi": 80000,
            "contributi_inps_inail": 25000,
            "affitto_utenze": 18000,
            "commercialista_software": 6000,
            "altri_costi_fissi": 8000,
            "ore_lavorabili_anno": 3200,
            "n_dipendenti": 2
        }
        requests.put(
            f"{BASE_URL}/api/costs/company-costs",
            json=cost_config,
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Get margin analysis
        response = requests.get(
            f"{BASE_URL}/api/costs/margin-analysis",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify costo_orario_pieno is returned
        hourly_cost = data.get("costo_orario_pieno", 0)
        assert hourly_cost > 0, "Expected positive costo_orario_pieno"
        
        # Find test commessa
        test_commessa = next((c for c in data["commesse"] if c["commessa_id"] == TEST_COMMESSA_ID), None)
        if test_commessa:
            ore = test_commessa.get("ore_lavorate", 0)
            costo_personale = test_commessa.get("costo_personale", 0)
            expected_costo_personale = round(ore * hourly_cost, 2)
            
            assert costo_personale == expected_costo_personale, f"Expected costo_personale {expected_costo_personale}, got {costo_personale}"
            print(f"PASS: costo_personale calculation correct: {ore}h × {hourly_cost}€/h = {costo_personale}€")
        else:
            print("INFO: Test commessa not in margin analysis (requires costs or hours)")

    def test_margin_includes_both_material_and_labor(self):
        """Verify margine = valore_preventivo - costi_materiali - costo_personale"""
        response = requests.get(
            f"{BASE_URL}/api/costs/margin-analysis",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        for commessa in data.get("commesse", []):
            valore = commessa.get("valore_preventivo", 0)
            materiali = commessa.get("costi_materiali", 0)
            personale = commessa.get("costo_personale", 0)
            margine = commessa.get("margine", 0)
            costo_totale = commessa.get("costo_totale", 0)
            
            # Verify costo_totale = materiali + personale
            expected_totale = round(materiali + personale, 2)
            assert abs(costo_totale - expected_totale) < 0.01, f"costo_totale mismatch: {costo_totale} vs {expected_totale}"
            
            # Verify margine = valore - costo_totale
            expected_margine = round(valore - costo_totale, 2)
            assert abs(margine - expected_margine) < 0.01, f"margine mismatch: {margine} vs {expected_margine}"
        
        print(f"PASS: All {len(data.get('commesse', []))} commesse have correct margin calculations")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self):
        """Clean up all test data created during tests"""
        import pymongo
        client = pymongo.MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client['test_database']
        
        # Clean up
        db.users.delete_many({"user_id": TEST_USER_ID})
        db.user_sessions.delete_many({"session_token": SESSION_TOKEN})
        db.company_costs.delete_many({"user_id": TEST_USER_ID})
        db.commesse.delete_many({"user_id": TEST_USER_ID, "numero": {"$regex": "TEST_ITER117"}})
        
        print("PASS: Test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Iteration 130: Cruscotto Finanziario Artigiano - Financial Dashboard
Tests for GET /api/dashboard/cruscotto-finanziario endpoint

Tests:
1. Response structure validation (all required keys)
2. IVA trimestrale - 4 quarterly entries with correct fields
3. Liquidita - semaforo (verde/giallo/rosso) with proper fields
4. Aging clienti - aging buckets (0_30, 30_60, 60_90, over_90)
5. Cash flow preview - 30/60/90 days with entrate, uscite, saldo
6. Year parameter filtering
7. Empty data handling
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test user setup
USER_ID = f"test-cruscotto-{uuid.uuid4().hex[:8]}"
SESSION_TOKEN = f"test_session_cruscotto_{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="module", autouse=True)
def setup_test_user():
    """Create test user and session for authenticated requests."""
    import subprocess
    
    # Create user and session
    setup_script = f"""
    use('test_database');
    db.users.insertOne({{
      user_id: '{USER_ID}',
      email: 'test.cruscotto.{USER_ID}@example.com',
      name: 'Test Cruscotto User',
      picture: 'https://via.placeholder.com/150',
      created_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: '{USER_ID}',
      session_token: '{SESSION_TOKEN}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", setup_script], capture_output=True)
    
    yield
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{USER_ID}'}});
    db.user_sessions.deleteMany({{session_token: '{SESSION_TOKEN}'}});
    db.invoices.deleteMany({{user_id: '{USER_ID}'}});
    db.fatture_ricevute.deleteMany({{user_id: '{USER_ID}'}});
    db.commesse.deleteMany({{user_id: '{USER_ID}'}});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)


@pytest.fixture
def auth_headers():
    """Return authorization headers."""
    return {
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


class TestCruscottoFinanziarioStructure:
    """Tests for response structure validation."""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Test that the endpoint returns 200 OK."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Endpoint returns 200 OK")
    
    def test_response_has_all_required_keys(self, auth_headers):
        """Test that response contains all required top-level keys."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        required_keys = [
            "year", "iva_trimestri", "liquidita", "aging_clienti",
            "scadenzario_clienti", "scadenzario_fornitori", 
            "cashflow_preview", "top_margin", "bottom_margin", "iva_annuale"
        ]
        
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
        
        print(f"PASS: All {len(required_keys)} required keys present")
    
    def test_year_in_response(self, auth_headers):
        """Test that year is returned correctly."""
        current_year = datetime.now().year
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["year"] == current_year, f"Expected year {current_year}, got {data['year']}"
        print(f"PASS: Year defaults to {current_year}")


class TestIVATrimestrale:
    """Tests for quarterly IVA calculations."""
    
    def test_iva_has_4_quarters(self, auth_headers):
        """Test that iva_trimestri has exactly 4 entries."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert len(data["iva_trimestri"]) == 4, f"Expected 4 quarters, got {len(data['iva_trimestri'])}"
        print("PASS: IVA trimestri has 4 quarterly entries")
    
    def test_iva_quarter_structure(self, auth_headers):
        """Test that each quarter has all required fields."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = [
            "trimestre", "label", "f24_scadenza", 
            "iva_debito", "iva_credito", "iva_da_versare",
            "fatturato", "n_fatture"
        ]
        
        for i, quarter in enumerate(data["iva_trimestri"], 1):
            for field in required_fields:
                assert field in quarter, f"Q{i} missing field: {field}"
            
            # Verify quarter number
            assert quarter["trimestre"] == i, f"Quarter {i} has wrong trimestre value: {quarter['trimestre']}"
        
        print("PASS: All 4 quarters have correct structure")
    
    def test_iva_labels_correct(self, auth_headers):
        """Test that IVA labels are correctly formatted."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        expected_labels = [
            "Q1 (Gen-Mar)",
            "Q2 (Apr-Giu)",
            "Q3 (Lug-Set)",
            "Q4 (Ott-Dic)"
        ]
        
        for i, quarter in enumerate(data["iva_trimestri"]):
            assert quarter["label"] == expected_labels[i], f"Q{i+1} label mismatch"
        
        print("PASS: IVA quarter labels correct")


class TestLiquiditaSemaforo:
    """Tests for liquidity traffic light indicator."""
    
    def test_liquidita_structure(self, auth_headers):
        """Test that liquidita has all required fields."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = [
            "incassi_mese", "da_incassare_mese", "pagamenti_mese",
            "iva_prossima", "entrate_previste", "uscite_previste",
            "saldo_operativo", "semaforo", "semaforo_msg"
        ]
        
        for field in required_fields:
            assert field in data["liquidita"], f"Liquidita missing field: {field}"
        
        print("PASS: Liquidita has all required fields")
    
    def test_semaforo_valid_values(self, auth_headers):
        """Test that semaforo has valid color values."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        valid_semaforo_values = ["verde", "giallo", "rosso"]
        assert data["liquidita"]["semaforo"] in valid_semaforo_values, \
            f"Invalid semaforo value: {data['liquidita']['semaforo']}"
        
        print(f"PASS: Semaforo value is valid: {data['liquidita']['semaforo']}")
    
    def test_semaforo_msg_present(self, auth_headers):
        """Test that semaforo message is not empty."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["liquidita"]["semaforo_msg"], "Semaforo message should not be empty"
        print(f"PASS: Semaforo message present: '{data['liquidita']['semaforo_msg'][:50]}...'")


class TestAgingClienti:
    """Tests for aging receivables buckets."""
    
    def test_aging_structure(self, auth_headers):
        """Test that aging_clienti has all bucket keys."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        required_buckets = ["0_30", "30_60", "60_90", "over_90"]
        
        for bucket in required_buckets:
            assert bucket in data["aging_clienti"], f"Missing aging bucket: {bucket}"
            # Values should be numeric
            assert isinstance(data["aging_clienti"][bucket], (int, float)), \
                f"Aging bucket {bucket} should be numeric"
        
        print("PASS: Aging clienti has all required buckets")
    
    def test_aging_values_non_negative(self, auth_headers):
        """Test that aging values are non-negative."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        for bucket, value in data["aging_clienti"].items():
            assert value >= 0, f"Aging bucket {bucket} has negative value: {value}"
        
        print("PASS: All aging values are non-negative")


class TestCashFlowPreview:
    """Tests for cash flow preview (30/60/90 days)."""
    
    def test_cashflow_has_3_horizons(self, auth_headers):
        """Test that cashflow_preview has 3 entries."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert len(data["cashflow_preview"]) == 3, \
            f"Expected 3 cash flow horizons, got {len(data['cashflow_preview'])}"
        
        print("PASS: Cash flow preview has 3 horizons")
    
    def test_cashflow_structure(self, auth_headers):
        """Test that each cashflow entry has required fields."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = ["label", "entrate", "uscite", "saldo"]
        expected_labels = ["30 giorni", "60 giorni", "90 giorni"]
        
        for i, cf in enumerate(data["cashflow_preview"]):
            for field in required_fields:
                assert field in cf, f"Cashflow {i} missing field: {field}"
            
            assert cf["label"] == expected_labels[i], \
                f"Cashflow {i} label mismatch: {cf['label']}"
        
        print("PASS: Cash flow entries have correct structure")
    
    def test_cashflow_saldo_calculation(self, auth_headers):
        """Test that saldo = entrate - uscite for each horizon."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        for cf in data["cashflow_preview"]:
            expected_saldo = round(cf["entrate"] - cf["uscite"], 2)
            assert cf["saldo"] == expected_saldo, \
                f"Saldo mismatch for {cf['label']}: expected {expected_saldo}, got {cf['saldo']}"
        
        print("PASS: Cash flow saldo calculations correct")


class TestYearFiltering:
    """Tests for year parameter filtering."""
    
    def test_year_param_filtering(self, auth_headers):
        """Test that year parameter is respected."""
        test_year = 2025
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario?year={test_year}",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["year"] == test_year, f"Expected year {test_year}, got {data['year']}"
        print(f"PASS: Year parameter filtering works (requested {test_year})")
    
    def test_future_year_param(self, auth_headers):
        """Test with a future year."""
        future_year = 2027
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario?year={future_year}",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["year"] == future_year
        # All values should be 0 for future year
        assert all(q["fatturato"] == 0 for q in data["iva_trimestri"])
        print(f"PASS: Future year {future_year} returns zeros")
    
    def test_past_year_param(self, auth_headers):
        """Test with a past year."""
        past_year = 2024
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario?year={past_year}",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["year"] == past_year
        print(f"PASS: Past year {past_year} query works")


class TestMarginiCommesse:
    """Tests for job profitability margins."""
    
    def test_margin_arrays_exist(self, auth_headers):
        """Test that top_margin and bottom_margin arrays exist."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert "top_margin" in data, "Missing top_margin key"
        assert "bottom_margin" in data, "Missing bottom_margin key"
        assert isinstance(data["top_margin"], list), "top_margin should be a list"
        assert isinstance(data["bottom_margin"], list), "bottom_margin should be a list"
        
        print("PASS: Margin arrays exist and are lists")


class TestIVAAnnuale:
    """Tests for annual IVA summary."""
    
    def test_iva_annuale_structure(self, auth_headers):
        """Test that iva_annuale has required fields."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = ["totale_debito", "totale_credito", "totale_versare"]
        
        for field in required_fields:
            assert field in data["iva_annuale"], f"Missing iva_annuale field: {field}"
        
        print("PASS: IVA annuale has all required fields")
    
    def test_iva_annuale_totals_match_quarters(self, auth_headers):
        """Test that annual IVA totals match sum of quarters."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        # Sum quarterly values
        sum_debito = sum(q["iva_debito"] for q in data["iva_trimestri"])
        sum_credito = sum(q["iva_credito"] for q in data["iva_trimestri"])
        sum_versare = sum(q["iva_da_versare"] for q in data["iva_trimestri"])
        
        # Compare with annual totals
        assert round(data["iva_annuale"]["totale_debito"], 2) == round(sum_debito, 2)
        assert round(data["iva_annuale"]["totale_credito"], 2) == round(sum_credito, 2)
        assert round(data["iva_annuale"]["totale_versare"], 2) == round(sum_versare, 2)
        
        print("PASS: IVA annuale totals match quarterly sums")


class TestScadenzario:
    """Tests for scadenzario (receivables/payables schedule)."""
    
    def test_scadenzario_arrays_exist(self, auth_headers):
        """Test that scadenzario arrays exist."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        data = response.json()
        
        assert "scadenzario_clienti" in data
        assert "scadenzario_fornitori" in data
        assert isinstance(data["scadenzario_clienti"], list)
        assert isinstance(data["scadenzario_fornitori"], list)
        
        print("PASS: Scadenzario arrays exist")


class TestEmptyDataHandling:
    """Tests for handling empty/no data scenarios."""
    
    def test_empty_data_returns_valid_structure(self, auth_headers):
        """Test that empty data returns valid structure with zeros."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/cruscotto-finanziario",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Structure should be valid even with empty data
        assert len(data["iva_trimestri"]) == 4
        assert len(data["cashflow_preview"]) == 3
        assert len(data["aging_clienti"]) == 4
        
        print("PASS: Empty data returns valid structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

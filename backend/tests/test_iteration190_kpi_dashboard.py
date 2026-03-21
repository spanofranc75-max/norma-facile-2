"""
Iteration 190: KPI Dashboard - Confidence Score & Analytics
Tests for all 7 KPI endpoints:
- GET /api/kpi/overview - Dashboard overview with counts and totals
- GET /api/kpi/accuracy-score - AI accuracy score with confronti array
- GET /api/kpi/trend-accuracy - Trend array with mese/accuracy
- GET /api/kpi/marginalita - Commesse with margins
- GET /api/kpi/ritardi-fornitori - Fornitori stats
- GET /api/kpi/tempi-medi - Tipologie with ore_per_ton
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestKPIEndpointsNoAuth:
    """Test that all KPI endpoints require authentication (return 401 without auth)"""
    
    def test_overview_no_auth(self):
        """GET /api/kpi/overview should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/overview")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/overview returns 401 without auth")
    
    def test_accuracy_score_no_auth(self):
        """GET /api/kpi/accuracy-score should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/accuracy-score")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/accuracy-score returns 401 without auth")
    
    def test_trend_accuracy_no_auth(self):
        """GET /api/kpi/trend-accuracy should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/trend-accuracy")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/trend-accuracy returns 401 without auth")
    
    def test_marginalita_no_auth(self):
        """GET /api/kpi/marginalita should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/marginalita")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/marginalita returns 401 without auth")
    
    def test_ritardi_fornitori_no_auth(self):
        """GET /api/kpi/ritardi-fornitori should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/ritardi-fornitori")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/ritardi-fornitori returns 401 without auth")
    
    def test_tempi_medi_no_auth(self):
        """GET /api/kpi/tempi-medi should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/kpi/tempi-medi")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/kpi/tempi-medi returns 401 without auth")


@pytest.fixture(scope="module")
def auth_session():
    """Create test user and session for authenticated tests"""
    import subprocess
    import json
    
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f"test-kpi-user-{timestamp}"
    session_token = f"test_kpi_session_{timestamp}"
    
    # Create test user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.kpi.{timestamp}@example.com',
        name: 'Test KPI User',
        role: 'admin',
        picture: 'https://via.placeholder.com/150',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print('OK');
    """
    
    result = subprocess.run(
        ['mongosh', '--quiet', '--eval', mongo_script],
        capture_output=True, text=True
    )
    
    if 'OK' not in result.stdout:
        pytest.skip(f"Failed to create test user: {result.stderr}")
    
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    })
    
    yield {
        "session": session,
        "user_id": user_id,
        "session_token": session_token
    }
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    print('CLEANED');
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


class TestKPIOverviewEndpoint:
    """Test GET /api/kpi/overview endpoint"""
    
    def test_overview_with_auth(self, auth_session):
        """GET /api/kpi/overview should return 200 with counts and totals"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/overview")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "commesse_totali" in data, "Missing commesse_totali"
        assert "commesse_chiuse" in data, "Missing commesse_chiuse"
        assert "preventivi_totali" in data, "Missing preventivi_totali"
        assert "preventivi_predittivi" in data, "Missing preventivi_predittivi"
        assert "fatture_emesse" in data, "Missing fatture_emesse"
        assert "fatturato_totale" in data, "Missing fatturato_totale"
        assert "cl_attivi" in data, "Missing cl_attivi"
        assert "cl_totali" in data, "Missing cl_totali"
        
        # Verify data types
        assert isinstance(data["commesse_totali"], int), "commesse_totali should be int"
        assert isinstance(data["fatturato_totale"], (int, float)), "fatturato_totale should be numeric"
        
        print(f"✓ GET /api/kpi/overview returns 200 with valid structure")
        print(f"  - commesse_totali: {data['commesse_totali']}")
        print(f"  - fatturato_totale: {data['fatturato_totale']}")


class TestKPIAccuracyScoreEndpoint:
    """Test GET /api/kpi/accuracy-score endpoint"""
    
    def test_accuracy_score_with_auth(self, auth_session):
        """GET /api/kpi/accuracy-score should return 200 with score and confronti"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/accuracy-score")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "score_globale" in data, "Missing score_globale"
        assert "score_ore" in data, "Missing score_ore"
        assert "score_costi" in data, "Missing score_costi"
        assert "commesse_analizzate" in data, "Missing commesse_analizzate"
        assert "commesse_con_dati_ore" in data, "Missing commesse_con_dati_ore"
        assert "commesse_con_dati_costi" in data, "Missing commesse_con_dati_costi"
        assert "top_scostamenti" in data, "Missing top_scostamenti"
        assert "confronti" in data, "Missing confronti"
        
        # Verify confronti is an array
        assert isinstance(data["confronti"], list), "confronti should be a list"
        
        # Verify top_scostamenti is an array
        assert isinstance(data["top_scostamenti"], list), "top_scostamenti should be a list"
        
        # score_globale can be null if no data
        if data["score_globale"] is not None:
            assert isinstance(data["score_globale"], (int, float)), "score_globale should be numeric"
            assert 0 <= data["score_globale"] <= 100, "score_globale should be 0-100"
        
        print(f"✓ GET /api/kpi/accuracy-score returns 200 with valid structure")
        print(f"  - score_globale: {data['score_globale']}")
        print(f"  - commesse_analizzate: {data['commesse_analizzate']}")
        print(f"  - confronti count: {len(data['confronti'])}")


class TestKPITrendAccuracyEndpoint:
    """Test GET /api/kpi/trend-accuracy endpoint"""
    
    def test_trend_accuracy_with_auth(self, auth_session):
        """GET /api/kpi/trend-accuracy should return 200 with trend array"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/trend-accuracy")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "trend" in data, "Missing trend"
        assert isinstance(data["trend"], list), "trend should be a list"
        
        # If there's trend data, verify structure
        if len(data["trend"]) > 0:
            item = data["trend"][0]
            assert "mese" in item, "Missing mese in trend item"
            assert "accuracy" in item, "Missing accuracy in trend item"
            assert "commesse" in item, "Missing commesse in trend item"
        
        print(f"✓ GET /api/kpi/trend-accuracy returns 200 with valid structure")
        print(f"  - trend count: {len(data['trend'])}")


class TestKPIMarginalitaEndpoint:
    """Test GET /api/kpi/marginalita endpoint"""
    
    def test_marginalita_with_auth(self, auth_session):
        """GET /api/kpi/marginalita should return 200 with commesse margins"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/marginalita")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "commesse" in data, "Missing commesse"
        assert isinstance(data["commesse"], list), "commesse should be a list"
        
        # If there's data, verify structure
        if len(data["commesse"]) > 0:
            item = data["commesse"][0]
            assert "commessa_id" in item, "Missing commessa_id"
            assert "numero" in item, "Missing numero"
            assert "importo" in item, "Missing importo"
            assert "costo_manodopera" in item, "Missing costo_manodopera"
            assert "costo_materiali" in item, "Missing costo_materiali"
            assert "costo_totale" in item, "Missing costo_totale"
            assert "margine" in item, "Missing margine"
            assert "margine_pct" in item, "Missing margine_pct"
        
        print(f"✓ GET /api/kpi/marginalita returns 200 with valid structure")
        print(f"  - commesse count: {len(data['commesse'])}")


class TestKPIRitardiFornitoriEndpoint:
    """Test GET /api/kpi/ritardi-fornitori endpoint"""
    
    def test_ritardi_fornitori_with_auth(self, auth_session):
        """GET /api/kpi/ritardi-fornitori should return 200 with fornitori stats"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/ritardi-fornitori")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "fornitori" in data, "Missing fornitori"
        assert isinstance(data["fornitori"], list), "fornitori should be a list"
        
        # If there's data, verify structure
        if len(data["fornitori"]) > 0:
            item = data["fornitori"][0]
            assert "fornitore" in item, "Missing fornitore"
            assert "totali" in item, "Missing totali"
            assert "rientrati" in item, "Missing rientrati"
            assert "in_corso" in item, "Missing in_corso"
            assert "giorni_medi" in item, "Missing giorni_medi"
            assert "tipi" in item, "Missing tipi"
        
        print(f"✓ GET /api/kpi/ritardi-fornitori returns 200 with valid structure")
        print(f"  - fornitori count: {len(data['fornitori'])}")


class TestKPITempiMediEndpoint:
    """Test GET /api/kpi/tempi-medi endpoint"""
    
    def test_tempi_medi_with_auth(self, auth_session):
        """GET /api/kpi/tempi-medi should return 200 with tipologie"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/tempi-medi")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "tipologie" in data, "Missing tipologie"
        assert isinstance(data["tipologie"], dict), "tipologie should be a dict"
        
        # If there's data, verify structure
        for tip_name, tip_data in data["tipologie"].items():
            assert "ore_per_ton" in tip_data, f"Missing ore_per_ton in {tip_name}"
            assert "commesse_count" in tip_data, f"Missing commesse_count in {tip_name}"
            assert "ore_totali" in tip_data, f"Missing ore_totali in {tip_name}"
            assert "peso_totale_kg" in tip_data, f"Missing peso_totale_kg in {tip_name}"
        
        print(f"✓ GET /api/kpi/tempi-medi returns 200 with valid structure")
        print(f"  - tipologie: {list(data['tipologie'].keys())}")


class TestKPIDataIntegrity:
    """Test data integrity and edge cases"""
    
    def test_overview_no_mongodb_id(self, auth_session):
        """Verify overview response doesn't contain MongoDB _id"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/overview")
        assert response.status_code == 200
        data = response.json()
        assert "_id" not in data, "Response should not contain _id"
        print("✓ Overview response excludes _id")
    
    def test_accuracy_score_no_mongodb_id(self, auth_session):
        """Verify accuracy-score response doesn't contain MongoDB _id"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/accuracy-score")
        assert response.status_code == 200
        data = response.json()
        assert "_id" not in data, "Response should not contain _id"
        for item in data.get("confronti", []):
            assert "_id" not in item, "Confronti items should not contain _id"
        print("✓ Accuracy-score response excludes _id")
    
    def test_marginalita_no_mongodb_id(self, auth_session):
        """Verify marginalita response doesn't contain MongoDB _id"""
        response = auth_session["session"].get(f"{BASE_URL}/api/kpi/marginalita")
        assert response.status_code == 200
        data = response.json()
        assert "_id" not in data, "Response should not contain _id"
        for item in data.get("commesse", []):
            assert "_id" not in item, "Commesse items should not contain _id"
        print("✓ Marginalita response excludes _id")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

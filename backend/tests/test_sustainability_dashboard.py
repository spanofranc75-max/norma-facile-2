"""
Test suite for Sustainability Dashboard - Iteration 66
Tests new KPIs: alberi_equivalenti, indice_economia_circolare, co2_per_commessa, trend_mensile
Verifies CO2 calculations: CO2 saved = peso_riciclato_kg / 1000 * (2.33 - 0.67)
                          alberi_equivalenti = co2_risparmiata_kg / 22
"""
import pytest
import requests
import os
import time
import subprocess

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = None
USER_ID = None
CREATED_LOTTI = []


@pytest.fixture(scope="module", autouse=True)
def setup_test_session():
    """Create test user and session for authenticated tests."""
    global SESSION_TOKEN, USER_ID
    
    ts = int(time.time() * 1000)
    
    result = subprocess.run([
        "mongosh", "--eval", f"""
        use('test_database');
        var userId = 'test-sustainability-{ts}';
        var sessionToken = 'test_session_sustain_{ts}';
        db.users.insertOne({{
            user_id: userId,
            email: 'test.sustainability.{ts}@example.com',
            name: 'Test Sustainability User',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: userId,
            session_token: sessionToken,
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        print('SESSION=' + sessionToken);
        print('USERID=' + userId);
        """
    ], capture_output=True, text=True)
    
    for line in result.stdout.split('\n'):
        if line.startswith('SESSION='):
            SESSION_TOKEN = line.split('=')[1]
        elif line.startswith('USERID='):
            USER_ID = line.split('=')[1]
    
    yield
    
    # Cleanup
    for lotto_id in CREATED_LOTTI:
        requests.delete(
            f"{BASE_URL}/api/cam/lotti/{lotto_id}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
    
    subprocess.run([
        "mongosh", "--eval", f"""
        use('test_database');
        db.users.deleteOne({{user_id: '{USER_ID}'}});
        db.user_sessions.deleteOne({{session_token: '{SESSION_TOKEN}'}});
        db.lotti_cam.deleteMany({{user_id: '{USER_ID}'}});
        """
    ], capture_output=True)


class TestSustainabilityDashboardNewFields:
    """Test new sustainability KPI fields in /api/cam/report-aziendale response."""
    
    @pytest.fixture(autouse=True)
    def create_test_lotti(self):
        """Create test CAM lotti with known values for calculation verification."""
        global CREATED_LOTTI
        
        # Lotto 1: 1000kg, 80% recycled (800kg recycled)
        # CO2 saved = 800/1000 * (2.33 - 0.67) = 0.8 * 1.66 = 1.328 tCO2 = 1328 kg
        # Alberi = 1328 / 22 = 60.36
        response1 = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_Sustain_Lotto_1",
                "peso_kg": 1000,
                "percentuale_riciclato": 80,
                "metodo_produttivo": "forno_elettrico_non_legato",
                "tipo_certificazione": "epd",
                "commessa_id": "TEST_sustain_comm_001",
                "fornitore": "TEST_Acciaieria_Verde",
                "uso_strutturale": True
            }
        )
        assert response1.status_code == 200
        lotto1_id = response1.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto1_id)
        
        # Lotto 2: 500kg, 60% recycled (300kg recycled)
        # CO2 saved = 300/1000 * (2.33 - 0.67) = 0.3 * 1.66 = 0.498 tCO2 = 498 kg
        response2 = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_Sustain_Lotto_2",
                "peso_kg": 500,
                "percentuale_riciclato": 60,
                "metodo_produttivo": "forno_elettrico_legato",
                "tipo_certificazione": "dichiarazione_produttore",
                "commessa_id": "TEST_sustain_comm_002",
                "fornitore": "TEST_Acciaieria_Verde",
                "uso_strutturale": True
            }
        )
        assert response2.status_code == 200
        lotto2_id = response2.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto2_id)
        
        yield
    
    def test_report_contains_alberi_equivalenti(self):
        """Response contains alberi_equivalenti field."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "alberi_equivalenti" in data
        assert isinstance(data["alberi_equivalenti"], (int, float))
        print(f"alberi_equivalenti: {data['alberi_equivalenti']}")
    
    def test_report_contains_indice_economia_circolare(self):
        """Response contains indice_economia_circolare field."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "indice_economia_circolare" in data
        assert isinstance(data["indice_economia_circolare"], (int, float))
        assert 0 <= data["indice_economia_circolare"] <= 100  # percentage
        print(f"indice_economia_circolare: {data['indice_economia_circolare']}%")
    
    def test_report_contains_co2_per_commessa(self):
        """Response contains co2_per_commessa array."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "co2_per_commessa" in data
        assert isinstance(data["co2_per_commessa"], list)
        
        # Verify structure of each item
        for item in data["co2_per_commessa"]:
            assert "commessa_id" in item
            assert "numero" in item
            assert "co2_risparmiata_kg" in item
            assert "peso_kg" in item
        
        print(f"co2_per_commessa count: {len(data['co2_per_commessa'])}")
    
    def test_report_contains_trend_mensile(self):
        """Response contains trend_mensile array."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "trend_mensile" in data
        assert isinstance(data["trend_mensile"], list)
        
        # Verify structure of each item
        for item in data["trend_mensile"]:
            assert "mese" in item
            assert "peso_kg" in item
            assert "peso_riciclato_kg" in item
            assert "co2_risparmiata_kg" in item
        
        print(f"trend_mensile count: {len(data['trend_mensile'])}")


class TestCO2CalculationFormula:
    """Verify CO2 calculation formulas match specification."""
    
    @pytest.fixture(autouse=True)
    def create_precise_test_data(self):
        """Create lotto with known values for exact calculation verification."""
        global CREATED_LOTTI
        
        # Create exact test: 1000kg, 100% recycled
        # CO2 saved = 1000/1000 * (2.33 - 0.67) = 1.0 * 1.66 = 1.66 tCO2 = 1660 kg
        response = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_CO2_Formula_100pct",
                "peso_kg": 1000,
                "percentuale_riciclato": 100,
                "metodo_produttivo": "forno_elettrico_non_legato",
                "tipo_certificazione": "epd",
                "commessa_id": "TEST_co2_formula_comm",
                "fornitore": "TEST_Acciaieria_CO2",
                "uso_strutturale": True
            }
        )
        assert response.status_code == 200
        lotto_id = response.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto_id)
        yield
    
    def test_co2_saved_formula(self):
        """CO2 saved = peso_riciclato_kg / 1000 * (2.33 - 0.67)."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Get actual values
        peso_riciclato_kg = data["peso_riciclato_kg"]
        co2_saved_kg = data["co2"]["co2_risparmiata_kg"]
        
        # Expected CO2 saved using formula: peso_riciclato_kg / 1000 * (2.33 - 0.67)
        BOF_FACTOR = 2.33
        EAF_FACTOR = 0.67
        expected_co2_saved_t = (peso_riciclato_kg / 1000) * (BOF_FACTOR - EAF_FACTOR)
        expected_co2_saved_kg = expected_co2_saved_t * 1000
        
        # Allow small floating point tolerance
        assert abs(co2_saved_kg - expected_co2_saved_kg) < 1, \
            f"CO2 mismatch: actual={co2_saved_kg}, expected={expected_co2_saved_kg}"
        print(f"CO2 formula verified: {peso_riciclato_kg}kg recycled -> {co2_saved_kg}kg CO2 saved")
    
    def test_alberi_equivalenti_formula(self):
        """alberi_equivalenti = co2_risparmiata_kg / 22."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        co2_saved_kg = data["co2"]["co2_risparmiata_kg"]
        alberi = data["alberi_equivalenti"]
        
        # Expected: co2_saved_kg / 22
        expected_alberi = co2_saved_kg / 22
        
        # Allow tolerance for rounding
        assert abs(alberi - expected_alberi) < 0.5, \
            f"Alberi mismatch: actual={alberi}, expected={expected_alberi}"
        print(f"Alberi formula verified: {co2_saved_kg}kg CO2 / 22 = {alberi} alberi")
    
    def test_indice_economia_circolare_equals_percentuale_media(self):
        """indice_economia_circolare should equal percentuale_riciclato_media."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        perc_media = data["percentuale_riciclato_media"]
        indice = data["indice_economia_circolare"]
        
        assert abs(indice - perc_media) < 0.1, \
            f"Indice mismatch: indice={indice}, perc_media={perc_media}"
        print(f"Indice economia circolare verified: {indice}%")


class TestReportAziendalePDFEndpoint:
    """Test PDF generation still works after sustainability dashboard update."""
    
    def test_pdf_endpoint_returns_pdf_or_400(self):
        """GET /api/cam/report-aziendale/pdf?anno=2026 returns valid PDF or 400 for no data."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        if response.status_code == 200:
            # Check it's a PDF
            assert response.headers.get("content-type") == "application/pdf"
            assert response.content[:5] == b'%PDF-'
            print("PDF generation successful")
        elif response.status_code == 400:
            # No data is acceptable
            assert "nessun dato" in response.json().get("detail", "").lower()
            print("PDF returned 400 (no data) - acceptable")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_pdf_endpoint_requires_auth(self):
        """PDF endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=2026")
        assert response.status_code == 401


class TestEmptyStateSustainability:
    """Test sustainability fields in empty state (no CAM data)."""
    
    def test_empty_state_has_sustainability_fields(self):
        """Empty report (no data for year) still has all sustainability fields."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=1990",  # Old year = no data
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all new fields exist even with no data
        assert "alberi_equivalenti" in data
        assert "indice_economia_circolare" in data
        assert "co2_per_commessa" in data
        assert "trend_mensile" in data
        
        # Values should be zero/empty
        assert data["alberi_equivalenti"] == 0
        assert data["indice_economia_circolare"] == 0
        assert data["co2_per_commessa"] == []
        assert data["trend_mensile"] == []
        print("Empty state sustainability fields verified")

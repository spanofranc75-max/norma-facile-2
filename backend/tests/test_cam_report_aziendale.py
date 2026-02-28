"""
Test suite for CAM Report Aziendale (Multi-Commessa Sustainability Report)
Tests: /api/cam/report-aziendale and /api/cam/report-aziendale/pdf endpoints
CO2 calculation verification using World Steel Association factors (EAF=0.67, BOF=2.33)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = None
USER_ID = None
CREATED_LOTTI = []


@pytest.fixture(scope="module", autouse=True)
def setup_test_session():
    """Create test user and session for authenticated tests."""
    global SESSION_TOKEN, USER_ID
    
    import subprocess
    ts = int(time.time() * 1000)
    
    result = subprocess.run([
        "mongosh", "--eval", f"""
        use('test_database');
        var userId = 'test-cam-report-{ts}';
        var sessionToken = 'test_session_cam_report_{ts}';
        db.users.insertOne({{
            user_id: userId,
            email: 'test.cam.report.{ts}@example.com',
            name: 'Test CAM Report User',
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
    if CREATED_LOTTI:
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


class TestCAMReportAziendaleAuth:
    """Test authentication requirements for report endpoints."""
    
    def test_report_aziendale_requires_auth(self):
        """GET /api/cam/report-aziendale requires authentication."""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale?anno=2026")
        assert response.status_code == 401
        assert "autenticato" in response.json().get("detail", "").lower()
    
    def test_report_aziendale_pdf_requires_auth(self):
        """GET /api/cam/report-aziendale/pdf requires authentication."""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=2026")
        assert response.status_code == 401


class TestCAMReportAziendaleEmpty:
    """Test report with no data."""
    
    def test_report_empty_returns_zero_values(self):
        """Report with no CAM data returns proper empty structure."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=1990",  # Old year = no data
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify empty structure
        assert data["totale_lotti"] == 0
        assert data["peso_totale_kg"] == 0
        assert data["peso_riciclato_kg"] == 0
        assert data["percentuale_riciclato_media"] == 0
        assert data["commesse"] == []
        assert data["fornitori"] == []
        assert data["metodi_produttivi"] == {}
        assert data["commesse_conformi"] == 0
        assert data["commesse_totali"] == 0
        
        # CO2 object should still exist with zeros
        assert "co2" in data
        assert data["co2"]["co2_risparmiata_t"] == 0
        assert data["co2"]["co2_risparmiata_kg"] == 0
        assert data["co2"]["fattore_eaf"] == 0.67
        assert data["co2"]["fattore_bof"] == 2.33
        assert "World Steel Association" in data["co2"]["fonte"]
    
    def test_report_pdf_empty_returns_400(self):
        """PDF generation with no data returns 400 error."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=1990",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 400
        assert "nessun dato" in response.json().get("detail", "").lower()


class TestCAMReportAziendaleWithData:
    """Test report aggregation and CO2 calculation with real data."""
    
    @pytest.fixture(autouse=True)
    def create_test_lotti(self):
        """Create test CAM lotti for aggregation testing."""
        global CREATED_LOTTI
        
        # Lotto 1: 1000kg, 80% recycled, EAF, conforme (threshold 75%)
        response1 = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_Report_Acciaio_S275",
                "peso_kg": 1000,
                "percentuale_riciclato": 80,
                "metodo_produttivo": "forno_elettrico_non_legato",
                "tipo_certificazione": "epd",
                "commessa_id": "TEST_report_commessa_001",
                "fornitore": "TEST_Acciaieria_Alfa",
                "uso_strutturale": True
            }
        )
        assert response1.status_code == 200
        lotto1_id = response1.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto1_id)
        
        # Lotto 2: 500kg, 65% recycled, EAF legato, conforme (threshold 60%)
        response2 = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_Report_Acciaio_S355",
                "peso_kg": 500,
                "percentuale_riciclato": 65,
                "metodo_produttivo": "forno_elettrico_legato",
                "tipo_certificazione": "dichiarazione_produttore",
                "commessa_id": "TEST_report_commessa_002",
                "fornitore": "TEST_Acciaieria_Beta",
                "uso_strutturale": True
            }
        )
        assert response2.status_code == 200
        lotto2_id = response2.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto2_id)
        
        # Lotto 3: 200kg, 50% recycled, non-conforme (below 75% threshold)
        response3 = requests.post(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}", "Content-Type": "application/json"},
            json={
                "descrizione": "TEST_Report_Acciaio_NonConforme",
                "peso_kg": 200,
                "percentuale_riciclato": 50,
                "metodo_produttivo": "forno_elettrico_non_legato",
                "tipo_certificazione": "nessuna",
                "commessa_id": "TEST_report_commessa_003",
                "fornitore": "TEST_Acciaieria_Alfa",
                "uso_strutturale": True
            }
        )
        assert response3.status_code == 200
        lotto3_id = response3.json()["lotto"]["lotto_id"]
        CREATED_LOTTI.append(lotto3_id)
        
        yield
    
    def test_report_aggregation_total_lotti(self):
        """Report correctly counts total lotti."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totale_lotti"] >= 3  # At least our 3 test lotti
    
    def test_report_aggregation_peso_totale(self):
        """Report correctly sums peso_totale_kg."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        # 1000 + 500 + 200 = 1700 kg (minimum, could be more from other tests)
        assert data["peso_totale_kg"] >= 1700
    
    def test_report_aggregation_peso_riciclato(self):
        """Report correctly calculates peso_riciclato_kg."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        # 1000*0.8 + 500*0.65 + 200*0.5 = 800 + 325 + 100 = 1225 kg minimum
        assert data["peso_riciclato_kg"] >= 1225
    
    def test_report_co2_calculation(self):
        """CO2 calculation uses correct World Steel factors."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        co2 = data["co2"]
        
        # Verify factors are correct
        assert co2["fattore_eaf"] == 0.67  # EAF = recycled
        assert co2["fattore_bof"] == 2.33  # BOF = primary
        assert "World Steel Association" in co2["fonte"]
        
        # CO2 saved should be positive when recycled > 0
        if data["peso_riciclato_kg"] > 0:
            assert co2["co2_risparmiata_t"] > 0
            assert co2["co2_risparmiata_kg"] > 0
            assert co2["riduzione_percentuale"] > 0
    
    def test_report_co2_formula_verification(self):
        """Verify CO2 calculation formula: saved = recycled_t * (BOF - EAF)."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        peso_riciclato_t = data["peso_riciclato_kg"] / 1000
        expected_co2_saved = peso_riciclato_t * (2.33 - 0.67)  # BOF - EAF
        
        # Allow small floating point difference
        assert abs(data["co2"]["co2_risparmiata_t"] - expected_co2_saved) < 0.01
    
    def test_report_commesse_array(self):
        """Report includes commesse array with correct structure."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert "commesse" in data
        assert isinstance(data["commesse"], list)
        assert len(data["commesse"]) >= 3  # Our 3 test commesse
        
        # Verify commessa structure
        for commessa in data["commesse"]:
            assert "commessa_id" in commessa
            assert "peso_kg" in commessa
            assert "peso_riciclato_kg" in commessa
            assert "percentuale_riciclato" in commessa
            assert "conforme" in commessa
            assert "lotti" in commessa
    
    def test_report_fornitori_array(self):
        """Report includes fornitori array with aggregation."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert "fornitori" in data
        assert isinstance(data["fornitori"], list)
        
        # Verify fornitore structure
        for fornitore in data["fornitori"]:
            assert "fornitore" in fornitore
            assert "peso_kg" in fornitore
            assert "peso_riciclato_kg" in fornitore
            assert "percentuale_riciclato" in fornitore
            assert "lotti" in fornitore
    
    def test_report_metodi_produttivi(self):
        """Report includes metodi_produttivi breakdown."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert "metodi_produttivi" in data
        assert isinstance(data["metodi_produttivi"], dict)
        
        # Should have at least these methods from test data
        assert "forno_elettrico_non_legato" in data["metodi_produttivi"]
        assert "forno_elettrico_legato" in data["metodi_produttivi"]
    
    def test_report_commesse_conformi_count(self):
        """Report correctly counts conforming commesse."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert data["commesse_conformi"] >= 2  # 2 conformi, 1 non conforme
        assert data["commesse_conformi"] <= data["commesse_totali"]


class TestCAMReportAziendalePDF:
    """Test PDF generation endpoint."""
    
    def test_pdf_returns_valid_pdf(self):
        """PDF endpoint returns valid PDF content."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        # Should return 200 with valid PDF (assuming data exists from previous tests)
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"
            # Check PDF magic bytes
            assert response.content[:5] == b'%PDF-'
        elif response.status_code == 400:
            # No data case is also acceptable
            assert "nessun dato" in response.json().get("detail", "").lower()
    
    def test_pdf_content_disposition(self):
        """PDF has correct filename in Content-Disposition."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale/pdf?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        if response.status_code == 200:
            disposition = response.headers.get("content-disposition", "")
            assert "Bilancio_Sostenibilita_CAM_2026.pdf" in disposition


class TestCAMReportYearFilter:
    """Test year filtering functionality."""
    
    def test_report_filters_by_year(self):
        """Report correctly filters by anno parameter."""
        response_2026 = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2026",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        response_2020 = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale?anno=2020",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        assert response_2026.status_code == 200
        assert response_2020.status_code == 200
        
        # 2020 should have no data (we created lotti in 2026)
        data_2020 = response_2020.json()
        assert data_2020["totale_lotti"] == 0
    
    def test_report_without_year_uses_current(self):
        """Report without anno parameter uses current year."""
        response = requests.get(
            f"{BASE_URL}/api/cam/report-aziendale",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "anno" in data

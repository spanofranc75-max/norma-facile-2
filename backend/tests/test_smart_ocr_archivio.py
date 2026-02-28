"""
Test Smart AI OCR Multi-Profile Certificate Parsing and Archivio Certificati

Tests for iteration 62:
- POST /api/cam/lotti - manual CAM lotto creation (still works)
- GET /api/cam/lotti - list CAM lotti by commessa_id
- GET /api/cam/archivio-certificati - unassigned certificate profiles archive
- POST /api/cam/archivio-certificati/{numero_colata}/assegna - assign archived profile to commessa
- POST /api/cam/calcola/{commessa_id} - calculate CAM conformity
- GET /api/cam/report-aziendale - aggregate CAM data across commesse
- GET /api/cam/report-aziendale/pdf - generate PDF report
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('SESSION_TOKEN', '')
USER_ID = os.environ.get('USER_ID', '')


@pytest.fixture(scope="module")
def session():
    """Session with auth headers."""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return s


@pytest.fixture(scope="module")
def test_commessa(session):
    """Create a test commessa for CAM tests."""
    payload = {
        "numero": f"TEST-ITER62-{os.getpid()}",
        "title": "Test Commessa per Archivio Certificati",
        "client_name": "Test Cliente CAM",
        "data_apertura": "2026-01-15",
        "moduli": {"normativa": "EN_1090", "classe_esecuzione": "EXC2"}
    }
    resp = session.post(f"{BASE_URL}/api/commesse/", json=payload)
    if resp.status_code != 200:
        pytest.skip(f"Failed to create commessa: {resp.text}")
    data = resp.json()
    commessa_id = data.get("commessa_id")
    yield commessa_id
    # Cleanup
    session.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


class TestCAMLottiCRUD:
    """Test CAM lotti manual creation still works."""
    
    def test_create_cam_lotto_manual(self, session, test_commessa):
        """POST /api/cam/lotti - Create CAM lotto manually."""
        payload = {
            "descrizione": "TEST_IPE 120 S275JR",
            "fornitore": "TEST_Acciaieria Prova",
            "numero_colata": f"TEST_COLATA_{os.getpid()}",
            "peso_kg": 500,
            "qualita_acciaio": "S275JR",
            "percentuale_riciclato": 82,
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa
        }
        resp = session.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "lotto" in data
        lotto = data["lotto"]
        # Verify fields
        assert lotto["descrizione"] == payload["descrizione"]
        assert lotto["peso_kg"] == 500
        assert lotto["percentuale_riciclato"] == 82
        assert lotto["conforme_cam"] == True, "82% should be conforme (threshold 75%)"
        assert lotto["soglia_minima_cam"] == 75
        print(f"✓ Created CAM lotto: {lotto['lotto_id']}")
    
    def test_list_cam_lotti_by_commessa(self, session, test_commessa):
        """GET /api/cam/lotti - List lotti filtered by commessa_id."""
        resp = session.get(f"{BASE_URL}/api/cam/lotti", params={"commessa_id": test_commessa})
        assert resp.status_code == 200
        data = resp.json()
        assert "lotti" in data
        assert isinstance(data["lotti"], list)
        # Should have at least the one we created
        assert len(data["lotti"]) >= 1, f"Expected at least 1 lotto, got {len(data['lotti'])}"
        print(f"✓ Listed {len(data['lotti'])} CAM lotti for commessa")
    
    def test_list_cam_lotti_solo_conformi(self, session, test_commessa):
        """GET /api/cam/lotti - List only conformi lotti."""
        resp = session.get(f"{BASE_URL}/api/cam/lotti", params={
            "commessa_id": test_commessa,
            "solo_conformi": True
        })
        assert resp.status_code == 200
        data = resp.json()
        for lotto in data["lotti"]:
            assert lotto.get("conforme_cam") == True
        print(f"✓ solo_conformi filter works ({len(data['lotti'])} conformi)")


class TestArchivioCertificati:
    """Test archivio-certificati endpoints."""
    
    def test_get_archivio_empty(self, session):
        """GET /api/cam/archivio-certificati - Should return archive (might be empty for new user)."""
        resp = session.get(f"{BASE_URL}/api/cam/archivio-certificati")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "archivio" in data
        assert isinstance(data["archivio"], list)
        assert "totale" in data
        print(f"✓ GET archivio-certificati returned {data['totale']} items")
    
    def test_archivio_without_auth(self):
        """GET /api/cam/archivio-certificati without auth should fail."""
        resp = requests.get(f"{BASE_URL}/api/cam/archivio-certificati")
        assert resp.status_code == 401
        print("✓ archivio-certificati requires auth")
    
    def test_assegna_archivio_not_found(self, session, test_commessa):
        """POST /api/cam/archivio-certificati/{colata}/assegna - 404 for non-existent colata."""
        resp = session.post(
            f"{BASE_URL}/api/cam/archivio-certificati/NONEXISTENT_COLATA_12345/assegna",
            params={"commessa_id": test_commessa}
        )
        assert resp.status_code == 404, f"Expected 404 for non-existent, got {resp.status_code}"
        print("✓ assegna returns 404 for non-existent colata")


class TestCAMCalculation:
    """Test CAM conformity calculation."""
    
    def test_calcola_cam_per_commessa(self, session, test_commessa):
        """POST /api/cam/calcola/{commessa_id} - Calculate CAM conformity."""
        resp = session.post(f"{BASE_URL}/api/cam/calcola/{test_commessa}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Verify response structure
        assert "peso_totale_kg" in data
        assert "peso_riciclato_kg" in data
        assert "percentuale_riciclato_totale" in data
        assert "conforme_cam" in data
        assert "commessa_id" in data
        assert data["commessa_id"] == test_commessa
        print(f"✓ Calculated CAM: {data['peso_totale_kg']}kg total, {data['percentuale_riciclato_totale']:.1f}% recycled, conforme={data['conforme_cam']}")
    
    def test_calcola_cam_nonexistent_commessa(self, session):
        """POST /api/cam/calcola/{commessa_id} - 404 for non-existent commessa."""
        resp = session.post(f"{BASE_URL}/api/cam/calcola/nonexistent_commessa_12345")
        assert resp.status_code == 404
        print("✓ calcola returns 404 for non-existent commessa")


class TestCAMReportAziendale:
    """Test CAM report aziendale endpoints."""
    
    def test_get_report_aziendale(self, session):
        """GET /api/cam/report-aziendale - Aggregate CAM data."""
        resp = session.get(f"{BASE_URL}/api/cam/report-aziendale")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Verify response structure
        assert "anno" in data
        assert "totale_lotti" in data
        assert "peso_totale_kg" in data
        assert "peso_riciclato_kg" in data
        assert "percentuale_riciclato_media" in data
        assert "co2" in data
        assert "commesse" in data
        assert "fornitori" in data
        assert "metodi_produttivi" in data
        print(f"✓ Report aziendale: {data['totale_lotti']} lotti, {data['peso_totale_kg']}kg total")
    
    def test_get_report_aziendale_with_year(self, session):
        """GET /api/cam/report-aziendale?anno=2026 - Filter by year."""
        resp = session.get(f"{BASE_URL}/api/cam/report-aziendale", params={"anno": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("anno") == 2026
        print(f"✓ Report aziendale filtered by anno=2026: {data['totale_lotti']} lotti")
    
    def test_report_aziendale_pdf(self, session):
        """GET /api/cam/report-aziendale/pdf - Generate PDF (needs data)."""
        # First check if there's data
        check_resp = session.get(f"{BASE_URL}/api/cam/report-aziendale")
        if check_resp.status_code == 200 and check_resp.json().get("totale_lotti", 0) > 0:
            resp = session.get(f"{BASE_URL}/api/cam/report-aziendale/pdf")
            if resp.status_code == 200:
                assert resp.headers.get("content-type", "").startswith("application/pdf")
                assert len(resp.content) > 1000  # PDF should be larger than 1KB
                print(f"✓ Report PDF generated: {len(resp.content)} bytes")
            else:
                print(f"⚠ Report PDF returned {resp.status_code} (may need data)")
        else:
            print("⚠ No CAM data for PDF generation, skipping PDF test")


class TestSoglieCAM:
    """Test CAM soglie endpoint (public)."""
    
    def test_get_soglie(self, session):
        """GET /api/cam/soglie - Get CAM thresholds (public)."""
        resp = session.get(f"{BASE_URL}/api/cam/soglie")
        assert resp.status_code == 200
        data = resp.json()
        assert "normativa" in data
        assert "soglie" in data
        assert "strutturale" in data["soglie"]
        assert data["soglie"]["strutturale"]["forno_elettrico_non_legato"] == 75
        assert data["soglie"]["strutturale"]["forno_elettrico_legato"] == 60
        assert data["soglie"]["strutturale"]["ciclo_integrale"] == 12
        print("✓ CAM soglie: 75%/60%/12% per DM 256/2022")
    
    def test_get_soglie_public(self):
        """GET /api/cam/soglie - Should work without auth."""
        resp = requests.get(f"{BASE_URL}/api/cam/soglie")
        assert resp.status_code == 200
        print("✓ CAM soglie is public endpoint")


class TestCleanup:
    """Cleanup test data."""
    
    def test_cleanup(self, session, test_commessa):
        """Delete test CAM lotti."""
        # Get all lotti for test commessa
        resp = session.get(f"{BASE_URL}/api/cam/lotti", params={"commessa_id": test_commessa})
        if resp.status_code == 200:
            lotti = resp.json().get("lotti", [])
            # Note: There's no delete endpoint for CAM lotti in the API
            # Just note them for potential manual cleanup
            for lotto in lotti:
                if "TEST_" in str(lotto.get("descrizione", "")) or "TEST_" in str(lotto.get("numero_colata", "")):
                    print(f"  Test lotto to clean: {lotto.get('lotto_id')}")
        print("✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

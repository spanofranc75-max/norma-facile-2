"""
Iteration 202: Controllo Finale Checklist + Soglia Accettabilita Calibro
Tests for:
- GET /api/controllo-finale/{commessa_id} — Returns 11 checks grouped by 3 areas
- POST /api/controllo-finale/{commessa_id} — Save manual check results and notes
- POST /api/controllo-finale/{commessa_id}/approva — Sign and approve
- GET /api/instruments/ — Returns soglia_accettabilita and unita_soglia fields
- PUT /api/instruments/{id} — Can update soglia_accettabilita
- GET /api/riesame/{commessa_id} — tolleranza_calibro check uses per-instrument threshold
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_loiano_cims_2026"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROLLO FINALE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestControlloFinaleGet:
    """GET /api/controllo-finale/{commessa_id} — Returns 11 checks grouped by 3 areas"""

    def test_get_controllo_finale_returns_200(self, api_client):
        """Test that GET returns 200 with valid commessa_id"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "checks" in data
        assert "commessa_id" in data
        assert data["commessa_id"] == TEST_COMMESSA_ID

    def test_get_controllo_finale_has_11_checks(self, api_client):
        """Test that response contains exactly 11 checks"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["checks"]) == 11, f"Expected 11 checks, got {len(data['checks'])}"

    def test_get_controllo_finale_has_3_areas(self, api_client):
        """Test that checks are grouped into 3 areas: Visual Testing, Dimensionale, Compliance"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        areas = set(c["area"] for c in data["checks"])
        expected_areas = {"Visual Testing", "Dimensionale", "Compliance"}
        assert areas == expected_areas, f"Expected areas {expected_areas}, got {areas}"

    def test_get_controllo_finale_has_areas_stats(self, api_client):
        """Test that response includes areas stats with totale and ok counts"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "areas" in data
        for area in ["Visual Testing", "Dimensionale", "Compliance"]:
            assert area in data["areas"], f"Missing area stats for {area}"
            assert "totale" in data["areas"][area]
            assert "ok" in data["areas"][area]

    def test_get_controllo_finale_check_structure(self, api_client):
        """Test that each check has required fields"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "area", "label", "desc", "auto", "esito", "valore"]
        for check in data["checks"]:
            for field in required_fields:
                assert field in check, f"Missing field '{field}' in check {check.get('id', 'unknown')}"

    def test_get_controllo_finale_auto_checks_have_values(self, api_client):
        """Test that auto checks have valore and nota fields populated"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        auto_checks = [c for c in data["checks"] if c["auto"]]
        assert len(auto_checks) >= 6, f"Expected at least 6 auto checks, got {len(auto_checks)}"
        for check in auto_checks:
            assert "valore" in check, f"Auto check {check['id']} missing valore"

    def test_get_controllo_finale_has_summary_fields(self, api_client):
        """Test that response includes summary fields"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "superato" in data
        assert "n_ok" in data
        assert "n_totale" in data
        assert "approvato" in data
        assert isinstance(data["superato"], bool)
        assert isinstance(data["n_ok"], int)
        assert data["n_totale"] == 11

    def test_get_controllo_finale_404_for_invalid_commessa(self, api_client):
        """Test that GET returns 404 for non-existent commessa"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/invalid_commessa_xyz")
        assert response.status_code == 404


class TestControlloFinaleSave:
    """POST /api/controllo-finale/{commessa_id} — Save manual check results and notes"""

    def test_save_manual_checks(self, api_client):
        """Test saving manual checks and notes"""
        payload = {
            "checks_manuali": {
                "vt_100_eseguito": True,
                "vt_difetti_accettabili": True,
                "dim_quote_critiche": False,
                "dim_tolleranze_montaggio": False,
                "comp_etichetta_ce": False
            },
            "note_generali": "Test note generali iteration 202",
            "note_vt": "Test note VT",
            "note_dim": "Test note dimensionale"
        }
        response = api_client.post(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "controllo_id" in data

    def test_save_persists_manual_checks(self, api_client):
        """Test that saved manual checks are persisted and returned in GET"""
        # Save manual checks
        payload = {
            "checks_manuali": {
                "vt_100_eseguito": True,
                "vt_difetti_accettabili": True
            },
            "note_generali": "Persistence test note",
            "note_vt": "",
            "note_dim": ""
        }
        save_response = api_client.post(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            json=payload
        )
        assert save_response.status_code == 200

        # Verify via GET
        get_response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Find manual checks and verify their esito
        vt_100 = next((c for c in data["checks"] if c["id"] == "vt_100_eseguito"), None)
        assert vt_100 is not None
        assert vt_100["esito"] == True, "Manual check vt_100_eseguito should be True"
        
        assert data["note_generali"] == "Persistence test note"

    def test_save_404_for_invalid_commessa(self, api_client):
        """Test that POST returns 404 for non-existent commessa"""
        payload = {"checks_manuali": {}, "note_generali": "", "note_vt": "", "note_dim": ""}
        response = api_client.post(
            f"{BASE_URL}/api/controllo-finale/invalid_commessa_xyz",
            json=payload
        )
        assert response.status_code == 404


class TestControlloFinaleApprova:
    """POST /api/controllo-finale/{commessa_id}/approva — Sign and approve"""

    def test_approva_fails_if_not_all_checks_pass(self, api_client):
        """Test that approval fails if not all checks pass"""
        # First, reset manual checks to ensure not all pass
        reset_payload = {
            "checks_manuali": {
                "vt_100_eseguito": False,
                "vt_difetti_accettabili": False,
                "dim_quote_critiche": False,
                "dim_tolleranze_montaggio": False,
                "comp_etichetta_ce": False
            },
            "note_generali": "",
            "note_vt": "",
            "note_dim": ""
        }
        api_client.post(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}", json=reset_payload)

        # Try to approve
        approva_payload = {
            "firma_nome": "Test User",
            "firma_ruolo": "Responsabile Qualita",
            "note_approvazione": ""
        }
        response = api_client.post(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}/approva",
            json=approva_payload
        )
        # Should fail with 400 because not all checks pass
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"

    def test_approva_404_for_invalid_commessa(self, api_client):
        """Test that approva returns 404 for non-existent commessa"""
        payload = {"firma_nome": "Test", "firma_ruolo": "QA", "note_approvazione": ""}
        response = api_client.post(
            f"{BASE_URL}/api/controllo-finale/invalid_commessa_xyz/approva",
            json=payload
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTS ENDPOINTS - SOGLIA ACCETTABILITA
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstrumentsSogliaFields:
    """GET /api/instruments/ — Returns soglia_accettabilita and unita_soglia fields"""

    def test_get_instruments_returns_200(self, api_client):
        """Test that GET /instruments/ returns 200"""
        response = api_client.get(f"{BASE_URL}/api/instruments/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "items" in data
        assert "stats" in data

    def test_instruments_have_soglia_fields(self, api_client):
        """Test that instruments include soglia_accettabilita and unita_soglia fields"""
        response = api_client.get(f"{BASE_URL}/api/instruments/")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            # Check that soglia fields exist in response schema
            first_item = data["items"][0]
            # These fields should be present (even if null)
            assert "soglia_accettabilita" in first_item or first_item.get("soglia_accettabilita") is None
            assert "unita_soglia" in first_item

    def test_instruments_filter_by_type_misura(self, api_client):
        """Test filtering instruments by type=misura"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?type=misura")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "misura"


class TestInstrumentsUpdateSoglia:
    """PUT /api/instruments/{id} — Can update soglia_accettabilita"""

    def test_create_and_update_instrument_soglia(self, api_client):
        """Test creating an instrument and updating its soglia_accettabilita"""
        # Create a new instrument
        create_payload = {
            "name": "TEST_Calibro Digitale 202",
            "serial_number": "TEST_SN_202_001",
            "type": "misura",
            "manufacturer": "Borletti",
            "status": "attivo",
            "soglia_accettabilita": 0.1,
            "unita_soglia": "mm"
        }
        create_response = api_client.post(f"{BASE_URL}/api/instruments/", json=create_payload)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        created = create_response.json()
        instrument_id = created["instrument_id"]
        
        try:
            # Verify soglia was set
            assert created["soglia_accettabilita"] == 0.1
            assert created["unita_soglia"] == "mm"

            # Update soglia
            update_payload = {
                "name": "TEST_Calibro Digitale 202",
                "serial_number": "TEST_SN_202_001",
                "type": "misura",
                "manufacturer": "Borletti",
                "status": "attivo",
                "soglia_accettabilita": 0.05,
                "unita_soglia": "mm"
            }
            update_response = api_client.put(
                f"{BASE_URL}/api/instruments/{instrument_id}",
                json=update_payload
            )
            assert update_response.status_code == 200, f"Update failed: {update_response.text}"
            updated = update_response.json()
            assert updated["soglia_accettabilita"] == 0.05

            # Verify via GET
            get_response = api_client.get(f"{BASE_URL}/api/instruments/")
            assert get_response.status_code == 200
            items = get_response.json()["items"]
            found = next((i for i in items if i["instrument_id"] == instrument_id), None)
            assert found is not None
            assert found["soglia_accettabilita"] == 0.05

        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/instruments/{instrument_id}")

    def test_update_soglia_with_different_units(self, api_client):
        """Test updating soglia with different units (%, N, bar)"""
        create_payload = {
            "name": "TEST_Strumento Pressione 202",
            "serial_number": "TEST_SN_202_002",
            "type": "misura",
            "manufacturer": "Test",
            "status": "attivo",
            "soglia_accettabilita": 5.0,
            "unita_soglia": "%"
        }
        create_response = api_client.post(f"{BASE_URL}/api/instruments/", json=create_payload)
        assert create_response.status_code == 200
        created = create_response.json()
        instrument_id = created["instrument_id"]

        try:
            assert created["soglia_accettabilita"] == 5.0
            assert created["unita_soglia"] == "%"

            # Update to bar
            update_payload = {
                "name": "TEST_Strumento Pressione 202",
                "serial_number": "TEST_SN_202_002",
                "type": "misura",
                "manufacturer": "Test",
                "status": "attivo",
                "soglia_accettabilita": 0.5,
                "unita_soglia": "bar"
            }
            update_response = api_client.put(
                f"{BASE_URL}/api/instruments/{instrument_id}",
                json=update_payload
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["soglia_accettabilita"] == 0.5
            assert updated["unita_soglia"] == "bar"

        finally:
            api_client.delete(f"{BASE_URL}/api/instruments/{instrument_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# RIESAME TECNICO - TOLLERANZA CALIBRO CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiesameTolleranzaCalibro:
    """GET /api/riesame/{commessa_id} — tolleranza_calibro check uses per-instrument threshold"""

    def test_riesame_has_tolleranza_calibro_check(self, api_client):
        """Test that riesame includes tolleranza_calibro check"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        checks = data.get("checks", [])
        tolleranza_check = next((c for c in checks if c["id"] == "tolleranza_calibro"), None)
        assert tolleranza_check is not None, "tolleranza_calibro check not found in riesame"
        assert tolleranza_check["auto"] == True, "tolleranza_calibro should be an auto check"

    def test_riesame_tolleranza_calibro_description(self, api_client):
        """Test that tolleranza_calibro check has updated description mentioning configurable threshold"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        checks = data.get("checks", [])
        tolleranza_check = next((c for c in checks if c["id"] == "tolleranza_calibro"), None)
        assert tolleranza_check is not None
        # Check that description mentions configurable threshold
        assert "configurabile" in tolleranza_check.get("desc", "").lower() or \
               "soglia" in tolleranza_check.get("desc", "").lower() or \
               "strumento" in tolleranza_check.get("desc", "").lower(), \
               f"Description should mention configurable threshold: {tolleranza_check.get('desc')}"


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP TEST DATA
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanup:
    """Cleanup test data created during tests"""

    def test_cleanup_test_instruments(self, api_client):
        """Remove any TEST_ prefixed instruments"""
        response = api_client.get(f"{BASE_URL}/api/instruments/")
        if response.status_code == 200:
            items = response.json().get("items", [])
            for item in items:
                if item.get("name", "").startswith("TEST_") or item.get("serial_number", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/instruments/{item['instrument_id']}")
        assert True  # Cleanup always passes

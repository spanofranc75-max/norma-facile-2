"""
Iteration 201: Registro Saldatura + Link DDT → Lotti FPC (EN 1090 FPC Fase 2)

Tests for:
- GET /api/registro-saldatura/{commessa_id} — List welding log entries
- POST /api/registro-saldatura/{commessa_id} — Add welding log entry
- PUT /api/registro-saldatura/{commessa_id}/{riga_id} — Update welding log entry
- DELETE /api/registro-saldatura/{commessa_id}/{riga_id} — Delete welding log entry
- GET /api/registro-saldatura/{commessa_id}/saldatori-idonei — Get eligible welders by process
- POST /api/fpc/batches/link-ddt/{commessa_id} — Auto-link DDT to FPC batches
- GET /api/fpc/batches/rintracciabilita/{commessa_id} — Get material traceability sheet
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_loiano_cims_2026"
TEST_WELDERS = [
    "wld_022030bdcf",  # Marco Bianchi
    "wld_811fabf3a1",  # Luca Rossi
    "wld_1282360dd4",  # Andrea Verdi
]


@pytest.fixture
def auth_session():
    """Session with authentication cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def no_auth_session():
    """Session without authentication."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestRegistroSaldaturaList:
    """Tests for GET /api/registro-saldatura/{commessa_id}"""

    def test_list_registro_success(self, auth_session):
        """List welding log entries for a commessa."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "righe" in data, "Response should contain 'righe' key"
        assert "stats" in data, "Response should contain 'stats' key"
        assert isinstance(data["righe"], list), "'righe' should be a list"
        
        # Verify stats structure
        stats = data["stats"]
        assert "totale" in stats
        assert "conformi" in stats
        assert "non_conformi" in stats
        assert "da_eseguire" in stats

    def test_list_registro_no_auth(self, no_auth_session):
        """List without auth should return 401."""
        response = no_auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_list_registro_invalid_commessa(self, auth_session):
        """List with invalid commessa should return 404."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/invalid_commessa_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestSaldatoriIdonei:
    """Tests for GET /api/registro-saldatura/{commessa_id}/saldatori-idonei"""

    def test_saldatori_idonei_default_process(self, auth_session):
        """Get eligible welders for default process (135 MIG/MAG)."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "saldatori" in data, "Response should contain 'saldatori' key"
        assert "processo" in data, "Response should contain 'processo' key"
        assert "totale" in data, "Response should contain 'totale' key"
        assert isinstance(data["saldatori"], list), "'saldatori' should be a list"

    def test_saldatori_idonei_process_135(self, auth_session):
        """Get eligible welders for process 135 (MIG/MAG)."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["processo"] == "135", f"Expected processo '135', got '{data['processo']}'"
        
        # Verify welder structure if any welders returned
        if data["saldatori"]:
            welder = data["saldatori"][0]
            assert "welder_id" in welder
            assert "name" in welder

    def test_saldatori_idonei_process_111(self, auth_session):
        """Get eligible welders for process 111 (SMAW)."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=111")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["processo"] == "111"

    def test_saldatori_idonei_process_141(self, auth_session):
        """Get eligible welders for process 141 (TIG)."""
        response = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=141")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["processo"] == "141"

    def test_saldatori_idonei_no_auth(self, no_auth_session):
        """Get welders without auth should return 401."""
        response = no_auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei")
        assert response.status_code == 401


class TestRegistroSaldaturaCRUD:
    """Tests for POST/PUT/DELETE /api/registro-saldatura/{commessa_id}"""

    def test_create_riga_success(self, auth_session):
        """Create a new welding log entry."""
        # First get an eligible welder
        welders_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        welders_data = welders_resp.json()
        
        # Use first available welder or fallback to test welder
        welder_id = welders_data["saldatori"][0]["welder_id"] if welders_data["saldatori"] else TEST_WELDERS[0]
        
        payload = {
            "giunto": "TEST_G1",
            "posizione_dwg": "Pos.1 TEST",
            "saldatore_id": welder_id,
            "wps_id": "",
            "processo": "135",
            "data_esecuzione": "2026-01-15",
            "esito_vt": "da_eseguire",
            "note": "Test entry from iteration 201"
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "riga_id" in data, "Response should contain 'riga_id'"
        assert "message" in data, "Response should contain 'message'"
        assert data["riga_id"].startswith("rs_"), f"riga_id should start with 'rs_', got {data['riga_id']}"
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{data['riga_id']}")
        
        return data["riga_id"]

    def test_create_riga_invalid_welder(self, auth_session):
        """Create entry with invalid welder should return 404."""
        payload = {
            "giunto": "TEST_G2",
            "saldatore_id": "invalid_welder_xyz",
            "processo": "135"
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_update_riga_success(self, auth_session):
        """Update an existing welding log entry."""
        # First get an eligible welder
        welders_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        welders_data = welders_resp.json()
        welder_id = welders_data["saldatori"][0]["welder_id"] if welders_data["saldatori"] else TEST_WELDERS[0]
        
        # Create an entry first
        create_payload = {
            "giunto": "TEST_UPDATE_G1",
            "saldatore_id": welder_id,
            "processo": "135",
            "esito_vt": "da_eseguire"
        }
        
        create_resp = auth_session.post(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}",
            json=create_payload
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        riga_id = create_resp.json()["riga_id"]
        
        # Now update it
        update_payload = {
            "giunto": "TEST_UPDATE_G1_MODIFIED",
            "saldatore_id": welder_id,
            "processo": "135",
            "esito_vt": "conforme",
            "note": "Updated to conforme"
        }
        
        update_resp = auth_session.put(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga_id}",
            json=update_payload
        )
        assert update_resp.status_code == 200, f"Expected 200, got {update_resp.status_code}: {update_resp.text}"
        
        data = update_resp.json()
        assert "message" in data
        assert data["riga_id"] == riga_id
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga_id}")

    def test_update_riga_not_found(self, auth_session):
        """Update non-existent entry should return 404."""
        # First get an eligible welder for valid payload
        welders_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        welders_data = welders_resp.json()
        welder_id = welders_data["saldatori"][0]["welder_id"] if welders_data["saldatori"] else TEST_WELDERS[0]
        
        payload = {
            "giunto": "TEST_G1",
            "saldatore_id": welder_id,
            "processo": "135"
        }
        
        response = auth_session.put(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/rs_nonexistent123",
            json=payload
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_delete_riga_success(self, auth_session):
        """Delete a welding log entry."""
        # First get an eligible welder
        welders_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        welders_data = welders_resp.json()
        welder_id = welders_data["saldatori"][0]["welder_id"] if welders_data["saldatori"] else TEST_WELDERS[0]
        
        # Create an entry first
        create_payload = {
            "giunto": "TEST_DELETE_G1",
            "saldatore_id": welder_id,
            "processo": "135"
        }
        
        create_resp = auth_session.post(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}",
            json=create_payload
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        riga_id = create_resp.json()["riga_id"]
        
        # Now delete it
        delete_resp = auth_session.delete(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga_id}"
        )
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"
        
        data = delete_resp.json()
        assert "message" in data
        
        # Verify it's deleted
        list_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        righe = list_resp.json()["righe"]
        assert not any(r["riga_id"] == riga_id for r in righe), "Deleted entry should not appear in list"

    def test_delete_riga_not_found(self, auth_session):
        """Delete non-existent entry should return 404."""
        response = auth_session.delete(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/rs_nonexistent456"
        )
        assert response.status_code == 404


class TestFPCBatchesLinkDDT:
    """Tests for POST /api/fpc/batches/link-ddt/{commessa_id}"""

    def test_link_ddt_success(self, auth_session):
        """Auto-link DDT to FPC batches."""
        response = auth_session.post(f"{BASE_URL}/api/fpc/batches/link-ddt/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "links" in data, "Response should contain 'links'"
        assert "totale" in data, "Response should contain 'totale'"
        assert isinstance(data["links"], list), "'links' should be a list"

    def test_link_ddt_no_auth(self, no_auth_session):
        """Link DDT without auth should return 401."""
        response = no_auth_session.post(f"{BASE_URL}/api/fpc/batches/link-ddt/{TEST_COMMESSA_ID}")
        assert response.status_code == 401

    def test_link_ddt_invalid_commessa(self, auth_session):
        """Link DDT with invalid commessa should return 404."""
        response = auth_session.post(f"{BASE_URL}/api/fpc/batches/link-ddt/invalid_commessa_xyz")
        assert response.status_code == 404


class TestFPCBatchesRintracciabilita:
    """Tests for GET /api/fpc/batches/rintracciabilita/{commessa_id}"""

    def test_rintracciabilita_success(self, auth_session):
        """Get material traceability sheet."""
        response = auth_session.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa_id" in data, "Response should contain 'commessa_id'"
        assert "righe" in data, "Response should contain 'righe'"
        assert "totale" in data, "Response should contain 'totale'"
        assert "collegati" in data, "Response should contain 'collegati'"
        assert isinstance(data["righe"], list), "'righe' should be a list"
        
        # Verify commessa_id matches
        assert data["commessa_id"] == TEST_COMMESSA_ID

    def test_rintracciabilita_no_auth(self, no_auth_session):
        """Get traceability without auth should return 401."""
        response = no_auth_session.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        assert response.status_code == 401

    def test_rintracciabilita_invalid_commessa(self, auth_session):
        """Get traceability with invalid commessa should return 404."""
        response = auth_session.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/invalid_commessa_xyz")
        assert response.status_code == 404


class TestRegistroSaldaturaFullCycle:
    """Full CRUD cycle test for welding log."""

    def test_full_crud_cycle(self, auth_session):
        """Test complete Create → Read → Update → Delete cycle."""
        # 1. Get eligible welder
        welders_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei?processo=135")
        assert welders_resp.status_code == 200
        welders_data = welders_resp.json()
        welder_id = welders_data["saldatori"][0]["welder_id"] if welders_data["saldatori"] else TEST_WELDERS[0]
        
        # 2. CREATE
        create_payload = {
            "giunto": "TEST_CYCLE_G1",
            "posizione_dwg": "Pos.CYCLE",
            "saldatore_id": welder_id,
            "processo": "135",
            "data_esecuzione": "2026-01-15",
            "esito_vt": "da_eseguire",
            "note": "Full cycle test"
        }
        
        create_resp = auth_session.post(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}",
            json=create_payload
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        riga_id = create_resp.json()["riga_id"]
        print(f"Created riga: {riga_id}")
        
        # 3. READ - Verify in list
        list_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        assert list_resp.status_code == 200
        righe = list_resp.json()["righe"]
        created_riga = next((r for r in righe if r["riga_id"] == riga_id), None)
        assert created_riga is not None, "Created entry should appear in list"
        assert created_riga["giunto"] == "TEST_CYCLE_G1"
        assert created_riga["esito_vt"] == "da_eseguire"
        print(f"Verified riga in list: {created_riga['giunto']}")
        
        # 4. UPDATE
        update_payload = {
            "giunto": "TEST_CYCLE_G1",
            "posizione_dwg": "Pos.CYCLE_UPDATED",
            "saldatore_id": welder_id,
            "processo": "135",
            "data_esecuzione": "2026-01-16",
            "esito_vt": "conforme",
            "note": "Updated to conforme after VT inspection"
        }
        
        update_resp = auth_session.put(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga_id}",
            json=update_payload
        )
        assert update_resp.status_code == 200
        print(f"Updated riga: {riga_id}")
        
        # 5. READ - Verify update
        list_resp2 = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        righe2 = list_resp2.json()["righe"]
        updated_riga = next((r for r in righe2 if r["riga_id"] == riga_id), None)
        assert updated_riga is not None
        assert updated_riga["esito_vt"] == "conforme", f"Expected 'conforme', got '{updated_riga['esito_vt']}'"
        print(f"Verified update: esito_vt = {updated_riga['esito_vt']}")
        
        # 6. DELETE
        delete_resp = auth_session.delete(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga_id}"
        )
        assert delete_resp.status_code == 200
        print(f"Deleted riga: {riga_id}")
        
        # 7. READ - Verify deletion
        list_resp3 = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        righe3 = list_resp3.json()["righe"]
        deleted_riga = next((r for r in righe3 if r["riga_id"] == riga_id), None)
        assert deleted_riga is None, "Deleted entry should not appear in list"
        print("Verified deletion: entry no longer in list")


class TestCleanupTestData:
    """Cleanup any test data created during tests."""

    def test_cleanup_test_entries(self, auth_session):
        """Remove any TEST_ prefixed entries from registro saldatura."""
        list_resp = auth_session.get(f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}")
        if list_resp.status_code == 200:
            righe = list_resp.json()["righe"]
            test_righe = [r for r in righe if r.get("giunto", "").startswith("TEST_")]
            
            for riga in test_righe:
                auth_session.delete(
                    f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/{riga['riga_id']}"
                )
                print(f"Cleaned up test entry: {riga['riga_id']}")
        
        # This test always passes - it's just cleanup
        assert True

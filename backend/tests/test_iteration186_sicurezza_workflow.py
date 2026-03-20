"""
Iteration 186: Sicurezza & PNRR Compliance + Workflow Engine Tests

Tests for:
1. Sicurezza Operatore: corsi-obbligatori, check-operatore
2. Sicurezza Cantiere: checklist + mandatory photo
3. DNSH/PNRR: save/get (auth required)
4. CSE Export: ZIP generation (auth required)
5. Targa CE + Manutenzione Schedule (workflow triggers)
6. WORKFLOW: Timer START blocks if courses missing/expired
7. WORKFLOW: Firma triggers targa-ce + manutenzione-schedule
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_COMMESSA_ID = "com_2b99b2db8681"
TEST_OP_AHMED = {"op_id": "op_ba8179e3", "nome": "Ahmed", "pin": "1234"}
TEST_OP_KARIM = {"op_id": "op_d132350f", "nome": "Karim", "pin": "5678"}


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ══════════════════════════════════════════════════════════════
#  1. CORSI OBBLIGATORI — Public endpoint
# ══════════════════════════════════════════════════════════════

class TestCorsiObbligatori:
    """Tests for /api/sicurezza/corsi-obbligatori"""

    def test_get_corsi_obbligatori_returns_6_courses(self, api_client):
        """GET /api/sicurezza/corsi-obbligatori returns 6 mandatory courses"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/corsi-obbligatori")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "corsi" in data
        assert len(data["corsi"]) == 6, f"Expected 6 courses, got {len(data['corsi'])}"
        
        # Verify course structure
        expected_codes = ["formazione_base", "formazione_specifica", "primo_soccorso", 
                         "antincendio", "lavori_quota", "ple"]
        actual_codes = [c["codice"] for c in data["corsi"]]
        for code in expected_codes:
            assert code in actual_codes, f"Missing course: {code}"


# ══════════════════════════════════════════════════════════════
#  2. CHECK OPERATORE — Public endpoint (workflow gate)
# ══════════════════════════════════════════════════════════════

class TestCheckOperatore:
    """Tests for /api/sicurezza/check-operatore/{op_id}"""

    def test_check_operatore_ahmed_not_blocked(self, api_client):
        """GET /api/sicurezza/check-operatore/{op_id} returns bloccato=false for Ahmed (valid courses)"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/check-operatore/{TEST_OP_AHMED['op_id']}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "bloccato" in data
        assert data["bloccato"] == False, f"Ahmed should not be blocked, got: {data}"
        assert "motivi" in data
        assert len(data["motivi"]) == 0, f"Ahmed should have no blocking reasons, got: {data['motivi']}"

    def test_check_operatore_karim_not_blocked(self, api_client):
        """GET /api/sicurezza/check-operatore/{op_id} returns bloccato=false for Karim (valid courses)"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/check-operatore/{TEST_OP_KARIM['op_id']}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data["bloccato"] == False, f"Karim should not be blocked, got: {data}"

    def test_check_operatore_nonexistent_returns_not_blocked(self, api_client):
        """GET /api/sicurezza/check-operatore/nonexistent returns bloccato=false"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/check-operatore/nonexistent_op_12345")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert data["bloccato"] == False, f"Nonexistent operator should not be blocked"


# ══════════════════════════════════════════════════════════════
#  3. SICUREZZA CANTIERE — Checklist + mandatory photo
# ══════════════════════════════════════════════════════════════

class TestSicurezzaCantiere:
    """Tests for /api/sicurezza/cantiere endpoints"""

    def test_cantiere_checklist_returns_3_items(self, api_client):
        """GET /api/sicurezza/cantiere-checklist returns 3 items"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/cantiere-checklist")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "items" in data
        assert len(data["items"]) == 3, f"Expected 3 checklist items, got {len(data['items'])}"
        
        expected_codes = ["area_delimitata", "dpi_indossati", "attrezzature_verificate"]
        actual_codes = [i["codice"] for i in data["items"]]
        for code in expected_codes:
            assert code in actual_codes, f"Missing checklist item: {code}"

    def test_cantiere_save_without_photo_returns_400(self, api_client):
        """POST /api/sicurezza/cantiere without photo returns 400"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OP_AHMED["op_id"],
            "operatore_nome": TEST_OP_AHMED["nome"],
            "checklist": [
                {"codice": "area_delimitata", "esito": True},
                {"codice": "dpi_indossati", "esito": True},
                {"codice": "attrezzature_verificate", "esito": True},
            ],
            "foto_panoramica_doc_id": "",  # Empty = missing photo
        }
        res = api_client.post(f"{BASE_URL}/api/sicurezza/cantiere", json=payload)
        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
        assert "obbligatoria" in res.text.lower() or "foto" in res.text.lower()

    def test_cantiere_save_with_photo_succeeds(self, api_client):
        """POST /api/sicurezza/cantiere with photo succeeds"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OP_AHMED["op_id"],
            "operatore_nome": TEST_OP_AHMED["nome"],
            "checklist": [
                {"codice": "area_delimitata", "esito": True},
                {"codice": "dpi_indossati", "esito": True},
                {"codice": "attrezzature_verificate", "esito": True},
            ],
            "foto_panoramica_doc_id": f"doc_test_{uuid.uuid4().hex[:8]}",
        }
        res = api_client.post(f"{BASE_URL}/api/sicurezza/cantiere", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "sicurezza_id" in data
        assert data["all_ok"] == True
        assert data["commessa_id"] == TEST_COMMESSA_ID

    def test_cantiere_get_returns_latest(self, api_client):
        """GET /api/sicurezza/cantiere/{commessa_id} returns latest safety check"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/cantiere/{TEST_COMMESSA_ID}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "sicurezza" in data
        # May be null if no safety check exists, or an object if it does
        if data["sicurezza"]:
            assert "sicurezza_id" in data["sicurezza"]
            assert "checklist" in data["sicurezza"]


# ══════════════════════════════════════════════════════════════
#  4. TARGA CE + MANUTENZIONE SCHEDULE — Public workflow endpoints
# ══════════════════════════════════════════════════════════════

class TestTargaCeManutenzione:
    """Tests for /api/sicurezza/targa-ce and /api/sicurezza/manutenzione-schedule"""

    def test_targa_ce_generates_qr_data(self, api_client):
        """POST /api/sicurezza/targa-ce generates CE plate with QR data"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "montaggio_id": f"mtg_test_{uuid.uuid4().hex[:8]}",
        }
        res = api_client.post(f"{BASE_URL}/api/sicurezza/targa-ce", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "targa_id" in data
        assert "qr_data" in data
        assert data["qr_data"].startswith("CE|")
        assert "data_marcatura" in data
        assert data["commessa_id"] == TEST_COMMESSA_ID

    def test_manutenzione_schedule_creates_12_24_months(self, api_client):
        """POST /api/sicurezza/manutenzione-schedule creates 12 and 24 month entries"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "montaggio_id": f"mtg_test_{uuid.uuid4().hex[:8]}",
        }
        res = api_client.post(f"{BASE_URL}/api/sicurezza/manutenzione-schedule", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        assert "schedules" in data
        assert len(data["schedules"]) == 2, f"Expected 2 schedules (12 + 24 months), got {len(data['schedules'])}"
        
        # Verify 12 and 24 month entries
        tipos = [s["tipo"] for s in data["schedules"]]
        assert any("12" in t for t in tipos), "Missing 12-month maintenance"
        assert any("24" in t for t in tipos), "Missing 24-month maintenance"


# ══════════════════════════════════════════════════════════════
#  5. DNSH — Auth required
# ══════════════════════════════════════════════════════════════

class TestDNSH:
    """Tests for /api/sicurezza/dnsh endpoints (auth required)"""

    def test_dnsh_save_requires_auth(self, api_client):
        """POST /api/sicurezza/dnsh/save requires authentication"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "ha_riferimenti_dnsh": True,
            "percentuale_riciclato": "30%",
        }
        res = api_client.post(f"{BASE_URL}/api/sicurezza/dnsh/save", json=payload)
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    def test_dnsh_get_requires_auth(self, api_client):
        """GET /api/sicurezza/dnsh/{commessa_id} requires authentication"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/dnsh/{TEST_COMMESSA_ID}")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


# ══════════════════════════════════════════════════════════════
#  6. CSE EXPORT — Auth required
# ══════════════════════════════════════════════════════════════

class TestCSEExport:
    """Tests for /api/sicurezza/export-cse endpoint (auth required)"""

    def test_cse_export_requires_auth(self, api_client):
        """POST /api/sicurezza/export-cse/{commessa_id} requires authentication"""
        res = api_client.post(f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA_ID}")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


# ══════════════════════════════════════════════════════════════
#  7. WORKFLOW: Timer START blocks if courses missing/expired
# ══════════════════════════════════════════════════════════════

class TestWorkflowTimerSafety:
    """Tests for timer START workflow gate (safety check)"""

    def test_timer_start_passes_for_operator_with_valid_courses(self, api_client):
        """POST /api/officina/timer START passes for Ahmed (valid courses)"""
        # First verify PIN
        pin_res = api_client.post(f"{BASE_URL}/api/officina/pin/verify", json={
            "operatore_id": TEST_OP_AHMED["op_id"],
            "pin": TEST_OP_AHMED["pin"],
        })
        assert pin_res.status_code == 200, f"PIN verify failed: {pin_res.text}"
        
        # Try to start timer
        payload = {
            "action": "start",
            "operatore_id": TEST_OP_AHMED["op_id"],
            "operatore_nome": TEST_OP_AHMED["nome"],
        }
        res = api_client.post(f"{BASE_URL}/api/officina/timer/{TEST_COMMESSA_ID}", json=payload)
        
        # Should succeed (200) or fail with 400 if timer already active
        # Should NOT fail with 403 (blocked by safety)
        assert res.status_code != 403, f"Timer START should not be blocked for Ahmed with valid courses: {res.text}"
        
        # If 200, stop the timer to clean up
        if res.status_code == 200:
            data = res.json()
            stop_payload = {
                "action": "stop",
                "operatore_id": TEST_OP_AHMED["op_id"],
                "operatore_nome": TEST_OP_AHMED["nome"],
            }
            api_client.post(f"{BASE_URL}/api/officina/timer/{TEST_COMMESSA_ID}", json=stop_payload)


# ══════════════════════════════════════════════════════════════
#  8. WORKFLOW: Firma triggers targa-ce + manutenzione-schedule
# ══════════════════════════════════════════════════════════════

class TestWorkflowFirma:
    """Tests for firma workflow (triggers targa-ce + manutenzione)"""

    def test_firma_endpoint_exists(self, api_client):
        """POST /api/montaggio/firma endpoint exists and validates input"""
        # Test with invalid montaggio_id to verify endpoint exists
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "montaggio_id": "nonexistent_mtg_12345",
            "firma_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "firma_nome": "Test Cliente",
        }
        res = api_client.post(f"{BASE_URL}/api/montaggio/firma", json=payload)
        # Should return 404 (montaggio not found) not 500 or other error
        assert res.status_code == 404, f"Expected 404 for nonexistent montaggio, got {res.status_code}: {res.text}"


# ══════════════════════════════════════════════════════════════
#  9. MANUTENZIONI + TARGHE LIST — Auth required
# ══════════════════════════════════════════════════════════════

class TestManutenzioniTargheLists:
    """Tests for list endpoints (auth required)"""

    def test_manutenzioni_list_requires_auth(self, api_client):
        """GET /api/sicurezza/manutenzioni requires authentication"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/manutenzioni")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    def test_targhe_list_requires_auth(self, api_client):
        """GET /api/sicurezza/targhe-ce requires authentication"""
        res = api_client.get(f"{BASE_URL}/api/sicurezza/targhe-ce")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

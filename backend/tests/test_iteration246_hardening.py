"""
Iteration 246 — Backend Hardening Tests
=========================================
Tests for TD-005 (rate limiting), TD-009 (safe background tasks), TD-010 (user_id filter).

Test Categories:
1. Health endpoints (no auth required)
2. Rate-limited AI endpoints (should return 401 without auth, not 500)
3. User_id filtered routes (should return 401 without auth)
4. Backend idempotency (restart test)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Session for all tests
@pytest.fixture(scope="module")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ═══════════════════════════════════════════════════════════════════
# 1. HEALTH ENDPOINTS (No Auth Required)
# ═══════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    """Health check endpoints should work without authentication."""

    def test_root_health(self, api_client):
        """GET /api/ should return status operativo."""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Root health failed: {response.text}"
        data = response.json()
        assert data.get("status") == "operativo"
        assert "version" in data
        print(f"✓ Root health: {data}")

    def test_health_check(self, api_client):
        """GET /api/health should return status healthy."""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("service") == "Norma Facile 2.0"
        print(f"✓ Health check: {data}")

    def test_health_indexes(self, api_client):
        """GET /api/health/indexes should return all_indexes_present=true."""
        response = api_client.get(f"{BASE_URL}/api/health/indexes")
        assert response.status_code == 200, f"Health indexes failed: {response.text}"
        data = response.json()
        assert data.get("all_indexes_present") == True, f"Indexes not present: {data}"
        assert data.get("collections_checked") >= 12
        print(f"✓ Health indexes: {data.get('collections_checked')} collections, all_indexes_present={data.get('all_indexes_present')}")


# ═══════════════════════════════════════════════════════════════════
# 2. RATE-LIMITED AI ENDPOINTS (TD-005)
# Should return 401 without auth, NOT 500 (rate limiting shouldn't break endpoints)
# ═══════════════════════════════════════════════════════════════════

class TestRateLimitedEndpointsNoAuth:
    """Rate-limited endpoints should return 401 without auth, not 500."""

    # Istruttoria endpoints
    def test_istruttoria_analizza_no_auth(self, api_client):
        """POST /api/istruttoria/analizza-preventivo/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/istruttoria/analizza-preventivo/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Istruttoria analizza: 401 (correct)")

    def test_istruttoria_segmenta_no_auth(self, api_client):
        """POST /api/istruttoria/segmenta/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/istruttoria/segmenta/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Istruttoria segmenta: 401 (correct)")

    def test_istruttoria_phase2_genera_no_auth(self, api_client):
        """POST /api/istruttoria/phase2/genera/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/istruttoria/phase2/genera/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Istruttoria phase2 genera: 401 (correct)")

    # Committenza endpoints
    def test_committenza_analizza_no_auth(self, api_client):
        """POST /api/committenza/analizza/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Committenza analizza: 401 (correct)")

    def test_committenza_genera_obblighi_no_auth(self, api_client):
        """POST /api/committenza/analisi/{id}/genera-obblighi without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/committenza/analisi/test_id/genera-obblighi")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Committenza genera-obblighi: 401 (correct)")

    # Cantieri Sicurezza endpoints
    def test_cantieri_ai_precompila_no_auth(self, api_client):
        """POST /api/cantieri-sicurezza/{id}/ai-precompila without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza/test_id/ai-precompila")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Cantieri AI precompila: 401 (correct)")

    def test_cantieri_genera_pos_no_auth(self, api_client):
        """POST /api/cantieri-sicurezza/{id}/genera-pos without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza/test_id/genera-pos")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Cantieri genera-pos: 401 (correct)")

    # Smistatore endpoints
    def test_smistatore_analyze_no_auth(self, api_client):
        """POST /api/smistatore/analyze/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/smistatore/analyze/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Smistatore analyze: 401 (correct)")

    def test_smistatore_analyze_drawing_no_auth(self, api_client):
        """POST /api/smistatore/analyze-drawing/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/smistatore/analyze-drawing/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Smistatore analyze-drawing: 401 (correct)")

    # Sicurezza DNSH endpoint
    def test_sicurezza_dnsh_analyze_no_auth(self, api_client):
        """POST /api/sicurezza/dnsh/analyze without auth should return 401."""
        # This endpoint requires multipart form data
        response = api_client.post(f"{BASE_URL}/api/sicurezza/dnsh/analyze")
        # Should be 401 (no auth) or 422 (missing file) - not 500
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}: {response.text}"
        print(f"✓ Sicurezza DNSH analyze: {response.status_code} (correct)")

    # Perizia endpoint
    def test_perizia_genera_lettera_no_auth(self, api_client):
        """POST /api/perizie/{id}/genera-lettera without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/perizie/test_id/genera-lettera")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Perizia genera-lettera: 401 (correct)")

    # Engine endpoint
    def test_engine_validate_photos_no_auth(self, api_client):
        """POST /api/engine/validate-installation-photos without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/engine/validate-installation-photos", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Engine validate-photos: 401 (correct)")

    # Validation endpoints
    def test_validation_run_no_auth(self, api_client):
        """POST /api/validation/run/{id} without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/validation/run/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Validation run: 401 (correct)")

    def test_validation_run_batch_no_auth(self, api_client):
        """POST /api/validation/run-batch without auth should return 401."""
        response = api_client.post(f"{BASE_URL}/api/validation/run-batch", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Validation run-batch: 401 (correct)")


# ═══════════════════════════════════════════════════════════════════
# 3. USER_ID FILTERED ROUTES (TD-010)
# Should return 401 without auth
# ═══════════════════════════════════════════════════════════════════

class TestUserIdFilteredRoutesNoAuth:
    """User_id filtered routes should return 401 without auth."""

    # Audits
    def test_audits_list_no_auth(self, api_client):
        """GET /api/audits without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/audits")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Audits list: 401 (correct)")

    def test_audits_get_no_auth(self, api_client):
        """GET /api/audits/{id} without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/audits/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Audits get: 401 (correct)")

    def test_ncs_list_no_auth(self, api_client):
        """GET /api/ncs without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ NCs list: 401 (correct)")

    # Instruments
    def test_instruments_list_no_auth(self, api_client):
        """GET /api/instruments without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/instruments/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Instruments list: 401 (correct)")

    # Welders
    def test_welders_list_no_auth(self, api_client):
        """GET /api/welders without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Welders list: 401 (correct)")

    def test_welders_matrice_no_auth(self, api_client):
        """GET /api/welders/matrice-scadenze without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/welders/matrice-scadenze")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Welders matrice: 401 (correct)")

    # Quality Hub
    def test_quality_hub_summary_no_auth(self, api_client):
        """GET /api/quality-hub/summary without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/quality-hub/summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Quality Hub summary: 401 (correct)")

    # Cantieri Sicurezza
    def test_cantieri_list_no_auth(self, api_client):
        """GET /api/cantieri-sicurezza without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Cantieri list: 401 (correct)")

    # Istruttoria
    def test_istruttoria_list_no_auth(self, api_client):
        """GET /api/istruttoria without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/istruttoria")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Istruttoria list: 401 (correct)")

    # Committenza
    def test_committenza_packages_no_auth(self, api_client):
        """GET /api/committenza/packages without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/committenza/packages")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Committenza packages: 401 (correct)")


# ═══════════════════════════════════════════════════════════════════
# 4. BACKEND IDEMPOTENCY TEST
# ═══════════════════════════════════════════════════════════════════

class TestBackendIdempotency:
    """Backend should restart without errors and maintain health."""

    def test_multiple_health_checks(self, api_client):
        """Multiple health checks should all succeed."""
        for i in range(3):
            response = api_client.get(f"{BASE_URL}/api/health")
            assert response.status_code == 200, f"Health check {i+1} failed: {response.text}"
            data = response.json()
            assert data.get("status") == "healthy"
            print(f"✓ Health check {i+1}: healthy")
            time.sleep(0.5)

    def test_indexes_consistent(self, api_client):
        """Index check should be consistent across multiple calls."""
        for i in range(2):
            response = api_client.get(f"{BASE_URL}/api/health/indexes")
            assert response.status_code == 200, f"Index check {i+1} failed: {response.text}"
            data = response.json()
            assert data.get("all_indexes_present") == True
            print(f"✓ Index check {i+1}: all_indexes_present=True")
            time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════
# 5. ADDITIONAL ROUTE CHECKS
# ═══════════════════════════════════════════════════════════════════

class TestAdditionalRoutes:
    """Additional route checks for completeness."""

    def test_verbale_posa_no_auth(self, api_client):
        """GET /api/verbale-posa/{commessa_id} without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/verbale-posa/test_commessa_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Verbale posa: 401 (correct)")

    def test_montaggio_torque_table_public(self, api_client):
        """GET /api/montaggio/torque-table is a public reference endpoint (no auth needed)."""
        response = api_client.get(f"{BASE_URL}/api/montaggio/torque-table")
        # This is a public reference endpoint - returns static torque data
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "table" in data
        assert "diameters" in data
        print(f"✓ Montaggio torque-table: 200 (public reference endpoint)")

    def test_smistatore_index_no_auth(self, api_client):
        """GET /api/smistatore/index/{id} without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/smistatore/index/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Smistatore index: 401 (correct)")

    def test_smistatore_scorte_no_auth(self, api_client):
        """GET /api/smistatore/scorte without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/smistatore/scorte")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Smistatore scorte: 401 (correct)")

    def test_libreria_fasi_no_auth(self, api_client):
        """GET /api/libreria/fasi without auth should return 401."""
        response = api_client.get(f"{BASE_URL}/api/libreria/fasi")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Libreria fasi: 401 (correct)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

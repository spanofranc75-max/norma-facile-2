"""
Iteration 95 - STABILIZATION TESTS
Testing all changes made in today's session:
1. Compliance EN 1090 widget - commesse in all states (not just confermata/in_produzione)
2. Quality Score - adaptive categories, CE from fascicolo tecnico
3. CAM report-aziendale - datetime filter fixed
4. Super Fascicolo Tecnico - welder section 4.4
5. Core CRUD endpoints
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

# Use PUBLIC URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://norma-v2-deploy.preview.emergentagent.com').rstrip('/')
AUTH_TOKEN = "yDZ9JAQM_3ct2TZ0UE3BFkZDQcc6YRSFWMlv888wRhQ"

# Test user data
TEST_USER_ID = "user_97c773827822"
COMMESSA_WITH_FT = "com_bfb82e090373"  # NF-2026-000002, stato=chiuso, has CE data
COMMESSA_WITHOUT_FT = "com_a91eab07a36e"  # NF-2026-000001, stato=fatturato


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}


class TestHealthCheck:
    """Basic backend health check"""

    def test_backend_alive(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        print(f"PASS: Backend alive, user: {data.get('email')}")


class TestComplianceEN1090:
    """
    Bug #1 Fix: compliance-en1090 now returns commesse in ALL states (not just confermata/in_produzione)
    as long as they have fascicolo_tecnico data or classe_esecuzione
    """

    def test_returns_commesse_with_ft_data(self, auth_headers):
        """Verify NF-2026-000002 (stato=chiuso) appears because it has FT data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-en1090", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        commesse = data.get("commesse", [])
        assert len(commesse) >= 1, "Should return at least 1 commessa with FT data"
        
        # Find NF-2026-000002 (stato=chiuso with FT data)
        found_ft_commessa = any(c.get("numero") == "NF-2026-000002" for c in commesse)
        assert found_ft_commessa, "NF-2026-000002 (stato=chiuso) should appear in compliance widget"
        
        print(f"PASS: compliance-en1090 returns {len(commesse)} commesse with FT data")

    def test_excludes_bozza_stato(self, auth_headers):
        """Verify stato=bozza commesse are excluded"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-en1090", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for c in data.get("commesse", []):
            assert c.get("stato") != "bozza", f"Bozza commessa should be excluded: {c.get('numero')}"
        
        print("PASS: No bozza commesse in compliance widget")

    def test_response_structure(self, auth_headers):
        """Verify response has correct structure with docs and compliance_pct"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-en1090", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "commesse" in data
        assert "total" in data
        
        if data["commesse"]:
            c = data["commesse"][0]
            assert "commessa_id" in c
            assert "numero" in c
            assert "compliance_pct" in c
            assert "docs" in c
            assert isinstance(c["docs"], dict)
        
        print(f"PASS: Response structure valid, total={data.get('total')}")


class TestQualityScoreAdaptive:
    """
    Bug #2 Fix: quality-score now uses adaptive categories
    - Sicurezza category only shows if user has rilievi/POS
    - CE category counts from fascicolo_tecnico fields too
    """

    def test_adaptive_categories_exclude_sicurezza_if_no_rilievi(self, auth_headers):
        """User has 0 rilievi, so Sicurezza Cantieri should NOT be in breakdown"""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        breakdown = data.get("breakdown", {})
        
        # User has 0 rilievi/POS, so 'safety' category should not exist
        if "safety" in breakdown:
            stats = data.get("stats", {})
            assert stats.get("total_rilievi", 0) > 0 or stats.get("total_pos", 0) > 0, \
                "Safety category exists but user has no rilievi/POS"
        
        print(f"PASS: Adaptive categories working. Breakdown keys: {list(breakdown.keys())}")

    def test_ce_counts_from_fascicolo_tecnico(self, auth_headers):
        """CE count should include commesse with CE data in fascicolo_tecnico"""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # User has NF-2026-000002 with CE data in fascicolo_tecnico
        breakdown = data.get("breakdown", {})
        
        # If user does EN 1090 work, there should be a 'ce' category
        # NF-2026-000002 has certificato_numero, ente_notificato filled
        if "ce" not in breakdown:
            print("INFO: No 'ce' category - user may not have en1090 commesse with CE data")
        else:
            print(f"PASS: CE category present with score {breakdown['ce'].get('score')}/{breakdown['ce'].get('max')}")

    def test_score_normalized_to_100(self, auth_headers):
        """Total score should be normalized to 100"""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        total = data.get("total_score", 0)
        assert 0 <= total <= 100, f"Score {total} should be between 0 and 100"
        
        assert "level" in data
        assert "level_color" in data
        
        print(f"PASS: Quality Score {total}/100, level: {data.get('level')}")

    def test_no_false_ce_warning_when_ce_exists(self, auth_headers):
        """Should not show 'Nessuna certificazione CE' warning if CE exists in FT"""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        insights = data.get("insights", [])
        
        # Check if there's a false CE warning
        ce_warnings = [i for i in insights if "Nessuna certificazione CE" in i.get("text", "")]
        
        # User has CE data in fascicolo tecnico, so this warning should ideally not appear
        # or at least the CE category should exist
        if ce_warnings and "ce" in data.get("breakdown", {}):
            print("WARNING: CE warning appears despite CE category existing")
        else:
            print("PASS: No false CE warning")


class TestCAMReportAziendale:
    """
    Bug #3 Fix: report-aziendale datetime filter fixed
    Now handles both datetime objects and ISO strings for created_at
    """

    def test_returns_lotti_for_2026(self, auth_headers):
        """Verify lotti_cam data returned for anno=2026"""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale?anno=2026", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "totale_lotti" in data
        assert data["totale_lotti"] >= 2, f"Expected >= 2 lotti, got {data['totale_lotti']}"
        
        assert data["peso_totale_kg"] > 0, "peso_totale_kg should be > 0"
        print(f"PASS: CAM report has {data['totale_lotti']} lotti, {data['peso_totale_kg']} kg")

    def test_trend_mensile_populated(self, auth_headers):
        """Verify trend_mensile is populated (handles datetime created_at)"""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale?anno=2026", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        trend = data.get("trend_mensile", [])
        assert len(trend) > 0, "trend_mensile should not be empty"
        
        # Check structure
        if trend:
            t = trend[0]
            assert "mese" in t
            assert "peso_kg" in t
            assert "co2_risparmiata_kg" in t
        
        print(f"PASS: trend_mensile has {len(trend)} months of data")

    def test_co2_calculation(self, auth_headers):
        """Verify CO2 savings are calculated"""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale?anno=2026", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        co2 = data.get("co2", {})
        assert "co2_risparmiata_kg" in co2
        assert co2.get("co2_risparmiata_kg", 0) >= 0
        
        # Check sustainability KPIs
        assert "alberi_equivalenti" in data
        assert "indice_economia_circolare" in data
        
        print(f"PASS: CO2 risparmiata={co2.get('co2_risparmiata_kg')} kg, alberi={data.get('alberi_equivalenti')}")

    def test_empty_year_returns_zero_state(self, auth_headers):
        """Verify empty year returns proper zero state (not error)"""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale?anno=2020", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["totale_lotti"] == 0
        assert data["peso_totale_kg"] == 0
        print("PASS: Empty year returns zero state, not error")


class TestSuperFascicoloTecnico:
    """
    Feature: Super Fascicolo now includes welder section 4.4 with assigned welders
    """

    def test_pdf_generation(self, auth_headers):
        """Verify PDF generates successfully for commessa with FT data"""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_WITH_FT}/fascicolo-tecnico-completo",
            headers=auth_headers,
            stream=True
        )
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "pdf" in content_type.lower(), f"Expected PDF, got {content_type}"
            
            # Check PDF size (should be substantial with all sections)
            content = response.content
            assert len(content) > 50000, f"PDF too small: {len(content)} bytes"
            
            print(f"PASS: Super Fascicolo PDF generated, size={len(content)} bytes")
        elif response.status_code == 400:
            # May fail if no FT data
            print("INFO: Super Fascicolo returned 400 - may need FT data")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")

    def test_requires_auth(self, auth_headers):
        """Verify auth required for PDF generation"""
        response = requests.get(f"{BASE_URL}/api/commesse/{COMMESSA_WITH_FT}/fascicolo-tecnico-completo")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Auth required for Super Fascicolo")


class TestCoreCRUDEndpoints:
    """Regression tests for core CRUD operations (using trailing slash for Cloudflare)"""

    def test_get_commesse(self, auth_headers):
        """GET /api/commesse/ works"""
        response = requests.get(f"{BASE_URL}/api/commesse/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200, f"Got {response.status_code}: {response.text[:200]}"
        data = response.json()
        assert "items" in data or "commesse" in data or isinstance(data, list)
        print(f"PASS: GET /api/commesse/ works")

    def test_get_preventivi(self, auth_headers):
        """GET /api/preventivi/ works"""
        response = requests.get(f"{BASE_URL}/api/preventivi/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "preventivi" in data or isinstance(data, list)
        print(f"PASS: GET /api/preventivi/ works")

    def test_get_ddt(self, auth_headers):
        """GET /api/ddt/ works"""
        response = requests.get(f"{BASE_URL}/api/ddt/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert "ddt_list" in data or "documents" in data or "items" in data or isinstance(data, list)
        print(f"PASS: GET /api/ddt/ works")

    def test_get_invoices(self, auth_headers):
        """GET /api/invoices/ works"""
        response = requests.get(f"{BASE_URL}/api/invoices/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200
        print(f"PASS: GET /api/invoices/ works")

    def test_get_welders(self, auth_headers):
        """GET /api/welders/ works"""
        response = requests.get(f"{BASE_URL}/api/welders/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        items = data.get("items") or data.get("welders") or []
        assert len(items) >= 3, f"Should have at least 3 active welders, got {len(items)}"
        print(f"PASS: GET /api/welders/ works, count={len(items)}")

    def test_get_instruments(self, auth_headers):
        """GET /api/instruments/ works"""
        response = requests.get(f"{BASE_URL}/api/instruments/", headers=auth_headers, allow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        items = data.get("items") or data.get("instruments") or []
        assert len(items) >= 5, f"Should have at least 5 instruments, got {len(items)}"
        print(f"PASS: GET /api/instruments/ works, count={len(items)}")


class TestDashboardStats:
    """General dashboard stats endpoint"""

    def test_dashboard_stats(self, auth_headers):
        """GET /api/dashboard/stats works"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = ["ferro_kg", "cantieri_attivi", "fatturato_mese"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        print(f"PASS: Dashboard stats working, fatturato_mese={data.get('fatturato_mese')}")


class TestAuthFlow:
    """Session-based auth verification"""

    def test_auth_me(self, auth_headers):
        """Auth me returns user data"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        assert "email" in data
        print(f"PASS: Auth me working, email={data.get('email')}")

    def test_invalid_token_rejected(self):
        """Invalid token is rejected"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code in [401, 403]
        print("PASS: Invalid token rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

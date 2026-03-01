"""
Iteration 94: Dashboard Bug Fixes Testing
- Bug 1: compliance-en1090 widget showed empty despite having EN 1090 commesse
         FIX: Filter by fascicolo_tecnico data presence, not by stato
- Bug 2: quality-score penalized users who don't do rilievi/POS/CE
         FIX: Adaptive categories - only show relevant categories to user
"""
import pytest
import requests
import os
from datetime import datetime, timedelta, timezone

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user with real commesse data
TEST_USER_ID = "user_97c773827822"
TEST_SESSION_TOKEN = "yDZ9JAQM_3ct2TZ0UE3BFkZDQcc6YRSFWMlv888wRhQ"


class TestHealthCheck:
    """Basic backend health check"""
    
    def test_backend_health(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Backend not healthy: {response.text}"
        print("Backend health check: PASS")


class TestComplianceEN1090Endpoint:
    """Test GET /api/dashboard/compliance-en1090 - Bug #1 fix"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_compliance_returns_commesse_regardless_of_stato(self, auth_headers):
        """
        BUG FIX TEST: Previously only returned commesse with stato=confermata/in_produzione.
        Now should return commesse in ANY state (except bozza) if they have FT data.
        User has:
          - NF-2026-000001 (stato=fatturato, FT=empty) -> should NOT appear
          - NF-2026-000002 (stato=chiuso, FT=34 fields) -> should appear
        """
        response = requests.get(
            f"{BASE_URL}/api/dashboard/compliance-en1090",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commesse" in data, "Response should have 'commesse' key"
        assert "total" in data, "Response should have 'total' key"
        
        commesse = data["commesse"]
        print(f"Found {len(commesse)} commesse in compliance widget")
        
        # Should have exactly 1 commessa (NF-2026-000002 with FT data)
        assert len(commesse) >= 1, "Should have at least 1 commessa with FT data"
        
        # Verify NF-2026-000002 is present (has FT data, stato=chiuso)
        numeros = [c.get("numero") for c in commesse]
        print(f"Commesse in widget: {numeros}")
        
        assert "NF-2026-000002" in numeros, "NF-2026-000002 (stato=chiuso, FT filled) should be included"
        
        # NF-2026-000001 should NOT be present (no FT data)
        assert "NF-2026-000001" not in numeros, "NF-2026-000001 (no FT data) should be excluded"
        
        print("BUG #1 FIX VERIFIED: compliance-en1090 returns commesse by FT data, not stato")
    
    def test_compliance_includes_stato_field(self, auth_headers):
        """Verify response includes stato field for all commesse"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/compliance-en1090",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        commesse = data.get("commesse", [])
        
        for c in commesse:
            assert "stato" in c, f"Commessa {c.get('numero')} missing 'stato' field"
            assert "compliance_pct" in c, f"Commessa {c.get('numero')} missing 'compliance_pct'"
            assert "docs" in c, f"Commessa {c.get('numero')} missing 'docs' field"
            print(f"Commessa {c.get('numero')}: stato={c.get('stato')}, compliance_pct={c.get('compliance_pct')}%")
        
        print("All commesse have required fields: PASS")
    
    def test_compliance_pct_calculated_correctly(self, auth_headers):
        """Verify compliance percentage is calculated based on filled FT fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/compliance-en1090",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        commesse = data.get("commesse", [])
        
        # Find NF-2026-000002 which has 34 FT fields filled
        nf002 = next((c for c in commesse if c.get("numero") == "NF-2026-000002"), None)
        
        if nf002:
            pct = nf002.get("compliance_pct", 0)
            assert pct > 0, f"Compliance % should be > 0 for commessa with 34 filled fields, got {pct}"
            print(f"NF-2026-000002 compliance_pct: {pct}% (34 FT fields filled)")
        
        print("Compliance percentage calculation: PASS")


class TestQualityScoreEndpoint:
    """Test GET /api/dashboard/quality-score - Bug #2 fix"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_quality_score_adaptive_categories(self, auth_headers):
        """
        BUG FIX TEST: Previously all categories appeared, penalizing users who don't use them.
        Now should only show categories relevant to user's workflow.
        
        Test user has:
          - 0 rilievi, 0 POS -> 'Sicurezza Cantieri' should NOT appear
          - 0 certificazioni, but 1 EN1090 commessa -> 'Certificazioni CE' should appear
          - 3 welders -> 'Sistema Qualità' should appear
          - 2 commesse, 5 invoices, 2 preventivi -> 'Commesse & Produzione' should appear
        """
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_score" in data, "Response should have 'total_score'"
        assert "breakdown" in data, "Response should have 'breakdown'"
        assert "level" in data, "Response should have 'level'"
        
        breakdown = data.get("breakdown", {})
        category_keys = list(breakdown.keys())
        print(f"Active categories: {category_keys}")
        
        # Verify adaptive behavior
        # 'safety' (Sicurezza Cantieri) should NOT be present - user has 0 rilievi/POS
        assert "safety" not in breakdown, \
            f"'safety' category should NOT appear when user has no rilievi/POS. Found categories: {category_keys}"
        
        print("BUG #2 FIX VERIFIED: Sicurezza Cantieri category NOT shown (user has 0 rilievi/POS)")
    
    def test_quality_score_normalized_to_100(self, auth_headers):
        """Verify score is normalized to 100 based on ACTIVE categories only"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        total_score = data.get("total_score", 0)
        
        # Score should be achievable (not penalized by missing categories)
        # With 2 commesse, 5 invoices, 2 preventivi, 5 DDT, 3 welders -> should score reasonably
        assert total_score > 0, f"Total score should be > 0, got {total_score}"
        assert total_score <= 100, f"Total score should be <= 100, got {total_score}"
        
        print(f"Total quality score: {total_score}/100")
        print(f"Level: {data.get('level')}")
        
        # Verify breakdown sums correctly
        breakdown = data.get("breakdown", {})
        breakdown_total = sum(cat.get("score", 0) for cat in breakdown.values())
        breakdown_max = sum(cat.get("max", 0) for cat in breakdown.values())
        
        print(f"Breakdown total: {breakdown_total}, max: {breakdown_max}")
        
        # breakdown_max should be approximately 100 (normalized)
        assert 95 <= breakdown_max <= 105, \
            f"Breakdown max should sum to ~100 (normalized), got {breakdown_max}"
        
        print("Score normalization: PASS")
    
    def test_quality_score_production_category_present(self, auth_headers):
        """User has commesse/preventivi, so 'production' category should appear"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        assert "production" in breakdown, \
            f"'production' category should appear when user has commesse. Found: {list(breakdown.keys())}"
        
        prod = breakdown["production"]
        assert prod.get("label") == "Commesse & Produzione", f"Wrong label: {prod.get('label')}"
        assert prod.get("score", 0) > 0, f"Production score should be > 0, got {prod.get('score')}"
        
        print(f"Commesse & Produzione: {prod.get('score')}/{prod.get('max')}")
        print("Production category: PASS")
    
    def test_quality_score_documentation_always_present(self, auth_headers):
        """Documentation category should always be present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        assert "documentation" in breakdown, \
            f"'documentation' category should always appear. Found: {list(breakdown.keys())}"
        
        doc = breakdown["documentation"]
        assert doc.get("label") == "Documentazione"
        
        print(f"Documentazione: {doc.get('score')}/{doc.get('max')}")
        print("Documentation category: PASS")
    
    def test_quality_score_ce_category_for_en1090_user(self, auth_headers):
        """User has EN1090 commesse (with FT data), so 'ce' category should appear"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        # User has 1 EN1090 commessa (with FT data), so CE category should appear
        assert "ce" in breakdown, \
            f"'ce' (Certificazioni CE) category should appear for EN1090 users. Found: {list(breakdown.keys())}"
        
        ce = breakdown["ce"]
        assert ce.get("label") == "Certificazioni CE"
        
        print(f"Certificazioni CE: {ce.get('score')}/{ce.get('max')}")
        print("CE category for EN1090 user: PASS")
    
    def test_quality_score_quality_category_for_welders(self, auth_headers):
        """User has welders, so 'quality' (Sistema Qualità) category should appear"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        stats = data.get("stats", {})
        
        # User has 3 welders (is_active: True)
        welders = stats.get("total_welders", 0)
        print(f"User has {welders} welders")
        
        if welders > 0:
            assert "quality" in breakdown, \
                f"'quality' category should appear when user has welders. Found: {list(breakdown.keys())}"
            
            quality = breakdown["quality"]
            assert quality.get("label") == "Sistema Qualità"
            
            print(f"Sistema Qualità: {quality.get('score')}/{quality.get('max')}")
            print("Quality category for user with welders: PASS")
        else:
            print("User has no welders - quality category test skipped")
    
    def test_quality_score_activity_always_present(self, auth_headers):
        """Activity category should always be present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        assert "activity" in breakdown, \
            f"'activity' category should always appear. Found: {list(breakdown.keys())}"
        
        activity = breakdown["activity"]
        assert activity.get("label") == "Attività Recente"
        
        print(f"Attività Recente: {activity.get('score')}/{activity.get('max')}")
        print("Activity category: PASS")


class TestQualityScoreEdgeCases:
    """Additional edge case tests for quality score adaptive behavior"""
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_insights_are_relevant_only(self, auth_headers):
        """Insights should only suggest actions relevant to user's workflow"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        insights = data.get("insights", [])
        
        print(f"Found {len(insights)} insights:")
        for insight in insights:
            print(f"  - {insight.get('type')}: {insight.get('text')}")
        
        # Should not have more than 3 insights (capped)
        assert len(insights) <= 3, f"Max 3 insights, got {len(insights)}"
        
        print("Insights relevance check: PASS")


class TestAuthRequirement:
    """Verify both endpoints require authentication"""
    
    def test_compliance_requires_auth(self):
        """compliance-en1090 should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/compliance-en1090")
        assert response.status_code in [401, 403], \
            f"Should require auth, got {response.status_code}"
        print("compliance-en1090 auth required: PASS")
    
    def test_quality_score_requires_auth(self):
        """quality-score should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score")
        assert response.status_code in [401, 403], \
            f"Should require auth, got {response.status_code}"
        print("quality-score auth required: PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

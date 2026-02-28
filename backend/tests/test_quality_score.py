"""
Test suite for the Officina Quality Score API (GET /api/dashboard/quality-score).
Tests score calculation, breakdown categories, level assignments, and insights.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "bridge_test_token_2026"


@pytest.fixture
def api_client():
    """Shared requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


class TestQualityScoreEndpoint:
    """Tests for GET /api/dashboard/quality-score endpoint."""

    def test_quality_score_returns_200(self, api_client):
        """Verify endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/dashboard/quality-score returns 200")

    def test_quality_score_has_total_score(self, api_client):
        """Verify response contains total_score (0-100)."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "total_score" in data, "Missing total_score field"
        assert isinstance(data["total_score"], int), "total_score should be integer"
        assert 0 <= data["total_score"] <= 100, f"total_score {data['total_score']} not in 0-100 range"
        print(f"PASS: total_score = {data['total_score']} (valid 0-100)")

    def test_quality_score_has_level(self, api_client):
        """Verify response contains level field."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "level" in data, "Missing level field"
        assert isinstance(data["level"], str), "level should be string"
        assert len(data["level"]) > 0, "level should not be empty"
        print(f"PASS: level = '{data['level']}'")

    def test_quality_score_has_level_color(self, api_client):
        """Verify response contains level_color field."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "level_color" in data, "Missing level_color field"
        valid_colors = ["emerald", "blue", "amber", "slate"]
        assert data["level_color"] in valid_colors, f"level_color '{data['level_color']}' not in valid colors"
        print(f"PASS: level_color = '{data['level_color']}'")

    def test_quality_score_level_matches_score(self, api_client):
        """Verify level corresponds to score thresholds."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        score = data["total_score"]
        level = data["level"]
        
        if score >= 80:
            assert "Maestro" in level, f"Score {score} >= 80 should be Maestro, got {level}"
        elif score >= 60:
            assert "Esperto" in level, f"Score {score} >= 60 should be Esperto, got {level}"
        elif score >= 40:
            assert "Crescita" in level, f"Score {score} >= 40 should be Crescita, got {level}"
        else:
            assert "Apprendista" in level, f"Score {score} < 40 should be Apprendista, got {level}"
        print(f"PASS: Level '{level}' matches score {score}")


class TestQualityScoreBreakdown:
    """Tests for breakdown section in quality score."""

    def test_breakdown_exists(self, api_client):
        """Verify breakdown object exists."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "breakdown" in data, "Missing breakdown field"
        assert isinstance(data["breakdown"], dict), "breakdown should be object"
        print("PASS: breakdown object exists")

    def test_breakdown_has_five_categories(self, api_client):
        """Verify breakdown has exactly 5 required categories."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        breakdown = data["breakdown"]
        required_categories = ["safety", "ce", "documentation", "photos", "activity"]
        
        for cat in required_categories:
            assert cat in breakdown, f"Missing breakdown category: {cat}"
        
        assert len(breakdown) == 5, f"Expected 5 categories, got {len(breakdown)}"
        print(f"PASS: All 5 categories present: {list(breakdown.keys())}")

    def test_breakdown_category_structure(self, api_client):
        """Verify each breakdown category has score, max, label."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        breakdown = data["breakdown"]
        
        for cat_name, cat_data in breakdown.items():
            assert "score" in cat_data, f"Missing 'score' in {cat_name}"
            assert "max" in cat_data, f"Missing 'max' in {cat_name}"
            assert "label" in cat_data, f"Missing 'label' in {cat_name}"
            
            assert isinstance(cat_data["score"], int), f"{cat_name} score should be int"
            assert isinstance(cat_data["max"], int), f"{cat_name} max should be int"
            assert isinstance(cat_data["label"], str), f"{cat_name} label should be string"
            
            assert 0 <= cat_data["score"] <= cat_data["max"], f"{cat_name} score {cat_data['score']} out of max {cat_data['max']}"
        
        print("PASS: All breakdown categories have valid structure")

    def test_breakdown_max_values(self, api_client):
        """Verify breakdown max values match expected totals."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        breakdown = data["breakdown"]
        expected_max = {
            "safety": 30,
            "ce": 25,
            "documentation": 20,
            "photos": 10,
            "activity": 15
        }
        
        for cat, expected in expected_max.items():
            actual = breakdown[cat]["max"]
            assert actual == expected, f"{cat} max should be {expected}, got {actual}"
        
        total_max = sum(v["max"] for v in breakdown.values())
        assert total_max == 100, f"Total max should be 100, got {total_max}"
        print("PASS: All breakdown max values correct (30+25+20+10+15=100)")


class TestQualityScoreInsights:
    """Tests for insights section in quality score."""

    def test_insights_exists(self, api_client):
        """Verify insights array exists."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "insights" in data, "Missing insights field"
        assert isinstance(data["insights"], list), "insights should be array"
        print(f"PASS: insights array exists with {len(data['insights'])} items")

    def test_insights_structure(self, api_client):
        """Verify each insight has required fields."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        for i, insight in enumerate(data["insights"]):
            assert "type" in insight, f"Insight {i} missing 'type'"
            assert "text" in insight, f"Insight {i} missing 'text'"
            assert "action" in insight, f"Insight {i} missing 'action'"
            assert "points" in insight, f"Insight {i} missing 'points'"
            
            valid_types = ["warning", "tip", "info"]
            assert insight["type"] in valid_types, f"Insight {i} type '{insight['type']}' invalid"
            assert isinstance(insight["text"], str), f"Insight {i} text should be string"
            assert isinstance(insight["action"], str), f"Insight {i} action should be string"
            assert isinstance(insight["points"], int), f"Insight {i} points should be int"
            assert insight["points"] >= 0, f"Insight {i} points should be >= 0"
        
        print("PASS: All insights have valid structure")

    def test_insights_max_three(self, api_client):
        """Verify insights array has at most 3 items (top 3 by points)."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert len(data["insights"]) <= 3, f"Expected at most 3 insights, got {len(data['insights'])}"
        print(f"PASS: insights count ({len(data['insights'])}) <= 3")

    def test_insights_sorted_by_points(self, api_client):
        """Verify insights are sorted by points descending."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        insights = data["insights"]
        if len(insights) > 1:
            points = [i["points"] for i in insights]
            for i in range(len(points) - 1):
                assert points[i] >= points[i + 1], f"Insights not sorted: {points}"
        
        print(f"PASS: Insights sorted by points: {[i['points'] for i in insights]}")


class TestQualityScoreStats:
    """Tests for stats section in quality score (optional additional info)."""

    def test_stats_exists(self, api_client):
        """Verify stats object exists."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        assert "stats" in data, "Missing stats field"
        assert isinstance(data["stats"], dict), "stats should be object"
        print("PASS: stats object exists")

    def test_stats_has_counts(self, api_client):
        """Verify stats has relevant document counts."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/quality-score")
        data = response.json()
        
        stats = data["stats"]
        expected_keys = ["total_rilievi", "total_pos", "total_certs", "total_invoices", "total_prev", "total_distinte"]
        
        for key in expected_keys:
            assert key in stats, f"Missing stats key: {key}"
            assert isinstance(stats[key], int), f"stats[{key}] should be int"
            assert stats[key] >= 0, f"stats[{key}] should be >= 0"
        
        print(f"PASS: stats has all counts: rilievi={stats['total_rilievi']}, pos={stats['total_pos']}, certs={stats['total_certs']}")


class TestQualityScoreAuth:
    """Test authentication requirements."""

    def test_without_auth_returns_401(self):
        """Verify endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/dashboard/quality-score")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: Returns 401 without authentication")

    def test_with_invalid_token_returns_401(self):
        """Verify invalid token is rejected."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/quality-score",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 401, f"Expected 401 with invalid token, got {response.status_code}"
        print("PASS: Returns 401 with invalid token")

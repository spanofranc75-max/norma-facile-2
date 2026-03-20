"""
Iteration 187: SettingsPage Refactoring + AI Vision Drawing Analysis Tests

Tests:
1. Company settings GET/PUT endpoints
2. Smistatore analyze-drawing endpoint (401 without auth, 404 with wrong doc_id)
3. Smistatore drawing-to-rdp endpoint (401 without auth, 404 with wrong doc_id)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "SGz2wNxiQd67E3cYdQqGqeBRaO1FOzaGpgo3Xf9jQco"


class TestCompanySettings:
    """Company settings endpoint tests"""

    def test_get_company_settings_without_auth(self):
        """GET /api/company/settings should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/company/settings returns 401 without auth")

    def test_get_company_settings_with_auth(self):
        """GET /api/company/settings should return 200 with auth"""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dict"
        print(f"✓ GET /api/company/settings returns 200 with auth, keys: {list(data.keys())[:5]}...")

    def test_put_company_settings_without_auth(self):
        """PUT /api/company/settings should return 401 without auth"""
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            json={"business_name": "Test Company"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ PUT /api/company/settings returns 401 without auth")

    def test_put_company_settings_with_auth(self):
        """PUT /api/company/settings should return 200 with auth"""
        # First get current settings
        get_response = requests.get(
            f"{BASE_URL}/api/company/settings",
            cookies={"session_token": SESSION_TOKEN}
        )
        if get_response.status_code != 200:
            pytest.skip("Cannot get current settings")
        
        current = get_response.json()
        
        # Update with same data (no actual change)
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            json=current,
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PUT /api/company/settings returns 200 with auth")


class TestSmistatoreDrawingAnalysis:
    """Smistatore drawing analysis endpoint tests"""

    def test_analyze_drawing_without_auth(self):
        """POST /api/smistatore/analyze-drawing/{doc_id} should return 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/smistatore/analyze-drawing/fake_doc_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/smistatore/analyze-drawing returns 401 without auth")

    def test_analyze_drawing_with_invalid_doc_id(self):
        """POST /api/smistatore/analyze-drawing/{doc_id} should return 404 for non-existent doc"""
        response = requests.post(
            f"{BASE_URL}/api/smistatore/analyze-drawing/nonexistent_doc_12345",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data or "message" in data, "Should have error message"
        print("✓ POST /api/smistatore/analyze-drawing returns 404 for invalid doc_id")


class TestSmistatoreDrawingToRdp:
    """Smistatore drawing-to-rdp endpoint tests"""

    def test_drawing_to_rdp_without_auth(self):
        """POST /api/smistatore/drawing-to-rdp/{doc_id} should return 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/smistatore/drawing-to-rdp/fake_doc_id",
            json={"selected_indices": [0, 1]}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/smistatore/drawing-to-rdp returns 401 without auth")

    def test_drawing_to_rdp_with_invalid_doc_id(self):
        """POST /api/smistatore/drawing-to-rdp/{doc_id} should return 404 for non-existent doc"""
        response = requests.post(
            f"{BASE_URL}/api/smistatore/drawing-to-rdp/nonexistent_doc_12345",
            json={"selected_indices": [0, 1], "fornitore_nome": "Test", "note": ""},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data or "message" in data, "Should have error message"
        print("✓ POST /api/smistatore/drawing-to-rdp returns 404 for invalid doc_id")


class TestSmistatoreIndex:
    """Smistatore index endpoint tests"""

    def test_get_index_without_auth(self):
        """GET /api/smistatore/index/{commessa_id} should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/smistatore/index/com_test123")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/smistatore/index returns 401 without auth")

    def test_get_index_with_auth(self):
        """GET /api/smistatore/index/{commessa_id} should return 200 with auth (even for non-existent commessa)"""
        response = requests.get(
            f"{BASE_URL}/api/smistatore/index/com_test123",
            cookies={"session_token": SESSION_TOKEN}
        )
        # Should return 200 with empty results for non-existent commessa
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "commessa_id" in data, "Should have commessa_id"
        assert "total_pages" in data, "Should have total_pages"
        print(f"✓ GET /api/smistatore/index returns 200 with auth, total_pages: {data.get('total_pages', 0)}")


class TestSmistatoreScorte:
    """Smistatore scorte endpoint tests"""

    def test_get_scorte_without_auth(self):
        """GET /api/smistatore/scorte should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/smistatore/scorte")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/smistatore/scorte returns 401 without auth")

    def test_get_scorte_with_auth(self):
        """GET /api/smistatore/scorte should return 200 with auth"""
        response = requests.get(
            f"{BASE_URL}/api/smistatore/scorte",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_scorte" in data, "Should have total_scorte"
        assert "scorte" in data, "Should have scorte array"
        print(f"✓ GET /api/smistatore/scorte returns 200 with auth, total: {data.get('total_scorte', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

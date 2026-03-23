"""
Test iteration 248: Onboarding endpoints for NormaFacile 2.0
Tests:
- GET /api/onboarding/status - auto-detection of step completion
- POST /api/onboarding/dismiss - marks onboarding as dismissed
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_COOKIE = 'session_token=test_session_token_for_dev_2026'


class TestOnboardingStatus:
    """Test GET /api/onboarding/status endpoint"""
    
    def test_onboarding_status_returns_200(self):
        """Test that onboarding status endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_onboarding_status_has_required_fields(self):
        """Test that response contains all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required top-level fields
        assert 'steps' in data, "Missing 'steps' field"
        assert 'completed_count' in data, "Missing 'completed_count' field"
        assert 'total_steps' in data, "Missing 'total_steps' field"
        assert 'all_completed' in data, "Missing 'all_completed' field"
        assert 'dismissed' in data, "Missing 'dismissed' field"
        assert 'show_onboarding' in data, "Missing 'show_onboarding' field"
    
    def test_onboarding_status_steps_structure(self):
        """Test that steps object has all 4 required step keys"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        
        steps = data['steps']
        assert 'company_configured' in steps, "Missing 'company_configured' step"
        assert 'first_client' in steps, "Missing 'first_client' step"
        assert 'first_preventivo' in steps, "Missing 'first_preventivo' step"
        assert 'first_commessa' in steps, "Missing 'first_commessa' step"
        
        # All step values should be boolean
        for key, value in steps.items():
            assert isinstance(value, bool), f"Step '{key}' should be boolean, got {type(value)}"
    
    def test_onboarding_status_auto_detection(self):
        """Test that steps are auto-detected based on user data"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Test user has clients, preventivi, commesse but NO company settings
        steps = data['steps']
        assert steps['company_configured'] == False, "company_configured should be False (no company settings)"
        assert steps['first_client'] == True, "first_client should be True (user has clients)"
        assert steps['first_preventivo'] == True, "first_preventivo should be True (user has preventivi)"
        assert steps['first_commessa'] == True, "first_commessa should be True (user has commesse)"
    
    def test_onboarding_completed_count_matches_steps(self):
        """Test that completed_count matches actual completed steps"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        
        steps = data['steps']
        actual_completed = sum(1 for v in steps.values() if v)
        assert data['completed_count'] == actual_completed, \
            f"completed_count ({data['completed_count']}) doesn't match actual ({actual_completed})"
    
    def test_onboarding_total_steps_is_4(self):
        """Test that total_steps is always 4"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['total_steps'] == 4, f"total_steps should be 4, got {data['total_steps']}"
    
    def test_onboarding_show_onboarding_logic(self):
        """Test show_onboarding is True when not dismissed and not all completed"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        
        # show_onboarding should be: not dismissed AND not all_completed
        expected = not data['dismissed'] and not data['all_completed']
        assert data['show_onboarding'] == expected, \
            f"show_onboarding should be {expected}, got {data['show_onboarding']}"


class TestOnboardingDismiss:
    """Test POST /api/onboarding/dismiss endpoint"""
    
    def test_dismiss_returns_200(self):
        """Test that dismiss endpoint returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/dismiss",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_dismiss_returns_message(self):
        """Test that dismiss returns success message"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/dismiss",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data, "Missing 'message' field in response"
        assert data['message'] == "Onboarding nascosto", f"Unexpected message: {data['message']}"
    
    def test_dismiss_updates_status(self):
        """Test that dismiss updates the onboarding status"""
        # First dismiss
        dismiss_response = requests.post(
            f"{BASE_URL}/api/onboarding/dismiss",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert dismiss_response.status_code == 200
        
        # Then check status
        status_response = requests.get(
            f"{BASE_URL}/api/onboarding/status",
            headers={'Cookie': SESSION_COOKIE}
        )
        assert status_response.status_code == 200
        data = status_response.json()
        
        assert data['dismissed'] == True, "dismissed should be True after dismiss"
        assert data['show_onboarding'] == False, "show_onboarding should be False after dismiss"


class TestOnboardingAuth:
    """Test authentication requirements for onboarding endpoints"""
    
    def test_status_requires_auth(self):
        """Test that status endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/onboarding/status")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_dismiss_requires_auth(self):
        """Test that dismiss endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/onboarding/dismiss")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

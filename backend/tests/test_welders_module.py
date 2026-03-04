"""
Welders Module (Registro Saldatori & Patentini) - Backend API Tests
Tests for welder CRUD operations, qualification management, status computation, and search filtering.
"""
import pytest
import requests
import os
import uuid

# API configuration - use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cam-manager-1.preview.emergentagent.com').rstrip('/')
AUTH_TOKEN = "TGOMljLQmmdDakMy3F9zTH_X1-_w2HFsTfcSo8Kbq3Q"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


# ========================
# List & Stats Tests
# ========================

class TestWeldersList:
    """Tests for GET /api/welders/ listing and stats"""

    def test_list_all_welders(self, api_client):
        """GET /api/welders/ returns list of welders with stats"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "stats" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 3  # At least seed data

    def test_stats_structure(self, api_client):
        """Stats contain required fields for dashboard"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200
        
        stats = response.json()["stats"]
        required_fields = ["total", "active_welders", "ok", "warning", "expired", "no_qual", "total_qualifications"]
        for field in required_fields:
            assert field in stats, f"Missing stats field: {field}"
        
        # Verify stats values are integers
        for field in required_fields:
            assert isinstance(stats[field], int), f"Stats field {field} should be int"

    def test_welder_item_structure(self, api_client):
        """Each welder item has required fields"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        assert response.status_code == 200
        
        items = response.json()["items"]
        assert len(items) > 0
        
        welder = items[0]
        required_fields = [
            "welder_id", "name", "stamp_id", "role", "is_active",
            "qualifications", "overall_status", "active_quals", 
            "expiring_quals", "expired_quals", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in welder, f"Missing welder field: {field}"


# ========================
# Search & Filter Tests
# ========================

class TestWeldersSearch:
    """Tests for search and filter functionality"""

    def test_search_by_name(self, api_client):
        """Search by name returns matching welders"""
        response = api_client.get(f"{BASE_URL}/api/welders/?search=Marco")
        assert response.status_code == 200
        
        items = response.json()["items"]
        # Should find Marco Bianchi
        assert any("Marco" in w["name"] for w in items)

    def test_search_by_stamp_id(self, api_client):
        """Search by stamp_id (punzone) returns matching welders"""
        response = api_client.get(f"{BASE_URL}/api/welders/?search=MB01")
        assert response.status_code == 200
        
        items = response.json()["items"]
        assert any("MB01" in w["stamp_id"] for w in items)

    def test_search_no_results(self, api_client):
        """Search with non-matching query returns empty list"""
        response = api_client.get(f"{BASE_URL}/api/welders/?search=NONEXISTENT123")
        assert response.status_code == 200
        
        items = response.json()["items"]
        assert len(items) == 0

    def test_stats_unchanged_with_search(self, api_client):
        """Stats represent global counts regardless of search filter"""
        # Get global stats
        global_response = api_client.get(f"{BASE_URL}/api/welders/")
        global_stats = global_response.json()["stats"]
        
        # Get filtered stats
        filtered_response = api_client.get(f"{BASE_URL}/api/welders/?search=Marco")
        filtered_stats = filtered_response.json()["stats"]
        
        # Stats should be the same (global counts)
        assert global_stats["total"] == filtered_stats["total"]
        assert global_stats["total_qualifications"] == filtered_stats["total_qualifications"]


# ========================
# Status Computation Tests
# ========================

class TestStatusComputation:
    """Tests for dynamic status computation based on expiry dates"""

    def test_scaduto_status_for_expired(self, api_client):
        """Qualification with past expiry date has 'scaduto' status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find welder with expired qualification (Luca Verdi)
        luca = next((w for w in items if "Luca" in w["name"]), None)
        if luca:
            expired_quals = [q for q in luca["qualifications"] if q["status"] == "scaduto"]
            assert len(expired_quals) > 0, "Luca should have expired qualifications"
            # Check days_until_expiry is negative for expired
            for q in expired_quals:
                assert q["days_until_expiry"] < 0, "Expired qual should have negative days"

    def test_in_scadenza_status_within_30_days(self, api_client):
        """Qualification expiring within 30 days has 'in_scadenza' status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find welder with expiring qualification (Marco Bianchi)
        marco = next((w for w in items if "Marco" in w["name"]), None)
        if marco:
            expiring_quals = [q for q in marco["qualifications"] if q["status"] == "in_scadenza"]
            for q in expiring_quals:
                assert 0 <= q["days_until_expiry"] <= 30, "In scadenza quals should be within 30 days"

    def test_attivo_status_for_future(self, api_client):
        """Qualification with future expiry (>30 days) has 'attivo' status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find welder with active qualification (Marco Bianchi)
        marco = next((w for w in items if "Marco" in w["name"]), None)
        if marco:
            active_quals = [q for q in marco["qualifications"] if q["status"] == "attivo"]
            for q in active_quals:
                assert q["days_until_expiry"] > 30, "Active quals should be >30 days from expiry"

    def test_overall_status_no_qual(self, api_client):
        """Welder with no qualifications has 'no_qual' overall status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find Andrea Rossi (no qualifications)
        andrea = next((w for w in items if "Andrea" in w["name"]), None)
        if andrea:
            assert andrea["overall_status"] == "no_qual"
            assert len(andrea["qualifications"]) == 0

    def test_overall_status_warning(self, api_client):
        """Welder with some expiring/expired quals has 'warning' overall status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find Marco Bianchi (has expiring and active)
        marco = next((w for w in items if "Marco" in w["name"]), None)
        if marco:
            assert marco["overall_status"] == "warning"
            assert marco["expiring_quals"] > 0 or marco["expired_quals"] > 0

    def test_overall_status_expired(self, api_client):
        """Welder with all expired quals has 'expired' overall status"""
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        
        # Find Luca Verdi (all expired)
        luca = next((w for w in items if "Luca" in w["name"]), None)
        if luca:
            assert luca["overall_status"] == "expired"
            assert luca["active_quals"] == 0
            assert luca["expiring_quals"] == 0
            assert luca["expired_quals"] > 0


# ========================
# Get Single Welder Tests
# ========================

class TestGetSingleWelder:
    """Tests for GET /api/welders/{welder_id}"""

    def test_get_existing_welder(self, api_client):
        """GET existing welder returns full details"""
        # First get list to find a welder_id
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        assert len(items) > 0
        
        welder_id = items[0]["welder_id"]
        
        # Get single welder
        response = api_client.get(f"{BASE_URL}/api/welders/{welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["welder_id"] == welder_id

    def test_get_nonexistent_welder(self, api_client):
        """GET non-existent welder returns 404"""
        response = api_client.get(f"{BASE_URL}/api/welders/wld_nonexistent123")
        assert response.status_code == 404


# ========================
# Welder CRUD Tests
# ========================

class TestWelderCRUD:
    """Tests for welder Create, Read, Update, Delete operations"""
    
    test_welder_id = None
    
    def test_create_welder(self, api_client):
        """POST /api/welders/ creates new welder"""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_Saldatore_{unique_id}",
            "stamp_id": f"TS{unique_id[:4]}",
            "role": "saldatore",
            "phone": "+39 333 9999999",
            "email": f"test_{unique_id}@example.com",
            "hire_date": "2024-01-01",
            "notes": "Test welder for pytest"
        }
        
        response = api_client.post(f"{BASE_URL}/api/welders/", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["stamp_id"] == payload["stamp_id"]
        assert data["role"] == payload["role"]
        assert "welder_id" in data
        assert data["overall_status"] == "no_qual"  # No qualifications initially
        
        # Store for subsequent tests
        TestWelderCRUD.test_welder_id = data["welder_id"]

    def test_read_created_welder(self, api_client):
        """GET /api/welders/{id} returns created welder"""
        assert TestWelderCRUD.test_welder_id is not None
        
        response = api_client.get(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "TEST_Saldatore" in data["name"]

    def test_update_welder(self, api_client):
        """PUT /api/welders/{id} updates welder info"""
        assert TestWelderCRUD.test_welder_id is not None
        
        # Get current data
        get_response = api_client.get(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}")
        current_data = get_response.json()
        
        # Update with modified data
        payload = {
            "name": current_data["name"] + " UPDATED",
            "stamp_id": current_data["stamp_id"],
            "role": "capo_saldatore",  # Changed role
            "phone": current_data.get("phone", ""),
            "email": current_data.get("email", ""),
            "hire_date": current_data.get("hire_date", ""),
            "notes": "Updated via pytest"
        }
        
        response = api_client.put(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "UPDATED" in data["name"]
        assert data["role"] == "capo_saldatore"

    def test_verify_update_persisted(self, api_client):
        """GET after PUT confirms changes persisted in database"""
        assert TestWelderCRUD.test_welder_id is not None
        
        response = api_client.get(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "UPDATED" in data["name"]
        assert data["role"] == "capo_saldatore"

    def test_delete_welder(self, api_client):
        """DELETE /api/welders/{id} removes welder"""
        assert TestWelderCRUD.test_welder_id is not None
        
        response = api_client.delete(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["welder_id"] == TestWelderCRUD.test_welder_id

    def test_verify_delete_removed(self, api_client):
        """GET after DELETE confirms welder no longer exists"""
        assert TestWelderCRUD.test_welder_id is not None
        
        response = api_client.get(f"{BASE_URL}/api/welders/{TestWelderCRUD.test_welder_id}")
        assert response.status_code == 404

    def test_update_nonexistent_welder(self, api_client):
        """PUT on non-existent welder returns 404"""
        payload = {
            "name": "Test",
            "stamp_id": "XX99",
            "role": "saldatore"
        }
        response = api_client.put(f"{BASE_URL}/api/welders/wld_nonexistent123", json=payload)
        assert response.status_code == 404

    def test_delete_nonexistent_welder(self, api_client):
        """DELETE on non-existent welder returns 404"""
        response = api_client.delete(f"{BASE_URL}/api/welders/wld_nonexistent123")
        assert response.status_code == 404


# ========================
# Qualification CRUD Tests
# ========================

class TestQualificationCRUD:
    """Tests for qualification Create and Delete operations"""
    
    test_welder_id = None
    test_qual_id = None

    def test_setup_create_test_welder(self, api_client):
        """Create a test welder for qualification tests"""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_QualWelder_{unique_id}",
            "stamp_id": f"QW{unique_id[:4]}",
            "role": "saldatore",
            "notes": "For qualification tests"
        }
        
        response = api_client.post(f"{BASE_URL}/api/welders/", json=payload)
        assert response.status_code == 200
        TestQualificationCRUD.test_welder_id = response.json()["welder_id"]

    def test_add_qualification(self, api_client):
        """POST /api/welders/{id}/qualifications adds qualification (multipart form)"""
        assert TestQualificationCRUD.test_welder_id is not None
        
        # Use multipart form data (no file)
        data = {
            "standard": "ISO 9606-1",
            "process": "135 (MAG)",
            "material_group": "FM1",
            "thickness_range": "3-30mm",
            "position": "PA, PB, PC",
            "issue_date": "2024-06-01",
            "expiry_date": "2027-06-01",  # Future date = active
            "notes": "Test qualification"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}/qualifications",
            data=data,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            cookies={"session_token": AUTH_TOKEN}
        )
        assert response.status_code == 200
        
        welder_data = response.json()
        assert len(welder_data["qualifications"]) == 1
        
        qual = welder_data["qualifications"][0]
        assert qual["standard"] == "ISO 9606-1"
        assert qual["process"] == "135 (MAG)"
        assert qual["status"] == "attivo"  # Future expiry = active
        
        TestQualificationCRUD.test_qual_id = qual["qual_id"]

    def test_verify_qualification_persisted(self, api_client):
        """GET welder after adding qualification confirms persistence"""
        assert TestQualificationCRUD.test_welder_id is not None
        
        response = api_client.get(f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["qualifications"]) == 1
        assert data["overall_status"] == "ok"  # Has active qualification
        assert data["active_quals"] == 1

    def test_delete_qualification(self, api_client):
        """DELETE /api/welders/{id}/qualifications/{qual_id} removes qualification"""
        assert TestQualificationCRUD.test_welder_id is not None
        assert TestQualificationCRUD.test_qual_id is not None
        
        response = api_client.delete(
            f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}/qualifications/{TestQualificationCRUD.test_qual_id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data

    def test_verify_qualification_deleted(self, api_client):
        """GET welder after deleting qualification confirms removal"""
        assert TestQualificationCRUD.test_welder_id is not None
        
        response = api_client.get(f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["qualifications"]) == 0
        assert data["overall_status"] == "no_qual"  # No qualifications

    def test_delete_nonexistent_qualification(self, api_client):
        """DELETE non-existent qualification returns 404"""
        assert TestQualificationCRUD.test_welder_id is not None
        
        response = api_client.delete(
            f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}/qualifications/qual_nonexistent123"
        )
        assert response.status_code == 404

    def test_cleanup_delete_test_welder(self, api_client):
        """Cleanup: Delete test welder created for qualification tests"""
        assert TestQualificationCRUD.test_welder_id is not None
        
        response = api_client.delete(f"{BASE_URL}/api/welders/{TestQualificationCRUD.test_welder_id}")
        assert response.status_code == 200


# ========================
# Validation Tests
# ========================

class TestValidation:
    """Tests for input validation"""

    def test_create_welder_requires_name(self, api_client):
        """Creating welder without name fails validation"""
        payload = {
            "name": "",  # Empty name
            "stamp_id": "XX00"
        }
        response = api_client.post(f"{BASE_URL}/api/welders/", json=payload)
        # Pydantic should validate - either 422 or 400
        assert response.status_code in [400, 422, 500]

    def test_create_welder_requires_stamp_id(self, api_client):
        """Creating welder without stamp_id fails validation"""
        payload = {
            "name": "Test Name",
            "stamp_id": ""  # Empty stamp_id
        }
        response = api_client.post(f"{BASE_URL}/api/welders/", json=payload)
        # Should fail validation
        assert response.status_code in [400, 422, 500]

    def test_qualification_requires_expiry_date(self, api_client):
        """Adding qualification without expiry_date fails validation"""
        # First get any existing welder
        response = api_client.get(f"{BASE_URL}/api/welders/")
        items = response.json()["items"]
        if not items:
            pytest.skip("No welders available for test")
        
        welder_id = items[0]["welder_id"]
        
        # Try adding qualification without expiry_date
        data = {
            "standard": "ISO 9606-1",
            "process": "135 (MAG)",
            # Missing expiry_date
        }
        
        response = requests.post(
            f"{BASE_URL}/api/welders/{welder_id}/qualifications",
            data=data,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        # Should fail - expiry_date is required
        assert response.status_code in [400, 422]

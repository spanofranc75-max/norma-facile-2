"""
Test WPS (Welding Procedure Specification) Module - Iteration 110
Tests EN 1090 compliant WPS generation and CRUD operations.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test session management
TEST_SESSION_TOKEN = None
TEST_USER_ID = None
CREATED_WPS_IDS = []


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """Create test user/session before tests, cleanup after."""
    global TEST_SESSION_TOKEN, TEST_USER_ID
    
    # Create test user and session using mongosh
    timestamp = int(time.time() * 1000)
    user_id = f"test_wps_user_{timestamp}"
    session_token = f"test_wps_session_{timestamp}"
    
    import subprocess
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
      user_id: '{user_id}',
      email: 'test.wps.{timestamp}@example.com',
      name: 'WPS Test User',
      role: 'admin',
      created_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: '{user_id}',
      session_token: '{session_token}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", mongo_script], capture_output=True)
    
    TEST_SESSION_TOKEN = session_token
    TEST_USER_ID = user_id
    
    yield
    
    # Cleanup: Delete test user, session, and all created WPS documents
    cleanup_script = f"""
    use('test_database');
    db.users.deleteOne({{ user_id: '{user_id}' }});
    db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
    db.wps_documents.deleteMany({{ user_id: '{user_id}' }});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)
    print(f"Cleaned up test user: {user_id}")


@pytest.fixture
def auth_headers():
    """Return headers with auth token."""
    return {
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


class TestWPSReferenceData:
    """Tests for GET /api/wps/reference-data (public endpoint)"""
    
    def test_reference_data_returns_200(self):
        """Reference data endpoint should be accessible without auth."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Reference data endpoint returns 200")
    
    def test_reference_data_contains_processes(self):
        """Should return welding processes with correct structure."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        data = response.json()
        
        assert "processes" in data, "Missing 'processes' in response"
        processes = data["processes"]
        
        # Verify all expected processes exist
        expected_codes = ["111", "135", "136", "138", "141", "21", "131"]
        for code in expected_codes:
            assert code in processes, f"Missing process {code}"
            assert "label" in processes[code], f"Process {code} missing label"
        
        print(f"PASS: All {len(expected_codes)} welding processes present")
    
    def test_reference_data_contains_material_groups(self):
        """Should return material groups with EN 1090 data."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        data = response.json()
        
        assert "material_groups" in data, "Missing 'material_groups' in response"
        material_groups = data["material_groups"]
        
        # Verify key material groups
        expected_groups = ["1.1", "1.2", "1.3", "2.1", "8.1", "21.1"]
        for group in expected_groups:
            assert group in material_groups, f"Missing material group {group}"
            mg = material_groups[group]
            assert "label" in mg, f"Material group {group} missing label"
            assert "materials" in mg, f"Material group {group} missing materials list"
        
        print(f"PASS: All {len(expected_groups)} material groups present")
    
    def test_reference_data_contains_positions(self):
        """Should return welding positions with ISO codes."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        data = response.json()
        
        assert "positions" in data, "Missing 'positions' in response"
        positions = data["positions"]
        
        # Verify positions structure
        assert isinstance(positions, list), "Positions should be a list"
        expected_codes = ["PA", "PB", "PC", "PD", "PE", "PF", "PG"]
        position_codes = [p["code"] for p in positions]
        
        for code in expected_codes:
            assert code in position_codes, f"Missing position {code}"
        
        print(f"PASS: All {len(expected_codes)} welding positions present")
    
    def test_reference_data_contains_joint_types(self):
        """Should return joint types (BW, FW, BW+FW)."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        data = response.json()
        
        assert "joint_types" in data, "Missing 'joint_types' in response"
        joint_types = data["joint_types"]
        
        expected_codes = ["BW", "FW", "BW+FW"]
        joint_codes = [j["code"] for j in joint_types]
        
        for code in expected_codes:
            assert code in joint_codes, f"Missing joint type {code}"
        
        print(f"PASS: All {len(expected_codes)} joint types present")
    
    def test_reference_data_contains_exec_classes(self):
        """Should return execution classes (EXC1-EXC4)."""
        response = requests.get(f"{BASE_URL}/api/wps/reference-data")
        data = response.json()
        
        assert "exec_classes" in data, "Missing 'exec_classes' in response"
        exec_classes = data["exec_classes"]
        
        expected_classes = ["EXC1", "EXC2", "EXC3", "EXC4"]
        for exc in expected_classes:
            assert exc in exec_classes, f"Missing exec class {exc}"
            assert "ndt_pct" in exec_classes[exc], f"Exec class {exc} missing ndt_pct"
        
        # Verify NDT percentages
        assert exec_classes["EXC1"]["ndt_pct"] == 0
        assert exec_classes["EXC2"]["ndt_pct"] == 10
        assert exec_classes["EXC3"]["ndt_pct"] == 20
        assert exec_classes["EXC4"]["ndt_pct"] == 100
        
        print("PASS: All execution classes with correct NDT percentages")


class TestWPSSuggestEndpoint:
    """Tests for GET /api/wps/suggest (auth required)"""
    
    def test_suggest_requires_auth(self):
        """Suggest endpoint should require authentication."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            params={"process": "135", "material_group": "1.2", "thickness": 10}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Suggest endpoint requires auth")
    
    def test_suggest_carbon_steel_mag(self, auth_headers):
        """Test suggestion for MAG welding on S355 steel."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "135",
                "material_group": "1.2",
                "thickness": 10,
                "joint_type": "BW",
                "exec_class": "EXC2"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify structure
        assert "process" in data
        assert "material" in data
        assert "suggestion" in data
        assert "qualified_welders" in data
        
        suggestion = data["suggestion"]
        assert "filler_material" in suggestion
        assert "shielding_gas" in suggestion
        assert "preheat" in suggestion
        assert "interpass" in suggestion
        assert "ndt_percentage" in suggestion
        
        # Verify EXC2 NDT is 10%
        assert suggestion["ndt_percentage"] == 10
        
        # For 10mm S355, preheat should not be required (threshold is 25mm)
        assert suggestion["preheat"]["temp_min"] is None or suggestion["preheat"]["temp_min"] == 0
        
        print(f"PASS: Suggest returns valid data for MAG/S355: filler={suggestion['filler_material']}")
    
    def test_suggest_stainless_steel_tig(self, auth_headers):
        """Test suggestion for TIG welding on inox (material group 8.1)."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "141",
                "material_group": "8.1",
                "thickness": 5,
                "joint_type": "FW",
                "exec_class": "EXC3"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        suggestion = data["suggestion"]
        
        # Stainless steel should have no preheat
        assert suggestion["preheat"]["temp_min"] is None
        
        # Interpass max should be 150°C for inox
        assert suggestion["interpass"]["temp_max"] == 150
        
        # EXC3 NDT should be 20%
        assert suggestion["ndt_percentage"] == 20
        
        # Shielding gas should be Argon
        assert "Argon" in suggestion["shielding_gas"] or "I1" in suggestion["shielding_gas"]
        
        print(f"PASS: Suggest returns valid data for TIG/Inox: interpass max={suggestion['interpass']['temp_max']}°C")
    
    def test_suggest_aluminum_mig(self, auth_headers):
        """Test suggestion for MIG welding on aluminum (material group 21.1)."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "131",
                "material_group": "21.1",
                "thickness": 8,
                "joint_type": "BW",
                "exec_class": "EXC2"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        suggestion = data["suggestion"]
        
        # Aluminum should have no preheat
        assert suggestion["preheat"]["temp_min"] is None
        
        # Interpass max should be 120°C for aluminum
        assert suggestion["interpass"]["temp_max"] == 120
        
        # Shielding gas should be Argon
        assert "Argon" in suggestion["shielding_gas"] or "I1" in suggestion["shielding_gas"]
        
        print(f"PASS: Suggest returns valid data for MIG/Aluminum: interpass max={suggestion['interpass']['temp_max']}°C")
    
    def test_suggest_thick_material_preheat(self, auth_headers):
        """Test that thick material (>40mm) recommends preheat."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "135",
                "material_group": "1.2",
                "thickness": 50,  # >40mm should trigger preheat
                "joint_type": "BW",
                "exec_class": "EXC3"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        suggestion = data["suggestion"]
        
        # For 50mm S355, preheat should be recommended
        assert suggestion["preheat"]["temp_min"] is not None
        assert suggestion["preheat"]["temp_min"] > 0
        
        print(f"PASS: Thick material (50mm) correctly recommends preheat >= {suggestion['preheat']['temp_min']}°C")
    
    def test_suggest_exc4_full_ndt(self, auth_headers):
        """Test that EXC4 requires 100% NDT."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "136",
                "material_group": "1.3",
                "thickness": 20,
                "joint_type": "BW+FW",
                "exec_class": "EXC4"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # EXC4 should have 100% NDT
        assert data["suggestion"]["ndt_percentage"] == 100
        
        print("PASS: EXC4 correctly requires 100% NDT")
    
    def test_suggest_invalid_process(self, auth_headers):
        """Test error handling for invalid process code."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "999",
                "material_group": "1.2",
                "thickness": 10
            }
        )
        assert response.status_code == 400
        print("PASS: Invalid process returns 400")
    
    def test_suggest_invalid_material_group(self, auth_headers):
        """Test error handling for invalid material group."""
        response = requests.get(
            f"{BASE_URL}/api/wps/suggest",
            headers=auth_headers,
            params={
                "process": "135",
                "material_group": "99.99",
                "thickness": 10
            }
        )
        assert response.status_code == 400
        print("PASS: Invalid material group returns 400")


class TestWPSCRUD:
    """Tests for WPS CRUD operations"""
    
    def test_create_wps_requires_auth(self):
        """Create WPS should require authentication."""
        response = requests.post(
            f"{BASE_URL}/api/wps/",
            json={
                "title": "Test WPS",
                "process": "135",
                "material_group": "1.2"
            }
        )
        assert response.status_code == 401
        print("PASS: Create WPS requires auth")
    
    def test_create_wps_success(self, auth_headers):
        """Test creating a WPS document."""
        payload = {
            "title": "TEST_WPS S355 MAG",
            "process": "135",
            "material_group": "1.2",
            "base_material": "S355J2",
            "thickness_min": 5,
            "thickness_max": 30,
            "joint_type": "BW",
            "positions": ["PA", "PB"],
            "exec_class": "EXC2",
            "filler_material": "G 46 2 M21 3Si1",
            "filler_standard": "EN ISO 14341",
            "shielding_gas": "M21 (Ar 82% + CO2 18%)",
            "preheat_temp": None,
            "interpass_temp_max": 250,
            "notes": "Test WPS document"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/wps/",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "wps_id" in data
        assert "wps_number" in data
        assert "status" in data
        
        # Verify auto-numbering (should be WPS-001 for first)
        assert data["wps_number"].startswith("WPS-")
        
        # Verify data was persisted correctly
        assert data["title"] == payload["title"]
        assert data["process"] == payload["process"]
        assert data["material_group"] == payload["material_group"]
        assert data["status"] == "bozza"
        
        # Store for later tests
        CREATED_WPS_IDS.append(data["wps_id"])
        
        print(f"PASS: Created WPS {data['wps_number']} with ID {data['wps_id']}")
        return data["wps_id"]
    
    def test_list_wps(self, auth_headers):
        """Test listing WPS documents."""
        # First create one if list is empty
        if not CREATED_WPS_IDS:
            self.test_create_wps_success(auth_headers)
        
        response = requests.get(
            f"{BASE_URL}/api/wps/",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        
        print(f"PASS: List WPS returns {data['total']} documents")
    
    def test_get_wps_by_id(self, auth_headers):
        """Test getting a single WPS by ID."""
        # Ensure we have a WPS to get
        if not CREATED_WPS_IDS:
            self.test_create_wps_success(auth_headers)
        
        wps_id = CREATED_WPS_IDS[0]
        
        response = requests.get(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["wps_id"] == wps_id
        assert "title" in data
        assert "process" in data
        
        print(f"PASS: Get WPS by ID returns correct document")
    
    def test_get_wps_not_found(self, auth_headers):
        """Test 404 for non-existent WPS."""
        response = requests.get(
            f"{BASE_URL}/api/wps/wps_nonexistent123",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("PASS: Non-existent WPS returns 404")
    
    def test_update_wps_status(self, auth_headers):
        """Test updating WPS status field."""
        # Ensure we have a WPS to update
        if not CREATED_WPS_IDS:
            self.test_create_wps_success(auth_headers)
        
        wps_id = CREATED_WPS_IDS[0]
        
        # Update status
        response = requests.put(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers,
            json={"status": "approvato"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "approvato"
        
        # Verify with GET
        get_response = requests.get(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers
        )
        assert get_response.json()["status"] == "approvato"
        
        print("PASS: Update WPS status works and persists")
    
    def test_update_wps_fields(self, auth_headers):
        """Test updating multiple WPS fields."""
        # Ensure we have a WPS to update
        if not CREATED_WPS_IDS:
            self.test_create_wps_success(auth_headers)
        
        wps_id = CREATED_WPS_IDS[0]
        
        update_payload = {
            "title": "TEST_WPS Updated Title",
            "thickness_max": 40,
            "notes": "Updated notes for testing"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers,
            json=update_payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == update_payload["title"]
        assert data["thickness_max"] == update_payload["thickness_max"]
        assert data["notes"] == update_payload["notes"]
        
        print("PASS: Update WPS multiple fields works")
    
    def test_delete_wps(self, auth_headers):
        """Test deleting a WPS document."""
        # Create a new WPS to delete
        create_response = requests.post(
            f"{BASE_URL}/api/wps/",
            headers=auth_headers,
            json={
                "title": "TEST_WPS To Delete",
                "process": "141",
                "material_group": "8.1"
            }
        )
        assert create_response.status_code == 200
        wps_id = create_response.json()["wps_id"]
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(
            f"{BASE_URL}/api/wps/{wps_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
        
        print("PASS: Delete WPS works and resource no longer accessible")
    
    def test_delete_wps_not_found(self, auth_headers):
        """Test 404 when deleting non-existent WPS."""
        response = requests.delete(
            f"{BASE_URL}/api/wps/wps_nonexistent456",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("PASS: Delete non-existent WPS returns 404")


class TestWPSAutoNumbering:
    """Test WPS auto-numbering feature"""
    
    def test_wps_sequential_numbering(self, auth_headers):
        """Test that WPS numbers increment correctly."""
        # Create first WPS
        resp1 = requests.post(
            f"{BASE_URL}/api/wps/",
            headers=auth_headers,
            json={
                "title": "TEST_WPS Number 1",
                "process": "135",
                "material_group": "1.1"
            }
        )
        assert resp1.status_code == 200
        wps1 = resp1.json()
        CREATED_WPS_IDS.append(wps1["wps_id"])
        
        # Create second WPS
        resp2 = requests.post(
            f"{BASE_URL}/api/wps/",
            headers=auth_headers,
            json={
                "title": "TEST_WPS Number 2",
                "process": "136",
                "material_group": "1.2"
            }
        )
        assert resp2.status_code == 200
        wps2 = resp2.json()
        CREATED_WPS_IDS.append(wps2["wps_id"])
        
        # Extract number parts and verify sequence
        num1 = int(wps1["wps_number"].split("-")[1])
        num2 = int(wps2["wps_number"].split("-")[1])
        
        assert num2 == num1 + 1, f"Expected sequential numbering: {wps1['wps_number']} -> {wps2['wps_number']}"
        
        print(f"PASS: WPS auto-numbering works: {wps1['wps_number']} -> {wps2['wps_number']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

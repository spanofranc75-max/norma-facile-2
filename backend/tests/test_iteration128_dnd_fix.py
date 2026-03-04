"""
Iteration 128: Test Kanban DnD Fix
Tests the fix for drag-and-drop on Planning Board that was broken because 
preventivi (non-Draggable) were mixed with commesse (Draggable) causing index mismatches.

The fix: 
- Preventivi stored in separate `acceptedPrevs` state 
- `columns` state now ONLY contains commesse
- Draggable indices are now sequential (0, 1, 2...)

Key endpoints:
- GET /api/commesse/board/view - Returns columns with separated preventivi
- PATCH /api/commesse/{id}/status - Called when card is dropped in new column
- POST /api/commesse/from-preventivo/{preventivo_id} - Create commessa from preventivo
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def session_token():
    """Get or create a test session token"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', """
        use('test_database');
        var session = db.user_sessions.findOne({session_token: /test_session/});
        if (session && new Date(session.expires_at) > new Date()) {
            print('SESSION_TOKEN=' + session.session_token);
            print('USER_ID=' + session.user_id);
        } else {
            var userId = 'test-user-' + Date.now();
            var sessionToken = 'test_session_' + Date.now();
            db.users.updateOne(
                {user_id: userId},
                {$set: {user_id: userId, email: 'test.user.' + Date.now() + '@example.com', name: 'Test User', created_at: new Date()}},
                {upsert: true}
            );
            db.user_sessions.insertOne({
                user_id: userId,
                session_token: sessionToken,
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                created_at: new Date()
            });
            print('SESSION_TOKEN=' + sessionToken);
            print('USER_ID=' + userId);
        }
        """
    ], capture_output=True, text=True)
    
    lines = result.stdout.strip().split('\n')
    token = None
    user_id = None
    for line in lines:
        if line.startswith('SESSION_TOKEN='):
            token = line.split('=')[1]
        if line.startswith('USER_ID='):
            user_id = line.split('=')[1]
    return {"token": token, "user_id": user_id}


@pytest.fixture(scope="module")
def auth_headers(session_token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {session_token['token']}",
        "Content-Type": "application/json"
    }


class TestBoardViewStructure:
    """Test GET /api/commesse/board/view returns correctly structured data for DnD"""

    def test_board_view_returns_columns(self, auth_headers):
        """Board view should return columns array with proper structure"""
        response = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "columns" in data, "Response should contain 'columns' key"
        assert "total" in data, "Response should contain 'total' key"
        
        columns = data["columns"]
        assert isinstance(columns, list), "Columns should be a list"
        assert len(columns) >= 1, "Should have at least one column"
        
        # Each column should have id, label, order, items
        for col in columns:
            assert "id" in col, f"Column missing 'id': {col}"
            assert "label" in col, f"Column missing 'label': {col}"
            assert "order" in col, f"Column missing 'order': {col}"
            assert "items" in col, f"Column missing 'items': {col}"
            assert isinstance(col["items"], list), f"Items should be a list: {col}"

    def test_preventivi_have_is_preventivo_flag(self, auth_headers):
        """Preventivi items should have is_preventivo: true flag"""
        response = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        preventivo_col = next((c for c in data["columns"] if c["id"] == "preventivo"), None)
        
        if preventivo_col:
            preventivi = [i for i in preventivo_col["items"] if i.get("is_preventivo")]
            for prev in preventivi:
                assert prev.get("is_preventivo") == True, "Preventivo should have is_preventivo=True"
                assert "preventivo_id" in prev, "Preventivo should have preventivo_id field"
                # commessa_id should equal preventivo_id (both have prev_ prefix)
                assert prev["commessa_id"] == prev["preventivo_id"], \
                    f"commessa_id ({prev['commessa_id']}) should equal preventivo_id ({prev['preventivo_id']})"

    def test_commesse_have_no_is_preventivo_flag(self, auth_headers):
        """Regular commesse items should NOT have is_preventivo flag or have it as false"""
        response = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for col in data["columns"]:
            commesse = [i for i in col["items"] if not i.get("is_preventivo")]
            for comm in commesse:
                # Either no is_preventivo field or is_preventivo=False
                assert not comm.get("is_preventivo"), \
                    f"Commessa should not have is_preventivo=True: {comm.get('commessa_id')}"


class TestStatusUpdate:
    """Test PATCH /api/commesse/{id}/status - Critical for DnD functionality"""

    def test_create_commessa_and_update_status(self, auth_headers):
        """Create a test commessa and verify status can be updated (DnD operation)"""
        # Create a commessa
        create_payload = {
            "title": f"TEST_DnD_Commessa_{uuid.uuid4().hex[:8]}",
            "priority": "media",
            "value": 1000.0
        }
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        
        commessa = create_response.json()
        commessa_id = commessa["commessa_id"]
        initial_status = commessa.get("status", "preventivo")
        
        # Test status update - this is what DnD calls
        new_status = "lavorazione"  # Move to different column
        patch_response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            headers=auth_headers,
            json={"new_status": new_status}
        )
        assert patch_response.status_code == 200, f"Status update failed: {patch_response.text}"
        
        updated = patch_response.json()
        assert updated["status"] == new_status, f"Status should be {new_status}, got {updated['status']}"
        
        # Verify with GET
        get_response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == new_status
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)

    def test_status_update_invalid_status(self, auth_headers):
        """Updating to invalid status should fail with 422"""
        # Create a commessa first
        create_payload = {"title": f"TEST_InvalidStatus_{uuid.uuid4().hex[:8]}"}
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        commessa_id = create_response.json()["commessa_id"]
        
        # Try invalid status
        patch_response = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            headers=auth_headers,
            json={"new_status": "invalid_status_xyz"}
        )
        assert patch_response.status_code == 422, f"Should reject invalid status: {patch_response.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)

    def test_status_update_all_valid_statuses(self, auth_headers):
        """Test that all valid Kanban statuses work"""
        valid_statuses = [
            "preventivo", "approvvigionamento", "lavorazione", 
            "conto_lavoro", "pronto_consegna", "montaggio", "completato"
        ]
        
        # Create a commessa
        create_payload = {"title": f"TEST_AllStatuses_{uuid.uuid4().hex[:8]}"}
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        commessa_id = create_response.json()["commessa_id"]
        
        # Test each status
        for status in valid_statuses:
            patch_response = requests.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                headers=auth_headers,
                json={"new_status": status}
            )
            assert patch_response.status_code == 200, f"Status update to {status} failed: {patch_response.text}"
            assert patch_response.json()["status"] == status
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)


class TestCreateCommessaFromPreventivo:
    """Test POST /api/commesse/from-preventivo/{preventivo_id} - 'Crea Commessa' button"""

    def test_create_commessa_from_preventivo(self, auth_headers, session_token):
        """Create preventivo, then create commessa from it"""
        # Create a preventivo first
        prev_payload = {
            "subject": f"TEST_Prev_For_Commessa_{uuid.uuid4().hex[:8]}",
            "client_id": "",
            "lines": [{"description": "Test item", "quantity": 1, "unit_price": 500}]
        }
        prev_response = requests.post(
            f"{BASE_URL}/api/preventivi/",
            headers=auth_headers,
            json=prev_payload
        )
        
        if prev_response.status_code != 201:
            pytest.skip(f"Could not create preventivo: {prev_response.text}")
        
        preventivo = prev_response.json()
        preventivo_id = preventivo["preventivo_id"]
        
        # Create commessa from preventivo
        commessa_response = requests.post(
            f"{BASE_URL}/api/commesse/from-preventivo/{preventivo_id}",
            headers=auth_headers
        )
        assert commessa_response.status_code in [200, 201], \
            f"Create commessa from preventivo failed: {commessa_response.text}"
        
        commessa = commessa_response.json()
        assert "commessa_id" in commessa, "Response should contain commessa_id"
        assert commessa.get("linked_preventivo_id") == preventivo_id or \
               commessa.get("moduli", {}).get("preventivo_id") == preventivo_id, \
               "Commessa should be linked to the preventivo"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}", headers=auth_headers)
        requests.delete(f"{BASE_URL}/api/preventivi/{preventivo_id}", headers=auth_headers)

    def test_create_commessa_from_nonexistent_preventivo(self, auth_headers):
        """Creating commessa from non-existent preventivo should fail"""
        fake_id = f"prev_nonexistent_{uuid.uuid4().hex[:12]}"
        response = requests.post(
            f"{BASE_URL}/api/commesse/from-preventivo/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Should return 404 for non-existent preventivo"


class TestBoardViewSeparation:
    """Test that board view correctly separates preventivi from commesse"""

    def test_board_items_structure(self, auth_headers):
        """Verify board items have required fields for DnD"""
        response = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for col in data["columns"]:
            for item in col["items"]:
                # All items must have commessa_id (used as draggableId)
                assert "commessa_id" in item, f"Item missing commessa_id: {item}"
                
                # Items must have status matching their column
                # (preventivi might not have status field in the same way)
                if not item.get("is_preventivo"):
                    # Regular commesse should have status
                    assert "status" in item, f"Commessa missing status: {item}"

    def test_preventivi_only_in_preventivo_column(self, auth_headers):
        """Preventivi (is_preventivo=True) should only appear in 'preventivo' column"""
        response = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for col in data["columns"]:
            if col["id"] != "preventivo":
                # Other columns should NOT have items with is_preventivo=True
                preventivi_in_wrong_col = [i for i in col["items"] if i.get("is_preventivo")]
                assert len(preventivi_in_wrong_col) == 0, \
                    f"Found preventivi in wrong column '{col['id']}': {preventivi_in_wrong_col}"


class TestDnDEdgeCases:
    """Edge cases related to DnD functionality"""

    def test_multiple_status_updates_in_sequence(self, auth_headers):
        """Simulate rapid DnD moves - multiple status updates"""
        # Create a commessa
        create_payload = {"title": f"TEST_RapidDnD_{uuid.uuid4().hex[:8]}"}
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/",
            headers=auth_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        commessa_id = create_response.json()["commessa_id"]
        
        # Rapid status updates (simulating DnD)
        statuses = ["approvvigionamento", "lavorazione", "conto_lavoro", "pronto_consegna"]
        for status in statuses:
            patch_response = requests.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                headers=auth_headers,
                json={"new_status": status}
            )
            assert patch_response.status_code == 200
            assert patch_response.json()["status"] == status
        
        # Verify final state
        get_response = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        assert get_response.json()["status"] == "pronto_consegna"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)

    def test_status_update_nonexistent_commessa(self, auth_headers):
        """Status update on non-existent commessa should return 404"""
        fake_id = f"com_nonexistent_{uuid.uuid4().hex[:12]}"
        response = requests.patch(
            f"{BASE_URL}/api/commesse/{fake_id}/status",
            headers=auth_headers,
            json={"new_status": "lavorazione"}
        )
        assert response.status_code == 404


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(auth_headers):
    """Cleanup TEST_ prefixed data after all tests"""
    yield
    # Cleanup any leftover test data
    import subprocess
    subprocess.run([
        'mongosh', '--quiet', '--eval', """
        use('test_database');
        db.commesse.deleteMany({title: /^TEST_/});
        db.preventivi.deleteMany({subject: /^TEST_/});
        print('Cleaned up test data');
        """
    ], capture_output=True)

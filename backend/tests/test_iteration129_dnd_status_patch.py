"""
Iteration 129: DnD Status PATCH Endpoint Tests
==============================================
Tests for the Kanban drag-and-drop fix:
1. PATCH /api/commesse/{id}/status - Update status and verify persistence
2. Test ALL valid Kanban status values
3. Test invalid status returns 422
4. Verify board/view reflects status changes
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = None
USER_ID = None
TEST_COMMESSA_IDS = []

# All valid Kanban status values from KANBAN_META
VALID_KANBAN_STATUSES = [
    "preventivo",
    "approvvigionamento",
    "lavorazione",
    "conto_lavoro",
    "pronto_consegna",
    "montaggio",
    "completato"
]


@pytest.fixture(scope="module", autouse=True)
def setup_test_user():
    """Create test user and session for authenticated requests."""
    global SESSION_TOKEN, USER_ID
    
    import subprocess
    import json
    
    # Create unique test user
    timestamp = int(time.time() * 1000)
    user_id = f"test_user_{timestamp}"
    session_token = f"test_session_{timestamp}"
    
    # Create user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.{timestamp}@example.com',
        name: 'Test User DnD',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 24*60*60*1000),
        created_at: new Date()
    }});
    """
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True, text=True
    )
    
    SESSION_TOKEN = session_token
    USER_ID = user_id
    
    yield
    
    # Cleanup: Delete test data
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{ user_id: '{user_id}' }});
    db.user_sessions.deleteMany({{ session_token: '{session_token}' }});
    db.commesse.deleteMany({{ user_id: '{user_id}' }});
    """
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)
    print(f"Cleaned up test user {user_id}")


@pytest.fixture
def auth_headers():
    """Return headers with authentication."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    }


def create_test_commessa(auth_headers, title="Test Commessa DnD"):
    """Helper to create a test commessa and return its ID."""
    response = requests.post(
        f"{BASE_URL}/api/commesse/",
        headers=auth_headers,
        json={
            "title": title,
            "description": "Test commessa for DnD testing",
            "value": 1000.00,
            "priority": "media"
        }
    )
    assert response.status_code == 201, f"Failed to create commessa: {response.text}"
    data = response.json()
    commessa_id = data.get("commessa_id")
    TEST_COMMESSA_IDS.append(commessa_id)
    return commessa_id


class TestPatchStatusEndpoint:
    """Tests for PATCH /api/commesse/{id}/status endpoint."""
    
    def test_patch_status_preventivo_to_lavorazione(self, auth_headers):
        """CRITICAL: Create commessa, update status from preventivo to lavorazione, verify persistence."""
        # Create test commessa
        commessa_id = create_test_commessa(auth_headers, "TEST_DnD_Status_1")
        
        # Verify initial status is 'preventivo'
        get_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        initial_data = get_resp.json()
        assert initial_data.get("status") == "preventivo", f"Expected initial status 'preventivo', got {initial_data.get('status')}"
        
        # Update status to 'lavorazione'
        patch_resp = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            headers=auth_headers,
            json={"new_status": "lavorazione"}
        )
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.text}"
        patch_data = patch_resp.json()
        assert patch_data.get("status") == "lavorazione", f"PATCH response status mismatch: {patch_data.get('status')}"
        
        # GET to verify persistence
        verify_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data.get("status") == "lavorazione", f"Status not persisted: {verify_data.get('status')}"
        
        print(f"PASS: Status updated from 'preventivo' to 'lavorazione' and persisted correctly")
    
    def test_patch_all_valid_kanban_statuses(self, auth_headers):
        """CRITICAL: Test ALL valid Kanban status values."""
        # Create test commessa
        commessa_id = create_test_commessa(auth_headers, "TEST_DnD_AllStatuses")
        
        for status in VALID_KANBAN_STATUSES:
            # Update to this status
            patch_resp = requests.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                headers=auth_headers,
                json={"new_status": status}
            )
            assert patch_resp.status_code == 200, f"PATCH to '{status}' failed: {patch_resp.text}"
            
            # Verify persistence
            get_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
            assert get_resp.status_code == 200
            data = get_resp.json()
            assert data.get("status") == status, f"Status '{status}' not persisted, got: {data.get('status')}"
            print(f"  PASS: Status '{status}' accepted and persisted")
        
        print(f"PASS: All {len(VALID_KANBAN_STATUSES)} Kanban statuses work correctly")
    
    def test_patch_invalid_status_returns_422(self, auth_headers):
        """CRITICAL: Test invalid status returns 422."""
        # Create test commessa
        commessa_id = create_test_commessa(auth_headers, "TEST_DnD_InvalidStatus")
        
        invalid_statuses = ["invalid_status", "LAVORAZIONE", "working", "done", ""]
        
        for invalid in invalid_statuses:
            patch_resp = requests.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                headers=auth_headers,
                json={"new_status": invalid}
            )
            assert patch_resp.status_code == 422, f"Expected 422 for '{invalid}', got {patch_resp.status_code}"
            print(f"  PASS: Invalid status '{invalid}' correctly rejected with 422")
        
        print("PASS: All invalid statuses correctly rejected with 422")
    
    def test_patch_status_not_found(self, auth_headers):
        """Test PATCH on non-existent commessa returns 404."""
        patch_resp = requests.patch(
            f"{BASE_URL}/api/commesse/nonexistent_commessa_id/status",
            headers=auth_headers,
            json={"new_status": "lavorazione"}
        )
        assert patch_resp.status_code == 404, f"Expected 404, got {patch_resp.status_code}"
        print("PASS: Non-existent commessa correctly returns 404")


class TestBoardViewAfterStatusChange:
    """Tests for GET /api/commesse/board/view after status changes."""
    
    def test_board_view_shows_commessa_in_correct_column(self, auth_headers):
        """After PATCH, GET board/view must show commessa in the new column."""
        # Create test commessa
        commessa_id = create_test_commessa(auth_headers, "TEST_BoardView_Column")
        
        # Update status to 'conto_lavoro'
        patch_resp = requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            headers=auth_headers,
            json={"new_status": "conto_lavoro"}
        )
        assert patch_resp.status_code == 200
        
        # Get board view
        board_resp = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert board_resp.status_code == 200
        board_data = board_resp.json()
        
        # Find the conto_lavoro column
        columns = board_data.get("columns", [])
        conto_lavoro_col = next((c for c in columns if c.get("id") == "conto_lavoro"), None)
        assert conto_lavoro_col is not None, "Column 'conto_lavoro' not found in board view"
        
        # Verify commessa is in the column
        items = conto_lavoro_col.get("items", [])
        commessa_in_column = next((i for i in items if i.get("commessa_id") == commessa_id), None)
        assert commessa_in_column is not None, f"Commessa {commessa_id} not found in 'conto_lavoro' column"
        
        print(f"PASS: Commessa correctly appears in 'conto_lavoro' column after status change")
    
    def test_board_view_column_structure(self, auth_headers):
        """Verify board/view returns correct column structure."""
        board_resp = requests.get(f"{BASE_URL}/api/commesse/board/view", headers=auth_headers)
        assert board_resp.status_code == 200
        board_data = board_resp.json()
        
        columns = board_data.get("columns", [])
        assert len(columns) == 7, f"Expected 7 columns, got {len(columns)}"
        
        expected_columns = {
            "preventivo": "Nuove Commesse",
            "approvvigionamento": "Approvvigionamento",
            "lavorazione": "In Lavorazione",
            "conto_lavoro": "Conto Lavoro",
            "pronto_consegna": "Pronto / Consegna",
            "montaggio": "Montaggio / Posa",
            "completato": "Completato"
        }
        
        for col in columns:
            col_id = col.get("id")
            assert col_id in expected_columns, f"Unexpected column id: {col_id}"
            assert col.get("label") == expected_columns[col_id], f"Wrong label for {col_id}"
            assert "items" in col, f"Column {col_id} missing 'items' array"
            assert "order" in col, f"Column {col_id} missing 'order' field"
        
        print("PASS: Board view column structure is correct")


class TestStatusUpdateChain:
    """Test rapid status updates (simulating fast drag-and-drop)."""
    
    def test_rapid_status_changes(self, auth_headers):
        """Simulate rapid DnD status changes."""
        commessa_id = create_test_commessa(auth_headers, "TEST_RapidStatusChanges")
        
        # Chain of status changes
        status_chain = ["approvvigionamento", "lavorazione", "conto_lavoro", "pronto_consegna", "completato"]
        
        for status in status_chain:
            patch_resp = requests.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                headers=auth_headers,
                json={"new_status": status}
            )
            assert patch_resp.status_code == 200, f"Failed to update to {status}: {patch_resp.text}"
        
        # Final verification
        get_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        final_status = get_resp.json().get("status")
        assert final_status == "completato", f"Final status should be 'completato', got {final_status}"
        
        # Verify status_history contains all changes
        status_history = get_resp.json().get("status_history", [])
        assert len(status_history) >= len(status_chain), f"Status history should have at least {len(status_chain)} entries"
        
        print(f"PASS: Rapid status chain completed: {' -> '.join(status_chain)}")


class TestOptimisticUpdateRollback:
    """Test scenarios related to optimistic update and rollback."""
    
    def test_status_update_records_history(self, auth_headers):
        """Verify PATCH /status adds entry to status_history."""
        commessa_id = create_test_commessa(auth_headers, "TEST_StatusHistory")
        
        # Get initial history count
        get_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        initial_history_len = len(get_resp.json().get("status_history", []))
        
        # Update status
        requests.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            headers=auth_headers,
            json={"new_status": "montaggio"}
        )
        
        # Verify history grew
        get_resp = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}", headers=auth_headers)
        new_history = get_resp.json().get("status_history", [])
        assert len(new_history) > initial_history_len, "Status history should grow after update"
        
        # Verify last entry
        last_entry = new_history[-1]
        assert last_entry.get("status") == "montaggio"
        assert "date" in last_entry
        assert "note" in last_entry
        
        print("PASS: Status history correctly updated after PATCH")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

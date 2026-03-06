"""
Test Iteration 146: Chiusura Diretta (Close without certification) feature
Tests the new POST /api/commesse/{commessa_id}/complete-simple endpoint
"""
import pytest
import requests
import os
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token created for user_97c773827822
TEST_SESSION_TOKEN = "test_session_pytest_1772778592685"

# Test commesse from the database
TEST_COMMESSE = {
    "richiesta": "com_a418e85eb68a",      # stato: richiesta (active - can close)
    "richiesta_2": "com_a9450707e479",    # stato: richiesta (active - can close)
    "firmato": "com_1fa6adc6ca90",        # stato: firmato (active - can close)
    "chiuso": "com_e8c4810ad476",         # stato: chiuso (should reject)
}

@pytest.fixture
def auth_session():
    """Create authenticated session with test token"""
    session = requests.Session()
    session.cookies.set("session_token", TEST_SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCompleteSimpleEndpoint:
    """Test the new POST /api/commesse/{commessa_id}/complete-simple endpoint"""
    
    def test_endpoint_exists_and_accessible(self, auth_session):
        """Verify endpoint exists and responds (not 404)"""
        # Use a commessa that can be closed
        commessa_id = TEST_COMMESSE["firmato"]
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/complete-simple",
            json={"note": "Test note"}
        )
        # Should be 200 success or 400 validation error, NOT 404/405
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}, body: {response.text}"
        print(f"✓ Endpoint accessible, status: {response.status_code}")
    
    def test_close_commessa_from_firmato_state(self, auth_session):
        """Test closing a commessa from 'firmato' state - should succeed"""
        commessa_id = TEST_COMMESSE["firmato"]
        
        # First, get current state
        get_response = auth_session.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert get_response.status_code == 200, f"Failed to get commessa: {get_response.text}"
        initial_state = get_response.json()
        print(f"Initial stato: {initial_state.get('stato')}")
        
        # If already closed from previous test run, reset it first
        if initial_state.get('stato') == 'chiuso':
            # Reset to firmato for test
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017")
            db = client.test_database
            db.commesse.update_one(
                {"commessa_id": commessa_id},
                {"$set": {"stato": "firmato", "status": "lavorazione"}}
            )
            client.close()
            print("Reset commessa to firmato state for test")
        
        # Close the commessa
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/complete-simple",
            json={"note": "Test chiusura diretta from firmato"}
        )
        
        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response data
        assert "message" in data, "Response should contain 'message'"
        assert data.get("stato") == "chiuso", f"Expected stato='chiuso', got {data.get('stato')}"
        assert data.get("stato_label") == "Chiuso", f"Expected stato_label='Chiuso', got {data.get('stato_label')}"
        print(f"✓ Commessa closed successfully: {data}")
        
        # Verify database state changed
        verify_response = auth_session.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert verify_response.status_code == 200
        updated_commessa = verify_response.json()
        assert updated_commessa.get("stato") == "chiuso", "Stato should be 'chiuso' in database"
        assert updated_commessa.get("status") == "completato", "Kanban status should be 'completato'"
        print(f"✓ Database state verified: stato={updated_commessa.get('stato')}, status={updated_commessa.get('status')}")
    
    def test_close_commessa_from_richiesta_state(self, auth_session):
        """Test closing a commessa from 'richiesta' state - should succeed"""
        commessa_id = TEST_COMMESSE["richiesta_2"]
        
        # Get current state
        get_response = auth_session.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert get_response.status_code == 200
        initial = get_response.json()
        print(f"Initial stato: {initial.get('stato')}")
        
        # If already closed, reset
        if initial.get('stato') == 'chiuso':
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017")
            db = client.test_database
            db.commesse.update_one(
                {"commessa_id": commessa_id},
                {"$set": {"stato": "richiesta", "status": "preventivo"}}
            )
            client.close()
            print("Reset commessa to richiesta state for test")
        
        # Close without note
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/complete-simple",
            json={}  # Empty body, note is optional
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("stato") == "chiuso"
        print(f"✓ Closed from richiesta state: {data}")
    
    def test_reject_close_already_chiuso(self, auth_session):
        """Test that closing an already closed commessa returns 400"""
        commessa_id = TEST_COMMESSE["chiuso"]
        
        # Verify it's in chiuso state
        get_response = auth_session.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert get_response.status_code == 200
        current = get_response.json()
        print(f"Current stato: {current.get('stato')}")
        
        # Ensure it's closed
        if current.get('stato') != 'chiuso':
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017")
            db = client.test_database
            db.commesse.update_one(
                {"commessa_id": commessa_id},
                {"$set": {"stato": "chiuso", "status": "completato"}}
            )
            client.close()
        
        # Try to close again
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/complete-simple",
            json={"note": "Should fail"}
        )
        
        assert response.status_code == 400, f"Expected 400 for already closed, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        assert "chiuso" in data["detail"].lower() or "non permessa" in data["detail"].lower(), f"Error message should mention state issue: {data['detail']}"
        print(f"✓ Correctly rejected close on already-chiuso commessa: {data['detail']}")
    
    def test_event_chiusura_diretta_recorded(self, auth_session):
        """Test that CHIUSURA_DIRETTA event is recorded in timeline"""
        commessa_id = TEST_COMMESSE["richiesta"]
        
        # Reset commessa state if needed
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client.test_database
        
        # Reset to active state
        db.commesse.update_one(
            {"commessa_id": commessa_id},
            {"$set": {"stato": "richiesta", "status": "preventivo"}}
        )
        
        # Close the commessa
        note_text = "Lavoro semplice completato senza certificazione"
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/complete-simple",
            json={"note": note_text}
        )
        
        assert response.status_code == 200, f"Failed to close: {response.text}"
        
        # Verify event was recorded
        commessa = db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "eventi": 1})
        client.close()
        
        assert commessa is not None, "Commessa not found"
        eventi = commessa.get("eventi", [])
        
        # Find CHIUSURA_DIRETTA event
        chiusura_eventi = [e for e in eventi if e.get("tipo") == "CHIUSURA_DIRETTA"]
        assert len(chiusura_eventi) > 0, f"CHIUSURA_DIRETTA event not found in timeline. Events: {[e.get('tipo') for e in eventi]}"
        
        latest_chiusura = chiusura_eventi[-1]
        assert note_text in latest_chiusura.get("note", ""), f"Event note should contain our note: {latest_chiusura.get('note')}"
        print(f"✓ CHIUSURA_DIRETTA event recorded: {latest_chiusura}")
    
    def test_unauthorized_access_rejected(self):
        """Test that unauthorized requests are rejected"""
        session = requests.Session()
        # No auth token
        response = session.post(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSE['richiesta']}/complete-simple",
            json={"note": "test"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthorized access correctly rejected")
    
    def test_nonexistent_commessa_returns_404(self, auth_session):
        """Test that closing a non-existent commessa returns 404"""
        response = auth_session.post(
            f"{BASE_URL}/api/commesse/com_nonexistent_12345/complete-simple",
            json={"note": "test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Non-existent commessa correctly returns 404")


class TestChiusuraDirettaAllowedStates:
    """Test which states allow direct closure"""
    
    def test_allowed_states_list(self):
        """Verify the allowed states for chiusura diretta match requirements"""
        # These are the states that should allow direct closure
        expected_allowed = ["richiesta", "bozza", "rilievo_completato", "firmato", "in_produzione", "fatturato"]
        
        # Read from routes/commesse.py to verify
        with open("/app/backend/routes/commesse.py", "r") as f:
            content = f.read()
        
        # Find CHIUSURA_DIRETTA_ALLOWED definition
        assert "CHIUSURA_DIRETTA_ALLOWED" in content, "CHIUSURA_DIRETTA_ALLOWED constant should exist"
        
        for state in expected_allowed:
            assert state in content, f"State '{state}' should be in allowed list"
        
        # Verify chiuso and sospesa are NOT in the allowed list (they're terminal states)
        # This is done by checking the actual list in the code
        import re
        match = re.search(r'CHIUSURA_DIRETTA_ALLOWED\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            allowed_str = match.group(1)
            assert "chiuso" not in allowed_str.lower(), "'chiuso' should NOT be in allowed states"
            assert "sospesa" not in allowed_str.lower(), "'sospesa' should NOT be in allowed states"
        
        print("✓ Allowed states for chiusura diretta verified")


class TestFrontendButtonVisibility:
    """Test logic for when the button should appear in frontend"""
    
    def test_frontend_button_states_defined(self):
        """Verify CommessaHubPage.js has the correct states for button visibility"""
        with open("/app/frontend/src/pages/CommessaHubPage.js", "r") as f:
            content = f.read()
        
        # Check for CHIUSURA_DIRETTA_STATES constant
        assert "CHIUSURA_DIRETTA_STATES" in content, "CHIUSURA_DIRETTA_STATES should be defined in frontend"
        
        # Verify the button component exists
        assert "Chiudi senza certificazione" in content, "Button text 'Chiudi senza certificazione' should exist"
        assert "action-CHIUSURA_DIRETTA" in content, "data-testid='action-CHIUSURA_DIRETTA' should exist"
        
        # Verify dialog exists
        assert "close-simple-dialog" in content, "Close simple dialog should exist"
        assert "closeSimpleOpen" in content, "closeSimpleOpen state should exist"
        
        print("✓ Frontend button and dialog components verified")
    
    def test_frontend_calls_complete_simple_endpoint(self):
        """Verify frontend calls the correct endpoint"""
        with open("/app/frontend/src/pages/CommessaHubPage.js", "r") as f:
            content = f.read()
        
        assert "complete-simple" in content, "Frontend should call /complete-simple endpoint"
        assert "handleCloseSimple" in content, "Handler function should exist"
        
        print("✓ Frontend endpoint call verified")


# Cleanup fixture to reset test data after tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Reset test commesse to original states after tests"""
    yield
    # Cleanup after all tests
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client.test_database
    
    # Reset commesse to their original states
    reset_data = [
        ("com_1fa6adc6ca90", "firmato", "lavorazione"),
        ("com_a418e85eb68a", "richiesta", "completato"),
        ("com_a9450707e479", "richiesta", "approvvigionamento"),
        ("com_e8c4810ad476", "chiuso", "completato"),
    ]
    
    for commessa_id, stato, status in reset_data:
        db.commesse.update_one(
            {"commessa_id": commessa_id},
            {"$set": {"stato": stato, "status": status}}
        )
    
    # Don't clean up session tokens - they may still be needed
    # db.user_sessions.delete_many({"session_token": {"$regex": "test_session"}})
    
    client.close()
    print("✓ Test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
Iteration 127: Testing Accepted Preventivi on Planning Board

Tests the feature where accepted quotes (preventivi with status 'accettato')
without a linked commessa appear on the Planning Board's Kanban view.

Test scenarios:
1. GET /api/commesse/board/view returns accepted preventivi in 'preventivo' column
2. Preventivi items have is_preventivo: true flag
3. Preventivi items have commessa_id prefixed with 'prev_'
4. Preventivi with linked commessa do NOT appear as separate items
5. Fields: commessa_id, preventivo_id, is_preventivo, title, numero, client_name, value
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Use existing session token from previous iterations
AUTH_TOKEN = "a93tNVox2FkeFH8NRffvMIy09_aExaDt2X6zYAPFwPU"


@pytest.fixture
def auth_headers():
    """Auth headers with session token"""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def api_client(auth_headers):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update(auth_headers)
    return session


class TestBoardViewEndpoint:
    """Test GET /api/commesse/board/view endpoint"""
    
    def test_board_view_returns_columns(self, api_client):
        """Board view returns kanban columns structure"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "columns" in data, "Response should have 'columns' key"
        assert "total" in data, "Response should have 'total' key"
        assert isinstance(data["columns"], list), "Columns should be a list"
        
        # Verify column structure
        column_ids = [col["id"] for col in data["columns"]]
        assert "preventivo" in column_ids, "Should have 'preventivo' column"
        print(f"PASS: Board view returns {len(data['columns'])} columns, total {data['total']} items")
    
    def test_preventivo_column_has_label(self, api_client):
        """Preventivo column has 'Nuove Commesse' label"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        preventivo_col = next((c for c in data["columns"] if c["id"] == "preventivo"), None)
        assert preventivo_col is not None, "Should have preventivo column"
        assert preventivo_col["label"] == "Nuove Commesse", f"Wrong label: {preventivo_col.get('label')}"
        print(f"PASS: Preventivo column label is 'Nuove Commesse'")


class TestAcceptedPreventiviOnBoard:
    """Test accepted preventivi without linked commessa appear on board"""
    
    def test_accepted_preventivi_in_preventivo_column(self, api_client):
        """Board view includes accepted preventivi without linked commessa"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        preventivo_col = next((c for c in data["columns"] if c["id"] == "preventivo"), None)
        assert preventivo_col is not None
        
        # Check if there are any preventivo items (with is_preventivo flag)
        preventivo_items = [item for item in preventivo_col["items"] if item.get("is_preventivo")]
        commessa_items = [item for item in preventivo_col["items"] if not item.get("is_preventivo")]
        
        print(f"Preventivo column: {len(preventivo_items)} preventivi, {len(commessa_items)} commesse")
        
        # Verify structure of preventivo items
        for item in preventivo_items:
            assert item.get("is_preventivo") == True, "Should have is_preventivo=True"
            assert item.get("commessa_id", "").startswith("prev_"), f"commessa_id should start with 'prev_': {item.get('commessa_id')}"
            assert "preventivo_id" in item, "Should have preventivo_id"
            assert "title" in item, "Should have title"
            assert "client_name" in item, "Should have client_name"
            assert "value" in item, "Should have value"
            print(f"  - Preventivo: {item.get('numero')} - {item.get('title')} ({item.get('client_name')}) = {item.get('value')} EUR")
        
        print(f"PASS: Found {len(preventivo_items)} accepted preventivi on board")
    
    def test_preventivo_item_structure(self, api_client):
        """Verify preventivo item has correct fields"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        preventivo_col = next((c for c in data["columns"] if c["id"] == "preventivo"), None)
        preventivo_items = [item for item in preventivo_col["items"] if item.get("is_preventivo")]
        
        if not preventivo_items:
            pytest.skip("No accepted preventivi without linked commessa found")
        
        # Test first preventivo item
        item = preventivo_items[0]
        
        # Required fields
        assert "commessa_id" in item, "Missing commessa_id"
        assert "preventivo_id" in item, "Missing preventivo_id"
        assert "is_preventivo" in item, "Missing is_preventivo"
        assert "title" in item, "Missing title"
        assert "numero" in item, "Missing numero"
        assert "client_name" in item, "Missing client_name"
        assert "value" in item, "Missing value"
        assert "status" in item, "Missing status"
        
        # Verify values
        assert item["is_preventivo"] == True
        assert item["commessa_id"].startswith("prev_")
        # commessa_id should equal preventivo_id (both have prev_ prefix)
        assert item["commessa_id"] == item["preventivo_id"]
        assert item["status"] == "preventivo"
        assert isinstance(item["value"], (int, float))
        
        print(f"PASS: Preventivo item has correct structure: {item['numero']}")


class TestPreventiviWithLinkedCommessa:
    """Test that preventivi with linked commessa don't appear as separate items"""
    
    def test_linked_preventivi_not_duplicated(self, api_client):
        """Preventivi already linked to a commessa should NOT appear as separate board items"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        
        # Collect all preventivo_ids from preventivo items
        prev_items_ids = set()
        # Collect all linked_preventivo_ids from commesse
        linked_prev_ids = set()
        
        for col in data["columns"]:
            for item in col["items"]:
                if item.get("is_preventivo"):
                    prev_items_ids.add(item.get("preventivo_id"))
                else:
                    # This is a commessa - check if it has linked preventivo
                    moduli = item.get("moduli", {})
                    linked_prev = moduli.get("preventivo_id") or item.get("linked_preventivo_id")
                    if linked_prev:
                        linked_prev_ids.add(linked_prev)
        
        # There should be no overlap
        overlap = prev_items_ids.intersection(linked_prev_ids)
        assert len(overlap) == 0, f"These preventivi appear both as items AND are linked to commesse: {overlap}"
        
        print(f"PASS: No duplicate preventivi (board items: {len(prev_items_ids)}, linked: {len(linked_prev_ids)})")


class TestCreateAndVerifyPreventivo:
    """Integration test: create accepted preventivo and verify it appears on board"""
    
    def test_new_accepted_preventivo_appears_on_board(self, api_client):
        """Newly created and accepted preventivo should appear on the board"""
        # Create a simple preventivo (it starts as 'bozza' by default)
        unique_num = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "number": unique_num,
            "subject": f"Test Preventivo for Board {unique_num}",
            "client_name": "Test Client Board",
            "lines": [
                {
                    "description": "Test Item for Board",
                    "quantity": 1,
                    "unit": "pz",
                    "unit_price": 100.00
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        if response.status_code != 201:
            pytest.skip(f"Could not create test preventivo: {response.status_code} - {response.text}")
        
        prev_id = response.json().get("preventivo_id")
        print(f"Created test preventivo: {prev_id}")
        
        try:
            # Update status to 'accettato' (required for it to appear on board)
            update_response = api_client.put(
                f"{BASE_URL}/api/preventivi/{prev_id}",
                json={"status": "accettato"}
            )
            assert update_response.status_code == 200, f"Failed to update status: {update_response.text}"
            print(f"Updated preventivo status to 'accettato'")
            
            # Get board view
            board_response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
            assert board_response.status_code == 200
            
            data = board_response.json()
            preventivo_col = next((c for c in data["columns"] if c["id"] == "preventivo"), None)
            assert preventivo_col is not None
            
            # Find our test preventivo
            test_item = None
            for item in preventivo_col["items"]:
                if item.get("preventivo_id") == prev_id:
                    test_item = item
                    break
            
            assert test_item is not None, f"Test preventivo {prev_id} should appear on board"
            
            # Verify structure
            assert test_item["is_preventivo"] == True
            assert test_item["commessa_id"] == prev_id
            assert "Test Preventivo for Board" in test_item["title"]
            
            print(f"PASS: New accepted preventivo appears on board: {test_item['numero']}")
        finally:
            # Cleanup - delete the test preventivo
            try:
                api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")
                print(f"Cleaned up test preventivo: {prev_id}")
            except:
                pass


class TestPreventivoStatusFilter:
    """Test that only 'accettato' status preventivi appear on board"""
    
    def test_only_accepted_status(self, api_client):
        """Board should only show preventivi with status 'accettato'"""
        # Get all preventivi
        prev_response = api_client.get(f"{BASE_URL}/api/preventivi/")
        if prev_response.status_code != 200:
            pytest.skip("Could not fetch preventivi list")
        
        all_preventivi = prev_response.json().get("preventivi", [])
        accepted_prev_ids = {p["preventivo_id"] for p in all_preventivi if p.get("status") == "accettato"}
        
        print(f"Total preventivi: {len(all_preventivi)}, accepted: {len(accepted_prev_ids)}")
        
        # Get board view
        board_response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert board_response.status_code == 200
        
        data = board_response.json()
        
        # Collect preventivo_ids from board
        board_prev_ids = set()
        for col in data["columns"]:
            for item in col["items"]:
                if item.get("is_preventivo"):
                    board_prev_ids.add(item["preventivo_id"])
        
        # All board preventivi should be from accepted set (minus those already linked to commesse)
        for prev_id in board_prev_ids:
            assert prev_id in accepted_prev_ids, f"Preventivo {prev_id} on board is not in accepted status"
        
        print(f"PASS: Board shows {len(board_prev_ids)} preventivi, all have 'accettato' status")


class TestDragAndDropPrevention:
    """Test that drag operations on preventivi are handled correctly"""
    
    def test_preventivo_item_has_is_preventivo_flag(self, api_client):
        """Preventivo items must have is_preventivo=true for frontend to prevent drag"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        
        for col in data["columns"]:
            for item in col["items"]:
                if item.get("commessa_id", "").startswith("prev_"):
                    # This is a preventivo item
                    assert item.get("is_preventivo") == True, \
                        f"Preventivo item {item['commessa_id']} missing is_preventivo=true"
        
        print("PASS: All preventivo items have is_preventivo=true flag")
    
    def test_preventivo_commessa_id_prefix(self, api_client):
        """Preventivo commessa_id should have 'prev_' prefix for drag prevention"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        
        prev_count = 0
        for col in data["columns"]:
            for item in col["items"]:
                if item.get("is_preventivo"):
                    prev_count += 1
                    assert item.get("commessa_id", "").startswith("prev_"), \
                        f"Preventivo {item.get('preventivo_id')} commessa_id should start with 'prev_'"
        
        print(f"PASS: All {prev_count} preventivo items have 'prev_' prefix in commessa_id")


class TestBoardTotals:
    """Test board totals include both commesse and preventivi"""
    
    def test_total_count_includes_preventivi(self, api_client):
        """Board total should include both commesse and preventivi"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        
        # Count items manually
        total_items = 0
        total_commesse = 0
        total_preventivi = 0
        
        for col in data["columns"]:
            for item in col["items"]:
                total_items += 1
                if item.get("is_preventivo"):
                    total_preventivi += 1
                else:
                    total_commesse += 1
        
        # Verify total matches
        assert data["total"] == total_items, \
            f"Total mismatch: API says {data['total']}, counted {total_items}"
        
        print(f"PASS: Board total={data['total']} (commesse={total_commesse}, preventivi={total_preventivi})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

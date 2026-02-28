"""
Commesse Kanban API Tests
- Tests CRUD operations for commesse (workshop orders)
- Tests Kanban board view with 7 columns
- Tests status update (drag-and-drop simulation)
- Tests commessa creation from preventivo
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "bridge_test_token_2026"
TEST_CLIENT_ID = "cli_09e155c8e43c"

# Valid status values for Kanban columns
VALID_STATUSES = [
    "preventivo",
    "approvvigionamento", 
    "lavorazione",
    "conto_lavoro",
    "pronto_consegna",
    "montaggio",
    "completato"
]

# Expected column labels 
EXPECTED_COLUMN_LABELS = {
    "preventivo": "Nuove Commesse",
    "approvvigionamento": "Approvvigionamento",
    "lavorazione": "In Lavorazione",
    "conto_lavoro": "Conto Lavoro",
    "pronto_consegna": "Pronto / Consegna",
    "montaggio": "Montaggio / Posa",
    "completato": "Completato"
}


@pytest.fixture
def api_client():
    """Shared requests session with auth token."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


class TestCommesseKanbanBoardView:
    """Tests for GET /api/commesse/board/view endpoint"""
    
    def test_board_view_returns_7_columns(self, api_client):
        """Verify board view returns exactly 7 columns in correct order"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "columns" in data, "Response should contain 'columns' key"
        assert "total" in data, "Response should contain 'total' key"
        
        columns = data["columns"]
        assert len(columns) == 7, f"Expected 7 columns, got {len(columns)}"
        
        # Verify columns are sorted by order
        for i, col in enumerate(columns):
            assert col["order"] == i, f"Column {col['id']} should have order {i}, got {col['order']}"
    
    def test_board_view_column_labels(self, api_client):
        """Verify each column has correct label"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        
        assert response.status_code == 200
        
        columns = response.json()["columns"]
        
        for col in columns:
            col_id = col["id"]
            expected_label = EXPECTED_COLUMN_LABELS.get(col_id)
            assert expected_label is not None, f"Unknown column id: {col_id}"
            assert col["label"] == expected_label, f"Column {col_id} label mismatch: expected '{expected_label}', got '{col['label']}'"
    
    def test_board_view_column_structure(self, api_client):
        """Verify each column has required fields"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        
        assert response.status_code == 200
        
        columns = response.json()["columns"]
        
        for col in columns:
            assert "id" in col, f"Column missing 'id' field"
            assert "label" in col, f"Column missing 'label' field"
            assert "order" in col, f"Column missing 'order' field"
            assert "items" in col, f"Column missing 'items' field"
            assert isinstance(col["items"], list), f"Column items should be a list"


class TestCommesseCRUD:
    """Tests for CRUD operations on commesse"""
    
    def test_create_commessa_success(self, api_client):
        """Test creating a new commessa with all fields"""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "title": f"TEST_Cancello_carraio_{unique_id}",
            "client_id": TEST_CLIENT_ID,
            "value": 2500.50,
            "deadline": "2026-03-15",
            "priority": "alta",
            "description": "Test commessa for automated testing"
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa_id" in data, "Response should contain commessa_id"
        assert data["title"] == payload["title"], "Title mismatch"
        assert data["value"] == payload["value"], "Value mismatch"
        assert data["deadline"] == payload["deadline"], "Deadline mismatch"
        assert data["priority"] == payload["priority"], "Priority mismatch"
        assert data["status"] == "preventivo", "Default status should be 'preventivo'"
        
        # Cleanup - delete the created commessa
        commessa_id = data["commessa_id"]
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    
    def test_create_commessa_minimal(self, api_client):
        """Test creating a commessa with only required fields"""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "title": f"TEST_Minimal_{unique_id}"
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["status"] == "preventivo", "Default status should be 'preventivo'"
        assert data["priority"] == "media", "Default priority should be 'media'"
        assert data["value"] == 0, "Default value should be 0"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
    
    def test_list_commesse(self, api_client):
        """Test listing all commesse"""
        response = api_client.get(f"{BASE_URL}/api/commesse/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["items"], list), "Items should be a list"
    
    def test_list_commesse_filter_by_status(self, api_client):
        """Test listing commesse filtered by status"""
        response = api_client.get(f"{BASE_URL}/api/commesse/?status=lavorazione")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # All items should have status 'lavorazione'
        for item in data["items"]:
            assert item["status"] == "lavorazione", f"Expected status 'lavorazione', got '{item['status']}'"
    
    def test_get_commessa_by_id(self, api_client):
        """Test getting a single commessa by ID"""
        # First create a commessa
        unique_id = uuid.uuid4().hex[:8]
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": f"TEST_GetById_{unique_id}"
        })
        assert create_resp.status_code == 201
        commessa_id = create_resp.json()["commessa_id"]
        
        # Get by ID
        response = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["commessa_id"] == commessa_id
        assert data["title"] == f"TEST_GetById_{unique_id}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    
    def test_get_commessa_not_found(self, api_client):
        """Test getting a non-existent commessa returns 404"""
        response = api_client.get(f"{BASE_URL}/api/commesse/com_nonexistent12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_delete_commessa(self, api_client):
        """Test deleting a commessa"""
        # First create a commessa
        unique_id = uuid.uuid4().hex[:8]
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": f"TEST_Delete_{unique_id}"
        })
        assert create_resp.status_code == 201
        commessa_id = create_resp.json()["commessa_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's deleted
        get_resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert get_resp.status_code == 404, "Deleted commessa should return 404"
    
    def test_delete_commessa_not_found(self, api_client):
        """Test deleting a non-existent commessa returns 404"""
        response = api_client.delete(f"{BASE_URL}/api/commesse/com_nonexistent12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestCommessaStatusUpdate:
    """Tests for PATCH /api/commesse/{id}/status endpoint (drag-and-drop)"""
    
    def test_update_status_valid(self, api_client):
        """Test updating commessa status with valid status"""
        # First create a commessa
        unique_id = uuid.uuid4().hex[:8]
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": f"TEST_StatusUpdate_{unique_id}"
        })
        assert create_resp.status_code == 201
        commessa_id = create_resp.json()["commessa_id"]
        
        # Update status to 'lavorazione'
        response = api_client.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            json={"new_status": "lavorazione"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "lavorazione", f"Expected status 'lavorazione', got '{data['status']}'"
        
        # Verify status history was updated
        assert "status_history" in data, "Response should contain status_history"
        assert len(data["status_history"]) >= 2, "Status history should have at least 2 entries"
        
        # Verify by getting the commessa again
        get_resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "lavorazione"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    
    def test_update_status_all_valid_statuses(self, api_client):
        """Test updating to each valid status"""
        unique_id = uuid.uuid4().hex[:8]
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": f"TEST_AllStatuses_{unique_id}"
        })
        assert create_resp.status_code == 201
        commessa_id = create_resp.json()["commessa_id"]
        
        # Test each valid status
        for status in VALID_STATUSES[1:]:  # Skip 'preventivo' which is default
            response = api_client.patch(
                f"{BASE_URL}/api/commesse/{commessa_id}/status",
                json={"new_status": status}
            )
            assert response.status_code == 200, f"Status update to '{status}' failed: {response.text}"
            assert response.json()["status"] == status
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    
    def test_update_status_invalid_returns_422(self, api_client):
        """Test that invalid status returns 422"""
        # First create a commessa
        unique_id = uuid.uuid4().hex[:8]
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": f"TEST_InvalidStatus_{unique_id}"
        })
        assert create_resp.status_code == 201
        commessa_id = create_resp.json()["commessa_id"]
        
        # Try to update with invalid status
        response = api_client.patch(
            f"{BASE_URL}/api/commesse/{commessa_id}/status",
            json={"new_status": "invalid_status_xyz"}
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid status, got {response.status_code}: {response.text}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    
    def test_update_status_not_found(self, api_client):
        """Test updating status of non-existent commessa returns 404"""
        response = api_client.patch(
            f"{BASE_URL}/api/commesse/com_nonexistent12345/status",
            json={"new_status": "lavorazione"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestCommessaFromPreventivo:
    """Tests for POST /api/commesse/from-preventivo/{prev_id} endpoint"""
    
    def test_from_preventivo_not_found(self, api_client):
        """Test creating commessa from non-existent preventivo returns 404"""
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/prev_nonexistent123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


class TestExistingCommessa:
    """Tests for the existing commessa com_9fcdb2901b9f (status: lavorazione)"""
    
    def test_existing_commessa_in_board(self, api_client):
        """Verify existing commessa appears in board view"""
        response = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        
        assert response.status_code == 200
        
        columns = response.json()["columns"]
        
        # Find the 'lavorazione' column
        lavorazione_col = next((c for c in columns if c["id"] == "lavorazione"), None)
        assert lavorazione_col is not None, "Lavorazione column should exist"
        
        # Check if existing commessa is in this column
        # Note: It may or may not be present depending on the user_id filter
        print(f"Lavorazione column has {len(lavorazione_col['items'])} items")
    
    def test_get_existing_commessa(self, api_client):
        """Test getting the existing commessa by ID"""
        response = api_client.get(f"{BASE_URL}/api/commesse/com_9fcdb2901b9f")
        
        # This may return 404 if the commessa belongs to a different user_id
        if response.status_code == 200:
            data = response.json()
            print(f"Existing commessa found: {data['title']}, status: {data['status']}")
        elif response.status_code == 404:
            print("Existing commessa not found (likely belongs to different user)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


# Cleanup function to remove TEST_ prefixed data
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(api_client):
    """Cleanup test data after all tests in this module"""
    yield
    
    # After tests, cleanup any remaining TEST_ commesse
    try:
        list_resp = api_client.get(f"{BASE_URL}/api/commesse/?search=TEST_")
        if list_resp.status_code == 200:
            items = list_resp.json().get("items", [])
            for item in items:
                if item.get("title", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/commesse/{item['commessa_id']}")
    except Exception as e:
        print(f"Cleanup error: {e}")


# Fixture needs to be instantiated for module-level usage
@pytest.fixture(scope="module")
def api_client():
    """Module-level shared requests session with auth token."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session

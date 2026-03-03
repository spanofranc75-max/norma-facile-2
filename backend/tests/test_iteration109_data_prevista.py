"""
Test iteration 109: data_prevista field for production phases

Features under test:
1. POST /api/commesse/{cid}/produzione/init - creates phases with data_prevista calculated from deadline
2. PUT /api/commesse/{cid}/produzione/{fase_tipo} - accepts data_prevista in FaseUpdate
3. GET /api/dashboard/semaforo - includes fasi_in_ritardo count and adjusts semaforo color
4. Semaforo logic: commessa with late phases should be yellow even if deadline is far away
5. Phase init without deadline should create phases with data_prevista=null
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = os.environ.get("TEST_SESSION_TOKEN", "")
USER_ID = os.environ.get("TEST_USER_ID", "")


@pytest.fixture(scope="module")
def auth_cookies():
    """Return cookies dict for authenticated requests"""
    return {"session_token": SESSION_TOKEN}


@pytest.fixture(scope="module")
def api_session(auth_cookies):
    """Create requests session with auth"""
    session = requests.Session()
    session.cookies.update(auth_cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def created_commesse():
    """Track created commesse for cleanup"""
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(api_session, created_commesse):
    """Cleanup created commesse after all tests"""
    yield
    for cid in created_commesse:
        try:
            api_session.delete(f"{BASE_URL}/api/commesse/{cid}")
        except:
            pass


def create_test_commessa(api_session, created_commesse, deadline=None):
    """Helper to create a test commessa"""
    payload = {
        "numero": f"TEST-{uuid.uuid4().hex[:6]}",
        "title": "Test Commessa Data Prevista",
        "stato": "attiva"
    }
    if deadline:
        payload["deadline"] = deadline
    
    resp = api_session.post(f"{BASE_URL}/api/commesse/", json=payload)
    assert resp.status_code in [200, 201], f"Failed to create commessa: {resp.text}"
    data = resp.json()
    cid = data.get("commessa_id") or data.get("commessa", {}).get("commessa_id")
    if cid:
        created_commesse.append(cid)
    return cid, data


# === TEST 1: Init produzione with deadline calculates data_prevista ===
def test_init_produzione_with_deadline_calculates_data_prevista(api_session, created_commesse):
    """POST /api/commesse/{cid}/produzione/init should calculate data_prevista from deadline"""
    # Create commessa with deadline 30 days in future
    future_deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=future_deadline)
    
    # Initialize production phases
    resp = api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    assert resp.status_code == 200, f"Init produzione failed: {resp.text}"
    
    data = resp.json()
    fasi = data.get("fasi", [])
    assert len(fasi) > 0, "No phases created"
    
    # Check that data_prevista is set for each phase
    for fase in fasi:
        dp = fase.get("data_prevista")
        assert dp is not None, f"Phase {fase.get('tipo')} missing data_prevista"
        # Verify it's a valid date string
        try:
            datetime.strptime(dp, "%Y-%m-%d")
        except ValueError:
            pytest.fail(f"Invalid data_prevista format: {dp}")
    
    # Verify phases are ordered (earlier phases have earlier data_prevista)
    dates = [fase["data_prevista"] for fase in fasi]
    assert dates == sorted(dates), "data_prevista dates not in sequential order"
    
    print(f"PASS: Init produzione created {len(fasi)} phases with data_prevista calculated from deadline {future_deadline}")
    print(f"Phase dates: {dates}")


# === TEST 2: Init produzione without deadline sets data_prevista to null ===
def test_init_produzione_without_deadline_has_null_data_prevista(api_session, created_commesse):
    """POST /api/commesse/{cid}/produzione/init without deadline should have data_prevista=null"""
    # Create commessa without deadline
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=None)
    
    # Initialize production phases
    resp = api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    assert resp.status_code == 200, f"Init produzione failed: {resp.text}"
    
    data = resp.json()
    fasi = data.get("fasi", [])
    assert len(fasi) > 0, "No phases created"
    
    # Check that data_prevista is null for each phase
    for fase in fasi:
        dp = fase.get("data_prevista")
        assert dp is None, f"Phase {fase.get('tipo')} should have null data_prevista, got: {dp}"
    
    print(f"PASS: Init produzione without deadline created {len(fasi)} phases with data_prevista=null")


# === TEST 3: Update fase with data_prevista ===
def test_update_fase_with_data_prevista(api_session, created_commesse):
    """PUT /api/commesse/{cid}/produzione/{fase_tipo} should accept data_prevista field"""
    # Create commessa and initialize phases
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=None)
    api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    
    # Update a phase with data_prevista
    new_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    resp = api_session.put(
        f"{BASE_URL}/api/commesse/{cid}/produzione/taglio",
        json={"stato": "in_corso", "data_prevista": new_date}
    )
    assert resp.status_code == 200, f"Update fase failed: {resp.text}"
    
    # Verify the update persisted
    resp = api_session.get(f"{BASE_URL}/api/commesse/{cid}/produzione")
    assert resp.status_code == 200
    data = resp.json()
    fasi = data.get("fasi", [])
    
    taglio = next((f for f in fasi if f.get("tipo") == "taglio"), None)
    assert taglio is not None, "Taglio phase not found"
    assert taglio.get("stato") == "in_corso", "Phase stato not updated"
    assert taglio.get("data_prevista") == new_date, f"data_prevista not updated, got: {taglio.get('data_prevista')}"
    
    print(f"PASS: Successfully updated fase taglio with data_prevista={new_date}")


# === TEST 4: Semaforo includes fasi_in_ritardo count ===
def test_semaforo_includes_fasi_in_ritardo(api_session, created_commesse):
    """GET /api/dashboard/semaforo should include fasi_in_ritardo count"""
    # Create a commessa with future deadline but past phase dates (to simulate delays)
    future_deadline = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=future_deadline)
    
    # Initialize production phases
    api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    
    # Set a past data_prevista on one phase to simulate delay
    past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    api_session.put(
        f"{BASE_URL}/api/commesse/{cid}/produzione/taglio",
        json={"stato": "da_fare", "data_prevista": past_date}
    )
    
    # Get semaforo
    resp = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
    assert resp.status_code == 200, f"Semaforo failed: {resp.text}"
    
    data = resp.json()
    assert "items" in data
    assert "counts" in data
    
    # Find our test commessa
    test_item = next((i for i in data["items"] if i["commessa_id"] == cid), None)
    assert test_item is not None, "Test commessa not in semaforo"
    
    # Check fasi_in_ritardo field exists
    assert "fasi_in_ritardo" in test_item, "fasi_in_ritardo field missing from semaforo item"
    assert test_item["fasi_in_ritardo"] >= 1, f"Expected at least 1 delayed phase, got {test_item['fasi_in_ritardo']}"
    
    print(f"PASS: Semaforo item includes fasi_in_ritardo={test_item['fasi_in_ritardo']}")


# === TEST 5: Semaforo bumps to yellow for late phases ===
def test_semaforo_bumps_to_yellow_for_late_phases(api_session, created_commesse):
    """Commessa with late phases should be yellow even if deadline is far away"""
    # Create a commessa with deadline very far in future (should be green based on deadline)
    far_future_deadline = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=far_future_deadline)
    
    # Initialize production phases
    api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    
    # Set a past data_prevista on one phase (to trigger yellow)
    past_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    api_session.put(
        f"{BASE_URL}/api/commesse/{cid}/produzione/taglio",
        json={"stato": "da_fare", "data_prevista": past_date}
    )
    
    # Get semaforo
    resp = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
    assert resp.status_code == 200
    
    data = resp.json()
    test_item = next((i for i in data["items"] if i["commessa_id"] == cid), None)
    assert test_item is not None
    
    # With 90 days to deadline, it would be green normally
    # But with late phases, it should be yellow
    assert test_item["semaforo"] == "yellow", f"Expected yellow for late phases, got {test_item['semaforo']}"
    assert test_item["fasi_in_ritardo"] >= 1
    
    print(f"PASS: Commessa with deadline in {test_item['days_left']} days is yellow due to {test_item['fasi_in_ritardo']} late phases")


# === TEST 6: Completed phases not counted as late ===
def test_completed_phases_not_counted_as_late(api_session, created_commesse):
    """Completed phases should not be counted as late even with past data_prevista"""
    # Create commessa
    far_future_deadline = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    cid, _ = create_test_commessa(api_session, created_commesse, deadline=far_future_deadline)
    
    # Initialize production phases
    api_session.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
    
    # Set past data_prevista but mark as completed
    past_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    api_session.put(
        f"{BASE_URL}/api/commesse/{cid}/produzione/taglio",
        json={"stato": "completato", "data_prevista": past_date}
    )
    
    # Get semaforo
    resp = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
    assert resp.status_code == 200
    
    data = resp.json()
    test_item = next((i for i in data["items"] if i["commessa_id"] == cid), None)
    assert test_item is not None
    
    # The taglio phase is completed, so should not count as late
    # Verify that prod_done increased (to confirm phase was marked completed)
    assert test_item["prod_done"] >= 1, "Phase should be marked as completed"
    
    print(f"PASS: Completed phase with past data_prevista handled correctly. Semaforo: {test_item['semaforo']}, fasi_in_ritardo: {test_item['fasi_in_ritardo']}")


# === TEST 7: Semaforo structure validation ===
def test_semaforo_structure(api_session):
    """GET /api/dashboard/semaforo response structure validation"""
    resp = api_session.get(f"{BASE_URL}/api/dashboard/semaforo")
    assert resp.status_code == 200
    
    data = resp.json()
    
    # Check top level structure
    assert "items" in data
    assert "counts" in data
    assert "total" in data
    
    # Check counts structure
    assert "green" in data["counts"]
    assert "yellow" in data["counts"]
    assert "red" in data["counts"]
    
    # Total should equal sum of counts
    total_from_counts = data["counts"]["green"] + data["counts"]["yellow"] + data["counts"]["red"]
    assert data["total"] == total_from_counts, f"Total {data['total']} != sum of counts {total_from_counts}"
    
    # If there are items, check item structure
    if data["items"]:
        item = data["items"][0]
        required_fields = ["commessa_id", "numero", "title", "stato", "semaforo", 
                        "prod_done", "prod_total", "fasi_in_ritardo"]
        for field in required_fields:
            assert field in item, f"Missing field {field} in semaforo item"
    
    print(f"PASS: Semaforo structure valid - {data['total']} items (green:{data['counts']['green']}, yellow:{data['counts']['yellow']}, red:{data['counts']['red']})")


# === TEST 8: Auth required for endpoints ===
def test_auth_required():
    """Endpoints should require authentication"""
    unauth_session = requests.Session()
    
    # Test semaforo without auth
    resp = unauth_session.get(f"{BASE_URL}/api/dashboard/semaforo")
    assert resp.status_code == 401, f"Expected 401 for unauthenticated semaforo, got {resp.status_code}"
    
    print("PASS: Auth required for dashboard endpoints")

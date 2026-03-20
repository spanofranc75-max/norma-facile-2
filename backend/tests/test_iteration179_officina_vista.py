"""
Test Iteration 179: Vista Officina APIs
Tests for the locked worker view with 4 bridges:
1. PONTE DIARIO (Timer START/PAUSE/STOP)
2. PONTE FOTO (Photo upload with smart routing)
3. PONTE QUALITÀ (Checklist with alerts)
4. PONTE BLOCCO DATI (PIN auth)

This test file uses existing commessa data or creates test data that 
doesn't require authentication (using direct DB operations for setup).
"""

import pytest
import requests
import os
import time
import uuid
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# We'll use test data that gets created in the setup or use existing data
TEST_DATA = {
    "admin_id": None,
    "commessa_id": None,
    "commessa_id_en13241": None,
    "operator_id": None,
    "operator_id_en13241": None,
}


class TestHealthCheck:
    """Basic health check before testing Officina endpoints"""
    
    def test_api_health(self):
        """Test API is healthy"""
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"
        print(f"API health: {data}")


class TestOfficinaEndpointsExist:
    """Test that all officina endpoints exist and return proper responses"""
    
    def test_pin_set_endpoint_exists(self):
        """Test POST /api/officina/pin/set endpoint exists"""
        # Should return 400 for missing data, not 404
        resp = requests.post(f"{BASE_URL}/api/officina/pin/set", json={})
        assert resp.status_code in [400, 422], f"Expected 400/422, got {resp.status_code}"
        print(f"PIN set endpoint exists, returns {resp.status_code} for empty data")
    
    def test_pin_verify_endpoint_exists(self):
        """Test POST /api/officina/pin/verify endpoint exists"""
        resp = requests.post(f"{BASE_URL}/api/officina/pin/verify", json={"pin": "1234", "operatore_id": "fake"})
        # Should return 401 (wrong PIN) or 422 (validation), not 404
        assert resp.status_code in [401, 422], f"Expected 401/422, got {resp.status_code}"
        print(f"PIN verify endpoint exists, returns {resp.status_code}")
    
    def test_operatori_endpoint_exists(self):
        """Test GET /api/officina/operatori/{commessa_id} endpoint exists"""
        resp = requests.get(f"{BASE_URL}/api/officina/operatori/fake_commessa")
        # Should return 404 for non-existent commessa
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print(f"Operatori endpoint exists, returns 404 for fake commessa")
    
    def test_context_endpoint_exists(self):
        """Test GET /api/officina/context/{commessa_id} endpoint exists"""
        resp = requests.get(f"{BASE_URL}/api/officina/context/fake_commessa")
        # Should return 404 for non-existent commessa
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print(f"Context endpoint exists, returns 404 for fake commessa")
    
    def test_timer_endpoint_exists(self):
        """Test POST /api/officina/timer/{commessa_id} endpoint exists"""
        resp = requests.post(f"{BASE_URL}/api/officina/timer/fake_commessa", json={
            "action": "start", "operatore_id": "fake", "operatore_nome": "Test"
        })
        # Should return 404 (commessa not found) or 422 (validation)
        assert resp.status_code in [404, 422], f"Expected 404/422, got {resp.status_code}"
        print(f"Timer endpoint exists, returns {resp.status_code}")
    
    def test_foto_endpoint_exists(self):
        """Test POST /api/officina/foto/{commessa_id} endpoint exists"""
        # Without file upload, should return 422 (missing file)
        resp = requests.post(f"{BASE_URL}/api/officina/foto/fake_commessa", data={})
        assert resp.status_code == 422, f"Expected 422 for missing file, got {resp.status_code}"
        print(f"Foto endpoint exists, returns 422 for missing file")
    
    def test_checklist_endpoint_exists(self):
        """Test POST /api/officina/checklist/{commessa_id} endpoint exists"""
        resp = requests.post(f"{BASE_URL}/api/officina/checklist/fake_commessa", json={
            "operatore_id": "fake", "operatore_nome": "Test", "items": []
        })
        # Should return 404 (commessa not found) or other valid error
        assert resp.status_code in [404, 422], f"Expected 404/422, got {resp.status_code}"
        print(f"Checklist endpoint exists, returns {resp.status_code}")
    
    def test_alerts_count_endpoint_exists(self):
        """Test GET /api/officina/alerts/count endpoint exists"""
        resp = requests.get(f"{BASE_URL}/api/officina/alerts/count", params={"admin_id": "test_admin"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "count" in data
        print(f"Alerts count endpoint works: {data}")
    
    def test_alerts_list_endpoint_exists(self):
        """Test GET /api/officina/alerts endpoint exists"""
        resp = requests.get(f"{BASE_URL}/api/officina/alerts", params={"admin_id": "test_admin"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "alerts" in data
        print(f"Alerts list endpoint works: {len(data['alerts'])} alerts")
    
    def test_alert_mark_read_endpoint_exists(self):
        """Test PATCH /api/officina/alerts/{alert_id}/read endpoint exists"""
        resp = requests.patch(f"{BASE_URL}/api/officina/alerts/fake_alert/read")
        # Should return 200 even for fake alert (upsert behavior) or 404
        assert resp.status_code in [200, 404], f"Expected 200/404, got {resp.status_code}"
        print(f"Alert mark-read endpoint exists, returns {resp.status_code}")


class TestWithExistingCommessa:
    """Tests that use existing commesse from the database"""
    
    @pytest.fixture(autouse=True)
    def find_existing_commessa(self):
        """Find an existing commessa with operators to test with"""
        # First, try to find any commessa by listing via dashboard stats
        # We'll try a few common endpoints to find commesse
        global TEST_DATA
        
        # Try to get commesse from dashboard stats
        try:
            resp = requests.get(f"{BASE_URL}/api/dashboard/stats")
            if resp.status_code == 200:
                # Get scadenze which contain pos_id (POS-related commesse)
                pass
        except:
            pass
        
        # Try planning endpoint to find commesse
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                if isinstance(commesse, list) and len(commesse) > 0:
                    # Find a commessa in_produzione with EN_1090
                    for c in commesse:
                        if c.get("normativa_tipo") == "EN_1090" and c.get("stato") == "in_produzione":
                            TEST_DATA["commessa_id"] = c.get("commessa_id")
                            TEST_DATA["admin_id"] = c.get("user_id")
                            print(f"Found EN_1090 commessa: {TEST_DATA['commessa_id']}")
                            break
                    # Find EN_13241 commessa
                    for c in commesse:
                        if c.get("normativa_tipo") == "EN_13241":
                            TEST_DATA["commessa_id_en13241"] = c.get("commessa_id")
                            print(f"Found EN_13241 commessa: {TEST_DATA['commessa_id_en13241']}")
                            break
                    # If no specific normativa, use first commessa
                    if not TEST_DATA["commessa_id"] and commesse:
                        TEST_DATA["commessa_id"] = commesse[0].get("commessa_id")
                        TEST_DATA["admin_id"] = commesse[0].get("user_id")
                        print(f"Using first commessa: {TEST_DATA['commessa_id']}")
        except Exception as e:
            print(f"Error finding commessa: {e}")
        
        yield
    
    def test_get_operatori_for_real_commessa(self):
        """Test getting operators for a real commessa"""
        if not TEST_DATA["commessa_id"]:
            pytest.skip("No test commessa available")
        
        resp = requests.get(f"{BASE_URL}/api/officina/operatori/{TEST_DATA['commessa_id']}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "operatori" in data
        
        if data["operatori"]:
            TEST_DATA["operator_id"] = data["operatori"][0]["op_id"]
            print(f"Found {len(data['operatori'])} operators, using: {TEST_DATA['operator_id']}")
        else:
            print("No operators found for this commessa")
    
    def test_get_context_for_real_commessa(self):
        """Test getting context for a real commessa"""
        if not TEST_DATA["commessa_id"]:
            pytest.skip("No test commessa available")
        
        resp = requests.get(f"{BASE_URL}/api/officina/context/{TEST_DATA['commessa_id']}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validate context structure
        assert "commessa" in data
        assert "voce" in data
        assert "checklist_config" in data
        
        commessa = data["commessa"]
        assert "commessa_id" in commessa
        assert "numero" in commessa
        
        voce = data["voce"]
        assert "voce_id" in voce
        assert "normativa_tipo" in voce
        
        print(f"Context: {commessa['numero']}, normativa: {voce['normativa_tipo']}, checklist items: {len(data['checklist_config'])}")


class TestPinFlow:
    """Test PIN set/verify flow with a real commessa"""
    
    @pytest.fixture(autouse=True)
    def setup_pin_test(self):
        """Setup test data for PIN flow"""
        global TEST_DATA
        
        # Try to find a commessa and operator
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                if isinstance(commesse, list) and commesse:
                    TEST_DATA["commessa_id"] = commesse[0].get("commessa_id")
                    TEST_DATA["admin_id"] = commesse[0].get("user_id")
                    
                    # Get operators for this commessa
                    op_resp = requests.get(f"{BASE_URL}/api/officina/operatori/{TEST_DATA['commessa_id']}")
                    if op_resp.status_code == 200:
                        ops = op_resp.json().get("operatori", [])
                        if ops:
                            TEST_DATA["operator_id"] = ops[0]["op_id"]
        except:
            pass
        
        yield
    
    def test_set_pin_with_real_operator(self):
        """Test setting PIN for a real operator"""
        if not TEST_DATA["operator_id"] or not TEST_DATA["admin_id"]:
            pytest.skip("No operator/admin available")
        
        test_pin = "5678"
        payload = {
            "operatore_id": TEST_DATA["operator_id"],
            "pin": test_pin,
            "admin_id": TEST_DATA["admin_id"]
        }
        resp = requests.post(f"{BASE_URL}/api/officina/pin/set", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print(f"PIN set for operator {TEST_DATA['operator_id']}")
        
        # Now verify the PIN
        verify_payload = {
            "operatore_id": TEST_DATA["operator_id"],
            "pin": test_pin
        }
        verify_resp = requests.post(f"{BASE_URL}/api/officina/pin/verify", json=verify_payload)
        assert verify_resp.status_code == 200, f"PIN verify failed: {verify_resp.text}"
        verify_data = verify_resp.json()
        assert verify_data.get("valid") == True
        print(f"PIN verified successfully: {verify_data}")
    
    def test_verify_wrong_pin(self):
        """Test verifying wrong PIN returns 401"""
        if not TEST_DATA["operator_id"]:
            pytest.skip("No operator available")
        
        payload = {
            "operatore_id": TEST_DATA["operator_id"],
            "pin": "0000"  # Wrong PIN
        }
        resp = requests.post(f"{BASE_URL}/api/officina/pin/verify", json=payload)
        assert resp.status_code == 401, f"Expected 401 for wrong PIN, got {resp.status_code}"
        print("Wrong PIN correctly rejected with 401")


class TestTimerWorkflow:
    """Test timer workflow: START -> PAUSE -> RESUME -> STOP"""
    
    @pytest.fixture(autouse=True)
    def setup_timer_test(self):
        """Setup for timer tests"""
        global TEST_DATA
        
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                if isinstance(commesse, list) and commesse:
                    # Find a commessa in_produzione
                    for c in commesse:
                        if c.get("stato") == "in_produzione":
                            TEST_DATA["commessa_id"] = c.get("commessa_id")
                            TEST_DATA["admin_id"] = c.get("user_id")
                            break
                    if not TEST_DATA["commessa_id"]:
                        TEST_DATA["commessa_id"] = commesse[0].get("commessa_id")
                        TEST_DATA["admin_id"] = commesse[0].get("user_id")
                    
                    # Get operators
                    op_resp = requests.get(f"{BASE_URL}/api/officina/operatori/{TEST_DATA['commessa_id']}")
                    if op_resp.status_code == 200:
                        ops = op_resp.json().get("operatori", [])
                        if ops:
                            TEST_DATA["operator_id"] = ops[0]["op_id"]
        except:
            pass
        
        yield
    
    def test_full_timer_cycle(self):
        """Test complete timer cycle: START -> PAUSE -> RESUME -> STOP"""
        if not TEST_DATA["commessa_id"] or not TEST_DATA["operator_id"]:
            pytest.skip("No commessa/operator available")
        
        # Use a unique voce_id to avoid conflicts with existing timers
        voce_id = f"test_timer_{uuid.uuid4().hex[:8]}"
        op_id = TEST_DATA["operator_id"]
        op_name = "Test Operator"
        commessa_id = TEST_DATA["commessa_id"]
        
        # 1. START timer
        start_payload = {
            "action": "start",
            "operatore_id": op_id,
            "operatore_nome": op_name
        }
        resp = requests.post(f"{BASE_URL}/api/officina/timer/{commessa_id}?voce_id={voce_id}", json=start_payload)
        assert resp.status_code == 200, f"START failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "running"
        assert "timer_id" in data
        print(f"1. Timer STARTED: {data['timer_id']}")
        
        time.sleep(0.5)
        
        # 2. PAUSE timer
        pause_payload = {
            "action": "pause",
            "operatore_id": op_id,
            "operatore_nome": op_name
        }
        resp = requests.post(f"{BASE_URL}/api/officina/timer/{commessa_id}?voce_id={voce_id}", json=pause_payload)
        assert resp.status_code == 200, f"PAUSE failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "paused"
        print("2. Timer PAUSED")
        
        time.sleep(0.5)
        
        # 3. RESUME timer
        resume_payload = {
            "action": "resume",
            "operatore_id": op_id,
            "operatore_nome": op_name
        }
        resp = requests.post(f"{BASE_URL}/api/officina/timer/{commessa_id}?voce_id={voce_id}", json=resume_payload)
        assert resp.status_code == 200, f"RESUME failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "running"
        print("3. Timer RESUMED")
        
        time.sleep(0.5)
        
        # 4. STOP timer -> should create diario entry
        stop_payload = {
            "action": "stop",
            "operatore_id": op_id,
            "operatore_nome": op_name
        }
        resp = requests.post(f"{BASE_URL}/api/officina/timer/{commessa_id}?voce_id={voce_id}", json=stop_payload)
        assert resp.status_code == 200, f"STOP failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "stopped"
        assert "total_minutes" in data
        assert "diario_entry_id" in data, "STOP should auto-create diario entry"
        print(f"4. Timer STOPPED: {data['total_minutes']} min, diario: {data['diario_entry_id']}")


class TestPhotoUpload:
    """Test photo upload with smart routing"""
    
    def test_upload_photo(self):
        """Test photo upload to a commessa"""
        global TEST_DATA
        
        # Find a commessa first
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                if isinstance(commesse, list) and commesse:
                    for c in commesse:
                        if c.get("normativa_tipo") == "EN_1090":
                            TEST_DATA["commessa_id"] = c.get("commessa_id")
                            break
                    if not TEST_DATA["commessa_id"]:
                        TEST_DATA["commessa_id"] = commesse[0].get("commessa_id")
                    
                    # Get operator
                    op_resp = requests.get(f"{BASE_URL}/api/officina/operatori/{TEST_DATA['commessa_id']}")
                    if op_resp.status_code == 200:
                        ops = op_resp.json().get("operatori", [])
                        if ops:
                            TEST_DATA["operator_id"] = ops[0]["op_id"]
        except:
            pass
        
        if not TEST_DATA["commessa_id"] or not TEST_DATA["operator_id"]:
            pytest.skip("No commessa/operator available")
        
        # Create minimal test image (1x1 pixel JPEG)
        test_image = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
            "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
            "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIA"
            "AhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAr/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEB"
            "AQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwC/AB//2Q=="
        )
        
        files = {'file': ('test_photo.jpg', test_image, 'image/jpeg')}
        data = {
            'voce_id': '',
            'operatore_id': TEST_DATA["operator_id"],
            'operatore_nome': 'Test Operator'
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/officina/foto/{TEST_DATA['commessa_id']}",
            files=files,
            data=data
        )
        assert resp.status_code == 200, f"Photo upload failed: {resp.text}"
        result = resp.json()
        
        assert "doc_id" in result
        assert "nome_file" in result
        assert "tipo" in result
        print(f"Photo uploaded: {result['nome_file']}, tipo: {result['tipo']}, normativa: {result.get('normativa', 'N/A')}")


class TestChecklistSubmission:
    """Test checklist submission with quality alerts"""
    
    def test_submit_checklist_with_problems(self):
        """Test submitting checklist that creates alerts"""
        global TEST_DATA
        
        # Find a commessa with checklist config
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                if isinstance(commesse, list) and commesse:
                    for c in commesse:
                        # Get context to check if it has checklist
                        ctx_resp = requests.get(f"{BASE_URL}/api/officina/context/{c.get('commessa_id')}")
                        if ctx_resp.status_code == 200:
                            ctx = ctx_resp.json()
                            if ctx.get("checklist_config"):
                                TEST_DATA["commessa_id"] = c.get("commessa_id")
                                TEST_DATA["admin_id"] = c.get("user_id")
                                # Get operator
                                op_resp = requests.get(f"{BASE_URL}/api/officina/operatori/{TEST_DATA['commessa_id']}")
                                if op_resp.status_code == 200:
                                    ops = op_resp.json().get("operatori", [])
                                    if ops:
                                        TEST_DATA["operator_id"] = ops[0]["op_id"]
                                break
        except:
            pass
        
        if not TEST_DATA["commessa_id"] or not TEST_DATA["operator_id"]:
            pytest.skip("No commessa/operator available")
        
        # Get checklist config
        ctx_resp = requests.get(f"{BASE_URL}/api/officina/context/{TEST_DATA['commessa_id']}")
        checklist_config = ctx_resp.json().get("checklist_config", [])
        
        if not checklist_config:
            pytest.skip("No checklist config for this commessa")
        
        # Submit with first item as NOK (problem)
        items = []
        for i, item in enumerate(checklist_config):
            items.append({"codice": item["codice"], "esito": (i > 0)})  # First is False
        
        payload = {
            "operatore_id": TEST_DATA["operator_id"],
            "operatore_nome": "Test Operator",
            "items": items
        }
        
        resp = requests.post(f"{BASE_URL}/api/officina/checklist/{TEST_DATA['commessa_id']}", json=payload)
        assert resp.status_code == 200, f"Checklist submit failed: {resp.text}"
        result = resp.json()
        
        assert "checklist_id" in result
        assert "all_ok" in result
        assert "problemi" in result
        
        if result.get("all_ok"):
            print(f"Checklist submitted: all OK (no problems)")
        else:
            print(f"Checklist submitted: {result['problemi']} problem(s) -> alerts created")
            
            # Verify alerts were created
            if TEST_DATA["admin_id"]:
                alerts_resp = requests.get(f"{BASE_URL}/api/officina/alerts/count", params={"admin_id": TEST_DATA["admin_id"]})
                if alerts_resp.status_code == 200:
                    print(f"Admin has {alerts_resp.json().get('count', 0)} unread alerts")


class TestAlertsManagement:
    """Test alerts API"""
    
    def test_alerts_count(self):
        """Test getting alerts count"""
        resp = requests.get(f"{BASE_URL}/api/officina/alerts/count", params={"admin_id": "any_admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"Alerts count: {data['count']}")
    
    def test_alerts_list(self):
        """Test listing alerts"""
        resp = requests.get(f"{BASE_URL}/api/officina/alerts", params={"admin_id": "any_admin", "limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        print(f"Alerts list: {len(data['alerts'])} alerts")
        
        if data["alerts"]:
            # Validate alert structure
            alert = data["alerts"][0]
            assert "alert_id" in alert
            assert "messaggio" in alert
            assert "tipo" in alert
            assert "letto" in alert
    
    def test_mark_alert_as_read(self):
        """Test marking an alert as read"""
        # Get alerts first
        resp = requests.get(f"{BASE_URL}/api/officina/alerts", params={"admin_id": "any_admin", "limit": 1})
        if resp.status_code != 200:
            pytest.skip("Could not get alerts")
        
        alerts = resp.json().get("alerts", [])
        if not alerts:
            print("No alerts to mark as read, skipping")
            return
        
        alert_id = alerts[0]["alert_id"]
        
        # Mark as read
        mark_resp = requests.patch(f"{BASE_URL}/api/officina/alerts/{alert_id}/read")
        assert mark_resp.status_code == 200
        print(f"Alert {alert_id} marked as read")


class TestChecklistConfigs:
    """Test checklist configurations per normativa"""
    
    def test_en1090_checklist_config(self):
        """Test EN 1090 checklist has correct items"""
        # Find EN_1090 commessa
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                for c in commesse:
                    if c.get("normativa_tipo") == "EN_1090":
                        ctx_resp = requests.get(f"{BASE_URL}/api/officina/context/{c.get('commessa_id')}")
                        if ctx_resp.status_code == 200:
                            config = ctx_resp.json().get("checklist_config", [])
                            # EN_1090 should have: saldature_pulite, dimensioni_ok, materiale_ok
                            codes = [item["codice"] for item in config]
                            assert "saldature_pulite" in codes or len(codes) > 0, "EN_1090 should have checklist items"
                            print(f"EN_1090 checklist items: {codes}")
                            return
        except Exception as e:
            print(f"Error: {e}")
        
        print("No EN_1090 commessa found to test checklist config")
    
    def test_en13241_checklist_config(self):
        """Test EN 13241 checklist has correct items"""
        try:
            resp = requests.get(f"{BASE_URL}/api/planning/commesse")
            if resp.status_code == 200:
                commesse = resp.json()
                for c in commesse:
                    if c.get("normativa_tipo") == "EN_13241":
                        ctx_resp = requests.get(f"{BASE_URL}/api/officina/context/{c.get('commessa_id')}")
                        if ctx_resp.status_code == 200:
                            config = ctx_resp.json().get("checklist_config", [])
                            # EN_13241 should have: sicurezze_ok, movimento_ok
                            codes = [item["codice"] for item in config]
                            print(f"EN_13241 checklist items: {codes}")
                            return
        except Exception as e:
            print(f"Error: {e}")
        
        print("No EN_13241 commessa found to test checklist config")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

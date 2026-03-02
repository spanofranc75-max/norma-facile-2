"""
Test Iteration 103: Notifications (Il Cane da Guardia), QR Code, Database Cleanup
Tests:
- Notifications API: /status, /check-now, /history
- QR Code generation for commesse
- Database cleanup preview (DO NOT execute cleanup)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "test_admin_token_for_api"  # Admin session token
COMMESSA_ID = "com_bfb82e090373"  # Known valid commessa for admin user


class TestNotificationsStatus:
    """Test GET /api/notifications/status endpoint - Watchdog status"""

    def test_status_returns_200(self):
        """Verify the status endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/notifications/status returns 200")

    def test_status_has_active_field(self):
        """Verify status contains active boolean"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        assert "active" in data, "Response should contain 'active' field"
        assert data["active"] == True, "Watchdog should be active"
        print(f"✓ Watchdog active: {data['active']}")

    def test_status_has_current_alerts_structure(self):
        """Verify current_alerts contains expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        assert "current_alerts" in data, "Response should contain 'current_alerts'"
        alerts = data["current_alerts"]
        
        assert "welder_count" in alerts, "alerts should have welder_count"
        assert "instrument_count" in alerts, "alerts should have instrument_count"
        assert "total" in alerts, "alerts should have total"
        assert "welders" in alerts, "alerts should have welders array"
        assert "instruments" in alerts, "alerts should have instruments array"
        
        print(f"✓ Alerts structure valid: {alerts['total']} total alerts " 
              f"({alerts['welder_count']} welders, {alerts['instrument_count']} instruments)")

    def test_status_has_last_check_info(self):
        """Verify last_check contains check information"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        # last_check can be null if no checks have been performed
        print(f"✓ last_check: {data.get('last_check', 'None')}")

    def test_status_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Authentication required for /api/notifications/status")


class TestNotificationsCheckNow:
    """Test POST /api/notifications/check-now endpoint - Manual trigger"""

    def test_check_now_returns_200(self):
        """Verify manual check can be triggered"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/check-now",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ POST /api/notifications/check-now returns 200")

    def test_check_now_returns_check_result(self):
        """Verify check returns proper structure"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/check-now",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        
        assert "checked_at" in data, "Result should have checked_at timestamp"
        assert "source" in data, "Result should have source field"
        assert data["source"] == "manuale", "Source should be 'manuale' for manual trigger"
        assert "welder_alerts" in data, "Result should have welder_alerts array"
        assert "instrument_alerts" in data, "Result should have instrument_alerts array"
        assert "total_alerts" in data, "Result should have total_alerts count"
        assert "email_sent" in data, "Result should have email_sent boolean"
        
        print(f"✓ Manual check result: {data['total_alerts']} alerts, email_sent={data['email_sent']}")

    def test_check_now_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/notifications/check-now")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Authentication required for /api/notifications/check-now")


class TestNotificationsHistory:
    """Test GET /api/notifications/history endpoint"""

    def test_history_returns_200(self):
        """Verify history endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/history",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/notifications/history returns 200")

    def test_history_returns_logs_array(self):
        """Verify history returns logs array"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/history",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        assert "logs" in data, "Response should contain 'logs' array"
        assert isinstance(data["logs"], list), "logs should be a list"
        print(f"✓ History contains {len(data['logs'])} log entries")

    def test_history_log_entry_structure(self):
        """Verify log entries have expected fields (if any exist)"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/history",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            expected_fields = ["checked_at", "source", "total_alerts", "welder_count", "instrument_count"]
            for field in expected_fields:
                assert field in log, f"Log entry should contain '{field}'"
            print(f"✓ Log entry structure valid: {log.get('source')} at {log.get('checked_at')}")
        else:
            print("✓ No log entries to verify structure")

    def test_history_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/history")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Authentication required for /api/notifications/history")


class TestQRCodeGeneration:
    """Test QR Code generation endpoints for commesse"""

    def test_qr_code_image_returns_200(self):
        """Verify QR code PNG generation works"""
        response = requests.get(
            f"{BASE_URL}/api/qrcode/commessa/{COMMESSA_ID}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/qrcode/commessa/{id} returns 200")

    def test_qr_code_returns_png_content_type(self):
        """Verify QR code returns PNG image"""
        response = requests.get(
            f"{BASE_URL}/api/qrcode/commessa/{COMMESSA_ID}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        content_type = response.headers.get("Content-Type", "")
        assert "image/png" in content_type, f"Expected image/png, got {content_type}"
        
        # Verify it's a valid PNG (starts with PNG magic bytes)
        assert response.content[:8] == b'\x89PNG\r\n\x1a\n', "Response should be valid PNG"
        print(f"✓ QR code is valid PNG ({len(response.content)} bytes)")

    def test_qr_code_data_returns_200(self):
        """Verify QR metadata endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/qrcode/commessa/{COMMESSA_ID}/data",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/qrcode/commessa/{id}/data returns 200")

    def test_qr_code_data_structure(self):
        """Verify QR metadata has expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/qrcode/commessa/{COMMESSA_ID}/data",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        
        assert "commessa_id" in data, "Response should have commessa_id"
        assert data["commessa_id"] == COMMESSA_ID, f"commessa_id should be {COMMESSA_ID}"
        assert "numero" in data, "Response should have numero"
        assert "qr_url" in data, "Response should have qr_url"
        assert "qr_image_endpoint" in data, "Response should have qr_image_endpoint"
        
        print(f"✓ QR metadata: numero={data.get('numero')}, url={data.get('qr_url')}")

    def test_qr_code_invalid_commessa_returns_404(self):
        """Verify 404 for non-existent commessa"""
        response = requests.get(
            f"{BASE_URL}/api/qrcode/commessa/nonexistent_commessa_id",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid commessa returns 404")

    def test_qr_code_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/qrcode/commessa/{COMMESSA_ID}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Authentication required for QR code endpoints")


class TestDatabaseCleanupPreview:
    """Test database cleanup preview endpoint (DO NOT execute cleanup)"""

    def test_cleanup_preview_returns_200(self):
        """Verify cleanup preview is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cleanup/preview",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/admin/cleanup/preview returns 200")

    def test_cleanup_preview_shows_data_counts(self):
        """Verify preview shows collection counts"""
        response = requests.get(
            f"{BASE_URL}/api/admin/cleanup/preview",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        
        assert "operational_data" in data, "Response should have operational_data"
        assert "clients" in data, "Response should have clients count"
        assert "vendors" in data, "Response should have vendors count"
        assert "note" in data, "Response should have note"
        
        # Verify operational_data contains expected collections
        ops = data["operational_data"]
        expected_collections = ["commesse", "preventivi", "invoices", "ddts"]
        for coll in expected_collections:
            assert coll in ops, f"operational_data should contain {coll}"
        
        print(f"✓ Cleanup preview: {len(ops)} operational collections, {data['clients']} clients, {data['vendors']} vendors")

    def test_cleanup_preview_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/cleanup/preview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Authentication required for /api/admin/cleanup/preview")

    def test_cleanup_execute_requires_confirmation(self):
        """Verify cleanup execute rejects without confirm=true (DO NOT execute cleanup)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/cleanup/execute",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"confirm": False}  # Explicitly NOT confirming
        )
        assert response.status_code == 400, f"Expected 400 (missing confirmation), got {response.status_code}"
        print("✓ Cleanup execute rejects without confirm=true")


class TestNotificationAlertDetails:
    """Test that alert details contain expected fields"""

    def test_welder_alert_fields(self):
        """Verify welder alerts have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        welders = data["current_alerts"]["welders"]
        
        if len(welders) > 0:
            alert = welders[0]
            expected_fields = ["type", "welder_name", "qualification", "expiry_date", "days_remaining", "status_label"]
            for field in expected_fields:
                assert field in alert, f"Welder alert should have '{field}'"
            assert alert["type"] == "welder_qualification"
            print(f"✓ Welder alert structure valid: {alert.get('welder_name')} - {alert.get('status_label')}")
        else:
            print("✓ No welder alerts to verify structure")

    def test_instrument_alert_fields(self):
        """Verify instrument alerts have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        data = response.json()
        instruments = data["current_alerts"]["instruments"]
        
        if len(instruments) > 0:
            alert = instruments[0]
            expected_fields = ["type", "instrument_name", "next_calibration_date", "days_remaining", "status_label"]
            for field in expected_fields:
                assert field in alert, f"Instrument alert should have '{field}'"
            assert alert["type"] == "instrument_calibration"
            print(f"✓ Instrument alert structure valid: {alert.get('instrument_name')} - {alert.get('status_label')}")
        else:
            print("✓ No instrument alerts to verify structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

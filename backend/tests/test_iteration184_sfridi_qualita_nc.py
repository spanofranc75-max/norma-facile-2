"""
Iteration 184: Sfridi, Controlli Visivi, Registro NC, and NC Alerts Testing
Tests the new Admin UI backend APIs for:
- Sfridi (scrap material management with cert 3.1 link)
- Controlli Visivi (visual inspections with OK/NOK)
- Registro NC (Non-Conformity Registry)
- NC Alerts on Dashboard
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test commessa and admin from the review request
TEST_COMMESSA_ID = "com_2b99b2db8681"
TEST_ADMIN_ID = "user_97c773827822"


class TestSfridiEndpoints:
    """Test Sfridi (scrap material) API endpoints"""
    
    def test_get_sfridi_by_commessa_requires_auth(self):
        """GET /api/sfridi/commessa/{commessa_id} should require auth"""
        response = requests.get(f"{BASE_URL}/api/sfridi/commessa/{TEST_COMMESSA_ID}")
        # Without auth, should return 401
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /api/sfridi/commessa/{TEST_COMMESSA_ID} correctly requires auth (401)")
    
    def test_create_sfrido_requires_auth(self):
        """POST /api/sfridi should require auth"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "tipo_materiale": "IPE 200",
            "quantita": "3 barre",
            "numero_colata": "12345",
            "certificato_doc_id": "",
            "note": "Test sfrido"
        }
        response = requests.post(f"{BASE_URL}/api/sfridi", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/sfridi correctly requires auth (401)")
    
    def test_preleva_sfrido_requires_auth(self):
        """POST /api/sfridi/{sfrido_id}/preleva should require auth"""
        payload = {
            "commessa_id_destinazione": "com_test",
            "quantita_prelevata": "1 barra",
            "note": "Test prelievo"
        }
        response = requests.post(f"{BASE_URL}/api/sfridi/sfr_test123/preleva", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/sfridi/{sfrido_id}/preleva correctly requires auth (401)")
    
    def test_mark_esaurito_requires_auth(self):
        """PATCH /api/sfridi/{sfrido_id}/esaurito should require auth"""
        response = requests.patch(f"{BASE_URL}/api/sfridi/sfr_test123/esaurito")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ PATCH /api/sfridi/{sfrido_id}/esaurito correctly requires auth (401)")


class TestControlliVisiviEndpoints:
    """Test Controlli Visivi (visual inspections) API endpoints"""
    
    def test_get_controlli_visivi_requires_auth(self):
        """GET /api/controlli-visivi/{commessa_id} should require auth"""
        response = requests.get(f"{BASE_URL}/api/controlli-visivi/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /api/controlli-visivi/{TEST_COMMESSA_ID} correctly requires auth (401)")
    
    def test_create_controllo_visivo_requires_auth(self):
        """POST /api/controlli-visivi should require auth"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "normativa_tipo": "EN_1090",
            "esito": True,
            "note": "Test controllo OK"
        }
        response = requests.post(f"{BASE_URL}/api/controlli-visivi", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/controlli-visivi correctly requires auth (401)")
    
    def test_check_controlli_completi_requires_auth(self):
        """GET /api/controlli-visivi/{commessa_id}/check should require auth"""
        response = requests.get(f"{BASE_URL}/api/controlli-visivi/{TEST_COMMESSA_ID}/check")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /api/controlli-visivi/{TEST_COMMESSA_ID}/check correctly requires auth (401)")


class TestRegistroNCEndpoints:
    """Test Registro NC (Non-Conformity Registry) API endpoints"""
    
    def test_get_nc_by_commessa_requires_auth(self):
        """GET /api/registro-nc/{commessa_id} should require auth"""
        response = requests.get(f"{BASE_URL}/api/registro-nc/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /api/registro-nc/{TEST_COMMESSA_ID} correctly requires auth (401)")
    
    def test_get_all_nc_requires_auth(self):
        """GET /api/registro-nc should require auth"""
        response = requests.get(f"{BASE_URL}/api/registro-nc")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/registro-nc correctly requires auth (401)")
    
    def test_update_nc_requires_auth(self):
        """PATCH /api/registro-nc/{nc_id} should require auth"""
        payload = {
            "stato": "in_corso",
            "azione_correttiva": "Test azione"
        }
        response = requests.patch(f"{BASE_URL}/api/registro-nc/nc_test123", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ PATCH /api/registro-nc/{nc_id} correctly requires auth (401)")


class TestOfficinaAlertsEndpoints:
    """Test Officina Alerts API endpoints (for Dashboard NC alerts)"""
    
    def test_get_alerts_count(self):
        """GET /api/officina/alerts/count?admin_id=... should return count"""
        response = requests.get(f"{BASE_URL}/api/officina/alerts/count?admin_id={TEST_ADMIN_ID}")
        # This endpoint doesn't require auth (used by dashboard)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["count"], int), "Count should be an integer"
        print(f"✓ GET /api/officina/alerts/count returns count: {data['count']}")
    
    def test_get_alerts_list(self):
        """GET /api/officina/alerts?admin_id=... should return alerts list"""
        response = requests.get(f"{BASE_URL}/api/officina/alerts?admin_id={TEST_ADMIN_ID}&limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "alerts" in data, "Response should contain 'alerts' field"
        assert isinstance(data["alerts"], list), "Alerts should be a list"
        print(f"✓ GET /api/officina/alerts returns {len(data['alerts'])} alerts")
        
        # Verify alert structure if any exist
        if data["alerts"]:
            alert = data["alerts"][0]
            expected_fields = ["alert_id", "admin_id", "commessa_id", "tipo", "messaggio", "letto", "created_at"]
            for field in expected_fields:
                assert field in alert, f"Alert should contain '{field}' field"
            print(f"✓ Alert structure verified with fields: {list(alert.keys())}")
    
    def test_mark_alert_read(self):
        """PATCH /api/officina/alerts/{alert_id}/read should mark alert as read"""
        # First get an alert to mark as read
        response = requests.get(f"{BASE_URL}/api/officina/alerts?admin_id={TEST_ADMIN_ID}&limit=1")
        if response.status_code == 200 and response.json().get("alerts"):
            alert_id = response.json()["alerts"][0]["alert_id"]
            mark_response = requests.patch(f"{BASE_URL}/api/officina/alerts/{alert_id}/read")
            assert mark_response.status_code == 200, f"Expected 200, got {mark_response.status_code}"
            print(f"✓ PATCH /api/officina/alerts/{alert_id}/read successful")
        else:
            print("⚠ No alerts to test mark_alert_read (skipped)")


class TestEndpointResponseFormats:
    """Test that endpoints return proper response formats"""
    
    def test_sfridi_endpoint_exists(self):
        """Verify /api/sfridi endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/sfridi")
        # Should return 401 (auth required) not 404
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/sfridi endpoint exists (returns 401 without auth)")
    
    def test_controlli_visivi_endpoint_exists(self):
        """Verify /api/controlli-visivi endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/controlli-visivi", json={})
        # Should return 401 (auth required) or 422 (validation), not 404
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print(f"✓ /api/controlli-visivi endpoint exists (returns {response.status_code})")
    
    def test_registro_nc_endpoint_exists(self):
        """Verify /api/registro-nc endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/registro-nc")
        # Should return 401 (auth required) not 404
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/registro-nc endpoint exists (returns 401 without auth)")


class TestAlertIntegration:
    """Test NC alert integration with Dashboard"""
    
    def test_alerts_count_with_invalid_admin(self):
        """GET /api/officina/alerts/count with invalid admin should return 0"""
        response = requests.get(f"{BASE_URL}/api/officina/alerts/count?admin_id=invalid_user_id")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["count"] == 0, f"Expected count 0 for invalid admin, got {data['count']}"
        print("✓ Alerts count returns 0 for invalid admin_id")
    
    def test_alerts_list_with_invalid_admin(self):
        """GET /api/officina/alerts with invalid admin should return empty list"""
        response = requests.get(f"{BASE_URL}/api/officina/alerts?admin_id=invalid_user_id")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["alerts"] == [], f"Expected empty alerts list for invalid admin"
        print("✓ Alerts list returns empty for invalid admin_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

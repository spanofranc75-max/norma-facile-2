"""Tests for Registro Apparecchiature & Strumenti module - /api/instruments endpoints"""
import pytest
import requests
import os
from datetime import date, timedelta

# Use external URL to test what user sees
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_3ce08f7a2e65452aa6e466779454ceb0"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestInstrumentsList:
    """Test GET /api/instruments/ - listing and filtering"""

    def test_list_all_instruments(self, api_client):
        """Verify all 5 test instruments are returned with correct stats"""
        response = api_client.get(f"{BASE_URL}/api/instruments/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "stats" in data
        assert "total" in data
        
        # Verify we have 5 instruments
        assert data["total"] == 5
        assert len(data["items"]) == 5
        
        # Verify stats match expected values
        stats = data["stats"]
        assert stats["total"] == 5
        assert stats["attivi"] == 2
        assert stats["in_scadenza"] == 1
        assert stats["scaduti"] == 1
        assert stats["in_manutenzione"] == 1
        assert stats["fuori_uso"] == 0

    def test_filter_by_type_misura(self, api_client):
        """Filter by type=misura should return only measurement instruments"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?type=misura")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        # Should have Calibro Digitale 150mm and Micrometro 0-25mm
        assert len(items) == 2
        for item in items:
            assert item["type"] == "misura"

    def test_filter_by_type_saldatura(self, api_client):
        """Filter by type=saldatura should return welding equipment"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?type=saldatura")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        # Should have Saldatrice and Forno Essicazione
        assert len(items) == 2
        for item in items:
            assert item["type"] == "saldatura"

    def test_filter_by_status_scaduto(self, api_client):
        """Filter by computed_status=scaduto"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?status=scaduto")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        # Only Micrometro 0-25mm is expired
        assert len(items) == 1
        assert items[0]["computed_status"] == "scaduto"
        assert items[0]["name"] == "Micrometro 0-25mm"

    def test_filter_by_status_in_scadenza(self, api_client):
        """Filter by computed_status=in_scadenza"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?status=in_scadenza")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        # Only Saldatrice MIG/MAG 320A is expiring soon
        assert len(items) == 1
        assert items[0]["computed_status"] == "in_scadenza"
        assert items[0]["name"] == "Saldatrice MIG/MAG 320A"

    def test_search_by_manufacturer_mitutoyo(self, api_client):
        """Search for Mitutoyo should find Calibro Digitale"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Mitutoyo")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        assert items[0]["manufacturer"] == "Mitutoyo"
        assert items[0]["name"] == "Calibro Digitale 150mm"

    def test_search_by_partial_name(self, api_client):
        """Search for partial name 'Micro' should find Micrometro"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Micro")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        assert "Micrometro" in items[0]["name"]


class TestInstrumentComputedStatus:
    """Test automatic expiry status calculation"""

    def test_scaduto_status_for_past_date(self, api_client):
        """Micrometro with next_calibration_date in past should be 'scaduto'"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Micrometro")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        
        micrometro = items[0]
        assert micrometro["computed_status"] == "scaduto"
        assert micrometro["days_until_expiry"] < 0  # Negative means past due

    def test_in_scadenza_status_within_30_days(self, api_client):
        """Saldatrice expiring within 30 days should be 'in_scadenza'"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Saldatrice")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        
        saldatrice = items[0]
        assert saldatrice["computed_status"] == "in_scadenza"
        assert 0 <= saldatrice["days_until_expiry"] <= 30

    def test_attivo_status_for_future_date(self, api_client):
        """Calibro with next_calibration_date > 30 days should be 'attivo'"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Calibro")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        
        calibro = items[0]
        assert calibro["computed_status"] == "attivo"
        assert calibro["days_until_expiry"] > 30

    def test_in_manutenzione_overrides_calibration(self, api_client):
        """in_manutenzione status should override calibration calculation"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=Cesoia")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) == 1
        
        cesoia = items[0]
        assert cesoia["status"] == "in_manutenzione"
        assert cesoia["computed_status"] == "in_manutenzione"
        assert cesoia["days_until_expiry"] is None  # No expiry calculation for maintenance


class TestInstrumentsCRUD:
    """Test Create, Read, Update, Delete operations"""
    
    created_instrument_id = None

    def test_create_instrument(self, api_client):
        """POST /api/instruments/ - Create a new instrument"""
        payload = {
            "name": "TEST_Termometro Digitale",
            "serial_number": "TEST-THERM-001",
            "type": "misura",
            "manufacturer": "Fluke",
            "purchase_date": "2024-06-01",
            "last_calibration_date": "2025-12-01",
            "next_calibration_date": "2026-12-01",
            "calibration_interval_months": 12,
            "status": "attivo",
            "notes": "Test instrument for pytest"
        }
        
        response = api_client.post(f"{BASE_URL}/api/instruments/", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "instrument_id" in data
        assert data["name"] == payload["name"]
        assert data["serial_number"] == payload["serial_number"]
        assert data["type"] == "misura"
        assert data["manufacturer"] == "Fluke"
        assert data["computed_status"] == "attivo"
        
        # Store for later tests
        TestInstrumentsCRUD.created_instrument_id = data["instrument_id"]

    def test_read_created_instrument(self, api_client):
        """Verify created instrument appears in list"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=TEST_Termometro")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) >= 1
        
        test_inst = next((i for i in items if "TEST_Termometro" in i["name"]), None)
        assert test_inst is not None
        assert test_inst["serial_number"] == "TEST-THERM-001"

    def test_update_instrument(self, api_client):
        """PUT /api/instruments/{id} - Update the instrument"""
        inst_id = TestInstrumentsCRUD.created_instrument_id
        if not inst_id:
            pytest.skip("No instrument created in previous test")
        
        update_payload = {
            "name": "TEST_Termometro Digitale UPDATED",
            "serial_number": "TEST-THERM-001",
            "type": "misura",
            "manufacturer": "Fluke Updated",
            "purchase_date": "2024-06-01",
            "last_calibration_date": "2025-12-01",
            "next_calibration_date": "2026-12-01",
            "calibration_interval_months": 12,
            "status": "attivo",
            "notes": "Updated notes"
        }
        
        response = api_client.put(f"{BASE_URL}/api/instruments/{inst_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "TEST_Termometro Digitale UPDATED"
        assert data["manufacturer"] == "Fluke Updated"
        assert data["notes"] == "Updated notes"

    def test_verify_update_persisted(self, api_client):
        """Verify update was persisted in database"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=UPDATED")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        assert len(items) >= 1
        
        updated_inst = next((i for i in items if "UPDATED" in i["name"]), None)
        assert updated_inst is not None
        assert updated_inst["manufacturer"] == "Fluke Updated"

    def test_delete_instrument(self, api_client):
        """DELETE /api/instruments/{id} - Delete the instrument"""
        inst_id = TestInstrumentsCRUD.created_instrument_id
        if not inst_id:
            pytest.skip("No instrument created in previous test")
        
        response = api_client.delete(f"{BASE_URL}/api/instruments/{inst_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Strumento eliminato"
        assert data["instrument_id"] == inst_id

    def test_verify_delete_removed(self, api_client):
        """Verify deleted instrument no longer exists"""
        response = api_client.get(f"{BASE_URL}/api/instruments/?search=TEST_Termometro")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        # Should not find the deleted instrument
        test_inst = next((i for i in items if "TEST_Termometro" in i["name"]), None)
        assert test_inst is None, "Deleted instrument should not be found"


class TestInstrumentValidation:
    """Test input validation and error handling"""

    def test_create_invalid_type(self, api_client):
        """Creating with invalid type should fail with 400"""
        payload = {
            "name": "TEST_Invalid Type",
            "serial_number": "TEST-INV-001",
            "type": "invalid_type",
            "status": "attivo"
        }
        
        response = api_client.post(f"{BASE_URL}/api/instruments/", json=payload)
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid type, got {response.status_code}"

    def test_update_nonexistent_instrument(self, api_client):
        """Updating non-existent instrument should return 404"""
        payload = {
            "name": "Test",
            "serial_number": "TEST-001",
            "type": "misura",
            "status": "attivo"
        }
        
        response = api_client.put(f"{BASE_URL}/api/instruments/nonexistent_id_12345", json=payload)
        assert response.status_code == 404

    def test_delete_nonexistent_instrument(self, api_client):
        """Deleting non-existent instrument should return 404"""
        response = api_client.delete(f"{BASE_URL}/api/instruments/nonexistent_id_12345")
        assert response.status_code == 404


class TestStatsCalculation:
    """Test that stats are always calculated from ALL instruments regardless of filters"""

    def test_stats_unchanged_with_filter(self, api_client):
        """Stats should show total counts even when filter is applied"""
        # Get stats without filter
        response_all = api_client.get(f"{BASE_URL}/api/instruments/")
        stats_all = response_all.json()["stats"]
        
        # Get stats with type filter
        response_filtered = api_client.get(f"{BASE_URL}/api/instruments/?type=misura")
        stats_filtered = response_filtered.json()["stats"]
        
        # Stats should be the same
        assert stats_all == stats_filtered, "Stats should be unchanged by filters"

    def test_stats_unchanged_with_search(self, api_client):
        """Stats should show total counts even when search is applied"""
        # Get stats without search
        response_all = api_client.get(f"{BASE_URL}/api/instruments/")
        stats_all = response_all.json()["stats"]
        
        # Get stats with search
        response_searched = api_client.get(f"{BASE_URL}/api/instruments/?search=Mitutoyo")
        stats_searched = response_searched.json()["stats"]
        
        # Stats should be the same
        assert stats_all == stats_searched, "Stats should be unchanged by search"

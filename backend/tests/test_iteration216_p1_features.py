"""
Iteration 216 — Testing 3 P1 Features:
1. Ponte Perizie→Preventivatore: POST /api/perizie/{perizia_id}/genera-preventivo
2. Sistema Notifiche Proattive: POST /api/notifications/check-now with ITT + urgency levels
3. Report CAM Mensile: GET /api/cam/report-mensile/pdf
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "fresh_4f69b847846148459e91"
USER_ID = "user_97c773827822"
TEST_PERIZIA_ID = "per_test_ponte_8baac379"


@pytest.fixture
def auth_headers():
    """Auth headers with session cookie."""
    return {"Cookie": f"session_token={SESSION_TOKEN}"}


class TestPontePeriziaPreventivo:
    """Test Ponte Perizia → Preventivatore feature."""

    def test_genera_preventivo_endpoint_exists(self, auth_headers):
        """POST /api/perizie/{perizia_id}/genera-preventivo should exist."""
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}/genera-preventivo"
        resp = requests.post(url, headers=auth_headers)
        # Should not be 404 (endpoint exists)
        assert resp.status_code != 404, f"Endpoint not found: {resp.status_code}"
        print(f"Ponte endpoint status: {resp.status_code}")

    def test_genera_preventivo_creates_preventivo(self, auth_headers):
        """POST /api/perizie/{perizia_id}/genera-preventivo creates a new preventivo."""
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}/genera-preventivo"
        resp = requests.post(url, headers=auth_headers)
        
        # Should succeed (200 or 201)
        assert resp.status_code in [200, 201], f"Failed: {resp.status_code} - {resp.text[:500]}"
        
        data = resp.json()
        print(f"Ponte response: {data}")
        
        # Verify response structure
        assert "preventivo_id" in data, "Missing preventivo_id in response"
        assert "preventivo_number" in data, "Missing preventivo_number in response"
        assert "totale" in data, "Missing totale in response"
        assert "righe" in data, "Missing righe (line count) in response"
        
        # Verify values
        assert data["preventivo_id"].startswith("prev_"), f"Invalid preventivo_id format: {data['preventivo_id']}"
        assert data["preventivo_number"].startswith("PV-"), f"Invalid number format: {data['preventivo_number']}"
        assert data["righe"] > 0, "Should have at least 1 line"
        
        print(f"Created preventivo: {data['preventivo_number']} with {data['righe']} lines, total: {data['totale']}")
        return data

    def test_preventivo_has_perizia_source_metadata(self, auth_headers):
        """Verify the created preventivo has perizia_source metadata."""
        # First create a preventivo
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}/genera-preventivo"
        resp = requests.post(url, headers=auth_headers)
        assert resp.status_code in [200, 201], f"Failed to create: {resp.status_code}"
        
        prev_id = resp.json()["preventivo_id"]
        
        # Fetch the preventivo
        prev_url = f"{BASE_URL}/api/preventivi/{prev_id}"
        prev_resp = requests.get(prev_url, headers=auth_headers)
        assert prev_resp.status_code == 200, f"Failed to fetch preventivo: {prev_resp.status_code}"
        
        prev_data = prev_resp.json()
        print(f"Preventivo data keys: {list(prev_data.keys())}")
        
        # Verify perizia_source metadata
        assert "perizia_source" in prev_data, "Missing perizia_source metadata"
        ps = prev_data["perizia_source"]
        assert ps.get("perizia_id") == TEST_PERIZIA_ID, f"Wrong perizia_id: {ps.get('perizia_id')}"
        assert "perizia_number" in ps, "Missing perizia_number in perizia_source"
        assert "tipo_danno" in ps, "Missing tipo_danno in perizia_source"
        
        print(f"perizia_source: {ps}")

    def test_perizia_updated_with_preventivo_link(self, auth_headers):
        """After ponte, perizia should have preventivo_id and preventivo_number."""
        # First create a preventivo
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}/genera-preventivo"
        resp = requests.post(url, headers=auth_headers)
        assert resp.status_code in [200, 201]
        
        prev_id = resp.json()["preventivo_id"]
        prev_number = resp.json()["preventivo_number"]
        
        # Fetch the perizia
        perizia_url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}"
        perizia_resp = requests.get(perizia_url, headers=auth_headers)
        assert perizia_resp.status_code == 200, f"Failed to fetch perizia: {perizia_resp.status_code}"
        
        perizia_data = perizia_resp.json()
        
        # Verify linking
        assert perizia_data.get("preventivo_id") == prev_id, f"Perizia not linked to preventivo: {perizia_data.get('preventivo_id')}"
        assert perizia_data.get("preventivo_number") == prev_number, f"Wrong preventivo_number: {perizia_data.get('preventivo_number')}"
        
        print(f"Perizia linked to preventivo: {prev_id} ({prev_number})")


class TestNotificheProattive:
    """Test Sistema Notifiche Proattive with ITT checks and urgency levels."""

    def test_check_now_endpoint_exists(self, auth_headers):
        """POST /api/notifications/check-now should exist."""
        url = f"{BASE_URL}/api/notifications/check-now"
        resp = requests.post(url, headers=auth_headers)
        # Should not be 404
        assert resp.status_code != 404, f"Endpoint not found: {resp.status_code}"
        print(f"Notifications check-now status: {resp.status_code}")

    def test_check_now_returns_alert_structure(self, auth_headers):
        """POST /api/notifications/check-now returns welder_alerts, instrument_alerts, itt_alerts."""
        url = f"{BASE_URL}/api/notifications/check-now"
        resp = requests.post(url, headers=auth_headers)
        
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text[:500]}"
        
        data = resp.json()
        print(f"Notification check response keys: {list(data.keys())}")
        
        # Verify structure
        assert "welder_alerts" in data, "Missing welder_alerts"
        assert "instrument_alerts" in data, "Missing instrument_alerts"
        assert "itt_alerts" in data, "Missing itt_alerts"
        assert "total_alerts" in data, "Missing total_alerts"
        
        print(f"Total alerts: {data['total_alerts']}")
        print(f"Welder alerts: {len(data['welder_alerts'])}")
        print(f"Instrument alerts: {len(data['instrument_alerts'])}")
        print(f"ITT alerts: {len(data['itt_alerts'])}")

    def test_alerts_have_urgency_field(self, auth_headers):
        """All alerts should have urgency field with valid values."""
        url = f"{BASE_URL}/api/notifications/check-now"
        resp = requests.post(url, headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        valid_urgencies = {"scaduto", "critico", "urgente", "alert"}
        
        # Check welder alerts
        for alert in data.get("welder_alerts", []):
            assert "urgency" in alert, f"Welder alert missing urgency: {alert}"
            assert alert["urgency"] in valid_urgencies, f"Invalid urgency: {alert['urgency']}"
            print(f"Welder alert: {alert.get('welder_name')} - {alert['urgency']}")
        
        # Check instrument alerts
        for alert in data.get("instrument_alerts", []):
            assert "urgency" in alert, f"Instrument alert missing urgency: {alert}"
            assert alert["urgency"] in valid_urgencies, f"Invalid urgency: {alert['urgency']}"
            print(f"Instrument alert: {alert.get('instrument_name')} - {alert['urgency']}")
        
        # Check ITT alerts
        for alert in data.get("itt_alerts", []):
            assert "urgency" in alert, f"ITT alert missing urgency: {alert}"
            assert alert["urgency"] in valid_urgencies, f"Invalid urgency: {alert['urgency']}"
            print(f"ITT alert: {alert.get('verbale_numero')} - {alert['urgency']}")

    def test_urgency_levels_correct(self, auth_headers):
        """Verify urgency levels: scaduto (<0), critico (<=1), urgente (<=7), alert (<=30)."""
        url = f"{BASE_URL}/api/notifications/check-now"
        resp = requests.post(url, headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        
        all_alerts = (
            data.get("welder_alerts", []) + 
            data.get("instrument_alerts", []) + 
            data.get("itt_alerts", [])
        )
        
        for alert in all_alerts:
            days = alert.get("days_remaining", 999)
            urgency = alert.get("urgency", "")
            
            if days < 0:
                assert urgency == "scaduto", f"Days {days} should be 'scaduto', got '{urgency}'"
            elif days <= 1:
                assert urgency == "critico", f"Days {days} should be 'critico', got '{urgency}'"
            elif days <= 7:
                assert urgency == "urgente", f"Days {days} should be 'urgente', got '{urgency}'"
            elif days <= 30:
                assert urgency == "alert", f"Days {days} should be 'alert', got '{urgency}'"
            
            print(f"Alert: days={days}, urgency={urgency} - CORRECT")

    def test_email_sent_field_present(self, auth_headers):
        """Response should include email_sent field."""
        url = f"{BASE_URL}/api/notifications/check-now"
        resp = requests.post(url, headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "email_sent" in data, "Missing email_sent field"
        print(f"Email sent: {data['email_sent']}")


class TestReportCAMMensile:
    """Test Report CAM Mensile PDF endpoint."""

    def test_report_mensile_pdf_endpoint_exists(self, auth_headers):
        """GET /api/cam/report-mensile/pdf should exist."""
        url = f"{BASE_URL}/api/cam/report-mensile/pdf"
        resp = requests.get(url, headers=auth_headers)
        # Should not be 404
        assert resp.status_code != 404, f"Endpoint not found: {resp.status_code}"
        print(f"CAM report-mensile/pdf status: {resp.status_code}")

    def test_report_mensile_returns_pdf(self, auth_headers):
        """GET /api/cam/report-mensile/pdf returns a valid PDF."""
        url = f"{BASE_URL}/api/cam/report-mensile/pdf"
        resp = requests.get(url, headers=auth_headers)
        
        assert resp.status_code == 200, f"Failed: {resp.status_code} - {resp.text[:500]}"
        
        # Verify content type
        content_type = resp.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Wrong content type: {content_type}"
        
        # Verify PDF magic bytes
        content = resp.content
        assert content[:4] == b"%PDF", f"Not a valid PDF: {content[:20]}"
        
        # Verify reasonable size
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        
        print(f"CAM Report PDF: {len(content)} bytes, content-type: {content_type}")

    def test_report_mensile_has_content_disposition(self, auth_headers):
        """PDF response should have Content-Disposition header with filename."""
        url = f"{BASE_URL}/api/cam/report-mensile/pdf"
        resp = requests.get(url, headers=auth_headers)
        assert resp.status_code == 200
        
        cd = resp.headers.get("Content-Disposition", "")
        assert "filename" in cd, f"Missing filename in Content-Disposition: {cd}"
        assert "Report_CAM" in cd, f"Filename should contain 'Report_CAM': {cd}"
        
        print(f"Content-Disposition: {cd}")


class TestPeriziaExists:
    """Verify test perizia exists with required data."""

    def test_perizia_exists(self, auth_headers):
        """Test perizia per_test_ponte_8baac379 should exist."""
        url = f"{BASE_URL}/api/perizie/{TEST_PERIZIA_ID}"
        resp = requests.get(url, headers=auth_headers)
        
        assert resp.status_code == 200, f"Test perizia not found: {resp.status_code}"
        
        data = resp.json()
        print(f"Test perizia: {data.get('number')} - {data.get('tipo_danno')}")
        
        # Verify it has voci_costo for ponte test
        voci = data.get("voci_costo", [])
        assert len(voci) > 0, "Test perizia should have voci_costo for ponte test"
        
        print(f"Perizia has {len(voci)} voci_costo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

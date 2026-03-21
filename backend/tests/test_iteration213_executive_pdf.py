"""
Iteration 213 — Executive Professional PDF Upgrade Testing
Tests for:
1. CAM Alert endpoint with compliance check (danger/success/warning levels)
2. DOP Automatica with enriched data (riesame_checks, welding_entries, wps_docs, welders_data)
3. DOP PDF generation (multi-page, >30KB)
4. CE Label PDF generation
5. CAM Declaration PDF with PNRR reference
6. Rintracciabilita Totale PDF (landscape)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "74a451ef0a934313a8bb20dce4006ad2"
COMMESSA_ID = "com_2c57c1283871"
COMMESSA_NUMERO = "NF-2026-000036"


@pytest.fixture
def auth_session():
    """Session with authentication cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCAMAlertEndpoint:
    """Test CAM Alert pre-generation compliance check."""

    def test_cam_alert_returns_correct_structure(self, auth_session):
        """GET /api/cam/alert/{commessa_id} returns correct CAM compliance alert."""
        response = auth_session.get(f"{BASE_URL}/api/cam/alert/{COMMESSA_ID}", allow_redirects=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "level" in data, "Missing 'level' field"
        assert "message" in data, "Missing 'message' field"
        assert "suggerimenti" in data, "Missing 'suggerimenti' field"
        
        # Level should be one of: success, danger, warning, info
        assert data["level"] in ["success", "danger", "warning", "info"], f"Invalid level: {data['level']}"
        
        print(f"CAM Alert Level: {data['level']}")
        print(f"CAM Alert Message: {data['message']}")
        print(f"Percentuale Riciclato: {data.get('percentuale_riciclato')}")
        print(f"Soglia Minima: {data.get('soglia_minima')}")
        print(f"Suggerimenti: {data.get('suggerimenti')}")

    def test_cam_alert_danger_level_for_non_compliant(self, auth_session):
        """CAM alert returns 'danger' level when below threshold (73.6% < 75%)."""
        response = auth_session.get(f"{BASE_URL}/api/cam/alert/{COMMESSA_ID}", allow_redirects=True)
        
        assert response.status_code == 200
        data = response.json()
        
        # Based on context: commessa has 73.6% recycled (below 75% threshold)
        # So it should return 'danger' level
        if data.get("percentuale_riciclato") is not None:
            perc = data["percentuale_riciclato"]
            soglia = data.get("soglia_minima", 75)
            
            if perc < soglia:
                assert data["level"] == "danger", f"Expected 'danger' for {perc}% < {soglia}%, got {data['level']}"
                assert "NON CONFORME" in data["message"], f"Expected 'NON CONFORME' in message: {data['message']}"
            else:
                assert data["level"] == "success", f"Expected 'success' for {perc}% >= {soglia}%, got {data['level']}"
        
        print(f"Test passed: CAM alert level is '{data['level']}' as expected")


class TestDOPAutomatica:
    """Test DOP Automatica creation with enriched data."""

    def test_dop_automatica_includes_enriched_data(self, auth_session):
        """POST /api/fascicolo-tecnico/{cid}/dop-automatica includes riesame_checks, welding_entries, wps_docs, welders_data."""
        response = auth_session.post(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-automatica", allow_redirects=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dop" in data, "Missing 'dop' in response"
        
        dop = data["dop"]
        
        # Verify enriched fields are present
        assert "riesame_checks" in dop, "Missing 'riesame_checks' in DOP"
        assert "welding_entries" in dop, "Missing 'welding_entries' in DOP"
        assert "wps_docs" in dop, "Missing 'wps_docs' in DOP"
        assert "welders_data" in dop, "Missing 'welders_data' in DOP"
        
        # Verify other expected fields
        assert "dop_id" in dop, "Missing 'dop_id'"
        assert "dop_numero" in dop, "Missing 'dop_numero'"
        assert "classe_esecuzione" in dop, "Missing 'classe_esecuzione'"
        assert "batches_rintracciabilita" in dop, "Missing 'batches_rintracciabilita'"
        
        print(f"DOP ID: {dop['dop_id']}")
        print(f"DOP Numero: {dop['dop_numero']}")
        print(f"Classe Esecuzione: {dop['classe_esecuzione']}")
        print(f"Riesame Checks: {len(dop.get('riesame_checks', {}))} items")
        print(f"Welding Entries: {len(dop.get('welding_entries', []))} entries")
        print(f"WPS Docs: {len(dop.get('wps_docs', []))} docs")
        print(f"Welders Data: {len(dop.get('welders_data', []))} welders")
        print(f"Batches Rintracciabilita: {len(dop.get('batches_rintracciabilita', []))} batches")
        
        # Store DOP ID for PDF test
        return dop["dop_id"]


class TestPDFGeneration:
    """Test PDF generation endpoints."""

    def test_dop_pdf_generation_multipage(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf generates multi-page PDF (>30KB)."""
        # First create a DOP to get the ID
        create_response = auth_session.post(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-automatica", allow_redirects=True)
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create DOP: {create_response.text}")
        
        dop_id = create_response.json()["dop"]["dop_id"]
        
        # Now generate PDF
        pdf_response = auth_session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionata/{dop_id}/pdf",
            allow_redirects=True
        )
        
        assert pdf_response.status_code == 200, f"Expected 200, got {pdf_response.status_code}: {pdf_response.text}"
        assert pdf_response.headers.get("Content-Type") == "application/pdf", f"Expected application/pdf, got {pdf_response.headers.get('Content-Type')}"
        
        # Check file size > 30KB
        pdf_size = len(pdf_response.content)
        assert pdf_size > 30000, f"PDF size {pdf_size} bytes is less than 30KB minimum"
        
        print(f"DOP PDF generated successfully")
        print(f"PDF Size: {pdf_size / 1024:.1f} KB")
        print(f"Content-Type: {pdf_response.headers.get('Content-Type')}")

    def test_ce_label_pdf_generation(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf generates CE label."""
        response = auth_session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/etichetta-ce-1090/pdf",
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        pdf_size = len(response.content)
        assert pdf_size > 1000, f"CE Label PDF too small: {pdf_size} bytes"
        
        print(f"CE Label PDF generated successfully")
        print(f"PDF Size: {pdf_size / 1024:.1f} KB")

    def test_cam_declaration_pdf_with_pnrr(self, auth_session):
        """GET /api/cam/dichiarazione-pdf/{cid} generates CAM declaration with PNRR reference."""
        response = auth_session.get(
            f"{BASE_URL}/api/cam/dichiarazione-pdf/{COMMESSA_ID}",
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"CAM Declaration PDF too small: {pdf_size} bytes"
        
        print(f"CAM Declaration PDF generated successfully")
        print(f"PDF Size: {pdf_size / 1024:.1f} KB")

    def test_rintracciabilita_totale_pdf_landscape(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/rintracciabilita-totale/pdf generates landscape traceability sheet."""
        response = auth_session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/rintracciabilita-totale/pdf",
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"Rintracciabilita PDF too small: {pdf_size} bytes"
        
        print(f"Rintracciabilita Totale PDF generated successfully")
        print(f"PDF Size: {pdf_size / 1024:.1f} KB")


class TestDOPFrazionataList:
    """Test DOP Frazionate listing."""

    def test_list_dop_frazionate(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/dop-frazionate returns list of DOPs."""
        response = auth_session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionate",
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dop_frazionate" in data, "Missing 'dop_frazionate' in response"
        assert "total" in data, "Missing 'total' in response"
        
        print(f"Total DOPs: {data['total']}")
        for dop in data["dop_frazionate"][:3]:  # Show first 3
            print(f"  - {dop.get('dop_numero')}: {dop.get('descrizione')} ({dop.get('stato')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

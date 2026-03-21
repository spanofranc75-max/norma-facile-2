"""
Iteration 200: Manuale Utente Module Tests
Tests for:
1. GET /api/manuale/contenuti - returns 7 chapters and 8 FAQ items
2. GET /api/manuale/genera-pdf - returns a valid PDF file
3. POST /api/preventivatore/calcola with peso_kg_target (AI Predittivo Stima Rapida)
4. GET /api/preventivi - excludes 'eliminato' status
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_2026_active"


@pytest.fixture
def auth_cookies():
    """Return auth cookies for authenticated requests."""
    return {"session_token": SESSION_TOKEN}


@pytest.fixture
def auth_headers():
    """Return auth headers for authenticated requests."""
    return {"Authorization": f"Bearer {SESSION_TOKEN}"}


class TestManualeContenuti:
    """Tests for GET /api/manuale/contenuti endpoint."""

    def test_manuale_contenuti_requires_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/manuale/contenuti")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/manuale/contenuti requires authentication")

    def test_manuale_contenuti_returns_7_chapters(self, auth_cookies):
        """Test that endpoint returns exactly 7 chapters."""
        response = requests.get(
            f"{BASE_URL}/api/manuale/contenuti",
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "capitoli" in data, "Response should contain 'capitoli'"
        assert len(data["capitoli"]) == 7, f"Expected 7 chapters, got {len(data['capitoli'])}"
        
        # Verify chapter structure
        for ch in data["capitoli"]:
            assert "id" in ch, "Chapter should have 'id'"
            assert "titolo" in ch, "Chapter should have 'titolo'"
            assert "icona" in ch, "Chapter should have 'icona'"
        
        # Verify expected chapter IDs
        chapter_ids = [ch["id"] for ch in data["capitoli"]]
        expected_ids = ["intro", "preventivi", "commesse", "sicurezza", "risorse_umane", "tracciabilita", "dashboard"]
        assert chapter_ids == expected_ids, f"Chapter IDs mismatch: {chapter_ids}"
        
        print(f"PASS: /api/manuale/contenuti returns 7 chapters: {chapter_ids}")

    def test_manuale_contenuti_returns_8_faq(self, auth_cookies):
        """Test that endpoint returns exactly 8 FAQ items."""
        response = requests.get(
            f"{BASE_URL}/api/manuale/contenuti",
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "faq" in data, "Response should contain 'faq'"
        assert len(data["faq"]) == 8, f"Expected 8 FAQ items, got {len(data['faq'])}"
        
        # Verify FAQ structure
        for faq in data["faq"]:
            assert "domanda" in faq, "FAQ should have 'domanda'"
            assert "risposta" in faq, "FAQ should have 'risposta'"
        
        print(f"PASS: /api/manuale/contenuti returns 8 FAQ items")

    def test_manuale_contenuti_returns_version(self, auth_cookies):
        """Test that endpoint returns version 2.0."""
        response = requests.get(
            f"{BASE_URL}/api/manuale/contenuti",
            cookies=auth_cookies
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "versione" in data, "Response should contain 'versione'"
        assert data["versione"] == "2.0", f"Expected version 2.0, got {data['versione']}"
        
        print("PASS: /api/manuale/contenuti returns version 2.0")


class TestManualeGeneraPDF:
    """Tests for GET /api/manuale/genera-pdf endpoint."""

    def test_genera_pdf_requires_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/manuale/genera-pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/manuale/genera-pdf requires authentication")

    def test_genera_pdf_returns_valid_pdf(self, auth_cookies):
        """Test that endpoint returns a valid PDF file."""
        response = requests.get(
            f"{BASE_URL}/api/manuale/genera-pdf",
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment disposition, got {content_disp}"
        assert "Manuale_Utente" in content_disp, f"Expected 'Manuale_Utente' in filename, got {content_disp}"
        
        # Check PDF content starts with PDF magic bytes
        content = response.content
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b'%PDF', "Content should start with PDF magic bytes"
        
        print(f"PASS: /api/manuale/genera-pdf returns valid PDF ({len(content)} bytes)")


class TestPreventivatoreCalcola:
    """Tests for POST /api/preventivatore/calcola endpoint (AI Predittivo Stima Rapida)."""

    def test_calcola_requires_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            json={"peso_kg_target": 2500}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/preventivatore/calcola requires authentication")

    def test_calcola_with_peso_kg_target(self, auth_cookies):
        """Test Stima Rapida with peso_kg_target=2500."""
        payload = {
            "materiali": [],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20,
            "peso_kg_target": 2500
        }
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            json=payload,
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "calcolo" in data, "Response should contain 'calcolo'"
        assert "stima_ore" in data, "Response should contain 'stima_ore'"
        
        # peso_totale_kg is at top level
        assert "peso_totale_kg" in data, "Response should have 'peso_totale_kg'"
        assert data["peso_totale_kg"] == 2500, f"Expected peso 2500, got {data['peso_totale_kg']}"
        
        calcolo = data["calcolo"]
        riepilogo = calcolo.get("riepilogo", {})
        
        # Verify totals are calculated (not zero)
        assert "totale_vendita" in riepilogo, "riepilogo should have 'totale_vendita'"
        assert "costo_materiali" in riepilogo, "riepilogo should have 'costo_materiali'"
        assert "costo_manodopera" in riepilogo, "riepilogo should have 'costo_manodopera'"
        
        # Totale vendita should be > 0 for 2500kg
        assert riepilogo["totale_vendita"] > 0, f"totale_vendita should be > 0, got {riepilogo['totale_vendita']}"
        
        print(f"PASS: /api/preventivatore/calcola with peso_kg_target=2500 returns valid calculation")
        print(f"  - peso_totale_kg: {data['peso_totale_kg']}")
        print(f"  - costo_materiali: {riepilogo.get('costo_materiali', 0)}")
        print(f"  - costo_manodopera: {riepilogo.get('costo_manodopera', 0)}")
        print(f"  - totale_vendita: {riepilogo['totale_vendita']}")

    def test_calcola_with_different_tipologie(self, auth_cookies):
        """Test Stima Rapida with different structure types."""
        tipologie = ["leggera", "media", "complessa", "speciale"]
        
        for tipo in tipologie:
            payload = {
                "materiali": [],
                "tipologia_struttura": tipo,
                "peso_kg_target": 1000
            }
            response = requests.post(
                f"{BASE_URL}/api/preventivatore/calcola",
                json=payload,
                cookies=auth_cookies
            )
            assert response.status_code == 200, f"Failed for tipologia {tipo}: {response.text}"
            data = response.json()
            assert data["peso_totale_kg"] == 1000, f"Expected peso 1000, got {data.get('peso_totale_kg')}"
            totale = data["calcolo"]["riepilogo"]["totale_vendita"]
            print(f"  - tipologia '{tipo}': totale_vendita = {totale}")
        
        print("PASS: /api/preventivatore/calcola works with all tipologie")


class TestPreventiviListExcludesEliminato:
    """Tests for GET /api/preventivi excluding 'eliminato' status."""

    def test_preventivi_list_requires_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/preventivi")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/preventivi requires authentication")

    def test_preventivi_list_excludes_eliminato(self, auth_cookies):
        """Test that preventivi list excludes 'eliminato' status."""
        response = requests.get(
            f"{BASE_URL}/api/preventivi",
            cookies=auth_cookies
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check that no preventivo has status 'eliminato'
        preventivi = data.get("preventivi", data) if isinstance(data, dict) else data
        if isinstance(preventivi, dict):
            preventivi = preventivi.get("preventivi", [])
        
        eliminati_count = 0
        for prev in preventivi:
            if prev.get("status") == "eliminato":
                eliminati_count += 1
        
        assert eliminati_count == 0, f"Found {eliminati_count} preventivi with status 'eliminato'"
        
        print(f"PASS: /api/preventivi excludes 'eliminato' status (checked {len(preventivi)} items)")


class TestManualeEndpointIntegration:
    """Integration tests for manuale module."""

    def test_full_manuale_workflow(self, auth_cookies):
        """Test complete workflow: get contents, then generate PDF."""
        # Step 1: Get contents
        response1 = requests.get(
            f"{BASE_URL}/api/manuale/contenuti",
            cookies=auth_cookies
        )
        assert response1.status_code == 200
        data = response1.json()
        assert len(data["capitoli"]) == 7
        assert len(data["faq"]) == 8
        
        # Step 2: Generate PDF
        response2 = requests.get(
            f"{BASE_URL}/api/manuale/genera-pdf",
            cookies=auth_cookies
        )
        assert response2.status_code == 200
        assert "application/pdf" in response2.headers.get("Content-Type", "")
        
        print("PASS: Full manuale workflow (contents + PDF generation)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

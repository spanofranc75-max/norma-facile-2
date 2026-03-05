"""Test Iteration 139: Perizia Pro PDF Features

Tests for the upgraded PDF perizia report with:
1. SVG semicircular tachometer gauge for Risk Score
2. Two-column layout for risk cards (problem+photo left, solution+ref image right)
3. Reference solution images from static library
4. Professional summary box with risk counts
5. Numbered section headers
"""
import pytest
import sys
import os
import base64

sys.path.insert(0, "/app/backend")

from services.pdf_perizia_sopralluogo import generate_perizia_pdf, _gauge_svg, _get_solution_image
from services.ref_images_library import get_ref_image_b64, KEYWORD_MAP

# ── Reference Images Library Tests ──

class TestRefImagesLibrary:
    """Test the reference image library for solution images."""

    def test_costa_keyword_returns_base64(self):
        """costa keyword should return non-empty base64 string."""
        b64 = get_ref_image_b64("costa")
        assert b64, "costa keyword should return base64 image"
        assert len(b64) > 1000, "costa image should be substantial (> 1000 chars)"
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(b64)
            assert len(decoded) > 0, "Should decode to non-empty bytes"
        except Exception as e:
            pytest.fail(f"costa base64 is not valid: {e}")

    def test_fotocellula_keyword_returns_base64(self):
        """fotocellula keyword should return non-empty base64 string."""
        b64 = get_ref_image_b64("fotocellula")
        assert b64, "fotocellula keyword should return base64 image"
        assert len(b64) > 1000, "fotocellula image should be substantial"

    def test_fotocellule_plural_also_works(self):
        """fotocellule (plural) should also map to the same image."""
        b64 = get_ref_image_b64("fotocellule")
        assert b64, "fotocellule (plural) should also return base64 image"

    def test_rete_keyword_returns_base64(self):
        """rete keyword should return non-empty base64 string."""
        b64 = get_ref_image_b64("rete")
        assert b64, "rete keyword should return base64 image"
        assert len(b64) > 1000, "rete image should be substantial"

    def test_encoder_keyword_returns_base64(self):
        """encoder keyword should return non-empty base64 string."""
        b64 = get_ref_image_b64("encoder")
        assert b64, "encoder keyword should return base64 image"
        assert len(b64) > 1000, "encoder image should be substantial"

    def test_motore_maps_to_encoder(self):
        """motore keyword should map to encoder image."""
        b64_motore = get_ref_image_b64("motore")
        b64_encoder = get_ref_image_b64("encoder")
        assert b64_motore, "motore should return an image"
        assert b64_motore == b64_encoder, "motore should map to same image as encoder"

    def test_limitatore_maps_to_encoder(self):
        """limitatore keyword should map to encoder image."""
        b64_limitatore = get_ref_image_b64("limitatore")
        b64_encoder = get_ref_image_b64("encoder")
        assert b64_limitatore, "limitatore should return an image"
        assert b64_limitatore == b64_encoder, "limitatore should map to same image as encoder"

    def test_unknown_keyword_returns_empty(self):
        """Unknown keywords should return empty string."""
        b64 = get_ref_image_b64("nonexistent_keyword_xyz123")
        assert b64 == "", "Unknown keyword should return empty string"

    def test_keyword_map_has_all_expected_entries(self):
        """KEYWORD_MAP should have entries for all 4 base images."""
        expected = ["costa", "fotocellula", "rete", "encoder"]
        for kw in expected:
            assert kw in KEYWORD_MAP, f"KEYWORD_MAP should contain '{kw}'"


# ── SVG Gauge Tests ──

class TestGaugeSvg:
    """Test the SVG tachometer gauge generation."""

    def test_gauge_low_conformity_28_percent(self):
        """28% conformity should render red gauge."""
        svg = _gauge_svg(28)
        assert "svg" in svg.lower(), "Should contain SVG element"
        assert "28%" in svg, "Should display 28% text"
        # Red color for low conformity
        assert "#DC2626" in svg or "dc2626" in svg.lower(), "Should use red color for low conformity"

    def test_gauge_medium_conformity_50_percent(self):
        """50% conformity should render amber gauge."""
        svg = _gauge_svg(50)
        assert "50%" in svg, "Should display 50% text"
        # Amber color for medium conformity
        assert "#D97706" in svg or "d97706" in svg.lower(), "Should use amber color for medium conformity"

    def test_gauge_high_conformity_72_percent(self):
        """72% conformity should render green gauge."""
        svg = _gauge_svg(72)
        assert "72%" in svg, "Should display 72% text"
        # Green color for high conformity
        assert "#16A34A" in svg or "16a34a" in svg.lower(), "Should use green color for high conformity"

    def test_gauge_edge_case_0_percent(self):
        """0% conformity should be clamped and render red."""
        svg = _gauge_svg(0)
        assert "0%" in svg, "Should display 0%"
        assert "#DC2626" in svg or "dc2626" in svg.lower(), "Should use red color"

    def test_gauge_edge_case_100_percent(self):
        """100% conformity should render green."""
        svg = _gauge_svg(100)
        assert "100%" in svg, "Should display 100%"
        assert "#16A34A" in svg or "16a34a" in svg.lower(), "Should use green color"

    def test_gauge_contains_semicircle_arc(self):
        """Gauge should contain semicircle arc path."""
        svg = _gauge_svg(50)
        assert "path" in svg.lower(), "Should contain path element for arc"
        assert "A" in svg, "Should contain arc command in path"

    def test_gauge_contains_needle(self):
        """Gauge should contain needle line element."""
        svg = _gauge_svg(50)
        assert "line" in svg.lower(), "Should contain line element for needle"


# ── PDF Generation Tests ──

class TestPdfGeneration:
    """Test the full PDF generation with mock data."""

    @pytest.fixture
    def mock_sopralluogo_4_risks(self):
        """Mock sopralluogo with 4 risks (2 alta, 2 media) and matching keywords."""
        return {
            "sopralluogo_id": "sop_test139",
            "document_number": "SOP-2026/0139",
            "client_name": "Test Cliente S.r.l.",
            "indirizzo": "Via Test 1",
            "comune": "Testville",
            "provincia": "TV",
            "descrizione_utente": "Test description",
            "created_at": "2026-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "scorrevole",
                "descrizione_generale": "Test cancello scorrevole",
                "conformita_percentuale": 28,
                "rischi": [
                    {
                        "zona": "Bordo chiusura",
                        "tipo_rischio": "schiacciamento",
                        "gravita": "alta",
                        "problema": "Assenza costa sensibile",
                        "norma_riferimento": "EN 12453",
                        "soluzione": "Installare costa sensibile 8K2",
                        "confermato": True,
                    },
                    {
                        "zona": "Zona passaggio",
                        "tipo_rischio": "impatto",
                        "gravita": "alta",
                        "problema": "Nessuna fotocellula",
                        "norma_riferimento": "EN 12453",
                        "soluzione": "Installare coppia fotocellule",
                        "confermato": True,
                    },
                    {
                        "zona": "Parte alta",
                        "tipo_rischio": "cesoiamento",
                        "gravita": "media",
                        "problema": "Spazi ampi tra maglie",
                        "norma_riferimento": "EN 13241",
                        "soluzione": "Applicare rete anti-cesoiamento",
                        "confermato": True,
                    },
                    {
                        "zona": "Motore",
                        "tipo_rischio": "impatto",
                        "gravita": "media",
                        "problema": "Motore senza encoder",
                        "norma_riferimento": "EN 12453",
                        "soluzione": "Installare encoder sul motore",
                        "confermato": True,
                    },
                ],
                "dispositivi_presenti": ["Lampeggiante"],
                "dispositivi_mancanti": ["Costa", "Fotocellule", "Encoder"],
                "materiali_suggeriti": [
                    {"keyword": "costa", "descrizione": "Costa sensibile", "quantita": 1, "prezzo": 180, "priorita": "obbligatorio"},
                    {"keyword": "fotocellula", "descrizione": "Fotocellule", "quantita": 2, "prezzo": 85, "priorita": "obbligatorio"},
                ],
                "note_tecniche": "Test notes",
            },
        }

    @pytest.fixture
    def mock_company(self):
        return {
            "company_name": "Test Company S.r.l.",
            "address": "Via Company 1",
            "cap": "12345",
            "city": "TestCity",
            "province": "TC",
            "partita_iva": "01234567890",
        }

    def test_pdf_generates_with_4_risks(self, mock_sopralluogo_4_risks, mock_company):
        """PDF should generate successfully with 4 risks."""
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=None)
        assert pdf_bytes, "PDF should be generated"
        assert len(pdf_bytes) > 10000, "PDF should have substantial content"
        # PDF magic bytes
        assert pdf_bytes[:4] == b'%PDF', "Should be valid PDF format"

    def test_pdf_generates_with_empty_photos(self, mock_sopralluogo_4_risks, mock_company):
        """PDF should generate even with empty photos list."""
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=[])
        assert pdf_bytes, "PDF should generate with empty photos"
        assert len(pdf_bytes) > 10000, "PDF should have content"

    def test_pdf_file_size_indicates_embedded_images(self, mock_sopralluogo_4_risks, mock_company):
        """PDF with ref images should be larger than without."""
        # The ref images add substantial size when embedded in HTML
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=None)
        # With 4 ref images (~800KB total), PDF should be >100KB
        assert len(pdf_bytes) > 100 * 1024, f"PDF should be >100KB with embedded images, got {len(pdf_bytes)//1024}KB"

    def test_pdf_with_low_conformity_28(self, mock_sopralluogo_4_risks, mock_company):
        """PDF with 28% conformity should generate correctly."""
        mock_sopralluogo_4_risks["analisi_ai"]["conformita_percentuale"] = 28
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=None)
        assert pdf_bytes, "PDF should generate"
        assert len(pdf_bytes) > 10000

    def test_pdf_with_medium_conformity_50(self, mock_sopralluogo_4_risks, mock_company):
        """PDF with 50% conformity should generate correctly."""
        mock_sopralluogo_4_risks["analisi_ai"]["conformita_percentuale"] = 50
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=None)
        assert pdf_bytes, "PDF should generate"

    def test_pdf_with_high_conformity_72(self, mock_sopralluogo_4_risks, mock_company):
        """PDF with 72% conformity should generate correctly."""
        mock_sopralluogo_4_risks["analisi_ai"]["conformita_percentuale"] = 72
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo_4_risks, mock_company, photos_b64=None)
        assert pdf_bytes, "PDF should generate"


# ── Solution Image Matching Tests ──

class TestSolutionImageMatching:
    """Test the _get_solution_image function for keyword matching."""

    def test_costa_in_soluzione_returns_image(self):
        """Risk with 'costa' in soluzione should get ref image."""
        risk = {"soluzione": "Installare costa sensibile", "zona": "", "tipo_rischio": ""}
        b64 = _get_solution_image(risk)
        assert b64, "Should return costa image"

    def test_fotocellula_in_soluzione_returns_image(self):
        """Risk with 'fotocellula' in soluzione should get ref image."""
        risk = {"soluzione": "Installare fotocellula orientabile", "zona": "", "tipo_rischio": ""}
        b64 = _get_solution_image(risk)
        assert b64, "Should return fotocellula image"

    def test_rete_in_soluzione_returns_image(self):
        """Risk with 'rete' in soluzione should get ref image."""
        risk = {"soluzione": "Applicare rete anti-cesoiamento", "zona": "", "tipo_rischio": ""}
        b64 = _get_solution_image(risk)
        assert b64, "Should return rete image"

    def test_encoder_in_soluzione_returns_image(self):
        """Risk with 'encoder' in soluzione should get ref image."""
        risk = {"soluzione": "Installare encoder sul motore", "zona": "", "tipo_rischio": ""}
        b64 = _get_solution_image(risk)
        assert b64, "Should return encoder image"

    def test_no_keyword_match_returns_empty(self):
        """Risk without matching keywords should return empty."""
        risk = {"soluzione": "Riparare la struttura", "zona": "base", "tipo_rischio": "altro"}
        b64 = _get_solution_image(risk)
        assert b64 == "", "Should return empty for no keyword match"


# ── API Endpoint Tests ──

class TestApiEndpoint:
    """Test the /api/sopralluoghi/{id}/pdf endpoint edge cases."""

    @pytest.fixture(scope="class")
    def session_token(self):
        """Create test user and session for API tests."""
        import subprocess
        result = subprocess.run([
            "mongosh", "--quiet", "--eval", """
            use('test_database');
            var userId = 'user_perizia139_' + Date.now();
            var sessionToken = 'test_session_perizia139_' + Date.now();
            db.users.insertOne({
              user_id: userId,
              email: 'test.perizia139@example.com',
              name: 'Test Perizia User',
              role: 'admin',
              created_at: new Date()
            });
            db.user_sessions.insertOne({
              user_id: userId,
              session_token: sessionToken,
              expires_at: new Date(Date.now() + 24*60*60*1000),
              created_at: new Date()
            });
            print(sessionToken);
            """
        ], capture_output=True, text=True)
        token = result.stdout.strip().split('\n')[-1]
        return token

    @pytest.fixture
    def base_url(self):
        return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

    def test_pdf_endpoint_returns_400_without_ai_analysis(self, session_token, base_url):
        """PDF endpoint should return 400 if no AI analysis exists."""
        import requests
        import uuid
        
        # First create a sopralluogo without AI analysis
        headers = {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}
        
        create_resp = requests.post(
            f"{base_url}/api/sopralluoghi/",
            json={
                "client_id": "",
                "indirizzo": "Via Test PDF 1",
                "comune": "TestCity",
                "provincia": "TV",
                "tipo_intervento": "messa_a_norma",
                "descrizione_utente": "Test for PDF 400 error"
            },
            headers=headers
        )
        
        if create_resp.status_code != 200:
            pytest.skip(f"Could not create sopralluogo: {create_resp.status_code}")
        
        sop_id = create_resp.json().get("sopralluogo_id")
        
        # Now try to get PDF without running AI analysis
        pdf_resp = requests.get(
            f"{base_url}/api/sopralluoghi/{sop_id}/pdf",
            headers=headers
        )
        
        assert pdf_resp.status_code == 400, f"Should return 400, got {pdf_resp.status_code}"
        assert "analisi" in pdf_resp.text.lower() or "ai" in pdf_resp.text.lower(), \
            "Error should mention AI analysis requirement"
        
        # Cleanup
        requests.delete(f"{base_url}/api/sopralluoghi/{sop_id}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

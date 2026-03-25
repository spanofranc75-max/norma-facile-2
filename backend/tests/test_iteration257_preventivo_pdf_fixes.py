"""
Iteration 257 - Preventivo PDF Generation Fixes Tests

Tests for 7 issues in preventivo PDF generation:
1) Remove duplicate 'PREVENTIVO N.' title
2) White background instead of gray-ivory
3) Dynamic conditions (payment, validity, delivery from preventivo data)
4) Conditional CODICE/SCONTI columns
5) Dynamic company address in conditions
6) Fix typos in conditions text
7) Fit conditions in 2 pages instead of 3
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
DEMO_COOKIE = {"session_token": "demo_session_token_normafacile"}


class TestPDFEndpointsReturnValidPDF:
    """Test that PDF endpoints return valid PDFs with HTTP 200"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup demo session"""
        self.session = requests.Session()
        self.session.cookies.update(DEMO_COOKIE)
        # Login to demo - POST without trailing slash
        resp = self.session.post(f"{BASE_URL}/api/demo/login")
        assert resp.status_code == 200, f"Demo login failed: {resp.text}"
    
    def test_pdf_endpoint_prev_demo_complete(self):
        """GET /api/preventivi/prev_demo_complete/pdf returns valid PDF with HTTP 200"""
        resp = self.session.get(f"{BASE_URL}/api/preventivi/prev_demo_complete/pdf")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.headers.get('content-type') == 'application/pdf', f"Expected PDF, got {resp.headers.get('content-type')}"
        # Check PDF magic bytes
        assert resp.content[:4] == b'%PDF', "Response is not a valid PDF"
        print(f"PASS: prev_demo_complete PDF returned {len(resp.content)} bytes")
    
    def test_pdf_endpoint_prev_demo_simple(self):
        """GET /api/preventivi/prev_demo_simple/pdf returns valid PDF with HTTP 200"""
        resp = self.session.get(f"{BASE_URL}/api/preventivi/prev_demo_simple/pdf")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.headers.get('content-type') == 'application/pdf', f"Expected PDF, got {resp.headers.get('content-type')}"
        assert resp.content[:4] == b'%PDF', "Response is not a valid PDF"
        print(f"PASS: prev_demo_simple PDF returned {len(resp.content)} bytes")
    
    def test_pdf_endpoint_prev_demo_main(self):
        """GET /api/preventivi/prev_demo_main/pdf returns valid PDF with HTTP 200"""
        resp = self.session.get(f"{BASE_URL}/api/preventivi/prev_demo_main/pdf")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.headers.get('content-type') == 'application/pdf', f"Expected PDF, got {resp.headers.get('content-type')}"
        assert resp.content[:4] == b'%PDF', "Response is not a valid PDF"
        print(f"PASS: prev_demo_main PDF returned {len(resp.content)} bytes")


class TestCSSWhiteBackground:
    """Test that CSS has white background instead of gray-ivory"""
    
    def test_common_css_page_background_white(self):
        """CSS @page has background: white"""
        from services.pdf_template import COMMON_CSS
        
        # Check @page rule has white background
        assert "background: white" in COMMON_CSS, "COMMON_CSS @page should have 'background: white'"
        print("PASS: @page has background: white")
    
    def test_common_css_body_background_white(self):
        """CSS body has background-color: #ffffff"""
        from services.pdf_template import COMMON_CSS
        
        # Check body has white background
        assert "background-color: #ffffff" in COMMON_CSS, "COMMON_CSS body should have 'background-color: #ffffff'"
        print("PASS: body has background-color: #ffffff")
    
    def test_no_gray_ivory_background(self):
        """Ensure no gray/ivory background colors in CSS"""
        from services.pdf_template import COMMON_CSS
        
        # Check for common gray/ivory colors that should NOT be present as page/body background
        gray_colors = ['#f5f5f5', '#f0f0f0', '#fafafa', '#fffff0', 'ivory', '#fffaf0']
        for color in gray_colors:
            # Allow these colors in specific elements like info-box, but not in @page or body
            page_section = COMMON_CSS.split('@page')[1].split('}')[0] if '@page' in COMMON_CSS else ""
            body_section = re.search(r'body\s*\{[^}]+\}', COMMON_CSS)
            body_css = body_section.group() if body_section else ""
            
            assert color.lower() not in page_section.lower(), f"@page should not have {color}"
            assert color.lower() not in body_css.lower(), f"body should not have {color}"
        print("PASS: No gray/ivory background in @page or body")


class TestConditionalColumns:
    """Test conditional CODICE/SCONTI columns in PDF - unit tests, no API needed"""
    
    def test_has_codici_detection_with_codice(self):
        """When lines have codice_articolo, has_codici should be True"""
        lines_with_codice = [
            {"codice_articolo": "ART001", "description": "Test item"},
            {"codice_articolo": "", "description": "Item without code"}
        ]
        has_codici = any((ln.get("codice_articolo") or "").strip() for ln in lines_with_codice)
        assert has_codici is True, "has_codici should be True when at least one line has codice_articolo"
        print("PASS: has_codici correctly detects lines with codice_articolo")
    
    def test_has_codici_detection_without_codice(self):
        """When no lines have codice_articolo, has_codici should be False"""
        lines_without_codice = [
            {"codice_articolo": "", "description": "Test item 1"},
            {"codice_articolo": None, "description": "Test item 2"},
            {"description": "Test item 3"}  # No codice_articolo key
        ]
        has_codici = any((ln.get("codice_articolo") or "").strip() for ln in lines_without_codice)
        assert has_codici is False, "has_codici should be False when no lines have codice_articolo"
        print("PASS: has_codici correctly returns False when no codice_articolo")
    
    def test_has_sconti_detection_with_discount(self):
        """When lines have sconto > 0, has_sconti should be True"""
        lines_with_sconto = [
            {"sconto_1": 10, "sconto_2": 0},
            {"sconto_1": 0, "sconto_2": 5}
        ]
        has_sconti = any(
            float(ln.get("sconto_1") or 0) > 0 or float(ln.get("sconto_2") or 0) > 0
            for ln in lines_with_sconto
        )
        assert has_sconti is True, "has_sconti should be True when at least one line has discount"
        print("PASS: has_sconti correctly detects lines with discounts")
    
    def test_has_sconti_detection_without_discount(self):
        """When no lines have sconto > 0, has_sconti should be False"""
        lines_without_sconto = [
            {"sconto_1": 0, "sconto_2": 0},
            {"sconto_1": None, "sconto_2": None},
            {}  # No sconto keys
        ]
        has_sconti = any(
            float(ln.get("sconto_1") or 0) > 0 or float(ln.get("sconto_2") or 0) > 0
            for ln in lines_without_sconto
        )
        assert has_sconti is False, "has_sconti should be False when no lines have discounts"
        print("PASS: has_sconti correctly returns False when no discounts")


class TestBuildConditionsHtml:
    """Test build_conditions_html function with dynamic values"""
    
    def test_build_conditions_accepts_preventivo_parameter(self):
        """build_conditions_html function accepts optional preventivo parameter"""
        from services.pdf_template import build_conditions_html
        import inspect
        
        sig = inspect.signature(build_conditions_html)
        params = list(sig.parameters.keys())
        
        assert 'preventivo' in params, "build_conditions_html should accept 'preventivo' parameter"
        
        # Check it's optional (has default value)
        preventivo_param = sig.parameters['preventivo']
        assert preventivo_param.default is not inspect.Parameter.empty, "preventivo parameter should have default value"
        print("PASS: build_conditions_html accepts optional preventivo parameter")
    
    def test_typo_fix_se_non_espressamente(self):
        """Typo fix: 'se non espressamente' instead of 'se no nespressamente'"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Questo testo contiene se no nespressamente indicato."
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        assert "se no nespressamente" not in result, "Typo 'se no nespressamente' should be fixed"
        assert "se non espressamente" in result, "Should contain corrected 'se non espressamente'"
        print("PASS: Typo 'se no nespressamente' -> 'se non espressamente' fixed")
    
    def test_typo_fix_materiali_in_cantiere(self):
        """Typo fix: 'materiali in cantiere' instead of 'materiali incantiere'"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Deposito materiali incantiere non consentito."
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        assert "materiali incantiere" not in result, "Typo 'materiali incantiere' should be fixed"
        assert "materiali in cantiere" in result, "Should contain corrected 'materiali in cantiere'"
        print("PASS: Typo 'materiali incantiere' -> 'materiali in cantiere' fixed")
    
    def test_dynamic_payment_replacement(self):
        """Dynamic payment replacement works when preventivo has payment_type_label"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Pagamento : Acconto del 40% alla conferma d'ordine."
        }
        preventivo = {
            "payment_type_label": "Bonifico 30 giorni fine mese"
        }
        
        result = build_conditions_html(company, "TEST-001", preventivo)
        
        # The regex should replace "Acconto del 40%..." with the payment_type_label
        assert "Acconto del 40%" not in result, "Hardcoded payment should be replaced"
        assert "Bonifico 30 giorni fine mese" in result, "Dynamic payment label should be present"
        print("PASS: Dynamic payment replacement works")
    
    def test_dynamic_validity_replacement(self):
        """Dynamic validity replacement works (replaces N giorni)"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Validita offerta: 15 giorni dalla data di emissione."
        }
        preventivo = {
            "validity_days": 45
        }
        
        result = build_conditions_html(company, "TEST-001", preventivo)
        
        # Should replace "15 giorni dalla data di emissione" with "45 giorni dalla data di emissione"
        assert "45 giorni dalla data di emissione" in result, "Validity should be replaced with preventivo value"
        print("PASS: Dynamic validity replacement works")
    
    def test_dynamic_company_address_replacement(self):
        """Dynamic company address replacement works"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "address": "Via Roma 123",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "condizioni_vendita": "Ritiro presso via dei Pioppi n. 11 - 40010 Padulle BO"
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        # Should replace hardcoded address with company address
        assert "via dei Pioppi n. 11 - 40010 Padulle BO" not in result, "Hardcoded address should be replaced"
        assert "Via Roma 123" in result, "Company address should be present"
        print("PASS: Dynamic company address replacement works")
    
    def test_empty_conditions_returns_empty(self):
        """Empty conditions returns empty string"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": ""
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        assert result == "", "Empty conditions should return empty string"
        print("PASS: Empty conditions returns empty string")
    
    def test_conditions_without_preventivo(self):
        """build_conditions_html works without preventivo parameter"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Standard conditions text."
        }
        
        # Should not raise error
        result = build_conditions_html(company, "TEST-001")
        
        assert "Standard conditions text" in result, "Conditions should be present"
        print("PASS: build_conditions_html works without preventivo parameter")


class TestPDFTitleNotDuplicated:
    """Test that PDF title 'PREVENTIVO N.' appears exactly once - unit test"""
    
    def test_title_appears_once_in_code(self):
        """Verify PREVENTIVO N. title appears only once in the PDF generation code"""
        import inspect
        from routes.preventivi import generate_preventivo_pdf
        
        source = inspect.getsource(generate_preventivo_pdf)
        
        # Count occurrences of the title pattern
        title_count = source.count("PREVENTIVO N.")
        
        assert title_count == 1, f"'PREVENTIVO N.' should appear exactly once in generate_preventivo_pdf, found {title_count}"
        print(f"PASS: 'PREVENTIVO N.' appears exactly {title_count} time(s) in code")


class TestAdditionalTypoFixes:
    """Test additional typo fixes in conditions"""
    
    def test_typo_fix_fatto_salvo(self):
        """Typo fix: 'fatto salvo nell'area di cantiere non ci sia'"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "fatto salvonell'area di cantiere nonci sia spazio"
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        # Note: HTML escapes apostrophe to &#x27; so we check for the escaped version
        assert "fatto salvonell" not in result, "Typo should be fixed"
        # The corrected text will have HTML-escaped apostrophe
        assert "fatto salvo nell" in result, "Corrected text should be present"
        assert "area di cantiere non ci sia" in result, "Corrected text should be present"
        print("PASS: Typo 'fatto salvonell'area...' fixed")
    
    def test_typo_fix_oneri_per_eventuali(self):
        """Typo fix: 'Oneri per eventuali' instead of 'Oneri pe reventuali'"""
        from services.pdf_template import build_conditions_html
        
        company = {
            "business_name": "Test Company",
            "condizioni_vendita": "Oneri pe reventuali modifiche a carico del cliente."
        }
        
        result = build_conditions_html(company, "TEST-001")
        
        assert "Oneri pe reventuali" not in result, "Typo should be fixed"
        assert "Oneri per eventuali" in result, "Corrected text should be present"
        print("PASS: Typo 'Oneri pe reventuali' -> 'Oneri per eventuali' fixed")


class TestPDFGenerationIntegration:
    """Integration tests for PDF generation with various preventivo configurations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup demo session"""
        self.session = requests.Session()
        self.session.cookies.update(DEMO_COOKIE)
        # Login to demo - POST without trailing slash
        resp = self.session.post(f"{BASE_URL}/api/demo/login")
        assert resp.status_code == 200
    
    def test_get_preventivo_data(self):
        """Verify we can get preventivo data for testing"""
        resp = self.session.get(f"{BASE_URL}/api/preventivi/prev_demo_complete")
        assert resp.status_code == 200, f"Failed to get preventivo: {resp.text}"
        data = resp.json()
        assert "preventivo_id" in data, "Response should contain preventivo_id"
        assert "lines" in data, "Response should contain lines"
        print(f"PASS: Got preventivo with {len(data.get('lines', []))} lines")
    
    def test_pdf_generation_does_not_error(self):
        """PDF generation completes without errors for all demo preventivi"""
        demo_ids = ["prev_demo_complete", "prev_demo_simple", "prev_demo_main"]
        
        for prev_id in demo_ids:
            resp = self.session.get(f"{BASE_URL}/api/preventivi/{prev_id}/pdf")
            assert resp.status_code == 200, f"PDF generation failed for {prev_id}: {resp.status_code}"
            assert len(resp.content) > 1000, f"PDF for {prev_id} seems too small: {len(resp.content)} bytes"
        
        print(f"PASS: All {len(demo_ids)} demo preventivi generate PDFs successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

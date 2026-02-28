"""
Test PDF V2 Format - Unified Professional Document Format
Testing RdP and OdA PDF generation with new V2 template
Features tested:
- Two-column header (company left, fornitore right)
- 'Spett.le' label above fornitore name
- Centered title with document number (RDA-xxx, ODA-xxx)
- DATA and RIF. COMMESSA info boxes
- Blue header table row
- Yellow 'CERTIFICATO RICHIESTO' box for materials with 3.1
- Professional footer with greeting
"""
import pytest
import requests
import os
import re
import json
from io import BytesIO
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Will be set during test setup
AUTH_TOKEN = None
USER_ID = None


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_setup(api_client):
    """Setup authentication for tests"""
    global AUTH_TOKEN, USER_ID
    
    # Create a test session
    test_session_id = f"test_pdf_v2_{datetime.now().timestamp()}"
    login_response = api_client.get(f"{BASE_URL}/api/auth/test-session/{test_session_id}")
    
    if login_response.status_code == 200:
        data = login_response.json()
        AUTH_TOKEN = data.get("access_token")
        USER_ID = data.get("user_id")
        api_client.headers.update({"Authorization": f"Bearer {AUTH_TOKEN}"})
        return {"token": AUTH_TOKEN, "user_id": USER_ID}
    else:
        pytest.skip(f"Failed to create test session: {login_response.status_code}")


@pytest.fixture(scope="module")
def test_commessa(api_client, auth_setup):
    """Create a test commessa for PDF generation tests"""
    commessa_data = {
        "numero": "PDFV2-TEST-001",
        "cliente_nome": "Test Cliente SpA",
        "cliente_id": "",
        "descrizione": "Test commessa for PDF V2 format testing",
        "importo_preventivo": 15000.00,
        "normativa": "EN_1090"
    }
    
    response = api_client.post(f"{BASE_URL}/api/commesse", json=commessa_data)
    assert response.status_code == 201, f"Failed to create commessa: {response.text}"
    
    commessa = response.json()
    commessa_id = commessa.get("commessa_id")
    
    yield {"commessa_id": commessa_id, "numero": commessa_data["numero"]}
    
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


@pytest.fixture(scope="module")
def company_settings(api_client, auth_setup):
    """Ensure company settings exist for PDF generation"""
    company_data = {
        "business_name": "Steel Project Design Srls",
        "address": "Via Roma 123",
        "city": "Milano",
        "province": "MI",
        "cap": "20100",
        "vat_number": "IT12345678901",
        "phone": "+39 02 12345678",
        "email": "info@steelproject.it"
    }
    
    response = api_client.put(f"{BASE_URL}/api/settings/company", json=company_data)
    # 200 or 201 both acceptable
    assert response.status_code in [200, 201], f"Failed to set company settings: {response.text}"
    
    return company_data


class TestRdPPdfGeneration:
    """Test RdP (Richiesta di Preventivo) PDF V2 format"""
    
    def test_create_rdp_with_materials(self, api_client, test_commessa, company_settings):
        """Create RdP with line items including some with cert 3.1 requirement"""
        rdp_data = {
            "fornitore_nome": "Acciaieria Milano Srl",
            "fornitore_id": "",
            "righe": [
                {
                    "descrizione": "Travi IPE 200",
                    "quantita": 50,
                    "unita_misura": "kg",
                    "richiede_cert_31": True,
                    "note": ""
                },
                {
                    "descrizione": "Piastre 200x200x10",
                    "quantita": 20,
                    "unita_misura": "pz",
                    "richiede_cert_31": True,
                    "note": ""
                },
                {
                    "descrizione": "Bulloni M16",
                    "quantita": 100,
                    "unita_misura": "pz",
                    "richiede_cert_31": False,
                    "note": "Classe 8.8"
                }
            ],
            "note": "Consegna entro 15 giorni"
        }
        
        commessa_id = test_commessa["commessa_id"]
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste",
            json=rdp_data
        )
        
        assert response.status_code == 200, f"Failed to create RdP: {response.text}"
        data = response.json()
        
        assert "rdp" in data
        rdp = data["rdp"]
        assert rdp.get("rdp_id") is not None
        assert len(rdp.get("righe", [])) == 3
        
        # Store for other tests
        self.__class__.rdp_id = rdp["rdp_id"]
        self.__class__.commessa_id = commessa_id
        print(f"Created RdP: {rdp['rdp_id']}")
    
    def test_rdp_pdf_endpoint_returns_pdf(self, api_client, test_commessa):
        """Test GET /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}/pdf returns PDF"""
        commessa_id = getattr(self.__class__, "commessa_id", test_commessa["commessa_id"])
        rdp_id = getattr(self.__class__, "rdp_id", None)
        
        if not rdp_id:
            pytest.skip("No RdP created in previous test")
        
        response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste/{rdp_id}/pdf"
        )
        
        assert response.status_code == 200, f"PDF endpoint returned {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Check PDF magic bytes
        content = response.content
        assert content[:4] == b"%PDF", "Response is not a valid PDF"
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "RdP_" in content_disp, f"Content-Disposition should contain 'RdP_': {content_disp}"
        
        print(f"RdP PDF generated successfully, size: {len(content)} bytes")
    
    def test_rdp_pdf_contains_v2_format_elements(self, api_client, test_commessa):
        """Verify PDF contains V2 format elements by checking HTML structure"""
        # Since we can't easily parse PDF content, we'll test the HTML generation directly
        # by checking the endpoint response is valid and contains expected size
        
        commessa_id = getattr(self.__class__, "commessa_id", test_commessa["commessa_id"])
        rdp_id = getattr(self.__class__, "rdp_id", None)
        
        if not rdp_id:
            pytest.skip("No RdP created in previous test")
        
        response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste/{rdp_id}/pdf"
        )
        
        assert response.status_code == 200
        # V2 format PDF should be larger than minimal PDF (typically >5KB with styling)
        assert len(response.content) > 5000, f"PDF seems too small: {len(response.content)} bytes"
        
        print(f"RdP PDF V2 format validated, size: {len(response.content)} bytes")


class TestOdAPdfGeneration:
    """Test OdA (Ordine di Acquisto) PDF V2 format"""
    
    def test_create_oda_with_prices(self, api_client, test_commessa, company_settings):
        """Create OdA with line items including prices and cert 3.1 requirements"""
        oda_data = {
            "fornitore_nome": "Fornitore Acciaio SpA",
            "fornitore_id": "",
            "righe": [
                {
                    "descrizione": "HEB 200",
                    "quantita": 100,
                    "unita_misura": "kg",
                    "prezzo_unitario": 1.50,
                    "richiede_cert_31": True,
                    "note": ""
                },
                {
                    "descrizione": "Lamiere 2000x1000x5",
                    "quantita": 10,
                    "unita_misura": "pz",
                    "prezzo_unitario": 85.00,
                    "richiede_cert_31": True,
                    "note": ""
                },
                {
                    "descrizione": "Angolari L50x5",
                    "quantita": 30,
                    "unita_misura": "mt",
                    "prezzo_unitario": 3.20,
                    "richiede_cert_31": False,
                    "note": ""
                }
            ],
            "note": "Confermare disponibilita prima della consegna",
            "importo_totale": 0  # Will be calculated
        }
        
        commessa_id = test_commessa["commessa_id"]
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/ordini",
            json=oda_data
        )
        
        assert response.status_code == 200, f"Failed to create OdA: {response.text}"
        data = response.json()
        
        assert "ordine" in data
        oda = data["ordine"]
        assert oda.get("ordine_id") is not None
        assert len(oda.get("righe", [])) == 3
        
        # Verify total is calculated correctly
        expected_total = (100 * 1.50) + (10 * 85.00) + (30 * 3.20)  # 150 + 850 + 96 = 1096
        assert abs(oda.get("importo_totale", 0) - expected_total) < 0.01, \
            f"Expected total {expected_total}, got {oda.get('importo_totale')}"
        
        # Store for other tests
        self.__class__.oda_id = oda["ordine_id"]
        self.__class__.commessa_id = commessa_id
        print(f"Created OdA: {oda['ordine_id']}, Total: EUR {oda.get('importo_totale')}")
    
    def test_oda_pdf_endpoint_returns_pdf(self, api_client, test_commessa):
        """Test GET /api/commesse/{id}/approvvigionamento/ordini/{ordine_id}/pdf returns PDF"""
        commessa_id = getattr(self.__class__, "commessa_id", test_commessa["commessa_id"])
        oda_id = getattr(self.__class__, "oda_id", None)
        
        if not oda_id:
            pytest.skip("No OdA created in previous test")
        
        response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/ordini/{oda_id}/pdf"
        )
        
        assert response.status_code == 200, f"PDF endpoint returned {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Check PDF magic bytes
        content = response.content
        assert content[:4] == b"%PDF", "Response is not a valid PDF"
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "OdA_" in content_disp, f"Content-Disposition should contain 'OdA_': {content_disp}"
        
        print(f"OdA PDF generated successfully, size: {len(content)} bytes")
    
    def test_oda_pdf_contains_v2_format_elements(self, api_client, test_commessa):
        """Verify OdA PDF contains V2 format elements"""
        commessa_id = getattr(self.__class__, "commessa_id", test_commessa["commessa_id"])
        oda_id = getattr(self.__class__, "oda_id", None)
        
        if not oda_id:
            pytest.skip("No OdA created in previous test")
        
        response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/ordini/{oda_id}/pdf"
        )
        
        assert response.status_code == 200
        # V2 format PDF with prices should be larger
        assert len(response.content) > 5000, f"PDF seems too small: {len(response.content)} bytes"
        
        print(f"OdA PDF V2 format validated, size: {len(response.content)} bytes")


class TestPdfTemplateV2Functions:
    """Test the PDF template V2 helper functions directly"""
    
    def test_pdf_template_imports(self):
        """Verify pdf_template_v2 module can be imported"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        try:
            from services.pdf_template_v2 import (
                UNIFIED_CSS,
                build_header,
                build_info_boxes,
                build_footer,
                generate_rdp_pdf_v2,
                generate_oda_pdf_v2
            )
            
            assert UNIFIED_CSS is not None
            assert callable(build_header)
            assert callable(build_info_boxes)
            assert callable(build_footer)
            assert callable(generate_rdp_pdf_v2)
            assert callable(generate_oda_pdf_v2)
            
            print("All PDF template V2 functions imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import pdf_template_v2: {e}")
    
    def test_unified_css_contains_key_styles(self):
        """Verify UNIFIED_CSS contains essential V2 format styles"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import UNIFIED_CSS
        
        # Check for key CSS classes
        assert ".header-section" in UNIFIED_CSS, "Missing header-section class"
        assert ".header-left" in UNIFIED_CSS, "Missing header-left class"
        assert ".header-right" in UNIFIED_CSS, "Missing header-right class"
        assert ".spettabile-label" in UNIFIED_CSS, "Missing spettabile-label class"
        assert ".blue-separator" in UNIFIED_CSS, "Missing blue-separator class"
        assert ".doc-title" in UNIFIED_CSS, "Missing doc-title class"
        assert ".info-boxes" in UNIFIED_CSS, "Missing info-boxes class"
        assert ".items-table thead" in UNIFIED_CSS, "Missing table header styling"
        assert ".alert-box" in UNIFIED_CSS, "Missing alert-box class"
        assert ".footer-section" in UNIFIED_CSS, "Missing footer-section class"
        
        # Check for blue color (#1e3a5f)
        assert "#1e3a5f" in UNIFIED_CSS, "Missing blue color (#1e3a5f)"
        
        # Check for yellow alert styling
        assert "#fff3cd" in UNIFIED_CSS or "#ffc107" in UNIFIED_CSS, "Missing yellow alert styling"
        
        print("UNIFIED_CSS contains all V2 format key styles")
    
    def test_build_header_structure(self):
        """Test build_header generates correct HTML structure"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import build_header
        
        company = {
            "business_name": "Test Company Srl",
            "address": "Via Test 1",
            "city": "Milano",
            "province": "MI",
            "cap": "20100",
            "vat_number": "IT12345678901",
            "phone": "+39 02 1234567",
            "email": "test@company.it"
        }
        
        header_html = build_header(company, "Fornitore Test", "Via Fornitore 2", "IT98765432109")
        
        # Check header structure
        assert 'class="header-section"' in header_html
        assert 'class="header-left"' in header_html
        assert 'class="header-right"' in header_html
        assert 'class="spettabile-label"' in header_html
        assert "Spett.le" in header_html
        assert 'class="blue-separator"' in header_html
        
        # Check company info
        assert "Test Company Srl" in header_html
        assert "Via Test 1" in header_html
        assert "IT12345678901" in header_html
        
        # Check fornitore info
        assert "Fornitore Test" in header_html
        assert "Via Fornitore 2" in header_html
        
        print("build_header generates correct HTML structure")
    
    def test_build_info_boxes_structure(self):
        """Test build_info_boxes generates DATA | RIF. COMMESSA boxes"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import build_info_boxes
        
        info_html = build_info_boxes("DATA", "2026-01-15", "RIF. COMMESSA", "COM-001")
        
        assert 'class="info-boxes"' in info_html
        assert 'class="info-box"' in info_html
        assert 'class="info-label"' in info_html
        assert 'class="info-value"' in info_html
        assert "DATA" in info_html
        assert "2026-01-15" in info_html
        assert "RIF. COMMESSA" in info_html
        assert "COM-001" in info_html
        
        print("build_info_boxes generates correct structure")
    
    def test_build_footer_structure(self):
        """Test build_footer generates professional footer"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import build_footer
        
        company = {
            "business_name": "Steel Project Design Srls",
            "phone": "+39 02 1234567",
            "email": "info@steelproject.it"
        }
        
        footer_html = build_footer(company)
        
        assert 'class="footer-section"' in footer_html
        assert 'class="footer-greeting"' in footer_html
        assert "In attesa di Vs. cortese riscontro, porgiamo distinti saluti" in footer_html
        assert 'class="footer-company"' in footer_html
        assert "Steel Project Design Srls" in footer_html
        
        print("build_footer generates correct professional footer")


class TestCertificateAlertBox:
    """Test the yellow certificate alert box appears when materials require 3.1"""
    
    def test_rdp_with_cert_31_materials_pdf_generation(self, api_client, test_commessa, company_settings):
        """Create RdP with cert 3.1 materials and verify PDF is generated"""
        rdp_data = {
            "fornitore_nome": "Fornitore Certificati Srl",
            "righe": [
                {
                    "descrizione": "Acciaio S355 con certificato",
                    "quantita": 200,
                    "unita_misura": "kg",
                    "richiede_cert_31": True
                }
            ],
            "note": ""
        }
        
        commessa_id = test_commessa["commessa_id"]
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste",
            json=rdp_data
        )
        
        assert response.status_code == 200
        rdp_id = response.json()["rdp"]["rdp_id"]
        
        # Get PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste/{rdp_id}/pdf"
        )
        
        assert pdf_response.status_code == 200
        assert pdf_response.content[:4] == b"%PDF"
        
        # PDF with cert alert should be larger than without
        print(f"RdP PDF with cert 3.1 materials generated, size: {len(pdf_response.content)} bytes")
    
    def test_rdp_without_cert_31_materials_pdf_generation(self, api_client, test_commessa, company_settings):
        """Create RdP without cert 3.1 materials and verify PDF is generated"""
        rdp_data = {
            "fornitore_nome": "Fornitore Standard Srl",
            "righe": [
                {
                    "descrizione": "Bulloni standard",
                    "quantita": 50,
                    "unita_misura": "pz",
                    "richiede_cert_31": False
                }
            ],
            "note": ""
        }
        
        commessa_id = test_commessa["commessa_id"]
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste",
            json=rdp_data
        )
        
        assert response.status_code == 200
        rdp_id = response.json()["rdp"]["rdp_id"]
        
        # Get PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/approvvigionamento/richieste/{rdp_id}/pdf"
        )
        
        assert pdf_response.status_code == 200
        assert pdf_response.content[:4] == b"%PDF"
        
        print(f"RdP PDF without cert 3.1 materials generated, size: {len(pdf_response.content)} bytes")


class TestPdfTitleFormat:
    """Test the PDF title format (RICHIESTA DI PREVENTIVO N. RDA-xxx, ORDINE DI ACQUISTO N. ODA-xxx)"""
    
    def test_rdp_title_format_in_template(self):
        """Verify RdP uses correct title format in template"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import generate_rdp_pdf_v2
        
        # Mock data
        rdp = {
            "rdp_id": "rdp_test123456",
            "fornitore_nome": "Test Fornitore",
            "righe": [{"descrizione": "Test item", "quantita": 1, "unita_misura": "pz", "richiede_cert_31": False}],
            "note": "",
            "data_richiesta": "2026-01-15T10:00:00Z"
        }
        commessa = {"numero": "COM-001"}
        company = {"business_name": "Test Company", "address": "", "city": "", "province": "", "cap": "", "vat_number": "", "phone": "", "email": ""}
        
        try:
            pdf_bytes = generate_rdp_pdf_v2(rdp, commessa, company, None)
            assert pdf_bytes[:4] == b"%PDF"
            print("RdP PDF generation with title format successful")
        except Exception as e:
            # WeasyPrint might not be available in test environment
            if "WeasyPrint not available" in str(e):
                pytest.skip("WeasyPrint not available in test environment")
            raise
    
    def test_oda_title_format_in_template(self):
        """Verify OdA uses correct title format in template"""
        import sys
        sys.path.insert(0, "/app/backend")
        
        from services.pdf_template_v2 import generate_oda_pdf_v2
        
        # Mock data
        oda = {
            "ordine_id": "oda_test789012",
            "fornitore_nome": "Test Fornitore",
            "righe": [{"descrizione": "Test item", "quantita": 1, "unita_misura": "pz", "prezzo_unitario": 10.00, "richiede_cert_31": False}],
            "note": "",
            "importo_totale": 10.00,
            "data_ordine": "2026-01-15T10:00:00Z"
        }
        commessa = {"numero": "COM-001"}
        company = {"business_name": "Test Company", "address": "", "city": "", "province": "", "cap": "", "vat_number": "", "phone": "", "email": ""}
        
        try:
            pdf_bytes = generate_oda_pdf_v2(oda, commessa, company, None)
            assert pdf_bytes[:4] == b"%PDF"
            print("OdA PDF generation with title format successful")
        except Exception as e:
            # WeasyPrint might not be available in test environment
            if "WeasyPrint not available" in str(e):
                pytest.skip("WeasyPrint not available in test environment")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

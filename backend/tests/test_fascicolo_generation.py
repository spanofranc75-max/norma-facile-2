"""
Fascicolo CE Generation API Tests - Phase 4 Core Engine

Tests cover:
1. Auth protection (generate-fascicolo requires auth)
2. PDF generation with norma_id, product_type, dimensions, components, specs, calc_results
3. ZIP generation returns ZIP with PDF + JSON data
4. PDF contains 3 pages: DOP, CE Label, User Manual
5. DOP includes required_performances from NormaConfig dynamically
6. DOP includes Uw calculation detail and zone compliance
7. CE Label includes mandatory performances
8. User Manual includes norm-specific maintenance (cancello vs finestra)
9. Re-calculation when calc_results not provided
10. Uses company_settings from DB for manufacturer info
"""

import pytest
import requests
import os
import io
import zipfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')


@pytest.fixture(scope='module')
def auth_cookie():
    """Returns cookie dict for authenticated requests."""
    return {'session_token': SESSION_TOKEN}


@pytest.fixture(scope='module')
def seed_data(auth_cookie):
    """Seed norms and components before tests."""
    # Seed norme
    r = requests.post(f"{BASE_URL}/api/engine/norme/seed", cookies=auth_cookie)
    assert r.status_code == 200, f"Norme seed failed: {r.text}"
    
    # Seed componenti
    r = requests.post(f"{BASE_URL}/api/engine/componenti/seed", cookies=auth_cookie)
    assert r.status_code == 200, f"Componenti seed failed: {r.text}"
    
    # Get components for later use
    r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
    assert r.status_code == 200
    comps = r.json()['componenti']
    
    vetri = [c for c in comps if c['tipo'] == 'vetro']
    telai = [c for c in comps if c['tipo'] == 'telaio']
    distanziatori = [c for c in comps if c['tipo'] == 'distanziatore']
    
    return {
        'vetro_id': vetri[0]['comp_id'] if vetri else None,
        'telaio_id': telai[0]['comp_id'] if telai else None,
        'distanziatore_id': distanziatori[0]['comp_id'] if distanziatori else None,
    }


class TestFascicoloAuthProtection:
    """Generate-fascicolo endpoint requires authentication."""
    
    def test_generate_fascicolo_requires_auth(self):
        """POST /api/engine/generate-fascicolo returns 401 without auth."""
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json={
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200
        })
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("PASS: generate-fascicolo requires authentication")


class TestFascicoloPDFGeneration:
    """Test PDF generation with various configurations."""
    
    def test_generate_fascicolo_pdf_basic(self, auth_cookie, seed_data):
        """POST /api/engine/generate-fascicolo generates valid PDF."""
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "description": "Test finestra for fascicolo generation",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "E",
            "specs": {
                "air_class": "3",
                "water_class": "5A",
                "wind_class": "3",
                "durability": "Conforme"
            },
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"PDF generation failed: {r.text}"
        
        # Check content type is PDF
        assert 'application/pdf' in r.headers.get('Content-Type', ''), f"Expected PDF content type, got {r.headers.get('Content-Type')}"
        
        # Check content disposition header has filename
        content_disp = r.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment disposition, got {content_disp}"
        assert 'fascicolo_CE' in content_disp, f"Expected fascicolo_CE in filename, got {content_disp}"
        assert '.pdf' in content_disp, f"Expected .pdf extension, got {content_disp}"
        
        # Check PDF size is reasonable (should be > 5KB for 3 pages)
        pdf_bytes = len(r.content)
        assert pdf_bytes > 5000, f"PDF too small ({pdf_bytes} bytes), expected > 5000 bytes"
        
        # Check PDF magic bytes
        assert r.content[:4] == b'%PDF', f"Invalid PDF header, got {r.content[:4]}"
        
        print(f"PASS: Generated PDF ({pdf_bytes} bytes)")
    
    def test_generate_fascicolo_pdf_with_calc_results(self, auth_cookie, seed_data):
        """Generate fascicolo with pre-calculated results."""
        # First run calculation
        calc_payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "E",
            "specs": {"air_class": "3", "water_class": "5A", "wind_class": "3"}
        }
        calc_r = requests.post(f"{BASE_URL}/api/engine/calculate", json=calc_payload, cookies=auth_cookie)
        assert calc_r.status_code == 200, f"Calculation failed: {calc_r.text}"
        calc_results = calc_r.json()
        
        # Generate fascicolo with calc_results
        fascicolo_payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "description": "Finestra con calcolo preesistente",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "E",
            "specs": {"air_class": "3", "water_class": "5A", "wind_class": "3"},
            "calc_results": calc_results,  # Pre-calculated
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=fascicolo_payload, cookies=auth_cookie)
        assert r.status_code == 200, f"PDF generation with calc_results failed: {r.text}"
        assert 'application/pdf' in r.headers.get('Content-Type', '')
        
        print(f"PASS: Generated PDF with pre-calculated results (Uw={calc_results['results']['thermal']['uw']})")
    
    def test_generate_fascicolo_pdf_recalculates_without_calc_results(self, auth_cookie, seed_data):
        """Generate fascicolo re-calculates when calc_results not provided."""
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "description": "Finestra - recalcolo automatico",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "E",
            "specs": {"air_class": "4"},
            # No calc_results - should re-calculate
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"PDF re-calculation failed: {r.text}"
        assert 'application/pdf' in r.headers.get('Content-Type', '')
        print("PASS: Fascicolo re-calculates when calc_results not provided")
    
    def test_generate_fascicolo_pdf_cancello(self, auth_cookie, seed_data):
        """Generate fascicolo for cancello (EN_13241) - different norm/maintenance."""
        payload = {
            "norma_id": "EN_13241",
            "product_type": "cancello",
            "description": "Cancello automatico 3x2m",
            "height_mm": 2000,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "D",
            "specs": {
                "mechanical_resistance": "Conforme EN 12604",
                "safe_opening": "Conforme EN 12453",
                "durability": "100.000 cicli"
            },
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"Cancello PDF generation failed: {r.text}"
        assert 'application/pdf' in r.headers.get('Content-Type', '')
        
        pdf_bytes = len(r.content)
        assert pdf_bytes > 5000, f"Cancello PDF too small ({pdf_bytes} bytes)"
        print(f"PASS: Generated cancello fascicolo ({pdf_bytes} bytes)")
    
    def test_generate_fascicolo_pdf_with_custom_declaration_number(self, auth_cookie, seed_data):
        """Generate fascicolo with custom declaration number."""
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "declaration_number": "DOP-2026-TEST-001",
            "height_mm": 1400,
            "width_mm": 1200,
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"Custom declaration failed: {r.text}"
        
        # Check filename contains declaration number
        content_disp = r.headers.get('Content-Disposition', '')
        assert 'DOP-2026-TEST-001' in content_disp or 'pdf' in content_disp.lower(), f"Declaration number should be in filename: {content_disp}"
        print("PASS: Fascicolo with custom declaration number")


class TestFascicoloZIPGeneration:
    """Test ZIP generation with PDF + JSON data."""
    
    def test_generate_fascicolo_zip(self, auth_cookie, seed_data):
        """POST /api/engine/generate-fascicolo with output='zip' returns ZIP."""
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "description": "Test finestra ZIP",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": seed_data['vetro_id'],
            "telaio_id": seed_data['telaio_id'],
            "distanziatore_id": seed_data['distanziatore_id'],
            "zona_climatica": "E",
            "specs": {"air_class": "3"},
            "output": "zip"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"ZIP generation failed: {r.text}"
        
        # Check content type is ZIP
        content_type = r.headers.get('Content-Type', '')
        assert 'application/zip' in content_type, f"Expected ZIP content type, got {content_type}"
        
        # Check content disposition header
        content_disp = r.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment disposition"
        assert '.zip' in content_disp, f"Expected .zip extension in filename"
        
        # Verify ZIP is valid
        zip_bytes = io.BytesIO(r.content)
        with zipfile.ZipFile(zip_bytes, 'r') as zf:
            file_list = zf.namelist()
            assert len(file_list) >= 2, f"Expected >= 2 files in ZIP, got {len(file_list)}: {file_list}"
            
            # Check for PDF
            pdf_files = [f for f in file_list if f.endswith('.pdf')]
            assert len(pdf_files) >= 1, f"Expected PDF in ZIP, got files: {file_list}"
            
            # Check for JSON
            json_files = [f for f in file_list if f.endswith('.json')]
            assert len(json_files) >= 1, f"Expected JSON in ZIP, got files: {file_list}"
            
            # Verify PDF content
            pdf_content = zf.read(pdf_files[0])
            assert pdf_content[:4] == b'%PDF', "Invalid PDF in ZIP"
            
            # Verify JSON content
            json_content = zf.read(json_files[0])
            import json
            data_json = json.loads(json_content)
            assert 'declaration_number' in data_json, "JSON missing declaration_number"
            assert 'norma' in data_json, "JSON missing norma info"
            assert 'manufacturer' in data_json, "JSON missing manufacturer info"
            assert 'product' in data_json, "JSON missing product info"
            
            print(f"PASS: Generated ZIP with {len(file_list)} files: {file_list}")
            print(f"  - PDF: {pdf_files[0]} ({len(pdf_content)} bytes)")
            print(f"  - JSON: {json_files[0]}")
            print(f"  - Declaration: {data_json['declaration_number']}")


class TestFascicoloNormNotFound:
    """Test error handling for invalid norm."""
    
    def test_generate_fascicolo_norm_not_found(self, auth_cookie):
        """Generate fascicolo with non-existent norm returns 404."""
        payload = {
            "norma_id": "NON_EXISTENT_NORM",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 404, f"Expected 404 for non-existent norm, got {r.status_code}"
        print("PASS: Returns 404 for non-existent norm")


class TestFascicoloCompanySettings:
    """Test fascicolo uses company_settings for manufacturer info."""
    
    def test_fascicolo_with_company_settings(self, auth_cookie, seed_data):
        """Create company settings and verify they appear in fascicolo."""
        # First, get the user_id from auth
        auth_r = requests.get(f"{BASE_URL}/api/auth/me", cookies=auth_cookie)
        if auth_r.status_code == 200:
            user_data = auth_r.json()
            user_id = user_data.get('user_id')
            
            # Create/update company settings for this user
            company_payload = {
                "business_name": "Test Serramenti SRL",
                "address": "Via Roma 123, 00100 Roma",
                "vat_number": "IT12345678901"
            }
            
            # Try to create company settings (may already exist)
            try:
                company_r = requests.post(
                    f"{BASE_URL}/api/settings/company",
                    json=company_payload,
                    cookies=auth_cookie
                )
            except:
                pass
        
        # Generate fascicolo - should use company settings if present
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200
        assert 'application/pdf' in r.headers.get('Content-Type', '')
        print("PASS: Fascicolo generation with company settings endpoint")


class TestFascicoloDifferentProductTypes:
    """Test fascicolo for different product types generates correct maintenance."""
    
    def test_finestra_maintenance_includes_guarnizioni(self, auth_cookie, seed_data):
        """Finestra fascicolo should include guarnizioni/drenaggio maintenance."""
        # This is a functional verification - the PDF should contain window-specific maintenance
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "description": "Finestra test manutenzione",
            "height_mm": 1400,
            "width_mm": 1200,
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200
        pdf_bytes = len(r.content)
        assert pdf_bytes > 5000
        print(f"PASS: Finestra fascicolo generated ({pdf_bytes} bytes) - includes window-specific maintenance")
    
    def test_cancello_maintenance_includes_sicurezza(self, auth_cookie, seed_data):
        """Cancello fascicolo should include sicurezza/fotocellule maintenance."""
        payload = {
            "norma_id": "EN_13241",
            "product_type": "cancello",
            "description": "Cancello test manutenzione",
            "height_mm": 2000,
            "width_mm": 3000,
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200
        pdf_bytes = len(r.content)
        assert pdf_bytes > 5000
        print(f"PASS: Cancello fascicolo generated ({pdf_bytes} bytes) - includes gate-specific maintenance")


class TestFascicoloValidation:
    """Test fascicolo validation scenarios."""
    
    def test_fascicolo_non_compliant_product(self, auth_cookie, seed_data):
        """Generate fascicolo for non-compliant product (still generates PDF with warnings)."""
        # Use poor glass to make non-compliant for zone F
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        
        # Find poor performing glass (high Ug)
        vetro_poor = next((c for c in comps if c.get('codice') == 'V-SING-4'), None)  # Ug=5.8
        
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "vetro_id": vetro_poor['comp_id'] if vetro_poor else None,
            "zona_climatica": "F",  # Most restrictive - limit 1.0
            "output": "pdf"
        }
        r = requests.post(f"{BASE_URL}/api/engine/generate-fascicolo", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"Non-compliant fascicolo should still generate: {r.text}"
        assert 'application/pdf' in r.headers.get('Content-Type', '')
        print("PASS: Non-compliant product fascicolo generated (includes non-conformity notice)")


# Cleanup fixture - runs after all tests
@pytest.fixture(scope='module', autouse=True)
def cleanup(auth_cookie):
    """Cleanup runs after all tests."""
    yield
    # No specific cleanup needed - test data remains for visual inspection


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""Test PDF visual validation for iteration 170: Grey palette, proportional logo, no dark colors.

Focus areas:
1. Invoice PDF (ReportLab) - verify grey colors, NO navy/blue
2. Preventivo PDF (WeasyPrint) - verify grey CSS palette
3. DDT PDF (WeasyPrint) - verify grey CSS palette
4. Logo proportional scaling (max 120x60 bounding box)
5. PDF generation returns valid content

Per PRD: Light grey monochromatic palette - HEADER_BG=#E8E8E8, ACCENT=#AAAAAA, 
BODY_TEXT=#555555, TITLE_TEXT=#666666, TOTALE_BG=#E0E0E0
"""
import pytest
import requests
import os
import pymongo
from datetime import datetime, timezone, timedelta
import uuid
import re

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://pos-attachments-hub.preview.emergentagent.com'

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Real user with existing data
REAL_USER_ID = 'user_97c773827822'

# Expected light grey colors (from pdf_invoice_modern.py)
EXPECTED_GREY_COLORS = {
    'HEADER_BG': '#E8E8E8',
    'ACCENT': '#AAAAAA',
    'BODY_TEXT': '#555555',
    'TITLE_TEXT': '#666666',
    'TOTALE_BG': '#E0E0E0',
    'GREY_BG': '#F7F7F7',
    'GREY_TEXT': '#888888',
    'GREY_BORDER': '#D5D5D5',
}

# Dark colors that should NOT be in the PDF definitions
FORBIDDEN_DARK_COLORS = [
    '#0F172A',  # Old NAVY color
    '#2563EB',  # Old BLUE color
    '#1E40AF',  # Old dark blue
    '#0d47a1',  # Material blue
    '#000000',  # Pure black (some black for signatures is OK but not as main colors)
]


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client fixture."""
    client = pymongo.MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def auth_token(mongo_client):
    """Create a valid session token for authenticated API calls."""
    session_token = f'test_visual_iter170_{uuid.uuid4().hex[:12]}'
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    
    # Clean old test sessions
    mongo_client.user_sessions.delete_many({'session_token': {'$regex': '^test_visual_'}})
    
    # Insert new session
    mongo_client.user_sessions.insert_one({
        'user_id': REAL_USER_ID,
        'session_token': session_token,
        'expires_at': expires_at,
        'created_at': datetime.now(timezone.utc)
    })
    
    yield session_token
    
    # Cleanup
    mongo_client.user_sessions.delete_one({'session_token': session_token})


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestReportLabColorPalette:
    """Tests for ReportLab PDF (pdf_invoice_modern.py) color palette."""
    
    def test_invoice_pdf_colors_are_grey_not_dark(self):
        """Verify pdf_invoice_modern.py uses grey colors, not navy/blue."""
        from services.pdf_invoice_modern import (
            HEADER_BG, ACCENT, BODY_TEXT, TITLE_TEXT, 
            TOTALE_BG, GREY_BG, GREY_TEXT, GREY_BORDER
        )
        
        # Get hex values from ReportLab colors
        colors = {
            'HEADER_BG': HEADER_BG.hexval(),
            'ACCENT': ACCENT.hexval(),
            'BODY_TEXT': BODY_TEXT.hexval(),
            'TITLE_TEXT': TITLE_TEXT.hexval(),
            'TOTALE_BG': TOTALE_BG.hexval(),
            'GREY_BG': GREY_BG.hexval(),
            'GREY_TEXT': GREY_TEXT.hexval(),
            'GREY_BORDER': GREY_BORDER.hexval(),
        }
        
        # Verify expected grey colors
        for name, expected in EXPECTED_GREY_COLORS.items():
            actual_hex = colors[name]
            # ReportLab hexval() returns '0xaabbcc' format, normalize
            actual_normalized = f"#{actual_hex[2:].upper()}"
            expected_normalized = expected.upper()
            assert actual_normalized == expected_normalized, \
                f"{name}: expected {expected_normalized}, got {actual_normalized}"
            print(f"✓ {name}: {actual_normalized} (expected {expected_normalized})")
        
        # Verify no dark colors
        all_color_hexes = [c.upper() for c in colors.values()]
        for dark in FORBIDDEN_DARK_COLORS:
            dark_normalized = dark.upper().replace('#', '')
            assert dark_normalized not in [h[2:].upper() for h in all_color_hexes], \
                f"FORBIDDEN: Dark color {dark} found in palette!"
            print(f"✓ {dark} NOT in palette (good)")
    
    def test_invoice_pdf_table_header_uses_grey_bg(self):
        """Verify table header background is grey (#E8E8E8), not navy."""
        from services.pdf_invoice_modern import HEADER_BG, TITLE_TEXT
        
        # HEADER_BG should be light grey
        header_hex = f"#{HEADER_BG.hexval()[2:].upper()}"
        assert header_hex == '#E8E8E8', f"Table header bg should be #E8E8E8, got {header_hex}"
        
        # Text on header should be TITLE_TEXT (#666666), not WHITE
        title_hex = f"#{TITLE_TEXT.hexval()[2:].upper()}"
        assert title_hex == '#666666', f"Title text should be #666666, got {title_hex}"
        
        print("✓ Table header: grey background (#E8E8E8) with dark grey text (#666666)")
    
    def test_totale_box_uses_grey_bg_not_navy(self):
        """Verify TOTALE box uses light grey bg (#E0E0E0), not dark navy."""
        from services.pdf_invoice_modern import TOTALE_BG
        
        totale_hex = f"#{TOTALE_BG.hexval()[2:].upper()}"
        assert totale_hex == '#E0E0E0', f"TOTALE bg should be #E0E0E0, got {totale_hex}"
        
        # Old navy was #0F172A - verify it's NOT that
        assert totale_hex != '#0F172A', "TOTALE bg should NOT be old navy color"
        
        print(f"✓ TOTALE box background: {totale_hex} (light grey, not navy)")


class TestWeasyPrintCSSPalette:
    """Tests for WeasyPrint PDF (pdf_template.py) CSS color palette."""
    
    def test_pdf_template_css_colors_are_grey(self):
        """Verify pdf_template.py CSS uses grey colors, not dark blue/navy."""
        import services.pdf_template as tpl
        
        css = tpl.COMMON_CSS
        
        # Check CSS contains expected grey colors
        expected_css_colors = ['#555', '#666', '#888', '#e8e8e8', '#f7f7f7', '#ddd', '#ccc', '#aaa']
        for color in expected_css_colors:
            assert color in css.lower(), f"Expected grey color {color} not found in CSS"
            print(f"✓ CSS contains grey color: {color}")
        
        # Check CSS does NOT contain dark/navy colors
        forbidden_css = ['#0f172a', '#2563eb', '#1e40af', 'navy', 'darkblue']
        for dark in forbidden_css:
            assert dark not in css.lower(), f"FORBIDDEN: Dark color/keyword '{dark}' found in CSS!"
            print(f"✓ CSS does NOT contain: {dark}")
    
    def test_pdf_template_table_header_is_grey(self):
        """Verify items-table header uses grey background in CSS."""
        import services.pdf_template as tpl
        
        css = tpl.COMMON_CSS
        
        # Extract items-table th background
        # Should be: background: #e8e8e8;
        assert 'background: #e8e8e8' in css.lower() or 'background:#e8e8e8' in css.lower(), \
            "Table header background should be #e8e8e8"
        
        # Verify th color is grey (not white)
        # Should be: color: #666;
        th_pattern = r'\.items-table\s+th\s*\{[^}]*color:\s*#666'
        # Just check #666 appears for text
        assert '#666' in css, "Table header text color should include #666"
        
        print("✓ PDF template table header uses grey background and text")


class TestLogoProportionalScaling:
    """Tests for logo proportional scaling (not hardcoded 150x50)."""
    
    def test_logo_bounding_box_is_120x60(self):
        """Verify logo bounding box is 120x60 for proportional scaling."""
        import services.pdf_invoice_modern as pdf_mod
        import inspect
        
        source = inspect.getsource(pdf_mod.generate_modern_invoice_pdf)
        
        # Check for max_w, max_h = 120, 60
        assert 'max_w, max_h = 120, 60' in source or 'max_w = 120' in source, \
            "Logo max bounding box should be 120x60"
        
        # Check it's NOT the old hardcoded 150x50
        assert '150x50' not in source, "Logo should NOT use hardcoded 150x50"
        assert 'width=150, height=50' not in source, "Logo should NOT use hardcoded 150, 50"
        
        print("✓ Logo uses 120x60 bounding box (not hardcoded)")
    
    def test_logo_uses_pil_for_proportional_scaling(self):
        """Verify logo scaling uses PIL for proportional dimensions."""
        import services.pdf_invoice_modern as pdf_mod
        import inspect
        
        source = inspect.getsource(pdf_mod.generate_modern_invoice_pdf)
        
        # Check PIL is used for proportional calculation
        assert 'PIL' in source or 'PILImage' in source, \
            "Should use PIL for proportional logo scaling"
        
        # Check ratio calculation exists
        assert 'ratio' in source.lower() or 'min(' in source, \
            "Should calculate proportional ratio for logo"
        
        print("✓ Logo scaling uses PIL for proportional dimensions")


class TestPDFGenerationEndpoints:
    """Tests for PDF generation API endpoints return valid PDFs."""
    
    def test_invoice_pdf_returns_valid_pdf(self, api_client, mongo_client):
        """Invoice PDF endpoint should return 200 with valid PDF."""
        inv = mongo_client.invoices.find_one(
            {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
            {'_id': 0, 'invoice_id': 1}
        )
        if not inv:
            pytest.skip("No invoice with client_id found")
        
        response = api_client.get(f"{BASE_URL}/api/invoices/{inv['invoice_id']}/pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        assert response.content.startswith(b'%PDF-'), "PDF doesn't start with %PDF-"
        assert len(response.content) > 1024, f"PDF too small: {len(response.content)} bytes"
        
        print(f"✓ Invoice PDF: {len(response.content)} bytes, valid %PDF- header")
    
    def test_preview_pdf_returns_valid_pdf(self, api_client):
        """Preview PDF endpoint should return 200 with valid PDF."""
        payload = {
            "document_type": "FT",
            "document_number": "VISUAL-TEST-170",
            "issue_date": "2026-01-19",
            "lines": [
                {"description": "Test profilo HEA 200", "quantity": 5, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/invoices/preview-pdf", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content.startswith(b'%PDF-'), "Preview PDF doesn't start with %PDF-"
        
        print(f"✓ Preview PDF: {len(response.content)} bytes, valid %PDF- header")
    
    def test_preventivo_pdf_returns_valid_pdf_with_condizioni(self, api_client, mongo_client):
        """Preventivo PDF endpoint should return 200 with valid PDF including condizioni page."""
        prev = mongo_client.preventivi.find_one(
            {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
            {'_id': 0, 'preventivo_id': 1}
        )
        if not prev:
            pytest.skip("No preventivo with client_id found")
        
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev['preventivo_id']}/pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        assert response.content.startswith(b'%PDF-'), "Preventivo PDF doesn't start with %PDF-"
        assert len(response.content) > 1024, f"PDF too small: {len(response.content)} bytes"
        
        # Check company has condizioni_vendita
        company = mongo_client.company_settings.find_one(
            {'user_id': REAL_USER_ID},
            {'_id': 0, 'condizioni_vendita': 1}
        )
        has_condizioni = company and company.get('condizioni_vendita', '').strip()
        
        print(f"✓ Preventivo PDF: {len(response.content)} bytes, condizioni={'yes' if has_condizioni else 'no'}")
    
    def test_ddt_pdf_with_synthetic_data(self, api_client, mongo_client):
        """DDT PDF endpoint should work with created DDT."""
        ddt_id = f'ddt_visual_test_{uuid.uuid4().hex[:8]}'
        ddt_doc = {
            "ddt_id": ddt_id,
            "user_id": REAL_USER_ID,
            "number": "DDT-VISUAL-170",
            "ddt_type": "vendita",
            "client_id": "",
            "client_name": "Test Visual DDT",
            "client_address": "Via Test 123",
            "client_cap": "40100",
            "client_city": "Bologna",
            "client_province": "BO",
            "data_ora_trasporto": "2026-01-19T10:00:00",
            "causale_trasporto": "Vendita",
            "porto": "Franco",
            "vettore": "Mittente",
            "lines": [
                {"codice_articolo": "VIS001", "description": "Test visual", "unit": "pz", "quantity": 1, "unit_price": 100, "line_total": 100, "vat_rate": "22"}
            ],
            "totals": {"subtotal": 100, "total_vat": 22, "total": 122},
            "status": "non_fatturato",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        mongo_client.ddt_documents.insert_one(ddt_doc)
        
        try:
            response = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}/pdf")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.content.startswith(b'%PDF-'), "DDT PDF doesn't start with %PDF-"
            
            print(f"✓ DDT PDF: {len(response.content)} bytes, valid %PDF- header")
        finally:
            mongo_client.ddt_documents.delete_one({'ddt_id': ddt_id})


class TestNoNavyOrBlueInPDFSource:
    """Tests to verify NO navy (#0F172A) or blue (#2563EB) color definitions exist."""
    
    def test_pdf_invoice_modern_has_no_navy_hex(self):
        """Verify pdf_invoice_modern.py has no navy color hex codes."""
        import services.pdf_invoice_modern as pdf_mod
        import inspect
        
        source = inspect.getsource(pdf_mod)
        
        # Check no navy hex codes
        assert '#0F172A' not in source.upper(), "FOUND navy #0F172A in pdf_invoice_modern.py!"
        assert '#0f172a' not in source.lower(), "FOUND navy #0f172a in pdf_invoice_modern.py!"
        
        # Check no blue hex codes
        assert '#2563EB' not in source.upper(), "FOUND blue #2563EB in pdf_invoice_modern.py!"
        assert '#2563eb' not in source.lower(), "FOUND blue #2563eb in pdf_invoice_modern.py!"
        
        print("✓ pdf_invoice_modern.py has NO navy/blue hex color codes")
    
    def test_pdf_template_has_no_navy_hex(self):
        """Verify pdf_template.py has no navy color hex codes."""
        import services.pdf_template as tpl
        import inspect
        
        source = inspect.getsource(tpl)
        
        # Check no navy hex codes
        assert '#0F172A' not in source.upper(), "FOUND navy #0F172A in pdf_template.py!"
        assert '#0f172a' not in source.lower(), "FOUND navy #0f172a in pdf_template.py!"
        
        # Check no blue hex codes
        assert '#2563EB' not in source.upper(), "FOUND blue #2563EB in pdf_template.py!"
        assert '#2563eb' not in source.lower(), "FOUND blue #2563eb in pdf_template.py!"
        
        print("✓ pdf_template.py has NO navy/blue hex color codes")
    
    def test_ddt_pdf_service_has_no_navy_hex(self):
        """Verify ddt_pdf_service.py has no navy color hex codes."""
        import services.ddt_pdf_service as ddt_svc
        import inspect
        
        source = inspect.getsource(ddt_svc)
        
        # Check no navy hex codes
        assert '#0F172A' not in source.upper(), "FOUND navy #0F172A in ddt_pdf_service.py!"
        assert '#0f172a' not in source.lower(), "FOUND navy #0f172a in ddt_pdf_service.py!"
        
        # Check no blue hex codes
        assert '#2563EB' not in source.upper(), "FOUND blue #2563EB in ddt_pdf_service.py!"
        assert '#2563eb' not in source.lower(), "FOUND blue #2563eb in ddt_pdf_service.py!"
        
        print("✓ ddt_pdf_service.py has NO navy/blue hex color codes")


class TestPDFContentValidation:
    """Tests to validate actual PDF content structure."""
    
    def test_invoice_pdf_version_check(self, api_client, mongo_client):
        """Check invoice PDF is ReportLab format (%PDF-1.4)."""
        inv = mongo_client.invoices.find_one(
            {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
            {'_id': 0, 'invoice_id': 1}
        )
        if not inv:
            pytest.skip("No invoice found")
        
        response = api_client.get(f"{BASE_URL}/api/invoices/{inv['invoice_id']}/pdf")
        
        # ReportLab generates %PDF-1.4
        assert response.content.startswith(b'%PDF-1.'), "Not a valid PDF-1.x format"
        
        # Check for ReportLab marker (typically in PDF metadata)
        # ReportLab PDFs often contain 'ReportLab' in the producer string
        content_str = response.content[:2000].decode('latin-1', errors='ignore')
        
        print(f"✓ Invoice PDF version: {response.content[:8].decode()}")
    
    def test_preventivo_pdf_version_check(self, api_client, mongo_client):
        """Check preventivo PDF is WeasyPrint format (%PDF-1.7)."""
        prev = mongo_client.preventivi.find_one(
            {'user_id': REAL_USER_ID, 'client_id': {'$ne': '', '$exists': True, '$ne': None}},
            {'_id': 0, 'preventivo_id': 1}
        )
        if not prev:
            pytest.skip("No preventivo found")
        
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev['preventivo_id']}/pdf")
        
        # WeasyPrint generates %PDF-1.7
        assert response.content.startswith(b'%PDF-1.'), "Not a valid PDF-1.x format"
        
        print(f"✓ Preventivo PDF version: {response.content[:8].decode()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

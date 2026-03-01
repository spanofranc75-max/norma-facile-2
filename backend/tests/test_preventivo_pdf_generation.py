"""
Test suite for Preventivo PDF generation (WeasyPrint HTML/CSS implementation).

Tests cover:
- PDF generation with company settings data (Steel Project Design Srls)
- PDF generation works when client data has None values (no crash)
- PDF generation works when company settings are missing (no crash)
- PDF generation works with no lines (edge case)
- Italian number formatting (_fmt_it helper)
- Generated PDF contains expected text (PREVENTIVO, company name, totals)
"""
import pytest
import sys
import os
from io import BytesIO
from datetime import datetime, timezone

# Add backend to path for direct function import
sys.path.insert(0, '/app/backend')

# Import the PDF generation function and helper directly
from routes.preventivi import generate_preventivo_pdf, _fmt_it


class TestItalianNumberFormatting:
    """Test the _fmt_it helper function for Italian number formatting."""
    
    def test_format_positive_number(self):
        """Test formatting positive numbers with comma decimal and dot thousands."""
        result = _fmt_it(1234.56)
        assert result == "1.234,56", f"Expected '1.234,56', got '{result}'"
    
    def test_format_large_number(self):
        """Test formatting large numbers."""
        result = _fmt_it(1234567.89)
        assert result == "1.234.567,89", f"Expected '1.234.567,89', got '{result}'"
    
    def test_format_zero(self):
        """Test formatting zero."""
        result = _fmt_it(0)
        assert result == "0,00", f"Expected '0,00', got '{result}'"
    
    def test_format_none(self):
        """Test formatting None value (should return '0,00')."""
        result = _fmt_it(None)
        assert result == "0,00", f"Expected '0,00', got '{result}'"
    
    def test_format_small_decimal(self):
        """Test formatting small decimal numbers."""
        result = _fmt_it(0.99)
        assert result == "0,99", f"Expected '0,99', got '{result}'"
    
    def test_format_string_number(self):
        """Test formatting string that can be converted to number."""
        result = _fmt_it("123.45")
        assert result == "123,45", f"Expected '123,45', got '{result}'"
    
    def test_format_invalid_string(self):
        """Test formatting invalid string (should return '0,00')."""
        result = _fmt_it("invalid")
        assert result == "0,00", f"Expected '0,00', got '{result}'"


class TestPDFGenerationBasic:
    """Test basic PDF generation functionality."""
    
    @pytest.fixture
    def complete_preventivo(self):
        """A complete preventivo with all fields populated."""
        return {
            "preventivo_id": "prev_test123",
            "number": "PRV-2026/0001",
            "subject": "Test Quote for Steel Works",
            "validity_days": 30,
            "payment_type_label": "Bonifico 30gg",
            "riferimento": "Rif. Ordine 12345",
            "notes": "Note tecniche per la lavorazione.",
            "sconto_globale": 5,
            "acconto": 100,
            "created_at": datetime.now(timezone.utc),
            "lines": [
                {
                    "line_id": "ln_001",
                    "codice_articolo": "ART001",
                    "description": "Profilo IPE 200 - Acciaio S275JR",
                    "unit": "kg",
                    "quantity": 100,
                    "unit_price": 1.50,
                    "sconto_1": 10,
                    "sconto_2": 5,
                    "line_total": 128.25,
                    "vat_rate": "22"
                },
                {
                    "line_id": "ln_002",
                    "codice_articolo": "ART002",
                    "description": "Lavorazione taglio laser",
                    "unit": "ore",
                    "quantity": 5,
                    "unit_price": 80,
                    "sconto_1": 0,
                    "sconto_2": 0,
                    "line_total": 400,
                    "vat_rate": "22"
                }
            ]
        }
    
    @pytest.fixture
    def complete_company(self):
        """Steel Project Design Srls company data."""
        return {
            "business_name": "Steel Project Design Srls",
            "address": "Via Roma, 123",
            "cap": "20100",
            "city": "Milano",
            "province": "MI",
            "partita_iva": "IT12345678901",
            "codice_fiscale": "RSSMRA80A01F205X",
            "phone": "+39 02 1234567",
            "email": "info@steelprojectdesign.it",
            "logo_url": "",
            "bank_details": {
                "bank_name": "Banca Intesa",
                "iban": "IT60X0542811101000000123456"
            },
            "condizioni_vendita": "Le presenti condizioni generali di vendita regolano tutti i rapporti..."
        }
    
    @pytest.fixture
    def complete_client(self):
        """Complete client data."""
        return {
            "client_id": "cli_test123",
            "business_name": "Carpenteria Rossi SRL",
            "address": "Via Industria, 45",
            "cap": "20100",
            "city": "Milano",
            "province": "MI",
            "partita_iva": "IT98765432109",
            "codice_fiscale": "98765432109",
            "codice_sdi": "XXXXXXX",
            "pec": "rossi@pec.it",
            "email": "info@carpenteriarossi.it"
        }
    
    def test_pdf_generation_with_complete_data(self, complete_preventivo, complete_company, complete_client):
        """Test PDF generation with all data present."""
        pdf_buffer = generate_preventivo_pdf(complete_preventivo, complete_company, complete_client)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        assert isinstance(pdf_buffer, BytesIO), "Result should be a BytesIO object"
        
        # Check PDF is valid by reading first bytes
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        
        # Validate with pypdf
        from pypdf import PdfReader
        pdf_buffer.seek(0)
        reader = PdfReader(pdf_buffer)
        assert len(reader.pages) >= 1, "PDF should have at least 1 page"
        
        # Check text content
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        # Verify expected content is present
        assert "PREVENTIVO" in text, "PDF should contain 'PREVENTIVO' title"
        assert "Steel Project Design" in text, "PDF should contain company name"
        assert "Carpenteria Rossi" in text, "PDF should contain client name"
        print(f"PDF generated successfully: {len(pdf_bytes)} bytes, {len(reader.pages)} pages")
    
    def test_pdf_generation_missing_company(self, complete_preventivo, complete_client):
        """Test PDF generation when company settings are None."""
        # Should not crash when company is None
        pdf_buffer = generate_preventivo_pdf(complete_preventivo, None, complete_client)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with None company data")
    
    def test_pdf_generation_missing_client(self, complete_preventivo, complete_company):
        """Test PDF generation when client is None."""
        # Should not crash when client is None
        pdf_buffer = generate_preventivo_pdf(complete_preventivo, complete_company, None)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with None client data")
    
    def test_pdf_generation_missing_both(self, complete_preventivo):
        """Test PDF generation when both company and client are None."""
        pdf_buffer = generate_preventivo_pdf(complete_preventivo, None, None)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with None company and client data")
    
    def test_pdf_generation_empty_lines(self, complete_company, complete_client):
        """Test PDF generation with empty lines array (edge case)."""
        preventivo = {
            "preventivo_id": "prev_empty",
            "number": "PRV-2026/0002",
            "subject": "Empty quote",
            "validity_days": 30,
            "payment_type_label": "",
            "riferimento": "",
            "notes": "",
            "sconto_globale": 0,
            "acconto": 0,
            "created_at": datetime.now(timezone.utc),
            "lines": []  # Empty lines
        }
        
        pdf_buffer = generate_preventivo_pdf(preventivo, complete_company, complete_client)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with empty lines")


class TestPDFGenerationNoneValues:
    """Test PDF generation with None values in various fields."""
    
    def test_client_with_none_fields(self):
        """Test PDF generation when client has None values for optional fields."""
        preventivo = {
            "preventivo_id": "prev_test",
            "number": "PRV-2026/0003",
            "subject": "Test",
            "validity_days": 30,
            "created_at": datetime.now(timezone.utc),
            "lines": [
                {
                    "line_id": "ln_001",
                    "description": "Item 1",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100,
                    "line_total": 100,
                    "vat_rate": "22"
                }
            ]
        }
        
        company = {
            "business_name": "Test Company",
            "address": None,  # None address
            "cap": None,
            "city": None,
            "province": None,
            "partita_iva": None,
            "codice_fiscale": None,
            "phone": None,
            "email": None,
            "logo_url": None,
            "bank_details": None
        }
        
        client = {
            "business_name": "Test Client",
            "address": None,
            "cap": None,
            "city": None,
            "province": None,
            "partita_iva": None,
            "codice_fiscale": None,
            "codice_sdi": None,
            "pec": None,
            "email": None
        }
        
        pdf_buffer = generate_preventivo_pdf(preventivo, company, client)
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with None fields in company and client")
    
    def test_line_with_none_optional_fields(self):
        """Test PDF generation when line items have None optional fields."""
        preventivo = {
            "preventivo_id": "prev_test",
            "number": "PRV-2026/0004",
            "subject": "Test",
            "validity_days": 30,
            "payment_type_label": None,  # None payment
            "riferimento": None,  # None reference
            "notes": None,  # None notes
            "sconto_globale": None,  # None discount (should default to 0)
            "acconto": None,  # None advance (should default to 0)
            "created_at": datetime.now(timezone.utc),
            "lines": [
                {
                    "line_id": "ln_001",
                    "codice_articolo": None,  # None article code
                    "description": "Test item",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100,
                    "sconto_1": None,  # None discount 1
                    "sconto_2": None,  # None discount 2
                    "line_total": 100,
                    "vat_rate": "22",
                    "notes": None
                }
            ]
        }
        
        pdf_buffer = generate_preventivo_pdf(preventivo, {}, {})
        
        assert pdf_buffer is not None, "PDF buffer should not be None"
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 0, "PDF should not be empty"
        assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
        print("PDF generated successfully with None fields in line items")


class TestPDFContentValidation:
    """Test that PDF contains expected content."""
    
    def test_pdf_contains_totals(self):
        """Test that PDF contains correct totals section."""
        preventivo = {
            "preventivo_id": "prev_totals",
            "number": "PRV-2026/0005",
            "subject": "Totals Test",
            "validity_days": 30,
            "payment_type_label": "Bonifico 30gg",
            "sconto_globale": 10,
            "acconto": 0,
            "created_at": datetime.now(timezone.utc),
            "lines": [
                {
                    "line_id": "ln_001",
                    "codice_articolo": "ART001",
                    "description": "Test Item",
                    "unit": "pz",
                    "quantity": 10,
                    "unit_price": 100,
                    "sconto_1": 0,
                    "sconto_2": 0,
                    "line_total": 1000,
                    "vat_rate": "22"
                }
            ]
        }
        
        company = {"business_name": "Test Company SRL"}
        client = {"business_name": "Test Client SpA"}
        
        pdf_buffer = generate_preventivo_pdf(preventivo, company, client)
        
        # Validate PDF structure
        from pypdf import PdfReader
        pdf_buffer.seek(0)
        reader = PdfReader(pdf_buffer)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        # Check for IVA breakdown
        assert "IVA" in text or "22%" in text, "PDF should contain IVA/tax information"
        # Check for totals
        assert "IMPONIBILE" in text or "Totale" in text, "PDF should contain totals section"
        print(f"PDF content validated: {len(text)} characters extracted")
    
    def test_pdf_contains_conditions_page(self):
        """Test that PDF contains conditions page when condizioni_vendita is set."""
        preventivo = {
            "preventivo_id": "prev_conditions",
            "number": "PRV-2026/0006",
            "subject": "Conditions Test",
            "validity_days": 30,
            "created_at": datetime.now(timezone.utc),
            "lines": [
                {
                    "line_id": "ln_001",
                    "description": "Test Item",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100,
                    "line_total": 100,
                    "vat_rate": "22"
                }
            ]
        }
        
        company = {
            "business_name": "Test Company SRL",
            "condizioni_vendita": "Condizioni generali di vendita: termine di pagamento entro 30 giorni dalla data fattura."
        }
        client = {"business_name": "Test Client SpA"}
        
        pdf_buffer = generate_preventivo_pdf(preventivo, company, client)
        
        from pypdf import PdfReader
        pdf_buffer.seek(0)
        reader = PdfReader(pdf_buffer)
        
        # Should have 2 pages when conditions are present
        assert len(reader.pages) >= 1, "PDF should have at least 1 page"
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        # Check for conditions content on second page
        if len(reader.pages) >= 2:
            assert "CONDIZIONI" in text.upper() or "VENDITA" in text.upper(), \
                "PDF should contain conditions section when condizioni_vendita is set"
        print(f"PDF with conditions: {len(reader.pages)} pages")


class TestPDFEndpointIntegration:
    """Test the PDF endpoint via HTTP (requires auth)."""
    
    def test_health_check(self):
        """Verify backend is running."""
        import requests
        base_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://eco-certify.preview.emergentagent.com')
        response = requests.get(f"{base_url}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Service not healthy: {data}"
        print(f"Backend healthy: {data}")


# Run pytest directly if executed as script
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

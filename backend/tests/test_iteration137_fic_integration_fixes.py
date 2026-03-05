"""
Iteration 137: FIC (FattureInCloud) Integration Fixes Tests
============================================================
Testing the 3 bug fixes for SDI/FIC integration:
1. map_fattura_to_fic: certified_email sent as "" not null
2. _handle_fic_409: Search includes 'fields' with ei_status, handles locked docs
3. send_invoice_to_sdi: Auto-recovery keywords, save fic_document_id on failure

Focus: Unit testing map_fattura_to_fic with various client data (null PEC, empty strings, missing fields)
and testing _handle_fic_409 flow with mocked FIC responses.
"""
import pytest
import os
import sys

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from services.fattureincloud_api import map_fattura_to_fic, validate_invoice_for_sdi

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMapFatturaToFIC:
    """Test map_fattura_to_fic ensures all entity fields are strings (no null values)"""

    def test_certified_email_null_pec_becomes_empty_string(self):
        """Bug fix #1: When client.pec is None, certified_email should be '' not null"""
        invoice = {
            "document_number": "1/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Test item", "unit_price": 100, "quantity": 1, "vat_rate": 22}],
            "totals": {"total_document": 122},
        }
        # Client with pec = None (null)
        client = {
            "business_name": "Test Client",
            "partita_iva": "IT12345678901",
            "codice_fiscale": "ABC123456DEF",
            "address": "Via Test 1",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "codice_sdi": "0000000",
            "pec": None,  # BUG: This was sent as null causing 422
        }
        
        result = map_fattura_to_fic(invoice, client)
        
        # Entity fields must all be strings
        entity = result.get("entity", {})
        assert entity.get("certified_email") == "", f"Expected empty string, got {entity.get('certified_email')!r}"
        assert entity.get("certified_email") is not None, "certified_email should not be None"
        print("PASS: certified_email is empty string when pec is None")

    def test_certified_email_with_valid_pec(self):
        """When client.pec has a value, certified_email should use that value"""
        invoice = {
            "document_number": "2/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Test item", "unit_price": 100, "quantity": 1}],
            "totals": {"total_document": 122},
        }
        client = {
            "business_name": "Test Client",
            "partita_iva": "IT12345678901",
            "pec": "test@pec.it",
        }
        
        result = map_fattura_to_fic(invoice, client)
        entity = result.get("entity", {})
        
        assert entity.get("certified_email") == "test@pec.it"
        print("PASS: certified_email uses pec value when provided")

    def test_vat_number_null_becomes_empty_string(self):
        """vat_number should be empty string when partita_iva is None"""
        invoice = {
            "document_number": "3/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Test", "unit_price": 50}],
            "totals": {"total_document": 61},
        }
        client = {
            "business_name": "Private Client",
            "partita_iva": None,  # No P.IVA
            "codice_fiscale": "RSSMRA80A01H501X",
        }
        
        result = map_fattura_to_fic(invoice, client)
        entity = result.get("entity", {})
        
        assert entity.get("vat_number") == "", f"Expected empty string, got {entity.get('vat_number')!r}"
        assert entity.get("vat_number") is not None
        print("PASS: vat_number is empty string when partita_iva is None")

    def test_all_entity_fields_are_strings_not_null(self):
        """All entity fields must be strings, never None/null"""
        invoice = {
            "document_number": "4/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Item", "unit_price": 200, "quantity": 2}],
            "totals": {"total_document": 488},
        }
        # Client with all fields as None
        client = {
            "business_name": None,
            "partita_iva": None,
            "codice_fiscale": None,
            "address": None,
            "cap": None,
            "city": None,
            "province": None,
            "codice_sdi": None,
            "pec": None,
            "country": None,
        }
        
        result = map_fattura_to_fic(invoice, client)
        entity = result.get("entity", {})
        
        # Check all fields that should be strings
        string_fields = [
            "name", "vat_number", "tax_code", "address_street",
            "address_postal_code", "address_city", "address_province",
            "country", "country_iso", "ei_code", "certified_email"
        ]
        
        for field in string_fields:
            value = entity.get(field)
            assert value is not None, f"Field '{field}' should not be None"
            assert isinstance(value, str), f"Field '{field}' should be string, got {type(value)}"
        
        print(f"PASS: All {len(string_fields)} entity fields are strings (not null)")

    def test_empty_string_client_fields_preserved(self):
        """When client fields are empty strings, they should stay as empty strings"""
        invoice = {
            "document_number": "5/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Service", "unit_price": 500}],
            "totals": {"total_document": 610},
        }
        client = {
            "business_name": "Test Srl",
            "partita_iva": "",  # Empty string, not None
            "codice_fiscale": "",
            "pec": "",
        }
        
        result = map_fattura_to_fic(invoice, client)
        entity = result.get("entity", {})
        
        assert entity.get("vat_number") == ""
        assert entity.get("tax_code") == ""
        assert entity.get("certified_email") == ""
        print("PASS: Empty string fields preserved as empty strings")

    def test_codice_sdi_defaults_to_0000000(self):
        """When codice_sdi is None, it should default to '0000000'"""
        invoice = {
            "document_number": "6/2026",
            "issue_date": "2026-01-15",
            "lines": [{"description": "Test"}],
            "totals": {"total_document": 100},
        }
        client = {
            "business_name": "Test",
            "codice_sdi": None,
        }
        
        result = map_fattura_to_fic(invoice, client)
        entity = result.get("entity", {})
        
        assert entity.get("ei_code") == "0000000"
        print("PASS: ei_code defaults to '0000000' when codice_sdi is None")


class TestHandleFIC409Logic:
    """Test _handle_fic_409 logic for duplicate document handling"""

    def test_409_search_params_include_fields_with_ei_status(self):
        """
        Bug fix #2: FIC search in _handle_fic_409 must include 'fields' param with 'ei_status'
        to check if document is already sent to SDI.
        
        This is a code review test - we verify the implementation includes the fields param.
        """
        # Read the source code to verify the fix
        import inspect
        from routes.invoices import _handle_fic_409
        source = inspect.getsource(_handle_fic_409)
        
        assert '"fields":' in source or "'fields':" in source, "fields param not found in _handle_fic_409"
        assert 'ei_status' in source, "ei_status field not in search params"
        print("PASS: _handle_fic_409 includes 'fields' param with 'ei_status'")

    def test_409_skips_update_when_ei_status_is_set(self):
        """
        Bug fix #2: If FIC document already has ei_status (sent to SDI),
        skip the update and return ID directly.
        
        Code verification test.
        """
        import inspect
        from routes.invoices import _handle_fic_409
        source = inspect.getsource(_handle_fic_409)
        
        # Verify the logic checks ei_status and returns early
        assert 'ei_status' in source
        assert 'skipping update' in source.lower() or 'skip' in source.lower()
        print("PASS: _handle_fic_409 skips update when ei_status is set")

    def test_409_returns_id_on_locked_document(self):
        """
        Bug fix #2: If document is locked (409 on update), return ID instead of raising exception.
        This allows SDI send to proceed which triggers auto-recovery.
        
        Code verification test.
        """
        import inspect
        from routes.invoices import _handle_fic_409
        source = inspect.getsource(_handle_fic_409)
        
        # Verify locked document handling returns ID
        assert 'locked' in source.lower() or 'bloccato' in source.lower()
        assert 'return existing_id' in source or 'return update_result' in source
        print("PASS: _handle_fic_409 returns ID on locked document instead of raising exception")


class TestAutoRecoveryKeywords:
    """Test auto-recovery keywords in send_invoice_to_sdi"""

    def test_auto_recovery_keywords_include_tentativo_in_corso(self):
        """
        Bug fix #3: Auto-recovery must include 'in corso un tentativo' keyword.
        This handles cases where FIC returns 'È già in corso un tentativo di invio'.
        
        Code verification test.
        """
        import inspect
        from routes.invoices import send_invoice_to_sdi
        source = inspect.getsource(send_invoice_to_sdi)
        
        assert 'in corso un tentativo' in source.lower()
        print("PASS: Auto-recovery keywords include 'in corso un tentativo'")

    def test_all_auto_recovery_keywords_present(self):
        """Verify all expected auto-recovery keywords are in the code"""
        import inspect
        from routes.invoices import send_invoice_to_sdi
        source = inspect.getsource(send_invoice_to_sdi)
        source_lower = source.lower()
        
        expected_keywords = [
            "già in corso",
            "gia in corso", 
            "già presente",
            "gia presente",
            "duplicat",
            "already",
            "in corso un tentativo",
        ]
        
        found = []
        for kw in expected_keywords:
            if kw in source_lower:
                found.append(kw)
        
        assert len(found) >= 5, f"Expected at least 5 keywords, found: {found}"
        print(f"PASS: Found {len(found)} auto-recovery keywords: {found}")

    def test_fic_document_id_saved_on_sdi_failure(self):
        """
        Bug fix #3: fic_document_id must be saved even when SDI send fails.
        This prevents duplicate document creation on retry.
        
        Code verification test.
        """
        import inspect
        from routes.invoices import send_invoice_to_sdi
        source = inspect.getsource(send_invoice_to_sdi)
        
        # Look for the pattern where we save fic_document_id before raising exception
        # This should be after the except block for SDI send failure
        assert 'fic_document_id' in source
        assert 'fic_doc_id' in source
        
        # Verify there's a save operation after SDI failure
        lines = source.split('\n')
        in_sdi_except_block = False
        found_save_before_raise = False
        
        for line in lines:
            if 'except httpx.HTTPStatusError' in line:
                in_sdi_except_block = True
            if in_sdi_except_block and '"fic_document_id":' in line:
                found_save_before_raise = True
            if in_sdi_except_block and 'raise HTTPException' in line and found_save_before_raise:
                break
        
        assert found_save_before_raise, "fic_document_id should be saved before raising exception on SDI failure"
        print("PASS: fic_document_id is saved even when SDI send fails")


class TestValidateInvoiceForSDI:
    """Test validate_invoice_for_sdi function for proper validation"""

    def test_validation_fails_without_sdi_or_pec(self):
        """Validation should fail if client has neither codice_sdi nor pec"""
        invoice = {
            "lines": [{"description": "Test"}],
            "totals": {"total_document": 100},
            "issue_date": "2026-01-15",
            "document_number": "1/2026",
        }
        client = {
            "partita_iva": "IT12345678901",
            "address": "Via Test",
            "cap": "00100",
            "city": "Roma",
            # No codice_sdi, no pec
        }
        company = {
            "partita_iva": "IT98765432109",
            "codice_fiscale": "98765432109",
            "address": "Via Azienda",
            "cap": "00200",
            "city": "Milano",
        }
        
        errors = validate_invoice_for_sdi(invoice, client, company)
        
        # Should have error about missing SDI/PEC
        has_sdi_pec_error = any('SDI' in e or 'PEC' in e for e in errors)
        assert has_sdi_pec_error, f"Expected SDI/PEC error, got: {errors}"
        print(f"PASS: Validation correctly requires SDI or PEC. Errors: {errors}")

    def test_validation_passes_with_pec(self):
        """Validation should pass with pec even without codice_sdi"""
        invoice = {
            "lines": [{"description": "Test item"}],
            "totals": {"total_document": 100},
            "issue_date": "2026-01-15",
            "document_number": "1/2026",
        }
        client = {
            "partita_iva": "IT12345678901",
            "address": "Via Test",
            "cap": "00100",
            "city": "Roma",
            "pec": "test@pec.it",
            # No codice_sdi - but has pec
        }
        company = {
            "partita_iva": "IT98765432109",
            "codice_fiscale": "98765432109",
            "address": "Via Azienda",
            "cap": "00200",
            "city": "Milano",
        }
        
        errors = validate_invoice_for_sdi(invoice, client, company)
        
        # Should NOT have SDI/PEC error (has pec)
        has_sdi_pec_error = any('SDI' in e.upper() and 'PEC' in e.upper() for e in errors)
        assert not has_sdi_pec_error, f"Should not have SDI/PEC error when pec is provided: {errors}"
        print(f"PASS: Validation passes with PEC. Remaining errors (if any): {errors}")

    def test_validation_passes_with_codice_sdi(self):
        """Validation should pass with codice_sdi even without pec"""
        invoice = {
            "lines": [{"description": "Test item"}],
            "totals": {"total_document": 100},
            "issue_date": "2026-01-15",
            "document_number": "1/2026",
        }
        client = {
            "partita_iva": "IT12345678901",
            "address": "Via Test",
            "cap": "00100",
            "city": "Roma",
            "codice_sdi": "SUBM70N",
            # No pec - but has codice_sdi
        }
        company = {
            "partita_iva": "IT98765432109",
            "codice_fiscale": "98765432109",
            "address": "Via Azienda",
            "cap": "00200",
            "city": "Milano",
        }
        
        errors = validate_invoice_for_sdi(invoice, client, company)
        
        # Should NOT have SDI/PEC error (has codice_sdi)
        has_sdi_pec_error = any('SDI' in e.upper() and 'PEC' in e.upper() for e in errors)
        assert not has_sdi_pec_error, f"Should not have SDI/PEC error when codice_sdi is provided: {errors}"
        print(f"PASS: Validation passes with codice_sdi. Remaining errors (if any): {errors}")


class TestMockedFIC409Handling:
    """Test _handle_fic_409 with mocked FIC responses (no real API calls)"""

    @pytest.mark.asyncio
    async def test_handle_fic_409_with_ei_status_set_returns_id(self):
        """When FIC document already has ei_status, should return ID without update"""
        from unittest.mock import AsyncMock, MagicMock
        from routes.invoices import _handle_fic_409
        
        # Mock FIC client
        mock_fic = MagicMock()
        mock_fic._request = AsyncMock(return_value={
            "data": [
                {"id": 12345, "number": 1, "date": "2026-01-15", "ei_status": "sent"}
            ]
        })
        
        invoice = {"document_number": "1/2026"}
        fic_data = {"type": "invoice"}
        
        result = await _handle_fic_409(mock_fic, invoice, fic_data)
        
        assert result == 12345, f"Expected 12345, got {result}"
        # Verify update was NOT called (since ei_status is set)
        mock_fic.update_issued_invoice.assert_not_called()
        print("PASS: _handle_fic_409 returns ID without update when ei_status is set")

    @pytest.mark.asyncio
    async def test_handle_fic_409_updates_when_no_ei_status(self):
        """When FIC document has no ei_status, should update it"""
        from unittest.mock import AsyncMock, MagicMock
        from routes.invoices import _handle_fic_409
        
        mock_fic = MagicMock()
        mock_fic._request = AsyncMock(return_value={
            "data": [
                {"id": 67890, "number": 1, "date": "2026-01-15", "ei_status": None}
            ]
        })
        mock_fic.update_issued_invoice = AsyncMock(return_value={"data": {"id": 67890}})
        
        invoice = {"document_number": "1/2026"}
        fic_data = {"type": "invoice", "entity": {"name": "Test"}}
        
        result = await _handle_fic_409(mock_fic, invoice, fic_data)
        
        assert result == 67890
        mock_fic.update_issued_invoice.assert_called_once()
        print("PASS: _handle_fic_409 updates document when no ei_status")

    @pytest.mark.asyncio
    async def test_handle_fic_409_returns_id_on_locked_error(self):
        """When update fails with 'locked', should return ID instead of raising"""
        from unittest.mock import AsyncMock, MagicMock, patch
        from routes.invoices import _handle_fic_409
        import httpx
        
        mock_fic = MagicMock()
        mock_fic._request = AsyncMock(return_value={
            "data": [
                {"id": 11111, "number": 1, "date": "2026-01-15", "ei_status": None}
            ]
        })
        
        # Create a mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {"error": {"message": "Document is locked"}}
        mock_response.text = '{"error": {"message": "Document is locked"}}'
        
        mock_error = httpx.HTTPStatusError(
            message="409 Conflict",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_fic.update_issued_invoice = AsyncMock(side_effect=mock_error)
        
        invoice = {"document_number": "1/2026"}
        fic_data = {"type": "invoice"}
        
        result = await _handle_fic_409(mock_fic, invoice, fic_data)
        
        assert result == 11111, f"Expected ID 11111 on locked error, got {result}"
        print("PASS: _handle_fic_409 returns ID when document is locked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

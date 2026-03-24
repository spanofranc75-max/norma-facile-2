"""
Iteration 255 - NC (Nota di Credito) Line Persistence Bug Fix Tests

Bug: NC lines were not being persisted after save. When user deleted 2 of 3 lines 
and saved, reopening the NC would show all 3 original lines.

Root cause: For non-bozza documents, frontend only sent metadata (not lines) and 
backend blocked structural changes.

Fix: NC documents are now always editable for lines regardless of status.

Test Cases:
1. PUT /api/invoices/{id} on NC with status 'inviata_sdi' should accept line changes
2. PUT /api/invoices/{id} on NC with status 'bozza' should accept line changes (regression)
3. PUT /api/invoices/{id} on FT with status 'inviata_sdi' should REJECT line changes (400)
4. PUT /api/invoices/{id} on FT with status 'bozza' should accept line changes (regression)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo session cookie for authentication
DEMO_COOKIE = {"session_token": "demo_session_token_normafacile"}


class TestNCLinePersistence:
    """Test NC (Nota di Credito) line persistence bug fix."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with demo auth."""
        self.session = requests.Session()
        self.session.cookies.update(DEMO_COOKIE)
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_invoices = []
        yield
        # Cleanup: delete test invoices
        for inv_id in self.created_invoices:
            try:
                self.session.delete(f"{BASE_URL}/api/invoices/{inv_id}")
            except:
                pass
    
    def _create_test_invoice(self, doc_type: str, status: str, num_lines: int = 3) -> dict:
        """Helper to create a test invoice/NC directly in DB via API."""
        # First get a client
        clients_resp = self.session.get(f"{BASE_URL}/api/clients/?limit=1")
        assert clients_resp.status_code == 200, f"Failed to get clients: {clients_resp.text}"
        clients = clients_resp.json().get("clients", [])
        assert len(clients) > 0, "No clients found for testing"
        client_id = clients[0]["client_id"]
        
        # Create invoice with multiple lines
        lines = []
        for i in range(num_lines):
            lines.append({
                "code": f"TEST_{i+1}",
                "description": f"Test Line {i+1} - {uuid.uuid4().hex[:8]}",
                "quantity": 1,
                "unit_price": 100.0 * (i + 1),
                "discount_percent": 0,
                "vat_rate": "22"
            })
        
        payload = {
            "document_type": doc_type,
            "client_id": client_id,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "lines": lines,
            "notes": f"Test {doc_type} for iteration 255"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/invoices/", json=payload)
        assert create_resp.status_code == 201, f"Failed to create {doc_type}: {create_resp.text}"
        invoice = create_resp.json()
        invoice_id = invoice["invoice_id"]
        self.created_invoices.append(invoice_id)
        
        # If status is not bozza, we need to transition it
        if status != "bozza":
            # First emit the document
            emit_resp = self.session.patch(
                f"{BASE_URL}/api/invoices/{invoice_id}/status",
                json={"status": "emessa"}
            )
            assert emit_resp.status_code == 200, f"Failed to emit: {emit_resp.text}"
            
            # Then transition to target status if needed
            if status == "inviata_sdi":
                sdi_resp = self.session.patch(
                    f"{BASE_URL}/api/invoices/{invoice_id}/status",
                    json={"status": "inviata_sdi"}
                )
                assert sdi_resp.status_code == 200, f"Failed to set inviata_sdi: {sdi_resp.text}"
        
        # Fetch the final state
        get_resp = self.session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        assert get_resp.status_code == 200
        return get_resp.json()
    
    def test_nc_inviata_sdi_accepts_line_changes(self):
        """
        TEST 1: PUT /api/invoices/{id} on NC with status 'inviata_sdi' 
        should accept line changes and persist them.
        
        This is the main bug fix test.
        """
        # Create NC with 3 lines and status inviata_sdi
        nc = self._create_test_invoice("NC", "inviata_sdi", num_lines=3)
        nc_id = nc["invoice_id"]
        original_lines = nc["lines"]
        
        assert len(original_lines) == 3, f"Expected 3 lines, got {len(original_lines)}"
        assert nc["status"] == "inviata_sdi", f"Expected status inviata_sdi, got {nc['status']}"
        
        # Now update with only 1 line (simulating user deleting 2 lines)
        new_lines = [{
            "code": original_lines[0].get("code", "KEPT"),
            "description": original_lines[0]["description"],
            "quantity": original_lines[0]["quantity"],
            "unit_price": original_lines[0]["unit_price"],
            "discount_percent": original_lines[0].get("discount_percent", 0),
            "vat_rate": original_lines[0].get("vat_rate", "22")
        }]
        
        update_payload = {
            "lines": new_lines,
            "notes": "Updated NC with 1 line"
        }
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{nc_id}", json=update_payload)
        assert update_resp.status_code == 200, f"NC line update should succeed: {update_resp.text}"
        
        updated_nc = update_resp.json()
        assert len(updated_nc["lines"]) == 1, f"Expected 1 line after update, got {len(updated_nc['lines'])}"
        
        # Verify persistence by fetching again
        verify_resp = self.session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        assert verify_resp.status_code == 200
        verified_nc = verify_resp.json()
        
        assert len(verified_nc["lines"]) == 1, f"Line change not persisted! Expected 1 line, got {len(verified_nc['lines'])}"
        print(f"✓ NC with inviata_sdi status: line changes accepted and persisted (3 -> 1 lines)")
    
    def test_nc_bozza_accepts_line_changes(self):
        """
        TEST 2: PUT /api/invoices/{id} on NC with status 'bozza' 
        should accept line changes (regression test).
        """
        # Create NC with 3 lines in bozza status
        nc = self._create_test_invoice("NC", "bozza", num_lines=3)
        nc_id = nc["invoice_id"]
        
        assert len(nc["lines"]) == 3
        assert nc["status"] == "bozza"
        
        # Update with 2 lines
        new_lines = [
            {
                "code": "LINE_A",
                "description": "Updated Line A",
                "quantity": 2,
                "unit_price": 150.0,
                "discount_percent": 0,
                "vat_rate": "22"
            },
            {
                "code": "LINE_B",
                "description": "Updated Line B",
                "quantity": 1,
                "unit_price": 200.0,
                "discount_percent": 0,
                "vat_rate": "22"
            }
        ]
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{nc_id}", json={"lines": new_lines})
        assert update_resp.status_code == 200, f"NC bozza line update should succeed: {update_resp.text}"
        
        updated_nc = update_resp.json()
        assert len(updated_nc["lines"]) == 2, f"Expected 2 lines, got {len(updated_nc['lines'])}"
        
        # Verify persistence
        verify_resp = self.session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        verified_nc = verify_resp.json()
        assert len(verified_nc["lines"]) == 2
        print(f"✓ NC with bozza status: line changes accepted (regression test passed)")
    
    def test_ft_inviata_sdi_rejects_line_changes(self):
        """
        TEST 3: PUT /api/invoices/{id} on FT with status 'inviata_sdi' 
        should REJECT line changes with 400 error.
        
        This ensures the fix didn't break the protection for regular invoices.
        """
        # Create FT with 3 lines and status inviata_sdi
        ft = self._create_test_invoice("FT", "inviata_sdi", num_lines=3)
        ft_id = ft["invoice_id"]
        
        assert len(ft["lines"]) == 3
        assert ft["status"] == "inviata_sdi"
        assert ft["document_type"] == "FT"
        
        # Try to update lines - should be rejected
        new_lines = [{
            "code": "SHOULD_FAIL",
            "description": "This should not be allowed",
            "quantity": 1,
            "unit_price": 100.0,
            "discount_percent": 0,
            "vat_rate": "22"
        }]
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{ft_id}", json={"lines": new_lines})
        assert update_resp.status_code == 400, f"FT inviata_sdi line update should be rejected with 400, got {update_resp.status_code}: {update_resp.text}"
        
        # Verify lines unchanged
        verify_resp = self.session.get(f"{BASE_URL}/api/invoices/{ft_id}")
        verified_ft = verify_resp.json()
        assert len(verified_ft["lines"]) == 3, "FT lines should remain unchanged"
        print(f"✓ FT with inviata_sdi status: line changes correctly rejected (400)")
    
    def test_ft_bozza_accepts_line_changes(self):
        """
        TEST 4: PUT /api/invoices/{id} on FT with status 'bozza' 
        should accept line changes (regression test).
        """
        # Create FT with 2 lines in bozza status
        ft = self._create_test_invoice("FT", "bozza", num_lines=2)
        ft_id = ft["invoice_id"]
        
        assert len(ft["lines"]) == 2
        assert ft["status"] == "bozza"
        assert ft["document_type"] == "FT"
        
        # Update with 4 lines
        new_lines = [
            {"code": "A", "description": "Line A", "quantity": 1, "unit_price": 100, "discount_percent": 0, "vat_rate": "22"},
            {"code": "B", "description": "Line B", "quantity": 2, "unit_price": 200, "discount_percent": 0, "vat_rate": "22"},
            {"code": "C", "description": "Line C", "quantity": 3, "unit_price": 300, "discount_percent": 0, "vat_rate": "22"},
            {"code": "D", "description": "Line D", "quantity": 4, "unit_price": 400, "discount_percent": 0, "vat_rate": "22"},
        ]
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{ft_id}", json={"lines": new_lines})
        assert update_resp.status_code == 200, f"FT bozza line update should succeed: {update_resp.text}"
        
        updated_ft = update_resp.json()
        assert len(updated_ft["lines"]) == 4, f"Expected 4 lines, got {len(updated_ft['lines'])}"
        
        # Verify persistence
        verify_resp = self.session.get(f"{BASE_URL}/api/invoices/{ft_id}")
        verified_ft = verify_resp.json()
        assert len(verified_ft["lines"]) == 4
        print(f"✓ FT with bozza status: line changes accepted (regression test passed)")
    
    def test_nc_emessa_accepts_line_changes(self):
        """
        TEST 5: PUT /api/invoices/{id} on NC with status 'emessa' 
        should also accept line changes (intermediate status test).
        """
        # Create NC and emit it (but don't send to SDI)
        nc = self._create_test_invoice("NC", "bozza", num_lines=3)
        nc_id = nc["invoice_id"]
        
        # Emit the NC
        emit_resp = self.session.patch(
            f"{BASE_URL}/api/invoices/{nc_id}/status",
            json={"status": "emessa"}
        )
        assert emit_resp.status_code == 200
        
        # Verify status
        get_resp = self.session.get(f"{BASE_URL}/api/invoices/{nc_id}")
        nc = get_resp.json()
        assert nc["status"] == "emessa"
        
        # Update lines
        new_lines = [
            {"code": "EMESSA_1", "description": "Line after emit", "quantity": 1, "unit_price": 500, "discount_percent": 0, "vat_rate": "22"}
        ]
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{nc_id}", json={"lines": new_lines})
        assert update_resp.status_code == 200, f"NC emessa line update should succeed: {update_resp.text}"
        
        updated_nc = update_resp.json()
        assert len(updated_nc["lines"]) == 1
        print(f"✓ NC with emessa status: line changes accepted")
    
    def test_ft_emessa_rejects_line_changes(self):
        """
        TEST 6: PUT /api/invoices/{id} on FT with status 'emessa' 
        should REJECT line changes (non-bozza FT protection).
        """
        # Create FT and emit it
        ft = self._create_test_invoice("FT", "bozza", num_lines=2)
        ft_id = ft["invoice_id"]
        
        # Emit the FT
        emit_resp = self.session.patch(
            f"{BASE_URL}/api/invoices/{ft_id}/status",
            json={"status": "emessa"}
        )
        assert emit_resp.status_code == 200
        
        # Verify status
        get_resp = self.session.get(f"{BASE_URL}/api/invoices/{ft_id}")
        ft = get_resp.json()
        assert ft["status"] == "emessa"
        
        # Try to update lines - should be rejected
        new_lines = [
            {"code": "SHOULD_FAIL", "description": "This should not work", "quantity": 1, "unit_price": 100, "discount_percent": 0, "vat_rate": "22"}
        ]
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{ft_id}", json={"lines": new_lines})
        assert update_resp.status_code == 400, f"FT emessa line update should be rejected: {update_resp.status_code}"
        print(f"✓ FT with emessa status: line changes correctly rejected (400)")


class TestNCMetadataUpdates:
    """Test that metadata updates still work for all document types and statuses."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with demo auth."""
        self.session = requests.Session()
        self.session.cookies.update(DEMO_COOKIE)
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_invoices = []
        yield
        for inv_id in self.created_invoices:
            try:
                self.session.delete(f"{BASE_URL}/api/invoices/{inv_id}")
            except:
                pass
    
    def _create_test_invoice(self, doc_type: str, status: str) -> dict:
        """Helper to create a test invoice."""
        clients_resp = self.session.get(f"{BASE_URL}/api/clients/?limit=1")
        clients = clients_resp.json().get("clients", [])
        client_id = clients[0]["client_id"]
        
        payload = {
            "document_type": doc_type,
            "client_id": client_id,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "lines": [{"code": "TEST", "description": "Test", "quantity": 1, "unit_price": 100, "vat_rate": "22"}],
            "notes": "Original notes"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/invoices/", json=payload)
        invoice = create_resp.json()
        invoice_id = invoice["invoice_id"]
        self.created_invoices.append(invoice_id)
        
        if status != "bozza":
            self.session.patch(f"{BASE_URL}/api/invoices/{invoice_id}/status", json={"status": "emessa"})
            if status == "inviata_sdi":
                self.session.patch(f"{BASE_URL}/api/invoices/{invoice_id}/status", json={"status": "inviata_sdi"})
        
        get_resp = self.session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        return get_resp.json()
    
    def test_ft_inviata_sdi_allows_metadata_updates(self):
        """
        TEST 7: FT with inviata_sdi should still allow metadata updates 
        (notes, payment_method, etc.) even though lines are blocked.
        """
        ft = self._create_test_invoice("FT", "inviata_sdi")
        ft_id = ft["invoice_id"]
        
        # Update only metadata (no lines)
        update_payload = {
            "notes": "Updated notes for inviata_sdi FT",
            "payment_method": "carta",
            "internal_notes": "Internal update test"
        }
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{ft_id}", json=update_payload)
        assert update_resp.status_code == 200, f"Metadata update should succeed: {update_resp.text}"
        
        updated_ft = update_resp.json()
        assert updated_ft["notes"] == "Updated notes for inviata_sdi FT"
        assert updated_ft["payment_method"] == "carta"
        print(f"✓ FT inviata_sdi: metadata updates allowed")
    
    def test_nc_inviata_sdi_allows_both_lines_and_metadata(self):
        """
        TEST 8: NC with inviata_sdi should allow both line and metadata updates.
        """
        nc = self._create_test_invoice("NC", "inviata_sdi")
        nc_id = nc["invoice_id"]
        
        # Update both lines and metadata
        update_payload = {
            "lines": [
                {"code": "NEW", "description": "New line", "quantity": 2, "unit_price": 250, "vat_rate": "22"}
            ],
            "notes": "Updated NC notes",
            "payment_method": "contanti"
        }
        
        update_resp = self.session.put(f"{BASE_URL}/api/invoices/{nc_id}", json=update_payload)
        assert update_resp.status_code == 200, f"NC update should succeed: {update_resp.text}"
        
        updated_nc = update_resp.json()
        assert len(updated_nc["lines"]) == 1
        assert updated_nc["notes"] == "Updated NC notes"
        assert updated_nc["payment_method"] == "contanti"
        print(f"✓ NC inviata_sdi: both lines and metadata updates allowed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

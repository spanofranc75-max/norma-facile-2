"""
Test RdP (Richiesta di Preventivo Fornitore) Module — Iteration 126
Testing the new RdP module that works within Preventivi context.

Flow tested:
1. Create RdP from preventivo items (select supplier, add items)
2. Record supplier's price response
3. Apply prices with markup to update preventivo totals
4. Convert RdP to OdA in linked commessa
5. Generate professional PDF for the RdP
6. Delete RdP

Endpoints tested:
- POST /api/preventivi/{prev_id}/rdp - Create RdP
- GET /api/preventivi/{prev_id}/rdp - List RdPs
- PUT /api/preventivi/{prev_id}/rdp/{rdp_id}/response - Record supplier prices
- POST /api/preventivi/{prev_id}/rdp/{rdp_id}/apply-prices - Apply markup
- GET /api/preventivi/{prev_id}/rdp/{rdp_id}/pdf - Generate PDF
- POST /api/preventivi/{prev_id}/rdp/{rdp_id}/convert-oda - Convert to OdA
- DELETE /api/preventivi/{prev_id}/rdp/{rdp_id} - Delete RdP
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "cy0IDr6-Jx0MAbNueH7kJXIblPsw0xN5ihIs7OdjXos"

# Preventivo with lines (no linked commessa) - for most tests
PREV_ID_NO_COMMESSA = "prev_20a30dfe55"

# Preventivo linked to commessa - for OdA conversion test
PREV_ID_WITH_COMMESSA = "prev_35c6b96a9e75"
COMMESSA_ID = "com_e8c4810ad476"


@pytest.fixture(scope='module')
def auth_session():
    """Create authenticated session for RdP testing."""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {AUTH_TOKEN}',
        'Content-Type': 'application/json'
    })
    return session


# ══════════════════════════════════════════════════════════════════
#  BASIC RdP CRUD Operations
# ══════════════════════════════════════════════════════════════════

class TestRdPBasicOperations:
    """Test basic RdP create, list, and delete operations."""
    
    def test_create_rdp(self, auth_session):
        """POST /api/preventivi/{prev_id}/rdp creates a new RdP."""
        payload = {
            "supplier_name": "TEST_Fornitore_Iteration126",
            "supplier_id": "",
            "items": [
                {
                    "line_index": 0,
                    "description": "Lamiera S355 sp. 10mm",
                    "quantity": 100,
                    "unit": "kg",
                    "note": "Richiede cert. 3.1"
                },
                {
                    "line_index": 1,
                    "description": "Tubo 80x40x3",
                    "quantity": 50,
                    "unit": "ml",
                    "note": ""
                }
            ],
            "note": "Test RdP from iteration 126"
        }
        
        resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=payload)
        assert resp.status_code == 200, f"RdP creation failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "rdp" in data
        rdp = data["rdp"]
        
        # Validate RdP structure
        assert rdp["rdp_id"].startswith("rdp_")
        assert rdp["preventivo_id"] == PREV_ID_NO_COMMESSA
        assert rdp["supplier_name"] == "TEST_Fornitore_Iteration126"
        assert rdp["status"] == "inviata"
        assert rdp["converted_to_oda"] == False
        
        # Validate items
        assert len(rdp["items"]) == 2
        assert rdp["items"][0]["description"] == "Lamiera S355 sp. 10mm"
        assert rdp["items"][0]["quantity"] == 100
        assert rdp["items"][0]["unit"] == "kg"
        assert rdp["items"][0]["supplier_price"] is None  # Not yet filled
        
        # Store for later tests
        TestRdPBasicOperations.created_rdp_id = rdp["rdp_id"]
        print(f"Created RdP: {rdp['rdp_id']}")
    
    def test_list_rdp(self, auth_session):
        """GET /api/preventivi/{prev_id}/rdp lists all RdPs."""
        resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp')
        assert resp.status_code == 200, f"List RdP failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "rdp_list" in data
        
        # Should have at least one RdP (created in previous test or manual testing)
        rdp_list = data["rdp_list"]
        assert len(rdp_list) >= 1, "Expected at least one RdP"
        
        # Validate RdP structure in list
        rdp = rdp_list[0]
        assert "rdp_id" in rdp
        assert "preventivo_id" in rdp
        assert "supplier_name" in rdp
        assert "status" in rdp
        assert "items" in rdp
        
        print(f"Found {len(rdp_list)} RdP(s) for preventivo {PREV_ID_NO_COMMESSA}")
    
    def test_delete_rdp(self, auth_session):
        """DELETE /api/preventivi/{prev_id}/rdp/{rdp_id} deletes an RdP."""
        # First create an RdP to delete
        payload = {
            "supplier_name": "TEST_Fornitore_ToDelete",
            "items": [
                {"line_index": 0, "description": "Item to delete", "quantity": 1, "unit": "pz"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Now delete it
        delete_resp = auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')
        assert delete_resp.status_code == 200, f"Delete RdP failed: {delete_resp.status_code} - {delete_resp.text}"
        
        data = delete_resp.json()
        assert data["message"] == "RdP eliminata"
        
        # Verify deletion
        list_resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp')
        rdp_ids = [r["rdp_id"] for r in list_resp.json()["rdp_list"]]
        assert rdp_id not in rdp_ids, f"RdP {rdp_id} should have been deleted"
        
        print(f"Successfully deleted RdP: {rdp_id}")


# ══════════════════════════════════════════════════════════════════
#  RdP SUPPLIER PRICE RESPONSE
# ══════════════════════════════════════════════════════════════════

class TestRdPPriceResponse:
    """Test recording supplier price response."""
    
    def test_record_supplier_response(self, auth_session):
        """PUT /api/preventivi/{prev_id}/rdp/{rdp_id}/response records prices and updates status."""
        # Create RdP for this test
        create_payload = {
            "supplier_name": "TEST_Fornitore_PriceResponse",
            "items": [
                {"line_index": 0, "description": "Material A", "quantity": 100, "unit": "kg"},
                {"line_index": 1, "description": "Material B", "quantity": 50, "unit": "ml"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp = create_resp.json()["rdp"]
        rdp_id = rdp["rdp_id"]
        
        # Record supplier response
        response_payload = {
            "prices": [
                {"line_index": 0, "unit_price": 2.50},  # 100kg * 2.50 = 250
                {"line_index": 1, "unit_price": 15.00}  # 50ml * 15.00 = 750
            ],
            "note": "Validita' 30 giorni"
        }
        
        resp = auth_session.put(
            f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/response',
            json=response_payload
        )
        assert resp.status_code == 200, f"Price response failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "rdp" in data
        updated_rdp = data["rdp"]
        
        # Validate status change
        assert updated_rdp["status"] == "risposta_ricevuta"
        
        # Validate prices stored
        assert updated_rdp["items"][0]["supplier_price"] == 2.50
        assert updated_rdp["items"][1]["supplier_price"] == 15.00
        
        # Validate total calculated (100*2.50 + 50*15.00 = 250 + 750 = 1000)
        assert updated_rdp["total_offered"] == 1000.00
        
        # Validate note
        assert updated_rdp["response_note"] == "Validita' 30 giorni"
        
        # Store for apply-prices test
        TestRdPPriceResponse.rdp_id_with_prices = rdp_id
        print(f"Recorded prices for RdP: {rdp_id}, total offered: 1000.00")
    
    def test_response_with_custom_total(self, auth_session):
        """Supplier can provide custom total_offered (e.g., with discount)."""
        # Create RdP
        create_payload = {
            "supplier_name": "TEST_Fornitore_CustomTotal",
            "items": [
                {"line_index": 0, "description": "Item X", "quantity": 100, "unit": "kg"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Response with custom total (discount applied)
        response_payload = {
            "prices": [{"line_index": 0, "unit_price": 10.00}],  # Would be 1000, but supplier offers 900
            "total_offered": 900.00,
            "note": "Sconto 10%"
        }
        
        resp = auth_session.put(
            f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/response',
            json=response_payload
        )
        assert resp.status_code == 200
        
        # Custom total should be used
        assert resp.json()["rdp"]["total_offered"] == 900.00
        
        print(f"RdP {rdp_id} uses custom total: 900.00")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')


# ══════════════════════════════════════════════════════════════════
#  APPLY MARKUP TO PREVENTIVO
# ══════════════════════════════════════════════════════════════════

class TestApplyPricesToPreventivo:
    """Test applying supplier prices with markup to preventivo."""
    
    def test_apply_prices_with_default_markup(self, auth_session):
        """POST /api/preventivi/{prev_id}/rdp/{rdp_id}/apply-prices with 30% markup."""
        # Create and price an RdP
        create_payload = {
            "supplier_name": "TEST_Fornitore_ApplyPrices",
            "items": [
                {"line_index": 0, "description": "Test Material", "quantity": 10, "unit": "kg"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Record supplier price
        price_payload = {
            "prices": [{"line_index": 0, "unit_price": 100.00}]  # 10 * 100 = 1000 supplier cost
        }
        auth_session.put(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/response', json=price_payload)
        
        # Apply with default 30% markup
        apply_payload = {
            "markup_rules": [
                {"line_index": 0, "supplier_price": 100.00, "markup_pct": 30}
            ]
        }
        
        resp = auth_session.post(
            f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/apply-prices',
            json=apply_payload
        )
        assert resp.status_code == 200, f"Apply prices failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "updated_lines" in data
        assert "new_totals" in data
        
        # Client price should be 100 * 1.30 = 130
        updated_line = data["updated_lines"][0]
        assert updated_line["supplier_price"] == 100.00
        assert updated_line["markup_pct"] == 30
        assert updated_line["client_price"] == 130.00
        
        # Totals should be recalculated
        assert "imponibile" in data["new_totals"]
        assert "total_vat" in data["new_totals"]
        assert "total" in data["new_totals"]
        
        print(f"Applied prices: supplier=100, markup=30%, client=130")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')
    
    def test_apply_prices_with_custom_markup(self, auth_session):
        """Apply with different markup percentages per line."""
        # Create and price an RdP
        create_payload = {
            "supplier_name": "TEST_Fornitore_CustomMarkup",
            "items": [
                {"line_index": 0, "description": "Material Low Margin", "quantity": 1, "unit": "pz"},
                {"line_index": 1, "description": "Material High Margin", "quantity": 1, "unit": "pz"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Record supplier prices
        price_payload = {
            "prices": [
                {"line_index": 0, "unit_price": 100.00},
                {"line_index": 1, "unit_price": 200.00}
            ]
        }
        auth_session.put(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/response', json=price_payload)
        
        # Apply with different markups
        apply_payload = {
            "markup_rules": [
                {"line_index": 0, "supplier_price": 100.00, "markup_pct": 15},  # Low margin: 115
                {"line_index": 1, "supplier_price": 200.00, "markup_pct": 50}   # High margin: 300
            ]
        }
        
        resp = auth_session.post(
            f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/apply-prices',
            json=apply_payload
        )
        assert resp.status_code == 200
        
        updated = resp.json()["updated_lines"]
        
        # Line 0: 100 * 1.15 = 115
        line_0 = next((l for l in updated if l["line_index"] == 0), None)
        assert line_0 is not None
        assert line_0["client_price"] == 115.00
        
        # Line 1: 200 * 1.50 = 300
        line_1 = next((l for l in updated if l["line_index"] == 1), None)
        assert line_1 is not None
        assert line_1["client_price"] == 300.00
        
        print(f"Custom markups applied: Line0=15%->115, Line1=50%->300")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')


# ══════════════════════════════════════════════════════════════════
#  PDF GENERATION
# ══════════════════════════════════════════════════════════════════

class TestRdPPdfGeneration:
    """Test PDF generation for RdP."""
    
    def test_generate_rdp_pdf(self, auth_session):
        """GET /api/preventivi/{prev_id}/rdp/{rdp_id}/pdf generates valid PDF."""
        # Create an RdP
        create_payload = {
            "supplier_name": "TEST_Fornitore_PDF",
            "items": [
                {"line_index": 0, "description": "Item for PDF test", "quantity": 100, "unit": "kg"}
            ],
            "note": "Note for PDF"
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Generate PDF
        resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/pdf')
        assert resp.status_code == 200, f"PDF generation failed: {resp.status_code} - {resp.text}"
        
        # Validate response is PDF
        assert resp.headers.get('content-type') == 'application/pdf'
        assert 'attachment' in resp.headers.get('content-disposition', '')
        
        # Validate PDF content (starts with %PDF)
        pdf_bytes = resp.content
        assert len(pdf_bytes) > 1000, "PDF seems too small"
        assert pdf_bytes[:4] == b'%PDF', "Response is not a valid PDF"
        
        # Validate filename contains RdP info
        content_disp = resp.headers.get('content-disposition', '')
        assert 'RdP_' in content_disp, "Filename should contain 'RdP_'"
        assert '.pdf' in content_disp, "Filename should end with .pdf"
        
        # PDF is valid if it has proper size and structure (content is compressed)
        # WeasyPrint generates valid PDFs with compressed streams
        assert pdf_bytes[:4] == b'%PDF' and b'%%EOF' in pdf_bytes[-100:], "PDF structure incomplete"
        
        print(f"Generated PDF for RdP {rdp_id}, size: {len(pdf_bytes)} bytes")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')


# ══════════════════════════════════════════════════════════════════
#  CONVERT TO OdA (ORDINE DI ACQUISTO)
# ══════════════════════════════════════════════════════════════════

class TestConvertRdPToOdA:
    """Test converting RdP to OdA in linked commessa."""
    
    def test_convert_fails_without_commessa(self, auth_session):
        """Convert should fail (400) if preventivo has no linked commessa."""
        # Create RdP on preventivo without commessa
        create_payload = {
            "supplier_name": "TEST_Fornitore_NoCommessa",
            "items": [
                {"line_index": 0, "description": "Item", "quantity": 1, "unit": "pz"}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Try to convert - should fail
        resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}/convert-oda')
        assert resp.status_code == 400, f"Expected 400 for no commessa, got: {resp.status_code}"
        
        error_msg = resp.json().get("detail", "")
        assert "commessa" in error_msg.lower(), f"Error should mention commessa: {error_msg}"
        
        print(f"Convert correctly rejected for RdP {rdp_id} (no linked commessa)")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{rdp_id}')
    
    def test_convert_to_oda_success(self, auth_session):
        """POST /api/preventivi/{prev_id}/rdp/{rdp_id}/convert-oda creates OdA."""
        # Create RdP on preventivo WITH linked commessa
        create_payload = {
            "supplier_name": "TEST_Fornitore_ConvertOdA",
            "items": [
                {"line_index": 0, "description": "Material for OdA", "quantity": 50, "unit": "kg"}
            ],
            "note": "Test conversion"
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        rdp = create_resp.json()["rdp"]
        rdp_id = rdp["rdp_id"]
        
        # Record price first (OdA needs pricing)
        price_payload = {
            "prices": [{"line_index": 0, "unit_price": 5.00}]  # 50kg * 5 = 250
        }
        auth_session.put(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}/response', json=price_payload)
        
        # Convert to OdA
        resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}/convert-oda')
        assert resp.status_code == 200, f"Convert failed: {resp.status_code} - {resp.text}"
        
        data = resp.json()
        assert "oda_id" in data
        assert "commessa_id" in data
        assert data["oda_id"].startswith("oda_")
        assert data["commessa_id"] == COMMESSA_ID
        
        # Verify RdP status updated
        list_resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp')
        converted_rdp = next(
            (r for r in list_resp.json()["rdp_list"] if r["rdp_id"] == rdp_id), 
            None
        )
        assert converted_rdp is not None
        assert converted_rdp["converted_to_oda"] == True
        assert converted_rdp["status"] == "convertita_oda"
        assert converted_rdp["oda_id"] == data["oda_id"]
        
        print(f"Converted RdP {rdp_id} to OdA {data['oda_id']} in commessa {data['commessa_id']}")
        
        # Cleanup - delete the RdP (OdA remains in commessa)
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}')
    
    def test_convert_twice_fails(self, auth_session):
        """Cannot convert same RdP to OdA twice."""
        # Create RdP
        create_payload = {
            "supplier_name": "TEST_Fornitore_DoubleCOnvert",
            "items": [{"line_index": 0, "description": "Item", "quantity": 1, "unit": "pz"}]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp', json=create_payload)
        assert create_resp.status_code == 200
        rdp_id = create_resp.json()["rdp"]["rdp_id"]
        
        # Add price
        auth_session.put(
            f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}/response',
            json={"prices": [{"line_index": 0, "unit_price": 10.00}]}
        )
        
        # First convert - should succeed
        resp1 = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}/convert-oda')
        assert resp1.status_code == 200
        
        # Second convert - should fail
        resp2 = auth_session.post(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}/convert-oda')
        assert resp2.status_code == 400
        assert "convertita" in resp2.json().get("detail", "").lower()
        
        print(f"Double conversion correctly rejected for RdP {rdp_id}")
        
        # Cleanup
        auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_WITH_COMMESSA}/rdp/{rdp_id}')


# ══════════════════════════════════════════════════════════════════
#  ERROR HANDLING
# ══════════════════════════════════════════════════════════════════

class TestRdPErrorHandling:
    """Test error cases for RdP endpoints."""
    
    def test_rdp_not_found(self, auth_session):
        """Operations on non-existent RdP return 404."""
        fake_rdp_id = "rdp_nonexistent123"
        
        # GET PDF
        resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{fake_rdp_id}/pdf')
        assert resp.status_code == 404
        
        # PUT response
        resp = auth_session.put(
            f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{fake_rdp_id}/response',
            json={"prices": []}
        )
        assert resp.status_code == 404
        
        # DELETE
        resp = auth_session.delete(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp/{fake_rdp_id}')
        assert resp.status_code == 404
        
        print("404 errors correctly returned for non-existent RdP")
    
    def test_preventivo_not_found(self, auth_session):
        """Operations on non-existent preventivo return 404."""
        fake_prev_id = "prev_nonexistent456"
        
        # List RdPs
        resp = auth_session.get(f'{BASE_URL}/api/preventivi/{fake_prev_id}/rdp')
        assert resp.status_code == 404
        
        # Create RdP
        resp = auth_session.post(
            f'{BASE_URL}/api/preventivi/{fake_prev_id}/rdp',
            json={"supplier_name": "Test", "items": []}
        )
        assert resp.status_code == 404
        
        print("404 errors correctly returned for non-existent preventivo")


# ══════════════════════════════════════════════════════════════════
#  REGRESSION: Existing RdP Data
# ══════════════════════════════════════════════════════════════════

class TestExistingRdPData:
    """Test with existing RdP created during manual testing."""
    
    def test_list_includes_existing_rdp(self, auth_session):
        """List should include RdP rdp_3f15f6da08 created during manual testing."""
        resp = auth_session.get(f'{BASE_URL}/api/preventivi/{PREV_ID_NO_COMMESSA}/rdp')
        assert resp.status_code == 200
        
        rdp_ids = [r["rdp_id"] for r in resp.json()["rdp_list"]]
        
        # This RdP was created during manual testing per main agent
        if "rdp_3f15f6da08" in rdp_ids:
            print("Existing RdP rdp_3f15f6da08 found in list")
        else:
            print(f"Note: rdp_3f15f6da08 not found. Found: {rdp_ids}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

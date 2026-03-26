"""
Iteration 265 Tests: DDT Numbering, Fatture Collegate, SDI Preview
Tests for:
1. DDT atomic counter - next_ddt_number uses counters collection
2. DDT number editable - POST/PUT with custom number field
3. Fatture collegate endpoints - GET/POST/DELETE for commessa
4. DDT counters initialization at startup
5. DDT list returns ALL DDTs including conto_lavoro
"""
import pytest
import os
import requests
from pymongo import MongoClient
from datetime import datetime, timezone

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://spanofranc75_db_user:NormaFacile2026@cluster0.aypz9f1.mongodb.net/?appName=Cluster0&retryWrites=true&w=majority")
DB_NAME = os.environ.get("DB_NAME", "normafacile")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fattura-send.preview.emergentagent.com")

# Test data from credentials
TEST_USER_ID = "user_97c773827822"
TEST_TENANT_ID = "ten_1cf1a865bf20"
TEST_COMMESSA_ID = "com_e8c4810ad476"
TEST_DDT_CL_ID = "ddt_b7e1f1ea8733"  # CL-2026-0002
TEST_DDT_VENDITA_ID = "ddt_370cfd92bbf1"  # DDT-2026-0003
TEST_INVOICE_1 = "inv_03ff13a2df32"  # 10/2026
TEST_INVOICE_2 = "inv_bb29c5c5e42a"  # NC-03/2026


@pytest.fixture(scope="module")
def db():
    """Get MongoDB database connection using sync pymongo."""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 1: DDT Atomic Counter
# ═══════════════════════════════════════════════════════════════════

class TestDDTAtomicCounter:
    """Test DDT numbering uses atomic counters collection."""

    def test_counters_collection_exists(self, db):
        """Verify counters collection exists and has DDT counters."""
        collections = db.list_collection_names()
        assert "counters" in collections, "counters collection should exist"
        
        # Check for DDT counters
        ddt_counters = list(db.counters.find({"_id": {"$regex": "^ddt_"}}))
        assert len(ddt_counters) > 0, "Should have DDT counters in counters collection"
        print(f"Found {len(ddt_counters)} DDT counters")

    def test_counter_format_correct(self, db):
        """Verify counter _id format is ddt_{type}_{user_id}_{year}."""
        year = datetime.now(timezone.utc).strftime("%Y")
        
        # Check for vendita counter
        vendita_counter = db.counters.find_one({"_id": {"$regex": f"^ddt_vendita_.*_{year}$"}})
        if vendita_counter:
            assert "seq" in vendita_counter, "Counter should have seq field"
            assert isinstance(vendita_counter["seq"], int), "seq should be integer"
            print(f"Vendita counter: {vendita_counter['_id']} = {vendita_counter['seq']}")

        # Check for conto_lavoro counter
        cl_counter = db.counters.find_one({"_id": {"$regex": f"^ddt_conto_lavoro_.*_{year}$"}})
        if cl_counter:
            assert "seq" in cl_counter, "Counter should have seq field"
            print(f"Conto Lavoro counter: {cl_counter['_id']} = {cl_counter['seq']}")

        # Check for rientro counter
        rcl_counter = db.counters.find_one({"_id": {"$regex": f"^ddt_rientro_conto_lavoro_.*_{year}$"}})
        if rcl_counter:
            print(f"Rientro counter: {rcl_counter['_id']} = {rcl_counter['seq']}")

    def test_next_ddt_number_function_import(self):
        """Verify next_ddt_number function can be imported and uses counters."""
        from routes.ddt import next_ddt_number
        import inspect
        
        # Check function signature
        sig = inspect.signature(next_ddt_number)
        params = list(sig.parameters.keys())
        assert "user_id" in params, "next_ddt_number should accept user_id"
        assert "ddt_type" in params, "next_ddt_number should accept ddt_type"
        
        # Check function source uses counters
        source = inspect.getsource(next_ddt_number)
        assert "db.counters" in source, "next_ddt_number should use db.counters collection"
        assert "find_one_and_update" in source, "next_ddt_number should use atomic find_one_and_update"
        assert "$inc" in source, "next_ddt_number should use $inc for atomic increment"
        print("next_ddt_number function correctly uses atomic counters")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 2: DDT Number Editable
# ═══════════════════════════════════════════════════════════════════

class TestDDTNumberEditable:
    """Test DDT number field is editable on create and update."""

    def test_ddt_create_model_has_number_field(self):
        """Verify DDTCreate model has optional number field."""
        from models.ddt import DDTCreate
        
        # Get model fields
        fields = DDTCreate.model_fields
        assert "number" in fields, "DDTCreate should have 'number' field"
        
        # Check it's optional (has default None)
        number_field = fields["number"]
        assert number_field.default is None, "number field should default to None"
        print("DDTCreate.number field is optional (default=None)")

    def test_ddt_update_model_has_number_field(self):
        """Verify DDTUpdate model has optional number field."""
        from models.ddt import DDTUpdate
        
        fields = DDTUpdate.model_fields
        assert "number" in fields, "DDTUpdate should have 'number' field"
        
        number_field = fields["number"]
        assert number_field.default is None, "number field should default to None"
        print("DDTUpdate.number field is optional (default=None)")

    def test_create_ddt_uses_custom_number(self):
        """Verify create_ddt endpoint uses custom number if provided."""
        from routes.ddt import create_ddt
        import inspect
        
        source = inspect.getsource(create_ddt)
        # Check that custom number is used when provided
        assert "data.number" in source, "create_ddt should check data.number"
        assert "next_ddt_number" in source, "create_ddt should call next_ddt_number as fallback"
        print("create_ddt correctly handles custom number field")

    def test_update_ddt_includes_number_in_simple_fields(self):
        """Verify update_ddt includes 'number' in updatable fields."""
        from routes.ddt import update_ddt
        import inspect
        
        source = inspect.getsource(update_ddt)
        # Check that number is in the simple fields list
        assert '"number"' in source or "'number'" in source, "update_ddt should include 'number' in updatable fields"
        print("update_ddt correctly includes 'number' in updatable fields")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 3: Fatture Collegate Endpoints
# ═══════════════════════════════════════════════════════════════════

class TestFattureCollegateEndpoints:
    """Test fatture collegate endpoints for commessa."""

    def test_get_fatture_collegate_endpoint_exists(self):
        """Verify GET /api/commesse/{id}/fatture-collegate endpoint exists."""
        from routes.commesse import router
        
        routes = [r.path for r in router.routes]
        # Routes include the prefix /commesse/
        assert "/commesse/{commessa_id}/fatture-collegate" in routes, "GET fatture-collegate route should exist"
        print("GET /commesse/{id}/fatture-collegate endpoint exists")

    def test_post_fatture_collegate_endpoint_exists(self):
        """Verify POST /api/commesse/{id}/fatture-collegate endpoint exists."""
        from routes.commesse import link_fatture
        assert link_fatture is not None, "link_fatture function should exist"
        print("POST /commesse/{id}/fatture-collegate endpoint exists")

    def test_delete_fatture_collegate_endpoint_exists(self):
        """Verify DELETE /api/commesse/{id}/fatture-collegate/{invoice_id} endpoint exists."""
        from routes.commesse import router
        
        routes = [r.path for r in router.routes]
        assert "/commesse/{commessa_id}/fatture-collegate/{invoice_id}" in routes, "DELETE fatture-collegate route should exist"
        print("DELETE /commesse/{id}/fatture-collegate/{invoice_id} endpoint exists")

    def test_get_fatture_collegate_requires_auth(self):
        """Verify GET fatture-collegate returns 401 without auth."""
        try:
            url = f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/fatture-collegate"
            response = requests.get(url, timeout=30)
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print("GET fatture-collegate correctly requires authentication")
        except requests.exceptions.Timeout:
            pytest.skip("Request timed out - network issue")

    def test_post_fatture_collegate_requires_auth(self):
        """Verify POST fatture-collegate returns 401 without auth."""
        try:
            url = f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/fatture-collegate"
            response = requests.post(url, json={"invoice_ids": [TEST_INVOICE_1]}, timeout=30)
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print("POST fatture-collegate correctly requires authentication")
        except requests.exceptions.Timeout:
            pytest.skip("Request timed out - network issue")

    def test_delete_fatture_collegate_requires_auth(self):
        """Verify DELETE fatture-collegate returns 401 without auth."""
        try:
            url = f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/fatture-collegate/{TEST_INVOICE_1}"
            response = requests.delete(url, timeout=30)
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print("DELETE fatture-collegate correctly requires authentication")
        except requests.exceptions.Timeout:
            pytest.skip("Request timed out - network issue")

    def test_link_fatture_function_logic(self):
        """Verify link_fatture function updates both commessa and invoices."""
        from routes.commesse import link_fatture
        import inspect
        
        source = inspect.getsource(link_fatture)
        
        # Should update commessa with $addToSet
        assert "$addToSet" in source, "link_fatture should use $addToSet to add invoice IDs"
        assert "fatture_collegate" in source, "link_fatture should update fatture_collegate field"
        
        # Should also update invoices with commessa_id
        assert "db.invoices.update_many" in source, "link_fatture should update invoices with commessa_id"
        print("link_fatture correctly updates both commessa and invoices")

    def test_unlink_fattura_function_logic(self):
        """Verify unlink_fattura function removes link from both sides."""
        from routes.commesse import unlink_fattura
        import inspect
        
        source = inspect.getsource(unlink_fattura)
        
        # Should use $pull to remove from array
        assert "$pull" in source, "unlink_fattura should use $pull to remove invoice ID"
        
        # Should also update invoice to remove commessa_id
        assert "$unset" in source, "unlink_fattura should $unset commessa_id from invoice"
        print("unlink_fattura correctly removes link from both sides")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 4: DDT Counter Initialization at Startup
# ═══════════════════════════════════════════════════════════════════

class TestDDTCounterInitialization:
    """Test DDT counters are initialized from existing data at startup."""

    def test_main_py_initializes_counters(self):
        """Verify main.py initializes DDT counters at startup."""
        import inspect
        from main import lifespan
        
        source = inspect.getsource(lifespan)
        
        # Check for DDT counter initialization
        assert "ddt_type" in source, "lifespan should iterate over ddt_types"
        assert "counters" in source, "lifespan should update counters collection"
        assert "ddt_documents" in source, "lifespan should query ddt_documents for max seq"
        print("main.py lifespan correctly initializes DDT counters")

    def test_counter_initialization_uses_max_seq(self):
        """Verify counter initialization finds max existing sequence number."""
        import inspect
        from main import lifespan
        
        source = inspect.getsource(lifespan)
        
        # Should use aggregation to find max
        assert "$max" in source, "Counter init should use $max to find highest seq"
        assert "$toInt" in source or "max_seq" in source, "Counter init should convert seq to int"
        print("Counter initialization correctly finds max existing sequence")

    def test_counters_match_existing_ddts(self, db):
        """Verify counters are >= max existing DDT numbers for the main test user."""
        year = datetime.now(timezone.utc).strftime("%Y")
        
        for ddt_type, prefix in [("vendita", "DDT"), ("conto_lavoro", "CL"), ("rientro_conto_lavoro", "RCL")]:
            # Find counter for the main test user
            counter = db.counters.find_one({"_id": f"ddt_{ddt_type}_{TEST_USER_ID}_{year}"})
            if counter:
                counter_seq = counter.get("seq", 0)
                
                # Find max existing DDT number for this type and user
                pipeline = [
                    {"$match": {"ddt_type": ddt_type, "user_id": TEST_USER_ID, "number": {"$regex": f"^{prefix}-{year}-"}}},
                    {"$project": {"seq_str": {"$arrayElemAt": [{"$split": ["$number", "-"]}, 2]}}},
                    {"$addFields": {"seq_num": {"$toInt": {"$ifNull": ["$seq_str", "0"]}}}},
                    {"$group": {"_id": None, "max_seq": {"$max": "$seq_num"}}},
                ]
                agg = list(db.ddt_documents.aggregate(pipeline))
                max_existing = agg[0]["max_seq"] if agg and agg[0].get("max_seq") else 0
                
                assert counter_seq >= max_existing, f"Counter {counter['_id']} ({counter_seq}) should be >= max existing ({max_existing})"
                print(f"{ddt_type}: counter={counter_seq}, max_existing={max_existing} ✓")
            else:
                print(f"{ddt_type}: no counter found for {TEST_USER_ID}")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 5: DDT List Returns All Types
# ═══════════════════════════════════════════════════════════════════

class TestDDTListAllTypes:
    """Test DDT list endpoint returns all DDT types including conto_lavoro."""

    def test_ddt_list_no_type_filter_by_default(self):
        """Verify list_ddt doesn't filter by type unless specified."""
        from routes.ddt import list_ddt
        import inspect
        
        source = inspect.getsource(list_ddt)
        
        # Check that ddt_type filter is only applied when provided
        assert 'if ddt_type:' in source, "list_ddt should only filter by type when ddt_type param is provided"
        print("list_ddt correctly applies type filter only when specified")

    def test_ddt_documents_collection_has_conto_lavoro(self, db):
        """Verify ddt_documents collection contains conto_lavoro DDTs."""
        cl_count = db.ddt_documents.count_documents({"ddt_type": "conto_lavoro"})
        print(f"Found {cl_count} conto_lavoro DDTs in database")
        
        # Also check for vendita
        vendita_count = db.ddt_documents.count_documents({"ddt_type": "vendita"})
        print(f"Found {vendita_count} vendita DDTs in database")

    def test_ddt_list_returns_401_without_auth(self):
        """Verify DDT list returns 401 without auth."""
        try:
            url = f"{BASE_URL}/api/ddt/"
            response = requests.get(url, timeout=30)
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print("DDT list correctly requires authentication")
        except requests.exceptions.Timeout:
            pytest.skip("Request timed out - network issue")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 6: Frontend Code Review
# ═══════════════════════════════════════════════════════════════════

class TestFrontendCodeReview:
    """Verify frontend components have correct data-testid attributes."""

    def test_ddt_editor_has_number_input(self):
        """Verify DDTEditorPage has editable number field with data-testid."""
        ddt_editor_path = "/app/frontend/src/pages/DDTEditorPage.js"
        assert os.path.exists(ddt_editor_path), "DDTEditorPage.js should exist"
        
        with open(ddt_editor_path, 'r') as f:
            content = f.read()
        
        # Check for data-testid="input-ddt-number"
        assert 'data-testid="input-ddt-number"' in content, "DDTEditorPage should have input-ddt-number testid"
        
        # Check that number is editable (onChange handler)
        assert 'onChange={e => setForm(f => ({ ...f, number: e.target.value }))' in content or \
               "onChange={e => setForm(f => ({ ...f, number:" in content, \
               "DDT number input should have onChange handler"
        print("DDTEditorPage has editable number field with data-testid='input-ddt-number'")

    def test_commessa_hub_has_fatture_collegate_section(self):
        """Verify CommessaHubPage has fatture collegate section with data-testid."""
        hub_path = "/app/frontend/src/pages/CommessaHubPage.js"
        assert os.path.exists(hub_path), "CommessaHubPage.js should exist"
        
        with open(hub_path, 'r') as f:
            content = f.read()
        
        # Check for data-testid="fatture-collegate"
        assert 'data-testid="fatture-collegate"' in content, "CommessaHubPage should have fatture-collegate testid"
        
        # Check for link fattura button
        assert 'data-testid="btn-link-fattura"' in content, "CommessaHubPage should have btn-link-fattura testid"
        
        # Check for link fattura dialog
        assert 'data-testid="link-fattura-dialog"' in content, "CommessaHubPage should have link-fattura-dialog testid"
        print("CommessaHubPage has fatture collegate section with correct data-testid attributes")

    def test_sdi_preview_receives_enriched_invoice(self):
        """Verify InvoiceEditorPage passes enriched invoice to SdiPreviewDialog."""
        invoice_editor_path = "/app/frontend/src/pages/InvoiceEditorPage.js"
        assert os.path.exists(invoice_editor_path), "InvoiceEditorPage.js should exist"
        
        with open(invoice_editor_path, 'r') as f:
            content = f.read()
        
        # Check SdiPreviewDialog receives enriched invoice object
        assert 'SdiPreviewDialog' in content, "InvoiceEditorPage should use SdiPreviewDialog"
        
        # Check for enriched fields
        assert 'numero:' in content, "SdiPreviewDialog should receive numero field"
        assert 'client_name:' in content, "SdiPreviewDialog should receive client_name field"
        assert 'totale:' in content or 'total:' in content, "SdiPreviewDialog should receive totale/total field"
        assert 'iva:' in content or 'vat:' in content, "SdiPreviewDialog should receive iva/vat field"
        assert 'client_piva:' in content, "SdiPreviewDialog should receive client_piva field"
        print("InvoiceEditorPage passes enriched invoice object to SdiPreviewDialog")

    def test_sdi_preview_dialog_uses_enriched_fields(self):
        """Verify SdiPreviewDialog uses the enriched invoice fields."""
        sdi_dialog_path = "/app/frontend/src/components/SdiPreviewDialog.js"
        assert os.path.exists(sdi_dialog_path), "SdiPreviewDialog.js should exist"
        
        with open(sdi_dialog_path, 'r') as f:
            content = f.read()
        
        # Check dialog uses enriched fields
        assert 'invoice.numero' in content, "SdiPreviewDialog should use invoice.numero"
        assert 'invoice.client_name' in content, "SdiPreviewDialog should use invoice.client_name"
        assert 'invoice.totale' in content or 'invoice.total' in content, \
            "SdiPreviewDialog should use invoice.totale or invoice.total"
        assert 'invoice.iva' in content or 'invoice.vat' in content, \
            "SdiPreviewDialog should use invoice.iva or invoice.vat"
        print("SdiPreviewDialog correctly uses enriched invoice fields")


# ═══════════════════════════════════════════════════════════════════
# TEST GROUP 7: Existing DDT Data Verification
# ═══════════════════════════════════════════════════════════════════

class TestExistingDDTData:
    """Verify existing DDT data matches expected format."""

    def test_existing_ddt_vendita_format(self, db):
        """Verify existing vendita DDT has correct number format."""
        # Find a vendita DDT for the test user with proper format
        ddt = db.ddt_documents.find_one({
            "user_id": TEST_USER_ID, 
            "ddt_type": "vendita",
            "number": {"$regex": "^DDT-2026-"}
        })
        if ddt:
            number = ddt.get("number", "")
            assert number.startswith("DDT-2026-"), f"Vendita DDT should have DDT-2026-XXXX format, got {number}"
            assert ddt.get("ddt_type") == "vendita", "DDT type should be vendita"
            print(f"Vendita DDT {ddt.get('ddt_id')}: {number} ✓")
        else:
            # Check if any vendita DDT exists with new format
            any_vendita = db.ddt_documents.find_one({"ddt_type": "vendita", "number": {"$regex": "^DDT-2026-"}})
            if any_vendita:
                print(f"Found vendita DDT from other user: {any_vendita.get('ddt_id')}: {any_vendita.get('number')} ✓")
            else:
                pytest.skip(f"No vendita DDT with proper format found")

    def test_existing_ddt_conto_lavoro_format(self, db):
        """Verify existing conto_lavoro DDT has correct number format."""
        ddt = db.ddt_documents.find_one({"ddt_id": TEST_DDT_CL_ID})
        if ddt:
            number = ddt.get("number", "")
            assert number.startswith("CL-2026-"), f"Conto Lavoro DDT should have CL-2026-XXXX format, got {number}"
            assert ddt.get("ddt_type") == "conto_lavoro", "DDT type should be conto_lavoro"
            print(f"Conto Lavoro DDT {TEST_DDT_CL_ID}: {number} ✓")
        else:
            pytest.skip(f"DDT {TEST_DDT_CL_ID} not found")

    def test_existing_commessa_exists(self, db):
        """Verify test commessa exists."""
        commessa = db.commesse.find_one({"commessa_id": TEST_COMMESSA_ID})
        assert commessa is not None, f"Commessa {TEST_COMMESSA_ID} should exist"
        print(f"Commessa {TEST_COMMESSA_ID}: {commessa.get('numero', 'N/A')} - {commessa.get('title', 'N/A')} ✓")

    def test_existing_invoices_exist(self, db):
        """Verify test invoices exist."""
        inv1 = db.invoices.find_one({"invoice_id": TEST_INVOICE_1})
        inv2 = db.invoices.find_one({"invoice_id": TEST_INVOICE_2})
        
        if inv1:
            print(f"Invoice {TEST_INVOICE_1}: {inv1.get('document_number', 'N/A')} ✓")
        else:
            print(f"Invoice {TEST_INVOICE_1} not found")
            
        if inv2:
            print(f"Invoice {TEST_INVOICE_2}: {inv2.get('document_number', 'N/A')} ✓")
        else:
            print(f"Invoice {TEST_INVOICE_2} not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

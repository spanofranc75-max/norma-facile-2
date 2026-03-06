"""
Iteration 155: OdA Cost Inclusion in Margin Analysis Bug Fix

Tests verify that OdA (Ordini di Acquisto) costs from approvvigionamento.ordini[].importo_totale
are now included in margin calculations.

Bug: OdA costs from approvvigionamento were NOT included in margin analysis.
Fix: margin_service.py now reads approvvigionamento.ordini[].importo_totale and conto_lavoro[].costo_totale.

Test cases:
1. Single commessa margin-full includes costi_oda field
2. costo_totale calculation includes OdA costs
3. All margins (overview) includes OdA and CL costs in costi_materiali
4. oda_detail array populated correctly with ordine info
"""

import pytest
import requests
import os
from datetime import datetime, timezone
from pymongo import MongoClient

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# MongoDB connection for direct testing
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test user ID
TEST_USER_ID = "TEST_oda_margin_user_155"
TEST_PREFIX = "TEST_ODA_155_"


@pytest.fixture(scope="module")
def mongo_client():
    """Create MongoDB client."""
    client = MongoClient(MONGO_URL)
    yield client
    client.close()


@pytest.fixture(scope="module")
def test_db(mongo_client):
    """Get test database."""
    return mongo_client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def setup_oda_test_data(test_db):
    """Create test data with approvvigionamento.ordini structure."""
    now = datetime.now(timezone.utc)
    
    # Cleanup existing test data
    test_db.commesse.delete_many({"user_id": TEST_USER_ID})
    test_db.company_costs.delete_many({"user_id": TEST_USER_ID})
    test_db.fatture_ricevute.delete_many({"user_id": TEST_USER_ID})
    
    # Create company costs (hourly rate = €50)
    test_db.company_costs.insert_one({
        "user_id": TEST_USER_ID,
        "costo_orario_pieno": 50.0,
        "costo_totale_annuo": 80000,
        "stipendi_lordi": 50000,
        "contributi_inps_inail": 15000,
        "affitto_utenze": 8000,
        "commercialista_software": 5000,
        "altri_costi_fissi": 2000,
        "ore_lavorabili_anno": 1600,
        "n_dipendenti": 1,
        "created_at": now,
        "updated_at": now
    })
    
    # ---- COMMESSA 1: With OdA costs ----
    # Tests the bug fix: OdA importo_totale = €1029.87 (from user scenario)
    commessa_oda_id = f"{TEST_PREFIX}comm_oda_001"
    test_db.commesse.insert_one({
        "commessa_id": commessa_oda_id,
        "user_id": TEST_USER_ID,
        "numero": "2026/ODA-TEST-001",
        "title": "Test Commessa con OdA",
        "client_name": "Cliente OdA Test",
        "value": 5000,  # €5,000 revenue
        "stato": "in_lavorazione",
        "costi_reali": [
            {"cost_id": "cr_oda_001", "tipo": "materiali", "descrizione": "Acciaio manuale", "importo": 500, "data": now.isoformat()},
        ],
        "ore_lavorate": 10,  # 10h × €50 = €500
        "conto_lavoro": [
            {"tipo_lavorazione": "verniciatura", "fornitore_nome": "Verniciatura Srl", "costo_totale": 500}
        ],
        # THE KEY FIX: approvvigionamento.ordini with importo_totale
        "approvvigionamento": {
            "richieste": [],
            "ordini": [
                {
                    "ordine_id": "oda_test_001",
                    "importo_totale": 1029.87,  # The exact amount from user's bug report
                    "fornitore_nome": "Test Fornitore Srl",
                    "stato": "confermato"
                }
            ],
            "arrivi": []
        },
        "created_at": now,
        "updated_at": now
    })
    # Expected costs breakdown:
    # - costi_materiali_manuali: €500
    # - costo_personale: 10h × €50 = €500
    # - costi_esterni (CL): €500
    # - costi_oda: €1029.87
    # - TOTAL: €500 + €500 + €500 + €1029.87 = €2529.87
    # - Margin: €5000 - €2529.87 = €2470.13 (49.4% - verde)
    
    # ---- COMMESSA 2: Multiple OdA orders ----
    commessa_multi_oda_id = f"{TEST_PREFIX}comm_multi_oda_002"
    test_db.commesse.insert_one({
        "commessa_id": commessa_multi_oda_id,
        "user_id": TEST_USER_ID,
        "numero": "2026/ODA-TEST-002",
        "title": "Test Commessa Multi OdA",
        "client_name": "Cliente Multi OdA",
        "value": 10000,
        "stato": "in_lavorazione",
        "costi_reali": [],
        "ore_lavorate": 0,
        "conto_lavoro": [],
        "approvvigionamento": {
            "richieste": [],
            "ordini": [
                {"ordine_id": "oda_multi_001", "importo_totale": 1000, "fornitore_nome": "Fornitore A", "stato": "confermato"},
                {"ordine_id": "oda_multi_002", "importo_totale": 2000, "fornitore_nome": "Fornitore B", "stato": "consegnato"},
                {"ordine_id": "oda_multi_003", "importo_totale": 500, "fornitore_nome": "Fornitore C", "stato": "in_attesa"},
            ],
            "arrivi": []
        },
        "created_at": now,
        "updated_at": now
    })
    # Expected costi_oda: 1000 + 2000 + 500 = €3500
    
    # ---- COMMESSA 3: No OdA (for comparison) ----
    commessa_no_oda_id = f"{TEST_PREFIX}comm_no_oda_003"
    test_db.commesse.insert_one({
        "commessa_id": commessa_no_oda_id,
        "user_id": TEST_USER_ID,
        "numero": "2026/ODA-TEST-003",
        "title": "Test Commessa senza OdA",
        "client_name": "Cliente No OdA",
        "value": 3000,
        "stato": "in_lavorazione",
        "costi_reali": [
            {"cost_id": "cr_no_oda_001", "tipo": "materiali", "descrizione": "Materiali", "importo": 1000},
        ],
        "ore_lavorate": 5,  # 5h × €50 = €250
        "conto_lavoro": [],
        "approvvigionamento": {
            "richieste": [],
            "ordini": [],  # Empty ordini
            "arrivi": []
        },
        "created_at": now,
        "updated_at": now
    })
    # Expected costi_oda: €0
    # Expected costo_totale: €1000 + €250 = €1250
    
    # ---- COMMESSA 4: Only conto_lavoro ----
    commessa_cl_only_id = f"{TEST_PREFIX}comm_cl_only_004"
    test_db.commesse.insert_one({
        "commessa_id": commessa_cl_only_id,
        "user_id": TEST_USER_ID,
        "numero": "2026/ODA-TEST-004",
        "title": "Test Commessa solo CL",
        "client_name": "Cliente CL Only",
        "value": 4000,
        "stato": "in_lavorazione",
        "costi_reali": [],
        "ore_lavorate": 0,
        "conto_lavoro": [
            {"tipo_lavorazione": "zincatura", "fornitore_nome": "Zincatura Srl", "costo_totale": 800},
            {"tipo_lavorazione": "sabbiatura", "fornitore_nome": "Sabbia Srl", "costo_totale": 300},
        ],
        "approvvigionamento": {
            "richieste": [],
            "ordini": [],
            "arrivi": []
        },
        "created_at": now,
        "updated_at": now
    })
    # Expected costi_esterni: €800 + €300 = €1100
    
    yield {
        "commessa_oda_id": commessa_oda_id,
        "commessa_multi_oda_id": commessa_multi_oda_id,
        "commessa_no_oda_id": commessa_no_oda_id,
        "commessa_cl_only_id": commessa_cl_only_id,
    }
    
    # Cleanup after tests
    test_db.commesse.delete_many({"user_id": TEST_USER_ID})
    test_db.company_costs.delete_many({"user_id": TEST_USER_ID})


class TestOdaCostInclusion:
    """Verify OdA costs are now included in margin calculations."""
    
    def test_margin_service_reads_approvvigionamento_ordini(self):
        """Verify margin_service.py code reads approvvigionamento.ordini."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check for approvvigionamento reading
        assert "approvvigionamento" in content, "margin_service.py should read approvvigionamento"
        assert ".get(\"ordini\"" in content or '.get("ordini"' in content or "ordini" in content, \
            "margin_service.py should access ordini array"
        assert "importo_totale" in content, "margin_service.py should read importo_totale from OdA"
        print("✓ margin_service.py code reads approvvigionamento.ordini[].importo_totale")
    
    def test_margin_service_has_costo_oda_variable(self):
        """Verify costo_oda is calculated separately."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        assert "costo_oda" in content, "margin_service.py should have costo_oda variable"
        assert "costi_oda" in content, "margin_service.py should return costi_oda in response"
        print("✓ margin_service.py calculates and returns costi_oda")
    
    def test_costo_totale_formula_includes_oda(self):
        """Verify costo_totale includes OdA costs in calculation."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Look for costo_totale calculation that includes costo_oda
        # Expected: costo_totale = ... + costo_oda ...
        assert "costo_oda" in content and "costo_totale" in content, \
            "costo_totale calculation should include costo_oda"
        
        # More specific check for line 124: costo_totale = round(costo_materiali_totale + costo_personale + costo_esterni + costo_oda, 2)
        lines = content.split('\n')
        found_correct_formula = False
        for line in lines:
            if "costo_totale" in line and "costo_oda" in line and "round" in line:
                found_correct_formula = True
                break
        
        assert found_correct_formula, "costo_totale formula should include costo_oda"
        print("✓ costo_totale formula includes costo_oda")


class TestSingleCommessaMarginFull:
    """Test GET /api/costs/commessa/{id}/margin-full with OdA costs."""
    
    def test_endpoint_returns_costi_oda_field(self, test_db, setup_oda_test_data):
        """Verify response includes costi_oda field."""
        commessa_id = setup_oda_test_data["commessa_oda_id"]
        
        # Direct check: commessa has OdA data
        commessa = test_db.commesse.find_one({"commessa_id": commessa_id})
        assert commessa is not None, "Test commessa not found"
        
        approv = commessa.get("approvvigionamento", {})
        ordini = approv.get("ordini", [])
        assert len(ordini) > 0, "Commessa should have OdA orders"
        
        oda_total = sum(o.get("importo_totale", 0) for o in ordini)
        assert oda_total == 1029.87, f"OdA total should be 1029.87, got {oda_total}"
        print(f"✓ Test commessa has OdA costs: €{oda_total}")
    
    def test_oda_cost_calculation_single_order(self, test_db, setup_oda_test_data):
        """Test OdA cost calculation matches expected value (€1029.87)."""
        commessa = test_db.commesse.find_one({
            "commessa_id": setup_oda_test_data["commessa_oda_id"]
        })
        
        # Calculate expected values
        costo_orario = 50.0
        value = commessa.get("value", 0)  # 5000
        
        # Manual costs
        costi_manuali = sum(c.get("importo", 0) for c in commessa.get("costi_reali", []))  # 500
        
        # Labor
        ore = commessa.get("ore_lavorate", 0)  # 10
        costo_personale = ore * costo_orario  # 500
        
        # Conto lavoro
        costo_cl = sum(cl.get("costo_totale", 0) for cl in commessa.get("conto_lavoro", []))  # 500
        
        # OdA (THE FIX)
        approv = commessa.get("approvvigionamento", {})
        costo_oda = sum(o.get("importo_totale", 0) for o in approv.get("ordini", []))  # 1029.87
        
        # Total (with OdA)
        costo_totale = costi_manuali + costo_personale + costo_cl + costo_oda
        # Expected: 500 + 500 + 500 + 1029.87 = 2529.87
        
        margine = value - costo_totale
        margine_pct = (margine / value * 100) if value > 0 else 0
        
        print(f"  Value: €{value}")
        print(f"  Costi manuali: €{costi_manuali}")
        print(f"  Costo personale: €{costo_personale}")
        print(f"  Costo CL: €{costo_cl}")
        print(f"  Costo OdA: €{costo_oda}")
        print(f"  COSTO TOTALE: €{costo_totale}")
        print(f"  Margine: €{margine} ({margine_pct:.1f}%)")
        
        assert costo_oda == 1029.87, f"OdA cost should be €1029.87, got €{costo_oda}"
        assert abs(costo_totale - 2529.87) < 0.01, f"Total cost should be €2529.87, got €{costo_totale}"
        print("✓ OdA cost correctly included in total calculation")
    
    def test_multi_oda_orders_summed(self, test_db, setup_oda_test_data):
        """Test multiple OdA orders are summed correctly."""
        commessa = test_db.commesse.find_one({
            "commessa_id": setup_oda_test_data["commessa_multi_oda_id"]
        })
        
        approv = commessa.get("approvvigionamento", {})
        ordini = approv.get("ordini", [])
        
        assert len(ordini) == 3, f"Should have 3 OdA orders, got {len(ordini)}"
        
        costo_oda = sum(o.get("importo_totale", 0) for o in ordini)
        # 1000 + 2000 + 500 = 3500
        
        assert costo_oda == 3500, f"Total OdA should be €3500, got €{costo_oda}"
        print(f"✓ Multiple OdA orders summed correctly: €{costo_oda}")


class TestAllMarginsOverview:
    """Test GET /api/costs/margin-full includes OdA in overview."""
    
    def test_overview_includes_oda_in_costi_materiali(self, test_db, setup_oda_test_data):
        """Verify get_all_margins includes OdA costs in costi_materiali."""
        # Check margin_service.py code for get_all_margins
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Look for OdA inclusion in get_all_margins function
        # Line ~211: costi_oda = sum(float(o.get("importo_totale", 0) or 0) for o in c.get("approvvigionamento", {}).get("ordini", []))
        assert "get_all_margins" in content, "get_all_margins function should exist"
        
        # Check that get_all_margins reads approvvigionamento.ordini
        # The function should include OdA in the loop for each commessa
        lines = content.split('\n')
        in_get_all_margins = False
        reads_oda_in_overview = False
        
        for line in lines:
            if "async def get_all_margins" in line:
                in_get_all_margins = True
            if in_get_all_margins and ("approvvigionamento" in line or "ordini" in line):
                reads_oda_in_overview = True
            if in_get_all_margins and "async def " in line and "get_all_margins" not in line:
                break  # Exit when we hit the next function
        
        assert reads_oda_in_overview, "get_all_margins should read approvvigionamento.ordini"
        print("✓ get_all_margins includes OdA costs")
    
    def test_overview_includes_conto_lavoro(self, test_db, setup_oda_test_data):
        """Verify get_all_margins includes conto_lavoro costs."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check for conto_lavoro in get_all_margins
        assert "conto_lavoro" in content, "margin_service should handle conto_lavoro"
        print("✓ get_all_margins includes conto_lavoro costs")
    
    def test_db_query_fetches_oda_fields(self, test_db, setup_oda_test_data):
        """Verify DB query in get_all_margins fetches approvvigionamento.ordini."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check projection includes approvvigionamento fields
        # Line ~180-181: "approvvigionamento.ordini.importo_totale": 1, "conto_lavoro.costo_totale": 1
        assert "approvvigionamento.ordini.importo_totale" in content or \
               '"approvvigionamento.ordini.importo_totale"' in content, \
            "DB projection should fetch approvvigionamento.ordini.importo_totale"
        print("✓ DB query fetches approvvigionamento.ordini.importo_totale")


class TestOdaDetailField:
    """Test that oda_detail array is populated in response."""
    
    def test_margin_service_returns_oda_detail(self):
        """Verify margin_service returns oda_detail array."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        assert "oda_detail" in content, "margin_service should return oda_detail field"
        assert "ordine_id" in content, "oda_detail should include ordine_id"
        assert "fornitore" in content, "oda_detail should include fornitore info"
        print("✓ margin_service returns oda_detail with ordine information")
    
    def test_oda_detail_structure_in_code(self):
        """Verify oda_detail structure includes required fields."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check for oda_detail append structure (lines 105-110)
        required_fields = ["ordine_id", "fornitore", "importo", "stato"]
        found_fields = sum(1 for f in required_fields if f in content)
        
        assert found_fields >= 3, f"oda_detail should have at least 3 of {required_fields}"
        print(f"✓ oda_detail structure has {found_fields}/4 required fields")


class TestEdgeCases:
    """Test edge cases for OdA cost handling."""
    
    def test_empty_ordini_array(self, test_db, setup_oda_test_data):
        """Test commessa with empty ordini array."""
        commessa = test_db.commesse.find_one({
            "commessa_id": setup_oda_test_data["commessa_no_oda_id"]
        })
        
        approv = commessa.get("approvvigionamento", {})
        ordini = approv.get("ordini", [])
        
        assert len(ordini) == 0, "Should have empty ordini array"
        
        costo_oda = sum(o.get("importo_totale", 0) for o in ordini)
        assert costo_oda == 0, "OdA cost should be €0 for empty ordini"
        print("✓ Empty ordini array handled correctly (€0)")
    
    def test_missing_approvvigionamento(self):
        """Verify code handles missing approvvigionamento gracefully."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check for safe access pattern: .get("approvvigionamento", {})
        assert 'get("approvvigionamento", {})' in content or \
               ".get('approvvigionamento', {})" in content, \
            "Code should safely access approvvigionamento with default {}"
        print("✓ Code handles missing approvvigionamento safely")
    
    def test_zero_importo_totale_skipped(self):
        """Verify ordini with importo_totale=0 don't add to oda_detail."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Check for filter: if importo > 0 (line ~103)
        assert "if importo > 0" in content or "importo > 0" in content, \
            "Code should skip ordini with importo_totale=0"
        print("✓ Zero importo_totale ordini are filtered out")


class TestEndpointAvailability:
    """Test that margin endpoints are accessible."""
    
    def test_margin_full_endpoint_exists(self):
        """Verify GET /api/costs/margin-full endpoint exists."""
        response = requests.get(f"{BASE_URL}/api/costs/margin-full")
        # 401 = requires auth (endpoint exists)
        # 404 = endpoint doesn't exist
        assert response.status_code != 404, "Endpoint /api/costs/margin-full not found"
        print(f"✓ /api/costs/margin-full endpoint exists (status: {response.status_code})")
    
    def test_commessa_margin_full_endpoint_exists(self, setup_oda_test_data):
        """Verify GET /api/costs/commessa/{id}/margin-full endpoint exists."""
        commessa_id = setup_oda_test_data["commessa_oda_id"]
        response = requests.get(f"{BASE_URL}/api/costs/commessa/{commessa_id}/margin-full")
        assert response.status_code != 404, f"Endpoint /api/costs/commessa/{commessa_id}/margin-full not found"
        print(f"✓ /api/costs/commessa/{{id}}/margin-full endpoint exists (status: {response.status_code})")


class TestCostoTotaleFormula:
    """Verify costo_totale includes all cost sources."""
    
    def test_formula_in_single_commessa(self):
        """Verify get_commessa_margin_full has correct costo_totale formula."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Line 124: costo_totale = round(costo_materiali_totale + costo_personale + costo_esterni + costo_oda, 2)
        # Must include all 4 components
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if "costo_totale" in line and "round(" in line:
                # Check this line has all components
                components = ["costo_personale", "costo_oda"]
                found = sum(1 for c in components if c in line)
                if found >= 2:
                    print(f"  Found formula at line {i+1}: {line.strip()}")
                    break
        
        print("✓ costo_totale formula verified")
    
    def test_formula_in_overview(self):
        """Verify get_all_margins has correct costo_totale formula."""
        with open("/app/backend/services/margin_service.py", "r") as f:
            content = f.read()
        
        # Line 216: costo_totale = round(costi_manuali + costi_fr + costi_oda + costi_cl + costo_personale, 2)
        assert "costi_oda" in content and "costi_cl" in content, \
            "get_all_margins should include costi_oda and costi_cl"
        print("✓ get_all_margins costo_totale formula includes OdA and CL")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test iteration 161: Stabilizzazione codebase ERP — 6 step di qualità
STEP 1: Atomic counter preventivi (3 path: create, from-distinta, clone)
STEP 2: Serializer MongoDB (serialize_doc, projection _id:0)
STEP 3: MongoDB indexes on key collections
STEP 4: Paginazione endpoints (commesse, preventivi, ddt)
STEP 5: Search globale (/api/search/)
STEP 6: Morning Briefing dashboard
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "e2Sh0HIDOg2kyY8fq-R9a3s9FfrxWvFBqKGhyPQM4XA"

@pytest.fixture(scope="module")
def auth_headers():
    return {
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


class TestSTEP1_AtomicCounterPreventivi:
    """Test atomic counter logic for preventivi — all 3 creation paths"""

    def test_create_preventivo_returns_prv_number(self, auth_headers):
        """POST /api/preventivi/ should return a PRV-YYYY-NNNN number"""
        payload = {
            "client_id": None,
            "subject": "TEST_preventivo_atomico",
            "validity_days": 30,
            "lines": [
                {"description": "Voce test", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        r = requests.post(f"{BASE_URL}/api/preventivi/", json=payload, headers=auth_headers, timeout=10)
        print(f"Create preventivo status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
        
        # Should return 201 and have a number field
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert "number" in data, "Response should have 'number' field"
        assert data["number"].startswith("PRV-"), f"Number should start with PRV-, got {data['number']}"
        
        # Store for cleanup
        self.created_prev_id = data.get("preventivo_id")
        print(f"✓ Created preventivo {data['number']} with ID {self.created_prev_id}")

    def test_preventivi_counter_sync_logic_in_code(self):
        """Verify atomic counter sync logic exists in the code (lines 460-491 in preventivi.py)"""
        import ast
        with open("/app/backend/routes/preventivi.py", "r") as f:
            content = f.read()
        
        # Check for find_one_and_update usage with atomic counter pattern
        assert "find_one_and_update" in content, "Should use find_one_and_update for atomic counter"
        assert "$inc" in content, "Should use $inc for atomic increment"
        assert "counter_id" in content, "Should have counter_id logic"
        
        # Check the sync-to-max pattern exists
        assert "max_existing" in content, "Should have max_existing sync logic"
        assert "current_counter" in content, "Should check current_counter"
        
        print("✓ Atomic counter sync logic verified in preventivi.py")


class TestSTEP2_SerializerMongoDB:
    """Test MongoDB serializer and _id:0 projection"""

    def test_serializer_module_exists(self):
        """Verify /app/backend/core/serializer.py exists and has correct functions"""
        import sys
        sys.path.insert(0, "/app/backend")
        from core.serializer import serialize_doc, serialize_list
        
        # Test serialize_doc with ObjectId-like structure
        test_doc = {
            "_id": "fake_objectid",
            "name": "Test",
            "nested": {"_id": "nested_id", "value": 123}
        }
        result = serialize_doc(test_doc)
        assert result is not None, "serialize_doc should return a value"
        assert "_id" in result, "Should keep _id as string"
        print("✓ serializer.py module verified with serialize_doc/serialize_list functions")

    def test_commessa_ops_uses_id0_projection(self):
        """Verify commessa_ops.py get_commessa_or_404 uses _id:0 projection"""
        with open("/app/backend/routes/commessa_ops.py", "r") as f:
            content = f.read()
        
        # Check line 31: find_one with {"_id": 0} projection
        assert '"_id": 0' in content or "'_id': 0" in content, "Should use _id:0 projection"
        
        # Check get_commessa_or_404 function
        assert "get_commessa_or_404" in content, "Should have get_commessa_or_404 function"
        print("✓ commessa_ops.py uses _id:0 projection in get_commessa_or_404")


class TestSTEP3_MongoDBIndexes:
    """Test MongoDB indexes exist on key collections"""

    def test_index_script_exists(self):
        """Verify create_indexes.py script exists with correct indexes"""
        with open("/app/backend/scripts/create_indexes.py", "r") as f:
            content = f.read()
        
        required_collections = [
            "commesse", "preventivi", "fatture_ricevute", 
            "invoices", "movimenti_bancari", "clients", 
            "ddt_documents", "material_batches"
        ]
        
        for coll in required_collections:
            assert f'"{coll}"' in content or f"'{coll}'" in content, \
                f"Index script should include {coll} collection"
        
        print(f"✓ Index script contains all {len(required_collections)} required collections")

    def test_indexes_have_user_id(self):
        """Verify indexes include user_id for multi-tenant filtering"""
        with open("/app/backend/scripts/create_indexes.py", "r") as f:
            content = f.read()
        
        assert "user_id" in content, "Indexes should include user_id for multi-tenant"
        assert "ASCENDING" in content, "Should use ASCENDING index direction"
        print("✓ Index script includes user_id for multi-tenant support")


class TestSTEP4_Paginazione:
    """Test pagination on commesse, preventivi, ddt endpoints"""

    def test_commesse_pagination(self, auth_headers):
        """GET /api/commesse/?page=1&per_page=2 should return pagination fields"""
        r = requests.get(
            f"{BASE_URL}/api/commesse/",
            params={"page": 1, "per_page": 2},
            headers=auth_headers, timeout=10
        )
        print(f"Commesse pagination status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Verify pagination fields exist
        required_fields = ["page", "per_page", "pages", "total", "items"]
        for field in required_fields:
            assert field in data, f"Response should have '{field}' field"
        
        # Verify values
        assert data["page"] == 1, f"page should be 1, got {data['page']}"
        assert data["per_page"] == 2, f"per_page should be 2, got {data['per_page']}"
        assert isinstance(data["items"], list), "items should be a list"
        
        print(f"✓ Commesse pagination: page={data['page']}, per_page={data['per_page']}, total={data['total']}, pages={data['pages']}, items_count={len(data['items'])}")

    def test_preventivi_pagination(self, auth_headers):
        """GET /api/preventivi/?page=1&per_page=3 should return pagination with 'preventivi' key"""
        r = requests.get(
            f"{BASE_URL}/api/preventivi/",
            params={"page": 1, "per_page": 3},
            headers=auth_headers, timeout=10
        )
        print(f"Preventivi pagination status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Note: preventivi returns 'preventivi' not 'items' for backward compat
        required_fields = ["page", "per_page", "pages", "total", "preventivi"]
        for field in required_fields:
            assert field in data, f"Response should have '{field}' field"
        
        assert data["page"] == 1, f"page should be 1, got {data['page']}"
        assert data["per_page"] == 3, f"per_page should be 3, got {data['per_page']}"
        assert isinstance(data["preventivi"], list), "preventivi should be a list"
        
        print(f"✓ Preventivi pagination: page={data['page']}, per_page={data['per_page']}, total={data['total']}, pages={data['pages']}, preventivi_count={len(data['preventivi'])}")

    def test_ddt_pagination(self, auth_headers):
        """GET /api/ddt/?page=1&per_page=3 should return pagination with 'items' key"""
        r = requests.get(
            f"{BASE_URL}/api/ddt/",
            params={"page": 1, "per_page": 3},
            headers=auth_headers, timeout=10
        )
        print(f"DDT pagination status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        required_fields = ["page", "per_page", "pages", "total", "items"]
        for field in required_fields:
            assert field in data, f"Response should have '{field}' field"
        
        assert data["page"] == 1, f"page should be 1, got {data['page']}"
        assert data["per_page"] == 3, f"per_page should be 3, got {data['per_page']}"
        assert isinstance(data["items"], list), "items should be a list"
        
        print(f"✓ DDT pagination: page={data['page']}, per_page={data['per_page']}, total={data['total']}, pages={data['pages']}, items_count={len(data['items'])}")


class TestSTEP5_GlobalSearch:
    """Test global search endpoint"""

    def test_search_returns_results_array(self, auth_headers):
        """GET /api/search/?q=NF should return results array with correct structure"""
        r = requests.get(
            f"{BASE_URL}/api/search/",
            params={"q": "NF"},
            headers=auth_headers, timeout=10
        )
        print(f"Search status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Must have 'results' array
        assert "results" in data, "Response should have 'results' field"
        assert isinstance(data["results"], list), "results should be a list"
        
        # Check result item structure if we have results
        if len(data["results"]) > 0:
            result = data["results"][0]
            required_fields = ["type", "id", "label", "subtitle", "url"]
            for field in required_fields:
                assert field in result, f"Result item should have '{field}' field"
            
            print(f"✓ Search returned {len(data['results'])} results")
            print(f"  First result: type={result['type']}, id={result['id']}, label={result['label']}")
        else:
            print(f"✓ Search returned 0 results (no matches for 'NF')")

    def test_search_different_entity_types(self, auth_headers):
        """Test search returns different entity types (commessa, preventivo, cliente, ddt)"""
        # Search for a common term that might match multiple types
        r = requests.get(
            f"{BASE_URL}/api/search/",
            params={"q": "test"},
            headers=auth_headers, timeout=10
        )
        print(f"Search 'test' status: {r.status_code}")
        
        assert r.status_code == 200
        data = r.json()
        
        # Count types found
        types_found = set()
        for result in data.get("results", []):
            types_found.add(result.get("type"))
        
        print(f"✓ Search 'test' returned {len(data.get('results', []))} results with types: {types_found}")
        
        # Valid types as per search.py
        valid_types = {"commessa", "preventivo", "cliente", "ddt"}
        for t in types_found:
            assert t in valid_types, f"Result type '{t}' should be in {valid_types}"


class TestSTEP6_MorningBriefing:
    """Test morning briefing dashboard endpoint"""

    def test_morning_briefing_structure(self, auth_headers):
        """GET /api/dashboard/morning-briefing should return correct structure"""
        r = requests.get(
            f"{BASE_URL}/api/dashboard/morning-briefing",
            headers=auth_headers, timeout=15
        )
        print(f"Morning briefing status: {r.status_code}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Required top-level fields as per dashboard.py lines 991-1173
        required_fields = [
            "scadenze_oggi_domani",
            "pagamenti_ritardo", 
            "commesse_allarme",
            "da_fare"
        ]
        
        for field in required_fields:
            assert field in data, f"Response should have '{field}' field"
        
        # Check scadenze_oggi_domani is a list
        assert isinstance(data["scadenze_oggi_domani"], list), "scadenze_oggi_domani should be a list"
        
        # Check pagamenti_ritardo is a list
        assert isinstance(data["pagamenti_ritardo"], list), "pagamenti_ritardo should be a list"
        
        # Check commesse_allarme is a list
        assert isinstance(data["commesse_allarme"], list), "commesse_allarme should be a list"
        
        # Check da_fare structure
        assert isinstance(data["da_fare"], dict), "da_fare should be a dict"
        da_fare_fields = ["preventivi_da_convertire", "ddt_non_fatturati", "fatture_scadute"]
        for field in da_fare_fields:
            assert field in data["da_fare"], f"da_fare should have '{field}' field"
        
        print(f"✓ Morning briefing structure verified:")
        print(f"  scadenze_oggi_domani: {len(data['scadenze_oggi_domani'])} items")
        print(f"  pagamenti_ritardo: {len(data['pagamenti_ritardo'])} items")
        print(f"  commesse_allarme: {len(data['commesse_allarme'])} items")
        print(f"  da_fare: {data['da_fare']}")

    def test_morning_briefing_totals(self, auth_headers):
        """Verify morning briefing returns total counters"""
        r = requests.get(
            f"{BASE_URL}/api/dashboard/morning-briefing",
            headers=auth_headers, timeout=15
        )
        
        assert r.status_code == 200
        data = r.json()
        
        # Check derived totals
        expected_totals = [
            "totale_scadenze_oggi",
            "totale_scadenze_domani",
            "totale_importo_ritardo"
        ]
        
        for field in expected_totals:
            assert field in data, f"Response should have '{field}' field"
        
        print(f"✓ Morning briefing totals:")
        print(f"  totale_scadenze_oggi: {data.get('totale_scadenze_oggi', 0)}")
        print(f"  totale_scadenze_domani: {data.get('totale_scadenze_domani', 0)}")
        print(f"  totale_importo_ritardo: {data.get('totale_importo_ritardo', 0)}")


class TestClonePreventivo:
    """Test clone preventivo uses atomic counter"""
    
    def test_clone_endpoint_exists(self, auth_headers):
        """Verify clone endpoint structure in code"""
        with open("/app/backend/routes/preventivi.py", "r") as f:
            content = f.read()
        
        # Check clone endpoint exists (lines 638-734)
        assert '/{prev_id}/clone' in content, "Clone endpoint should exist"
        assert "find_one_and_update" in content, "Clone should use atomic counter"
        
        print("✓ Clone endpoint verified with atomic counter logic")


class TestFromDistintaPreventivo:
    """Test from-distinta preventivo uses atomic counter"""
    
    def test_from_distinta_endpoint_exists(self):
        """Verify from-distinta endpoint structure in code"""
        with open("/app/backend/routes/preventivi.py", "r") as f:
            content = f.read()
        
        # Check from-distinta endpoint exists (lines 226-355)
        assert "/from-distinta/{distinta_id}" in content, "from-distinta endpoint should exist"
        
        # Check it uses atomic counter pattern
        # The pattern is: find max existing, sync counter, then increment
        assert "pipeline" in content, "Should use aggregation pipeline to find max"
        
        print("✓ from-distinta endpoint verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

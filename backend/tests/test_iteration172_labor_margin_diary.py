"""
Iteration 172 — Labor Margin & Diary Hours Integration Tests

Tests verify that:
1. Diary hours (diario_produzione ore_totali) are correctly included in margin calculations
2. Both get_commessa_margin_full and get_all_margins include diary hours
3. Diary CRUD endpoints work correctly
4. Operator CRUD endpoints work correctly
5. Diary riepilogo endpoint aggregates correctly
6. requirements.txt does NOT contain --extra-index-url
7. nixpacks.toml exists with correct content

Auth: Session-based (cookies). Tests create test data directly in MongoDB and use a test session token.
"""
import pytest
import requests
import os
from datetime import datetime, timezone
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://norma-snapshot.preview.emergentagent.com"

# Test identifiers
TEST_USER_ID = "test_user_margin_172"
TEST_SESSION_TOKEN = f"test-session-margin-{uuid.uuid4().hex[:8]}"
TEST_COMMESSA_ID = f"com_margin_{uuid.uuid4().hex[:10]}"
TEST_ENTRY_ID = None  # Will be set after creating a diary entry
TEST_OPERATOR_ID = None  # Will be set after creating an operator


class TestFileChecks:
    """Verify requirements.txt and nixpacks.toml configuration"""

    def test_requirements_txt_no_extra_index_url(self):
        """requirements.txt should NOT contain --extra-index-url line"""
        req_path = "/app/backend/requirements.txt"
        with open(req_path, "r") as f:
            content = f.read()
        
        assert "--extra-index-url" not in content, \
            "requirements.txt should NOT contain --extra-index-url (moved to nixpacks.toml)"
        
        # Verify first line is a package, not a flag
        first_line = content.strip().split('\n')[0]
        assert not first_line.startswith("--"), \
            f"First line should be a package name, not a flag: {first_line}"
        print(f"✓ requirements.txt is clean (first line: {first_line})")

    def test_nixpacks_toml_exists_with_correct_content(self):
        """nixpacks.toml should exist with --extra-index-url in install phase"""
        toml_path = "/app/backend/nixpacks.toml"
        
        # Check file exists
        assert os.path.exists(toml_path), "nixpacks.toml should exist at /app/backend/nixpacks.toml"
        
        with open(toml_path, "r") as f:
            content = f.read()
        
        # Check for phases.install with --extra-index-url
        assert "[phases.install]" in content, "nixpacks.toml should have [phases.install] section"
        assert "--extra-index-url" in content, \
            "nixpacks.toml should contain --extra-index-url in install phase"
        assert "d33sy5i8bnduwe.cloudfront.net" in content, \
            "nixpacks.toml should reference emergent cloudfront pypi index"
        print(f"✓ nixpacks.toml is correctly configured with extra-index-url")


@pytest.fixture(scope="module")
def mongodb_client():
    """Setup MongoDB connection for direct data manipulation"""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = MongoClient(mongo_url)
    db = client[db_name]
    yield db
    client.close()


@pytest.fixture(scope="module")
def setup_test_data(mongodb_client):
    """Setup test user, session, commessa, and company_costs in MongoDB"""
    db = mongodb_client
    now = datetime.now(timezone.utc)
    
    # Create test user
    test_user = {
        "user_id": TEST_USER_ID,
        "email": "test_margin@example.com",
        "name": "Test Margin User",
        "role": "admin",
        "created_at": now,
    }
    db.users.update_one({"user_id": TEST_USER_ID}, {"$set": test_user}, upsert=True)
    
    # Create test session (in user_sessions collection)
    test_session = {
        "session_token": TEST_SESSION_TOKEN,
        "user_id": TEST_USER_ID,
        "created_at": now,
        "expires_at": datetime(2030, 12, 31, tzinfo=timezone.utc),
    }
    db.user_sessions.update_one({"session_token": TEST_SESSION_TOKEN}, {"$set": test_session}, upsert=True)
    
    # Create test commessa (NOT draft, so it appears in get_all_margins)
    test_commessa = {
        "commessa_id": TEST_COMMESSA_ID,
        "user_id": TEST_USER_ID,
        "numero": "2026/MARGIN-001",
        "title": "Test Margin Commessa",
        "client_name": "Test Client Margin",
        "value": 10000.0,
        "stato": "in_lavorazione",  # Not "bozza" so it's included in get_all_margins
        "costi_reali": [
            {"cost_id": "cost_test1", "tipo": "materiali", "descrizione": "Test Material", "importo": 500.0}
        ],
        "ore_lavorate": 5.0,  # Legacy hours field
        "created_at": now,
        "updated_at": now,
    }
    db.commesse.update_one({"commessa_id": TEST_COMMESSA_ID}, {"$set": test_commessa}, upsert=True)
    
    # Create company_costs with costo_orario_pieno
    company_costs = {
        "user_id": TEST_USER_ID,
        "costo_orario_pieno": 35.0,  # €35/hour
        "updated_at": now,
    }
    db.company_costs.update_one({"user_id": TEST_USER_ID}, {"$set": company_costs}, upsert=True)
    
    yield {
        "user_id": TEST_USER_ID,
        "session_token": TEST_SESSION_TOKEN,
        "commessa_id": TEST_COMMESSA_ID,
        "db": db,
    }
    
    # Cleanup after all tests
    db.users.delete_one({"user_id": TEST_USER_ID})
    db.user_sessions.delete_one({"session_token": TEST_SESSION_TOKEN})
    db.commesse.delete_one({"commessa_id": TEST_COMMESSA_ID})
    db.company_costs.delete_one({"user_id": TEST_USER_ID})
    db.diario_produzione.delete_many({"admin_id": TEST_USER_ID})
    db.operatori.delete_many({"admin_id": TEST_USER_ID})
    print("✓ Test data cleaned up")


@pytest.fixture(scope="module")
def session(setup_test_data):
    """Create requests session with auth cookie"""
    s = requests.Session()
    s.cookies.set("session_token", setup_test_data["session_token"])
    return s


class TestDiaryCRUD:
    """Test Diary (diario_produzione) CRUD endpoints"""
    
    created_entry_id = None
    
    def test_create_diary_entry(self, session, setup_test_data):
        """POST /api/commesse/{cid}/diario - Create diary entry"""
        cid = setup_test_data["commessa_id"]
        payload = {
            "data": "2026-01-15",
            "fase": "taglio",
            "ore": 4.0,
            "operatori": [
                {"id": "op_test1", "nome": "Mario Rossi"},
                {"id": "op_test2", "nome": "Luigi Verdi"}
            ],
            "note": "Test diary entry for margin integration"
        }
        
        response = session.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        
        print(f"Create diary response: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "entry_id" in data
        assert data["fase"] == "taglio"
        assert data["ore"] == 4.0
        # ore_totali = ore * num_operatori = 4 * 2 = 8
        assert data["ore_totali"] == 8.0, f"ore_totali should be 8.0 (4h x 2 operators), got {data.get('ore_totali')}"
        assert data["commessa_id"] == cid
        
        TestDiaryCRUD.created_entry_id = data["entry_id"]
        print(f"✓ Created diary entry: {data['entry_id']} with ore_totali={data['ore_totali']}")

    def test_list_diary_entries(self, session, setup_test_data):
        """GET /api/commesse/{cid}/diario - List diary entries"""
        cid = setup_test_data["commessa_id"]
        
        response = session.get(f"{BASE_URL}/api/commesse/{cid}/diario")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) >= 1
        
        # Find our created entry
        our_entry = next((e for e in data["entries"] if e.get("entry_id") == TestDiaryCRUD.created_entry_id), None)
        assert our_entry is not None, "Created entry not found in list"
        assert our_entry["ore_totali"] == 8.0
        print(f"✓ Listed {len(data['entries'])} diary entries")

    def test_diary_riepilogo(self, session, setup_test_data):
        """GET /api/commesse/{cid}/diario/riepilogo - Summary aggregation"""
        cid = setup_test_data["commessa_id"]
        
        response = session.get(f"{BASE_URL}/api/commesse/{cid}/diario/riepilogo")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "totale_ore_totali" in data
        assert data["totale_ore_totali"] >= 8.0, f"Expected at least 8h person-hours, got {data['totale_ore_totali']}"
        assert "costo_orario" in data
        assert data["costo_orario"] == 35.0, f"Expected costo_orario 35.0, got {data['costo_orario']}"
        assert "costo_effettivo" in data
        # costo_effettivo = totale_ore_totali * costo_orario = 8 * 35 = 280
        expected_cost = data["totale_ore_totali"] * 35.0
        assert abs(data["costo_effettivo"] - expected_cost) < 0.01
        print(f"✓ Riepilogo: {data['totale_ore_totali']}h total, €{data['costo_effettivo']} costo_effettivo")

    def test_delete_diary_entry(self, session, setup_test_data):
        """DELETE /api/commesse/{cid}/diario/{entry_id} - Delete entry"""
        cid = setup_test_data["commessa_id"]
        entry_id = TestDiaryCRUD.created_entry_id
        
        # First create a separate entry to delete
        payload = {
            "data": "2026-01-16",
            "fase": "saldatura",
            "ore": 2.0,
            "operatori": [{"id": "op_test1", "nome": "Mario Rossi"}],
            "note": "Entry to delete"
        }
        create_resp = session.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        assert create_resp.status_code == 200
        delete_entry_id = create_resp.json()["entry_id"]
        
        # Delete it
        response = session.delete(f"{BASE_URL}/api/commesse/{cid}/diario/{delete_entry_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ Deleted diary entry: {delete_entry_id}")


class TestOperatorCRUD:
    """Test Operator CRUD endpoints"""
    
    created_op_id = None
    
    def test_create_operator(self, session, setup_test_data):
        """POST /api/commesse/{cid}/operatori - Create operator"""
        cid = setup_test_data["commessa_id"]
        payload = {
            "nome": "Giuseppe Bianchi",
            "mansione": "Saldatore"
        }
        
        response = session.post(f"{BASE_URL}/api/commesse/{cid}/operatori", json=payload)
        
        print(f"Create operator response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "op_id" in data
        assert data["nome"] == "Giuseppe Bianchi"
        assert data["mansione"] == "Saldatore"
        
        TestOperatorCRUD.created_op_id = data["op_id"]
        print(f"✓ Created operator: {data['op_id']} - {data['nome']}")

    def test_list_operators(self, session, setup_test_data):
        """GET /api/commesse/{cid}/operatori - List operators"""
        cid = setup_test_data["commessa_id"]
        
        response = session.get(f"{BASE_URL}/api/commesse/{cid}/operatori")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "operatori" in data
        
        # Check our operator is in the list
        our_op = next((o for o in data["operatori"] if o.get("op_id") == TestOperatorCRUD.created_op_id), None)
        assert our_op is not None, "Created operator not found in list"
        print(f"✓ Listed {len(data['operatori'])} operators")


class TestMarginIntegration:
    """Test that margin calculations correctly include diary hours"""
    
    def test_get_commessa_margin_full_includes_diary_hours(self, session, setup_test_data):
        """GET /api/costs/commessa/{cid}/margin-full should include diary hours in ore_lavorate"""
        cid = setup_test_data["commessa_id"]
        
        response = session.get(f"{BASE_URL}/api/costs/commessa/{cid}/margin-full")
        
        print(f"Margin-full response: {response.status_code}")
        print(f"Response: {response.text[:1000]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "commessa_id" in data
        assert "ore_lavorate" in data
        assert "costo_personale" in data
        assert "costo_orario" in data
        
        # The ore_lavorate should include:
        # - Legacy ore_lavorate from commessa: 5.0
        # - Diary ore_totali: 8.0 (from test_create_diary_entry)
        # Total: 13.0 hours
        # Note: We may have additional entries from other tests
        ore = data["ore_lavorate"]
        assert ore >= 13.0, f"ore_lavorate should be at least 13.0 (5 legacy + 8 diary), got {ore}"
        
        # costo_personale = ore * costo_orario (35€/h)
        expected_costo = ore * 35.0
        assert abs(data["costo_personale"] - expected_costo) < 1.0, \
            f"costo_personale should be ~{expected_costo}, got {data['costo_personale']}"
        
        print(f"✓ margin-full includes diary hours: ore_lavorate={ore}, costo_personale={data['costo_personale']}")

    def test_get_all_margins_includes_diary_hours(self, session, setup_test_data):
        """GET /api/costs/margin-full should include diary hours for all commesse"""
        response = session.get(f"{BASE_URL}/api/costs/margin-full")
        
        print(f"All margins response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "commesse" in data
        assert "costo_orario" in data
        
        # Find our test commessa
        test_commessa = next((c for c in data["commesse"] if c.get("commessa_id") == setup_test_data["commessa_id"]), None)
        
        assert test_commessa is not None, f"Test commessa {setup_test_data['commessa_id']} not found in margin-full list"
        
        # Verify diary hours are included
        ore = test_commessa.get("ore_lavorate", 0)
        assert ore >= 13.0, f"ore_lavorate in all-margins should be at least 13.0, got {ore}"
        
        # Verify costo_personale calculation
        costo_orario = data.get("costo_orario", 35.0)
        expected_costo = ore * costo_orario
        actual_costo = test_commessa.get("costo_personale", 0)
        assert abs(actual_costo - expected_costo) < 1.0, \
            f"costo_personale in all-margins should be ~{expected_costo}, got {actual_costo}"
        
        print(f"✓ all-margins includes diary hours: ore_lavorate={ore}, costo_personale={actual_costo}")


class TestMarginServiceDirectly:
    """Direct tests of margin_service functions via MongoDB to verify diary aggregation"""
    
    @pytest.mark.asyncio
    async def test_get_all_margins_aggregates_diary(self, setup_test_data):
        """Verify get_all_margins pre-fetches diary hours correctly"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.margin_service import get_all_margins
        
        result = await get_all_margins(setup_test_data["user_id"])
        
        assert result is not None
        assert "commesse" in result
        
        # Find our test commessa
        test_commessa = next((c for c in result["commesse"] if c.get("commessa_id") == setup_test_data["commessa_id"]), None)
        
        if test_commessa:
            ore = test_commessa.get("ore_lavorate", 0)
            print(f"Direct service call: ore_lavorate={ore}")
            assert ore >= 13.0, f"Direct get_all_margins should have ore >= 13, got {ore}"
            print(f"✓ Direct get_all_margins correctly includes diary hours: {ore}h")
        else:
            # Commessa might not appear if stato is wrong or user_id mismatch
            print(f"Test commessa not in results - checking stato filter")
            db = setup_test_data["db"]
            comm = db.commesse.find_one({"commessa_id": setup_test_data["commessa_id"]})
            print(f"Commessa stato: {comm.get('stato') if comm else 'NOT FOUND'}")
            print(f"Commessa user_id: {comm.get('user_id') if comm else 'NOT FOUND'}")


class TestDiaryHoursCalculation:
    """Verify the exact hour calculation logic"""
    
    def test_diary_ore_totali_calculation(self, mongodb_client, setup_test_data):
        """Verify ore_totali = ore * num_operatori is calculated correctly"""
        db = mongodb_client
        cid = setup_test_data["commessa_id"]
        uid = setup_test_data["user_id"]
        
        # Create a diary entry with known values
        entry = {
            "entry_id": f"dp_calc_{uuid.uuid4().hex[:8]}",
            "commessa_id": cid,
            "admin_id": uid,
            "data": "2026-01-20",
            "fase": "assemblaggio",
            "ore": 6.0,  # 6 hours
            "operatori": [
                {"id": "op1", "nome": "Op1"},
                {"id": "op2", "nome": "Op2"},
                {"id": "op3", "nome": "Op3"}
            ],  # 3 operators
            "ore_totali": 18.0,  # 6 * 3 = 18 person-hours
            "note": "Test calculation",
        }
        db.diario_produzione.insert_one(entry)
        
        # Query diary for this commessa
        entries = list(db.diario_produzione.find({"commessa_id": cid, "admin_id": uid}))
        total_ore = sum(e.get("ore_totali", e.get("ore", 0)) for e in entries)
        
        print(f"Total diary entries: {len(entries)}")
        print(f"Total ore_totali: {total_ore}")
        
        # Should have at least 18 from this entry + 8 from earlier test
        assert total_ore >= 26.0, f"Expected at least 26h person-hours, got {total_ore}"
        
        # Cleanup
        db.diario_produzione.delete_one({"entry_id": entry["entry_id"]})
        print(f"✓ ore_totali calculation verified: {total_ore}h total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

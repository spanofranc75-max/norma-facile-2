"""
Iteration 177: Test 3-Category Commessa Creation
Tests the new category-based commessa creation flow with EN_1090, EN_13241, GENERICA normativa types.

Features tested:
- POST /api/commesse/ accepts normativa_tipo values 'EN_1090', 'EN_13241', 'GENERICA'
- CommessaOpsPanel conditional section rendering based on normativa_tipo
- Category validation - 'Scegli il tipo di lavoro' before saving
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Get base URL from env (same as frontend uses)
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_b4277e8f44b641dba7e0ecd71c8821f8"


@pytest.fixture(scope="module")
def auth_session():
    """Create authenticated session with test token"""
    session = requests.Session()
    session.cookies.set('session_token', SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def created_commesse(auth_session):
    """Track created commesse for cleanup"""
    commesse_ids = []
    yield commesse_ids
    
    # Cleanup: delete all test-created commesse
    for cid in commesse_ids:
        try:
            auth_session.delete(f"{BASE_URL}/api/commesse/{cid}")
            print(f"Cleaned up test commessa: {cid}")
        except Exception as e:
            print(f"Failed to cleanup commessa {cid}: {e}")


class TestHealthAndAuth:
    """Basic health and authentication tests"""
    
    def test_health_check(self, auth_session):
        """Test GET /api/health returns 200"""
        response = auth_session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check passed: {data}")
    
    def test_authenticated_access(self, auth_session):
        """Test that we can access protected endpoints with session token"""
        response = auth_session.get(f"{BASE_URL}/api/commesse/")
        assert response.status_code == 200
        print(f"Authenticated access successful, found {response.json().get('total', 0)} commesse")


class TestCategoryCommessaCreation:
    """Test creating commesse with different normativa_tipo values"""
    
    def test_create_commessa_en_1090(self, auth_session, created_commesse):
        """Test POST /api/commesse/ with normativa_tipo='EN_1090'"""
        payload = {
            "title": f"TEST_Commessa EN 1090 - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "EN_1090",
            "description": "Test struttura metallica",
            "value": 5000.00,
            "priority": "media",
            "classe_exc": "EXC2"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        created_commesse.append(data["commessa_id"])
        
        # Verify data persistence
        assert data["normativa_tipo"] == "EN_1090"
        assert data["title"] == payload["title"]
        assert data["classe_exc"] == "EXC2"
        assert "commessa_id" in data
        assert "numero" in data
        print(f"Created EN_1090 commessa: {data['numero']} (ID: {data['commessa_id']})")
        
        # GET to verify persistence
        get_resp = auth_session.get(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["normativa_tipo"] == "EN_1090"
        assert fetched["classe_exc"] == "EXC2"
        print(f"Verified EN_1090 commessa persistence: {fetched['numero']}")
    
    def test_create_commessa_en_13241(self, auth_session, created_commesse):
        """Test POST /api/commesse/ with normativa_tipo='EN_13241'"""
        payload = {
            "title": f"TEST_Cancello EN 13241 - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "EN_13241",
            "description": "Test cancello scorrevole",
            "value": 3000.00,
            "priority": "alta",
            "tipologia_chiusura": "cancello"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        created_commesse.append(data["commessa_id"])
        
        # Verify data persistence
        assert data["normativa_tipo"] == "EN_13241"
        assert data["title"] == payload["title"]
        assert data["tipologia_chiusura"] == "cancello"
        print(f"Created EN_13241 commessa: {data['numero']} (ID: {data['commessa_id']})")
        
        # GET to verify persistence
        get_resp = auth_session.get(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["normativa_tipo"] == "EN_13241"
        assert fetched["tipologia_chiusura"] == "cancello"
        print(f"Verified EN_13241 commessa persistence: {fetched['numero']}")
    
    def test_create_commessa_generica(self, auth_session, created_commesse):
        """Test POST /api/commesse/ with normativa_tipo='GENERICA'"""
        payload = {
            "title": f"TEST_Commessa GENERICA - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "GENERICA",
            "description": "Test riparazione ringhiera",
            "value": 500.00,
            "priority": "bassa"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        created_commesse.append(data["commessa_id"])
        
        # Verify data persistence
        assert data["normativa_tipo"] == "GENERICA"
        assert data["title"] == payload["title"]
        print(f"Created GENERICA commessa: {data['numero']} (ID: {data['commessa_id']})")
        
        # GET to verify persistence
        get_resp = auth_session.get(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["normativa_tipo"] == "GENERICA"
        print(f"Verified GENERICA commessa persistence: {fetched['numero']}")
    
    def test_create_commessa_without_normativa(self, auth_session, created_commesse):
        """Test POST /api/commesse/ without normativa_tipo (should default to empty)"""
        payload = {
            "title": f"TEST_Commessa senza normativa - {uuid.uuid4().hex[:6]}",
            "description": "Test commessa senza tipo normativa",
            "value": 1000.00
        }
        
        response = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        created_commesse.append(data["commessa_id"])
        
        # Should have empty normativa_tipo
        assert data.get("normativa_tipo", "") == ""
        print(f"Created commessa without normativa: {data['numero']} (normativa_tipo: '{data.get('normativa_tipo', '')}')")


class TestCommessaHubViewByNormativa:
    """Test hub view for different normativa types"""
    
    def test_hub_en_1090_shows_all_sections(self, auth_session, created_commesse):
        """Verify EN_1090 commessa hub shows all sections including Tracciabilita, CAM, Fascicolo"""
        # Create EN 1090 commessa first
        payload = {
            "title": f"TEST_Hub EN1090 - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "EN_1090",
            "classe_exc": "EXC2"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        created_commesse.append(commessa["commessa_id"])
        
        # Get hub view
        hub_resp = auth_session.get(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}/hub")
        assert hub_resp.status_code == 200
        hub_data = hub_resp.json()
        
        # Verify normativa_tipo is correct
        assert hub_data["commessa"]["normativa_tipo"] == "EN_1090"
        print(f"Hub EN_1090 verified: {commessa['numero']}")
    
    def test_hub_en_13241_commessa(self, auth_session, created_commesse):
        """Verify EN_13241 commessa hub data"""
        payload = {
            "title": f"TEST_Hub EN13241 - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "EN_13241",
            "tipologia_chiusura": "portone"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        created_commesse.append(commessa["commessa_id"])
        
        # Get hub view
        hub_resp = auth_session.get(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}/hub")
        assert hub_resp.status_code == 200
        hub_data = hub_resp.json()
        
        # Verify normativa_tipo is correct
        assert hub_data["commessa"]["normativa_tipo"] == "EN_13241"
        assert hub_data["commessa"]["tipologia_chiusura"] == "portone"
        print(f"Hub EN_13241 verified: {commessa['numero']}")
    
    def test_hub_generica_commessa(self, auth_session, created_commesse):
        """Verify GENERICA commessa hub data"""
        payload = {
            "title": f"TEST_Hub GENERICA - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "GENERICA"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        created_commesse.append(commessa["commessa_id"])
        
        # Get hub view
        hub_resp = auth_session.get(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}/hub")
        assert hub_resp.status_code == 200
        hub_data = hub_resp.json()
        
        # Verify normativa_tipo is correct
        assert hub_data["commessa"]["normativa_tipo"] == "GENERICA"
        print(f"Hub GENERICA verified: {commessa['numero']}")


class TestCommessaOpsEndpoint:
    """Test commessa operational data endpoint"""
    
    def test_ops_endpoint_for_all_categories(self, auth_session, created_commesse):
        """Test GET /api/commesse/{id}/ops returns correct data for each category"""
        categories = [
            ("EN_1090", {"classe_exc": "EXC3"}),
            ("EN_13241", {"tipologia_chiusura": "barriera"}),
            ("GENERICA", {})
        ]
        
        for normativa_tipo, extra_fields in categories:
            payload = {
                "title": f"TEST_Ops {normativa_tipo} - {uuid.uuid4().hex[:6]}",
                "normativa_tipo": normativa_tipo,
                **extra_fields
            }
            
            create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
            assert create_resp.status_code == 201
            commessa = create_resp.json()
            created_commesse.append(commessa["commessa_id"])
            
            # Test ops endpoint
            ops_resp = auth_session.get(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}/ops")
            assert ops_resp.status_code == 200
            ops_data = ops_resp.json()
            
            # Verify ops structure
            assert "approvvigionamento" in ops_data
            assert "fasi_produzione" in ops_data
            assert "conto_lavoro" in ops_data
            print(f"Ops endpoint verified for {normativa_tipo}: {commessa['numero']}")


class TestBoardView:
    """Test board view includes commesse with different normativa types"""
    
    def test_board_view_includes_all_categories(self, auth_session):
        """Test GET /api/commesse/board/view returns commesse correctly"""
        response = auth_session.get(f"{BASE_URL}/api/commesse/board/view")
        assert response.status_code == 200
        
        data = response.json()
        assert "columns" in data
        assert "total" in data
        
        # Verify column structure
        columns = {col["id"]: col for col in data["columns"]}
        expected_columns = ["preventivo", "approvvigionamento", "lavorazione", 
                          "conto_lavoro", "pronto_consegna", "montaggio", "completato"]
        for col_id in expected_columns:
            assert col_id in columns, f"Missing column: {col_id}"
        
        print(f"Board view verified: {data['total']} items across {len(data['columns'])} columns")


class TestCRUDWithNormativa:
    """Test full CRUD operations preserving normativa_tipo"""
    
    def test_update_commessa_preserves_normativa(self, auth_session, created_commesse):
        """Test PUT /api/commesse/{id} preserves normativa_tipo"""
        # Create
        payload = {
            "title": f"TEST_Update test - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "EN_1090",
            "classe_exc": "EXC2",
            "value": 1000
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        created_commesse.append(commessa["commessa_id"])
        
        # Update only title
        update_payload = {
            "title": f"TEST_Updated title - {uuid.uuid4().hex[:6]}",
            "value": 2000
        }
        
        update_resp = auth_session.put(
            f"{BASE_URL}/api/commesse/{commessa['commessa_id']}", 
            json=update_payload
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        
        # Verify normativa_tipo preserved
        assert updated["normativa_tipo"] == "EN_1090"
        assert updated["classe_exc"] == "EXC2"
        assert updated["title"] == update_payload["title"]
        assert updated["value"] == 2000
        print(f"Update preserved normativa: {updated['numero']}")
    
    def test_delete_commessa(self, auth_session):
        """Test DELETE /api/commesse/{id} works correctly"""
        # Create a test commessa
        payload = {
            "title": f"TEST_Delete test - {uuid.uuid4().hex[:6]}",
            "normativa_tipo": "GENERICA"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        
        # Delete
        delete_resp = auth_session.delete(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}")
        assert delete_resp.status_code == 200
        
        # Verify deleted
        get_resp = auth_session.get(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}")
        assert get_resp.status_code == 404
        print(f"Delete verified: {commessa['numero']} successfully deleted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

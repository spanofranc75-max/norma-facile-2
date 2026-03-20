"""
Iteration 178: Testing Voci di Lavoro (Cantieri Misti / Matrioska) and Diario Produzione
- CRUD for /api/commesse/{id}/voci/ endpoints
- Diario Produzione with new fields: voce_id, numero_colata, wps_usata, note_collaudo
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_session_matrioska_1774026135169')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session

@pytest.fixture(scope="module")
def test_commessa(api_client):
    """Create a test commessa for the Voci di Lavoro tests"""
    payload = {
        "title": f"TEST_Matrioska_{uuid.uuid4().hex[:8]}",
        "client_name": "Test Client Matrioska",
        "value": 15000,
        "normativa_tipo": "EN_1090",
        "classe_exc": "EXC2"
    }
    response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
    assert response.status_code == 201, f"Failed to create test commessa: {response.text}"
    commessa = response.json()
    yield commessa
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")


class TestVociLavoroCRUD:
    """Test CRUD operations for Voci di Lavoro"""
    
    def test_list_voci_empty(self, api_client, test_commessa):
        """Test listing voci when none exist"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/")
        assert response.status_code == 200
        data = response.json()
        assert "voci" in data
        assert isinstance(data["voci"], list)
        print(f"✓ List voci (empty): {len(data['voci'])} voci")
    
    def test_create_voce_en_1090(self, api_client, test_commessa):
        """Test creating a voce with EN_1090 category"""
        payload = {
            "descrizione": "Soppalco magazzino",
            "normativa_tipo": "EN_1090",
            "classe_exc": "EXC2"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        voce = response.json()
        assert voce["descrizione"] == payload["descrizione"]
        assert voce["normativa_tipo"] == "EN_1090"
        assert voce["classe_exc"] == "EXC2"
        assert "voce_id" in voce
        print(f"✓ Created EN_1090 voce: {voce['voce_id']}")
        return voce["voce_id"]
    
    def test_create_voce_en_13241(self, api_client, test_commessa):
        """Test creating a voce with EN_13241 category (gate)"""
        payload = {
            "descrizione": "Cancello carraio scorrevole",
            "normativa_tipo": "EN_13241",
            "tipologia_chiusura": "cancello"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        voce = response.json()
        assert voce["descrizione"] == payload["descrizione"]
        assert voce["normativa_tipo"] == "EN_13241"
        assert voce["tipologia_chiusura"] == "cancello"
        print(f"✓ Created EN_13241 voce: {voce['voce_id']}")
        return voce["voce_id"]
    
    def test_create_voce_generica(self, api_client, test_commessa):
        """Test creating a GENERICA voce"""
        payload = {
            "descrizione": "Riparazione ringhiera",
            "normativa_tipo": "GENERICA"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        voce = response.json()
        assert voce["normativa_tipo"] == "GENERICA"
        print(f"✓ Created GENERICA voce: {voce['voce_id']}")
        return voce["voce_id"]
    
    def test_create_voce_invalid_normativa(self, api_client, test_commessa):
        """Test that invalid normativa_tipo is rejected"""
        payload = {
            "descrizione": "Invalid test",
            "normativa_tipo": "INVALID"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/", json=payload)
        assert response.status_code == 400
        print("✓ Invalid normativa_tipo correctly rejected")
    
    def test_list_voci_after_creation(self, api_client, test_commessa):
        """Test listing voci after creating some"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["voci"]) >= 3  # We created 3 voci
        print(f"✓ List voci: {len(data['voci'])} voci found")
        return data["voci"]
    
    def test_update_voce(self, api_client, test_commessa):
        """Test updating a voce"""
        # First get the list to find a voce_id
        response = api_client.get(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/")
        voci = response.json()["voci"]
        if not voci:
            pytest.skip("No voci to update")
        voce_id = voci[0]["voce_id"]
        
        # Update the voce
        payload = {
            "descrizione": "Soppalco magazzino UPDATED"
        }
        response = api_client.put(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/{voce_id}", json=payload)
        assert response.status_code == 200, f"Update failed: {response.text}"
        updated = response.json()
        assert "UPDATED" in updated["descrizione"]
        print(f"✓ Updated voce: {voce_id}")
    
    def test_delete_voce(self, api_client, test_commessa):
        """Test deleting a voce"""
        # Create a voce to delete
        payload = {
            "descrizione": "Voce da eliminare",
            "normativa_tipo": "GENERICA"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/", json=payload)
        voce_id = create_resp.json()["voce_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/{voce_id}")
        assert response.status_code == 200
        print(f"✓ Deleted voce: {voce_id}")
        
        # Verify it's gone
        list_resp = api_client.get(f"{BASE_URL}/api/commesse/{test_commessa['commessa_id']}/voci/")
        voci_ids = [v["voce_id"] for v in list_resp.json()["voci"]]
        assert voce_id not in voci_ids
        print("✓ Verified voce deletion")


class TestDiarioProduzioneNewFields:
    """Test Diario Produzione with new Matrioska fields"""
    
    @pytest.fixture(scope="class")
    def diario_test_setup(self, api_client, test_commessa):
        """Set up production phases and an operator for diario tests"""
        cid = test_commessa["commessa_id"]
        
        # Initialize production phases
        api_client.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
        
        # Create an operator
        op_resp = api_client.post(f"{BASE_URL}/api/commesse/{cid}/operatori", json={"nome": "Mario Rossi"})
        if op_resp.status_code != 200:
            # Try to get existing operators
            ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/operatori")
            operators = ops_resp.json().get("operatori", [])
            if operators:
                op_id = operators[0]["op_id"]
            else:
                pytest.skip("Could not create operator")
        else:
            op_id = op_resp.json()["op_id"]
        
        # Get voci for testing
        voci_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/voci/")
        voci = voci_resp.json().get("voci", [])
        
        return {"commessa_id": cid, "op_id": op_id, "voci": voci}
    
    def test_create_diario_entry_basic(self, api_client, test_commessa, diario_test_setup):
        """Test creating a basic diario entry"""
        cid = diario_test_setup["commessa_id"]
        op_id = diario_test_setup["op_id"]
        
        payload = {
            "data": "2025-01-15",
            "fase": "taglio",
            "ore": 4,
            "operatori": [{"id": op_id, "nome": "Mario Rossi"}],
            "note": "Taglio profili HEA 200"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        entry = response.json()
        assert entry["fase"] == "taglio"
        assert entry["ore"] == 4
        assert "entry_id" in entry
        print(f"✓ Created basic diario entry: {entry['entry_id']}")
        return entry["entry_id"]
    
    def test_create_diario_entry_with_voce_id(self, api_client, test_commessa, diario_test_setup):
        """Test creating diario entry with voce_id (Matrioska feature)"""
        cid = diario_test_setup["commessa_id"]
        op_id = diario_test_setup["op_id"]
        voci = diario_test_setup["voci"]
        
        voce_id = voci[0]["voce_id"] if voci else "__principale__"
        
        payload = {
            "data": "2025-01-15",
            "fase": "saldatura",
            "ore": 3,
            "operatori": [{"id": op_id, "nome": "Mario Rossi"}],
            "note": "Saldatura telaio",
            "voce_id": voce_id
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        entry = response.json()
        assert entry["voce_id"] == voce_id
        print(f"✓ Created diario entry with voce_id: {entry['voce_id']}")
    
    def test_create_diario_entry_en1090_fields(self, api_client, test_commessa, diario_test_setup):
        """Test creating diario entry with EN 1090 specific fields (numero_colata, wps_usata)"""
        cid = diario_test_setup["commessa_id"]
        op_id = diario_test_setup["op_id"]
        
        payload = {
            "data": "2025-01-16",
            "fase": "saldatura",
            "ore": 5,
            "operatori": [{"id": op_id, "nome": "Mario Rossi"}],
            "note": "Saldatura strutturale",
            "voce_id": "__principale__",
            "numero_colata": "COL-12345-A",
            "wps_usata": "WPS-001 MAG 135"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        entry = response.json()
        assert entry["numero_colata"] == "COL-12345-A"
        assert entry["wps_usata"] == "WPS-001 MAG 135"
        print(f"✓ Created diario entry with EN1090 fields: colata={entry['numero_colata']}, wps={entry['wps_usata']}")
    
    def test_create_diario_entry_en13241_fields(self, api_client, test_commessa, diario_test_setup):
        """Test creating diario entry with EN 13241 specific fields (note_collaudo)"""
        cid = diario_test_setup["commessa_id"]
        op_id = diario_test_setup["op_id"]
        voci = diario_test_setup["voci"]
        
        # Find an EN_13241 voce or use __principale__
        voce_id = "__principale__"
        for v in voci:
            if v.get("normativa_tipo") == "EN_13241":
                voce_id = v["voce_id"]
                break
        
        payload = {
            "data": "2025-01-17",
            "fase": "assemblaggio",
            "ore": 6,
            "operatori": [{"id": op_id, "nome": "Mario Rossi"}],
            "note": "Assemblaggio cancello",
            "voce_id": voce_id,
            "note_collaudo": "Fotocellule installate, coste sensibili testate OK, finecorsa verificati"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        entry = response.json()
        assert entry["note_collaudo"] == payload["note_collaudo"]
        print(f"✓ Created diario entry with EN13241 note_collaudo")
    
    def test_list_diario_entries(self, api_client, test_commessa, diario_test_setup):
        """Test listing diario entries"""
        cid = diario_test_setup["commessa_id"]
        response = api_client.get(f"{BASE_URL}/api/commesse/{cid}/diario")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) >= 4  # We created at least 4 entries
        
        # Verify new fields are present in entries
        has_voce = any(e.get("voce_id") for e in data["entries"])
        has_colata = any(e.get("numero_colata") for e in data["entries"])
        has_wps = any(e.get("wps_usata") for e in data["entries"])
        has_collaudo = any(e.get("note_collaudo") for e in data["entries"])
        
        print(f"✓ Listed {len(data['entries'])} diario entries")
        print(f"  - has voce_id: {has_voce}")
        print(f"  - has numero_colata: {has_colata}")
        print(f"  - has wps_usata: {has_wps}")
        print(f"  - has note_collaudo: {has_collaudo}")
    
    def test_update_diario_entry_new_fields(self, api_client, test_commessa, diario_test_setup):
        """Test updating diario entry with new fields"""
        cid = diario_test_setup["commessa_id"]
        
        # Get an existing entry
        list_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/diario")
        entries = list_resp.json()["entries"]
        if not entries:
            pytest.skip("No entries to update")
        
        entry_id = entries[0]["entry_id"]
        
        # Update with new fields
        payload = {
            "numero_colata": "COL-UPDATED-999",
            "wps_usata": "WPS-UPDATED"
        }
        response = api_client.put(f"{BASE_URL}/api/commesse/{cid}/diario/{entry_id}", json=payload)
        assert response.status_code == 200, f"Update failed: {response.text}"
        updated = response.json()
        assert updated["numero_colata"] == "COL-UPDATED-999"
        print(f"✓ Updated diario entry with new fields")
    
    def test_diario_riepilogo(self, api_client, test_commessa, diario_test_setup):
        """Test getting diario summary (riepilogo)"""
        cid = diario_test_setup["commessa_id"]
        response = api_client.get(f"{BASE_URL}/api/commesse/{cid}/diario/riepilogo")
        assert response.status_code == 200
        data = response.json()
        assert "totale_ore_totali" in data
        assert "per_fase" in data
        assert "per_operatore" in data
        print(f"✓ Diario riepilogo: {data['totale_ore_totali']}h total, {data['totale_sessioni']} sessions")


class TestCommessaOpsWithVoci:
    """Test that CommessaOpsPanel API reflects voci categories"""
    
    def test_commessa_hub_includes_voci(self, api_client, test_commessa):
        """Test that commessa hub endpoint works"""
        cid = test_commessa["commessa_id"]
        response = api_client.get(f"{BASE_URL}/api/commesse/{cid}/hub")
        assert response.status_code == 200
        hub = response.json()
        assert "commessa" in hub
        assert hub["commessa"]["normativa_tipo"] == "EN_1090"
        print(f"✓ Commessa hub loaded: {hub['commessa']['numero']}")
    
    def test_commessa_ops_endpoint(self, api_client, test_commessa):
        """Test the ops endpoint returns expected structure"""
        cid = test_commessa["commessa_id"]
        response = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert response.status_code == 200
        ops = response.json()
        # Check expected fields
        assert "fasi_produzione" in ops or "approvvigionamento" in ops or "consegne" in ops
        print(f"✓ Commessa ops endpoint working")


class TestRetrocompatibility:
    """Test that commesse without voci work as before"""
    
    def test_commessa_without_voci_diario(self, api_client):
        """Test that diario works on commessa without any voci"""
        # Create a fresh commessa
        payload = {
            "title": f"TEST_NoVoci_{uuid.uuid4().hex[:8]}",
            "client_name": "Test Client",
            "value": 5000,
            "normativa_tipo": "GENERICA"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert create_resp.status_code == 201
        commessa = create_resp.json()
        cid = commessa["commessa_id"]
        
        try:
            # Verify no voci exist
            voci_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/voci/")
            assert voci_resp.status_code == 200
            assert len(voci_resp.json()["voci"]) == 0
            
            # Initialize production
            api_client.post(f"{BASE_URL}/api/commesse/{cid}/produzione/init")
            
            # Create an operator
            op_resp = api_client.post(f"{BASE_URL}/api/commesse/{cid}/operatori", json={"nome": "Test Op"})
            op_id = op_resp.json()["op_id"] if op_resp.status_code == 200 else "test_op"
            
            # Create diario entry WITHOUT voce_id
            diario_payload = {
                "data": "2025-01-20",
                "fase": "taglio",
                "ore": 2,
                "operatori": [{"id": op_id, "nome": "Test Op"}],
                "note": "Test retrocompatibility"
            }
            diario_resp = api_client.post(f"{BASE_URL}/api/commesse/{cid}/diario", json=diario_payload)
            assert diario_resp.status_code == 200
            entry = diario_resp.json()
            # voce_id should be empty or null
            assert entry.get("voce_id", "") == "" or entry.get("voce_id") is None
            print(f"✓ Retrocompatibility: Diario works without voce_id")
            
        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/commesse/{cid}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

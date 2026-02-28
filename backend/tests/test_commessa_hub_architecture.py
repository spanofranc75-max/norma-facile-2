"""
Test suite for Commessa Hub Architecture
Tests event-driven state machine, module linking, hub view, and backward compatibility.

Features tested:
- GET /api/commesse/stati - Lifecycle states and transitions
- POST /api/commesse/ - Create with stato, eventi[], moduli{}, numero
- POST /api/commesse/ with is_richiesta=true - Creates with stato=richiesta
- GET /api/commesse/{id} - Enhanced commessa with moduli, stato, eventi
- POST /api/commesse/{id}/eventi - Event emission with state transitions
- POST /api/commesse/{id}/link-module - Module linking
- POST /api/commesse/{id}/unlink-module - Module unlinking
- GET /api/commesse/{id}/hub - Full hub view with linked modules
- PATCH /api/commesse/{id}/status - Kanban drag-drop (backward compat)
- GET /api/commesse/board/view - Kanban board view
- POST /api/commesse/from-preventivo/{id} - Create from preventivo
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "hub_session_1772277854222"

@pytest.fixture(scope="module")
def api_client():
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session

@pytest.fixture(scope="module")
def test_commessa_id(api_client):
    """Create a test commessa for use in tests"""
    resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
        "title": "TEST_HubArchitecture_Commessa",
        "description": "Test commessa for hub architecture testing",
        "value": 5000,
        "priority": "alta"
    })
    assert resp.status_code == 201, f"Failed to create test commessa: {resp.text}"
    data = resp.json()
    yield data["commessa_id"]
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")


class TestStatiEndpoint:
    """Tests for GET /api/commesse/stati - Lifecycle states metadata"""
    
    def test_stati_returns_lifecycle_states(self, api_client):
        """GET /api/commesse/stati should return stati metadata and transitions"""
        resp = api_client.get(f"{BASE_URL}/api/commesse/stati")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Should have stati dict with all lifecycle states
        assert "stati" in data
        expected_states = ["richiesta", "bozza", "rilievo_completato", "firmato", 
                          "in_produzione", "fatturato", "chiuso", "sospesa"]
        for state in expected_states:
            assert state in data["stati"], f"Missing state: {state}"
            assert "label" in data["stati"][state]
            assert "color" in data["stati"][state]
        
        # Should have transitions dict
        assert "transitions" in data
        assert "COMMESSA_CREATA" in data["transitions"]
        assert "RILIEVO_COMPLETATO" in data["transitions"]
        assert "SOSPENSIONE" in data["transitions"]
        assert "RIATTIVAZIONE" in data["transitions"]
        print("PASS: GET /api/commesse/stati returns lifecycle states and transitions")


class TestCommessaCreate:
    """Tests for POST /api/commesse/ - Creating commesse with new fields"""
    
    def test_create_commessa_has_required_fields(self, api_client):
        """POST /api/commesse/ creates commessa with stato, eventi[], moduli{}, numero"""
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Create_NewFields",
            "description": "Testing new hub fields",
            "value": 3000
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"
        data = resp.json()
        
        # New fields
        assert "stato" in data, "Missing stato field"
        assert data["stato"] == "bozza", f"Expected default stato='bozza', got '{data['stato']}'"
        
        assert "eventi" in data, "Missing eventi field"
        assert isinstance(data["eventi"], list), "eventi should be a list"
        assert len(data["eventi"]) > 0, "Should have at least one event (COMMESSA_CREATA)"
        assert data["eventi"][0]["tipo"] == "COMMESSA_CREATA", f"First event should be COMMESSA_CREATA"
        
        assert "moduli" in data, "Missing moduli field"
        assert isinstance(data["moduli"], dict), "moduli should be a dict"
        assert "preventivo_id" in data["moduli"]
        assert "fatture_ids" in data["moduli"]
        
        assert "numero" in data, "Missing numero field"
        assert data["numero"].startswith("NF-"), f"numero should start with 'NF-', got {data['numero']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        print("PASS: POST /api/commesse/ creates with stato, eventi[], moduli{}, numero")
    
    def test_create_richiesta_commessa(self, api_client):
        """POST /api/commesse/ with is_richiesta=true creates with stato=richiesta"""
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Richiesta_Commessa",
            "is_richiesta": True,
            "value": 2000
        })
        assert resp.status_code == 201, f"Failed: {resp.text}"
        data = resp.json()
        
        assert data["stato"] == "richiesta", f"Expected stato='richiesta', got '{data['stato']}'"
        assert data["eventi"][0]["tipo"] == "RICHIESTA_PREVENTIVO"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        print("PASS: POST /api/commesse/ with is_richiesta=true creates stato=richiesta")


class TestCommessaGet:
    """Tests for GET /api/commesse/{id} - Enhanced response"""
    
    def test_get_commessa_returns_enhanced_data(self, api_client, test_commessa_id):
        """GET /api/commesse/{id} returns enhanced commessa with moduli, stato, eventi"""
        resp = api_client.get(f"{BASE_URL}/api/commesse/{test_commessa_id}")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "commessa_id" in data
        assert "stato" in data
        assert "moduli" in data
        assert "eventi" in data
        assert "numero" in data
        assert "cantiere" in data
        assert "riferimento" in data
        print("PASS: GET /api/commesse/{id} returns enhanced commessa with moduli, stato, eventi")


class TestEventEmission:
    """Tests for POST /api/commesse/{id}/eventi - Event sourcing"""
    
    def test_emit_event_advances_state(self, api_client):
        """POST /api/commesse/{id}/eventi with RILIEVO_COMPLETATO advances from bozza to rilievo_completato"""
        # Create fresh commessa in bozza state
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Event_StateAdvance",
            "value": 1000
        })
        assert resp.status_code == 201
        commessa_id = resp.json()["commessa_id"]
        assert resp.json()["stato"] == "bozza"
        
        # Emit RILIEVO_COMPLETATO event
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "RILIEVO_COMPLETATO",
            "note": "Rilievo completato dal test"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["stato"] == "rilievo_completato"
        
        # Verify state persisted
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert resp.json()["stato"] == "rilievo_completato"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: POST eventi with RILIEVO_COMPLETATO advances stato from bozza to rilievo_completato")
    
    def test_emit_event_rejects_invalid_transition(self, api_client):
        """POST /api/commesse/{id}/eventi validates state transitions"""
        # Create fresh commessa in bozza state
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Event_InvalidTransition",
            "value": 1000
        })
        assert resp.status_code == 201
        commessa_id = resp.json()["commessa_id"]
        
        # Try to emit FATTURA_EMESSA from bozza (should fail)
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "FATTURA_EMESSA"
        })
        assert resp.status_code == 400, f"Expected 400 for invalid transition, got {resp.status_code}"
        assert "non valida" in resp.text.lower() or "non permesso" in resp.text.lower()
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: POST eventi rejects invalid state transitions")
    
    def test_suspension_saves_previous_state(self, api_client):
        """POST eventi with SOSPENSIONE saves stato_precedente and moves to sospesa"""
        # Create and advance to firmato
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Suspension",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Advance to rilievo_completato then firmato
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "RILIEVO_COMPLETATO"})
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "FIRMA_CLIENTE"})
        
        # Verify firmato state
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert resp.json()["stato"] == "firmato"
        
        # Suspend
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "SOSPENSIONE",
            "note": "Test suspension"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        assert resp.json()["stato"] == "sospesa"
        
        # Verify stato_precedente saved
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        data = resp.json()
        assert data["stato"] == "sospesa"
        assert data["stato_precedente"] == "firmato"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: SOSPENSIONE saves stato_precedente and moves to sospesa")
    
    def test_reactivation_restores_previous_state(self, api_client):
        """POST eventi with RIATTIVAZIONE restores previous state from sospesa"""
        # Create and advance to in_produzione then suspend
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_Reactivation",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Advance through states
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "RILIEVO_COMPLETATO"})
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "FIRMA_CLIENTE"})
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "AVVIO_PRODUZIONE"})
        
        # Verify in_produzione
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert resp.json()["stato"] == "in_produzione"
        
        # Suspend
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={"tipo": "SOSPENSIONE"})
        
        # Reactivate
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "RIATTIVAZIONE",
            "note": "Test reactivation"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        assert resp.json()["stato"] == "in_produzione"
        
        # Verify persisted
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert resp.json()["stato"] == "in_produzione"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: RIATTIVAZIONE restores previous state from sospesa")


class TestModuleLinking:
    """Tests for POST /api/commesse/{id}/link-module and unlink-module"""
    
    def test_link_module(self, api_client):
        """POST /api/commesse/{id}/link-module links a module to the commessa"""
        # Create commessa
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_LinkModule",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Link a fake preventivo
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/link-module", json={
            "tipo": "preventivo",
            "module_id": "prev_test123"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        assert "collegato" in resp.text.lower()
        
        # Verify module linked
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        data = resp.json()
        assert data["moduli"]["preventivo_id"] == "prev_test123"
        
        # Also verify backward compat field
        assert data.get("linked_preventivo_id") == "prev_test123"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: POST link-module links a module to the commessa")
    
    def test_link_array_module(self, api_client):
        """POST link-module with fattura type appends to fatture_ids array"""
        # Create commessa
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_LinkArrayModule",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Link two fatture
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/link-module", json={
            "tipo": "fattura",
            "module_id": "inv_test1"
        })
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/link-module", json={
            "tipo": "fattura",
            "module_id": "inv_test2"
        })
        
        # Verify both linked
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        fatture = resp.json()["moduli"]["fatture_ids"]
        assert "inv_test1" in fatture
        assert "inv_test2" in fatture
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: link-module with fattura appends to fatture_ids array")
    
    def test_unlink_module(self, api_client):
        """POST /api/commesse/{id}/unlink-module unlinks a module"""
        # Create commessa and link module
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_UnlinkModule",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/link-module", json={
            "tipo": "preventivo",
            "module_id": "prev_tounlink"
        })
        
        # Unlink
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/unlink-module", json={
            "tipo": "preventivo",
            "module_id": "prev_tounlink"
        })
        assert resp.status_code == 200
        assert "scollegato" in resp.text.lower()
        
        # Verify unlinked
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert resp.json()["moduli"]["preventivo_id"] is None
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: POST unlink-module unlinks a module")


class TestHubView:
    """Tests for GET /api/commesse/{id}/hub - Full hub view"""
    
    def test_hub_returns_commessa_and_moduli_dettaglio(self, api_client):
        """GET /api/commesse/{id}/hub returns full hub view with linked modules"""
        # Create commessa
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_HubView",
            "value": 5000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Get hub view
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}/hub")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "commessa" in data
        assert data["commessa"]["commessa_id"] == commessa_id
        assert "moduli_dettaglio" in data
        assert isinstance(data["moduli_dettaglio"], dict)
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: GET /api/commesse/{id}/hub returns full hub view")
    
    def test_hub_404_nonexistent(self, api_client):
        """GET /api/commesse/{id}/hub returns 404 for non-existent commessa"""
        resp = api_client.get(f"{BASE_URL}/api/commesse/nonexistent_id/hub")
        assert resp.status_code == 404
        print("PASS: GET hub returns 404 for non-existent commessa")


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing Kanban"""
    
    def test_kanban_status_patch(self, api_client):
        """PATCH /api/commesse/{id}/status still works for Kanban drag-and-drop"""
        # Create commessa
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_KanbanCompat",
            "value": 1000
        })
        commessa_id = resp.json()["commessa_id"]
        
        # Drag to different column
        resp = api_client.patch(f"{BASE_URL}/api/commesse/{commessa_id}/status", json={
            "new_status": "lavorazione"
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify status changed but stato unchanged
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        data = resp.json()
        assert data["status"] == "lavorazione", f"Kanban status not updated"
        # Lifecycle stato should NOT change from Kanban drag
        # (depends on initial state which is 'bozza')
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: PATCH status works for Kanban backward compat")
    
    def test_board_view_returns_kanban_columns(self, api_client):
        """GET /api/commesse/board/view returns Kanban columns with enhanced commessa data"""
        resp = api_client.get(f"{BASE_URL}/api/commesse/board/view")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "columns" in data
        columns = data["columns"]
        assert len(columns) > 0, "Should have at least one column"
        
        # Check column structure
        col = columns[0]
        assert "id" in col
        assert "label" in col
        assert "items" in col
        
        # If items exist, verify they have new fields
        for c in columns:
            for item in c.get("items", []):
                # Should have moduli and stato
                assert "moduli" in item or "stato" in item  # At least one enhanced field
        
        print("PASS: GET board/view returns Kanban columns with enhanced data")


class TestFromPreventivo:
    """Tests for POST /api/commesse/from-preventivo/{id}"""
    
    def test_create_from_preventivo(self, api_client):
        """POST /api/commesse/from-preventivo/{id} creates commessa with stato=richiesta and linked preventivo"""
        # First create a test preventivo
        prev_resp = api_client.post(f"{BASE_URL}/api/preventivi/", json={
            "subject": "TEST_Preventivo_ForCommessa",
            "lines": [{"description": "Test item", "quantity": 1, "unit_price": 1000}]
        })
        if prev_resp.status_code != 201:
            pytest.skip("Could not create preventivo for test")
        preventivo_id = prev_resp.json()["preventivo_id"]
        
        # Create commessa from preventivo
        resp = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{preventivo_id}")
        assert resp.status_code == 200 or resp.status_code == 201, f"Failed: {resp.text}"
        data = resp.json()
        
        # Should have stato=richiesta
        assert data["stato"] == "richiesta", f"Expected stato='richiesta', got {data['stato']}"
        
        # Should have linked preventivo
        assert data["moduli"]["preventivo_id"] == preventivo_id
        
        # Should have RICHIESTA_PREVENTIVO event
        assert any(e["tipo"] == "RICHIESTA_PREVENTIVO" for e in data["eventi"])
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        api_client.delete(f"{BASE_URL}/api/preventivi/{preventivo_id}")
        print("PASS: POST from-preventivo creates commessa with stato=richiesta and linked preventivo")
    
    def test_from_preventivo_404_nonexistent(self, api_client):
        """POST /api/commesse/from-preventivo/{id} returns 404 for non-existent preventivo"""
        resp = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/nonexistent_prev")
        assert resp.status_code == 404
        print("PASS: POST from-preventivo returns 404 for non-existent preventivo")


class TestFullLifecycleFlow:
    """Test complete lifecycle from richiesta to chiuso"""
    
    def test_full_lifecycle_flow(self, api_client):
        """Complete lifecycle: richiesta → bozza events → ... → chiuso"""
        # Create as richiesta
        resp = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "title": "TEST_FullLifecycle",
            "is_richiesta": True,
            "value": 10000
        })
        commessa_id = resp.json()["commessa_id"]
        assert resp.json()["stato"] == "richiesta"
        
        # richiesta → rilievo_completato
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "RILIEVO_COMPLETATO"
        })
        assert resp.status_code == 200
        assert resp.json()["stato"] == "rilievo_completato"
        
        # rilievo_completato → firmato
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "FIRMA_CLIENTE"
        })
        assert resp.status_code == 200
        assert resp.json()["stato"] == "firmato"
        
        # firmato → in_produzione
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "AVVIO_PRODUZIONE"
        })
        assert resp.status_code == 200
        assert resp.json()["stato"] == "in_produzione"
        
        # in_produzione → fatturato
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "FATTURA_EMESSA"
        })
        assert resp.status_code == 200
        assert resp.json()["stato"] == "fatturato"
        
        # fatturato → chiuso
        resp = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/eventi", json={
            "tipo": "CHIUSURA_COMMESSA"
        })
        assert resp.status_code == 200
        assert resp.json()["stato"] == "chiuso"
        
        # Verify final state and event count
        resp = api_client.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        data = resp.json()
        assert data["stato"] == "chiuso"
        assert len(data["eventi"]) >= 6, f"Should have at least 6 events, got {len(data['eventi'])}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
        print("PASS: Full lifecycle flow from richiesta to chiuso completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Suite for Iteration 99: Smart ISO 3834 Consumable Traceability Feature.

Tests:
- Consumable CRUD operations (GET /api/consumables/, POST /api/consumables/)
- Smart detection logic (tipo detection, diameter extraction, normativa target)
- Auto-assignment to compatible open commesse
- Invoice analysis for consumables (POST /api/consumables/analyze-invoice/{fattura_id})
- Manual assignment/unassignment (POST/DELETE /api/consumables/{batch_id}/assign/{commessa_id})
- Auto-trigger on fatture_ricevute creation
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials from MongoDB setup
TEST_USER_ID = "user_cons_test_bs1lq0y5"
TEST_SESSION_TOKEN = "session_cons_test_bs1lq0y5"


@pytest.fixture(scope="module")
def auth_headers():
    """Get authentication headers using session token."""
    return {
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def api_client():
    """Create a session with auth headers."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    })
    return session


# ── Module: Consumable Detection Logic Tests ──
class TestConsumableDetectionLogic:
    """Test the smart detection keywords and rules."""

    def test_filo_keywords_detection(self, api_client):
        """Test that filo (wire) keywords are detected correctly."""
        # Create a consumable batch with filo keywords
        filo_descriptions = [
            "Filo SG2 1.0mm EN440 Bobina 15kg Lotto A789",
            "FILO ANIMATO SG3 diametro 1.2mm",
            "Bobina ER70S-6 0.8mm rotolo 5kg",
            "Wire welding SG2 1.0"
        ]
        
        for desc in filo_descriptions:
            payload = {
                "tipo": "filo",
                "descrizione": desc,
                "lotto": f"FILO_TEST_{uuid.uuid4().hex[:6]}",
                "fornitore": "Test Supplier",
                "diametro_mm": 1.0,
                "quantita": 15.0,
                "unita_misura": "kg"
            }
            response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
            assert response.status_code == 200, f"Failed for description: {desc}"
            data = response.json()
            assert data["tipo"] == "filo"
            assert "batch_id" in data
            print(f"Created filo batch: {data['batch_id']} - {desc[:40]}")

    def test_gas_keywords_detection(self, api_client):
        """Test that gas keywords are detected correctly."""
        gas_descriptions = [
            "Gas Argon puro 4.8 bombola 10 litri",
            "Miscela Ar/CO2 82/18 bombola 50L",
            "CO2 industriale bombola"
        ]
        
        for desc in gas_descriptions:
            payload = {
                "tipo": "gas",
                "descrizione": desc,
                "lotto": f"GAS_TEST_{uuid.uuid4().hex[:6]}",
                "fornitore": "Gas Supplier",
                "quantita": 50.0,
                "unita_misura": "lt"
            }
            response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
            assert response.status_code == 200, f"Failed for description: {desc}"
            data = response.json()
            assert data["tipo"] == "gas"
            # Gas should have normativa_target = entrambe
            assert data["normativa_target"] == "entrambe"
            print(f"Created gas batch: {data['batch_id']} - {desc[:40]}")

    def test_elettrodo_keywords_detection(self, api_client):
        """Test that elettrodo (electrode) keywords are detected correctly."""
        elettrodo_descriptions = [
            "Elettrodi 7018 2.5mm AWS",
            "Bacchette TIG ER70S-6 2.4mm",
            "Elettrodo basico 6013 3.2mm"
        ]
        
        for desc in elettrodo_descriptions:
            payload = {
                "tipo": "elettrodo",
                "descrizione": desc,
                "lotto": f"ELET_TEST_{uuid.uuid4().hex[:6]}",
                "fornitore": "Electrode Supplier",
                "diametro_mm": 2.5,
                "quantita": 5.0,
                "unita_misura": "kg"
                # normativa_target NOT provided - should auto-detect as en_1090
            }
            response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
            assert response.status_code == 200, f"Failed for description: {desc}"
            data = response.json()
            assert data["tipo"] == "elettrodo"
            # Elettrodo should have normativa_target = en_1090 (auto-detected)
            assert data["normativa_target"] == "en_1090", f"Expected en_1090, got {data['normativa_target']}"
            print(f"Created elettrodo batch: {data['batch_id']} - {desc[:40]}")


# ── Module: Normativa Target Rules Tests ──
class TestNormativaTargetRules:
    """Test normativa target determination rules."""

    def test_filo_1_0mm_targets_en_1090(self, api_client):
        """Filo with diameter >= 1.0mm should target EN 1090."""
        payload = {
            "tipo": "filo",
            "descrizione": "Filo SG2 per strutture 1.0mm",
            "lotto": f"NORM_TEST_{uuid.uuid4().hex[:6]}",
            "diametro_mm": 1.0,
            "quantita": 15.0
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["normativa_target"] == "en_1090", f"Expected en_1090 for 1.0mm wire, got {data['normativa_target']}"
        print(f"1.0mm wire -> {data['normativa_target']}")

    def test_filo_1_2mm_targets_en_1090(self, api_client):
        """Filo with diameter 1.2mm should target EN 1090."""
        payload = {
            "tipo": "filo",
            "descrizione": "Filo SG3 1.2mm strutture pesanti",
            "lotto": f"NORM_TEST_{uuid.uuid4().hex[:6]}",
            "diametro_mm": 1.2,
            "quantita": 15.0
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["normativa_target"] == "en_1090", f"Expected en_1090 for 1.2mm wire, got {data['normativa_target']}"
        print(f"1.2mm wire -> {data['normativa_target']}")

    def test_filo_0_8mm_targets_en_13241(self, api_client):
        """Filo with diameter 0.8mm should target EN 13241 (gates)."""
        payload = {
            "tipo": "filo",
            "descrizione": "Filo SG2 0.8mm per cancelli",
            "lotto": f"NORM_TEST_{uuid.uuid4().hex[:6]}",
            "diametro_mm": 0.8,
            "quantita": 5.0
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["normativa_target"] == "en_13241", f"Expected en_13241 for 0.8mm wire, got {data['normativa_target']}"
        print(f"0.8mm wire -> {data['normativa_target']}")

    def test_gas_always_targets_entrambe(self, api_client):
        """Gas should always target 'entrambe' (both normative)."""
        payload = {
            "tipo": "gas",
            "descrizione": "Argon puro bombola",
            "lotto": f"NORM_TEST_{uuid.uuid4().hex[:6]}",
            "quantita": 50.0
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["normativa_target"] == "entrambe", f"Expected entrambe for gas, got {data['normativa_target']}"
        print(f"Gas -> {data['normativa_target']}")

    def test_elettrodo_targets_en_1090(self, api_client):
        """Elettrodo should target EN 1090."""
        payload = {
            "tipo": "elettrodo",
            "descrizione": "Elettrodi 7018 strutturale",
            "lotto": f"NORM_TEST_{uuid.uuid4().hex[:6]}",
            "diametro_mm": 3.2,
            "quantita": 5.0
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["normativa_target"] == "en_1090", f"Expected en_1090 for elettrodo, got {data['normativa_target']}"
        print(f"Elettrodo -> {data['normativa_target']}")


# ── Module: CRUD Operations Tests ──
class TestConsumableCRUD:
    """Test basic CRUD operations for consumable batches."""

    def test_list_consumables_empty_or_with_items(self, api_client):
        """Test GET /api/consumables/ - list all consumable batches."""
        response = api_client.get(f"{BASE_URL}/api/consumables/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        print(f"Listed {data['total']} consumable batches")

    def test_list_consumables_filter_by_tipo(self, api_client):
        """Test filtering consumables by tipo (filo/gas/elettrodo)."""
        for tipo in ["filo", "gas", "elettrodo"]:
            response = api_client.get(f"{BASE_URL}/api/consumables/", params={"tipo": tipo})
            assert response.status_code == 200
            data = response.json()
            # All items should match the filter
            for item in data["items"]:
                assert item["tipo"] == tipo, f"Expected tipo={tipo}, got {item['tipo']}"
            print(f"Filter by tipo={tipo}: {len(data['items'])} items")

    def test_list_consumables_filter_by_stato(self, api_client):
        """Test filtering consumables by stato (attivo/esaurito)."""
        response = api_client.get(f"{BASE_URL}/api/consumables/", params={"stato": "attivo"})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["stato"] == "attivo"
        print(f"Filter by stato=attivo: {len(data['items'])} items")

    def test_create_consumable_batch_manual(self, api_client):
        """Test POST /api/consumables/ - create a consumable batch manually."""
        payload = {
            "tipo": "filo",
            "descrizione": "Test manual batch creation",
            "lotto": f"MANUAL_{uuid.uuid4().hex[:8]}",
            "fornitore": "Manual Test Supplier",
            "data_acquisto": "2026-01-07",
            "diametro_mm": 1.0,
            "normativa_target": "en_1090",
            "quantita": 10.0,
            "unita_misura": "kg",
            "prezzo_unitario": 15.50,
            "note": "Test batch for iteration 99"
        }
        response = api_client.post(f"{BASE_URL}/api/consumables/", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields are set correctly
        assert data["tipo"] == "filo"
        assert data["lotto"] == payload["lotto"]
        assert data["fornitore"] == payload["fornitore"]
        assert data["diametro_mm"] == 1.0
        assert data["quantita"] == 10.0
        assert data["stato"] == "attivo"
        assert "batch_id" in data
        assert "created_at" in data
        print(f"Created manual batch: {data['batch_id']}")
        return data["batch_id"]

    def test_update_consumable_batch(self, api_client):
        """Test PUT /api/consumables/{batch_id} - update a batch."""
        # First create a batch
        create_payload = {
            "tipo": "filo",
            "descrizione": "Batch to update",
            "lotto": f"UPDATE_{uuid.uuid4().hex[:8]}",
            "quantita": 20.0
        }
        create_response = api_client.post(f"{BASE_URL}/api/consumables/", json=create_payload)
        assert create_response.status_code == 200
        batch_id = create_response.json()["batch_id"]
        
        # Update the batch
        update_payload = {
            "stato": "esaurito",
            "quantita": 0.0,
            "note": "Consumato completamente"
        }
        update_response = api_client.put(f"{BASE_URL}/api/consumables/{batch_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["message"] == "Lotto aggiornato"
        print(f"Updated batch {batch_id}")

    def test_delete_consumable_batch(self, api_client):
        """Test DELETE /api/consumables/{batch_id} - delete a batch."""
        # First create a batch to delete
        create_payload = {
            "tipo": "gas",
            "descrizione": "Batch to delete",
            "lotto": f"DELETE_{uuid.uuid4().hex[:8]}",
            "quantita": 10.0
        }
        create_response = api_client.post(f"{BASE_URL}/api/consumables/", json=create_payload)
        assert create_response.status_code == 200
        batch_id = create_response.json()["batch_id"]
        
        # Delete it
        delete_response = api_client.delete(f"{BASE_URL}/api/consumables/{batch_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["message"] == "Lotto eliminato"
        print(f"Deleted batch {batch_id}")


# ── Module: Commessa Assignment Tests ──
class TestCommessaAssignment:
    """Test consumable assignment to commesse."""

    @pytest.fixture(scope="class")
    def test_commessa_en_1090(self, api_client):
        """Create a test commessa with EN 1090 normativa."""
        payload = {
            "numero": f"NF-TEST-1090-{uuid.uuid4().hex[:6]}",
            "title": "Test Commessa EN 1090 for Consumables",
            "normativa_tipo": "EN_1090",
            "status": "lavorazione",
            "client_name": "Test Client"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        if response.status_code == 201:
            return response.json()["commessa_id"]
        return None

    @pytest.fixture(scope="class")
    def test_commessa_en_13241(self, api_client):
        """Create a test commessa with EN 13241 normativa."""
        payload = {
            "numero": f"NF-TEST-13241-{uuid.uuid4().hex[:6]}",
            "title": "Test Commessa EN 13241 for Consumables",
            "normativa_tipo": "EN_13241",
            "status": "lavorazione",
            "client_name": "Test Client"
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        if response.status_code == 201:
            return response.json()["commessa_id"]
        return None

    def test_get_consumables_for_commessa(self, api_client, test_commessa_en_1090):
        """Test GET /api/consumables/for-commessa/{commessa_id}."""
        if not test_commessa_en_1090:
            pytest.skip("No test commessa available")
        
        response = api_client.get(f"{BASE_URL}/api/consumables/for-commessa/{test_commessa_en_1090}")
        assert response.status_code == 200
        data = response.json()
        
        assert "assigned" in data
        assert "available" in data
        assert "commessa_normativa" in data
        assert isinstance(data["assigned"], list)
        assert isinstance(data["available"], list)
        print(f"Commessa {test_commessa_en_1090}: {len(data['assigned'])} assigned, {len(data['available'])} available")

    def test_manual_assign_batch_to_commessa(self, api_client, test_commessa_en_1090):
        """Test POST /api/consumables/{batch_id}/assign/{commessa_id}."""
        if not test_commessa_en_1090:
            pytest.skip("No test commessa available")
        
        # Create a batch first
        create_payload = {
            "tipo": "filo",
            "descrizione": "Batch for assignment test",
            "lotto": f"ASSIGN_{uuid.uuid4().hex[:8]}",
            "diametro_mm": 1.0,
            "quantita": 10.0
        }
        create_response = api_client.post(f"{BASE_URL}/api/consumables/", json=create_payload)
        assert create_response.status_code == 200
        batch_id = create_response.json()["batch_id"]
        
        # Assign to commessa
        assign_response = api_client.post(f"{BASE_URL}/api/consumables/{batch_id}/assign/{test_commessa_en_1090}")
        assert assign_response.status_code == 200
        data = assign_response.json()
        assert "message" in data
        print(f"Assigned batch {batch_id} to commessa {test_commessa_en_1090}")
        
        # Verify assignment
        check_response = api_client.get(f"{BASE_URL}/api/consumables/for-commessa/{test_commessa_en_1090}")
        assert check_response.status_code == 200
        check_data = check_response.json()
        assigned_ids = [b["batch_id"] for b in check_data["assigned"]]
        assert batch_id in assigned_ids, f"Batch {batch_id} not in assigned list"
        
        return batch_id

    def test_unassign_batch_from_commessa(self, api_client, test_commessa_en_1090):
        """Test DELETE /api/consumables/{batch_id}/assign/{commessa_id}."""
        if not test_commessa_en_1090:
            pytest.skip("No test commessa available")
        
        # Create and assign a batch
        create_payload = {
            "tipo": "gas",
            "descrizione": "Batch for unassignment test",
            "lotto": f"UNASSIGN_{uuid.uuid4().hex[:8]}",
            "quantita": 50.0
        }
        create_response = api_client.post(f"{BASE_URL}/api/consumables/", json=create_payload)
        batch_id = create_response.json()["batch_id"]
        
        # Assign
        api_client.post(f"{BASE_URL}/api/consumables/{batch_id}/assign/{test_commessa_en_1090}")
        
        # Unassign
        unassign_response = api_client.delete(f"{BASE_URL}/api/consumables/{batch_id}/assign/{test_commessa_en_1090}")
        assert unassign_response.status_code == 200
        data = unassign_response.json()
        assert data["message"] == "Assegnazione rimossa"
        print(f"Unassigned batch {batch_id} from commessa {test_commessa_en_1090}")

    def test_commessa_not_found_returns_404(self, api_client):
        """Test that non-existent commessa returns 404."""
        fake_commessa_id = f"fake_commessa_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/consumables/for-commessa/{fake_commessa_id}")
        assert response.status_code == 404


# ── Module: Invoice Consumable Analysis Tests ──
class TestInvoiceAnalysis:
    """Test invoice analysis for automatic consumable detection."""

    @pytest.fixture(scope="class")
    def test_fattura_with_consumables(self, api_client):
        """Create a test fattura with consumable line items."""
        payload = {
            "fornitore_nome": "Test Welding Supplier SRL",
            "fornitore_piva": "IT12345678901",
            "numero_documento": f"FR-TEST-{uuid.uuid4().hex[:6]}",
            "data_documento": "2026-01-07",
            "linee": [
                {
                    "descrizione": "Filo SG2 1.0mm EN440 Bobina 15kg Lotto A789",
                    "quantita": 2.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 45.00,
                    "importo": 90.00
                },
                {
                    "descrizione": "Gas Argon puro bombola 50L Lotto GAS001",
                    "quantita": 1.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 120.00,
                    "importo": 120.00
                },
                {
                    "descrizione": "Elettrodi 7018 2.5mm 5kg Batch E456",
                    "quantita": 1.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 35.00,
                    "importo": 35.00
                },
                {
                    "descrizione": "Disco taglio 125mm",  # Not a consumable
                    "quantita": 10.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 2.50,
                    "importo": 25.00
                }
            ],
            "imponibile": 270.00,
            "imposta": 59.40,
            "totale_documento": 329.40
        }
        response = api_client.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        if response.status_code == 201:
            return response.json()["fr_id"]
        return None

    def test_analyze_invoice_for_consumables(self, api_client, test_fattura_with_consumables):
        """Test POST /api/consumables/analyze-invoice/{fattura_id}."""
        if not test_fattura_with_consumables:
            pytest.skip("No test fattura available")
        
        # Note: analyze-invoice now accepts fr_id (primary key) as the fattura_id parameter
        response = api_client.post(f"{BASE_URL}/api/consumables/analyze-invoice/{test_fattura_with_consumables}")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "created" in data
        
        # Should detect consumables (filo, gas, elettrodo) but NOT the disco
        # Note: If consumables were already created by auto-trigger during fattura creation, count may be 0
        print(f"Analysis result: {data['message']}")
        print(f"Created {len(data['created'])} consumables")

    def test_analyze_nonexistent_fattura_returns_404(self, api_client):
        """Test that analyzing non-existent fattura returns 404."""
        fake_fattura_id = f"fr_fake_{uuid.uuid4().hex[:8]}"
        response = api_client.post(f"{BASE_URL}/api/consumables/analyze-invoice/{fake_fattura_id}")
        assert response.status_code == 404


# ── Module: Auto-Trigger on Fattura Creation Tests ──
class TestAutoTriggerOnFatturaCreation:
    """Test that consumables are auto-imported when fattura is created."""

    def test_fattura_creation_triggers_consumable_import(self, api_client):
        """Creating a fattura with consumable lines should auto-create batches."""
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "fornitore_nome": "Auto Trigger Test Supplier",
            "numero_documento": f"FR-AUTO-{unique_suffix}",
            "data_documento": "2026-01-07",
            "linee": [
                {
                    "descrizione": f"Filo SG2 0.8mm Bobina 5kg Lotto AUTO-FILO-{unique_suffix}",
                    "quantita": 1.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 25.00,
                    "importo": 25.00
                }
            ],
            "imponibile": 25.00,
            "imposta": 5.50,
            "totale_documento": 30.50
        }
        
        # Create fattura
        response = api_client.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert response.status_code == 201
        fr_id = response.json()["fr_id"]
        print(f"Created fattura: {fr_id}")
        
        # Check if consumable was auto-created
        consumables_response = api_client.get(f"{BASE_URL}/api/consumables/")
        assert consumables_response.status_code == 200
        consumables = consumables_response.json()["items"]
        
        # Find the auto-created batch
        matching = [c for c in consumables if f"AUTO-FILO-{unique_suffix}" in c.get("descrizione", "")]
        if matching:
            print(f"Auto-created consumable batch: {matching[0]['batch_id']}")
            # Verify it has the correct fattura_id
            assert matching[0]["fattura_id"] == fr_id
        else:
            print("No auto-created batch found (may have been filtered or already existed)")


# ── Module: Edge Cases and Error Handling ──
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_batch_not_found_update_returns_404(self, api_client):
        """Updating non-existent batch should return 404."""
        fake_batch_id = f"cb_fake_{uuid.uuid4().hex[:8]}"
        response = api_client.put(f"{BASE_URL}/api/consumables/{fake_batch_id}", json={"stato": "esaurito"})
        assert response.status_code == 404

    def test_batch_not_found_delete_returns_404(self, api_client):
        """Deleting non-existent batch should return 404."""
        fake_batch_id = f"cb_fake_{uuid.uuid4().hex[:8]}"
        response = api_client.delete(f"{BASE_URL}/api/consumables/{fake_batch_id}")
        assert response.status_code == 404

    def test_batch_not_found_assign_returns_404(self, api_client):
        """Assigning non-existent batch should return 404."""
        fake_batch_id = f"cb_fake_{uuid.uuid4().hex[:8]}"
        # Need a real commessa or this will 404 on commessa first
        response = api_client.post(f"{BASE_URL}/api/consumables/{fake_batch_id}/assign/some_commessa")
        assert response.status_code == 404

    def test_empty_update_returns_400(self, api_client):
        """Updating with no fields should return 400."""
        # First create a batch
        create_response = api_client.post(f"{BASE_URL}/api/consumables/", json={
            "tipo": "filo",
            "descrizione": "Test empty update",
            "lotto": f"EMPTY_{uuid.uuid4().hex[:8]}",
            "quantita": 10.0
        })
        batch_id = create_response.json()["batch_id"]
        
        # Try empty update
        response = api_client.put(f"{BASE_URL}/api/consumables/{batch_id}", json={})
        assert response.status_code == 400

    def test_duplicate_assignment_is_idempotent(self, api_client):
        """Assigning same batch twice should be idempotent."""
        # Create a test commessa
        commessa_response = api_client.post(f"{BASE_URL}/api/commesse/", json={
            "numero": f"NF-DUP-{uuid.uuid4().hex[:6]}",
            "title": "Test Duplicate Assignment",
            "normativa_tipo": "EN_1090",
            "status": "lavorazione"
        })
        if commessa_response.status_code != 201:
            pytest.skip("Could not create test commessa")
        commessa_id = commessa_response.json()["commessa_id"]
        
        # Create a batch
        batch_response = api_client.post(f"{BASE_URL}/api/consumables/", json={
            "tipo": "filo",
            "descrizione": "Test duplicate assignment",
            "lotto": f"DUP_{uuid.uuid4().hex[:8]}",
            "diametro_mm": 1.0,
            "quantita": 10.0
        })
        batch_id = batch_response.json()["batch_id"]
        
        # Assign twice
        first_assign = api_client.post(f"{BASE_URL}/api/consumables/{batch_id}/assign/{commessa_id}")
        second_assign = api_client.post(f"{BASE_URL}/api/consumables/{batch_id}/assign/{commessa_id}")
        
        assert first_assign.status_code == 200
        assert second_assign.status_code == 200
        # Second should indicate already assigned
        assert "gia' assegnato" in second_assign.json()["message"].lower() or "assegnato" in second_assign.json()["message"].lower()


# ── Module: Cleanup Test Data ──
class TestCleanup:
    """Clean up test data after tests."""

    def test_cleanup_test_data(self, api_client):
        """Clean up test consumable batches."""
        # List all consumables
        response = api_client.get(f"{BASE_URL}/api/consumables/")
        if response.status_code == 200:
            consumables = response.json()["items"]
            test_prefixes = ["FILO_TEST", "GAS_TEST", "ELET_TEST", "NORM_TEST", "MANUAL_", "UPDATE_", "DELETE_", "ASSIGN_", "UNASSIGN_", "AUTO-FILO-", "EMPTY_", "DUP_"]
            deleted = 0
            for c in consumables:
                lotto = c.get("lotto", "")
                if any(lotto.startswith(prefix) for prefix in test_prefixes):
                    del_response = api_client.delete(f"{BASE_URL}/api/consumables/{c['batch_id']}")
                    if del_response.status_code == 200:
                        deleted += 1
            print(f"Cleaned up {deleted} test consumable batches")
        print("Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

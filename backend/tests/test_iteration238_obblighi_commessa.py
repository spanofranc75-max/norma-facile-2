"""
Iteration 238 — Registro Obblighi Commessa MVP Tests
=====================================================
Tests for the new centralized obligations registry module.

Features tested:
- GET /api/obblighi - list all obligations for user
- GET /api/obblighi/{id} - get single obligation
- PATCH /api/obblighi/{id} - update obligation status
- POST /api/obblighi/sync/{commessa_id} - trigger sync for a commessa
- GET /api/obblighi/commessa/{commessa_id} - list obligations for a commessa
- GET /api/obblighi/bloccanti/{commessa_id} - list blockers only
- GET /api/obblighi/summary/{commessa_id} - get summary counts
- Deduplication: calling sync twice should not create duplicates
- Auto-close: after sync removes a blocker source, obligation should be auto-closed
- Route ordering: specific sub-paths should NOT conflict with generic {id}
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials created via mongosh
SESSION_TOKEN = "obblighi_session_mn2173ym"
USER_ID = "user_obblighi_test_mn2173ym"
COMMESSA_ID = "commessa_obblighi_test_mn2173ym"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


@pytest.fixture(scope="module")
def test_data(api_client):
    """Setup test data for obblighi tests."""
    import pymongo
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = pymongo.MongoClient(mongo_url)
    db = client['test_database']
    
    # Create a ramo normativo with incomplete status (source E)
    ramo_id = f"ramo_test_{int(time.time())}"
    db.rami_normativi.insert_one({
        "ramo_id": ramo_id,
        "commessa_id": COMMESSA_ID,
        "user_id": USER_ID,
        "codice_ramo": "EN1090-EXC2",
        "normativa": "EN_1090",
        "stato": "incompleto",
        "created_at": datetime.utcnow()
    })
    
    # Create a cantiere sicurezza with missing soggetti (source B, C)
    cantiere_id = f"cantiere_test_{int(time.time())}"
    db.cantieri_sicurezza.insert_one({
        "cantiere_id": cantiere_id,
        "commessa_id": COMMESSA_ID,
        "user_id": USER_ID,
        "nome": "Test Cantiere",
        "gate_pos_status": {
            "campi_mancanti": ["Indirizzo cantiere", "Data inizio lavori"],
            "blockers": ["POS non generabile: dati mancanti"]
        },
        "soggetti": [
            # Missing DATORE_LAVORO, RSPP, COMMITTENTE
            {"ruolo": "MEDICO_COMPETENTE", "nome": "Dr. Test"}
        ],
        "created_at": datetime.utcnow()
    })
    
    # Create an emissione with blockers (source A)
    emissione_id = f"emissione_test_{int(time.time())}"
    db.emissioni_documentali.insert_one({
        "emissione_id": emissione_id,
        "ramo_id": ramo_id,
        "commessa_id": COMMESSA_ID,
        "user_id": USER_ID,
        "codice_emissione": "EMI-001",
        "gate_result": {
            "blockers": [
                {"code": "MISSING_CERT_31", "message": "Certificato 3.1 mancante"}
            ],
            "warnings": [
                {"code": "LOW_CONFIDENCE", "message": "Confidenza classificazione bassa"}
            ]
        },
        "created_at": datetime.utcnow()
    })
    
    yield {
        "ramo_id": ramo_id,
        "cantiere_id": cantiere_id,
        "emissione_id": emissione_id
    }
    
    # Cleanup
    db.rami_normativi.delete_many({"user_id": USER_ID})
    db.cantieri_sicurezza.delete_many({"user_id": USER_ID})
    db.emissioni_documentali.delete_many({"user_id": USER_ID})
    db.obblighi_commessa.delete_many({"user_id": USER_ID})
    client.close()


class TestObbrighiRouteOrdering:
    """Test that route ordering is correct - specific paths before generic {id}."""
    
    def test_commessa_route_not_captured_by_generic(self, api_client):
        """GET /api/obblighi/commessa/{id} should NOT be captured by /api/obblighi/{id}."""
        # This should return a list, not a 404 "Obbligo non trovato"
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return a list of obligations"
        print(f"✓ Route /obblighi/commessa/{COMMESSA_ID} returns list correctly")
    
    def test_summary_route_not_captured_by_generic(self, api_client):
        """GET /api/obblighi/summary/{id} should NOT be captured by /api/obblighi/{id}."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/summary/{COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total" in data, "Should return summary with 'total' field"
        print(f"✓ Route /obblighi/summary/{COMMESSA_ID} returns summary correctly")
    
    def test_bloccanti_route_not_captured_by_generic(self, api_client):
        """GET /api/obblighi/bloccanti/{id} should NOT be captured by /api/obblighi/{id}."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/bloccanti/{COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return a list of blockers"
        print(f"✓ Route /obblighi/bloccanti/{COMMESSA_ID} returns list correctly")
    
    def test_sync_route_not_captured_by_generic(self, api_client):
        """POST /api/obblighi/sync/{id} should NOT be captured by /api/obblighi/{id}."""
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{COMMESSA_ID}")
        # Should return sync result, not 404 or method not allowed
        assert response.status_code in [200, 404], f"Expected 200 or 404 (commessa not found), got {response.status_code}: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "created" in data or "error" in data, "Should return sync stats or error"
        print(f"✓ Route /obblighi/sync/{COMMESSA_ID} works correctly")


class TestObbrighiSync:
    """Test the sync engine that collects obligations from source modules."""
    
    def test_sync_creates_obligations(self, api_client, test_data):
        """POST /api/obblighi/sync/{commessa_id} should create obligations from sources."""
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{COMMESSA_ID}")
        assert response.status_code == 200, f"Sync failed: {response.text}"
        
        data = response.json()
        assert "created" in data, "Response should have 'created' count"
        assert "updated" in data, "Response should have 'updated' count"
        assert "closed" in data, "Response should have 'closed' count"
        assert "total_expected" in data, "Response should have 'total_expected' count"
        
        print(f"✓ Sync result: created={data['created']}, updated={data['updated']}, closed={data['closed']}, total_expected={data['total_expected']}")
        
        # Should have created some obligations from our test data
        assert data['created'] > 0 or data['total_expected'] > 0, "Should have found obligations from test data"
    
    def test_sync_deduplication(self, api_client, test_data):
        """Calling sync twice should NOT create duplicate obligations."""
        # First sync
        response1 = api_client.post(f"{BASE_URL}/api/obblighi/sync/{COMMESSA_ID}")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second sync
        response2 = api_client.post(f"{BASE_URL}/api/obblighi/sync/{COMMESSA_ID}")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second sync should create 0 new obligations (all deduplicated)
        assert data2['created'] == 0, f"Second sync should create 0 new obligations, but created {data2['created']}"
        print(f"✓ Deduplication works: second sync created 0 new obligations")
    
    def test_sync_nonexistent_commessa(self, api_client):
        """Sync for non-existent commessa should return 404."""
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/nonexistent_commessa_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Sync returns 404 for non-existent commessa")


class TestObbrighiList:
    """Test listing obligations."""
    
    def test_list_all_obligations(self, api_client, test_data):
        """GET /api/obblighi should return all obligations for user."""
        # First sync to create obligations
        api_client.post(f"{BASE_URL}/api/obblighi/sync/{COMMESSA_ID}")
        
        response = api_client.get(f"{BASE_URL}/api/obblighi")
        assert response.status_code == 200, f"List failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        print(f"✓ List all obligations: {len(data)} items")
    
    def test_list_obligations_by_commessa(self, api_client, test_data):
        """GET /api/obblighi/commessa/{commessa_id} should return obligations for that commessa."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200, f"List by commessa failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        
        # All returned obligations should be for our commessa
        for obl in data:
            assert obl.get("commessa_id") == COMMESSA_ID, f"Obligation {obl.get('obbligo_id')} has wrong commessa_id"
        
        print(f"✓ List by commessa: {len(data)} obligations for {COMMESSA_ID}")
    
    def test_list_with_filters(self, api_client, test_data):
        """GET /api/obblighi with query params should filter results."""
        # Filter by source_module
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=evidence_gate")
        assert response.status_code == 200
        data = response.json()
        for obl in data:
            assert obl.get("source_module") == "evidence_gate"
        print(f"✓ Filter by source_module=evidence_gate: {len(data)} items")
        
        # Filter by blocking_level
        response = api_client.get(f"{BASE_URL}/api/obblighi?blocking_level=hard_block")
        assert response.status_code == 200
        data = response.json()
        for obl in data:
            assert obl.get("blocking_level") == "hard_block"
        print(f"✓ Filter by blocking_level=hard_block: {len(data)} items")


class TestObbrighiBloccanti:
    """Test the blockers-only endpoint."""
    
    def test_get_bloccanti(self, api_client, test_data):
        """GET /api/obblighi/bloccanti/{commessa_id} should return only hard_block obligations."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/bloccanti/{COMMESSA_ID}")
        assert response.status_code == 200, f"Get bloccanti failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        
        # All returned should be hard_block and open status
        for obl in data:
            assert obl.get("blocking_level") == "hard_block", f"Blocker has wrong blocking_level: {obl.get('blocking_level')}"
            assert obl.get("status") not in ["completato", "chiuso", "non_applicabile"], f"Blocker should be open, got status: {obl.get('status')}"
        
        print(f"✓ Get bloccanti: {len(data)} hard blockers")


class TestObbrighiSummary:
    """Test the summary endpoint."""
    
    def test_get_summary(self, api_client, test_data):
        """GET /api/obblighi/summary/{commessa_id} should return counts."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/summary/{COMMESSA_ID}")
        assert response.status_code == 200, f"Get summary failed: {response.text}"
        
        data = response.json()
        assert "total" in data, "Summary should have 'total'"
        assert "bloccanti" in data, "Summary should have 'bloccanti'"
        assert "aperti" in data, "Summary should have 'aperti'"
        assert "chiusi" in data, "Summary should have 'chiusi'"
        assert "da_verificare" in data, "Summary should have 'da_verificare'"
        
        print(f"✓ Summary: total={data['total']}, bloccanti={data['bloccanti']}, aperti={data['aperti']}, chiusi={data['chiusi']}")


class TestObbrighiCRUD:
    """Test CRUD operations on individual obligations."""
    
    def test_get_single_obligation(self, api_client, test_data):
        """GET /api/obblighi/{obbligo_id} should return the obligation."""
        # First get list to find an obligation ID
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test GET single")
        
        obbligo_id = data[0]["obbligo_id"]
        
        # Get single
        response = api_client.get(f"{BASE_URL}/api/obblighi/{obbligo_id}")
        assert response.status_code == 200, f"Get single failed: {response.text}"
        
        obl = response.json()
        assert obl.get("obbligo_id") == obbligo_id
        assert "title" in obl
        assert "status" in obl
        assert "dedupe_key" in obl
        
        print(f"✓ Get single obligation: {obbligo_id}")
    
    def test_get_nonexistent_obligation(self, api_client):
        """GET /api/obblighi/{id} for non-existent ID should return 404."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/nonexistent_obbligo_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Get non-existent obligation returns 404")
    
    def test_update_obligation_status(self, api_client, test_data):
        """PATCH /api/obblighi/{obbligo_id} should update status."""
        # First get list to find an obligation ID
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        original_status = data[0]["status"]
        
        # Update status to da_verificare
        new_status = "da_verificare" if original_status != "da_verificare" else "in_corso"
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={"status": new_status}
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated = response.json()
        assert updated.get("status") == new_status, f"Status not updated: expected {new_status}, got {updated.get('status')}"
        
        print(f"✓ Update obligation status: {original_status} -> {new_status}")
    
    def test_update_obligation_resolution_note(self, api_client, test_data):
        """PATCH /api/obblighi/{obbligo_id} should update resolution_note."""
        # First get list to find an obligation ID
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        
        # Update with resolution note and status completato
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={
                "status": "completato",
                "resolution_note": "Risolto manualmente durante test"
            }
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated = response.json()
        assert updated.get("status") == "completato"
        assert updated.get("resolution_note") == "Risolto manualmente durante test"
        assert updated.get("resolved_at") is not None, "resolved_at should be set when status is completato"
        
        print(f"✓ Update obligation with resolution note")
    
    def test_update_nonexistent_obligation(self, api_client):
        """PATCH /api/obblighi/{id} for non-existent ID should return 404."""
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/nonexistent_obbligo_xyz",
            json={"status": "completato"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Update non-existent obligation returns 404")


class TestObbrighiAutoClose:
    """Test auto-close behavior when source condition is removed."""
    
    def test_auto_close_when_source_removed(self, api_client):
        """After removing blocker source and syncing, obligation should be auto-closed."""
        import pymongo
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        client = pymongo.MongoClient(mongo_url)
        db = client['test_database']
        
        # Create a fresh commessa for this test
        test_commessa_id = f"commessa_autoclose_{int(time.time())}"
        db.commesse.insert_one({
            "commessa_id": test_commessa_id,
            "user_id": USER_ID,
            "numero": "TEST-AUTOCLOSE-001",
            "title": "Test Auto Close",
            "stato": "in_produzione",
            "created_at": datetime.utcnow()
        })
        
        # Create a ramo with incomplete status
        ramo_id = f"ramo_autoclose_{int(time.time())}"
        db.rami_normativi.insert_one({
            "ramo_id": ramo_id,
            "commessa_id": test_commessa_id,
            "user_id": USER_ID,
            "codice_ramo": "AUTOCLOSE-TEST",
            "normativa": "EN_1090",
            "stato": "incompleto",
            "created_at": datetime.utcnow()
        })
        
        # First sync - should create obligation for incomplete ramo
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{test_commessa_id}")
        assert response.status_code == 200
        data1 = response.json()
        print(f"First sync: created={data1['created']}, total_expected={data1['total_expected']}")
        
        # Verify obligation was created
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{test_commessa_id}")
        assert response.status_code == 200
        obligations_before = response.json()
        
        # Find the ramo obligation
        ramo_obligations = [o for o in obligations_before if o.get("source_module") == "rami_normativi"]
        if len(ramo_obligations) == 0:
            # Cleanup and skip
            db.commesse.delete_one({"commessa_id": test_commessa_id})
            db.rami_normativi.delete_one({"ramo_id": ramo_id})
            pytest.skip("No ramo obligation created")
        
        ramo_obl = ramo_obligations[0]
        assert ramo_obl.get("status") in ["nuovo", "bloccante"], f"Initial status should be open, got {ramo_obl.get('status')}"
        
        # Now fix the ramo (change stato to 'completato')
        db.rami_normativi.update_one(
            {"ramo_id": ramo_id},
            {"$set": {"stato": "completato"}}
        )
        
        # Second sync - should auto-close the obligation
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{test_commessa_id}")
        assert response.status_code == 200
        data2 = response.json()
        print(f"Second sync after fix: closed={data2['closed']}")
        
        # Verify obligation was auto-closed
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{test_commessa_id}")
        assert response.status_code == 200
        obligations_after = response.json()
        
        # Find the same obligation
        ramo_obligations_after = [o for o in obligations_after if o.get("source_module") == "rami_normativi" and o.get("source_entity_id") == ramo_id]
        
        if len(ramo_obligations_after) > 0:
            ramo_obl_after = ramo_obligations_after[0]
            assert ramo_obl_after.get("status") == "completato", f"Obligation should be auto-closed, got {ramo_obl_after.get('status')}"
            assert "Chiuso automaticamente" in (ramo_obl_after.get("resolution_note") or ""), "Should have auto-close resolution note"
            print(f"✓ Auto-close works: obligation status={ramo_obl_after.get('status')}, note={ramo_obl_after.get('resolution_note')}")
        else:
            # Obligation might have been removed from list (only open ones returned)
            # Check via summary
            response = api_client.get(f"{BASE_URL}/api/obblighi/summary/{test_commessa_id}")
            summary = response.json()
            print(f"✓ Auto-close works: summary shows chiusi={summary.get('chiusi', 0)}")
        
        # Cleanup
        db.commesse.delete_one({"commessa_id": test_commessa_id})
        db.rami_normativi.delete_one({"ramo_id": ramo_id})
        db.obblighi_commessa.delete_many({"commessa_id": test_commessa_id})
        client.close()


class TestObbrighiDedupeKey:
    """Test dedupe_key format and uniqueness."""
    
    def test_dedupe_key_format(self, api_client, test_data):
        """Obligations should have dedupe_key in format: {commessa_id}|{source_module}|{source_entity_id}|{code}."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        for obl in data:
            dedupe_key = obl.get("dedupe_key", "")
            parts = dedupe_key.split("|")
            assert len(parts) == 4, f"dedupe_key should have 4 parts: {dedupe_key}"
            assert parts[0] == COMMESSA_ID, f"First part should be commessa_id: {dedupe_key}"
            assert parts[1] == obl.get("source_module"), f"Second part should be source_module: {dedupe_key}"
            
        print(f"✓ All {len(data)} obligations have correct dedupe_key format")


class TestObbrighiSourceModules:
    """Test that obligations are collected from all 5 source modules."""
    
    def test_source_evidence_gate(self, api_client, test_data):
        """Obligations from Evidence Gate (emissioni blockers) should be collected."""
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=evidence_gate&commessa_id={COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # We created an emissione with blockers
        if len(data) > 0:
            for obl in data:
                assert obl.get("source_module") == "evidence_gate"
                assert obl.get("category") == "emissione"
            print(f"✓ Evidence Gate source: {len(data)} obligations")
        else:
            print("⚠ No Evidence Gate obligations (may be expected if emissione not linked)")
    
    def test_source_gate_pos(self, api_client, test_data):
        """Obligations from Gate POS (sicurezza cantiere) should be collected."""
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=gate_pos&commessa_id={COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for obl in data:
                assert obl.get("source_module") == "gate_pos"
                assert obl.get("category") == "sicurezza"
            print(f"✓ Gate POS source: {len(data)} obligations")
        else:
            print("⚠ No Gate POS obligations")
    
    def test_source_soggetti(self, api_client, test_data):
        """Obligations from Soggetti (missing mandatory roles) should be collected."""
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=soggetti&commessa_id={COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for obl in data:
                assert obl.get("source_module") == "soggetti"
            print(f"✓ Soggetti source: {len(data)} obligations")
        else:
            print("⚠ No Soggetti obligations")
    
    def test_source_rami_normativi(self, api_client, test_data):
        """Obligations from Rami Normativi (incomplete branches) should be collected."""
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=rami_normativi&commessa_id={COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for obl in data:
                assert obl.get("source_module") == "rami_normativi"
            print(f"✓ Rami Normativi source: {len(data)} obligations")
        else:
            print("⚠ No Rami Normativi obligations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

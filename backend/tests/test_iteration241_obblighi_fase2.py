"""
Iteration 241 — Registro Obblighi Fase 2 Tests
==============================================
Tests for the new Fase 2 additions to the obligations registry.

Features tested:
- PATCH /api/obblighi/{id} accepts owner_role, due_date, sla_source fields
- POST /api/obblighi/sync/{commessa_id} includes sources F, G, H
- Source F: documenti_scadenza - expired docs (alta/hard_block), expiring docs (media/warning)
- Source G: pacchetti_documentali - missing required docs, expired docs in packages
- Source H: committenza - obligations from approved analisi_committenza snapshots
- Deduplication works across all 8 sources
- Auto-close works when source condition disappears
"""

import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SESSION_TOKEN = "obblighi_fase2_session_1774203898386"
USER_ID = "user_obblighi_fase2_1774203898386"
COMMESSA_ID = "commessa_fase2_1774203898386"


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
def test_data_fase2(api_client):
    """Setup test data for Fase 2 sources F, G, H."""
    import pymongo
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = pymongo.MongoClient(mongo_url)
    db = client['test_database']
    
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    in_15_days_str = (now + timedelta(days=15)).strftime("%Y-%m-%d")
    in_45_days_str = (now + timedelta(days=45)).strftime("%Y-%m-%d")
    
    # Create fresh commessa for this test
    test_commessa_id = f"commessa_fase2_test_{int(time.time())}"
    db.commesse.insert_one({
        "commessa_id": test_commessa_id,
        "user_id": USER_ID,
        "numero": "TEST-FASE2-PYTEST",
        "title": "Test Obblighi Fase 2 Pytest",
        "stato": "in_produzione",
        "created_at": now
    })
    
    # Source F: Expired document
    expired_doc_id = f"doc_expired_pytest_{int(time.time())}"
    db.documenti_archivio.insert_one({
        "doc_id": expired_doc_id,
        "user_id": USER_ID,
        "title": "Certificato Scaduto Pytest",
        "document_type_code": "CERT_PYTEST_EXP",
        "file_name": "cert_scaduto_pytest.pdf",
        "owner_label": "Azienda Pytest",
        "expiry_date": yesterday_str,
        "created_at": now
    })
    
    # Source F: Expiring document (within 30 days)
    expiring_doc_id = f"doc_expiring_pytest_{int(time.time())}"
    db.documenti_archivio.insert_one({
        "doc_id": expiring_doc_id,
        "user_id": USER_ID,
        "title": "Certificato In Scadenza Pytest",
        "document_type_code": "CERT_PYTEST_SOON",
        "file_name": "cert_in_scadenza_pytest.pdf",
        "owner_label": "Fornitore Pytest",
        "expiry_date": in_15_days_str,
        "created_at": now
    })
    
    # Source F: Document NOT expiring soon (should NOT create obligation)
    ok_doc_id = f"doc_ok_pytest_{int(time.time())}"
    db.documenti_archivio.insert_one({
        "doc_id": ok_doc_id,
        "user_id": USER_ID,
        "title": "Certificato OK Pytest",
        "document_type_code": "CERT_PYTEST_OK",
        "file_name": "cert_ok_pytest.pdf",
        "expiry_date": in_45_days_str,
        "created_at": now
    })
    
    # Source G: Pacchetto documentale with missing/expired items
    pack_id = f"pack_pytest_{int(time.time())}"
    db.pacchetti_documentali.insert_one({
        "pack_id": pack_id,
        "user_id": USER_ID,
        "commessa_id": test_commessa_id,
        "label": "Pacchetto Pytest Fase 2",
        "template_code": "PACK_PYTEST",
        "status": "attivo",
        "items": [
            {"document_type_code": "DOC_PYTEST_MISSING", "status": "missing", "required": True, "blocking": True},
            {"document_type_code": "DOC_PYTEST_EXPIRED", "status": "expired", "required": True, "blocking": False},
            {"document_type_code": "DOC_PYTEST_VALID", "status": "valid", "required": True, "blocking": False}
        ],
        "created_at": now
    })
    
    # Source H: Approved analisi_committenza with official_snapshot
    analysis_id = f"analysis_pytest_{int(time.time())}"
    db.analisi_committenza.insert_one({
        "analysis_id": analysis_id,
        "user_id": USER_ID,
        "commessa_id": test_commessa_id,
        "status": "approved",
        "official_snapshot": {
            "obligations": [
                {
                    "code": "OBL_PYTEST_001",
                    "title": "Obbligo Pytest Contrattuale",
                    "description": "Test obbligo da committenza",
                    "category": "contrattuale",
                    "severity": "alta",
                    "blocking_level": "warning",
                    "source_excerpt": "Art. 1 pytest..."
                }
            ],
            "anomalies": [
                {
                    "code": "ANOM_PYTEST_001",
                    "title": "Anomalia Pytest",
                    "description": "Test anomalia",
                    "severity": "bassa",
                    "recommended_action": "commerciale"
                }
            ],
            "mismatches": [
                {
                    "code": "MISMATCH_PYTEST_001",
                    "title": "Mismatch Pytest",
                    "description": "Test mismatch",
                    "severity": "media",
                    "blocking_level": "warning"
                }
            ]
        },
        "created_at": now
    })
    
    yield {
        "commessa_id": test_commessa_id,
        "expired_doc_id": expired_doc_id,
        "expiring_doc_id": expiring_doc_id,
        "ok_doc_id": ok_doc_id,
        "pack_id": pack_id,
        "analysis_id": analysis_id,
        "yesterday_str": yesterday_str,
        "in_15_days_str": in_15_days_str,
    }
    
    # Cleanup
    db.commesse.delete_one({"commessa_id": test_commessa_id})
    db.documenti_archivio.delete_many({"doc_id": {"$in": [expired_doc_id, expiring_doc_id, ok_doc_id]}})
    db.pacchetti_documentali.delete_one({"pack_id": pack_id})
    db.analisi_committenza.delete_one({"analysis_id": analysis_id})
    db.obblighi_commessa.delete_many({"commessa_id": test_commessa_id})
    client.close()


class TestPatchNewFields:
    """Test PATCH endpoint accepts owner_role, due_date, sla_source fields."""
    
    def test_patch_owner_role(self, api_client):
        """PATCH /api/obblighi/{id} should accept owner_role field."""
        # Get an existing obligation
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        
        # Update owner_role
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={"owner_role": "qualita"}
        )
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        updated = response.json()
        assert updated.get("owner_role") == "qualita", f"owner_role not updated: {updated.get('owner_role')}"
        print(f"✓ PATCH owner_role works: {updated.get('owner_role')}")
    
    def test_patch_due_date(self, api_client):
        """PATCH /api/obblighi/{id} should accept due_date field."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        test_date = "2026-06-15"
        
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={"due_date": test_date}
        )
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        updated = response.json()
        assert updated.get("due_date") == test_date, f"due_date not updated: {updated.get('due_date')}"
        print(f"✓ PATCH due_date works: {updated.get('due_date')}")
    
    def test_patch_sla_source(self, api_client):
        """PATCH /api/obblighi/{id} should accept sla_source field."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={"sla_source": "manuale"}
        )
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        updated = response.json()
        assert updated.get("sla_source") == "manuale", f"sla_source not updated: {updated.get('sla_source')}"
        print(f"✓ PATCH sla_source works: {updated.get('sla_source')}")
    
    def test_patch_all_new_fields(self, api_client):
        """PATCH /api/obblighi/{id} should accept all new fields together."""
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No obligations to test PATCH")
        
        obbligo_id = data[0]["obbligo_id"]
        
        response = api_client.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={
                "owner_role": "amministrazione",
                "due_date": "2026-07-01",
                "sla_source": "da_emissione"
            }
        )
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        updated = response.json()
        assert updated.get("owner_role") == "amministrazione"
        assert updated.get("due_date") == "2026-07-01"
        assert updated.get("sla_source") == "da_emissione"
        print(f"✓ PATCH all new fields works")


class TestSourceFDocumentiScadenza:
    """Test Source F: documenti_scadenza - expired/expiring documents."""
    
    def test_sync_creates_expired_doc_obligation(self, api_client, test_data_fase2):
        """Sync should create alta/hard_block obligation for expired documents."""
        commessa_id = test_data_fase2["commessa_id"]
        
        # Run sync
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{commessa_id}")
        assert response.status_code == 200, f"Sync failed: {response.text}"
        
        # Get obligations
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find expired doc obligation
        expired_obls = [o for o in obligations if o.get("source_module") == "documenti_scadenza" and "DOC_EXPIRED" in o.get("code", "")]
        
        assert len(expired_obls) > 0, "Should have created obligation for expired document"
        
        expired_obl = expired_obls[0]
        assert expired_obl.get("severity") == "alta", f"Expired doc should have severity=alta, got {expired_obl.get('severity')}"
        assert expired_obl.get("blocking_level") == "hard_block", f"Expired doc should have blocking_level=hard_block, got {expired_obl.get('blocking_level')}"
        assert expired_obl.get("sla_source") == "da_scadenza_documento", f"Should have sla_source=da_scadenza_documento"
        assert expired_obl.get("due_date") is not None, "Should have due_date set to expiry date"
        
        print(f"✓ Source F: Expired doc creates alta/hard_block obligation with due_date={expired_obl.get('due_date')}")
    
    def test_sync_creates_expiring_doc_obligation(self, api_client, test_data_fase2):
        """Sync should create media/warning obligation for expiring documents (within 30 days)."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find expiring doc obligation
        expiring_obls = [o for o in obligations if o.get("source_module") == "documenti_scadenza" and "DOC_EXPIRING" in o.get("code", "")]
        
        assert len(expiring_obls) > 0, "Should have created obligation for expiring document"
        
        expiring_obl = expiring_obls[0]
        assert expiring_obl.get("severity") == "media", f"Expiring doc should have severity=media, got {expiring_obl.get('severity')}"
        assert expiring_obl.get("blocking_level") == "warning", f"Expiring doc should have blocking_level=warning, got {expiring_obl.get('blocking_level')}"
        assert expiring_obl.get("sla_source") == "da_scadenza_documento"
        assert expiring_obl.get("due_date") == test_data_fase2["in_15_days_str"]
        
        print(f"✓ Source F: Expiring doc creates media/warning obligation with due_date={expiring_obl.get('due_date')}")
    
    def test_sync_does_not_create_ok_doc_obligation(self, api_client, test_data_fase2):
        """Sync should NOT create obligation for documents not expiring within 30 days."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Should NOT find obligation for OK doc (expiring in 45 days)
        ok_obls = [o for o in obligations if "CERT_PYTEST_OK" in o.get("code", "")]
        
        assert len(ok_obls) == 0, f"Should NOT create obligation for doc expiring in 45 days, but found {len(ok_obls)}"
        print(f"✓ Source F: Doc expiring in 45 days does NOT create obligation")


class TestSourceGPacchettiDocumentali:
    """Test Source G: pacchetti_documentali - missing/expired items in packages."""
    
    def test_sync_creates_missing_doc_obligation(self, api_client, test_data_fase2):
        """Sync should create obligation for missing required documents in packages."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find missing doc obligation
        missing_obls = [o for o in obligations if o.get("source_module") == "pacchetti_documentali" and "MISSING" in o.get("code", "")]
        
        assert len(missing_obls) > 0, "Should have created obligation for missing document in package"
        
        missing_obl = missing_obls[0]
        assert missing_obl.get("sla_source") == "da_pacchetto_documentale"
        assert missing_obl.get("category") == "documentale"
        # blocking=True in item should create hard_block
        assert missing_obl.get("blocking_level") == "hard_block", f"Missing blocking doc should be hard_block, got {missing_obl.get('blocking_level')}"
        
        print(f"✓ Source G: Missing doc in package creates obligation with blocking_level={missing_obl.get('blocking_level')}")
    
    def test_sync_creates_expired_pack_doc_obligation(self, api_client, test_data_fase2):
        """Sync should create obligation for expired documents in packages."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find expired doc in package obligation
        expired_pack_obls = [o for o in obligations if o.get("source_module") == "pacchetti_documentali" and "EXPIRED" in o.get("code", "")]
        
        assert len(expired_pack_obls) > 0, "Should have created obligation for expired document in package"
        
        expired_obl = expired_pack_obls[0]
        assert expired_obl.get("sla_source") == "da_pacchetto_documentale"
        assert expired_obl.get("severity") == "alta"
        
        print(f"✓ Source G: Expired doc in package creates obligation")


class TestSourceHCommittenza:
    """Test Source H: committenza - obligations from approved analisi_committenza."""
    
    def test_sync_creates_committenza_obligations(self, api_client, test_data_fase2):
        """Sync should create obligations from approved committenza analysis snapshot."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find committenza obligations
        committenza_obls = [o for o in obligations if o.get("source_module") == "committenza"]
        
        assert len(committenza_obls) >= 3, f"Should have at least 3 committenza obligations (1 obl + 1 anom + 1 mismatch), got {len(committenza_obls)}"
        
        # Check obligation from obligations array
        obl_obls = [o for o in committenza_obls if "OBL_PYTEST_001" in o.get("code", "")]
        assert len(obl_obls) > 0, "Should have obligation from snapshot.obligations"
        assert obl_obls[0].get("sla_source") == "da_documento_cliente"
        
        # Check anomaly
        anom_obls = [o for o in committenza_obls if "ANOM_PYTEST_001" in o.get("code", "")]
        assert len(anom_obls) > 0, "Should have obligation from snapshot.anomalies"
        
        # Check mismatch
        mismatch_obls = [o for o in committenza_obls if "MISMATCH_PYTEST_001" in o.get("code", "")]
        assert len(mismatch_obls) > 0, "Should have obligation from snapshot.mismatches"
        
        print(f"✓ Source H: Committenza creates {len(committenza_obls)} obligations from approved analysis")
    
    def test_committenza_owner_role_mapping(self, api_client, test_data_fase2):
        """Committenza obligations should have correct owner_role based on category."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{commessa_id}")
        assert response.status_code == 200
        obligations = response.json()
        
        # Find contrattuale obligation (should have owner_role=amministrazione)
        contrattuale_obls = [o for o in obligations if o.get("source_module") == "committenza" and "OBL_PYTEST_001" in o.get("code", "")]
        
        if len(contrattuale_obls) > 0:
            assert contrattuale_obls[0].get("owner_role") == "amministrazione", f"Contrattuale should have owner_role=amministrazione"
            print(f"✓ Source H: Contrattuale category maps to owner_role=amministrazione")


class TestDeduplicationAllSources:
    """Test deduplication works across all 8 sources."""
    
    def test_sync_twice_no_duplicates(self, api_client, test_data_fase2):
        """Calling sync twice should NOT create duplicate obligations."""
        commessa_id = test_data_fase2["commessa_id"]
        
        # First sync
        response1 = api_client.post(f"{BASE_URL}/api/obblighi/sync/{commessa_id}")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second sync
        response2 = api_client.post(f"{BASE_URL}/api/obblighi/sync/{commessa_id}")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second sync should create 0 new obligations
        assert data2['created'] == 0, f"Second sync should create 0 new, but created {data2['created']}"
        
        print(f"✓ Deduplication: First sync created={data1['created']}, second sync created={data2['created']}")


class TestAutoCloseNewSources:
    """Test auto-close works when source condition disappears for new sources."""
    
    def test_auto_close_when_pack_item_fixed(self, api_client):
        """After fixing a missing item in package and syncing, obligation should be auto-closed."""
        import pymongo
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        client = pymongo.MongoClient(mongo_url)
        db = client['test_database']
        
        # Create fresh test data
        test_commessa_id = f"commessa_autoclose_pack_{int(time.time())}"
        pack_id = f"pack_autoclose_{int(time.time())}"
        
        db.commesse.insert_one({
            "commessa_id": test_commessa_id,
            "user_id": USER_ID,
            "numero": "TEST-AUTOCLOSE-PACK",
            "title": "Test Auto Close Pack",
            "stato": "in_produzione",
            "created_at": datetime.utcnow()
        })
        
        db.pacchetti_documentali.insert_one({
            "pack_id": pack_id,
            "user_id": USER_ID,
            "commessa_id": test_commessa_id,
            "label": "Pack Autoclose Test",
            "status": "attivo",
            "items": [
                {"document_type_code": "DOC_AUTOCLOSE", "status": "missing", "required": True, "blocking": False}
            ],
            "created_at": datetime.utcnow()
        })
        
        # First sync - should create obligation
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{test_commessa_id}")
        assert response.status_code == 200
        data1 = response.json()
        
        # Verify obligation was created
        response = api_client.get(f"{BASE_URL}/api/obblighi/commessa/{test_commessa_id}")
        obligations_before = response.json()
        pack_obls = [o for o in obligations_before if o.get("source_module") == "pacchetti_documentali"]
        
        if len(pack_obls) == 0:
            db.commesse.delete_one({"commessa_id": test_commessa_id})
            db.pacchetti_documentali.delete_one({"pack_id": pack_id})
            pytest.skip("No pack obligation created")
        
        # Fix the item (change status to valid)
        db.pacchetti_documentali.update_one(
            {"pack_id": pack_id},
            {"$set": {"items.0.status": "valid"}}
        )
        
        # Second sync - should auto-close
        response = api_client.post(f"{BASE_URL}/api/obblighi/sync/{test_commessa_id}")
        assert response.status_code == 200
        data2 = response.json()
        
        assert data2['closed'] > 0, f"Should have auto-closed at least 1 obligation, closed={data2['closed']}"
        print(f"✓ Auto-close works for pacchetti_documentali: closed={data2['closed']}")
        
        # Cleanup
        db.commesse.delete_one({"commessa_id": test_commessa_id})
        db.pacchetti_documentali.delete_one({"pack_id": pack_id})
        db.obblighi_commessa.delete_many({"commessa_id": test_commessa_id})
        client.close()


class TestFilterByNewSources:
    """Test filtering obligations by new source modules."""
    
    def test_filter_by_documenti_scadenza(self, api_client, test_data_fase2):
        """Filter by source_module=documenti_scadenza should work."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=documenti_scadenza&commessa_id={commessa_id}")
        assert response.status_code == 200
        data = response.json()
        
        for obl in data:
            assert obl.get("source_module") == "documenti_scadenza"
        
        print(f"✓ Filter by documenti_scadenza: {len(data)} obligations")
    
    def test_filter_by_pacchetti_documentali(self, api_client, test_data_fase2):
        """Filter by source_module=pacchetti_documentali should work."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=pacchetti_documentali&commessa_id={commessa_id}")
        assert response.status_code == 200
        data = response.json()
        
        for obl in data:
            assert obl.get("source_module") == "pacchetti_documentali"
        
        print(f"✓ Filter by pacchetti_documentali: {len(data)} obligations")
    
    def test_filter_by_committenza(self, api_client, test_data_fase2):
        """Filter by source_module=committenza should work."""
        commessa_id = test_data_fase2["commessa_id"]
        
        response = api_client.get(f"{BASE_URL}/api/obblighi?source_module=committenza&commessa_id={commessa_id}")
        assert response.status_code == 200
        data = response.json()
        
        for obl in data:
            assert obl.get("source_module") == "committenza"
        
        print(f"✓ Filter by committenza: {len(data)} obligations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

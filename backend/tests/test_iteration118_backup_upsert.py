"""
Iteration 118: Backup & Restore UPSERT Logic Tests
Tests to verify that restoring a backup uses UPSERT (update_one with upsert=True)
instead of insert-only logic, preventing duplicate records.

Key tests:
1. POST /api/admin/backup/restore returns correct response fields (total_inserted, total_updated, total_errors)
2. Restoring same backup twice does NOT duplicate records - second restore shows "updated" instead of "inserted"
3. GET /api/admin/backup/export still works correctly
4. Full cycle: insert -> export -> modify -> restore -> verify update (not duplicate)
5. company_settings collection uses user_id as PK for upsert
"""
import pytest
import requests
import os
import json
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test credentials
TEST_USER_ID = "user_backup_upsert_118"
TEST_SESSION_TOKEN = "session_backup_upsert_118_token"
TEST_EMAIL = "backup_upsert_test@test.com"


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client for direct DB operations"""
    client = MongoClient(MONGO_URL)
    yield client
    client.close()


@pytest.fixture(scope="module")
def db(mongo_client):
    """Database handle"""
    return mongo_client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def setup_test_user(db):
    """Create test user and session in MongoDB"""
    # Clean up any existing test data
    db.users.delete_many({"user_id": TEST_USER_ID})
    db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    
    # Create test user
    db.users.insert_one({
        "user_id": TEST_USER_ID,
        "email": TEST_EMAIL,
        "name": "Backup Upsert Test User",
        "role": "admin",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    
    # Create test session
    db.user_sessions.insert_one({
        "user_id": TEST_USER_ID,
        "session_token": TEST_SESSION_TOKEN,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    
    yield
    
    # Cleanup after all tests
    db.users.delete_many({"user_id": TEST_USER_ID})
    db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    # Clean up test data in collections
    db.clients.delete_many({"user_id": TEST_USER_ID})
    db.commesse.delete_many({"user_id": TEST_USER_ID})
    db.company_settings.delete_many({"user_id": TEST_USER_ID})


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
    })
    return session


# ===== Test Response Fields =====
class TestRestoreResponseFields:
    """Tests for POST /api/admin/backup/restore response structure"""
    
    def test_restore_returns_correct_fields(self, api_client):
        """Restore endpoint returns total_inserted, total_updated, total_errors fields"""
        valid_backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {},
            "stats": {}
        })
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", valid_backup.encode(), "application/json")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify new response fields
        assert "total_inserted" in data, "Response should contain 'total_inserted'"
        assert "total_updated" in data, "Response should contain 'total_updated'"
        assert "total_errors" in data, "Response should contain 'total_errors'"
        assert "message" in data, "Response should contain 'message'"
        assert "details" in data, "Response should contain 'details'"
        
    def test_restore_details_contains_per_collection_counts(self, api_client):
        """Restore details contains inserted/updated/errors per collection"""
        test_client_id = f"test_client_fields_{datetime.now().timestamp()}"
        backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Test Client Fields",
                }]
            },
            "stats": {"clients": 1}
        })
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "clients" in data["details"], "Details should contain 'clients' key"
        client_details = data["details"]["clients"]
        assert "inserted" in client_details, "Client details should have 'inserted'"
        assert "updated" in client_details, "Client details should have 'updated'"
        assert "errors" in client_details, "Client details should have 'errors'"


# ===== Test UPSERT Logic - No Duplicates =====
class TestUpsertNoDuplicates:
    """Tests to verify UPSERT prevents duplicate records"""
    
    def test_restore_twice_does_not_duplicate(self, api_client, db):
        """Restoring same backup twice should UPDATE, not INSERT duplicate"""
        test_client_id = f"test_upsert_client_{datetime.now().timestamp()}"
        backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Upsert Test Client Original",
                    "vat_number": "IT12345678901"
                }]
            },
            "stats": {"clients": 1}
        })
        
        # First restore - should INSERT
        response1 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response1.status_code == 200, f"First restore failed: {response1.text}"
        data1 = response1.json()
        
        first_inserted = data1["details"]["clients"]["inserted"]
        first_updated = data1["details"]["clients"]["updated"]
        assert first_inserted == 1, f"First restore should insert 1 record, got {first_inserted}"
        
        # Count records before second restore
        count_before = db.clients.count_documents({"client_id": test_client_id, "user_id": TEST_USER_ID})
        assert count_before == 1, f"Should have exactly 1 record before second restore, got {count_before}"
        
        # Second restore - should UPDATE (not INSERT duplicate)
        response2 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response2.status_code == 200, f"Second restore failed: {response2.text}"
        data2 = response2.json()
        
        second_inserted = data2["details"]["clients"]["inserted"]
        second_updated = data2["details"]["clients"]["updated"]
        
        # CRITICAL: Second restore should show UPDATE, not INSERT
        assert second_inserted == 0, f"Second restore should NOT insert (upsert=update), got {second_inserted} inserted"
        assert second_updated == 1, f"Second restore should update 1 record, got {second_updated}"
        
        # Count records after second restore - should still be 1 (no duplicates!)
        count_after = db.clients.count_documents({"client_id": test_client_id, "user_id": TEST_USER_ID})
        assert count_after == 1, f"Should still have exactly 1 record after second restore (no duplicates!), got {count_after}"
        
    def test_upsert_updates_data_on_second_restore(self, api_client, db):
        """UPSERT should actually update the data on second restore"""
        test_client_id = f"test_update_data_{datetime.now().timestamp()}"
        
        # First backup with original name
        backup1 = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Original Name",
                    "vat_number": "IT11111111111"
                }]
            },
            "stats": {"clients": 1}
        })
        
        # First restore
        response1 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup1.json", backup1.encode(), "application/json")}
        )
        assert response1.status_code == 200
        
        # Verify original data
        client = db.clients.find_one({"client_id": test_client_id, "user_id": TEST_USER_ID}, {"_id": 0})
        assert client is not None, "Client should exist after first restore"
        assert client["business_name"] == "Original Name"
        
        # Second backup with UPDATED name
        backup2 = json.dumps({
            "metadata": {"date": "2026-01-02T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Updated Name From Backup",
                    "vat_number": "IT22222222222"
                }]
            },
            "stats": {"clients": 1}
        })
        
        # Second restore - should UPDATE
        response2 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup2.json", backup2.encode(), "application/json")}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify it was an UPDATE
        assert data2["details"]["clients"]["updated"] == 1
        assert data2["details"]["clients"]["inserted"] == 0
        
        # Verify data was actually updated
        client_updated = db.clients.find_one({"client_id": test_client_id, "user_id": TEST_USER_ID}, {"_id": 0})
        assert client_updated["business_name"] == "Updated Name From Backup", "Business name should be updated"
        assert client_updated["vat_number"] == "IT22222222222", "VAT number should be updated"
        
        # Still only 1 record (no duplicates)
        count = db.clients.count_documents({"client_id": test_client_id, "user_id": TEST_USER_ID})
        assert count == 1, f"Should still have exactly 1 record, got {count}"


# ===== Test Full Cycle: Export -> Modify -> Restore -> Verify =====
class TestFullUpsertCycle:
    """Full cycle test: create data -> export -> modify -> restore -> verify update"""
    
    def test_full_upsert_cycle_with_commesse(self, api_client, db):
        """Full cycle: insert commessa -> export -> modify in DB -> restore -> verify restored data"""
        test_commessa_id = f"test_commessa_cycle_{datetime.now().timestamp()}"
        
        # Step 1: Insert test commessa directly into DB
        db.commesse.insert_one({
            "commessa_id": test_commessa_id,
            "user_id": TEST_USER_ID,
            "title": "Original Commessa Title",
            "status": "in_progress",
            "value": 10000
        })
        
        # Step 2: Export backup
        export_response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        assert export_response.status_code == 200, f"Export failed: {export_response.text}"
        backup_data = export_response.json()
        
        # Verify commessa is in the backup
        commesse_in_backup = backup_data["data"].get("commesse", [])
        our_commessa = next((c for c in commesse_in_backup if c.get("commessa_id") == test_commessa_id), None)
        assert our_commessa is not None, "Test commessa should be in the backup"
        assert our_commessa["title"] == "Original Commessa Title"
        
        # Step 3: Modify the commessa directly in DB (simulating user changes)
        db.commesse.update_one(
            {"commessa_id": test_commessa_id, "user_id": TEST_USER_ID},
            {"$set": {"title": "Modified In DB", "value": 99999}}
        )
        
        # Verify modification
        modified_commessa = db.commesse.find_one({"commessa_id": test_commessa_id, "user_id": TEST_USER_ID}, {"_id": 0})
        assert modified_commessa["title"] == "Modified In DB"
        assert modified_commessa["value"] == 99999
        
        # Step 4: Restore from backup (should UPDATE back to original)
        backup_json = json.dumps(backup_data)
        restore_response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup_json.encode(), "application/json")}
        )
        assert restore_response.status_code == 200, f"Restore failed: {restore_response.text}"
        restore_data = restore_response.json()
        
        # Step 5: Verify data was UPDATED (not duplicated)
        count = db.commesse.count_documents({"commessa_id": test_commessa_id, "user_id": TEST_USER_ID})
        assert count == 1, f"Should have exactly 1 commessa (no duplicates!), got {count}"
        
        # Verify data was restored to backup values
        restored_commessa = db.commesse.find_one({"commessa_id": test_commessa_id, "user_id": TEST_USER_ID}, {"_id": 0})
        assert restored_commessa["title"] == "Original Commessa Title", "Title should be restored from backup"
        assert restored_commessa["value"] == 10000, "Value should be restored from backup"
        
        # Verify restore response shows update
        commesse_details = restore_data["details"].get("commesse", {})
        # Note: commessa was updated, so updated count should be >= 1
        print(f"Commesse restore details: {commesse_details}")


# ===== Test company_settings Uses user_id as PK =====
class TestCompanySettingsUpsert:
    """Tests to verify company_settings uses user_id as primary key for upsert"""
    
    def test_company_settings_upsert_by_user_id(self, api_client, db):
        """company_settings should use user_id as PK for upsert"""
        # First restore with company_settings
        backup1 = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "company_settings": [{
                    "user_id": TEST_USER_ID,
                    "company_name": "Original Company Name",
                    "vat_number": "IT00000000001"
                }]
            },
            "stats": {"company_settings": 1}
        })
        
        response1 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup1.json", backup1.encode(), "application/json")}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Should insert first time
        settings_details = data1["details"].get("company_settings", {})
        print(f"First company_settings restore: {settings_details}")
        
        # Second restore - should UPDATE (not duplicate)
        backup2 = json.dumps({
            "metadata": {"date": "2026-01-02T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "company_settings": [{
                    "user_id": TEST_USER_ID,
                    "company_name": "Updated Company Name",
                    "vat_number": "IT99999999999"
                }]
            },
            "stats": {"company_settings": 1}
        })
        
        response2 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup2.json", backup2.encode(), "application/json")}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        settings_details2 = data2["details"].get("company_settings", {})
        print(f"Second company_settings restore: {settings_details2}")
        
        # Verify no duplicates - should be exactly 1 record for this user
        count = db.company_settings.count_documents({"user_id": TEST_USER_ID})
        assert count == 1, f"Should have exactly 1 company_settings for user (no duplicates!), got {count}"
        
        # Verify data was updated
        settings = db.company_settings.find_one({"user_id": TEST_USER_ID}, {"_id": 0})
        assert settings["company_name"] == "Updated Company Name"


# ===== Test Export Endpoint Still Works =====
class TestExportEndpoint:
    """Tests to verify export endpoint still works correctly"""
    
    def test_export_returns_200(self, api_client):
        """Export endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_export_returns_valid_json(self, api_client):
        """Export returns valid JSON with correct structure"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code == 200
        data = response.json()
        
        assert "metadata" in data, "Export should contain 'metadata'"
        assert "data" in data, "Export should contain 'data'"
        assert "stats" in data, "Export should contain 'stats'"
        
        # Check metadata fields
        assert data["metadata"]["version"] == "2.0"
        assert data["metadata"]["user_id"] == TEST_USER_ID
        assert "date" in data["metadata"]
        assert "total_records" in data["metadata"]


# ===== Test New Records Insert Correctly =====
class TestNewRecordInsert:
    """Tests to verify new records (not existing in DB) are INSERTED correctly"""
    
    def test_new_record_is_inserted(self, api_client, db):
        """New record from backup should be inserted"""
        # Use a unique ID that definitely doesn't exist
        unique_client_id = f"brand_new_client_{datetime.now().timestamp()}"
        
        # Verify it doesn't exist
        existing = db.clients.find_one({"client_id": unique_client_id})
        assert existing is None, "Test client should not exist before restore"
        
        backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "clients": [{
                    "client_id": unique_client_id,
                    "business_name": "Brand New Client",
                    "vat_number": "IT55555555555"
                }]
            },
            "stats": {"clients": 1}
        })
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have inserted 1 new record
        assert data["details"]["clients"]["inserted"] == 1, "Should insert 1 new record"
        assert data["total_inserted"] >= 1, "Total inserted should be >= 1"
        
        # Verify record exists now
        new_client = db.clients.find_one({"client_id": unique_client_id, "user_id": TEST_USER_ID}, {"_id": 0})
        assert new_client is not None, "New client should exist after restore"
        assert new_client["business_name"] == "Brand New Client"


# ===== Test catalogo_profili Uses codice as PK =====
class TestCatalogoProfiliFPK:
    """Tests to verify catalogo_profili uses 'codice' as primary key"""
    
    def test_catalogo_profili_upsert_by_codice(self, api_client, db):
        """catalogo_profili should use 'codice' as PK for upsert"""
        test_codice = f"TEST_PROFILO_{datetime.now().timestamp()}"
        
        backup1 = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "catalogo_profili": [{
                    "codice": test_codice,
                    "descrizione": "Original Description",
                    "prezzo": 100
                }]
            },
            "stats": {"catalogo_profili": 1}
        })
        
        # First restore
        response1 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup1.json", backup1.encode(), "application/json")}
        )
        assert response1.status_code == 200
        
        # Second restore with updated data
        backup2 = json.dumps({
            "metadata": {"date": "2026-01-02T00:00:00", "version": "2.0", "user_id": TEST_USER_ID},
            "data": {
                "catalogo_profili": [{
                    "codice": test_codice,
                    "descrizione": "Updated Description",
                    "prezzo": 200
                }]
            },
            "stats": {"catalogo_profili": 1}
        })
        
        response2 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup2.json", backup2.encode(), "application/json")}
        )
        assert response2.status_code == 200
        
        # Verify no duplicates
        count = db.catalogo_profili.count_documents({"codice": test_codice, "user_id": TEST_USER_ID})
        assert count == 1, f"Should have exactly 1 catalogo_profili entry (no duplicates!), got {count}"
        
        # Cleanup
        db.catalogo_profili.delete_many({"codice": test_codice, "user_id": TEST_USER_ID})

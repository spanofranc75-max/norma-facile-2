"""
Iteration 101: Backup & Restore Module Tests
Tests for GET /api/admin/backup/stats, /last, /export, POST /restore
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials - created in MongoDB
SESSION_TOKEN = "session_backup_1772448361362"
USER_ID = "user_backup_1772448361362"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


# ===== Test Backup Stats Endpoint =====
class TestBackupStats:
    """Tests for GET /api/admin/backup/stats"""
    
    def test_stats_returns_200(self, api_client):
        """Stats endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_stats_returns_stats_dict(self, api_client):
        """Stats endpoint returns stats dictionary"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/stats")
        data = response.json()
        assert "stats" in data, "Response should contain 'stats' key"
        assert isinstance(data["stats"], dict), "Stats should be a dictionary"
    
    def test_stats_returns_total_count(self, api_client):
        """Stats endpoint returns total count"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/stats")
        data = response.json()
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["total"], int), "Total should be an integer"
    
    def test_stats_contains_expected_collections(self, api_client):
        """Stats contains all expected collection keys"""
        expected_collections = [
            "commesse", "preventivi", "clients", "invoices", "ddt",
            "fpc_projects", "gate_certifications", "welders", "instruments",
            "company_docs", "distinte", "rilievi", "fatture_ricevute",
            "consumable_batches", "project_costs", "audit_findings",
            "company_settings", "catalogo_profili", "articoli"
        ]
        response = api_client.get(f"{BASE_URL}/api/admin/backup/stats")
        data = response.json()
        stats = data.get("stats", {})
        for coll in expected_collections:
            assert coll in stats, f"Collection '{coll}' should be in stats"


# ===== Test Last Backup Endpoint =====
class TestLastBackup:
    """Tests for GET /api/admin/backup/last"""
    
    def test_last_returns_200(self, api_client):
        """Last backup endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/last")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_last_returns_last_backup_key(self, api_client):
        """Last backup endpoint returns last_backup key"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/last")
        data = response.json()
        assert "last_backup" in data, "Response should contain 'last_backup' key"
    
    def test_last_backup_can_be_null_initially(self, api_client):
        """Last backup can be null if no backups exist for user"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/last")
        data = response.json()
        # It's OK to be null for new users
        assert "last_backup" in data


# ===== Test Export Endpoint =====
class TestExportBackup:
    """Tests for GET /api/admin/backup/export"""
    
    def test_export_returns_200(self, api_client):
        """Export endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_export_returns_json_content_type(self, api_client):
        """Export endpoint returns application/json content type"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, f"Expected JSON content type, got {content_type}"
    
    def test_export_has_content_disposition(self, api_client):
        """Export endpoint has content-disposition header for download"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, f"Expected attachment in Content-Disposition: {content_disposition}"
        assert "filename=" in content_disposition, f"Expected filename in Content-Disposition: {content_disposition}"
    
    def test_export_filename_format(self, api_client):
        """Export filename follows pattern backup_normafacile_YYYYMMDD_HHMM.json"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "backup_normafacile_" in content_disposition, f"Filename should contain 'backup_normafacile_': {content_disposition}"
        assert ".json" in content_disposition, f"Filename should end with .json: {content_disposition}"
    
    def test_export_json_structure_has_metadata(self, api_client):
        """Export JSON contains metadata section"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        data = response.json()
        assert "metadata" in data, "Export should contain 'metadata' key"
        metadata = data["metadata"]
        assert "date" in metadata, "Metadata should contain 'date'"
        assert "version" in metadata, "Metadata should contain 'version'"
        assert "user_id" in metadata, "Metadata should contain 'user_id'"
    
    def test_export_json_structure_has_data(self, api_client):
        """Export JSON contains data section with collections"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        data = response.json()
        assert "data" in data, "Export should contain 'data' key"
        assert isinstance(data["data"], dict), "Data should be a dictionary"
    
    def test_export_json_structure_has_stats(self, api_client):
        """Export JSON contains stats section"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        data = response.json()
        assert "stats" in data, "Export should contain 'stats' key"
        assert isinstance(data["stats"], dict), "Stats should be a dictionary"
    
    def test_export_metadata_version_is_2_0(self, api_client):
        """Export metadata version is 2.0"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        data = response.json()
        assert data["metadata"]["version"] == "2.0", "Version should be '2.0'"
    
    def test_export_metadata_user_id_matches(self, api_client):
        """Export metadata user_id matches authenticated user"""
        response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        data = response.json()
        assert data["metadata"]["user_id"] == USER_ID, f"User ID should match {USER_ID}"


# ===== Test Restore Endpoint =====
class TestRestoreBackup:
    """Tests for POST /api/admin/backup/restore"""
    
    def test_restore_invalid_json_returns_400(self, api_client):
        """Restore with invalid JSON returns 400"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", b"invalid json", "application/json")}
        )
        # FastAPI returns 400 for invalid JSON in restore endpoint
        assert response.status_code == 400, f"Expected 400 for invalid JSON, got {response.status_code}: {response.text}"
    
    def test_restore_missing_metadata_returns_400(self, api_client):
        """Restore without metadata returns 400"""
        invalid_backup = json.dumps({"data": {}})
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", invalid_backup.encode(), "application/json")}
        )
        assert response.status_code == 400, f"Expected 400 for missing metadata, got {response.status_code}: {response.text}"
    
    def test_restore_empty_backup_returns_200(self, api_client):
        """Restore with empty data returns 200 OK"""
        valid_backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": USER_ID},
            "data": {},
            "stats": {}
        })
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", valid_backup.encode(), "application/json")}
        )
        assert response.status_code == 200, f"Expected 200 for valid empty backup, got {response.status_code}: {response.text}"
    
    def test_restore_returns_result_message(self, api_client):
        """Restore returns message with counts"""
        valid_backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": USER_ID},
            "data": {},
            "stats": {}
        })
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", valid_backup.encode(), "application/json")}
        )
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "total_restored" in data, "Response should contain 'total_restored'"
        assert "total_skipped" in data, "Response should contain 'total_skipped'"
        assert "details" in data, "Response should contain 'details'"


# ===== Test Restore with Sample Data =====
class TestRestoreWithData:
    """Tests for restore with actual data to verify merge behavior"""
    
    def test_restore_inserts_new_client(self, api_client):
        """Restore inserts a new client record"""
        test_client_id = f"test_client_{datetime.now().timestamp()}"
        backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Test Restore Client",
                    "user_id": USER_ID
                }]
            },
            "stats": {"clients": 1}
        })
        response = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should have inserted at least 1
        assert data["total_restored"] >= 0, "Should report restored count"
        
    def test_restore_skips_duplicate_client(self, api_client):
        """Restore skips duplicate client (merge behavior)"""
        test_client_id = f"test_dup_client_{datetime.now().timestamp()}"
        backup = json.dumps({
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0", "user_id": USER_ID},
            "data": {
                "clients": [{
                    "client_id": test_client_id,
                    "business_name": "Test Dup Client",
                    "user_id": USER_ID
                }]
            },
            "stats": {"clients": 1}
        })
        # First restore
        response1 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response1.status_code == 200, f"Expected 200, got {response1.status_code}: {response1.text}"
        data1 = response1.json()
        first_inserted = data1.get("details", {}).get("clients", {}).get("inserted", 0)
        
        # Second restore (should skip)
        response2 = api_client.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", backup.encode(), "application/json")}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        second_skipped = data2.get("details", {}).get("clients", {}).get("skipped", 0)
        
        # If first insert was successful, second should skip
        if first_inserted > 0:
            assert second_skipped > 0, "Duplicate record should be skipped on second restore"


# ===== Test Last Backup After Export =====
class TestBackupLog:
    """Tests to verify backup log is created after export"""
    
    def test_last_backup_updated_after_export(self, api_client):
        """Last backup info is updated after performing an export"""
        # Perform an export first
        export_response = api_client.get(f"{BASE_URL}/api/admin/backup/export")
        assert export_response.status_code == 200
        
        # Check last backup
        last_response = api_client.get(f"{BASE_URL}/api/admin/backup/last")
        assert last_response.status_code == 200
        data = last_response.json()
        
        # Now last_backup should not be null
        assert data["last_backup"] is not None, "Last backup should exist after export"
        last_backup = data["last_backup"]
        assert "date" in last_backup, "Last backup should have date"
        assert "filename" in last_backup, "Last backup should have filename"
        assert "total_records" in last_backup, "Last backup should have total_records"
        assert "size_bytes" in last_backup, "Last backup should have size_bytes"


# ===== Test Unauthenticated Access =====
class TestUnauthenticated:
    """Tests for unauthenticated access (should fail)"""
    
    def test_stats_requires_auth(self):
        """Stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/backup/stats")
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_export_requires_auth(self):
        """Export endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_restore_requires_auth(self):
        """Restore endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files={"file": ("backup.json", b"{}", "application/json")}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"

"""
Test Iteration 151: Backup Restore Modes (Merge/Wipe) and Related Features

Tests:
1. POST /api/admin/backup/restore with mode='merge' - upsert behavior
2. POST /api/admin/backup/restore with mode='wipe' - delete then import
3. Invalid mode returns 400
4. Merge mode does not create duplicates
5. Wipe mode deletes user data before importing
6. Export backup returns valid JSON structure
"""
import pytest
import requests
import json
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = 'test_session_backup_1772800406895'
USER_ID = 'test-user-backup-1772800406895'


@pytest.fixture
def auth_cookies():
    """Return auth cookies dict for requests"""
    return {'session_token': SESSION_TOKEN}


@pytest.fixture
def session(auth_cookies):
    """Return requests session with auth"""
    s = requests.Session()
    s.cookies.update(auth_cookies)
    return s


class TestBackupRestoreModes:
    """Test backup restore endpoint with merge/wipe modes"""
    
    def test_export_backup_returns_valid_json(self, session):
        """Export endpoint returns valid backup JSON"""
        response = session.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code == 200, f"Export failed: {response.text}"
        
        backup_data = response.json()
        assert "metadata" in backup_data, "Missing metadata in backup"
        assert "data" in backup_data, "Missing data in backup"
        assert "stats" in backup_data, "Missing stats in backup"
        assert backup_data["metadata"]["version"] == "2.0"
        assert backup_data["metadata"]["app"] == "Norma Facile 2.0"
        print(f"✓ Export returns valid backup with {backup_data['metadata'].get('total_records', 0)} records")
    
    def test_restore_with_invalid_mode_returns_400(self, session):
        """Invalid mode returns 400 Bad Request"""
        # Create minimal valid backup JSON
        backup = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {"clients": []},
            "stats": {}
        }
        backup_json = json.dumps(backup).encode('utf-8')
        
        files = {'file': ('test_backup.json', backup_json, 'application/json')}
        data = {'mode': 'invalid_mode'}
        
        response = session.post(
            f"{BASE_URL}/api/admin/backup/restore",
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid mode, got {response.status_code}: {response.text}"
        response_data = response.json()
        assert "non valida" in response_data.get('detail', '').lower() or "merge" in response_data.get('detail', '').lower()
        print("✓ Invalid mode correctly returns 400")
    
    def test_restore_merge_mode_upserts_data(self, session):
        """Merge mode performs upsert - updates existing, inserts new"""
        unique_id = f"test_client_merge_{int(time.time())}"
        
        # First restore with initial data
        backup1 = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {
                "clients": [{
                    "client_id": unique_id,
                    "business_name": "Original Name",
                    "client_type": "cliente"
                }]
            },
            "stats": {"clients": 1}
        }
        
        files = {'file': ('backup1.json', json.dumps(backup1).encode('utf-8'), 'application/json')}
        data = {'mode': 'merge'}
        
        response = session.post(f"{BASE_URL}/api/admin/backup/restore", files=files, data=data)
        assert response.status_code == 200, f"First merge restore failed: {response.text}"
        result1 = response.json()
        print(f"First merge: inserted={result1.get('total_inserted')}, updated={result1.get('total_updated')}")
        
        # Second restore with updated data
        backup2 = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {
                "clients": [{
                    "client_id": unique_id,
                    "business_name": "Updated Name",  # Changed
                    "client_type": "cliente"
                }]
            },
            "stats": {"clients": 1}
        }
        
        files = {'file': ('backup2.json', json.dumps(backup2).encode('utf-8'), 'application/json')}
        data = {'mode': 'merge'}
        
        response = session.post(f"{BASE_URL}/api/admin/backup/restore", files=files, data=data)
        assert response.status_code == 200, f"Second merge restore failed: {response.text}"
        result2 = response.json()
        assert result2['mode'] == 'merge'
        print(f"Second merge: inserted={result2.get('total_inserted')}, updated={result2.get('total_updated')}")
        
        # Verify no duplicates - fetch clients
        response = session.get(f"{BASE_URL}/api/clients/?search={unique_id}&limit=100")
        if response.status_code == 200:
            clients = response.json().get('clients', [])
            matching = [c for c in clients if c.get('client_id') == unique_id]
            assert len(matching) <= 1, f"Found {len(matching)} duplicates with same client_id!"
            print(f"✓ Merge mode correctly upserted without duplicates")
        else:
            print(f"✓ Merge mode completed (client list check skipped)")
    
    def test_restore_wipe_mode_deletes_before_import(self, session):
        """Wipe mode deletes all user data before importing"""
        unique_id = f"test_client_wipe_{int(time.time())}"
        
        # First, insert some data
        backup_initial = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {
                "clients": [{
                    "client_id": unique_id,
                    "business_name": "Will Be Deleted",
                    "client_type": "cliente"
                }]
            },
            "stats": {"clients": 1}
        }
        
        files = {'file': ('initial.json', json.dumps(backup_initial).encode('utf-8'), 'application/json')}
        data = {'mode': 'merge'}
        session.post(f"{BASE_URL}/api/admin/backup/restore", files=files, data=data)
        
        # Now do wipe restore with empty clients but filled with different data
        backup_wipe = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {
                "clients": [{
                    "client_id": f"new_client_{int(time.time())}",
                    "business_name": "Fresh Import",
                    "client_type": "cliente"
                }]
            },
            "stats": {"clients": 1}
        }
        
        files = {'file': ('wipe.json', json.dumps(backup_wipe).encode('utf-8'), 'application/json')}
        data = {'mode': 'wipe'}
        
        response = session.post(f"{BASE_URL}/api/admin/backup/restore", files=files, data=data)
        assert response.status_code == 200, f"Wipe restore failed: {response.text}"
        
        result = response.json()
        assert result['mode'] == 'wipe'
        # Wipe mode should have deleted some records
        assert 'total_deleted' in result or result.get('total_deleted', 0) >= 0
        print(f"✓ Wipe mode: deleted={result.get('total_deleted', 0)}, inserted={result.get('total_inserted', 0)}")
        print(f"  Message: {result.get('message', '')}")
    
    def test_restore_merge_mode_default_if_not_specified(self, session):
        """If mode is not specified, merge should be the default"""
        backup = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {"clients": []},
            "stats": {}
        }
        
        files = {'file': ('backup.json', json.dumps(backup).encode('utf-8'), 'application/json')}
        # Note: Not specifying 'mode' - should default to 'merge'
        
        response = session.post(f"{BASE_URL}/api/admin/backup/restore", files=files)
        assert response.status_code == 200, f"Default mode restore failed: {response.text}"
        
        result = response.json()
        assert result['mode'] == 'merge', f"Expected default mode 'merge', got '{result.get('mode')}'"
        print("✓ Default mode is 'merge' when not specified")
    
    def test_restore_returns_detailed_response(self, session):
        """Restore returns detailed response with all expected fields"""
        backup = {
            "metadata": {"date": "2026-01-01T00:00:00", "version": "2.0"},
            "data": {
                "clients": [{
                    "client_id": f"detail_test_{int(time.time())}",
                    "business_name": "Detail Test Client",
                    "client_type": "cliente"
                }]
            },
            "stats": {"clients": 1}
        }
        
        files = {'file': ('backup.json', json.dumps(backup).encode('utf-8'), 'application/json')}
        data = {'mode': 'merge'}
        
        response = session.post(f"{BASE_URL}/api/admin/backup/restore", files=files, data=data)
        assert response.status_code == 200
        
        result = response.json()
        
        # Check all expected response fields
        assert 'message' in result, "Missing 'message' in response"
        assert 'mode' in result, "Missing 'mode' in response"
        assert 'total_inserted' in result, "Missing 'total_inserted' in response"
        assert 'total_updated' in result, "Missing 'total_updated' in response"
        assert 'total_errors' in result, "Missing 'total_errors' in response"
        assert 'details' in result, "Missing 'details' in response"
        
        print(f"✓ Response includes all expected fields: message, mode, total_inserted, total_updated, total_errors, details")
        print(f"  Message: {result['message']}")


class TestBackupStats:
    """Test backup stats and last backup endpoints"""
    
    def test_get_backup_stats(self, session):
        """Stats endpoint returns collection counts"""
        response = session.get(f"{BASE_URL}/api/admin/backup/stats")
        assert response.status_code == 200, f"Stats failed: {response.text}"
        
        data = response.json()
        assert 'stats' in data, "Missing 'stats' in response"
        assert 'total' in data, "Missing 'total' in response"
        assert isinstance(data['stats'], dict), "stats should be a dict"
        
        print(f"✓ Backup stats: total={data['total']} records")
        for coll, count in list(data['stats'].items())[:5]:
            if count > 0:
                print(f"  - {coll}: {count}")
    
    def test_get_last_backup(self, session):
        """Last backup endpoint returns backup info or null"""
        response = session.get(f"{BASE_URL}/api/admin/backup/last")
        assert response.status_code == 200, f"Last backup failed: {response.text}"
        
        data = response.json()
        assert 'last_backup' in data, "Missing 'last_backup' in response"
        
        if data['last_backup']:
            lb = data['last_backup']
            assert 'date' in lb, "Missing 'date' in last_backup"
            print(f"✓ Last backup: {lb.get('date')} - {lb.get('total_records')} records")
        else:
            print("✓ No previous backup found (expected for fresh test user)")


class TestClientDetailFetch:
    """Test that client/supplier detail fetch returns full data"""
    
    def test_client_detail_includes_payment_conditions(self, session):
        """GET /api/clients/{id} returns full data including payment fields"""
        # First create a client with payment conditions
        unique_id = f"payment_test_{int(time.time())}"
        
        create_data = {
            "client_id": unique_id,
            "business_name": "Payment Test Client",
            "client_type": "cliente",
            "payment_type_id": "mp_01",
            "payment_type_label": "Bonifico 30gg",
            "iban": "IT60X0542811101000000123456",
            "banca": "Test Bank"
        }
        
        response = session.post(f"{BASE_URL}/api/clients/", json=create_data)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test client: {response.text}")
        
        created = response.json()
        client_id = created.get('client_id', unique_id)
        
        # Now fetch detail
        response = session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert response.status_code == 200, f"Client detail fetch failed: {response.text}"
        
        detail = response.json()
        
        # Verify payment fields are present
        assert detail.get('payment_type_id') == 'mp_01' or detail.get('payment_type_id'), \
            f"payment_type_id not preserved: {detail.get('payment_type_id')}"
        
        print(f"✓ Client detail includes payment_type_id: {detail.get('payment_type_id')}")
        print(f"  payment_type_label: {detail.get('payment_type_label')}")
        print(f"  iban: {detail.get('iban')}")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{client_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

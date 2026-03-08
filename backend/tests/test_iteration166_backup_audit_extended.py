"""
Test Suite for Iteration 166 - Backup History with Auto-Backup and Extended Audit Trail
Tests:
1. GET /api/admin/backup/history - returns list with auto flag
2. GET /api/admin/backup/last - returns last backup info
3. GET /api/admin/backup/stats - returns per-collection stats
4. Audit trail entries for sopralluogo, rilievi, perizie modules
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestBackupHistoryAPI:
    """Tests for backup history endpoints: GET /api/admin/backup/history, /last, /stats"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_backup_history_endpoint_returns_list(self):
        """GET /api/admin/backup/history should return history array with auto flag"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup/history")
        print(f"Backup history response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Backup history data: {data}")
        
        # Should have 'history' key
        assert 'history' in data, "Response should contain 'history' key"
        assert isinstance(data['history'], list), "'history' should be a list"
        
        # If there are backup entries, verify structure
        if data['history']:
            entry = data['history'][0]
            print(f"Sample history entry: {entry}")
            # Check expected fields
            expected_fields = ['date', 'filename', 'total_records', 'size_bytes', 'auto']
            for field in expected_fields:
                assert field in entry, f"History entry missing field: {field}"
            
            # 'auto' field should be boolean
            assert isinstance(entry['auto'], bool), "'auto' field should be boolean"
        else:
            print("No backup history found - this is expected for new users")
    
    def test_backup_last_endpoint_returns_info(self):
        """GET /api/admin/backup/last should return last backup info"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup/last")
        print(f"Backup last response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Backup last data: {data}")
        
        # Should have 'last_backup' key
        assert 'last_backup' in data, "Response should contain 'last_backup' key"
        
        if data['last_backup']:
            backup = data['last_backup']
            expected_fields = ['date', 'filename', 'total_records', 'size_bytes', 'stats']
            for field in expected_fields:
                assert field in backup, f"Last backup missing field: {field}"
            assert isinstance(backup['stats'], dict), "'stats' should be a dict"
        else:
            print("No last backup found - expected for users without any backups")
    
    def test_backup_stats_endpoint_returns_collection_counts(self):
        """GET /api/admin/backup/stats should return per-collection stats"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup/stats")
        print(f"Backup stats response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Backup stats data: {data}")
        
        # Should have 'stats' and 'total' keys
        assert 'stats' in data, "Response should contain 'stats' key"
        assert 'total' in data, "Response should contain 'total' key"
        assert isinstance(data['stats'], dict), "'stats' should be a dict"
        assert isinstance(data['total'], int), "'total' should be an int"


class TestExtendedAuditTrail:
    """Tests to verify audit trail covers sopralluogo, rilievi, perizia modules"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_rilievo_entity_type_in_audit(self):
        """Test that 'rilievo' is a supported entity_type in audit trail"""
        # Check stats endpoint for entity types
        response = self.session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        if data:
            entity_types = data.get('entity_types', [])
            print(f"Entity types: {entity_types}")
            assert 'rilievo' in entity_types, "'rilievo' should be in entity_types"
    
    def test_perizia_entity_type_in_audit(self):
        """Test that 'perizia' is a supported entity_type in audit trail"""
        response = self.session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        if data:
            entity_types = data.get('entity_types', [])
            print(f"Entity types: {entity_types}")
            assert 'perizia' in entity_types, "'perizia' should be in entity_types"
    
    def test_audit_log_filter_by_rilievo(self):
        """Test that activity log can filter by entity_type=rilievo"""
        response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=rilievo")
        print(f"Filter by rilievo response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        print(f"Rilievo activities count: {data['total']}")
    
    def test_audit_log_filter_by_perizia(self):
        """Test that activity log can filter by entity_type=perizia"""
        response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=perizia")
        print(f"Filter by perizia response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        print(f"Perizia activities count: {data['total']}")
    
    def test_entity_labels_include_rilievo_perizia(self):
        """Test that entity labels include Italian translations for rilievo and perizia"""
        response = self.session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        if data:
            entity_labels = data.get('entity_labels', {})
            print(f"Entity labels: {entity_labels}")
            
            # Check rilievo has label
            assert 'rilievo' in entity_labels, "'rilievo' should have a label"
            assert entity_labels['rilievo'] == 'Rilievo', "rilievo label should be 'Rilievo'"
            
            # Check perizia has label
            assert 'perizia' in entity_labels, "'perizia' should have a label"
            assert entity_labels['perizia'] == 'Perizia', "perizia label should be 'Perizia'"


class TestNotificationPreferencesExtended:
    """Additional tests for notification preferences to ensure completeness"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_notification_preferences_persists_preavviso_giorni(self):
        """Test that preavviso_giorni setting is persisted correctly"""
        # Set a specific preavviso value
        new_prefs = {
            'email_alerts_enabled': True,
            'alert_email': None,
            'preavviso_giorni': 30,
            'alert_scadenze_pagamento': True,
            'alert_qualita': True
        }
        
        put_response = self.session.put(
            f"{BASE_URL}/api/notifications/preferences",
            json=new_prefs
        )
        assert put_response.status_code == 200
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        data = get_response.json()
        assert data['preavviso_giorni'] == 30, "preavviso_giorni should be 30"
        
        # Restore default
        new_prefs['preavviso_giorni'] = 7
        self.session.put(f"{BASE_URL}/api/notifications/preferences", json=new_prefs)


class TestActivityLogStats:
    """Tests for activity log statistics endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_stats_returns_action_labels(self):
        """Test that stats include Italian action labels"""
        response = self.session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        if data:
            action_labels = data.get('action_labels', {})
            print(f"Action labels: {action_labels}")
            
            # Check expected action labels
            expected_actions = {
                'create': 'Creazione',
                'update': 'Modifica',
                'delete': 'Eliminazione'
            }
            for action, label in expected_actions.items():
                assert action in action_labels, f"Missing action: {action}"
                assert action_labels[action] == label, f"Wrong label for {action}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

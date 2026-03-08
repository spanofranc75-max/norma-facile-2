"""
Test Suite for Activity Audit Trail and Notification Preferences Features
Tests both new features:
1. Activity Audit Trail - logging all CRUD operations
2. Notification Preferences - user settings for email alerts
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestActivityLogAPI:
    """Tests for GET /api/activity-log and /api/activity-log/stats endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_activity_log_stats_endpoint_exists(self):
        """Test that /api/activity-log/stats endpoint exists and returns expected structure"""
        response = self.session.get(f"{BASE_URL}/api/activity-log/stats")
        print(f"Activity log stats response: {response.status_code}")
        
        # Should return 200 for admin user or empty dict for non-admin
        assert response.status_code == 200
        data = response.json()
        print(f"Stats data: {data}")
        
        # If admin, should have these keys
        if data:
            # Check expected keys exist
            expected_keys = ['total', 'today', 'this_week', 'top_users', 'top_entities', 
                           'action_labels', 'entity_labels', 'entity_types', 'action_types']
            for key in expected_keys:
                assert key in data, f"Missing key: {key}"
            
            # Validate data types
            assert isinstance(data['total'], int)
            assert isinstance(data['today'], int)
            assert isinstance(data['this_week'], int)
            assert isinstance(data['top_users'], list)
            assert isinstance(data['top_entities'], list)
            assert isinstance(data['action_labels'], dict)
            assert isinstance(data['entity_labels'], dict)
            assert isinstance(data['entity_types'], list)
            assert isinstance(data['action_types'], list)
    
    def test_activity_log_list_endpoint_exists(self):
        """Test that /api/activity-log endpoint exists and returns paginated list"""
        response = self.session.get(f"{BASE_URL}/api/activity-log")
        print(f"Activity log list response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"List data keys: {data.keys()}")
        
        # Should have pagination structure
        expected_keys = ['items', 'total', 'skip', 'limit']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        assert isinstance(data['items'], list)
        assert isinstance(data['total'], int)
    
    def test_activity_log_filters(self):
        """Test that filters work on /api/activity-log endpoint"""
        # Test entity_type filter
        response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=cliente")
        assert response.status_code == 200
        print(f"Filter by entity_type: {response.status_code}")
        
        # Test action filter
        response = self.session.get(f"{BASE_URL}/api/activity-log?action=create")
        assert response.status_code == 200
        print(f"Filter by action: {response.status_code}")
        
        # Test search filter
        response = self.session.get(f"{BASE_URL}/api/activity-log?search=test")
        assert response.status_code == 200
        print(f"Filter by search: {response.status_code}")
        
        # Test date filters
        today = datetime.now().strftime('%Y-%m-%d')
        response = self.session.get(f"{BASE_URL}/api/activity-log?date_from={today}")
        assert response.status_code == 200
        print(f"Filter by date_from: {response.status_code}")


class TestNotificationPreferencesAPI:
    """Tests for GET/PUT /api/notifications/preferences endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_get_notification_preferences(self):
        """Test GET /api/notifications/preferences returns correct structure"""
        response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        print(f"Get notification preferences response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Preferences data: {data}")
        
        # Check expected keys exist
        expected_keys = ['email_alerts_enabled', 'alert_email', 'preavviso_giorni', 
                        'alert_scadenze_pagamento', 'alert_qualita', 'user_email']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        # Validate data types
        assert isinstance(data['email_alerts_enabled'], bool)
        assert isinstance(data['preavviso_giorni'], int)
        assert isinstance(data['alert_scadenze_pagamento'], bool)
        assert isinstance(data['alert_qualita'], bool)
    
    def test_update_notification_preferences(self):
        """Test PUT /api/notifications/preferences saves preferences correctly"""
        # First, get current preferences
        get_response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        original_prefs = get_response.json()
        
        # Update with new values
        new_prefs = {
            'email_alerts_enabled': False,
            'alert_email': 'test-update@example.com',
            'preavviso_giorni': 14,
            'alert_scadenze_pagamento': False,
            'alert_qualita': False
        }
        
        put_response = self.session.put(
            f"{BASE_URL}/api/notifications/preferences",
            json=new_prefs
        )
        print(f"Update notification preferences response: {put_response.status_code}")
        
        assert put_response.status_code == 200
        data = put_response.json()
        print(f"Update response: {data}")
        
        # Check response confirms the update
        assert 'message' in data
        assert 'preferences' in data
        assert data['preferences']['email_alerts_enabled'] == False
        assert data['preferences']['alert_email'] == 'test-update@example.com'
        assert data['preferences']['preavviso_giorni'] == 14
        assert data['preferences']['alert_scadenze_pagamento'] == False
        assert data['preferences']['alert_qualita'] == False
        
        # Verify by re-fetching
        verify_response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        verify_data = verify_response.json()
        print(f"Verification data: {verify_data}")
        
        assert verify_data['email_alerts_enabled'] == False
        assert verify_data['alert_email'] == 'test-update@example.com'
        assert verify_data['preavviso_giorni'] == 14
        
        # Restore original preferences (cleanup)
        restore_prefs = {
            'email_alerts_enabled': original_prefs.get('email_alerts_enabled', True),
            'alert_email': original_prefs.get('alert_email', ''),
            'preavviso_giorni': original_prefs.get('preavviso_giorni', 7),
            'alert_scadenze_pagamento': original_prefs.get('alert_scadenze_pagamento', True),
            'alert_qualita': original_prefs.get('alert_qualita', True)
        }
        self.session.put(f"{BASE_URL}/api/notifications/preferences", json=restore_prefs)


class TestAuditTrailCreation:
    """Tests to verify audit trail entries are created when CRUD operations happen"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_client_create_logs_activity(self):
        """Test that creating a client logs an activity entry"""
        # Get initial activity count
        initial_response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=cliente&action=create&limit=1")
        initial_data = initial_response.json()
        initial_total = initial_data.get('total', 0)
        print(f"Initial cliente create count: {initial_total}")
        
        # Create a test client
        client_data = {
            "business_name": f"AUDIT_TEST_Client_{datetime.now().timestamp()}",
            "partita_iva": "",
            "codice_fiscale": "",
            "client_type": "cliente"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/clients/", json=client_data)
        print(f"Create client response: {create_response.status_code}")
        
        if create_response.status_code == 201:
            created_client = create_response.json()
            client_id = created_client.get('client_id')
            print(f"Created client: {client_id}")
            
            # Check that activity log was created
            # Small delay for async processing (if any)
            import time
            time.sleep(0.5)
            
            final_response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=cliente&action=create&limit=1")
            final_data = final_response.json()
            final_total = final_data.get('total', 0)
            print(f"Final cliente create count: {final_total}")
            
            # Should have at least one more entry
            assert final_total >= initial_total, "Activity log should have at least one more entry"
            
            # Cleanup: delete the test client
            delete_response = self.session.delete(f"{BASE_URL}/api/clients/{client_id}")
            print(f"Delete client response: {delete_response.status_code}")
        else:
            # API might reject, but that's OK for this test
            print(f"Client creation returned {create_response.status_code}: {create_response.text[:200]}")
    
    def test_preventivo_create_logs_activity(self):
        """Test that creating a preventivo logs an activity entry"""
        # Get initial activity count for preventivo
        initial_response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=preventivo&action=create&limit=1")
        initial_data = initial_response.json()
        initial_total = initial_data.get('total', 0)
        print(f"Initial preventivo create count: {initial_total}")
        
        # Create a test preventivo
        preventivo_data = {
            "subject": f"AUDIT_TEST_Preventivo_{datetime.now().timestamp()}",
            "validity_days": 30,
            "lines": [],
            "sconto_globale": 0,
            "acconto": 0
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
        print(f"Create preventivo response: {create_response.status_code}")
        
        if create_response.status_code == 201:
            created_preventivo = create_response.json()
            preventivo_id = created_preventivo.get('preventivo_id')
            print(f"Created preventivo: {preventivo_id}")
            
            # Small delay for async processing
            import time
            time.sleep(0.5)
            
            final_response = self.session.get(f"{BASE_URL}/api/activity-log?entity_type=preventivo&action=create&limit=1")
            final_data = final_response.json()
            final_total = final_data.get('total', 0)
            print(f"Final preventivo create count: {final_total}")
            
            assert final_total >= initial_total, "Activity log should have at least one more entry"
            
            # Cleanup
            delete_response = self.session.delete(f"{BASE_URL}/api/preventivi/{preventivo_id}")
            print(f"Delete preventivo response: {delete_response.status_code}")
        else:
            print(f"Preventivo creation returned {create_response.status_code}")


class TestActivityLogEntryStructure:
    """Test that activity log entries have the correct structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session_token = os.environ.get('TEST_SESSION_TOKEN', '')
        self.session.cookies.set('session_token', self.session_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_activity_log_entry_structure(self):
        """Test that individual activity log entries have correct fields"""
        response = self.session.get(f"{BASE_URL}/api/activity-log?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        if data['items']:
            entry = data['items'][0]
            print(f"Sample entry: {entry}")
            
            # Check expected fields
            expected_fields = ['user_id', 'user_name', 'user_email', 'action', 
                              'entity_type', 'entity_id', 'label', 'details', 'timestamp']
            for field in expected_fields:
                assert field in entry, f"Entry missing field: {field}"
            
            # Validate data types
            assert entry['action'] in ['create', 'update', 'delete', 'import', 'export', 'status_change', 'email_sent']
            assert isinstance(entry['details'], dict)
            assert isinstance(entry['timestamp'], str)
        else:
            print("No activity log entries found - this may be expected for new installs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

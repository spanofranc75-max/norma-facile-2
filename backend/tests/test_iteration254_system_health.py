"""
Iteration 254 — SystemHealthWidget & Outbound Audit Log Testing
Tests:
1. GET /api/dashboard/system-health endpoint returns correct data structure
2. Outbound audit log calls in sopralluogo.py, ddt.py, conto_lavoro.py, preventivi.py
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo mode session token
DEMO_TOKEN = "demo_session_token_normafacile"


class TestSystemHealthEndpoint:
    """Test GET /api/dashboard/system-health endpoint"""
    
    def test_system_health_requires_auth(self):
        """System health endpoint should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/system-health")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/dashboard/system-health returns 401 without auth")
    
    def test_system_health_with_demo_auth(self):
        """System health endpoint should return correct structure with demo auth"""
        headers = {"Authorization": f"Bearer {DEMO_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/system-health", headers=headers)
        
        # Should return 200 with demo token
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "data_counts" in data, "Missing 'data_counts' field"
        assert "company_settings" in data, "Missing 'company_settings' field"
        assert "outbound_activity" in data, "Missing 'outbound_activity' field"
        assert "warnings" in data, "Missing 'warnings' field"
        
        # Verify data_counts structure
        dc = data["data_counts"]
        assert "fatture" in dc, "Missing 'fatture' in data_counts"
        assert "preventivi" in dc, "Missing 'preventivi' in data_counts"
        assert "commesse" in dc, "Missing 'commesse' in data_counts"
        
        # Verify outbound_activity structure
        oa = data["outbound_activity"]
        assert "last_7d" in oa, "Missing 'last_7d' in outbound_activity"
        assert "last_24h" in oa, "Missing 'last_24h' in outbound_activity"
        
        # Verify company_settings structure
        cs = data["company_settings"]
        assert "complete" in cs, "Missing 'complete' in company_settings"
        
        print(f"PASS: /api/dashboard/system-health returns correct structure")
        print(f"  - data_counts: fatture={dc.get('fatture')}, preventivi={dc.get('preventivi')}, commesse={dc.get('commesse')}")
        print(f"  - outbound_activity: last_7d={oa.get('last_7d')}, last_24h={oa.get('last_24h')}")
        print(f"  - company_settings.complete={cs.get('complete')}")
        print(f"  - warnings count: {len(data.get('warnings', []))}")


class TestOutboundAuditLogCodeInspection:
    """Verify outbound audit log calls exist in route files via code inspection"""
    
    def test_sopralluogo_has_log_outbound(self):
        """sopralluogo.py should have log_outbound call with action_type 'email_perizia'"""
        with open('/app/backend/routes/sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Check import
        assert "from services.outbound_audit import log_outbound" in content, \
            "Missing import of log_outbound in sopralluogo.py"
        
        # Check call with email_perizia action type
        assert 'log_outbound' in content, "Missing log_outbound call in sopralluogo.py"
        assert '"email_perizia"' in content or "'email_perizia'" in content, \
            "Missing action_type 'email_perizia' in sopralluogo.py"
        
        print("PASS: sopralluogo.py has log_outbound call with action_type 'email_perizia'")
    
    def test_ddt_has_log_outbound(self):
        """ddt.py should have log_outbound call with action_type 'email_ddt'"""
        with open('/app/backend/routes/ddt.py', 'r') as f:
            content = f.read()
        
        # Check import
        assert "from services.outbound_audit import log_outbound" in content, \
            "Missing import of log_outbound in ddt.py"
        
        # Check call with email_ddt action type
        assert 'log_outbound' in content, "Missing log_outbound call in ddt.py"
        assert '"email_ddt"' in content or "'email_ddt'" in content, \
            "Missing action_type 'email_ddt' in ddt.py"
        
        print("PASS: ddt.py has log_outbound call with action_type 'email_ddt'")
    
    def test_conto_lavoro_has_log_outbound(self):
        """conto_lavoro.py should have log_outbound call with action_type 'email_conto_lavoro'"""
        with open('/app/backend/routes/conto_lavoro.py', 'r') as f:
            content = f.read()
        
        # Check import
        assert "from services.outbound_audit import log_outbound" in content, \
            "Missing import of log_outbound in conto_lavoro.py"
        
        # Check call with email_conto_lavoro action type
        assert 'log_outbound' in content, "Missing log_outbound call in conto_lavoro.py"
        assert '"email_conto_lavoro"' in content or "'email_conto_lavoro'" in content, \
            "Missing action_type 'email_conto_lavoro' in conto_lavoro.py"
        
        print("PASS: conto_lavoro.py has log_outbound call with action_type 'email_conto_lavoro'")
    
    def test_preventivi_has_log_outbound(self):
        """preventivi.py should have log_outbound call with action_type 'email_preventivo'"""
        with open('/app/backend/routes/preventivi.py', 'r') as f:
            content = f.read()
        
        # Check import
        assert "from services.outbound_audit import log_outbound" in content, \
            "Missing import of log_outbound in preventivi.py"
        
        # Check call with email_preventivo action type
        assert 'log_outbound' in content, "Missing log_outbound call in preventivi.py"
        assert '"email_preventivo"' in content or "'email_preventivo'" in content, \
            "Missing action_type 'email_preventivo' in preventivi.py"
        
        print("PASS: preventivi.py has log_outbound call with action_type 'email_preventivo'")


class TestOutboundAuditService:
    """Verify outbound_audit.py service exists and has correct structure"""
    
    def test_outbound_audit_service_exists(self):
        """outbound_audit.py should exist with log_outbound function"""
        with open('/app/backend/services/outbound_audit.py', 'r') as f:
            content = f.read()
        
        # Check function definition
        assert "async def log_outbound(" in content, \
            "Missing log_outbound function definition in outbound_audit.py"
        
        # Check required parameters
        assert "user_id:" in content, "Missing user_id parameter"
        assert "action_type:" in content, "Missing action_type parameter"
        assert "recipient:" in content, "Missing recipient parameter"
        assert "status:" in content, "Missing status parameter"
        
        # Check collection name
        assert 'outbound_audit_log' in content, "Missing collection name 'outbound_audit_log'"
        
        print("PASS: outbound_audit.py has correct log_outbound function structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

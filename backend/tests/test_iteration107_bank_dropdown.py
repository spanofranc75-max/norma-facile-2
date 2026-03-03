"""
Test iteration 107 - Bug fix for bank account dropdown in PreventivoEditorPage
The bug was: PreventivoEditorPage.js was calling /api/company/ (404) instead of /api/company/settings (correct).
Fix: Changed line 143 from apiRequest('/company/') to apiRequest('/company/settings').

Test cases:
1. GET /api/company/ should return 404 (old broken endpoint doesn't exist)
2. GET /api/company/settings should return 200 with bank_accounts array
3. PUT /api/company/settings should save bank_accounts correctly
4. GET /api/company/settings after PUT should return saved bank_accounts (persistence)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBankAccountDropdownBugFix:
    """Test that /api/company/settings returns bank_accounts correctly (Bug Fix Iteration 107)"""
    
    @pytest.fixture(scope="class")
    def test_session(self):
        """Create test user and session for authenticated requests"""
        import subprocess
        timestamp = str(int(__import__('time').time() * 1000))
        user_id = f"test-user-iter107-{timestamp}"
        session_token = f"test_session_iter107_{timestamp}"
        
        # Create user and session in MongoDB
        mongo_script = f"""
        use('test_database');
        db.users.insertOne({{
            user_id: '{user_id}',
            email: 'test.iter107.{timestamp}@example.com',
            name: 'Test User Iteration 107',
            role: 'admin',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{user_id}',
            session_token: '{session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        """
        subprocess.run(['mongosh', '--eval', mongo_script], capture_output=True)
        
        yield {
            'user_id': user_id,
            'session_token': session_token,
            'cookies': {'session_token': session_token}
        }
        
        # Cleanup after tests
        cleanup_script = f"""
        use('test_database');
        db.users.deleteMany({{ user_id: '{user_id}' }});
        db.user_sessions.deleteMany({{ session_token: '{session_token}' }});
        db.company_settings.deleteMany({{ user_id: '{user_id}' }});
        """
        subprocess.run(['mongosh', '--eval', cleanup_script], capture_output=True)
    
    def test_old_broken_endpoint_returns_404(self, test_session):
        """GET /api/company/ should return 404 (the old broken endpoint)"""
        response = requests.get(
            f"{BASE_URL}/api/company/",
            cookies=test_session['cookies']
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: /api/company/ returns 404 as expected (old broken endpoint)")
    
    def test_correct_endpoint_returns_200(self, test_session):
        """GET /api/company/settings should return 200 with bank_accounts"""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            cookies=test_session['cookies']
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'bank_accounts' in data, "Response should contain bank_accounts field"
        assert isinstance(data['bank_accounts'], list), "bank_accounts should be a list"
        print(f"PASS: /api/company/settings returns 200 with bank_accounts (count: {len(data['bank_accounts'])})")
    
    def test_put_saves_bank_accounts(self, test_session):
        """PUT /api/company/settings should save bank_accounts correctly"""
        test_bank_accounts = [
            {
                "account_id": f"ba_pytest_{uuid.uuid4().hex[:8]}",
                "bank_name": "Test Bank Pytest 1",
                "iban": "IT60X0542811101000000123456",
                "bic_swift": "PASCITM1XXX",
                "intestatario": "Test Company Pytest",
                "predefinito": True
            },
            {
                "account_id": f"ba_pytest_{uuid.uuid4().hex[:8]}",
                "bank_name": "Test Bank Pytest 2",
                "iban": "IT60X0542811101000000654321",
                "bic_swift": "UNCRITM1XXX",
                "intestatario": "Test Company Pytest",
                "predefinito": False
            }
        ]
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            json={"bank_accounts": test_bank_accounts},
            cookies=test_session['cookies']
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data['bank_accounts']) == 2, f"Expected 2 bank accounts, got {len(data['bank_accounts'])}"
        assert data['bank_accounts'][0]['bank_name'] == "Test Bank Pytest 1"
        assert data['bank_accounts'][1]['bank_name'] == "Test Bank Pytest 2"
        print("PASS: PUT /api/company/settings saves bank_accounts correctly")
    
    def test_get_after_put_returns_saved_data(self, test_session):
        """GET /api/company/settings after PUT should return saved bank_accounts"""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            cookies=test_session['cookies']
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data['bank_accounts']) == 2, "Bank accounts should persist after GET"
        assert data['bank_accounts'][0]['bank_name'] == "Test Bank Pytest 1"
        print("PASS: GET after PUT returns saved bank_accounts (data persisted)")
    
    def test_unauthenticated_request_returns_401(self):
        """GET /api/company/settings without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 401, f"Expected 401 for unauthenticated request, got {response.status_code}"
        print("PASS: Unauthenticated request returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

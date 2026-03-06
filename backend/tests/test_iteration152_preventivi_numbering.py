"""
Test iteration 152: Preventivi numbering and counting bug fixes
Tests:
1. POST /api/preventivi/ - counter syncs with max existing number before create
2. DELETE /api/preventivi/{id} - counter recalculates to max existing after delete
3. POST /api/preventivi/{id}/clone - counter syncs before generating new number
4. GET /api/preventivi/?limit=500 - verify limit accepts 500
5. GET /api/preventivi/ - verify response includes 'total' field
6. Counter gap prevention: create 3, delete last, create another - should reuse deleted number
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials for auth bypass via direct DB session
TEST_USER_PREFIX = "TEST_PREV_NUM_"


class TestPreventiviNumberingFixes:
    """Tests for preventivi numbering bug fixes"""
    
    session_token = None
    user_id = None
    created_preventivi = []
    
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup test user and session before each test class"""
        if TestPreventiviNumberingFixes.session_token is None:
            self._create_test_user_and_session()
        yield
        # Cleanup after all tests in class complete
        if request.node.name == request.session.items[-1].name:
            self._cleanup_test_data()
    
    def _create_test_user_and_session(self):
        """Create test user and session in DB"""
        import subprocess
        timestamp = int(time.time() * 1000)
        user_id = f"{TEST_USER_PREFIX}{timestamp}"
        session_token = f"session_prev_num_{timestamp}"
        
        # Create user and session via mongosh
        mongo_script = f"""
        use('test_database');
        db.users.insertOne({{
            user_id: '{user_id}',
            email: 'test.prev.num.{timestamp}@example.com',
            name: 'Test Preventivi Numbering',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{user_id}',
            session_token: '{session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        print('OK');
        """
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True, text=True
        )
        
        TestPreventiviNumberingFixes.user_id = user_id
        TestPreventiviNumberingFixes.session_token = session_token
        TestPreventiviNumberingFixes.created_preventivi = []
        print(f"Created test user: {user_id}, session: {session_token}")
    
    def _cleanup_test_data(self):
        """Cleanup test data after tests"""
        import subprocess
        if TestPreventiviNumberingFixes.user_id:
            user_id = TestPreventiviNumberingFixes.user_id
            mongo_script = f"""
            use('test_database');
            db.preventivi.deleteMany({{ user_id: '{user_id}' }});
            db.document_counters.deleteMany({{ counter_id: {{ $regex: '^PRV-{user_id}' }} }});
            db.users.deleteOne({{ user_id: '{user_id}' }});
            db.user_sessions.deleteOne({{ user_id: '{user_id}' }});
            print('Cleanup OK');
            """
            subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
            print(f"Cleaned up test data for user: {user_id}")
    
    def _get_headers(self):
        """Get headers with auth token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TestPreventiviNumberingFixes.session_token}"
        }
    
    def _create_preventivo(self, subject="Test Preventivo"):
        """Helper to create a preventivo"""
        payload = {
            "client_id": "test_client_123",
            "subject": subject,
            "lines": [
                {
                    "description": "Test item",
                    "quantity": 1,
                    "unit_price": 100,
                    "vat_rate": "22"
                }
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/preventivi/",
            json=payload,
            headers=self._get_headers()
        )
        if response.status_code == 201:
            data = response.json()
            TestPreventiviNumberingFixes.created_preventivi.append(data.get('preventivo_id'))
        return response
    
    def _extract_number(self, preventivo_number):
        """Extract numeric part from PRV-YYYY-NNNN format"""
        try:
            parts = preventivo_number.split('-')
            return int(parts[2])
        except (IndexError, ValueError):
            return 0
    
    # ── Test 1: List endpoint accepts limit=500 ──
    def test_01_list_accepts_limit_500(self):
        """GET /api/preventivi/?limit=500 should work (was capped at 100 before)"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/?limit=500",
            headers=self._get_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert 'preventivi' in data, "Response missing 'preventivi' field"
        print(f"TEST PASSED: limit=500 accepted, returned {len(data['preventivi'])} items")
    
    # ── Test 2: List endpoint returns 'total' field ──
    def test_02_list_returns_total_field(self):
        """GET /api/preventivi/ should return 'total' field with accurate count"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=self._get_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'total' in data, "Response missing 'total' field"
        assert isinstance(data['total'], int), "'total' field should be integer"
        print(f"TEST PASSED: 'total' field present with value {data['total']}")
    
    # ── Test 3: Create preventivo generates correct number ──
    def test_03_create_generates_sequential_number(self):
        """POST /api/preventivi/ should generate sequential number"""
        response = self._create_preventivo("Test Sequential #1")
        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()
        assert 'number' in data, "Response missing 'number' field"
        assert data['number'].startswith('PRV-'), f"Invalid number format: {data['number']}"
        print(f"TEST PASSED: Created preventivo with number {data['number']}")
    
    # ── Test 4: Counter gap prevention - the key bug fix test ──
    def test_04_counter_gap_prevention_create_delete_create(self):
        """
        Counter gap prevention scenario:
        1. Create 3 preventivi (get numbers N+1, N+2, N+3)
        2. Delete the last one (N+3)
        3. Create new preventivo - should get N+3 again (not N+4)
        """
        # Step 1: Create 3 preventivi
        prev1 = self._create_preventivo("Gap Test #1")
        assert prev1.status_code == 201, f"Create #1 failed: {prev1.text}"
        num1 = self._extract_number(prev1.json()['number'])
        
        prev2 = self._create_preventivo("Gap Test #2")
        assert prev2.status_code == 201, f"Create #2 failed: {prev2.text}"
        num2 = self._extract_number(prev2.json()['number'])
        
        prev3 = self._create_preventivo("Gap Test #3")
        assert prev3.status_code == 201, f"Create #3 failed: {prev3.text}"
        num3 = self._extract_number(prev3.json()['number'])
        prev3_id = prev3.json()['preventivo_id']
        prev3_number = prev3.json()['number']
        
        # Verify sequential numbering
        assert num2 == num1 + 1, f"Expected {num1 + 1}, got {num2}"
        assert num3 == num2 + 1, f"Expected {num2 + 1}, got {num3}"
        print(f"Created 3 preventivi: {num1}, {num2}, {num3}")
        
        # Step 2: Delete the last one
        delete_response = requests.delete(
            f"{BASE_URL}/api/preventivi/{prev3_id}",
            headers=self._get_headers()
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        # Remove from cleanup list since we deleted it
        TestPreventiviNumberingFixes.created_preventivi.remove(prev3_id)
        print(f"Deleted preventivo {prev3_number} (number {num3})")
        
        # Step 3: Create new preventivo - should reuse the deleted number
        prev4 = self._create_preventivo("Gap Test #4 (should reuse)")
        assert prev4.status_code == 201, f"Create #4 failed: {prev4.text}"
        num4 = self._extract_number(prev4.json()['number'])
        
        # The key assertion: new number should be same as deleted one (num3)
        assert num4 == num3, f"Counter gap detected! Expected {num3}, got {num4}. Counter should have been reset after delete."
        print(f"TEST PASSED: New preventivo got number {num4} (same as deleted {num3})")
    
    # ── Test 5: Delete recalculates counter ──
    def test_05_delete_recalculates_counter(self):
        """DELETE /api/preventivi/{id} should recalculate counter to max existing"""
        # Create a preventivo
        create_resp = self._create_preventivo("Delete Counter Test")
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        created_num = self._extract_number(create_resp.json()['number'])
        
        # Delete it
        delete_resp = requests.delete(
            f"{BASE_URL}/api/preventivi/{prev_id}",
            headers=self._get_headers()
        )
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        TestPreventiviNumberingFixes.created_preventivi.remove(prev_id)
        
        # Create another - should get same number as deleted
        create_resp2 = self._create_preventivo("After Delete")
        assert create_resp2.status_code == 201
        new_num = self._extract_number(create_resp2.json()['number'])
        
        assert new_num == created_num, f"Counter not reset after delete! Expected {created_num}, got {new_num}"
        print(f"TEST PASSED: Counter reset from {created_num} after delete, new preventivo got {new_num}")
    
    # ── Test 6: Clone also syncs counter ──
    def test_06_clone_syncs_counter(self):
        """POST /api/preventivi/{id}/clone should sync counter before generating new number"""
        # Create source preventivo
        source_resp = self._create_preventivo("Clone Source")
        assert source_resp.status_code == 201
        source_id = source_resp.json()['preventivo_id']
        source_num = self._extract_number(source_resp.json()['number'])
        
        # Clone it
        clone_resp = requests.post(
            f"{BASE_URL}/api/preventivi/{source_id}/clone",
            headers=self._get_headers()
        )
        assert clone_resp.status_code == 201, f"Clone failed: {clone_resp.text}"
        clone_data = clone_resp.json()
        clone_num = self._extract_number(clone_data['number'])
        TestPreventiviNumberingFixes.created_preventivi.append(clone_data['preventivo_id'])
        
        # Clone should have number = source + 1
        assert clone_num == source_num + 1, f"Clone numbering wrong! Source={source_num}, Clone={clone_num}, expected {source_num + 1}"
        print(f"TEST PASSED: Cloned preventivo got sequential number {clone_num} (source was {source_num})")
    
    # ── Test 7: Counter sync when counter is ahead ──
    def test_07_counter_sync_when_ahead(self):
        """
        Simulate scenario where counter is ahead of actual max number.
        This can happen when preventivi are deleted but counter wasn't reset (old bug).
        The fix should detect this and reset counter before creating new number.
        """
        import subprocess
        user_id = TestPreventiviNumberingFixes.user_id
        year = time.strftime('%Y')
        counter_id = f"PRV-{user_id}-{year}"
        
        # First, create a preventivo to establish baseline
        resp1 = self._create_preventivo("Baseline for counter ahead test")
        assert resp1.status_code == 201
        baseline_num = self._extract_number(resp1.json()['number'])
        
        # Manually set counter to be way ahead (simulating old bug state)
        ahead_value = baseline_num + 100
        mongo_script = f"""
        use('test_database');
        db.document_counters.updateOne(
            {{ counter_id: '{counter_id}' }},
            {{ $set: {{ counter: {ahead_value} }} }}
        );
        print('Counter set to {ahead_value}');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        print(f"Manually set counter to {ahead_value} (ahead of actual max {baseline_num})")
        
        # Create new preventivo - with the fix, it should detect counter is ahead
        # and reset to max existing number before incrementing
        resp2 = self._create_preventivo("After counter artificially advanced")
        assert resp2.status_code == 201
        new_num = self._extract_number(resp2.json()['number'])
        
        # The new number should be baseline + 1, NOT ahead_value + 1
        expected = baseline_num + 1
        assert new_num == expected, f"Counter sync failed! Counter was {ahead_value}, max existing was {baseline_num}, expected new number {expected}, got {new_num}"
        print(f"TEST PASSED: Counter was {ahead_value}, but new preventivo correctly got number {new_num} (max was {baseline_num})")
    
    # ── Test 8: Total field accuracy ──
    def test_08_total_field_accuracy(self):
        """Verify 'total' field in list response matches actual count"""
        # Get current count
        resp1 = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=self._get_headers()
        )
        assert resp1.status_code == 200
        initial_total = resp1.json()['total']
        initial_list_len = len(resp1.json()['preventivi'])
        
        # Create a new preventivo
        create_resp = self._create_preventivo("Total accuracy test")
        assert create_resp.status_code == 201
        
        # Get count again
        resp2 = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=self._get_headers()
        )
        assert resp2.status_code == 200
        new_total = resp2.json()['total']
        
        # Total should have increased by 1
        assert new_total == initial_total + 1, f"Total not updated correctly! Was {initial_total}, expected {initial_total + 1}, got {new_total}"
        print(f"TEST PASSED: Total field accurate - was {initial_total}, now {new_total}")
    
    # ── Test 9: List with high limit doesn't break ──
    def test_09_list_high_limit_works(self):
        """Verify API handles limit=1000 (max allowed per schema)"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/?limit=1000",
            headers=self._get_headers()
        )
        # Should either work or return validation error, not 500
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"
        if response.status_code == 200:
            print("TEST PASSED: limit=1000 accepted")
        else:
            print(f"TEST PASSED: limit=1000 properly rejected with 422")


class TestPreventiviEndpointBasics:
    """Basic endpoint tests for preventivi module"""
    
    session_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reuse session from previous class or create new"""
        if TestPreventiviNumberingFixes.session_token:
            TestPreventiviEndpointBasics.session_token = TestPreventiviNumberingFixes.session_token
        yield
    
    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TestPreventiviEndpointBasics.session_token}"
        }
    
    def test_list_endpoint_structure(self):
        """Verify list endpoint returns expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=self._get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert 'preventivi' in data, "Missing 'preventivi' array"
        assert 'total' in data, "Missing 'total' count"
        assert isinstance(data['preventivi'], list), "'preventivi' should be a list"
        assert isinstance(data['total'], int), "'total' should be an integer"
        
        print(f"TEST PASSED: List endpoint structure correct with {data['total']} total items")

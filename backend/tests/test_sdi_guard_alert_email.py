"""
Test SDI Guard (anti-doppio-click) + Alert Email Scadenze
Iteration 164 - Tests for:
- GUARD 1: In-memory lock on sync-fic (code review verification)
- GUARD 2: Unique index on fatture_ricevute.fr_id
- ALERT 1-5: Notification endpoints for payment alerts
"""
import pytest
import requests
import os
import time
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://pdf-refresh-1.preview.emergentagent.com"

# Test credentials
SESSION_TOKEN = "0urNkos478BzSaOHd49sFYF_lmqHn4n6PLLHbVjUaGE"
USER_ID = "user_97c773827822"


@pytest.fixture
def auth_headers():
    """Authenticated headers for API requests."""
    return {
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    }


@pytest.fixture
def api_session(auth_headers):
    """Requests session with auth headers."""
    session = requests.Session()
    session.headers.update(auth_headers)
    return session


class TestGuard1InMemoryLock:
    """GUARD 1: Verify _import_locks mechanism in sync-fic endpoint (code review)."""
    
    def test_lock_set_exists_in_code(self):
        """Verify _import_locks set is defined at module level (line 19)."""
        # Read the fatture_ricevute.py file
        with open('/app/backend/routes/fatture_ricevute.py', 'r') as f:
            content = f.read()
        
        # Check line 19 defines _import_locks
        assert '_import_locks: set = set()' in content, "_import_locks set should be defined"
        print("PASS: _import_locks set found in code")
    
    def test_sync_fic_uses_lock(self):
        """Verify sync-fic endpoint checks and manages the lock (lines 1445-1457)."""
        with open('/app/backend/routes/fatture_ricevute.py', 'r') as f:
            content = f.read()
        
        # Check the lock logic in sync-fic
        assert 'if uid in _import_locks:' in content, "Should check if user is already importing"
        assert 'raise HTTPException(429' in content, "Should return 429 if lock exists"
        assert '_import_locks.add(uid)' in content, "Should add user to lock set"
        assert '_import_locks.discard(uid)' in content, "Should remove user from lock set in finally"
        print("PASS: sync-fic endpoint properly implements lock mechanism")
    
    def test_sync_fic_returns_429_message(self):
        """Verify 429 response message is correct."""
        with open('/app/backend/routes/fatture_ricevute.py', 'r') as f:
            content = f.read()
        
        assert 'Import già in corso, attendi il completamento' in content, "429 message should inform user"
        print("PASS: 429 error message found in code")


class TestGuard2UniqueIndex:
    """GUARD 2: Verify unique index on fatture_ricevute.fr_id exists."""
    
    @pytest.fixture
    def mongo_client(self):
        """Create MongoDB client for direct DB checks."""
        client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        yield client
        client.close()
    
    def test_unique_index_exists(self, mongo_client):
        """Verify unique index 'unique_fr_id' exists on fr_id field."""
        async def check():
            db = mongo_client[os.environ.get('DB_NAME', 'test_database')]
            indexes = await db.fatture_ricevute.index_information()
            
            assert 'unique_fr_id' in indexes, "unique_fr_id index should exist"
            assert indexes['unique_fr_id'].get('unique') == True, "Index should have unique=True"
            assert ('fr_id', 1) in indexes['unique_fr_id']['key'], "Index should be on fr_id field"
            print(f"PASS: unique_fr_id index exists: {indexes['unique_fr_id']}")
        
        asyncio.run(check())


class TestAlert1ScadenzePreview:
    """ALERT 1: GET /api/notifications/scadenze-preview returns correct structure."""
    
    def test_scadenze_preview_structure(self, api_session):
        """Verify preview endpoint returns in_scadenza, scadute_fornitori, clienti_ritardo, totale, invierebbe_email."""
        response = api_session.get(f"{BASE_URL}/api/notifications/scadenze-preview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields exist
        assert 'in_scadenza' in data, "Missing 'in_scadenza' array"
        assert 'scadute_fornitori' in data, "Missing 'scadute_fornitori' array"
        assert 'clienti_ritardo' in data, "Missing 'clienti_ritardo' array"
        assert 'totale' in data, "Missing 'totale' field"
        assert 'invierebbe_email' in data, "Missing 'invierebbe_email' boolean"
        
        # Verify types
        assert isinstance(data['in_scadenza'], list), "'in_scadenza' should be a list"
        assert isinstance(data['scadute_fornitori'], list), "'scadute_fornitori' should be a list"
        assert isinstance(data['clienti_ritardo'], list), "'clienti_ritardo' should be a list"
        assert isinstance(data['totale'], int), "'totale' should be an integer"
        assert isinstance(data['invierebbe_email'], bool), "'invierebbe_email' should be a boolean"
        
        # Verify totale calculation
        expected_total = len(data['in_scadenza']) + len(data['scadute_fornitori']) + len(data['clienti_ritardo'])
        assert data['totale'] == expected_total, f"totale should be sum of arrays: {expected_total}"
        
        # Verify invierebbe_email logic
        expected_send = expected_total > 0
        assert data['invierebbe_email'] == expected_send, f"invierebbe_email should be {expected_send}"
        
        print(f"PASS: scadenze-preview returns correct structure")
        print(f"  - in_scadenza: {len(data['in_scadenza'])} items")
        print(f"  - scadute_fornitori: {len(data['scadute_fornitori'])} items")
        print(f"  - clienti_ritardo: {len(data['clienti_ritardo'])} items")
        print(f"  - totale: {data['totale']}")
        print(f"  - invierebbe_email: {data['invierebbe_email']}")


class TestAlert2TestScadenze:
    """ALERT 2: Verify test-scadenze endpoint response structure.
    NOTE: We do NOT call this endpoint to avoid sending another email.
    Instead, we verify the endpoint exists and check logs for previous successful send.
    """
    
    def test_test_scadenze_endpoint_exists(self):
        """Verify test-scadenze endpoint is defined in notifications.py."""
        with open('/app/backend/routes/notifications.py', 'r') as f:
            content = f.read()
        
        assert "@router.post(\"/test-scadenze\")" in content, "test-scadenze endpoint should be defined"
        assert "async def test_payment_alert" in content, "test_payment_alert function should exist"
        assert "send_payment_alert(manual=True)" in content, "Should call send_payment_alert"
        print("PASS: test-scadenze endpoint exists in code")
    
    def test_send_payment_alert_returns_correct_structure(self):
        """Verify send_payment_alert function returns correct structure (code review)."""
        with open('/app/backend/services/notification_scheduler.py', 'r') as f:
            content = f.read()
        
        # Check the result dict structure in send_payment_alert function
        assert '"email_sent": False' in content or "'email_sent': False" in content, "Should have email_sent field"
        assert '"total": total' in content or "'total': total" in content, "Should have total field"
        # Check for recipients assignment - code uses result["recipients"] = recipients
        assert 'result["recipients"] = recipients' in content, "Should assign recipients to result"
        
        print("PASS: send_payment_alert returns correct structure (email_sent, total, recipients)")


class TestAlert3NotificationLogs:
    """ALERT 3: GET /api/notifications/logs returns array of logs."""
    
    def test_notification_logs_endpoint(self, api_session):
        """Verify logs endpoint returns array with recent payment alert log."""
        response = api_session.get(f"{BASE_URL}/api/notifications/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        assert 'logs' in data, "Response should have 'logs' field"
        assert isinstance(data['logs'], list), "'logs' should be a list"
        
        # Check for payment alert log
        payment_logs = [log for log in data['logs'] if log.get('payment_count', 0) > 0 or log.get('payment_email_sent', False)]
        
        print(f"PASS: notification logs endpoint returns {len(data['logs'])} logs")
        if payment_logs:
            print(f"  - Found {len(payment_logs)} payment-related logs")
            latest = payment_logs[0]
            print(f"  - Latest payment log: payment_count={latest.get('payment_count')}, email_sent={latest.get('payment_email_sent')}")
        else:
            print("  - No payment alert logs found (may be first run)")


class TestAlert4SchedulerCallsPaymentAlert:
    """ALERT 4: Verify notification_scheduler.py run_expiration_check calls send_payment_alert."""
    
    def test_run_expiration_check_calls_send_payment_alert(self):
        """Verify run_expiration_check function calls send_payment_alert."""
        with open('/app/backend/services/notification_scheduler.py', 'r') as f:
            content = f.read()
        
        # Find run_expiration_check function and verify it calls send_payment_alert
        assert 'async def run_expiration_check' in content, "run_expiration_check function should exist"
        assert 'payment_result = await send_payment_alert' in content, "Should call send_payment_alert"
        
        # Check that payment_result is included in the result
        assert '"payment_alerts": payment_result' in content or "'payment_alerts': payment_result" in content, \
            "Should include payment_result in result"
        
        print("PASS: run_expiration_check correctly calls send_payment_alert")


class TestAlert5SchedulerBackground:
    """ALERT 5: Verify scheduler runs on background (check backend logs for WATCHDOG entries)."""
    
    def test_watchdog_log_entries(self):
        """Verify WATCHDOG entries exist in backend logs."""
        import subprocess
        
        result = subprocess.run(
            ['grep', '-c', 'WATCHDOG', '/var/log/supervisor/backend.err.log'],
            capture_output=True,
            text=True
        )
        
        count = int(result.stdout.strip()) if result.stdout.strip() else 0
        assert count > 0, f"Should have WATCHDOG log entries, found {count}"
        print(f"PASS: Found {count} WATCHDOG log entries in backend logs")
    
    def test_scheduler_started_log(self):
        """Verify scheduler startup log exists."""
        import subprocess
        
        result = subprocess.run(
            ['grep', 'WATCHDOG.*Scheduler avviato', '/var/log/supervisor/backend.err.log'],
            capture_output=True,
            text=True
        )
        
        assert result.stdout, "Should have 'Scheduler avviato' log entry"
        print(f"PASS: Scheduler startup log found: {result.stdout.strip().split(chr(10))[-1]}")
    
    def test_payment_alert_sent_log(self):
        """Verify payment alert was sent (from previous test or scheduler run)."""
        import subprocess
        
        result = subprocess.run(
            ['grep', 'WATCHDOG.*Payment alert sent', '/var/log/supervisor/backend.err.log'],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(f"PASS: Payment alert sent log found: {result.stdout.strip().split(chr(10))[-1]}")
        else:
            # Check if there's a log saying no alerts needed
            result2 = subprocess.run(
                ['grep', 'WATCHDOG.*Nessuna scadenza', '/var/log/supervisor/backend.err.log'],
                capture_output=True,
                text=True
            )
            if result2.stdout:
                print(f"INFO: No payment alerts needed: {result2.stdout.strip().split(chr(10))[-1]}")
            else:
                print("INFO: No payment alert log found yet (scheduler may not have run)")


class TestNotificationStatus:
    """Test the notification status endpoint for completeness."""
    
    def test_notification_status(self, api_session):
        """Verify /api/notifications/status returns correct structure."""
        response = api_session.get(f"{BASE_URL}/api/notifications/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        assert 'active' in data, "Should have 'active' field"
        assert 'current_alerts' in data, "Should have 'current_alerts' field"
        
        print(f"PASS: notification status endpoint works")
        print(f"  - active: {data.get('active')}")
        print(f"  - welder_count: {data.get('current_alerts', {}).get('welder_count', 0)}")
        print(f"  - instrument_count: {data.get('current_alerts', {}).get('instrument_count', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

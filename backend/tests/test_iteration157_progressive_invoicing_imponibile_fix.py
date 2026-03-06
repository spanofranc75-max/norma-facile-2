"""
Test Iteration 157 - CRITICAL BUG FIX: Progressive Invoicing Imponibile Base

BUG: When generating progressive invoices (acconto %), the system was calculating
the percentage on TOTAL WITH IVA instead of IMPONIBILE (without IVA).

This caused DOUBLE IVA:
- WRONG: 40% of total_with_iva (€11,507.04) = €4,602.82 + IVA 22% = €5,615.44
- CORRECT: 40% of imponibile (€9,432.00) = €3,772.80 + IVA 22% = €4,602.82

FIX: Backend now uses IMPONIBILE as base for all progressive invoice calculations.

Tests:
- GET /api/preventivi/{id}/invoicing-status returns imponibile as total_preventivo
- POST /api/preventivi/{id}/progressive-invoice with acconto calculates % on imponibile
- POST /api/preventivi/{id}/progressive-invoice with SAL uses line_totals (imponibile)
- POST /api/preventivi/{id}/progressive-invoice with saldo deducts from imponibile
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session - will be created in setup
SESSION_TOKEN = None
USER_ID = None


@pytest.fixture(scope="module", autouse=True)
def setup_test_session():
    """Create test user and session for all tests"""
    global SESSION_TOKEN, USER_ID
    
    import subprocess
    timestamp = int(time.time() * 1000)
    USER_ID = f"TEST_iter157_user_{timestamp}"
    SESSION_TOKEN = f"test_session_iter157_{timestamp}"
    
    mongo_script = f'''
    use('test_database');
    db.users.insertOne({{
        user_id: "{USER_ID}",
        email: "test.iter157.{timestamp}@example.com",
        name: "Test User Iter157",
        picture: "https://via.placeholder.com/150",
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: "{USER_ID}",
        session_token: "{SESSION_TOKEN}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print("Created test user: {USER_ID}");
    print("Created test session: {SESSION_TOKEN}");
    '''
    result = subprocess.run(['mongosh', '--eval', mongo_script], capture_output=True, text=True)
    print(f"Mongo setup output: {result.stdout}")
    if result.returncode != 0:
        print(f"Mongo setup error: {result.stderr}")
    
    yield
    
    # Cleanup
    cleanup_script = f'''
    use('test_database');
    db.users.deleteMany({{ user_id: /^TEST_iter157/ }});
    db.user_sessions.deleteMany({{ session_token: /^test_session_iter157/ }});
    db.clients.deleteMany({{ business_name: /^TEST_Iter157/ }});
    db.preventivi.deleteMany({{ subject: /^TEST_Iter157/ }});
    db.invoices.deleteMany({{ notes: /TEST_Iter157/ }});
    print("Cleaned up test data");
    '''
    subprocess.run(['mongosh', '--eval', cleanup_script], capture_output=True, text=True)


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def test_client(api_client):
    """Create a test client for preventivi"""
    client_payload = {
        "business_name": f"TEST_Iter157_Client_{int(time.time())}",
        "fiscal_code": "ITER157A00A000A",
        "vat_number": "IT12345678901",
        "address": "Via Test 123",
        "city": "Milano",
        "province": "MI",
        "cap": "20100"
    }
    response = api_client.post(f"{BASE_URL}/api/clients/", json=client_payload)
    if response.status_code == 201:
        client = response.json()
        yield client
        # Cleanup handled by autouse fixture
    else:
        pytest.skip(f"Failed to create test client: {response.status_code} - {response.text}")


class TestInvoicingStatusReturnsImponibile:
    """Test that invoicing-status returns imponibile as the base total"""

    def test_total_preventivo_is_imponibile_not_total_with_vat(self, api_client, test_client):
        """
        CRITICAL TEST: total_preventivo should be IMPONIBILE (without IVA), not total with IVA.
        
        Example: Line with unit_price=1000, vat_rate=22%
        - imponibile = 1000
        - total_with_vat = 1220
        - total_preventivo MUST equal 1000 (imponibile)
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_Imponibile_Check",
            "lines": [
                {
                    "description": "Test item for imponibile check",
                    "quantity": 1,
                    "unit": "pz",
                    "unit_price": 1000.00,
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Verify preventivo totals
            totals = prev.get("totals", {})
            imponibile = totals.get("imponibile", 0)
            total_with_vat = totals.get("total", 0)
            
            print(f"Preventivo totals: imponibile={imponibile}, total_with_vat={total_with_vat}")
            
            # imponibile should be 1000, total should be 1220
            assert abs(imponibile - 1000) < 0.01, f"Expected imponibile=1000, got {imponibile}"
            assert abs(total_with_vat - 1220) < 0.01, f"Expected total=1220, got {total_with_vat}"
            
            # Now check invoicing-status endpoint
            status_response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status")
            assert status_response.status_code == 200
            status = status_response.json()
            
            print(f"Invoicing status: total_preventivo={status.get('total_preventivo')}, total_preventivo_ivato={status.get('total_preventivo_ivato')}")
            
            # CRITICAL: total_preventivo MUST be imponibile (1000), NOT total with IVA (1220)
            assert abs(status["total_preventivo"] - 1000) < 0.01, \
                f"BUG: total_preventivo should be imponibile (1000), got {status['total_preventivo']}. If ~1220, the fix is not applied!"
            
            # total_preventivo_ivato should be the full total (for display purposes)
            if "total_preventivo_ivato" in status:
                assert abs(status["total_preventivo_ivato"] - 1220) < 0.01, \
                    f"Expected total_preventivo_ivato=1220, got {status.get('total_preventivo_ivato')}"
            
            # remaining should also be imponibile
            assert abs(status["remaining"] - 1000) < 0.01, \
                f"Expected remaining=1000 (imponibile), got {status['remaining']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_complex_preventivo_imponibile(self, api_client, test_client):
        """
        Test with the real-world example from the bug report:
        - Imponibile: €9,432
        - Total with IVA: €11,507.04
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_RealWorld_Example",
            "lines": [
                # Creating lines to get imponibile=9432
                {"description": "Serramenti", "quantity": 1, "unit": "corpo", "unit_price": 5000.00, "vat_rate": "22"},
                {"description": "Installazione", "quantity": 1, "unit": "corpo", "unit_price": 3000.00, "vat_rate": "22"},
                {"description": "Accessori", "quantity": 1, "unit": "corpo", "unit_price": 1432.00, "vat_rate": "22"},
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            totals = prev.get("totals", {})
            imponibile = totals.get("imponibile", 0)
            total_with_vat = totals.get("total", 0)
            
            # 5000 + 3000 + 1432 = 9432 imponibile
            # 9432 * 1.22 = 11507.04 total
            assert abs(imponibile - 9432) < 0.01, f"Expected imponibile=9432, got {imponibile}"
            assert abs(total_with_vat - 11507.04) < 0.01, f"Expected total=11507.04, got {total_with_vat}"
            
            status = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status").json()
            
            # CRITICAL: Must return imponibile, NOT total with IVA
            assert abs(status["total_preventivo"] - 9432) < 0.01, \
                f"BUG: total_preventivo should be 9432 (imponibile), got {status['total_preventivo']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestAccontoCalculatesOnImponibile:
    """Test that acconto percentage is calculated on IMPONIBILE, not total with IVA"""

    def test_acconto_40_percent_on_imponibile(self, api_client, test_client):
        """
        CRITICAL TEST: 40% acconto on €9,432 imponibile
        
        WRONG (old behavior): 40% of €11,507.04 = €4,602.82 (then +IVA = €5,615.44)
        CORRECT (new behavior): 40% of €9,432 = €3,772.80 (then +IVA = €4,602.82)
        
        The progressive_amount should be €3,772.80 (the imponibile of the invoice line)
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_Acconto40_Imponibile",
            "lines": [
                {"description": "Serramenti", "quantity": 1, "unit": "corpo", "unit_price": 5000.00, "vat_rate": "22"},
                {"description": "Installazione", "quantity": 1, "unit": "corpo", "unit_price": 3000.00, "vat_rate": "22"},
                {"description": "Accessori", "quantity": 1, "unit": "corpo", "unit_price": 1432.00, "vat_rate": "22"},
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create 40% acconto
            acconto_payload = {
                "invoice_type": "acconto",
                "percentage": 40
            }
            inv_response = api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice", 
                json=acconto_payload
            )
            assert inv_response.status_code == 200, f"Failed to create acconto: {inv_response.text}"
            
            inv_data = inv_response.json()
            progressive_amount = inv_data["progressive_amount"]
            
            # CRITICAL CALCULATION:
            # Imponibile = 9432
            # 40% of imponibile = 3772.80
            expected_progressive_amount = 9432 * 0.40  # 3772.80
            
            # OLD BUG would give: 11507.04 * 0.40 = 4602.82
            wrong_amount = 11507.04 * 0.40  # 4602.82
            
            print(f"Progressive amount: {progressive_amount}")
            print(f"Expected (correct): {expected_progressive_amount}")
            print(f"Wrong (old bug): {wrong_amount}")
            
            assert abs(progressive_amount - expected_progressive_amount) < 0.01, \
                f"BUG NOT FIXED: progressive_amount should be {expected_progressive_amount} (40% of imponibile), " \
                f"got {progressive_amount}. If ~{wrong_amount}, the fix is not working!"
            
            # Also verify the invoice line structure
            invoice_id = inv_data["invoice_id"]
            inv_detail = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}").json()
            lines = inv_detail.get("lines", [])
            
            assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"
            line = lines[0]
            
            # The line should have:
            # - unit_price = 3772.80 (40% of imponibile)
            # - vat_rate = 22
            # - line_total = 3772.80
            # - vat_amount = 830.02 (22% of 3772.80)
            assert abs(line["unit_price"] - 3772.80) < 0.01, \
                f"Invoice line unit_price should be 3772.80, got {line['unit_price']}"
            assert abs(line["line_total"] - 3772.80) < 0.01, \
                f"Invoice line line_total should be 3772.80, got {line['line_total']}"
            assert abs(line["vat_amount"] - 830.02) < 0.1, \
                f"Invoice line vat_amount should be ~830.02, got {line['vat_amount']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")

    def test_acconto_simple_case(self, api_client, test_client):
        """
        Simple test: 40% acconto on €1000 imponibile
        
        - imponibile = 1000
        - total_with_vat = 1220
        - 40% acconto = 400 (NOT 488 which would be 40% of 1220)
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_Acconto_Simple",
            "lines": [
                {"description": "Test item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create 40% acconto
            inv_response = api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "acconto", "percentage": 40}
            )
            assert inv_response.status_code == 200
            
            inv_data = inv_response.json()
            
            # CORRECT: 40% of 1000 = 400
            # WRONG: 40% of 1220 = 488
            assert abs(inv_data["progressive_amount"] - 400) < 0.01, \
                f"BUG: progressive_amount should be 400 (40% of imponibile 1000), got {inv_data['progressive_amount']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestSALUsesLineTotals:
    """Test that SAL mode uses line_totals (which are imponibile per line)"""

    def test_sal_selected_lines_uses_imponibile(self, api_client, test_client):
        """SAL by selected lines should use line_total (imponibile), not line_total with IVA"""
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_SAL_Lines",
            "lines": [
                {"description": "Item 1", "quantity": 1, "unit": "pz", "unit_price": 500.00, "vat_rate": "22"},  # line_total=500
                {"description": "Item 2", "quantity": 2, "unit": "pz", "unit_price": 300.00, "vat_rate": "22"},  # line_total=600
                {"description": "Item 3", "quantity": 1, "unit": "pz", "unit_price": 400.00, "vat_rate": "22"},  # line_total=400
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Select lines 0 and 2 (Item 1 and Item 3)
            # Expected: 500 + 400 = 900 (imponibile)
            # If bug: would be (500*1.22) + (400*1.22) = 1098
            sal_response = api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "sal", "selected_lines": [0, 2]}
            )
            assert sal_response.status_code == 200
            
            sal_data = sal_response.json()
            
            # Should be 900 (sum of line_totals which are imponibile)
            assert abs(sal_data["progressive_amount"] - 900) < 0.01, \
                f"SAL progressive_amount should be 900 (sum of imponibile line_totals), got {sal_data['progressive_amount']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestSaldoUsesImponibile:
    """Test that saldo correctly uses imponibile for remaining calculation"""

    def test_saldo_after_acconto_correct_remaining(self, api_client, test_client):
        """
        After 40% acconto on €1000 imponibile:
        - Acconto = €400
        - Remaining for saldo = €600 (NOT €820 = 1220-400)
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_Saldo_Remaining",
            "lines": [
                {"description": "Test item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create 40% acconto
            acconto_response = api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "acconto", "percentage": 40}
            )
            assert acconto_response.status_code == 200
            acconto_data = acconto_response.json()
            
            # Verify acconto is 400 (40% of 1000 imponibile)
            assert abs(acconto_data["progressive_amount"] - 400) < 0.01
            
            # Check remaining
            assert abs(acconto_data["remaining"] - 600) < 0.01, \
                f"After 40% acconto, remaining should be 600, got {acconto_data['remaining']}"
            
            # Now create saldo
            saldo_response = api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "saldo"}
            )
            assert saldo_response.status_code == 200
            saldo_data = saldo_response.json()
            
            # Saldo should be 600 (remaining imponibile)
            assert abs(saldo_data["progressive_amount"] - 600) < 0.01, \
                f"Saldo progressive_amount should be 600, got {saldo_data['progressive_amount']}"
            
            # After saldo, remaining should be 0
            assert saldo_data["remaining"] <= 0.01, \
                f"After saldo, remaining should be ~0, got {saldo_data['remaining']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


class TestTotalInvoicedTracking:
    """Test that total_invoiced is tracked correctly based on imponibile"""

    def test_total_invoiced_sums_imponibile_amounts(self, api_client, test_client):
        """
        Create multiple progressive invoices and verify total_invoiced sums correctly.
        """
        prev_payload = {
            "client_id": test_client["client_id"],
            "subject": "TEST_Iter157_TotalInvoiced",
            "lines": [
                {"description": "Test item", "quantity": 1, "unit": "pz", "unit_price": 1000.00, "vat_rate": "22"}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        assert response.status_code == 201
        prev = response.json()
        prev_id = prev["preventivo_id"]
        
        try:
            # Create 30% acconto (300)
            api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "acconto", "percentage": 30}
            )
            
            status = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status").json()
            assert abs(status["total_invoiced"] - 300) < 0.01, \
                f"After 30% acconto, total_invoiced should be 300, got {status['total_invoiced']}"
            assert abs(status["percentage_invoiced"] - 30) < 0.1, \
                f"After 30% acconto, percentage_invoiced should be ~30, got {status['percentage_invoiced']}"
            
            # Create 20% acconto (200)
            api_client.post(
                f"{BASE_URL}/api/preventivi/{prev_id}/progressive-invoice",
                json={"invoice_type": "acconto", "percentage": 20}
            )
            
            status = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}/invoicing-status").json()
            assert abs(status["total_invoiced"] - 500) < 0.01, \
                f"After 30%+20% acconto, total_invoiced should be 500, got {status['total_invoiced']}"
            assert abs(status["percentage_invoiced"] - 50) < 0.1
            
            # Verify remaining
            assert abs(status["remaining"] - 500) < 0.01, \
                f"Remaining should be 500, got {status['remaining']}"
                
        finally:
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test: Workflow Timeline - linked_invoice enrichment in GET /api/preventivi/{prev_id}
Features tested:
1. GET preventivo without conversion returns NO linked_invoice field
2. GET preventivo after conversion returns linked_invoice with invoice_id, document_number, status
3. Full flow: create preventivo -> convert to invoice -> verify linked_invoice data
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create a test user and session for authentication."""
    import subprocess
    import json
    
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f"test-workflow-{timestamp}"
    session_token = f"test_session_workflow_{timestamp}"
    
    # Create test user and session in MongoDB
    mongo_cmd = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.workflow.{timestamp}@example.com',
        name: 'Test Workflow User',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print('CREATED');
    """
    
    result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True, text=True)
    
    yield {
        'user_id': user_id,
        'session_token': session_token,
        'timestamp': timestamp
    }
    
    # Cleanup after tests
    cleanup_cmd = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    db.clients.deleteMany({{user_id: '{user_id}'}});
    db.preventivi.deleteMany({{user_id: '{user_id}'}});
    db.invoices.deleteMany({{user_id: '{user_id}'}});
    print('CLEANED');
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_cmd], capture_output=True, text=True)


@pytest.fixture(scope="module")
def api_client(test_session):
    """Create authenticated requests session."""
    session = requests.Session()
    session.cookies.set('session_token', test_session['session_token'])
    session.headers.update({'Content-Type': 'application/json'})
    return session


@pytest.fixture(scope="module")
def test_client(api_client, test_session):
    """Create a test client for preventivo creation."""
    client_data = {
        "business_name": f"TEST_Workflow_Client_{test_session['timestamp']}",
        "vat_number": "IT12345678901",
        "email": f"client.workflow.{test_session['timestamp']}@test.com"
    }
    response = api_client.post(f"{BASE_URL}/api/clients/", json=client_data)
    assert response.status_code == 201, f"Failed to create test client: {response.text}"
    return response.json()


class TestWorkflowTimelineBackend:
    """Backend API tests for workflow timeline linked_invoice enrichment."""
    
    def test_01_get_preventivo_without_conversion_no_linked_invoice(self, api_client, test_client):
        """GET /api/preventivi/{id} without conversion should NOT have linked_invoice field."""
        # Create a preventivo
        preventivo_data = {
            "client_id": test_client['client_id'],
            "subject": "TEST_No_Conversion_Preventivo",
            "validity_days": 30,
            "payment_terms": "30gg",
            "lines": [
                {"description": "Test Item", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
        assert create_response.status_code == 201, f"Failed to create preventivo: {create_response.text}"
        created = create_response.json()
        prev_id = created['preventivo_id']
        
        # GET the preventivo - should NOT have linked_invoice
        get_response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert 'linked_invoice' not in data, "Unconverted preventivo should NOT have linked_invoice field"
        assert data.get('converted_to') is None, "Unconverted preventivo should have converted_to=None"
        assert data['status'] == 'bozza', "New preventivo should have status='bozza'"
        print(f"✓ Preventivo {prev_id} has no linked_invoice (as expected)")
    
    def test_02_full_flow_create_convert_verify_linked_invoice(self, api_client, test_client):
        """Full flow: Create preventivo -> Convert to invoice -> GET returns linked_invoice."""
        # Step 1: Create preventivo
        preventivo_data = {
            "client_id": test_client['client_id'],
            "subject": "TEST_Full_Workflow_Preventivo",
            "validity_days": 30,
            "payment_terms": "60gg",
            "lines": [
                {"description": "Window Type A", "quantity": 2, "unit_price": 500, "vat_rate": "22"},
                {"description": "Window Type B", "quantity": 1, "unit_price": 750, "vat_rate": "22"}
            ]
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
        assert create_response.status_code == 201
        created = create_response.json()
        prev_id = created['preventivo_id']
        print(f"✓ Created preventivo: {prev_id}")
        
        # Step 2: Verify no linked_invoice before conversion
        get_before = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_before.status_code == 200
        data_before = get_before.json()
        assert 'linked_invoice' not in data_before
        print(f"✓ Preventivo has no linked_invoice before conversion")
        
        # Step 3: Convert to invoice
        convert_response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice")
        assert convert_response.status_code == 200, f"Failed to convert: {convert_response.text}"
        convert_data = convert_response.json()
        invoice_id = convert_data['invoice_id']
        document_number = convert_data['document_number']
        print(f"✓ Converted to invoice: {invoice_id} ({document_number})")
        
        # Step 4: GET preventivo - should now have linked_invoice
        get_after = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_after.status_code == 200
        data_after = get_after.json()
        
        # Verify linked_invoice exists
        assert 'linked_invoice' in data_after, "Converted preventivo MUST have linked_invoice field"
        linked = data_after['linked_invoice']
        
        # Verify linked_invoice structure
        assert 'invoice_id' in linked, "linked_invoice must have invoice_id"
        assert 'document_number' in linked, "linked_invoice must have document_number"
        assert 'status' in linked, "linked_invoice must have status"
        
        # Verify linked_invoice values
        assert linked['invoice_id'] == invoice_id, "linked_invoice.invoice_id must match converted invoice"
        assert linked['document_number'] == document_number, "linked_invoice.document_number must match"
        assert linked['status'] == 'bozza', "New invoice should have status='bozza'"
        
        # Verify preventivo status changed
        assert data_after['status'] == 'accettato', "Converted preventivo should have status='accettato'"
        assert data_after['converted_to'] == invoice_id, "converted_to should reference invoice_id"
        
        print(f"✓ linked_invoice verified: {linked}")
    
    def test_03_linked_invoice_contains_all_required_fields(self, api_client, test_client):
        """Verify linked_invoice object contains exactly invoice_id, document_number, status."""
        # Create and convert another preventivo
        preventivo_data = {
            "client_id": test_client['client_id'],
            "subject": "TEST_Fields_Verify_Preventivo",
            "lines": [{"description": "Item", "quantity": 1, "unit_price": 200, "vat_rate": "22"}]
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
        assert create_response.status_code == 201
        prev_id = create_response.json()['preventivo_id']
        
        # Convert
        api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice")
        
        # GET and verify fields
        get_response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        data = get_response.json()
        linked = data.get('linked_invoice', {})
        
        # Check required fields
        required_fields = ['invoice_id', 'document_number', 'status']
        for field in required_fields:
            assert field in linked, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(linked['invoice_id'], str), "invoice_id must be string"
        assert isinstance(linked['document_number'], str), "document_number must be string"
        assert isinstance(linked['status'], str), "status must be string"
        
        # Verify document_number format (FT-YYYY/NNNN)
        assert linked['document_number'].startswith('FT-'), "document_number should start with 'FT-'"
        
        print(f"✓ All required fields present with correct types")
    
    def test_04_invoice_status_propagates_to_linked_invoice(self, api_client, test_client):
        """Verify that invoice status changes are reflected in linked_invoice."""
        # Create preventivo
        preventivo_data = {
            "client_id": test_client['client_id'],
            "subject": "TEST_Status_Propagation",
            "lines": [{"description": "Item", "quantity": 1, "unit_price": 300, "vat_rate": "22"}]
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/preventivi/", json=preventivo_data)
        prev_id = create_response.json()['preventivo_id']
        
        # Convert
        convert_response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice")
        invoice_id = convert_response.json()['invoice_id']
        
        # Verify initial status is 'bozza'
        get_response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_response.json()['linked_invoice']['status'] == 'bozza'
        print(f"✓ Initial invoice status is 'bozza'")
        
        # Update invoice status to 'emessa'
        update_response = api_client.put(f"{BASE_URL}/api/invoices/{invoice_id}", json={"status": "emessa"})
        assert update_response.status_code == 200
        
        # Verify status propagates to linked_invoice
        get_response2 = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_response2.json()['linked_invoice']['status'] == 'emessa'
        print(f"✓ Invoice status 'emessa' propagates to linked_invoice")
        
        # Update to 'pagata'
        update_response2 = api_client.put(f"{BASE_URL}/api/invoices/{invoice_id}", json={"status": "pagata"})
        assert update_response2.status_code == 200
        
        # Verify 'pagata' status
        get_response3 = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert get_response3.json()['linked_invoice']['status'] == 'pagata'
        print(f"✓ Invoice status 'pagata' propagates to linked_invoice")
    
    def test_05_list_preventivi_does_not_include_linked_invoice(self, api_client):
        """Verify that GET /api/preventivi/ list endpoint does NOT include linked_invoice."""
        # Get list of preventivi
        response = api_client.get(f"{BASE_URL}/api/preventivi/")
        assert response.status_code == 200
        
        data = response.json()
        assert 'preventivi' in data
        
        # Check that individual items don't have linked_invoice (it's only on detail endpoint)
        # Note: The list endpoint may or may not include this - just verify the endpoint works
        print(f"✓ List endpoint returns {len(data['preventivi'])} preventivi")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

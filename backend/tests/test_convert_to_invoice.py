"""
Test Convert Preventivo to Invoice Feature.

Tests:
- POST /api/preventivi/{prev_id}/convert-to-invoice creates a new invoice from preventivo
- FT-YYYY/NNNN document number generation
- Line mapping (description, qty, price, vat)
- Preventivo status update to 'accettato' with converted_to link
- Invoice converted_from link to preventivo
- Response contains invoice_id and document_number
- 422 rejection when no client_id
- 409 rejection for duplicate conversion
- Invoice totals calculation (subtotal, total_vat, total_document)
- Invoice appears in GET /api/invoices/ list
"""
import pytest
import requests
import os
from datetime import datetime
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://norma-facile-erp.preview.emergentagent.com'


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated requests."""
    import subprocess
    
    timestamp = int(time.time() * 1000)
    user_id = f'test-conv-{timestamp}'
    session_token = f'test_conv_session_{timestamp}'
    
    # Create user and session
    mongo_cmd = f'''
    use('test_database');
    db.users.insertOne({{
      user_id: '{user_id}',
      email: 'test.conv.{timestamp}@example.com',
      name: 'Test Convert User',
      picture: 'https://via.placeholder.com/150',
      created_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: '{user_id}',
      session_token: '{session_token}',
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    '''
    subprocess.run(['mongosh', '--eval', mongo_cmd], capture_output=True)
    
    yield {'user_id': user_id, 'session_token': session_token}
    
    # Cleanup
    cleanup_cmd = f'''
    use('test_database');
    db.users.deleteOne({{ user_id: '{user_id}' }});
    db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
    db.preventivi.deleteMany({{ user_id: '{user_id}' }});
    db.invoices.deleteMany({{ user_id: '{user_id}' }});
    db.clients.deleteMany({{ user_id: '{user_id}' }});
    '''
    subprocess.run(['mongosh', '--eval', cleanup_cmd], capture_output=True)


@pytest.fixture
def auth_session(test_session):
    """Get requests session with authentication cookie."""
    session = requests.Session()
    session.cookies.set('session_token', test_session['session_token'])
    session.headers.update({'Content-Type': 'application/json'})
    return session


@pytest.fixture
def test_client(auth_session):
    """Create a test client for conversion tests."""
    client_payload = {
        'business_name': 'TEST_Client for Conversion',
        'vat_number': 'IT12345678901',
        'tax_code': 'TSTCNV80A01H501X',
        'client_type': 'azienda',  # Valid values: 'azienda', 'privato', 'pa'
        'address': 'Via Test 123',
        'city': 'Milano',
        'province': 'MI',
        'postal_code': '20100',
        'email': 'test.client@example.com'
    }
    response = auth_session.post(f'{BASE_URL}/api/clients/', json=client_payload)
    assert response.status_code == 201, f"Failed to create client: {response.text}"
    return response.json()


# ── Test: Convert to Invoice - Happy Path ─────────────────────────

class TestConvertToInvoiceHappyPath:
    """Test successful conversion of preventivo to invoice."""
    
    def test_convert_basic_preventivo(self, auth_session, test_client):
        """POST convert-to-invoice creates invoice with correct data."""
        # Step 1: Create a preventivo with 2 lines
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Preventivo for conversion',
            'validity_days': 30,
            'payment_terms': '30gg',
            'notes': 'Note del preventivo',
            'lines': [
                {
                    'description': 'Finestra PVC 120x140',
                    'dimensions': '120x140',
                    'quantity': 2,
                    'unit': 'pz',
                    'unit_price': 450.00,
                    'vat_rate': '22'
                },
                {
                    'description': 'Porta ingresso',
                    'dimensions': '90x210',
                    'quantity': 1,
                    'unit': 'pz',
                    'unit_price': 800.00,
                    'vat_rate': '22'
                }
            ]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201, f"Failed to create preventivo: {prev_response.text}"
        preventivo = prev_response.json()
        prev_id = preventivo['preventivo_id']
        prev_number = preventivo['number']
        
        print(f"✓ Created preventivo: {prev_number} (id={prev_id})")
        
        # Step 2: Convert to invoice
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200, f"Conversion failed: {convert_response.text}"
        
        convert_data = convert_response.json()
        
        # Verify response contains required fields
        assert 'invoice_id' in convert_data, "Response missing invoice_id"
        assert 'document_number' in convert_data, "Response missing document_number"
        assert 'message' in convert_data, "Response missing message"
        
        invoice_id = convert_data['invoice_id']
        doc_number = convert_data['document_number']
        
        print(f"✓ Conversion successful: {doc_number} (id={invoice_id})")
        
        # Verify document number format FT-YYYY/NNNN
        current_year = datetime.now().year
        assert doc_number.startswith('FT-'), f"Document number should start with FT-, got {doc_number}"
        assert f'FT-{current_year}/' in doc_number, f"Document number should contain year, got {doc_number}"
        
        print(f"✓ Document number format correct: {doc_number}")
        
        return invoice_id, prev_id
    
    def test_invoice_lines_mapping(self, auth_session, test_client):
        """Verify that preventivo lines are correctly mapped to invoice lines."""
        # Create preventivo with specific line data
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Line mapping test',
            'lines': [
                {
                    'description': 'Serramento alluminio',
                    'quantity': 3,
                    'unit_price': 550.00,
                    'vat_rate': '22'
                },
                {
                    'description': 'Porta scorrevole',
                    'quantity': 2,
                    'unit_price': 1200.00,
                    'vat_rate': '10'
                }
            ]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        prev_lines = prev_response.json()['lines']
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        
        # Get invoice and verify lines
        invoice_response = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}')
        assert invoice_response.status_code == 200
        invoice = invoice_response.json()
        
        # Verify number of lines
        assert len(invoice['lines']) == 2, f"Expected 2 lines, got {len(invoice['lines'])}"
        
        # Verify line data mapping
        for i, inv_line in enumerate(invoice['lines']):
            prev_line = prev_lines[i]
            assert inv_line['description'] == prev_line['description'], f"Line {i} description mismatch"
            assert float(inv_line['quantity']) == float(prev_line['quantity']), f"Line {i} quantity mismatch"
            assert float(inv_line['unit_price']) == float(prev_line['unit_price']), f"Line {i} unit_price mismatch"
            assert inv_line['vat_rate'] == prev_line['vat_rate'], f"Line {i} vat_rate mismatch"
        
        print(f"✓ All {len(invoice['lines'])} lines correctly mapped from preventivo to invoice")
    
    def test_invoice_totals_calculation(self, auth_session, test_client):
        """Verify invoice totals are correctly calculated."""
        # Create preventivo
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Totals test',
            'lines': [
                {
                    'description': 'Item 1',
                    'quantity': 2,
                    'unit_price': 100.00,
                    'vat_rate': '22'  # 200 * 22% = 44
                },
                {
                    'description': 'Item 2',
                    'quantity': 1,
                    'unit_price': 500.00,
                    'vat_rate': '10'  # 500 * 10% = 50
                }
            ]
        }
        # Expected: subtotal = 200 + 500 = 700
        # Expected: total_vat = 44 + 50 = 94
        # Expected: total_document = 700 + 94 = 794
        
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        
        # Get invoice and verify totals
        invoice_response = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}')
        assert invoice_response.status_code == 200
        invoice = invoice_response.json()
        
        totals = invoice['totals']
        assert float(totals['subtotal']) == 700.00, f"Expected subtotal 700, got {totals['subtotal']}"
        assert float(totals['total_vat']) == 94.00, f"Expected total_vat 94, got {totals['total_vat']}"
        assert float(totals['total_document']) == 794.00, f"Expected total_document 794, got {totals['total_document']}"
        
        print(f"✓ Invoice totals correct: subtotal={totals['subtotal']}, VAT={totals['total_vat']}, total={totals['total_document']}")
    
    def test_preventivo_marked_as_accettato(self, auth_session, test_client):
        """Verify preventivo status is set to 'accettato' after conversion."""
        # Create preventivo
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Status update test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # Verify initial status is 'bozza'
        get_prev = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}')
        assert get_prev.json()['status'] == 'bozza', "Initial status should be 'bozza'"
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        
        # Verify preventivo status is now 'accettato'
        get_prev_after = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}')
        assert get_prev_after.status_code == 200
        prev_after = get_prev_after.json()
        
        assert prev_after['status'] == 'accettato', f"Expected status 'accettato', got {prev_after['status']}"
        assert prev_after.get('converted_to') == invoice_id, f"Expected converted_to={invoice_id}, got {prev_after.get('converted_to')}"
        
        print(f"✓ Preventivo status updated to 'accettato' with converted_to={invoice_id}")
    
    def test_invoice_converted_from_link(self, auth_session, test_client):
        """Verify invoice has converted_from link to preventivo."""
        # Create preventivo
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Converted from test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        
        # Verify invoice converted_from
        invoice_response = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}')
        assert invoice_response.status_code == 200
        invoice = invoice_response.json()
        
        assert invoice.get('converted_from') == prev_id, f"Expected converted_from={prev_id}, got {invoice.get('converted_from')}"
        
        print(f"✓ Invoice converted_from correctly set to {prev_id}")
    
    def test_invoice_appears_in_list(self, auth_session, test_client):
        """Verify converted invoice appears in GET /api/invoices/ list."""
        # Create preventivo
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Invoice list test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        doc_number = convert_response.json()['document_number']
        
        # Get invoices list
        list_response = auth_session.get(f'{BASE_URL}/api/invoices/')
        assert list_response.status_code == 200
        invoices_data = list_response.json()
        
        # Find our invoice in the list
        invoice_ids = [inv['invoice_id'] for inv in invoices_data['invoices']]
        assert invoice_id in invoice_ids, f"Invoice {invoice_id} not found in list"
        
        # Verify document type is 'FT' (fattura enum value)
        our_invoice = next(inv for inv in invoices_data['invoices'] if inv['invoice_id'] == invoice_id)
        assert our_invoice['document_type'] == 'FT', f"Expected document_type 'FT', got {our_invoice['document_type']}"
        
        print(f"✓ Invoice {doc_number} appears in GET /api/invoices/ list")
    
    def test_invoice_notes_include_preventivo_reference(self, auth_session, test_client):
        """Verify invoice notes include reference to preventivo number."""
        # Create preventivo with notes
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Notes reference test',
            'notes': 'Note originali del preventivo',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        prev_number = prev_response.json()['number']
        
        # Convert
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 200
        invoice_id = convert_response.json()['invoice_id']
        
        # Verify invoice notes contain preventivo reference
        invoice_response = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}')
        assert invoice_response.status_code == 200
        invoice = invoice_response.json()
        
        notes = invoice.get('notes', '')
        assert prev_number in notes, f"Invoice notes should reference preventivo {prev_number}, got: {notes}"
        assert 'Riferimento preventivo' in notes, f"Invoice notes should contain 'Riferimento preventivo', got: {notes}"
        
        print(f"✓ Invoice notes include reference to preventivo {prev_number}")


# ── Test: Convert to Invoice - Error Cases ────────────────────────

class TestConvertToInvoiceErrors:
    """Test error handling for convert-to-invoice endpoint."""
    
    def test_convert_without_client_returns_422(self, auth_session):
        """Convert-to-invoice rejects preventivo without client (422)."""
        # Create preventivo WITHOUT client_id
        preventivo_payload = {
            'subject': 'TEST_No client test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # Try to convert - should fail with 422
        convert_response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert_response.status_code == 422, f"Expected 422, got {convert_response.status_code}: {convert_response.text}"
        
        error_detail = convert_response.json().get('detail', '')
        assert 'cliente' in error_detail.lower() or 'client' in error_detail.lower(), \
            f"Error message should mention client, got: {error_detail}"
        
        print(f"✓ Conversion without client correctly rejected with 422: {error_detail}")
    
    def test_duplicate_conversion_returns_409(self, auth_session, test_client):
        """Convert-to-invoice rejects duplicate conversion (409)."""
        # Create preventivo
        preventivo_payload = {
            'client_id': test_client['client_id'],
            'subject': 'TEST_Duplicate conversion test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        }
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=preventivo_payload)
        assert prev_response.status_code == 201
        prev_id = prev_response.json()['preventivo_id']
        
        # First conversion - should succeed
        convert1 = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert1.status_code == 200, f"First conversion should succeed: {convert1.text}"
        invoice1_id = convert1.json()['invoice_id']
        
        # Second conversion - should fail with 409
        convert2 = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        assert convert2.status_code == 409, f"Expected 409 for duplicate, got {convert2.status_code}: {convert2.text}"
        
        error_detail = convert2.json().get('detail', '')
        assert 'convertito' in error_detail.lower() or 'gia' in error_detail.lower() or invoice1_id in error_detail, \
            f"Error message should indicate already converted, got: {error_detail}"
        
        print(f"✓ Duplicate conversion correctly rejected with 409: {error_detail}")
    
    def test_convert_nonexistent_preventivo_returns_404(self, auth_session):
        """Convert-to-invoice returns 404 for nonexistent preventivo."""
        response = auth_session.post(f'{BASE_URL}/api/preventivi/prev_nonexistent123/convert-to-invoice')
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Conversion of nonexistent preventivo returns 404")
    
    def test_convert_requires_authentication(self):
        """Convert-to-invoice requires authentication (401)."""
        response = requests.post(f'{BASE_URL}/api/preventivi/prev_test/convert-to-invoice')
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Convert-to-invoice requires authentication (401)")


# ── Test: Invoice Properties ──────────────────────────────────────

class TestInvoiceProperties:
    """Verify invoice properties set by conversion."""
    
    def test_invoice_document_type_is_fattura(self, auth_session, test_client):
        """Verify converted invoice has document_type='fattura'."""
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json={
            'client_id': test_client['client_id'],
            'subject': 'TEST_Doc type test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        })
        prev_id = prev_response.json()['preventivo_id']
        
        convert = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        invoice_id = convert.json()['invoice_id']
        
        invoice = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}').json()
        assert invoice['document_type'] == 'FT', f"Expected document_type 'FT', got {invoice['document_type']}"
        
        print("✓ Invoice document_type is 'FT' (fattura)")
    
    def test_invoice_status_is_bozza(self, auth_session, test_client):
        """Verify converted invoice has status='bozza'."""
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json={
            'client_id': test_client['client_id'],
            'subject': 'TEST_Status test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        })
        prev_id = prev_response.json()['preventivo_id']
        
        convert = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        invoice_id = convert.json()['invoice_id']
        
        invoice = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}').json()
        assert invoice['status'] == 'bozza', f"Expected status 'bozza', got {invoice['status']}"
        
        print("✓ Invoice status is 'bozza'")
    
    def test_invoice_payment_method_is_bonifico(self, auth_session, test_client):
        """Verify converted invoice has payment_method='bonifico'."""
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json={
            'client_id': test_client['client_id'],
            'subject': 'TEST_Payment method test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        })
        prev_id = prev_response.json()['preventivo_id']
        
        convert = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        invoice_id = convert.json()['invoice_id']
        
        invoice = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}').json()
        assert invoice['payment_method'] == 'bonifico', f"Expected payment_method 'bonifico', got {invoice['payment_method']}"
        
        print("✓ Invoice payment_method is 'bonifico'")
    
    def test_invoice_client_id_matches(self, auth_session, test_client):
        """Verify invoice has same client_id as preventivo."""
        prev_response = auth_session.post(f'{BASE_URL}/api/preventivi/', json={
            'client_id': test_client['client_id'],
            'subject': 'TEST_Client match test',
            'lines': [{'description': 'Item', 'quantity': 1, 'unit_price': 100}]
        })
        prev_id = prev_response.json()['preventivo_id']
        
        convert = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice')
        invoice_id = convert.json()['invoice_id']
        
        invoice = auth_session.get(f'{BASE_URL}/api/invoices/{invoice_id}').json()
        assert invoice['client_id'] == test_client['client_id'], \
            f"Expected client_id {test_client['client_id']}, got {invoice['client_id']}"
        
        print(f"✓ Invoice client_id matches preventivo: {test_client['client_id']}")


# ── Run Tests ─────────────────────────────────────────────────────

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

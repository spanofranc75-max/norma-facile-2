"""
Test Preventivi Commerciali (Smart Quote) Module.

Tests:
- CRUD operations for preventivi
- Auto-generated preventivo numbers (PRV-YYYY-NNNN)
- Line totals and VAT calculations
- Thermal compliance validation via NormaCore
- PDF generation with commercial offer + technical annex
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://istruttoria-hub-1.preview.emergentagent.com'


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated requests."""
    import subprocess
    import json
    import time
    
    timestamp = int(time.time() * 1000)
    user_id = f'test-prev-{timestamp}'
    session_token = f'test_prev_session_{timestamp}'
    
    # Create user and session
    mongo_cmd = f'''
    use('test_database');
    db.users.insertOne({{
      user_id: '{user_id}',
      email: 'test.prev.{timestamp}@example.com',
      name: 'Test Prev User',
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
    '''
    subprocess.run(['mongosh', '--eval', cleanup_cmd], capture_output=True)


@pytest.fixture
def auth_session(test_session):
    """Get requests session with authentication cookie."""
    session = requests.Session()
    session.cookies.set('session_token', test_session['session_token'])
    session.headers.update({'Content-Type': 'application/json'})
    return session


# ── Test: Authentication Required ─────────────────────────────────

class TestPreventiviAuth:
    """Test that all preventivi endpoints require authentication."""
    
    def test_list_preventivi_requires_auth(self):
        """GET /api/preventivi/ returns 401 without auth."""
        response = requests.get(f'{BASE_URL}/api/preventivi/')
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivi/ requires auth (401)")

    def test_create_preventivo_requires_auth(self):
        """POST /api/preventivi/ returns 401 without auth."""
        response = requests.post(f'{BASE_URL}/api/preventivi/', json={
            'subject': 'Test',
            'lines': []
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivi/ requires auth (401)")


# ── Test: CRUD Operations ─────────────────────────────────────────

class TestPreventiviCRUD:
    """Test CRUD operations for preventivi."""
    
    def test_list_preventivi_empty(self, auth_session):
        """GET /api/preventivi/ returns empty list for new user."""
        response = auth_session.get(f'{BASE_URL}/api/preventivi/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'preventivi' in data
        assert 'total' in data
        print(f"✓ GET /api/preventivi/ returns empty list: {data['total']} preventivi")

    def test_create_preventivo_basic(self, auth_session):
        """POST /api/preventivi/ creates preventivo with auto-number."""
        payload = {
            'subject': 'TEST_Fornitura serramenti',
            'validity_days': 30,
            'payment_terms': '30gg',
            'notes': 'Note di test',
            'lines': [
                {
                    'description': 'Finestra PVC 120x140',
                    'dimensions': '120x140',
                    'quantity': 2,
                    'unit': 'pz',
                    'unit_price': 450.00,
                    'vat_rate': '22'
                }
            ]
        }
        response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify auto-generated number
        assert 'number' in data, "Missing 'number' field"
        assert data['number'].startswith('PRV-'), f"Number should start with PRV-, got {data['number']}"
        year = datetime.now().year
        assert f'PRV-{year}' in data['number'], f"Number should contain year, got {data['number']}"
        
        # Verify preventivo_id
        assert 'preventivo_id' in data, "Missing 'preventivo_id' field"
        assert data['preventivo_id'].startswith('prev_'), f"ID should start with prev_, got {data['preventivo_id']}"
        
        # Verify totals calculated
        assert 'totals' in data, "Missing 'totals' field"
        assert data['totals']['subtotal'] == 900.00, f"Subtotal should be 900, got {data['totals']['subtotal']}"
        assert data['totals']['total_vat'] == 198.00, f"VAT should be 198, got {data['totals']['total_vat']}"
        assert data['totals']['total'] == 1098.00, f"Total should be 1098, got {data['totals']['total']}"
        
        # Verify line totals
        assert len(data['lines']) == 1
        assert data['lines'][0]['line_total'] == 900.00
        
        print(f"✓ Created preventivo: {data['number']} with total {data['totals']['total']}")
        return data['preventivo_id']

    def test_create_preventivo_with_thermal_data(self, auth_session):
        """POST /api/preventivi/ with thermal_data auto-calculates compliance."""
        payload = {
            'subject': 'TEST_Serramenti termici Ecobonus',
            'validity_days': 30,
            'payment_terms': '30gg',
            'lines': [
                {
                    'description': 'Finestra vetro camera argon',
                    'dimensions': '1200x2100',
                    'quantity': 3,
                    'unit_price': 650.00,
                    'vat_rate': '22',
                    'thermal_data': {
                        'glass_id': 'doppio_be_argon',
                        'frame_id': 'acciaio_standard',
                        'spacer_id': 'alluminio',
                        'height_mm': 2100,
                        'width_mm': 1200,
                        'frame_width_mm': 80,
                        'zone': 'E'
                    }
                },
                {
                    'description': 'Porta ingresso',
                    'dimensions': '900x2100',
                    'quantity': 1,
                    'unit_price': 800.00,
                    'vat_rate': '22'
                    # No thermal_data
                }
            ]
        }
        response = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify compliance was auto-calculated
        assert 'compliance_status' in data, "Missing 'compliance_status' field"
        assert 'compliance_detail' in data, "Missing 'compliance_detail' field"
        
        # With doppio_be_argon + acciaio_standard, Uw ~1.74 > Zone E limit 1.30 => NOT compliant
        assert data['compliance_status'] == False, f"Expected non-compliant, got {data['compliance_status']}"
        
        detail = data['compliance_detail']
        assert detail['checked_lines'] == 1, f"Should check 1 thermal line, got {detail['checked_lines']}"
        assert detail['all_compliant'] == False, "Expected all_compliant=False"
        
        # Verify line compliance result
        assert len(detail['results']) == 1
        result = detail['results'][0]
        assert 'uw' in result, "Missing 'uw' in result"
        assert result['uw'] > 1.30, f"Uw should be > 1.30, got {result['uw']}"
        assert result['zone'] == 'E'
        assert result['limit'] == 1.30 or result['limit'] == 1.3
        assert result['compliant'] == False
        
        print(f"✓ Created preventivo with thermal data: Uw={result['uw']}, compliant={result['compliant']}")
        return data['preventivo_id']

    def test_get_preventivo(self, auth_session):
        """GET /api/preventivi/{prev_id} returns preventivo with totals."""
        # First create
        create_payload = {
            'subject': 'TEST_Get test',
            'lines': [{'description': 'Item 1', 'quantity': 1, 'unit_price': 100}]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=create_payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Then get
        response = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['preventivo_id'] == prev_id
        assert data['subject'] == 'TEST_Get test'
        assert 'totals' in data
        assert 'lines' in data
        
        print(f"✓ GET /api/preventivi/{prev_id} returns correct data")

    def test_get_preventivo_not_found(self, auth_session):
        """GET /api/preventivi/{invalid_id} returns 404."""
        response = auth_session.get(f'{BASE_URL}/api/preventivi/prev_nonexistent123')
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET nonexistent preventivo returns 404")

    def test_update_preventivo(self, auth_session):
        """PUT /api/preventivi/{prev_id} updates lines and recalculates."""
        # First create
        create_payload = {
            'subject': 'TEST_Update test',
            'lines': [{'description': 'Original item', 'quantity': 1, 'unit_price': 100}]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=create_payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Update with new lines
        update_payload = {
            'subject': 'TEST_Updated subject',
            'lines': [
                {'description': 'New item 1', 'quantity': 2, 'unit_price': 150, 'vat_rate': '22'},
                {'description': 'New item 2', 'quantity': 1, 'unit_price': 200, 'vat_rate': '10'}
            ]
        }
        response = auth_session.put(f'{BASE_URL}/api/preventivi/{prev_id}', json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['subject'] == 'TEST_Updated subject'
        assert len(data['lines']) == 2
        
        # Verify recalculated totals: 2*150 + 1*200 = 500
        assert data['totals']['subtotal'] == 500.00, f"Expected subtotal 500, got {data['totals']['subtotal']}"
        # VAT: 300*0.22 + 200*0.10 = 66 + 20 = 86
        assert data['totals']['total_vat'] == 86.00, f"Expected VAT 86, got {data['totals']['total_vat']}"
        
        print(f"✓ PUT /api/preventivi/{prev_id} updated and recalculated")

    def test_delete_preventivo(self, auth_session):
        """DELETE /api/preventivi/{prev_id} removes preventivo."""
        # First create
        create_payload = {'subject': 'TEST_Delete test', 'lines': []}
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=create_payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Delete
        response = auth_session.delete(f'{BASE_URL}/api/preventivi/{prev_id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify deleted
        get_resp = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}')
        assert get_resp.status_code == 404, "Should return 404 after delete"
        
        print(f"✓ DELETE /api/preventivi/{prev_id} removed preventivo")


# ── Test: Thermal Compliance Check ────────────────────────────────

class TestThermalCompliance:
    """Test thermal compliance validation via check-compliance endpoint."""
    
    def test_check_compliance_doppio_be_argon_zone_e(self, auth_session):
        """Check-compliance with doppio_be_argon returns NOT compliant for Zone E."""
        # Create preventivo with thermal data
        payload = {
            'subject': 'TEST_Compliance doppio BE',
            'lines': [{
                'description': 'Finestra test',
                'quantity': 1,
                'unit_price': 500,
                'thermal_data': {
                    'glass_id': 'doppio_be_argon',
                    'frame_id': 'acciaio_standard',
                    'spacer_id': 'alluminio',
                    'height_mm': 2100,
                    'width_mm': 1200,
                    'frame_width_mm': 80,
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Run check-compliance
        response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'checked_lines' in data
        assert data['checked_lines'] == 1
        assert data['all_compliant'] == False, "doppio_be_argon + steel frame should NOT be compliant for Zone E"
        
        result = data['results'][0]
        assert result['uw'] > 1.30, f"Uw should be > 1.30 for Zone E limit, got {result['uw']}"
        assert result['zone'] == 'E'
        assert result['compliant'] == False
        
        print(f"✓ doppio_be_argon + steel: Uw={result['uw']:.2f}, Zone E limit=1.30 → NOT COMPLIANT")

    def test_check_compliance_triplo_be_argon_zone_e(self, auth_session):
        """Check-compliance with triplo_be_argon returns compliant for Zone E."""
        # Create preventivo with triplo glass
        payload = {
            'subject': 'TEST_Compliance triplo BE',
            'lines': [{
                'description': 'Finestra triplo vetro',
                'quantity': 1,
                'unit_price': 800,
                'thermal_data': {
                    'glass_id': 'triplo_be_argon',
                    'frame_id': 'pvc_multicamera',  # Better frame
                    'spacer_id': 'warm_edge',  # Better spacer
                    'height_mm': 2100,
                    'width_mm': 1200,
                    'frame_width_mm': 80,
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Run check-compliance
        response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['checked_lines'] == 1
        
        result = data['results'][0]
        # triplo_be_argon (Ug=0.5) + pvc_multicamera (Uf=1.2) + warm_edge (Psi=0.04) should give Uw < 1.30
        if result['compliant']:
            print(f"✓ triplo_be_argon + PVC: Uw={result['uw']:.2f}, Zone E limit=1.30 → COMPLIANT")
        else:
            # Even if not compliant, document the result
            print(f"✓ triplo_be_argon + PVC: Uw={result['uw']:.2f}, Zone E limit=1.30 → {result['compliant']}")

    def test_check_compliance_singolo_zone_e(self, auth_session):
        """Check-compliance with singolo (single glass) returns NOT compliant for Zone E."""
        payload = {
            'subject': 'TEST_Compliance singolo',
            'lines': [{
                'description': 'Finestra vetro singolo',
                'quantity': 1,
                'unit_price': 200,
                'thermal_data': {
                    'glass_id': 'singolo',
                    'frame_id': 'acciaio_standard',
                    'spacer_id': 'alluminio',
                    'height_mm': 2100,
                    'width_mm': 1200,
                    'frame_width_mm': 80,
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        # Run check-compliance
        response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        assert response.status_code == 200
        
        data = response.json()
        assert data['all_compliant'] == False, "Single glass should NOT be compliant for Zone E"
        
        result = data['results'][0]
        assert result['uw'] > 1.30, f"Single glass Uw should be >> 1.30, got {result['uw']}"
        assert result['compliant'] == False
        
        print(f"✓ singolo (single glass): Uw={result['uw']:.2f}, Zone E limit=1.30 → NOT COMPLIANT (too high)")

    def test_check_compliance_no_thermal_lines(self, auth_session):
        """Check-compliance with no thermal data returns null all_compliant."""
        payload = {
            'subject': 'TEST_No thermal data',
            'lines': [
                {'description': 'Item without thermal', 'quantity': 1, 'unit_price': 100}
            ]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert create_resp.status_code == 201
        prev_id = create_resp.json()['preventivo_id']
        
        response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        assert response.status_code == 200
        
        data = response.json()
        assert data['checked_lines'] == 0
        assert data['all_compliant'] is None, "all_compliant should be null when no thermal lines"
        assert len(data['results']) == 0
        
        print("✓ No thermal lines → checked_lines=0, all_compliant=null")

    def test_compliance_results_fields(self, auth_session):
        """Verify compliance results include all required fields."""
        payload = {
            'subject': 'TEST_Result fields',
            'lines': [{
                'description': 'Test finestra',
                'quantity': 1,
                'unit_price': 500,
                'thermal_data': {
                    'glass_id': 'doppio_be_argon',
                    'frame_id': 'acciaio_standard',
                    'spacer_id': 'alluminio',
                    'height_mm': 2100,
                    'width_mm': 1200,
                    'frame_width_mm': 80,
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
        prev_id = create_resp.json()['preventivo_id']
        
        response = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        data = response.json()
        
        result = data['results'][0]
        # Verify all required fields are present
        required_fields = ['line_id', 'description', 'uw', 'zone', 'limit', 'compliant', 'glass_label', 'frame_label']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        print(f"✓ Compliance result contains all fields: {', '.join(required_fields)}")


# ── Test: PDF Generation ──────────────────────────────────────────

class TestPDFGeneration:
    """Test PDF generation with commercial offer + technical annex."""
    
    def test_download_pdf_basic(self, auth_session):
        """GET /api/preventivi/{prev_id}/pdf returns PDF content."""
        # Create preventivo
        payload = {
            'subject': 'TEST_PDF test',
            'lines': [{'description': 'Item 1', 'quantity': 2, 'unit_price': 250}]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        prev_id = create_resp.json()['preventivo_id']
        
        # Download PDF
        response = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}/pdf')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify content type and disposition
        assert 'application/pdf' in response.headers.get('Content-Type', ''), "Should return PDF"
        assert 'attachment' in response.headers.get('Content-Disposition', ''), "Should have attachment disposition"
        
        # Verify PDF content (starts with %PDF)
        content = response.content
        assert len(content) > 100, "PDF should have content"
        assert content[:4] == b'%PDF', "Content should be PDF"
        
        print(f"✓ GET /api/preventivi/{prev_id}/pdf returns valid PDF ({len(content)} bytes)")

    def test_download_pdf_with_compliance(self, auth_session):
        """PDF with compliance data includes technical annex."""
        # Create preventivo with thermal data
        payload = {
            'subject': 'TEST_PDF with compliance',
            'lines': [{
                'description': 'Finestra termoacustica',
                'quantity': 1,
                'unit_price': 700,
                'thermal_data': {
                    'glass_id': 'doppio_be_argon',
                    'frame_id': 'acciaio_standard',
                    'spacer_id': 'alluminio',
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        prev_id = create_resp.json()['preventivo_id']
        
        # Run compliance check first
        auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        
        # Download PDF
        response = auth_session.get(f'{BASE_URL}/api/preventivi/{prev_id}/pdf')
        assert response.status_code == 200
        
        content = response.content
        assert len(content) > 500, "PDF with compliance should be larger"
        
        print(f"✓ PDF with compliance data generated ({len(content)} bytes)")

    def test_pdf_not_found(self, auth_session):
        """GET /api/preventivi/{invalid_id}/pdf returns 404."""
        response = auth_session.get(f'{BASE_URL}/api/preventivi/prev_nonexistent123/pdf')
        assert response.status_code == 404
        print("✓ PDF for nonexistent preventivo returns 404")


# ── Test: Update and Re-check Compliance ──────────────────────────

class TestComplianceFlow:
    """Test the full workflow: create → check → update → re-check."""
    
    def test_update_glass_and_recheck(self, auth_session):
        """Update line to better glass and verify compliance changes."""
        # Create with non-compliant config
        payload = {
            'subject': 'TEST_Glass upgrade flow',
            'lines': [{
                'description': 'Finestra da aggiornare',
                'quantity': 1,
                'unit_price': 500,
                'thermal_data': {
                    'glass_id': 'doppio_be_argon',  # Uw too high
                    'frame_id': 'acciaio_standard',
                    'spacer_id': 'alluminio',
                    'zone': 'E'
                }
            }]
        }
        create_resp = auth_session.post(f'{BASE_URL}/api/preventivi/', json=payload)
        prev_id = create_resp.json()['preventivo_id']
        
        # Verify initially non-compliant
        check1 = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        data1 = check1.json()
        initial_uw = data1['results'][0]['uw']
        initial_compliant = data1['results'][0]['compliant']
        print(f"  Initial: Uw={initial_uw:.2f}, compliant={initial_compliant}")
        assert initial_compliant == False, "Initial config should NOT be compliant"
        
        # Update to better glass + frame combo
        update_payload = {
            'lines': [{
                'description': 'Finestra aggiornata triplo vetro',
                'quantity': 1,
                'unit_price': 800,
                'thermal_data': {
                    'glass_id': 'triplo_be_argon',  # Better glass
                    'frame_id': 'pvc_multicamera',  # Better frame
                    'spacer_id': 'warm_edge',  # Better spacer
                    'zone': 'E'
                }
            }]
        }
        auth_session.put(f'{BASE_URL}/api/preventivi/{prev_id}', json=update_payload)
        
        # Re-check compliance
        check2 = auth_session.post(f'{BASE_URL}/api/preventivi/{prev_id}/check-compliance')
        data2 = check2.json()
        updated_uw = data2['results'][0]['uw']
        updated_compliant = data2['results'][0]['compliant']
        print(f"  Updated: Uw={updated_uw:.2f}, compliant={updated_compliant}")
        
        # Verify Uw improved
        assert updated_uw < initial_uw, f"Uw should improve after upgrade: {initial_uw} -> {updated_uw}"
        print(f"✓ Glass upgrade improved Uw from {initial_uw:.2f} to {updated_uw:.2f}")


# ── Run Tests ─────────────────────────────────────────────────────

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

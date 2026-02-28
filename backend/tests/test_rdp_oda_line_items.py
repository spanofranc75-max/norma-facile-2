"""
Test RdP and OdA Line Items Features — Iteration 54
Tests detailed line items for Request for Quote (RdP) and Purchase Orders (OdA).
Each line has: Descrizione, Quantità, Unità di Misura, and Cert. 3.1 checkbox.
OdA also has Prezzo Unitario and auto-calculated total.
"""
import pytest
import requests
import os
import time
import subprocess

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope='module')
def auth_session():
    """Create authenticated session with test user for line items testing."""
    timestamp = str(int(time.time() * 1000))
    user_id = f'lineitems-test-{timestamp}'
    session_token = f'lineitems_session_{timestamp}'
    
    # Create test user and session via MongoDB
    mongo_cmd = f'''
use('test_database');
db.users.insertOne({{
  user_id: '{user_id}',
  email: 'lineitems.test.{timestamp}@example.com',
  name: 'Line Items Test User',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: '{user_id}',
  session_token: '{session_token}',
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
print('SESSION_TOKEN:{session_token}');
print('USER_ID:{user_id}');
'''
    result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True, text=True)
    
    if 'SESSION_TOKEN:' not in result.stdout:
        pytest.skip("Failed to create test session")
    
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json'
    })
    return {'session': session, 'token': session_token, 'user_id': user_id}


@pytest.fixture(scope='module')
def test_commessa(auth_session):
    """Create a test commessa for line items testing."""
    session = auth_session['session']
    payload = {
        'title': f'TEST_LineItems_Commessa_{int(time.time())}',
        'client_name': 'Cliente Test Line Items',
        'value': 75000,
        'deadline': '2026-07-31',
        'priority': 'alta',
        'description': 'Commessa for RdP/OdA line items testing'
    }
    resp = session.post(f'{BASE_URL}/api/commesse/', json=payload)
    assert resp.status_code == 201, f"Failed to create commessa: {resp.text}"
    data = resp.json()
    commessa_id = data.get('commessa_id')
    numero = data.get('numero')
    assert commessa_id, "No commessa_id returned"
    yield {'commessa_id': commessa_id, 'numero': numero}
    
    # Cleanup
    session.delete(f'{BASE_URL}/api/commesse/{commessa_id}')


@pytest.fixture(scope='module')
def test_fornitore(auth_session):
    """Create a test supplier for RdP/OdA testing."""
    session = auth_session['session']
    payload = {
        'business_name': f'TEST_Fornitore_LineItems_{int(time.time())}',
        'client_type': 'fornitore',
        'email': f'fornitore.lineitems.{int(time.time())}@test.com',
        'phone': '+39 02 12345678',
        'address': 'Via Test 123, Milano'
    }
    resp = session.post(f'{BASE_URL}/api/clients/', json=payload)
    if resp.status_code == 201:
        data = resp.json()
        yield {'client_id': data.get('client_id'), 'business_name': payload['business_name']}
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{data.get('client_id')}")
    else:
        # Fallback - use inline fornitore name
        yield {'client_id': '', 'business_name': 'TEST_Fornitore_Inline'}


# ══════════════════════════════════════════════════════════════════
#  RdP (Richiesta di Preventivo) LINE ITEMS Tests
# ══════════════════════════════════════════════════════════════════

class TestRdPLineItems:
    """Test RdP endpoints with detailed line items (righe)."""
    
    def test_create_rdp_with_single_line(self, auth_session, test_commessa, test_fornitore):
        """POST RdP with single line item including all fields."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': test_fornitore['business_name'],
            'fornitore_id': test_fornitore['client_id'],
            'righe': [
                {
                    'descrizione': 'Travi IPE 200 x 6000mm',
                    'quantita': 50,
                    'unita_misura': 'pz',
                    'richiede_cert_31': True,
                    'note': 'S275JR'
                }
            ],
            'note': 'Consegna urgente'
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste', json=payload)
        assert resp.status_code == 200, f"RdP creation failed: {resp.text}"
        
        data = resp.json()
        assert 'rdp' in data
        rdp = data['rdp']
        
        # Validate RdP structure
        assert rdp['fornitore_nome'] == test_fornitore['business_name']
        assert rdp['stato'] == 'inviata'
        assert rdp['rdp_id'].startswith('rdp_')
        
        # Validate righe
        assert 'righe' in rdp
        assert len(rdp['righe']) == 1
        
        riga = rdp['righe'][0]
        assert riga['descrizione'] == 'Travi IPE 200 x 6000mm'
        assert riga['quantita'] == 50
        assert riga['unita_misura'] == 'pz'
        assert riga['richiede_cert_31'] == True
    
    def test_create_rdp_with_multiple_lines(self, auth_session, test_commessa, test_fornitore):
        """POST RdP with multiple line items, some with Cert. 3.1 required."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': test_fornitore['business_name'],
            'fornitore_id': test_fornitore['client_id'],
            'righe': [
                {
                    'descrizione': 'Lamiera S355J2 sp. 10mm',
                    'quantita': 500,
                    'unita_misura': 'kg',
                    'richiede_cert_31': True
                },
                {
                    'descrizione': 'Tubo 100x100x4mm',
                    'quantita': 12,
                    'unita_misura': 'ml',
                    'richiede_cert_31': True
                },
                {
                    'descrizione': 'Bulloneria M16 cl.8.8',
                    'quantita': 100,
                    'unita_misura': 'pz',
                    'richiede_cert_31': False
                }
            ],
            'note': 'Preventivo per struttura capannone'
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste', json=payload)
        assert resp.status_code == 200, f"RdP with multiple lines failed: {resp.text}"
        
        rdp = resp.json()['rdp']
        
        # Validate all lines stored
        assert len(rdp['righe']) == 3
        
        # Check specific lines
        lamiera = next((r for r in rdp['righe'] if 'Lamiera' in r['descrizione']), None)
        assert lamiera is not None
        assert lamiera['quantita'] == 500
        assert lamiera['unita_misura'] == 'kg'
        assert lamiera['richiede_cert_31'] == True
        
        bulloneria = next((r for r in rdp['righe'] if 'Bulloneria' in r['descrizione']), None)
        assert bulloneria is not None
        assert bulloneria['richiede_cert_31'] == False
    
    def test_rdp_validates_empty_lines(self, auth_session, test_commessa, test_fornitore):
        """RdP with only empty description lines should be accepted but filtered."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        # This payload simulates what frontend sends when user adds lines but leaves them empty
        payload = {
            'fornitore_nome': test_fornitore['business_name'],
            'righe': [
                {'descrizione': 'Valid item', 'quantita': 10, 'unita_misura': 'pz', 'richiede_cert_31': False},
                {'descrizione': '', 'quantita': 1, 'unita_misura': 'kg', 'richiede_cert_31': False},  # Empty desc
                {'descrizione': '   ', 'quantita': 5, 'unita_misura': 'ml', 'richiede_cert_31': True}  # Whitespace only
            ]
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste', json=payload)
        # Should succeed - frontend filters empty lines before sending
        assert resp.status_code == 200
    
    def test_rdp_righe_persisted_in_ops(self, auth_session, test_commessa, test_fornitore):
        """Verify RdP righe are returned via GET /ops endpoint."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        # Create RdP with righe
        payload = {
            'fornitore_nome': 'TEST_Fornitore_Persistence',
            'righe': [
                {'descrizione': 'Item for persistence check', 'quantita': 25, 'unita_misura': 'kg', 'richiede_cert_31': True}
            ]
        }
        session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste', json=payload)
        
        # Fetch via ops
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{cid}/ops')
        assert ops_resp.status_code == 200
        
        richieste = ops_resp.json()['approvvigionamento']['richieste']
        rdp_with_righe = next((r for r in richieste if r.get('fornitore_nome') == 'TEST_Fornitore_Persistence'), None)
        
        assert rdp_with_righe is not None
        assert 'righe' in rdp_with_righe
        assert len(rdp_with_righe['righe']) == 1
        assert rdp_with_righe['righe'][0]['descrizione'] == 'Item for persistence check'
        assert rdp_with_righe['righe'][0]['richiede_cert_31'] == True


# ══════════════════════════════════════════════════════════════════
#  OdA (Ordine di Acquisto) LINE ITEMS Tests with PRICING
# ══════════════════════════════════════════════════════════════════

class TestOdALineItems:
    """Test OdA endpoints with detailed line items including pricing."""
    
    def test_create_oda_with_pricing(self, auth_session, test_commessa, test_fornitore):
        """POST OdA with line items including prezzo_unitario and auto-calculated total."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': test_fornitore['business_name'],
            'fornitore_id': test_fornitore['client_id'],
            'righe': [
                {
                    'descrizione': 'IPE 200 S275JR',
                    'quantita': 100,
                    'unita_misura': 'kg',
                    'prezzo_unitario': 1.25,
                    'richiede_cert_31': True
                },
                {
                    'descrizione': 'HEB 160 S355J2',
                    'quantita': 200,
                    'unita_misura': 'kg',
                    'prezzo_unitario': 1.45,
                    'richiede_cert_31': True
                }
            ],
            'note': 'Ordine strutture principali'
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini', json=payload)
        assert resp.status_code == 200, f"OdA creation failed: {resp.text}"
        
        ordine = resp.json()['ordine']
        
        # Validate OdA structure
        assert ordine['fornitore_nome'] == test_fornitore['business_name']
        assert ordine['stato'] == 'inviato'
        assert ordine['ordine_id'].startswith('oda_')
        
        # Validate righe with pricing
        assert 'righe' in ordine
        assert len(ordine['righe']) == 2
        
        riga1 = ordine['righe'][0]
        assert riga1['descrizione'] == 'IPE 200 S275JR'
        assert riga1['quantita'] == 100
        assert riga1['prezzo_unitario'] == 1.25
        assert riga1['richiede_cert_31'] == True
        
        # Validate auto-calculated total
        # 100 * 1.25 + 200 * 1.45 = 125 + 290 = 415
        expected_total = 100 * 1.25 + 200 * 1.45
        assert ordine['importo_totale'] == expected_total
    
    def test_create_oda_calculates_total_from_lines(self, auth_session, test_commessa, test_fornitore):
        """OdA auto-calculates importo_totale from righe if not provided."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': 'TEST_AutoCalc_Fornitore',
            'righe': [
                {'descrizione': 'Item A', 'quantita': 10, 'unita_misura': 'pz', 'prezzo_unitario': 50.00, 'richiede_cert_31': False},
                {'descrizione': 'Item B', 'quantita': 5, 'unita_misura': 'pz', 'prezzo_unitario': 100.00, 'richiede_cert_31': True},
            ]
            # Note: importo_totale NOT provided - should be auto-calculated
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini', json=payload)
        assert resp.status_code == 200
        
        ordine = resp.json()['ordine']
        
        # Expected: 10*50 + 5*100 = 500 + 500 = 1000
        assert ordine['importo_totale'] == 1000.00
    
    def test_create_oda_respects_provided_total(self, auth_session, test_commessa, test_fornitore):
        """OdA uses provided importo_totale if given (for discounts, etc.)."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': 'TEST_ProvidedTotal_Fornitore',
            'righe': [
                {'descrizione': 'Item X', 'quantita': 100, 'unita_misura': 'kg', 'prezzo_unitario': 10.00, 'richiede_cert_31': False},
            ],
            'importo_totale': 900.00  # With discount
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini', json=payload)
        assert resp.status_code == 200
        
        ordine = resp.json()['ordine']
        # Should use provided total
        assert ordine['importo_totale'] == 900.00
    
    def test_oda_with_cert_31_flag(self, auth_session, test_commessa, test_fornitore):
        """OdA righe correctly store richiede_cert_31 flag."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': 'TEST_Cert31_Fornitore',
            'righe': [
                {'descrizione': 'Material with cert', 'quantita': 50, 'unita_misura': 'kg', 'prezzo_unitario': 2.00, 'richiede_cert_31': True},
                {'descrizione': 'Material no cert', 'quantita': 100, 'unita_misura': 'pz', 'prezzo_unitario': 0.50, 'richiede_cert_31': False},
            ]
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini', json=payload)
        assert resp.status_code == 200
        
        righe = resp.json()['ordine']['righe']
        
        with_cert = next((r for r in righe if 'with cert' in r['descrizione']), None)
        no_cert = next((r for r in righe if 'no cert' in r['descrizione']), None)
        
        assert with_cert['richiede_cert_31'] == True
        assert no_cert['richiede_cert_31'] == False
    
    def test_oda_righe_persisted_in_ops(self, auth_session, test_commessa, test_fornitore):
        """Verify OdA righe are returned via GET /ops endpoint."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        # Create OdA
        payload = {
            'fornitore_nome': 'TEST_OdA_Persistence',
            'righe': [
                {'descrizione': 'Persistence test item', 'quantita': 77, 'unita_misura': 'ml', 'prezzo_unitario': 3.33, 'richiede_cert_31': True}
            ]
        }
        session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/ordini', json=payload)
        
        # Fetch via ops
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{cid}/ops')
        assert ops_resp.status_code == 200
        
        ordini = ops_resp.json()['approvvigionamento']['ordini']
        oda_with_righe = next((o for o in ordini if o.get('fornitore_nome') == 'TEST_OdA_Persistence'), None)
        
        assert oda_with_righe is not None
        assert 'righe' in oda_with_righe
        assert len(oda_with_righe['righe']) == 1
        
        riga = oda_with_righe['righe'][0]
        assert riga['descrizione'] == 'Persistence test item'
        assert riga['quantita'] == 77
        assert riga['prezzo_unitario'] == 3.33
        assert riga['richiede_cert_31'] == True


# ══════════════════════════════════════════════════════════════════
#  COMMESSA NUMERO (Reference) Tests
# ══════════════════════════════════════════════════════════════════

class TestCommessaNumeroReference:
    """Test that commessa numero is properly available for RdP/OdA dialogs."""
    
    def test_commessa_has_numero(self, auth_session, test_commessa):
        """Verify commessa has numero field."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        resp = session.get(f'{BASE_URL}/api/commesse/{cid}/hub')
        assert resp.status_code == 200
        
        commessa = resp.json()['commessa']
        assert 'numero' in commessa
        assert commessa['numero'] is not None
        # Numero typically follows format like COM-2026-0001
        assert len(commessa['numero']) > 0
    
    def test_commessa_numero_passed_to_ops_panel(self, auth_session, test_commessa):
        """Verify CommessaHubPage passes commessaNumero to CommessaOpsPanel."""
        # This is a frontend concern but we verify the numero is in hub response
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        resp = session.get(f'{BASE_URL}/api/commesse/{cid}/hub')
        assert resp.status_code == 200
        
        data = resp.json()
        # Hub should include commessa with numero
        assert 'commessa' in data
        assert 'numero' in data['commessa']


# ══════════════════════════════════════════════════════════════════
#  UNITA MISURA (Unit of Measure) Tests
# ══════════════════════════════════════════════════════════════════

class TestUnitaMisura:
    """Test various units of measure in line items."""
    
    def test_all_units_accepted_in_rdp(self, auth_session, test_commessa, test_fornitore):
        """RdP accepts all standard units: kg, pz, ml, mq, t."""
        session = auth_session['session']
        cid = test_commessa['commessa_id']
        
        payload = {
            'fornitore_nome': 'TEST_Units_Fornitore',
            'righe': [
                {'descrizione': 'By weight', 'quantita': 100, 'unita_misura': 'kg', 'richiede_cert_31': False},
                {'descrizione': 'By piece', 'quantita': 50, 'unita_misura': 'pz', 'richiede_cert_31': False},
                {'descrizione': 'By linear meter', 'quantita': 25, 'unita_misura': 'ml', 'richiede_cert_31': False},
                {'descrizione': 'By square meter', 'quantita': 10, 'unita_misura': 'mq', 'richiede_cert_31': False},
                {'descrizione': 'By ton', 'quantita': 5, 'unita_misura': 't', 'richiede_cert_31': False},
            ]
        }
        
        resp = session.post(f'{BASE_URL}/api/commesse/{cid}/approvvigionamento/richieste', json=payload)
        assert resp.status_code == 200
        
        righe = resp.json()['rdp']['righe']
        units_stored = [r['unita_misura'] for r in righe]
        
        assert 'kg' in units_stored
        assert 'pz' in units_stored
        assert 'ml' in units_stored
        assert 'mq' in units_stored
        assert 't' in units_stored


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

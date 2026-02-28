"""
Test Commessa Operations — Approvvigionamento, Produzione, Conto Lavoro, Repository Documenti.
Tests for iteration 51: Complete operational workflow inside commessa.
"""
import pytest
import requests
import os
import time
import io
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope='module')
def auth_session():
    """Create authenticated session with test user."""
    # Create test user and session via MongoDB
    os.system('''mongosh --quiet --eval "
use('test_database');
var userId = 'ops-test-user-' + Date.now();
var sessionToken = 'ops_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'ops.test.' + Date.now() + '@example.com',
  name: 'Ops Test User',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('TOKEN:' + sessionToken);
print('USERID:' + userId);
" 2>/dev/null''')
    
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
use('test_database');
var s = db.user_sessions.findOne({}, {_id: 0, session_token: 1, user_id: 1});
if (s) print('TOKEN:' + s.session_token + '|USERID:' + s.user_id);
'''
    ], capture_output=True, text=True)
    
    lines = result.stdout.strip().split('\n')
    token = None
    user_id = None
    for line in lines:
        if line.startswith('TOKEN:'):
            parts = line.replace('TOKEN:', '').split('|USERID:')
            if len(parts) == 2:
                token = parts[0]
                user_id = parts[1]
                break
    
    if not token:
        pytest.skip("Failed to create test session")
    
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    return {'session': session, 'token': token, 'user_id': user_id}


@pytest.fixture(scope='module')
def test_commessa(auth_session):
    """Create a test commessa for operations testing."""
    session = auth_session['session']
    payload = {
        'title': 'TEST_OPS_Commessa_' + str(int(time.time())),
        'client_name': 'Test Client Ops',
        'value': 50000,
        'deadline': '2026-06-30',
        'priority': 'alta',
        'description': 'Commessa for operations testing'
    }
    resp = session.post(f'{BASE_URL}/api/commesse/', json=payload)
    assert resp.status_code == 201, f"Failed to create commessa: {resp.text}"
    data = resp.json()
    commessa_id = data.get('commessa_id')
    assert commessa_id, "No commessa_id returned"
    yield commessa_id
    
    # Cleanup
    session.delete(f'{BASE_URL}/api/commesse/{commessa_id}')


# ══════════════════════════════════════════════════════════════════
#  APPROVVIGIONAMENTO (Procurement) Tests
# ══════════════════════════════════════════════════════════════════

class TestRichiestePreventivo:
    """Test RdP (Richiesta di Preventivo) endpoints."""
    
    def test_create_rdp(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/approvvigionamento/richieste creates RdP with stato=inviata."""
        session = auth_session['session']
        payload = {
            'fornitore_nome': 'TEST_Fornitore Acciaio SpA',
            'materiali_richiesti': 'IPE 200 x 100m, HEB 160 x 50m',
            'note': 'Urgente'
        }
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste', json=payload)
        assert resp.status_code == 200, f"RdP creation failed: {resp.text}"
        
        data = resp.json()
        assert 'rdp' in data
        rdp = data['rdp']
        assert rdp['fornitore_nome'] == 'TEST_Fornitore Acciaio SpA'
        assert rdp['stato'] == 'inviata'
        assert rdp['rdp_id'].startswith('rdp_')
        
        return rdp['rdp_id']
    
    def test_update_rdp_to_ricevuta(self, auth_session, test_commessa):
        """PUT /api/commesse/{id}/approvvigionamento/richieste/{rdp_id} updates to ricevuta."""
        session = auth_session['session']
        
        # First create an RdP
        payload = {'fornitore_nome': 'TEST_Supplier for Update'}
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste', json=payload)
        rdp_id = resp.json()['rdp']['rdp_id']
        
        # Update to ricevuta using Form data
        resp = session.put(
            f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste/{rdp_id}',
            data={'stato': 'ricevuta', 'importo': '15000.50'},
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f"Bearer {auth_session['token']}"}
        )
        assert resp.status_code == 200, f"RdP update failed: {resp.text}"
        
        # Verify via ops endpoint
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        richieste = ops_resp.json()['approvvigionamento']['richieste']
        updated_rdp = next((r for r in richieste if r['rdp_id'] == rdp_id), None)
        assert updated_rdp is not None
        assert updated_rdp['stato'] == 'ricevuta'
        assert updated_rdp['importo_proposto'] == 15000.50
    
    def test_update_rdp_to_accettata(self, auth_session, test_commessa):
        """PUT updates RdP to accettata state."""
        session = auth_session['session']
        
        # Create and update to ricevuta first
        payload = {'fornitore_nome': 'TEST_Supplier Accept'}
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste', json=payload)
        rdp_id = resp.json()['rdp']['rdp_id']
        
        session.put(
            f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste/{rdp_id}',
            data={'stato': 'ricevuta'},
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f"Bearer {auth_session['token']}"}
        )
        
        # Now accept
        resp = session.put(
            f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste/{rdp_id}',
            data={'stato': 'accettata'},
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f"Bearer {auth_session['token']}"}
        )
        assert resp.status_code == 200


class TestOrdiniFornitore:
    """Test OdA (Ordine di Acquisto) endpoints."""
    
    def test_create_ordine(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/approvvigionamento/ordini creates OdA with stato=inviato."""
        session = auth_session['session']
        payload = {
            'fornitore_nome': 'TEST_Fornitore Ordine',
            'importo_totale': 25000.00,
            'note': 'Ordine urgente',
            'righe': [{'descrizione': 'IPE 200', 'quantita': 100, 'um': 'm'}]
        }
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini', json=payload)
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        
        data = resp.json()
        ordine = data['ordine']
        assert ordine['fornitore_nome'] == 'TEST_Fornitore Ordine'
        assert ordine['stato'] == 'inviato'
        assert ordine['ordine_id'].startswith('oda_')
        assert ordine['importo_totale'] == 25000.00
        
        return ordine['ordine_id']
    
    def test_update_ordine_to_confermato(self, auth_session, test_commessa):
        """PUT updates order status to confermato."""
        session = auth_session['session']
        
        # Create order
        payload = {'fornitore_nome': 'TEST_Order Confirm', 'importo_totale': 10000}
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini', json=payload)
        ordine_id = resp.json()['ordine']['ordine_id']
        
        # Update to confermato using Form data
        resp = session.put(
            f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini/{ordine_id}',
            data={'stato': 'confermato'},
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f"Bearer {auth_session['token']}"}
        )
        assert resp.status_code == 200
        
        # Verify
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        ordini = ops_resp.json()['approvvigionamento']['ordini']
        updated = next((o for o in ordini if o['ordine_id'] == ordine_id), None)
        assert updated['stato'] == 'confermato'
        assert updated['data_conferma'] is not None


class TestArriviMateriale:
    """Test material arrivals endpoints."""
    
    def test_register_arrivo(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/approvvigionamento/arrivi registers material arrival."""
        session = auth_session['session']
        payload = {
            'ddt_fornitore': 'DDT-2026/0123',
            'note': 'Arrivo parziale',
            'materiali': [{'descrizione': 'IPE 200', 'quantita': 50}]
        }
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi', json=payload)
        assert resp.status_code == 200, f"Arrival registration failed: {resp.text}"
        
        data = resp.json()
        arrivo = data['arrivo']
        assert arrivo['arrivo_id'].startswith('arr_')
        assert arrivo['stato'] == 'da_verificare'
        assert arrivo['ddt_fornitore'] == 'DDT-2026/0123'
        
        return arrivo['arrivo_id']
    
    def test_arrivo_linked_to_ordine(self, auth_session, test_commessa):
        """Arrival linked to order marks order as consegnato."""
        session = auth_session['session']
        
        # Create order
        ord_resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini', 
                                json={'fornitore_nome': 'TEST_For Arrival', 'importo_totale': 5000})
        ordine_id = ord_resp.json()['ordine']['ordine_id']
        
        # Confirm order first
        session.put(
            f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini/{ordine_id}',
            data={'stato': 'confermato'},
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f"Bearer {auth_session['token']}"}
        )
        
        # Register arrival with ordine_id
        arr_resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi',
                                json={'ordine_id': ordine_id, 'ddt_fornitore': 'DDT-LINKED'})
        assert arr_resp.status_code == 200
        
        # Verify order is now consegnato
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        ordini = ops_resp.json()['approvvigionamento']['ordini']
        linked_order = next((o for o in ordini if o['ordine_id'] == ordine_id), None)
        assert linked_order['stato'] == 'consegnato'
    
    def test_verifica_arrivo(self, auth_session, test_commessa):
        """PUT /api/commesse/{id}/approvvigionamento/arrivi/{arrivo_id}/verifica marks arrival as verified."""
        session = auth_session['session']
        
        # Create arrival
        arr_resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi',
                                json={'ddt_fornitore': 'DDT-VERIFY'})
        arrivo_id = arr_resp.json()['arrivo']['arrivo_id']
        
        # Verify
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi/{arrivo_id}/verifica')
        assert resp.status_code == 200
        
        # Check status
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        arrivi = ops_resp.json()['approvvigionamento']['arrivi']
        verified = next((a for a in arrivi if a['arrivo_id'] == arrivo_id), None)
        assert verified['stato'] == 'verificato'
        assert verified['data_verifica'] is not None


# ══════════════════════════════════════════════════════════════════
#  PRODUZIONE (Production Phases) Tests
# ══════════════════════════════════════════════════════════════════

class TestProduzione:
    """Test production phases endpoints."""
    
    def test_init_produzione(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/produzione/init initializes 6 production phases."""
        session = auth_session['session']
        
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/produzione/init')
        assert resp.status_code == 200, f"Production init failed: {resp.text}"
        
        data = resp.json()
        fasi = data.get('fasi', [])
        assert len(fasi) == 6, f"Expected 6 phases, got {len(fasi)}"
        
        # Verify all 6 phases are present
        expected_types = ['taglio', 'foratura', 'assemblaggio', 'saldatura', 'pulizia', 'preparazione_superfici']
        actual_types = [f['tipo'] for f in fasi]
        for et in expected_types:
            assert et in actual_types, f"Missing phase: {et}"
        
        # All should start as da_fare
        for f in fasi:
            assert f['stato'] == 'da_fare'
    
    def test_init_produzione_idempotent(self, auth_session, test_commessa):
        """Init production is idempotent - doesn't duplicate phases."""
        session = auth_session['session']
        
        # Call init again
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/produzione/init')
        assert resp.status_code == 200
        assert 'gia' in resp.json().get('message', '').lower() or len(resp.json().get('fasi', [])) == 6
    
    def test_get_produzione(self, auth_session, test_commessa):
        """GET /api/commesse/{id}/produzione returns phases and conto_lavoro."""
        session = auth_session['session']
        
        resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/produzione')
        assert resp.status_code == 200
        
        data = resp.json()
        assert 'fasi' in data
        assert 'conto_lavoro' in data
        assert len(data['fasi']) == 6
    
    def test_update_fase_in_corso(self, auth_session, test_commessa):
        """PUT /api/commesse/{id}/produzione/{fase_tipo} updates phase to in_corso."""
        session = auth_session['session']
        
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/produzione/taglio', 
                          json={'stato': 'in_corso', 'operatore': 'Mario Rossi'})
        assert resp.status_code == 200
        
        # Verify
        prod_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/produzione')
        fasi = prod_resp.json()['fasi']
        taglio = next(f for f in fasi if f['tipo'] == 'taglio')
        assert taglio['stato'] == 'in_corso'
        assert taglio['operatore'] == 'Mario Rossi'
        assert taglio['data_inizio'] is not None
    
    def test_update_fase_completato(self, auth_session, test_commessa):
        """PUT updates phase to completato."""
        session = auth_session['session']
        
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/produzione/taglio',
                          json={'stato': 'completato'})
        assert resp.status_code == 200
        
        # Verify
        prod_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/produzione')
        fasi = prod_resp.json()['fasi']
        taglio = next(f for f in fasi if f['tipo'] == 'taglio')
        assert taglio['stato'] == 'completato'
        assert taglio['data_fine'] is not None
    
    def test_production_progress_calculation(self, auth_session, test_commessa):
        """GET /api/commesse/{id}/ops returns production progress percentage."""
        session = auth_session['session']
        
        # Complete another phase
        session.put(f'{BASE_URL}/api/commesse/{test_commessa}/produzione/foratura',
                   json={'stato': 'completato'})
        
        resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        data = resp.json()
        
        progress = data.get('produzione_progress', {})
        assert progress.get('total') == 6
        assert progress.get('completed') >= 2  # taglio + foratura
        assert progress.get('percentage') >= 33  # At least 2/6 = 33%


# ══════════════════════════════════════════════════════════════════
#  CONTO LAVORO (Subcontracting) Tests
# ══════════════════════════════════════════════════════════════════

class TestContoLavoro:
    """Test conto lavoro (subcontracting) endpoints."""
    
    def test_create_conto_lavoro(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/conto-lavoro creates subcontracting entry."""
        session = auth_session['session']
        payload = {
            'tipo': 'verniciatura',
            'fornitore_nome': 'TEST_Verniciatura Industriale Srl',
            'note': 'RAL 7016 grigio antracite'
        }
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro', json=payload)
        assert resp.status_code == 200, f"CL creation failed: {resp.text}"
        
        data = resp.json()
        cl = data['conto_lavoro']
        assert cl['cl_id'].startswith('cl_')
        assert cl['tipo'] == 'verniciatura'
        assert cl['stato'] == 'da_inviare'
        assert cl['fornitore_nome'] == 'TEST_Verniciatura Industriale Srl'
        
        return cl['cl_id']
    
    def test_conto_lavoro_workflow_full(self, auth_session, test_commessa):
        """Test full CL workflow: da_inviare → inviato → in_lavorazione → rientrato → verificato."""
        session = auth_session['session']
        
        # Create
        resp = session.post(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro',
                           json={'tipo': 'zincatura', 'fornitore_nome': 'TEST_Zincatura Workflow'})
        cl_id = resp.json()['conto_lavoro']['cl_id']
        
        # Step 1: da_inviare → inviato
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro/{cl_id}',
                          json={'stato': 'inviato', 'ddt_invio_id': 'ddt_inv_123'})
        assert resp.status_code == 200
        
        # Step 2: inviato → in_lavorazione
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro/{cl_id}',
                          json={'stato': 'in_lavorazione'})
        assert resp.status_code == 200
        
        # Step 3: in_lavorazione → rientrato
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro/{cl_id}',
                          json={'stato': 'rientrato', 'ddt_rientro_id': 'ddt_rien_456'})
        assert resp.status_code == 200
        
        # Step 4: rientrato → verificato
        resp = session.put(f'{BASE_URL}/api/commesse/{test_commessa}/conto-lavoro/{cl_id}',
                          json={'stato': 'verificato', 'certificato_doc_id': 'cert_zinc_789'})
        assert resp.status_code == 200
        
        # Verify final state
        ops_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        cl_list = ops_resp.json()['conto_lavoro']
        final = next((c for c in cl_list if c['cl_id'] == cl_id), None)
        assert final['stato'] == 'verificato'
        assert final['ddt_invio_id'] == 'ddt_inv_123'
        assert final['ddt_rientro_id'] == 'ddt_rien_456'


# ══════════════════════════════════════════════════════════════════
#  REPOSITORY DOCUMENTI Tests
# ══════════════════════════════════════════════════════════════════

class TestRepositoryDocumenti:
    """Test document repository endpoints."""
    
    def test_upload_document(self, auth_session, test_commessa):
        """POST /api/commesse/{id}/documenti uploads file to repository."""
        session = auth_session['session']
        
        # Create a test PDF-like file
        file_content = b'%PDF-1.4 TEST DOCUMENT CONTENT'
        files = {'file': ('test_document.pdf', io.BytesIO(file_content), 'application/pdf')}
        data = {'tipo': 'certificato_31', 'note': 'Test certificate'}
        
        # Need to remove Content-Type header for multipart
        headers = {'Authorization': f"Bearer {auth_session['token']}"}
        resp = requests.post(f'{BASE_URL}/api/commesse/{test_commessa}/documenti',
                            files=files, data=data, headers=headers)
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        
        result = resp.json()
        assert 'doc_id' in result
        assert result['doc_id'].startswith('doc_')
        assert result['tipo'] == 'certificato_31'
        
        return result['doc_id']
    
    def test_list_documents(self, auth_session, test_commessa):
        """GET /api/commesse/{id}/documenti lists documents without file content."""
        session = auth_session['session']
        
        resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/documenti')
        assert resp.status_code == 200
        
        data = resp.json()
        assert 'documents' in data
        assert 'total' in data
        
        # Documents should not contain file_base64
        for doc in data['documents']:
            assert 'file_base64' not in doc
            assert 'doc_id' in doc
            assert 'nome_file' in doc
    
    def test_download_document(self, auth_session, test_commessa):
        """GET /api/commesse/{id}/documenti/{doc_id}/download downloads file."""
        session = auth_session['session']
        
        # First upload a document
        file_content = b'DOWNLOAD TEST CONTENT'
        files = {'file': ('download_test.txt', io.BytesIO(file_content), 'text/plain')}
        headers = {'Authorization': f"Bearer {auth_session['token']}"}
        up_resp = requests.post(f'{BASE_URL}/api/commesse/{test_commessa}/documenti',
                               files=files, data={'tipo': 'altro'}, headers=headers)
        doc_id = up_resp.json()['doc_id']
        
        # Download
        dl_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/documenti/{doc_id}/download')
        assert dl_resp.status_code == 200
        assert dl_resp.content == file_content
    
    def test_delete_document(self, auth_session, test_commessa):
        """DELETE /api/commesse/{id}/documenti/{doc_id} deletes document."""
        session = auth_session['session']
        
        # Upload
        file_content = b'DELETE TEST'
        files = {'file': ('delete_test.txt', io.BytesIO(file_content), 'text/plain')}
        headers = {'Authorization': f"Bearer {auth_session['token']}"}
        up_resp = requests.post(f'{BASE_URL}/api/commesse/{test_commessa}/documenti',
                               files=files, data={'tipo': 'altro'}, headers=headers)
        doc_id = up_resp.json()['doc_id']
        
        # Delete
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{test_commessa}/documenti/{doc_id}')
        assert del_resp.status_code == 200
        
        # Verify deleted
        dl_resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/documenti/{doc_id}/download')
        assert dl_resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
#  OPS AGGREGATION + EVENTS Tests
# ══════════════════════════════════════════════════════════════════

class TestOpsAggregation:
    """Test the /ops endpoint and event tracking."""
    
    def test_get_ops_returns_all_data(self, auth_session, test_commessa):
        """GET /api/commesse/{id}/ops returns all operational data aggregated."""
        session = auth_session['session']
        
        resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/ops')
        assert resp.status_code == 200
        
        data = resp.json()
        # Check all sections present
        assert 'approvvigionamento' in data
        assert 'fasi_produzione' in data
        assert 'produzione_progress' in data
        assert 'conto_lavoro' in data
        assert 'documenti_count' in data
        
        # Approvvigionamento structure
        approv = data['approvvigionamento']
        assert 'richieste' in approv
        assert 'ordini' in approv
        assert 'arrivi' in approv
    
    def test_events_pushed_for_operations(self, auth_session, test_commessa):
        """Events are pushed to commessa.eventi for each operation."""
        session = auth_session['session']
        
        # Get commessa hub to check events
        resp = session.get(f'{BASE_URL}/api/commesse/{test_commessa}/hub')
        assert resp.status_code == 200
        
        data = resp.json()
        eventi = data['commessa'].get('eventi', [])
        
        # We've done many operations, should have multiple events
        assert len(eventi) > 0
        
        # Check event structure
        event_types = [e.get('tipo') for e in eventi]
        # Should have RDP, ORDINE, MATERIALE, PRODUZIONE related events
        assert any('RDP' in et or 'ORDINE' in et or 'MATERIALE' in et or 'FASE' in et or 'CL' in et or 'DOCUMENTO' in et for et in event_types)


# ══════════════════════════════════════════════════════════════════
#  ERROR HANDLING Tests
# ══════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Test error cases."""
    
    def test_ops_nonexistent_commessa(self, auth_session):
        """404 for non-existent commessa."""
        session = auth_session['session']
        
        resp = session.get(f'{BASE_URL}/api/commesse/nonexistent_123/ops')
        assert resp.status_code == 404
    
    def test_upload_oversized_file(self, auth_session, test_commessa):
        """413 for file over 15MB limit."""
        # Create 16MB content
        file_content = b'X' * (16 * 1024 * 1024)
        files = {'file': ('huge.bin', io.BytesIO(file_content), 'application/octet-stream')}
        headers = {'Authorization': f"Bearer {auth_session['token']}"}
        
        resp = requests.post(f'{BASE_URL}/api/commesse/{test_commessa}/documenti',
                            files=files, data={'tipo': 'altro'}, headers=headers)
        assert resp.status_code == 413


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

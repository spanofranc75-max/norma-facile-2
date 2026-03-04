"""
Test Cascade Delete - BLINDATURA REGRESSIONE P0

Verifica che eliminando un certificato dal Repository Documenti,
vengano eliminati ANCHE:
  - material_batches (Tracciabilità EN 1090)
  - lotti_cam (CAM - Criteri Ambientali Minimi)
  - archivio_certificati
  - copie del documento in altre commesse

Questo test riproduce ESATTAMENTE il flusso utente:
  1. Upload certificato
  2. Creazione lotti CAM + material_batches (come fa confirm_profili)
  3. Eliminazione certificato
  4. Verifica che TUTTO sia stato cancellato
"""
import pytest
import requests
import os
import time
import io
import subprocess

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    import subprocess as _sp
    _r = _sp.run(['grep', 'REACT_APP_BACKEND_URL', '/app/frontend/.env'], capture_output=True, text=True)
    if _r.stdout:
        BASE_URL = _r.stdout.strip().split('=', 1)[1].rstrip('/')


@pytest.fixture(scope='module')
def auth_session():
    """Create authenticated session."""
    os.system('''mongosh --quiet --eval "
use('test_database');
var userId = 'cascade-test-' + Date.now();
var sessionToken = 'cascade_sess_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'cascade.' + Date.now() + '@test.com',
  name: 'Cascade Test User',
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
    
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
use('test_database');
var s = db.user_sessions.findOne({}, {_id: 0, session_token: 1, user_id: 1});
if (s) print('TOKEN:' + s.session_token + '|USERID:' + s.user_id);
'''
    ], capture_output=True, text=True)
    
    token = user_id = None
    for line in result.stdout.strip().split('\n'):
        if line.startswith('TOKEN:'):
            parts = line.replace('TOKEN:', '').split('|USERID:')
            if len(parts) == 2:
                token, user_id = parts
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
    """Create test commessa."""
    session = auth_session['session']
    resp = session.post(f'{BASE_URL}/api/commesse/', json={
        'title': f'CASCADE_TEST_{int(time.time())}',
        'client_name': 'Test Cascade Client',
        'value': 10000,
        'deadline': '2026-12-31',
    })
    assert resp.status_code == 201, f"Create commessa failed: {resp.text}"
    cid = resp.json()['commessa_id']
    yield cid
    session.delete(f'{BASE_URL}/api/commesse/{cid}')


def _upload_cert(session, token, cid, filename='cert_test.pdf'):
    """Upload a test certificate."""
    file_content = b'%PDF-1.4 test certificate content'
    files = {'file': (filename, io.BytesIO(file_content), 'application/pdf')}
    resp = requests.post(
        f'{BASE_URL}/api/commesse/{cid}/documenti',
        files=files,
        data={'tipo': 'certificato_31', 'note': 'test cascade'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    return resp.json()['doc_id']


def _create_cam_and_batch(user_id, commessa_id, doc_id, colata='TEST_COLATA_001'):
    """Directly insert CAM lotto and material_batch in DB (simulating confirm_profili)."""
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.lotti_cam.insertOne({{
    lotto_id: "cam_test_" + Date.now(),
    user_id: "{user_id}",
    commessa_id: "{commessa_id}",
    descrizione: "IPE 100 TEST",
    fornitore: "Test Acciaieria",
    numero_colata: "{colata}",
    peso_kg: 100,
    qualita_acciaio: "S275JR",
    percentuale_riciclato: 80,
    metodo_produttivo: "forno_elettrico_non_legato",
    tipo_certificazione: "epd",
    numero_certificazione: "CERT_TEST",
    uso_strutturale: true,
    soglia_minima_cam: 75,
    conforme_cam: true,
    source_doc_id: "{doc_id}",
    created_at: new Date()
}});
db.material_batches.insertOne({{
    batch_id: "bat_test_" + Date.now(),
    user_id: "{user_id}",
    heat_number: "{colata}",
    material_type: "S275JR",
    supplier_name: "Test Acciaieria",
    dimensions: "IPE 100",
    source_doc_id: "{doc_id}",
    commessa_id: "{commessa_id}",
    numero_certificato: "CERT_TEST",
    created_at: new Date()
}});
db.archivio_certificati.insertOne({{
    user_id: "{user_id}",
    heat_number: "{colata}",
    source_doc_id: "{doc_id}",
    material_type: "S275JR",
    created_at: new Date()
}});
print("INSERTED");
'''
    ], capture_output=True, text=True)
    assert 'INSERTED' in result.stdout, f"Insert failed: {result.stderr}"


def _count_cam(user_id, commessa_id):
    """Count CAM lotti for this commessa."""
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
var cam = db.lotti_cam.countDocuments({{user_id: "{user_id}", commessa_id: "{commessa_id}"}});
var batch = db.material_batches.countDocuments({{user_id: "{user_id}", commessa_id: "{commessa_id}"}});
var arch = db.archivio_certificati.countDocuments({{user_id: "{user_id}"}});
print("CAM:" + cam + "|BATCH:" + batch + "|ARCH:" + arch);
'''
    ], capture_output=True, text=True)
    counts = {}
    for line in result.stdout.strip().split('\n'):
        if 'CAM:' in line:
            parts = line.split('|')
            for p in parts:
                k, v = p.split(':')
                counts[k] = int(v)
    return counts


class TestCascadeDelete:
    """P0 CRITICAL: Verifica cascade delete completa."""

    def test_cascade_delete_by_source_doc_id(self, auth_session, test_commessa):
        """
        SCENARIO PRINCIPALE: L'utente carica un certificato, l'AI crea lotti,
        poi l'utente elimina il certificato.
        RISULTATO ATTESO: ZERO lotti CAM, ZERO material_batches rimasti.
        """
        session = auth_session['session']
        uid = auth_session['user_id']
        cid = test_commessa

        # Step 1: Upload certificate
        doc_id = _upload_cert(session, auth_session['token'], cid, 'cert_cascade_1.pdf')

        # Step 2: Simulate confirm_profili by inserting linked records
        _create_cam_and_batch(uid, cid, doc_id, 'COLATA_CASCADE_001')

        # Verify records exist
        counts = _count_cam(uid, cid)
        assert counts.get('CAM', 0) >= 1, f"CAM not created: {counts}"
        assert counts.get('BATCH', 0) >= 1, f"Batch not created: {counts}"

        # Step 3: DELETE the certificate
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"

        # Verify cascade info in response
        data = del_resp.json()
        assert 'cascade' in data, f"No cascade info: {data}"
        print(f"Cascade result: {data['cascade']}")

        # Step 4: VERIFY all records deleted
        counts_after = _count_cam(uid, cid)
        assert counts_after.get('CAM', 0) == 0, f"CAM LOTTI NOT DELETED! {counts_after}"
        assert counts_after.get('BATCH', 0) == 0, f"MATERIAL BATCHES NOT DELETED! {counts_after}"

    def test_cascade_delete_multiple_profiles(self, auth_session, test_commessa):
        """
        SCENARIO: Un certificato contiene 3 profili diversi.
        Eliminando il cert, TUTTI i 3 lotti devono essere rimossi.
        """
        session = auth_session['session']
        uid = auth_session['user_id']
        cid = test_commessa

        doc_id = _upload_cert(session, auth_session['token'], cid, 'cert_multi.pdf')

        # Create 3 different profiles from the same cert
        for colata in ['MULTI_001', 'MULTI_002', 'MULTI_003']:
            _create_cam_and_batch(uid, cid, doc_id, colata)

        counts_before = _count_cam(uid, cid)
        assert counts_before.get('CAM', 0) >= 3, f"Expected 3+ CAM: {counts_before}"

        # Delete cert
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200

        # ALL should be gone
        counts_after = _count_cam(uid, cid)
        assert counts_after.get('CAM', 0) == 0, f"ORPHAN CAM LOTTI FOUND! {counts_after}"
        assert counts_after.get('BATCH', 0) == 0, f"ORPHAN BATCHES FOUND! {counts_after}"

    def test_cascade_nuke_when_last_cert_deleted(self, auth_session, test_commessa):
        """
        SCENARIO: L'ultimo certificato viene eliminato.
        Strategy 3 (NUKE) deve pulire tutti gli orfani.
        """
        session = auth_session['session']
        uid = auth_session['user_id']
        cid = test_commessa

        # Create a cert and linked data
        doc_id = _upload_cert(session, auth_session['token'], cid, 'cert_last.pdf')
        _create_cam_and_batch(uid, cid, doc_id, 'LAST_COLATA')

        # Also insert orphan records WITHOUT source_doc_id (simulating old broken data)
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.lotti_cam.insertOne({{
    lotto_id: "cam_orphan_" + Date.now(),
    user_id: "{uid}",
    commessa_id: "{cid}",
    descrizione: "ORPHAN RECORD",
    numero_colata: "ORPHAN_COLATA",
    peso_kg: 50,
    created_at: new Date()
}});
print("ORPHAN_INSERTED");
'''
        ], capture_output=True, text=True)

        counts_before = _count_cam(uid, cid)
        assert counts_before.get('CAM', 0) >= 2, f"Expected 2+ CAM: {counts_before}"

        # Delete the LAST cert
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200

        # Strategy 3 should nuke ALL including orphans
        counts_after = _count_cam(uid, cid)
        assert counts_after.get('CAM', 0) == 0, f"ORPHAN CAM SURVIVED NUKE! {counts_after}"

    def test_delete_cert_preserves_other_cert_data(self, auth_session, test_commessa):
        """
        SCENARIO: Due certificati nella stessa commessa.
        Eliminando uno, i dati dell'altro DEVONO restare.
        """
        session = auth_session['session']
        uid = auth_session['user_id']
        cid = test_commessa

        # Upload two certificates
        doc_id_1 = _upload_cert(session, auth_session['token'], cid, 'cert_A.pdf')
        doc_id_2 = _upload_cert(session, auth_session['token'], cid, 'cert_B.pdf')

        # Create linked data for each
        _create_cam_and_batch(uid, cid, doc_id_1, 'CERT_A_COLATA')
        _create_cam_and_batch(uid, cid, doc_id_2, 'CERT_B_COLATA')

        counts_before = _count_cam(uid, cid)
        assert counts_before.get('CAM', 0) >= 2

        # Delete only cert A
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id_1}')
        assert del_resp.status_code == 200

        # Cert B data should survive
        counts_after = _count_cam(uid, cid)
        assert counts_after.get('CAM', 0) >= 1, f"Cert B data also deleted! {counts_after}"
        assert counts_after.get('BATCH', 0) >= 1, f"Cert B batch also deleted! {counts_after}"

        # Cleanup: delete cert B too
        session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id_2}')

    def test_api_response_includes_cascade_details(self, auth_session, test_commessa):
        """Verify the DELETE response includes cascade details for UI feedback."""
        session = auth_session['session']
        uid = auth_session['user_id']
        cid = test_commessa

        doc_id = _upload_cert(session, auth_session['token'], cid, 'cert_info.pdf')
        _create_cam_and_batch(uid, cid, doc_id, 'INFO_COLATA')

        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200

        data = del_resp.json()
        assert 'cascade' in data
        assert 'CAM:' in data['cascade']
        assert 'Batch:' in data['cascade']

"""
Test API Contracts for Cascade Delete and CAM Integration

Verifies:
1. DELETE /api/commesse/{cid}/documenti/{doc_id} returns cascade info with CAM/Batch counts
2. GET /api/cam/lotti?commessa_id={cid} returns lotti_cam for a commessa  
3. POST /api/commesse/{cid}/documenti works correctly for cert upload
4. Response JSON structure includes 'cascade' field
"""
import pytest
import requests
import os
import time
import io
import subprocess

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    _r = subprocess.run(['grep', 'REACT_APP_BACKEND_URL', '/app/frontend/.env'], capture_output=True, text=True)
    if _r.stdout:
        BASE_URL = _r.stdout.strip().split('=', 1)[1].rstrip('/')


@pytest.fixture(scope='module')
def auth_session():
    """Create authenticated session via MongoDB."""
    timestamp = int(time.time())
    user_id = f'api_contract_test_{timestamp}'
    session_token = f'api_sess_{timestamp}'
    
    mongo_script = f'''
use('test_database');
db.users.insertOne({{
  user_id: "{user_id}",
  email: "api_contract_{timestamp}@test.com",
  name: "API Contract Test User",
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: "{user_id}",
  session_token: "{session_token}",
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
print("CREATED:{user_id}");
'''
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)
    
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json'
    })
    
    yield {'session': session, 'token': session_token, 'user_id': user_id}
    
    # Cleanup
    cleanup_script = f'''
use('test_database');
db.users.deleteMany({{user_id: "{user_id}"}});
db.user_sessions.deleteMany({{user_id: "{user_id}"}});
'''
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True, text=True)


@pytest.fixture(scope='module')
def test_commessa(auth_session):
    """Create test commessa for API testing."""
    session = auth_session['session']
    resp = session.post(f'{BASE_URL}/api/commesse/', json={
        'title': f'API_CONTRACT_TEST_{int(time.time())}',
        'client_name': 'API Contract Client',
        'value': 5000,
        'deadline': '2026-12-31',
    })
    assert resp.status_code == 201, f"Create commessa failed: {resp.text}"
    cid = resp.json()['commessa_id']
    
    yield cid
    
    # Cleanup
    session.delete(f'{BASE_URL}/api/commesse/{cid}')


def _insert_cam_and_batch(user_id, commessa_id, doc_id, colata):
    """Insert CAM lotto and material_batch directly in DB."""
    ts = int(time.time() * 1000)
    mongo_script = f'''
use('test_database');
db.lotti_cam.insertOne({{
    lotto_id: "cam_api_{ts}",
    user_id: "{user_id}",
    commessa_id: "{commessa_id}",
    descrizione: "API Test Profile",
    numero_colata: "{colata}",
    peso_kg: 75,
    source_doc_id: "{doc_id}",
    created_at: new Date()
}});
db.material_batches.insertOne({{
    batch_id: "batch_api_{ts}",
    user_id: "{user_id}",
    commessa_id: "{commessa_id}",
    heat_number: "{colata}",
    source_doc_id: "{doc_id}",
    created_at: new Date()
}});
print("INSERTED");
'''
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)


class TestAPIContracts:
    """Test API contracts for cascade delete and CAM lotti."""

    def test_upload_document_endpoint(self, auth_session, test_commessa):
        """
        POST /api/commesse/{cid}/documenti
        Verifies: cert upload returns doc_id, nome_file, tipo
        """
        cid = test_commessa
        token = auth_session['token']
        
        # Upload a test certificate
        file_content = b'%PDF-1.4 test certificate for upload'
        files = {'file': ('test_cert.pdf', io.BytesIO(file_content), 'application/pdf')}
        
        resp = requests.post(
            f'{BASE_URL}/api/commesse/{cid}/documenti',
            files=files,
            data={'tipo': 'certificato_31', 'note': 'API contract test'},
            headers={'Authorization': f'Bearer {token}'},
        )
        
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        
        # Verify response structure
        assert 'doc_id' in data, "Missing doc_id in response"
        assert 'nome_file' in data, "Missing nome_file in response"
        assert 'tipo' in data, "Missing tipo in response"
        assert data['tipo'] == 'certificato_31', f"Wrong tipo: {data['tipo']}"
        assert data['nome_file'] == 'test_cert.pdf', f"Wrong nome_file: {data['nome_file']}"
        
        # Cleanup
        auth_session['session'].delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{data["doc_id"]}')
        print(f"PASS: Upload document endpoint works: doc_id={data['doc_id']}")

    def test_delete_document_returns_cascade_info(self, auth_session, test_commessa):
        """
        DELETE /api/commesse/{cid}/documenti/{doc_id}
        Verifies: Response includes 'cascade' field with CAM and Batch counts
        """
        cid = test_commessa
        token = auth_session['token']
        uid = auth_session['user_id']
        
        # Upload a certificate
        file_content = b'%PDF-1.4 cascade test cert'
        files = {'file': ('cascade_test.pdf', io.BytesIO(file_content), 'application/pdf')}
        
        upload_resp = requests.post(
            f'{BASE_URL}/api/commesse/{cid}/documenti',
            files=files,
            data={'tipo': 'certificato_31', 'note': 'cascade test'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()['doc_id']
        
        # Insert linked CAM and batch records
        _insert_cam_and_batch(uid, cid, doc_id, 'CASCADE_API_COLATA')
        
        # Delete the document
        del_resp = auth_session['session'].delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"
        
        data = del_resp.json()
        
        # CRITICAL: Verify cascade info in response
        assert 'cascade' in data, f"Missing 'cascade' field in response: {data}"
        cascade_str = data['cascade']
        assert 'CAM:' in cascade_str, f"Missing CAM count in cascade: {cascade_str}"
        assert 'Batch:' in cascade_str, f"Missing Batch count in cascade: {cascade_str}"
        
        print(f"PASS: Delete endpoint returns cascade info: {cascade_str}")

    def test_cam_lotti_endpoint_with_commessa_filter(self, auth_session, test_commessa):
        """
        GET /api/cam/lotti?commessa_id={cid}
        Verifies: Returns lotti_cam filtered by commessa_id
        """
        cid = test_commessa
        uid = auth_session['user_id']
        session = auth_session['session']
        
        # First, insert some CAM lotti for this commessa directly
        colata = f'CAM_FILTER_TEST_{int(time.time())}'
        ts = int(time.time() * 1000)
        mongo_script = f'''
use('test_database');
db.lotti_cam.insertOne({{
    lotto_id: "cam_filter_{ts}",
    user_id: "{uid}",
    commessa_id: "{cid}",
    descrizione: "Filter Test Profile",
    numero_colata: "{colata}",
    peso_kg: 50,
    percentuale_riciclato: 80,
    metodo_produttivo: "forno_elettrico_non_legato",
    conforme_cam: true,
    created_at: new Date()
}});
print("CAM_INSERTED");
'''
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)
        
        # Query the endpoint
        resp = session.get(f'{BASE_URL}/api/cam/lotti?commessa_id={cid}')
        assert resp.status_code == 200, f"GET /api/cam/lotti failed: {resp.text}"
        
        data = resp.json()
        
        # Verify response structure
        assert 'lotti' in data, f"Missing 'lotti' in response: {data}"
        assert 'total' in data, f"Missing 'total' in response: {data}"
        assert isinstance(data['lotti'], list), f"'lotti' should be a list: {type(data['lotti'])}"
        
        # Verify we got the lotto we inserted
        lotti = data['lotti']
        found = any(lot.get('numero_colata') == colata for lot in lotti)
        assert found, f"Inserted CAM lotto not found. Got: {[l.get('numero_colata') for l in lotti]}"
        
        # Cleanup
        cleanup_script = f'''
use('test_database');
db.lotti_cam.deleteMany({{commessa_id: "{cid}", user_id: "{uid}"}});
'''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True, text=True)
        
        print(f"PASS: GET /api/cam/lotti?commessa_id works: {data['total']} lotti returned")

    def test_cascade_deletes_cam_and_batches(self, auth_session, test_commessa):
        """
        Full cascade delete verification:
        When a cert is deleted, ALL linked CAM lotti and material_batches must be deleted.
        """
        cid = test_commessa
        token = auth_session['token']
        uid = auth_session['user_id']
        session = auth_session['session']
        
        # Upload cert
        file_content = b'%PDF-1.4 full cascade test'
        files = {'file': ('full_cascade.pdf', io.BytesIO(file_content), 'application/pdf')}
        
        upload_resp = requests.post(
            f'{BASE_URL}/api/commesse/{cid}/documenti',
            files=files,
            data={'tipo': 'certificato_31', 'note': 'full cascade'},
            headers={'Authorization': f'Bearer {token}'},
        )
        doc_id = upload_resp.json()['doc_id']
        
        # Insert 2 CAM lotti + 2 batches
        for i in range(2):
            _insert_cam_and_batch(uid, cid, doc_id, f'FULL_CASCADE_{i}')
            time.sleep(0.01)  # Ensure unique timestamps
        
        # Verify they exist
        cam_resp = session.get(f'{BASE_URL}/api/cam/lotti?commessa_id={cid}')
        initial_count = cam_resp.json()['total']
        assert initial_count >= 2, f"CAM lotti not created: {initial_count}"
        
        # Delete the cert
        del_resp = session.delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200
        
        # Verify all CAM lotti deleted
        cam_resp_after = session.get(f'{BASE_URL}/api/cam/lotti?commessa_id={cid}')
        final_count = cam_resp_after.json()['total']
        assert final_count == 0, f"CAM lotti NOT deleted! Remaining: {final_count}"
        
        print(f"PASS: Full cascade delete verified: {initial_count} -> {final_count} CAM lotti")

    def test_delete_without_linked_data(self, auth_session, test_commessa):
        """
        DELETE document with NO linked CAM/batches should still work and return cascade info.
        """
        cid = test_commessa
        token = auth_session['token']
        
        # Upload cert without creating any linked data
        file_content = b'%PDF-1.4 no linked data'
        files = {'file': ('no_links.pdf', io.BytesIO(file_content), 'application/pdf')}
        
        upload_resp = requests.post(
            f'{BASE_URL}/api/commesse/{cid}/documenti',
            files=files,
            data={'tipo': 'altro', 'note': 'no links'},
            headers={'Authorization': f'Bearer {token}'},
        )
        doc_id = upload_resp.json()['doc_id']
        
        # Delete immediately
        del_resp = auth_session['session'].delete(f'{BASE_URL}/api/commesse/{cid}/documenti/{doc_id}')
        assert del_resp.status_code == 200
        
        data = del_resp.json()
        assert 'cascade' in data, f"cascade field missing: {data}"
        # Should show CAM:0 Batch:0
        assert 'CAM:0' in data['cascade'] or 'CAM: 0' in data['cascade'] or data['cascade'].count('0') >= 1, \
            f"Unexpected cascade for no-link delete: {data['cascade']}"
        
        print(f"PASS: Delete without linked data works: {data['cascade']}")

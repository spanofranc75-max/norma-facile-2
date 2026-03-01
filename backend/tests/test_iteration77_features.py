"""
Iteration 77 Tests - Auto-compilation, Timeline, Fascicolo Completo, giorni_consegna

Tests cover:
1. GET /api/fascicolo-tecnico/{cid} - returns _auto_fields, _timeline, auto-populated data
2. GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf?docs=dop,ce - combines PDFs
3. POST /api/preventivi with giorni_consegna - saves correctly
4. GET /api/preventivi/{prev_id} - returns giorni_consegna
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials setup
@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated API calls."""
    import subprocess
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    user_id = f"test-user-iter77-{timestamp}"
    session_token = f"test_session_iter77_{timestamp}"
    
    mongo_script = f"""
    db = db.getSiblingDB('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.iter77.{timestamp}@example.com',
        name: 'Test Iter77 User',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, check=True)
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_script = f"""
    db = db.getSiblingDB('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    db.preventivi.deleteMany({{user_id: '{user_id}'}});
    db.commesse.deleteMany({{user_id: '{user_id}'}});
    db.clients.deleteMany({{user_id: '{user_id}'}});
    db.material_batches.deleteMany({{user_id: '{user_id}'}});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


@pytest.fixture(scope="module")
def auth_headers(test_session):
    """Return authorization headers for API requests."""
    return {"Authorization": f"Bearer {test_session['session_token']}"}


@pytest.fixture(scope="module")
def test_client(test_session, auth_headers):
    """Create a test client."""
    import subprocess
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    client_id = f"cli-iter77-{timestamp}"
    
    mongo_script = f"""
    db = db.getSiblingDB('test_database');
    db.clients.insertOne({{
        client_id: '{client_id}',
        user_id: '{test_session["user_id"]}',
        business_name: 'Test Client Iter77',
        vat_number: '01234567890',
        address: 'Via Test 123',
        cap: '40100',
        city: 'Bologna',
        province: 'BO',
        country: 'IT',
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, check=True)
    return client_id


@pytest.fixture(scope="module")
def test_preventivo_with_giorni(test_session, auth_headers, test_client):
    """Create a preventivo with giorni_consegna, numero_disegno, and ingegnere_disegno."""
    response = requests.post(
        f"{BASE_URL}/api/preventivi/",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "client_id": test_client,
            "subject": "Test Preventivo Iter77",
            "validity_days": 30,
            "giorni_consegna": 45,
            "numero_disegno": "DIS-TEST-001",
            "ingegnere_disegno": "Ing. Test Engineer",
            "classe_esecuzione": "EXC2",
            "lines": [
                {
                    "description": "Test item for iter77",
                    "quantity": 1,
                    "unit": "pz",
                    "unit_price": 1000.00,
                    "vat_rate": "22"
                }
            ]
        }
    )
    assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
    data = response.json()
    return data["preventivo_id"]


@pytest.fixture(scope="module")
def test_commessa_linked(test_session, auth_headers, test_preventivo_with_giorni):
    """Create a commessa linked to the preventivo."""
    import subprocess
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    commessa_id = f"comm-iter77-{timestamp}"
    
    mongo_script = f"""
    db = db.getSiblingDB('test_database');
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{test_session["user_id"]}',
        numero: 'COMM-IT77-001',
        title: 'Test Commessa Iter77',
        status: 'in_lavorazione',
        preventivo_id: '{test_preventivo_with_giorni}',
        fasi_produzione: [
            {{tipo: 'taglio', label: 'Taglio', stato: 'completato', data_inizio: '2026-01-01T09:00:00Z', data_fine: '2026-01-02T17:00:00Z'}},
            {{tipo: 'foratura', label: 'Foratura', stato: 'in_corso', data_inizio: '2026-01-03T09:00:00Z'}},
            {{tipo: 'assemblaggio', label: 'Assemblaggio', stato: 'da_fare'}},
            {{tipo: 'saldatura', label: 'Saldatura', stato: 'da_fare'}}
        ],
        fascicolo_tecnico: {{
            ddt_riferimento: 'DDT-001',
            ddt_data: '01/01/2026'
        }},
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, check=True)
    return commessa_id


class TestHealthEndpoint:
    """Basic health check."""
    
    def test_health(self):
        """API health endpoint returns healthy."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint returns {status: healthy}")


class TestPreventivoGiorniConsegna:
    """Tests for giorni_consegna field in preventivi."""
    
    def test_create_preventivo_with_giorni_consegna(self, auth_headers, test_client):
        """POST /api/preventivi with giorni_consegna saves correctly."""
        response = requests.post(
            f"{BASE_URL}/api/preventivi/",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "client_id": test_client,
                "subject": "Test giorni_consegna create",
                "validity_days": 30,
                "giorni_consegna": 60,
                "lines": [{"description": "Item 1", "quantity": 1, "unit_price": 500}]
            }
        )
        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()
        assert data.get("giorni_consegna") == 60, f"giorni_consegna not saved: {data.get('giorni_consegna')}"
        print(f"PASS: POST preventivo with giorni_consegna=60, got: {data.get('giorni_consegna')}")
        return data["preventivo_id"]
    
    def test_get_preventivo_returns_giorni_consegna(self, auth_headers, test_preventivo_with_giorni):
        """GET /api/preventivi/{prev_id} returns giorni_consegna field."""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/{test_preventivo_with_giorni}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET failed: {response.text}"
        data = response.json()
        assert "giorni_consegna" in data, f"giorni_consegna field missing: {data.keys()}"
        assert data["giorni_consegna"] == 45, f"giorni_consegna wrong value: {data.get('giorni_consegna')}"
        print(f"PASS: GET preventivo returns giorni_consegna=45: {data.get('giorni_consegna')}")
    
    def test_update_preventivo_giorni_consegna(self, auth_headers, test_preventivo_with_giorni):
        """PUT /api/preventivi/{prev_id} updates giorni_consegna."""
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{test_preventivo_with_giorni}",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"giorni_consegna": 90}
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        assert data.get("giorni_consegna") == 90, f"Update didn't work: {data.get('giorni_consegna')}"
        print(f"PASS: PUT preventivo updates giorni_consegna to 90: {data.get('giorni_consegna')}")


class TestFascicoloTecnicoAutoCompilation:
    """Tests for auto-compilation features in fascicolo tecnico."""
    
    def test_get_fascicolo_returns_auto_fields(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} returns _auto_fields list."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET fascicolo failed: {response.text}"
        data = response.json()
        
        # Check _auto_fields is present and is a list
        assert "_auto_fields" in data, f"_auto_fields key missing: {data.keys()}"
        assert isinstance(data["_auto_fields"], list), f"_auto_fields should be list: {type(data['_auto_fields'])}"
        print(f"PASS: _auto_fields present: {data['_auto_fields']}")
        
        # Auto-populated fields should include data from preventivo
        auto_fields = data["_auto_fields"]
        assert "disegno_numero" in auto_fields or "disegno_riferimento" in auto_fields, \
            f"Expected disegno fields in auto_fields: {auto_fields}"
        print(f"PASS: Auto fields include drawing info: {auto_fields}")
    
    def test_get_fascicolo_returns_timeline(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} returns _timeline from fasi_produzione."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET fascicolo failed: {response.text}"
        data = response.json()
        
        # Check _timeline is present and has entries
        assert "_timeline" in data, f"_timeline key missing: {data.keys()}"
        timeline = data["_timeline"]
        assert isinstance(timeline, list), f"_timeline should be list: {type(timeline)}"
        assert len(timeline) > 0, f"_timeline should have entries from fasi_produzione"
        
        # Check timeline structure
        first = timeline[0]
        assert "fase" in first, f"Timeline entry missing 'fase': {first}"
        assert "stato" in first, f"Timeline entry missing 'stato': {first}"
        print(f"PASS: _timeline has {len(timeline)} entries: {[t.get('fase') for t in timeline]}")
    
    def test_fascicolo_auto_populated_disegno(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} auto-populates disegno_numero from preventivo."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have disegno_numero from preventivo
        disegno = data.get("disegno_numero") or data.get("disegno_riferimento")
        assert disegno is not None, f"disegno fields should be auto-populated: disegno_numero={data.get('disegno_numero')}, disegno_riferimento={data.get('disegno_riferimento')}"
        print(f"PASS: Auto-populated disegno fields: disegno_numero={data.get('disegno_numero')}, disegno_riferimento={data.get('disegno_riferimento')}")
    
    def test_fascicolo_auto_populated_redatto_da(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} auto-populates redatto_da from preventivo.ingegnere_disegno."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # redatto_da should be populated from ingegnere_disegno
        redatto_da = data.get("redatto_da")
        assert redatto_da is not None, f"redatto_da should be auto-populated from ingegnere_disegno: {redatto_da}"
        print(f"PASS: Auto-populated redatto_da: {redatto_da}")
    
    def test_fascicolo_returns_giorni_consegna(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} returns _giorni_consegna from linked preventivo."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # _giorni_consegna should be present
        # Note: We updated giorni_consegna to 90 in earlier test, so it might be 90 or 45
        assert "_giorni_consegna" in data, f"_giorni_consegna key missing: {data.keys()}"
        print(f"PASS: _giorni_consegna returned: {data.get('_giorni_consegna')}")


class TestFascicoloCompletoPDF:
    """Tests for fascicolo-completo-pdf endpoint (PDF merging)."""
    
    def test_fascicolo_completo_all_docs(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf with all docs returns PDF."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/fascicolo-completo-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Fascicolo completo failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", \
            f"Expected PDF content-type: {response.headers.get('Content-Type')}"
        assert len(response.content) > 1000, f"PDF too small: {len(response.content)} bytes"
        print(f"PASS: Fascicolo completo PDF generated, size: {len(response.content)} bytes")
    
    def test_fascicolo_completo_dop_ce_only(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf?docs=dop,ce combines only DOP and CE."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/fascicolo-completo-pdf?docs=dop,ce",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Fascicolo completo dop,ce failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        # Combined PDF should be smaller than all docs
        print(f"PASS: Fascicolo completo (dop,ce) PDF generated, size: {len(response.content)} bytes")
    
    def test_fascicolo_completo_single_doc(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf?docs=piano generates single doc."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/fascicolo-completo-pdf?docs=piano",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Fascicolo completo piano failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"PASS: Fascicolo completo (piano only) PDF generated, size: {len(response.content)} bytes")
    
    def test_fascicolo_completo_custom_selection(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf?docs=dop,piano,vt,registro combines 4 docs."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/fascicolo-completo-pdf?docs=dop,piano,vt,registro",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Fascicolo completo custom selection failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"PASS: Fascicolo completo (dop,piano,vt,registro) PDF generated, size: {len(response.content)} bytes")


class TestIndividualPDFs:
    """Tests to ensure individual PDF endpoints still work."""
    
    def test_dop_pdf(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/dop-pdf works."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/dop-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"DOP PDF failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"PASS: DOP PDF generated, size: {len(response.content)} bytes")
    
    def test_ce_pdf(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/ce-pdf works."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/ce-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"CE PDF failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"PASS: CE PDF generated, size: {len(response.content)} bytes")
    
    def test_piano_controllo_pdf(self, auth_headers, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/piano-controllo-pdf works."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/piano-controllo-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Piano controllo PDF failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"PASS: Piano controllo PDF generated, size: {len(response.content)} bytes")


class TestAuthRequirements:
    """Test that endpoints require authentication."""
    
    def test_fascicolo_requires_auth(self, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid} returns 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Fascicolo endpoint requires auth (401)")
    
    def test_fascicolo_completo_requires_auth(self, test_commessa_linked):
        """GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf returns 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa_linked}/fascicolo-completo-pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Fascicolo completo endpoint requires auth (401)")

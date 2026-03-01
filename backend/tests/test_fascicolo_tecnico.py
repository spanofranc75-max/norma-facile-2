"""
Tests for Fascicolo Tecnico EN 1090 feature - All 6 document types:
DOP, CE, Piano Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico.
Tests: GET/PUT fascicolo data, all 6 PDF endpoints, auth requirements.
"""
import pytest
import requests
import uuid
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session setup
@pytest.fixture(scope="module")
def session():
    """Create requests session with headers"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def test_user_and_session():
    """Create test user and session for authenticated tests"""
    import subprocess
    import json
    
    user_id = f"ft_user_{uuid.uuid4().hex[:8]}"
    session_token = f"ft_session_{uuid.uuid4().hex[:16]}"
    
    # Create test user and session in MongoDB
    mongo_cmd = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'ft_test_{uuid.uuid4().hex[:6]}@example.com',
        name: 'FT Test User',
        picture: 'https://via.placeholder.com/150',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True)
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_cmd = f"""
    use('test_database');
    db.users.deleteOne({{ user_id: '{user_id}' }});
    db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
    db.commesse.deleteMany({{ user_id: '{user_id}' }});
    db.preventivi.deleteMany({{ user_id: '{user_id}' }});
    db.company_settings.deleteMany({{ user_id: '{user_id}' }});
    db.clients.deleteMany({{ user_id: '{user_id}' }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_cmd], capture_output=True)

@pytest.fixture(scope="module")
def auth_headers(test_user_and_session):
    """Get authorization headers with session token"""
    return {"Authorization": f"Bearer {test_user_and_session['session_token']}"}

@pytest.fixture(scope="module")
def test_commessa(session, auth_headers, test_user_and_session):
    """Create a test commessa for fascicolo tecnico testing"""
    import subprocess
    
    commessa_id = f"comm_ft_{uuid.uuid4().hex[:8]}"
    user_id = test_user_and_session['user_id']
    
    # Create commessa directly in DB
    mongo_cmd = f"""
    use('test_database');
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        numero: 'FT-TEST-001',
        title: 'Test Commessa per Fascicolo Tecnico',
        cliente_nome: 'Cliente Test FT',
        classe_esecuzione: 'EXC2',
        status: 'in_lavorazione',
        created_at: new Date(),
        updated_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True)
    
    yield commessa_id
    
    # Cleanup done in test_user_and_session cleanup

# ═══════════════════════════════════════════════════════════════
# HEALTH ENDPOINT TEST
# ═══════════════════════════════════════════════════════════════
class TestHealth:
    """Health check endpoint"""
    
    def test_health_endpoint(self, session):
        """GET /api/health returns 200 with healthy status"""
        r = session.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data.get("status") == "healthy"
        print("✓ Health endpoint OK")

# ═══════════════════════════════════════════════════════════════
# FASCICOLO TECNICO CRUD TESTS
# ═══════════════════════════════════════════════════════════════
class TestFascicoloTecnicoData:
    """Test GET/PUT fascicolo tecnico data"""
    
    def test_get_fascicolo_returns_default_phases(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid} returns default fascicolo data with 16 default phases"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}", headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Verify fasi is populated with defaults
        assert "fasi" in data, "Response should contain 'fasi' field"
        fasi = data.get("fasi", [])
        assert len(fasi) == 16, f"Expected 16 default phases, got {len(fasi)}"
        
        # Verify first phase structure
        if fasi:
            first_fase = fasi[0]
            assert "fase" in first_fase, "Phase should have 'fase' field"
            assert "doc_rif" in first_fase, "Phase should have 'doc_rif' field"
            assert "applicabile" in first_fase, "Phase should have 'applicabile' field"
        
        print(f"✓ GET fascicolo returns data with {len(fasi)} default phases")
    
    def test_put_fascicolo_saves_editable_data(self, session, auth_headers, test_commessa):
        """PUT /api/fascicolo-tecnico/{cid} saves editable data to commessa.fascicolo_tecnico"""
        update_data = {
            "ddt_riferimento": "DDT-2026-001",
            "ddt_data": "2026-01-15",
            "mandatario": "Test Mandatario Srl",
            "firmatario": "Mario Rossi",
            "ruolo_firmatario": "Direttore Tecnico",
            "luogo_data_firma": "Milano, 15/01/2026",
            "certificato_numero": "CERT-12345",
            "ente_notificato": "TUV Rheinland",
            "ente_numero": "0123",
            "materiali_saldabilita": "S355JR in accordo EN 10025-2",
            "resilienza": "27 Joule a +20°C",
            "disegno_riferimento": "DIS-FT-001",
            "dop_numero": "DOP-2026-001",
            "ordine_numero": "ORD-FT-001",
            "disegno_numero": "STR-001",
            "report_numero": "VT-2026-001",
            "report_data": "2026-01-15",
            "processo_saldatura": "135",
            "norma_procedura": "UNI EN ISO 17637 - IO 03",
            "accettabilita": "ISO 5817 livello C",
            "materiale": "S355JR",
            "profilato": "HEA 200",
            "spessore": "12mm"
        }
        
        r = session.put(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}",
            headers=auth_headers,
            json=update_data
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "message" in data
        
        # Verify data was saved by fetching again
        r2 = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}", headers=auth_headers)
        assert r2.status_code == 200
        saved_data = r2.json()
        
        assert saved_data.get("ddt_riferimento") == "DDT-2026-001"
        assert saved_data.get("firmatario") == "Mario Rossi"
        assert saved_data.get("certificato_numero") == "CERT-12345"
        
        print("✓ PUT fascicolo saves editable data correctly")

# ═══════════════════════════════════════════════════════════════
# AUTH REQUIREMENTS TESTS
# ═══════════════════════════════════════════════════════════════
class TestFascicoloAuth:
    """Test that all fascicolo endpoints require authentication"""
    
    def test_get_fascicolo_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid} returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ GET fascicolo requires auth (401 without token)")
    
    def test_put_fascicolo_requires_auth(self, session, test_commessa):
        """PUT /api/fascicolo-tecnico/{cid} returns 401 without token"""
        r = session.put(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}",
            json={"firmatario": "Test"}
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ PUT fascicolo requires auth (401 without token)")
    
    def test_dop_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/dop-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/dop-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ DOP PDF requires auth (401 without token)")
    
    def test_ce_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/ce-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/ce-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ CE PDF requires auth (401 without token)")
    
    def test_piano_controllo_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/piano-controllo-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/piano-controllo-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ Piano Controllo PDF requires auth (401 without token)")
    
    def test_rapporto_vt_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/rapporto-vt-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/rapporto-vt-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ Rapporto VT PDF requires auth (401 without token)")
    
    def test_registro_saldatura_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/registro-saldatura-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/registro-saldatura-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ Registro Saldatura PDF requires auth (401 without token)")
    
    def test_riesame_tecnico_pdf_requires_auth(self, session, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/riesame-tecnico-pdf returns 401 without token"""
        r = session.get(f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/riesame-tecnico-pdf")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        print("✓ Riesame Tecnico PDF requires auth (401 without token)")

# ═══════════════════════════════════════════════════════════════
# PDF GENERATION TESTS
# ═══════════════════════════════════════════════════════════════
class TestFascicoloPDFs:
    """Test all 6 PDF generation endpoints"""
    
    def test_dop_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/dop-pdf returns PDF (application/pdf content type)"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/dop-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", ""), \
            f"Expected application/pdf, got {r.headers.get('Content-Type')}"
        # Check PDF starts with %PDF
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ DOP PDF generated ({len(r.content)} bytes)")
    
    def test_ce_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/ce-pdf returns PDF"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/ce-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ CE PDF generated ({len(r.content)} bytes)")
    
    def test_piano_controllo_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/piano-controllo-pdf returns PDF (landscape A4)"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/piano-controllo-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Piano Controllo PDF generated ({len(r.content)} bytes)")
    
    def test_rapporto_vt_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/rapporto-vt-pdf returns PDF"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/rapporto-vt-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Rapporto VT PDF generated ({len(r.content)} bytes)")
    
    def test_registro_saldatura_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/registro-saldatura-pdf returns PDF (MOD. 04)"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/registro-saldatura-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Registro Saldatura PDF generated ({len(r.content)} bytes)")
    
    def test_riesame_tecnico_pdf_returns_pdf(self, session, auth_headers, test_commessa):
        """GET /api/fascicolo-tecnico/{cid}/riesame-tecnico-pdf returns PDF (MOD. 01)"""
        r = session.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{test_commessa}/riesame-tecnico-pdf",
            headers=auth_headers
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert r.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Riesame Tecnico PDF generated ({len(r.content)} bytes)")

# ═══════════════════════════════════════════════════════════════
# PREVENTIVO DISEGNO FIELDS TEST
# ═══════════════════════════════════════════════════════════════
class TestPreventivoDisegnoFields:
    """Test POST /api/preventivi creates preventivo with numero_disegno and ingegnere_disegno"""
    
    def test_create_preventivo_with_disegno_fields(self, session, auth_headers):
        """POST /api/preventivi creates preventivo with numero_disegno and ingegnere_disegno"""
        payload = {
            "subject": "Test Preventivo Disegno",
            "validity_days": 30,
            "notes": "Test note",
            "numero_disegno": "DIS-2026-001",
            "ingegnere_disegno": "Ing. Giovanni Bianchi",
            "normativa": "EN_1090",
            "lines": [
                {
                    "description": "Struttura metallica",
                    "quantity": 1,
                    "unit_price": 1500.00,
                    "unit": "corpo",
                    "vat_rate": "22"
                }
            ]
        }
        
        r = session.post(
            f"{BASE_URL}/api/preventivi/",
            headers=auth_headers,
            json=payload
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        
        assert data.get("numero_disegno") == "DIS-2026-001"
        assert data.get("ingegnere_disegno") == "Ing. Giovanni Bianchi"
        assert data.get("normativa") == "EN_1090"
        
        # Store preventivo_id for cleanup
        preventivo_id = data.get("preventivo_id")
        
        # Verify by GET
        r2 = session.get(f"{BASE_URL}/api/preventivi/{preventivo_id}", headers=auth_headers)
        assert r2.status_code == 200
        get_data = r2.json()
        assert get_data.get("numero_disegno") == "DIS-2026-001"
        assert get_data.get("ingegnere_disegno") == "Ing. Giovanni Bianchi"
        
        print("✓ Preventivo created with numero_disegno and ingegnere_disegno")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/preventivi/{preventivo_id}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

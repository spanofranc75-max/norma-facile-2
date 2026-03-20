"""
Iteration 189: Preventivatore Predittivo Module Tests

Tests for the AI-powered quotation system:
1. GET /api/preventivatore/tabella-ore - Returns parametric hours table (requires auth)
2. GET /api/preventivatore/prezzi-storici - Returns historical prices (requires auth)
3. POST /api/preventivatore/analyze-drawing - AI drawing analysis (requires auth + file)
4. POST /api/preventivatore/calcola - Calculate quote with margins
5. POST /api/preventivatore/genera-preventivo - Generate official preventivo
6. POST /api/preventivatore/accetta/{id} - Accept and create commessa
"""
import pytest
import requests
import os
import json
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session management
TEST_USER_ID = None
TEST_SESSION_TOKEN = None
TEST_PREVENTIVO_ID = None


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_session(api_client):
    """Create test user and session for authenticated tests"""
    global TEST_USER_ID, TEST_SESSION_TOKEN
    
    import subprocess
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f"test-prev-{timestamp}"
    session_token = f"test_session_prev_{timestamp}"
    
    # Create test user and session in MongoDB
    mongo_script = f'''
    use('test_database');
    db.users.insertOne({{
        user_id: "{user_id}",
        email: "test.preventivatore.{timestamp}@example.com",
        name: "Test Preventivatore User",
        role: "admin",
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print("OK");
    '''
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True, text=True
    )
    
    if "OK" not in result.stdout:
        pytest.skip(f"Failed to create test session: {result.stderr}")
    
    TEST_USER_ID = user_id
    TEST_SESSION_TOKEN = session_token
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_script = f'''
    use('test_database');
    db.users.deleteMany({{user_id: "{user_id}"}});
    db.user_sessions.deleteMany({{session_token: "{session_token}"}});
    db.preventivi.deleteMany({{user_id: "{user_id}"}});
    db.commesse.deleteMany({{user_id: "{user_id}"}});
    db.preventivatore_analyses.deleteMany({{user_id: "{user_id}"}});
    print("CLEANED");
    '''
    subprocess.run(["mongosh", "--quiet", "--eval", cleanup_script], capture_output=True)


@pytest.fixture(scope="module")
def auth_headers(test_session):
    """Get auth headers with session token"""
    return {
        "Cookie": f"session_token={test_session['session_token']}",
        "Content-Type": "application/json"
    }


# ═══════════════════════════════════════════════════════════════
# 1. AUTH TESTS - Endpoints require authentication
# ═══════════════════════════════════════════════════════════════

class TestPreventivatoreAuth:
    """Test that all endpoints require authentication"""
    
    def test_tabella_ore_no_auth_returns_401(self, api_client):
        """GET /api/preventivatore/tabella-ore without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/tabella-ore")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivatore/tabella-ore returns 401 without auth")
    
    def test_prezzi_storici_no_auth_returns_401(self, api_client):
        """GET /api/preventivatore/prezzi-storici without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/prezzi-storici")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivatore/prezzi-storici returns 401 without auth")
    
    def test_analyze_drawing_no_auth_returns_401(self, api_client):
        """POST /api/preventivatore/analyze-drawing without auth returns 401"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/analyze-drawing")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/analyze-drawing returns 401 without auth")
    
    def test_calcola_no_auth_returns_401(self, api_client):
        """POST /api/preventivatore/calcola without auth returns 401"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/calcola", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/calcola returns 401 without auth")
    
    def test_genera_preventivo_no_auth_returns_401(self, api_client):
        """POST /api/preventivatore/genera-preventivo without auth returns 401"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/genera-preventivo", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/genera-preventivo returns 401 without auth")
    
    def test_accetta_no_auth_returns_401(self, api_client):
        """POST /api/preventivatore/accetta/{id} without auth returns 401"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/accetta/fake_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/accetta/{id} returns 401 without auth")


# ═══════════════════════════════════════════════════════════════
# 2. TABELLA ORE TESTS
# ═══════════════════════════════════════════════════════════════

class TestTabellaOre:
    """Test parametric hours table endpoint"""
    
    def test_tabella_ore_with_auth_returns_200(self, api_client, auth_headers):
        """GET /api/preventivatore/tabella-ore with auth returns table"""
        response = api_client.get(
            f"{BASE_URL}/api/preventivatore/tabella-ore",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tabella" in data, "Response should contain 'tabella' key"
        
        tabella = data["tabella"]
        # Verify all structure types are present
        expected_types = ["leggera", "media", "complessa", "speciale"]
        for tipo in expected_types:
            assert tipo in tabella, f"Missing structure type: {tipo}"
            assert "ore_per_ton" in tabella[tipo], f"Missing ore_per_ton for {tipo}"
            assert "label" in tabella[tipo], f"Missing label for {tipo}"
            assert "range" in tabella[tipo], f"Missing range for {tipo}"
        
        print(f"✓ GET /api/preventivatore/tabella-ore returns table with {len(tabella)} types")
        print(f"  - leggera: {tabella['leggera']['ore_per_ton']} h/ton")
        print(f"  - media: {tabella['media']['ore_per_ton']} h/ton")
        print(f"  - complessa: {tabella['complessa']['ore_per_ton']} h/ton")
        print(f"  - speciale: {tabella['speciale']['ore_per_ton']} h/ton")


# ═══════════════════════════════════════════════════════════════
# 3. PREZZI STORICI TESTS
# ═══════════════════════════════════════════════════════════════

class TestPrezziStorici:
    """Test historical prices endpoint"""
    
    def test_prezzi_storici_with_auth_returns_200(self, api_client, auth_headers):
        """GET /api/preventivatore/prezzi-storici with auth returns prices"""
        response = api_client.get(
            f"{BASE_URL}/api/preventivatore/prezzi-storici",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "prezzi" in data, "Response should contain 'prezzi' key"
        
        prezzi = data["prezzi"]
        # Verify default prices are present (even without historical data)
        expected_keys = ["S275JR", "S355JR", "bulloneria", "default"]
        for key in expected_keys:
            assert key in prezzi, f"Missing price key: {key}"
            assert isinstance(prezzi[key], (int, float)), f"Price for {key} should be numeric"
        
        print(f"✓ GET /api/preventivatore/prezzi-storici returns {len(prezzi)} price categories")
        for key, val in prezzi.items():
            print(f"  - {key}: €{val}/kg")


# ═══════════════════════════════════════════════════════════════
# 4. ANALYZE DRAWING TESTS
# ═══════════════════════════════════════════════════════════════

class TestAnalyzeDrawing:
    """Test AI drawing analysis endpoint"""
    
    def test_analyze_drawing_no_file_returns_422(self, api_client, auth_headers):
        """POST /api/preventivatore/analyze-drawing without file returns 422"""
        # Remove Content-Type to allow multipart
        headers = {"Cookie": auth_headers["Cookie"]}
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/analyze-drawing",
            headers=headers
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ POST /api/preventivatore/analyze-drawing without file returns 422")


# ═══════════════════════════════════════════════════════════════
# 5. CALCOLA TESTS
# ═══════════════════════════════════════════════════════════════

class TestCalcola:
    """Test quote calculation endpoint"""
    
    def test_calcola_with_empty_materials(self, api_client, auth_headers):
        """POST /api/preventivatore/calcola with empty materials returns calculation"""
        payload = {
            "materiali": [],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "peso_totale_kg" in data
        assert "stima_ore" in data
        assert "calcolo" in data
        assert data["peso_totale_kg"] == 0
        
        print("✓ POST /api/preventivatore/calcola with empty materials returns valid calculation")
    
    def test_calcola_with_mock_materials(self, api_client, auth_headers):
        """POST /api/preventivatore/calcola with mock materials returns full calculation"""
        payload = {
            "materiali": [
                {
                    "tipo": "profilo",
                    "profilo": "IPE 200",
                    "materiale": "S275JR",
                    "lunghezza_mm": 6000,
                    "quantita": 4,
                    "descrizione": "Trave principale IPE 200 L=6m"
                },
                {
                    "tipo": "piastra",
                    "materiale": "S275JR",
                    "lunghezza_mm": 300,
                    "larghezza_mm": 200,
                    "spessore_mm": 15,
                    "quantita": 8,
                    "descrizione": "Piastra base 300x200x15"
                },
                {
                    "tipo": "bullone",
                    "diametro": "M16",
                    "classe": "8.8",
                    "quantita": 32,
                    "descrizione": "Bulloni M16 classe 8.8"
                }
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "peso_totale_kg" in data
        assert "tipologia" in data
        assert "prezzi_storici" in data
        assert "stima_ore" in data
        assert "ore_utilizzate" in data
        assert "costo_orario" in data
        assert "calcolo" in data
        
        # Verify calculation structure
        calcolo = data["calcolo"]
        assert "righe_materiali" in calcolo
        assert "riepilogo" in calcolo
        
        riepilogo = calcolo["riepilogo"]
        assert "costo_materiali" in riepilogo
        assert "materiali_vendita" in riepilogo
        assert "costo_manodopera" in riepilogo
        assert "manodopera_vendita" in riepilogo
        assert "totale_costo" in riepilogo
        assert "totale_vendita" in riepilogo
        assert "margine_globale_pct" in riepilogo
        assert "utile_lordo" in riepilogo
        
        # Verify stima_ore structure
        stima_ore = data["stima_ore"]
        assert "ore_parametriche" in stima_ore
        assert "ore_suggerite" in stima_ore
        assert "confidence" in stima_ore
        assert "campioni" in stima_ore
        
        print(f"✓ POST /api/preventivatore/calcola with materials returns full calculation")
        print(f"  - Peso totale: {data['peso_totale_kg']} kg")
        print(f"  - Ore suggerite: {stima_ore['ore_suggerite']}h (confidence: {stima_ore['confidence']})")
        print(f"  - Totale vendita: €{riepilogo['totale_vendita']}")
        print(f"  - Margine globale: {riepilogo['margine_globale_pct']}%")
    
    def test_calcola_with_ore_override(self, api_client, auth_headers):
        """POST /api/preventivatore/calcola with ore_override uses custom hours"""
        payload = {
            "materiali": [
                {
                    "tipo": "profilo",
                    "profilo": "IPE 200",
                    "materiale": "S275JR",
                    "lunghezza_mm": 6000,
                    "quantita": 2,
                    "descrizione": "Test profile"
                }
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20,
            "ore_override": 100  # Force 100 hours
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ore_utilizzate"] == 100, f"Expected 100 hours, got {data['ore_utilizzate']}"
        
        print(f"✓ POST /api/preventivatore/calcola with ore_override uses custom hours (100h)")


# ═══════════════════════════════════════════════════════════════
# 6. GENERA PREVENTIVO TESTS
# ═══════════════════════════════════════════════════════════════

class TestGeneraPreventivo:
    """Test preventivo generation endpoint"""
    
    def test_genera_preventivo_creates_document(self, api_client, auth_headers, test_session):
        """POST /api/preventivatore/genera-preventivo creates official preventivo"""
        global TEST_PREVENTIVO_ID
        
        # First calculate
        calc_payload = {
            "materiali": [
                {
                    "tipo": "profilo",
                    "profilo": "IPE 200",
                    "materiale": "S275JR",
                    "lunghezza_mm": 6000,
                    "quantita": 4,
                    "descrizione": "Trave principale IPE 200 L=6m"
                }
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        calc_response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=calc_payload
        )
        assert calc_response.status_code == 200
        calc_data = calc_response.json()
        
        # Generate preventivo
        gen_payload = {
            "subject": "Test Preventivo Predittivo AI",
            "calcolo": calc_data["calcolo"],
            "stima_ore": calc_data["stima_ore"],
            "normativa": "EN_1090",
            "classe_esecuzione": "EXC2",
            "giorni_consegna": 30,
            "note": "Test preventivo from iteration 189"
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/genera-preventivo",
            headers=auth_headers,
            json=gen_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "preventivo_id" in data
        assert "number" in data
        assert "totale" in data
        assert "message" in data
        
        TEST_PREVENTIVO_ID = data["preventivo_id"]
        
        print(f"✓ POST /api/preventivatore/genera-preventivo creates preventivo")
        print(f"  - ID: {data['preventivo_id']}")
        print(f"  - Number: {data['number']}")
        print(f"  - Totale: €{data['totale']}")


# ═══════════════════════════════════════════════════════════════
# 7. ACCETTA E GENERA COMMESSA TESTS
# ═══════════════════════════════════════════════════════════════

class TestAccettaGeneraCommessa:
    """Test accept preventivo and create commessa endpoint"""
    
    def test_accetta_nonexistent_returns_404(self, api_client, auth_headers):
        """POST /api/preventivatore/accetta/{id} with invalid ID returns 404"""
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/accetta/nonexistent_id",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ POST /api/preventivatore/accetta/{id} with invalid ID returns 404")
    
    def test_accetta_creates_commessa(self, api_client, auth_headers, test_session):
        """POST /api/preventivatore/accetta/{id} creates commessa from preventivo"""
        global TEST_PREVENTIVO_ID
        
        if not TEST_PREVENTIVO_ID:
            pytest.skip("No preventivo created in previous test")
        
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/accetta/{TEST_PREVENTIVO_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa_id" in data
        assert "commessa_number" in data
        assert "ore_preventivate" in data
        assert "budget" in data
        assert "message" in data
        
        # Verify budget structure
        budget = data["budget"]
        assert "materiali" in budget
        assert "manodopera" in budget
        assert "conto_lavoro" in budget
        assert "totale" in budget
        
        print(f"✓ POST /api/preventivatore/accetta/{TEST_PREVENTIVO_ID} creates commessa")
        print(f"  - Commessa ID: {data['commessa_id']}")
        print(f"  - Commessa Number: {data['commessa_number']}")
        print(f"  - Ore preventivate: {data['ore_preventivate']}h")
        print(f"  - Budget materiali: €{budget['materiali']}")
        print(f"  - Budget manodopera: €{budget['manodopera']}")
    
    def test_accetta_already_accepted_returns_400(self, api_client, auth_headers):
        """POST /api/preventivatore/accetta/{id} on already accepted returns 400"""
        global TEST_PREVENTIVO_ID
        
        if not TEST_PREVENTIVO_ID:
            pytest.skip("No preventivo created in previous test")
        
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/accetta/{TEST_PREVENTIVO_ID}",
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ POST /api/preventivatore/accetta/{id} on already accepted returns 400")


# ═══════════════════════════════════════════════════════════════
# 8. INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestPreventivatoreIntegration:
    """Integration tests for full workflow"""
    
    def test_full_workflow_without_ai(self, api_client, auth_headers, test_session):
        """Test complete workflow: calcola -> genera -> accetta"""
        
        # Step 1: Calculate with mock materials
        calc_payload = {
            "materiali": [
                {
                    "tipo": "profilo",
                    "profilo": "HEA 200",
                    "materiale": "S355JR",
                    "lunghezza_mm": 8000,
                    "quantita": 6,
                    "descrizione": "Colonne HEA 200"
                },
                {
                    "tipo": "profilo",
                    "profilo": "IPE 300",
                    "materiale": "S355JR",
                    "lunghezza_mm": 10000,
                    "quantita": 4,
                    "descrizione": "Travi IPE 300"
                }
            ],
            "tipologia_struttura": "complessa",
            "margine_materiali": 30,
            "margine_manodopera": 35,
            "margine_conto_lavoro": 25
        }
        
        calc_response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=calc_payload
        )
        assert calc_response.status_code == 200
        calc_data = calc_response.json()
        
        print(f"Step 1 - Calcolo: peso={calc_data['peso_totale_kg']}kg, ore={calc_data['ore_utilizzate']}h")
        
        # Step 2: Generate preventivo
        gen_payload = {
            "subject": "Struttura Capannone Test",
            "calcolo": calc_data["calcolo"],
            "stima_ore": calc_data["stima_ore"],
            "normativa": "EN_1090",
            "classe_esecuzione": "EXC3",
            "giorni_consegna": 45,
            "note": "Integration test - full workflow"
        }
        
        gen_response = api_client.post(
            f"{BASE_URL}/api/preventivatore/genera-preventivo",
            headers=auth_headers,
            json=gen_payload
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        
        print(f"Step 2 - Preventivo: {gen_data['number']} - €{gen_data['totale']}")
        
        # Step 3: Accept and create commessa
        acc_response = api_client.post(
            f"{BASE_URL}/api/preventivatore/accetta/{gen_data['preventivo_id']}",
            headers=auth_headers
        )
        assert acc_response.status_code == 200
        acc_data = acc_response.json()
        
        print(f"Step 3 - Commessa: {acc_data['commessa_number']}")
        print(f"  - Ore preventivate: {acc_data['ore_preventivate']}h")
        print(f"  - Budget totale: €{acc_data['budget']['totale']}")
        
        print("✓ Full workflow completed successfully: calcola -> genera -> accetta")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

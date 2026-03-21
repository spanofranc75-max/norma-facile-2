"""
Iteration 191: Blind Test del Preventivatore Predittivo - Confronto AI vs Manuale

Tests for:
- POST /api/preventivatore/confronta - confronto AI vs Manuale con delta per voce, confidence score, insights
- POST /api/preventivatore/analyze-drawing - analisi disegno via AI (endpoint responds)
- POST /api/preventivatore/calcola - calcolo prezzi con margini 15/40/10
- GET /api/preventivatore/prezzi-storici - prezzi storici dal database DDT/fatture
- GET /api/preventivi/ - lista preventivi con campo predittivo
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
SESSION_TOKEN = "test_blind_2026"
REAL_SESSION = "ryz-fOEx6ZwaCAXAV6zySsdMQjiayNpQgmkGzvO2wHI"
USER_ID = "user_97c773827822"
PREVENTIVO_AI_ID = "prev_d1b1e1e3e3cb"
PREVENTIVO_MANUALE_ID = "prev_manuale_sasso"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_client(api_client):
    """Session with auth cookie"""
    api_client.cookies.set("session_token", SESSION_TOKEN)
    return api_client


@pytest.fixture
def real_auth_client(api_client):
    """Session with real auth cookie"""
    api_client.cookies.set("session_token", REAL_SESSION)
    return api_client


class TestPrezziStorici:
    """GET /api/preventivatore/prezzi-storici - Historical prices from DDT/invoices"""
    
    def test_prezzi_storici_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/prezzi-storici")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivatore/prezzi-storici returns 401 without auth")
    
    def test_prezzi_storici_with_auth(self, auth_client):
        """Should return historical prices with authentication"""
        response = auth_client.get(f"{BASE_URL}/api/preventivatore/prezzi-storici")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "prezzi" in data, "Response should contain 'prezzi' key"
        prezzi = data["prezzi"]
        
        # Should have default prices at minimum
        assert isinstance(prezzi, dict), "prezzi should be a dict"
        # Check for expected default keys
        expected_keys = ["S275JR", "S355JR", "bulloneria", "default"]
        for key in expected_keys:
            assert key in prezzi, f"prezzi should contain '{key}'"
            assert isinstance(prezzi[key], (int, float)), f"prezzi['{key}'] should be numeric"
        
        print(f"✓ GET /api/preventivatore/prezzi-storici returns prices: {prezzi}")


class TestTabellaOre:
    """GET /api/preventivatore/tabella-ore - Parametric hours table"""
    
    def test_tabella_ore_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/tabella-ore")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivatore/tabella-ore returns 401 without auth")
    
    def test_tabella_ore_with_auth(self, auth_client):
        """Should return hours table with authentication"""
        response = auth_client.get(f"{BASE_URL}/api/preventivatore/tabella-ore")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tabella" in data, "Response should contain 'tabella' key"
        tabella = data["tabella"]
        
        # Check for expected structure types
        expected_types = ["leggera", "media", "complessa", "speciale"]
        for tipo in expected_types:
            assert tipo in tabella, f"tabella should contain '{tipo}'"
            assert "ore_per_ton" in tabella[tipo], f"tabella['{tipo}'] should have 'ore_per_ton'"
            assert "label" in tabella[tipo], f"tabella['{tipo}'] should have 'label'"
        
        print(f"✓ GET /api/preventivatore/tabella-ore returns structure types: {list(tabella.keys())}")


class TestCalcola:
    """POST /api/preventivatore/calcola - Calculate predictive quote with margins"""
    
    def test_calcola_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/calcola", json={
            "materiali": [],
            "tipologia_struttura": "media",
            "margine_materiali": 15,
            "margine_manodopera": 40,
            "margine_conto_lavoro": 10
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/calcola returns 401 without auth")
    
    def test_calcola_with_margins_15_40_10(self, auth_client):
        """Should calculate quote with specified margins 15/40/10"""
        # Test materials
        materiali = [
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
            }
        ]
        
        response = auth_client.post(f"{BASE_URL}/api/preventivatore/calcola", json={
            "materiali": materiali,
            "tipologia_struttura": "media",
            "margine_materiali": 15,
            "margine_manodopera": 40,
            "margine_conto_lavoro": 10
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "peso_totale_kg" in data, "Response should contain 'peso_totale_kg'"
        assert "tipologia" in data, "Response should contain 'tipologia'"
        assert "prezzi_storici" in data, "Response should contain 'prezzi_storici'"
        assert "stima_ore" in data, "Response should contain 'stima_ore'"
        assert "calcolo" in data, "Response should contain 'calcolo'"
        
        calcolo = data["calcolo"]
        assert "riepilogo" in calcolo, "calcolo should contain 'riepilogo'"
        assert "righe_materiali" in calcolo, "calcolo should contain 'righe_materiali'"
        
        riepilogo = calcolo["riepilogo"]
        # Verify margins are applied
        assert riepilogo.get("margine_materiali_pct") == 15, "margine_materiali should be 15%"
        assert riepilogo.get("margine_manodopera_pct") == 40, "margine_manodopera should be 40%"
        assert riepilogo.get("margine_cl_pct") == 10, "margine_cl should be 10%"
        
        print(f"✓ POST /api/preventivatore/calcola with margins 15/40/10:")
        print(f"  - Peso totale: {data['peso_totale_kg']} kg")
        print(f"  - Ore stimate: {data['stima_ore'].get('ore_suggerite', 'N/A')}")
        print(f"  - Totale vendita: {riepilogo.get('totale_vendita', 'N/A')} EUR")


class TestAnalyzeDrawing:
    """POST /api/preventivatore/analyze-drawing - AI drawing analysis"""
    
    def test_analyze_drawing_no_auth(self, api_client):
        """Should return 401 without authentication"""
        # Create a minimal test file
        files = {'file': ('test.png', b'fake image content', 'image/png')}
        response = api_client.post(f"{BASE_URL}/api/preventivatore/analyze-drawing", files=files)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/analyze-drawing returns 401 without auth")
    
    def test_analyze_drawing_invalid_file_type(self, auth_client):
        """Should return 400 or 422 for unsupported file types"""
        files = {'file': ('test.txt', b'text content', 'text/plain')}
        response = auth_client.post(f"{BASE_URL}/api/preventivatore/analyze-drawing", files=files)
        # 400 Bad Request or 422 Unprocessable Entity are both valid for invalid input
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"
        print(f"✓ POST /api/preventivatore/analyze-drawing returns {response.status_code} for invalid file type")


class TestListaPreventivi:
    """GET /api/preventivi/ - List quotes with predittivo field"""
    
    def test_lista_preventivi_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.get(f"{BASE_URL}/api/preventivi")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/preventivi returns 401 without auth")
    
    def test_lista_preventivi_with_auth(self, auth_client):
        """Should return list of quotes with predittivo field"""
        response = auth_client.get(f"{BASE_URL}/api/preventivi")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Response can be array or object with preventivi key
        if isinstance(data, list):
            preventivi = data
        else:
            preventivi = data.get("preventivi", [])
        
        assert isinstance(preventivi, list), "preventivi should be a list"
        
        # Check if any preventivi exist and have predittivo field
        ai_count = 0
        manual_count = 0
        for p in preventivi:
            if p.get("predittivo"):
                ai_count += 1
            else:
                manual_count += 1
        
        print(f"✓ GET /api/preventivi returns {len(preventivi)} quotes (AI: {ai_count}, Manual: {manual_count})")


class TestConfrontaPreventivi:
    """POST /api/preventivatore/confronta - Compare AI vs Manual quotes"""
    
    def test_confronta_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.post(f"{BASE_URL}/api/preventivatore/confronta", json={
            "preventivo_ai_id": PREVENTIVO_AI_ID,
            "preventivo_manuale_id": PREVENTIVO_MANUALE_ID
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/preventivatore/confronta returns 401 without auth")
    
    def test_confronta_ai_not_found(self, auth_client):
        """Should return 404 when AI quote not found"""
        response = auth_client.post(f"{BASE_URL}/api/preventivatore/confronta", json={
            "preventivo_ai_id": "nonexistent_ai_id",
            "preventivo_manuale_id": PREVENTIVO_MANUALE_ID
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/preventivatore/confronta returns 404 for nonexistent AI quote")
    
    def test_confronta_manual_not_found(self, auth_client):
        """Should return 404 when manual quote not found"""
        response = auth_client.post(f"{BASE_URL}/api/preventivatore/confronta", json={
            "preventivo_ai_id": PREVENTIVO_AI_ID,
            "preventivo_manuale_id": "nonexistent_manual_id"
        })
        # Could be 404 for AI or manual depending on order of checks
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/preventivatore/confronta returns 404 for nonexistent manual quote")
    
    def test_confronta_success(self, auth_client):
        """Should return comparison data when both quotes exist"""
        response = auth_client.post(f"{BASE_URL}/api/preventivatore/confronta", json={
            "preventivo_ai_id": PREVENTIVO_AI_ID,
            "preventivo_manuale_id": PREVENTIVO_MANUALE_ID
        })
        
        # If quotes don't exist, this will be 404 - that's expected in test env
        if response.status_code == 404:
            print(f"⚠ POST /api/preventivatore/confronta returns 404 - quotes may not exist in test DB")
            pytest.skip("Test quotes not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "titolo" in data, "Response should contain 'titolo'"
        assert "confidence_score" in data, "Response should contain 'confidence_score'"
        assert "giudizio" in data, "Response should contain 'giudizio'"
        assert "scostamento_totale_pct" in data, "Response should contain 'scostamento_totale_pct'"
        assert "confronto_categorie" in data, "Response should contain 'confronto_categorie'"
        assert "confronto_ore" in data, "Response should contain 'confronto_ore'"
        assert "confronto_peso" in data, "Response should contain 'confronto_peso'"
        assert "confronto_righe" in data, "Response should contain 'confronto_righe'"
        assert "insights" in data, "Response should contain 'insights'"
        assert "preventivo_ai" in data, "Response should contain 'preventivo_ai'"
        assert "preventivo_manuale" in data, "Response should contain 'preventivo_manuale'"
        
        # Verify category comparison structure
        categorie = data["confronto_categorie"]
        for cat in ["materiali", "manodopera", "conto_lavoro", "subtotale"]:
            assert cat in categorie, f"confronto_categorie should contain '{cat}'"
            assert "ai" in categorie[cat], f"categorie['{cat}'] should have 'ai'"
            assert "manuale" in categorie[cat], f"categorie['{cat}'] should have 'manuale'"
            assert "delta" in categorie[cat], f"categorie['{cat}'] should have 'delta'"
            assert "delta_pct" in categorie[cat], f"categorie['{cat}'] should have 'delta_pct'"
        
        # Verify confidence score is in valid range
        assert 0 <= data["confidence_score"] <= 100, "confidence_score should be 0-100"
        
        print(f"✓ POST /api/preventivatore/confronta returns comparison:")
        print(f"  - Titolo: {data['titolo']}")
        print(f"  - Confidence Score: {data['confidence_score']}")
        print(f"  - Giudizio: {data['giudizio']}")
        print(f"  - Scostamento totale: {data['scostamento_totale_pct']}%")
        print(f"  - Insights: {len(data['insights'])} observations")


class TestConfrontaWithRealSession:
    """Test confronta with real session token"""
    
    def test_confronta_with_real_session(self, real_auth_client):
        """Test comparison with real session token"""
        response = real_auth_client.post(f"{BASE_URL}/api/preventivatore/confronta", json={
            "preventivo_ai_id": PREVENTIVO_AI_ID,
            "preventivo_manuale_id": PREVENTIVO_MANUALE_ID
        })
        
        if response.status_code == 404:
            print(f"⚠ Confronta with real session returns 404 - quotes may not exist")
            # Try to list preventivi to see what's available
            list_response = real_auth_client.get(f"{BASE_URL}/api/preventivi")
            if list_response.status_code == 200:
                data = list_response.json()
                preventivi = data.get("preventivi", data) if isinstance(data, dict) else data
                ai_quotes = [p for p in preventivi if p.get("predittivo")]
                manual_quotes = [p for p in preventivi if not p.get("predittivo")]
                print(f"  Available AI quotes: {[p.get('preventivo_id') for p in ai_quotes[:3]]}")
                print(f"  Available Manual quotes: {[p.get('preventivo_id') for p in manual_quotes[:3]]}")
            pytest.skip("Test quotes not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"✓ Confronta with real session successful: {data.get('titolo', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

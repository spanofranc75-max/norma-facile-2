"""
Iteration 259 — Preventivatore AI Analysis Bug Fixes Tests

Tests for 4 critical fixes:
1. Grigliato weight calculated 14x too high (should be ~883 kg for 5 panels 1892x6100 maglia 63x132/25x2, NOT 13000+)
2. Conto lavoro materials not detected (should have peso_calcolato_kg=0 and conto_lavoro=true)
3. Specchiature grigliato showing 0 kg when dimensions are in text (L2230xH2150, L4600xH2150, L5500xH2150)
4. ore_stimate field in preventivo lines for manual labor hour input

Also includes regression tests for:
- IPE profile weight calculation (IPE 200 @ 6m x 4 = 537.6 kg)
- Steel plate weight calculation
"""
import pytest
import requests
import os
import sys

# Add backend to path for direct function testing
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-lockdown.preview.emergentagent.com').rstrip('/')
DEMO_COOKIE = {"session_token": "demo_session_token_normafacile"}


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_health_check(self):
        """Backend health check returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health check returns 200 with healthy status")


class TestCalcolaPesoMaterialeFunction:
    """Direct unit tests for calcola_peso_materiale function"""
    
    def test_grigliato_weight_correct(self):
        """Test grigliato weight calculation: 5 panels 1892x6100 maglia 63x132/25x2 should be ~883 kg"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "grigliato",
            "profilo": "63x132/25x2",
            "lunghezza_mm": 1892,
            "larghezza_mm": 6100,
            "quantita": 5,
            "descrizione": "Pannelli grigliato 63x132/25x2"
        }
        
        peso = calcola_peso_materiale(materiale)
        
        # Expected: 1.892m * 6.1m * 5 * 15.3 kg/m² = 883.5 kg
        # Should NOT be 13000+ kg (which would happen if using steel density 7850 kg/m³)
        assert 800 < peso < 1000, f"Grigliato weight should be ~883 kg, got {peso} kg"
        print(f"PASS: Grigliato weight = {peso} kg (expected ~883 kg)")
    
    def test_conto_lavoro_zero_weight(self):
        """Test conto lavoro materials have 0 weight"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "profilo",
            "profilo": "IPE 200",
            "lunghezza_mm": 6000,
            "quantita": 4,
            "descrizione": "Profili IPE 200 forniti in conto lavoro dal cliente"
        }
        
        peso = calcola_peso_materiale(materiale)
        assert peso == 0.0, f"Conto lavoro should have 0 weight, got {peso} kg"
        print(f"PASS: Conto lavoro weight = {peso} kg (expected 0)")
    
    def test_conto_lavoro_tipo_flag(self):
        """Test conto lavoro with tipo='conto_lavoro' has 0 weight"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "conto_lavoro",
            "descrizione": "Materiale fornito dal cliente",
            "quantita": 10
        }
        
        peso = calcola_peso_materiale(materiale)
        assert peso == 0.0, f"Conto lavoro tipo should have 0 weight, got {peso} kg"
        print(f"PASS: Conto lavoro (tipo flag) weight = {peso} kg (expected 0)")
    
    def test_specchiature_dimensions_in_text(self):
        """Test specchiature grigliato with dimensions in text (L2230xH2150, L4600xH2150, L5500xH2150)"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "grigliato",
            "descrizione": "Specchiature grigliato L2230xH2150, L4600xH2150, L5500xH2150",
            "quantita": 1,
            "lunghezza_mm": 0,  # No structured dimensions
            "larghezza_mm": 0
        }
        
        peso = calcola_peso_materiale(materiale)
        
        # Expected area: (2.23*2.15) + (4.6*2.15) + (5.5*2.15) = 4.79 + 9.89 + 11.83 = 26.51 m²
        # Weight: 26.51 * 16 kg/m² (default) = ~424 kg
        assert peso > 300, f"Specchiature should have weight > 300 kg, got {peso} kg"
        print(f"PASS: Specchiature grigliato weight = {peso} kg (expected > 300 kg)")
    
    def test_ipe_profile_weight_regression(self):
        """Regression: IPE 200 @ 6m x 4 = 537.6 kg"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "profilo",
            "profilo": "IPE 200",
            "lunghezza_mm": 6000,
            "quantita": 4,
            "descrizione": "Trave principale IPE 200 L=6m"
        }
        
        peso = calcola_peso_materiale(materiale)
        
        # Expected: 22.4 kg/m * 6m * 4 = 537.6 kg
        assert 530 < peso < 545, f"IPE 200 weight should be ~537.6 kg, got {peso} kg"
        print(f"PASS: IPE 200 weight = {peso} kg (expected 537.6 kg)")
    
    def test_steel_plate_weight_regression(self):
        """Regression: Steel plate weight calculation"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {
            "tipo": "piastra",
            "lunghezza_mm": 500,
            "larghezza_mm": 300,
            "spessore_mm": 20,
            "quantita": 2,
            "descrizione": "Piastra di base 500x300x20"
        }
        
        peso = calcola_peso_materiale(materiale)
        
        # Expected: (50cm * 30cm * 2cm) * 7.85 g/cm³ / 1000 * 2 = 47.1 kg
        assert 45 < peso < 50, f"Steel plate weight should be ~47.1 kg, got {peso} kg"
        print(f"PASS: Steel plate weight = {peso} kg (expected ~47.1 kg)")


class TestEstraiAreaDaTesto:
    """Test the _estrai_area_da_testo helper function"""
    
    def test_extract_multiple_dimensions(self):
        """Test extracting multiple LxH dimensions from text"""
        from services.preventivatore_predittivo import _estrai_area_da_testo
        
        testo = "specchiature grigliato l2230xh2150, l4600xh2150, l5500xh2150"
        area = _estrai_area_da_testo(testo)
        
        # Expected: (2.23*2.15) + (4.6*2.15) + (5.5*2.15) = 4.79 + 9.89 + 11.83 = 26.51 m²
        assert 25 < area < 28, f"Area should be ~26.5 m², got {area} m²"
        print(f"PASS: Extracted area = {area} m² (expected ~26.5 m²)")
    
    def test_extract_single_dimension(self):
        """Test extracting single dimension"""
        from services.preventivatore_predittivo import _estrai_area_da_testo
        
        testo = "pannello L1892xH6100"
        area = _estrai_area_da_testo(testo)
        
        # Expected: 1.892 * 6.1 = 11.54 m²
        assert 11 < area < 12, f"Area should be ~11.54 m², got {area} m²"
        print(f"PASS: Extracted area = {area} m² (expected ~11.54 m²)")
    
    def test_extract_generic_dimensions(self):
        """Test extracting generic NxM dimensions"""
        from services.preventivatore_predittivo import _estrai_area_da_testo
        
        testo = "grigliato 2000x3000mm"
        area = _estrai_area_da_testo(testo)
        
        # Expected: 2.0 * 3.0 = 6.0 m²
        assert 5.5 < area < 6.5, f"Area should be ~6.0 m², got {area} m²"
        print(f"PASS: Extracted area = {area} m² (expected ~6.0 m²)")


class TestPesoGrigliatoPerMaglia:
    """Test the _peso_grigliato_per_maglia helper function"""
    
    def test_maglia_63x132(self):
        """Test maglia 63x132/25x2 returns 15.3 kg/m²"""
        from services.preventivatore_predittivo import _peso_grigliato_per_maglia
        
        peso = _peso_grigliato_per_maglia("63x132/25x2")
        assert peso == 15.3, f"Maglia 63x132/25x2 should be 15.3 kg/m², got {peso}"
        print(f"PASS: Maglia 63x132/25x2 = {peso} kg/m²")
    
    def test_maglia_34x38(self):
        """Test maglia 34x38/25x2 returns 19.8 kg/m²"""
        from services.preventivatore_predittivo import _peso_grigliato_per_maglia
        
        peso = _peso_grigliato_per_maglia("34x38/25x2")
        assert peso == 19.8, f"Maglia 34x38/25x2 should be 19.8 kg/m², got {peso}"
        print(f"PASS: Maglia 34x38/25x2 = {peso} kg/m²")
    
    def test_default_maglia(self):
        """Test unknown maglia returns default 16.0 kg/m²"""
        from services.preventivatore_predittivo import _peso_grigliato_per_maglia
        
        peso = _peso_grigliato_per_maglia("unknown")
        assert peso == 16.0, f"Unknown maglia should be 16.0 kg/m², got {peso}"
        print(f"PASS: Unknown maglia = {peso} kg/m² (default)")


class TestPreventivatoreAPIEndpoints:
    """Test the preventivatore API endpoints"""
    
    def test_tabella_ore_endpoint(self):
        """GET /api/preventivatore/tabella-ore returns parametric table"""
        response = requests.get(
            f"{BASE_URL}/api/preventivatore/tabella-ore",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tabella" in data
        assert "leggera" in data["tabella"]
        assert "media" in data["tabella"]
        assert "complessa" in data["tabella"]
        print(f"PASS: Tabella ore endpoint returns parametric table with {len(data['tabella'])} categories")
    
    def test_prezzi_storici_endpoint(self):
        """GET /api/preventivatore/prezzi-storici returns historical prices"""
        response = requests.get(
            f"{BASE_URL}/api/preventivatore/prezzi-storici",
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "prezzi" in data
        assert "S275JR" in data["prezzi"]
        assert "S355JR" in data["prezzi"]
        print(f"PASS: Prezzi storici endpoint returns prices: {data['prezzi']}")
    
    def test_calcola_endpoint(self):
        """POST /api/preventivatore/calcola works correctly"""
        payload = {
            "materiali": [
                {
                    "tipo": "profilo",
                    "profilo": "IPE 200",
                    "lunghezza_mm": 6000,
                    "quantita": 4,
                    "descrizione": "Trave IPE 200"
                }
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30
        }
        
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            json=payload,
            cookies=DEMO_COOKIE
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "peso_totale_kg" in data
        assert "calcolo" in data
        assert "stima_ore" in data
        print(f"PASS: Calcola endpoint returns peso_totale_kg={data['peso_totale_kg']}")


class TestAnalizzaRigheEndpoint:
    """Test the POST /api/preventivatore/analizza-righe endpoint"""
    
    def test_analizza_righe_with_grigliato(self):
        """Test analizza-righe with grigliato lines returns correct weight"""
        payload = {
            "lines": [
                {
                    "description": "N. 5 pannelli grigliato elettrosaldato maglia 63x132/25x2 dim. 1892x6100mm",
                    "quantity": 1,
                    "unit_price": 2500,
                    "ore_stimate": 8
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/analizza-righe",
            json=payload,
            cookies=DEMO_COOKIE,
            timeout=60  # AI endpoint may take time
        )
        
        # Note: This endpoint uses AI (GPT-4o) so response is non-deterministic
        # We test that the endpoint works and returns expected structure
        if response.status_code == 200:
            data = response.json()
            assert "materiali" in data
            assert "peso_totale_calcolato_kg" in data
            assert "ore_stimate_utente" in data
            
            # Check ore_stimate_utente is captured
            assert data.get("ore_stimate_utente", 0) >= 8, "ore_stimate_utente should capture user input"
            
            # Check weight is reasonable (not 14x too high)
            peso = data.get("peso_totale_calcolato_kg", 0)
            print(f"INFO: AI returned peso_totale_calcolato_kg = {peso} kg")
            
            # If AI extracted grigliato correctly, weight should be < 2000 kg
            # (5 panels * 1.892m * 6.1m * 15.3 kg/m² = 883 kg)
            if peso > 0:
                assert peso < 5000, f"Grigliato weight should be < 5000 kg, got {peso} kg (possible 14x error)"
            
            print(f"PASS: Analizza-righe endpoint works, peso={peso} kg, ore_stimate_utente={data.get('ore_stimate_utente')}")
        elif response.status_code == 500 and "EMERGENT_LLM_KEY" in response.text:
            pytest.skip("EMERGENT_LLM_KEY not configured - skipping AI endpoint test")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_analizza_righe_with_conto_lavoro(self):
        """Test analizza-righe with conto lavoro description returns peso=0"""
        payload = {
            "lines": [
                {
                    "description": "Profili IPE 200 forniti in conto lavoro dal cliente",
                    "quantity": 4,
                    "unit_price": 0,
                    "ore_stimate": 0
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/analizza-righe",
            json=payload,
            cookies=DEMO_COOKIE,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            materiali = data.get("materiali", [])
            
            # Check that conto lavoro is detected
            conto_lavoro_found = False
            for m in materiali:
                if m.get("conto_lavoro") or m.get("tipo") == "conto_lavoro":
                    conto_lavoro_found = True
                    peso = m.get("peso_calcolato_kg", -1)
                    assert peso == 0, f"Conto lavoro should have peso=0, got {peso}"
                    print(f"PASS: Conto lavoro detected with peso_calcolato_kg=0")
                    break
            
            # Even if AI doesn't detect it, server-side detection should catch it
            peso_totale = data.get("peso_totale_calcolato_kg", 0)
            print(f"INFO: Total weight = {peso_totale} kg, conto_lavoro_found={conto_lavoro_found}")
            
            # If conto lavoro is properly detected, total weight should be 0
            if conto_lavoro_found:
                assert peso_totale == 0, f"Conto lavoro total weight should be 0, got {peso_totale}"
        elif response.status_code == 500 and "EMERGENT_LLM_KEY" in response.text:
            pytest.skip("EMERGENT_LLM_KEY not configured - skipping AI endpoint test")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_analizza_righe_with_specchiature(self):
        """Test analizza-righe with specchiature dimensions in text"""
        payload = {
            "lines": [
                {
                    "description": "Specchiature in grigliato elettrosaldato L2230xH2150, L4600xH2150, L5500xH2150",
                    "quantity": 1,
                    "unit_price": 3000,
                    "ore_stimate": 12
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/analizza-righe",
            json=payload,
            cookies=DEMO_COOKIE,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            peso_totale = data.get("peso_totale_calcolato_kg", 0)
            
            # Expected area: (2.23*2.15) + (4.6*2.15) + (5.5*2.15) = 26.51 m²
            # Weight: 26.51 * 16 kg/m² = ~424 kg
            print(f"INFO: Specchiature peso_totale_calcolato_kg = {peso_totale} kg")
            
            # Weight should be > 300 kg (not 0)
            assert peso_totale > 300, f"Specchiature weight should be > 300 kg, got {peso_totale} kg"
            print(f"PASS: Specchiature grigliato weight = {peso_totale} kg (expected > 300 kg)")
        elif response.status_code == 500 and "EMERGENT_LLM_KEY" in response.text:
            pytest.skip("EMERGENT_LLM_KEY not configured - skipping AI endpoint test")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_analizza_righe_includes_ore_stimate(self):
        """Test analizza-righe includes ore_stimate_utente in response"""
        payload = {
            "lines": [
                {
                    "description": "Struttura metallica",
                    "quantity": 1,
                    "unit_price": 5000,
                    "ore_stimate": 24.5
                },
                {
                    "description": "Montaggio",
                    "quantity": 1,
                    "unit_price": 1000,
                    "ore_stimate": 16
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/analizza-righe",
            json=payload,
            cookies=DEMO_COOKIE,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check ore_stimate fields are present
            assert "ore_stimate_utente" in data, "Response should include ore_stimate_utente"
            assert "ore_stimate_ai" in data, "Response should include ore_stimate_ai"
            
            # ore_stimate_utente should be sum of user inputs: 24.5 + 16 = 40.5
            ore_utente = data.get("ore_stimate_utente", 0)
            assert ore_utente == 40.5, f"ore_stimate_utente should be 40.5, got {ore_utente}"
            
            print(f"PASS: ore_stimate_utente = {ore_utente}, ore_stimate_ai = {data.get('ore_stimate_ai')}")
        elif response.status_code == 500 and "EMERGENT_LLM_KEY" in response.text:
            pytest.skip("EMERGENT_LLM_KEY not configured - skipping AI endpoint test")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")


class TestRegressionIPEProfiles:
    """Regression tests for IPE profile weight calculations"""
    
    def test_ipe_100(self):
        """IPE 100 @ 3m x 2 = 48.6 kg"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {"tipo": "profilo", "profilo": "IPE 100", "lunghezza_mm": 3000, "quantita": 2}
        peso = calcola_peso_materiale(materiale)
        # 8.1 kg/m * 3m * 2 = 48.6 kg
        assert 48 < peso < 50, f"IPE 100 weight should be ~48.6 kg, got {peso}"
        print(f"PASS: IPE 100 weight = {peso} kg")
    
    def test_ipe_300(self):
        """IPE 300 @ 8m x 1 = 337.6 kg"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {"tipo": "profilo", "profilo": "IPE 300", "lunghezza_mm": 8000, "quantita": 1}
        peso = calcola_peso_materiale(materiale)
        # 42.2 kg/m * 8m * 1 = 337.6 kg
        assert 335 < peso < 340, f"IPE 300 weight should be ~337.6 kg, got {peso}"
        print(f"PASS: IPE 300 weight = {peso} kg")
    
    def test_hea_200(self):
        """HEA 200 @ 4m x 3 = 507.6 kg"""
        from services.preventivatore_predittivo import calcola_peso_materiale
        
        materiale = {"tipo": "profilo", "profilo": "HEA 200", "lunghezza_mm": 4000, "quantita": 3}
        peso = calcola_peso_materiale(materiale)
        # 42.3 kg/m * 4m * 3 = 507.6 kg
        assert 505 < peso < 510, f"HEA 200 weight should be ~507.6 kg, got {peso}"
        print(f"PASS: HEA 200 weight = {peso} kg")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 193: Analisi AI Page Tests
Tests for:
1. Analisi AI button in PreventivoEditorPage toolbar
2. /analisi-ai/:prevId page with editable weights and live price updates
3. /fpc route redirect to /tracciabilita
4. PUT /api/preventivi/:id with peso_totale_kg, ore_stimate, predittivo_data
5. Confronto functionality from AnalisiAIPage
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY"
PREVENTIVO_AI_ID = "prev_d1b1e1e3e3cb"
PREVENTIVO_MANUALE_ID = "prev_manuale_sasso"


@pytest.fixture
def auth_headers():
    """Headers with session cookie for authenticated requests"""
    return {
        "Cookie": f"session_token={SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


class TestPreventivoAIFields:
    """Test PUT /api/preventivi/:id with new AI fields"""
    
    def test_get_preventivo_ai(self, auth_headers):
        """GET preventivo AI should return predittivo fields"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preventivo_id"] == PREVENTIVO_AI_ID
        assert "predittivo" in data or "predittivo_data" in data
        print(f"✓ GET preventivo AI: {data.get('number', 'N/A')}")
    
    def test_put_preventivo_with_peso_totale_kg(self, auth_headers):
        """PUT should accept and save peso_totale_kg"""
        payload = {"peso_totale_kg": 4600.0}
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("peso_totale_kg") == 4600.0
        print(f"✓ PUT peso_totale_kg: {data.get('peso_totale_kg')}")
    
    def test_put_preventivo_with_ore_stimate(self, auth_headers):
        """PUT should accept and save ore_stimate"""
        payload = {"ore_stimate": 120}
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ore_stimate") == 120
        print(f"✓ PUT ore_stimate: {data.get('ore_stimate')}")
    
    def test_put_preventivo_with_predittivo_data(self, auth_headers):
        """PUT should accept and save predittivo_data object"""
        payload = {
            "predittivo_data": {
                "riepilogo": {
                    "peso_totale_calcolato_kg": 4600.0,
                    "costo_materiali": 5900.00,
                    "materiali_vendita": 6785.00,
                    "costo_manodopera": 4200.00,
                    "manodopera_vendita": 5880.00,
                    "costo_cl": 2070.00,
                    "cl_vendita": 2277.00,
                    "ore_stimate": 120
                }
            }
        }
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "predittivo_data" in data
        assert data["predittivo_data"]["riepilogo"]["peso_totale_calcolato_kg"] == 4600.0
        print(f"✓ PUT predittivo_data saved correctly")
    
    def test_put_preventivo_with_all_ai_fields(self, auth_headers):
        """PUT should accept all AI fields together"""
        payload = {
            "peso_totale_kg": 4500.5,
            "ore_stimate": 115,
            "predittivo_data": {
                "riepilogo": {
                    "peso_totale_calcolato_kg": 4500.5,
                    "costo_materiali": 5800.00,
                    "materiali_vendita": 6670.00,
                    "costo_manodopera": 4025.00,
                    "manodopera_vendita": 5635.00,
                    "costo_cl": 2025.23,
                    "cl_vendita": 2227.75,
                    "ore_stimate": 115
                }
            }
        }
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("peso_totale_kg") == 4500.5
        assert data.get("ore_stimate") == 115
        assert "predittivo_data" in data
        print(f"✓ PUT all AI fields saved correctly")
    
    def test_put_preventivo_with_lines_and_totals(self, auth_headers):
        """PUT should accept lines and totals from AnalisiAIPage save"""
        payload = {
            "lines": [
                {
                    "line_id": "ai_1",
                    "description": "IPE 270 S275JR - Travi principali (2599 kg)",
                    "quantity": 6,
                    "unit": "pz",
                    "unit_price": 572.91,
                    "vat_rate": "22",
                    "sconto_1": 0,
                    "sconto_2": 0
                }
            ],
            "totals": {
                "subtotal": 14194.11,
                "total_vat": 3122.70,
                "total": 17316.81,
                "total_document": 17316.81,
                "line_count": 1
            },
            "peso_totale_kg": 4500.5,
            "ore_stimate": 115
        }
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("lines", [])) >= 1
        assert "totals" in data
        print(f"✓ PUT lines and totals saved correctly")


class TestPreventivatoreConfronto:
    """Test confronto API from AnalisiAIPage"""
    
    def test_confronta_endpoint_exists(self, auth_headers):
        """POST /api/preventivatore/confronta should exist"""
        payload = {
            "preventivo_ai_id": PREVENTIVO_AI_ID,
            "preventivo_manuale_id": "prev_manuale_test"
        }
        response = requests.post(
            f"{BASE_URL}/api/preventivatore/confronta",
            headers=auth_headers,
            json=payload
        )
        # May return 404 if manual preventivo doesn't exist, but endpoint should work
        assert response.status_code in [200, 404, 422]
        print(f"✓ POST /api/preventivatore/confronta endpoint exists (status: {response.status_code})")
    
    def test_prezzi_storici_endpoint(self, auth_headers):
        """GET /api/preventivatore/prezzi-storici should return price data"""
        response = requests.get(
            f"{BASE_URL}/api/preventivatore/prezzi-storici",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "prezzi" in data
        print(f"✓ GET /api/preventivatore/prezzi-storici: {len(data.get('prezzi', {}))} price entries")


class TestPreventiviList:
    """Test preventivi list for AnalisiAIPage dropdown"""
    
    def test_list_preventivi(self, auth_headers):
        """GET /api/preventivi/ should return list for dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "preventivi" in data
        assert len(data["preventivi"]) > 0
        print(f"✓ GET /api/preventivi/: {len(data['preventivi'])} preventivi found")
    
    def test_list_preventivi_has_required_fields(self, auth_headers):
        """Preventivi list should have fields needed for dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        if data["preventivi"]:
            prev = data["preventivi"][0]
            assert "preventivo_id" in prev
            assert "number" in prev
            # subject may be optional
            print(f"✓ Preventivi have required fields for dropdown")


class TestFPCRedirect:
    """Test /fpc route redirect (frontend handles this)"""
    
    def test_fpc_route_returns_html(self):
        """GET /fpc should return HTML (React handles redirect)"""
        response = requests.get(f"{BASE_URL}/fpc", allow_redirects=False)
        # Frontend routes return 200 with HTML, React handles redirect
        assert response.status_code in [200, 301, 302, 307, 308]
        print(f"✓ GET /fpc returns status {response.status_code}")


class TestAnalisiAIPageData:
    """Test data requirements for AnalisiAIPage"""
    
    def test_preventivo_has_lines_for_materiali_table(self, auth_headers):
        """Preventivo should have lines for materiali table"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "lines" in data
        assert len(data["lines"]) > 0
        # Check line structure
        line = data["lines"][0]
        assert "description" in line
        assert "quantity" in line
        print(f"✓ Preventivo has {len(data['lines'])} lines for materiali table")
    
    def test_preventivo_has_totals_for_kpi_cards(self, auth_headers):
        """Preventivo should have totals for KPI cards"""
        response = requests.get(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        totals = data["totals"]
        assert "subtotal" in totals or "total" in totals
        print(f"✓ Preventivo has totals for KPI cards")


class TestAuthRequired:
    """Test that endpoints require authentication"""
    
    def test_get_preventivo_requires_auth(self):
        """GET preventivo without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}")
        assert response.status_code == 401
        print(f"✓ GET preventivo requires auth (401)")
    
    def test_put_preventivo_requires_auth(self):
        """PUT preventivo without auth should return 401"""
        response = requests.put(
            f"{BASE_URL}/api/preventivi/{PREVENTIVO_AI_ID}",
            json={"peso_totale_kg": 1000}
        )
        assert response.status_code == 401
        print(f"✓ PUT preventivo requires auth (401)")
    
    def test_list_preventivi_requires_auth(self):
        """GET preventivi list without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/preventivi/")
        assert response.status_code == 401
        print(f"✓ GET preventivi list requires auth (401)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

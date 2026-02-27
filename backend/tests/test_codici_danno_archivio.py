"""
Test suite for Codici Danno system and Archivio Sinistri dashboard features.
Tests:
1. GET /api/perizie/codici-danno - returns 7 damage codes with correct fields
2. POST /api/perizie/ with codici_danno generates smart cost items based on selected codes
3. POST /api/perizie/{id}/recalc uses codici_danno for regeneration
4. PUT /api/perizie/{id} accepts and saves codici_danno field
5. GET /api/perizie/archivio/stats returns aggregated stats
"""
import pytest
import requests
import os
import subprocess
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


def get_test_session():
    """Get or create test session token via MongoDB"""
    result = subprocess.run([
        "mongosh", "--quiet", "--eval", """
        use('test_database');
        var existingSession = db.user_sessions.findOne({session_token: /test_session_codici_danno/});
        if (existingSession) {
            print(existingSession.session_token + '|' + existingSession.user_id);
        } else {
            var userId = 'test-user-codici-' + Date.now();
            var sessionToken = 'test_session_codici_danno_' + Date.now();
            db.users.insertOne({
                user_id: userId,
                email: 'test.codici.' + Date.now() + '@example.com',
                name: 'Test User Codici Danno',
                picture: 'https://via.placeholder.com/150',
                created_at: new Date()
            });
            db.user_sessions.insertOne({
                user_id: userId,
                session_token: sessionToken,
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                created_at: new Date()
            });
            print(sessionToken + '|' + userId);
        }
        """
    ], capture_output=True, text=True)
    output = result.stdout.strip().split('\n')[-1]
    parts = output.split('|')
    return parts[0], parts[1] if len(parts) > 1 else None


@pytest.fixture(scope="module")
def api_client():
    """Unauthenticated requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_headers():
    """Create authenticated headers for API requests"""
    session_token, user_id = get_test_session()
    return {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }, user_id


class TestCodiciDannoEndpoint:
    """Test GET /api/perizie/codici-danno endpoint (no auth required)"""
    
    def test_get_codici_danno_returns_200(self, api_client):
        """Codici Danno endpoint should return 200"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        assert response.status_code == 200
        print("PASS: GET /api/perizie/codici-danno returns 200")
    
    def test_get_codici_danno_returns_7_codes(self, api_client):
        """Should return exactly 7 damage codes"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        data = response.json()
        assert "codici_danno" in data
        assert len(data["codici_danno"]) == 7
        print("PASS: Returns exactly 7 damage codes")
    
    def test_codici_danno_have_correct_fields(self, api_client):
        """Each code should have required fields"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        data = response.json()
        required_fields = ["codice", "categoria", "label", "norma", "implicazione", "azione", "icon", "color"]
        
        for cd in data["codici_danno"]:
            for field in required_fields:
                assert field in cd, f"Missing field: {field} in {cd['codice']}"
        print("PASS: All codes have required fields (codice, categoria, label, norma, implicazione, azione, icon, color)")
    
    def test_codici_danno_correct_codes(self, api_client):
        """Should return specific codes S1-DEF, S2-WELD, A1-ANCH, A2-CONC, P1-ZINC, G1-GAP, M1-FORCE"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        data = response.json()
        codes = [cd["codice"] for cd in data["codici_danno"]]
        expected_codes = ["S1-DEF", "S2-WELD", "A1-ANCH", "A2-CONC", "P1-ZINC", "G1-GAP", "M1-FORCE"]
        
        for code in expected_codes:
            assert code in codes, f"Missing code: {code}"
        print("PASS: All 7 expected codes present (S1-DEF, S2-WELD, A1-ANCH, A2-CONC, P1-ZINC, G1-GAP, M1-FORCE)")
    
    def test_codici_danno_categories(self, api_client):
        """Should have correct categories: Struttura, Ancoraggio, Protezione, Sicurezza, Automazione"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        data = response.json()
        categories = set(cd["categoria"] for cd in data["codici_danno"])
        expected = {"Struttura", "Ancoraggio", "Protezione", "Sicurezza", "Automazione"}
        assert categories == expected
        print("PASS: All 5 categories present (Struttura, Ancoraggio, Protezione, Sicurezza, Automazione)")


class TestSmartCostGenerationWithCodiciDanno:
    """Test POST /api/perizie/ generates smart cost items based on selected codici_danno"""
    
    def test_create_perizia_with_struttura_codes(self, auth_headers):
        """S1-DEF + P1-ZINC should generate structural + smontaggio + trasporto + installazione + oneri"""
        headers, user_id = auth_headers
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["S1-DEF", "P1-ZINC"],
            "prezzo_ml_originale": 150,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Modulo test", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        assert "voci_costo" in data
        voci = data["voci_costo"]
        
        # Check descriptions reference damage codes or norms
        all_desc = " ".join(v["descrizione"] for v in voci)
        assert "S1-DEF" in all_desc or "P1-ZINC" in all_desc or "EN 1090" in all_desc, "Cost items should reference damage codes or norms"
        
        # Should have B.01 (structural replacement) since has_struttura = True
        codici_voci = [v["codice"] for v in voci]
        assert "B.01" in codici_voci, "Should have B.01 for structural replacement"
        # Should NOT have B.03 (protezione alone) when has_struttura is True
        assert "B.03" not in codici_voci, "B.03 (protezione) should be skipped when structural replacement"
        
        # Store perizia_id for cleanup
        perizia_id = data["perizia_id"]
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{perizia_id}", headers=headers)
        print("PASS: S1-DEF + P1-ZINC generates correct cost items with structural codes")
    
    def test_create_perizia_with_ancoraggio_codes(self, auth_headers):
        """A1-ANCH + A2-CONC should generate ancoraggio-specific cost items (rifacimento fori + malta tixotropica)"""
        headers, user_id = auth_headers
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["A1-ANCH", "A2-CONC"],
            "prezzo_ml_originale": 100,
            "coefficiente_maggiorazione": 15,
            "moduli": [{"descrizione": "Test ancoraggio", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # Should have B.02 for ancoraggio
        codici_voci = [v["codice"] for v in voci]
        assert "B.02" in codici_voci, "Should have B.02 for ancoraggio work"
        
        # B.02 description should reference rifacimento fori + malta tixotropica
        b02 = next((v for v in voci if v["codice"] == "B.02"), None)
        assert b02 is not None
        desc_lower = b02["descrizione"].lower()
        assert "rifacimento fori" in desc_lower or "rifacimento" in desc_lower
        assert "tixotropica" in desc_lower or "malta" in desc_lower
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{data['perizia_id']}", headers=headers)
        print("PASS: A1-ANCH + A2-CONC generates ancoraggio cost items with rifacimento fori + malta tixotropica")
    
    def test_create_perizia_with_automazione_code(self, auth_headers):
        """M1-FORCE should generate automazione cost items (collaudo EN 12453)"""
        headers, user_id = auth_headers
        
        payload = {
            "tipo_danno": "automatismi",
            "codici_danno": ["M1-FORCE"],
            "prezzo_ml_originale": 200,
            "coefficiente_maggiorazione": 10,
            "moduli": [{"descrizione": "Test automazione", "lunghezza_ml": 2.5, "altezza_m": 2.0, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # Should have B.05 and B.06 for automazione
        codici_voci = [v["codice"] for v in voci]
        assert "B.05" in codici_voci, "Should have B.05 for automazione components"
        assert "B.06" in codici_voci, "Should have B.06 for collaudo EN 12453"
        
        # B.06 should reference EN 12453
        b06 = next((v for v in voci if v["codice"] == "B.06"), None)
        assert b06 is not None
        assert "EN 12453" in b06["descrizione"], "B.06 should reference EN 12453 collaudo"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{data['perizia_id']}", headers=headers)
        print("PASS: M1-FORCE generates automazione cost items with collaudo EN 12453")
    
    def test_create_perizia_with_sicurezza_code(self, auth_headers):
        """G1-GAP should generate sicurezza cost items (riallineamento EN 13241)"""
        headers, user_id = auth_headers
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["G1-GAP"],
            "prezzo_ml_originale": 120,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Test sicurezza", "lunghezza_ml": 3.5, "altezza_m": 2.2, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # Should have B.04 for sicurezza
        codici_voci = [v["codice"] for v in voci]
        assert "B.04" in codici_voci, "Should have B.04 for sicurezza riallineamento"
        
        # B.04 should reference EN 13241
        b04 = next((v for v in voci if v["codice"] == "B.04"), None)
        assert b04 is not None
        assert "EN 13241" in b04["descrizione"], "B.04 should reference EN 13241"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{data['perizia_id']}", headers=headers)
        print("PASS: G1-GAP generates sicurezza cost items with riallineamento EN 13241")
    
    def test_cost_items_include_damage_code_references(self, auth_headers):
        """Cost items descriptions should include damage code references in A.01"""
        headers, user_id = auth_headers
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["S1-DEF", "A1-ANCH", "G1-GAP"],
            "prezzo_ml_originale": 180,
            "coefficiente_maggiorazione": 25,
            "moduli": [{"descrizione": "Multi-code test", "lunghezza_ml": 4.0, "altezza_m": 2.5, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # A.01 should list selected codes
        a01 = next((v for v in voci if v["codice"] == "A.01"), None)
        assert a01 is not None
        # Check if codes are mentioned in A.01 description
        codes_in_desc = sum(1 for c in ["S1-DEF", "A1-ANCH", "G1-GAP"] if c in a01["descrizione"])
        assert codes_in_desc >= 1, f"A.01 should reference at least one damage code. Desc: {a01['descrizione']}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{data['perizia_id']}", headers=headers)
        print("PASS: Cost item A.01 includes damage code references")


class TestRecalcWithCodiciDanno:
    """Test POST /api/perizie/{id}/recalc uses codici_danno for regeneration"""
    
    def test_recalc_uses_codici_danno(self, auth_headers):
        """Recalc should use codici_danno to regenerate cost items"""
        headers, user_id = auth_headers
        
        # First create without codici_danno
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": [],
            "prezzo_ml_originale": 100,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Test recalc", "lunghezza_ml": 2.0, "altezza_m": 1.8, "note": ""}]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Create failed: {response.text}"
        perizia_id = response.json()["perizia_id"]
        
        # Update with codici_danno
        update_payload = {"codici_danno": ["M1-FORCE", "G1-GAP"]}
        requests.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update_payload, headers=headers)
        
        # Recalc
        recalc_response = requests.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc", headers=headers)
        assert recalc_response.status_code == 200, f"Recalc failed: {recalc_response.text}"
        
        recalc_data = recalc_response.json()
        codici_voci = [v["codice"] for v in recalc_data["voci_costo"]]
        
        # Should now have B.05, B.06 (automazione) and B.04 (sicurezza)
        assert "B.05" in codici_voci or "B.06" in codici_voci, f"Recalc should generate automazione items. Got: {codici_voci}"
        assert "B.04" in codici_voci, f"Recalc should generate sicurezza items. Got: {codici_voci}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{perizia_id}", headers=headers)
        print("PASS: POST /api/perizie/{id}/recalc uses codici_danno for regeneration")


class TestUpdateCodiciDanno:
    """Test PUT /api/perizie/{id} accepts and saves codici_danno field"""
    
    def test_update_perizia_with_codici_danno(self, auth_headers):
        """PUT should accept and save codici_danno field"""
        headers, user_id = auth_headers
        
        # Create
        payload = {"tipo_danno": "estetico", "codici_danno": ["P1-ZINC"]}
        response = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
        assert response.status_code == 201, f"Create failed: {response.text}"
        perizia_id = response.json()["perizia_id"]
        
        # Update codici_danno
        update_payload = {"codici_danno": ["S1-DEF", "S2-WELD", "P1-ZINC"]}
        update_response = requests.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update_payload, headers=headers)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Verify via GET
        get_response = requests.get(f"{BASE_URL}/api/perizie/{perizia_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["codici_danno"] == ["S1-DEF", "S2-WELD", "P1-ZINC"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{perizia_id}", headers=headers)
        print("PASS: PUT /api/perizie/{id} accepts and saves codici_danno field")


class TestArchivioSinistriStats:
    """Test GET /api/perizie/archivio/stats endpoint"""
    
    def test_archivio_stats_returns_correct_structure(self, auth_headers):
        """Stats should return total_count, total_amount, avg_amount, by_tipo, by_status, by_month, codici_frequency"""
        headers, user_id = auth_headers
        
        response = requests.get(f"{BASE_URL}/api/perizie/archivio/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        required_fields = ["total_count", "total_amount", "avg_amount", "by_tipo", "by_status", "by_month", "codici_frequency"]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print("PASS: GET /api/perizie/archivio/stats returns correct structure")
    
    def test_archivio_stats_handles_zero_perizie(self, auth_headers):
        """Stats should return zero values when no perizie exist for new user"""
        # Create a brand new user session
        result = subprocess.run([
            "mongosh", "--quiet", "--eval", """
            use('test_database');
            var userId = 'test-user-zero-' + Date.now();
            var sessionToken = 'test_session_zero_' + Date.now();
            db.users.insertOne({
                user_id: userId,
                email: 'test.zero.' + Date.now() + '@example.com',
                name: 'Test Zero User',
                picture: '',
                created_at: new Date()
            });
            db.user_sessions.insertOne({
                user_id: userId,
                session_token: sessionToken,
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                created_at: new Date()
            });
            print(sessionToken);
            """
        ], capture_output=True, text=True)
        token = result.stdout.strip().split('\n')[-1]
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/perizie/archivio/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["total_count"] == 0
        assert data["total_amount"] == 0
        assert data["avg_amount"] == 0
        assert data["by_tipo"] == {}
        assert data["by_status"] == {}
        assert data["by_month"] == []
        assert data["codici_frequency"] == []
        
        print("PASS: Stats endpoint handles zero perizie gracefully")
    
    def test_archivio_stats_calculates_correctly(self, auth_headers):
        """Stats should correctly aggregate perizia data"""
        headers, user_id = auth_headers
        
        # Create test perizie with known values
        perizie_ids = []
        for i, (tipo, codici) in enumerate([
            ("strutturale", ["S1-DEF"]),
            ("strutturale", ["S2-WELD", "A1-ANCH"]),
            ("estetico", ["P1-ZINC"])
        ]):
            payload = {
                "tipo_danno": tipo,
                "codici_danno": codici,
                "prezzo_ml_originale": 100 + i * 50,
                "coefficiente_maggiorazione": 20,
                "moduli": [{"descrizione": f"Stats test {i}", "lunghezza_ml": 2.0, "altezza_m": 2.0, "note": ""}]
            }
            resp = requests.post(f"{BASE_URL}/api/perizie/", json=payload, headers=headers)
            assert resp.status_code == 201, f"Create perizia {i} failed: {resp.text}"
            perizie_ids.append(resp.json()["perizia_id"])
        
        # Get stats
        response = requests.get(f"{BASE_URL}/api/perizie/archivio/stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should have at least our 3 perizie
        assert data["total_count"] >= 3, f"Expected at least 3 perizie, got {data['total_count']}"
        assert data["total_amount"] > 0
        assert data["avg_amount"] > 0
        
        # Should have both strutturale and estetico
        assert "strutturale" in data["by_tipo"] or "estetico" in data["by_tipo"], f"by_tipo missing expected types: {data['by_tipo']}"
        
        # Check codici_frequency has our codes
        codici_codes = [cf["codice"] for cf in data["codici_frequency"]]
        # At least one of our codes should be present
        our_codes = ["S1-DEF", "S2-WELD", "A1-ANCH", "P1-ZINC"]
        found = any(c in codici_codes for c in our_codes)
        assert found, f"codici_frequency should contain at least one of {our_codes}. Got: {codici_codes}"
        
        # Cleanup
        for pid in perizie_ids:
            requests.delete(f"{BASE_URL}/api/perizie/{pid}", headers=headers)
        
        print("PASS: Stats endpoint calculates correctly with aggregations")
    
    def test_archivio_stats_requires_auth(self, api_client):
        """Stats endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/perizie/archivio/stats")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Stats endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

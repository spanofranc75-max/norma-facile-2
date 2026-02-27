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
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Create a test session for authenticated requests
TEST_SESSION_ID = f"test_codici_danno_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def api_client():
    """Unauthenticated requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_client():
    """Authenticated requests session with test session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_SESSION_ID}"
    })
    
    # Seed test session in MongoDB
    import pymongo
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    
    user_id = f"user_codici_danno_{uuid.uuid4().hex[:8]}"
    db.sessions.insert_one({
        "session_id": TEST_SESSION_ID,
        "user_id": user_id,
        "email": "test_codici@example.com",
        "name": "Test Codici Danno User",
        "picture": "",
        "created_at": datetime.utcnow(),
        "expires_at": datetime(2030, 1, 1)
    })
    
    yield session, user_id, db
    
    # Cleanup
    db.sessions.delete_one({"session_id": TEST_SESSION_ID})
    db.perizie.delete_many({"user_id": user_id})
    client.close()


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
    
    def test_create_perizia_with_struttura_codes(self, auth_client):
        """S1-DEF + P1-ZINC should generate structural + smontaggio + trasporto + installazione + oneri"""
        session, user_id, db = auth_client
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["S1-DEF", "P1-ZINC"],
            "prezzo_ml_originale": 150,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Modulo test", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        assert "voci_costo" in data
        voci = data["voci_costo"]
        
        # Check descriptions reference damage codes
        all_desc = " ".join(v["descrizione"] for v in voci)
        assert "S1-DEF" in all_desc or "P1-ZINC" in all_desc or "EN 1090" in all_desc, "Cost items should reference damage codes or norms"
        
        # Should have B.01 (structural replacement) since has_struttura = True
        codici_voci = [v["codice"] for v in voci]
        assert "B.01" in codici_voci, "Should have B.01 for structural replacement"
        # Should NOT have B.03 (protezione alone) when has_struttura is True
        assert "B.03" not in codici_voci, "B.03 (protezione) should be skipped when structural replacement"
        
        # Cleanup
        db.perizie.delete_one({"perizia_id": data["perizia_id"]})
        print("PASS: S1-DEF + P1-ZINC generates correct cost items with structural codes")
    
    def test_create_perizia_with_ancoraggio_codes(self, auth_client):
        """A1-ANCH + A2-CONC should generate ancoraggio-specific cost items (rifacimento fori + malta tixotropica)"""
        session, user_id, db = auth_client
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["A1-ANCH", "A2-CONC"],
            "prezzo_ml_originale": 100,
            "coefficiente_maggiorazione": 15,
            "moduli": [{"descrizione": "Test ancoraggio", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # Should have B.02 for ancoraggio
        codici_voci = [v["codice"] for v in voci]
        assert "B.02" in codici_voci, "Should have B.02 for ancoraggio work"
        
        # B.02 description should reference rifacimento fori + malta tixotropica
        b02 = next((v for v in voci if v["codice"] == "B.02"), None)
        assert b02 is not None
        assert "Rifacimento fori" in b02["descrizione"] or "rifacimento fori" in b02["descrizione"].lower()
        assert "malta tixotropica" in b02["descrizione"].lower() or "tixotropica" in b02["descrizione"]
        
        # Cleanup
        db.perizie.delete_one({"perizia_id": data["perizia_id"]})
        print("PASS: A1-ANCH + A2-CONC generates ancoraggio cost items with rifacimento fori + malta tixotropica")
    
    def test_create_perizia_with_automazione_code(self, auth_client):
        """M1-FORCE should generate automazione cost items (collaudo EN 12453)"""
        session, user_id, db = auth_client
        
        payload = {
            "tipo_danno": "automatismi",
            "codici_danno": ["M1-FORCE"],
            "prezzo_ml_originale": 200,
            "coefficiente_maggiorazione": 10,
            "moduli": [{"descrizione": "Test automazione", "lunghezza_ml": 2.5, "altezza_m": 2.0, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
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
        db.perizie.delete_one({"perizia_id": data["perizia_id"]})
        print("PASS: M1-FORCE generates automazione cost items with collaudo EN 12453")
    
    def test_create_perizia_with_sicurezza_code(self, auth_client):
        """G1-GAP should generate sicurezza cost items (riallineamento EN 13241)"""
        session, user_id, db = auth_client
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["G1-GAP"],
            "prezzo_ml_originale": 120,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Test sicurezza", "lunghezza_ml": 3.5, "altezza_m": 2.2, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
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
        db.perizie.delete_one({"perizia_id": data["perizia_id"]})
        print("PASS: G1-GAP generates sicurezza cost items with riallineamento EN 13241")
    
    def test_cost_items_include_damage_code_references(self, auth_client):
        """Cost items descriptions should include damage code references"""
        session, user_id, db = auth_client
        
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": ["S1-DEF", "A1-ANCH", "G1-GAP"],
            "prezzo_ml_originale": 180,
            "coefficiente_maggiorazione": 25,
            "moduli": [{"descrizione": "Multi-code test", "lunghezza_ml": 4.0, "altezza_m": 2.5, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        voci = data["voci_costo"]
        
        # A.01 should list selected codes
        a01 = next((v for v in voci if v["codice"] == "A.01"), None)
        assert a01 is not None
        # Check if codes are mentioned in A.01 description
        codes_in_desc = sum(1 for c in ["S1-DEF", "A1-ANCH", "G1-GAP"] if c in a01["descrizione"])
        assert codes_in_desc >= 1, "A.01 should reference at least one damage code"
        
        # Cleanup
        db.perizie.delete_one({"perizia_id": data["perizia_id"]})
        print("PASS: Cost item descriptions include damage code references")


class TestRecalcWithCodiciDanno:
    """Test POST /api/perizie/{id}/recalc uses codici_danno for regeneration"""
    
    def test_recalc_uses_codici_danno(self, auth_client):
        """Recalc should use codici_danno to regenerate cost items"""
        session, user_id, db = auth_client
        
        # First create without codici_danno
        payload = {
            "tipo_danno": "strutturale",
            "codici_danno": [],
            "prezzo_ml_originale": 100,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Test recalc", "lunghezza_ml": 2.0, "altezza_m": 1.8, "note": ""}]
        }
        
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        perizia_id = response.json()["perizia_id"]
        
        # Update with codici_danno
        update_payload = {"codici_danno": ["M1-FORCE", "G1-GAP"]}
        session.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update_payload)
        
        # Recalc
        recalc_response = session.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc")
        assert recalc_response.status_code == 200
        
        recalc_data = recalc_response.json()
        codici_voci = [v["codice"] for v in recalc_data["voci_costo"]]
        
        # Should now have B.05, B.06 (automazione) and B.04 (sicurezza)
        assert "B.05" in codici_voci or "B.06" in codici_voci, "Recalc should generate automazione items"
        assert "B.04" in codici_voci, "Recalc should generate sicurezza items"
        
        # Cleanup
        db.perizie.delete_one({"perizia_id": perizia_id})
        print("PASS: POST /api/perizie/{id}/recalc uses codici_danno for regeneration")


class TestUpdateCodiciDanno:
    """Test PUT /api/perizie/{id} accepts and saves codici_danno field"""
    
    def test_update_perizia_with_codici_danno(self, auth_client):
        """PUT should accept and save codici_danno field"""
        session, user_id, db = auth_client
        
        # Create
        payload = {"tipo_danno": "estetico", "codici_danno": ["P1-ZINC"]}
        response = session.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        perizia_id = response.json()["perizia_id"]
        
        # Update codici_danno
        update_payload = {"codici_danno": ["S1-DEF", "S2-WELD", "P1-ZINC"]}
        update_response = session.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update_payload)
        assert update_response.status_code == 200
        
        # Verify via GET
        get_response = session.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["codici_danno"] == ["S1-DEF", "S2-WELD", "P1-ZINC"]
        
        # Cleanup
        db.perizie.delete_one({"perizia_id": perizia_id})
        print("PASS: PUT /api/perizie/{id} accepts and saves codici_danno field")


class TestArchivioSinistriStats:
    """Test GET /api/perizie/archivio/stats endpoint"""
    
    def test_archivio_stats_returns_correct_structure(self, auth_client):
        """Stats should return total_count, total_amount, avg_amount, by_tipo, by_status, by_month, codici_frequency"""
        session, user_id, db = auth_client
        
        response = session.get(f"{BASE_URL}/api/perizie/archivio/stats")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["total_count", "total_amount", "avg_amount", "by_tipo", "by_status", "by_month", "codici_frequency"]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print("PASS: GET /api/perizie/archivio/stats returns correct structure")
    
    def test_archivio_stats_handles_zero_perizie(self, auth_client):
        """Stats should return zero values when no perizie exist"""
        session, user_id, db = auth_client
        
        # Clean up any existing perizie for this user
        db.perizie.delete_many({"user_id": user_id})
        
        response = session.get(f"{BASE_URL}/api/perizie/archivio/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 0
        assert data["total_amount"] == 0
        assert data["avg_amount"] == 0
        assert data["by_tipo"] == {}
        assert data["by_status"] == {}
        assert data["by_month"] == []
        assert data["codici_frequency"] == []
        
        print("PASS: Stats endpoint handles zero perizie gracefully")
    
    def test_archivio_stats_calculates_correctly(self, auth_client):
        """Stats should correctly aggregate perizia data"""
        session, user_id, db = auth_client
        
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
            resp = session.post(f"{BASE_URL}/api/perizie/", json=payload)
            assert resp.status_code == 201
            perizie_ids.append(resp.json()["perizia_id"])
        
        # Get stats
        response = session.get(f"{BASE_URL}/api/perizie/archivio/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 3
        assert data["total_amount"] > 0
        assert data["avg_amount"] > 0
        assert "strutturale" in data["by_tipo"]
        assert "estetico" in data["by_tipo"]
        assert data["by_tipo"]["strutturale"]["count"] == 2
        assert data["by_tipo"]["estetico"]["count"] == 1
        
        # Check codici_frequency
        codici_counts = {cf["codice"]: cf["count"] for cf in data["codici_frequency"]}
        assert codici_counts.get("S1-DEF", 0) >= 1
        assert codici_counts.get("S2-WELD", 0) >= 1
        assert codici_counts.get("A1-ANCH", 0) >= 1
        assert codici_counts.get("P1-ZINC", 0) >= 1
        
        # Cleanup
        for pid in perizie_ids:
            db.perizie.delete_one({"perizia_id": pid})
        
        print("PASS: Stats endpoint calculates correctly with aggregations")
    
    def test_archivio_stats_requires_auth(self, api_client):
        """Stats endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/perizie/archivio/stats")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Stats endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

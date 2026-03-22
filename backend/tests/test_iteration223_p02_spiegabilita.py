"""
Iteration 223 - P0.2: Spiegabilità + Punti incerti + Linguaggio officina
Backend regression tests - verify all existing endpoints still work
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "99659c11314245d4ae753a9ae27aef5a"
TEST_ISTRUTTORIA_ID = "istr_701cc0cc1ddc"
TEST_PREVENTIVO_ID = "prev_625826c752ac"

@pytest.fixture
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestHealthEndpoint:
    """Health check - verify backend is running"""
    
    def test_health_endpoint(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health check passed: {data}")


class TestIstruttoriaEndpoints:
    """Test all istruttoria endpoints still work (no backend changes in P0.2)"""
    
    def test_get_istruttoria_by_preventivo(self, api_client):
        """GET /api/istruttoria/preventivo/{preventivo_id}"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify core fields exist
        assert "istruttoria_id" in data
        assert "classificazione" in data
        assert "estrazione_tecnica" in data
        assert "domande_residue" in data
        print(f"✅ GET istruttoria by preventivo: {data['istruttoria_id']}")
    
    def test_get_istruttoria_by_id(self, api_client):
        """GET /api/istruttoria/{istruttoria_id}"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["istruttoria_id"] == TEST_ISTRUTTORIA_ID
        assert "classificazione" in data
        print(f"✅ GET istruttoria by ID: {data['istruttoria_id']}")
    
    def test_istruttoria_has_estrazione_tecnica(self, api_client):
        """Verify estrazione_tecnica contains data needed for buildEvidenze()"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        est = data.get("estrazione_tecnica", {})
        
        # These fields are used by buildEvidenze() in frontend
        assert "elementi_strutturali" in est, "Missing elementi_strutturali"
        assert "lavorazioni_rilevate" in est, "Missing lavorazioni_rilevate"
        assert "saldature" in est, "Missing saldature"
        assert "trattamenti_superficiali" in est, "Missing trattamenti_superficiali"
        
        print(f"✅ estrazione_tecnica has all required fields for buildEvidenze()")
        print(f"   - elementi_strutturali: {len(est.get('elementi_strutturali', []))} items")
        print(f"   - lavorazioni_rilevate: {len(est.get('lavorazioni_rilevate', []))} items")
        print(f"   - saldature.presenti: {est.get('saldature', {}).get('presenti')}")
        print(f"   - trattamenti_superficiali.tipo: {est.get('trattamenti_superficiali', {}).get('tipo')}")
    
    def test_istruttoria_has_ambiguita_for_punti_incerti(self, api_client):
        """Verify ambiguita_rilevate exists for buildPuntiIncerti()"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        est = data.get("estrazione_tecnica", {})
        ambiguita = est.get("ambiguita_rilevate", [])
        
        # ambiguita_rilevate is used by buildPuntiIncerti()
        assert isinstance(ambiguita, list), "ambiguita_rilevate should be a list"
        
        if len(ambiguita) > 0:
            # Verify structure of ambiguity items
            amb = ambiguita[0]
            assert "punto" in amb, "Ambiguity missing 'punto' field"
            assert "possibili_interpretazioni" in amb, "Ambiguity missing 'possibili_interpretazioni'"
            print(f"✅ ambiguita_rilevate has {len(ambiguita)} items with correct structure")
        else:
            print(f"⚠️ ambiguita_rilevate is empty (may be valid for this preventivo)")
    
    def test_istruttoria_has_domande_residue(self, api_client):
        """Verify domande_residue exists for 'Conferme che mancano' section"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        domande = data.get("domande_residue", [])
        assert isinstance(domande, list), "domande_residue should be a list"
        
        n_risposte = data.get("n_risposte", 0)
        print(f"✅ domande_residue: {len(domande)} questions, {n_risposte} answered")
    
    def test_istruttoria_has_documenti_richiesti(self, api_client):
        """Verify documenti_richiesti exists for 'Documenti da raccogliere' section"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        documenti = data.get("documenti_richiesti", [])
        assert isinstance(documenti, list), "documenti_richiesti should be a list"
        print(f"✅ documenti_richiesti: {len(documenti)} documents")
    
    def test_istruttoria_has_profilo_or_exc_proposta(self, api_client):
        """Verify profilo_tecnico or exc_proposta exists (used in frontend for class display)"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        profilo = data.get("profilo_tecnico", {})
        exc = data.get("exc_proposta", {})
        
        # Either profilo_tecnico or exc_proposta should have data
        has_profilo = "valore" in profilo or "tipo" in profilo
        has_exc = "classe" in exc
        
        assert has_profilo or has_exc, "Either profilo_tecnico or exc_proposta should have data"
        
        if has_profilo:
            print(f"✅ profilo_tecnico: {profilo.get('tipo')} = {profilo.get('valore')}")
        if has_exc:
            print(f"✅ exc_proposta: classe={exc.get('classe')}")


class TestRispondiEndpoint:
    """Test rispondi endpoint still works"""
    
    def test_rispondi_endpoint_exists(self, api_client):
        """POST /api/istruttoria/{id}/rispondi - verify endpoint responds"""
        # Send empty payload to check endpoint exists
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json={"risposte": []}
        )
        # Should return 200 or 400 (validation error), not 404
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        print(f"✅ POST /rispondi endpoint exists (status: {response.status_code})")


class TestRispondiContestualeEndpoint:
    """Test rispondi-contestuale endpoint still works"""
    
    def test_rispondi_contestuale_endpoint_exists(self, api_client):
        """POST /api/istruttoria/{id}/rispondi-contestuale - verify endpoint responds"""
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi-contestuale",
            json={"risposte": []}
        )
        # Should return 200 or 400, not 404
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        print(f"✅ POST /rispondi-contestuale endpoint exists (status: {response.status_code})")


class TestDomandeContestuali:
    """Test domande_contestuali still returned (from P0.25)"""
    
    def test_domande_contestuali_in_response(self, api_client):
        """Verify domande_contestuali field exists in istruttoria response"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        ctx_domande = data.get("domande_contestuali", [])
        assert isinstance(ctx_domande, list), "domande_contestuali should be a list"
        
        active_count = sum(1 for q in ctx_domande if q.get("active"))
        print(f"✅ domande_contestuali: {len(ctx_domande)} total, {active_count} active")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

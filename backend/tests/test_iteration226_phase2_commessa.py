"""
Iteration 226 — Phase 2 Commessa Pre-Istruita Testing
======================================================
Tests for Phase 2 feature: Generate 'Commessa Pre-Istruita Revisionata' from confirmed istruttoria.

Eligibility checks:
- istruttoria_confermata
- classificazione_pura (EN_1090, EN_13241, GENERICA)
- confidenza_alta
- segmentazione_ok
- domande_alto_risposte
- nessun_blocco
- campi_critici

Test preventivi:
- prev_625826c752ac: Tunnel, EN_1090, confermata (eligible, commessa already generated)
- prev_4db2a68b44: Scale, non confermata (not eligible)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session tokens from credentials
MAIN_USER_SESSION = "session_main_validazione_2026"
TEST_USER_SESSION = "test_perizia_205a45704b22"

# Test preventivi
CONFERMATA_PREVENTIVO = "prev_625826c752ac"  # Tunnel, EN_1090, confermata
NON_CONFERMATA_PREVENTIVO = "prev_4db2a68b44"  # Scale, non confermata


@pytest.fixture
def main_user_client():
    """Session with main user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MAIN_USER_SESSION}"
    })
    return session


@pytest.fixture
def test_user_client():
    """Session with test user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_USER_SESSION}"
    })
    return session


class TestPhase2Eligibility:
    """Test Phase 2 eligibility endpoint"""

    def test_eligibility_confermata_returns_allowed_true(self, main_user_client):
        """GET /api/istruttoria/phase2/eligibility/{preventivo_id} returns allowed=true for confermata case"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/eligibility/{CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Eligibility response for confermata: {data}")
        
        # Verify structure
        assert "allowed" in data, "Response should have 'allowed' field"
        assert "checks" in data, "Response should have 'checks' field"
        assert "reasons" in data, "Response should have 'reasons' field"
        
        # For confermata case, should be allowed
        assert data["allowed"] is True, f"Expected allowed=True for confermata preventivo, got {data['allowed']}. Reasons: {data.get('reasons', [])}"
        
        # Verify checks structure
        checks = data["checks"]
        assert "istruttoria_confermata" in checks
        assert "classificazione_pura" in checks
        assert "confidenza_alta" in checks
        assert "segmentazione_ok" in checks
        assert "domande_alto_risposte" in checks
        assert "nessun_blocco" in checks
        assert "campi_critici" in checks
        
        # All checks should pass for eligible case
        assert checks["istruttoria_confermata"] is True
        assert checks["classificazione_pura"] is True
        assert checks["confidenza_alta"] is True

    def test_eligibility_non_confermata_returns_allowed_false(self, main_user_client):
        """GET /api/istruttoria/phase2/eligibility/{preventivo_id} returns allowed=false for non-confermata case"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/eligibility/{NON_CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Eligibility response for non-confermata: {data}")
        
        # Verify structure
        assert "allowed" in data
        assert "checks" in data
        assert "reasons" in data
        
        # For non-confermata case, should NOT be allowed
        assert data["allowed"] is False, f"Expected allowed=False for non-confermata preventivo, got {data['allowed']}"
        
        # Should have at least one reason
        assert len(data["reasons"]) > 0, "Should have at least one blocking reason"
        
        # Check that istruttoria_confermata is False
        checks = data["checks"]
        assert checks["istruttoria_confermata"] is False, "istruttoria_confermata check should be False"

    def test_eligibility_returns_reasons_list(self, main_user_client):
        """Eligibility endpoint returns list of blocking reasons when not allowed"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/eligibility/{NON_CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Reasons should be a list of strings
        assert isinstance(data["reasons"], list)
        if not data["allowed"]:
            assert len(data["reasons"]) > 0
            for reason in data["reasons"]:
                assert isinstance(reason, str)
                print(f"Blocking reason: {reason}")


class TestPhase2GeneraCommessa:
    """Test Phase 2 commessa generation endpoint"""

    def test_genera_returns_409_when_not_eligible(self, main_user_client):
        """POST /api/istruttoria/phase2/genera/{preventivo_id} returns 409 when not eligible"""
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/phase2/genera/{NON_CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 409, f"Expected 409 Conflict, got {response.status_code}: {response.text}"
        
        # Response should contain error details
        data = response.json()
        print(f"409 response: {data}")
        
        # Should have detail with reasons
        assert "detail" in data or "message" in data or "reasons" in data

    def test_genera_success_for_eligible_preventivo(self, main_user_client):
        """POST /api/istruttoria/phase2/genera/{preventivo_id} generates commessa for eligible case"""
        # First check eligibility
        elig_response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/eligibility/{CONFERMATA_PREVENTIVO}")
        assert elig_response.status_code == 200
        elig_data = elig_response.json()
        
        if not elig_data["allowed"]:
            pytest.skip(f"Preventivo not eligible: {elig_data['reasons']}")
        
        # Generate commessa
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/phase2/genera/{CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Generated commessa response: {data}")
        
        # Verify response structure
        assert "commessa" in data, "Response should have 'commessa' field"
        commessa = data["commessa"]
        
        # Verify commessa structure
        assert "commessa_id" in commessa
        assert "status" in commessa
        assert "normativa" in commessa
        assert "voci_lavoro" in commessa
        assert "controlli" in commessa
        assert "documenti" in commessa
        assert "materiali" in commessa
        assert "rami_attivi" in commessa
        assert "etichette" in commessa
        
        # Verify etichette structure
        etichette = commessa["etichette"]
        assert "precompilato" in etichette
        assert "da_completare" in etichette
        assert "non_emettibile" in etichette
        
        print(f"Commessa ID: {commessa['commessa_id']}")
        print(f"Normativa: {commessa['normativa']}")
        print(f"Voci lavoro: {len(commessa['voci_lavoro'])}")
        print(f"Controlli: {len(commessa['controlli'])}")
        print(f"Documenti: {len(commessa['documenti'])}")


class TestPhase2GetCommessa:
    """Test Phase 2 get commessa endpoint"""

    def test_get_commessa_returns_generated_commessa(self, main_user_client):
        """GET /api/istruttoria/phase2/commessa/{preventivo_id} retrieves generated commessa"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/commessa/{CONFERMATA_PREVENTIVO}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Get commessa response: {data}")
        
        # Verify response structure
        assert "commessa" in data
        commessa = data["commessa"]
        
        # Verify commessa fields
        assert "commessa_id" in commessa
        assert "preventivo_id" in commessa
        assert commessa["preventivo_id"] == CONFERMATA_PREVENTIVO
        
        # Verify key fields
        assert "voci_lavoro" in commessa
        assert "controlli" in commessa
        assert "documenti" in commessa
        assert "rami_attivi" in commessa
        assert "etichette" in commessa

    def test_get_commessa_returns_404_when_not_generated(self, main_user_client):
        """GET /api/istruttoria/phase2/commessa/{preventivo_id} returns 404 when no commessa exists"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/commessa/{NON_CONFERMATA_PREVENTIVO}")
        
        # Should return 404 since commessa was never generated for non-confermata
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


class TestPhase2CommessaContent:
    """Test Phase 2 commessa content structure"""

    def test_commessa_has_voci_lavoro_with_correct_structure(self, main_user_client):
        """Commessa voci_lavoro have correct structure"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/commessa/{CONFERMATA_PREVENTIVO}")
        
        if response.status_code == 404:
            pytest.skip("Commessa not yet generated")
        
        assert response.status_code == 200
        commessa = response.json()["commessa"]
        
        voci = commessa.get("voci_lavoro", [])
        if len(voci) > 0:
            voce = voci[0]
            # Check expected fields
            assert "descrizione" in voce
            assert "stato" in voce
            assert "fonte" in voce
            print(f"Sample voce: {voce}")

    def test_commessa_has_rami_attivi_structure(self, main_user_client):
        """Commessa rami_attivi have correct structure"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/commessa/{CONFERMATA_PREVENTIVO}")
        
        if response.status_code == 404:
            pytest.skip("Commessa not yet generated")
        
        assert response.status_code == 200
        commessa = response.json()["commessa"]
        
        rami = commessa.get("rami_attivi", {})
        
        # Should have saldatura, zincatura, montaggio branches
        assert "saldatura" in rami
        assert "zincatura" in rami
        assert "montaggio" in rami
        
        # Each branch should have attivo and stato
        for branch_name, branch in rami.items():
            assert "attivo" in branch, f"Branch {branch_name} missing 'attivo'"
            assert "stato" in branch, f"Branch {branch_name} missing 'stato'"
            print(f"Branch {branch_name}: attivo={branch['attivo']}, stato={branch['stato']}")

    def test_commessa_etichette_counts(self, main_user_client):
        """Commessa etichette have precompilato, da_completare, non_emettibile counts"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/phase2/commessa/{CONFERMATA_PREVENTIVO}")
        
        if response.status_code == 404:
            pytest.skip("Commessa not yet generated")
        
        assert response.status_code == 200
        commessa = response.json()["commessa"]
        
        etichette = commessa.get("etichette", {})
        
        assert "precompilato" in etichette
        assert "da_completare" in etichette
        assert "non_emettibile" in etichette
        
        # precompilato and da_completare should be integers
        assert isinstance(etichette["precompilato"], int)
        assert isinstance(etichette["da_completare"], int)
        
        # non_emettibile should be a list
        assert isinstance(etichette["non_emettibile"], list)
        
        print(f"Etichette: precompilato={etichette['precompilato']}, da_completare={etichette['da_completare']}, non_emettibile={etichette['non_emettibile']}")


class TestValidationScoring:
    """Test validation engine scoring improvements"""

    def test_validation_aggregate_score(self, test_user_client):
        """Validation aggregate score should be around 91% global"""
        response = test_user_client.get(f"{BASE_URL}/api/validation/aggregate")
        
        if response.status_code == 404:
            pytest.skip("Validation aggregate endpoint not available")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Validation aggregate: {data}")
        
        # Check for aggregate score
        if "punteggio_medio_globale" in data:
            score = data["punteggio_medio_globale"]
            print(f"Global score: {score}")
            # Score should be improved (around 0.91 or 91%)
            assert score >= 0.80, f"Expected score >= 0.80, got {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

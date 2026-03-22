"""
Iteration 227 — Commesse Normative (Rami Normativi + Emissioni Documentali) Tests
==================================================================================
Tests for the hierarchical model: Commessa Madre → Ramo Normativo → Emissione Documentale

Features tested:
- GET /api/commesse-normative/{commessa_id} — list branches (includes legacy wrap if no real branch)
- POST /api/commesse-normative/{commessa_id} — create manual branch (idempotent)
- POST /api/commesse-normative/{commessa_id} with invalid normativa → 400
- GET /api/commesse-normative/{commessa_id}/{ramo_id} — branch detail with emissions
- POST /api/emissioni/{ramo_id} — create new emission with progressive numbering (D01, D02)
- GET /api/emissioni/{ramo_id}/{emissione_id}/gate — Evidence Gate check for EN 1090
- POST /api/emissioni/{ramo_id}/{emissione_id}/emetti — block emission if gate NOT OK (409)
- PATCH /api/emissioni/{ramo_id}/{emissione_id} — update emission fields
- GET /api/commesse/{commessa_id}/gerarchia — aggregated view with branches and nested emissions
- POST /api/commesse-normative/{commessa_id}/materializza-legacy — convert legacy to real branch
- Unique index: cannot create 2 branches with same normativa for same commessa
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "test_session_rami_normativi_227"
COMMESSA_ID = "com_e8c4810ad476"  # Existing commessa: NF-2026-000001, EN_13241

# Module-level storage for test data
_test_data = {
    "created_ramo_id": None,
    "created_emissione_id": None,
    "generica_ramo_id": None,
}


@pytest.fixture(scope="module")
def api_session():
    """Create a session for all tests in this module"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCommesseNormativeAPI:
    """Tests for Rami Normativi (Normative Branches) API"""

    # ─── RAMI NORMATIVI TESTS ────────────────────────────────────────────────

    def test_01_list_rami_empty_returns_legacy_wrap(self, api_session):
        """GET /api/commesse-normative/{commessa_id} — returns legacy wrap when no real branches"""
        response = api_session.get(f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rami" in data
        assert "total" in data
        
        # Should have legacy wrap since no real branches exist yet
        if data["total"] > 0:
            ramo = data["rami"][0]
            # Legacy wrap has is_virtual=True or ramo_id=None
            if ramo.get("is_virtual") or ramo.get("ramo_id") is None:
                assert ramo["normativa"] == "EN_13241"  # Matches commessa normativa_tipo
                assert "codice_ramo" in ramo
                print(f"✓ Legacy wrap returned: {ramo['codice_ramo']}")
            else:
                print(f"✓ Real branch exists: {ramo['ramo_id']}")

    def test_02_create_ramo_manual_success(self, api_session):
        """POST /api/commesse-normative/{commessa_id} — create manual branch"""
        payload = {"normativa": "EN_1090"}
        response = api_session.post(
            f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        ramo = response.json()
        assert "ramo_id" in ramo
        assert ramo["normativa"] == "EN_1090"
        assert ramo["commessa_id"] == COMMESSA_ID
        assert "codice_ramo" in ramo
        assert ramo["status"] == "active"
        assert ramo["created_from"] == "manuale"
        
        # Store for later tests
        _test_data["created_ramo_id"] = ramo["ramo_id"]
        print(f"✓ Created ramo: {ramo['ramo_id']} — {ramo['codice_ramo']}")

    def test_03_create_ramo_idempotent(self, api_session):
        """POST /api/commesse-normative/{commessa_id} — idempotent: returns existing if same normativa"""
        payload = {"normativa": "EN_1090"}
        response = api_session.post(
            f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}",
            json=payload
        )
        # Should return 201 but with the same ramo_id (idempotent)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        ramo = response.json()
        assert ramo["ramo_id"] == _test_data["created_ramo_id"]
        print(f"✓ Idempotent: returned existing ramo {ramo['ramo_id']}")

    def test_04_create_ramo_invalid_normativa_400(self, api_session):
        """POST /api/commesse-normative/{commessa_id} with invalid normativa → 400"""
        payload = {"normativa": "INVALID_NORM"}
        response = api_session.post(
            f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "EN_1090" in data["detail"] or "non valida" in data["detail"].lower()
        print(f"✓ Invalid normativa rejected: {data['detail']}")

    def test_05_list_rami_after_creation(self, api_session):
        """GET /api/commesse-normative/{commessa_id} — list includes created branch"""
        response = api_session.get(f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        
        # Find our created branch
        ramo_ids = [r["ramo_id"] for r in data["rami"] if r.get("ramo_id")]
        assert _test_data["created_ramo_id"] in ramo_ids
        print(f"✓ Listed {data['total']} rami, includes created branch")

    def test_06_get_ramo_detail(self, api_session):
        """GET /api/commesse-normative/{commessa_id}/{ramo_id} — branch detail with emissions"""
        ramo_id = _test_data["created_ramo_id"]
        assert ramo_id, "Ramo ID not set from previous test"
        
        response = api_session.get(f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}/{ramo_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        ramo = response.json()
        assert ramo["ramo_id"] == ramo_id
        assert "emissioni" in ramo
        assert "n_emissioni" in ramo
        print(f"✓ Ramo detail: {ramo['codice_ramo']}, {ramo['n_emissioni']} emissioni")

    # ─── EMISSIONI DOCUMENTALI TESTS ─────────────────────────────────────────

    def test_07_create_emissione_success(self, api_session):
        """POST /api/emissioni/{ramo_id} — create new emission with progressive numbering"""
        ramo_id = _test_data["created_ramo_id"]
        assert ramo_id, "Ramo ID not set from previous test"
        
        payload = {"descrizione": "Prima emissione test travi"}
        
        response = api_session.post(f"{BASE_URL}/api/emissioni/{ramo_id}", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        emissione = response.json()
        assert "emissione_id" in emissione
        assert emissione["ramo_id"] == ramo_id
        assert emissione["stato"] == "draft"
        assert "codice_emissione" in emissione
        # EN_1090 → DOP → D prefix
        assert "D" in emissione["codice_emissione"]
        
        _test_data["created_emissione_id"] = emissione["emissione_id"]
        print(f"✓ Created emissione: {emissione['codice_emissione']} (seq={emissione['emission_seq']})")

    def test_08_create_second_emissione_progressive(self, api_session):
        """POST /api/emissioni/{ramo_id} — second emission has seq=2"""
        ramo_id = _test_data["created_ramo_id"]
        assert ramo_id, "Ramo ID not set from previous test"
        
        payload = {"descrizione": "Seconda emissione test pilastri"}
        
        response = api_session.post(f"{BASE_URL}/api/emissioni/{ramo_id}", json=payload)
        assert response.status_code == 201
        
        emissione = response.json()
        assert emissione["emission_seq"] >= 2
        print(f"✓ Second emissione: {emissione['codice_emissione']} (seq={emissione['emission_seq']})")

    def test_09_get_emissione_detail(self, api_session):
        """GET /api/emissioni/{ramo_id}/{emissione_id} — emission detail"""
        ramo_id = _test_data["created_ramo_id"]
        emissione_id = _test_data["created_emissione_id"]
        assert ramo_id and emissione_id, "Test data not set from previous tests"
        
        response = api_session.get(f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}")
        assert response.status_code == 200
        
        emissione = response.json()
        assert emissione["emissione_id"] == emissione_id
        assert "evidence_gate" in emissione
        assert "batch_ids" in emissione
        assert "ddt_ids" in emissione
        print(f"✓ Emissione detail: {emissione['codice_emissione']}, stato={emissione['stato']}")

    def test_10_update_emissione_patch(self, api_session):
        """PATCH /api/emissioni/{ramo_id}/{emissione_id} — update emission fields"""
        ramo_id = _test_data["created_ramo_id"]
        emissione_id = _test_data["created_emissione_id"]
        assert ramo_id and emissione_id, "Test data not set from previous tests"
        
        payload = {"descrizione": "Descrizione aggiornata per test"}
        response = api_session.patch(
            f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        emissione = response.json()
        assert emissione["descrizione"] == "Descrizione aggiornata per test"
        print(f"✓ Updated emissione descrizione")

    # ─── EVIDENCE GATE TESTS ─────────────────────────────────────────────────

    def test_11_check_evidence_gate_en1090(self, api_session):
        """GET /api/emissioni/{ramo_id}/{emissione_id}/gate — Evidence Gate check for EN 1090"""
        ramo_id = _test_data["created_ramo_id"]
        emissione_id = _test_data["created_emissione_id"]
        assert ramo_id and emissione_id, "Test data not set from previous tests"
        
        response = api_session.get(f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}/gate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        gate = response.json()
        assert "emittable" in gate
        assert "checks" in gate
        assert "blocking_reasons" in gate
        
        # EN 1090 checks: certificati_31, riesame_tecnico, controllo_finale, wps_wpqr
        checks = gate["checks"]
        expected_checks = ["certificati_31", "riesame_tecnico", "controllo_finale", "wps_wpqr"]
        for check in expected_checks:
            assert check in checks, f"Missing check: {check}"
        
        print(f"✓ Evidence Gate: emittable={gate['emittable']}, checks={list(checks.keys())}")
        if gate["blocking_reasons"]:
            print(f"  Blocking reasons: {gate['blocking_reasons'][:2]}...")

    def test_12_emetti_blocked_when_gate_not_ok(self, api_session):
        """POST /api/emissioni/{ramo_id}/{emissione_id}/emetti — block emission if gate NOT OK (409)"""
        ramo_id = _test_data["created_ramo_id"]
        emissione_id = _test_data["created_emissione_id"]
        assert ramo_id and emissione_id, "Test data not set from previous tests"
        
        # First check gate status
        gate_response = api_session.get(f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}/gate")
        gate = gate_response.json()
        
        if not gate["emittable"]:
            # Try to emit — should fail with 409
            response = api_session.post(f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}/emetti")
            assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "detail" in data
            print(f"✓ Emission blocked (409): {data['detail'][:80]}...")
        else:
            # Gate is OK, emission should succeed
            response = api_session.post(f"{BASE_URL}/api/emissioni/{ramo_id}/{emissione_id}/emetti")
            assert response.status_code == 200
            print(f"✓ Emission succeeded (gate was OK)")

    # ─── GERARCHIA (AGGREGATED VIEW) TESTS ───────────────────────────────────

    def test_13_get_gerarchia_aggregated_view(self, api_session):
        """GET /api/commesse/{commessa_id}/gerarchia — aggregated view with branches and emissions"""
        response = api_session.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/gerarchia")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        gerarchia = response.json()
        assert "commessa" in gerarchia
        assert "rami" in gerarchia
        assert "n_rami" in gerarchia
        assert "has_branches" in gerarchia
        
        # Verify commessa info
        assert gerarchia["commessa"]["commessa_id"] == COMMESSA_ID
        
        # Verify rami have nested emissioni
        for ramo in gerarchia["rami"]:
            assert "emissioni" in ramo
            assert "n_emissioni" in ramo
            assert "n_emesse" in ramo
            assert "n_bloccate" in ramo
            assert "n_draft" in ramo
        
        print(f"✓ Gerarchia: {gerarchia['n_rami']} rami, has_branches={gerarchia['has_branches']}")

    # ─── MATERIALIZZA LEGACY TESTS ───────────────────────────────────────────

    def test_14_materializza_legacy(self, api_session):
        """POST /api/commesse-normative/{commessa_id}/materializza-legacy — convert legacy to real branch"""
        response = api_session.post(f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}/materializza-legacy")
        
        # Should return 200 with the existing/materialized branch
        if response.status_code == 200:
            ramo = response.json()
            assert "ramo_id" in ramo
            assert ramo["commessa_id"] == COMMESSA_ID
            print(f"✓ Materializza legacy: returned ramo {ramo['ramo_id']}")
        elif response.status_code == 400:
            # Already has branches or invalid normativa
            data = response.json()
            print(f"✓ Materializza legacy: {data.get('detail', 'already has branches')}")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}: {response.text}")

    # ─── UNIQUE INDEX TEST ───────────────────────────────────────────────────

    def test_15_unique_index_same_normativa(self, api_session):
        """Unique index: cannot create 2 branches with same normativa for same commessa"""
        # Try to create another EN_1090 branch — should return existing (idempotent)
        payload = {"normativa": "EN_1090"}
        response = api_session.post(
            f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}",
            json=payload
        )
        
        # Due to idempotency, this returns 201 with the existing branch
        assert response.status_code == 201
        ramo = response.json()
        assert ramo["ramo_id"] == _test_data["created_ramo_id"]
        print(f"✓ Unique index enforced via idempotency: same ramo_id returned")

    # ─── CREATE DIFFERENT NORMATIVA BRANCH ───────────────────────────────────

    def test_16_create_generica_branch(self, api_session):
        """Create GENERICA branch to test different emission types"""
        payload = {"normativa": "GENERICA"}
        response = api_session.post(
            f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}",
            json=payload
        )
        assert response.status_code == 201
        
        ramo = response.json()
        assert ramo["normativa"] == "GENERICA"
        assert "GEN" in ramo["codice_ramo"]
        
        _test_data["generica_ramo_id"] = ramo["ramo_id"]
        
        # Create emission for GENERICA — should have LOT type with L prefix
        em_response = api_session.post(
            f"{BASE_URL}/api/emissioni/{ramo['ramo_id']}",
            json={"descrizione": "Lotto generico test"}
        )
        assert em_response.status_code == 201
        
        emissione = em_response.json()
        assert emissione["emission_type"] == "LOT"
        assert "L" in emissione["codice_emissione"]
        print(f"✓ GENERICA branch: {ramo['codice_ramo']}, emission: {emissione['codice_emissione']}")

    def test_17_list_emissioni_for_ramo(self, api_session):
        """GET /api/emissioni/{ramo_id} — list emissions for a branch"""
        ramo_id = _test_data["created_ramo_id"]
        assert ramo_id, "Ramo ID not set from previous test"
        
        response = api_session.get(f"{BASE_URL}/api/emissioni/{ramo_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "emissioni" in data
        assert "total" in data
        assert "ramo" in data
        assert data["total"] >= 2  # We created 2 emissions
        print(f"✓ Listed {data['total']} emissioni for ramo {data['ramo']}")


class TestCommesseNormativeEdgeCases:
    """Edge case tests for Commesse Normative"""

    def test_get_ramo_not_found(self, api_session):
        """GET /api/commesse-normative/{commessa_id}/{ramo_id} — 404 for non-existent ramo"""
        response = api_session.get(f"{BASE_URL}/api/commesse-normative/{COMMESSA_ID}/ramo_nonexistent")
        assert response.status_code == 404

    def test_get_emissione_not_found(self, api_session):
        """GET /api/emissioni/{ramo_id}/{emissione_id} — 404 for non-existent emission"""
        ramo_id = _test_data.get("created_ramo_id")
        if ramo_id:
            response = api_session.get(f"{BASE_URL}/api/emissioni/{ramo_id}/em_nonexistent")
            assert response.status_code == 404
        else:
            pytest.skip("No ramo_id available")

    def test_create_emissione_invalid_ramo(self, api_session):
        """POST /api/emissioni/{ramo_id} — 400/404 for non-existent ramo"""
        response = api_session.post(
            f"{BASE_URL}/api/emissioni/ramo_nonexistent",
            json={"descrizione": "Test"}
        )
        # API returns 400 (ValueError) when ramo not found
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"

    def test_gerarchia_not_found(self, api_session):
        """GET /api/commesse/{commessa_id}/gerarchia — 404 for non-existent commessa"""
        response = api_session.get(f"{BASE_URL}/api/commesse/com_nonexistent/gerarchia")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

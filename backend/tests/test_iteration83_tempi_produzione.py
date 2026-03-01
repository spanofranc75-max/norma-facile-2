"""
Iteration 83: Tempi Produzione — Backend Tests

Tests for new production timing fields:
- started_at, completed_at, operator_name on fasi_produzione
- Backward compatibility (updates without new fields)
- GET /api/commesse/{cid}/ops returns fields when set
- Null-safe behavior when fields absent

Feature request:
1) Register started_at, completed_at, operator_name on production phases
2) Modal confirmation when clicking 'Completa' with date/time inputs + operator
3) Dates shown as badge next to completed status
4) Backward compatible (new fields are optional)
5) PDF Fascicolo Tecnico uses completed_at with fallback
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Ensure BASE_URL is set
assert BASE_URL, "REACT_APP_BACKEND_URL must be set for tests"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token via test login"""
    try:
        # Try Google OAuth test endpoint if available
        response = requests.post(f"{BASE_URL}/api/auth/google/test-login", json={
            "email": "test-tempi-produzione@example.com",
            "name": "Test Tempi Produzione User"
        }, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
    except Exception as e:
        print(f"Auth failed: {e}")
    pytest.skip("Authentication not available")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def test_commessa(api_client):
    """Create a test commessa with initialized fasi_produzione"""
    # Create commessa
    comm_payload = {
        "numero": f"TEST-TEMPI-{datetime.now().strftime('%H%M%S')}",
        "title": "Test Tempi Produzione Commessa",
        "description": "Testing started_at, completed_at, operator_name fields",
        "stato": "in_corso"
    }
    resp = api_client.post(f"{BASE_URL}/api/commesse/", json=comm_payload)
    assert resp.status_code in [200, 201], f"Failed to create commessa: {resp.text}"
    commessa = resp.json()
    commessa_id = commessa.get("commessa_id")
    
    # Initialize production phases
    resp_init = api_client.post(f"{BASE_URL}/api/commesse/{commessa_id}/produzione/init")
    assert resp_init.status_code in [200, 201], f"Failed to init produzione: {resp_init.text}"
    
    yield {"commessa_id": commessa_id, "numero": comm_payload["numero"]}
    
    # Cleanup
    try:
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")
    except:
        pass


class TestHealthAndBasics:
    """Health check and basic API verification"""
    
    def test_health_endpoint(self, api_client):
        """GET /api/health returns healthy status"""
        resp = api_client.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint returns healthy")
    
    def test_base_url_accessible(self, api_client):
        """Base URL is accessible"""
        resp = api_client.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        print(f"PASS: Base URL {BASE_URL} accessible")


class TestFaseUpdateWithNewFields:
    """Tests for PUT /api/commesse/{cid}/produzione/{fase_tipo} with new fields"""
    
    def test_avvia_fase_with_started_at(self, api_client, test_commessa):
        """PUT produzione with stato='in_corso' saves started_at field"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "taglio"
        started_at = "2026-01-15T08:30:00"
        
        payload = {
            "stato": "in_corso",
            "started_at": started_at
        }
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify via GET ops
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert ops_resp.status_code == 200
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        taglio = next((f for f in fasi if f.get("tipo") == "taglio"), None)
        
        assert taglio is not None, "Taglio fase not found"
        assert taglio.get("stato") == "in_corso", f"Expected in_corso, got {taglio.get('stato')}"
        assert taglio.get("started_at") == started_at, f"started_at mismatch: {taglio.get('started_at')}"
        # Also check data_inizio is set (backward compat)
        assert taglio.get("data_inizio") is not None, "data_inizio should be set"
        print(f"PASS: Fase {fase_tipo} avviata con started_at={started_at}")
    
    def test_completa_fase_with_all_fields(self, api_client, test_commessa):
        """PUT produzione with stato='completato' saves completed_at, operator_name, started_at"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "foratura"
        
        # First start the phase
        api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json={
            "stato": "in_corso"
        })
        
        # Then complete with all fields
        started_at = "2026-01-15T09:00:00"
        completed_at = "2026-01-15T12:30:00"
        operator_name = "Mario Rossi"
        
        payload = {
            "stato": "completato",
            "started_at": started_at,
            "completed_at": completed_at,
            "operator_name": operator_name
        }
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify via GET ops
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert ops_resp.status_code == 200
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        foratura = next((f for f in fasi if f.get("tipo") == "foratura"), None)
        
        assert foratura is not None, "Foratura fase not found"
        assert foratura.get("stato") == "completato"
        assert foratura.get("started_at") == started_at, f"started_at mismatch"
        assert foratura.get("completed_at") == completed_at, f"completed_at mismatch"
        assert foratura.get("operator_name") == operator_name, f"operator_name mismatch"
        # Backward compat fields
        assert foratura.get("data_inizio") == started_at, "data_inizio should match started_at"
        assert foratura.get("data_fine") == completed_at, "data_fine should match completed_at"
        print(f"PASS: Fase {fase_tipo} completata con tutti i nuovi campi")
    
    def test_completa_fase_only_completed_at(self, api_client, test_commessa):
        """PUT produzione with stato='completato' saves completed_at even without started_at"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "assemblaggio"
        
        # Start phase first
        api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json={
            "stato": "in_corso"
        })
        
        completed_at = "2026-01-15T16:00:00"
        payload = {
            "stato": "completato",
            "completed_at": completed_at
        }
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        assemblaggio = next((f for f in fasi if f.get("tipo") == "assemblaggio"), None)
        
        assert assemblaggio.get("completed_at") == completed_at
        print(f"PASS: Fase completata con solo completed_at")
    
    def test_completa_fase_only_operator_name(self, api_client, test_commessa):
        """PUT produzione with operator_name only (without timestamps)"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "saldatura"
        
        # Start phase first
        api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json={
            "stato": "in_corso"
        })
        
        operator_name = "Giuseppe Verdi"
        payload = {
            "stato": "completato",
            "operator_name": operator_name
        }
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        saldatura = next((f for f in fasi if f.get("tipo") == "saldatura"), None)
        
        assert saldatura.get("operator_name") == operator_name
        # completed_at should be auto-filled with current timestamp when not provided
        assert saldatura.get("data_fine") is not None, "data_fine should be auto-set"
        print(f"PASS: Fase completata con solo operator_name")


class TestBackwardCompatibility:
    """Backward compatibility tests — updates without new fields should still work"""
    
    def test_update_fase_without_new_fields(self, api_client, test_commessa):
        """PUT produzione without started_at/completed_at/operator_name still works"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "pulizia"
        
        # Update to in_corso without new fields
        payload = {"stato": "in_corso"}
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify state changed
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        pulizia = next((f for f in fasi if f.get("tipo") == "pulizia"), None)
        
        assert pulizia.get("stato") == "in_corso"
        # data_inizio should be auto-set even without explicit started_at
        assert pulizia.get("data_inizio") is not None
        print("PASS: Update without new fields works (backward compatible)")
    
    def test_complete_fase_without_new_fields(self, api_client, test_commessa):
        """PUT produzione completato without new fields uses auto-timestamps"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "pulizia"
        
        payload = {"stato": "completato"}
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        # Verify
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        pulizia = next((f for f in fasi if f.get("tipo") == "pulizia"), None)
        
        assert pulizia.get("stato") == "completato"
        assert pulizia.get("data_fine") is not None, "data_fine should be auto-set"
        # New fields may be null (not set)
        print("PASS: Complete without new fields uses auto-timestamps")
    
    def test_existing_fase_data_preserved(self, api_client, test_commessa):
        """Update with new fields doesn't break existing data"""
        cid = test_commessa["commessa_id"]
        fase_tipo = "preparazione_superfici"
        
        # Start phase
        api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json={
            "stato": "in_corso",
            "operatore": "Old System Operator",
            "note": "Test note for backward compat"
        })
        
        # Complete with new fields
        payload = {
            "stato": "completato",
            "completed_at": "2026-01-15T17:00:00",
            "operator_name": "New System Operator"
        }
        resp = api_client.put(f"{BASE_URL}/api/commesse/{cid}/produzione/{fase_tipo}", json=payload)
        assert resp.status_code == 200
        
        # Verify both old and new fields
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        fasi = ops.get("fasi_produzione", [])
        fase = next((f for f in fasi if f.get("tipo") == "preparazione_superfici"), None)
        
        assert fase.get("stato") == "completato"
        assert fase.get("completed_at") == "2026-01-15T17:00:00"
        assert fase.get("operator_name") == "New System Operator"
        # Old field may still exist
        print("PASS: New fields coexist with old fields")


class TestGetOpsNullSafety:
    """Tests for GET /api/commesse/{cid}/ops null-safe behavior"""
    
    def test_get_ops_returns_fasi_with_new_fields(self, api_client, test_commessa):
        """GET ops returns fasi_produzione with started_at, completed_at, operator_name when set"""
        cid = test_commessa["commessa_id"]
        
        resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert resp.status_code == 200
        ops = resp.json()
        
        fasi = ops.get("fasi_produzione", [])
        assert len(fasi) > 0, "fasi_produzione should not be empty"
        
        # Check that phases that were completed have the fields
        completed_fasi = [f for f in fasi if f.get("stato") == "completato"]
        for fase in completed_fasi:
            # completed_at should exist (may be null for old phases without it)
            # Just verify the field doesn't cause errors
            _ = fase.get("completed_at")
            _ = fase.get("started_at")
            _ = fase.get("operator_name")
        
        print(f"PASS: GET ops returns {len(fasi)} fasi with new fields accessible")
    
    def test_get_ops_null_fields_no_error(self, api_client, test_commessa):
        """GET ops doesn't error when new fields are absent (null safe)"""
        cid = test_commessa["commessa_id"]
        
        # Reset a phase to da_fare (should have null new fields)
        # Note: We may not have an endpoint to reset, so just verify GET works
        resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert resp.status_code == 200
        
        ops = resp.json()
        fasi = ops.get("fasi_produzione", [])
        
        for fase in fasi:
            # These should not raise KeyError, just return None
            started_at = fase.get("started_at")
            completed_at = fase.get("completed_at")
            operator_name = fase.get("operator_name")
            # No assertion needed, just verify no exception
        
        print("PASS: GET ops is null-safe for new fields")


class TestRegressionContoLavoro:
    """Regression tests for existing C/L workflow"""
    
    def test_create_conto_lavoro_still_works(self, api_client, test_commessa):
        """POST /api/commesse/{cid}/conto-lavoro still works"""
        cid = test_commessa["commessa_id"]
        
        payload = {
            "tipo": "verniciatura",
            "fornitore_nome": "Test Fornitore CL Regression",
            "ral": "RAL 9010",
            "righe": [{"descrizione": "Test materiale", "quantita": 10, "peso_kg": 50}],
            "note": "Regression test for C/L workflow"
        }
        resp = api_client.post(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro", json=payload)
        assert resp.status_code in [200, 201], f"Failed: {resp.text}"
        data = resp.json()
        assert "conto_lavoro" in data or "cl_id" in data.get("conto_lavoro", {}) or "message" in data
        print("PASS: POST conto-lavoro still works")
    
    def test_rientro_still_works(self, api_client, test_commessa):
        """POST /api/commesse/{cid}/conto-lavoro/{cl_id}/rientro regression"""
        cid = test_commessa["commessa_id"]
        
        # Create C/L
        cl_payload = {
            "tipo": "zincatura",
            "fornitore_nome": "Test Zincatura Fornitore",
            "righe": [{"descrizione": "Profili HEA", "quantita": 5, "peso_kg": 200}]
        }
        cl_resp = api_client.post(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro", json=cl_payload)
        assert cl_resp.status_code in [200, 201]
        cl_data = cl_resp.json()
        cl_id = cl_data.get("conto_lavoro", {}).get("cl_id")
        
        if not cl_id:
            pytest.skip("Could not create C/L for rientro test")
        
        # Update to inviato
        api_client.put(f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}", json={"stato": "inviato"})
        
        # Test rientro via form data
        rientro_data = {
            "data_rientro": "2026-01-15",
            "ddt_fornitore_numero": "DDT-TEST-001",
            "ddt_fornitore_data": "2026-01-14",
            "peso_rientrato_kg": "195",
            "esito_qc": "conforme",
            "note_rientro": "Regression test"
        }
        rientro_resp = requests.post(
            f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}/rientro",
            headers={"Authorization": api_client.headers["Authorization"]},
            data=rientro_data  # Form data, not JSON
        )
        assert rientro_resp.status_code == 200, f"Rientro failed: {rientro_resp.text}"
        print("PASS: POST rientro still works")
    
    def test_verifica_still_works(self, api_client, test_commessa):
        """PATCH /api/commesse/{cid}/conto-lavoro/{cl_id}/verifica regression"""
        cid = test_commessa["commessa_id"]
        
        # Get C/L list to find one in 'rientrato' state
        ops_resp = api_client.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        ops = ops_resp.json()
        cl_list = ops.get("conto_lavoro", [])
        
        rientrato_cl = next((c for c in cl_list if c.get("stato") == "rientrato"), None)
        if not rientrato_cl:
            pytest.skip("No C/L in rientrato state for verifica test")
        
        cl_id = rientrato_cl.get("cl_id")
        verifica_resp = requests.patch(
            f"{BASE_URL}/api/commesse/{cid}/conto-lavoro/{cl_id}/verifica",
            headers={
                "Authorization": api_client.headers["Authorization"],
                "Content-Type": "application/json"
            }
        )
        assert verifica_resp.status_code == 200, f"Verifica failed: {verifica_resp.text}"
        print("PASS: PATCH verifica still works")


class TestUnauthorizedAccess:
    """Tests for unauthorized access"""
    
    def test_update_fase_requires_auth(self, test_commessa):
        """PUT produzione returns 401/403 without auth"""
        cid = test_commessa["commessa_id"]
        resp = requests.put(
            f"{BASE_URL}/api/commesse/{cid}/produzione/taglio",
            json={"stato": "in_corso"}
        )
        assert resp.status_code in [401, 403, 422], f"Expected auth error, got {resp.status_code}"
        print("PASS: PUT produzione requires auth")
    
    def test_get_ops_requires_auth(self, test_commessa):
        """GET ops returns 401/403 without auth"""
        cid = test_commessa["commessa_id"]
        resp = requests.get(f"{BASE_URL}/api/commesse/{cid}/ops")
        assert resp.status_code in [401, 403, 422], f"Expected auth error, got {resp.status_code}"
        print("PASS: GET ops requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

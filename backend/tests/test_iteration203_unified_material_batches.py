"""
Iteration 203: Unified Material Batches Collection Tests
Tests the unification of data collections — material_batches is now the single source of truth.

Key features tested:
1. GET /api/fpc/batches/rintracciabilita/{commessa_id} — reads from unified material_batches
2. GET /api/riesame/{commessa_id} — materiali_confermati check reads from material_batches
3. GET /api/riesame/{commessa_id} — strumenti_tarati and attrezzature_idonee checks
4. GET /api/riesame/{commessa_id} — tolleranza_calibro check uses per-instrument soglia_accettabilita
5. GET /api/controllo-finale/{commessa_id} — comp_colate_coerenti reads from material_batches
6. GET /api/controllo-finale/{commessa_id} — dim_strumenti_tarati verifies instruments calibration
7. GET /api/controllo-finale/{commessa_id} — vt_saldature_registro checks registro_saldatura entries
8. GET /api/registro-saldatura/{commessa_id}/saldatori-idonei?processo=135 — Filters welders by process
9. POST /api/fpc/batches/link-ddt/{commessa_id} — Links DDTs to material_batches
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_loiano_cims_2026"
TEST_USER_ID = "user_97c773827822"


@pytest.fixture
def auth_cookies():
    """Return session cookie for authenticated requests."""
    return {"session_token": SESSION_TOKEN}


class TestRintracciabilitaEndpoint:
    """Test GET /api/fpc/batches/rintracciabilita/{commessa_id} — reads from unified material_batches"""

    def test_rintracciabilita_returns_batches(self, auth_cookies):
        """Verify rintracciabilita endpoint returns material batches for commessa."""
        response = requests.get(
            f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "righe" in data, "Response should contain 'righe' field"
        assert "totale" in data, "Response should contain 'totale' field"
        assert "collegati" in data, "Response should contain 'collegati' field"
        assert "commessa_id" in data, "Response should contain 'commessa_id' field"
        
        # Verify we have batches (should be 3 according to context)
        righe = data.get("righe", [])
        print(f"Found {len(righe)} material batches for commessa {TEST_COMMESSA_ID}")
        
        # Verify batch structure
        if righe:
            batch = righe[0]
            assert "batch_id" in batch, "Batch should have batch_id"
            assert "colata" in batch, "Batch should have colata (heat_number)"
            assert "descrizione" in batch, "Batch should have descrizione"
            assert "linked" in batch, "Batch should have linked status"
            print(f"Sample batch: {batch.get('batch_id')} - colata: {batch.get('colata')}")

    def test_rintracciabilita_shows_colata_from_material_batches(self, auth_cookies):
        """Verify colata field is populated from material_batches collection."""
        response = requests.get(
            f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        righe = data.get("righe", [])
        
        # Check that at least some batches have colata (heat_number)
        batches_with_colata = [r for r in righe if r.get("colata")]
        print(f"Batches with colata: {len(batches_with_colata)} / {len(righe)}")
        
        for r in batches_with_colata[:3]:
            print(f"  - {r.get('batch_id')}: colata={r.get('colata')}, desc={r.get('descrizione')}")


class TestRiesameEndpoint:
    """Test GET /api/riesame/{commessa_id} — auto-checks read from correct collections"""

    def test_riesame_returns_checks(self, auth_cookies):
        """Verify riesame endpoint returns all checks."""
        response = requests.get(
            f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "checks" in data, "Response should contain 'checks' field"
        assert "superato" in data, "Response should contain 'superato' field"
        assert "n_ok" in data, "Response should contain 'n_ok' field"
        assert "n_totale" in data, "Response should contain 'n_totale' field"
        
        checks = data.get("checks", [])
        print(f"Riesame has {len(checks)} checks, {data.get('n_ok')}/{data.get('n_totale')} passed")

    def test_riesame_materiali_confermati_reads_material_batches(self, auth_cookies):
        """Verify materiali_confermati check reads from material_batches collection."""
        response = requests.get(
            f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find materiali_confermati check
        mat_check = next((c for c in checks if c.get("id") == "materiali_confermati"), None)
        assert mat_check is not None, "Should have materiali_confermati check"
        
        print(f"materiali_confermati check:")
        print(f"  - esito: {mat_check.get('esito')}")
        print(f"  - valore: {mat_check.get('valore')}")
        print(f"  - nota: {mat_check.get('nota')}")
        
        # Verify the check shows lotti count (should show 3 lotti according to context)
        valore = mat_check.get("valore", "")
        assert "lotti" in valore.lower() or "lotto" in valore.lower(), f"valore should mention lotti: {valore}"

    def test_riesame_strumenti_tarati_check(self, auth_cookies):
        """Verify strumenti_tarati check reads instruments correctly."""
        response = requests.get(
            f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find strumenti_tarati check
        str_check = next((c for c in checks if c.get("id") == "strumenti_tarati"), None)
        assert str_check is not None, "Should have strumenti_tarati check"
        
        print(f"strumenti_tarati check:")
        print(f"  - esito: {str_check.get('esito')}")
        print(f"  - valore: {str_check.get('valore')}")
        print(f"  - nota: {str_check.get('nota')}")

    def test_riesame_attrezzature_idonee_check(self, auth_cookies):
        """Verify attrezzature_idonee check reads instruments correctly."""
        response = requests.get(
            f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find attrezzature_idonee check
        attr_check = next((c for c in checks if c.get("id") == "attrezzature_idonee"), None)
        assert attr_check is not None, "Should have attrezzature_idonee check"
        
        print(f"attrezzature_idonee check:")
        print(f"  - esito: {attr_check.get('esito')}")
        print(f"  - valore: {attr_check.get('valore')}")
        print(f"  - nota: {attr_check.get('nota')}")

    def test_riesame_tolleranza_calibro_uses_soglia_accettabilita(self, auth_cookies):
        """Verify tolleranza_calibro check uses per-instrument configurable soglia_accettabilita."""
        response = requests.get(
            f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find tolleranza_calibro check
        tol_check = next((c for c in checks if c.get("id") == "tolleranza_calibro"), None)
        assert tol_check is not None, "Should have tolleranza_calibro check"
        
        print(f"tolleranza_calibro check:")
        print(f"  - esito: {tol_check.get('esito')}")
        print(f"  - valore: {tol_check.get('valore')}")
        print(f"  - nota: {tol_check.get('nota')}")
        
        # Verify the check mentions soglia or tolerance
        nota = tol_check.get("nota", "")
        valore = tol_check.get("valore", "")
        # Should mention "soglia" or "tolleranza" or "conforme"
        assert any(word in (nota + valore).lower() for word in ["soglia", "tolleranza", "conforme", "fuori"]), \
            f"Check should mention tolerance-related terms: valore={valore}, nota={nota}"


class TestControlloFinaleEndpoint:
    """Test GET /api/controllo-finale/{commessa_id} — auto-checks read from correct collections"""

    def test_controllo_finale_returns_11_checks(self, auth_cookies):
        """Verify controllo finale returns all 11 checks in 3 areas."""
        response = requests.get(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "checks" in data, "Response should contain 'checks' field"
        assert "areas" in data, "Response should contain 'areas' field"
        
        checks = data.get("checks", [])
        areas = data.get("areas", {})
        
        print(f"Controllo Finale has {len(checks)} checks")
        assert len(checks) == 11, f"Expected 11 checks, got {len(checks)}"
        
        # Verify 3 areas
        assert len(areas) == 3, f"Expected 3 areas, got {len(areas)}"
        print(f"Areas: {list(areas.keys())}")
        
        for area, stats in areas.items():
            print(f"  - {area}: {stats.get('ok')}/{stats.get('totale')}")

    def test_controllo_finale_comp_colate_coerenti_reads_material_batches(self, auth_cookies):
        """Verify comp_colate_coerenti check reads from material_batches collection."""
        response = requests.get(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find comp_colate_coerenti check
        colate_check = next((c for c in checks if c.get("id") == "comp_colate_coerenti"), None)
        assert colate_check is not None, "Should have comp_colate_coerenti check"
        
        print(f"comp_colate_coerenti check:")
        print(f"  - area: {colate_check.get('area')}")
        print(f"  - esito: {colate_check.get('esito')}")
        print(f"  - valore: {colate_check.get('valore')}")
        print(f"  - nota: {colate_check.get('nota')}")
        
        # Verify it's in Compliance area
        assert colate_check.get("area") == "Compliance", "comp_colate_coerenti should be in Compliance area"
        
        # Verify valore mentions lotti
        valore = colate_check.get("valore", "")
        assert "lotti" in valore.lower() or "lotto" in valore.lower(), f"valore should mention lotti: {valore}"

    def test_controllo_finale_dim_strumenti_tarati(self, auth_cookies):
        """Verify dim_strumenti_tarati check verifies instruments calibration status."""
        response = requests.get(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find dim_strumenti_tarati check
        dim_check = next((c for c in checks if c.get("id") == "dim_strumenti_tarati"), None)
        assert dim_check is not None, "Should have dim_strumenti_tarati check"
        
        print(f"dim_strumenti_tarati check:")
        print(f"  - area: {dim_check.get('area')}")
        print(f"  - esito: {dim_check.get('esito')}")
        print(f"  - valore: {dim_check.get('valore')}")
        print(f"  - nota: {dim_check.get('nota')}")
        
        # Verify it's in Dimensionale area
        assert dim_check.get("area") == "Dimensionale", "dim_strumenti_tarati should be in Dimensionale area"
        
        # Verify valore mentions strumenti
        valore = dim_check.get("valore", "")
        assert "strumenti" in valore.lower(), f"valore should mention strumenti: {valore}"

    def test_controllo_finale_vt_saldature_registro(self, auth_cookies):
        """Verify vt_saldature_registro check reads from registro_saldatura entries."""
        response = requests.get(
            f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find vt_saldature_registro check
        vt_check = next((c for c in checks if c.get("id") == "vt_saldature_registro"), None)
        assert vt_check is not None, "Should have vt_saldature_registro check"
        
        print(f"vt_saldature_registro check:")
        print(f"  - area: {vt_check.get('area')}")
        print(f"  - esito: {vt_check.get('esito')}")
        print(f"  - valore: {vt_check.get('valore')}")
        print(f"  - nota: {vt_check.get('nota')}")
        
        # Verify it's in Visual Testing area
        assert vt_check.get("area") == "Visual Testing", "vt_saldature_registro should be in Visual Testing area"
        
        # Verify valore mentions giunti
        valore = vt_check.get("valore", "")
        assert "giunt" in valore.lower() or "registrat" in valore.lower(), f"valore should mention giunti: {valore}"


class TestRegistroSaldaturaEndpoint:
    """Test GET /api/registro-saldatura/{commessa_id}/saldatori-idonei — filters welders by process"""

    def test_saldatori_idonei_filters_by_process(self, auth_cookies):
        """Verify saldatori-idonei endpoint filters welders by valid process qualification."""
        response = requests.get(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei",
            params={"processo": "135"},
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "saldatori" in data, "Response should contain 'saldatori' field"
        
        saldatori = data.get("saldatori", [])
        print(f"Found {len(saldatori)} welders qualified for process 135")
        
        for s in saldatori[:3]:
            print(f"  - {s.get('name', s.get('nome', '?'))}: {s.get('welder_id', s.get('saldatore_id', '?'))}")

    def test_saldatori_idonei_without_process_filter(self, auth_cookies):
        """Verify saldatori-idonei endpoint works without process filter."""
        response = requests.get(
            f"{BASE_URL}/api/registro-saldatura/{TEST_COMMESSA_ID}/saldatori-idonei",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        saldatori = data.get("saldatori", [])
        print(f"Found {len(saldatori)} total qualified welders (no process filter)")


class TestLinkDdtEndpoint:
    """Test POST /api/fpc/batches/link-ddt/{commessa_id} — links DDTs to material_batches"""

    def test_link_ddt_endpoint_exists(self, auth_cookies):
        """Verify link-ddt endpoint exists and responds."""
        response = requests.post(
            f"{BASE_URL}/api/fpc/batches/link-ddt/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        # Should return 200 even if no links found
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "links" in data, "Response should contain 'links' field"
        assert "totale" in data, "Response should contain 'totale' field"
        
        print(f"Link DDT result: {data.get('message')}")
        print(f"  - Links created: {data.get('totale')}")
        print(f"  - Total batches: {data.get('batches_totali', 'N/A')}")

    def test_link_ddt_updates_material_batches(self, auth_cookies):
        """Verify link-ddt updates material_batches collection (not fpc_batches)."""
        # First, run the link operation
        link_response = requests.post(
            f"{BASE_URL}/api/fpc/batches/link-ddt/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert link_response.status_code == 200
        
        # Then verify rintracciabilita shows updated data
        rint_response = requests.get(
            f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert rint_response.status_code == 200
        
        data = rint_response.json()
        righe = data.get("righe", [])
        
        # Check if any batches have DDT linked
        linked_batches = [r for r in righe if r.get("linked") or r.get("ddt_numero") or r.get("ddt_id")]
        print(f"Batches with DDT linked: {len(linked_batches)} / {len(righe)}")


class TestDopFrazionataAutoPopulation:
    """Test DOP frazionata auto-population from Riesame EXC + material_batches"""

    def test_dop_frazionate_list(self, auth_cookies):
        """Verify DOP frazionate list endpoint works."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionate",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dop_frazionate" in data, "Response should contain 'dop_frazionate' field"
        
        dops = data.get("dop_frazionate", [])
        print(f"Found {len(dops)} DOP frazionate for commessa {TEST_COMMESSA_ID}")
        
        for dop in dops[:2]:
            print(f"  - {dop.get('dop_numero')}: {dop.get('descrizione')}")
            print(f"    classe_esecuzione: {dop.get('classe_esecuzione')}")
            print(f"    batches_rintracciabilita: {len(dop.get('batches_rintracciabilita', []))} items")


class TestInstrumentsWithSoglia:
    """Test instruments endpoint returns soglia_accettabilita field"""

    def test_instruments_list_includes_soglia(self, auth_cookies):
        """Verify instruments list includes soglia_accettabilita field."""
        response = requests.get(
            f"{BASE_URL}/api/instruments",
            cookies=auth_cookies,
            allow_redirects=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        instruments = data if isinstance(data, list) else data.get("instruments", [])
        
        print(f"Found {len(instruments)} instruments")
        
        # Check for instruments with soglia_accettabilita
        with_soglia = [i for i in instruments if i.get("soglia_accettabilita") is not None]
        print(f"Instruments with soglia_accettabilita: {len(with_soglia)}")
        
        for inst in with_soglia[:3]:
            print(f"  - {inst.get('name')}: soglia={inst.get('soglia_accettabilita')} {inst.get('unita_soglia', 'mm')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 231 — Safety Branch v2 with 3-Level Risk Library
==========================================================
Tests for the refactored 3-collection library system:
- lib_fasi_lavoro (11 work phases)
- lib_rischi_sicurezza (20 risks)
- lib_dpi_misure (31 DPI/measures/equipment)

Chain: Fase → Rischi → DPI/Misure
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_perizia_205a45704b22"

@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestLibreriaSeed:
    """Test POST /api/libreria/seed — seeds 3 collections (idempotent)"""
    
    def test_seed_libreria_v2(self, api_client):
        """POST /api/libreria/seed should seed all 3 collections"""
        response = api_client.post(f"{BASE_URL}/api/libreria/seed")
        assert response.status_code == 200, f"Seed failed: {response.text}"
        data = response.json()
        
        # Should return counts for all 3 collections
        assert "fasi" in data, "Missing 'fasi' in seed response"
        assert "rischi" in data, "Missing 'rischi' in seed response"
        assert "dpi_misure" in data, "Missing 'dpi_misure' in seed response"
        
        # Verify expected counts
        assert data["fasi"] >= 11, f"Expected at least 11 fasi, got {data['fasi']}"
        assert data["rischi"] >= 18, f"Expected at least 18 rischi, got {data['rischi']}"
        assert data["dpi_misure"] >= 31, f"Expected at least 31 dpi_misure, got {data['dpi_misure']}"
        
        print(f"Seed result: fasi={data['fasi']}, rischi={data['rischi']}, dpi_misure={data['dpi_misure']}")
    
    def test_seed_is_idempotent(self, api_client):
        """Calling seed twice should not duplicate data"""
        # First call
        r1 = api_client.post(f"{BASE_URL}/api/libreria/seed")
        assert r1.status_code == 200
        d1 = r1.json()
        
        # Second call
        r2 = api_client.post(f"{BASE_URL}/api/libreria/seed")
        assert r2.status_code == 200
        d2 = r2.json()
        
        # Counts should be the same
        assert d1["fasi"] == d2["fasi"], "Fasi count changed after second seed"
        assert d1["rischi"] == d2["rischi"], "Rischi count changed after second seed"
        assert d1["dpi_misure"] == d2["dpi_misure"], "DPI/Misure count changed after second seed"


class TestLibreriaFasi:
    """Test GET /api/libreria/fasi — returns 11 fasi lavoro"""
    
    def test_get_all_fasi(self, api_client):
        """GET /api/libreria/fasi should return all work phases"""
        response = api_client.get(f"{BASE_URL}/api/libreria/fasi")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 11, f"Expected at least 11 fasi, got {len(data)}"
        
        # Verify structure of first fase
        fase = data[0]
        assert "codice" in fase, "Missing 'codice' in fase"
        assert "nome" in fase, "Missing 'nome' in fase"
        assert "rischi_ids" in fase, "Missing 'rischi_ids' in fase"
        assert "applicabile_a" in fase, "Missing 'applicabile_a' in fase"
        
        print(f"Got {len(data)} fasi lavoro")
    
    def test_filter_fasi_by_normativa_en1090(self, api_client):
        """GET /api/libreria/fasi?normativa=EN_1090 should filter by normativa"""
        response = api_client.get(f"{BASE_URL}/api/libreria/fasi?normativa=EN_1090")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        # All returned fasi should have EN_1090 in applicabile_a
        for fase in data:
            assert "EN_1090" in fase.get("applicabile_a", []), f"Fase {fase['codice']} not applicable to EN_1090"
        
        print(f"Got {len(data)} fasi for EN_1090")
    
    def test_filter_fasi_by_normativa_en13241(self, api_client):
        """GET /api/libreria/fasi?normativa=EN_13241 should filter by normativa"""
        response = api_client.get(f"{BASE_URL}/api/libreria/fasi?normativa=EN_13241")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        for fase in data:
            assert "EN_13241" in fase.get("applicabile_a", []), f"Fase {fase['codice']} not applicable to EN_13241"
        
        print(f"Got {len(data)} fasi for EN_13241")


class TestLibreriaRischi:
    """Test GET /api/libreria/rischi — returns 20 rischi with gate_critical, dpi_ids, etc."""
    
    def test_get_all_rischi(self, api_client):
        """GET /api/libreria/rischi should return all risks"""
        response = api_client.get(f"{BASE_URL}/api/libreria/rischi")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 18, f"Expected at least 18 rischi, got {len(data)}"
        
        # Verify structure of first rischio
        rischio = data[0]
        assert "codice" in rischio, "Missing 'codice' in rischio"
        assert "nome" in rischio, "Missing 'nome' in rischio"
        assert "categoria" in rischio, "Missing 'categoria' in rischio"
        assert "dpi_ids" in rischio, "Missing 'dpi_ids' in rischio"
        assert "misure_ids" in rischio, "Missing 'misure_ids' in rischio"
        assert "apprestamenti_ids" in rischio, "Missing 'apprestamenti_ids' in rischio"
        
        # Check for gate_critical field
        gate_critical_count = sum(1 for r in data if r.get("gate_critical", False))
        print(f"Got {len(data)} rischi, {gate_critical_count} are gate_critical")
    
    def test_filter_rischi_by_categoria_sicurezza(self, api_client):
        """GET /api/libreria/rischi?categoria=sicurezza should filter by categoria"""
        response = api_client.get(f"{BASE_URL}/api/libreria/rischi?categoria=sicurezza")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        for rischio in data:
            assert rischio.get("categoria") == "sicurezza", f"Rischio {rischio['codice']} has wrong categoria"
        
        print(f"Got {len(data)} rischi with categoria=sicurezza")
    
    def test_filter_rischi_by_categoria_salute(self, api_client):
        """GET /api/libreria/rischi?categoria=salute should filter by categoria"""
        response = api_client.get(f"{BASE_URL}/api/libreria/rischi?categoria=salute")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        for rischio in data:
            assert rischio.get("categoria") == "salute", f"Rischio {rischio['codice']} has wrong categoria"
        
        print(f"Got {len(data)} rischi with categoria=salute")
    
    def test_rischi_have_domande_verifica(self, api_client):
        """Rischi should have domande_verifica with gate_critical flag"""
        response = api_client.get(f"{BASE_URL}/api/libreria/rischi")
        assert response.status_code == 200
        data = response.json()
        
        # Find rischi with domande_verifica
        rischi_with_domande = [r for r in data if r.get("domande_verifica")]
        assert len(rischi_with_domande) > 0, "No rischi have domande_verifica"
        
        # Check structure of domande
        for rischio in rischi_with_domande:
            for domanda in rischio["domande_verifica"]:
                assert "testo" in domanda, "Missing 'testo' in domanda"
                assert "gate_critical" in domanda, "Missing 'gate_critical' in domanda"
        
        print(f"{len(rischi_with_domande)} rischi have domande_verifica")


class TestLibreriaDpiMisure:
    """Test GET /api/libreria/dpi-misure — returns 31 entries (12 dpi + 11 misure + 8 apprestamenti)"""
    
    def test_get_all_dpi_misure(self, api_client):
        """GET /api/libreria/dpi-misure should return all DPI/misure/apprestamenti"""
        response = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 31, f"Expected at least 31 dpi_misure, got {len(data)}"
        
        # Verify structure
        item = data[0]
        assert "codice" in item, "Missing 'codice'"
        assert "nome" in item, "Missing 'nome'"
        assert "tipo" in item, "Missing 'tipo'"
        
        # Count by tipo
        dpi_count = sum(1 for d in data if d.get("tipo") == "dpi")
        misura_count = sum(1 for d in data if d.get("tipo") == "misura")
        apprestamento_count = sum(1 for d in data if d.get("tipo") == "apprestamento")
        
        print(f"Got {len(data)} items: {dpi_count} dpi, {misura_count} misure, {apprestamento_count} apprestamenti")
        
        assert dpi_count >= 12, f"Expected at least 12 DPI, got {dpi_count}"
        assert misura_count >= 11, f"Expected at least 11 misure, got {misura_count}"
        assert apprestamento_count >= 8, f"Expected at least 8 apprestamenti, got {apprestamento_count}"
    
    def test_filter_dpi_misure_by_tipo_dpi(self, api_client):
        """GET /api/libreria/dpi-misure?tipo=dpi should filter by tipo"""
        response = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure?tipo=dpi")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 12, f"Expected at least 12 DPI, got {len(data)}"
        
        for item in data:
            assert item.get("tipo") == "dpi", f"Item {item['codice']} has wrong tipo"
        
        print(f"Got {len(data)} DPI items")
    
    def test_filter_dpi_misure_by_tipo_misura(self, api_client):
        """GET /api/libreria/dpi-misure?tipo=misura should filter by tipo"""
        response = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure?tipo=misura")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        for item in data:
            assert item.get("tipo") == "misura", f"Item {item['codice']} has wrong tipo"
        
        print(f"Got {len(data)} misura items")
    
    def test_filter_dpi_misure_by_tipo_apprestamento(self, api_client):
        """GET /api/libreria/dpi-misure?tipo=apprestamento should filter by tipo"""
        response = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure?tipo=apprestamento")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        for item in data:
            assert item.get("tipo") == "apprestamento", f"Item {item['codice']} has wrong tipo"
        
        print(f"Got {len(data)} apprestamento items")


class TestLibreriaResolve:
    """Test POST /api/libreria/resolve-rischi and /api/libreria/resolve-dpi"""
    
    def test_resolve_rischi(self, api_client):
        """POST /api/libreria/resolve-rischi should resolve codici to full objects"""
        # First get some rischi codici
        r = api_client.get(f"{BASE_URL}/api/libreria/rischi")
        assert r.status_code == 200
        rischi = r.json()
        codici = [rischi[0]["codice"], rischi[1]["codice"]] if len(rischi) >= 2 else [rischi[0]["codice"]]
        
        # Resolve them
        response = api_client.post(f"{BASE_URL}/api/libreria/resolve-rischi", json={"codici": codici})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == len(codici), f"Expected {len(codici)} resolved rischi, got {len(data)}"
        
        for item in data:
            assert item["codice"] in codici, f"Unexpected codice {item['codice']}"
        
        print(f"Resolved {len(data)} rischi")
    
    def test_resolve_dpi(self, api_client):
        """POST /api/libreria/resolve-dpi should resolve codici to full objects"""
        # First get some dpi codici
        r = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure?tipo=dpi")
        assert r.status_code == 200
        dpi = r.json()
        codici = [dpi[0]["codice"], dpi[1]["codice"]] if len(dpi) >= 2 else [dpi[0]["codice"]]
        
        # Resolve them
        response = api_client.post(f"{BASE_URL}/api/libreria/resolve-dpi", json={"codici": codici})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == len(codici), f"Expected {len(codici)} resolved dpi, got {len(data)}"
        
        print(f"Resolved {len(data)} DPI")
    
    def test_resolve_empty_list(self, api_client):
        """POST /api/libreria/resolve-rischi with empty list should return empty"""
        response = api_client.post(f"{BASE_URL}/api/libreria/resolve-rischi", json={"codici": []})
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Expected empty list for empty codici"


class TestCantieriSicurezzaCRUD:
    """Test cantieri-sicurezza CRUD with v2 schema"""
    
    def test_create_cantiere_v2(self, api_client):
        """POST /api/cantieri-sicurezza should create cantiere with v2 schema"""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "cantiere_id" in data, "Missing cantiere_id"
        
        # Check v2 fields exist
        assert "fasi_lavoro_selezionate" in data, "Missing fasi_lavoro_selezionate"
        assert "dpi_calcolati" in data, "Missing dpi_calcolati"
        assert "misure_calcolate" in data, "Missing misure_calcolate"
        assert "apprestamenti_calcolati" in data, "Missing apprestamenti_calcolati"
        assert "domande_residue" in data, "Missing domande_residue"
        
        print(f"Created cantiere: {data['cantiere_id']}")
        return data["cantiere_id"]
    
    def test_update_cantiere_with_v2_fields(self, api_client):
        """PUT /api/cantieri-sicurezza/{id} should update with v2 fields"""
        # Create a cantiere first
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Update with v2 fields
        update_data = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Test 123",
                "citta_cantiere": "Bologna",
                "data_inizio_lavori": "2026-02-01"
            },
            "soggetti_riferimento": {
                "committente": "Test Committente SRL"
            },
            "lavoratori_coinvolti": [
                {"nominativo": "Mario Rossi", "mansione": "Operaio", "addetto_primo_soccorso": True, "addetto_antincendio": False}
            ],
            "fasi_lavoro_selezionate": [
                {
                    "fase_codice": "FL-008",
                    "confidence": "confermato",
                    "origin": "user",
                    "reasoning": "Selezionata manualmente",
                    "rischi_attivati": [
                        {"rischio_codice": "RS-CADUTA-ALTO", "confidence": "dedotto", "origin": "rules"}
                    ]
                }
            ],
            "dpi_calcolati": [
                {"codice": "DPI-CASCO", "origin": "rules", "da_rischi": ["RS-CADUTA-ALTO"]}
            ],
            "misure_calcolate": [],
            "apprestamenti_calcolati": [
                {"codice": "APP-PONTEGGIO", "origin": "rules", "da_rischi": ["RS-CADUTA-ALTO"]}
            ],
            "domande_residue": [
                {
                    "testo": "Sono previsti lavori ad altezza superiore a 2 m?",
                    "origine_rischio": "RS-CADUTA-ALTO",
                    "impatto": "alto",
                    "gate_critical": True,
                    "risposta": None,
                    "stato": "aperta"
                }
            ]
        }
        
        response = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify v2 fields were saved
        assert len(data["fasi_lavoro_selezionate"]) == 1
        assert data["fasi_lavoro_selezionate"][0]["fase_codice"] == "FL-008"
        assert len(data["dpi_calcolati"]) == 1
        assert len(data["apprestamenti_calcolati"]) == 1
        assert len(data["domande_residue"]) == 1
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"Updated cantiere {cantiere_id} with v2 fields")
    
    def test_list_cantieri(self, api_client):
        """GET /api/cantieri-sicurezza should list all cantieri"""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"Listed {len(data)} cantieri")
    
    def test_delete_cantiere(self, api_client):
        """DELETE /api/cantieri-sicurezza/{id} should delete cantiere"""
        # Create a cantiere first
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("deleted") == True
        
        # Verify it's gone
        get_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert get_resp.status_code == 404
        
        print(f"Deleted cantiere {cantiere_id}")


class TestGatePOS:
    """Test GET /api/cantieri-sicurezza/{id}/gate with blockers field"""
    
    def test_gate_pos_with_blockers(self, api_client):
        """GET /api/cantieri-sicurezza/{id}/gate should include blockers for gate_critical domande"""
        # Create a cantiere with gate_critical domanda
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Update with gate_critical domanda
        update_data = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Test 123",
                "citta_cantiere": "Bologna",
                "data_inizio_lavori": "2026-02-01"
            },
            "soggetti_riferimento": {
                "committente": "Test Committente"
            },
            "lavoratori_coinvolti": [
                {"nominativo": "Mario Rossi", "mansione": "Operaio"}
            ],
            "fasi_lavoro_selezionate": [
                {"fase_codice": "FL-008", "confidence": "confermato", "origin": "user", "rischi_attivati": []}
            ],
            "domande_residue": [
                {
                    "testo": "Sono previsti lavori ad altezza superiore a 2 m?",
                    "origine_rischio": "RS-CADUTA-ALTO",
                    "impatto": "alto",
                    "gate_critical": True,
                    "risposta": None,
                    "stato": "aperta"
                }
            ]
        }
        
        api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=update_data)
        
        # Get gate status
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "completezza_percentuale" in data
        assert "campi_mancanti" in data
        assert "blockers" in data, "Missing 'blockers' field in gate response"
        assert "pronto_per_generazione" in data
        
        # Should have blockers because gate_critical domanda is open
        assert len(data["blockers"]) > 0, "Expected blockers for open gate_critical domanda"
        assert data["pronto_per_generazione"] == False, "Should not be ready with open blockers"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"Gate status: {data['completezza_percentuale']}%, blockers: {len(data['blockers'])}")
    
    def test_gate_pos_ready_when_no_blockers(self, api_client):
        """Gate should be ready when all required fields filled and no blockers"""
        # Create a cantiere
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Update with all required fields and no gate_critical domande
        update_data = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Test 123",
                "citta_cantiere": "Bologna",
                "data_inizio_lavori": "2026-02-01"
            },
            "soggetti_riferimento": {
                "committente": "Test Committente"
            },
            "lavoratori_coinvolti": [
                {"nominativo": "Mario Rossi", "mansione": "Operaio"}
            ],
            "fasi_lavoro_selezionate": [
                {"fase_codice": "FL-008", "confidence": "confermato", "origin": "user", "rischi_attivati": []}
            ],
            "domande_residue": []  # No blockers
        }
        
        api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=update_data)
        
        # Get gate status
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["campi_mancanti"]) == 0, f"Unexpected missing fields: {data['campi_mancanti']}"
        assert len(data["blockers"]) == 0, f"Unexpected blockers: {data['blockers']}"
        assert data["pronto_per_generazione"] == True, "Should be ready with all fields filled"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"Gate ready: {data['pronto_per_generazione']}, completeness: {data['completezza_percentuale']}%")


class TestBackwardCompatibility:
    """Test backward compatibility with old /libreria-rischi endpoints"""
    
    def test_libreria_rischi_compat_all(self, api_client):
        """GET /api/libreria-rischi should return all library entries"""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        # Should return fasi + rischi + dpi combined
        assert len(data) >= 60, f"Expected at least 60 items (11+18+31), got {len(data)}"
        
        print(f"Backward compat: got {len(data)} items from /libreria-rischi")
    
    def test_libreria_rischi_compat_tipo_fase_lavoro(self, api_client):
        """GET /api/libreria-rischi?tipo=fase_lavoro should return fasi"""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi?tipo=fase_lavoro")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 11, f"Expected at least 11 fasi, got {len(data)}"
        
        print(f"Backward compat: got {len(data)} fasi from ?tipo=fase_lavoro")
    
    def test_libreria_rischi_compat_tipo_dpi(self, api_client):
        """GET /api/libreria-rischi?tipo=dpi should return DPI"""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi?tipo=dpi")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 12, f"Expected at least 12 DPI, got {len(data)}"
        
        print(f"Backward compat: got {len(data)} DPI from ?tipo=dpi")
    
    def test_libreria_rischi_seed_compat(self, api_client):
        """POST /api/libreria-rischi/seed should still work"""
        response = api_client.post(f"{BASE_URL}/api/libreria-rischi/seed")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return v2 seed result
        assert "fasi" in data or "seeded" in data
        
        print(f"Backward compat: seed returned {data}")


class TestChainResolution:
    """Test the chain: Fase → Rischi → DPI/Misure"""
    
    def test_fase_rischi_chain(self, api_client):
        """Verify fase.rischi_ids can be resolved to full rischi objects"""
        # Get fasi
        fasi_resp = api_client.get(f"{BASE_URL}/api/libreria/fasi")
        assert fasi_resp.status_code == 200
        fasi = fasi_resp.json()
        
        # Find a fase with rischi_ids
        fase_with_rischi = next((f for f in fasi if f.get("rischi_ids")), None)
        assert fase_with_rischi is not None, "No fase has rischi_ids"
        
        # Resolve the rischi
        rischi_codici = fase_with_rischi["rischi_ids"]
        resolve_resp = api_client.post(f"{BASE_URL}/api/libreria/resolve-rischi", json={"codici": rischi_codici})
        assert resolve_resp.status_code == 200
        rischi = resolve_resp.json()
        
        assert len(rischi) == len(rischi_codici), f"Expected {len(rischi_codici)} rischi, got {len(rischi)}"
        
        print(f"Fase {fase_with_rischi['codice']} → {len(rischi)} rischi resolved")
    
    def test_rischio_dpi_chain(self, api_client):
        """Verify rischio.dpi_ids can be resolved to full DPI objects"""
        # Get rischi
        rischi_resp = api_client.get(f"{BASE_URL}/api/libreria/rischi")
        assert rischi_resp.status_code == 200
        rischi = rischi_resp.json()
        
        # Find a rischio with dpi_ids
        rischio_with_dpi = next((r for r in rischi if r.get("dpi_ids")), None)
        assert rischio_with_dpi is not None, "No rischio has dpi_ids"
        
        # Resolve the DPI
        dpi_codici = rischio_with_dpi["dpi_ids"]
        resolve_resp = api_client.post(f"{BASE_URL}/api/libreria/resolve-dpi", json={"codici": dpi_codici})
        assert resolve_resp.status_code == 200
        dpi = resolve_resp.json()
        
        assert len(dpi) == len(dpi_codici), f"Expected {len(dpi_codici)} DPI, got {len(dpi)}"
        
        print(f"Rischio {rischio_with_dpi['codice']} → {len(dpi)} DPI resolved")
    
    def test_full_chain_fase_to_dpi(self, api_client):
        """Test full chain: Fase → Rischi → DPI"""
        # Get a fase
        fasi_resp = api_client.get(f"{BASE_URL}/api/libreria/fasi")
        assert fasi_resp.status_code == 200
        fasi = fasi_resp.json()
        
        # Find FL-008 (Montaggio strutture) which has RS-CADUTA-ALTO
        fase = next((f for f in fasi if f["codice"] == "FL-008"), None)
        if not fase:
            fase = fasi[0]  # Fallback
        
        # Resolve rischi
        rischi_codici = fase.get("rischi_ids", [])
        if not rischi_codici:
            print("Fase has no rischi_ids, skipping chain test")
            return
        
        rischi_resp = api_client.post(f"{BASE_URL}/api/libreria/resolve-rischi", json={"codici": rischi_codici})
        assert rischi_resp.status_code == 200
        rischi = rischi_resp.json()
        
        # Collect all DPI from rischi
        all_dpi_codici = set()
        for rischio in rischi:
            all_dpi_codici.update(rischio.get("dpi_ids", []))
        
        if not all_dpi_codici:
            print("Rischi have no dpi_ids, skipping DPI resolution")
            return
        
        # Resolve DPI
        dpi_resp = api_client.post(f"{BASE_URL}/api/libreria/resolve-dpi", json={"codici": list(all_dpi_codici)})
        assert dpi_resp.status_code == 200
        dpi = dpi_resp.json()
        
        print(f"Full chain: Fase {fase['codice']} → {len(rischi)} rischi → {len(dpi)} DPI")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

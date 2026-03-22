"""
Iteration 233 — S3 Motore AI Sicurezza Tests
=============================================
Tests for AI Safety Engine that pre-compiles POS (Piano Operativo di Sicurezza)
by analyzing commessa/istruttoria/preventivo data.

Features tested:
- POST /api/cantieri-sicurezza/{id}/ai-precompila endpoint
- AI precompila saves results to cantiere document
- AI precompila correctly maps fasi from lib_fasi_lavoro
- Rules engine expands rischi from fasi correctly
- Rules engine expands DPI/misure/apprestamenti from rischi
- Gate POS recalculated after AI precompila with blockers
- Soggetti pre-filled from company_settings.figure_aziendali
- AI precompila metadata saved (timestamp, model, sources_used, counts)
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "BccyJvnOyrPXRRYy4GfxR5osuF51RWcYWWnUUoHx434"
USER_ID = "user_6988e9b9316c"
EXISTING_CANTIERE_ID = "cant_3894750ebe93"


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def api_client(auth_headers):
    """Requests session with auth headers."""
    session = requests.Session()
    session.headers.update(auth_headers)
    return session


class TestExistingCantiereWithAIResults:
    """Test existing cantiere that already has AI precompilation results."""
    
    def test_get_existing_cantiere_with_ai_results(self, api_client):
        """Verify existing cantiere has AI precompilation data."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200, f"Failed to get cantiere: {response.text}"
        
        data = response.json()
        assert data["cantiere_id"] == EXISTING_CANTIERE_ID
        
        # Verify AI precompilazione metadata exists
        ai_meta = data.get("ai_precompilazione")
        assert ai_meta is not None, "ai_precompilazione should exist"
        assert "timestamp" in ai_meta
        assert ai_meta["modello"] == "gpt-4o"
        assert "sources_used" in ai_meta
        assert "n_fasi_proposte" in ai_meta
        assert "n_rischi_attivati" in ai_meta
        assert "n_dpi" in ai_meta
        assert "n_misure" in ai_meta
        assert "n_apprestamenti" in ai_meta
        assert "n_domande" in ai_meta
        
        # Verify contesto_operativo
        contesto = ai_meta.get("contesto_operativo", {})
        assert "tipo_cantiere" in contesto
        assert "lavori_in_quota" in contesto
        assert "saldatura_in_opera" in contesto
        
    def test_existing_cantiere_has_fasi_lavoro_selezionate(self, api_client):
        """Verify AI populated fasi_lavoro_selezionate."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        fasi = data.get("fasi_lavoro_selezionate", [])
        assert len(fasi) > 0, "Should have fasi_lavoro_selezionate from AI"
        
        # Verify fase structure
        for fase in fasi:
            assert "fase_codice" in fase
            assert "confidence" in fase
            assert "origin" in fase
            assert "rischi_attivati" in fase
            assert fase["origin"] == "ai"
            
    def test_existing_cantiere_has_dpi_calcolati(self, api_client):
        """Verify AI populated dpi_calcolati."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        dpi = data.get("dpi_calcolati", [])
        assert len(dpi) > 0, "Should have dpi_calcolati from rules engine"
        
        # Verify DPI structure
        for d in dpi:
            assert "codice" in d
            assert "origin" in d
            assert "da_rischi" in d
            
    def test_existing_cantiere_has_misure_calcolate(self, api_client):
        """Verify AI populated misure_calcolate."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        misure = data.get("misure_calcolate", [])
        assert len(misure) > 0, "Should have misure_calcolate from rules engine"
        
    def test_existing_cantiere_has_apprestamenti_calcolati(self, api_client):
        """Verify AI populated apprestamenti_calcolati."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        apprestamenti = data.get("apprestamenti_calcolati", [])
        assert len(apprestamenti) > 0, "Should have apprestamenti_calcolati from rules engine"
        
    def test_existing_cantiere_has_domande_residue(self, api_client):
        """Verify AI populated domande_residue."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        domande = data.get("domande_residue", [])
        assert len(domande) > 0, "Should have domande_residue from AI + rules"
        
        # Verify domanda structure
        for d in domande:
            assert "testo" in d
            assert "impatto" in d
            assert "gate_critical" in d
            assert "stato" in d
            
    def test_existing_cantiere_has_soggetti_prefilled(self, api_client):
        """Verify soggetti were pre-filled from company settings."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        soggetti = data.get("soggetti", [])
        assert len(soggetti) == 14, "Should have all 14 soggetti roles"
        
        # Check that some soggetti are pre-filled
        datore = next((s for s in soggetti if s["ruolo"] == "DATORE_LAVORO"), None)
        assert datore is not None
        # Status should be precompilato if nome is filled
        if datore.get("nome"):
            assert datore["status"] in ["precompilato", "confermato"]


class TestAIPrecompilaEndpoint:
    """Test POST /api/cantieri-sicurezza/{id}/ai-precompila endpoint."""
    
    def test_ai_precompila_returns_expected_fields(self, api_client):
        """Test AI precompila endpoint returns expected response structure."""
        # First create a new cantiere with activity description
        create_response = api_client.post(
            f"{BASE_URL}/api/cantieri-sicurezza",
            json={
                "pre_fill": {
                    "dati_cantiere": {
                        "attivita_cantiere": "Montaggio struttura metallica per capannone industriale con saldature in opera e lavori in quota"
                    }
                }
            }
        )
        assert create_response.status_code == 200, f"Failed to create cantiere: {create_response.text}"
        new_cantiere_id = create_response.json()["cantiere_id"]
        
        try:
            # Call AI precompila with longer timeout (AI can take 10-15 seconds)
            response = api_client.post(
                f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}/ai-precompila",
                timeout=60
            )
            assert response.status_code == 200, f"AI precompila failed: {response.text}"
            
            data = response.json()
            
            # Verify response structure
            assert data.get("success") == True
            assert data.get("cantiere_id") == new_cantiere_id
            assert "ai_precompilazione" in data
            assert "gate_pos_status" in data
            assert "fasi_proposte" in data
            assert "rischi_attivati" in data
            assert "dpi_calcolati" in data
            assert "misure_calcolate" in data
            assert "apprestamenti_calcolati" in data
            assert "domande_residue" in data
            
            # Verify counts are integers
            assert isinstance(data["fasi_proposte"], int)
            assert isinstance(data["rischi_attivati"], int)
            assert isinstance(data["dpi_calcolati"], int)
            
            # Verify ai_precompilazione metadata
            ai_meta = data["ai_precompilazione"]
            assert ai_meta["modello"] == "gpt-4o"
            assert "timestamp" in ai_meta
            assert "sources_used" in ai_meta
            assert "contesto_operativo" in ai_meta
            
        finally:
            # Cleanup: delete test cantiere
            api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}")
            
    def test_ai_precompila_saves_to_cantiere(self, api_client):
        """Test AI precompila saves results to cantiere document."""
        # Create cantiere
        create_response = api_client.post(
            f"{BASE_URL}/api/cantieri-sicurezza",
            json={
                "pre_fill": {
                    "dati_cantiere": {
                        "attivita_cantiere": "Installazione cancelli automatici industriali EN 13241"
                    }
                }
            }
        )
        assert create_response.status_code == 200
        new_cantiere_id = create_response.json()["cantiere_id"]
        
        try:
            # Call AI precompila
            response = api_client.post(
                f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}/ai-precompila",
                timeout=60
            )
            assert response.status_code == 200
            
            # GET cantiere to verify data was saved
            get_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}")
            assert get_response.status_code == 200
            
            cantiere = get_response.json()
            
            # Verify AI results were saved
            assert cantiere.get("ai_precompilazione") is not None
            assert len(cantiere.get("fasi_lavoro_selezionate", [])) > 0
            assert len(cantiere.get("dpi_calcolati", [])) > 0
            assert len(cantiere.get("domande_residue", [])) > 0
            
        finally:
            api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}")
            
    def test_ai_precompila_nonexistent_cantiere(self, api_client):
        """Test AI precompila returns 404 for nonexistent cantiere."""
        response = api_client.post(
            f"{BASE_URL}/api/cantieri-sicurezza/nonexistent_cantiere_id/ai-precompila",
            timeout=30
        )
        assert response.status_code in [400, 404]


class TestRulesEngineExpansion:
    """Test rules engine expansion: fasi → rischi → DPI/misure/apprestamenti."""
    
    def test_fasi_have_rischi_attivati(self, api_client):
        """Verify each selected fase has rischi_attivati populated."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        fasi = data.get("fasi_lavoro_selezionate", [])
        
        # At least some fasi should have rischi
        fasi_with_rischi = [f for f in fasi if len(f.get("rischi_attivati", [])) > 0]
        assert len(fasi_with_rischi) > 0, "At least some fasi should have rischi_attivati"
        
        # Verify rischi structure
        for fase in fasi_with_rischi:
            for rischio in fase["rischi_attivati"]:
                assert "rischio_codice" in rischio
                assert "confidence" in rischio
                assert "origin" in rischio
                
    def test_dpi_linked_to_rischi(self, api_client):
        """Verify DPI are linked to rischi via da_rischi field."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        dpi = data.get("dpi_calcolati", [])
        
        # Each DPI should have da_rischi
        for d in dpi:
            assert "da_rischi" in d
            assert isinstance(d["da_rischi"], list)
            
    def test_misure_linked_to_rischi(self, api_client):
        """Verify misure are linked to rischi via da_rischi field."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        misure = data.get("misure_calcolate", [])
        
        for m in misure:
            assert "da_rischi" in m
            assert isinstance(m["da_rischi"], list)
            
    def test_apprestamenti_linked_to_rischi(self, api_client):
        """Verify apprestamenti are linked to rischi via da_rischi field."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        apprestamenti = data.get("apprestamenti_calcolati", [])
        
        for a in apprestamenti:
            assert "da_rischi" in a
            assert isinstance(a["da_rischi"], list)


class TestGatePOSAfterAIPrecompila:
    """Test Gate POS recalculation after AI precompila."""
    
    def test_gate_pos_has_blockers_for_critical_domande(self, api_client):
        """Verify gate POS includes blockers for gate_critical domande."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}/gate")
        assert response.status_code == 200
        
        gate = response.json()
        assert "completezza_percentuale" in gate
        assert "campi_mancanti" in gate
        assert "blockers" in gate
        assert "pronto_per_generazione" in gate
        
        # If there are open gate_critical domande, blockers should be populated
        cantiere_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        cantiere = cantiere_response.json()
        
        open_critical = [d for d in cantiere.get("domande_residue", []) 
                        if d.get("gate_critical") and d.get("stato") == "aperta"]
        
        if len(open_critical) > 0:
            assert len(gate["blockers"]) > 0, "Should have blockers for open critical domande"
            assert gate["pronto_per_generazione"] == False
            
    def test_gate_pos_completeness_percentage(self, api_client):
        """Verify gate POS completeness percentage is calculated."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}/gate")
        assert response.status_code == 200
        
        gate = response.json()
        pct = gate["completezza_percentuale"]
        assert isinstance(pct, int)
        assert 0 <= pct <= 100


class TestSoggettiPrefillFromCompanySettings:
    """Test soggetti pre-fill from company_settings.figure_aziendali."""
    
    def test_company_settings_has_figure_aziendali(self, api_client):
        """Verify company settings has figure_aziendali."""
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 200
        
        data = response.json()
        figure = data.get("figure_aziendali", [])
        assert len(figure) > 0, "Company should have figure_aziendali"
        
        # Verify structure
        for fig in figure:
            assert "ruolo" in fig
            assert "nome" in fig
            
    def test_new_cantiere_prefills_soggetti_from_company(self, api_client):
        """Test new cantiere pre-fills soggetti from company figure_aziendali."""
        # Get company settings first
        company_response = api_client.get(f"{BASE_URL}/api/company/settings")
        company = company_response.json()
        figure_aziendali = company.get("figure_aziendali", [])
        
        # Create new cantiere
        create_response = api_client.post(
            f"{BASE_URL}/api/cantieri-sicurezza",
            json={}
        )
        assert create_response.status_code == 200
        new_cantiere_id = create_response.json()["cantiere_id"]
        
        try:
            # Get cantiere
            get_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}")
            cantiere = get_response.json()
            soggetti = cantiere.get("soggetti", [])
            
            # Verify figure_aziendali were pre-filled
            for fig in figure_aziendali:
                if fig.get("nome"):
                    soggetto = next((s for s in soggetti if s["ruolo"] == fig["ruolo"]), None)
                    assert soggetto is not None, f"Soggetto {fig['ruolo']} should exist"
                    assert soggetto["nome"] == fig["nome"], f"Soggetto {fig['ruolo']} nome should match"
                    assert soggetto["status"] == "precompilato"
                    
        finally:
            api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{new_cantiere_id}")


class TestLibraryAPIs:
    """Test library APIs used by AI engine."""
    
    def test_get_fasi_lavoro(self, api_client):
        """Test GET /api/libreria/fasi returns fasi."""
        response = api_client.get(f"{BASE_URL}/api/libreria/fasi")
        assert response.status_code == 200
        
        fasi = response.json()
        assert len(fasi) >= 11, "Should have at least 11 fasi"
        
        # Verify structure
        for fase in fasi:
            assert "codice" in fase
            assert "nome" in fase
            assert "rischi_ids" in fase
            
    def test_get_rischi_sicurezza(self, api_client):
        """Test GET /api/libreria/rischi returns rischi."""
        response = api_client.get(f"{BASE_URL}/api/libreria/rischi")
        assert response.status_code == 200
        
        rischi = response.json()
        assert len(rischi) >= 18, "Should have at least 18 rischi"
        
        # Verify structure
        for rischio in rischi:
            assert "codice" in rischio
            assert "nome" in rischio
            assert "dpi_ids" in rischio
            assert "gate_critical" in rischio
            
    def test_get_dpi_misure(self, api_client):
        """Test GET /api/libreria/dpi-misure returns DPI/misure/apprestamenti."""
        response = api_client.get(f"{BASE_URL}/api/libreria/dpi-misure")
        assert response.status_code == 200
        
        items = response.json()
        assert len(items) >= 31, "Should have at least 31 items"
        
        # Verify types
        dpi = [i for i in items if i["tipo"] == "dpi"]
        misure = [i for i in items if i["tipo"] == "misura"]
        apprestamenti = [i for i in items if i["tipo"] == "apprestamento"]
        
        assert len(dpi) >= 12
        assert len(misure) >= 11
        assert len(apprestamenti) >= 8


class TestAIPrecompilaMetadata:
    """Test AI precompila metadata structure."""
    
    def test_ai_metadata_has_timestamp(self, api_client):
        """Verify AI metadata has timestamp."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        ai_meta = response.json().get("ai_precompilazione", {})
        assert "timestamp" in ai_meta
        # Timestamp should be ISO format
        assert "T" in ai_meta["timestamp"]
        
    def test_ai_metadata_has_model(self, api_client):
        """Verify AI metadata has model name."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        ai_meta = response.json().get("ai_precompilazione", {})
        assert ai_meta.get("modello") == "gpt-4o"
        
    def test_ai_metadata_has_sources_used(self, api_client):
        """Verify AI metadata has sources_used."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        ai_meta = response.json().get("ai_precompilazione", {})
        sources = ai_meta.get("sources_used", [])
        assert isinstance(sources, list)
        
    def test_ai_metadata_has_counts(self, api_client):
        """Verify AI metadata has all count fields."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        ai_meta = response.json().get("ai_precompilazione", {})
        assert "n_fasi_proposte" in ai_meta
        assert "n_rischi_attivati" in ai_meta
        assert "n_dpi" in ai_meta
        assert "n_misure" in ai_meta
        assert "n_apprestamenti" in ai_meta
        assert "n_domande" in ai_meta
        
    def test_ai_metadata_has_contesto_operativo(self, api_client):
        """Verify AI metadata has contesto_operativo."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{EXISTING_CANTIERE_ID}")
        assert response.status_code == 200
        
        ai_meta = response.json().get("ai_precompilazione", {})
        contesto = ai_meta.get("contesto_operativo", {})
        
        # Verify expected fields
        assert "tipo_cantiere" in contesto
        assert "lavori_in_quota" in contesto
        assert "saldatura_in_opera" in contesto
        assert "mezzi_sollevamento" in contesto


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

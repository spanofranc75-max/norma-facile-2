"""
Iteration 232 — S2.5 Modello Soggetti & Ruoli Testing
=====================================================
Tests for figure_aziendali in company settings and soggetti pre-fill in cantieri.

Key features:
1. PUT /api/company/settings saves figure_aziendali array correctly (critical bug fix)
2. GET /api/company/settings returns figure_aziendali persisted data
3. POST /api/cantieri-sicurezza creates cantiere with pre-filled soggetti from company figure_aziendali
4. PUT /api/cantieri-sicurezza/{id} updates soggetti correctly
5. GET /api/cantieri-sicurezza/{id} returns soggetti with all roles (14 total)
6. GET /api/ruoli-disponibili returns all available roles
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "BccyJvnOyrPXRRYy4GfxR5osuF51RWcYWWnUUoHx434"

# Expected 14 roles from ALL_RUOLI
EXPECTED_RUOLI = [
    # Azienda (5)
    {"ruolo": "DATORE_LAVORO", "label": "Datore di Lavoro", "categoria": "azienda", "obbligatorio": True},
    {"ruolo": "RSPP", "label": "RSPP", "categoria": "azienda", "obbligatorio": True},
    {"ruolo": "MEDICO_COMPETENTE", "label": "Medico Competente", "categoria": "azienda", "obbligatorio": True},
    {"ruolo": "PREPOSTO_CANTIERE", "label": "Preposto di Cantiere", "categoria": "azienda", "obbligatorio": False},
    {"ruolo": "DIRETTORE_TECNICO", "label": "Direttore Tecnico", "categoria": "azienda", "obbligatorio": False},
    # Committente (6)
    {"ruolo": "COMMITTENTE", "label": "Committente", "categoria": "committente", "obbligatorio": True},
    {"ruolo": "REFERENTE_COMMITTENTE", "label": "Referente Committente", "categoria": "committente", "obbligatorio": False},
    {"ruolo": "RESPONSABILE_LAVORI", "label": "Responsabile dei Lavori", "categoria": "committente", "obbligatorio": False},
    {"ruolo": "DIRETTORE_LAVORI", "label": "Direttore dei Lavori", "categoria": "committente", "obbligatorio": False},
    {"ruolo": "CSP", "label": "Coordinatore Sicurezza Progettazione", "categoria": "committente", "obbligatorio": False},
    {"ruolo": "CSE", "label": "Coordinatore Sicurezza Esecuzione", "categoria": "committente", "obbligatorio": False},
    # Tecnico (3)
    {"ruolo": "PROGETTISTA", "label": "Progettista", "categoria": "tecnico", "obbligatorio": False},
    {"ruolo": "STRUTTURISTA", "label": "Ingegnere Strutturista", "categoria": "tecnico", "obbligatorio": False},
    {"ruolo": "COLLAUDATORE", "label": "Collaudatore", "categoria": "tecnico", "obbligatorio": False},
]


@pytest.fixture
def api_client():
    """Shared requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


class TestRuoliDisponibili:
    """Test GET /api/ruoli-disponibili endpoint."""
    
    def test_get_ruoli_disponibili_returns_14_roles(self, api_client):
        """GET /api/ruoli-disponibili should return all 14 roles."""
        response = api_client.get(f"{BASE_URL}/api/ruoli-disponibili")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 14, f"Expected 14 roles, got {len(data)}"
        
        # Verify all expected roles are present
        ruoli_codes = [r["ruolo"] for r in data]
        for expected in EXPECTED_RUOLI:
            assert expected["ruolo"] in ruoli_codes, f"Missing role: {expected['ruolo']}"
        
        print(f"✓ GET /api/ruoli-disponibili returns {len(data)} roles")
    
    def test_ruoli_have_correct_structure(self, api_client):
        """Each role should have ruolo, label, categoria, obbligatorio fields."""
        response = api_client.get(f"{BASE_URL}/api/ruoli-disponibili")
        assert response.status_code == 200
        
        data = response.json()
        for role in data:
            assert "ruolo" in role, f"Missing 'ruolo' field in {role}"
            assert "label" in role, f"Missing 'label' field in {role}"
            assert "categoria" in role, f"Missing 'categoria' field in {role}"
            assert "obbligatorio" in role, f"Missing 'obbligatorio' field in {role}"
        
        print("✓ All roles have correct structure (ruolo, label, categoria, obbligatorio)")
    
    def test_ruoli_categories_distribution(self, api_client):
        """Verify correct distribution: 5 azienda, 6 committente, 3 tecnico."""
        response = api_client.get(f"{BASE_URL}/api/ruoli-disponibili")
        assert response.status_code == 200
        
        data = response.json()
        azienda = [r for r in data if r["categoria"] == "azienda"]
        committente = [r for r in data if r["categoria"] == "committente"]
        tecnico = [r for r in data if r["categoria"] == "tecnico"]
        
        assert len(azienda) == 5, f"Expected 5 azienda roles, got {len(azienda)}"
        assert len(committente) == 6, f"Expected 6 committente roles, got {len(committente)}"
        assert len(tecnico) == 3, f"Expected 3 tecnico roles, got {len(tecnico)}"
        
        print(f"✓ Role categories: azienda={len(azienda)}, committente={len(committente)}, tecnico={len(tecnico)}")


class TestCompanySettingsFigureAziendali:
    """Test figure_aziendali in company settings (critical bug fix)."""
    
    def test_put_company_settings_saves_figure_aziendali(self, api_client):
        """PUT /api/company/settings should save figure_aziendali array correctly."""
        # Prepare test data
        test_figure = [
            {"ruolo": "DATORE_LAVORO", "label": "Datore di Lavoro", "nome": "Mario Rossi", "telefono": "0512345678", "email": "mario@test.it"},
            {"ruolo": "RSPP", "label": "RSPP", "nome": "Luigi Verdi", "telefono": "0519876543", "email": "luigi@test.it"},
            {"ruolo": "MEDICO_COMPETENTE", "label": "Medico Competente", "nome": "Dr. Bianchi", "telefono": "0511112222", "email": "drbianchi@test.it"},
        ]
        
        payload = {
            "figure_aziendali": test_figure
        }
        
        response = api_client.put(f"{BASE_URL}/api/company/settings", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "figure_aziendali" in data, "Response should contain figure_aziendali"
        assert len(data["figure_aziendali"]) == 3, f"Expected 3 figures, got {len(data['figure_aziendali'])}"
        
        # Verify data was saved correctly
        saved_datore = next((f for f in data["figure_aziendali"] if f["ruolo"] == "DATORE_LAVORO"), None)
        assert saved_datore is not None, "DATORE_LAVORO should be saved"
        assert saved_datore["nome"] == "Mario Rossi", f"Expected 'Mario Rossi', got '{saved_datore.get('nome')}'"
        
        print("✓ PUT /api/company/settings saves figure_aziendali correctly")
    
    def test_get_company_settings_returns_figure_aziendali(self, api_client):
        """GET /api/company/settings should return persisted figure_aziendali."""
        # First save some data
        test_figure = [
            {"ruolo": "DATORE_LAVORO", "label": "Datore di Lavoro", "nome": "Test Datore", "telefono": "123", "email": "test@test.it"},
        ]
        api_client.put(f"{BASE_URL}/api/company/settings", json={"figure_aziendali": test_figure})
        
        # Now GET and verify
        response = api_client.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "figure_aziendali" in data, "Response should contain figure_aziendali"
        assert isinstance(data["figure_aziendali"], list), "figure_aziendali should be a list"
        
        # Verify persisted data
        if len(data["figure_aziendali"]) > 0:
            datore = next((f for f in data["figure_aziendali"] if f["ruolo"] == "DATORE_LAVORO"), None)
            if datore:
                assert datore["nome"] == "Test Datore", f"Expected 'Test Datore', got '{datore.get('nome')}'"
        
        print(f"✓ GET /api/company/settings returns figure_aziendali with {len(data['figure_aziendali'])} entries")
    
    def test_update_figure_aziendali_preserves_other_settings(self, api_client):
        """Updating figure_aziendali should not affect other company settings."""
        # First set some other settings
        api_client.put(f"{BASE_URL}/api/company/settings", json={
            "business_name": "Test Company S.r.l.",
            "partita_iva": "12345678901"
        })
        
        # Now update only figure_aziendali
        test_figure = [
            {"ruolo": "RSPP", "label": "RSPP", "nome": "New RSPP", "telefono": "999", "email": "rspp@test.it"},
        ]
        response = api_client.put(f"{BASE_URL}/api/company/settings", json={"figure_aziendali": test_figure})
        assert response.status_code == 200
        
        data = response.json()
        # Verify other settings are preserved
        assert data.get("business_name") == "Test Company S.r.l.", "business_name should be preserved"
        assert data.get("partita_iva") == "12345678901", "partita_iva should be preserved"
        
        print("✓ Updating figure_aziendali preserves other company settings")


class TestCantierePreFillFromCompanySettings:
    """Test that cantiere soggetti are pre-filled from company figure_aziendali."""
    
    def test_create_cantiere_prefills_soggetti_from_company(self, api_client):
        """POST /api/cantieri-sicurezza should pre-fill soggetti from company figure_aziendali."""
        # First set company figure_aziendali
        test_figure = [
            {"ruolo": "DATORE_LAVORO", "label": "Datore di Lavoro", "nome": "Company Datore", "telefono": "111", "email": "datore@company.it"},
            {"ruolo": "RSPP", "label": "RSPP", "nome": "Company RSPP", "telefono": "222", "email": "rspp@company.it"},
            {"ruolo": "MEDICO_COMPETENTE", "label": "Medico Competente", "nome": "Dr. Company", "telefono": "333", "email": "medico@company.it"},
        ]
        api_client.put(f"{BASE_URL}/api/company/settings", json={"figure_aziendali": test_figure})
        
        # Create new cantiere
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        assert cantiere_id is not None, "Response should contain cantiere_id"
        
        # Verify soggetti are pre-filled
        soggetti = data.get("soggetti", [])
        assert len(soggetti) == 14, f"Expected 14 soggetti, got {len(soggetti)}"
        
        # Check DATORE_LAVORO is pre-filled
        datore = next((s for s in soggetti if s["ruolo"] == "DATORE_LAVORO"), None)
        assert datore is not None, "DATORE_LAVORO should exist in soggetti"
        assert datore["nome"] == "Company Datore", f"Expected 'Company Datore', got '{datore.get('nome')}'"
        assert datore["status"] == "precompilato", f"Expected status 'precompilato', got '{datore.get('status')}'"
        
        # Check RSPP is pre-filled
        rspp = next((s for s in soggetti if s["ruolo"] == "RSPP"), None)
        assert rspp is not None, "RSPP should exist in soggetti"
        assert rspp["nome"] == "Company RSPP", f"Expected 'Company RSPP', got '{rspp.get('nome')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ POST /api/cantieri-sicurezza pre-fills soggetti from company figure_aziendali")
    
    def test_cantiere_soggetti_have_all_14_roles(self, api_client):
        """New cantiere should have all 14 soggetti roles."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        soggetti = data.get("soggetti", [])
        
        assert len(soggetti) == 14, f"Expected 14 soggetti, got {len(soggetti)}"
        
        # Verify all expected roles are present
        soggetti_ruoli = [s["ruolo"] for s in soggetti]
        for expected in EXPECTED_RUOLI:
            assert expected["ruolo"] in soggetti_ruoli, f"Missing soggetto role: {expected['ruolo']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ New cantiere has all 14 soggetti roles")
    
    def test_cantiere_soggetti_have_correct_structure(self, api_client):
        """Each soggetto should have required fields."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        soggetti = data.get("soggetti", [])
        
        required_fields = ["ruolo", "label", "categoria", "obbligatorio", "status", "nome", "telefono", "email"]
        for soggetto in soggetti:
            for field in required_fields:
                assert field in soggetto, f"Missing field '{field}' in soggetto {soggetto.get('ruolo')}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ All soggetti have correct structure")


class TestCantiereUpdateSoggetti:
    """Test updating soggetti in cantiere."""
    
    def test_put_cantiere_updates_soggetti(self, api_client):
        """PUT /api/cantieri-sicurezza/{id} should update soggetti correctly."""
        # Create cantiere
        create_response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_response.status_code == 200
        cantiere_id = create_response.json().get("cantiere_id")
        
        # Get current soggetti and modify
        get_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        soggetti = get_response.json().get("soggetti", [])
        
        # Update COMMITTENTE
        for s in soggetti:
            if s["ruolo"] == "COMMITTENTE":
                s["nome"] = "Updated Committente S.p.A."
                s["telefono"] = "0512223344"
                s["email"] = "committente@updated.it"
                s["status"] = "confermato"
        
        # PUT update
        update_response = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json={"soggetti": soggetti})
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify update
        updated_data = update_response.json()
        updated_committente = next((s for s in updated_data.get("soggetti", []) if s["ruolo"] == "COMMITTENTE"), None)
        assert updated_committente is not None, "COMMITTENTE should exist"
        assert updated_committente["nome"] == "Updated Committente S.p.A.", f"Expected 'Updated Committente S.p.A.', got '{updated_committente.get('nome')}'"
        assert updated_committente["status"] == "confermato", f"Expected status 'confermato', got '{updated_committente.get('status')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ PUT /api/cantieri-sicurezza/{id} updates soggetti correctly")
    
    def test_get_cantiere_returns_updated_soggetti(self, api_client):
        """GET /api/cantieri-sicurezza/{id} should return updated soggetti."""
        # Create and update cantiere
        create_response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        cantiere_id = create_response.json().get("cantiere_id")
        
        # Get and modify soggetti
        get_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        soggetti = get_response.json().get("soggetti", [])
        
        for s in soggetti:
            if s["ruolo"] == "CSE":
                s["nome"] = "Ing. CSE Test"
                s["email"] = "cse@test.it"
        
        api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json={"soggetti": soggetti})
        
        # GET and verify persistence
        verify_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert verify_response.status_code == 200
        
        verified_soggetti = verify_response.json().get("soggetti", [])
        cse = next((s for s in verified_soggetti if s["ruolo"] == "CSE"), None)
        assert cse is not None, "CSE should exist"
        assert cse["nome"] == "Ing. CSE Test", f"Expected 'Ing. CSE Test', got '{cse.get('nome')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ GET /api/cantieri-sicurezza/{id} returns persisted soggetti updates")


class TestSoggettiCategories:
    """Test soggetti are correctly categorized."""
    
    def test_soggetti_categories_in_cantiere(self, api_client):
        """Soggetti should be correctly categorized: azienda, committente, tecnico."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        soggetti = data.get("soggetti", [])
        
        azienda = [s for s in soggetti if s["categoria"] == "azienda"]
        committente = [s for s in soggetti if s["categoria"] == "committente"]
        tecnico = [s for s in soggetti if s["categoria"] == "tecnico"]
        
        assert len(azienda) == 5, f"Expected 5 azienda soggetti, got {len(azienda)}"
        assert len(committente) == 6, f"Expected 6 committente soggetti, got {len(committente)}"
        assert len(tecnico) == 3, f"Expected 3 tecnico soggetti, got {len(tecnico)}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"✓ Soggetti categories: azienda={len(azienda)}, committente={len(committente)}, tecnico={len(tecnico)}")
    
    def test_obbligatorio_soggetti(self, api_client):
        """Verify obbligatorio flag on soggetti."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        soggetti = data.get("soggetti", [])
        
        # Expected obbligatorio: DATORE_LAVORO, RSPP, MEDICO_COMPETENTE, COMMITTENTE
        obbligatori = [s for s in soggetti if s.get("obbligatorio") == True]
        obbligatori_ruoli = [s["ruolo"] for s in obbligatori]
        
        assert "DATORE_LAVORO" in obbligatori_ruoli, "DATORE_LAVORO should be obbligatorio"
        assert "RSPP" in obbligatori_ruoli, "RSPP should be obbligatorio"
        assert "MEDICO_COMPETENTE" in obbligatori_ruoli, "MEDICO_COMPETENTE should be obbligatorio"
        assert "COMMITTENTE" in obbligatori_ruoli, "COMMITTENTE should be obbligatorio"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"✓ Obbligatorio soggetti: {obbligatori_ruoli}")


class TestGatePOSWithSoggetti:
    """Test Gate POS includes soggetti validation."""
    
    def test_gate_pos_reports_missing_obbligatorio_soggetti(self, api_client):
        """Gate POS should report missing obbligatorio soggetti."""
        # Create cantiere without pre-filled company settings
        # First clear company figure_aziendali
        api_client.put(f"{BASE_URL}/api/company/settings", json={"figure_aziendali": []})
        
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        
        # Get gate status
        gate_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert gate_response.status_code == 200
        
        gate = gate_response.json()
        campi_mancanti = gate.get("campi_mancanti", [])
        
        # Should report missing soggetti
        missing_soggetti = [c for c in campi_mancanti if "Soggetto" in c]
        assert len(missing_soggetti) > 0, "Gate should report missing obbligatorio soggetti"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print(f"✓ Gate POS reports missing soggetti: {missing_soggetti}")
    
    def test_gate_pos_improves_with_filled_soggetti(self, api_client):
        """Gate POS completeness should improve when soggetti are filled."""
        # Set company figure_aziendali
        test_figure = [
            {"ruolo": "DATORE_LAVORO", "label": "Datore di Lavoro", "nome": "Test Datore", "telefono": "111", "email": "d@t.it"},
            {"ruolo": "RSPP", "label": "RSPP", "nome": "Test RSPP", "telefono": "222", "email": "r@t.it"},
            {"ruolo": "MEDICO_COMPETENTE", "label": "Medico Competente", "nome": "Test Medico", "telefono": "333", "email": "m@t.it"},
        ]
        api_client.put(f"{BASE_URL}/api/company/settings", json={"figure_aziendali": test_figure})
        
        # Create cantiere (should have pre-filled soggetti)
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        cantiere_id = response.json().get("cantiere_id")
        
        # Get and update soggetti to add COMMITTENTE
        get_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        soggetti = get_response.json().get("soggetti", [])
        
        for s in soggetti:
            if s["ruolo"] == "COMMITTENTE":
                s["nome"] = "Test Committente"
                s["status"] = "confermato"
        
        api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json={"soggetti": soggetti})
        
        # Get gate status
        gate_response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        gate = gate_response.json()
        
        # Check that soggetti-related missing fields are reduced
        campi_mancanti = gate.get("campi_mancanti", [])
        missing_soggetti = [c for c in campi_mancanti if "Soggetto" in c]
        
        # With all 4 obbligatorio soggetti filled, there should be no missing soggetti
        assert len(missing_soggetti) == 0, f"Expected no missing soggetti, got: {missing_soggetti}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ Gate POS completeness improves with filled soggetti")


class TestResponsabileNomeMapping:
    """Test that responsabile_nome from company settings maps to DATORE_LAVORO."""
    
    def test_responsabile_nome_maps_to_datore_lavoro(self, api_client):
        """Company responsabile_nome should map to DATORE_LAVORO in cantiere."""
        # Set responsabile_nome in company settings
        api_client.put(f"{BASE_URL}/api/company/settings", json={
            "responsabile_nome": "Responsabile Test",
            "figure_aziendali": []  # Clear figure_aziendali to test responsabile_nome mapping
        })
        
        # Create cantiere
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        
        data = response.json()
        cantiere_id = data.get("cantiere_id")
        soggetti = data.get("soggetti", [])
        
        # Check DATORE_LAVORO is pre-filled from responsabile_nome
        datore = next((s for s in soggetti if s["ruolo"] == "DATORE_LAVORO"), None)
        assert datore is not None, "DATORE_LAVORO should exist"
        assert datore["nome"] == "Responsabile Test", f"Expected 'Responsabile Test', got '{datore.get('nome')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        
        print("✓ responsabile_nome maps to DATORE_LAVORO in cantiere")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

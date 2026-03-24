"""
Iteration 230 — Safety Branch MVP (Ramo Sicurezza) Tests
=========================================================
Tests for:
  - cantieri_sicurezza CRUD (Safety Site Sheets)
  - libreria_rischi (Risk Library with seed data)
  - gate_pos completeness check
  - Multi-step form data persistence

D.Lgs. 81/2008 compliance for POS (Piano Operativo di Sicurezza)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://production-debug-12.preview.emergentagent.com')
SESSION_TOKEN = "test_perizia_205a45704b22"
USER_ID = "user_perizia_de75ff42"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestLibreriaRischi:
    """Tests for Risk Library (libreria_rischi) endpoints."""

    def test_seed_libreria_rischi_idempotent(self, api_client):
        """POST /api/libreria-rischi/seed — idempotent seed of risk library."""
        # First call
        response = api_client.post(f"{BASE_URL}/api/libreria-rischi/seed")
        assert response.status_code == 200
        data = response.json()
        assert "seeded" in data
        assert "count" in data
        # Should have 20 items (10 DPI + 10 fasi_lavoro)
        assert data["count"] == 20
        
        # Second call should be idempotent (seeded=False)
        response2 = api_client.post(f"{BASE_URL}/api/libreria-rischi/seed")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["seeded"] == False
        assert data2["count"] == 20

    def test_get_libreria_rischi_all(self, api_client):
        """GET /api/libreria-rischi — returns all risk library entries."""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 20
        
        # Verify structure of entries
        for entry in data:
            assert "risk_id" in entry
            assert "user_id" in entry
            assert "tipo" in entry
            assert entry["tipo"] in ["dpi", "fase_lavoro"]
            assert "codice" in entry
            assert "nome" in entry
            assert "attivo" in entry
            assert entry["attivo"] == True

    def test_get_libreria_rischi_filter_dpi(self, api_client):
        """GET /api/libreria-rischi?tipo=dpi — filters by tipo DPI."""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi?tipo=dpi")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10
        
        # All entries should be DPI
        for entry in data:
            assert entry["tipo"] == "dpi"
            assert entry["codice"].startswith("DPI-")
            assert "rif_normativo" in entry

    def test_get_libreria_rischi_filter_fase_lavoro(self, api_client):
        """GET /api/libreria-rischi?tipo=fase_lavoro — filters by tipo fase_lavoro."""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi?tipo=fase_lavoro")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10
        
        # All entries should be fasi_lavoro
        for entry in data:
            assert entry["tipo"] == "fase_lavoro"
            assert entry["codice"].startswith("FL-")
            assert "categoria" in entry
            assert "applicabile_a" in entry
            assert "rischi_associati" in entry
            assert "misure_prevenzione" in entry
            assert "dpi_richiesti" in entry

    def test_get_fasi_per_normativa_en1090(self, api_client):
        """GET /api/libreria-rischi/fasi/EN_1090 — phases for EN_1090 normativa."""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi/fasi/EN_1090")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned phases should be applicable to EN_1090
        for fase in data:
            assert "EN_1090" in fase["applicabile_a"]
            assert fase["tipo"] == "fase_lavoro"

    def test_get_fasi_per_normativa_en13241(self, api_client):
        """GET /api/libreria-rischi/fasi/EN_13241 — phases for EN_13241 normativa."""
        response = api_client.get(f"{BASE_URL}/api/libreria-rischi/fasi/EN_13241")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned phases should be applicable to EN_13241
        for fase in data:
            assert "EN_13241" in fase["applicabile_a"]


class TestCantieriSicurezzaCRUD:
    """Tests for Cantieri Sicurezza (Safety Site Sheets) CRUD operations."""

    def test_create_cantiere_sicurezza(self, api_client):
        """POST /api/cantieri-sicurezza — creates a new cantiere_sicurezza."""
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "cantiere_id" in data
        assert data["cantiere_id"].startswith("cant_")
        assert data["user_id"] == USER_ID
        assert data["status"] == "bozza"
        
        # Verify default data structures
        assert "dati_cantiere" in data
        assert "soggetti_riferimento" in data
        assert "lavoratori_coinvolti" in data
        assert isinstance(data["lavoratori_coinvolti"], list)
        assert "dpi_presenti" in data
        assert len(data["dpi_presenti"]) == 8  # Default DPI
        assert "macchine_attrezzature" in data
        assert len(data["macchine_attrezzature"]) == 8  # Default machines
        assert "numeri_utili" in data
        assert len(data["numeri_utili"]) == 4  # Emergency numbers
        
        # Verify gate_pos_status
        assert "gate_pos_status" in data
        assert data["gate_pos_status"]["completezza_percentuale"] == 0
        assert data["gate_pos_status"]["pronto_per_generazione"] == False
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{data['cantiere_id']}")

    def test_create_cantiere_with_prefill(self, api_client):
        """POST /api/cantieri-sicurezza — creates with pre_fill data."""
        pre_fill = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Test 123",
                "citta_cantiere": "Milano",
                "data_inizio_lavori": "2026-05-01"
            },
            "soggetti_riferimento": {
                "committente": "Test Committente SRL"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={"pre_fill": pre_fill})
        assert response.status_code == 200
        data = response.json()
        
        # Verify pre-filled data
        assert data["dati_cantiere"]["indirizzo_cantiere"] == "Via Test 123"
        assert data["dati_cantiere"]["citta_cantiere"] == "Milano"
        assert data["soggetti_riferimento"]["committente"] == "Test Committente SRL"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{data['cantiere_id']}")

    def test_list_cantieri_sicurezza(self, api_client):
        """GET /api/cantieri-sicurezza — lists all cantieri for the user."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Should have at least the existing test cantiere
        assert len(data) >= 1
        
        # Verify structure of each cantiere
        for cantiere in data:
            assert "cantiere_id" in cantiere
            assert "user_id" in cantiere
            assert cantiere["user_id"] == USER_ID
            assert "status" in cantiere
            assert "dati_cantiere" in cantiere
            assert "gate_pos_status" in cantiere

    def test_get_single_cantiere(self, api_client):
        """GET /api/cantieri-sicurezza/{cantiere_id} — gets a single cantiere."""
        # Use existing test cantiere
        cantiere_id = "cant_9716558dc2ba"
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["cantiere_id"] == cantiere_id
        assert data["user_id"] == USER_ID
        assert "dati_cantiere" in data
        assert "soggetti_riferimento" in data
        assert "gate_pos_status" in data

    def test_get_nonexistent_cantiere_returns_404(self, api_client):
        """GET /api/cantieri-sicurezza/{cantiere_id} — returns 404 for non-existent."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/cant_nonexistent123")
        assert response.status_code == 404

    def test_update_cantiere_partial(self, api_client):
        """PUT /api/cantieri-sicurezza/{cantiere_id} — updates a cantiere (partial update)."""
        # Create a test cantiere
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Update with partial data
        update_data = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Aggiornata 456",
                "citta_cantiere": "Roma",
                "data_inizio_lavori": "2026-06-01"
            },
            "soggetti_riferimento": {
                "committente": "Nuovo Committente"
            },
            "lavoratori_coinvolti": [
                {"nominativo": "Mario Rossi", "mansione": "Operaio", "addetto_primo_soccorso": True, "addetto_antincendio": False}
            ],
            "fasi_lavoro_selezionate": [
                {"fase_id": "FL-001", "nome_fase": "Taglio e preparazione lamiere/profili"}
            ]
        }
        
        response = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        
        # Verify updates
        assert data["dati_cantiere"]["indirizzo_cantiere"] == "Via Aggiornata 456"
        assert data["dati_cantiere"]["citta_cantiere"] == "Roma"
        assert data["soggetti_riferimento"]["committente"] == "Nuovo Committente"
        assert len(data["lavoratori_coinvolti"]) == 1
        assert data["lavoratori_coinvolti"][0]["nominativo"] == "Mario Rossi"
        assert len(data["fasi_lavoro_selezionate"]) == 1
        
        # Verify gate_pos_status was recalculated
        assert "gate_pos_status" in data
        assert data["gate_pos_status"]["completezza_percentuale"] > 0
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")

    def test_update_nonexistent_cantiere_returns_404(self, api_client):
        """PUT /api/cantieri-sicurezza/{cantiere_id} — returns 404 for non-existent."""
        response = api_client.put(
            f"{BASE_URL}/api/cantieri-sicurezza/cant_nonexistent123",
            json={"dati_cantiere": {"indirizzo_cantiere": "Test"}}
        )
        assert response.status_code == 404

    def test_update_empty_body_returns_400(self, api_client):
        """PUT /api/cantieri-sicurezza/{cantiere_id} — returns 400 for empty update."""
        cantiere_id = "cant_9716558dc2ba"
        response = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json={})
        assert response.status_code == 400

    def test_delete_cantiere(self, api_client):
        """DELETE /api/cantieri-sicurezza/{cantiere_id} — deletes a cantiere."""
        # Create a test cantiere
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == True
        
        # Verify it's gone
        get_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_cantiere_returns_404(self, api_client):
        """DELETE /api/cantieri-sicurezza/{cantiere_id} — returns 404 for non-existent."""
        response = api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/cant_nonexistent123")
        assert response.status_code == 404


class TestGatePOS:
    """Tests for Gate POS (completeness check) functionality."""

    def test_gate_pos_status_endpoint(self, api_client):
        """GET /api/cantieri-sicurezza/{cantiere_id}/gate — returns gate_pos status."""
        cantiere_id = "cant_9716558dc2ba"
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert response.status_code == 200
        data = response.json()
        
        assert "completezza_percentuale" in data
        assert "campi_mancanti" in data
        assert "pronto_per_generazione" in data
        assert isinstance(data["completezza_percentuale"], int)
        assert isinstance(data["campi_mancanti"], list)
        assert isinstance(data["pronto_per_generazione"], bool)

    def test_gate_pos_nonexistent_cantiere_returns_404(self, api_client):
        """GET /api/cantieri-sicurezza/{cantiere_id}/gate — returns 404 for non-existent."""
        response = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/cant_nonexistent123/gate")
        assert response.status_code == 404

    def test_gate_pos_completeness_calculation(self, api_client):
        """Verify gate_pos completeness calculation with all required fields."""
        # Create a cantiere with all required fields
        pre_fill = {
            "dati_cantiere": {
                "indirizzo_cantiere": "Via Completa 1",
                "citta_cantiere": "Bologna",
                "data_inizio_lavori": "2026-07-01"
            },
            "soggetti_riferimento": {
                "committente": "Committente Completo SRL"
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={"pre_fill": pre_fill})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Add lavoratori and fasi_lavoro
        update_data = {
            "lavoratori_coinvolti": [
                {"nominativo": "Test Worker", "mansione": "Operaio", "addetto_primo_soccorso": True, "addetto_antincendio": True}
            ],
            "fasi_lavoro_selezionate": [
                {"fase_id": "FL-001", "nome_fase": "Taglio e preparazione lamiere/profili"}
            ]
        }
        update_resp = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=update_data)
        assert update_resp.status_code == 200
        
        # Check gate status
        gate_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert gate_resp.status_code == 200
        gate = gate_resp.json()
        
        # With all required fields, should be ready for generation
        assert gate["pronto_per_generazione"] == True
        assert len(gate["campi_mancanti"]) == 0
        assert gate["completezza_percentuale"] > 50
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")

    def test_gate_pos_missing_fields(self, api_client):
        """Verify gate_pos reports missing required fields."""
        # Create an empty cantiere
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Check gate status
        gate_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert gate_resp.status_code == 200
        gate = gate_resp.json()
        
        # Should not be ready and should have missing fields
        assert gate["pronto_per_generazione"] == False
        assert len(gate["campi_mancanti"]) > 0
        
        # Expected missing fields
        expected_missing = ["Indirizzo cantiere", "Citta cantiere", "Data inizio lavori", 
                          "Committente", "Almeno un lavoratore", "Almeno una fase di lavoro"]
        for field in expected_missing:
            assert field in gate["campi_mancanti"]
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")


class TestFullWorkflow:
    """End-to-end workflow tests for Safety Branch MVP."""

    def test_complete_cantiere_workflow(self, api_client):
        """Test complete workflow: Create → Update Steps → Verify Gate → Delete."""
        # Step 1: Create new cantiere
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        cantiere_id = create_resp.json()["cantiere_id"]
        
        # Step 2: Update Step 1 - Dati Cantiere
        step1_data = {
            "dati_cantiere": {
                "attivita_cantiere": "Installazione strutture metalliche",
                "indirizzo_cantiere": "Via Workflow 100",
                "citta_cantiere": "Firenze",
                "provincia_cantiere": "FI",
                "data_inizio_lavori": "2026-08-01",
                "data_fine_prevista": "2026-09-30"
            },
            "soggetti_riferimento": {
                "committente": "Workflow Test SRL",
                "responsabile_lavori": "Ing. Mario Bianchi",
                "direttore_lavori": "Arch. Luigi Verdi"
            },
            "lavoratori_coinvolti": [
                {"nominativo": "Paolo Neri", "mansione": "Capo Cantiere", "addetto_primo_soccorso": True, "addetto_antincendio": True},
                {"nominativo": "Marco Gialli", "mansione": "Saldatore", "addetto_primo_soccorso": False, "addetto_antincendio": False}
            ],
            "subappalti": [
                {"lavorazione": "Verniciatura", "impresa": "Vernici SRL", "durata_prevista": "2 settimane"}
            ]
        }
        step1_resp = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=step1_data)
        assert step1_resp.status_code == 200
        
        # Step 3: Update Step 2 - Fasi Lavoro
        step2_data = {
            "fasi_lavoro_selezionate": [
                {"fase_id": "FL-001", "nome_fase": "Taglio e preparazione lamiere/profili", "rischi_valutati": [], "dpi_richiesti": ["DPI-OCCHIALI", "DPI-GUANTI-CROSTA"]},
                {"fase_id": "FL-002", "nome_fase": "Saldatura (MIG/MAG, TIG, Elettrodo)", "rischi_valutati": [], "dpi_richiesti": ["DPI-SCHERMO-SALD", "DPI-GUANTI-CALORE"]}
            ]
        }
        step2_resp = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=step2_data)
        assert step2_resp.status_code == 200
        
        # Step 4: Update Step 3 - Macchine & DPI
        step3_data = {
            "macchine_attrezzature": [
                {"nome": "Saldatrice MIG/MAG", "marcata_ce": True, "verifiche_periodiche": True},
                {"nome": "Flessibile", "marcata_ce": True, "verifiche_periodiche": True}
            ],
            "dpi_presenti": [
                {"tipo_dpi": "Casco", "presente": True},
                {"tipo_dpi": "Guanti", "presente": True},
                {"tipo_dpi": "Occhiali", "presente": True},
                {"tipo_dpi": "Scarpe antinfortunistiche", "presente": True}
            ],
            "stoccaggio_materiali": "Area dedicata con scaffalature",
            "servizi_igienici": "Bagno chimico in cantiere"
        }
        step3_resp = api_client.put(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}", json=step3_data)
        assert step3_resp.status_code == 200
        
        # Step 5: Verify final state
        final_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")
        assert final_resp.status_code == 200
        final_data = final_resp.json()
        
        # Verify all data persisted
        assert final_data["dati_cantiere"]["indirizzo_cantiere"] == "Via Workflow 100"
        assert final_data["soggetti_riferimento"]["committente"] == "Workflow Test SRL"
        assert len(final_data["lavoratori_coinvolti"]) == 2
        assert len(final_data["fasi_lavoro_selezionate"]) == 2
        assert len(final_data["macchine_attrezzature"]) == 2
        
        # Step 6: Verify Gate POS
        gate_resp = api_client.get(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}/gate")
        assert gate_resp.status_code == 200
        gate = gate_resp.json()
        assert gate["pronto_per_generazione"] == True
        assert len(gate["campi_mancanti"]) == 0
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{cantiere_id}")


class TestDataValidation:
    """Tests for data validation and edge cases."""

    def test_cantiere_preserves_default_numeri_utili(self, api_client):
        """Verify default emergency numbers are preserved."""
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        data = create_resp.json()
        
        numeri = data["numeri_utili"]
        assert len(numeri) == 4
        
        servizi = [n["servizio"] for n in numeri]
        assert "Vigili del fuoco" in servizi
        assert "Pronto soccorso" in servizi
        assert "Carabinieri" in servizi
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{data['cantiere_id']}")

    def test_cantiere_preserves_default_dpi(self, api_client):
        """Verify default DPI list is preserved."""
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        data = create_resp.json()
        
        dpi = data["dpi_presenti"]
        assert len(dpi) == 8
        
        tipi_dpi = [d["tipo_dpi"] for d in dpi]
        assert "Tuta lavoro" in tipi_dpi
        assert "Scarpe antinfortunistiche" in tipi_dpi
        assert "Casco" in tipi_dpi
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{data['cantiere_id']}")

    def test_cantiere_preserves_default_macchine(self, api_client):
        """Verify default machines list is preserved."""
        create_resp = api_client.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert create_resp.status_code == 200
        data = create_resp.json()
        
        macchine = data["macchine_attrezzature"]
        assert len(macchine) == 8
        
        nomi = [m["nome"] for m in macchine]
        assert "Avvitatore elettrico" in nomi
        assert "Saldatrice MIG/MAG" in nomi
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cantieri-sicurezza/{data['cantiere_id']}")

"""
Iteration 210 — Full Audit Test for SOPRALLUOGHI, PERIZIE, PREVENTIVATORE, RILIEVI modules.

Tests the complete flow:
- Sopralluogo CRUD + articoli-catalogo + genera-preventivo + PDF
- Perizia CRUD + codici-danno + collega-commessa + recalc + PDF
- Preventivatore calcola + genera-preventivo + accetta + confronta
- Rilievi CRUD

NOTE: AI endpoints (analizza, analyze-photos, analyze-drawing) are SKIPPED as they require real images and API credits.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://production-debug-12.preview.emergentagent.com")
SESSION_COOKIE = {"session_token": "test_sopralluogo_session"}

# Test data IDs for cleanup
TEST_IDS = {
    "sopralluogo_id": None,
    "perizia_id": None,
    "preventivo_id": None,
    "commessa_id": None,
    "rilievo_id": None,
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.cookies.update(SESSION_COOKIE)
    session.headers.update({"Content-Type": "application/json"})
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# SOPRALLUOGHI MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSopralluoghiCRUD:
    """CRUD operations for Sopralluoghi module."""

    def test_list_sopralluoghi(self, api_client):
        """GET /api/sopralluoghi/ — lista con status e % conformita"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"✓ List sopralluoghi: {data['total']} items")

    def test_create_sopralluogo(self, api_client):
        """POST /api/sopralluoghi/ — crea nuovo sopralluogo"""
        payload = {
            "client_id": "cli_a8a39751d3d1",
            "indirizzo": "Via Test 123",
            "comune": "Bologna",
            "provincia": "BO",
            "descrizione_utente": "TEST_Sopralluogo per test automatico",
            "tipo_intervento": "messa_a_norma",
            "tipo_perizia": "cancelli"
        }
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "sopralluogo_id" in data
        assert data["indirizzo"] == "Via Test 123"
        assert data["status"] == "bozza"
        TEST_IDS["sopralluogo_id"] = data["sopralluogo_id"]
        print(f"✓ Created sopralluogo: {data['document_number']} ({data['sopralluogo_id']})")

    def test_get_sopralluogo_detail(self, api_client):
        """GET /api/sopralluoghi/{id} — dettaglio con analisi AI"""
        # Test with existing sopralluogo that has AI analysis
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54")
        assert response.status_code == 200
        data = response.json()
        assert data["sopralluogo_id"] == "sop_546b0934db54"
        assert data["document_number"] == "SOP-2026/0001"
        assert "analisi_ai" in data
        assert data["analisi_ai"] is not None
        assert "rischi" in data["analisi_ai"]
        assert "conformita_percentuale" in data["analisi_ai"]
        print(f"✓ Get sopralluogo detail: {data['document_number']}, conformita: {data['analisi_ai'].get('conformita_percentuale')}%")

    def test_update_sopralluogo(self, api_client):
        """PUT /api/sopralluoghi/{id} — aggiorna sopralluogo"""
        if not TEST_IDS["sopralluogo_id"]:
            pytest.skip("No test sopralluogo created")
        
        payload = {
            "descrizione_utente": "TEST_Sopralluogo aggiornato",
            "note_tecnico": "Note tecniche di test"
        }
        response = api_client.put(f"{BASE_URL}/api/sopralluoghi/{TEST_IDS['sopralluogo_id']}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["descrizione_utente"] == "TEST_Sopralluogo aggiornato"
        print(f"✓ Updated sopralluogo: {data['sopralluogo_id']}")


class TestSopralluoghiCatalogo:
    """Articoli catalogo for Sopralluoghi."""

    def test_list_articoli_catalogo(self, api_client):
        """GET /api/sopralluoghi/articoli-catalogo — lista articoli perizia con prezzi"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
        # Verify structure
        first_item = data["items"][0]
        assert "articolo_id" in first_item
        assert "codice" in first_item
        assert "descrizione" in first_item
        assert "prezzo_base" in first_item
        assert "categoria" in first_item
        print(f"✓ Articoli catalogo: {len(data['items'])} items")


class TestSopralluoghiFlow:
    """Flow tests for Sopralluoghi — genera-preventivo from existing AI analysis."""

    def test_genera_preventivo_from_sopralluogo(self, api_client):
        """POST /api/sopralluoghi/{id}/genera-preventivo — genera preventivo automatico dall'analisi AI"""
        # Use existing sopralluogo with AI analysis (sop_546b0934db54)
        # NOTE: This will create a NEW preventivo each time, so we test on a fresh sopralluogo
        if not TEST_IDS["sopralluogo_id"]:
            pytest.skip("No test sopralluogo created")
        
        # First, we need to add mock AI analysis to our test sopralluogo
        # Since we can't call the real AI, we'll test the endpoint behavior
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/{TEST_IDS['sopralluogo_id']}/genera-preventivo?variante=B")
        # Expected: 400 because no AI analysis exists
        assert response.status_code == 400
        data = response.json()
        assert "Esegui prima l'analisi AI" in data.get("detail", "")
        print(f"✓ Genera preventivo correctly requires AI analysis first")

    def test_existing_sopralluogo_has_preventivo(self, api_client):
        """Verify existing sopralluogo sop_546b0934db54 has preventivo_id"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54")
        assert response.status_code == 200
        data = response.json()
        # The preventivo_id may change if genera-preventivo is called multiple times
        assert data.get("preventivo_id") is not None
        assert data.get("preventivo_id").startswith("prev_")
        print(f"✓ Existing sopralluogo has preventivo: {data['preventivo_id']}")


class TestSopralluoghiPDF:
    """PDF generation for Sopralluoghi."""

    def test_genera_pdf_perizia(self, api_client):
        """GET /api/sopralluoghi/{id}/pdf — genera PDF perizia sopralluogo"""
        # Use existing sopralluogo with AI analysis
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54/pdf")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000  # PDF should have content
        print(f"✓ PDF generated: {len(response.content)} bytes")

    def test_pdf_requires_ai_analysis(self, api_client):
        """PDF generation requires AI analysis"""
        if not TEST_IDS["sopralluogo_id"]:
            pytest.skip("No test sopralluogo created")
        
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/{TEST_IDS['sopralluogo_id']}/pdf")
        assert response.status_code == 400
        print(f"✓ PDF correctly requires AI analysis")


# ═══════════════════════════════════════════════════════════════════════════════
# PERIZIE MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerizieCRUD:
    """CRUD operations for Perizie module."""

    def test_list_perizie(self, api_client):
        """GET /api/perizie/ — lista perizie"""
        response = api_client.get(f"{BASE_URL}/api/perizie/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"✓ List perizie: {data['total']} items")

    def test_create_perizia(self, api_client):
        """POST /api/perizie/ — crea nuova perizia con tipo_danno"""
        payload = {
            "client_id": "cli_a8a39751d3d1",
            "tipo_danno": "strutturale",
            "localizzazione": {
                "indirizzo": "Via Test Perizia 456",
                "comune": "Bologna",
                "provincia": "BO",
                "lat": 44.4949,
                "lng": 11.3426
            },
            "descrizione_utente": "TEST_Perizia strutturale per test automatico",
            "codici_danno": ["S1-DEF", "A1-ANCH"],
            "prezzo_ml_originale": 170,
            "coefficiente_maggiorazione": 20,
            "moduli": [
                {"descrizione": "Modulo Test 1", "lunghezza_ml": 4.5, "altezza_m": 1.8, "note": ""}
            ],
            "smaltimento": True,
            "accesso_difficile": False,
            "sconto_cortesia": 0
        }
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "perizia_id" in data
        assert data["tipo_danno"] == "strutturale"
        assert data["tipo_danno_label"] == "Danno Strutturale (EN 1090)"
        assert "voci_costo" in data
        assert len(data["voci_costo"]) > 0  # Auto-generated cost items
        assert data["total_perizia"] > 0
        TEST_IDS["perizia_id"] = data["perizia_id"]
        print(f"✓ Created perizia: {data['number']} ({data['perizia_id']}), total: {data['total_perizia']} EUR")

    def test_get_perizia_detail(self, api_client):
        """GET /api/perizie/{id} — dettaglio perizia"""
        # Test with existing perizia
        response = api_client.get(f"{BASE_URL}/api/perizie/per_a4308225da2f")
        assert response.status_code == 200
        data = response.json()
        assert data["perizia_id"] == "per_a4308225da2f"
        assert data["number"] == "PER-2026/0001"
        assert data["tipo_danno"] == "strutturale"
        print(f"✓ Get perizia detail: {data['number']}, total: {data.get('total_perizia', 0)} EUR")

    def test_update_perizia(self, api_client):
        """PUT /api/perizie/{id} — aggiorna perizia"""
        if not TEST_IDS["perizia_id"]:
            pytest.skip("No test perizia created")
        
        payload = {
            "descrizione_utente": "TEST_Perizia aggiornata",
            "sconto_cortesia": 5
        }
        response = api_client.put(f"{BASE_URL}/api/perizie/{TEST_IDS['perizia_id']}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["descrizione_utente"] == "TEST_Perizia aggiornata"
        assert data["sconto_cortesia"] == 5
        print(f"✓ Updated perizia: {data['perizia_id']}")


class TestPerizieCodici:
    """Codici danno reference data."""

    def test_get_codici_danno(self, api_client):
        """GET /api/perizie/codici-danno — lista codici danno disponibili"""
        response = api_client.get(f"{BASE_URL}/api/perizie/codici-danno")
        assert response.status_code == 200
        data = response.json()
        assert "codici_danno" in data
        assert len(data["codici_danno"]) > 0
        # Verify structure
        first_code = data["codici_danno"][0]
        assert "codice" in first_code
        assert "categoria" in first_code
        assert "label" in first_code
        assert "norma" in first_code
        assert "implicazione" in first_code
        print(f"✓ Codici danno: {len(data['codici_danno'])} codes")


class TestPerizieLink:
    """Perizia-Commessa linking."""

    def test_collega_perizia_a_commessa(self, api_client):
        """PATCH /api/perizie/{id}/collega-commessa — collega perizia a commessa esistente"""
        if not TEST_IDS["perizia_id"]:
            pytest.skip("No test perizia created")
        
        payload = {"commessa_id": "com_e8c4810ad476"}
        response = api_client.patch(f"{BASE_URL}/api/perizie/{TEST_IDS['perizia_id']}/collega-commessa", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["commessa_id"] == "com_e8c4810ad476"
        print(f"✓ Perizia linked to commessa: {data['commessa_id']}")


class TestPerizieRecalc:
    """Perizia cost recalculation."""

    def test_recalc_perizia(self, api_client):
        """POST /api/perizie/{id}/recalc — ricalcola costi perizia"""
        if not TEST_IDS["perizia_id"]:
            pytest.skip("No test perizia created")
        
        response = api_client.post(f"{BASE_URL}/api/perizie/{TEST_IDS['perizia_id']}/recalc")
        assert response.status_code == 200
        data = response.json()
        assert "voci_costo" in data
        assert "total_perizia" in data
        assert data["total_perizia"] > 0
        print(f"✓ Recalculated perizia: {data['total_perizia']} EUR, {len(data['voci_costo'])} voci")


class TestPeriziePDF:
    """PDF generation for Perizie."""

    def test_genera_pdf_perizia(self, api_client):
        """GET /api/perizie/{id}/pdf — genera PDF perizia"""
        response = api_client.get(f"{BASE_URL}/api/perizie/per_a4308225da2f/pdf")
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("content-type", "")
        assert len(response.content) > 1000
        print(f"✓ Perizia PDF generated: {len(response.content)} bytes")


# ═══════════════════════════════════════════════════════════════════════════════
# PREVENTIVATORE MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPreventivatoreReference:
    """Reference data for Preventivatore."""

    def test_get_tabella_ore(self, api_client):
        """GET /api/preventivatore/tabella-ore — tabella ore di riferimento"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/tabella-ore")
        assert response.status_code == 200
        data = response.json()
        assert "tabella" in data
        assert "leggera" in data["tabella"]
        assert "media" in data["tabella"]
        assert "complessa" in data["tabella"]
        assert "speciale" in data["tabella"]
        # Verify structure
        media = data["tabella"]["media"]
        assert "ore_per_ton" in media
        assert "range" in media
        print(f"✓ Tabella ore: {len(data['tabella'])} tipologie")

    def test_get_prezzi_storici(self, api_client):
        """GET /api/preventivatore/prezzi-storici — prezzi storici materiali"""
        response = api_client.get(f"{BASE_URL}/api/preventivatore/prezzi-storici")
        assert response.status_code == 200
        data = response.json()
        assert "prezzi" in data
        # Should have some default prices
        prezzi = data["prezzi"]
        assert "S275JR" in prezzi or "default" in prezzi
        print(f"✓ Prezzi storici: {len(prezzi)} entries")


class TestPreventivatoreCalcola:
    """Calcola endpoint for Preventivatore (pure math, no AI)."""

    def test_calcola_preventivo(self, api_client):
        """POST /api/preventivatore/calcola — calcola peso/ore/costo con materiali input"""
        payload = {
            "peso_kg_target": 500,
            "tipologia_struttura": "media",
            "materiali": [
                {
                    "profilo": "HEB 200",
                    "acciaio": "S355J2",
                    "lunghezza_mm": 6000,
                    "quantita": 4,
                    "tipo": "profilo"
                }
            ],
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        response = api_client.post(f"{BASE_URL}/api/preventivatore/calcola", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "peso_totale_kg" in data
        assert "stima_ore" in data
        assert "calcolo" in data
        assert "riepilogo" in data["calcolo"]
        riepilogo = data["calcolo"]["riepilogo"]
        assert "totale_vendita" in riepilogo
        assert riepilogo["totale_vendita"] > 0
        print(f"✓ Calcola preventivo: {data['peso_totale_kg']} kg, {riepilogo['ore_stimate']}h, {riepilogo['totale_vendita']} EUR")
        return data

    def test_calcola_with_manual_weight(self, api_client):
        """POST /api/preventivatore/calcola — calcola con peso manuale (no materiali)"""
        payload = {
            "peso_kg_target": 1000,
            "tipologia_struttura": "complessa",
            "materiali": [],
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        response = api_client.post(f"{BASE_URL}/api/preventivatore/calcola", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["peso_totale_kg"] == 1000
        assert data["tipologia"] == "complessa"
        print(f"✓ Calcola with manual weight: {data['peso_totale_kg']} kg")


class TestPreventivatoreGeneraPreventivo:
    """Genera preventivo from calcolo."""

    def test_genera_preventivo(self, api_client):
        """POST /api/preventivatore/genera-preventivo — genera preventivo dal calcolo predittivo"""
        # First, get a calcolo
        calcola_payload = {
            "peso_kg_target": 500,
            "tipologia_struttura": "media",
            "materiali": [
                {"profilo": "HEB 200", "acciaio": "S355J2", "lunghezza_mm": 6000, "quantita": 4, "tipo": "profilo"}
            ],
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20
        }
        calcola_response = api_client.post(f"{BASE_URL}/api/preventivatore/calcola", json=calcola_payload)
        assert calcola_response.status_code == 200
        calcolo_data = calcola_response.json()

        # Now generate preventivo
        genera_payload = {
            "client_id": "cli_a8a39751d3d1",
            "subject": "TEST_Preventivo Predittivo AI",
            "calcolo": calcolo_data["calcolo"],
            "stima_ore": calcolo_data["stima_ore"],
            "normativa": "EN_1090",
            "classe_esecuzione": "EXC2",
            "giorni_consegna": 30,
            "note": "Test preventivo generato automaticamente"
        }
        response = api_client.post(f"{BASE_URL}/api/preventivatore/genera-preventivo", json=genera_payload)
        assert response.status_code == 200
        data = response.json()
        assert "preventivo_id" in data
        assert "number" in data
        assert "totale" in data
        TEST_IDS["preventivo_id"] = data["preventivo_id"]
        print(f"✓ Generated preventivo: {data['number']} ({data['preventivo_id']}), totale: {data['totale']} EUR")


class TestPreventivatoreAccetta:
    """Accetta preventivo and create commessa."""

    def test_accetta_preventivo(self, api_client):
        """POST /api/preventivatore/accetta/{id} — accetta preventivo e genera commessa EN_1090"""
        if not TEST_IDS["preventivo_id"]:
            pytest.skip("No test preventivo created")
        
        response = api_client.post(f"{BASE_URL}/api/preventivatore/accetta/{TEST_IDS['preventivo_id']}")
        assert response.status_code == 200
        data = response.json()
        assert "commessa_id" in data
        assert "commessa_number" in data
        assert "ore_preventivate" in data
        assert "budget" in data
        TEST_IDS["commessa_id"] = data["commessa_id"]
        print(f"✓ Accepted preventivo, created commessa: {data['commessa_number']} ({data['commessa_id']})")

        # Verify commessa has correct normativa
        commessa_response = api_client.get(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
        assert commessa_response.status_code == 200
        commessa = commessa_response.json()
        assert commessa.get("normativa_tipo") == "EN_1090"
        assert commessa.get("classe_exc") == "EXC2"
        print(f"✓ Commessa has normativa_tipo=EN_1090, classe_exc=EXC2")


class TestPreventivatoreConfronta:
    """Confronta preventivi AI vs manuale."""

    def test_confronta_preventivi(self, api_client):
        """POST /api/preventivatore/confronta — confronta preventivi AI vs manuale"""
        # This requires two existing preventivi - skip if we don't have them
        if not TEST_IDS["preventivo_id"]:
            pytest.skip("No test preventivo created")
        
        # Get the current preventivo_id from sopralluogo
        sop_response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54")
        if sop_response.status_code != 200:
            pytest.skip("Could not get sopralluogo")
        sop_data = sop_response.json()
        manuale_prev_id = sop_data.get("preventivo_id")
        if not manuale_prev_id:
            pytest.skip("Sopralluogo has no preventivo")
        
        # We need another preventivo to compare - use the one from sopralluogo
        payload = {
            "preventivo_ai_id": TEST_IDS["preventivo_id"],
            "preventivo_manuale_id": manuale_prev_id
        }
        response = api_client.post(f"{BASE_URL}/api/preventivatore/confronta", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "confidence_score" in data
        assert "giudizio" in data
        assert "confronto_categorie" in data
        assert "scostamento_totale_pct" in data
        print(f"✓ Confronta preventivi: confidence={data['confidence_score']}, giudizio={data['giudizio']}, scostamento={data['scostamento_totale_pct']}%")


# ═══════════════════════════════════════════════════════════════════════════════
# RILIEVI MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRilieviCRUD:
    """CRUD operations for Rilievi module."""

    def test_list_rilievi(self, api_client):
        """GET /api/rilievi/ — lista rilievi tecnici"""
        response = api_client.get(f"{BASE_URL}/api/rilievi/")
        assert response.status_code == 200
        data = response.json()
        assert "rilievi" in data
        assert "total" in data
        print(f"✓ List rilievi: {data['total']} items")

    def test_create_rilievo(self, api_client):
        """POST /api/rilievi/ — crea rilievo"""
        from datetime import date
        payload = {
            "client_id": "cli_a8a39751d3d1",
            "project_name": "TEST_Rilievo Automatico",
            "survey_date": "2026-01-15",  # Date only, no time
            "location": "Via Test Rilievo 789, Bologna",
            "notes": "Rilievo di test automatico",
            "tipologia": "inferriata_fissa",
            "misure": {
                "luce_larghezza": 2000,
                "luce_altezza": 1200,
                "interasse_montanti": 120,
                "numero_traversi": 2,
                "profilo_montante": "30x30",
                "profilo_traverso": "20x20"
            },
            "elementi": [],
            "sketches": [],
            "photos": []
        }
        response = api_client.post(f"{BASE_URL}/api/rilievi/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "rilievo_id" in data
        assert data["project_name"] == "TEST_Rilievo Automatico"
        assert data["tipologia"] == "inferriata_fissa"
        TEST_IDS["rilievo_id"] = data["rilievo_id"]
        print(f"✓ Created rilievo: {data['rilievo_id']}")

    def test_get_rilievo_detail(self, api_client):
        """GET /api/rilievi/{id} — dettaglio rilievo"""
        if not TEST_IDS["rilievo_id"]:
            pytest.skip("No test rilievo created")
        
        response = api_client.get(f"{BASE_URL}/api/rilievi/{TEST_IDS['rilievo_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["rilievo_id"] == TEST_IDS["rilievo_id"]
        print(f"✓ Get rilievo detail: {data['rilievo_id']}")

    def test_update_rilievo(self, api_client):
        """PUT /api/rilievi/{id} — aggiorna rilievo"""
        if not TEST_IDS["rilievo_id"]:
            pytest.skip("No test rilievo created")
        
        payload = {
            "notes": "TEST_Rilievo aggiornato con note"
        }
        response = api_client.put(f"{BASE_URL}/api/rilievi/{TEST_IDS['rilievo_id']}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "TEST_Rilievo aggiornato con note"
        print(f"✓ Updated rilievo: {data['rilievo_id']}")

    def test_calcola_materiali_rilievo(self, api_client):
        """POST /api/rilievi/{id}/calcola-materiali — calcola materiali da misure"""
        if not TEST_IDS["rilievo_id"]:
            pytest.skip("No test rilievo created")
        
        response = api_client.post(f"{BASE_URL}/api/rilievi/{TEST_IDS['rilievo_id']}/calcola-materiali")
        assert response.status_code == 200
        data = response.json()
        assert "materiali" in data
        assert "peso_totale_kg" in data
        assert "superficie_verniciatura_m2" in data
        print(f"✓ Calcola materiali: {data['peso_totale_kg']} kg, {data['superficie_verniciatura_m2']} m²")


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressionSopralluoghiAI:
    """Regression: Verify sopralluoghi show AI analysis with rischi, dispositivi, materiali."""

    def test_sopralluogo_ai_analysis_structure(self, api_client):
        """Verify AI analysis has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54")
        assert response.status_code == 200
        data = response.json()
        analisi = data.get("analisi_ai")
        assert analisi is not None
        
        # Check required fields
        assert "tipo_chiusura" in analisi
        assert "descrizione_generale" in analisi
        assert "rischi" in analisi
        assert "dispositivi_presenti" in analisi
        assert "dispositivi_mancanti" in analisi
        assert "conformita_percentuale" in analisi
        
        # Check rischi structure
        if analisi["rischi"]:
            rischio = analisi["rischi"][0]
            assert "zona" in rischio
            assert "gravita" in rischio
            assert "problema" in rischio
            assert "norma_riferimento" in rischio
            assert "soluzione" in rischio
        
        print(f"✓ AI analysis structure verified: {len(analisi['rischi'])} rischi, {analisi['conformita_percentuale']}% conformita")


class TestRegressionPreventivoFromSopralluogo:
    """Regression: Verify preventivo generated from sopralluogo has correct voci with prezzi."""

    def test_preventivo_from_sopralluogo_structure(self, api_client):
        """Verify preventivo from sopralluogo has correct structure"""
        # First get the current preventivo_id from sopralluogo
        sop_response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_546b0934db54")
        assert sop_response.status_code == 200
        sop_data = sop_response.json()
        prev_id = sop_data.get("preventivo_id")
        assert prev_id is not None, "Sopralluogo should have a preventivo_id"
        
        # Get the preventivo linked to sopralluogo
        response = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "lines" in data
        assert "totals" in data
        assert data.get("sopralluogo_id") == "sop_546b0934db54"
        
        # Check lines have prices
        if data["lines"]:
            line = data["lines"][0]
            assert "unit_price" in line
            assert "line_total" in line
        
        print(f"✓ Preventivo from sopralluogo verified: {len(data['lines'])} lines, total: {data['totals'].get('total', 0)} EUR")


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanup:
    """Cleanup test data."""

    def test_delete_test_rilievo(self, api_client):
        """DELETE test rilievo"""
        if TEST_IDS["rilievo_id"]:
            response = api_client.delete(f"{BASE_URL}/api/rilievi/{TEST_IDS['rilievo_id']}")
            assert response.status_code == 200
            print(f"✓ Deleted test rilievo: {TEST_IDS['rilievo_id']}")

    def test_delete_test_perizia(self, api_client):
        """DELETE test perizia"""
        if TEST_IDS["perizia_id"]:
            response = api_client.delete(f"{BASE_URL}/api/perizie/{TEST_IDS['perizia_id']}")
            assert response.status_code == 200
            print(f"✓ Deleted test perizia: {TEST_IDS['perizia_id']}")

    def test_delete_test_sopralluogo(self, api_client):
        """DELETE test sopralluogo"""
        if TEST_IDS["sopralluogo_id"]:
            response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/{TEST_IDS['sopralluogo_id']}")
            assert response.status_code == 200
            print(f"✓ Deleted test sopralluogo: {TEST_IDS['sopralluogo_id']}")

    def test_delete_test_commessa(self, api_client):
        """DELETE test commessa (created from preventivatore accetta)"""
        if TEST_IDS["commessa_id"]:
            response = api_client.delete(f"{BASE_URL}/api/commesse/{TEST_IDS['commessa_id']}")
            # May fail if commessa has linked documents, that's OK
            if response.status_code == 200:
                print(f"✓ Deleted test commessa: {TEST_IDS['commessa_id']}")
            else:
                print(f"⚠ Could not delete test commessa (may have linked docs): {TEST_IDS['commessa_id']}")

    def test_delete_test_preventivo(self, api_client):
        """DELETE test preventivo"""
        if TEST_IDS["preventivo_id"]:
            response = api_client.delete(f"{BASE_URL}/api/preventivi/{TEST_IDS['preventivo_id']}")
            if response.status_code == 200:
                print(f"✓ Deleted test preventivo: {TEST_IDS['preventivo_id']}")
            else:
                print(f"⚠ Could not delete test preventivo: {TEST_IDS['preventivo_id']}")

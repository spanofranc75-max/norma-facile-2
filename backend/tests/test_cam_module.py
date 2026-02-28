"""
CAM (Criteri Ambientali Minimi) Module Tests
Tests for environmental compliance module per DM 23/06/2022 n.256

Endpoints tested:
- GET /api/cam/soglie - CAM thresholds (public)
- POST /api/cam/lotti - Create CAM material batch
- GET /api/cam/lotti - List CAM batches (with filters)
- PUT /api/cam/lotti/{lotto_id} - Update CAM batch
- POST /api/cam/calcola/{commessa_id} - Calculate CAM compliance
- GET /api/cam/calcolo/{commessa_id} - Get latest CAM calculation
- GET /api/cam/dichiarazione-pdf/{commessa_id} - Generate PDF declaration
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_cam_session_1772307497726')
TEST_USER_ID = os.environ.get('TEST_USER_ID', 'test-cam-user-1772307497726')


@pytest.fixture
def api_client():
    """Base requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_client(api_client):
    """Authenticated session."""
    api_client.headers.update({"Authorization": f"Bearer {TEST_TOKEN}"})
    return api_client


@pytest.fixture
def test_commessa_id(auth_client):
    """Create a test commessa for CAM tests."""
    commessa_id = f"com_cam_test_{uuid.uuid4().hex[:8]}"
    payload = {
        "commessa_id": commessa_id,
        "numero": f"CAM-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": "Test Commessa for CAM Module",
        "client_name": "Test Cliente CAM",
        "stato": "in_corso",
    }
    response = auth_client.post(f"{BASE_URL}/api/commesse", json=payload)
    if response.status_code not in [200, 201]:
        # Try to use existing commessa
        list_resp = auth_client.get(f"{BASE_URL}/api/commesse?limit=1")
        if list_resp.status_code == 200:
            commesse = list_resp.json().get("commesse", [])
            if commesse:
                yield commesse[0].get("commessa_id")
                return
        pytest.skip("Cannot create or find test commessa")
    
    yield commessa_id
    
    # Cleanup
    auth_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


class TestCAMSoglie:
    """Test CAM thresholds endpoint - PUBLIC (no auth required)."""
    
    def test_get_soglie_success(self, api_client):
        """GET /api/cam/soglie should return CAM thresholds."""
        response = api_client.get(f"{BASE_URL}/api/cam/soglie")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify normativa field
        assert "normativa" in data
        assert "DM 23 giugno 2022 n. 256" in data["normativa"]
        
        # Verify soglie structure
        assert "soglie" in data
        soglie = data["soglie"]
        assert "strutturale" in soglie
        assert "non_strutturale" in soglie
        
        # Verify threshold values per DM 256/2022
        strutturale = soglie["strutturale"]
        assert strutturale["forno_elettrico_non_legato"] == 75, "Electric furnace non-alloy should be 75%"
        assert strutturale["forno_elettrico_legato"] == 60, "Electric furnace alloy should be 60%"
        assert strutturale["ciclo_integrale"] == 12, "Integrated cycle should be 12%"
        
        # Verify certificazioni_ammesse
        assert "certificazioni_ammesse" in data
        cert_codici = [c["codice"] for c in data["certificazioni_ammesse"]]
        assert "epd" in cert_codici
        assert "remade_in_italy" in cert_codici
        assert "dichiarazione_produttore" in cert_codici


class TestCAMLotti:
    """Test CAM material batch CRUD operations."""
    
    def test_create_lotto_success(self, auth_client, test_commessa_id):
        """POST /api/cam/lotti should create a CAM material batch with conformity calculation."""
        payload = {
            "descrizione": "TEST_Acciaio S275JR - Test CAM Lotto",
            "fornitore": "TEST_Acciaieria Test",
            "numero_colata": f"TEST_COL_{uuid.uuid4().hex[:6]}",
            "peso_kg": 1000,
            "qualita_acciaio": "S275JR",
            "percentuale_riciclato": 78,  # Above 75% threshold
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "numero_certificazione": "CERT-TEST-001",
            "ente_certificatore": "Test Ente",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
            "note": "Test lotto for CAM module testing",
        }
        
        response = auth_client.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "lotto" in data
        lotto = data["lotto"]
        
        # Verify lotto_id generated
        assert "lotto_id" in lotto
        assert lotto["lotto_id"].startswith("lot_")
        
        # Verify data persistence
        assert lotto["descrizione"] == payload["descrizione"]
        assert lotto["peso_kg"] == payload["peso_kg"]
        assert lotto["percentuale_riciclato"] == payload["percentuale_riciclato"]
        assert lotto["metodo_produttivo"] == payload["metodo_produttivo"]
        
        # Verify conformity calculation
        assert "conforme_cam" in lotto
        assert lotto["conforme_cam"] == True, "78% should be conforme for 75% threshold"
        assert "soglia_minima_cam" in lotto
        assert lotto["soglia_minima_cam"] == 75
        assert "peso_riciclato_kg" in lotto
        assert lotto["peso_riciclato_kg"] == 780  # 1000 * 78%
        
        # Store for cleanup
        self.created_lotto_id = lotto["lotto_id"]
    
    def test_create_lotto_non_conforme(self, auth_client, test_commessa_id):
        """POST /api/cam/lotti with low recycled % should be non-conforme."""
        payload = {
            "descrizione": "TEST_Acciaio S355 - Non Conforme",
            "peso_kg": 500,
            "percentuale_riciclato": 50,  # Below 75% threshold
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "nessuna",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        
        response = auth_client.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        lotto = data["lotto"]
        
        assert lotto["conforme_cam"] == False, "50% should NOT be conforme for 75% threshold"
        assert lotto["soglia_minima_cam"] == 75
    
    def test_list_lotti_success(self, auth_client, test_commessa_id):
        """GET /api/cam/lotti should list CAM batches."""
        # First create a lotto
        create_payload = {
            "descrizione": "TEST_List Test Lotto",
            "peso_kg": 100,
            "percentuale_riciclato": 80,
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        auth_client.post(f"{BASE_URL}/api/cam/lotti", json=create_payload)
        
        # List all lotti
        response = auth_client.get(f"{BASE_URL}/api/cam/lotti")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "lotti" in data
        assert "total" in data
        assert isinstance(data["lotti"], list)
    
    def test_list_lotti_filter_by_commessa(self, auth_client, test_commessa_id):
        """GET /api/cam/lotti?commessa_id=xxx should filter by commessa."""
        # Create lotti for specific commessa
        create_payload = {
            "descrizione": "TEST_Filtered Lotto",
            "peso_kg": 200,
            "percentuale_riciclato": 85,
            "metodo_produttivo": "forno_elettrico_legato",
            "tipo_certificazione": "epd",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        auth_client.post(f"{BASE_URL}/api/cam/lotti", json=create_payload)
        
        # Filter by commessa_id
        response = auth_client.get(f"{BASE_URL}/api/cam/lotti?commessa_id={test_commessa_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        lotti = data["lotti"]
        
        # All returned lotti should belong to the test commessa
        for lotto in lotti:
            assert lotto.get("commessa_id") == test_commessa_id
    
    def test_update_lotto_recalculates_conformity(self, auth_client, test_commessa_id):
        """PUT /api/cam/lotti/{lotto_id} should update and recalculate conformity."""
        # First create a lotto
        create_payload = {
            "descrizione": "TEST_Update Test Lotto",
            "peso_kg": 100,
            "percentuale_riciclato": 80,
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        create_response = auth_client.post(f"{BASE_URL}/api/cam/lotti", json=create_payload)
        assert create_response.status_code == 200
        lotto_id = create_response.json()["lotto"]["lotto_id"]
        
        # Update with lower percentage (should become non-conforme)
        update_payload = {
            "descrizione": "TEST_Update Test Lotto - Modified",
            "peso_kg": 150,
            "percentuale_riciclato": 50,  # Now below threshold
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        
        update_response = auth_client.put(f"{BASE_URL}/api/cam/lotti/{lotto_id}", json=update_payload)
        
        assert update_response.status_code == 200
        
        # Verify the update by fetching
        get_response = auth_client.get(f"{BASE_URL}/api/cam/lotti/{lotto_id}")
        assert get_response.status_code == 200
        
        updated = get_response.json()
        assert updated["peso_kg"] == 150
        assert updated["percentuale_riciclato"] == 50
        assert updated["conforme_cam"] == False, "50% should be non-conforme"


class TestCAMCalcolo:
    """Test CAM compliance calculation for a commessa."""
    
    def test_calcola_cam_success(self, auth_client, test_commessa_id):
        """POST /api/cam/calcola/{commessa_id} should calculate total CAM compliance."""
        # First create some lotti for the commessa
        lotti_data = [
            {"descrizione": "TEST_Acciaio 1", "peso_kg": 500, "percentuale_riciclato": 80, "metodo_produttivo": "forno_elettrico_non_legato", "tipo_certificazione": "epd", "uso_strutturale": True},
            {"descrizione": "TEST_Acciaio 2", "peso_kg": 300, "percentuale_riciclato": 75, "metodo_produttivo": "forno_elettrico_non_legato", "tipo_certificazione": "dichiarazione_produttore", "uso_strutturale": True},
        ]
        
        for lotto in lotti_data:
            lotto["commessa_id"] = test_commessa_id
            auth_client.post(f"{BASE_URL}/api/cam/lotti", json=lotto)
        
        # Calculate CAM for commessa
        response = auth_client.post(f"{BASE_URL}/api/cam/calcola/{test_commessa_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify calculation result fields
        assert "peso_totale_kg" in data
        assert "peso_riciclato_kg" in data
        assert "percentuale_riciclato_totale" in data
        assert "soglia_minima_richiesta" in data
        assert "conforme_cam" in data
        assert "righe" in data
        
        # Verify values
        assert data["peso_totale_kg"] >= 800  # At least our test data
        assert isinstance(data["conforme_cam"], bool)
        assert isinstance(data["righe"], list)
    
    def test_get_calcolo_cam_success(self, auth_client, test_commessa_id):
        """GET /api/cam/calcolo/{commessa_id} should return latest CAM calculation."""
        # First trigger a calculation
        auth_client.post(f"{BASE_URL}/api/cam/calcola/{test_commessa_id}")
        
        # Get the calculation
        response = auth_client.get(f"{BASE_URL}/api/cam/calcolo/{test_commessa_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Same structure as calcola endpoint
        assert "peso_totale_kg" in data
        assert "percentuale_riciclato_totale" in data
        assert "conforme_cam" in data
        assert "data_calcolo" in data
    
    def test_calcola_cam_no_lotti(self, auth_client):
        """POST /api/cam/calcola/{commessa_id} with no lotti should return empty result."""
        # Create a fresh commessa with no lotti
        commessa_id = f"com_cam_empty_{uuid.uuid4().hex[:8]}"
        payload = {
            "commessa_id": commessa_id,
            "numero": f"CAM-EMPTY-{datetime.now().strftime('%H%M%S')}",
            "title": "Empty Commessa for CAM",
            "client_name": "Test",
            "stato": "in_corso",
        }
        auth_client.post(f"{BASE_URL}/api/commesse", json=payload)
        
        # Calculate - should return empty result
        response = auth_client.post(f"{BASE_URL}/api/cam/calcola/{commessa_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["peso_totale_kg"] == 0
        assert data["conforme_cam"] == False
        assert len(data["righe"]) == 0
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


class TestCAMPDF:
    """Test CAM PDF declaration generation."""
    
    def test_generate_pdf_success(self, auth_client, test_commessa_id):
        """GET /api/cam/dichiarazione-pdf/{commessa_id} should generate PDF."""
        # First create some lotti for the commessa
        lotto_payload = {
            "descrizione": "TEST_Acciaio per PDF",
            "peso_kg": 1000,
            "percentuale_riciclato": 80,
            "metodo_produttivo": "forno_elettrico_non_legato",
            "tipo_certificazione": "epd",
            "numero_certificazione": "EPD-TEST-001",
            "ente_certificatore": "ICMQ",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        auth_client.post(f"{BASE_URL}/api/cam/lotti", json=lotto_payload)
        
        # Generate PDF
        response = auth_client.get(f"{BASE_URL}/api/cam/dichiarazione-pdf/{test_commessa_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify PDF content type
        assert response.headers.get("content-type") == "application/pdf"
        
        # Verify it's a valid PDF (starts with %PDF)
        content = response.content
        assert content[:4] == b'%PDF', "Response should be a valid PDF file"
        
        # Verify Content-Disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "Dichiarazione_CAM" in content_disp
    
    def test_generate_pdf_no_lotti_error(self, auth_client):
        """GET /api/cam/dichiarazione-pdf/{commessa_id} with no lotti should return 400."""
        # Create empty commessa
        commessa_id = f"com_cam_pdf_empty_{uuid.uuid4().hex[:8]}"
        payload = {
            "commessa_id": commessa_id,
            "numero": f"CAM-PDF-EMPTY-{datetime.now().strftime('%H%M%S')}",
            "title": "Empty for PDF Test",
            "client_name": "Test",
            "stato": "in_corso",
        }
        auth_client.post(f"{BASE_URL}/api/commesse", json=payload)
        
        # Try to generate PDF - should fail
        response = auth_client.get(f"{BASE_URL}/api/cam/dichiarazione-pdf/{commessa_id}")
        
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "Nessun materiale CAM" in data["detail"]
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/commesse/{commessa_id}")


class TestCAMConformityLogic:
    """Test CAM conformity calculation logic for different scenarios."""
    
    def test_forno_elettrico_legato_60_threshold(self, auth_client, test_commessa_id):
        """Forno elettrico legato should have 60% threshold."""
        payload = {
            "descrizione": "TEST_Acciaio Legato",
            "peso_kg": 100,
            "percentuale_riciclato": 62,  # Above 60%
            "metodo_produttivo": "forno_elettrico_legato",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        
        response = auth_client.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        
        assert response.status_code == 200
        lotto = response.json()["lotto"]
        
        assert lotto["soglia_minima_cam"] == 60
        assert lotto["conforme_cam"] == True
    
    def test_ciclo_integrale_12_threshold(self, auth_client, test_commessa_id):
        """Ciclo integrale should have 12% threshold."""
        payload = {
            "descrizione": "TEST_Acciaio Ciclo Integrale",
            "peso_kg": 200,
            "percentuale_riciclato": 15,  # Above 12%
            "metodo_produttivo": "ciclo_integrale",
            "tipo_certificazione": "dichiarazione_produttore",
            "uso_strutturale": True,
            "commessa_id": test_commessa_id,
        }
        
        response = auth_client.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        
        assert response.status_code == 200
        lotto = response.json()["lotto"]
        
        assert lotto["soglia_minima_cam"] == 12
        assert lotto["conforme_cam"] == True


class TestCAMRequiresAuth:
    """Test that authenticated endpoints require auth."""
    
    def test_lotti_requires_auth(self, api_client):
        """POST /api/cam/lotti should require authentication."""
        payload = {"descrizione": "Test", "peso_kg": 100}
        response = api_client.post(f"{BASE_URL}/api/cam/lotti", json=payload)
        
        # Should be 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_calcola_requires_auth(self, api_client):
        """POST /api/cam/calcola/{id} should require authentication."""
        response = api_client.post(f"{BASE_URL}/api/cam/calcola/test_commessa_id")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_pdf_requires_auth(self, api_client):
        """GET /api/cam/dichiarazione-pdf/{id} should require authentication."""
        response = api_client.get(f"{BASE_URL}/api/cam/dichiarazione-pdf/test_commessa_id")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


@pytest.fixture(autouse=True, scope="module")
def cleanup_test_data(auth_client):
    """Cleanup TEST_ prefixed data after all tests."""
    yield
    
    # Cleanup test lotti
    try:
        response = requests.get(
            f"{BASE_URL}/api/cam/lotti",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        if response.status_code == 200:
            lotti = response.json().get("lotti", [])
            for lotto in lotti:
                if "TEST_" in (lotto.get("descrizione") or ""):
                    requests.delete(
                        f"{BASE_URL}/api/cam/lotti/{lotto['lotto_id']}",
                        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
                    )
    except Exception:
        pass

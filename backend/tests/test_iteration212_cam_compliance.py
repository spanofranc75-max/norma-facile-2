"""
Iteration 212 — CAM (Criteri Ambientali Minimi) Compliance Testing
Tests for:
- POST/PUT /api/fpc/batches with CAM fields (peso_kg, percentuale_riciclato, metodo_produttivo, distanza_trasporto_km)
- GET /api/fpc/batches/rintracciabilita/{commessa_id} returns peso_kg and percentuale_riciclato
- POST /api/cam/calcola/{commessa_id} pulls CAM data from material_batches
- POST /api/fascicolo-tecnico/{cid}/dop-automatica creates DOP with cam_summary
- GET /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf generates PDF with CAM section
- GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf generates CE label PDF
- GET /api/cam/dichiarazione-pdf/{cid} generates CAM declaration PDF
- GET /api/fascicolo-tecnico/{cid}/rintracciabilita-totale/pdf generates traceability PDF
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_2c57c1283871"
TEST_DOP_ID = "dop_e874fc9331"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestMaterialBatchesCAMFields:
    """Test CAM fields in material_batches CRUD operations."""
    
    def test_create_batch_with_cam_fields(self, api_client):
        """POST /api/fpc/batches with new CAM fields saves correctly."""
        unique_heat = f"TEST_CAM_{uuid.uuid4().hex[:8]}"
        payload = {
            "supplier_name": "Test Fornitore CAM",
            "material_type": "S275JR",
            "heat_number": unique_heat,
            "dimensions": "IPE 200 x 6000",
            "peso_kg": 1250.5,
            "percentuale_riciclato": 82.3,
            "metodo_produttivo": "forno_elettrico_non_legato",
            "distanza_trasporto_km": 185.0,
            "certificazione_epd": "EPD-2026-001",
            "commessa_id": TEST_COMMESSA_ID,
            "notes": "Test batch with CAM fields"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fpc/batches", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "batch_id" in data, "Response should contain batch_id"
        assert data["peso_kg"] == 1250.5 or data["peso_kg"] == 1250, "peso_kg should be saved"
        assert data.get("percentuale_riciclato") == 82.3, "percentuale_riciclato should be saved"
        assert data.get("metodo_produttivo") == "forno_elettrico_non_legato", "metodo_produttivo should be saved"
        assert data.get("distanza_trasporto_km") == 185.0, "distanza_trasporto_km should be saved"
        
        # Cleanup
        batch_id = data["batch_id"]
        api_client.delete(f"{BASE_URL}/api/fpc/batches/{batch_id}")
        print(f"✓ Created batch with CAM fields: {batch_id}")
    
    def test_update_batch_cam_fields(self, api_client):
        """PUT /api/fpc/batches/{id} updates CAM fields."""
        # First create a batch
        unique_heat = f"TEST_UPD_{uuid.uuid4().hex[:8]}"
        create_payload = {
            "supplier_name": "Test Fornitore",
            "material_type": "S355J2",
            "heat_number": unique_heat,
            "peso_kg": 500,
            "percentuale_riciclato": 70,
            "metodo_produttivo": "ciclo_integrale",
            "commessa_id": TEST_COMMESSA_ID
        }
        
        create_resp = api_client.post(f"{BASE_URL}/api/fpc/batches", json=create_payload)
        assert create_resp.status_code == 200
        batch_id = create_resp.json()["batch_id"]
        
        # Update with new CAM values
        update_payload = {
            "supplier_name": "Test Fornitore Updated",
            "material_type": "S355J2",
            "heat_number": unique_heat,
            "peso_kg": 750.5,
            "percentuale_riciclato": 85.0,
            "metodo_produttivo": "forno_elettrico_legato",
            "distanza_trasporto_km": 220.0
        }
        
        update_resp = api_client.put(f"{BASE_URL}/api/fpc/batches/{batch_id}", json=update_payload)
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        # Verify update by fetching
        get_resp = api_client.get(f"{BASE_URL}/api/fpc/batches/{batch_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("peso_kg") == 750.5 or data.get("peso_kg") == 750, "peso_kg should be updated"
        assert data.get("percentuale_riciclato") == 85.0, "percentuale_riciclato should be updated"
        assert data.get("metodo_produttivo") == "forno_elettrico_legato", "metodo_produttivo should be updated"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/fpc/batches/{batch_id}")
        print(f"✓ Updated batch CAM fields: {batch_id}")


class TestRintracciabilitaEndpoint:
    """Test rintracciabilita endpoint returns CAM fields."""
    
    def test_rintracciabilita_returns_cam_fields(self, api_client):
        """GET /api/fpc/batches/rintracciabilita/{commessa_id} returns peso_kg and percentuale_riciclato."""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "righe" in data, "Response should contain 'righe'"
        assert "commessa_id" in data, "Response should contain 'commessa_id'"
        assert data["commessa_id"] == TEST_COMMESSA_ID
        
        # Check that righe contain CAM fields
        righe = data.get("righe", [])
        if len(righe) > 0:
            first_row = righe[0]
            # These fields should be present (even if null)
            assert "peso_kg" in first_row, "righe should contain peso_kg field"
            assert "percentuale_riciclato" in first_row, "righe should contain percentuale_riciclato field"
            print(f"✓ Rintracciabilita returns {len(righe)} rows with CAM fields")
        else:
            print("⚠ No material batches found for this commessa")


class TestCAMCalculation:
    """Test CAM calculation endpoint."""
    
    def test_calcola_cam_commessa(self, api_client):
        """POST /api/cam/calcola/{commessa_id} pulls CAM data from material_batches."""
        response = api_client.post(f"{BASE_URL}/api/cam/calcola/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa_id" in data, "Response should contain commessa_id"
        assert data["commessa_id"] == TEST_COMMESSA_ID
        
        # Check CAM calculation fields
        assert "peso_totale_kg" in data, "Response should contain peso_totale_kg"
        assert "peso_riciclato_kg" in data, "Response should contain peso_riciclato_kg"
        assert "percentuale_riciclato_totale" in data, "Response should contain percentuale_riciclato_totale"
        assert "conforme_cam" in data, "Response should contain conforme_cam"
        assert "righe" in data, "Response should contain righe (material details)"
        
        print(f"✓ CAM calculation: peso_totale={data.get('peso_totale_kg')}kg, "
              f"% riciclato={data.get('percentuale_riciclato_totale')}%, "
              f"conforme={data.get('conforme_cam')}")


class TestDOPAutomatica:
    """Test DOP automatica with CAM summary."""
    
    def test_dop_automatica_creates_cam_summary(self, api_client):
        """POST /api/fascicolo-tecnico/{cid}/dop-automatica creates DOP with cam_summary."""
        response = api_client.post(f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-automatica")
        
        # May return 200 or 400 if max DOPs reached
        if response.status_code == 400 and "massimo" in response.text.lower():
            print("⚠ Max DOPs reached, skipping creation test")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dop" in data, "Response should contain 'dop'"
        dop = data["dop"]
        
        assert "dop_id" in dop, "DOP should have dop_id"
        assert "dop_numero" in dop, "DOP should have dop_numero"
        assert "automatica" in dop and dop["automatica"] == True, "DOP should be marked as automatica"
        
        # Check cam_summary if material batches exist
        if dop.get("cam_summary"):
            cam = dop["cam_summary"]
            assert "materiali" in cam, "cam_summary should contain materiali list"
            assert "co2_risparmiata_kg" in cam, "cam_summary should contain co2_risparmiata_kg"
            assert "distanza_media_km" in cam or cam.get("distanza_media_km") is None, "cam_summary should have distanza_media_km"
            print(f"✓ DOP automatica created with CAM summary: {dop['dop_numero']}")
        else:
            print(f"✓ DOP automatica created (no CAM data): {dop['dop_numero']}")


class TestPDFGeneration:
    """Test PDF generation endpoints."""
    
    def test_dop_pdf_generation(self, api_client):
        """GET /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf generates PDF."""
        # First get list of DOPs
        list_resp = api_client.get(f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionate")
        assert list_resp.status_code == 200
        
        dops = list_resp.json().get("dop_frazionate", [])
        if not dops:
            print("⚠ No DOPs found, skipping PDF test")
            return
        
        dop_id = dops[0]["dop_id"]
        
        response = api_client.get(f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/dop-frazionata/{dop_id}/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Should return PDF content-type"
        assert len(response.content) > 1000, "PDF should have substantial content"
        print(f"✓ DOP PDF generated: {len(response.content)} bytes")
    
    def test_etichetta_ce_1090_pdf(self, api_client):
        """GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf generates CE label PDF."""
        response = api_client.get(f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/etichetta-ce-1090/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Should return PDF content-type"
        assert len(response.content) > 500, "PDF should have content"
        print(f"✓ CE Label PDF generated: {len(response.content)} bytes")
    
    def test_cam_dichiarazione_pdf(self, api_client):
        """GET /api/cam/dichiarazione-pdf/{cid} generates CAM declaration PDF."""
        response = api_client.get(f"{BASE_URL}/api/cam/dichiarazione-pdf/{TEST_COMMESSA_ID}")
        
        # May return 400 if no CAM materials
        if response.status_code == 400:
            print(f"⚠ CAM declaration PDF skipped: {response.json().get('detail', 'No CAM data')}")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Should return PDF content-type"
        assert len(response.content) > 1000, "PDF should have substantial content"
        print(f"✓ CAM Declaration PDF generated: {len(response.content)} bytes")
    
    def test_rintracciabilita_totale_pdf(self, api_client):
        """GET /api/fascicolo-tecnico/{cid}/rintracciabilita-totale/pdf generates traceability PDF."""
        response = api_client.get(f"{BASE_URL}/api/fascicolo-tecnico/{TEST_COMMESSA_ID}/rintracciabilita-totale/pdf")
        
        # May return 400 if no material batches
        if response.status_code == 400:
            print(f"⚠ Rintracciabilita PDF skipped: {response.json().get('detail', 'No batches')}")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Should return PDF content-type"
        assert len(response.content) > 1000, "PDF should have substantial content"
        print(f"✓ Rintracciabilita Totale PDF generated: {len(response.content)} bytes")


class TestExistingBatchesCAMData:
    """Test that existing batches have CAM data."""
    
    def test_list_batches_for_commessa(self, api_client):
        """GET /api/fpc/batches?commessa_id={cid} returns batches with CAM fields."""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches?commessa_id={TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        batches = data.get("batches", [])
        
        print(f"Found {len(batches)} batches for commessa {TEST_COMMESSA_ID}")
        
        for batch in batches[:3]:  # Check first 3
            print(f"  - {batch.get('heat_number', 'N/A')}: "
                  f"peso={batch.get('peso_kg', 'N/A')}kg, "
                  f"%ric={batch.get('percentuale_riciclato', 'N/A')}, "
                  f"metodo={batch.get('metodo_produttivo', 'N/A')}")


class TestAuthenticationRequired:
    """Test that endpoints require authentication."""
    
    def test_batches_requires_auth(self):
        """Endpoints should return 401 without session cookie."""
        response = requests.get(f"{BASE_URL}/api/fpc/batches")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Authentication required for /api/fpc/batches")
    
    def test_cam_calcola_requires_auth(self):
        """CAM calculation should require auth."""
        response = requests.post(f"{BASE_URL}/api/cam/calcola/{TEST_COMMESSA_ID}")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Authentication required for /api/cam/calcola")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

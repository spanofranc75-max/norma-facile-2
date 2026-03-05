"""
Iteration 138: Sopralluoghi & Messa a Norma AI Module Tests
Tests for: Photo upload, GPT-4o Vision analysis, Quote generation, Article catalog
"""
import pytest
import requests
import os
import io
from PIL import Image

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_sopralluogo_1772722039719"
USER_ID = "user_97c773827822"


@pytest.fixture(scope="module")
def api_client():
    """Create a requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def created_sopralluogo(api_client):
    """Create a sopralluogo for testing and clean up after"""
    payload = {
        "client_id": None,
        "indirizzo": "Via Test 123",
        "comune": "Milano",
        "provincia": "MI",
        "descrizione_utente": "Cancello scorrevole da verificare per sicurezza",
        "tipo_intervento": "messa_a_norma"
    }
    response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
    assert response.status_code == 200, f"Failed to create sopralluogo: {response.text}"
    data = response.json()
    sopralluogo_id = data["sopralluogo_id"]
    yield data
    # Cleanup
    try:
        api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")
    except:
        pass


def create_test_image():
    """Create a real JPEG test image with actual visual features"""
    img = Image.new('RGB', (200, 200), color='white')
    # Add some visual features (a simple pattern)
    pixels = img.load()
    for i in range(0, 200, 20):
        for j in range(200):
            pixels[i, j] = (100, 100, 100)  # vertical gray lines
    for j in range(0, 200, 20):
        for i in range(200):
            pixels[i, j] = (50, 50, 50)  # horizontal dark gray lines
    # Add a red square in the center (simulating a gate component)
    for i in range(80, 120):
        for j in range(80, 120):
            pixels[i, j] = (200, 50, 50)
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer


class TestSopralluoghiCRUD:
    """Tests for basic CRUD operations on sopralluoghi"""

    def test_create_sopralluogo(self, api_client):
        """POST /api/sopralluoghi/ - Create new sopralluogo"""
        payload = {
            "client_id": None,
            "indirizzo": "Via Create Test 456",
            "comune": "Roma",
            "provincia": "RM",
            "descrizione_utente": "Test creation",
            "tipo_intervento": "manutenzione"
        }
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "sopralluogo_id" in data
        assert data["indirizzo"] == "Via Create Test 456"
        assert data["comune"] == "Roma"
        assert data["provincia"] == "RM"
        assert data["status"] == "bozza"
        assert data["document_number"].startswith("SOP-")
        assert data["foto"] == []
        assert data["analisi_ai"] is None
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/sopralluoghi/{data['sopralluogo_id']}")
        print(f"✓ Create sopralluogo: PASS - Created {data['sopralluogo_id']}")

    def test_list_sopralluoghi(self, api_client, created_sopralluogo):
        """GET /api/sopralluoghi/ - List sopralluoghi"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        print(f"✓ List sopralluoghi: PASS - Found {data['total']} items")

    def test_list_sopralluoghi_with_search(self, api_client):
        """GET /api/sopralluoghi/?search=UniqueSearch - Search sopralluoghi"""
        # Create a sopralluogo with unique search term
        payload = {
            "indirizzo": "Via UniqueSearch999 Test",
            "comune": "Milano",
            "provincia": "MI"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert create_response.status_code == 200
        sopralluogo_id = create_response.json()["sopralluogo_id"]
        
        try:
            response = api_client.get(f"{BASE_URL}/api/sopralluoghi/?search=UniqueSearch999")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "items" in data
            # Should find the created sopralluogo with unique search term
            found = any("UniqueSearch999" in s.get("indirizzo", "") for s in data["items"])
            assert found, "Should find sopralluogo with UniqueSearch999 in address"
            print(f"✓ List with search: PASS - Found search results")
        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")

    def test_list_sopralluoghi_with_status_filter(self, api_client, created_sopralluogo):
        """GET /api/sopralluoghi/?status=bozza - Filter by status"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/?status=bozza")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        # All items should have status=bozza
        for item in data["items"]:
            assert item["status"] == "bozza", f"Expected status=bozza, got {item['status']}"
        print(f"✓ List with status filter: PASS")

    def test_get_sopralluogo_by_id(self, api_client, created_sopralluogo):
        """GET /api/sopralluoghi/{id} - Get single sopralluogo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["sopralluogo_id"] == sopralluogo_id
        assert data["indirizzo"] == "Via Test 123"
        print(f"✓ Get sopralluogo by ID: PASS")

    def test_get_sopralluogo_not_found(self, api_client):
        """GET /api/sopralluoghi/{id} - 404 for non-existent sopralluogo"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/sop_nonexistent999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Get non-existent sopralluogo: PASS - Returns 404")

    def test_update_sopralluogo(self, api_client, created_sopralluogo):
        """PUT /api/sopralluoghi/{id} - Update sopralluogo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        payload = {
            "indirizzo": "Via Updated 789",
            "note_tecnico": "Note aggiornate dal tecnico"
        }
        response = api_client.put(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["indirizzo"] == "Via Updated 789"
        assert data["note_tecnico"] == "Note aggiornate dal tecnico"
        print(f"✓ Update sopralluogo: PASS")

    def test_delete_sopralluogo(self, api_client):
        """DELETE /api/sopralluoghi/{id} - Delete sopralluogo"""
        # Create one to delete
        payload = {
            "indirizzo": "Via Delete Test",
            "comune": "Napoli",
            "provincia": "NA"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert create_response.status_code == 200
        sopralluogo_id = create_response.json()["sopralluogo_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["deleted"] == True
        
        # Verify it's gone
        get_response = api_client.get(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")
        assert get_response.status_code == 404
        print(f"✓ Delete sopralluogo: PASS")


class TestPhotoUploadAndDownload:
    """Tests for photo upload and download functionality"""

    def test_upload_photo_jpeg(self, api_client, created_sopralluogo):
        """POST /api/sopralluoghi/{id}/upload-foto - Upload JPEG photo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        # Create a real JPEG image
        img_buffer = create_test_image()
        
        # Remove Content-Type for multipart
        headers = dict(api_client.headers)
        headers.pop("Content-Type", None)
        
        files = {
            "file": ("test_gate.jpg", img_buffer, "image/jpeg")
        }
        data = {
            "label": "panoramica"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "foto_id" in result
        assert "storage_path" in result
        assert result["label"] == "panoramica"
        assert result["content_type"] == "image/jpeg"
        print(f"✓ Upload JPEG photo: PASS - foto_id={result['foto_id']}")
        
        return result

    def test_upload_photo_png(self, api_client, created_sopralluogo):
        """POST /api/sopralluoghi/{id}/upload-foto - Upload PNG photo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        # Create a PNG image
        img = Image.new('RGB', (150, 150), color='blue')
        pixels = img.load()
        for i in range(50, 100):
            for j in range(50, 100):
                pixels[i, j] = (255, 255, 0)  # yellow square
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        files = {
            "file": ("test_motor.png", buffer, "image/png")
        }
        data = {
            "label": "motore"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["content_type"] == "image/png"
        print(f"✓ Upload PNG photo: PASS")

    def test_upload_photo_invalid_format(self, api_client, created_sopralluogo):
        """POST /api/sopralluoghi/{id}/upload-foto - Reject invalid format"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        # Try uploading a text file as an image
        files = {
            "file": ("test.txt", io.BytesIO(b"This is not an image"), "text/plain")
        }
        data = {
            "label": "test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Reject invalid format: PASS - Returns 400")

    def test_upload_photo_to_nonexistent_sopralluogo(self, api_client):
        """POST /api/sopralluoghi/{id}/upload-foto - 404 for non-existent sopralluogo"""
        img_buffer = create_test_image()
        
        files = {
            "file": ("test.jpg", img_buffer, "image/jpeg")
        }
        data = {
            "label": "test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/sop_nonexistent999/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Upload to non-existent sopralluogo: PASS - Returns 404")

    def test_delete_photo(self, api_client, created_sopralluogo):
        """DELETE /api/sopralluoghi/{id}/foto/{foto_id} - Delete photo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        # First upload a photo to delete
        img_buffer = create_test_image()
        files = {
            "file": ("to_delete.jpg", img_buffer, "image/jpeg")
        }
        data = {
            "label": "to_delete"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert upload_response.status_code == 200
        foto_id = upload_response.json()["foto_id"]
        
        # Now delete it
        response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/foto/{foto_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["deleted"] == True
        print(f"✓ Delete photo: PASS")

    def test_delete_photo_not_found(self, api_client, created_sopralluogo):
        """DELETE /api/sopralluoghi/{id}/foto/{foto_id} - 404 for non-existent photo"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/foto/foto_nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Delete non-existent photo: PASS - Returns 404")

    def test_download_photo(self, api_client, created_sopralluogo):
        """GET /api/sopralluoghi/foto/{path} - Download photo from storage"""
        sopralluogo_id = created_sopralluogo["sopralluogo_id"]
        
        # First upload a photo
        img_buffer = create_test_image()
        files = {
            "file": ("download_test.jpg", img_buffer, "image/jpeg")
        }
        data = {
            "label": "download_test"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
            headers={"Cookie": f"session_token={SESSION_TOKEN}"},
            files=files,
            data=data
        )
        assert upload_response.status_code == 200
        storage_path = upload_response.json()["storage_path"]
        
        # Download the photo
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/foto/{storage_path}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check it's actually image data
        assert len(response.content) > 0
        assert "image" in response.headers.get("Content-Type", "")
        print(f"✓ Download photo: PASS - Got {len(response.content)} bytes")


class TestArticoliCatalogo:
    """Tests for the configurable article catalog"""

    def test_list_articoli_auto_seed(self, api_client):
        """GET /api/sopralluoghi/articoli-catalogo - List articles (auto-seeds defaults)"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        # Should have auto-seeded 14 default articles
        assert len(data["items"]) >= 14, f"Expected at least 14 items, got {len(data['items'])}"
        
        # Verify some known default articles exist
        codici = [item["codice"] for item in data["items"]]
        assert "SIC-001" in codici, "Missing default article SIC-001"
        assert "SIC-003" in codici, "Missing default article SIC-003"
        assert "AUT-001" in codici, "Missing default article AUT-001"
        
        print(f"✓ List articoli (auto-seed): PASS - Found {len(data['items'])} articles")

    def test_articoli_have_required_fields(self, api_client):
        """Verify articles have all required fields"""
        response = api_client.get(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo")
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"][:3]:  # Check first 3
            assert "articolo_id" in item
            assert "codice" in item
            assert "descrizione" in item
            assert "prezzo_base" in item
            assert "unita" in item
            assert "keyword_ai" in item
            assert "categoria" in item
        
        print(f"✓ Articoli have required fields: PASS")

    def test_create_articolo(self, api_client):
        """POST /api/sopralluoghi/articoli-catalogo - Create new article"""
        payload = {
            "codice": "TEST-001",
            "descrizione": "Articolo di test per pytest",
            "prezzo_base": 99.99,
            "unita": "pz",
            "keyword_ai": "test_keyword",
            "categoria": "test",
            "note": "Articolo creato per testing"
        }
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "articolo_id" in data
        assert data["codice"] == "TEST-001"
        assert data["prezzo_base"] == 99.99
        assert data["keyword_ai"] == "test_keyword"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/{data['articolo_id']}")
        print(f"✓ Create articolo: PASS - Created {data['articolo_id']}")

    def test_update_articolo(self, api_client):
        """PUT /api/sopralluoghi/articoli-catalogo/{id} - Update article"""
        # First create an article
        payload = {
            "codice": "TEST-UPD",
            "descrizione": "To be updated",
            "prezzo_base": 50.00,
            "unita": "pz",
            "keyword_ai": "update_test",
            "categoria": "test"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo", json=payload)
        assert create_response.status_code == 200
        articolo_id = create_response.json()["articolo_id"]
        
        # Update it
        update_payload = {
            "descrizione": "Updated description",
            "prezzo_base": 75.00
        }
        response = api_client.put(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/{articolo_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["descrizione"] == "Updated description"
        assert data["prezzo_base"] == 75.00
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/{articolo_id}")
        print(f"✓ Update articolo: PASS")

    def test_delete_articolo(self, api_client):
        """DELETE /api/sopralluoghi/articoli-catalogo/{id} - Delete article"""
        # First create an article
        payload = {
            "codice": "TEST-DEL",
            "descrizione": "To be deleted",
            "prezzo_base": 10.00,
            "unita": "pz",
            "keyword_ai": "delete_test",
            "categoria": "test"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo", json=payload)
        assert create_response.status_code == 200
        articolo_id = create_response.json()["articolo_id"]
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/{articolo_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["deleted"] == True
        print(f"✓ Delete articolo: PASS")

    def test_delete_articolo_not_found(self, api_client):
        """DELETE /api/sopralluoghi/articoli-catalogo/{id} - 404 for non-existent article"""
        response = api_client.delete(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/art_nonexistent999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Delete non-existent articolo: PASS - Returns 404")

    def test_update_articolo_not_found(self, api_client):
        """PUT /api/sopralluoghi/articoli-catalogo/{id} - 404 for non-existent article"""
        payload = {"descrizione": "test"}
        response = api_client.put(f"{BASE_URL}/api/sopralluoghi/articoli-catalogo/art_nonexistent999", json=payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Update non-existent articolo: PASS - Returns 404")


class TestAIAnalysis:
    """Tests for AI analysis endpoint (validation only, no actual GPT-4o calls)"""

    def test_analizza_requires_photos(self, api_client):
        """POST /api/sopralluoghi/{id}/analizza - Requires photos to be uploaded first"""
        # Create a fresh sopralluogo without photos
        payload = {
            "indirizzo": "Via Analisi Test",
            "comune": "Bologna",
            "provincia": "BO"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert create_response.status_code == 200
        sopralluogo_id = create_response.json()["sopralluogo_id"]
        
        try:
            # Try to analyze without photos
            response = api_client.post(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/analizza")
            # Should return 400 because no photos uploaded
            assert response.status_code == 400, f"Expected 400 (no photos), got {response.status_code}: {response.text}"
            
            error_msg = response.json().get("detail", "")
            assert "foto" in error_msg.lower(), f"Error should mention photos: {error_msg}"
            print(f"✓ Analizza requires photos: PASS - Returns 400 without photos")
        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")

    def test_analizza_not_found(self, api_client):
        """POST /api/sopralluoghi/{id}/analizza - 404 for non-existent sopralluogo"""
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/sop_nonexistent999/analizza")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Analizza non-existent sopralluogo: PASS - Returns 404")


class TestGeneraPreventivo:
    """Tests for preventivo generation endpoint (validation only)"""

    def test_genera_preventivo_requires_analysis(self, api_client):
        """POST /api/sopralluoghi/{id}/genera-preventivo - Requires AI analysis first"""
        # Create a fresh sopralluogo without analysis
        payload = {
            "indirizzo": "Via Preventivo Test",
            "comune": "Firenze",
            "provincia": "FI"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert create_response.status_code == 200
        sopralluogo_id = create_response.json()["sopralluogo_id"]
        
        try:
            # Try to generate preventivo without analysis
            response = api_client.post(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/genera-preventivo")
            # Should return 400 because no analysis done
            assert response.status_code == 400, f"Expected 400 (no analysis), got {response.status_code}: {response.text}"
            
            error_msg = response.json().get("detail", "")
            assert "analisi" in error_msg.lower(), f"Error should mention analysis: {error_msg}"
            print(f"✓ Genera preventivo requires analysis: PASS - Returns 400 without analysis")
        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")

    def test_genera_preventivo_not_found(self, api_client):
        """POST /api/sopralluoghi/{id}/genera-preventivo - 404 for non-existent sopralluogo"""
        response = api_client.post(f"{BASE_URL}/api/sopralluoghi/sop_nonexistent999/genera-preventivo")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Genera preventivo non-existent: PASS - Returns 404")


class TestEndToEndWorkflow:
    """End-to-end workflow test without AI (validation of data flow)"""

    def test_full_workflow_up_to_analysis_validation(self, api_client):
        """Test complete workflow: Create -> Upload Photos -> Verify analysis requires photos"""
        # 1. Create sopralluogo
        payload = {
            "indirizzo": "Via Workflow Test 999",
            "comune": "Torino",
            "provincia": "TO",
            "descrizione_utente": "Test workflow cancello automatico",
            "tipo_intervento": "messa_a_norma"
        }
        create_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/", json=payload)
        assert create_response.status_code == 200
        sopralluogo_id = create_response.json()["sopralluogo_id"]
        print(f"  1. Created sopralluogo: {sopralluogo_id}")
        
        try:
            # 2. Verify it appears in list
            list_response = api_client.get(f"{BASE_URL}/api/sopralluoghi/?search=Workflow")
            assert list_response.status_code == 200
            items = list_response.json()["items"]
            found = any(s["sopralluogo_id"] == sopralluogo_id for s in items)
            assert found, "Sopralluogo should appear in list"
            print(f"  2. Verified in list: PASS")
            
            # 3. Upload a photo
            img_buffer = create_test_image()
            files = {"file": ("workflow_photo.jpg", img_buffer, "image/jpeg")}
            data = {"label": "panoramica"}
            
            upload_response = requests.post(
                f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/upload-foto",
                headers={"Cookie": f"session_token={SESSION_TOKEN}"},
                files=files,
                data=data
            )
            assert upload_response.status_code == 200
            foto_id = upload_response.json()["foto_id"]
            print(f"  3. Uploaded photo: {foto_id}")
            
            # 4. Verify photo is attached
            get_response = api_client.get(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")
            assert get_response.status_code == 200
            sopralluogo = get_response.json()
            assert len(sopralluogo["foto"]) >= 1
            print(f"  4. Photo attached: PASS")
            
            # 5. Verify genera-preventivo still requires analysis (even with photos)
            preventivo_response = api_client.post(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}/genera-preventivo")
            assert preventivo_response.status_code == 400, "Should require analysis before preventivo"
            print(f"  5. Preventivo validation: PASS (requires analysis)")
            
            print(f"✓ End-to-end workflow (validation): PASS")
            
        finally:
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/sopralluoghi/{sopralluogo_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

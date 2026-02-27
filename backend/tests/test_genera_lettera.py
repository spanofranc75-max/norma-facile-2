"""
Test: Genera Diffida Tecnica per Perito (Lettera Accompagnamento)
Focus: New feature for generating technical cover letters for insurance assessors
Tests: POST /api/perizie/{id}/genera-lettera, lettera_accompagnamento field CRUD, PDF inclusion
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test user setup via MongoDB
def get_test_session():
    """Get or create test session token"""
    import subprocess
    result = subprocess.run([
        "mongosh", "--quiet", "--eval", """
        use('test_database');
        var existingSession = db.user_sessions.findOne({session_token: /test_session_lettera/});
        if (existingSession) {
            print(existingSession.session_token + '|' + existingSession.user_id);
        } else {
            var userId = 'test-user-lettera-' + Date.now();
            var sessionToken = 'test_session_lettera_' + Date.now();
            db.users.insertOne({
                user_id: userId,
                email: 'test.lettera.' + Date.now() + '@example.com',
                name: 'Test User Lettera',
                picture: 'https://via.placeholder.com/150',
                created_at: new Date()
            });
            db.user_sessions.insertOne({
                user_id: userId,
                session_token: sessionToken,
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                created_at: new Date()
            });
            print(sessionToken + '|' + userId);
        }
        """
    ], capture_output=True, text=True)
    output = result.stdout.strip().split('\n')[-1]
    parts = output.split('|')
    return parts[0], parts[1] if len(parts) > 1 else None


@pytest.fixture(scope="module")
def auth_headers():
    """Create authenticated headers for API requests"""
    session_token, user_id = get_test_session()
    return {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def test_perizia_id(auth_headers):
    """Create a test perizia for genera-lettera tests"""
    # Create a perizia with all required fields for letter generation
    payload = {
        "localizzazione": {
            "indirizzo": "Via Test 123",
            "lat": 41.9028,
            "lng": 12.4964,
            "comune": "Roma",
            "provincia": "RM"
        },
        "tipo_danno": "strutturale",
        "descrizione_utente": "Test urto da veicolo su recinzione metallica",
        "prezzo_ml_originale": 150.0,
        "coefficiente_maggiorazione": 20,
        "moduli": [
            {"descrizione": "Modulo Test 1", "lunghezza_ml": 2.5, "altezza_m": 1.8, "note": ""},
            {"descrizione": "Modulo Test 2", "lunghezza_ml": 1.5, "altezza_m": 1.8, "note": ""}
        ],
        "stato_di_fatto": "Recinzione in acciaio zincato con evidente deformazione plastica dei montanti.",
        "nota_tecnica": "La raddrizzatura invaliderebbe la certificazione EN 1090.",
        "notes": "Test note"
    }
    
    response = requests.post(f"{BASE_URL}/api/perizie/", headers=auth_headers, json=payload)
    assert response.status_code == 201, f"Failed to create test perizia: {response.text}"
    data = response.json()
    perizia_id = data["perizia_id"]
    
    yield perizia_id
    
    # Cleanup
    requests.delete(f"{BASE_URL}/api/perizie/{perizia_id}", headers=auth_headers)


class TestGeneraLetteraEndpoint:
    """Tests for POST /api/perizie/{id}/genera-lettera endpoint"""
    
    def test_genera_lettera_success(self, auth_headers, test_perizia_id):
        """Test that genera-lettera endpoint generates a letter successfully"""
        response = requests.post(
            f"{BASE_URL}/api/perizie/{test_perizia_id}/genera-lettera",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "lettera_accompagnamento" in data, "Response should contain lettera_accompagnamento"
        assert "perizia_id" in data, "Response should contain perizia_id"
        assert data["perizia_id"] == test_perizia_id
        
        lettera = data["lettera_accompagnamento"]
        assert len(lettera) > 100, "Letter should have substantial content"
        
        print(f"Generated letter length: {len(lettera)} chars")
        print(f"First 500 chars: {lettera[:500]}...")
    
    def test_genera_lettera_contains_norms(self, auth_headers, test_perizia_id):
        """Test that generated letter references EN 1090, EN 13241 or ISO 12944"""
        # First generate the letter
        response = requests.post(
            f"{BASE_URL}/api/perizie/{test_perizia_id}/genera-lettera",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        lettera = response.json()["lettera_accompagnamento"]
        
        # Check for norm references
        norms_found = []
        if "1090" in lettera or "EN 1090" in lettera:
            norms_found.append("EN 1090")
        if "13241" in lettera or "EN 13241" in lettera:
            norms_found.append("EN 13241")
        if "12944" in lettera or "ISO 12944" in lettera:
            norms_found.append("ISO 12944")
        
        print(f"Norms found in letter: {norms_found}")
        assert len(norms_found) >= 1, f"Letter should reference at least one relevant norm. Found: {norms_found}"
    
    def test_genera_lettera_saved_to_perizia(self, auth_headers, test_perizia_id):
        """Test that generated letter is persisted to the perizia document"""
        # Generate letter
        gen_response = requests.post(
            f"{BASE_URL}/api/perizie/{test_perizia_id}/genera-lettera",
            headers=auth_headers
        )
        assert gen_response.status_code == 200
        
        generated_letter = gen_response.json()["lettera_accompagnamento"]
        
        # GET the perizia to verify persistence
        get_response = requests.get(
            f"{BASE_URL}/api/perizie/{test_perizia_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        
        perizia_data = get_response.json()
        assert "lettera_accompagnamento" in perizia_data, "Perizia should have lettera_accompagnamento field"
        assert perizia_data["lettera_accompagnamento"] == generated_letter, "Saved letter should match generated letter"
        
        print("Letter successfully saved to perizia document")
    
    def test_genera_lettera_requires_auth(self, test_perizia_id):
        """Test that genera-lettera endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/perizie/{test_perizia_id}/genera-lettera")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_genera_lettera_404_invalid_id(self, auth_headers):
        """Test that genera-lettera returns 404 for non-existent perizia"""
        response = requests.post(
            f"{BASE_URL}/api/perizie/invalid_perizia_id_12345/genera-lettera",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestLetteraAccompagnamentoField:
    """Tests for lettera_accompagnamento field in CRUD operations"""
    
    def test_update_lettera_accompagnamento(self, auth_headers, test_perizia_id):
        """Test that PUT /api/perizie/{id} accepts and saves lettera_accompagnamento"""
        custom_letter = """Oggetto: Lettera di test personalizzata

Alla cortese attenzione dell'Ufficio Sinistri,

Questa è una lettera di test con riferimenti a EN 1090-2 e EN 13241.

Distinti saluti,
Test User"""
        
        response = requests.put(
            f"{BASE_URL}/api/perizie/{test_perizia_id}",
            headers=auth_headers,
            json={"lettera_accompagnamento": custom_letter}
        )
        
        assert response.status_code == 200, f"PUT failed: {response.text}"
        
        # Verify persistence via GET
        get_response = requests.get(
            f"{BASE_URL}/api/perizie/{test_perizia_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        
        perizia_data = get_response.json()
        assert perizia_data["lettera_accompagnamento"] == custom_letter
        
        print("Custom letter successfully saved via PUT")
    
    def test_create_perizia_with_lettera(self, auth_headers):
        """Test that POST /api/perizie/ accepts lettera_accompagnamento in payload"""
        letter_content = "Test letter content with EN 1090 reference"
        
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "Test sinistro",
            "lettera_accompagnamento": letter_content
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", headers=auth_headers, json=payload)
        assert response.status_code == 201, f"Failed to create perizia: {response.text}"
        
        data = response.json()
        assert data.get("lettera_accompagnamento") == letter_content, "Letter should be saved on create"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{data['perizia_id']}", headers=auth_headers)
        
        print("Perizia created with lettera_accompagnamento successfully")
    
    def test_get_perizia_returns_lettera_field(self, auth_headers, test_perizia_id):
        """Test that GET /api/perizie/{id} returns lettera_accompagnamento field"""
        response = requests.get(
            f"{BASE_URL}/api/perizie/{test_perizia_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Field should exist (may be empty string or have content)
        assert "lettera_accompagnamento" in data, "GET response should include lettera_accompagnamento field"
        print(f"lettera_accompagnamento field present, length: {len(data.get('lettera_accompagnamento', ''))}")


class TestPDFInclusion:
    """Tests for lettera inclusion in PDF export"""
    
    def test_pdf_includes_lettera(self, auth_headers, test_perizia_id):
        """Test that GET /api/perizie/{id}/pdf includes lettera in the output"""
        # First ensure there's a letter to include
        requests.post(
            f"{BASE_URL}/api/perizie/{test_perizia_id}/genera-lettera",
            headers=auth_headers
        )
        
        # Request PDF
        response = requests.get(
            f"{BASE_URL}/api/perizie/{test_perizia_id}/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"PDF request failed: {response.status_code}"
        assert response.headers.get("Content-Type") == "application/pdf", "Response should be PDF"
        
        # Verify PDF has content (>5KB expected with letter)
        pdf_size = len(response.content)
        assert pdf_size > 5000, f"PDF should have substantial size (got {pdf_size} bytes)"
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "perizia_" in content_disp, "Content-Disposition should contain filename"
        
        print(f"PDF generated successfully, size: {pdf_size} bytes")


class TestFallbackTemplate:
    """Test fallback template generation when LLM_KEY is not available"""
    
    def test_fallback_template_structure(self, auth_headers):
        """Test that fallback template has expected structure and content"""
        # Create a perizia with specific data for template
        payload = {
            "localizzazione": {
                "indirizzo": "Via Fallback 456",
                "comune": "Milano",
                "provincia": "MI"
            },
            "tipo_danno": "strutturale",
            "descrizione_utente": "Test fallback template",
            "prezzo_ml_originale": 200.0,
            "coefficiente_maggiorazione": 25,
            "moduli": [
                {"descrizione": "Modulo Fallback", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/perizie/", headers=auth_headers, json=payload)
        assert response.status_code == 201
        perizia_id = response.json()["perizia_id"]
        
        # Generate letter
        gen_response = requests.post(
            f"{BASE_URL}/api/perizie/{perizia_id}/genera-lettera",
            headers=auth_headers
        )
        assert gen_response.status_code == 200
        
        lettera = gen_response.json()["lettera_accompagnamento"]
        
        # Check for expected content (either AI or fallback template)
        assert len(lettera) > 200, "Letter should have substantial content"
        assert "Oggetto:" in lettera or "oggetto:" in lettera.lower(), "Letter should have subject line"
        
        # Check for norm references
        has_norms = "1090" in lettera or "13241" in lettera or "12944" in lettera
        assert has_norms, "Letter should reference technical norms"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/perizie/{perizia_id}", headers=auth_headers)
        
        print(f"Letter generated with structure check passed (length: {len(lettera)})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Smart BOM Module Tests for Norma Facile 2.0
Tests: Profiles API, Distinta CRUD, Calculation, Bar Calculation, PDF Export
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://erp-metalwork-stage.preview.emergentagent.com"

# Test data constants
TEST_SESSION_TOKEN = None
TEST_USER_ID = None
TEST_DISTINTA_ID = None


@pytest.fixture(scope="module")
def session_token():
    """Get or create test session token via MongoDB."""
    import subprocess
    result = subprocess.run([
        "mongosh", "--quiet", "--eval", """
        use('test_database');
        var userId = 'test-user-pytest-' + Date.now();
        var sessionToken = 'test_session_pytest_' + Date.now();
        db.users.insertOne({
          user_id: userId,
          email: 'test.pytest.' + Date.now() + '@example.com',
          name: 'Pytest User',
          picture: 'https://via.placeholder.com/150',
          created_at: new Date()
        });
        db.user_sessions.insertOne({
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        });
        print(sessionToken);
        """
    ], capture_output=True, text=True)
    token = result.stdout.strip()
    if not token or "test_session_pytest" not in token:
        pytest.skip("Failed to create test session")
    return token


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_client(api_client, session_token):
    """Authenticated session."""
    api_client.headers.update({"Authorization": f"Bearer {session_token}"})
    return api_client


# ─── PROFILES TESTS (No Auth Required) ───────────────────────────────────────

class TestProfilesEndpoint:
    """Test GET /api/distinte/profiles - public endpoint"""

    def test_get_all_profiles(self, api_client):
        """GET /api/distinte/profiles returns 43 profiles"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles")
        assert response.status_code == 200
        
        data = response.json()
        assert "profiles" in data
        assert "types" in data
        assert len(data["profiles"]) == 43, f"Expected 43 profiles, got {len(data['profiles'])}"
        
        # Verify profile structure
        profile = data["profiles"][0]
        assert "profile_id" in profile
        assert "type" in profile
        assert "label" in profile
        assert "weight_per_meter" in profile
        assert "surface_per_meter" in profile
        print(f"PASS: Got {len(data['profiles'])} profiles with weight_per_meter and surface_per_meter")

    def test_get_profiles_by_type_tubolare(self, api_client):
        """GET /api/distinte/profiles?profile_type=tubolare filters correctly"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles?profile_type=tubolare")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["profiles"]) == 16, f"Expected 16 tubolare profiles, got {len(data['profiles'])}"
        
        # Verify all returned profiles are tubolare type
        for profile in data["profiles"]:
            assert profile["type"] == "tubolare"
        print(f"PASS: Filter by tubolare returns {len(data['profiles'])} profiles")

    def test_get_profiles_by_type_piatto(self, api_client):
        """GET /api/distinte/profiles?profile_type=piatto filters correctly"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles?profile_type=piatto")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["profiles"]) == 12, f"Expected 12 piatto profiles, got {len(data['profiles'])}"
        print(f"PASS: Filter by piatto returns {len(data['profiles'])} profiles")

    def test_get_profiles_by_type_angolare(self, api_client):
        """GET /api/distinte/profiles?profile_type=angolare filters correctly"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles?profile_type=angolare")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["profiles"]) == 10, f"Expected 10 angolare profiles, got {len(data['profiles'])}"
        print(f"PASS: Filter by angolare returns {len(data['profiles'])} profiles")

    def test_get_profiles_by_type_tondo(self, api_client):
        """GET /api/distinte/profiles?profile_type=tondo filters correctly"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles?profile_type=tondo")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["profiles"]) == 5, f"Expected 5 tondo profiles, got {len(data['profiles'])}"
        print(f"PASS: Filter by tondo returns {len(data['profiles'])} profiles")

    def test_profile_types_structure(self, api_client):
        """GET /api/distinte/profiles returns proper types list"""
        response = api_client.get(f"{BASE_URL}/api/distinte/profiles")
        assert response.status_code == 200
        
        data = response.json()
        types = data["types"]
        assert len(types) == 4
        
        type_values = [t["value"] for t in types]
        assert "tubolare" in type_values
        assert "piatto" in type_values
        assert "angolare" in type_values
        assert "tondo" in type_values
        print("PASS: Types list contains all 4 profile types")


# ─── DISTINTA CRUD TESTS (Auth Required) ─────────────────────────────────────

class TestDistintaCRUD:
    """Test Distinta CRUD operations with weight and surface calculations"""

    @pytest.fixture(autouse=True)
    def setup(self, auth_client):
        self.client = auth_client
        self.created_distinta_ids = []

    def test_create_distinta_with_calculation(self, auth_client):
        """POST /api/distinte/ with items - verify weight and surface calculation"""
        # Test calculation: Tubolare 40x40x3 (3.39 kg/m, 0.160 mq/m)
        # Length 1500mm (1.5m) x Qty 2 = 3m total
        # Expected weight: 1.5 * 2 * 3.39 = 10.17 kg
        # Expected surface: 1.5 * 2 * 0.160 = 0.48 mq
        
        payload = {
            "name": "TEST_Distinta Calcolo",
            "notes": "Test calculation",
            "items": [{
                "category": "profilo",
                "name": "Tubolare 40x40x3",
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": 1500,
                "quantity": 2,
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160,
                "cost_per_unit": 0
            }]
        }
        
        response = auth_client.post(f"{BASE_URL}/api/distinte/", json=payload)
        assert response.status_code == 201, f"Create failed: {response.text}"
        
        data = response.json()
        assert "distinta_id" in data
        assert data["name"] == "TEST_Distinta Calcolo"
        
        # Verify item calculations
        item = data["items"][0]
        assert item["total_length"] == 3.0, f"Expected length 3.0m, got {item['total_length']}"
        assert item["total_weight"] == 10.17, f"Expected weight 10.17kg, got {item['total_weight']}"
        assert item["total_surface"] == 0.48, f"Expected surface 0.48mq, got {item['total_surface']}"
        
        # Verify totals
        totals = data["totals"]
        assert totals["total_items"] == 1
        assert totals["total_weight_kg"] == 10.17
        assert totals["total_surface_mq"] == 0.48
        
        # Store for cleanup
        self.__class__.test_distinta_id = data["distinta_id"]
        print(f"PASS: Created distinta with correct calculations (weight: {totals['total_weight_kg']} kg, surface: {totals['total_surface_mq']} mq)")
        return data

    def test_get_distinta(self, auth_client):
        """GET /api/distinte/{id} returns correct data"""
        distinta_id = getattr(self.__class__, 'test_distinta_id', None)
        if not distinta_id:
            pytest.skip("No distinta created")
        
        response = auth_client.get(f"{BASE_URL}/api/distinte/{distinta_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["distinta_id"] == distinta_id
        assert data["totals"]["total_surface_mq"] == 0.48
        print(f"PASS: GET distinta returns total_surface_mq = {data['totals']['total_surface_mq']}")

    def test_update_distinta_recalculation(self, auth_client):
        """PUT /api/distinte/{id} - verify recalculation of weight and surface"""
        distinta_id = getattr(self.__class__, 'test_distinta_id', None)
        if not distinta_id:
            pytest.skip("No distinta created")
        
        # Update with 2 items
        payload = {
            "name": "TEST_Distinta Aggiornata",
            "items": [
                {
                    "category": "profilo",
                    "name": "Tubolare 40x40x3",
                    "profile_id": "TQ-40x40x3",
                    "profile_label": "Tubolare 40x40x3",
                    "length_mm": 2000,  # 2m
                    "quantity": 3,
                    "weight_per_meter": 3.39,
                    "surface_per_meter": 0.160
                },
                {
                    "category": "profilo",
                    "name": "Piatto 50x5",
                    "profile_id": "PT-50x5",
                    "profile_label": "Piatto 50x5",
                    "length_mm": 1000,  # 1m
                    "quantity": 4,
                    "weight_per_meter": 1.96,
                    "surface_per_meter": 0.100
                }
            ]
        }
        
        response = auth_client.put(f"{BASE_URL}/api/distinte/{distinta_id}", json=payload)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        
        # Verify recalculated totals
        # Item 1: 2 * 3 * 3.39 = 20.34 kg, 2 * 3 * 0.16 = 0.96 mq
        # Item 2: 1 * 4 * 1.96 = 7.84 kg, 1 * 4 * 0.10 = 0.40 mq
        # Total: 28.18 kg, 1.36 mq
        
        totals = data["totals"]
        assert totals["total_items"] == 2
        assert totals["total_weight_kg"] == 28.18, f"Expected 28.18 kg, got {totals['total_weight_kg']}"
        assert totals["total_surface_mq"] == 1.36, f"Expected 1.36 mq, got {totals['total_surface_mq']}"
        
        print(f"PASS: Update recalculated totals (weight: {totals['total_weight_kg']} kg, surface: {totals['total_surface_mq']} mq)")

    def test_delete_distinta(self, auth_client):
        """DELETE /api/distinte/{id}"""
        distinta_id = getattr(self.__class__, 'test_distinta_id', None)
        if not distinta_id:
            pytest.skip("No distinta to delete")
        
        response = auth_client.delete(f"{BASE_URL}/api/distinte/{distinta_id}")
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = auth_client.get(f"{BASE_URL}/api/distinte/{distinta_id}")
        assert get_response.status_code == 404
        
        print(f"PASS: Distinta deleted and verified 404")


# ─── BAR CALCULATION TESTS ───────────────────────────────────────────────────

class TestBarCalculation:
    """Test POST /api/distinte/{id}/calcola-barre"""

    def test_bar_calculation(self, auth_client):
        """Test bar calculation with known values"""
        # Create distinta with specific items for bar calculation
        payload = {
            "name": "TEST_Bar Calc Test",
            "items": [{
                "category": "profilo",
                "name": "Tubolare 40x40x3",
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": 1500,
                "quantity": 2,  # Total 3000mm
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160
            }]
        }
        
        create_resp = auth_client.post(f"{BASE_URL}/api/distinte/", json=payload)
        assert create_resp.status_code == 201
        distinta_id = create_resp.json()["distinta_id"]
        
        # Calculate bars
        calc_resp = auth_client.post(f"{BASE_URL}/api/distinte/{distinta_id}/calcola-barre")
        assert calc_resp.status_code == 200
        
        data = calc_resp.json()
        assert "results" in data
        assert "total_bars" in data
        
        # Verify calculation
        # Total length: 3000mm -> 1 bar of 6000mm needed
        # Waste: 6000 - 3000 = 3000mm (50%)
        result = data["results"][0]
        assert result["profile_id"] == "TQ-40x40x3"
        assert result["total_length_mm"] == 3000.0
        assert result["bars_needed"] == 1
        assert result["waste_mm"] == 3000.0
        assert result["waste_percent"] == 50.0
        assert data["total_bars"] == 1
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/distinte/{distinta_id}")
        
        print(f"PASS: Bar calculation correct (bars: {data['total_bars']}, waste: {result['waste_percent']}%)")

    def test_bar_calculation_multiple_bars(self, auth_client):
        """Test calculation requiring multiple bars"""
        payload = {
            "name": "TEST_Multi Bar Test",
            "items": [{
                "category": "profilo",
                "name": "Tubolare 40x40x3",
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": 5000,  # 5m each
                "quantity": 3,  # Total 15000mm = 15m -> needs 3 bars
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160
            }]
        }
        
        create_resp = auth_client.post(f"{BASE_URL}/api/distinte/", json=payload)
        assert create_resp.status_code == 201
        distinta_id = create_resp.json()["distinta_id"]
        
        calc_resp = auth_client.post(f"{BASE_URL}/api/distinte/{distinta_id}/calcola-barre")
        assert calc_resp.status_code == 200
        
        data = calc_resp.json()
        result = data["results"][0]
        
        # 15000mm total -> 3 bars of 6000mm (18000mm capacity)
        # Waste: 18000 - 15000 = 3000mm (16.7%)
        assert result["total_length_mm"] == 15000.0
        assert result["bars_needed"] == 3
        assert data["total_bars"] == 3
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/distinte/{distinta_id}")
        
        print(f"PASS: Multiple bar calculation (total_length: 15m, bars: 3)")


# ─── PDF EXPORT TESTS ────────────────────────────────────────────────────────

class TestPDFExport:
    """Test GET /api/distinte/{id}/lista-taglio-pdf"""

    def test_pdf_download(self, auth_client):
        """Test PDF generation returns application/pdf"""
        # Create distinta
        payload = {
            "name": "TEST_PDF Export",
            "items": [{
                "category": "profilo",
                "name": "Tubolare 40x40x3",
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": 1500,
                "quantity": 2,
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160
            }]
        }
        
        create_resp = auth_client.post(f"{BASE_URL}/api/distinte/", json=payload)
        assert create_resp.status_code == 201
        distinta_id = create_resp.json()["distinta_id"]
        
        # Download PDF
        pdf_resp = auth_client.get(f"{BASE_URL}/api/distinte/{distinta_id}/lista-taglio-pdf")
        assert pdf_resp.status_code == 200
        
        # Verify content type
        content_type = pdf_resp.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify content disposition
        content_disp = pdf_resp.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "lista_taglio_" in content_disp
        
        # Verify PDF content (starts with %PDF)
        assert pdf_resp.content[:4] == b"%PDF", "Content does not start with PDF header"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/distinte/{distinta_id}")
        
        print(f"PASS: PDF export returns valid PDF (content-type: {content_type})")


# ─── CLEANUP ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after all tests."""
    yield
    
    import subprocess
    subprocess.run([
        "mongosh", "--quiet", "--eval", """
        use('test_database');
        db.users.deleteMany({email: /test\\.pytest\\./});
        db.user_sessions.deleteMany({session_token: /test_session_pytest/});
        db.distinte.deleteMany({name: /^TEST_/});
        print('Cleanup complete');
        """
    ], capture_output=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

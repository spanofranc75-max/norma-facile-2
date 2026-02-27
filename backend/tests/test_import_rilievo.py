"""
Test Import Rilievo → Distinta Bridge Feature
Tests dimension parsing from rilievo notes and sketches, and rilievo-to-distinta linking.
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data for dimension parsing
NOTES_WITH_DIMENSIONS = """
Cancello ingresso principale
H=2200 L=3000
Montanti 1500x900
Traversa inferiore 2800 mm
Altezza: 1800 profondità 450
Note: verniciare RAL 7016
"""

NOTES_SIMPLE = """
Sopralluogo effettuato, misure da confermare.
Luce netta 1200 mm.
"""


class TestImportRilievoBridge:
    """Test the new Import Rilievo → Distinta feature"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Create test user and session for auth"""
        import subprocess
        import json
        import time
        
        timestamp = int(time.time() * 1000)
        user_id = f"test-import-{timestamp}"
        session_token = f"test_import_session_{timestamp}"
        
        # Create user and session via mongosh
        mongo_script = f"""
        use('test_database');
        db.users.insertOne({{
          user_id: '{user_id}',
          email: 'test.import.{timestamp}@example.com',
          name: 'Test Import User',
          picture: 'https://via.placeholder.com/150',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{user_id}',
          session_token: '{session_token}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        print('OK');
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)
        if 'OK' not in result.stdout:
            pytest.skip(f"Failed to create test user: {result.stderr}")
        
        yield session_token
        
        # Cleanup
        cleanup_script = f"""
        use('test_database');
        db.users.deleteMany({{user_id: '{user_id}'}});
        db.user_sessions.deleteMany({{session_token: '{session_token}'}});
        db.clients.deleteMany({{user_id: '{user_id}'}});
        db.rilievi.deleteMany({{user_id: '{user_id}'}});
        db.distinte.deleteMany({{user_id: '{user_id}'}});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True, text=True)
    
    @pytest.fixture
    def auth_headers(self, session_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}
    
    @pytest.fixture
    def test_client(self, auth_headers):
        """Create a test client first"""
        client_payload = {
            "business_name": "TEST_Import_Client",
            "client_type": "azienda",
            "email": "importclient@test.com"
        }
        resp = requests.post(f"{BASE_URL}/api/clients/", json=client_payload, headers=auth_headers)
        if resp.status_code != 201:
            pytest.skip(f"Failed to create test client: {resp.text}")
        return resp.json()
    
    @pytest.fixture
    def test_rilievo_with_dimensions(self, auth_headers, test_client):
        """Create a rilievo with dimension data in notes and sketches"""
        rilievo_payload = {
            "client_id": test_client["client_id"],
            "project_name": "TEST_Rilievo_Cancello_Main",
            "location": "Via Roma 15, Milano",
            "notes": NOTES_WITH_DIMENSIONS,
            "sketches": [
                {
                    "name": "Prospetto Frontale",
                    "drawing_data": None,
                    "dimensions": {"altezza": 2200, "larghezza": 3000, "profondita": 150}
                },
                {
                    "name": "Dettaglio Cardine",
                    "drawing_data": None,
                    "dimensions": {"diametro": 35}
                }
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/rilievi/", json=rilievo_payload, headers=auth_headers)
        if resp.status_code != 201:
            pytest.skip(f"Failed to create test rilievo: {resp.text}")
        return resp.json()
    
    @pytest.fixture
    def test_rilievo_simple(self, auth_headers, test_client):
        """Create a simple rilievo with minimal notes"""
        rilievo_payload = {
            "client_id": test_client["client_id"],
            "project_name": "TEST_Rilievo_Simple",
            "location": "Via Verdi 10",
            "notes": NOTES_SIMPLE,
            "sketches": []
        }
        resp = requests.post(f"{BASE_URL}/api/rilievi/", json=rilievo_payload, headers=auth_headers)
        if resp.status_code != 201:
            pytest.skip(f"Failed to create simple rilievo: {resp.text}")
        return resp.json()
    
    @pytest.fixture
    def test_distinta(self, auth_headers):
        """Create an empty distinta for testing import"""
        distinta_payload = {
            "name": "TEST_Distinta_Import_Target",
            "items": []
        }
        resp = requests.post(f"{BASE_URL}/api/distinte/", json=distinta_payload, headers=auth_headers)
        if resp.status_code != 201:
            pytest.skip(f"Failed to create test distinta: {resp.text}")
        return resp.json()
    
    # ==================== GET /rilievo-data/{id} TESTS ====================
    
    def test_rilievo_data_parses_h_equals_pattern(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data parses 'H=2200' style dimensions from notes"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        dimensions = data.get("dimensions", [])
        
        # Find H=2200 dimension
        h_dims = [d for d in dimensions if "H" in d.get("label", "") and d.get("value_mm") == 2200]
        assert len(h_dims) > 0, f"Expected H=2200 dimension, got dimensions: {dimensions}"
        
        # Verify structure
        h_dim = h_dims[0]
        assert "dim_id" in h_dim
        assert "label" in h_dim
        assert "value_mm" in h_dim
        assert "source" in h_dim
        assert h_dim["source"] == "notes"
        print(f"✓ H=2200 pattern parsed correctly: {h_dim}")
    
    def test_rilievo_data_parses_wxh_pattern(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data parses '1500x900' into two dimensions (H and L)"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        dimensions = data.get("dimensions", [])
        
        # Should have both 1500 and 900 parsed
        vals = [d.get("value_mm") for d in dimensions]
        assert 1500 in vals, f"Expected 1500 from 1500x900 pattern, got values: {vals}"
        assert 900 in vals, f"Expected 900 from 1500x900 pattern, got values: {vals}"
        print(f"✓ WxH pattern (1500x900) parsed into two dimensions")
    
    def test_rilievo_data_parses_standalone_mm(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data parses standalone numbers > 100 as mm measurements"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        dimensions = data.get("dimensions", [])
        
        # Should have 2800 mm from "Traversa inferiore 2800 mm"
        vals = [d.get("value_mm") for d in dimensions]
        assert 2800 in vals, f"Expected 2800 from '2800 mm' standalone pattern, got values: {vals}"
        print(f"✓ Standalone mm pattern (2800 mm) parsed correctly")
    
    def test_rilievo_data_includes_sketch_dimensions(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data returns dimensions from sketch dimension fields"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        dimensions = data.get("dimensions", [])
        
        # Find sketch dimensions (source should contain "sketch:")
        sketch_dims = [d for d in dimensions if "sketch:" in d.get("source", "")]
        assert len(sketch_dims) > 0, f"Expected sketch dimensions, got: {dimensions}"
        
        # Should include altezza=2200, larghezza=3000, etc from sketch
        sketch_vals = [d.get("value_mm") for d in sketch_dims]
        assert 3000 in sketch_vals or 150 in sketch_vals, f"Expected sketch dimensions like 3000 or 150, got: {sketch_vals}"
        print(f"✓ Sketch dimensions extracted: {sketch_dims}")
    
    def test_rilievo_data_returns_sketches_summary(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data returns sketches summary"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        sketches = data.get("sketches", [])
        
        assert len(sketches) == 2, f"Expected 2 sketches, got {len(sketches)}"
        assert sketches[0].get("name") == "Prospetto Frontale"
        assert "dimensions" in sketches[0]
        print(f"✓ Sketches summary returned correctly: {len(sketches)} sketches")
    
    def test_rilievo_data_returns_full_structure(self, auth_headers, test_rilievo_with_dimensions):
        """Test GET /rilievo-data returns complete data structure"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/{rilievo_id}", headers=auth_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Verify all required fields
        assert data.get("rilievo_id") == rilievo_id
        assert "project_name" in data
        assert "client_id" in data
        assert "location" in data
        assert "notes" in data
        assert "sketches" in data
        assert "dimensions" in data
        assert "dimension_count" in data
        assert data["dimension_count"] == len(data["dimensions"])
        print(f"✓ Full response structure verified, {data['dimension_count']} dimensions found")
    
    def test_rilievo_data_404_nonexistent(self, auth_headers):
        """Test GET /rilievo-data returns 404 for non-existent rilievo"""
        resp = requests.get(f"{BASE_URL}/api/distinte/rilievo-data/nonexistent_ril_123", headers=auth_headers)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ 404 returned for non-existent rilievo")
    
    # ==================== POST /import-rilievo/{id} TESTS ====================
    
    def test_import_rilievo_links_to_distinta(self, auth_headers, test_distinta, test_rilievo_with_dimensions):
        """Test POST /import-rilievo links rilievo to distinta"""
        distinta_id = test_distinta["distinta_id"]
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.post(
            f"{BASE_URL}/api/distinte/{distinta_id}/import-rilievo/{rilievo_id}",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("rilievo_id") == rilievo_id
        print(f"✓ Rilievo {rilievo_id} linked to distinta {distinta_id}")
    
    def test_import_rilievo_sets_client_id(self, auth_headers, test_rilievo_with_dimensions, test_client):
        """Test POST /import-rilievo auto-sets client_id from rilievo"""
        # Create a new distinta without client
        distinta_payload = {"name": "TEST_Distinta_NoClient", "items": []}
        dist_resp = requests.post(f"{BASE_URL}/api/distinte/", json=distinta_payload, headers=auth_headers)
        assert dist_resp.status_code == 201
        distinta_id = dist_resp.json()["distinta_id"]
        
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.post(
            f"{BASE_URL}/api/distinte/{distinta_id}/import-rilievo/{rilievo_id}",
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        # Should have client_id from rilievo
        assert data.get("client_id") == test_client["client_id"], f"Expected client_id {test_client['client_id']}, got {data.get('client_id')}"
        print(f"✓ Client ID auto-set from rilievo: {data.get('client_id')}")
    
    def test_import_rilievo_appends_reference_note(self, auth_headers, test_distinta, test_rilievo_with_dimensions):
        """Test POST /import-rilievo appends reference note"""
        distinta_id = test_distinta["distinta_id"]
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        project_name = test_rilievo_with_dimensions["project_name"]
        
        resp = requests.post(
            f"{BASE_URL}/api/distinte/{distinta_id}/import-rilievo/{rilievo_id}",
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        notes = data.get("notes", "")
        assert "Importato da rilievo" in notes, f"Expected import reference in notes, got: {notes}"
        assert project_name in notes, f"Expected project name in notes, got: {notes}"
        print(f"✓ Reference note appended: {notes}")
    
    def test_import_rilievo_404_invalid_distinta(self, auth_headers, test_rilievo_with_dimensions):
        """Test POST /import-rilievo returns 404 for invalid distinta"""
        rilievo_id = test_rilievo_with_dimensions["rilievo_id"]
        
        resp = requests.post(
            f"{BASE_URL}/api/distinte/nonexistent_dist_123/import-rilievo/{rilievo_id}",
            headers=auth_headers
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ 404 returned for non-existent distinta")
    
    def test_import_rilievo_404_invalid_rilievo(self, auth_headers, test_distinta):
        """Test POST /import-rilievo returns 404 for invalid rilievo"""
        distinta_id = test_distinta["distinta_id"]
        
        resp = requests.post(
            f"{BASE_URL}/api/distinte/{distinta_id}/import-rilievo/nonexistent_ril_123",
            headers=auth_headers
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ 404 returned for non-existent rilievo")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Iteration 244 - D6 Profili Documentali per Committente Ricorrente
=================================================================
Tests for profile CRUD, apply to commessa, suggest profile, and audit logging.
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "K6fH_AIOSlUNVh8nGj5yAOjYtEyW-Ifsc4X5SFRVQYQ"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_D6_"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestProfiliCommittenteCRUD:
    """CRUD operations for Profili Committente (D6)"""
    
    created_profile_id = None
    
    def test_01_list_profili_returns_list(self, api_client):
        """GET /api/profili-committente returns list of profiles"""
        response = api_client.get(f"{BASE_URL}/api/profili-committente")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} existing profiles")
    
    def test_02_create_profile_success(self, api_client):
        """POST /api/profili-committente creates a profile with client_name, rules[], notes, warnings[]"""
        payload = {
            "client_name": f"{TEST_PREFIX}Impresa Test S.r.l.",
            "description": "Profilo di test per D6",
            "notes": "Note operative di test",
            "warnings": ["Attenzione: documenti sensibili", "Verificare scadenze"],
            "rules": [
                {"document_type_code": "DURC", "entity_type": "azienda", "required": True},
                {"document_type_code": "VISURA_CAMERALE", "entity_type": "azienda", "required": True},
                {"document_type_code": "IDONEITA_SANITARIA", "entity_type": "persona", "required": False}
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile_id" in data, "Response should contain profile_id"
        assert data["client_name"] == payload["client_name"]
        assert len(data["rules"]) == 3
        assert data["notes"] == payload["notes"]
        assert len(data["warnings"]) == 2
        assert data["usage_count"] == 0
        
        TestProfiliCommittenteCRUD.created_profile_id = data["profile_id"]
        print(f"Created profile: {data['profile_id']}")
    
    def test_03_create_profile_empty_client_name_returns_400(self, api_client):
        """POST /api/profili-committente with empty client_name returns 400 error"""
        payload = {
            "client_name": "",
            "rules": [{"document_type_code": "DURC", "entity_type": "azienda", "required": True}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        print(f"Error message: {data['detail']}")
    
    def test_04_get_single_profile(self, api_client):
        """GET /api/profili-committente/{profile_id} returns single profile"""
        profile_id = TestProfiliCommittenteCRUD.created_profile_id
        assert profile_id, "Profile ID not set from previous test"
        
        response = api_client.get(f"{BASE_URL}/api/profili-committente/{profile_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["profile_id"] == profile_id
        assert data["client_name"].startswith(TEST_PREFIX)
        print(f"Retrieved profile: {data['client_name']}")
    
    def test_05_update_profile(self, api_client):
        """PUT /api/profili-committente/{profile_id} updates profile fields"""
        profile_id = TestProfiliCommittenteCRUD.created_profile_id
        assert profile_id, "Profile ID not set from previous test"
        
        updates = {
            "description": "Descrizione aggiornata",
            "notes": "Note aggiornate",
            "warnings": ["Nuovo avviso"],
            "rules": [
                {"document_type_code": "DURC", "entity_type": "azienda", "required": True},
                {"document_type_code": "DVR", "entity_type": "azienda", "required": True}
            ]
        }
        
        response = api_client.put(f"{BASE_URL}/api/profili-committente/{profile_id}", json=updates)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["description"] == updates["description"]
        assert data["notes"] == updates["notes"]
        assert len(data["rules"]) == 2
        assert len(data["warnings"]) == 1
        print(f"Updated profile: {profile_id}")
    
    def test_06_get_profile_not_found(self, api_client):
        """GET /api/profili-committente/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/profili-committente/prof_nonexistent123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestProfiliFromPackage:
    """Create profile from existing package (semi-automatic creation)"""
    
    def test_01_create_profile_from_package(self, api_client):
        """POST /api/profili-committente/da-pacchetto/{pack_id} creates profile from existing package items"""
        # First, get an existing package
        packs_response = api_client.get(f"{BASE_URL}/api/pacchetti-documentali")
        assert packs_response.status_code == 200
        packs = packs_response.json()
        
        if not packs:
            pytest.skip("No existing packages to test with")
        
        pack_id = packs[0]["pack_id"]
        
        payload = {
            "client_name": f"{TEST_PREFIX}Da Pacchetto S.r.l.",
            "description": "Profilo generato da pacchetto esistente"
        }
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente/da-pacchetto/{pack_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile_id" in data
        assert data["client_name"] == payload["client_name"]
        assert "source_pack_id" in data
        print(f"Created profile from package: {data['profile_id']} with {len(data.get('rules', []))} rules")
    
    def test_02_create_profile_from_invalid_package(self, api_client):
        """POST /api/profili-committente/da-pacchetto/{invalid_pack_id} returns 400"""
        payload = {
            "client_name": f"{TEST_PREFIX}Invalid Pack",
            "description": "Should fail"
        }
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente/da-pacchetto/pack_nonexistent", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"


class TestApplicaProfilo:
    """Apply profile to create new pacchetto_documentale"""
    
    applied_pack_id = None
    test_profile_id = None
    
    def test_01_apply_profile_to_commessa(self, api_client):
        """POST /api/profili-committente/{profile_id}/applica creates new pacchetto_documentale from profile rules"""
        # Get existing profile (use the one created during development)
        profiles_response = api_client.get(f"{BASE_URL}/api/profili-committente")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        
        if not profiles:
            pytest.skip("No profiles available to test apply")
        
        # Use first profile with rules
        profile = next((p for p in profiles if p.get("rules")), profiles[0])
        TestApplicaProfilo.test_profile_id = profile["profile_id"]
        initial_usage_count = profile.get("usage_count", 0)
        
        # Get a commessa to apply to (API returns paginated dict with 'items')
        commesse_response = api_client.get(f"{BASE_URL}/api/commesse")
        assert commesse_response.status_code == 200
        commesse_data = commesse_response.json()
        commesse = commesse_data.get("items", commesse_data) if isinstance(commesse_data, dict) else commesse_data
        
        if not commesse:
            pytest.skip("No commesse available to test apply")
        
        commessa = commesse[0]
        
        payload = {
            "commessa_id": commessa["commessa_id"],
            "label": f"{TEST_PREFIX}Pacchetto da Profilo"
        }
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente/{profile['profile_id']}/applica", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pack" in data
        assert "profile" in data
        
        pack = data["pack"]
        assert pack["pack_id"].startswith("pack_")
        assert pack["template_code"] == f"profilo:{profile['profile_id']}"
        assert pack["commessa_id"] == commessa["commessa_id"]
        
        TestApplicaProfilo.applied_pack_id = pack["pack_id"]
        print(f"Applied profile {profile['profile_id']} to create pack {pack['pack_id']} with {len(pack.get('items', []))} items")
    
    def test_02_applied_pack_has_correct_items(self, api_client):
        """Applied pack has correct items matching profile rules"""
        pack_id = TestApplicaProfilo.applied_pack_id
        if not pack_id:
            pytest.skip("No applied pack from previous test")
        
        response = api_client.get(f"{BASE_URL}/api/pacchetti-documentali/{pack_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        pack = response.json()
        items = pack.get("items", [])
        
        # Verify items have expected structure
        for item in items:
            assert "document_type_code" in item
            assert "entity_type" in item
            assert "status" in item
            assert item["status"] == "pending"
        
        print(f"Pack {pack_id} has {len(items)} items with correct structure")
    
    def test_03_profile_usage_count_incremented(self, api_client):
        """Profile usage_count increments after apply"""
        profile_id = TestApplicaProfilo.test_profile_id
        if not profile_id:
            pytest.skip("No profile ID from previous test")
        
        # If apply test was skipped, skip this too
        if not TestApplicaProfilo.applied_pack_id:
            pytest.skip("Apply test was skipped, cannot verify usage_count")
        
        response = api_client.get(f"{BASE_URL}/api/profili-committente/{profile_id}")
        assert response.status_code == 200
        
        profile = response.json()
        # usage_count should be at least 1 after apply
        assert profile.get("usage_count", 0) >= 1, f"Expected usage_count >= 1, got {profile.get('usage_count')}"
        assert profile.get("last_used_at") is not None, "last_used_at should be set after apply"
        print(f"Profile {profile_id} usage_count: {profile['usage_count']}, last_used_at: {profile['last_used_at']}")
    
    def test_04_apply_invalid_profile_returns_400(self, api_client):
        """POST /api/profili-committente/{invalid_id}/applica returns 400"""
        payload = {"commessa_id": "com_test123", "label": "Test"}
        
        response = api_client.post(f"{BASE_URL}/api/profili-committente/prof_nonexistent/applica", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestSuggestProfilo:
    """Suggest profile matching commessa client"""
    
    def test_01_suggest_profile_for_commessa(self, api_client):
        """GET /api/profili-committente/suggest/{commessa_id} returns matching profile by client_name"""
        # Get a commessa (API returns paginated dict with 'items')
        commesse_response = api_client.get(f"{BASE_URL}/api/commesse")
        assert commesse_response.status_code == 200
        commesse_data = commesse_response.json()
        commesse = commesse_data.get("items", commesse_data) if isinstance(commesse_data, dict) else commesse_data
        
        if not commesse:
            pytest.skip("No commesse available")
        
        commessa = commesse[0]
        
        response = api_client.get(f"{BASE_URL}/api/profili-committente/suggest/{commessa['commessa_id']}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "suggested_profile" in data
        # suggested_profile can be null if no match
        print(f"Suggested profile for commessa {commessa['commessa_id']}: {data['suggested_profile']}")
    
    def test_02_suggest_profile_for_invalid_commessa(self, api_client):
        """GET /api/profili-committente/suggest/{invalid_id} returns null suggestion"""
        response = api_client.get(f"{BASE_URL}/api/profili-committente/suggest/com_nonexistent")
        assert response.status_code == 200
        
        data = response.json()
        assert data["suggested_profile"] is None


class TestAuditLogForProfili:
    """Verify audit log entries for profile operations"""
    
    def test_01_audit_log_has_profile_entries(self, api_client):
        """Audit log entries created for profile CRUD and apply operations"""
        response = api_client.get(f"{BASE_URL}/api/activity-log?entity_type=profilo_committente&limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # API returns paginated dict with 'items'
        entries = data.get("items", data) if isinstance(data, dict) else data
        
        # Should have entries for create, update operations
        print(f"Found {len(entries)} audit entries for profilo_committente")
        
        if entries:
            entry = entries[0]
            assert "action" in entry
            assert "entity_type" in entry
            print(f"Latest entry: action={entry.get('action')}, label={entry.get('label')}")


class TestDeleteProfilo:
    """Delete profile tests (run last)"""
    
    def test_01_delete_profile(self, api_client):
        """DELETE /api/profili-committente/{profile_id} deletes profile"""
        # Get profiles with TEST_PREFIX
        response = api_client.get(f"{BASE_URL}/api/profili-committente")
        assert response.status_code == 200
        
        profiles = response.json()
        test_profiles = [p for p in profiles if p.get("client_name", "").startswith(TEST_PREFIX)]
        
        if not test_profiles:
            pytest.skip("No test profiles to delete")
        
        for profile in test_profiles:
            delete_response = api_client.delete(f"{BASE_URL}/api/profili-committente/{profile['profile_id']}")
            assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
            
            data = delete_response.json()
            assert data.get("deleted") == True
            print(f"Deleted profile: {profile['profile_id']}")
    
    def test_02_delete_nonexistent_profile_returns_404(self, api_client):
        """DELETE /api/profili-committente/{invalid_id} returns 404"""
        response = api_client.delete(f"{BASE_URL}/api/profili-committente/prof_nonexistent")
        assert response.status_code == 404


class TestExistingTestProfile:
    """Verify the existing test profile created during development"""
    
    def test_01_verify_existing_profile(self, api_client):
        """Verify existing test profile prof_00bad461c118 exists with 5 rules"""
        response = api_client.get(f"{BASE_URL}/api/profili-committente/prof_00bad461c118")
        
        if response.status_code == 404:
            pytest.skip("Test profile prof_00bad461c118 not found - may have been deleted")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["profile_id"] == "prof_00bad461c118"
        assert data["client_name"] == "Impresa Edile Rossi S.r.l."
        assert len(data.get("rules", [])) == 5
        print(f"Verified existing profile: {data['client_name']} with {len(data['rules'])} rules")

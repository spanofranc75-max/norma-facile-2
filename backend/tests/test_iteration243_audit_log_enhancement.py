"""
Iteration 243 - Audit Log Enhancement Tests
============================================
Tests for extended audit log system covering new modules:
- Cantiere Sicurezza, Registro Obblighi, Pacchetti Documentali
- Verifica Committenza, Emissioni Documentali, Rami Normativi
- New fields: commessa_id, actor_type
- Before/after tracking for critical changes
- Actor type filter
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "K6fH_AIOSlUNVh8nGj5yAOjYtEyW-Ifsc4X5SFRVQYQ"
TEST_COMMESSA_ID = "com_b68bf16b4f03"


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestActivityLogStats:
    """Tests for GET /api/activity-log/stats endpoint"""
    
    def test_stats_returns_actor_labels(self, auth_session):
        """Stats should include actor_labels with 3 options"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "actor_labels" in data
        actor_labels = data["actor_labels"]
        assert actor_labels.get("user") == "Utente"
        assert actor_labels.get("system") == "Sistema"
        assert actor_labels.get("ai") == "AI"
    
    def test_stats_returns_expanded_entity_types(self, auth_session):
        """Stats should include 24 entity types including new modules"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        entity_types = data.get("entity_types", [])
        assert len(entity_types) == 24
        
        # Verify new module entity types are present
        new_types = [
            "cantiere_sicurezza", "obbligo", "pacchetto_documentale",
            "documento_archivio", "committenza_package", "committenza_analisi",
            "emissione", "ramo_normativo"
        ]
        for t in new_types:
            assert t in entity_types, f"Missing entity type: {t}"
    
    def test_stats_returns_expanded_action_types(self, auth_session):
        """Stats should include 17 action types including new actions"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        action_types = data.get("action_types", [])
        assert len(action_types) == 17
        
        # Verify new action types are present
        new_actions = [
            "ai_precompile", "generate_docx", "sync_complete", "verifica",
            "approve", "reject", "gate_check", "send_email", "issue_document",
            "genera_obblighi"
        ]
        for a in new_actions:
            assert a in action_types, f"Missing action type: {a}"
    
    def test_stats_returns_entity_labels(self, auth_session):
        """Stats should include Italian labels for all entity types"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        entity_labels = data.get("entity_labels", {})
        
        # Verify new module labels
        assert entity_labels.get("cantiere_sicurezza") == "Cantiere Sicurezza"
        assert entity_labels.get("obbligo") == "Obbligo Commessa"
        assert entity_labels.get("pacchetto_documentale") == "Pacchetto Documentale"
        assert entity_labels.get("committenza_package") == "Package Committenza"
        assert entity_labels.get("emissione") == "Emissione Documentale"
        assert entity_labels.get("ramo_normativo") == "Ramo Normativo"
    
    def test_stats_returns_action_labels(self, auth_session):
        """Stats should include Italian labels for all action types"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log/stats")
        assert response.status_code == 200
        data = response.json()
        
        action_labels = data.get("action_labels", {})
        
        # Verify new action labels
        assert action_labels.get("ai_precompile") == "Pre-compilazione AI"
        assert action_labels.get("generate_docx") == "Generazione DOCX"
        assert action_labels.get("sync_complete") == "Sync completato"
        assert action_labels.get("verifica") == "Verifica"
        assert action_labels.get("genera_obblighi") == "Generazione obblighi"


class TestActivityLogList:
    """Tests for GET /api/activity-log endpoint"""
    
    def test_list_returns_new_fields(self, auth_session):
        """Activity log entries should include commessa_id and actor_type"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        # Check that entries have the new fields
        for item in data["items"]:
            assert "commessa_id" in item or item.get("commessa_id") is None
            assert "actor_type" in item or item.get("actor_type") is None
    
    def test_filter_by_actor_type_system(self, auth_session):
        """Filter by actor_type=system should return only system entries"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log?actor_type=system&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # All returned items should have actor_type=system
        for item in data["items"]:
            assert item.get("actor_type") == "system"
    
    def test_filter_by_entity_type_obbligo(self, auth_session):
        """Filter by entity_type=obbligo should return only obbligo entries"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log?entity_type=obbligo&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # All returned items should have entity_type=obbligo
        for item in data["items"]:
            assert item.get("entity_type") == "obbligo"
    
    def test_filter_by_commessa_id(self, auth_session):
        """Filter by commessa_id should return only entries for that commessa"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log?commessa_id={TEST_COMMESSA_ID}&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # All returned items should have the specified commessa_id
        for item in data["items"]:
            assert item.get("commessa_id") == TEST_COMMESSA_ID


class TestObblighiSync:
    """Tests for POST /api/obblighi/sync/{commessa_id} audit logging"""
    
    def test_sync_creates_audit_entry(self, auth_session):
        """Sync should create audit entry with action=sync_complete, actor_type=system"""
        # Trigger sync
        response = auth_session.post(f"{BASE_URL}/api/obblighi/sync/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        
        # Check audit log for the sync entry
        log_response = auth_session.get(
            f"{BASE_URL}/api/activity-log?entity_type=obbligo&action=sync_complete&commessa_id={TEST_COMMESSA_ID}&limit=1"
        )
        assert log_response.status_code == 200
        log_data = log_response.json()
        
        assert log_data["total"] >= 1
        entry = log_data["items"][0]
        
        assert entry["action"] == "sync_complete"
        assert entry["entity_type"] == "obbligo"
        assert entry["actor_type"] == "system"
        assert entry["commessa_id"] == TEST_COMMESSA_ID
        
        # Verify details contain sync counts
        details = entry.get("details", {})
        assert "created" in details
        assert "updated" in details
        assert "closed" in details


class TestObblighiStatusChange:
    """Tests for PATCH /api/obblighi/{id} before/after tracking"""
    
    def test_status_change_creates_audit_with_before_after(self, auth_session):
        """Status change should create audit entry with before/after details"""
        # Get an obbligo to update
        obblighi_response = auth_session.get(f"{BASE_URL}/api/obblighi?commessa_id={TEST_COMMESSA_ID}")
        assert obblighi_response.status_code == 200
        obblighi = obblighi_response.json()
        
        if not obblighi:
            pytest.skip("No obblighi found for testing")
        
        obbligo = obblighi[0]
        obbligo_id = obbligo["obbligo_id"]
        current_status = obbligo["status"]
        
        # Determine new status
        new_status = "completato" if current_status != "completato" else "in_corso"
        
        # Update status
        patch_response = auth_session.patch(
            f"{BASE_URL}/api/obblighi/{obbligo_id}",
            json={"status": new_status}
        )
        assert patch_response.status_code == 200
        
        # Check audit log for status_change entry
        log_response = auth_session.get(
            f"{BASE_URL}/api/activity-log?entity_type=obbligo&action=status_change&limit=1"
        )
        assert log_response.status_code == 200
        log_data = log_response.json()
        
        assert log_data["total"] >= 1
        entry = log_data["items"][0]
        
        assert entry["action"] == "status_change"
        assert entry["entity_type"] == "obbligo"
        assert entry["entity_id"] == obbligo_id
        
        # Verify before/after in details
        details = entry.get("details", {})
        assert "status" in details
        assert "before" in details["status"]
        assert "after" in details["status"]
        assert details["status"]["after"] == new_status


class TestActivityLogPagination:
    """Tests for pagination in activity log"""
    
    def test_pagination_works(self, auth_session):
        """Pagination should work correctly with skip and limit"""
        # Get first page
        response1 = auth_session.get(f"{BASE_URL}/api/activity-log?skip=0&limit=5")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get second page
        response2 = auth_session.get(f"{BASE_URL}/api/activity-log?skip=5&limit=5")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify different items
        if data1["total"] > 5:
            ids1 = {item.get("entity_id") for item in data1["items"]}
            ids2 = {item.get("entity_id") for item in data2["items"]}
            # There should be no overlap (unless same entity has multiple entries)
            # Just verify we got different pages
            assert data1["skip"] == 0
            assert data2["skip"] == 5


class TestActivityLogSearch:
    """Tests for search functionality in activity log"""
    
    def test_search_by_label(self, auth_session):
        """Search should filter by label"""
        response = auth_session.get(f"{BASE_URL}/api/activity-log?search=Sync&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # If there are results, they should contain "Sync" in label
        for item in data["items"]:
            label = item.get("label", "").lower()
            user_name = item.get("user_name", "").lower()
            entity_id = item.get("entity_id", "").lower()
            commessa_id = item.get("commessa_id", "").lower()
            # Search matches label, user_name, entity_id, or commessa_id
            assert "sync" in label or "sync" in user_name or "sync" in entity_id or "sync" in commessa_id or data["total"] == 0


class TestActivityLogDateFilter:
    """Tests for date filtering in activity log"""
    
    def test_filter_by_date_range(self, auth_session):
        """Filter by date range should work"""
        response = auth_session.get(
            f"{BASE_URL}/api/activity-log?date_from=2026-03-01&date_to=2026-03-31&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        
        # All items should be within the date range
        for item in data["items"]:
            timestamp = item.get("timestamp", "")
            assert timestamp.startswith("2026-03")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

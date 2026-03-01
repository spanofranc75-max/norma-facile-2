"""
Audit & Non-Conformity Module Tests - Iteration 91
Tests for /api/audits and /api/ncs endpoints
EN 1090 / ISO 9001 compliance module
"""
import pytest
import requests
import os
import uuid
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "TGOMljLQmmdDakMy3F9zTH_X1-_w2HFsTfcSo8Kbq3Q"


@pytest.fixture(scope="session")
def api_client():
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


# ═══════════════════════ AUDIT LIST & STATS TESTS ═══════════════════════

class TestAuditList:
    """Test GET /api/audits endpoint"""
    
    def test_list_audits_returns_200(self, api_client):
        """Verify audits list endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/audits returns 200")
    
    def test_audits_list_structure(self, api_client):
        """Verify response has items, total, and stats"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        data = response.json()
        
        assert "items" in data, "Response missing 'items'"
        assert "total" in data, "Response missing 'total'"
        assert "stats" in data, "Response missing 'stats'"
        assert isinstance(data["items"], list), "items should be a list"
        print(f"✓ Audit list structure correct: {data['total']} audits")
    
    def test_audit_stats_structure(self, api_client):
        """Verify stats contain required fields"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        stats = response.json()["stats"]
        
        required_stats = ["total_audits", "audits_this_year", "nc_open", "nc_closed", "next_audit_date"]
        for field in required_stats:
            assert field in stats, f"Stats missing '{field}'"
        print(f"✓ Stats structure correct: {stats}")
    
    def test_audit_stats_values(self, api_client):
        """Verify stats values based on seeded data"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        stats = response.json()["stats"]
        
        # Based on seeded data: 2 audits total, 1 audit in 2026
        assert stats["total_audits"] == 2, f"Expected 2 total audits, got {stats['total_audits']}"
        assert stats["audits_this_year"] == 1, f"Expected 1 audit this year, got {stats['audits_this_year']}"
        assert stats["next_audit_date"] == "2026-06-15", f"Expected next audit 2026-06-15, got {stats['next_audit_date']}"
        print(f"✓ Stats values correct: audits_this_year={stats['audits_this_year']}, next_audit={stats['next_audit_date']}")
    
    def test_audit_item_structure(self, api_client):
        """Verify audit item has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        items = response.json()["items"]
        
        assert len(items) > 0, "No audits found"
        audit = items[0]
        
        required_fields = [
            "audit_id", "date", "audit_type", "auditor_name", "outcome",
            "has_report", "nc_count", "nc_open", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in audit, f"Audit missing '{field}'"
        print(f"✓ Audit item structure correct: {audit['audit_id']}")
    
    def test_audit_type_badges(self, api_client):
        """Verify audit types are valid enum values"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        items = response.json()["items"]
        
        valid_types = {"interno", "esterno_ente", "cliente"}
        for audit in items:
            assert audit["audit_type"] in valid_types, f"Invalid audit_type: {audit['audit_type']}"
        print("✓ All audit types are valid")
    
    def test_audit_outcome_badges(self, api_client):
        """Verify audit outcomes are valid enum values"""
        response = api_client.get(f"{BASE_URL}/api/audits")
        items = response.json()["items"]
        
        valid_outcomes = {"positivo", "negativo", "con_osservazioni"}
        for audit in items:
            assert audit["outcome"] in valid_outcomes, f"Invalid outcome: {audit['outcome']}"
        print("✓ All audit outcomes are valid")
    
    def test_search_audits_by_auditor(self, api_client):
        """Verify search filter works on auditor name"""
        response = api_client.get(f"{BASE_URL}/api/audits?search=Marco")
        data = response.json()
        
        assert response.status_code == 200
        if data["total"] > 0:
            for audit in data["items"]:
                assert "marco" in audit["auditor_name"].lower() or "marco" in (audit.get("scope") or "").lower(), \
                    f"Search 'Marco' returned audit without match: {audit['auditor_name']}"
        print(f"✓ Search by auditor works: {data['total']} results for 'Marco'")


# ═══════════════════════ AUDIT CRUD TESTS ═══════════════════════

class TestAuditCRUD:
    """Test Audit Create, Read, Update, Delete operations"""
    
    created_audit_id = None
    
    def test_create_audit_with_form_data(self, api_client):
        """Create audit using multipart form data"""
        # Use session without JSON content-type for form data
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        
        form_data = {
            "date": "2026-03-01",
            "audit_type": "interno",
            "auditor_name": "TEST_Tester Pytest",
            "scope": "Test automatico - verificare e cancellare",
            "outcome": "positivo",
            "notes": "Created by pytest",
            "next_audit_date": "2026-09-01"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/audits",
            headers=headers,
            data=form_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "audit_id" in data, "Response missing audit_id"
        assert data["auditor_name"] == "TEST_Tester Pytest", f"Auditor name mismatch"
        assert data["date"] == "2026-03-01", "Date mismatch"
        assert data["audit_type"] == "interno", "Audit type mismatch"
        
        TestAuditCRUD.created_audit_id = data["audit_id"]
        print(f"✓ Audit created: {data['audit_id']}")
    
    def test_get_created_audit(self, api_client):
        """Verify created audit can be fetched"""
        if not TestAuditCRUD.created_audit_id:
            pytest.skip("No audit created")
        
        response = api_client.get(f"{BASE_URL}/api/audits/{TestAuditCRUD.created_audit_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["audit_id"] == TestAuditCRUD.created_audit_id
        assert data["auditor_name"] == "TEST_Tester Pytest"
        print(f"✓ Audit fetched successfully: {data['audit_id']}")
    
    def test_update_audit(self, api_client):
        """Update audit information"""
        if not TestAuditCRUD.created_audit_id:
            pytest.skip("No audit created")
        
        update_payload = {
            "date": "2026-03-02",
            "audit_type": "esterno_ente",
            "auditor_name": "TEST_Tester Pytest UPDATED",
            "scope": "Updated scope",
            "outcome": "con_osservazioni",
            "notes": "Updated by pytest",
            "next_audit_date": "2026-10-01"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/audits/{TestAuditCRUD.created_audit_id}",
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["auditor_name"] == "TEST_Tester Pytest UPDATED"
        assert data["audit_type"] == "esterno_ente"
        assert data["outcome"] == "con_osservazioni"
        print(f"✓ Audit updated successfully")
    
    def test_verify_update_persisted(self, api_client):
        """Verify update was persisted in database"""
        if not TestAuditCRUD.created_audit_id:
            pytest.skip("No audit created")
        
        response = api_client.get(f"{BASE_URL}/api/audits/{TestAuditCRUD.created_audit_id}")
        data = response.json()
        
        assert data["auditor_name"] == "TEST_Tester Pytest UPDATED", "Update not persisted"
        assert data["audit_type"] == "esterno_ente", "Type update not persisted"
        print(f"✓ Update persisted correctly")
    
    def test_delete_audit(self, api_client):
        """Delete the test audit"""
        if not TestAuditCRUD.created_audit_id:
            pytest.skip("No audit created")
        
        response = api_client.delete(f"{BASE_URL}/api/audits/{TestAuditCRUD.created_audit_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["audit_id"] == TestAuditCRUD.created_audit_id
        print(f"✓ Audit deleted successfully")
    
    def test_verify_audit_deleted(self, api_client):
        """Verify audit no longer exists"""
        if not TestAuditCRUD.created_audit_id:
            pytest.skip("No audit created")
        
        response = api_client.get(f"{BASE_URL}/api/audits/{TestAuditCRUD.created_audit_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Audit deletion verified")
    
    def test_get_nonexistent_audit(self, api_client):
        """Verify 404 for nonexistent audit"""
        response = api_client.get(f"{BASE_URL}/api/audits/nonexistent_audit_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned for nonexistent audit")


# ═══════════════════════ NC LIST & STATS TESTS ═══════════════════════

class TestNCList:
    """Test GET /api/ncs endpoint"""
    
    def test_list_ncs_returns_200(self, api_client):
        """Verify NC list endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/ncs returns 200")
    
    def test_nc_list_structure(self, api_client):
        """Verify response has items, total, and stats"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        data = response.json()
        
        assert "items" in data, "Response missing 'items'"
        assert "total" in data, "Response missing 'total'"
        assert "stats" in data, "Response missing 'stats'"
        print(f"✓ NC list structure correct: {data['total']} NCs")
    
    def test_nc_stats_structure(self, api_client):
        """Verify NC stats contain status and priority counts"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        stats = response.json()["stats"]
        
        required_stats = ["total", "aperte", "in_lavorazione", "chiuse", "alta", "media", "bassa"]
        for field in required_stats:
            assert field in stats, f"Stats missing '{field}'"
        print(f"✓ NC stats structure correct: {stats}")
    
    def test_nc_stats_values(self, api_client):
        """Verify NC stats values based on seeded data"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        stats = response.json()["stats"]
        
        # Based on seeded data: 4 NCs - 2 aperte, 1 in_lavorazione, 1 chiusa
        assert stats["total"] == 4, f"Expected 4 total NCs, got {stats['total']}"
        assert stats["aperte"] == 2, f"Expected 2 aperte, got {stats['aperte']}"
        assert stats["in_lavorazione"] == 1, f"Expected 1 in_lavorazione, got {stats['in_lavorazione']}"
        assert stats["chiuse"] == 1, f"Expected 1 chiuse, got {stats['chiuse']}"
        print(f"✓ NC stats values correct")
    
    def test_nc_item_structure(self, api_client):
        """Verify NC item has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        items = response.json()["items"]
        
        assert len(items) > 0, "No NCs found"
        nc = items[0]
        
        required_fields = [
            "nc_id", "nc_number", "date", "description", "priority", "status",
            "days_open", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in nc, f"NC missing '{field}'"
        print(f"✓ NC item structure correct: {nc['nc_number']}")
    
    def test_nc_number_format(self, api_client):
        """Verify NC numbers follow NC-YYYY-NNN format"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        items = response.json()["items"]
        
        import re
        pattern = r"^NC-\d{4}-\d{3}$"
        for nc in items:
            assert re.match(pattern, nc["nc_number"]), f"Invalid NC number format: {nc['nc_number']}"
        print("✓ All NC numbers follow NC-YYYY-NNN format")
    
    def test_nc_status_values(self, api_client):
        """Verify NC statuses are valid enum values"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        items = response.json()["items"]
        
        valid_statuses = {"aperta", "in_lavorazione", "chiusa"}
        for nc in items:
            assert nc["status"] in valid_statuses, f"Invalid status: {nc['status']}"
        print("✓ All NC statuses are valid")
    
    def test_nc_priority_values(self, api_client):
        """Verify NC priorities are valid enum values"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        items = response.json()["items"]
        
        valid_priorities = {"alta", "media", "bassa"}
        for nc in items:
            assert nc["priority"] in valid_priorities, f"Invalid priority: {nc['priority']}"
        print("✓ All NC priorities are valid")
    
    def test_nc_days_open_calculation(self, api_client):
        """Verify days_open is calculated correctly"""
        response = api_client.get(f"{BASE_URL}/api/ncs")
        items = response.json()["items"]
        
        for nc in items:
            days_open = nc.get("days_open")
            if days_open is not None:
                assert isinstance(days_open, int), f"days_open should be int, got {type(days_open)}"
                assert days_open >= 0, f"days_open should be >= 0, got {days_open}"
        print("✓ days_open calculation correct")
    
    def test_search_ncs_by_description(self, api_client):
        """Verify search filter works on description"""
        response = api_client.get(f"{BASE_URL}/api/ncs?search=saldatura")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Search by description works: {data['total']} results for 'saldatura'")
    
    def test_filter_ncs_by_status(self, api_client):
        """Verify status filter works"""
        response = api_client.get(f"{BASE_URL}/api/ncs?status=chiusa")
        assert response.status_code == 200
        data = response.json()
        
        for nc in data["items"]:
            assert nc["status"] == "chiusa", f"Status filter failed: got {nc['status']}"
        print(f"✓ Status filter works: {data['total']} chiuse")
    
    def test_filter_ncs_by_priority(self, api_client):
        """Verify priority filter works"""
        response = api_client.get(f"{BASE_URL}/api/ncs?priority=alta")
        assert response.status_code == 200
        data = response.json()
        
        for nc in data["items"]:
            assert nc["priority"] == "alta", f"Priority filter failed: got {nc['priority']}"
        print(f"✓ Priority filter works: {data['total']} alta priorità")


# ═══════════════════════ NC CRUD TESTS ═══════════════════════

class TestNCCRUD:
    """Test NC Create, Read, Update, Close, Reopen, Delete operations"""
    
    created_nc_id = None
    
    def test_create_standalone_nc(self, api_client):
        """Create a standalone NC (not linked to audit)"""
        payload = {
            "date": "2026-03-01",
            "description": "TEST_NC creata da pytest - non conformità di test",
            "source": "Test automatico",
            "priority": "media"
        }
        
        response = api_client.post(f"{BASE_URL}/api/ncs", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "nc_id" in data, "Response missing nc_id"
        assert "nc_number" in data, "Response missing nc_number"
        assert data["status"] == "aperta", "New NC should be 'aperta'"
        assert data["priority"] == "media", "Priority mismatch"
        
        TestNCCRUD.created_nc_id = data["nc_id"]
        print(f"✓ Standalone NC created: {data['nc_number']} ({data['nc_id']})")
    
    def test_nc_auto_numbering(self, api_client):
        """Verify NC number follows NC-YYYY-NNN format"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.get(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}")
        data = response.json()
        
        import re
        assert re.match(r"^NC-\d{4}-\d{3}$", data["nc_number"]), f"Invalid NC number: {data['nc_number']}"
        print(f"✓ NC auto-numbering correct: {data['nc_number']}")
    
    def test_get_created_nc(self, api_client):
        """Verify created NC can be fetched"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.get(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["nc_id"] == TestNCCRUD.created_nc_id
        assert "TEST_NC" in data["description"]
        print(f"✓ NC fetched successfully")
    
    def test_update_nc_details(self, api_client):
        """Update NC with cause, corrective action, preventive action"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        update_payload = {
            "cause": "TEST causa radice - problema di configurazione",
            "corrective_action": "TEST azione correttiva - riconfigurazione sistema",
            "preventive_action": "TEST azione preventiva - formazione personale",
            "priority": "alta",
            "status": "in_lavorazione",
            "notes": "Note di test aggiunte"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}",
            json=update_payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["cause"] == "TEST causa radice - problema di configurazione"
        assert data["corrective_action"] == "TEST azione correttiva - riconfigurazione sistema"
        assert data["preventive_action"] == "TEST azione preventiva - formazione personale"
        assert data["priority"] == "alta"
        assert data["status"] == "in_lavorazione"
        print(f"✓ NC updated with cause/actions")
    
    def test_verify_nc_update_persisted(self, api_client):
        """Verify NC update was persisted"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.get(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}")
        data = response.json()
        
        assert data["status"] == "in_lavorazione", "Status update not persisted"
        assert data["priority"] == "alta", "Priority update not persisted"
        assert data["cause"] is not None, "Cause not persisted"
        print(f"✓ NC update persisted correctly")
    
    def test_close_nc(self, api_client):
        """Close the NC using /close endpoint"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.put(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}/close")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "chiusa", f"Expected status 'chiusa', got {data['status']}"
        assert data["closure_date"] is not None, "closure_date should be set"
        assert data["closed_by"] is not None, "closed_by should be set"
        print(f"✓ NC closed successfully on {data['closure_date']} by {data['closed_by']}")
    
    def test_close_already_closed_nc_fails(self, api_client):
        """Verify closing already closed NC returns error"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.put(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}/close")
        assert response.status_code == 400, f"Expected 400 for already closed NC, got {response.status_code}"
        print(f"✓ Cannot close already closed NC (400)")
    
    def test_reopen_nc(self, api_client):
        """Reopen the closed NC"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.put(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}/reopen")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "aperta", f"Expected status 'aperta', got {data['status']}"
        assert data["closure_date"] is None, "closure_date should be cleared"
        assert data["closed_by"] is None, "closed_by should be cleared"
        print(f"✓ NC reopened successfully")
    
    def test_reopen_non_closed_nc_fails(self, api_client):
        """Verify reopening non-closed NC returns error"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.put(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}/reopen")
        assert response.status_code == 400, f"Expected 400 for non-closed NC, got {response.status_code}"
        print(f"✓ Cannot reopen non-closed NC (400)")
    
    def test_delete_nc(self, api_client):
        """Delete the test NC"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.delete(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["nc_id"] == TestNCCRUD.created_nc_id
        print(f"✓ NC deleted successfully")
    
    def test_verify_nc_deleted(self, api_client):
        """Verify NC no longer exists"""
        if not TestNCCRUD.created_nc_id:
            pytest.skip("No NC created")
        
        response = api_client.get(f"{BASE_URL}/api/ncs/{TestNCCRUD.created_nc_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ NC deletion verified")


# ═══════════════════════ NC LINKED TO AUDIT TESTS ═══════════════════════

class TestNCLinkedToAudit:
    """Test creating NC linked to audit and audit deletion behavior"""
    
    test_audit_id = None
    linked_nc_id = None
    
    def test_create_audit_for_nc_linking(self, api_client):
        """Create an audit to link NCs to"""
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        form_data = {
            "date": "2026-03-01",
            "audit_type": "interno",
            "auditor_name": "TEST_Auditor per NC",
            "scope": "Test NC linking",
            "outcome": "con_osservazioni",
            "notes": "Created for NC linking test"
        }
        
        response = requests.post(f"{BASE_URL}/api/audits", headers=headers, data=form_data)
        assert response.status_code == 200, f"Failed to create audit: {response.text}"
        
        TestNCLinkedToAudit.test_audit_id = response.json()["audit_id"]
        print(f"✓ Audit created for NC linking: {TestNCLinkedToAudit.test_audit_id}")
    
    def test_create_nc_linked_to_audit(self, api_client):
        """Create NC using POST /api/audits/{audit_id}/ncs"""
        if not TestNCLinkedToAudit.test_audit_id:
            pytest.skip("No audit created")
        
        payload = {
            "date": "2026-03-01",
            "description": "TEST_NC collegata all'audit - verifica tracciabilità",
            "source": "",  # Source should be set from audit
            "priority": "alta"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/audits/{TestNCLinkedToAudit.test_audit_id}/ncs",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["audit_id"] == TestNCLinkedToAudit.test_audit_id, "NC not linked to audit"
        assert data["audit_ref"] is not None, "audit_ref should be set"
        
        TestNCLinkedToAudit.linked_nc_id = data["nc_id"]
        print(f"✓ NC created linked to audit: {data['nc_number']}, audit_ref={data['audit_ref']}")
    
    def test_audit_shows_nc_count(self, api_client):
        """Verify audit shows linked NC count"""
        if not TestNCLinkedToAudit.test_audit_id:
            pytest.skip("No audit created")
        
        response = api_client.get(f"{BASE_URL}/api/audits/{TestNCLinkedToAudit.test_audit_id}")
        data = response.json()
        
        assert data["nc_count"] >= 1, f"Expected at least 1 NC, got {data['nc_count']}"
        print(f"✓ Audit shows nc_count={data['nc_count']}, nc_open={data['nc_open']}")
    
    def test_delete_audit_unlinks_ncs(self, api_client):
        """Verify deleting audit unlinks (not deletes) NCs"""
        if not TestNCLinkedToAudit.test_audit_id or not TestNCLinkedToAudit.linked_nc_id:
            pytest.skip("No audit or NC created")
        
        # Delete the audit
        response = api_client.delete(f"{BASE_URL}/api/audits/{TestNCLinkedToAudit.test_audit_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Audit deleted")
        
        # Verify NC still exists but is unlinked
        nc_response = api_client.get(f"{BASE_URL}/api/ncs/{TestNCLinkedToAudit.linked_nc_id}")
        assert nc_response.status_code == 200, f"NC should still exist, got {nc_response.status_code}"
        
        nc_data = nc_response.json()
        assert nc_data["audit_id"] is None, f"NC should be unlinked (audit_id=None), got {nc_data['audit_id']}"
        print(f"✓ NC still exists but unlinked (audit_id=None)")
    
    def test_cleanup_unlinked_nc(self, api_client):
        """Clean up the unlinked NC"""
        if not TestNCLinkedToAudit.linked_nc_id:
            pytest.skip("No NC to clean up")
        
        response = api_client.delete(f"{BASE_URL}/api/ncs/{TestNCLinkedToAudit.linked_nc_id}")
        assert response.status_code == 200
        print(f"✓ Unlinked NC cleaned up")


# ═══════════════════════ ERROR HANDLING TESTS ═══════════════════════

class TestErrorHandling:
    """Test error responses for invalid operations"""
    
    def test_get_nonexistent_nc(self, api_client):
        """Verify 404 for nonexistent NC"""
        response = api_client.get(f"{BASE_URL}/api/ncs/nonexistent_nc_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned for nonexistent NC")
    
    def test_update_nonexistent_nc(self, api_client):
        """Verify 404 when updating nonexistent NC"""
        response = api_client.put(
            f"{BASE_URL}/api/ncs/nonexistent_nc_id",
            json={"cause": "test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned when updating nonexistent NC")
    
    def test_delete_nonexistent_nc(self, api_client):
        """Verify 404 when deleting nonexistent NC"""
        response = api_client.delete(f"{BASE_URL}/api/ncs/nonexistent_nc_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned when deleting nonexistent NC")
    
    def test_close_nonexistent_nc(self, api_client):
        """Verify 404 when closing nonexistent NC"""
        response = api_client.put(f"{BASE_URL}/api/ncs/nonexistent_nc_id/close")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned when closing nonexistent NC")
    
    def test_reopen_nonexistent_nc(self, api_client):
        """Verify 404 when reopening nonexistent NC"""
        response = api_client.put(f"{BASE_URL}/api/ncs/nonexistent_nc_id/reopen")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned when reopening nonexistent NC")
    
    def test_create_nc_with_nonexistent_audit(self, api_client):
        """Verify 404 when creating NC for nonexistent audit"""
        payload = {
            "date": "2026-03-01",
            "description": "Test NC for nonexistent audit",
            "priority": "media"
        }
        response = api_client.post(f"{BASE_URL}/api/audits/nonexistent_audit/ncs", json=payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned when creating NC for nonexistent audit")
    
    def test_create_nc_requires_description(self, api_client):
        """Verify validation error when description is empty"""
        payload = {
            "date": "2026-03-01",
            "description": "",
            "priority": "media"
        }
        response = api_client.post(f"{BASE_URL}/api/ncs", json=payload)
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        print("✓ Validation error for empty description")
    
    def test_create_audit_requires_auditor_name(self):
        """Verify validation error when auditor_name is empty"""
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        form_data = {
            "date": "2026-03-01",
            "audit_type": "interno",
            "auditor_name": "   ",  # Only whitespace
            "outcome": "positivo"
        }
        
        response = requests.post(f"{BASE_URL}/api/audits", headers=headers, data=form_data)
        assert response.status_code == 400, f"Expected 400 for empty auditor, got {response.status_code}"
        print("✓ Validation error for empty auditor_name")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

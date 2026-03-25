"""
Iteration 256 — Client Snapshot + Client Status System Tests

Tests for:
1. Client status filtering (active/archived/blocked)
2. Archive/block/reactivate endpoints
3. Client snapshot stored on invoices
4. Migration endpoints for backfilling snapshots
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session for authenticated requests
session = requests.Session()


@pytest.fixture(scope="module", autouse=True)
def setup_demo_session():
    """Login via demo mode to get session cookie."""
    resp = session.post(f"{BASE_URL}/api/demo/login")
    assert resp.status_code == 200, f"Demo login failed: {resp.text}"
    print(f"Demo login successful: {resp.json()}")
    yield
    # Cleanup handled per-test


class TestClientStatusFiltering:
    """Test GET /api/clients/ with status filters."""
    
    test_client_id = None
    
    @pytest.fixture(autouse=True)
    def setup_test_client(self):
        """Create a test client for status tests."""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "business_name": f"TEST_StatusClient_{unique_id}",
            "client_type": "cliente",
            "partita_iva": f"IT{unique_id}12345",
        }
        resp = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert resp.status_code == 201, f"Failed to create test client: {resp.text}"
        self.test_client_id = resp.json()["client_id"]
        yield
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{self.test_client_id}")
    
    def test_get_clients_default_returns_active_only(self):
        """GET /api/clients/ without params should return only active clients."""
        resp = session.get(f"{BASE_URL}/api/clients/")
        assert resp.status_code == 200
        data = resp.json()
        assert "clients" in data
        # All returned clients should be active or have no status (legacy)
        for client in data["clients"]:
            status = client.get("status", "active")
            assert status in ["active", None], f"Non-active client returned: {client['business_name']} status={status}"
    
    def test_get_clients_with_status_active(self):
        """GET /api/clients/?status=active should return only active clients."""
        resp = session.get(f"{BASE_URL}/api/clients/?status=active")
        assert resp.status_code == 200
        data = resp.json()
        for client in data["clients"]:
            assert client.get("status", "active") == "active"
    
    def test_get_clients_include_archived(self):
        """GET /api/clients/?include_archived=true should return all clients."""
        # First archive our test client
        archive_resp = session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/archive")
        assert archive_resp.status_code == 200
        
        # Now fetch with include_archived
        resp = session.get(f"{BASE_URL}/api/clients/?include_archived=true")
        assert resp.status_code == 200
        data = resp.json()
        
        # Should find our archived client
        found = any(c["client_id"] == self.test_client_id for c in data["clients"])
        assert found, "Archived client not found when include_archived=true"
        
        # Verify it's marked as archived
        archived_client = next(c for c in data["clients"] if c["client_id"] == self.test_client_id)
        assert archived_client["status"] == "archived"
    
    def test_get_clients_status_archived(self):
        """GET /api/clients/?status=archived should return only archived clients."""
        # Archive our test client
        session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/archive")
        
        resp = session.get(f"{BASE_URL}/api/clients/?status=archived")
        assert resp.status_code == 200
        data = resp.json()
        
        for client in data["clients"]:
            assert client.get("status") == "archived"


class TestClientArchiveBlockReactivate:
    """Test archive/block/reactivate endpoints."""
    
    test_client_id = None
    
    @pytest.fixture(autouse=True)
    def setup_test_client(self):
        """Create a test client."""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "business_name": f"TEST_ArchiveClient_{unique_id}",
            "client_type": "cliente",
        }
        resp = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert resp.status_code == 201
        self.test_client_id = resp.json()["client_id"]
        yield
        # Cleanup
        session.delete(f"{BASE_URL}/api/clients/{self.test_client_id}")
    
    def test_archive_client(self):
        """POST /api/clients/{id}/archive should set status to archived."""
        resp = session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/archive")
        assert resp.status_code == 200
        data = resp.json()
        assert "archiviato" in data.get("message", "").lower() or "archived" in data.get("message", "").lower()
        
        # Verify via GET
        get_resp = session.get(f"{BASE_URL}/api/clients/{self.test_client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "archived"
    
    def test_block_client(self):
        """POST /api/clients/{id}/block should set status to blocked."""
        resp = session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/block")
        assert resp.status_code == 200
        data = resp.json()
        assert "bloccato" in data.get("message", "").lower() or "blocked" in data.get("message", "").lower()
        
        # Verify via GET
        get_resp = session.get(f"{BASE_URL}/api/clients/{self.test_client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "blocked"
    
    def test_reactivate_archived_client(self):
        """POST /api/clients/{id}/reactivate should set status back to active."""
        # First archive
        session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/archive")
        
        # Then reactivate
        resp = session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/reactivate")
        assert resp.status_code == 200
        data = resp.json()
        assert "riattivato" in data.get("message", "").lower() or "reactivated" in data.get("message", "").lower()
        
        # Verify via GET
        get_resp = session.get(f"{BASE_URL}/api/clients/{self.test_client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "active"
    
    def test_reactivate_blocked_client(self):
        """POST /api/clients/{id}/reactivate should work for blocked clients too."""
        # First block
        session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/block")
        
        # Then reactivate
        resp = session.post(f"{BASE_URL}/api/clients/{self.test_client_id}/reactivate")
        assert resp.status_code == 200
        
        # Verify via GET
        get_resp = session.get(f"{BASE_URL}/api/clients/{self.test_client_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "active"
    
    def test_archive_nonexistent_client(self):
        """POST /api/clients/{invalid_id}/archive should return 404."""
        resp = session.post(f"{BASE_URL}/api/clients/nonexistent_client_id/archive")
        assert resp.status_code == 404


class TestClientSnapshotOnInvoice:
    """Test that invoices store client_snapshot."""
    
    test_client_id = None
    test_invoice_id = None
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Create a test client and invoice."""
        unique_id = uuid.uuid4().hex[:8]
        
        # Create client with full details
        client_payload = {
            "business_name": f"TEST_SnapshotClient_{unique_id}",
            "client_type": "cliente",
            "partita_iva": f"IT{unique_id}12345",
            "codice_fiscale": f"TSTCF{unique_id}",
            "codice_sdi": "0000000",
            "address": "Via Test 123",
            "city": "Roma",
            "province": "RM",
            "cap": "00100",
        }
        client_resp = session.post(f"{BASE_URL}/api/clients/", json=client_payload)
        assert client_resp.status_code == 201
        self.test_client_id = client_resp.json()["client_id"]
        
        yield
        
        # Cleanup
        if self.test_invoice_id:
            session.delete(f"{BASE_URL}/api/invoices/{self.test_invoice_id}")
        session.delete(f"{BASE_URL}/api/clients/{self.test_client_id}")
    
    def test_create_invoice_stores_client_snapshot(self):
        """POST /api/invoices/ should store client_snapshot with business_name, partita_iva, etc."""
        invoice_payload = {
            "document_type": "FT",
            "client_id": self.test_client_id,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile",
            },
            "lines": [
                {
                    "code": "TEST001",
                    "description": "Test line item",
                    "quantity": 1,
                    "unit_price": 100,
                    "discount_percent": 0,
                    "vat_rate": "22",
                }
            ],
        }
        
        resp = session.post(f"{BASE_URL}/api/invoices/", json=invoice_payload)
        assert resp.status_code == 201, f"Failed to create invoice: {resp.text}"
        data = resp.json()
        self.test_invoice_id = data["invoice_id"]
        
        # The InvoiceResponse model doesn't include client_snapshot, but it's stored in DB
        # Verify via GET which returns raw document with client_snapshot
        get_resp = session.get(f"{BASE_URL}/api/invoices/{self.test_invoice_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        
        # Verify client_snapshot is present in the stored document
        assert "client_snapshot" in get_data, "client_snapshot not in GET response"
        snapshot = get_data["client_snapshot"]
        assert snapshot is not None, "client_snapshot is None"
        
        # Verify snapshot contains expected fields
        assert snapshot.get("business_name") is not None, "business_name not in snapshot"
        assert "TEST_SnapshotClient" in snapshot.get("business_name", "")
        assert snapshot.get("partita_iva") is not None
        assert snapshot.get("codice_sdi") == "0000000"
        assert snapshot.get("city") == "Roma"
        
        print(f"Client snapshot stored: {snapshot}")
    
    def test_get_invoice_returns_client_name_from_snapshot(self):
        """GET /api/invoices/{id} should return client_name from snapshot when available."""
        # First create an invoice
        invoice_payload = {
            "document_type": "FT",
            "client_id": self.test_client_id,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "tax_settings": {
                "apply_rivalsa_inps": False,
                "rivalsa_inps_rate": 4,
                "apply_cassa": False,
                "cassa_type": "",
                "cassa_rate": 4,
                "apply_ritenuta": False,
                "ritenuta_rate": 20,
                "ritenuta_base": "imponibile",
            },
            "lines": [
                {
                    "code": "TEST002",
                    "description": "Test line",
                    "quantity": 1,
                    "unit_price": 50,
                    "discount_percent": 0,
                    "vat_rate": "22",
                }
            ],
        }
        
        create_resp = session.post(f"{BASE_URL}/api/invoices/", json=invoice_payload)
        assert create_resp.status_code == 201
        self.test_invoice_id = create_resp.json()["invoice_id"]
        
        # Now GET the invoice
        get_resp = session.get(f"{BASE_URL}/api/invoices/{self.test_invoice_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        
        # Verify client_name is populated
        assert "client_name" in data
        assert "TEST_SnapshotClient" in data["client_name"]
        
        # Verify snapshot is still there
        assert "client_snapshot" in data
        assert data["client_snapshot"]["business_name"] == data["client_name"]


class TestMigrationEndpoints:
    """Test migration endpoints for backfilling snapshots."""
    
    def test_snapshot_status_endpoint(self):
        """GET /api/admin/migration/snapshot-status should return coverage stats."""
        resp = session.get(f"{BASE_URL}/api/admin/migration/snapshot-status")
        assert resp.status_code == 200
        data = resp.json()
        
        # Should have stats for each collection
        assert "invoices" in data
        assert "preventivi" in data
        assert "ddt" in data
        assert "commesse" in data
        
        # Each should have total, with_snapshot, without_snapshot, coverage
        for coll_name in ["invoices", "preventivi", "ddt", "commesse"]:
            coll_stats = data[coll_name]
            assert "total" in coll_stats
            assert "with_snapshot" in coll_stats
            assert "without_snapshot" in coll_stats
            assert "coverage" in coll_stats
            print(f"{coll_name}: {coll_stats}")
    
    def test_set_default_client_status_endpoint(self):
        """POST /api/admin/migration/set-default-client-status should set active on clients without status."""
        resp = session.post(f"{BASE_URL}/api/admin/migration/set-default-client-status")
        # May return 403 if not admin, or 200 if admin
        assert resp.status_code in [200, 403], f"Unexpected status: {resp.status_code} - {resp.text}"
        
        if resp.status_code == 200:
            data = resp.json()
            assert "modified_count" in data
            print(f"Set default status on {data['modified_count']} clients")
    
    def test_backfill_client_snapshots_endpoint(self):
        """POST /api/admin/migration/backfill-client-snapshots should add snapshots to existing documents."""
        resp = session.post(f"{BASE_URL}/api/admin/migration/backfill-client-snapshots")
        # May return 403 if not admin, or 200 if admin
        assert resp.status_code in [200, 403], f"Unexpected status: {resp.status_code} - {resp.text}"
        
        if resp.status_code == 200:
            data = resp.json()
            assert "report" in data
            report = data["report"]
            assert "total_updated" in report
            assert "collections" in report
            print(f"Backfill report: {report}")


class TestClientStatusInClientResponse:
    """Test that client status field is properly returned in API responses."""
    
    test_client_id = None
    
    @pytest.fixture(autouse=True)
    def setup_test_client(self):
        """Create a test client."""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "business_name": f"TEST_ResponseClient_{unique_id}",
            "client_type": "cliente",
        }
        resp = session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert resp.status_code == 201
        self.test_client_id = resp.json()["client_id"]
        yield
        session.delete(f"{BASE_URL}/api/clients/{self.test_client_id}")
    
    def test_new_client_has_active_status(self):
        """Newly created client should have status='active'."""
        resp = session.get(f"{BASE_URL}/api/clients/{self.test_client_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "active", f"Expected active, got {data.get('status')}"
    
    def test_client_list_includes_status(self):
        """GET /api/clients/ should include status field in response."""
        resp = session.get(f"{BASE_URL}/api/clients/?include_archived=true")
        assert resp.status_code == 200
        data = resp.json()
        
        # Find our test client
        test_client = next((c for c in data["clients"] if c["client_id"] == self.test_client_id), None)
        assert test_client is not None
        assert "status" in test_client
        assert test_client["status"] == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

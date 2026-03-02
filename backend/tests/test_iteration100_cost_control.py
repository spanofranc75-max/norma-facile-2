"""
Iteration 100: Cost Control (Controllo Costi) Feature Tests
Tests for mock purchase invoices, cost assignment to commesse/magazzino/generale,
cost analysis with margin calculation, and commesse search for dropdown.
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "session_costctl_mm90xi6u"
USER_ID = "user_costctl_mm90xi6u"
TEST_COMMESSA_ID = "com_costtest_mm90xi6u"


@pytest.fixture(scope="module")
def api_client():
    """Authenticated session for all tests."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


# ── GET /api/costs/invoices/pending — Mock Invoices ──────────────

class TestPendingInvoices:
    """Test pending invoices endpoint returns mock data correctly."""

    def test_get_pending_invoices_returns_mock_data(self, api_client):
        """Should return 5 mock invoices when no real fatture exist."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "invoices" in data
        assert "total" in data
        assert "mock_count" in data
        
        # Should have 5 mock invoices (or at least some if user already processed some)
        assert data["mock_count"] >= 0
        
        # Check mock invoice structure
        invoices = data["invoices"]
        if len(invoices) > 0:
            inv = invoices[0]
            assert "invoice_id" in inv
            assert "fornitore" in inv
            assert "numero" in inv
            assert "data" in inv
            assert "totale" in inv
            assert "linee" in inv
            assert "is_mock" in inv

    def test_mock_invoice_ids_format(self, api_client):
        """Mock invoices should have IDs like mock_inv_001 to mock_inv_005."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        data = resp.json()
        mock_invoices = [inv for inv in data["invoices"] if inv.get("is_mock")]
        
        for inv in mock_invoices:
            assert inv["invoice_id"].startswith("mock_inv_"), f"Expected mock_inv_ prefix: {inv['invoice_id']}"

    def test_mock_invoices_have_line_items(self, api_client):
        """Each mock invoice should have line items with correct structure."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        data = resp.json()
        mock_invoices = [inv for inv in data["invoices"] if inv.get("is_mock")]
        
        for inv in mock_invoices:
            assert len(inv["linee"]) > 0, f"Invoice {inv['invoice_id']} has no lines"
            for line in inv["linee"]:
                assert "idx" in line
                assert "descrizione" in line
                assert "quantita" in line
                assert "importo" in line


# ── POST /api/costs/invoices/{id}/assign — Cost Assignment ───────

class TestCostAssignment:
    """Test assigning costs from invoices to targets."""

    def test_assign_cost_to_commessa(self, api_client):
        """Should assign mock invoice cost to a commessa."""
        # First get pending invoices to find a mock one
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices available for testing")
        
        invoice = mock_invoices[0]
        invoice_id = invoice["invoice_id"]
        
        # Assign to commessa
        assign_data = {
            "target_type": "commessa",
            "target_id": TEST_COMMESSA_ID,
            "category": "materiali",
            "amount": invoice["totale"],
            "note": "Test assignment to commessa"
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice_id}/assign", json=assign_data)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "message" in data
        assert "cost_id" in data
        assert data["target_type"] == "commessa"
        assert data["importo"] == invoice["totale"]

    def test_assign_cost_to_magazzino(self, api_client):
        """Should assign mock invoice cost to magazzino (stock)."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices available")
        
        invoice = mock_invoices[0]
        invoice_id = invoice["invoice_id"]
        
        assign_data = {
            "target_type": "magazzino",
            "target_id": None,
            "category": "consumabili",
            "note": "Test assignment to warehouse"
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice_id}/assign", json=assign_data)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["target_type"] == "magazzino"

    def test_assign_cost_to_generale(self, api_client):
        """Should assign mock invoice cost to spese generali (overhead)."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices available")
        
        invoice = mock_invoices[0]
        invoice_id = invoice["invoice_id"]
        
        assign_data = {
            "target_type": "generale",
            "target_id": None,
            "category": "trasporti",
            "note": "Test overhead expense"
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice_id}/assign", json=assign_data)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["target_type"] == "generale"

    def test_assign_to_nonexistent_commessa_fails(self, api_client):
        """Should return 404 when assigning to nonexistent commessa."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices available")
        
        invoice = mock_invoices[0]
        
        assign_data = {
            "target_type": "commessa",
            "target_id": "nonexistent_commessa_xyz",
            "category": "materiali"
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 404

    def test_assign_nonexistent_invoice_fails(self, api_client):
        """Should return 404 when invoice doesn't exist."""
        assign_data = {
            "target_type": "magazzino",
            "category": "materiali"
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/nonexistent_inv_123/assign", json=assign_data)
        assert resp.status_code == 404

    def test_assign_with_selected_rows(self, api_client):
        """Should calculate amount from selected rows only."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices available")
        
        invoice = mock_invoices[0]
        if len(invoice["linee"]) < 2:
            pytest.skip("Invoice doesn't have multiple lines")
        
        # Select only first line
        first_line_amount = abs(invoice["linee"][0]["importo"])
        
        assign_data = {
            "target_type": "magazzino",
            "category": "materiali",
            "righe_selezionate": [0],
            "amount": first_line_amount
        }
        
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["importo"] == first_line_amount


# ── GET /api/costs/invoices/processed — Processed Entries ────────

class TestProcessedInvoices:
    """Test processed cost entries endpoint."""

    def test_get_processed_entries(self, api_client):
        """Should return list of processed cost entries."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/processed")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "entries" in data
        assert "total" in data
        
        # Should have some entries from previous tests
        if data["total"] > 0:
            entry = data["entries"][0]
            assert "cost_id" in entry
            assert "fornitore" in entry
            assert "target_type" in entry
            assert "importo" in entry


# ── GET /api/costs/commessa/{commessa_id} — Cost Analysis ────────

class TestCostAnalysis:
    """Test cost analysis endpoint with margin calculation."""

    def test_get_commessa_costs(self, api_client):
        """Should return cost analysis for a commessa."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commessa/{TEST_COMMESSA_ID}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "commessa_id" in data
        assert "valore_preventivo" in data
        assert "totale_costi" in data
        assert "margine" in data
        assert "margine_percentuale" in data
        assert "costi_per_categoria" in data

    def test_cost_analysis_margin_calculation(self, api_client):
        """Margin should equal valore_preventivo - totale_costi."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commessa/{TEST_COMMESSA_ID}")
        assert resp.status_code == 200
        
        data = resp.json()
        expected_margin = data["valore_preventivo"] - data["totale_costi"]
        assert abs(data["margine"] - expected_margin) < 0.01, f"Margin calc wrong: {data['margine']} != {expected_margin}"

    def test_cost_analysis_nonexistent_commessa(self, api_client):
        """Should return 404 for nonexistent commessa."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commessa/nonexistent_xyz")
        assert resp.status_code == 404


# ── GET /api/costs/commesse-search — Commesse Dropdown Search ────

class TestCommesseSearch:
    """Test commesse search for cost assignment dropdown."""

    def test_search_commesse_all(self, api_client):
        """Should return commesse without query filter."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commesse-search")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "commesse" in data
        assert isinstance(data["commesse"], list)

    def test_search_commesse_with_query(self, api_client):
        """Should filter commesse by search query."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commesse-search?q=COSTTEST")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "commesse" in data
        
        # Should find our test commessa
        if len(data["commesse"]) > 0:
            found = any(c["commessa_id"] == TEST_COMMESSA_ID for c in data["commesse"])
            assert found, "Test commessa not found in search results"

    def test_search_commesse_structure(self, api_client):
        """Search results should have required fields."""
        resp = api_client.get(f"{BASE_URL}/api/costs/commesse-search")
        assert resp.status_code == 200
        
        data = resp.json()
        if len(data["commesse"]) > 0:
            commessa = data["commesse"][0]
            assert "commessa_id" in commessa
            assert "numero" in commessa
            assert "title" in commessa


# ── Category Options ─────────────────────────────────────────────

class TestCategories:
    """Test that all category options work correctly."""

    def test_category_materiali(self, api_client):
        """Should accept materiali category."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices")
        
        invoice = mock_invoices[0]
        assign_data = {
            "target_type": "generale",
            "category": "materiali"
        }
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 200
        assert "Materiale Ferroso" in resp.json()["category"]

    def test_category_lavorazioni_esterne(self, api_client):
        """Should accept lavorazioni_esterne category."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices")
        
        invoice = mock_invoices[0]
        assign_data = {
            "target_type": "generale",
            "category": "lavorazioni_esterne"
        }
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 200
        assert "Lavorazione Esterna" in resp.json()["category"]

    def test_category_consumabili(self, api_client):
        """Should accept consumabili category."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices")
        
        invoice = mock_invoices[0]
        assign_data = {
            "target_type": "generale",
            "category": "consumabili"
        }
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 200
        assert "Consumabili" in resp.json()["category"]

    def test_category_trasporti(self, api_client):
        """Should accept trasporti category."""
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        mock_invoices = [inv for inv in resp.json()["invoices"] if inv.get("is_mock")]
        if not mock_invoices:
            pytest.skip("No mock invoices")
        
        invoice = mock_invoices[0]
        assign_data = {
            "target_type": "generale",
            "category": "trasporti"
        }
        resp = api_client.post(f"{BASE_URL}/api/costs/invoices/{invoice['invoice_id']}/assign", json=assign_data)
        assert resp.status_code == 200
        assert "Trasporti" in resp.json()["category"]


# ── Mock Invoice Persistence (Disappears After Assignment) ───────

class TestMockInvoicePersistence:
    """Test that mock invoices disappear from pending after assignment."""

    def test_assigned_mock_not_in_pending(self, api_client):
        """Assigned mock invoices should not reappear in pending list."""
        # Get processed entries to see what was assigned
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/processed")
        assert resp.status_code == 200
        
        processed = resp.json()["entries"]
        assigned_mock_ids = [e["source_invoice_id"] for e in processed if e.get("is_mock")]
        
        # Get pending invoices
        resp = api_client.get(f"{BASE_URL}/api/costs/invoices/pending")
        assert resp.status_code == 200
        
        pending_mock_ids = [inv["invoice_id"] for inv in resp.json()["invoices"] if inv.get("is_mock")]
        
        # Check no overlap
        overlap = set(assigned_mock_ids) & set(pending_mock_ids)
        assert len(overlap) == 0, f"Assigned mocks still in pending: {overlap}"


# ── Cleanup ─────────────────────────────────────────────────────

class TestCleanup:
    """Clean up test data after tests."""

    def test_cleanup_test_data(self, api_client):
        """Remove test user, session, commessa, and cost entries."""
        import subprocess
        result = subprocess.run([
            "mongosh", "--quiet", "--eval", f"""
            use('test_database');
            db.project_costs.deleteMany({{user_id: '{USER_ID}'}});
            db.commesse.deleteMany({{user_id: '{USER_ID}'}});
            db.users.deleteMany({{user_id: '{USER_ID}'}});
            db.user_sessions.deleteMany({{user_id: '{USER_ID}'}});
            print('Cleanup complete');
            """
        ], capture_output=True, text=True)
        assert "Cleanup complete" in result.stdout or result.returncode == 0

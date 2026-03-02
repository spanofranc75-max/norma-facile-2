"""
Test Atomic Counters for Preventivi/Invoices and Scadenziario Automatico Feature.

Features tested:
1. BUG FIX: POST /api/preventivi/ uses atomic counter (document_counters collection)
2. BUG FIX: POST /api/invoices/from-preventivo uses atomic counter for FT numbering
3. FEATURE: Scadenziario Automatico - auto-generated payment deadlines from client payment_type
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated API calls."""
    from pymongo import MongoClient
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    # Create test user
    user_id = f"test_counter_user_{int(time.time())}"
    session_token = f"test_session_{int(time.time())}"
    
    db.users.insert_one({
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Counter User",
        "created_at": time.time()
    })
    
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": time.time() + 86400,
        "created_at": time.time()
    })
    
    yield {"user_id": user_id, "session_token": session_token, "db": db}
    
    # Cleanup
    db.users.delete_many({"user_id": user_id})
    db.user_sessions.delete_many({"session_token": session_token})
    db.preventivi.delete_many({"user_id": user_id})
    db.invoices.delete_many({"user_id": user_id})
    db.clients.delete_many({"user_id": user_id})
    db.payment_types.delete_many({"user_id": user_id})
    db.document_counters.delete_many({"counter_id": {"$regex": f".*{user_id}.*"}})
    client.close()


@pytest.fixture(scope="module")
def api_client(test_session):
    """Requests session with auth cookie."""
    session = requests.Session()
    session.cookies.set("session_token", test_session["session_token"])
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_client(api_client, test_session):
    """Create a test client for invoice tests."""
    payload = {
        "business_name": "Test Client Scadenze",
        "partita_iva": "IT12345678901",
        "email": "client@test.com",
        "codice_sdi": "0000000"
    }
    res = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
    assert res.status_code == 201, f"Failed to create client: {res.text}"
    return res.json()


@pytest.fixture(scope="module")
def payment_type_30_60_90(api_client, test_session):
    """Create payment type with 30-60-90 days quotes."""
    payload = {
        "codice": "TEST_30_60_90",
        "descrizione": "Test 30-60-90 giorni",
        "tipo": "ricevuta_bancaria",
        "quote": [
            {"giorni": 30, "quota": 33.33},
            {"giorni": 60, "quota": 33.33},
            {"giorni": 90, "quota": 33.34}
        ],
        "fine_mese": False,
        "richiedi_giorno_scadenza": False
    }
    res = api_client.post(f"{BASE_URL}/api/payment-types/", json=payload)
    assert res.status_code == 201, f"Failed to create payment type: {res.text}"
    return res.json()


class TestAtomicCounterPreventivi:
    """Test atomic counter for preventivi numbering (BUG FIX)."""
    
    def test_create_first_preventivo_initializes_counter(self, api_client, test_session, test_client):
        """Test that creating a preventivo initializes counter in document_counters collection."""
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Preventivo Counter 1",
            "validity_days": 30,
            "lines": [
                {"description": "Test Line 1", "quantity": 1, "unit_price": 100, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201, f"Failed to create preventivo: {res.text}"
        
        data = res.json()
        assert "number" in data
        assert data["number"].startswith("PRV-"), f"Expected PRV- prefix, got: {data['number']}"
        print(f"Created preventivo with number: {data['number']}")
        
        # Store for later tests
        test_session["first_preventivo"] = data
        return data
    
    def test_second_preventivo_increments_counter(self, api_client, test_session, test_client):
        """Test that second preventivo gets incremented number."""
        # Create second preventivo
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Preventivo Counter 2",
            "validity_days": 30,
            "lines": [
                {"description": "Test Line 2", "quantity": 2, "unit_price": 200, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201, f"Failed to create second preventivo: {res.text}"
        
        data = res.json()
        first_number = test_session.get("first_preventivo", {}).get("number", "PRV-2026-0000")
        
        # Extract sequence numbers
        first_seq = int(first_number.split("-")[-1])
        second_seq = int(data["number"].split("-")[-1])
        
        assert second_seq == first_seq + 1, f"Expected sequential number. First: {first_seq}, Second: {second_seq}"
        print(f"Sequential numbering verified: {first_number} -> {data['number']}")
        
        test_session["second_preventivo"] = data
        return data
    
    def test_delete_preventivo_does_not_affect_counter(self, api_client, test_session, test_client):
        """Test that deleting a preventivo doesn't cause duplicate numbers (counter is atomic)."""
        # Delete first preventivo
        first_id = test_session.get("first_preventivo", {}).get("preventivo_id")
        if first_id:
            res = api_client.delete(f"{BASE_URL}/api/preventivi/{first_id}")
            assert res.status_code == 200, f"Failed to delete preventivo: {res.text}"
            print(f"Deleted preventivo: {first_id}")
        
        # Create new preventivo - should NOT reuse deleted number
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Preventivo After Delete",
            "validity_days": 30,
            "lines": [
                {"description": "Test Line 3", "quantity": 3, "unit_price": 300, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201, f"Failed to create preventivo after delete: {res.text}"
        
        data = res.json()
        second_number = test_session.get("second_preventivo", {}).get("number", "PRV-2026-0001")
        second_seq = int(second_number.split("-")[-1])
        new_seq = int(data["number"].split("-")[-1])
        
        # New number should be higher than second, not reusing first's deleted number
        assert new_seq == second_seq + 1, f"Counter should increment atomically. Second: {second_seq}, New: {new_seq}"
        print(f"Atomic counter verified after delete: {second_number} -> {data['number']}")
        
        test_session["third_preventivo"] = data
        return data


class TestAtomicCounterInvoices:
    """Test atomic counter for invoice numbering (BUG FIX)."""
    
    def test_create_invoice_from_preventivo_uses_atomic_counter(self, api_client, test_session, test_client):
        """Test that creating invoice from preventivo uses atomic FT counter."""
        # Create a preventivo first
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Preventivo for Invoice",
            "validity_days": 30,
            "lines": [
                {"description": "Service 1", "quantity": 1, "unit_price": 1000, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201, f"Failed to create preventivo: {res.text}"
        preventivo = res.json()
        
        # Convert to invoice
        res = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{preventivo['preventivo_id']}")
        assert res.status_code == 200, f"Failed to convert preventivo to invoice: {res.text}"
        
        invoice_data = res.json()
        assert "document_number" in invoice_data
        assert invoice_data["document_number"].startswith("FT-"), f"Expected FT- prefix, got: {invoice_data['document_number']}"
        print(f"Created invoice from preventivo: {invoice_data['document_number']}")
        
        test_session["first_invoice"] = invoice_data
        return invoice_data
    
    def test_second_invoice_increments_counter(self, api_client, test_session, test_client):
        """Test second invoice gets incremented number."""
        # Create another preventivo
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Preventivo for Second Invoice",
            "validity_days": 30,
            "lines": [
                {"description": "Service 2", "quantity": 1, "unit_price": 2000, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201
        preventivo = res.json()
        
        # Convert to invoice
        res = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{preventivo['preventivo_id']}")
        assert res.status_code == 200, f"Failed to convert second preventivo: {res.text}"
        
        invoice_data = res.json()
        first_doc = test_session.get("first_invoice", {}).get("document_number", "FT-2026/0000")
        
        # Extract sequence numbers from FT-YYYY/NNNN format
        first_seq = int(first_doc.split("/")[-1])
        second_seq = int(invoice_data["document_number"].split("/")[-1])
        
        assert second_seq == first_seq + 1, f"Invoice counter not sequential. First: {first_seq}, Second: {second_seq}"
        print(f"Sequential invoice numbering verified: {first_doc} -> {invoice_data['document_number']}")
        
        test_session["second_invoice"] = invoice_data
        return invoice_data


class TestScadenziarioAutomatico:
    """Test automatic payment deadlines from client payment type (FEATURE)."""
    
    def test_link_payment_type_to_client(self, api_client, test_session, test_client, payment_type_30_60_90):
        """Link payment type to client."""
        # Update client with payment_type_id
        res = api_client.put(
            f"{BASE_URL}/api/clients/{test_client['client_id']}",
            json={"payment_type_id": payment_type_30_60_90["payment_type_id"]}
        )
        assert res.status_code == 200, f"Failed to update client: {res.text}"
        print(f"Linked payment type {payment_type_30_60_90['codice']} to client")
        
        # Verify update
        res = api_client.get(f"{BASE_URL}/api/clients/{test_client['client_id']}")
        assert res.status_code == 200
        client_data = res.json()
        assert client_data.get("payment_type_id") == payment_type_30_60_90["payment_type_id"]
    
    def test_generate_scadenze_endpoint(self, api_client, test_session, test_client, payment_type_30_60_90):
        """Test POST /api/invoices/{id}/scadenze/genera generates deadlines."""
        # First create a preventivo and convert to invoice
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Scadenziario Preventivo",
            "validity_days": 30,
            "lines": [
                {"description": "Service Scadenze", "quantity": 1, "unit_price": 3000, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201
        preventivo = res.json()
        
        # Convert to invoice
        res = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{preventivo['preventivo_id']}")
        assert res.status_code == 200
        invoice = res.json()
        invoice_id = invoice["invoice_id"]
        
        # Now call /scadenze/genera
        res = api_client.post(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze/genera")
        assert res.status_code == 200, f"Failed to generate scadenze: {res.text}"
        
        data = res.json()
        assert "scadenze" in data
        scadenze = data["scadenze"]
        
        # Should have 3 scadenze (30-60-90 days)
        assert len(scadenze) == 3, f"Expected 3 scadenze, got {len(scadenze)}"
        
        print(f"Generated {len(scadenze)} scadenze:")
        for s in scadenze:
            print(f"  Rata {s['rata']}: {s['data_scadenza']} - {s['importo']}€ ({s['quota_pct']}%)")
        
        test_session["scadenze_invoice_id"] = invoice_id
        return scadenze
    
    def test_get_scadenze_endpoint(self, api_client, test_session):
        """Test GET /api/invoices/{id}/scadenze returns generated scadenze."""
        invoice_id = test_session.get("scadenze_invoice_id")
        if not invoice_id:
            pytest.skip("No invoice with scadenze to test")
        
        res = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze")
        assert res.status_code == 200, f"Failed to get scadenze: {res.text}"
        
        data = res.json()
        assert "scadenze" in data
        assert len(data["scadenze"]) == 3
        print(f"GET /scadenze returned {len(data['scadenze'])} scadenze")
    
    def test_mark_scadenza_as_paid(self, api_client, test_session):
        """Test PATCH /api/invoices/{id}/scadenze/{rata}/paga marks installment as paid."""
        invoice_id = test_session.get("scadenze_invoice_id")
        if not invoice_id:
            pytest.skip("No invoice with scadenze to test")
        
        # Mark first rata as paid
        res = api_client.patch(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze/1/paga")
        assert res.status_code == 200, f"Failed to mark scadenza as paid: {res.text}"
        
        data = res.json()
        assert "scadenze" in data
        
        # Find rata 1 and verify it's marked as paid
        rata_1 = next((s for s in data["scadenze"] if s["rata"] == 1), None)
        assert rata_1 is not None
        assert rata_1["pagata"] == True, f"Rata 1 should be marked as paid"
        assert rata_1["data_pagamento"] is not None
        print(f"Rata 1 marked as paid on {rata_1['data_pagamento']}")
    
    def test_toggle_scadenza_unpaid(self, api_client, test_session):
        """Test toggling payment status back to unpaid."""
        invoice_id = test_session.get("scadenze_invoice_id")
        if not invoice_id:
            pytest.skip("No invoice with scadenze to test")
        
        # Toggle rata 1 back to unpaid
        res = api_client.patch(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze/1/paga")
        assert res.status_code == 200, f"Failed to toggle scadenza: {res.text}"
        
        data = res.json()
        rata_1 = next((s for s in data["scadenze"] if s["rata"] == 1), None)
        assert rata_1 is not None
        assert rata_1["pagata"] == False, f"Rata 1 should be marked as unpaid after toggle"
        print("Rata 1 toggled back to unpaid")
    
    def test_status_emessa_auto_generates_scadenze(self, api_client, test_session, test_client, payment_type_30_60_90):
        """Test that changing invoice status to 'emessa' auto-generates scadenze."""
        # Create new invoice via direct API
        from datetime import date
        today = date.today().isoformat()
        
        # First create a preventivo and convert (to have an invoice)
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Auto Scadenze",
            "validity_days": 30,
            "lines": [
                {"description": "Auto Scadenze Test", "quantity": 1, "unit_price": 6000, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201
        preventivo = res.json()
        
        res = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{preventivo['preventivo_id']}")
        assert res.status_code == 200
        invoice = res.json()
        invoice_id = invoice["invoice_id"]
        
        # Verify no scadenze yet
        res = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze")
        assert res.status_code == 200
        initial_scadenze = res.json().get("scadenze", [])
        
        # Update status to 'emessa' - should trigger auto-generation
        res = api_client.patch(
            f"{BASE_URL}/api/invoices/{invoice_id}/status",
            json={"status": "emessa"}
        )
        assert res.status_code == 200, f"Failed to update status: {res.text}"
        
        # Verify scadenze were auto-generated
        res = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}/scadenze")
        assert res.status_code == 200
        data = res.json()
        
        assert "scadenze" in data
        scadenze = data["scadenze"]
        assert len(scadenze) == 3, f"Expected 3 auto-generated scadenze, got {len(scadenze)}"
        print(f"Auto-generated {len(scadenze)} scadenze when status changed to 'emessa'")


class TestScadenziarioDashboardKPI:
    """Test scadenziario dashboard includes 'incasso' type and KPIs."""
    
    def test_dashboard_returns_incasso_type(self, api_client, test_session, test_client, payment_type_30_60_90):
        """Test GET /api/fatture-ricevute/scadenziario/dashboard includes 'incasso' entries."""
        # First ensure we have an emitted invoice with scadenze
        payload = {
            "client_id": test_client["client_id"],
            "subject": "Test Dashboard Incasso",
            "validity_days": 30,
            "lines": [
                {"description": "Dashboard Test", "quantity": 1, "unit_price": 10000, "vat_rate": "22"}
            ]
        }
        res = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert res.status_code == 201
        preventivo = res.json()
        
        res = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{preventivo['preventivo_id']}")
        assert res.status_code == 200
        invoice = res.json()
        
        # Emit the invoice to trigger scadenze generation
        res = api_client.patch(
            f"{BASE_URL}/api/invoices/{invoice['invoice_id']}/status",
            json={"status": "emessa"}
        )
        assert res.status_code == 200
        
        # Now check dashboard
        res = api_client.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert res.status_code == 200, f"Dashboard request failed: {res.text}"
        
        data = res.json()
        assert "scadenze" in data
        assert "kpi" in data
        
        # Check for 'incasso' type entries
        incasso_entries = [s for s in data["scadenze"] if s.get("tipo") == "incasso"]
        print(f"Found {len(incasso_entries)} incasso entries in dashboard")
        
        # Should have incasso entries from our emitted invoice
        assert len(incasso_entries) > 0, "Expected 'incasso' type entries in scadenziario dashboard"
        
        # Verify incasso entry structure
        if incasso_entries:
            entry = incasso_entries[0]
            assert "titolo" in entry
            assert "data_scadenza" in entry
            assert "importo" in entry
            assert entry["tipo"] == "incasso"
            print(f"Sample incasso entry: {entry['titolo']} - {entry['data_scadenza']} - {entry['importo']}€")
    
    def test_dashboard_kpi_includes_incassi(self, api_client, test_session):
        """Test dashboard KPI includes incassi_scaduti and incassi_mese_corrente."""
        res = api_client.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert res.status_code == 200
        
        data = res.json()
        kpi = data.get("kpi", {})
        
        # Verify new KPI fields exist
        assert "incassi_scaduti" in kpi, "KPI should include incassi_scaduti"
        assert "incassi_mese_corrente" in kpi, "KPI should include incassi_mese_corrente"
        
        print(f"KPI incassi_scaduti: {kpi['incassi_scaduti']}€")
        print(f"KPI incassi_mese_corrente: {kpi['incassi_mese_corrente']}€")
        print(f"Full KPI: {kpi}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

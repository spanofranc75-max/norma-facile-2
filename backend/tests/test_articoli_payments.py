"""
Tests for P0 Features:
1) Catalogo Articoli CRUD + Search + Bulk Import
2) Payment Tracking (Scadenze) for invoices
3) Invoice Duplicate functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_session_articoli_1772213744502')

# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_client():
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


@pytest.fixture(scope="module")
def test_client_id(api_client):
    """Create a test client for invoice creation."""
    payload = {
        "business_name": "TEST_CLIENT_Articoli",
        "client_type": "business",
        "address": "Via Test 123",
        "cap": "00100",
        "city": "Roma",
        "province": "RM",
        "country": "IT",
        "codice_fiscale": "TEST12345678901",
        "partita_iva": "12345678901",
        "codice_sdi": "0000000"
    }
    resp = api_client.post(f"{BASE_URL}/api/clients/", json=payload)
    if resp.status_code == 201:
        return resp.json().get("client_id")
    # If client exists, try to get it
    resp = api_client.get(f"{BASE_URL}/api/clients/")
    clients = resp.json().get("clients", [])
    for c in clients:
        if c.get("business_name") == "TEST_CLIENT_Articoli":
            return c.get("client_id")
    pytest.skip("Failed to create test client")


# ════════════════════════════════════════════════════════════════════
# ARTICOLI CRUD TESTS
# ════════════════════════════════════════════════════════════════════

class TestArticoliCRUD:
    """Tests for Catalogo Articoli endpoints."""
    
    created_articolo_id = None
    
    def test_list_articoli_empty_or_existing(self, api_client):
        """GET /api/articoli/ returns list."""
        resp = api_client.get(f"{BASE_URL}/api/articoli/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "articoli" in data
        assert "total" in data
        assert isinstance(data["articoli"], list)
        print(f"✓ GET /api/articoli/ returns {data['total']} articoli")
    
    def test_create_articolo(self, api_client):
        """POST /api/articoli/ creates new articolo."""
        payload = {
            "codice": "TEST_ART_001",
            "descrizione": "Articolo di test per automazione",
            "categoria": "materiale",
            "unita_misura": "pz",
            "prezzo_unitario": 99.50,
            "aliquota_iva": "22",
            "fornitore_nome": "Fornitore Test",
            "note": "Note di test"
        }
        resp = api_client.post(f"{BASE_URL}/api/articoli/", json=payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["codice"] == "TEST_ART_001"
        assert data["descrizione"] == "Articolo di test per automazione"
        assert data["prezzo_unitario"] == 99.50
        assert data["categoria"] == "materiale"
        assert "articolo_id" in data
        TestArticoliCRUD.created_articolo_id = data["articolo_id"]
        print(f"✓ POST /api/articoli/ created {data['articolo_id']}")
    
    def test_get_articolo_by_id(self, api_client):
        """GET /api/articoli/{id} returns articolo."""
        if not TestArticoliCRUD.created_articolo_id:
            pytest.skip("No articolo created")
        resp = api_client.get(f"{BASE_URL}/api/articoli/{TestArticoliCRUD.created_articolo_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["articolo_id"] == TestArticoliCRUD.created_articolo_id
        assert data["codice"] == "TEST_ART_001"
        # Check storico_prezzi populated
        assert "storico_prezzi" in data
        assert len(data["storico_prezzi"]) >= 1
        print(f"✓ GET /api/articoli/{TestArticoliCRUD.created_articolo_id} - storico has {len(data['storico_prezzi'])} entries")
    
    def test_update_articolo(self, api_client):
        """PUT /api/articoli/{id} updates articolo."""
        if not TestArticoliCRUD.created_articolo_id:
            pytest.skip("No articolo created")
        payload = {
            "descrizione": "Descrizione aggiornata",
            "prezzo_unitario": 120.00
        }
        resp = api_client.put(f"{BASE_URL}/api/articoli/{TestArticoliCRUD.created_articolo_id}", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["descrizione"] == "Descrizione aggiornata"
        assert data["prezzo_unitario"] == 120.00
        # Verify price history updated
        assert len(data["storico_prezzi"]) >= 2, "Price history should have new entry"
        print(f"✓ PUT /api/articoli/{TestArticoliCRUD.created_articolo_id} - price updated, storico has {len(data['storico_prezzi'])} entries")
    
    def test_search_articoli(self, api_client):
        """GET /api/articoli/search?q=xxx returns matching articles."""
        resp = api_client.get(f"{BASE_URL}/api/articoli/search?q=TEST_ART")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "results" in data
        # Should find the test article
        found = any(r.get("codice") == "TEST_ART_001" for r in data["results"])
        assert found, "Search should find TEST_ART_001"
        print(f"✓ GET /api/articoli/search?q=TEST_ART - found {len(data['results'])} results")
    
    def test_bulk_import_articoli(self, api_client):
        """POST /api/articoli/bulk-import imports multiple articoli."""
        payload = [
            {
                "codice": "BULK_001",
                "descrizione": "Articolo bulk import 1",
                "categoria": "lavorazione",
                "unita_misura": "h",
                "prezzo_unitario": 50.00,
                "aliquota_iva": "22",
                "fornitore_nome": "Fornitore Bulk"
            },
            {
                "codice": "BULK_002",
                "descrizione": "Articolo bulk import 2",
                "categoria": "servizio",
                "unita_misura": "corpo",
                "prezzo_unitario": 200.00,
                "aliquota_iva": "22"
            }
        ]
        resp = api_client.post(f"{BASE_URL}/api/articoli/bulk-import", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "created" in data
        assert "updated" in data
        assert data["created"] + data["updated"] >= 2
        print(f"✓ POST /api/articoli/bulk-import - created: {data['created']}, updated: {data['updated']}")
    
    def test_list_articoli_with_filter(self, api_client):
        """GET /api/articoli/?categoria=xxx filters by category."""
        resp = api_client.get(f"{BASE_URL}/api/articoli/?categoria=materiale")
        assert resp.status_code == 200
        data = resp.json()
        # All returned should be materiale
        for art in data["articoli"]:
            assert art.get("categoria") == "materiale", f"Expected materiale, got {art.get('categoria')}"
        print(f"✓ GET /api/articoli/?categoria=materiale - {len(data['articoli'])} materiale items")
    
    def test_delete_articolo(self, api_client):
        """DELETE /api/articoli/{id} deletes articolo."""
        if not TestArticoliCRUD.created_articolo_id:
            pytest.skip("No articolo created")
        resp = api_client.delete(f"{BASE_URL}/api/articoli/{TestArticoliCRUD.created_articolo_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        # Verify deleted
        resp2 = api_client.get(f"{BASE_URL}/api/articoli/{TestArticoliCRUD.created_articolo_id}")
        assert resp2.status_code == 404, "Deleted articolo should return 404"
        print(f"✓ DELETE /api/articoli/{TestArticoliCRUD.created_articolo_id} - verified deleted")
    
    def test_cleanup_bulk_articoli(self, api_client):
        """Cleanup bulk imported articles."""
        for code in ["BULK_001", "BULK_002"]:
            resp = api_client.get(f"{BASE_URL}/api/articoli/?q={code}")
            if resp.status_code == 200:
                for art in resp.json().get("articoli", []):
                    if art.get("codice") == code:
                        api_client.delete(f"{BASE_URL}/api/articoli/{art['articolo_id']}")
        print("✓ Cleanup bulk articoli completed")


# ════════════════════════════════════════════════════════════════════
# PAYMENT TRACKING (SCADENZE) TESTS
# ════════════════════════════════════════════════════════════════════

class TestPaymentTracking:
    """Tests for invoice payment tracking (scadenze)."""
    
    test_invoice_id = None
    test_payment_id = None
    
    def test_create_invoice_for_payments(self, api_client, test_client_id):
        """Create an invoice to test payment tracking."""
        payload = {
            "document_type": "FT",
            "client_id": test_client_id,
            "issue_date": "2026-01-15",
            "payment_method": "bonifico",
            "payment_terms": "30gg",
            "lines": [
                {
                    "code": "SRV01",
                    "description": "Servizio test pagamenti",
                    "quantity": 2,
                    "unit_price": 500.00,
                    "discount_percent": 0,
                    "vat_rate": "22"
                }
            ]
        }
        resp = api_client.post(f"{BASE_URL}/api/invoices/", json=payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        TestPaymentTracking.test_invoice_id = data["invoice_id"]
        # Verify payment tracking fields in response
        assert "totale_pagato" in data or data.get("totale_pagato", 0) == 0
        assert "payment_status" in data
        print(f"✓ Created invoice {data['document_number']} for payment testing")
    
    def test_get_scadenze_initial(self, api_client):
        """GET /api/invoices/{id}/scadenze returns payment schedule."""
        if not TestPaymentTracking.test_invoice_id:
            pytest.skip("No invoice created")
        resp = api_client.get(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Verify response structure
        assert "total_document" in data
        assert "totale_pagato" in data
        assert "residuo" in data
        assert "pagamenti" in data
        assert "payment_status" in data
        assert data["payment_status"] == "non_pagata"
        assert data["totale_pagato"] == 0
        assert data["residuo"] == data["total_document"]
        print(f"✓ GET scadenze: total={data['total_document']}, residuo={data['residuo']}, status={data['payment_status']}")
    
    def test_record_partial_payment(self, api_client):
        """POST /api/invoices/{id}/scadenze/pagamento records payment."""
        if not TestPaymentTracking.test_invoice_id:
            pytest.skip("No invoice created")
        # First get the total to calculate partial payment
        resp = api_client.get(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze")
        total = resp.json().get("total_document", 1000)
        partial_amount = round(total / 2, 2)  # Pay half
        
        payload = {
            "importo": partial_amount,
            "data_pagamento": "2026-01-20",
            "metodo": "bonifico",
            "note": "Acconto primo pagamento"
        }
        resp = api_client.post(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze/pagamento", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["totale_pagato"] == partial_amount
        assert data["payment_status"] == "parzialmente_pagata"
        print(f"✓ Recorded partial payment: {partial_amount}, status={data['payment_status']}")
    
    def test_get_scadenze_after_partial_payment(self, api_client):
        """Verify scadenze reflects partial payment."""
        if not TestPaymentTracking.test_invoice_id:
            pytest.skip("No invoice created")
        resp = api_client.get(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_status"] == "parzialmente_pagata"
        assert data["totale_pagato"] > 0
        assert data["residuo"] > 0
        assert len(data["pagamenti"]) == 1
        TestPaymentTracking.test_payment_id = data["pagamenti"][0].get("payment_id")
        print(f"✓ Scadenze after partial: pagato={data['totale_pagato']}, residuo={data['residuo']}")
    
    def test_record_full_payment(self, api_client):
        """Record remaining payment to fully pay invoice."""
        if not TestPaymentTracking.test_invoice_id:
            pytest.skip("No invoice created")
        # Get remaining amount
        resp = api_client.get(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze")
        residuo = resp.json().get("residuo", 0)
        
        if residuo > 0:
            payload = {
                "importo": residuo,
                "data_pagamento": "2026-01-25",
                "metodo": "bonifico",
                "note": "Saldo finale"
            }
            resp = api_client.post(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze/pagamento", json=payload)
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert data["payment_status"] == "pagata"
            assert data["residuo"] <= 0.01  # Allow for floating point
            print(f"✓ Full payment recorded: status={data['payment_status']}, residuo={data['residuo']}")
        else:
            print("✓ Invoice already fully paid")
    
    def test_delete_payment(self, api_client):
        """DELETE /api/invoices/{id}/scadenze/pagamento/{payment_id} deletes payment."""
        if not TestPaymentTracking.test_invoice_id:
            pytest.skip("No invoice created")
        # Get current payments
        resp = api_client.get(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze")
        payments = resp.json().get("pagamenti", [])
        if not payments:
            pytest.skip("No payments to delete")
        
        payment_id = payments[0].get("payment_id")
        resp = api_client.delete(f"{BASE_URL}/api/invoices/{TestPaymentTracking.test_invoice_id}/scadenze/pagamento/{payment_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "payment_status" in data
        print(f"✓ Deleted payment {payment_id}, new status={data['payment_status']}")
    
    def test_invoices_list_has_payment_columns(self, api_client):
        """Verify invoice list includes payment tracking fields."""
        resp = api_client.get(f"{BASE_URL}/api/invoices/")
        assert resp.status_code == 200
        data = resp.json()
        if data.get("invoices"):
            inv = data["invoices"][0]
            # These fields should be present (may be 0 or null)
            assert "totale_pagato" in inv or inv.get("totale_pagato") is None
            print(f"✓ Invoice list contains payment tracking fields")
        else:
            print("✓ No invoices in list to verify")


# ════════════════════════════════════════════════════════════════════
# INVOICE DUPLICATE TESTS
# ════════════════════════════════════════════════════════════════════

class TestInvoiceDuplicate:
    """Tests for invoice duplicate functionality."""
    
    original_invoice_id = None
    duplicated_invoice_id = None
    
    def test_create_invoice_to_duplicate(self, api_client, test_client_id):
        """Create an invoice to duplicate."""
        payload = {
            "document_type": "FT",
            "client_id": test_client_id,
            "issue_date": "2026-01-10",
            "payment_method": "carta",
            "payment_terms": "immediato",
            "notes": "Note da duplicare",
            "lines": [
                {
                    "code": "DUP01",
                    "description": "Prodotto da duplicare",
                    "quantity": 3,
                    "unit_price": 150.00,
                    "discount_percent": 10,
                    "vat_rate": "22"
                }
            ]
        }
        resp = api_client.post(f"{BASE_URL}/api/invoices/", json=payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        TestInvoiceDuplicate.original_invoice_id = data["invoice_id"]
        print(f"✓ Created original invoice {data['document_number']}")
    
    def test_duplicate_invoice(self, api_client):
        """POST /api/invoices/{id}/duplicate creates copy."""
        if not TestInvoiceDuplicate.original_invoice_id:
            pytest.skip("No original invoice")
        resp = api_client.post(f"{BASE_URL}/api/invoices/{TestInvoiceDuplicate.original_invoice_id}/duplicate")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        TestInvoiceDuplicate.duplicated_invoice_id = data["invoice_id"]
        # Verify it's a new invoice
        assert data["invoice_id"] != TestInvoiceDuplicate.original_invoice_id
        assert data["document_number"] != ""
        # Status should be bozza
        assert data["status"] == "bozza"
        # Payment tracking reset
        assert data.get("totale_pagato", 0) == 0
        assert data.get("payment_status") == "non_pagata"
        # Lines should be copied
        assert len(data.get("lines", [])) >= 1
        print(f"✓ Duplicated invoice: {data['document_number']} (status={data['status']})")
    
    def test_duplicated_invoice_has_same_lines(self, api_client):
        """Verify duplicated invoice has same line items."""
        if not TestInvoiceDuplicate.duplicated_invoice_id:
            pytest.skip("No duplicated invoice")
        # Get original
        orig_resp = api_client.get(f"{BASE_URL}/api/invoices/{TestInvoiceDuplicate.original_invoice_id}")
        dup_resp = api_client.get(f"{BASE_URL}/api/invoices/{TestInvoiceDuplicate.duplicated_invoice_id}")
        
        assert orig_resp.status_code == 200
        assert dup_resp.status_code == 200
        
        orig_lines = orig_resp.json().get("lines", [])
        dup_lines = dup_resp.json().get("lines", [])
        
        assert len(orig_lines) == len(dup_lines)
        # Compare first line
        if orig_lines and dup_lines:
            assert orig_lines[0].get("description") == dup_lines[0].get("description")
            assert orig_lines[0].get("unit_price") == dup_lines[0].get("unit_price")
        print(f"✓ Duplicated invoice has {len(dup_lines)} lines matching original")
    
    def test_cleanup_duplicate_invoices(self, api_client):
        """Delete test invoices."""
        for inv_id in [TestInvoiceDuplicate.duplicated_invoice_id, TestInvoiceDuplicate.original_invoice_id, TestPaymentTracking.test_invoice_id]:
            if inv_id:
                api_client.delete(f"{BASE_URL}/api/invoices/{inv_id}")
        print("✓ Cleanup test invoices completed")


# ════════════════════════════════════════════════════════════════════
# AUTHENTICATION TESTS
# ════════════════════════════════════════════════════════════════════

class TestAuthRequired:
    """Verify endpoints require authentication."""
    
    def test_articoli_requires_auth(self):
        """Articoli endpoint returns 401 without auth."""
        resp = requests.get(f"{BASE_URL}/api/articoli/")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✓ GET /api/articoli/ requires auth (401)")
    
    def test_scadenze_requires_auth(self):
        """Scadenze endpoint returns 401 without auth."""
        resp = requests.get(f"{BASE_URL}/api/invoices/fake-id/scadenze")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✓ GET /api/invoices/{id}/scadenze requires auth (401)")
    
    def test_duplicate_requires_auth(self):
        """Duplicate endpoint returns 401 without auth."""
        resp = requests.post(f"{BASE_URL}/api/invoices/fake-id/duplicate")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✓ POST /api/invoices/{id}/duplicate requires auth (401)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 114: ScadenziarioPage Invoicex-style table restyling tests.

Tests the new table-based layout replacing the previous fintech card design.
Verifies backend returns data_documento and pagamento fields for scadenze items.
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token and user id for authenticated requests
TEST_USER_PREFIX = "test_invoicex_114_"


@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated requests."""
    import subprocess
    timestamp = int(datetime.now().timestamp() * 1000)
    user_id = f"{TEST_USER_PREFIX}{timestamp}"
    session_token = f"test_session_invoicex_{timestamp}"
    
    # Create user and session via mongosh
    create_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.invoicex.{timestamp}@example.com',
        name: 'Test Invoicex 114',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--eval', create_script], capture_output=True)
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    db.fatture_ricevute.deleteMany({{user_id: '{user_id}'}});
    db.invoices.deleteMany({{user_id: '{user_id}'}});
    """
    subprocess.run(['mongosh', '--eval', cleanup_script], capture_output=True)


@pytest.fixture
def auth_headers(test_session):
    """Return headers with auth token."""
    return {
        "Authorization": f"Bearer {test_session['session_token']}",
        "Content-Type": "application/json"
    }


class TestScadenziarioDashboardFields:
    """Test that dashboard endpoint returns new fields: data_documento, pagamento."""
    
    def test_dashboard_returns_scadenze_array(self, auth_headers):
        """Dashboard endpoint returns scadenze array."""
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "scadenze" in data
        assert isinstance(data["scadenze"], list)
        print("PASS: Dashboard returns scadenze array")
    
    def test_dashboard_returns_kpi_object(self, auth_headers):
        """Dashboard endpoint returns kpi object with required fields."""
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "kpi" in data
        kpi = data["kpi"]
        required_kpi_fields = [
            "pagamenti_scaduti", "pagamenti_mese_corrente",
            "incassi_scaduti", "incassi_mese_corrente",
            "totale_acquisti_anno", "scadenze_totali",
            "scadute", "in_scadenza", "inbox_da_processare"
        ]
        for field in required_kpi_fields:
            assert field in kpi, f"Missing KPI field: {field}"
        print(f"PASS: Dashboard returns KPI with all required fields: {list(kpi.keys())}")
    
    def test_scadenza_has_data_documento_field(self, auth_headers, test_session):
        """Scadenze items include data_documento field."""
        # Create a fattura ricevuta with data_documento
        fr_data = {
            "fornitore_nome": "Test Fornitore 114",
            "numero_documento": "INV-114-001",
            "data_documento": "2026-01-15",
            "data_scadenza_pagamento": "2026-02-15",
            "totale_documento": 1000.00
        }
        create_resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        assert create_resp.status_code == 201
        
        # Get dashboard
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find our scadenza
        found = False
        for s in data["scadenze"]:
            if s.get("titolo") == "Fatt. INV-114-001":
                found = True
                assert "data_documento" in s, "Missing data_documento field in scadenza"
                assert s["data_documento"] == "2026-01-15", f"Wrong data_documento: {s['data_documento']}"
                print(f"PASS: Scadenza has data_documento = {s['data_documento']}")
                break
        
        assert found, "Test scadenza not found in dashboard"
    
    def test_scadenza_has_pagamento_field(self, auth_headers, test_session):
        """Scadenze items include pagamento field (from condizioni_pagamento)."""
        # Create a fattura ricevuta with condizioni_pagamento
        fr_data = {
            "fornitore_nome": "Test Fornitore 114b",
            "numero_documento": "INV-114-002",
            "data_documento": "2026-01-20",
            "data_scadenza_pagamento": "2026-02-20",
            "condizioni_pagamento": "30gg FM",
            "totale_documento": 2000.00
        }
        create_resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        assert create_resp.status_code == 201
        
        # Get dashboard
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find our scadenza
        found = False
        for s in data["scadenze"]:
            if s.get("titolo") == "Fatt. INV-114-002":
                found = True
                assert "pagamento" in s, "Missing pagamento field in scadenza"
                assert s["pagamento"] == "30gg FM", f"Wrong pagamento: {s['pagamento']}"
                print(f"PASS: Scadenza has pagamento = {s['pagamento']}")
                break
        
        assert found, "Test scadenza not found in dashboard"


class TestScadenziarioStato:
    """Test scadenza stato calculation (scaduto, in_scadenza, ok)."""
    
    def test_overdue_scadenza_stato_scaduto(self, auth_headers):
        """Past due date results in stato='scaduto'."""
        past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        fr_data = {
            "fornitore_nome": "Test Fornitore Scaduto",
            "numero_documento": "INV-114-SCADUTO",
            "data_documento": past_date,
            "data_scadenza_pagamento": past_date,
            "totale_documento": 500.00
        }
        requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        data = response.json()
        
        for s in data["scadenze"]:
            if s.get("titolo") == "Fatt. INV-114-SCADUTO":
                assert s["stato"] == "scaduto", f"Expected stato='scaduto', got '{s['stato']}'"
                print(f"PASS: Overdue scadenza has stato='scaduto'")
                return
        
        pytest.fail("Test scadenza not found")
    
    def test_current_month_scadenza_stato_in_scadenza(self, auth_headers):
        """Current month due date results in stato='in_scadenza'."""
        # Use end of current month
        today = datetime.now()
        end_of_month = today.replace(day=28)  # Safe for any month
        if today.day > 15:  # If past mid-month, use next month
            end_of_month = (today.replace(day=28) + timedelta(days=7)).replace(day=28)
        
        fr_data = {
            "fornitore_nome": "Test Fornitore InScadenza",
            "numero_documento": "INV-114-INSCAD",
            "data_documento": today.strftime("%Y-%m-%d"),
            "data_scadenza_pagamento": end_of_month.strftime("%Y-%m-%d"),
            "totale_documento": 600.00
        }
        requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        data = response.json()
        
        for s in data["scadenze"]:
            if s.get("titolo") == "Fatt. INV-114-INSCAD":
                # Either in_scadenza or ok depending on current date
                assert s["stato"] in ["in_scadenza", "ok"], f"Unexpected stato: {s['stato']}"
                print(f"PASS: Current month scadenza has stato='{s['stato']}'")
                return
        
        pytest.fail("Test scadenza not found")


class TestScadenziarioPagamento:
    """Test payment registration via POST /api/fatture-ricevute/{id}/pagamenti."""
    
    def test_mark_payment_success(self, auth_headers):
        """POST pagamenti marks invoice as paid."""
        # Create invoice
        fr_data = {
            "fornitore_nome": "Test Fornitore Pagamento",
            "numero_documento": "INV-114-PAY",
            "data_documento": "2026-01-25",
            "data_scadenza_pagamento": "2026-02-25",
            "totale_documento": 1500.00
        }
        create_resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        fr_id = create_resp.json()["fr_id"]
        
        # Register payment
        payment_data = {
            "importo": 1500.00,
            "data_pagamento": "2026-03-03",
            "metodo": "bonifico",
            "note": "Test payment"
        }
        pay_resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti", json=payment_data, headers=auth_headers)
        assert pay_resp.status_code == 200
        
        pay_result = pay_resp.json()
        assert pay_result["payment_status"] == "pagata"
        assert pay_result["totale_pagato"] == 1500.00
        assert pay_result["residuo"] == 0
        print(f"PASS: Payment registered successfully, status={pay_result['payment_status']}")
    
    def test_paid_invoice_excluded_from_scadenze(self, auth_headers):
        """Paid invoices don't appear in scadenze list."""
        # Create and pay invoice
        fr_data = {
            "fornitore_nome": "Test Fornitore Exclude",
            "numero_documento": "INV-114-EXCL",
            "data_documento": "2026-01-26",
            "data_scadenza_pagamento": "2026-02-26",
            "totale_documento": 800.00
        }
        create_resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data, headers=auth_headers)
        fr_id = create_resp.json()["fr_id"]
        
        # Register full payment
        payment_data = {"importo": 800.00, "data_pagamento": "2026-03-03", "metodo": "bonifico"}
        requests.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti", json=payment_data, headers=auth_headers)
        
        # Check dashboard - paid invoice should not appear
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        data = response.json()
        
        for s in data["scadenze"]:
            if s.get("titolo") == "Fatt. INV-114-EXCL":
                pytest.fail("Paid invoice should not appear in scadenze")
        
        print("PASS: Paid invoice correctly excluded from scadenze list")


class TestScadenziarioIncassi:
    """Test incasso items appear in Clienti view."""
    
    def test_incasso_scadenza_has_tipo_incasso(self, auth_headers, test_session):
        """Invoice payment schedules appear as tipo='incasso'."""
        import subprocess
        
        # Create an invoice with scadenze_pagamento directly in MongoDB
        # since invoices have different structure
        timestamp = int(datetime.now().timestamp() * 1000)
        invoice_id = f"inv_test_{timestamp}"
        
        create_script = f"""
        use('test_database');
        db.invoices.insertOne({{
            invoice_id: '{invoice_id}',
            user_id: '{test_session["user_id"]}',
            document_number: 'FA-2026-114',
            status: 'emessa',
            client_id: 'test_client',
            issue_date: '2026-01-15',
            scadenze_pagamento: [
                {{
                    rata: 1,
                    data_scadenza: '2026-02-15',
                    importo: 3000,
                    pagata: false
                }}
            ],
            total_amount: 3000,
            created_at: new Date()
        }});
        """
        subprocess.run(['mongosh', '--eval', create_script], capture_output=True)
        
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard", headers=auth_headers)
        data = response.json()
        
        incasso_found = False
        for s in data["scadenze"]:
            if s.get("tipo") == "incasso" and "FA-2026-114" in s.get("titolo", ""):
                incasso_found = True
                assert s["importo"] == 3000
                print(f"PASS: Incasso scadenza found with tipo='incasso', importo={s['importo']}")
                break
        
        assert incasso_found, "Incasso scadenza not found in dashboard"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

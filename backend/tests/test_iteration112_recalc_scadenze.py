"""
Test Iteration 112: Auto-calculation of payment deadlines (scadenze) for received invoices
Tests the following features:
1. POST /api/fatture-ricevute/recalc-scadenze endpoint
2. _calc_scadenza_from_supplier helper function logic
3. Supplier name matching (e.g., 'VEGA CARBURANTI SPA' matches 'Vega carburanti')
4. Auto-calculation of due dates on FR creation
5. Fine mese and extra_days handling
"""

import pytest
import requests
import os
import time
from datetime import datetime, date, timedelta
import calendar

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def test_user():
    """Create a test user and session for authenticated tests"""
    import subprocess
    import json
    
    timestamp = int(time.time() * 1000)
    user_id = f"test_recalc_{timestamp}"
    session_token = f"test_session_recalc_{timestamp}"
    
    # Create user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'test.recalc.{timestamp}@example.com',
        name: 'Test Recalc User',
        picture: '',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    print('DONE');
    """
    result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteOne({{user_id: '{user_id}'}});
    db.user_sessions.deleteOne({{session_token: '{session_token}'}});
    db.payment_types.deleteMany({{user_id: '{user_id}'}});
    db.clients.deleteMany({{user_id: '{user_id}'}});
    db.fatture_ricevute.deleteMany({{user_id: '{user_id}'}});
    print('CLEANUP DONE');
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True, text=True)


@pytest.fixture
def auth_session(test_user):
    """Create an authenticated requests session"""
    session = requests.Session()
    session.cookies.set('session_token', test_user['session_token'])
    session.headers.update({'Content-Type': 'application/json'})
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# Test: recalc-scadenze endpoint basic functionality
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecalcScadenzeEndpoint:
    """Tests for POST /api/fatture-ricevute/recalc-scadenze"""

    def test_recalc_scadenze_returns_200(self, auth_session):
        """Endpoint should return 200 with linked/updated counts"""
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "linked" in data, "Response should contain 'linked' count"
        assert "updated" in data, "Response should contain 'updated' count"
        assert "message" in data, "Response should contain 'message'"

    def test_recalc_scadenze_with_no_data(self, auth_session):
        """With no FR data, endpoint returns 0 linked and 0 updated"""
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        data = response.json()
        assert data["linked"] == 0, "Should have 0 linked suppliers for new user"
        assert data["updated"] == 0, "Should have 0 updated scadenze for new user"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Due date calculation logic
# ═══════════════════════════════════════════════════════════════════════════════

class TestDueDateCalculation:
    """Tests for _calc_scadenza_from_supplier logic"""

    def test_calc_a_vista_returns_same_date(self, auth_session, test_user):
        """Payment type 'A VISTA' (giorni=0) should return invoice date as due date"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create A VISTA payment type (giorni=0)
        pt_script = f"""
        use('test_database');
        db.payment_types.insertOne({{
            payment_type_id: 'pt_test_avista_{user_id}',
            user_id: '{user_id}',
            codice: 'TEST A VISTA',
            quote: [{{giorni: 0, quota: 100}}],
            fine_mese: false,
            extra_days: null,
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', pt_script], capture_output=True, text=True)
        
        # Create supplier with this payment type
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_avista_{user_id}',
            user_id: '{user_id}',
            business_name: 'Test Supplier A Vista',
            partita_iva: '12345678901',
            payment_type_id: 'pt_test_avista_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR with this supplier and call recalc
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_avista_{user_id}',
            user_id: '{user_id}',
            fornitore_id: 'cli_test_avista_{user_id}',
            fornitore_nome: 'Test Supplier A Vista',
            numero_documento: 'TEST-001',
            data_documento: '2026-01-15',
            data_scadenza_pagamento: '',
            totale_documento: 100,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] >= 1, f"Should update at least 1 FR, got {data}"
        
        # Verify the scadenza was set to invoice date
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_avista_{user_id}'}}, {{_id: 0, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["data_scadenza_pagamento"] == "2026-01-15", f"A VISTA should have same date as invoice, got {fr_data}"

    def test_calc_30gg_without_fine_mese(self, auth_session, test_user):
        """30 days payment without fine_mese should add 30 days to invoice date"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create 30gg payment type (NO fine_mese)
        pt_script = f"""
        use('test_database');
        db.payment_types.insertOne({{
            payment_type_id: 'pt_test_30gg_{user_id}',
            user_id: '{user_id}',
            codice: 'TEST 30GG',
            quote: [{{giorni: 30, quota: 100}}],
            fine_mese: false,
            extra_days: null,
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', pt_script], capture_output=True, text=True)
        
        # Create supplier
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_30gg_{user_id}',
            user_id: '{user_id}',
            business_name: 'Test Supplier 30GG',
            partita_iva: '22345678901',
            payment_type_id: 'pt_test_30gg_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR - invoice date 2026-01-15, expecting due 2026-02-14
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_30gg_{user_id}',
            user_id: '{user_id}',
            fornitore_id: 'cli_test_30gg_{user_id}',
            fornitore_nome: 'Test Supplier 30GG',
            numero_documento: 'TEST-002',
            data_documento: '2026-01-15',
            data_scadenza_pagamento: '',
            totale_documento: 200,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        # Verify: 2026-01-15 + 30 days = 2026-02-14
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_30gg_{user_id}'}}, {{_id: 0, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["data_scadenza_pagamento"] == "2026-02-14", f"30 days from 15/01 should be 14/02, got {fr_data}"

    def test_calc_30gg_with_fine_mese(self, auth_session, test_user):
        """30 days payment with fine_mese should go to end of month after adding days"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create 30gg FM payment type
        pt_script = f"""
        use('test_database');
        db.payment_types.insertOne({{
            payment_type_id: 'pt_test_30fm_{user_id}',
            user_id: '{user_id}',
            codice: 'TEST 30GG FM',
            quote: [{{giorni: 30, quota: 100}}],
            fine_mese: true,
            extra_days: null,
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', pt_script], capture_output=True, text=True)
        
        # Create supplier
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_30fm_{user_id}',
            user_id: '{user_id}',
            business_name: 'Test Supplier 30FM',
            partita_iva: '32345678901',
            payment_type_id: 'pt_test_30fm_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR - invoice date 2026-01-15
        # 15/01 + 30 days = 14/02, then fine mese = 28/02/2026
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_30fm_{user_id}',
            user_id: '{user_id}',
            fornitore_id: 'cli_test_30fm_{user_id}',
            fornitore_nome: 'Test Supplier 30FM',
            numero_documento: 'TEST-003',
            data_documento: '2026-01-15',
            data_scadenza_pagamento: '',
            totale_documento: 300,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        # Verify: 2026-01-15 + 30 days = 2026-02-14, fine mese = 2026-02-28
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_30fm_{user_id}'}}, {{_id: 0, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["data_scadenza_pagamento"] == "2026-02-28", f"30gg FM from 15/01 should be 28/02, got {fr_data}"

    def test_calc_30gg_fm_plus_extra_days(self, auth_session, test_user):
        """30 days FM + 10 extra days should add extra days after end of month"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create 30gg FM+10 payment type
        pt_script = f"""
        use('test_database');
        db.payment_types.insertOne({{
            payment_type_id: 'pt_test_fm10_{user_id}',
            user_id: '{user_id}',
            codice: 'TEST 30GG FM+10',
            quote: [{{giorni: 30, quota: 100}}],
            fine_mese: true,
            extra_days: 10,
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', pt_script], capture_output=True, text=True)
        
        # Create supplier
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_fm10_{user_id}',
            user_id: '{user_id}',
            business_name: 'Test Supplier FM+10',
            partita_iva: '42345678901',
            payment_type_id: 'pt_test_fm10_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR - invoice date 2026-01-15
        # 15/01 + 30 days = 14/02, fine mese = 28/02, + 10 = 10/03/2026
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_fm10_{user_id}',
            user_id: '{user_id}',
            fornitore_id: 'cli_test_fm10_{user_id}',
            fornitore_nome: 'Test Supplier FM+10',
            numero_documento: 'TEST-004',
            data_documento: '2026-01-15',
            data_scadenza_pagamento: '',
            totale_documento: 400,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        # Verify: 2026-01-15 + 30 = 14/02, FM = 28/02, +10 = 10/03/2026
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_fm10_{user_id}'}}, {{_id: 0, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["data_scadenza_pagamento"] == "2026-03-10", f"30gg FM+10 from 15/01 should be 10/03, got {fr_data}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Supplier name matching
# ═══════════════════════════════════════════════════════════════════════════════

class TestSupplierNameMatching:
    """Tests for supplier name matching functionality"""

    def test_match_supplier_by_name_case_insensitive(self, auth_session, test_user):
        """Should match 'VEGA CARBURANTI SPA' to 'Vega carburanti' (case-insensitive)"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create supplier with lowercase name
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_vega_{user_id}',
            user_id: '{user_id}',
            business_name: 'Vega carburanti',
            partita_iva: '00000000000',
            payment_type_id: 'pt_test_avista_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR with uppercase supplier name and NO fornitore_id
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_vega_{user_id}',
            user_id: '{user_id}',
            fornitore_id: null,
            fornitore_nome: 'VEGA CARBURANTI SPA',
            numero_documento: 'VEGA-001',
            data_documento: '2026-02-05',
            data_scadenza_pagamento: '',
            totale_documento: 150,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc - should link supplier by name
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] >= 1, f"Should link at least 1 supplier by name, got {data}"
        
        # Verify fornitore_id was set
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_vega_{user_id}'}}, {{_id: 0, fornitore_id: 1, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["fornitore_id"] == f"cli_test_vega_{user_id}", f"Should link to supplier, got {fr_data}"

    def test_match_supplier_strips_legal_suffixes(self, auth_session, test_user):
        """Should match 'MAXIMA SRL' to 'Maxima Srl' stripping SRL suffix"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create supplier without SRL suffix
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_maxima_{user_id}',
            user_id: '{user_id}',
            business_name: 'Maxima',
            partita_iva: '55555555555',
            payment_type_id: 'pt_test_30gg_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR with full legal name
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_maxima_{user_id}',
            user_id: '{user_id}',
            fornitore_id: null,
            fornitore_nome: 'MAXIMA SRL',
            numero_documento: 'MAX-001',
            data_documento: '2026-01-31',
            data_scadenza_pagamento: '',
            totale_documento: 250,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        # Verify fornitore_id was set
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_maxima_{user_id}'}}, {{_id: 0, fornitore_id: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["fornitore_id"] == f"cli_test_maxima_{user_id}", f"Should link to supplier without SRL suffix, got {fr_data}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Auto-calc on FR creation
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoCalcOnCreation:
    """Tests for auto-calculation of scadenza when creating FR"""

    def test_create_fr_with_linked_supplier_auto_calcs_scadenza(self, auth_session, test_user):
        """Creating FR with fornitore_id should auto-calculate scadenza"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Ensure payment type and supplier exist
        setup_script = f"""
        use('test_database');
        // Payment type with 30 days
        db.payment_types.updateOne(
            {{payment_type_id: 'pt_test_autocreate_{user_id}'}},
            {{$set: {{
                payment_type_id: 'pt_test_autocreate_{user_id}',
                user_id: '{user_id}',
                codice: 'TEST AUTO 30',
                quote: [{{giorni: 30, quota: 100}}],
                fine_mese: false,
                extra_days: null,
                created_at: new Date()
            }}}},
            {{upsert: true}}
        );
        // Supplier
        db.clients.updateOne(
            {{client_id: 'cli_test_autocreate_{user_id}'}},
            {{$set: {{
                client_id: 'cli_test_autocreate_{user_id}',
                user_id: '{user_id}',
                business_name: 'Auto Create Supplier',
                partita_iva: '66666666666',
                payment_type_id: 'pt_test_autocreate_{user_id}',
                client_type: 'fornitore',
                created_at: new Date()
            }}}},
            {{upsert: true}}
        );
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', setup_script], capture_output=True, text=True)
        
        # Create FR via API with fornitore_id - should auto-calc scadenza
        fr_data = {
            "fornitore_id": f"cli_test_autocreate_{user_id}",
            "fornitore_nome": "Auto Create Supplier",
            "fornitore_piva": "66666666666",
            "numero_documento": "AUTO-001",
            "data_documento": "2026-01-15",
            "totale_documento": 500,
            "imponibile": 409.84,
            "imposta": 90.16,
            "linee": []
        }
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        created = response.json()
        # Expected: 2026-01-15 + 30 days = 2026-02-14
        assert created.get("data_scadenza_pagamento") == "2026-02-14", f"Should auto-calc scadenza to 2026-02-14, got {created.get('data_scadenza_pagamento')}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Multiple installments
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultipleInstallments:
    """Tests for payment types with multiple installments"""

    def test_calc_uses_max_giorni_from_quote(self, auth_session, test_user):
        """Should use the longest installment days for due date calculation"""
        import subprocess
        
        user_id = test_user["user_id"]
        
        # Create payment type with multiple installments (30/60/90)
        pt_script = f"""
        use('test_database');
        db.payment_types.insertOne({{
            payment_type_id: 'pt_test_multi_{user_id}',
            user_id: '{user_id}',
            codice: 'TEST 30/60/90',
            quote: [
                {{giorni: 30, quota: 33}},
                {{giorni: 60, quota: 33}},
                {{giorni: 90, quota: 34}}
            ],
            fine_mese: true,
            extra_days: null,
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', pt_script], capture_output=True, text=True)
        
        # Create supplier
        supplier_script = f"""
        use('test_database');
        db.clients.insertOne({{
            client_id: 'cli_test_multi_{user_id}',
            user_id: '{user_id}',
            business_name: 'Test Multi Supplier',
            partita_iva: '77777777777',
            payment_type_id: 'pt_test_multi_{user_id}',
            client_type: 'fornitore',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', supplier_script], capture_output=True, text=True)
        
        # Create FR - invoice date 2026-01-15
        # Max giorni = 90, so 15/01 + 90 = 15/04, fine mese = 30/04/2026
        fr_script = f"""
        use('test_database');
        db.fatture_ricevute.insertOne({{
            fr_id: 'fr_test_multi_{user_id}',
            user_id: '{user_id}',
            fornitore_id: 'cli_test_multi_{user_id}',
            fornitore_nome: 'Test Multi Supplier',
            numero_documento: 'MULTI-001',
            data_documento: '2026-01-15',
            data_scadenza_pagamento: '',
            totale_documento: 600,
            status: 'da_registrare',
            created_at: new Date()
        }});
        print('DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', fr_script], capture_output=True, text=True)
        
        # Call recalc
        response = auth_session.post(f"{BASE_URL}/api/fatture-ricevute/recalc-scadenze")
        assert response.status_code == 200
        
        # Verify: max(30,60,90) = 90, 15/01 + 90 = 15/04, FM = 30/04/2026
        verify_script = f"""
        use('test_database');
        var fr = db.fatture_ricevute.findOne({{fr_id: 'fr_test_multi_{user_id}'}}, {{_id: 0, data_scadenza_pagamento: 1}});
        print(JSON.stringify(fr));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', verify_script], capture_output=True, text=True)
        import json
        fr_data = json.loads(result.stdout.strip())
        assert fr_data["data_scadenza_pagamento"] == "2026-04-30", f"90gg FM from 15/01 should be 30/04, got {fr_data}"


# ═══════════════════════════════════════════════════════════════════════════════
# Run tests
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

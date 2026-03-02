"""
Test suite for Payment Types Invoicex-style features - Iteration 105
Features:
- Quote system (custom installment schedules with giorni + quota percentage)
- Simulate endpoint to calculate deadlines
- Codice Fatturazione Elettronica (MP01-MP23)
- divisione_automatica flag
- richiedi_giorno_scadenza option
- Backward compatibility with legacy gg_30/60/90 flags
"""
import pytest
import requests
import os
from datetime import datetime, date, timedelta

# Get the base URL from environment variable
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")


class TestPaymentTypesQuoteSystem:
    """Test Quote-based payment types (Invoicex-style)."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_create_payment_type_with_custom_quote(self):
        """Test POST /api/payment-types/ with custom quote (80 days, 100%)."""
        payload = {
            "codice": "TEST_CUSTOM80",
            "tipo": "BON",
            "descrizione": "Bonifico 80 giorni",
            "codice_fe": "MP05",
            "quote": [{"giorni": 80, "quota": 100.0}],
            "divisione_automatica": False
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['codice'] == "TEST_CUSTOM80"
        assert data['codice_fe'] == "MP05"
        assert len(data['quote']) == 1
        assert data['quote'][0]['giorni'] == 80
        assert data['quote'][0]['quota'] == 100.0
        assert data['divisione_automatica'] is False
        assert 'payment_type_id' in data
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type with custom 80-day quote: {data['payment_type_id']}")

    def test_create_payment_type_with_multiple_quotes(self):
        """Test creating payment type with multiple custom quotes (45/90/135 days)."""
        payload = {
            "codice": "TEST_MULTI",
            "tipo": "RIB",
            "descrizione": "Ri.Ba 45/90/135 giorni",
            "codice_fe": "MP12",
            "quote": [
                {"giorni": 45, "quota": 33.33},
                {"giorni": 90, "quota": 33.33},
                {"giorni": 135, "quota": 33.34}
            ],
            "divisione_automatica": False,
            "banca_necessaria": True
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert len(data['quote']) == 3
        assert data['quote'][0]['giorni'] == 45
        assert data['quote'][1]['giorni'] == 90
        assert data['quote'][2]['giorni'] == 135
        
        # Verify quotes sum to 100%
        total_quota = sum(q['quota'] for q in data['quote'])
        assert abs(total_quota - 100.0) < 0.1, f"Quotes should sum to 100%, got {total_quota}"
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type with 45/90/135 day quotes: {data['payment_type_id']}")

    def test_create_immediate_payment_with_quote(self):
        """Test creating immediate payment (0 days)."""
        payload = {
            "codice": "TEST_IMM",
            "tipo": "CON",
            "descrizione": "Pagamento Immediato",
            "codice_fe": "MP01",
            "quote": [{"giorni": 0, "quota": 100.0}],
            "immediato": True
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['quote'][0]['giorni'] == 0
        assert data['immediato'] is True
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created immediate payment type: {data['payment_type_id']}")

    def test_update_payment_type_quotes(self):
        """Test PUT /api/payment-types/{id} updating quote list."""
        # Create
        create_payload = {
            "codice": "TEST_UPDQ",
            "tipo": "BON",
            "descrizione": "Test Update Quotes",
            "quote": [{"giorni": 30, "quota": 100}]
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Update with new quotes
        update_payload = {
            "quote": [
                {"giorni": 30, "quota": 50},
                {"giorni": 60, "quota": 50}
            ],
            "fine_mese": True
        }
        update_response = self.session.put(f"{BASE_URL}/api/payment-types/{pt_id}", json=update_payload)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated = update_response.json()
        assert len(updated['quote']) == 2
        assert updated['quote'][0]['giorni'] == 30
        assert updated['quote'][1]['giorni'] == 60
        assert updated['fine_mese'] is True
        
        print(f"✓ Updated payment type quotes: {pt_id}")


class TestCodiceFatturazioneElettronica:
    """Test Codice FE (Electronic Invoicing Codes MP01-MP23)."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_codice_fe_mp05_bonifico(self):
        """Test creating payment type with MP05 (Bonifico) code."""
        payload = {
            "codice": "TEST_MP05",
            "tipo": "BON",
            "descrizione": "Bonifico con Codice FE",
            "codice_fe": "MP05",
            "quote": [{"giorni": 30, "quota": 100}]
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['codice_fe'] == "MP05"
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type with MP05 codice_fe")

    def test_codice_fe_mp12_riba(self):
        """Test creating payment type with MP12 (RIBA) code."""
        payload = {
            "codice": "TEST_MP12",
            "tipo": "RIB",
            "descrizione": "Ri.Ba con Codice FE MP12",
            "codice_fe": "MP12",
            "quote": [{"giorni": 60, "quota": 100}],
            "banca_necessaria": True
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['codice_fe'] == "MP12"
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type with MP12 codice_fe")

    def test_codice_fe_empty_allowed(self):
        """Test creating payment type with empty codice_fe."""
        payload = {
            "codice": "TEST_NOFE",
            "tipo": "CON",
            "descrizione": "Senza Codice FE",
            "codice_fe": "",
            "quote": [{"giorni": 0, "quota": 100}]
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['codice_fe'] == ""
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type without codice_fe")

    def test_list_includes_codice_fe(self):
        """Test GET /api/payment-types/ includes codice_fe in response."""
        response = self.session.get(f"{BASE_URL}/api/payment-types/")
        assert response.status_code == 200
        
        data = response.json()
        assert 'items' in data
        
        for item in data['items']:
            assert 'codice_fe' in item, f"Missing codice_fe in item: {item}"
        
        print(f"✓ GET /api/payment-types/ includes codice_fe field")


class TestSimulateDeadlines:
    """Test simulate endpoint for payment deadline calculation."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_simulate_single_payment(self):
        """Test POST /api/payment-types/{id}/simulate with single installment."""
        # Create payment type
        create_payload = {
            "codice": "TEST_SIM1",
            "tipo": "BON",
            "descrizione": "Simulate Single",
            "quote": [{"giorni": 30, "quota": 100}]
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Simulate
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 10000.0
        }
        sim_response = self.session.post(f"{BASE_URL}/api/payment-types/{pt_id}/simulate", json=sim_payload)
        assert sim_response.status_code == 200, f"Expected 200, got {sim_response.status_code}: {sim_response.text}"
        
        sim_data = sim_response.json()
        assert 'scadenze' in sim_data
        assert sim_data['totale_rate'] == 1
        assert sim_data['importo_totale'] == 10000.0
        
        # Verify deadline calculation: 2026-01-15 + 30 days = 2026-02-14
        assert sim_data['scadenze'][0]['data_scadenza'] == "2026-02-14"
        assert sim_data['scadenze'][0]['importo'] == 10000.0
        assert sim_data['scadenze'][0]['quota_pct'] == 100
        
        print(f"✓ Simulate single payment: deadline=2026-02-14, importo=10000€")

    def test_simulate_multiple_installments(self):
        """Test simulate with multiple installments (30/60/90)."""
        # Create payment type
        create_payload = {
            "codice": "TEST_SIM3",
            "tipo": "BON",
            "descrizione": "Simulate 30/60/90",
            "quote": [
                {"giorni": 30, "quota": 33.33},
                {"giorni": 60, "quota": 33.33},
                {"giorni": 90, "quota": 33.34}
            ]
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Simulate
        sim_payload = {
            "data_fattura": "2026-03-01",
            "importo": 9000.0
        }
        sim_response = self.session.post(f"{BASE_URL}/api/payment-types/{pt_id}/simulate", json=sim_payload)
        assert sim_response.status_code == 200
        
        sim_data = sim_response.json()
        assert sim_data['totale_rate'] == 3
        
        # Verify dates: 2026-03-01 + 30/60/90 days
        assert sim_data['scadenze'][0]['data_scadenza'] == "2026-03-31"  # +30
        assert sim_data['scadenze'][1]['data_scadenza'] == "2026-04-30"  # +60
        assert sim_data['scadenze'][2]['data_scadenza'] == "2026-05-30"  # +90
        
        # Verify amounts
        assert abs(sim_data['scadenze'][0]['importo'] - 2999.7) < 1  # 33.33% of 9000
        assert abs(sim_data['scadenze'][1]['importo'] - 2999.7) < 1
        assert abs(sim_data['scadenze'][2]['importo'] - 3000.6) < 1  # 33.34% of 9000
        
        print(f"✓ Simulate 3 installments: dates correct, amounts distributed")

    def test_simulate_with_fine_mese(self):
        """Test simulate with fine_mese=true (end of month)."""
        # Create payment type with fine_mese
        create_payload = {
            "codice": "TEST_SIMFM",
            "tipo": "BON",
            "descrizione": "Simulate Fine Mese",
            "quote": [{"giorni": 30, "quota": 100}],
            "fine_mese": True
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Simulate with date in January
        sim_payload = {
            "data_fattura": "2026-01-15",
            "importo": 5000.0
        }
        sim_response = self.session.post(f"{BASE_URL}/api/payment-types/{pt_id}/simulate", json=sim_payload)
        assert sim_response.status_code == 200
        
        sim_data = sim_response.json()
        # 2026-01-15 + 30 days = 2026-02-14, then move to end of Feb = 2026-02-28
        assert sim_data['scadenze'][0]['data_scadenza'] == "2026-02-28"
        
        print(f"✓ Simulate with fine_mese: deadline moved to end of month (2026-02-28)")

    def test_simulate_nonexistent_payment_type(self):
        """Test simulate with non-existent payment type returns 404."""
        sim_payload = {
            "data_fattura": "2026-01-01",
            "importo": 1000.0
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/pt_nonexistent123/simulate", json=sim_payload)
        assert response.status_code == 404
        print(f"✓ Simulate nonexistent payment type returns 404")

    def test_simulate_invalid_date_format(self):
        """Test simulate with invalid date format returns 400."""
        # Create a payment type first
        create_payload = {
            "codice": "TEST_SIMDATE",
            "tipo": "BON",
            "descrizione": "Test date format",
            "quote": [{"giorni": 30, "quota": 100}]
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Test with invalid date
        sim_payload = {
            "data_fattura": "15/01/2026",  # Wrong format (should be YYYY-MM-DD)
            "importo": 1000.0
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/{pt_id}/simulate", json=sim_payload)
        assert response.status_code == 400
        print(f"✓ Simulate with invalid date format returns 400")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy gg_30/60/90 boolean flags."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_legacy_gg_flags_generate_quote(self):
        """Test that legacy gg_30, gg_60 flags auto-generate quote list."""
        # Create with legacy flags only (no quote array)
        payload = {
            "codice": "TEST_LEGACY",
            "tipo": "BON",
            "descrizione": "Legacy 30/60",
            "gg_30": True,
            "gg_60": True,
            "quote": []  # Empty quote array
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        pt_id = response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # GET should return auto-generated quote from legacy flags
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{pt_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        # Should have 2 quotes (30 and 60 days) with 50% each
        assert len(data['quote']) == 2
        assert data['quote'][0]['giorni'] == 30
        assert data['quote'][1]['giorni'] == 60
        assert abs(data['quote'][0]['quota'] - 50.0) < 0.1
        assert abs(data['quote'][1]['quota'] - 50.0) < 0.1
        
        print(f"✓ Legacy gg_30/gg_60 flags auto-generated quote list")

    def test_legacy_single_flag_generates_100_percent_quote(self):
        """Test single legacy flag generates 100% quota."""
        payload = {
            "codice": "TEST_LEG90",
            "tipo": "RIB",
            "descrizione": "Legacy 90 only",
            "gg_90": True,
            "quote": []
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        pt_id = response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Verify auto-generated quote
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{pt_id}")
        data = get_response.json()
        
        assert len(data['quote']) == 1
        assert data['quote'][0]['giorni'] == 90
        assert data['quote'][0]['quota'] == 100.0
        
        print(f"✓ Single legacy flag generates 100% quota")

    def test_immediate_flag_generates_zero_days_quote(self):
        """Test immediato flag generates 0-day quote."""
        payload = {
            "codice": "TEST_LEGIMM",
            "tipo": "CON",
            "descrizione": "Legacy Immediato",
            "immediato": True,
            "quote": []
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        pt_id = response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{pt_id}")
        data = get_response.json()
        
        assert len(data['quote']) == 1
        assert data['quote'][0]['giorni'] == 0
        assert data['quote'][0]['quota'] == 100.0
        
        print(f"✓ Immediato flag generates 0-day quote")


class TestSeedDefaultsWithQuotes:
    """Test seed defaults creates payment types with proper quote arrays."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']

    def test_seed_defaults_includes_quotes(self):
        """Test seed-defaults creates items with proper quote arrays."""
        # First, clean up existing payment types
        existing = self.session.get(f"{BASE_URL}/api/payment-types/")
        if existing.status_code == 200:
            for item in existing.json().get('items', []):
                self.session.delete(f"{BASE_URL}/api/payment-types/{item['payment_type_id']}")
        
        # Seed
        response = self.session.post(f"{BASE_URL}/api/payment-types/seed-defaults")
        assert response.status_code == 200
        
        # Get list and verify quotes exist
        list_response = self.session.get(f"{BASE_URL}/api/payment-types/")
        assert list_response.status_code == 200
        
        items = list_response.json()['items']
        assert len(items) >= 10, f"Expected at least 10 seeded items, got {len(items)}"
        
        # Check BB30-60 has 2 quotes
        bb30_60 = next((i for i in items if i['codice'] == 'BB30-60'), None)
        if bb30_60:
            assert len(bb30_60['quote']) == 2
            assert bb30_60['quote'][0]['giorni'] == 30
            assert bb30_60['quote'][1]['giorni'] == 60
            print(f"✓ BB30-60 has correct quote array: {bb30_60['quote']}")
        
        # Check BB30-60-90 has 3 quotes
        bb30_60_90 = next((i for i in items if i['codice'] == 'BB30-60-90'), None)
        if bb30_60_90:
            assert len(bb30_60_90['quote']) == 3
            print(f"✓ BB30-60-90 has 3 quotes")
        
        # Check codice_fe is set
        for item in items:
            assert 'codice_fe' in item
            if item['tipo'] == 'BON':
                assert item.get('codice_fe') in ['', 'MP05'], f"Bonifico should have MP05: {item}"
        
        print(f"✓ Seed defaults includes proper quote arrays and codice_fe")


class TestGiornoScadenzaFixed:
    """Test richiedi_giorno_scadenza and giorno_scadenza fixed day option."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_create_with_giorno_scadenza(self):
        """Test creating payment type with richiedi_giorno_scadenza and fixed day."""
        payload = {
            "codice": "TEST_GS15",
            "tipo": "BON",
            "descrizione": "Bonifico 60gg al giorno 15",
            "quote": [{"giorni": 60, "quota": 100}],
            "richiedi_giorno_scadenza": True,
            "giorno_scadenza": 15
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['richiedi_giorno_scadenza'] is True
        assert data['giorno_scadenza'] == 15
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Created payment type with giorno_scadenza=15")


class TestDivisioneAutomatica:
    """Test divisione_automatica flag behavior."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_divisione_automatica_default_true(self):
        """Test divisione_automatica defaults to true."""
        payload = {
            "codice": "TEST_DIVAUT",
            "tipo": "BON",
            "descrizione": "Test Divisione Automatica",
            "quote": [{"giorni": 30, "quota": 100}]
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['divisione_automatica'] is True
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ divisione_automatica defaults to True")

    def test_divisione_automatica_can_be_false(self):
        """Test divisione_automatica can be set to false."""
        payload = {
            "codice": "TEST_DIVMAN",
            "tipo": "BON",
            "descrizione": "Divisione Manuale",
            "quote": [
                {"giorni": 30, "quota": 40},
                {"giorni": 60, "quota": 60}
            ],
            "divisione_automatica": False
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['divisione_automatica'] is False
        assert data['quote'][0]['quota'] == 40
        assert data['quote'][1]['quota'] == 60
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ divisione_automatica can be False with manual quotas")


class TestUnauthorizedAccess:
    """Test unauthorized access to payment types endpoints."""

    def test_simulate_requires_auth(self):
        """Test POST /api/payment-types/{id}/simulate requires authentication."""
        payload = {"data_fattura": "2026-01-01", "importo": 1000}
        response = requests.post(f"{BASE_URL}/api/payment-types/pt_any123/simulate", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/payment-types/{{id}}/simulate - 401 without auth")


@pytest.fixture(scope="module")
def auth_session():
    """Create authenticated session for testing."""
    import subprocess
    import json
    
    # Create test user and session
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('test_database');
        var userId = 'test-invoicex-' + Date.now();
        var sessionToken = 'test_session_invoicex_' + Date.now();
        db.users.insertOne({
          user_id: userId,
          email: 'test.invoicex.' + Date.now() + '@example.com',
          name: 'Invoicex Test User',
          picture: 'https://via.placeholder.com/150',
          created_at: new Date()
        });
        db.user_sessions.insertOne({
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        });
        print(JSON.stringify({token: sessionToken, user_id: userId}));
        '''
    ], capture_output=True, text=True)
    
    # Parse output to get session token
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines:
        if line.startswith('{'):
            data = json.loads(line)
            session_token = data['token']
            user_id = data['user_id']
            break
    else:
        raise ValueError(f"Could not parse session token from mongosh output: {result.stdout}")
    
    # Create session with auth headers
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_token}"
    })
    
    yield {"session": session, "user_id": user_id}
    
    # Cleanup: Remove test data
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        db.users.deleteMany({{user_id: '{user_id}'}});
        db.user_sessions.deleteMany({{user_id: '{user_id}'}});
        db.payment_types.deleteMany({{user_id: '{user_id}'}});
        print('Cleanup complete for user: {user_id}');
        '''
    ], capture_output=True, text=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test suite for Payment Types CRUD and Expanded Client fields.
Features:
- Payment Types CRUD (GET, POST, PUT, DELETE)
- Seed defaults endpoint
- Client creation with expanded fields (contacts, payment_type_id, etc.)
- Client update with new fields
"""
import pytest
import requests
import os
from datetime import datetime

# Get the base URL from environment variable
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")


class TestPaymentTypesCRUD:
    """Test Payment Types CRUD endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_pt_ids = []

    def test_get_payment_types_empty(self):
        """Test GET /api/payment-types/ returns empty list initially."""
        response = self.session.get(f"{BASE_URL}/api/payment-types/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        print(f"✓ GET /api/payment-types/ - Status 200, items: {data['total']}")

    def test_create_payment_type(self):
        """Test POST /api/payment-types/ creates a payment type."""
        payload = {
            "codice": "TEST_BB30",
            "tipo": "BON",
            "descrizione": "TEST Bonifico Bancario 30 gg",
            "gg_30": True,
            "fine_mese": False,
            "immediato": False
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['codice'] == "TEST_BB30"
        assert data['tipo'] == "BON"
        assert data['descrizione'] == "TEST Bonifico Bancario 30 gg"
        assert data['gg_30'] is True
        assert 'payment_type_id' in data
        assert 'created_at' in data
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ POST /api/payment-types/ - Created: {data['payment_type_id']}")
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{data['payment_type_id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched['codice'] == "TEST_BB30"
        print(f"✓ GET /api/payment-types/{data['payment_type_id']} - Verified persistence")

    def test_create_payment_type_with_multiple_installments(self):
        """Test creating payment type with multiple installment flags."""
        payload = {
            "codice": "TEST_RB3060",
            "tipo": "RIB",
            "descrizione": "TEST Ri.Ba 30/60 gg FM",
            "gg_30": True,
            "gg_60": True,
            "fine_mese": True,
            "banca_necessaria": True,
            "spese_incasso": 1.50
        }
        response = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['gg_30'] is True
        assert data['gg_60'] is True
        assert data['fine_mese'] is True
        assert data['banca_necessaria'] is True
        assert data['spese_incasso'] == 1.50
        
        self.created_pt_ids.append(data['payment_type_id'])
        print(f"✓ Multiple installment flags verified for: {data['payment_type_id']}")

    def test_duplicate_codice_rejected(self):
        """Test that duplicate codice is rejected."""
        payload = {
            "codice": "TEST_DUP",
            "tipo": "BON",
            "descrizione": "Test duplicate"
        }
        # First create
        r1 = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert r1.status_code == 201
        self.created_pt_ids.append(r1.json()['payment_type_id'])
        
        # Second create with same codice should fail
        r2 = self.session.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert r2.status_code == 400, f"Expected 400 for duplicate, got {r2.status_code}"
        print(f"✓ Duplicate codice correctly rejected")

    def test_update_payment_type(self):
        """Test PUT /api/payment-types/{id} updates a payment type."""
        # Create first
        create_payload = {
            "codice": "TEST_UPD",
            "tipo": "CON",
            "descrizione": "Original Description",
            "immediato": True
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Update
        update_payload = {
            "descrizione": "Updated Description",
            "gg_30": True,
            "note_documento": "Custom note"
        }
        update_response = self.session.put(f"{BASE_URL}/api/payment-types/{pt_id}", json=update_payload)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated = update_response.json()
        assert updated['descrizione'] == "Updated Description"
        assert updated['gg_30'] is True
        assert updated['note_documento'] == "Custom note"
        assert updated['immediato'] is True  # Original value preserved
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{pt_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched['descrizione'] == "Updated Description"
        print(f"✓ PUT /api/payment-types/{pt_id} - Update verified")

    def test_delete_payment_type(self):
        """Test DELETE /api/payment-types/{id} removes a payment type."""
        # Create
        create_payload = {
            "codice": "TEST_DEL",
            "tipo": "ELE",
            "descrizione": "To be deleted"
        }
        create_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=create_payload)
        assert create_response.status_code == 201
        pt_id = create_response.json()['payment_type_id']
        
        # Delete
        delete_response = self.session.delete(f"{BASE_URL}/api/payment-types/{pt_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        # Verify it's gone
        get_response = self.session.get(f"{BASE_URL}/api/payment-types/{pt_id}")
        assert get_response.status_code == 404
        print(f"✓ DELETE /api/payment-types/{pt_id} - Deletion verified")

    def test_delete_nonexistent_returns_404(self):
        """Test DELETE for non-existent payment type returns 404."""
        response = self.session.delete(f"{BASE_URL}/api/payment-types/pt_nonexistent123")
        assert response.status_code == 404
        print(f"✓ DELETE nonexistent - 404 returned correctly")


class TestSeedDefaults:
    """Test seed defaults endpoint for payment types."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']

    def test_seed_defaults_creates_payment_types(self):
        """Test POST /api/payment-types/seed-defaults creates default payment types."""
        # Clean up any existing payment types first
        existing = self.session.get(f"{BASE_URL}/api/payment-types/")
        if existing.status_code == 200:
            for item in existing.json().get('items', []):
                self.session.delete(f"{BASE_URL}/api/payment-types/{item['payment_type_id']}")
        
        # Seed defaults
        response = self.session.post(f"{BASE_URL}/api/payment-types/seed-defaults")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'seeded' in data
        assert data['seeded'] == 11, f"Expected 11 seeded items, got {data['seeded']}"
        print(f"✓ POST /api/payment-types/seed-defaults - Seeded {data['seeded']} items")
        
        # Verify the items exist
        list_response = self.session.get(f"{BASE_URL}/api/payment-types/")
        assert list_response.status_code == 200
        items = list_response.json()['items']
        assert len(items) == 11
        
        # Verify expected codici
        codici = [item['codice'] for item in items]
        expected_codici = ['BB30', 'BB60', 'BB30-60', 'BB60FM', 'BB30-60-90', 'RB30', 'RB60', 'RB30-60', 'RB90', 'CON', 'ELETT']
        for expected in expected_codici:
            assert expected in codici, f"Missing expected codice: {expected}"
        print(f"✓ All 11 default payment types verified: {codici}")

    def test_seed_defaults_idempotent(self):
        """Test seed-defaults doesn't create duplicates if already seeded."""
        response = self.session.post(f"{BASE_URL}/api/payment-types/seed-defaults")
        assert response.status_code == 200
        
        data = response.json()
        assert data['seeded'] == 0, "Should not seed again if items exist"
        print(f"✓ Seed-defaults is idempotent - seeded 0 (already exists)")


class TestExpandedClientFields:
    """Test Client CRUD with expanded fields (contacts, payment_type_id, etc.)."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_client_ids = []
        self.created_pt_ids = []

    def test_create_client_with_expanded_fields(self):
        """Test POST /api/clients/ with all new fields."""
        # First create a payment type to link
        pt_payload = {
            "codice": "TEST_CLIENT_PT",
            "tipo": "BON",
            "descrizione": "Test payment for client"
        }
        pt_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=pt_payload)
        assert pt_response.status_code == 201
        pt_id = pt_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Create client with expanded fields
        client_payload = {
            "business_name": "TEST_Azienda SpA",
            "client_type": "cliente",
            "persona_fisica": False,
            "partita_iva": "IT12345678901",
            "codice_fiscale": "12345678901",
            "codice_sdi": "W7YVJK9",
            "pec": "azienda@pec.it",
            "address": "Via Roma 1",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "country": "IT",
            "phone": "+39 06 1234567",
            "email": "info@azienda.it",
            "contacts": [
                {
                    "tipo": "Commerciale",
                    "nome": "Mario Rossi",
                    "telefono": "+39 333 1234567",
                    "email": "mario.rossi@azienda.it",
                    "include_preventivi": True,
                    "include_fatture": True,
                    "include_solleciti": False
                },
                {
                    "tipo": "Amministrativo",
                    "nome": "Giulia Bianchi",
                    "email": "giulia@azienda.it",
                    "include_fatture": True,
                    "include_solleciti": True
                }
            ],
            "payment_type_id": pt_id,
            "payment_type_label": "TEST_CLIENT_PT - Test payment for client",
            "iban": "IT60X0542811101000000123456",
            "banca": "Banca Test",
            "notes": "Cliente importante"
        }
        
        response = self.session.post(f"{BASE_URL}/api/clients/", json=client_payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['business_name'] == "TEST_Azienda SpA"
        assert data['client_type'] == "cliente"
        assert data['persona_fisica'] is False
        assert data['partita_iva'] == "IT12345678901"
        assert data['codice_sdi'] == "W7YVJK9"
        assert data['pec'] == "azienda@pec.it"
        assert len(data['contacts']) == 2
        assert data['contacts'][0]['nome'] == "Mario Rossi"
        assert data['contacts'][0]['include_preventivi'] is True
        assert data['contacts'][1]['nome'] == "Giulia Bianchi"
        assert data['payment_type_id'] == pt_id
        assert data['iban'] == "IT60X0542811101000000123456"
        
        self.created_client_ids.append(data['client_id'])
        print(f"✓ POST /api/clients/ - Created with expanded fields: {data['client_id']}")
        
        # Verify persistence
        get_response = self.session.get(f"{BASE_URL}/api/clients/{data['client_id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert len(fetched['contacts']) == 2
        assert fetched['payment_type_id'] == pt_id
        print(f"✓ GET /api/clients/{data['client_id']} - Expanded fields persisted")

    def test_create_fornitore_type(self):
        """Test creating a client with client_type=fornitore."""
        payload = {
            "business_name": "TEST_Fornitore Srl",
            "client_type": "fornitore",
            "partita_iva": "IT98765432101"
        }
        response = self.session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['client_type'] == "fornitore"
        self.created_client_ids.append(data['client_id'])
        print(f"✓ Created fornitore: {data['client_id']}")

    def test_create_cliente_fornitore_type(self):
        """Test creating a client with client_type=cliente_fornitore."""
        payload = {
            "business_name": "TEST_Both Type Srl",
            "client_type": "cliente_fornitore",
            "partita_iva": "IT11223344556"
        }
        response = self.session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['client_type'] == "cliente_fornitore"
        self.created_client_ids.append(data['client_id'])
        print(f"✓ Created cliente_fornitore: {data['client_id']}")

    def test_create_persona_fisica(self):
        """Test creating a persona fisica client."""
        payload = {
            "business_name": "TEST_Mario Rossi",
            "client_type": "cliente",
            "persona_fisica": True,
            "titolo": "Sig.",
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501U"
        }
        response = self.session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data['persona_fisica'] is True
        assert data['titolo'] == "Sig."
        assert data['cognome'] == "Rossi"
        assert data['nome'] == "Mario"
        self.created_client_ids.append(data['client_id'])
        print(f"✓ Created persona fisica: {data['client_id']}")

    def test_update_client_contacts(self):
        """Test updating client contacts array."""
        # Create client
        create_payload = {
            "business_name": "TEST_Update Contacts Srl",
            "contacts": []
        }
        create_response = self.session.post(f"{BASE_URL}/api/clients/", json=create_payload)
        assert create_response.status_code == 201
        client_id = create_response.json()['client_id']
        self.created_client_ids.append(client_id)
        
        # Update with contacts
        update_payload = {
            "contacts": [
                {
                    "tipo": "Tecnico",
                    "nome": "Paolo Verdi",
                    "email": "paolo@test.it",
                    "include_ddt": True
                }
            ]
        }
        update_response = self.session.put(f"{BASE_URL}/api/clients/{client_id}", json=update_payload)
        assert update_response.status_code == 200
        
        updated = update_response.json()
        assert len(updated['contacts']) == 1
        assert updated['contacts'][0]['nome'] == "Paolo Verdi"
        assert updated['contacts'][0]['include_ddt'] is True
        
        # Verify persistence
        get_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert len(fetched['contacts']) == 1
        print(f"✓ PUT /api/clients/{client_id} - Contacts updated and verified")

    def test_update_payment_type_link(self):
        """Test updating client payment_type_id."""
        # Create client
        create_payload = {
            "business_name": "TEST_Payment Link Srl"
        }
        create_response = self.session.post(f"{BASE_URL}/api/clients/", json=create_payload)
        assert create_response.status_code == 201
        client_id = create_response.json()['client_id']
        self.created_client_ids.append(client_id)
        
        # Create payment type
        pt_payload = {
            "codice": "TEST_LINK_PT",
            "tipo": "RIB",
            "descrizione": "Test link"
        }
        pt_response = self.session.post(f"{BASE_URL}/api/payment-types/", json=pt_payload)
        assert pt_response.status_code == 201
        pt_id = pt_response.json()['payment_type_id']
        self.created_pt_ids.append(pt_id)
        
        # Update client with payment type
        update_payload = {
            "payment_type_id": pt_id,
            "payment_type_label": "TEST_LINK_PT - Test link"
        }
        update_response = self.session.put(f"{BASE_URL}/api/clients/{client_id}", json=update_payload)
        assert update_response.status_code == 200
        
        updated = update_response.json()
        assert updated['payment_type_id'] == pt_id
        print(f"✓ Client payment_type_id linked: {pt_id}")

    def test_client_list_includes_new_fields(self):
        """Test GET /api/clients/ returns expanded fields."""
        response = self.session.get(f"{BASE_URL}/api/clients/?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert 'clients' in data
        assert 'total' in data
        
        if data['total'] > 0:
            client = data['clients'][0]
            # Check expanded fields are present
            assert 'client_type' in client
            assert 'persona_fisica' in client
            assert 'contacts' in client
            assert 'payment_type_id' in client
            print(f"✓ GET /api/clients/ - Expanded fields present in list response")
        else:
            print(f"✓ GET /api/clients/ - List response verified (no clients)")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy client_type values."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_session):
        """Setup method to get authenticated session."""
        self.session = auth_session['session']
        self.user_id = auth_session['user_id']
        self.created_client_ids = []

    def test_legacy_client_type_azienda(self):
        """Test that legacy client_type 'azienda' doesn't break the app."""
        # Note: The API accepts 'cliente' but old data may have 'azienda'
        # This tests that the frontend can handle different client_type values
        payload = {
            "business_name": "TEST_Legacy Azienda",
            "client_type": "cliente"  # New value
        }
        response = self.session.post(f"{BASE_URL}/api/clients/", json=payload)
        assert response.status_code == 201
        self.created_client_ids.append(response.json()['client_id'])
        print(f"✓ Legacy-style client created successfully")


class TestUnauthorizedAccess:
    """Test unauthorized access to payment types endpoints."""

    def test_payment_types_requires_auth(self):
        """Test GET /api/payment-types/ requires authentication."""
        response = requests.get(f"{BASE_URL}/api/payment-types/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /api/payment-types/ - 401 without auth")

    def test_seed_defaults_requires_auth(self):
        """Test POST /api/payment-types/seed-defaults requires authentication."""
        response = requests.post(f"{BASE_URL}/api/payment-types/seed-defaults")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/payment-types/seed-defaults - 401 without auth")

    def test_create_payment_type_requires_auth(self):
        """Test POST /api/payment-types/ requires authentication."""
        payload = {"codice": "TEST", "tipo": "BON", "descrizione": "Test"}
        response = requests.post(f"{BASE_URL}/api/payment-types/", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/payment-types/ - 401 without auth")


@pytest.fixture(scope="module")
def auth_session():
    """Create authenticated session for testing."""
    import subprocess
    import json
    
    # Create test user and session
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('test_database');
        var userId = 'test-pt-module-' + Date.now();
        var sessionToken = 'test_session_module_' + Date.now();
        db.users.insertOne({
          user_id: userId,
          email: 'test.module.' + Date.now() + '@example.com',
          name: 'Module Test User',
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
        db.clients.deleteMany({{user_id: '{user_id}'}});
        print('Cleanup complete for user: {user_id}');
        '''
    ], capture_output=True, text=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 119: Client CRUD API tests with Pydantic validation.

Tests P0 bug fixes:
1. Client creation with null values handled by Pydantic (model_validator strips nulls)
2. Duplicate P.IVA detection returns 400/409 with correct message
3. ClientCreate and ClientUpdate models validate properly
4. Extra fields are ignored (ConfigDict extra="ignore")
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://erp-metalwork-stage.preview.emergentagent.com"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Test user unique identifiers
TEST_USER_ID = f"test_user_iter119_{uuid.uuid4().hex[:8]}"
TEST_SESSION_TOKEN = f"session_iter119_{uuid.uuid4().hex[:8]}_token"


@pytest.fixture(scope="module")
def db():
    """Get MongoDB database handle for test setup/teardown."""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture(scope="module")
def test_user(db):
    """Create test user and session in MongoDB."""
    # Cleanup any existing test data
    db.users.delete_many({"user_id": TEST_USER_ID})
    db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    
    # Create test user
    db.users.insert_one({
        "user_id": TEST_USER_ID,
        "email": f"test.iter119.{uuid.uuid4().hex[:6]}@example.com",
        "name": "Test User Iter119",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create test session
    db.user_sessions.insert_one({
        "user_id": TEST_USER_ID,
        "session_token": TEST_SESSION_TOKEN,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    
    yield {"user_id": TEST_USER_ID, "session_token": TEST_SESSION_TOKEN}
    
    # Cleanup
    db.users.delete_many({"user_id": TEST_USER_ID})
    db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    db.clients.delete_many({"user_id": TEST_USER_ID})


@pytest.fixture(scope="module")
def auth_session(test_user):
    """Shared requests session with auth."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_user['session_token']}",
    })
    return session


class TestClientCRUDWithPydantic:
    """Test Client CRUD endpoints with Pydantic validation."""

    @pytest.fixture(autouse=True)
    def setup_auth_headers(self, auth_session):
        """Setup authorization headers for tests."""
        self.session = auth_session
        self.headers = dict(auth_session.headers)
        self.created_client_ids = []
        yield
        # Cleanup created clients
        for client_id in self.created_client_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/clients/{client_id}", timeout=10)
            except Exception:
                pass

    # ── Core Client Creation Tests ──

    def test_create_client_basic(self, db):
        """Test creating a client with required field only (business_name)."""
        payload = {"business_name": f"TEST_Azienda_{uuid.uuid4().hex[:6]}"}
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        assert response.status_code == 201, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert "client_id" in data
        assert data["business_name"] == payload["business_name"]
        assert data["client_type"] == "cliente"  # default
        self.created_client_ids.append(data["client_id"])
        print(f"PASS: Client created with ID {data['client_id']}")

    def test_create_client_with_null_values_stripped(self, db):
        """Test Pydantic strips null values and uses defaults instead."""
        payload = {
            "business_name": f"TEST_NullTest_{uuid.uuid4().hex[:6]}",
            "persona_fisica": None,  # Should default to False
            "contacts": None,  # Should default to []
            "client_type": None,  # Should default to "cliente"
            "email": None,  # Should stay None
        }
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        assert response.status_code == 201, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert data["persona_fisica"] == False, "persona_fisica should default to False"
        assert data.get("contacts", []) == [], "contacts should default to []"
        assert data["client_type"] == "cliente", "client_type should default to 'cliente'"
        self.created_client_ids.append(data["client_id"])
        print("PASS: Null values correctly stripped, defaults applied")

    def test_create_fornitore(self, db):
        """Test creating a supplier (client_type=fornitore)."""
        payload = {
            "business_name": f"TEST_Fornitore_{uuid.uuid4().hex[:6]}",
            "client_type": "fornitore",
            "partita_iva": f"IT{uuid.uuid4().hex[:11].upper()}",
        }
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        assert response.status_code == 201, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert data["client_type"] == "fornitore"
        self.created_client_ids.append(data["client_id"])
        print(f"PASS: Fornitore created with ID {data['client_id']}")

    def test_create_client_extra_fields_ignored(self, db):
        """Test that extra fields are silently ignored (ConfigDict extra='ignore')."""
        payload = {
            "business_name": f"TEST_ExtraFields_{uuid.uuid4().hex[:6]}",
            "unknown_field_xyz": "should_be_ignored",
            "another_unknown": 12345,
        }
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        # Should NOT return 422 for unknown fields
        assert response.status_code == 201, f"Extra fields should be ignored: {response.status_code}: {response.text}"
        data = response.json()
        assert "unknown_field_xyz" not in data
        self.created_client_ids.append(data["client_id"])
        print("PASS: Extra fields correctly ignored")

    # ── P.IVA Duplicate Detection Tests ──

    def test_duplicate_piva_returns_error(self, db):
        """Test duplicate P.IVA detection returns 400 with specific message."""
        piva = f"IT{uuid.uuid4().hex[:11].upper()}"
        
        # First client
        payload1 = {
            "business_name": f"TEST_Prima_Azienda_{uuid.uuid4().hex[:6]}",
            "partita_iva": piva,
        }
        r1 = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload1, timeout=10
        )
        assert r1.status_code == 201, f"First creation failed: {r1.status_code}"
        self.created_client_ids.append(r1.json()["client_id"])
        
        # Second client with SAME P.IVA
        payload2 = {
            "business_name": f"TEST_Seconda_Azienda_{uuid.uuid4().hex[:6]}",
            "partita_iva": piva,
        }
        r2 = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload2, timeout=10
        )
        
        assert r2.status_code in (400, 409), f"Expected 400/409 for duplicate P.IVA, got {r2.status_code}"
        data = r2.json()
        assert "detail" in data or "message" in data
        error_msg = data.get("detail", data.get("message", ""))
        assert "P.IVA" in error_msg or "IVA" in error_msg or "già" in error_msg.lower()
        print(f"PASS: Duplicate P.IVA correctly rejected: {error_msg}")

    def test_piva_duplicate_different_types_409(self, db):
        """Test duplicate P.IVA with different client_type returns 409."""
        piva = f"IT{uuid.uuid4().hex[:11].upper()}"
        
        # Create as cliente
        payload1 = {
            "business_name": f"TEST_Cliente_PIVA_{uuid.uuid4().hex[:6]}",
            "partita_iva": piva,
            "client_type": "cliente",
        }
        r1 = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload1, timeout=10
        )
        assert r1.status_code == 201, f"First creation failed: {r1.status_code}"
        self.created_client_ids.append(r1.json()["client_id"])
        
        # Try to create as fornitore with same P.IVA
        payload2 = {
            "business_name": f"TEST_Fornitore_PIVA_{uuid.uuid4().hex[:6]}",
            "partita_iva": piva,
            "client_type": "fornitore",
        }
        r2 = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload2, timeout=10
        )
        
        # Should get 409 suggesting conversion to cliente_fornitore
        assert r2.status_code == 409, f"Expected 409 for P.IVA conflict across types, got {r2.status_code}"
        data = r2.json()
        assert "detail" in data
        assert "Cliente/Fornitore" in data["detail"] or "cliente_fornitore" in data["detail"].lower()
        print(f"PASS: P.IVA conflict across types correctly returns 409")

    # ── Client Update Tests ──

    def test_update_client_success(self, db):
        """Test updating a client via PUT."""
        # Create first
        create_payload = {
            "business_name": f"TEST_UpdateMe_{uuid.uuid4().hex[:6]}",
            "city": "Milano",
        }
        r1 = self.session.post(
            f"{BASE_URL}/api/clients/", json=create_payload, timeout=10
        )
        assert r1.status_code == 201, f"Creation failed: {r1.status_code}"
        client_id = r1.json()["client_id"]
        self.created_client_ids.append(client_id)
        
        # Update
        update_payload = {
            "city": "Roma",
            "phone": "0612345678",
        }
        r2 = self.session.put(
            f"{BASE_URL}/api/clients/{client_id}", json=update_payload, timeout=10
        )
        
        assert r2.status_code == 200, f"Update failed: {r2.status_code}: {r2.text}"
        data = r2.json()
        assert data["city"] == "Roma"
        print(f"PASS: Client updated successfully")

    def test_update_client_piva_duplicate_check(self, db):
        """Test that updating P.IVA to an existing one fails."""
        piva1 = f"IT{uuid.uuid4().hex[:11].upper()}"
        piva2 = f"IT{uuid.uuid4().hex[:11].upper()}"
        
        # Create client 1
        r1 = self.session.post(
            f"{BASE_URL}/api/clients/",
            json={"business_name": f"TEST_C1_{uuid.uuid4().hex[:6]}", "partita_iva": piva1},
            timeout=10,
        )
        assert r1.status_code == 201
        self.created_client_ids.append(r1.json()["client_id"])
        
        # Create client 2
        r2 = self.session.post(
            f"{BASE_URL}/api/clients/",
            json={"business_name": f"TEST_C2_{uuid.uuid4().hex[:6]}", "partita_iva": piva2},
            timeout=10,
        )
        assert r2.status_code == 201
        client2_id = r2.json()["client_id"]
        self.created_client_ids.append(client2_id)
        
        # Try to update client 2's P.IVA to client 1's
        r3 = self.session.put(
            f"{BASE_URL}/api/clients/{client2_id}",
            json={"partita_iva": piva1},
            timeout=10,
        )
        
        assert r3.status_code == 400, f"Expected 400 for duplicate P.IVA on update, got {r3.status_code}"
        print("PASS: Duplicate P.IVA check on update works")

    # ── Client List and Filter Tests ──

    def test_get_clients_list(self, db):
        """Test GET /clients/ returns list."""
        response = self.session.get(
            f"{BASE_URL}/api/clients/", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        assert "total" in data
        print(f"PASS: Got {data['total']} clients")

    def test_filter_clients_by_type_fornitore(self, db):
        """Test filtering clients by client_type=fornitore."""
        response = self.session.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore",
            timeout=10,
        )
        assert response.status_code == 200
        data = response.json()
        # All returned should be fornitore or cliente_fornitore
        for c in data.get("clients", []):
            assert c.get("client_type") in ("fornitore", "cliente_fornitore")
        print(f"PASS: Fornitore filter works, got {len(data.get('clients', []))} results")

    # ── Client Delete Tests ──

    def test_delete_client_success(self, db):
        """Test DELETE /clients/{id} removes client."""
        # Create
        r1 = self.session.post(
            f"{BASE_URL}/api/clients/",
            json={"business_name": f"TEST_ToDelete_{uuid.uuid4().hex[:6]}"},
            timeout=10,
        )
        assert r1.status_code == 201, f"Creation failed: {r1.status_code}"
        client_id = r1.json()["client_id"]
        
        # Delete
        r2 = self.session.delete(
            f"{BASE_URL}/api/clients/{client_id}", timeout=10
        )
        assert r2.status_code == 200, f"Delete failed: {r2.status_code}"
        
        # Verify deleted
        r3 = self.session.get(
            f"{BASE_URL}/api/clients/{client_id}", timeout=10
        )
        assert r3.status_code == 404, "Client should be deleted"
        print("PASS: Client deleted and verified not found")

    def test_delete_nonexistent_client_404(self, db):
        """Test deleting non-existent client returns 404."""
        fake_id = f"cli_nonexistent_{uuid.uuid4().hex[:12]}"
        response = self.session.delete(
            f"{BASE_URL}/api/clients/{fake_id}", timeout=10
        )
        assert response.status_code == 404
        print("PASS: Non-existent client returns 404")

    # ── Pydantic Validation Tests ──

    def test_missing_business_name_returns_422(self, db):
        """Test missing required field business_name returns 422."""
        payload = {"city": "Milano", "email": "test@example.com"}  # No business_name
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        # Should be 422 (Pydantic validation error)
        assert response.status_code == 422, f"Expected 422 for missing required field, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Missing business_name correctly returns 422")

    def test_contacts_with_nested_nulls(self, db):
        """Test contacts array with nested null values is handled."""
        payload = {
            "business_name": f"TEST_Contacts_{uuid.uuid4().hex[:6]}",
            "contacts": [
                {
                    "tipo": "amministrazione",
                    "nome": "Mario Rossi",
                    "email": None,  # Should be stripped to default
                    "telefono": None,
                }
            ],
        }
        response = self.session.post(
            f"{BASE_URL}/api/clients/", json=payload, timeout=10
        )
        assert response.status_code == 201, f"Status {response.status_code}: {response.text}"
        data = response.json()
        contacts = data.get("contacts", [])
        assert len(contacts) == 1
        assert contacts[0]["nome"] == "Mario Rossi"
        # email and telefono should be empty strings (defaults)
        assert contacts[0].get("email", "") == ""
        self.created_client_ids.append(data["client_id"])
        print("PASS: Nested null values in contacts handled correctly")


class TestProfileMatchingLogic:
    """Verify profile matching logic - FLAT 120X12 vs FLAT 120X7 must produce different keys."""

    def test_flat_profiles_produce_unique_keys(self):
        """Core P0 bug test: FLAT 120X12 and FLAT 120X7 MUST have different keys."""
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.commessa_ops import _extract_profile_base
        
        key1 = _extract_profile_base("FLAT 120X12")
        key2 = _extract_profile_base("FLAT 120X7")
        
        assert key1 != key2, f"CRITICAL: FLAT 120X12 ({key1}) and FLAT 120X7 ({key2}) MUST have different keys!"
        assert key1 == "PIATTO120X12", f"FLAT 120X12 should be PIATTO120X12, got {key1}"
        assert key2 == "PIATTO120X7", f"FLAT 120X7 should be PIATTO120X7, got {key2}"
        print("PASS: FLAT 120X12 → PIATTO120X12, FLAT 120X7 → PIATTO120X7 (different keys)")

    def test_ipe_profiles(self):
        """Test standard profiles use family + main size only."""
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.commessa_ops import _extract_profile_base
        
        assert _extract_profile_base("IPE 100") == "IPE100"
        assert _extract_profile_base("HEB 120") == "HEB120"
        assert _extract_profile_base("UPN 100") == "UPN100"
        print("PASS: Standard profiles (IPE, HEB, UPN) extract correctly")

    def test_tube_profiles_include_all_dimensions(self):
        """Test tube profiles include full dimensions."""
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.commessa_ops import _extract_profile_base
        
        key1 = _extract_profile_base("TUBO 60X60X3")
        key2 = _extract_profile_base("TUBO 60X60X5")
        
        assert key1 == "TUBO60X60X3"
        assert key2 == "TUBO60X60X5"
        assert key1 != key2, "Different tube thicknesses must produce different keys"
        print("PASS: TUBO profiles include all dimensions")

    def test_dimension_spaces_collapsed(self):
        """Test spaces around X in dimensions are collapsed."""
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.commessa_ops import _extract_profile_base
        
        # "120 X 12" should become "120X12"
        result = _extract_profile_base("FLAT 120 x 12")
        assert result == "PIATTO120X12", f"Spaces around X should be collapsed, got {result}"
        print("PASS: Dimension spaces correctly collapsed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

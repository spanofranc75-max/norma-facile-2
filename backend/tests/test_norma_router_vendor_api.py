"""
Tests for Norma Router and Vendor API (Iteration 16)

Norma Router: Maps ProductType to required RegulationStandard with mandatory fields
Vendor API: Multi-key system for manufacturer catalog imports in NF-Standard JSON format

Features:
- Norma Router: GET /api/certificazioni/router/product-types, GET /api/certificazioni/router/{product_type}
- Vendor Keys: POST/GET/DELETE /api/vendor/keys (requires auth)
- Vendor Import: POST /api/vendor/import_catalog (requires X-Vendor-Key header)
- Vendor Catalogs: GET /api/vendor/catalogs, /api/vendor/catalogs/{catalog_id}, /api/vendor/catalogs/{vendor_name}/profiles
- Merged Thermal Profiles: GET /api/vendor/thermal-profiles
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create a test user and session for authenticated tests."""
    import subprocess
    result = subprocess.run([
        "mongosh", "--quiet", "--eval", """
use('test_database');
var userId = 'router_vendor_test_' + Date.now();
var sessionToken = 'router_vendor_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'router.vendor.' + Date.now() + '@example.com',
  name: 'Router Vendor Test',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print(JSON.stringify({session_token: sessionToken, user_id: userId}));
"""
    ], capture_output=True, text=True)
    import json
    data = json.loads(result.stdout.strip())
    yield data
    # Cleanup
    subprocess.run([
        "mongosh", "--quiet", "--eval", f"""
use('test_database');
db.users.deleteMany({{user_id: '{data["user_id"]}'}});
db.user_sessions.deleteMany({{session_token: '{data["session_token"]}'}});
db.vendor_keys.deleteMany({{owner_id: '{data["user_id"]}'}});
db.vendor_catalogs.deleteMany({{vendor: /^TEST_/}});
"""
    ], capture_output=True)


@pytest.fixture
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_headers(test_session):
    """Auth headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_session['session_token']}"}


# ==================== NORMA ROUTER TESTS (PUBLIC - no auth required) ====================

class TestNormaRouterProductTypes:
    """Tests for /api/certificazioni/router/product-types endpoint"""
    
    def test_get_product_types_returns_10_types(self, api_client):
        """GET /api/certificazioni/router/product-types returns 10 product types"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/product-types")
        assert response.status_code == 200
        
        data = response.json()
        assert "product_types" in data
        assert len(data["product_types"]) == 10
        
    def test_product_types_have_required_fields(self, api_client):
        """Each product type has id, label, standards, has_thermal"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/product-types")
        data = response.json()
        
        for pt in data["product_types"]:
            assert "id" in pt, f"Missing 'id' in {pt}"
            assert "label" in pt, f"Missing 'label' in {pt}"
            assert "standards" in pt, f"Missing 'standards' in {pt}"
            assert "has_thermal" in pt, f"Missing 'has_thermal' in {pt}"
            assert isinstance(pt["standards"], list)
            assert isinstance(pt["has_thermal"], bool)
    
    def test_finestra_has_thermal_true(self, api_client):
        """Finestra and Portafinestra have has_thermal=True (requires ThermalValidator)"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/product-types")
        data = response.json()
        
        finestra = next((p for p in data["product_types"] if p["id"] == "finestra"), None)
        portafinestra = next((p for p in data["product_types"] if p["id"] == "portafinestra"), None)
        
        assert finestra is not None
        assert portafinestra is not None
        assert finestra["has_thermal"] == True
        assert portafinestra["has_thermal"] == True
    
    def test_cancello_has_thermal_false(self, api_client):
        """Cancello has has_thermal=False (ThermalValidator is optional)"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/product-types")
        data = response.json()
        
        cancello = next((p for p in data["product_types"] if p["id"] == "cancello"), None)
        assert cancello is not None
        assert cancello["has_thermal"] == False


class TestNormaRouterCancello:
    """Tests for /api/certificazioni/router/cancello endpoint"""
    
    def test_cancello_returns_en13241(self, api_client):
        """GET /api/certificazioni/router/cancello returns EN 13241"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/cancello")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_type"] == "cancello"
        assert "EN 13241" in data["standards"]
    
    def test_cancello_mandatory_fields(self, api_client):
        """Cancello has mandatory fields: product_type, mechanical_resistance, safe_opening, durability"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/cancello")
        data = response.json()
        
        fields = [f["field"] for f in data["mandatory_fields"]]
        assert "product_type" in fields
        assert "mechanical_resistance" in fields
        assert "safe_opening" in fields
        assert "durability" in fields
    
    def test_cancello_thermal_optional(self, api_client):
        """Cancello has ThermalValidator as optional"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/cancello")
        data = response.json()
        
        assert "ThermalValidator" in data["optional_validators"]


class TestNormaRouterFinestra:
    """Tests for /api/certificazioni/router/finestra endpoint"""
    
    def test_finestra_returns_en14351(self, api_client):
        """GET /api/certificazioni/router/finestra returns EN 14351-1"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/finestra")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_type"] == "finestra"
        assert "EN 14351-1" in data["standards"]
    
    def test_finestra_requires_thermal(self, api_client):
        """Finestra has ThermalValidator as required validator (not optional)"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/finestra")
        data = response.json()
        
        assert "ThermalValidator" in data["validators"]
        assert "ThermalValidator" not in data["optional_validators"]
    
    def test_finestra_mandatory_thermal_uw(self, api_client):
        """Finestra has thermal_uw as mandatory field"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/finestra")
        data = response.json()
        
        fields = [f["field"] for f in data["mandatory_fields"]]
        assert "thermal_uw" in fields


class TestNormaRouterTettoia:
    """Tests for /api/certificazioni/router/tettoia endpoint"""
    
    def test_tettoia_returns_en1090(self, api_client):
        """GET /api/certificazioni/router/tettoia returns EN 1090-1"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/tettoia")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_type"] == "tettoia"
        assert "EN 1090-1" in data["standards"]
    
    def test_tettoia_execution_class_mandatory(self, api_client):
        """Tettoia (structural) has execution_class as mandatory field"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/tettoia")
        data = response.json()
        
        fields = [f["field"] for f in data["mandatory_fields"]]
        assert "execution_class" in fields


class TestNormaRouterUnknownType:
    """Tests for unknown product type defaults to structural"""
    
    def test_unknown_defaults_to_structural(self, api_client):
        """Unknown product type defaults to structural (EN 1090-1)"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/unknown_type")
        assert response.status_code == 200
        
        data = response.json()
        # Should default to tettoia (structural)
        assert "EN 1090-1" in data["standards"]
        
    def test_nonsense_type_defaults_to_structural(self, api_client):
        """Random nonsense type also defaults to structural"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/xyzabc123")
        assert response.status_code == 200
        
        data = response.json()
        assert "EN 1090-1" in data["standards"]


# ==================== VENDOR API TESTS ====================

class TestVendorImportAuth:
    """Tests for Vendor import authentication via X-Vendor-Key header"""
    
    def test_import_without_header_returns_422(self, api_client):
        """POST /api/vendor/import_catalog WITHOUT X-Vendor-Key returns 422 (missing field)"""
        response = api_client.post(
            f"{BASE_URL}/api/vendor/import_catalog",
            json={"vendor": "Test", "system": "Test", "profiles": [{"code": "123", "type": "Test"}]}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        # Should indicate missing x-vendor-key header
        assert any("x-vendor-key" in str(d).lower() for d in data.get("detail", []))
    
    def test_import_with_invalid_key_returns_403(self, api_client):
        """POST /api/vendor/import_catalog WITH invalid key returns 403"""
        response = api_client.post(
            f"{BASE_URL}/api/vendor/import_catalog",
            json={"vendor": "Test", "system": "Test", "profiles": [{"code": "123", "type": "Test"}]},
            headers={"X-Vendor-Key": "invalid_key_12345"}
        )
        assert response.status_code == 403


class TestVendorKeyManagement:
    """Tests for Vendor Key CRUD operations (require user auth)"""
    
    def test_create_vendor_key(self, api_client, auth_headers, test_session):
        """POST /api/vendor/keys creates a new vendor API key"""
        response = api_client.post(
            f"{BASE_URL}/api/vendor/keys",
            json={"vendor_name": "TEST_VendorCreate", "contact_email": "create@test.com", "notes": "Test note"},
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert "key_id" in data
        assert "api_key" in data
        assert data["vendor_name"] == "TEST_VendorCreate"
        assert data["api_key"].startswith("nf_vk_")
        
        # Store for later tests
        test_session["created_key_id"] = data["key_id"]
        test_session["created_api_key"] = data["api_key"]
    
    def test_list_vendor_keys_shows_masked(self, api_client, auth_headers, test_session):
        """GET /api/vendor/keys lists vendor keys with masked api_key"""
        response = api_client.get(f"{BASE_URL}/api/vendor/keys", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) >= 1
        
        # Check for masked key
        key = next((k for k in data["keys"] if k.get("key_id") == test_session.get("created_key_id")), None)
        if key:
            assert "api_key_masked" in key
            assert "..." in key["api_key_masked"]


class TestVendorCatalogImport:
    """Tests for Vendor Catalog import via X-Vendor-Key"""
    
    def test_import_catalog_with_valid_key(self, api_client, auth_headers, test_session):
        """POST /api/vendor/import_catalog WITH valid key imports NF-Standard catalog"""
        # First create a key if not already
        if "created_api_key" not in test_session:
            key_resp = api_client.post(
                f"{BASE_URL}/api/vendor/keys",
                json={"vendor_name": "TEST_ImportVendor"},
                headers=auth_headers
            )
            test_session["created_key_id"] = key_resp.json()["key_id"]
            test_session["created_api_key"] = key_resp.json()["api_key"]
        
        # Import catalog
        response = api_client.post(
            f"{BASE_URL}/api/vendor/import_catalog",
            json={
                "vendor": "TEST_Vendor",
                "system": "Test System 100",
                "profiles": [
                    {"code": "T001", "type": "Test Frame A", "uf": 2.5, "weight": 1.8},
                    {"code": "T002", "type": "Test Frame B", "uf": 2.8, "weight": 2.0}
                ]
            },
            headers={"X-Vendor-Key": test_session["created_api_key"]}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "importato"
        assert data["profiles_imported"] == 2
        assert "catalog_id" in data
        
        test_session["catalog_id"] = data["catalog_id"]
    
    def test_import_catalog_upsert(self, api_client, test_session):
        """POST /api/vendor/import_catalog same vendor+system updates existing (upsert)"""
        response = api_client.post(
            f"{BASE_URL}/api/vendor/import_catalog",
            json={
                "vendor": "TEST_Vendor",
                "system": "Test System 100",
                "profiles": [
                    {"code": "T001", "type": "Test Frame A Updated", "uf": 2.4, "weight": 1.75},
                    {"code": "T002", "type": "Test Frame B", "uf": 2.8, "weight": 2.0},
                    {"code": "T003", "type": "Test Frame C New", "uf": 3.0, "weight": 2.5}
                ]
            },
            headers={"X-Vendor-Key": test_session["created_api_key"]}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "aggiornato"
        assert data["profiles_imported"] == 3
        # Should use same catalog_id
        assert data["catalog_id"] == test_session.get("catalog_id")


class TestVendorCatalogRead:
    """Tests for reading vendor catalogs"""
    
    def test_list_catalogs(self, api_client, auth_headers, test_session):
        """GET /api/vendor/catalogs lists imported vendor catalogs"""
        response = api_client.get(f"{BASE_URL}/api/vendor/catalogs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "catalogs" in data
        # Should find our test catalog
        test_catalog = next((c for c in data["catalogs"] if c["vendor"] == "TEST_Vendor"), None)
        assert test_catalog is not None
        assert test_catalog["system"] == "Test System 100"
    
    def test_get_single_catalog(self, api_client, auth_headers, test_session):
        """GET /api/vendor/catalogs/{catalog_id} returns catalog with profiles"""
        if "catalog_id" not in test_session:
            pytest.skip("No catalog_id from previous test")
        
        response = api_client.get(
            f"{BASE_URL}/api/vendor/catalogs/{test_session['catalog_id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["catalog_id"] == test_session["catalog_id"]
        assert "profiles" in data
        assert len(data["profiles"]) >= 2
    
    def test_get_vendor_profiles(self, api_client, auth_headers):
        """GET /api/vendor/catalogs/{vendor_name}/profiles returns vendor's profiles"""
        response = api_client.get(
            f"{BASE_URL}/api/vendor/catalogs/TEST_Vendor/profiles",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["vendor"] == "TEST_Vendor"
        assert "profiles" in data
        assert data["total"] >= 2


class TestMergedThermalProfiles:
    """Tests for merged thermal profiles (builtin + vendor + custom)"""
    
    def test_merged_profiles_contains_builtin(self, api_client, auth_headers):
        """GET /api/vendor/thermal-profiles returns builtin frame types"""
        response = api_client.get(f"{BASE_URL}/api/vendor/thermal-profiles", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "frame_types" in data
        
        # Should have builtin profiles
        builtin = [f for f in data["frame_types"] if f.get("source") == "builtin"]
        assert len(builtin) >= 5  # At least several builtin frame types
    
    def test_merged_profiles_contains_vendor(self, api_client, auth_headers):
        """Merged thermal profiles include vendor profiles with source='vendor'"""
        response = api_client.get(f"{BASE_URL}/api/vendor/thermal-profiles", headers=auth_headers)
        data = response.json()
        
        # Should have vendor profiles (from our test import)
        vendor = [f for f in data["frame_types"] if f.get("source") == "vendor"]
        assert len(vendor) >= 1  # At least one from our test
        
        # Vendor profiles should have vendor field set
        for v in vendor:
            assert v.get("vendor") is not None
    
    def test_vendor_profile_has_correct_format(self, api_client, auth_headers):
        """Vendor profile has id, label, uf, source='vendor', vendor field"""
        response = api_client.get(f"{BASE_URL}/api/vendor/thermal-profiles", headers=auth_headers)
        data = response.json()
        
        vendor_profile = next((f for f in data["frame_types"] if f.get("source") == "vendor"), None)
        if vendor_profile:
            assert "id" in vendor_profile
            assert "label" in vendor_profile
            assert "uf" in vendor_profile
            assert vendor_profile["source"] == "vendor"


class TestVendorKeyRevocation:
    """Tests for vendor key revocation and subsequent auth failure"""
    
    def test_revoke_vendor_key(self, api_client, auth_headers, test_session):
        """DELETE /api/vendor/keys/{key_id} revokes (deactivates) a vendor key"""
        if "created_key_id" not in test_session:
            pytest.skip("No key_id from previous test")
        
        response = api_client.delete(
            f"{BASE_URL}/api/vendor/keys/{test_session['created_key_id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "revocata" in data.get("message", "").lower() or "success" in data.get("message", "").lower()
    
    def test_import_with_revoked_key_fails(self, api_client, test_session):
        """After revoke, import with that key returns 403"""
        if "created_api_key" not in test_session:
            pytest.skip("No api_key from previous test")
        
        response = api_client.post(
            f"{BASE_URL}/api/vendor/import_catalog",
            json={"vendor": "Test", "system": "Test", "profiles": [{"code": "123", "type": "Test"}]},
            headers={"X-Vendor-Key": test_session["created_api_key"]}
        )
        assert response.status_code == 403


# ==================== NO AUTH REQUIRED FOR ROUTER ====================

class TestNormaRouterNoAuth:
    """Verify Norma Router endpoints are public (no auth required)"""
    
    def test_product_types_no_auth(self, api_client):
        """Norma Router /product-types is accessible without auth"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/product-types")
        assert response.status_code == 200
        # No 401 or 403
    
    def test_route_product_no_auth(self, api_client):
        """Norma Router /{product_type} is accessible without auth"""
        response = api_client.get(f"{BASE_URL}/api/certificazioni/router/finestra")
        assert response.status_code == 200
        # No 401 or 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

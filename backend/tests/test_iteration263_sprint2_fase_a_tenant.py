"""
Sprint 2 Fase A: Multi-Tenant Reale (Fondamenta) Tests
Tests for:
- Tenant service CRUD (create_tenant, get_tenant, list_tenants, update_tenant, deactivate_tenant)
- ensure_tenant_for_user auto-onboarding
- Tenant counters with tenant isolation
- Admin tenant API routes (401 without auth)
- MongoDB indexes for tenants and tenant_counters
- Security.py auto-calls ensure_tenant_for_user for admin users
"""
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests
import asyncio
import uuid
from datetime import datetime

# Backend URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ============================================================================
# SYNC TESTS - API Auth and Module Imports
# ============================================================================

class TestHealthCheck:
    """Verify backend is running"""
    
    def test_health_returns_200(self):
        """Health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.2.0"
        print(f"PASS: Health check returns 200 with status={data['status']}")


class TestAdminTenantAPIAuth:
    """Test that admin tenant API routes return 401 without auth"""
    
    def test_list_tenants_401_without_auth(self):
        """GET /api/admin/tenants/ should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/tenants/")
        assert response.status_code == 401
        print("PASS: GET /api/admin/tenants/ returns 401 without auth")
    
    def test_create_tenant_401_without_auth(self):
        """POST /api/admin/tenants/ should return 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/admin/tenants/", json={
            "nome_azienda": "Test Company"
        })
        assert response.status_code == 401
        print("PASS: POST /api/admin/tenants/ returns 401 without auth")
    
    def test_my_tenant_401_without_auth(self):
        """GET /api/admin/tenants/my should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/tenants/my")
        assert response.status_code == 401
        print("PASS: GET /api/admin/tenants/my returns 401 without auth")
    
    def test_get_tenant_by_id_401_without_auth(self):
        """GET /api/admin/tenants/{tenant_id} should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/tenants/ten_test123")
        assert response.status_code == 401
        print("PASS: GET /api/admin/tenants/{tenant_id} returns 401 without auth")
    
    def test_update_tenant_401_without_auth(self):
        """PUT /api/admin/tenants/{tenant_id} should return 401 without auth"""
        response = requests.put(f"{BASE_URL}/api/admin/tenants/ten_test123", json={
            "nome_azienda": "Updated Name"
        })
        assert response.status_code == 401
        print("PASS: PUT /api/admin/tenants/{tenant_id} returns 401 without auth")
    
    def test_deactivate_tenant_401_without_auth(self):
        """DELETE /api/admin/tenants/{tenant_id} should return 401 without auth"""
        response = requests.delete(f"{BASE_URL}/api/admin/tenants/ten_test123")
        assert response.status_code == 401
        print("PASS: DELETE /api/admin/tenants/{tenant_id} returns 401 without auth")


class TestTenantServiceImports:
    """Test tenant_service.py module imports and structure"""
    
    def test_tenant_service_imports(self):
        """Verify tenant_service module imports correctly"""
        from services.tenant_service import (
            create_tenant,
            get_tenant,
            list_tenants,
            update_tenant,
            deactivate_tenant,
            ensure_tenant_for_user,
            PIANI_DISPONIBILI,
            COLLECTION
        )
        assert COLLECTION == "tenants"
        assert "pilot" in PIANI_DISPONIBILI
        assert "pro" in PIANI_DISPONIBILI
        assert "enterprise" in PIANI_DISPONIBILI
        print("PASS: tenant_service imports correctly with all CRUD functions")
    
    def test_piani_disponibili_limits(self):
        """Verify plan limits are correct"""
        from services.tenant_service import PIANI_DISPONIBILI
        
        # Pilot plan
        assert PIANI_DISPONIBILI["pilot"]["max_utenti"] == 3
        assert PIANI_DISPONIBILI["pilot"]["max_commesse"] == 50
        
        # Pro plan
        assert PIANI_DISPONIBILI["pro"]["max_utenti"] == 10
        assert PIANI_DISPONIBILI["pro"]["max_commesse"] == 500
        
        # Enterprise plan (unlimited = -1)
        assert PIANI_DISPONIBILI["enterprise"]["max_utenti"] == -1
        assert PIANI_DISPONIBILI["enterprise"]["max_commesse"] == -1
        
        print("PASS: Plan limits are correct (pilot: 3/50, pro: 10/500, enterprise: unlimited)")


class TestTenantCountersImports:
    """Test tenant_counters.py module imports"""
    
    def test_tenant_counters_imports(self):
        """Verify tenant_counters module imports correctly"""
        from services.tenant_counters import (
            get_next_counter,
            seed_counter,
            get_counter_value,
            list_counters,
            COLLECTION
        )
        assert COLLECTION == "tenant_counters"
        print("PASS: tenant_counters imports correctly with all functions")


class TestSecurityAutoOnboarding:
    """Test that security.py create_session auto-calls ensure_tenant_for_user"""
    
    def test_security_imports_ensure_tenant_for_user(self):
        """Verify security.py imports ensure_tenant_for_user"""
        import inspect
        from core import security
        
        source = inspect.getsource(security)
        
        # Check that ensure_tenant_for_user is imported and called
        assert "ensure_tenant_for_user" in source
        assert "from services.tenant_service import ensure_tenant_for_user" in source
        
        print("PASS: security.py imports ensure_tenant_for_user from tenant_service")
    
    def test_create_session_calls_ensure_tenant_for_user(self):
        """Verify create_session calls ensure_tenant_for_user for admin users"""
        import inspect
        from core import security
        
        source = inspect.getsource(security.create_session)
        
        # Check that ensure_tenant_for_user is called in create_session
        assert "ensure_tenant_for_user" in source
        
        # Check the condition for calling it (admin users with default tenant)
        assert 'role' in source
        assert 'admin' in source
        
        print("PASS: create_session calls ensure_tenant_for_user for admin users")


class TestAdminTenantsRouterStructure:
    """Test admin_tenants.py router structure"""
    
    def test_admin_tenants_router_imports(self):
        """Verify admin_tenants router imports correctly"""
        from routes.admin_tenants import router
        
        assert router.prefix == "/api/admin/tenants"
        assert "admin-tenants" in router.tags
        
        print("PASS: admin_tenants router has correct prefix /api/admin/tenants")
    
    def test_admin_tenants_routes_exist(self):
        """Verify all expected routes exist"""
        from routes.admin_tenants import router
        
        routes = [r.path for r in router.routes]
        
        # Routes include the prefix, so check for full paths
        assert any("/api/admin/tenants/" in r for r in routes)  # GET list, POST create
        assert any("/my" in r for r in routes)  # GET my tenant
        assert any("{tenant_id}" in r for r in routes)  # GET, PUT, DELETE
        
        print("PASS: admin_tenants router has all expected routes")


# ============================================================================
# ASYNC TESTS - Database Operations (Combined into single test for event loop)
# ============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_all_async_tenant_operations():
    """Combined async test for all tenant CRUD and counter operations"""
    from services.tenant_service import (
        create_tenant, get_tenant, list_tenants, 
        update_tenant, deactivate_tenant, ensure_tenant_for_user
    )
    from services.tenant_counters import get_next_counter
    from core.database import db
    
    results = []
    
    # Test 1: create_tenant with correct fields
    test_user_id = f"user_test_{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "user_id": test_user_id,
        "email": f"test_{uuid.uuid4().hex[:6]}@test.com",
        "name": "Test User",
        "role": "admin",
        "tenant_id": "default"
    })
    
    try:
        tenant = await create_tenant(
            nome_azienda="Test Company Sprint2",
            admin_user_id=test_user_id,
            piano="pilot",
            partita_iva="IT12345678901",
            email_contatto="test@sprint2.com"
        )
        
        assert tenant["tenant_id"].startswith("ten_")
        assert tenant["nome_azienda"] == "Test Company Sprint2"
        assert tenant["piano"] == "pilot"
        assert tenant["partita_iva"] == "IT12345678901"
        assert tenant["email_contatto"] == "test@sprint2.com"
        assert tenant["attivo"] == True
        assert tenant["admin_user_id"] == test_user_id
        assert tenant["max_utenti"] == 3  # pilot plan
        assert tenant["max_commesse"] == 50  # pilot plan
        assert "creato_il" in tenant
        assert "aggiornato_il" in tenant
        assert "_id" not in tenant
        
        user = await db.users.find_one({"user_id": test_user_id}, {"_id": 0})
        assert user["tenant_id"] == tenant["tenant_id"]
        
        results.append("PASS: create_tenant creates tenant with all correct fields")
        
        # Test 2: get_tenant returns tenant by id
        fetched = await get_tenant(tenant["tenant_id"])
        assert fetched is not None
        assert fetched["tenant_id"] == tenant["tenant_id"]
        assert fetched["nome_azienda"] == "Test Company Sprint2"
        assert "_id" not in fetched
        results.append("PASS: get_tenant returns tenant by tenant_id")
        
        # Test 3: list_tenants returns active with counts
        tenants = await list_tenants(only_active=True)
        assert isinstance(tenants, list)
        test_tenant = next((t for t in tenants if t["tenant_id"] == tenant["tenant_id"]), None)
        assert test_tenant is not None
        assert "utenti_count" in test_tenant
        assert "commesse_count" in test_tenant
        results.append("PASS: list_tenants returns active tenants with utenti_count and commesse_count")
        
        # Test 4: update_tenant updates fields and plan limits
        updated = await update_tenant(tenant["tenant_id"], {
            "nome_azienda": "Updated Company Name",
            "piano": "pro"
        })
        assert updated["nome_azienda"] == "Updated Company Name"
        assert updated["piano"] == "pro"
        assert updated["max_utenti"] == 10  # pro plan limits
        assert updated["max_commesse"] == 500  # pro plan limits
        results.append("PASS: update_tenant updates fields correctly, including plan-based limits")
        
        # Test 5: deactivate_tenant sets attivo=False
        success = await deactivate_tenant(tenant["tenant_id"])
        assert success == True
        fetched = await get_tenant(tenant["tenant_id"])
        assert fetched["attivo"] == False
        results.append("PASS: deactivate_tenant sets attivo=False")
        
        # Cleanup first tenant
        await db.tenants.delete_one({"tenant_id": tenant["tenant_id"]})
        await db.users.delete_one({"user_id": test_user_id})
        
    except Exception as e:
        await db.users.delete_one({"user_id": test_user_id})
        raise e
    
    # Test 6: ensure_tenant_for_user auto-creates for admin
    test_user_id2 = f"user_test_{uuid.uuid4().hex[:8]}"
    test_email2 = f"admin_{uuid.uuid4().hex[:6]}@test.com"
    
    await db.users.insert_one({
        "user_id": test_user_id2,
        "email": test_email2,
        "name": "Admin Test User",
        "role": "admin",
        "tenant_id": "default"
    })
    
    try:
        tenant_id = await ensure_tenant_for_user(test_user_id2, test_email2, "Admin Test User")
        assert tenant_id != "default"
        assert tenant_id.startswith("ten_")
        
        tenant = await get_tenant(tenant_id)
        assert tenant is not None
        assert tenant["nome_azienda"] == "Admin Test User"
        assert tenant["admin_user_id"] == test_user_id2
        results.append("PASS: ensure_tenant_for_user auto-creates tenant for admin users")
        
        await db.tenants.delete_one({"tenant_id": tenant_id})
        await db.users.delete_one({"user_id": test_user_id2})
        
    except Exception as e:
        await db.users.delete_one({"user_id": test_user_id2})
        raise e
    
    # Test 7: ensure_tenant_for_user does NOT create for non-admin
    test_user_id3 = f"user_test_{uuid.uuid4().hex[:8]}"
    test_email3 = f"guest_{uuid.uuid4().hex[:6]}@test.com"
    
    await db.users.insert_one({
        "user_id": test_user_id3,
        "email": test_email3,
        "name": "Guest Test User",
        "role": "guest",
        "tenant_id": "default"
    })
    
    try:
        tenant_id = await ensure_tenant_for_user(test_user_id3, test_email3, "Guest Test User")
        assert tenant_id == "default"
        results.append("PASS: ensure_tenant_for_user does NOT auto-create tenant for non-admin users")
        
        await db.users.delete_one({"user_id": test_user_id3})
        
    except Exception as e:
        await db.users.delete_one({"user_id": test_user_id3})
        raise e
    
    # Test 8: get_next_counter returns sequential numbers
    test_tenant_id = f"ten_test_{uuid.uuid4().hex[:8]}"
    year = 2026
    
    try:
        counter1 = await get_next_counter(test_tenant_id, "commessa", year, "NF")
        assert counter1 == "NF-2026-000001"
        
        counter2 = await get_next_counter(test_tenant_id, "commessa", year, "NF")
        assert counter2 == "NF-2026-000002"
        
        counter3 = await get_next_counter(test_tenant_id, "commessa", year, "NF")
        assert counter3 == "NF-2026-000003"
        
        results.append("PASS: get_next_counter returns sequential numbers (NF-2026-000001, NF-2026-000002, NF-2026-000003)")
        
        await db.tenant_counters.delete_many({"tenant_id": test_tenant_id})
        
    except Exception as e:
        await db.tenant_counters.delete_many({"tenant_id": test_tenant_id})
        raise e
    
    # Test 9: counters isolated per tenant
    tenant_a = f"ten_a_{uuid.uuid4().hex[:8]}"
    tenant_b = f"ten_b_{uuid.uuid4().hex[:8]}"
    
    try:
        counter_a1 = await get_next_counter(tenant_a, "commessa", year, "NF")
        assert counter_a1 == "NF-2026-000001"
        
        counter_b1 = await get_next_counter(tenant_b, "commessa", year, "NF")
        assert counter_b1 == "NF-2026-000001"  # Same number, different tenant
        
        counter_a2 = await get_next_counter(tenant_a, "commessa", year, "NF")
        assert counter_a2 == "NF-2026-000002"
        
        counter_b2 = await get_next_counter(tenant_b, "commessa", year, "NF")
        assert counter_b2 == "NF-2026-000002"
        
        results.append("PASS: Counters are isolated per tenant_id (tenant A and B have independent sequences)")
        
        await db.tenant_counters.delete_many({"tenant_id": tenant_a})
        await db.tenant_counters.delete_many({"tenant_id": tenant_b})
        
    except Exception as e:
        await db.tenant_counters.delete_many({"tenant_id": tenant_a})
        await db.tenant_counters.delete_many({"tenant_id": tenant_b})
        raise e
    
    # Test 10: counter document includes metadata
    test_tenant_id2 = f"ten_meta_{uuid.uuid4().hex[:8]}"
    
    try:
        await get_next_counter(test_tenant_id2, "fattura", year, "FT")
        
        doc = await db.tenant_counters.find_one({
            "counter_id": f"{test_tenant_id2}_fattura_{year}"
        })
        
        assert doc is not None
        assert doc["tenant_id"] == test_tenant_id2
        assert doc["counter_type"] == "fattura"
        assert doc["year"] == year
        assert doc["value"] == 1
        
        results.append("PASS: Counter document includes tenant_id, counter_type, year metadata")
        
        await db.tenant_counters.delete_many({"tenant_id": test_tenant_id2})
        
    except Exception as e:
        await db.tenant_counters.delete_many({"tenant_id": test_tenant_id2})
        raise e
    
    # Test 11-13: MongoDB indexes
    indexes = await db.tenants.index_information()
    assert "uq_tenant" in indexes
    assert indexes["uq_tenant"]["unique"] == True
    results.append("PASS: tenants.uq_tenant index exists and is unique")
    
    indexes = await db.tenant_counters.index_information()
    assert "uq_tenant_counter" in indexes
    assert indexes["uq_tenant_counter"]["unique"] == True
    results.append("PASS: tenant_counters.uq_tenant_counter index exists and is unique")
    
    assert "idx_tenant_counter_tid" in indexes
    results.append("PASS: tenant_counters.idx_tenant_counter_tid index exists")
    
    # Print all results
    for result in results:
        print(result)
    
    print(f"\nAll {len(results)} async tests passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

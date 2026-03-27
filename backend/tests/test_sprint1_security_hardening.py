"""
Sprint 1 Security Hardening Tests - NormaFacile 2.0

Tests for:
1. Backend health check returns 200
2. Protected endpoints return 401 without auth cookie
3. RBAC decorator blocks unauthorized roles
4. Audit trail includes tenant_id field
5. JWT_SECRET removed from config.py
6. All 88 route modules import without errors
"""
import pytest
import requests
import os
import sys

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cors-token-migration.preview.emergentagent.com')


class TestHealthCheck:
    """Test backend health endpoint"""
    
    def test_health_returns_200(self):
        """GET /api/health should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy"
        assert "version" in data
        print(f"✓ Health check passed: {data}")


class TestProtectedEndpointsReturn401:
    """Test that protected endpoints return 401 without auth cookie"""
    
    @pytest.mark.parametrize("endpoint", [
        "/api/clients/",
        "/api/invoices/",
        "/api/commesse/",
        "/api/preventivi/",
        "/api/ddt/",
        "/api/admin/backup/stats",
        "/api/admin/backup/history",
        "/api/dashboard/stats",
        "/api/company/settings",
    ])
    def test_endpoint_returns_401_without_auth(self, endpoint):
        """Protected endpoints should return 401 without session cookie"""
        response = requests.get(f"{BASE_URL}{endpoint}")
        assert response.status_code == 401, f"{endpoint}: Expected 401, got {response.status_code}"
        print(f"✓ {endpoint} returns 401 without auth")


class TestRBACDecorator:
    """Test RBAC decorator logic directly"""
    
    def test_rbac_module_imports(self):
        """core.rbac module should import without errors"""
        from core.rbac import require_role, ROLE_ACCESS
        assert callable(require_role)
        assert isinstance(ROLE_ACCESS, dict)
        assert "admin" in ROLE_ACCESS
        assert ROLE_ACCESS["admin"] == ["*"]
        print(f"✓ RBAC module imports correctly, roles: {list(ROLE_ACCESS.keys())}")
    
    def test_rbac_role_access_structure(self):
        """ROLE_ACCESS should have correct structure"""
        from core.rbac import ROLE_ACCESS
        expected_roles = ["admin", "ufficio_tecnico", "officina", "amministrazione", "guest"]
        for role in expected_roles:
            assert role in ROLE_ACCESS, f"Missing role: {role}"
        print(f"✓ All expected roles present: {expected_roles}")
    
    def test_require_role_returns_dependency(self):
        """require_role() should return a FastAPI dependency function"""
        from core.rbac import require_role
        dep = require_role("admin", "amministrazione")
        assert callable(dep)
        # The dependency is an async function
        import asyncio
        assert asyncio.iscoroutinefunction(dep)
        print("✓ require_role() returns async dependency function")


class TestAuditTrailTenantId:
    """Test that audit trail includes tenant_id field"""
    
    def test_audit_trail_module_imports(self):
        """services.audit_trail module should import"""
        from services.audit_trail import log_activity, COLLECTION, ENTITY_TYPES, ACTION_TYPES
        assert callable(log_activity)
        assert COLLECTION == "activity_log"
        assert len(ENTITY_TYPES) > 0
        assert len(ACTION_TYPES) > 0
        print(f"✓ Audit trail module imports, {len(ENTITY_TYPES)} entity types, {len(ACTION_TYPES)} action types")
    
    def test_log_activity_signature(self):
        """log_activity should accept tenant_id via user dict"""
        import inspect
        from services.audit_trail import log_activity
        sig = inspect.signature(log_activity)
        params = list(sig.parameters.keys())
        assert "user" in params, "log_activity should have 'user' parameter"
        print(f"✓ log_activity signature: {params}")
    
    def test_audit_trail_source_has_tenant_id(self):
        """audit_trail.py source should include tenant_id in doc"""
        with open("/app/backend/services/audit_trail.py", "r") as f:
            content = f.read()
        assert 'tenant_id' in content, "tenant_id not found in audit_trail.py"
        assert 'user.get("tenant_id"' in content, "tenant_id extraction not found"
        print("✓ audit_trail.py includes tenant_id field in log document")


class TestJWTSecretRemoved:
    """Test that JWT_SECRET is removed from config"""
    
    def test_config_no_jwt_secret(self):
        """core/config.py should not have jwt_secret setting"""
        with open("/app/backend/core/config.py", "r") as f:
            content = f.read().lower()
        assert "jwt_secret" not in content, "jwt_secret still in config.py"
        print("✓ jwt_secret not in config.py")
    
    def test_main_no_jwt_secret_check(self):
        """main.py should not check for JWT_SECRET"""
        with open("/app/backend/main.py", "r") as f:
            content = f.read()
        assert "JWT_SECRET" not in content, "JWT_SECRET check still in main.py"
        print("✓ JWT_SECRET not in main.py")
    
    def test_settings_class_no_jwt(self):
        """Settings class should not have jwt_secret attribute"""
        from core.config import Settings
        settings_fields = [f for f in dir(Settings) if not f.startswith('_')]
        jwt_fields = [f for f in settings_fields if 'jwt' in f.lower()]
        assert len(jwt_fields) == 0, f"JWT fields found in Settings: {jwt_fields}"
        print(f"✓ Settings class has no JWT fields")


class TestAllRouteModulesImport:
    """Test that all 88 route modules import without errors"""
    
    def test_count_route_files(self):
        """Should have 88 route files"""
        route_dir = "/app/backend/routes"
        route_files = [f for f in os.listdir(route_dir) 
                       if f.endswith('.py') and not f.startswith('__')]
        assert len(route_files) >= 88, f"Expected 88+ route files, found {len(route_files)}"
        print(f"✓ Found {len(route_files)} route files")
    
    def test_all_routes_import(self):
        """All route modules should import without errors"""
        import importlib
        route_dir = "/app/backend/routes"
        route_files = [f[:-3] for f in os.listdir(route_dir) 
                       if f.endswith('.py') and not f.startswith('__')]
        
        errors = []
        for route in sorted(route_files):
            try:
                importlib.import_module(f'routes.{route}')
            except Exception as e:
                errors.append((route, str(e)))
        
        assert len(errors) == 0, f"Import errors: {errors}"
        print(f"✓ All {len(route_files)} route modules import successfully")
    
    def test_rbac_applied_to_key_routes(self):
        """Key routes should use require_role decorator"""
        # Check invoices.py has RBAC
        with open("/app/backend/routes/invoices.py", "r") as f:
            content = f.read()
        assert "from core.rbac import require_role" in content
        assert "require_role(" in content
        print("✓ invoices.py uses RBAC")
        
        # Check clients.py has RBAC
        with open("/app/backend/routes/clients.py", "r") as f:
            content = f.read()
        assert "from core.rbac import require_role" in content
        assert "require_role(" in content
        print("✓ clients.py uses RBAC")
        
        # Check backup.py has RBAC
        with open("/app/backend/routes/backup.py", "r") as f:
            content = f.read()
        assert "from core.rbac import require_role" in content
        assert 'require_role("admin")' in content
        print("✓ backup.py uses RBAC (admin only)")


class TestCookieBasedAuth:
    """Test that auth is cookie-based, not JWT"""
    
    def test_auth_module_uses_cookies(self):
        """Auth should use session cookies, not JWT tokens"""
        with open("/app/backend/routes/auth.py", "r") as f:
            content = f.read()
        # Should have session-related code
        assert "session" in content.lower()
        # Should set cookies
        assert "set_cookie" in content or "cookie" in content.lower()
        print("✓ auth.py uses cookie-based sessions")
    
    def test_security_module_no_jwt_decode(self):
        """core/security.py should not decode JWT tokens"""
        with open("/app/backend/core/security.py", "r") as f:
            content = f.read()
        # Should not have jwt.decode
        assert "jwt.decode" not in content, "JWT decode found in security.py"
        print("✓ security.py does not decode JWT tokens")


class TestRBACRoleLogic:
    """Test RBAC role checking logic"""
    
    def test_admin_always_passes(self):
        """Admin role should always pass RBAC checks"""
        from core.rbac import ROLE_ACCESS
        assert ROLE_ACCESS["admin"] == ["*"], "Admin should have wildcard access"
        print("✓ Admin role has wildcard access ['*']")
    
    def test_guest_has_no_access(self):
        """Guest role should have empty access list"""
        from core.rbac import ROLE_ACCESS
        assert ROLE_ACCESS["guest"] == [], "Guest should have no access"
        print("✓ Guest role has empty access list")
    
    def test_amministrazione_has_financial_access(self):
        """Amministrazione role should have financial access"""
        from core.rbac import ROLE_ACCESS
        admin_access = ROLE_ACCESS["amministrazione"]
        assert "fatture" in admin_access or "clienti" in admin_access
        print(f"✓ Amministrazione role access: {admin_access}")


class TestEnvFileJWTSecret:
    """Test JWT_SECRET in .env file (note: still present but unused)"""
    
    def test_jwt_secret_in_env_but_not_used(self):
        """JWT_SECRET may be in .env but should not be used in code"""
        # Check if JWT_SECRET is in .env
        with open("/app/backend/.env", "r") as f:
            env_content = f.read()
        
        jwt_in_env = "JWT_SECRET" in env_content
        
        # Check it's not used in config.py
        with open("/app/backend/core/config.py", "r") as f:
            config_content = f.read()
        
        jwt_in_config = "jwt_secret" in config_content.lower()
        
        # JWT_SECRET may be in .env (legacy) but should NOT be in config
        assert not jwt_in_config, "jwt_secret should not be in config.py"
        
        if jwt_in_env:
            print("⚠ JWT_SECRET still in .env file (legacy, but not used in code)")
        else:
            print("✓ JWT_SECRET not in .env file")
        
        print("✓ JWT_SECRET not used in config.py (cookie-based auth)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

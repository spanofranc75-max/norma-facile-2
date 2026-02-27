"""
Core Engine API Tests - NormaConfig CRUD, Componenti CRUD, Configure, Calculate, Validate

Tests cover:
1. Auth protection (all endpoints require auth)
2. NormaConfig CRUD (list, create, get, update, delete)
3. NormaConfig seed (creates EN_1090_1, EN_13241, UNI_EN_14351_1)
4. Componenti CRUD (vetri, telai, distanziatori)
5. Componenti seed (8 vetri, 8 telai, 5 distanziatori)
6. Configure endpoint (returns applicable norms and components for product type)
7. Calculate endpoint (Uw calculation with ISO 10077-1 formula)
8. Validate endpoint (runs validation rules from norm config)
9. Uw formula verification: Uw = (Ag*Ug + Af*Uf + lg*Psi) / (Ag + Af)
10. Zone compliance and suggestion generation
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')


@pytest.fixture(scope='module')
def auth_cookie():
    """Returns cookie dict for authenticated requests."""
    return {'session_token': SESSION_TOKEN}


class TestAuthProtection:
    """All Core Engine endpoints require authentication."""
    
    def test_norme_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/engine/norme")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_componenti_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/engine/componenti")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_configure_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/engine/configure", json={"product_type": "finestra"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_calculate_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json={
            "norma_id": "test", "product_type": "finestra",
            "height_mm": 1400, "width_mm": 1200
        })
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_validate_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/engine/validate", json={
            "norma_id": "test", "product_type": "finestra", "specs": {}
        })
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"


class TestNormeSeed:
    """Test seeding standard Italian norms."""
    
    def test_seed_norme(self, auth_cookie):
        """POST /api/engine/norme/seed creates EN_1090_1, EN_13241, UNI_EN_14351_1."""
        r = requests.post(f"{BASE_URL}/api/engine/norme/seed", cookies=auth_cookie)
        assert r.status_code == 200, f"Seed failed: {r.text}"
        data = r.json()
        assert 'message' in data
        assert 'created' in data
        print(f"Norme seed: {data['message']}")
    
    def test_list_norme_after_seed(self, auth_cookie):
        """GET /api/engine/norme returns seeded norms."""
        r = requests.get(f"{BASE_URL}/api/engine/norme?active_only=false", cookies=auth_cookie)
        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()
        assert 'norme' in data
        norma_ids = [n['norma_id'] for n in data['norme']]
        # Check all 3 seeded norms exist
        assert 'EN_1090_1' in norma_ids, f"EN_1090_1 not found in {norma_ids}"
        assert 'EN_13241' in norma_ids, f"EN_13241 not found in {norma_ids}"
        assert 'UNI_EN_14351_1' in norma_ids, f"UNI_EN_14351_1 not found in {norma_ids}"
        print(f"Found {len(data['norme'])} norme: {norma_ids}")


class TestNormeCRUD:
    """Test NormaConfig CRUD operations."""
    
    def test_create_norma(self, auth_cookie):
        """POST /api/engine/norme creates a new norm config."""
        payload = {
            "norma_id": "TEST_NORMA_001",
            "title": "Test Norm for CRUD Testing",
            "standard_ref": "TEST-001",
            "product_types": ["test_product"],
            "required_performances": [
                {"code": "PERF1", "label": "Performance 1", "mandatory": True}
            ],
            "validation_rules": [
                {"rule_id": "R1", "condition": "test_value > 100", "action": "WARN", "message": "Test warning"}
            ],
            "calculation_methods": ["ISO_10077_1"],
            "active": True
        }
        r = requests.post(f"{BASE_URL}/api/engine/norme", json=payload, cookies=auth_cookie)
        assert r.status_code == 201, f"Create failed: {r.text}"
        data = r.json()
        assert data['norma_id'] == 'TEST_NORMA_001'
        assert data['title'] == payload['title']
        assert len(data['required_performances']) == 1
        assert len(data['validation_rules']) == 1
        print(f"Created norma: {data['norma_id']}")
    
    def test_get_norma(self, auth_cookie):
        """GET /api/engine/norme/{norma_id} returns single norm."""
        r = requests.get(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", cookies=auth_cookie)
        assert r.status_code == 200, f"Get failed: {r.text}"
        data = r.json()
        assert data['norma_id'] == 'TEST_NORMA_001'
        assert data['standard_ref'] == 'TEST-001'
    
    def test_update_norma(self, auth_cookie):
        """PUT /api/engine/norme/{norma_id} updates norm config."""
        payload = {
            "title": "Updated Test Norm Title",
            "notes": "Added note via update"
        }
        r = requests.put(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"Update failed: {r.text}"
        data = r.json()
        assert data['title'] == 'Updated Test Norm Title'
        assert data['notes'] == 'Added note via update'
        # Verify update persisted
        r2 = requests.get(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", cookies=auth_cookie)
        data2 = r2.json()
        assert data2['title'] == 'Updated Test Norm Title'
        print(f"Updated norma: {data['norma_id']}")
    
    def test_duplicate_norma_fails(self, auth_cookie):
        """POST with existing norma_id returns 400."""
        payload = {
            "norma_id": "TEST_NORMA_001",
            "title": "Duplicate",
            "standard_ref": "DUP"
        }
        r = requests.post(f"{BASE_URL}/api/engine/norme", json=payload, cookies=auth_cookie)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    
    def test_delete_norma(self, auth_cookie):
        """DELETE /api/engine/norme/{norma_id} removes norm."""
        r = requests.delete(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", cookies=auth_cookie)
        assert r.status_code == 200, f"Delete failed: {r.text}"
        # Verify deleted
        r2 = requests.get(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", cookies=auth_cookie)
        assert r2.status_code == 404, f"Expected 404 after delete, got {r2.status_code}"
        print("Deleted TEST_NORMA_001")


class TestComponentiSeed:
    """Test seeding standard components."""
    
    def test_seed_componenti(self, auth_cookie):
        """POST /api/engine/componenti/seed creates 21 components."""
        r = requests.post(f"{BASE_URL}/api/engine/componenti/seed", cookies=auth_cookie)
        assert r.status_code == 200, f"Seed failed: {r.text}"
        data = r.json()
        assert 'message' in data
        print(f"Componenti seed: {data['message']}")
    
    def test_list_componenti_vetri(self, auth_cookie):
        """GET /api/engine/componenti?tipo=vetro returns 8 vetri."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti?tipo=vetro", cookies=auth_cookie)
        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()
        vetri = data['componenti']
        assert len(vetri) >= 8, f"Expected >= 8 vetri, got {len(vetri)}"
        # Check some vetri have Ug values
        for v in vetri:
            assert 'ug' in v, f"Vetro {v['codice']} missing ug"
            assert v['tipo'] == 'vetro'
        print(f"Found {len(vetri)} vetri with Ug values ranging {min(v['ug'] for v in vetri)}-{max(v['ug'] for v in vetri)}")
    
    def test_list_componenti_telai(self, auth_cookie):
        """GET /api/engine/componenti?tipo=telaio returns 8 telai."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti?tipo=telaio", cookies=auth_cookie)
        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()
        telai = data['componenti']
        assert len(telai) >= 8, f"Expected >= 8 telai, got {len(telai)}"
        for t in telai:
            assert 'uf' in t, f"Telaio {t['codice']} missing uf"
            assert t['tipo'] == 'telaio'
        print(f"Found {len(telai)} telai with Uf values ranging {min(t['uf'] for t in telai)}-{max(t['uf'] for t in telai)}")
    
    def test_list_componenti_distanziatori(self, auth_cookie):
        """GET /api/engine/componenti?tipo=distanziatore returns 5 distanziatori."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti?tipo=distanziatore", cookies=auth_cookie)
        assert r.status_code == 200, f"List failed: {r.text}"
        data = r.json()
        dist = data['componenti']
        assert len(dist) >= 5, f"Expected >= 5 distanziatori, got {len(dist)}"
        for d in dist:
            assert 'psi' in d, f"Distanziatore {d['codice']} missing psi"
            assert d['tipo'] == 'distanziatore'
        print(f"Found {len(dist)} distanziatori with Psi values ranging {min(d['psi'] for d in dist)}-{max(d['psi'] for d in dist)}")


class TestComponentiCRUD:
    """Test Componenti CRUD operations."""
    
    def test_create_componente(self, auth_cookie):
        """POST /api/engine/componenti creates a new component."""
        payload = {
            "codice": "TEST-VETRO-001",
            "label": "Test Glass for CRUD",
            "tipo": "vetro",
            "ug": 2.5,
            "thickness_mm": 24,
            "produttore": "Test Manufacturer"
        }
        r = requests.post(f"{BASE_URL}/api/engine/componenti", json=payload, cookies=auth_cookie)
        assert r.status_code == 201, f"Create failed: {r.text}"
        data = r.json()
        assert data['codice'] == 'TEST-VETRO-001'
        assert data['ug'] == 2.5
        assert 'comp_id' in data
        print(f"Created component: {data['comp_id']}")
        return data['comp_id']
    
    def test_get_componente(self, auth_cookie):
        """GET /api/engine/componenti/{comp_id} returns single component."""
        # First get list to find our test component
        r = requests.get(f"{BASE_URL}/api/engine/componenti?q=TEST-VETRO-001", cookies=auth_cookie)
        assert r.status_code == 200
        comps = r.json()['componenti']
        if comps:
            comp_id = comps[0]['comp_id']
            r2 = requests.get(f"{BASE_URL}/api/engine/componenti/{comp_id}", cookies=auth_cookie)
            assert r2.status_code == 200
            data = r2.json()
            assert data['codice'] == 'TEST-VETRO-001'
    
    def test_update_componente(self, auth_cookie):
        """PUT /api/engine/componenti/{comp_id} updates component."""
        # Find our test component
        r = requests.get(f"{BASE_URL}/api/engine/componenti?q=TEST-VETRO-001", cookies=auth_cookie)
        comps = r.json()['componenti']
        if comps:
            comp_id = comps[0]['comp_id']
            payload = {"label": "Updated Test Glass", "ug": 2.0}
            r2 = requests.put(f"{BASE_URL}/api/engine/componenti/{comp_id}", json=payload, cookies=auth_cookie)
            assert r2.status_code == 200
            data = r2.json()
            assert data['label'] == 'Updated Test Glass'
            assert data['ug'] == 2.0
    
    def test_delete_componente(self, auth_cookie):
        """DELETE /api/engine/componenti/{comp_id} removes component."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti?q=TEST-VETRO-001", cookies=auth_cookie)
        comps = r.json()['componenti']
        if comps:
            comp_id = comps[0]['comp_id']
            r2 = requests.delete(f"{BASE_URL}/api/engine/componenti/{comp_id}", cookies=auth_cookie)
            assert r2.status_code == 200
            # Verify deleted
            r3 = requests.get(f"{BASE_URL}/api/engine/componenti/{comp_id}", cookies=auth_cookie)
            assert r3.status_code == 404
            print(f"Deleted component {comp_id}")


class TestConfigure:
    """Test product configuration endpoint."""
    
    def test_configure_finestra(self, auth_cookie):
        """POST /api/engine/configure for finestra returns UNI_EN_14351_1 norm."""
        r = requests.post(f"{BASE_URL}/api/engine/configure", json={"product_type": "finestra"}, cookies=auth_cookie)
        assert r.status_code == 200, f"Configure failed: {r.text}"
        data = r.json()
        assert data['product_type'] == 'finestra'
        assert 'norme' in data
        norma_ids = [n['norma_id'] for n in data['norme']]
        assert 'UNI_EN_14351_1' in norma_ids, f"Expected UNI_EN_14351_1, got {norma_ids}"
        assert data['has_thermal_calc'] == True, "Finestra should have thermal calc"
        assert 'zone_limits' in data
        assert 'componenti' in data
        assert 'vetri' in data['componenti']
        assert 'telai' in data['componenti']
        assert 'distanziatori' in data['componenti']
        print(f"Configure finestra: {len(data['norme'])} norme, {len(data['componenti']['vetri'])} vetri")
    
    def test_configure_cancello(self, auth_cookie):
        """POST /api/engine/configure for cancello returns EN_13241 norm."""
        r = requests.post(f"{BASE_URL}/api/engine/configure", json={"product_type": "cancello"}, cookies=auth_cookie)
        assert r.status_code == 200
        data = r.json()
        norma_ids = [n['norma_id'] for n in data['norme']]
        assert 'EN_13241' in norma_ids, f"Expected EN_13241, got {norma_ids}"
        print(f"Configure cancello: {norma_ids}")
    
    def test_configure_tettoia(self, auth_cookie):
        """POST /api/engine/configure for tettoia returns EN_1090_1 norm."""
        r = requests.post(f"{BASE_URL}/api/engine/configure", json={"product_type": "tettoia"}, cookies=auth_cookie)
        assert r.status_code == 200
        data = r.json()
        norma_ids = [n['norma_id'] for n in data['norme']]
        assert 'EN_1090_1' in norma_ids, f"Expected EN_1090_1, got {norma_ids}"
        print(f"Configure tettoia: {norma_ids}")


class TestCalculate:
    """Test Uw calculation endpoint with ISO 10077-1 formula."""
    
    def test_calculate_uw_basic(self, auth_cookie):
        """POST /api/engine/calculate computes Uw correctly."""
        # First get components to use their IDs
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        vetri = [c for c in comps if c['tipo'] == 'vetro']
        telai = [c for c in comps if c['tipo'] == 'telaio']
        dist = [c for c in comps if c['tipo'] == 'distanziatore']
        
        if not vetri or not telai or not dist:
            pytest.skip("No components found, run seed first")
        
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": vetri[0]['comp_id'],
            "telaio_id": telai[0]['comp_id'],
            "distanziatore_id": dist[0]['comp_id'],
            "zona_climatica": "E"
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        assert r.status_code == 200, f"Calculate failed: {r.text}"
        data = r.json()
        
        # Check result structure
        assert 'results' in data
        assert 'thermal' in data['results']
        thermal = data['results']['thermal']
        assert 'uw' in thermal
        assert 'ag' in thermal  # Glass area
        assert 'af' in thermal  # Frame area
        assert 'lg' in thermal  # Perimeter
        assert 'zone_compliance' in thermal
        
        # Check zone compliance for all 6 zones
        zones = thermal['zone_compliance']
        assert 'A' in zones
        assert 'B' in zones
        assert 'C' in zones
        assert 'D' in zones
        assert 'E' in zones
        assert 'F' in zones
        
        print(f"Calculated Uw={thermal['uw']} W/m²K")
        print(f"  Glass area: {thermal['ag']} m²")
        print(f"  Frame area: {thermal['af']} m²")
        print(f"  Perimeter: {thermal['lg']} m")
    
    def test_calculate_uw_formula_verification(self, auth_cookie):
        """Verify Uw = (Ag*Ug + Af*Uf + lg*Psi) / (Ag + Af) formula."""
        # Use known values to verify formula
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        
        # Find specific components
        vetro = next((c for c in comps if c.get('codice') == 'V-DV-ARIA'), None)
        telaio = next((c for c in comps if c.get('codice') == 'T-ACC-STD'), None)
        dist = next((c for c in comps if c.get('codice') == 'D-ALU'), None)
        
        if not all([vetro, telaio, dist]):
            pytest.skip("Required seed components not found")
        
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": vetro['comp_id'],
            "telaio_id": telaio['comp_id'],
            "distanziatore_id": dist['comp_id'],
            "zona_climatica": "E"
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        data = r.json()
        thermal = data['results']['thermal']
        
        # Manually calculate expected Uw
        h_m = 1400 / 1000
        w_m = 1200 / 1000
        fw = 80 / 1000
        
        total_area = h_m * w_m
        glass_h = h_m - 2 * fw
        glass_w = w_m - 2 * fw
        ag = glass_h * glass_w  # Glass area
        af = total_area - ag     # Frame area
        lg = 2 * (glass_h + glass_w)  # Glass perimeter
        
        ug = vetro['ug']  # 2.8
        uf = telaio['uf']  # 5.9
        psi = dist['psi']  # 0.08
        
        expected_uw = round((ag * ug + af * uf + lg * psi) / (ag + af), 2)
        
        assert thermal['uw'] == expected_uw, f"Uw mismatch: got {thermal['uw']}, expected {expected_uw}"
        print(f"Formula verification PASSED: Uw={thermal['uw']} (expected {expected_uw})")
    
    def test_calculate_zone_compliance_limits(self, auth_cookie):
        """Verify zone limits: A=2.6, B=2.6, C=1.75, D=1.67, E=1.3, F=1.0."""
        # Get components
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        vetri = [c for c in comps if c['tipo'] == 'vetro']
        telai = [c for c in comps if c['tipo'] == 'telaio']
        dist = [c for c in comps if c['tipo'] == 'distanziatore']
        
        if not vetri or not telai or not dist:
            pytest.skip("No components found")
        
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": vetri[0]['comp_id'],
            "telaio_id": telai[0]['comp_id'],
            "distanziatore_id": dist[0]['comp_id'],
            "zona_climatica": "E"
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        zones = r.json()['results']['thermal']['zone_compliance']
        
        # Check limits match climate_zones.py
        expected_limits = {'A': 2.6, 'B': 2.6, 'C': 1.75, 'D': 1.67, 'E': 1.3, 'F': 1.0}
        for zone, limit in expected_limits.items():
            assert zones[zone]['limit'] == limit, f"Zone {zone} limit mismatch: got {zones[zone]['limit']}, expected {limit}"
        print(f"Zone limits verified: {expected_limits}")


class TestValidation:
    """Test validation rules engine."""
    
    def test_validation_block_ce_marking(self, auth_cookie):
        """Height > 4000 blocks CE marking for EN_13241 cancello."""
        # First get some components
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        vetri = [c for c in comps if c['tipo'] == 'vetro']
        telai = [c for c in comps if c['tipo'] == 'telaio']
        dist = [c for c in comps if c['tipo'] == 'distanziatore']
        
        payload = {
            "norma_id": "EN_13241",
            "product_type": "cancello",
            "height_mm": 4500,  # > 4000 triggers BLOCK_CE_MARKING
            "width_mm": 2000,
            "frame_width_mm": 80,
            "vetro_id": vetri[0]['comp_id'] if vetri else None,
            "telaio_id": telai[0]['comp_id'] if telai else None,
            "distanziatore_id": dist[0]['comp_id'] if dist else None,
            "zona_climatica": "E"
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        assert r.status_code == 200
        data = r.json()
        
        # Should be non-compliant due to height rule
        assert data['compliant'] == False, "Expected non-compliant due to height > 4000"
        assert data['validation']['blocked'] == True, "Expected blocked = True"
        errors = data['validation']['errors']
        assert len(errors) > 0, "Expected validation errors"
        # Check error mentions height calculation requirement
        error_messages = [e['message'] for e in errors]
        height_error = any('4m' in m or '4000' in m or 'calcolo strutturale' in m.lower() for m in error_messages)
        assert height_error, f"Expected height-related error, got: {error_messages}"
        print(f"BLOCK_CE_MARKING rule fired: {errors}")
    
    def test_validation_warning_rule(self, auth_cookie):
        """Height > 2500 triggers warning for EN_13241 cancello."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        vetri = [c for c in comps if c['tipo'] == 'vetro']
        telai = [c for c in comps if c['tipo'] == 'telaio']
        dist = [c for c in comps if c['tipo'] == 'distanziatore']
        
        payload = {
            "norma_id": "EN_13241",
            "product_type": "cancello",
            "height_mm": 3000,  # > 2500 but < 4000 triggers WARN only
            "width_mm": 2000,
            "frame_width_mm": 80,
            "vetro_id": vetri[0]['comp_id'] if vetri else None,
            "telaio_id": telai[0]['comp_id'] if telai else None,
            "distanziatore_id": dist[0]['comp_id'] if dist else None,
            "zona_climatica": "E"
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        data = r.json()
        
        # Should have warning but still be compliant (no BLOCK)
        warnings = data['validation']['warnings']
        assert len(warnings) > 0, "Expected validation warnings"
        warning_messages = [w['message'] for w in warnings]
        height_warning = any('2.5m' in m or '2500' in m or 'cerniere' in m.lower() for m in warning_messages)
        assert height_warning, f"Expected height warning, got: {warning_messages}"
        print(f"Warning rule fired: {warnings}")


class TestSuggestions:
    """Test suggestion generation when Uw exceeds zone limit."""
    
    def test_suggestions_generated_when_uw_exceeds_limit(self, auth_cookie):
        """Using poor glass/frame should generate upgrade suggestions."""
        r = requests.get(f"{BASE_URL}/api/engine/componenti", cookies=auth_cookie)
        comps = r.json()['componenti']
        
        # Find poor performing components (high Ug/Uf/Psi)
        vetro = next((c for c in comps if c.get('codice') == 'V-SING-4'), None)  # Ug=5.8
        telaio = next((c for c in comps if c.get('codice') == 'T-FERRO'), None)  # Uf=7.0
        dist = next((c for c in comps if c.get('codice') == 'D-ALU'), None)  # Psi=0.08
        
        if not all([vetro, telaio, dist]):
            pytest.skip("Required poor-performing components not found")
        
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "height_mm": 1400,
            "width_mm": 1200,
            "frame_width_mm": 80,
            "vetro_id": vetro['comp_id'],
            "telaio_id": telaio['comp_id'],
            "distanziatore_id": dist['comp_id'],
            "zona_climatica": "F"  # Most restrictive zone (limit 1.0)
        }
        r = requests.post(f"{BASE_URL}/api/engine/calculate", json=payload, cookies=auth_cookie)
        data = r.json()
        thermal = data['results']['thermal']
        
        # With Ug=5.8, Uf=7.0, we should exceed zone F limit of 1.0
        assert thermal['uw'] > 1.0, f"Expected Uw > 1.0, got {thermal['uw']}"
        
        # Should have suggestions for improvement
        suggestions = data.get('suggestions', [])
        assert len(suggestions) > 0, "Expected suggestions when Uw exceeds limit"
        
        suggestion_types = [s['type'] for s in suggestions]
        assert 'UPGRADE_GLASS' in suggestion_types, f"Expected UPGRADE_GLASS suggestion, got: {suggestion_types}"
        print(f"Uw={thermal['uw']} exceeds zone F limit. Suggestions: {suggestions}")


class TestValidateEndpoint:
    """Test standalone validate endpoint."""
    
    def test_validate_missing_mandatory_fields(self, auth_cookie):
        """Validate returns field errors for missing mandatory fields."""
        payload = {
            "norma_id": "UNI_EN_14351_1",
            "product_type": "finestra",
            "specs": {},  # Missing required fields
            "calculated_values": {}
        }
        r = requests.post(f"{BASE_URL}/api/engine/validate", json=payload, cookies=auth_cookie)
        assert r.status_code == 200
        data = r.json()
        
        # Should have field errors for mandatory fields
        assert 'field_errors' in data
        assert len(data['field_errors']) > 0, "Expected field errors for missing mandatory fields"
        assert data['compliant'] == False, "Should not be compliant with missing fields"
        print(f"Validation field errors: {data['field_errors']}")


# Cleanup test data
@pytest.fixture(scope='module', autouse=True)
def cleanup(auth_cookie):
    """Cleanup test data after all tests."""
    yield
    # Delete test norm if exists
    try:
        requests.delete(f"{BASE_URL}/api/engine/norme/TEST_NORMA_001", cookies=auth_cookie)
    except:
        pass
    # Delete test component if exists
    r = requests.get(f"{BASE_URL}/api/engine/componenti?q=TEST-VETRO-001", cookies=auth_cookie)
    if r.status_code == 200:
        for c in r.json().get('componenti', []):
            try:
                requests.delete(f"{BASE_URL}/api/engine/componenti/{c['comp_id']}", cookies=auth_cookie)
            except:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

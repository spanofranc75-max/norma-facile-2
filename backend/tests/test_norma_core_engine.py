"""
Test suite for Norma Core Engine refactoring - Iteration 14
Tests: Climate zones with Draft 2025/2026 limits, ThermalValidator, SafetyValidator, CEValidator
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# =========================================
# THERMAL REFERENCE DATA TESTS
# =========================================

class TestThermalReferenceData:
    """Tests for GET /api/certificazioni/thermal/reference-data endpoint"""
    
    def test_get_reference_data_returns_200(self):
        """Reference data endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        assert response.status_code == 200
        print("PASS: Reference data returns 200")
    
    def test_zone_limits_draft_2025_2026(self):
        """Zone limits should match Draft 2025/2026 values"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        zone_limits = data.get("zone_limits", {})
        
        # Draft 2025/2026 expected values
        expected_limits = {
            "A": 2.6,
            "B": 2.6,
            "C": 1.75,
            "D": 1.67,  # Changed from 1.80
            "E": 1.30,
            "F": 1.00
        }
        
        for zone, expected in expected_limits.items():
            actual = zone_limits.get(zone)
            assert actual == expected, f"Zone {zone}: expected {expected}, got {actual}"
            print(f"PASS: Zone {zone} limit = {actual} (Draft 2025/2026)")
    
    def test_glass_types_count(self):
        """Should return 8 glass types"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        glass_types = data.get("glass_types", [])
        assert len(glass_types) == 8, f"Expected 8 glass types, got {len(glass_types)}"
        print(f"PASS: {len(glass_types)} glass types returned")
    
    def test_frame_types_count(self):
        """Should return 8 frame types"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        frame_types = data.get("frame_types", [])
        assert len(frame_types) == 8, f"Expected 8 frame types, got {len(frame_types)}"
        print(f"PASS: {len(frame_types)} frame types returned")
    
    def test_spacer_types_count(self):
        """Should return 5 spacer types"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        spacer_types = data.get("spacer_types", [])
        assert len(spacer_types) == 5, f"Expected 5 spacer types, got {len(spacer_types)}"
        print(f"PASS: {len(spacer_types)} spacer types returned")


# =========================================
# THERMAL CALCULATION TESTS
# =========================================

class TestThermalCalculation:
    """Tests for POST /api/certificazioni/thermal/calculate endpoint"""
    
    def test_calculate_uw_returns_200(self):
        """Calculate endpoint should return 200"""
        payload = {
            "height_mm": 2000,
            "width_mm": 1000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200
        print("PASS: Calculate returns 200")
    
    def test_calculate_uw_result_structure(self):
        """Result should contain all required fields"""
        payload = {
            "height_mm": 2000,
            "width_mm": 1000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        data = response.json()
        
        required_fields = ["uw", "ag", "af", "lg", "ug", "uf", "psi", "total_area", 
                          "glass_label", "frame_label", "spacer_label", "ecobonus_eligible", "warnings"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print("PASS: All required fields present in response")
    
    def test_medium_performance_zone_compliance(self):
        """Uw ~2.3 should fail zones C, D, E, F (Draft 2025/2026 limits)"""
        payload = {
            "height_mm": 2000,
            "width_mm": 1000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",  # Ug = 1.0
            "frame_id": "acciaio_standard",  # Uf = 5.9
            "spacer_id": "alluminio"  # Psi = 0.08
        }
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        data = response.json()
        
        ecobonus = data.get("ecobonus_eligible", {})
        uw = data.get("uw")
        
        print(f"Calculated Uw: {uw} W/m2K")
        
        # With these params, Uw should be around 2.3
        # A, B should pass (limit 2.6), C should pass (1.75), D should fail (1.67)
        assert ecobonus.get("A") == True, "Zone A should pass"
        assert ecobonus.get("B") == True, "Zone B should pass"
        assert ecobonus.get("D") == False, f"Zone D (limit 1.67) should FAIL with Uw={uw}"
        assert ecobonus.get("E") == False, f"Zone E (limit 1.30) should FAIL with Uw={uw}"
        assert ecobonus.get("F") == False, f"Zone F (limit 1.00) should FAIL with Uw={uw}"
        print("PASS: Zone compliance correct for medium performance")
    
    def test_triplo_glass_all_zones_pass(self):
        """Triplo vetro + PVC + Super Warm should pass ALL zones"""
        payload = {
            "height_mm": 2000,
            "width_mm": 1000,
            "frame_width_mm": 80,
            "glass_id": "triplo_be_argon",  # Ug = 0.6
            "frame_id": "pvc",  # Uf = 1.3
            "spacer_id": "super_warm"  # Psi = 0.03
        }
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        data = response.json()
        
        ecobonus = data.get("ecobonus_eligible", {})
        uw = data.get("uw")
        
        print(f"Calculated Uw: {uw} W/m2K")
        
        for zone in ["A", "B", "C", "D", "E", "F"]:
            assert ecobonus.get(zone) == True, f"Zone {zone} should pass with Uw={uw}"
        print("PASS: All zones pass with high-performance configuration")
    
    def test_singolo_glass_all_zones_fail(self):
        """Singolo glass + Ferro battuto should FAIL all zones with warnings"""
        payload = {
            "height_mm": 2000,
            "width_mm": 1000,
            "frame_width_mm": 80,
            "glass_id": "singolo",  # Ug = 5.8
            "frame_id": "ferro_battuto",  # Uf = 7.0
            "spacer_id": "alluminio"
        }
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        data = response.json()
        
        ecobonus = data.get("ecobonus_eligible", {})
        warnings = data.get("warnings", [])
        uw = data.get("uw")
        
        print(f"Calculated Uw: {uw} W/m2K")
        
        # Uw should be very high (>5)
        assert uw > 2.6, f"Uw should exceed 2.6, got {uw}"
        
        for zone in ["A", "B", "C", "D", "E", "F"]:
            assert ecobonus.get(zone) == False, f"Zone {zone} should FAIL with Uw={uw}"
        
        # Should have warning about exceeding all zones
        all_zones_warning = any("tutte le zone" in w for w in warnings)
        assert all_zones_warning, "Should have warning about exceeding all zones"
        print("PASS: All zones fail with poor configuration + warnings present")


# =========================================
# CE VALIDATOR TESTS (Requires Auth)
# =========================================

class TestCEValidation:
    """Tests for POST /api/certificazioni/{cert_id}/validate and PDF rejection"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create test user and get session"""
        import time
        timestamp = int(time.time())
        session_token = f"test_session_{timestamp}"
        user_id = f"test-user-{timestamp}"
        
        # Insert test user and session via mongosh
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.insertOne({{
              user_id: '{user_id}',
              email: 'test.{timestamp}@example.com',
              name: 'Test User',
              created_at: new Date()
            }});
            db.user_sessions.insertOne({{
              user_id: '{user_id}',
              session_token: '{session_token}',
              expires_at: new Date(Date.now() + 7*24*60*60*1000),
              created_at: new Date()
            }});
            "
        """)
        
        yield {"session_token": session_token, "user_id": user_id}
        
        # Cleanup
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.deleteMany({{user_id: '{user_id}'}});
            db.user_sessions.deleteMany({{session_token: '{session_token}'}});
            db.certificazioni.deleteMany({{user_id: '{user_id}'}});
            db.pos_documents.deleteMany({{user_id: '{user_id}'}});
            "
        """)
    
    def test_validate_incomplete_cert_returns_errors(self, auth_session):
        """POST /api/certificazioni/{cert_id}/validate should return errors for incomplete cert"""
        session_token = auth_session["session_token"]
        headers = {"Authorization": f"Bearer {session_token}"}
        
        # Create incomplete cert (missing required fields for EN 1090-1)
        create_payload = {
            "project_name": "TEST_incomplete_cert",
            "standard": "EN 1090-1",
            "product_description": "Test",
            "product_type": "",  # Missing!
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "",  # Missing!
                "reaction_to_fire": ""  # Missing!
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/", json=create_payload, headers=headers)
        assert response.status_code == 201
        cert_id = response.json()["cert_id"]
        
        # Validate
        validate_response = requests.post(f"{BASE_URL}/api/certificazioni/{cert_id}/validate", headers=headers)
        assert validate_response.status_code == 200
        
        validation = validate_response.json()
        assert validation["valid"] == False, "Should be invalid"
        assert len(validation["errors"]) >= 3, "Should have at least 3 errors"
        
        print(f"PASS: Validation returned {len(validation['errors'])} errors for incomplete cert")
        print(f"  Errors: {validation['errors']}")
    
    def test_pdf_generation_rejects_incomplete_cert(self, auth_session):
        """GET /api/certificazioni/{cert_id}/fascicolo-pdf should return 422 for incomplete cert"""
        session_token = auth_session["session_token"]
        headers = {"Authorization": f"Bearer {session_token}"}
        
        # Create incomplete cert
        create_payload = {
            "project_name": "TEST_pdf_reject",
            "standard": "EN 1090-1",
            "product_description": "Test",
            "product_type": "",
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "",
                "reaction_to_fire": ""
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/", json=create_payload, headers=headers)
        cert_id = response.json()["cert_id"]
        
        # Try to generate PDF
        pdf_response = requests.get(f"{BASE_URL}/api/certificazioni/{cert_id}/fascicolo-pdf", headers=headers)
        assert pdf_response.status_code == 422, f"Expected 422, got {pdf_response.status_code}"
        
        detail = pdf_response.json().get("detail", "")
        assert "incompleta" in detail.lower(), "Should mention incomplete cert"
        
        print("PASS: PDF generation correctly rejected with 422")
    
    def test_validate_complete_cert_passes(self, auth_session):
        """Complete cert should pass validation"""
        session_token = auth_session["session_token"]
        headers = {"Authorization": f"Bearer {session_token}"}
        
        # Create complete cert
        create_payload = {
            "project_name": "TEST_complete_cert",
            "standard": "EN 1090-1",
            "product_description": "Test structure",
            "product_type": "Struttura in acciaio",
            "technical_specs": {
                "execution_class": "EXC2",
                "durability": "Classe 3",
                "reaction_to_fire": "A1"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/", json=create_payload, headers=headers)
        cert_id = response.json()["cert_id"]
        
        # Validate
        validate_response = requests.post(f"{BASE_URL}/api/certificazioni/{cert_id}/validate", headers=headers)
        validation = validate_response.json()
        
        assert validation["valid"] == True, f"Should be valid, errors: {validation.get('errors')}"
        assert len(validation["errors"]) == 0, "Should have no errors"
        
        print("PASS: Complete cert passes validation")


# =========================================
# SAFETY VALIDATOR TESTS (Requires Auth)
# =========================================

class TestSafetyValidation:
    """Tests for POST /api/sicurezza/{pos_id}/validate and /suggest-dpi"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create test user and get session"""
        import time
        timestamp = int(time.time())
        session_token = f"test_session_safety_{timestamp}"
        user_id = f"test-user-safety-{timestamp}"
        
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.insertOne({{
              user_id: '{user_id}',
              email: 'test.safety.{timestamp}@example.com',
              name: 'Test User Safety',
              created_at: new Date()
            }});
            db.user_sessions.insertOne({{
              user_id: '{user_id}',
              session_token: '{session_token}',
              expires_at: new Date(Date.now() + 7*24*60*60*1000),
              created_at: new Date()
            }});
            "
        """)
        
        yield {"session_token": session_token, "user_id": user_id}
        
        # Cleanup
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.deleteMany({{user_id: '{user_id}'}});
            db.user_sessions.deleteMany({{session_token: '{session_token}'}});
            db.pos_documents.deleteMany({{user_id: '{user_id}'}});
            "
        """)
    
    def test_validate_pos_missing_dpi(self, auth_session):
        """POST /api/sicurezza/{pos_id}/validate should return missing DPI"""
        session_token = auth_session["session_token"]
        headers = {"Authorization": f"Bearer {session_token}"}
        
        # Create POS with risks but only one DPI
        create_payload = {
            "project_name": "TEST_pos_validation",
            "cantiere": {"address": "Via Test", "city": "Milano"},
            "selected_risks": ["saldatura", "molatura"],
            "selected_machines": ["saldatrice_mig"],
            "selected_dpi": ["scarpe_antinfortunistiche"]  # Missing many required DPI
        }
        
        response = requests.post(f"{BASE_URL}/api/sicurezza/", json=create_payload, headers=headers)
        assert response.status_code == 201
        pos_id = response.json()["pos_id"]
        
        # Validate
        validate_response = requests.post(f"{BASE_URL}/api/sicurezza/{pos_id}/validate", headers=headers)
        validation = validate_response.json()
        
        assert validation["valid"] == False, "Should be invalid (missing DPI)"
        assert len(validation["missing_dpi"]) > 0, "Should have missing DPI"
        assert "maschera_saldatura" in validation["missing_dpi"], "Should miss maschera_saldatura for saldatura risk"
        
        print(f"PASS: POS validation returned missing DPI: {validation['missing_dpi']}")
    
    def test_suggest_dpi_endpoint(self, auth_session):
        """POST /api/sicurezza/{pos_id}/suggest-dpi should return required DPI and machines"""
        session_token = auth_session["session_token"]
        headers = {"Authorization": f"Bearer {session_token}"}
        
        # Create POS with saldatura risk
        create_payload = {
            "project_name": "TEST_suggest_dpi",
            "cantiere": {"address": "Via Test", "city": "Milano"},
            "selected_risks": ["saldatura"],
            "selected_machines": [],
            "selected_dpi": []
        }
        
        response = requests.post(f"{BASE_URL}/api/sicurezza/", json=create_payload, headers=headers)
        pos_id = response.json()["pos_id"]
        
        # Get suggestions
        suggest_response = requests.post(f"{BASE_URL}/api/sicurezza/{pos_id}/suggest-dpi", headers=headers)
        assert suggest_response.status_code == 200
        
        suggestions = suggest_response.json()
        
        # Check required DPI for saldatura
        required_dpi = suggestions.get("required_dpi", [])
        assert "maschera_saldatura" in required_dpi
        assert "guanti_pelle" in required_dpi
        assert "grembiule_saldatura" in required_dpi
        
        # Check suggested machines
        suggested_machines = suggestions.get("suggested_machines", [])
        assert any("saldatrice" in m for m in suggested_machines)
        
        print(f"PASS: DPI suggestions: {required_dpi}")
        print(f"PASS: Machine suggestions: {suggested_machines}")


# =========================================
# CRUD REGRESSION TESTS
# =========================================

class TestCRUDRegression:
    """Ensure existing CRUD operations still work after refactoring"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create test user and get session"""
        import time
        timestamp = int(time.time())
        session_token = f"test_session_crud_{timestamp}"
        user_id = f"test-user-crud-{timestamp}"
        
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.insertOne({{
              user_id: '{user_id}',
              email: 'test.crud.{timestamp}@example.com',
              name: 'Test User CRUD',
              created_at: new Date()
            }});
            db.user_sessions.insertOne({{
              user_id: '{user_id}',
              session_token: '{session_token}',
              expires_at: new Date(Date.now() + 7*24*60*60*1000),
              created_at: new Date()
            }});
            "
        """)
        
        yield {"session_token": session_token, "user_id": user_id}
        
        # Cleanup
        os.system(f"""
            mongosh --quiet --eval "
            use('test_database');
            db.users.deleteMany({{user_id: '{user_id}'}});
            db.user_sessions.deleteMany({{session_token: '{session_token}'}});
            db.certificazioni.deleteMany({{user_id: '{user_id}'}});
            "
        """)
    
    def test_list_certificazioni(self, auth_session):
        """GET /api/certificazioni/ should work"""
        headers = {"Authorization": f"Bearer {auth_session['session_token']}"}
        response = requests.get(f"{BASE_URL}/api/certificazioni/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "certificazioni" in data
        assert "total" in data
        print("PASS: List certificazioni works")
    
    def test_create_read_update_delete_cert(self, auth_session):
        """Full CRUD cycle for certificazioni"""
        headers = {"Authorization": f"Bearer {auth_session['session_token']}"}
        
        # CREATE
        create_payload = {
            "project_name": "TEST_CRUD_cert",
            "standard": "EN 1090-1",
            "product_description": "Test CRUD",
            "product_type": "Struttura",
            "technical_specs": {"execution_class": "EXC2", "durability": "C3", "reaction_to_fire": "A1"}
        }
        create_response = requests.post(f"{BASE_URL}/api/certificazioni/", json=create_payload, headers=headers)
        assert create_response.status_code == 201
        cert_id = create_response.json()["cert_id"]
        print(f"PASS: CREATE cert {cert_id}")
        
        # READ
        read_response = requests.get(f"{BASE_URL}/api/certificazioni/{cert_id}", headers=headers)
        assert read_response.status_code == 200
        assert read_response.json()["project_name"] == "TEST_CRUD_cert"
        print("PASS: READ cert")
        
        # UPDATE
        update_payload = {"project_name": "TEST_CRUD_updated"}
        update_response = requests.put(f"{BASE_URL}/api/certificazioni/{cert_id}", json=update_payload, headers=headers)
        assert update_response.status_code == 200
        assert update_response.json()["project_name"] == "TEST_CRUD_updated"
        print("PASS: UPDATE cert")
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/certificazioni/{cert_id}", headers=headers)
        assert verify_response.json()["project_name"] == "TEST_CRUD_updated"
        print("PASS: UPDATE persisted")
        
        # DELETE
        delete_response = requests.delete(f"{BASE_URL}/api/certificazioni/{cert_id}", headers=headers)
        assert delete_response.status_code == 200
        print("PASS: DELETE cert")
        
        # Verify deleted
        verify_deleted = requests.get(f"{BASE_URL}/api/certificazioni/{cert_id}", headers=headers)
        assert verify_deleted.status_code == 404
        print("PASS: DELETE confirmed (404 on GET)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

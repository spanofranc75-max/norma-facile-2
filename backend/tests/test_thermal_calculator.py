"""
Thermal Calculator (Uw) Tests - EN ISO 10077-1
Tests for the Smart CE Calculator thermal transmittance calculation endpoints:
- GET /api/certificazioni/thermal/reference-data - Glass/frame/spacer types and zone limits
- POST /api/certificazioni/thermal/calculate - Uw calculation with ecobonus eligibility
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestThermalReferenceData:
    """Test GET /api/certificazioni/thermal/reference-data - Public endpoint"""
    
    def test_reference_data_returns_200(self):
        """Reference data endpoint is public and returns 200"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/certificazioni/thermal/reference-data returns 200")
    
    def test_reference_data_contains_glass_types(self):
        """Verify glass_types are returned with correct structure"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        assert "glass_types" in data, "Response should contain 'glass_types'"
        assert len(data["glass_types"]) == 8, f"Expected 8 glass types, got {len(data['glass_types'])}"
        
        # Verify structure
        glass = data["glass_types"][0]
        assert "id" in glass, "Glass should have 'id'"
        assert "label" in glass, "Glass should have 'label'"
        assert "ug" in glass, "Glass should have 'ug' (U-value)"
        assert "thickness_mm" in glass, "Glass should have 'thickness_mm'"
        print(f"PASS: Returns 8 glass types with correct structure")
    
    def test_reference_data_contains_frame_types(self):
        """Verify frame_types are returned with correct structure"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        assert "frame_types" in data, "Response should contain 'frame_types'"
        assert len(data["frame_types"]) == 8, f"Expected 8 frame types, got {len(data['frame_types'])}"
        
        # Verify structure
        frame = data["frame_types"][0]
        assert "id" in frame, "Frame should have 'id'"
        assert "label" in frame, "Frame should have 'label'"
        assert "uf" in frame, "Frame should have 'uf' (U-value)"
        print(f"PASS: Returns 8 frame types with correct structure")
    
    def test_reference_data_contains_spacer_types(self):
        """Verify spacer_types are returned with correct structure"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        assert "spacer_types" in data, "Response should contain 'spacer_types'"
        assert len(data["spacer_types"]) == 5, f"Expected 5 spacer types, got {len(data['spacer_types'])}"
        
        # Verify structure
        spacer = data["spacer_types"][0]
        assert "id" in spacer, "Spacer should have 'id'"
        assert "label" in spacer, "Spacer should have 'label'"
        assert "psi" in spacer, "Spacer should have 'psi' (thermal transmittance)"
        print(f"PASS: Returns 5 spacer types with correct structure")
    
    def test_reference_data_contains_zone_limits(self):
        """Verify zone_limits for ecobonus eligibility"""
        response = requests.get(f"{BASE_URL}/api/certificazioni/thermal/reference-data")
        data = response.json()
        
        assert "zone_limits" in data, "Response should contain 'zone_limits'"
        zones = data["zone_limits"]
        
        # Verify all Italian climate zones A-F
        expected_zones = {"A": 3.2, "B": 3.2, "C": 2.1, "D": 1.8, "E": 1.3, "F": 1.0}
        for zone, limit in expected_zones.items():
            assert zone in zones, f"Zone {zone} should be present"
            assert zones[zone] == limit, f"Zone {zone} limit should be {limit}, got {zones[zone]}"
        
        print(f"PASS: Zone limits correct for all 6 Italian climate zones")


class TestThermalCalculation:
    """Test POST /api/certificazioni/thermal/calculate - Public endpoint"""
    
    def test_calculate_uw_basic(self):
        """Calculate Uw with default parameters"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify response structure
        assert "uw" in data, "Response should contain 'uw'"
        assert "ag" in data, "Response should contain 'ag' (glass area)"
        assert "af" in data, "Response should contain 'af' (frame area)"
        assert "lg" in data, "Response should contain 'lg' (glass perimeter)"
        assert "ug" in data, "Response should contain 'ug'"
        assert "uf" in data, "Response should contain 'uf'"
        assert "psi" in data, "Response should contain 'psi'"
        assert "total_area" in data, "Response should contain 'total_area'"
        assert "ecobonus_eligible" in data, "Response should contain 'ecobonus_eligible'"
        assert "warnings" in data, "Response should contain 'warnings'"
        
        # Verify calculation is reasonable
        assert 1.0 <= data["uw"] <= 2.5, f"Uw should be between 1.0 and 2.5, got {data['uw']}"
        assert data["total_area"] == 6.3, f"Total area should be 6.3 m2, got {data['total_area']}"
        
        print(f"PASS: Basic Uw calculation returned {data['uw']} W/m2K")
    
    def test_calculate_uw_good_thermal_performance(self):
        """Calculate Uw with high-performance components (should pass Zone E)"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "triplo_be_argon",  # Best glass (Ug=0.6)
            "frame_id": "pvc",               # Best frame (Uf=1.3)
            "spacer_id": "super_warm"        # Best spacer (Psi=0.03)
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have good thermal performance
        assert data["uw"] <= 1.3, f"Uw should be <= 1.3 for Zone E compliance, got {data['uw']}"
        
        # Verify ecobonus eligibility for Zone E
        assert data["ecobonus_eligible"]["E"] == True, "Should be eligible for Zone E"
        
        # Should have no warnings about Ecobonus
        has_ecobonus_warning = any("NON detraibile" in w for w in data["warnings"])
        assert not has_ecobonus_warning, "Should not have Ecobonus warning with good performance"
        
        print(f"PASS: High-performance Uw = {data['uw']} W/m2K (Zone E eligible)")
    
    def test_calculate_uw_poor_thermal_performance(self):
        """Calculate Uw with poor components (should fail Zone E and show warnings)"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "singolo",         # Worst glass (Ug=5.8)
            "frame_id": "ferro_battuto",   # Worst frame (Uf=7.0)
            "spacer_id": "alluminio"       # Standard spacer
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have poor thermal performance
        assert data["uw"] > 3.2, f"Uw should be > 3.2 with poor components, got {data['uw']}"
        
        # Verify NOT eligible for any zone
        for zone in ["A", "B", "C", "D", "E", "F"]:
            assert data["ecobonus_eligible"][zone] == False, f"Should NOT be eligible for Zone {zone}"
        
        # Should have warning about exceeding all zone limits
        has_all_zones_warning = any("tutte le zone" in w for w in data["warnings"])
        assert has_all_zones_warning, "Should have warning about exceeding all zone limits"
        
        print(f"PASS: Poor thermal Uw = {data['uw']} W/m2K (fails all zones, warnings present)")
    
    def test_calculate_uw_medium_performance_zone_d_eligible(self):
        """Calculate Uw that passes Zone D but fails Zone E"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",  # Good glass (Ug=1.0)
            "frame_id": "acciaio_standard", # Standard steel (Uf=5.9)
            "spacer_id": "alluminio"
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should be around 1.7 W/m2K
        assert 1.3 < data["uw"] <= 1.8, f"Uw should be between 1.3 and 1.8, got {data['uw']}"
        
        # Verify Zone D eligible but Zone E not
        assert data["ecobonus_eligible"]["D"] == True, "Should be eligible for Zone D"
        assert data["ecobonus_eligible"]["E"] == False, "Should NOT be eligible for Zone E"
        
        # Should have warning about Zone E
        has_zone_e_warning = any("Zona E" in w and "NON detraibile" in w for w in data["warnings"])
        assert has_zone_e_warning, "Should have warning about Zone E non-eligibility"
        
        print(f"PASS: Medium Uw = {data['uw']} W/m2K (Zone D ok, Zone E fails)")
    
    def test_calculate_uw_returns_labels(self):
        """Verify calculation returns component labels"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        data = response.json()
        
        assert "glass_label" in data, "Response should contain 'glass_label'"
        assert "frame_label" in data, "Response should contain 'frame_label'"
        assert "spacer_label" in data, "Response should contain 'spacer_label'"
        
        assert data["glass_label"] == "Doppio vetro basso emissivo + argon"
        assert data["frame_label"] == "Acciaio zincato standard"
        assert data["spacer_label"] == "Canalina alluminio (standard)"
        
        print(f"PASS: Component labels returned correctly")
    
    def test_calculate_uw_different_dimensions(self):
        """Test calculation with different window dimensions"""
        # Small window
        payload_small = {
            "height_mm": 800,
            "width_mm": 600,
            "frame_width_mm": 60,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response_small = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload_small)
        assert response_small.status_code == 200
        data_small = response_small.json()
        
        # Large window
        payload_large = {
            "height_mm": 4000,
            "width_mm": 5000,
            "frame_width_mm": 100,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response_large = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload_large)
        assert response_large.status_code == 200
        data_large = response_large.json()
        
        # Larger windows should have slightly better Uw (more glass area relative to frame)
        assert data_large["total_area"] == 20.0, f"Large window area should be 20 m2"
        assert data_small["total_area"] == 0.48, f"Small window area should be 0.48 m2"
        
        print(f"PASS: Different dimensions calculated - small: {data_small['uw']}, large: {data_large['uw']} W/m2K")
    
    def test_calculate_uw_sandwich_panel(self):
        """Test calculation with sandwich panel (no glass, insulated panel)"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "pannello_sandwich_60",  # Best insulated panel (Ug=0.5)
            "frame_id": "acciaio_taglio_termico", # Thermal break steel (Uf=3.2)
            "spacer_id": "nessuna"                # No spacer for panels
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have very good performance
        assert data["uw"] <= 1.0, f"Insulated panel Uw should be <= 1.0, got {data['uw']}"
        assert data["psi"] == 0.0, "Panel should have no spacer thermal bridge"
        
        # Should be eligible for all zones including F
        assert data["ecobonus_eligible"]["F"] == True, "Insulated panel should pass Zone F"
        
        print(f"PASS: Sandwich panel Uw = {data['uw']} W/m2K (all zones eligible)")


class TestThermalCalculationEdgeCases:
    """Test edge cases for thermal calculation"""
    
    def test_calculate_with_minimum_valid_dimensions(self):
        """Test with very small but valid dimensions"""
        payload = {
            "height_mm": 200,
            "width_mm": 200,
            "frame_width_mm": 50,
            "glass_id": "doppio_be_argon",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200, f"Should handle small dimensions, got {response.status_code}"
        
        data = response.json()
        assert "uw" in data
        print(f"PASS: Small dimensions handled, Uw = {data['uw']}")
    
    def test_calculate_with_invalid_glass_id_uses_default(self):
        """Test that invalid glass_id falls back to first option"""
        payload = {
            "height_mm": 2100,
            "width_mm": 3000,
            "frame_width_mm": 80,
            "glass_id": "invalid_glass_type",
            "frame_id": "acciaio_standard",
            "spacer_id": "alluminio"
        }
        
        response = requests.post(f"{BASE_URL}/api/certificazioni/thermal/calculate", json=payload)
        assert response.status_code == 200, "Should handle invalid glass_id"
        
        data = response.json()
        # Should fall back to first glass type (singolo, Ug=5.8)
        assert data["ug"] == 5.8, f"Should use default glass Ug=5.8, got {data['ug']}"
        print(f"PASS: Invalid glass_id handled with fallback")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

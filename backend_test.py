#!/usr/bin/env python3
"""
Backend API Testing for Norma Facile 2.0 - Distinta Materiali Module
Tests CRUD operations, totals calculations, and import functionality.
"""
import requests
import json
import sys
from datetime import datetime

class DistinteAPITester:
    def __init__(self, base_url="https://norma-v2-deploy.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = "test_session_1772177028714"  # From auth setup
        self.user_id = "test-user-1772177028714"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_distinta_id = None
        self.created_rilievo_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, description=""):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.session_token}'
        }

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        if description:
            print(f"   📝 {description}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            print(f"   📍 URL: {url}")
            print(f"   📤 Status: {response.status_code}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json() if response.text else {}
                    if response_data:
                        print(f"   📦 Response keys: {list(response_data.keys())}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   🚨 Error: {error_data}")
                except:
                    print(f"   🚨 Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ FAILED - Network Error: {str(e)}")
            return False, {}

    def test_auth_status(self):
        """Test authentication status"""
        success, response = self.run_test(
            "Auth Status", "GET", "auth/me", 200,
            description="Verify test session is working"
        )
        if success:
            print(f"   👤 User: {response.get('name', 'Unknown')}")
        return success

    def test_get_empty_distinte_list(self):
        """Test getting empty distinte list"""
        success, response = self.run_test(
            "Get Empty Distinte List", "GET", "distinte/", 200,
            description="Should return empty list initially"
        )
        if success:
            print(f"   📋 Found {len(response.get('distinte', []))} distinte")
        return success

    def test_create_distinta(self):
        """Test creating a new distinta with items"""
        test_data = {
            "name": "Test BOM - Serramenti Ufficio",
            "notes": "Distinta di test per verificare i calcoli",
            "items": [
                {
                    "category": "profilo",
                    "code": "PRF001",
                    "name": "Profilo alluminio 60x20",
                    "description": "Profilo strutturale",
                    "length_mm": 2000,
                    "quantity": 4,
                    "unit": "pz",
                    "weight_per_unit": 0.8,
                    "cost_per_unit": 12.50,
                    "notes": "Per telaio"
                },
                {
                    "category": "vetro", 
                    "code": "VTR001",
                    "name": "Vetro temperato 6mm",
                    "description": "Vetro di sicurezza",
                    "length_mm": 1000,
                    "width_mm": 800,
                    "quantity": 2,
                    "unit": "m²",
                    "weight_per_unit": 15.0,
                    "cost_per_unit": 45.00,
                    "notes": "Pannelli laterali"
                }
            ]
        }

        success, response = self.run_test(
            "Create Distinta", "POST", "distinte/", 201, test_data,
            description="Create BOM with 2 items and verify totals calculation"
        )
        
        if success:
            self.created_distinta_id = response.get('distinta_id')
            print(f"   🆔 Created ID: {self.created_distinta_id}")
            
            # Verify totals calculation
            totals = response.get('totals', {})
            print(f"   🧮 Totals: {totals.get('total_items', 0)} items, "
                  f"{totals.get('total_weight_kg', 0):.2f}kg, "
                  f"€{totals.get('total_cost', 0):.2f}")
            
            # Check expected calculations
            expected_items = 2
            # Item 1: 4 pieces × 0.8kg = 3.2kg, 4 × 12.50 = €50.00
            # Item 2: 2 pieces × (1000×800/1000000) m² × 15kg/m² = 2 × 0.8 × 15 = 24kg, 2 × 0.8 × 45 = €72.00
            expected_weight = 3.2 + 24.0  # 27.2kg
            expected_cost = 50.00 + 72.00  # €122.00
            
            if (totals.get('total_items') == expected_items and 
                abs(totals.get('total_weight_kg', 0) - expected_weight) < 0.1 and
                abs(totals.get('total_cost', 0) - expected_cost) < 0.1):
                print("   ✅ Totals calculation correct")
            else:
                print(f"   ⚠️  Totals mismatch - Expected: {expected_items} items, {expected_weight}kg, €{expected_cost}")
                
        return success

    def test_get_distinta_by_id(self):
        """Test getting distinta by ID"""
        if not self.created_distinta_id:
            print("❌ No distinta ID available - skipping")
            return False
            
        success, response = self.run_test(
            "Get Distinta by ID", "GET", f"distinte/{self.created_distinta_id}", 200,
            description="Retrieve created distinta by ID"
        )
        
        if success:
            print(f"   📋 Name: {response.get('name')}")
            print(f"   🏷️  Status: {response.get('status')}")
            print(f"   📦 Items: {len(response.get('items', []))}")
        
        return success

    def test_update_distinta(self):
        """Test updating distinta and recalculating totals"""
        if not self.created_distinta_id:
            print("❌ No distinta ID available - skipping")
            return False

        # Add another item and modify existing ones
        update_data = {
            "name": "Test BOM - Serramenti Ufficio (Updated)",
            "status": "confermata",
            "items": [
                {
                    "category": "profilo",
                    "code": "PRF001",
                    "name": "Profilo alluminio 60x20",
                    "length_mm": 2000,
                    "quantity": 6,  # Increased from 4 to 6
                    "unit": "pz",
                    "weight_per_unit": 0.8,
                    "cost_per_unit": 12.50
                },
                {
                    "category": "accessorio",
                    "code": "ACC001", 
                    "name": "Cerniera a scomparsa",
                    "quantity": 8,
                    "unit": "pz",
                    "weight_per_unit": 0.15,
                    "cost_per_unit": 3.75
                }
            ]
        }

        success, response = self.run_test(
            "Update Distinta", "PUT", f"distinte/{self.created_distinta_id}", 200, update_data,
            description="Update distinta with new items and verify recalculation"
        )
        
        if success:
            totals = response.get('totals', {})
            print(f"   🧮 New Totals: {totals.get('total_items', 0)} items, "
                  f"{totals.get('total_weight_kg', 0):.2f}kg, "
                  f"€{totals.get('total_cost', 0):.2f}")
            print(f"   🏷️  Status: {response.get('status')}")
            
        return success

    def test_get_updated_distinte_list(self):
        """Test getting distinte list after creation"""
        success, response = self.run_test(
            "Get Distinte List", "GET", "distinte/", 200,
            description="Should now include created distinta"
        )
        
        if success:
            distinte = response.get('distinte', [])
            print(f"   📋 Found {len(distinte)} distinte")
            if distinte:
                for d in distinte:
                    print(f"   - {d.get('name')} (Status: {d.get('status')})")
        
        return success

    def setup_test_rilievo(self):
        """Create a test rilievo for import testing"""
        rilievo_data = {
            "project_name": "Test Project for Import",
            "client_id": "test_client_123",
            "sketches": [
                {
                    "name": "Finestra principale",
                    "dimensions": {
                        "width": 120,  # cm
                        "height": 150  # cm
                    },
                    "notes": "Finestra lato sud"
                },
                {
                    "name": "Porta ingresso", 
                    "dimensions": {
                        "width": 90,   # cm
                        "height": 210  # cm
                    },
                    "notes": "Porta principale"
                }
            ]
        }

        success, response = self.run_test(
            "Create Test Rilievo", "POST", "rilievi/", 201, rilievo_data,
            description="Create rilievo for import testing"
        )
        
        if success:
            self.created_rilievo_id = response.get('rilievo_id')
            print(f"   🆔 Created Rilievo ID: {self.created_rilievo_id}")
        
        return success

    def test_import_from_rilievo(self):
        """Test the mocked import-from-rilievo functionality"""
        if not self.created_distinta_id:
            print("❌ No distinta ID available - skipping")
            return False
        
        if not self.created_rilievo_id:
            print("❌ No rilievo ID available - skipping")
            return False

        success, response = self.run_test(
            "Import from Rilievo (MOCKED)", "POST", 
            f"distinte/{self.created_distinta_id}/import-rilievo/{self.created_rilievo_id}", 200,
            description="Test mocked import functionality"
        )
        
        if success:
            items = response.get('items', [])
            print(f"   📦 Total items after import: {len(items)}")
            
            # Count imported items (should have "Importato da rilievo" in description)
            imported_count = sum(1 for item in items if 'Importato da rilievo' in item.get('description', ''))
            print(f"   📥 Imported items: {imported_count}")
            
            totals = response.get('totals', {})
            print(f"   🧮 Updated Totals: {totals.get('total_items', 0)} items, "
                  f"€{totals.get('total_cost', 0):.2f}")
        
        return success

    def test_filter_by_status(self):
        """Test filtering distinte by status"""
        success, response = self.run_test(
            "Filter by Status", "GET", "distinte/?status=confermata", 200,
            description="Filter distinte by confirmed status"
        )
        
        if success:
            distinte = response.get('distinte', [])
            print(f"   📋 Found {len(distinte)} confirmed distinte")
            
        return success

    def test_delete_distinta(self):
        """Test deleting a distinta"""
        if not self.created_distinta_id:
            print("❌ No distinta ID available - skipping")
            return False

        success, response = self.run_test(
            "Delete Distinta", "DELETE", f"distinte/{self.created_distinta_id}", 200,
            description="Delete the test distinta"
        )
        
        return success

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test rilievo if created
        if self.created_rilievo_id:
            self.run_test("Cleanup Rilievo", "DELETE", f"rilievi/{self.created_rilievo_id}", 200)

def main():
    print("🚀 Starting Distinta Materiali API Testing")
    print("=" * 60)
    
    tester = DistinteAPITester()
    
    # Test sequence
    tests = [
        ("Auth Check", tester.test_auth_status),
        ("Empty List", tester.test_get_empty_distinte_list),
        ("Create Distinta", tester.test_create_distinta),
        ("Get by ID", tester.test_get_distinta_by_id),
        ("Update Distinta", tester.test_update_distinta),
        ("Get Updated List", tester.test_get_updated_distinte_list),
        ("Setup Rilievo", tester.setup_test_rilievo),
        ("Import from Rilievo", tester.test_import_from_rilievo),
        ("Filter by Status", tester.test_filter_by_status),
        ("Delete Distinta", tester.test_delete_distinta),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Cleanup
    tester.cleanup_test_data()
    
    # Results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
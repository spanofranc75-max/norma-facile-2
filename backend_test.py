#!/usr/bin/env python3
"""
Comprehensive Backend API Test Suite for Norma Facile 2.0 Rilievo Misure Module
Tests all CRUD operations, PDF generation, and business logic for Rilievi.
"""
import requests
import json
import sys
import time
import base64
from datetime import datetime, date, timedelta

class RilievoAPITester:
    def __init__(self, base_url="https://legal-easy-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = "test_session_1772176345185"  # From auth setup
        self.user_id = "test-user-1772176345185"
        self.tests_run = 0
        self.tests_passed = 0
        self.client_id = None
        self.rilievo_id = None
        self.session = requests.Session()
        
        # Set session cookie for authentication
        self.session.cookies.set("session_token", self.session_token)

    def log_test(self, name, success=None, details=""):
        """Log test results"""
        self.tests_run += 1
        if success is not None:
            if success:
                self.tests_passed += 1
                print(f"✅ {name} - PASSED {details}")
            else:
                print(f"❌ {name} - FAILED {details}")
        else:
            print(f"🔍 {name} {details}")

    def api_request(self, method, endpoint, data=None, expect_status=200):
        """Make API request with proper headers and error handling"""
        url = f"{self.base_url}/api{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'NormaFacile-Tester/1.0'
        }
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = self.session.put(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            elif method == 'PATCH':
                response = self.session.patch(url, headers=headers, json=data)
            
            success = response.status_code == expect_status
            
            if success:
                try:
                    return True, response.json() if response.content else {}
                except json.JSONDecodeError:
                    return True, {"raw_response": response.text}
            else:
                error_msg = f"Status {response.status_code}, expected {expect_status}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', response.text)}"
                except:
                    error_msg += f" - {response.text}"
                return False, {"error": error_msg}
                
        except Exception as e:
            return False, {"error": f"Request failed: {str(e)}"}

    def test_auth(self):
        """Test authentication endpoint"""
        print("\n🔐 TESTING AUTHENTICATION")
        
        success, data = self.api_request('GET', '/auth/me')
        self.log_test("GET /api/auth/me", success, f"User: {data.get('name', 'Unknown')}")
        return success

    def test_clients_crud(self):
        """Test complete client CRUD operations"""
        print("\n👥 TESTING CLIENT MANAGEMENT")
        
        # Test GET clients (empty list)
        success, data = self.api_request('GET', '/clients/')
        self.log_test("GET /api/clients/ (initial)", success, f"Total: {data.get('total', 0)}")
        
        # Test CREATE client
        client_data = {
            "business_name": "Test Client SRL",
            "client_type": "azienda",
            "partita_iva": "IT12345678901",
            "codice_fiscale": "TSTCLN123456789",
            "codice_sdi": "ABC1234",
            "address": "Via Roma 123",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "country": "IT",
            "phone": "+39 06 1234567",
            "email": "test@client.it",
            "notes": "Test client for automated testing"
        }
        
        success, data = self.api_request('POST', '/clients/', client_data, 201)
        if success and data.get('client_id'):
            self.client_id = data['client_id']
            self.log_test("POST /api/clients/", True, f"Client created: {self.client_id}")
        else:
            self.log_test("POST /api/clients/", False, str(data))
            return False
        
        # Test GET specific client
        success, data = self.api_request('GET', f'/clients/{self.client_id}')
        self.log_test("GET /api/clients/{id}", success, f"Name: {data.get('business_name', 'Unknown')}")
        
        # Test UPDATE client
        update_data = {
            "business_name": "Test Client SRL - Updated",
            "notes": "Updated via API test"
        }
        success, data = self.api_request('PUT', f'/clients/{self.client_id}', update_data)
        self.log_test("PUT /api/clients/{id}", success, f"Updated name: {data.get('business_name', 'Unknown')}")
        
        # Test search clients
        success, data = self.api_request('GET', '/clients/?search=Test Client')
        self.log_test("GET /api/clients/?search=Test", success, f"Found: {data.get('total', 0)} clients")
        
        return True

    def test_rilievi_crud(self):
        """Test complete rilievo CRUD operations"""
        print("\n📏 TESTING RILIEVO MANAGEMENT")
        
        if not self.client_id:
            self.log_test("Rilievo tests", False, "No client_id available")
            return False
        
        # Test GET rilievi (empty list)
        success, data = self.api_request('GET', '/rilievi/')
        self.log_test("GET /api/rilievi/ (initial)", success, f"Total: {data.get('total', 0)}")
        
        # Create a simple base64 test image for sketches and photos
        test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        # Test CREATE rilievo with sketches and photos
        today = date.today()
        
        rilievo_data = {
            "client_id": self.client_id,
            "project_name": "Test Rilievo Appartamento",
            "survey_date": today.isoformat(),
            "location": "Via Roma 123, Milano",
            "notes": "Test rilievo created by automated testing",
            "sketches": [
                {
                    "name": "Pianta principale",
                    "background_image": test_image,
                    "drawing_data": '{"lines":[],"width":800,"height":500}',
                    "dimensions": {
                        "width": "500",
                        "height": "300", 
                        "depth": "250"
                    }
                }
            ],
            "photos": [
                {
                    "name": "Foto ingresso",
                    "image_data": test_image,
                    "caption": "Vista dell'ingresso principale"
                }
            ]
        }
        
        success, data = self.api_request('POST', '/rilievi/', rilievo_data, 201)
        if success and data.get('rilievo_id'):
            self.rilievo_id = data['rilievo_id']
            self.log_test("POST /api/rilievi/", True, 
                f"Rilievo created: {self.rilievo_id}, Project: {data.get('project_name', '')}")
        else:
            self.log_test("POST /api/rilievi/", False, str(data))
            return False
        
        # Test GET specific rilievo
        success, data = self.api_request('GET', f'/rilievi/{self.rilievo_id}')
        if success:
            self.log_test("GET /api/rilievi/{id}", True, 
                f"Project: {data.get('project_name', '')}, Status: {data.get('status', '')}, Sketches: {len(data.get('sketches', []))}, Photos: {len(data.get('photos', []))}")
        else:
            self.log_test("GET /api/rilievi/{id}", False, str(data))
        
        # Test UPDATE rilievo (add sketch and photo)
        update_data = {
            "notes": "Updated rilievo notes via API test",
            "sketches": rilievo_data["sketches"] + [
                {
                    "name": "Schizzo bagno",
                    "background_image": test_image,
                    "drawing_data": '{"lines":[{"tool":"pencil","points":[10,10,50,50]}],"width":800,"height":500}',
                    "dimensions": {
                        "width": "200",
                        "height": "180"
                    }
                }
            ],
            "photos": rilievo_data["photos"] + [
                {
                    "name": "Foto cucina",
                    "image_data": test_image,
                    "caption": "Vista della cucina"
                }
            ]
        }
        success, data = self.api_request('PUT', f'/rilievi/{self.rilievo_id}', update_data)
        if success:
            self.log_test("PUT /api/rilievi/{id}", True, 
                f"Updated - Sketches: {len(data.get('sketches', []))}, Photos: {len(data.get('photos', []))}")
        else:
            self.log_test("PUT /api/rilievi/{id}", False, str(data))
        
        # Test add single sketch endpoint
        new_sketch = {
            "name": "Schizzo camera",
            "background_image": test_image,
            "drawing_data": '{"lines":[],"width":800,"height":500}',
            "dimensions": {
                "width": "400",
                "height": "350"
            }
        }
        success, data = self.api_request('POST', f'/rilievi/{self.rilievo_id}/sketch', new_sketch)
        self.log_test("POST /api/rilievi/{id}/sketch", success, 
            f"Total sketches: {len(data.get('sketches', []))}" if success else str(data))
        
        # Test add single photo endpoint
        new_photo = {
            "name": "Foto terrazzo",
            "image_data": test_image,
            "caption": "Vista del terrazzo"
        }
        success, data = self.api_request('POST', f'/rilievi/{self.rilievo_id}/photo', new_photo)
        self.log_test("POST /api/rilievi/{id}/photo", success, 
            f"Total photos: {len(data.get('photos', []))}" if success else str(data))
        
        # Test rilievo filters
        success, data = self.api_request('GET', f'/rilievi/?client_id={self.client_id}')
        self.log_test("GET /api/rilievi/?client_id={client_id}", success, f"Found: {data.get('total', 0)} for client")
        
        success, data = self.api_request('GET', '/rilievi/?status=bozza')
        self.log_test("GET /api/rilievi/?status=bozza", success, f"Found: {data.get('total', 0)} bozze")
        
        return True

    def test_rilievo_pdf_generation(self):
        """Test PDF generation for rilievi"""
        print("\n📑 TESTING RILIEVO PDF GENERATION")
        
        if not self.rilievo_id:
            self.log_test("Rilievo PDF generation", False, "No rilievo_id available")
            return False
        
        # Test PDF generation endpoint
        pdf_url = f"{self.base_url}/api/rilievi/{self.rilievo_id}/pdf"
        try:
            response = self.session.get(pdf_url)
            if response.status_code == 200:
                # Check if response is actually a PDF
                if response.headers.get('content-type') == 'application/pdf':
                    pdf_size = len(response.content)
                    self.log_test("GET /api/rilievi/{id}/pdf", True, f"PDF size: {pdf_size} bytes")
                else:
                    self.log_test("GET /api/rilievi/{id}/pdf", False, "Response not PDF format")
            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', response.text)}"
                except:
                    error_msg += f" - {response.text}"
                self.log_test("GET /api/rilievi/{id}/pdf", False, error_msg)
        except Exception as e:
            self.log_test("GET /api/rilievi/{id}/pdf", False, f"Request failed: {str(e)}")
            return False
            
        return True

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n🧹 CLEANING UP TEST DATA")
        
        # Note: In a real scenario, we might delete test data
        # For now, just report what was created
        if self.client_id:
            self.log_test("Test client created", None, f"ID: {self.client_id}")
        if self.rilievo_id:
            self.log_test("Test rilievo created", None, f"ID: {self.rilievo_id}")

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting Norma Facile 2.0 Rilievo Misure Backend API Test Suite")
        print("=" * 70)
        
        start_time = time.time()
        
        # Run all test suites
        test_results = []
        test_results.append(self.test_auth())
        test_results.append(self.test_clients_crud())
        test_results.append(self.test_rilievi_crud())
        test_results.append(self.test_rilievo_pdf_generation())
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final results
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(f"📊 TEST RESULTS SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"Execution Time: {elapsed:.2f} seconds")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED - See details above")
            return 1

def main():
    """Main test runner"""
    tester = RilievoAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
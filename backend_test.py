#!/usr/bin/env python3
"""
Backend API Tests for Norma Facile 2.0 Phase 1
Tests all API endpoints with public URL.
"""
import requests
import sys
from datetime import datetime

class NormaFacileAPITester:
    def __init__(self, base_url="https://legal-easy-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, expected_data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json={}, headers=headers, timeout=10)
            
            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"text": response.text}
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if expected_data:
                    for key, expected_val in expected_data.items():
                        actual_val = response_data.get(key)
                        if actual_val != expected_val:
                            print(f"   ⚠️  Expected {key}='{expected_val}', got '{actual_val}'")
                        else:
                            print(f"   ✓ {key}: '{actual_val}'")
                else:
                    print(f"   Response: {response_data}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response_data}")
            
            self.test_results.append({
                "name": name,
                "endpoint": endpoint, 
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_data": response_data
            })

            return success, response_data

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed - Network Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test GET /api/ for Italian welcome message"""
        return self.run_test(
            "Root API Endpoint",
            "GET", 
            "/api/",
            200,
            expected_data={
                "message": "Benvenuto a Norma Facile 2.0",
                "status": "operativo"
            }
        )

    def test_health_endpoint(self):
        """Test GET /api/health"""
        return self.run_test(
            "Health Check Endpoint",
            "GET",
            "/api/health", 
            200,
            expected_data={
                "status": "healthy",
                "service": "Norma Facile 2.0"
            }
        )

    def test_auth_me_unauthorized(self):
        """Test GET /api/auth/me returns 401 when not authenticated"""
        return self.run_test(
            "Auth Me - Unauthorized", 
            "GET",
            "/api/auth/me",
            401
        )

    def test_mocked_apis(self):
        """Test Phase 2 APIs return 501"""
        # Test document generation
        doc_success, _ = self.run_test(
            "Document Generation (Phase 2 - Should be 501)",
            "POST", 
            "/api/documents/",
            501
        )
        
        # Test chat 
        chat_success, _ = self.run_test(
            "Chat API (Phase 2 - Should be 501)",
            "POST",
            "/api/chat/",
            501
        )
        
        return doc_success and chat_success

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("🚀 Starting Norma Facile 2.0 Backend API Tests")
        print("=" * 60)
        
        # Core API tests
        self.test_root_endpoint()
        self.test_health_endpoint()
        self.test_auth_me_unauthorized()
        
        # Phase 2 mocked API tests
        self.test_mocked_apis()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} test(s) failed")
            
        return self.tests_passed == self.tests_run

def main():
    """Main test runner"""
    tester = NormaFacileAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
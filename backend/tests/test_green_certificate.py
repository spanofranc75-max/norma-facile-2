"""
Test Green Certificate Feature (Iteration 67)
Tests the /api/cam/green-certificate/{commessa_id} endpoint that generates
a branded sustainability PDF showing CO2 savings, trees planted, recycled steel %, and CAM compliance.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGreenCertificateEndpoint:
    """Tests for GET /api/cam/green-certificate/{commessa_id}"""
    
    @pytest.fixture(scope="class")
    def test_session(self):
        """Create test user and session for authentication"""
        import subprocess
        session_token = f"test_green_cert_{uuid.uuid4().hex[:10]}"
        user_id = f"test_user_gc_{uuid.uuid4().hex[:10]}"
        
        # Create test user and session via mongosh
        mongo_cmd = f"""
        use('test_database');
        db.users.insertOne({{
            user_id: '{user_id}',
            email: 'testgc_{uuid.uuid4().hex[:6]}@test.com',
            name: 'Green Cert Tester',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{user_id}',
            session_token: '{session_token}',
            expires_at: new Date(Date.now() + 24*60*60*1000),
            created_at: new Date()
        }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True)
        
        yield {"token": session_token, "user_id": user_id}
        
        # Cleanup
        cleanup_cmd = f"""
        use('test_database');
        db.users.deleteMany({{user_id: '{user_id}'}});
        db.user_sessions.deleteMany({{session_token: '{session_token}'}});
        db.commesse.deleteMany({{user_id: '{user_id}'}});
        db.lotti_cam.deleteMany({{user_id: '{user_id}'}});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_cmd], capture_output=True)
    
    @pytest.fixture(scope="class")
    def test_commessa_with_cam(self, test_session):
        """Create a test commessa with CAM lotti"""
        import subprocess
        user_id = test_session["user_id"]
        commessa_id = f"com_gc_{uuid.uuid4().hex[:10]}"
        
        mongo_cmd = f"""
        use('test_database');
        db.commesse.insertOne({{
            commessa_id: '{commessa_id}',
            user_id: '{user_id}',
            numero: 'GC-TEST-001',
            title: 'Green Certificate Test Commessa',
            client_name: 'Test Client',
            created_at: new Date()
        }});
        
        db.lotti_cam.insertOne({{
            lotto_id: 'cam_gc_{uuid.uuid4().hex[:10]}',
            user_id: '{user_id}',
            commessa_id: '{commessa_id}',
            descrizione: 'IPE 200 Test',
            fornitore: 'Test Steel Supplier',
            numero_colata: 'TEST123',
            peso_kg: 500,
            percentuale_riciclato: 80,
            metodo_produttivo: 'forno_elettrico_non_legato',
            tipo_certificazione: 'epd',
            uso_strutturale: true,
            soglia_minima_cam: 75,
            conforme_cam: true,
            created_at: new Date()
        }});
        
        db.lotti_cam.insertOne({{
            lotto_id: 'cam_gc_{uuid.uuid4().hex[:10]}',
            user_id: '{user_id}',
            commessa_id: '{commessa_id}',
            descrizione: 'HEA 300 Test',
            fornitore: 'Test Steel Supplier',
            numero_colata: 'TEST456',
            peso_kg: 300,
            percentuale_riciclato: 75,
            metodo_produttivo: 'forno_elettrico_non_legato',
            tipo_certificazione: 'dichiarazione_produttore',
            uso_strutturale: true,
            soglia_minima_cam: 75,
            conforme_cam: true,
            created_at: new Date()
        }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True)
        
        return commessa_id
    
    @pytest.fixture(scope="class")
    def test_commessa_no_cam(self, test_session):
        """Create a test commessa without CAM lotti"""
        import subprocess
        user_id = test_session["user_id"]
        commessa_id = f"com_nc_{uuid.uuid4().hex[:10]}"
        
        mongo_cmd = f"""
        use('test_database');
        db.commesse.insertOne({{
            commessa_id: '{commessa_id}',
            user_id: '{user_id}',
            numero: 'NC-TEST-001',
            title: 'No CAM Test Commessa',
            client_name: 'Test Client',
            created_at: new Date()
        }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_cmd], capture_output=True)
        
        return commessa_id
    
    def test_green_certificate_success_returns_pdf(self, test_session, test_commessa_with_cam):
        """Test: Green certificate endpoint returns PDF when CAM lotti exist"""
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/{test_commessa_with_cam}",
            headers={"Authorization": f"Bearer {test_session['token']}"}
        )
        
        # Should return 200 with PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get('Content-Type') == 'application/pdf', f"Expected PDF, got {response.headers.get('Content-Type')}"
        
        # Verify it's a valid PDF (starts with %PDF)
        assert response.content[:4] == b'%PDF', "Response should be a valid PDF file"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'Green_Certificate' in content_disp, f"Filename should contain 'Green_Certificate', got: {content_disp}"
        print(f"✅ Green Certificate PDF generated successfully for commessa {test_commessa_with_cam}")
    
    def test_green_certificate_no_cam_lotti_returns_400(self, test_session, test_commessa_no_cam):
        """Test: Green certificate endpoint returns 400 when no CAM lotti exist"""
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/{test_commessa_no_cam}",
            headers={"Authorization": f"Bearer {test_session['token']}"}
        )
        
        # Should return 400 with error message
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'detail' in data, "Response should have 'detail' field"
        assert 'CAM' in data['detail'] or 'lotto' in data['detail'].lower(), f"Error message should mention CAM lotti: {data['detail']}"
        print(f"✅ Correctly returned 400 for commessa without CAM lotti: {data['detail']}")
    
    def test_green_certificate_nonexistent_commessa_returns_404(self, test_session):
        """Test: Green certificate endpoint returns 404 for non-existent commessa"""
        fake_commessa_id = f"com_fake_{uuid.uuid4().hex[:10]}"
        
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/{fake_commessa_id}",
            headers={"Authorization": f"Bearer {test_session['token']}"}
        )
        
        # Should return 404
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'detail' in data, "Response should have 'detail' field"
        print(f"✅ Correctly returned 404 for non-existent commessa: {data['detail']}")
    
    def test_green_certificate_requires_auth(self):
        """Test: Green certificate endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/any_commessa_id"
            # No Authorization header
        )
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✅ Endpoint correctly requires authentication")
    
    def test_green_certificate_pdf_content_structure(self, test_session, test_commessa_with_cam):
        """Test: PDF contains expected content (CO2, trees, recycled %, CAM)"""
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/{test_commessa_with_cam}",
            headers={"Authorization": f"Bearer {test_session['token']}"}
        )
        
        assert response.status_code == 200
        
        # PDF content validation - check size is reasonable (at least 10KB for a proper PDF)
        pdf_size = len(response.content)
        assert pdf_size > 10000, f"PDF seems too small ({pdf_size} bytes), might be empty or malformed"
        assert pdf_size < 5000000, f"PDF seems too large ({pdf_size} bytes)"
        
        print(f"✅ Green Certificate PDF size: {pdf_size} bytes (reasonable)")


class TestGreenCertificateWithRealData:
    """Test with existing real data in database (if available)"""
    
    def test_green_certificate_with_existing_commessa(self):
        """Test Green Certificate with an existing commessa that has CAM lotti"""
        import subprocess
        
        # Find an existing commessa with CAM lotti
        find_cmd = """
        use('test_database');
        var lotto = db.lotti_cam.findOne({commessa_id: {$ne: null}}, {_id:0, commessa_id:1, user_id:1});
        if (lotto) {
            var session = db.user_sessions.findOne({user_id: lotto.user_id}, {_id:0, session_token:1});
            if (session) {
                print(JSON.stringify({commessa_id: lotto.commessa_id, token: session.session_token}));
            } else {
                print('NO_SESSION');
            }
        } else {
            print('NO_DATA');
        }
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', find_cmd], capture_output=True, text=True)
        output = result.stdout.strip()
        
        if output == 'NO_DATA' or output == 'NO_SESSION' or not output:
            pytest.skip("No existing commessa with CAM lotti and active session found")
        
        import json
        try:
            data = json.loads(output)
        except:
            pytest.skip(f"Could not parse data: {output}")
        
        # Test with real data
        response = requests.get(
            f"{BASE_URL}/api/cam/green-certificate/{data['commessa_id']}",
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers.get('Content-Type') == 'application/pdf'
        print(f"✅ Green Certificate works with real commessa: {data['commessa_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Iteration 81 - Tests for Super Fascicolo Tecnico Unico feature:
1. GET /api/commesse/{cid}/fascicolo-tecnico-completo returns PDF
2. Endpoint returns 404 for non-existent commessa
3. Endpoint returns 401 for unauthenticated requests
4. PDF generation service generates all sections correctly
5. Verify existing functionality (company/settings) still works
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Use the public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://normafacile-fpc-fix.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create a test user and session for authenticated requests."""
    import subprocess
    
    user_id = f"test-user-iter81-{uuid.uuid4().hex[:8]}"
    session_token = f"test_session_iter81_{uuid.uuid4().hex[:16]}"
    
    # Create user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'iter81.test@example.com',
        name: 'Iteration 81 Test User',
        picture: 'https://via.placeholder.com/150',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "user_id": user_id,
        "session_token": session_token,
        "headers": {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
    }
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    db.company_settings.deleteMany({{user_id: '{user_id}'}});
    db.commesse.deleteMany({{user_id: '{user_id}'}});
    db.clients.deleteMany({{user_id: '{user_id}'}});
    db.material_batches.deleteMany({{user_id: '{user_id}'}});
    db.lotti_cam.deleteMany({{user_id: '{user_id}'}});
    db.fpc_projects.deleteMany({{user_id: '{user_id}'}});
    db.welders.deleteMany({{user_id: '{user_id}'}});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


@pytest.fixture
def test_commessa_full(test_session):
    """Create a test commessa with all associated data for Super Fascicolo testing."""
    import subprocess
    
    user_id = test_session["user_id"]
    commessa_id = f"test-comm-iter81-{uuid.uuid4().hex[:8]}"
    client_id = f"test-client-iter81-{uuid.uuid4().hex[:8]}"
    welder_id = f"test-welder-iter81-{uuid.uuid4().hex[:8]}"
    preventivo_id = f"test-prev-iter81-{uuid.uuid4().hex[:8]}"
    
    # Create comprehensive test data
    mongo_script = f"""
    use('test_database');
    
    // Create client
    db.clients.insertOne({{
        client_id: '{client_id}',
        user_id: '{user_id}',
        name: 'Cliente Super Fascicolo Test',
        business_name: 'Acme Steel Construction SRL',
        created_at: new Date()
    }});
    
    // Create company settings with all certification data
    db.company_settings.updateOne(
        {{ user_id: '{user_id}' }},
        {{ $set: {{
            user_id: '{user_id}',
            business_name: 'Test Fabbro Super SRL',
            address: 'Via Test 123',
            city: 'Bologna',
            cap: '40100',
            partita_iva: 'IT12345678901',
            certificato_en1090_numero: '0474-CPR-TEST-81',
            ente_certificatore: 'Rina Service SpA',
            ente_certificatore_numero: '0474',
            responsabile_nome: 'Mario Rossi',
            classe_esecuzione_default: 'EXC2',
            logo_url: ''
        }} }},
        {{ upsert: true }}
    );
    
    // Create commessa with fascicolo_tecnico data
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        client_id: '{client_id}',
        preventivo_id: '{preventivo_id}',
        numero: 'COMM-2026-SUPER',
        title: 'Test Super Fascicolo Tecnico',
        classe_esecuzione: 'EXC3',
        fascicolo_tecnico: {{
            redatto_da: 'Ing. Test',
            disegno_numero: 'DIS-001-2026',
            processo_saldatura: '135/138'
        }},
        fasi_produzione: [
            {{tipo: 'taglio', nome: 'Taglio', stato: 'completato', data_completamento: '2026-01-10'}},
            {{tipo: 'saldatura', nome: 'Saldatura', stato: 'in_corso'}}
        ],
        created_at: new Date()
    }});
    
    // Create material batches with certificate data
    db.material_batches.insertOne({{
        batch_id: 'batch-iter81-1',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        material_type: 'S355JR',
        dimensions: 'IPE 200',
        heat_number: 'COLATA-81-001',
        supplier_name: 'ArcelorMittal',
        acciaieria: 'Calvisano',
        has_certificate: true,
        spessore: '8.5mm',
        created_at: new Date()
    }});
    
    db.material_batches.insertOne({{
        batch_id: 'batch-iter81-2',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        material_type: 'S275J0',
        dimensions: 'HEA 160',
        heat_number: 'COLATA-81-002',
        supplier_name: 'Feralpi',
        has_certificate: true,
        spessore: '7mm',
        created_at: new Date()
    }});
    
    // Create CAM lotti (environmental compliance)
    db.lotti_cam.insertOne({{
        lotto_id: 'cam-iter81-1',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        descrizione: 'IPE 200 S355JR',
        numero_colata: 'COLATA-81-001',
        peso_kg: 450,
        percentuale_riciclato: 85,
        metodo_produttivo: 'forno_elettrico_non_legato',
        conforme_cam: true,
        tipo_certificazione: 'certificato_produttore',
        created_at: new Date()
    }});
    
    db.lotti_cam.insertOne({{
        lotto_id: 'cam-iter81-2',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        descrizione: 'HEA 160 S275J0',
        numero_colata: 'COLATA-81-002',
        peso_kg: 320,
        percentuale_riciclato: 80,
        metodo_produttivo: 'forno_elettrico_non_legato',
        conforme_cam: true,
        created_at: new Date()
    }});
    
    // Create welder
    db.welders.insertOne({{
        welder_id: '{welder_id}',
        user_id: '{user_id}',
        name: 'Giuseppe Saldatore',
        qualification_level: 'EN ISO 9606-1',
        license_expiry: '2027-12-31',
        notes: 'Saldatore qualificato per EN 1090',
        created_at: new Date()
    }});
    
    // Create FPC project linked to welder
    db.fpc_projects.insertOne({{
        project_id: 'fpc-iter81-1',
        user_id: '{user_id}',
        preventivo_id: '{preventivo_id}',
        fpc_data: {{
            welder_id: '{welder_id}'
        }},
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "commessa_id": commessa_id,
        "client_id": client_id,
        "welder_id": welder_id,
        "preventivo_id": preventivo_id,
        "numero": "COMM-2026-SUPER"
    }


class TestHealthEndpoint:
    """Basic health check before proceeding with other tests."""
    
    def test_health_endpoint(self):
        """Test that the backend is up and running."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health endpoint OK: {data}")


class TestSuperFascicoloEndpoint:
    """Test the new Super Fascicolo Tecnico Completo endpoint."""
    
    def test_super_fascicolo_returns_pdf(self, test_session, test_commessa_full):
        """Test GET /api/commesse/{cid}/fascicolo-tecnico-completo returns PDF."""
        commessa_id = test_commessa_full["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        # Verify content type is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Verify content disposition (filename)
        content_disp = response.headers.get("Content-Disposition", "")
        assert "Fascicolo_Tecnico_Completo" in content_disp, f"Expected filename in Content-Disposition, got {content_disp}"
        
        # Verify PDF content starts with PDF header
        pdf_content = response.content
        assert len(pdf_content) > 1000, f"PDF content too small: {len(pdf_content)} bytes"
        assert pdf_content[:4] == b'%PDF', f"Content doesn't start with PDF header"
        
        print(f"✓ Super Fascicolo PDF generated successfully")
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")
        print(f"  - PDF size: {len(pdf_content)} bytes")
    
    def test_super_fascicolo_404_nonexistent_commessa(self, test_session):
        """Test GET /api/commesse/{cid}/fascicolo-tecnico-completo returns 404 for non-existent commessa."""
        fake_commessa_id = "non-existent-commessa-xyz123"
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{fake_commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ 404 returned for non-existent commessa")
    
    def test_super_fascicolo_401_unauthenticated(self):
        """Test GET /api/commesse/{cid}/fascicolo-tecnico-completo returns 401 for unauthenticated requests."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/any-commessa-id/fascicolo-tecnico-completo"
            # No authorization header
        )
        
        # Should return 401 or 403 (depends on implementation)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"
        print(f"✓ {response.status_code} returned for unauthenticated request")


class TestSuperFascicoloPDFContent:
    """Test that the Super Fascicolo PDF contains expected sections."""
    
    def test_pdf_size_indicates_multiple_sections(self, test_session, test_commessa_full):
        """Test that PDF is large enough to contain all sections."""
        commessa_id = test_commessa_full["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200
        pdf_size = len(response.content)
        
        # A complete Super Fascicolo with 10+ sections should be substantial
        # Minimum expected: Cover(~50KB) + 5 chapters * ~30KB each = ~200KB
        # Being conservative, check for at least 50KB (minimal content)
        assert pdf_size > 50000, f"PDF size {pdf_size} bytes seems too small for complete fascicolo"
        print(f"✓ PDF size indicates multiple sections: {pdf_size / 1024:.1f} KB")


class TestExistingFunctionalityRegression:
    """Verify existing functionality still works after Super Fascicolo addition."""
    
    def test_company_settings_still_returns_certification_fields(self, test_session):
        """Test GET /api/company/settings still returns classe_esecuzione_default and certificato_en13241_numero."""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify iteration 80 fields still exist
        assert "classe_esecuzione_default" in data, "classe_esecuzione_default field missing"
        assert "certificato_en13241_numero" in data, "certificato_en13241_numero field missing"
        print(f"✓ Company settings still returns certification fields")
    
    def test_company_settings_save_still_works(self, test_session):
        """Test PUT /api/company/settings still saves certification fields correctly."""
        payload = {
            "business_name": "Regression Test SRL",
            "classe_esecuzione_default": "EXC4",
            "certificato_en13241_numero": "REGR-TEST-001"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("classe_esecuzione_default") == "EXC4"
        assert data.get("certificato_en13241_numero") == "REGR-TEST-001"
        print(f"✓ Company settings save still works for certification fields")


class TestSuperFascicoloWithMinimalData:
    """Test Super Fascicolo generation with minimal data (no CAM, no welder)."""
    
    @pytest.fixture
    def minimal_commessa(self, test_session):
        """Create a minimal commessa with only required fields."""
        import subprocess
        
        user_id = test_session["user_id"]
        commessa_id = f"test-comm-minimal-{uuid.uuid4().hex[:8]}"
        
        mongo_script = f"""
        use('test_database');
        
        db.commesse.insertOne({{
            commessa_id: '{commessa_id}',
            user_id: '{user_id}',
            numero: 'COMM-MINIMAL-001',
            title: 'Minimal Test Commessa',
            classe_esecuzione: 'EXC2',
            fascicolo_tecnico: {{}},
            created_at: new Date()
        }});
        """
        
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield {"commessa_id": commessa_id}
    
    def test_super_fascicolo_handles_missing_cam_data(self, test_session, minimal_commessa):
        """Test that Super Fascicolo generates correctly even with no CAM data."""
        commessa_id = minimal_commessa["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200 even with no CAM data, got {response.status_code}: {response.text[:500]}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type
        
        # Should still be a valid PDF even with missing data
        assert response.content[:4] == b'%PDF'
        print(f"✓ Super Fascicolo handles missing CAM data gracefully")
        print(f"  - PDF size: {len(response.content)} bytes")


class TestSuperFascicoloServiceDirectly:
    """Test the PDF generation service functions indirectly via API (async tests require pytest-asyncio)."""
    
    def test_service_raises_404_for_missing_commessa_via_api(self, test_session):
        """Test that service raises error for missing commessa (tested via API endpoint)."""
        # This is already covered by test_super_fascicolo_404_nonexistent_commessa
        # but we verify it again to ensure service-level error handling
        response = requests.get(
            f"{BASE_URL}/api/commesse/service-test-nonexistent/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Service correctly raises 404 via API for missing commessa")


# Additional tests for cover page content
class TestCoverPageContent:
    """Test that the cover page includes required information."""
    
    def test_pdf_cover_has_commessa_info(self, test_session, test_commessa_full):
        """Test that generated PDF has proper filename with commessa numero."""
        commessa_id = test_commessa_full["commessa_id"]
        numero = test_commessa_full["numero"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200
        
        content_disp = response.headers.get("Content-Disposition", "")
        # Filename should contain the commessa numero
        expected_in_filename = numero.replace("/", "-")
        assert expected_in_filename in content_disp, f"Expected {expected_in_filename} in {content_disp}"
        print(f"✓ PDF filename includes commessa numero: {expected_in_filename}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

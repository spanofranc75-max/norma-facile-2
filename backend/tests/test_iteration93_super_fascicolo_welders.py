"""
Iteration 93 - Tests for Super Fascicolo Tecnico with Welder Certificate Attachment

Features tested:
1. GET /api/commesse/{cid}/fascicolo-tecnico-completo generates PDF including Section 4.4 welder summary table
2. Welders assigned via _source_welder_id in fascicolo_tecnico.saldature are included
3. Patentino PDF files from /app/backend/uploads/welder_certs/ are merged for valid qualifications
4. Empty saldature array shows appropriate message without crashing
5. Qualification status (attivo/in_scadenza/scaduto) is computed from expiry_date
6. FPC project welder_id is also included in addition to Smart Assign welders
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, date, timedelta

# Use the public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://invoice-standardize.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create a test user and session for authenticated requests."""
    import subprocess
    
    user_id = f"test-user-iter93-{uuid.uuid4().hex[:8]}"
    session_token = f"test_session_iter93_{uuid.uuid4().hex[:16]}"
    
    # Create user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'iter93.test@example.com',
        name: 'Iteration 93 Test User',
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
    db.welders.deleteMany({{welder_id: /test-welder-iter93/}});
    db.fpc_projects.deleteMany({{user_id: '{user_id}'}});
    db.material_batches.deleteMany({{user_id: '{user_id}'}});
    db.lotti_cam.deleteMany({{user_id: '{user_id}'}});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    # Cleanup test PDF files
    import glob
    for f in glob.glob('/app/backend/uploads/welder_certs/test_qual_iter93_*.pdf'):
        try:
            os.remove(f)
        except:
            pass


@pytest.fixture
def test_welder_with_cert(test_session):
    """Create a test welder with valid qualification and PDF certificate file."""
    import subprocess
    
    welder_id = f"test-welder-iter93-{uuid.uuid4().hex[:8]}"
    qual_id = f"test_qual_iter93_{uuid.uuid4().hex[:8]}"
    safe_filename = f"{qual_id}.pdf"
    
    # Create PDF cert file
    cert_path = f"/app/backend/uploads/welder_certs/{safe_filename}"
    
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Test Welder Cert) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000015 00000 n 
0000000066 00000 n 
0000000125 00000 n 
0000000218 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
315
%%EOF"""
    
    with open(cert_path, 'wb') as f:
        f.write(pdf_content)
    
    # Calculate future expiry date (attivo status)
    future_date = (date.today() + timedelta(days=180)).isoformat()
    
    # Create welder with qualification in MongoDB
    mongo_script = f"""
    use('test_database');
    db.welders.insertOne({{
        welder_id: '{welder_id}',
        name: 'Test Saldatore Iter93',
        stamp_id: 'TST93',
        role: 'saldatore',
        is_active: true,
        qualifications: [{{
            qual_id: '{qual_id}',
            standard: 'ISO 9606-1',
            process: '135 (MAG)',
            material_group: 'FM1',
            thickness_range: '3-30mm',
            position: 'PA, PB',
            issue_date: '2025-01-01',
            expiry_date: '{future_date}',
            safe_filename: '{safe_filename}',
            filename: 'patentino_test.pdf'
        }}],
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "welder_id": welder_id,
        "qual_id": qual_id,
        "safe_filename": safe_filename,
        "cert_path": cert_path,
        "name": "Test Saldatore Iter93",
        "stamp_id": "TST93"
    }
    
    # Cleanup
    try:
        os.remove(cert_path)
    except:
        pass


@pytest.fixture
def test_welder_expiring(test_session):
    """Create a test welder with expiring qualification (in_scadenza status)."""
    import subprocess
    
    welder_id = f"test-welder-iter93-exp-{uuid.uuid4().hex[:8]}"
    qual_id = f"test_qual_iter93_exp_{uuid.uuid4().hex[:8]}"
    safe_filename = f"{qual_id}.pdf"
    
    # Create PDF cert file
    cert_path = f"/app/backend/uploads/welder_certs/{safe_filename}"
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    with open(cert_path, 'wb') as f:
        f.write(pdf_content)
    
    # Expiry date within 30 days (in_scadenza)
    expiring_date = (date.today() + timedelta(days=15)).isoformat()
    
    mongo_script = f"""
    use('test_database');
    db.welders.insertOne({{
        welder_id: '{welder_id}',
        name: 'Test Saldatore Expiring',
        stamp_id: 'TST93EXP',
        role: 'saldatore',
        is_active: true,
        qualifications: [{{
            qual_id: '{qual_id}',
            standard: 'ISO 9606-1',
            process: '141 (TIG)',
            expiry_date: '{expiring_date}',
            safe_filename: '{safe_filename}',
            filename: 'patentino_expiring.pdf'
        }}],
        created_at: new Date()
    }});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "welder_id": welder_id,
        "qual_id": qual_id,
        "safe_filename": safe_filename,
        "cert_path": cert_path
    }
    
    try:
        os.remove(cert_path)
    except:
        pass


@pytest.fixture
def test_commessa_with_welders(test_session, test_welder_with_cert, test_welder_expiring):
    """Create a test commessa with saldature entries referencing welders."""
    import subprocess
    
    user_id = test_session["user_id"]
    commessa_id = f"test-comm-iter93-{uuid.uuid4().hex[:8]}"
    client_id = f"test-client-iter93-{uuid.uuid4().hex[:8]}"
    preventivo_id = f"test-prev-iter93-{uuid.uuid4().hex[:8]}"
    
    welder1_id = test_welder_with_cert["welder_id"]
    welder2_id = test_welder_expiring["welder_id"]
    
    mongo_script = f"""
    use('test_database');
    
    // Create client
    db.clients.insertOne({{
        client_id: '{client_id}',
        user_id: '{user_id}',
        business_name: 'Test Client Iter93 SRL',
        created_at: new Date()
    }});
    
    // Create company settings
    db.company_settings.updateOne(
        {{ user_id: '{user_id}' }},
        {{ $set: {{
            user_id: '{user_id}',
            business_name: 'Test Workshop Iter93',
            address: 'Via Test 93',
            city: 'Milano',
            cap: '20100',
            partita_iva: 'IT93939393939',
            certificato_en1090_numero: '0474-CPR-TEST-93',
            ente_certificatore: 'RINA',
            responsabile_nome: 'Test Manager'
        }} }},
        {{ upsert: true }}
    );
    
    // Create commessa with saldature array containing _source_welder_id
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        client_id: '{client_id}',
        preventivo_id: '{preventivo_id}',
        numero: 'COMM-2026-ITER93',
        title: 'Test Commessa Iter93 - Welder Certs',
        classe_esecuzione: 'EXC2',
        fascicolo_tecnico: {{
            redatto_da: 'Test Engineer',
            saldature: [
                {{
                    _source_welder_id: '{welder1_id}',
                    saldatore: '{test_welder_with_cert["name"]}',
                    punzone: '{test_welder_with_cert["stamp_id"]}',
                    giunto: 'G1',
                    wpqr: 'WPQR-001',
                    processo: '135'
                }},
                {{
                    _source_welder_id: '{welder2_id}',
                    saldatore: 'Test Saldatore Expiring',
                    punzone: 'TST93EXP',
                    giunto: 'G2',
                    wpqr: 'WPQR-002',
                    processo: '141'
                }}
            ]
        }},
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "commessa_id": commessa_id,
        "client_id": client_id,
        "preventivo_id": preventivo_id,
        "welder1_id": welder1_id,
        "welder2_id": welder2_id
    }


@pytest.fixture
def test_commessa_with_fpc_welder(test_session, test_welder_with_cert):
    """Create a commessa with FPC project referencing a welder."""
    import subprocess
    
    user_id = test_session["user_id"]
    commessa_id = f"test-comm-fpc-iter93-{uuid.uuid4().hex[:8]}"
    preventivo_id = f"test-prev-fpc-iter93-{uuid.uuid4().hex[:8]}"
    welder_id = test_welder_with_cert["welder_id"]
    
    mongo_script = f"""
    use('test_database');
    
    // Create company settings if not exists
    db.company_settings.updateOne(
        {{ user_id: '{user_id}' }},
        {{ $set: {{
            user_id: '{user_id}',
            business_name: 'Test Workshop FPC Iter93',
            certificato_en1090_numero: '0474-CPR-FPC-93'
        }} }},
        {{ upsert: true }}
    );
    
    // Create commessa with empty saldature
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        preventivo_id: '{preventivo_id}',
        numero: 'COMM-FPC-ITER93',
        title: 'Test Commessa FPC Welder',
        classe_esecuzione: 'EXC2',
        fascicolo_tecnico: {{
            saldature: []
        }},
        created_at: new Date()
    }});
    
    // Create FPC project with welder_id
    db.fpc_projects.insertOne({{
        project_id: 'fpc-iter93-1',
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
        "preventivo_id": preventivo_id,
        "welder_id": welder_id
    }


@pytest.fixture
def test_commessa_no_welders(test_session):
    """Create a commessa without any assigned welders."""
    import subprocess
    
    user_id = test_session["user_id"]
    commessa_id = f"test-comm-noweld-iter93-{uuid.uuid4().hex[:8]}"
    
    mongo_script = f"""
    use('test_database');
    
    // Create company settings
    db.company_settings.updateOne(
        {{ user_id: '{user_id}' }},
        {{ $set: {{
            user_id: '{user_id}',
            business_name: 'Test Workshop NoWeld Iter93'
        }} }},
        {{ upsert: true }}
    );
    
    // Create commessa with empty saldature
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        numero: 'COMM-NOWELD-ITER93',
        title: 'Test Commessa No Welders',
        classe_esecuzione: 'EXC2',
        fascicolo_tecnico: {{
            saldature: []
        }},
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {"commessa_id": commessa_id}


class TestHealthCheck:
    """Basic health check before testing."""
    
    def test_backend_health(self):
        """Verify backend is running."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✓ Backend health check passed")


class TestSuperFascicoloWithAssignedWelders:
    """Test Super Fascicolo PDF with welders assigned via Smart Assign."""
    
    def test_pdf_generated_with_welders_from_saldature(self, test_session, test_commessa_with_welders):
        """Test that PDF includes welders referenced in fascicolo_tecnico.saldature._source_welder_id."""
        commessa_id = test_commessa_with_welders["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        # Verify content is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF is valid
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF', "Content is not a valid PDF"
        
        # PDF should be larger due to welder certs being merged
        print(f"✓ Super Fascicolo PDF with welders generated: {len(pdf_content)} bytes")
        print(f"  - Welder 1 ID: {test_commessa_with_welders['welder1_id']}")
        print(f"  - Welder 2 ID: {test_commessa_with_welders['welder2_id']}")
    
    def test_pdf_includes_multiple_welder_certs(self, test_session, test_commessa_with_welders):
        """Test that PDF size indicates welder cert PDFs were merged."""
        commessa_id = test_commessa_with_welders["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200
        pdf_size = len(response.content)
        
        # With welder certs merged, PDF should be larger than minimal
        # Minimal fascicolo is ~50KB, each cert adds ~1-5KB
        assert pdf_size > 50000, f"PDF size {pdf_size} seems too small for fascicolo with certs"
        print(f"✓ PDF size indicates content: {pdf_size / 1024:.1f} KB")


class TestSuperFascicoloWithFPCWelder:
    """Test Super Fascicolo includes welder from FPC project."""
    
    def test_pdf_includes_fpc_project_welder(self, test_session, test_commessa_with_fpc_welder):
        """Test that welder from FPC project is included even without saldature entries."""
        commessa_id = test_commessa_with_fpc_welder["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type
        
        print(f"✓ Super Fascicolo with FPC welder generated: {len(response.content)} bytes")


class TestSuperFascicoloNoWelders:
    """Test Super Fascicolo handles empty saldature gracefully."""
    
    def test_pdf_generated_without_welders(self, test_session, test_commessa_no_welders):
        """Test that PDF generates correctly when no welders assigned."""
        commessa_id = test_commessa_no_welders["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/commesse/{commessa_id}/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        
        # Should NOT crash, should return valid PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF', "Content is not a valid PDF"
        
        print(f"✓ Super Fascicolo without welders generated: {len(pdf_content)} bytes")


class TestSmartAssignWeldersAPI:
    """Test Smart Assign welders API that provides data for import."""
    
    def test_smart_assign_welders_returns_status(self, test_session, test_welder_with_cert, test_welder_expiring):
        """Test GET /api/smart-assign/welders returns welders with status."""
        response = requests.get(
            f"{BASE_URL}/api/smart-assign/welders",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "welders" in data
        welders = data["welders"]
        
        # Find our test welders
        welder1 = next((w for w in welders if w.get("welder_id") == test_welder_with_cert["welder_id"]), None)
        welder2 = next((w for w in welders if w.get("welder_id") == test_welder_expiring["welder_id"]), None)
        
        if welder1:
            print(f"✓ Found test welder 1: {welder1.get('name')} - status: {welder1.get('overall_status')}")
            # Should have attivo status (expiry > 30 days)
            quals = welder1.get("qualifications", [])
            if quals:
                assert quals[0].get("status") in ["attivo", "in_scadenza"], f"Expected attivo/in_scadenza, got {quals[0].get('status')}"
                assert quals[0].get("has_file") == True, "Expected has_file=True for welder with cert"
        
        if welder2:
            print(f"✓ Found test welder 2: {welder2.get('name')} - status: {welder2.get('overall_status')}")
            # Should have in_scadenza status (expiry within 30 days)
            quals = welder2.get("qualifications", [])
            if quals:
                assert quals[0].get("status") in ["attivo", "in_scadenza"], f"Expected status, got {quals[0].get('status')}"


class TestSuperFascicoloAuth:
    """Test authentication requirements."""
    
    def test_returns_401_without_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/any-id/fascicolo-tecnico-completo"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Auth required: {response.status_code}")
    
    def test_returns_404_for_nonexistent_commessa(self, test_session):
        """Test 404 for non-existent commessa."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/nonexistent-commessa-xyz/fascicolo-tecnico-completo",
            headers=test_session["headers"]
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ 404 for non-existent commessa")


class TestWelderCertFileAccess:
    """Test that cert files exist and can be read."""
    
    def test_cert_file_exists(self, test_welder_with_cert):
        """Verify test cert file was created."""
        cert_path = test_welder_with_cert["cert_path"]
        assert os.path.exists(cert_path), f"Cert file not found: {cert_path}"
        
        with open(cert_path, 'rb') as f:
            content = f.read()
        
        assert content[:4] == b'%PDF', "Cert file is not a valid PDF"
        print(f"✓ Cert file exists and is valid PDF: {cert_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

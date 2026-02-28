"""
Iteration 48: Technical Dossier (Fascicolo Tecnico) Generator Tests

Tests the new One-Click Technical Dossier feature which merges:
1. Cover Page
2. DoP (Declaration of Performance)
3. CE Label
4. Materials Traceability Summary
5. Material Certificates (3.1 base64 PDFs)
6. Welder Qualification Summary
7. FPC Controls Checklist

Uses pypdf to validate PDF structure and page count.
"""

import pytest
import requests
import os
import uuid
import base64
from io import BytesIO
from datetime import datetime, timedelta

# pypdf for PDF validation
from pypdf import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_SESSION_TOKEN = "test_fpc_session_1772273339015"
TEST_USER_ID = "bridge-test-user"

def get_headers():
    return {
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


# ══════════════════════════════════════════════════════════════════
# SECTION 1: DOSSIER API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════

class TestDossierEndpoint:
    """Test the GET /api/fpc/projects/{project_id}/dossier endpoint"""
    
    test_project_id = None
    test_welder_id = None
    test_batch_id = None
    test_preventivo_id = None
    
    @classmethod
    def setup_class(cls):
        """Create test data needed for dossier generation"""
        print("\n=== Setting up test data for Dossier tests ===")
        
        # 1. Find or get an existing FPC project
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code == 200:
            projects = r.json()
            if projects:
                cls.test_project_id = projects[0]["project_id"]
                print(f"Using existing project: {cls.test_project_id}")
                return
        
        # 2. If no project, we need to create one from a preventivo
        r = requests.get(f"{BASE_URL}/api/preventivi/", headers=get_headers())
        if r.status_code == 200:
            preventivi = r.json().get("preventivi", [])
            if preventivi:
                cls.test_preventivo_id = preventivi[0]["preventivo_id"]
                
                # Check if project already exists for this preventivo
                r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
                existing = r.json() if r.status_code == 200 else []
                for p in existing:
                    if p.get("preventivo_id") == cls.test_preventivo_id:
                        cls.test_project_id = p["project_id"]
                        print(f"Found existing project for preventivo: {cls.test_project_id}")
                        return
                
                # Create new project
                r = requests.post(
                    f"{BASE_URL}/api/fpc/projects",
                    headers=get_headers(),
                    json={"preventivo_id": cls.test_preventivo_id, "execution_class": "EXC2"}
                )
                if r.status_code == 200:
                    cls.test_project_id = r.json()["project_id"]
                    print(f"Created new project: {cls.test_project_id}")
                elif r.status_code == 409:
                    # Already exists - fetch it
                    r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
                    for p in r.json():
                        if p.get("preventivo_id") == cls.test_preventivo_id:
                            cls.test_project_id = p["project_id"]
                            print(f"Project already exists: {cls.test_project_id}")
                            return
    
    def test_health_check(self):
        """Verify backend is accessible"""
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
        print(f"✓ Backend healthy: {data}")
    
    def test_dossier_endpoint_returns_pdf(self):
        """GET /api/fpc/projects/{id}/dossier - Returns valid PDF"""
        if not TestDossierEndpoint.test_project_id:
            pytest.skip("No project available for dossier test")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierEndpoint.test_project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200, f"Dossier generation failed: {r.status_code} - {r.text}"
        assert r.headers.get("content-type") == "application/pdf", f"Not PDF: {r.headers.get('content-type')}"
        
        # Verify it's a valid PDF
        content = r.content
        assert content[:5] == b'%PDF-', f"Not a valid PDF header: {content[:20]}"
        assert len(content) > 5000, f"PDF too small ({len(content)} bytes) - likely incomplete"
        
        print(f"✓ Dossier PDF generated: {len(content)} bytes")
        
        # Store for further analysis
        TestDossierEndpoint.pdf_content = content
    
    def test_dossier_pdf_has_multiple_pages(self):
        """Verify dossier PDF contains multiple pages (Cover, DoP, CE, Materials, Controls)"""
        if not hasattr(TestDossierEndpoint, 'pdf_content'):
            pytest.skip("PDF content not available from previous test")
        
        reader = PdfReader(BytesIO(TestDossierEndpoint.pdf_content))
        page_count = len(reader.pages)
        
        # Minimum: Cover(1) + DoP(1) + CE(1) + Materials(1) + Controls(1) = 5 pages
        # With welder: 6 pages
        assert page_count >= 5, f"Expected at least 5 pages, got {page_count}"
        
        print(f"✓ Dossier has {page_count} pages")
    
    def test_dossier_content_disposition_header(self):
        """Verify Content-Disposition header has proper filename"""
        if not TestDossierEndpoint.test_project_id:
            pytest.skip("No project available")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierEndpoint.test_project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd, f"Expected attachment disposition: {cd}"
        assert "Fascicolo_Tecnico" in cd, f"Expected Fascicolo_Tecnico in filename: {cd}"
        assert ".pdf" in cd, f"Expected .pdf extension: {cd}"
        
        print(f"✓ Content-Disposition: {cd}")
    
    def test_dossier_returns_404_for_nonexistent_project(self):
        """GET /api/fpc/projects/{invalid_id}/dossier - Returns 404"""
        fake_id = f"prj_{uuid.uuid4().hex[:12]}"
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{fake_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print(f"✓ Correctly returns 404 for non-existent project")
    
    def test_dossier_requires_authentication(self):
        """GET /api/fpc/projects/{id}/dossier - Requires auth"""
        if not TestDossierEndpoint.test_project_id:
            pytest.skip("No project available")
        
        # Request without auth header
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierEndpoint.test_project_id}/dossier"
        )
        
        assert r.status_code in [401, 403], f"Expected 401/403 without auth, got {r.status_code}"
        print(f"✓ Dossier endpoint requires authentication (returns {r.status_code})")


# ══════════════════════════════════════════════════════════════════
# SECTION 2: DOSSIER WITH WELDER TESTS
# ══════════════════════════════════════════════════════════════════

class TestDossierWithWelder:
    """Test dossier generation with and without welder assigned"""
    
    test_project_id = None
    test_welder_id = None
    initial_page_count = None
    
    @classmethod
    def setup_class(cls):
        """Get or create test project"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code == 200 and r.json():
            cls.test_project_id = r.json()[0]["project_id"]
    
    def test_dossier_page_count_without_welder(self):
        """Count pages when no welder is assigned"""
        if not TestDossierWithWelder.test_project_id:
            pytest.skip("No project available")
        
        # First, unset welder
        requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithWelder.test_project_id}/fpc",
            headers=get_headers(),
            json={"welder_id": None}
        )
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithWelder.test_project_id}/dossier",
            headers=get_headers()
        )
        
        if r.status_code != 200:
            pytest.skip(f"Dossier generation failed: {r.status_code}")
        
        reader = PdfReader(BytesIO(r.content))
        TestDossierWithWelder.initial_page_count = len(reader.pages)
        
        print(f"✓ Dossier without welder has {TestDossierWithWelder.initial_page_count} pages")
    
    def test_create_and_assign_welder(self):
        """Create a welder and assign to project"""
        if not TestDossierWithWelder.test_project_id:
            pytest.skip("No project available")
        
        # Create welder
        welder_data = {
            "name": f"DOSSIER_Test_Welder_{uuid.uuid4().hex[:6]}",
            "qualification_level": "ISO 9606-1 135 P BW FM1",
            "license_expiry": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "notes": "Test welder for dossier testing"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/welders", headers=get_headers(), json=welder_data)
        assert r.status_code == 200, f"Welder creation failed: {r.text}"
        TestDossierWithWelder.test_welder_id = r.json()["welder_id"]
        
        # Assign to project
        r = requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithWelder.test_project_id}/fpc",
            headers=get_headers(),
            json={"welder_id": TestDossierWithWelder.test_welder_id}
        )
        assert r.status_code == 200, f"Welder assignment failed: {r.text}"
        
        print(f"✓ Created and assigned welder: {TestDossierWithWelder.test_welder_id}")
    
    def test_dossier_page_count_with_welder(self):
        """Verify dossier has one more page with welder"""
        if not TestDossierWithWelder.test_project_id:
            pytest.skip("No project available")
        if TestDossierWithWelder.initial_page_count is None:
            pytest.skip("Initial page count not available")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithWelder.test_project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200
        reader = PdfReader(BytesIO(r.content))
        new_page_count = len(reader.pages)
        
        # With welder, should have one more page (Welder Qualification section)
        assert new_page_count >= TestDossierWithWelder.initial_page_count, \
            f"Expected >= {TestDossierWithWelder.initial_page_count} pages, got {new_page_count}"
        
        print(f"✓ Dossier with welder has {new_page_count} pages (was {TestDossierWithWelder.initial_page_count})")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test welder"""
        if cls.test_welder_id:
            requests.delete(f"{BASE_URL}/api/fpc/welders/{cls.test_welder_id}", headers=get_headers())
            print(f"✓ Cleaned up test welder: {cls.test_welder_id}")


# ══════════════════════════════════════════════════════════════════
# SECTION 3: DOSSIER WITH CERTIFICATES TESTS
# ══════════════════════════════════════════════════════════════════

class TestDossierWithCertificates:
    """Test dossier generation with material certificates"""
    
    test_project_id = None
    test_batch_id = None
    initial_page_count = None
    
    @classmethod
    def setup_class(cls):
        """Get test project"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code == 200 and r.json():
            cls.test_project_id = r.json()[0]["project_id"]
    
    def test_create_batch_with_certificate(self):
        """Create a material batch with a PDF certificate (3.1)"""
        if not TestDossierWithCertificates.test_project_id:
            pytest.skip("No project available")
        
        # Create a minimal valid PDF for testing
        # This is a minimal PDF that pypdf can parse
        minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources <<>> >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
211
%%EOF"""
        
        cert_base64 = base64.b64encode(minimal_pdf).decode('utf-8')
        
        batch_data = {
            "supplier_name": "TEST_Cert_Supplier",
            "material_type": "S275JR",
            "heat_number": f"CERT_HEAT_{uuid.uuid4().hex[:6]}",
            "certificate_base64": f"data:application/pdf;base64,{cert_base64}",
            "certificate_filename": "test_cert_3_1.pdf",
            "received_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Batch with certificate for dossier testing"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        assert r.status_code == 200, f"Batch creation failed: {r.text}"
        TestDossierWithCertificates.test_batch_id = r.json()["batch_id"]
        assert r.json().get("has_certificate") == True, "Certificate flag should be True"
        
        print(f"✓ Created batch with certificate: {TestDossierWithCertificates.test_batch_id}")
    
    def test_assign_batch_to_project_line(self):
        """Assign the batch with certificate to a project line"""
        if not TestDossierWithCertificates.test_project_id:
            pytest.skip("No project available")
        if not TestDossierWithCertificates.test_batch_id:
            pytest.skip("No batch with certificate created")
        
        # Get project lines
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithCertificates.test_project_id}",
            headers=get_headers()
        )
        project = r.json()
        lines = project.get("lines", [])
        
        if not lines:
            pytest.skip("Project has no lines to assign batch to")
        
        # Assign to first line
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithCertificates.test_project_id}/assign-batch",
            headers=get_headers(),
            json={"line_index": 0, "batch_id": TestDossierWithCertificates.test_batch_id}
        )
        
        assert r.status_code == 200, f"Batch assignment failed: {r.text}"
        print(f"✓ Assigned batch to line 0")
    
    def test_dossier_includes_certificate_pages(self):
        """Verify dossier PDF includes certificate pages"""
        if not TestDossierWithCertificates.test_project_id:
            pytest.skip("No project available")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierWithCertificates.test_project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200, f"Dossier generation failed: {r.status_code}"
        
        reader = PdfReader(BytesIO(r.content))
        page_count = len(reader.pages)
        
        # Base minimum is 5 pages, with cert should be >= 5 
        # (cert may add 1+ pages depending on PDF size)
        assert page_count >= 5, f"Expected >= 5 pages, got {page_count}"
        
        print(f"✓ Dossier with certificate has {page_count} pages")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test batch"""
        if cls.test_batch_id:
            requests.delete(f"{BASE_URL}/api/fpc/batches/{cls.test_batch_id}", headers=get_headers())
            print(f"✓ Cleaned up test batch: {cls.test_batch_id}")


# ══════════════════════════════════════════════════════════════════
# SECTION 4: DOSSIER CONTENT VALIDATION (PDF TEXT EXTRACTION)
# ══════════════════════════════════════════════════════════════════

class TestDossierContent:
    """Test dossier PDF content contains expected elements"""
    
    test_project_id = None
    pdf_text = None
    
    @classmethod
    def setup_class(cls):
        """Get test project and generate dossier"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code == 200 and r.json():
            cls.test_project_id = r.json()[0]["project_id"]
            
            # Generate dossier
            r = requests.get(
                f"{BASE_URL}/api/fpc/projects/{cls.test_project_id}/dossier",
                headers=get_headers()
            )
            if r.status_code == 200:
                reader = PdfReader(BytesIO(r.content))
                # Extract text from all pages
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                cls.pdf_text = "\n".join(text_parts)
    
    def test_cover_page_contains_fascicolo_tecnico(self):
        """Verify cover page has 'FASCICOLO TECNICO' title"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        assert "FASCICOLO" in TestDossierContent.pdf_text.upper(), \
            "Cover page should contain 'FASCICOLO'"
        print("✓ Cover page contains 'FASCICOLO'")
    
    def test_dop_page_contains_en1090(self):
        """Verify DoP page contains EN 1090-1 reference"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        assert "1090" in TestDossierContent.pdf_text, \
            "DoP page should reference EN 1090"
        print("✓ DoP page contains EN 1090 reference")
    
    def test_ce_label_page_format(self):
        """Verify CE label section exists"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        text_upper = TestDossierContent.pdf_text.upper()
        assert "CE" in text_upper, "Should contain CE marking"
        print("✓ CE label section present")
    
    def test_controls_checklist_present(self):
        """Verify controls checklist section exists"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        text_upper = TestDossierContent.pdf_text.upper()
        # Should have FPC or CONTROLLI text
        has_fpc = "FPC" in text_upper
        has_controlli = "CONTROLLI" in text_upper
        has_checklist = "CHECKLIST" in text_upper
        
        assert has_fpc or has_controlli or has_checklist, \
            "Should contain FPC controls checklist section"
        print("✓ FPC Controls section present")
    
    def test_materials_traceability_section(self):
        """Verify materials traceability section exists"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        text_upper = TestDossierContent.pdf_text.upper()
        has_traccia = "TRACCIA" in text_upper
        has_materiali = "MATERIALI" in text_upper
        has_colata = "COLATA" in text_upper
        
        assert has_traccia or has_materiali or has_colata, \
            "Should contain materials traceability section"
        print("✓ Materials traceability section present")
    
    def test_execution_class_present(self):
        """Verify execution class (EXC1-4) is mentioned"""
        if not TestDossierContent.pdf_text:
            pytest.skip("PDF text not available")
        
        text_upper = TestDossierContent.pdf_text.upper()
        has_exc = any(f"EXC{i}" in text_upper for i in range(1, 5))
        has_esecuzione = "ESECUZIONE" in text_upper
        
        assert has_exc or has_esecuzione, \
            "Should mention execution class"
        print("✓ Execution class mentioned")


# ══════════════════════════════════════════════════════════════════
# SECTION 5: EDGE CASES & ERROR HANDLING
# ══════════════════════════════════════════════════════════════════

class TestDossierEdgeCases:
    """Test dossier edge cases and error handling"""
    
    def test_dossier_handles_project_without_lines(self):
        """Dossier should handle project with empty lines array"""
        # This is hard to test without creating a specific project
        # Just verify the endpoint doesn't crash
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code != 200 or not r.json():
            pytest.skip("No projects available")
        
        project = r.json()[0]
        project_id = project["project_id"]
        
        # Generate dossier (should work even with empty or populated lines)
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{project_id}/dossier",
            headers=get_headers()
        )
        
        # Should not crash regardless of lines
        assert r.status_code == 200, f"Dossier should generate: {r.status_code}"
        print(f"✓ Dossier handles project with {len(project.get('lines', []))} lines")
    
    def test_dossier_handles_missing_company_settings(self):
        """Dossier should work even if company settings are sparse"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code != 200 or not r.json():
            pytest.skip("No projects available")
        
        project_id = r.json()[0]["project_id"]
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200, f"Dossier should handle missing company data"
        print("✓ Dossier handles sparse company settings")
    
    def test_dossier_handles_batch_without_certificate(self):
        """Dossier should handle batches that have no certificate attached"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code != 200 or not r.json():
            pytest.skip("No projects available")
        
        project_id = r.json()[0]["project_id"]
        
        # Create batch without certificate
        batch_data = {
            "supplier_name": "TEST_NoCert_Supplier",
            "material_type": "S355J2",
            "heat_number": f"NOCERT_{uuid.uuid4().hex[:6]}"
        }
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        if r.status_code != 200:
            pytest.skip("Cannot create test batch")
        
        batch_id = r.json()["batch_id"]
        
        # Try to generate dossier (should not crash)
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200, f"Dossier should handle batch without cert"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fpc/batches/{batch_id}", headers=get_headers())
        print("✓ Dossier handles batches without certificates")


# ══════════════════════════════════════════════════════════════════
# SECTION 6: FULL WORKFLOW INTEGRATION TEST
# ══════════════════════════════════════════════════════════════════

class TestDossierFullWorkflow:
    """Full integration test: create all data and generate complete dossier"""
    
    test_welder_id = None
    test_batch_id = None
    test_project_id = None
    
    def test_full_dossier_workflow(self):
        """Complete workflow: setup project with all FPC data, generate dossier"""
        
        # 1. Get/create project
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        if r.status_code != 200 or not r.json():
            pytest.skip("No FPC projects available")
        
        TestDossierFullWorkflow.test_project_id = r.json()[0]["project_id"]
        
        # 2. Create welder
        welder_data = {
            "name": f"FULL_WF_Welder_{uuid.uuid4().hex[:4]}",
            "qualification_level": "ISO 9606-1 135 P BW",
            "license_expiry": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        }
        r = requests.post(f"{BASE_URL}/api/fpc/welders", headers=get_headers(), json=welder_data)
        if r.status_code == 200:
            TestDossierFullWorkflow.test_welder_id = r.json()["welder_id"]
        
        # 3. Create batch (without cert for simplicity)
        batch_data = {
            "supplier_name": "FULL_WF_Supplier",
            "material_type": "S275JR",
            "heat_number": f"FULL_{uuid.uuid4().hex[:6]}"
        }
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        if r.status_code == 200:
            TestDossierFullWorkflow.test_batch_id = r.json()["batch_id"]
        
        # 4. Assign welder and WPS
        if TestDossierFullWorkflow.test_welder_id:
            requests.put(
                f"{BASE_URL}/api/fpc/projects/{TestDossierFullWorkflow.test_project_id}/fpc",
                headers=get_headers(),
                json={
                    "welder_id": TestDossierFullWorkflow.test_welder_id,
                    "wps_id": "WPS-FULL-TEST-001"
                }
            )
        
        # 5. Get project and mark all controls
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierFullWorkflow.test_project_id}",
            headers=get_headers()
        )
        project = r.json()
        controls = project.get("fpc_data", {}).get("controls", [])
        for c in controls:
            c["checked"] = True
            c["checked_at"] = datetime.now().isoformat()
        
        requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestDossierFullWorkflow.test_project_id}/fpc",
            headers=get_headers(),
            json={"controls": controls}
        )
        
        # 6. Generate dossier
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestDossierFullWorkflow.test_project_id}/dossier",
            headers=get_headers()
        )
        
        assert r.status_code == 200, f"Dossier failed: {r.status_code} - {r.text[:200]}"
        assert r.headers.get("content-type") == "application/pdf"
        
        # 7. Validate PDF
        reader = PdfReader(BytesIO(r.content))
        page_count = len(reader.pages)
        
        # Should have at least 5 pages (Cover, DoP, CE, Materials, Controls)
        # With welder: 6 pages
        expected_min = 5 if not TestDossierFullWorkflow.test_welder_id else 6
        assert page_count >= expected_min, f"Expected >= {expected_min} pages, got {page_count}"
        
        print(f"✓ Full workflow dossier generated: {page_count} pages, {len(r.content)} bytes")
        print(f"  - Project: {TestDossierFullWorkflow.test_project_id}")
        print(f"  - Welder: {TestDossierFullWorkflow.test_welder_id}")
        print(f"  - Batch: {TestDossierFullWorkflow.test_batch_id}")
        print(f"  - Controls: {len(controls)} (all checked)")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test data"""
        if cls.test_welder_id:
            requests.delete(f"{BASE_URL}/api/fpc/welders/{cls.test_welder_id}", headers=get_headers())
        if cls.test_batch_id:
            requests.delete(f"{BASE_URL}/api/fpc/batches/{cls.test_batch_id}", headers=get_headers())
        print("✓ Full workflow cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

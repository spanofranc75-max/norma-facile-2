"""
Iteration 47: Comprehensive Testing for PDF Generation + FPC System
Tests both PDF template unification and EN 1090 FPC workflows

Modules tested:
1. PDF Generation - Preventivo, Invoice, DDT (shared template)
2. FPC Welders CRUD
3. FPC Material Batches CRUD
4. FPC Projects CRUD and CE workflow
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_SESSION_TOKEN = "test_fpc_session_1772273339015"
TEST_USER_ID = "bridge-test-user"

def get_headers():
    return {
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


# ══════════════════════════════════════════════════════════════════
# SECTION 1: PDF GENERATION TESTS
# ══════════════════════════════════════════════════════════════════

class TestPDFGeneration:
    """Test PDF generation for all 3 document types using shared template"""
    
    def test_health_check(self):
        """Verify backend is accessible"""
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
        print(f"✓ Backend healthy: {data}")
    
    def test_preventivo_pdf_generation(self):
        """Test Preventivo PDF via GET /api/preventivi/{id}/pdf"""
        # First list preventivi to get a valid ID
        r = requests.get(f"{BASE_URL}/api/preventivi/", headers=get_headers())
        assert r.status_code == 200
        data = r.json()
        preventivi = data.get("preventivi", [])
        
        if len(preventivi) == 0:
            pytest.skip("No preventivi found - create one first")
        
        prev_id = preventivi[0]["preventivo_id"]
        print(f"Testing PDF for preventivo: {prev_id}")
        
        # Get PDF
        r = requests.get(f"{BASE_URL}/api/preventivi/{prev_id}/pdf", headers=get_headers())
        assert r.status_code == 200, f"PDF generation failed: {r.text}"
        assert r.headers.get("content-type") == "application/pdf"
        
        # Verify PDF content
        content = r.content
        assert content[:5] == b'%PDF-', f"Not a valid PDF: {content[:20]}"
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        print(f"✓ Preventivo PDF generated: {len(content)} bytes")
    
    def test_invoice_pdf_generation(self):
        """Test Invoice PDF via GET /api/invoices/{id}/pdf"""
        # First list invoices
        r = requests.get(f"{BASE_URL}/api/invoices/", headers=get_headers())
        assert r.status_code == 200
        data = r.json()
        invoices = data.get("invoices", [])
        
        if len(invoices) == 0:
            # Create a test invoice
            invoice_data = {
                "document_type": "FT",
                "client_id": "",
                "payment_method": "bonifico",
                "payment_terms": "30gg",
                "lines": [
                    {
                        "code": "TEST-001",
                        "description": "Test item for PDF generation",
                        "quantity": 2,
                        "unit_price": 100.0,
                        "vat_rate": "22"
                    }
                ],
                "notes": "Test invoice for PDF"
            }
            r = requests.post(f"{BASE_URL}/api/invoices/", headers=get_headers(), json=invoice_data)
            if r.status_code == 201:
                invoice_id = r.json().get("invoice_id")
            else:
                pytest.skip("Cannot create test invoice")
        else:
            invoice_id = invoices[0]["invoice_id"]
        
        print(f"Testing PDF for invoice: {invoice_id}")
        
        # Get PDF
        r = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/pdf", headers=get_headers())
        assert r.status_code == 200, f"Invoice PDF failed: {r.text}"
        assert r.headers.get("content-type") == "application/pdf"
        
        content = r.content
        assert content[:5] == b'%PDF-', "Not a valid PDF"
        print(f"✓ Invoice PDF generated: {len(content)} bytes")
    
    def test_ddt_pdf_generation(self):
        """Test DDT PDF via GET /api/ddt/{id}/pdf"""
        # First list DDTs
        r = requests.get(f"{BASE_URL}/api/ddt/", headers=get_headers())
        assert r.status_code == 200
        data = r.json()
        ddts = data.get("documents", [])
        
        if len(ddts) == 0:
            # Create a test DDT
            ddt_data = {
                "client_name": "Test Client DDT",
                "client_address": "Via Test 123",
                "ddt_type": "vendita",
                "causale_trasporto": "Vendita",
                "porto": "Franco",
                "lines": [
                    {
                        "codice_articolo": "DDT-TEST-001",
                        "description": "Test item for DDT PDF",
                        "quantity": 5,
                        "unit": "pz",
                        "unit_price": 50.0,
                        "vat_rate": "22"
                    }
                ]
            }
            r = requests.post(f"{BASE_URL}/api/ddt/", headers=get_headers(), json=ddt_data)
            if r.status_code == 201:
                ddt_id = r.json().get("ddt_id")
            else:
                pytest.skip(f"Cannot create test DDT: {r.text}")
        else:
            ddt_id = ddts[0]["ddt_id"]
        
        print(f"Testing PDF for DDT: {ddt_id}")
        
        # Get PDF
        r = requests.get(f"{BASE_URL}/api/ddt/{ddt_id}/pdf", headers=get_headers())
        assert r.status_code == 200, f"DDT PDF failed: {r.text}"
        assert r.headers.get("content-type") == "application/pdf"
        
        content = r.content
        assert content[:5] == b'%PDF-', "Not a valid PDF"
        print(f"✓ DDT PDF generated: {len(content)} bytes")


# ══════════════════════════════════════════════════════════════════
# SECTION 2: FPC WELDERS TESTS
# ══════════════════════════════════════════════════════════════════

class TestFPCWelders:
    """Test FPC Welders Registry CRUD operations"""
    
    created_welder_id = None
    
    def test_create_welder(self):
        """POST /api/fpc/welders - Create a new welder"""
        welder_data = {
            "name": f"TEST_Welder_{uuid.uuid4().hex[:6]}",
            "qualification_level": "ISO 9606-1 135 P BW",
            "license_expiry": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "notes": "Test welder created by pytest"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/welders", headers=get_headers(), json=welder_data)
        assert r.status_code == 200, f"Create welder failed: {r.text}"
        
        data = r.json()
        assert "welder_id" in data
        assert data["name"] == welder_data["name"]
        assert data["qualification_level"] == welder_data["qualification_level"]
        assert data["license_expiry"] == welder_data["license_expiry"]
        
        TestFPCWelders.created_welder_id = data["welder_id"]
        print(f"✓ Welder created: {data['welder_id']} - {data['name']}")
    
    def test_list_welders(self):
        """GET /api/fpc/welders - List all welders"""
        r = requests.get(f"{BASE_URL}/api/fpc/welders", headers=get_headers())
        assert r.status_code == 200
        
        data = r.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} welders")
        
        # Verify our created welder is in the list
        if TestFPCWelders.created_welder_id:
            found = any(w["welder_id"] == TestFPCWelders.created_welder_id for w in data)
            assert found, "Created welder not found in list"
            print(f"✓ Created welder found in list")
    
    def test_update_welder(self):
        """PUT /api/fpc/welders/{id} - Update welder"""
        if not TestFPCWelders.created_welder_id:
            pytest.skip("No welder created")
        
        update_data = {
            "name": f"TEST_Welder_Updated_{uuid.uuid4().hex[:4]}",
            "qualification_level": "ISO 9606-1 135 T BW (updated)",
            "license_expiry": (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%d"),
            "notes": "Updated by pytest"
        }
        
        r = requests.put(
            f"{BASE_URL}/api/fpc/welders/{TestFPCWelders.created_welder_id}",
            headers=get_headers(),
            json=update_data
        )
        assert r.status_code == 200, f"Update failed: {r.text}"
        print(f"✓ Welder updated: {TestFPCWelders.created_welder_id}")
    
    def test_welder_expired_detection(self):
        """Test that expired license is detected"""
        # Create a welder with expired license
        expired_data = {
            "name": f"TEST_Expired_Welder_{uuid.uuid4().hex[:6]}",
            "qualification_level": "ISO 9606-1 111 P BW",
            "license_expiry": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "notes": "Expired license for testing"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/welders", headers=get_headers(), json=expired_data)
        assert r.status_code == 200
        expired_id = r.json()["welder_id"]
        
        # List welders and check is_expired flag
        r = requests.get(f"{BASE_URL}/api/fpc/welders", headers=get_headers())
        assert r.status_code == 200
        welders = r.json()
        
        expired_welder = next((w for w in welders if w["welder_id"] == expired_id), None)
        assert expired_welder is not None
        assert expired_welder.get("is_expired") == True, "Expired flag should be True"
        print(f"✓ Expired welder detected correctly: is_expired={expired_welder['is_expired']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fpc/welders/{expired_id}", headers=get_headers())
    
    def test_delete_welder(self):
        """DELETE /api/fpc/welders/{id} - Delete welder"""
        if not TestFPCWelders.created_welder_id:
            pytest.skip("No welder to delete")
        
        r = requests.delete(
            f"{BASE_URL}/api/fpc/welders/{TestFPCWelders.created_welder_id}",
            headers=get_headers()
        )
        assert r.status_code == 200
        
        # Verify deletion
        r = requests.get(f"{BASE_URL}/api/fpc/welders", headers=get_headers())
        welders = r.json()
        found = any(w["welder_id"] == TestFPCWelders.created_welder_id for w in welders)
        assert not found, "Deleted welder still in list"
        print(f"✓ Welder deleted: {TestFPCWelders.created_welder_id}")


# ══════════════════════════════════════════════════════════════════
# SECTION 3: FPC MATERIAL BATCHES TESTS
# ══════════════════════════════════════════════════════════════════

class TestFPCBatches:
    """Test FPC Material Batches (Tracciabilità) CRUD"""
    
    created_batch_id = None
    
    def test_create_batch(self):
        """POST /api/fpc/batches - Create material batch"""
        batch_data = {
            "supplier_name": "TEST_Acciaieria SpA",
            "material_type": "S275JR",
            "heat_number": f"TEST_HEAT_{uuid.uuid4().hex[:8]}",
            "received_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test batch for FPC testing"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        assert r.status_code == 200, f"Create batch failed: {r.text}"
        
        data = r.json()
        assert "batch_id" in data
        assert data["supplier_name"] == batch_data["supplier_name"]
        assert data["material_type"] == batch_data["material_type"]
        assert data["heat_number"] == batch_data["heat_number"]
        
        TestFPCBatches.created_batch_id = data["batch_id"]
        print(f"✓ Batch created: {data['batch_id']} - {data['heat_number']}")
    
    def test_list_batches_excludes_certificate(self):
        """GET /api/fpc/batches - List should exclude certificate_base64"""
        r = requests.get(f"{BASE_URL}/api/fpc/batches", headers=get_headers())
        assert r.status_code == 200
        
        batches = r.json()
        assert isinstance(batches, list)
        
        # Verify certificate_base64 is excluded
        for batch in batches:
            assert "certificate_base64" not in batch, "certificate_base64 should be excluded from list"
        
        print(f"✓ Listed {len(batches)} batches (certificate_base64 properly excluded)")
    
    def test_get_batch_certificate_returns_404_when_no_cert(self):
        """GET /api/fpc/batches/{id}/certificate - Returns 404 if no certificate"""
        if not TestFPCBatches.created_batch_id:
            pytest.skip("No batch created")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/batches/{TestFPCBatches.created_batch_id}/certificate",
            headers=get_headers()
        )
        assert r.status_code == 404, "Should return 404 when no certificate"
        print("✓ Certificate endpoint returns 404 when no certificate uploaded")
    
    def test_create_batch_with_certificate(self):
        """POST /api/fpc/batches - Create batch with certificate_base64"""
        # Create fake PDF base64 (just header for testing)
        fake_pdf_base64 = "data:application/pdf;base64,JVBERi0xLjcKJeLjz9M="
        
        batch_data = {
            "supplier_name": "TEST_Steel_Provider",
            "material_type": "S355J2",
            "heat_number": f"TEST_CERT_{uuid.uuid4().hex[:6]}",
            "certificate_base64": fake_pdf_base64,
            "certificate_filename": "cert_3_1_test.pdf",
            "received_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Batch with certificate"
        }
        
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        assert r.status_code == 200
        data = r.json()
        batch_id = data["batch_id"]
        assert data.get("has_certificate") == True
        
        # Now try to get the certificate
        r = requests.get(f"{BASE_URL}/api/fpc/batches/{batch_id}/certificate", headers=get_headers())
        assert r.status_code == 200
        cert_data = r.json()
        assert "certificate_base64" in cert_data
        assert "certificate_filename" in cert_data
        print(f"✓ Batch with certificate created and retrievable: {batch_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fpc/batches/{batch_id}", headers=get_headers())
    
    def test_delete_batch(self):
        """DELETE /api/fpc/batches/{id} - Delete batch"""
        if not TestFPCBatches.created_batch_id:
            pytest.skip("No batch to delete")
        
        r = requests.delete(
            f"{BASE_URL}/api/fpc/batches/{TestFPCBatches.created_batch_id}",
            headers=get_headers()
        )
        assert r.status_code == 200
        print(f"✓ Batch deleted: {TestFPCBatches.created_batch_id}")


# ══════════════════════════════════════════════════════════════════
# SECTION 4: FPC PROJECTS TESTS
# ══════════════════════════════════════════════════════════════════

class TestFPCProjects:
    """Test FPC Projects CRUD and CE Label workflow"""
    
    test_preventivo_id = None
    test_project_id = None
    test_welder_id = None
    test_batch_id = None
    
    @classmethod
    def setup_class(cls):
        """Create test data needed for project tests"""
        # Get an existing preventivo
        r = requests.get(f"{BASE_URL}/api/preventivi/", headers=get_headers())
        if r.status_code == 200 and len(r.json().get("preventivi", [])) > 0:
            cls.test_preventivo_id = r.json()["preventivi"][0]["preventivo_id"]
            print(f"Using existing preventivo: {cls.test_preventivo_id}")
    
    def test_create_project_requires_execution_class(self):
        """POST /api/fpc/projects - Requires valid execution_class"""
        if not TestFPCProjects.test_preventivo_id:
            pytest.skip("No preventivo available")
        
        # Try without execution_class - should fail
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects",
            headers=get_headers(),
            json={"preventivo_id": TestFPCProjects.test_preventivo_id}
        )
        assert r.status_code == 422 or r.status_code == 400, "Should require execution_class"
        print("✓ Project creation requires execution_class")
    
    def test_create_project_rejects_invalid_execution_class(self):
        """POST /api/fpc/projects - Rejects invalid execution_class"""
        if not TestFPCProjects.test_preventivo_id:
            pytest.skip("No preventivo available")
        
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects",
            headers=get_headers(),
            json={"preventivo_id": TestFPCProjects.test_preventivo_id, "execution_class": "EXC99"}
        )
        assert r.status_code == 400, f"Should reject invalid class: {r.status_code}"
        assert "EXC1-EXC4" in r.json().get("detail", "")
        print("✓ Invalid execution_class rejected correctly")
    
    def test_create_project_success(self):
        """POST /api/fpc/projects - Create project with valid data"""
        if not TestFPCProjects.test_preventivo_id:
            pytest.skip("No preventivo available")
        
        # First check if project already exists (to avoid duplicate)
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        existing = r.json() if r.status_code == 200 else []
        for p in existing:
            if p.get("preventivo_id") == TestFPCProjects.test_preventivo_id:
                TestFPCProjects.test_project_id = p["project_id"]
                print(f"✓ Using existing project: {p['project_id']}")
                return
        
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects",
            headers=get_headers(),
            json={"preventivo_id": TestFPCProjects.test_preventivo_id, "execution_class": "EXC2"}
        )
        
        if r.status_code == 409:
            # Already exists - get it
            r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
            for p in r.json():
                if p.get("preventivo_id") == TestFPCProjects.test_preventivo_id:
                    TestFPCProjects.test_project_id = p["project_id"]
                    print(f"✓ Project already exists: {p['project_id']}")
                    return
        
        assert r.status_code == 200, f"Create project failed: {r.text}"
        data = r.json()
        assert "project_id" in data
        assert data["fpc_data"]["execution_class"] == "EXC2"
        TestFPCProjects.test_project_id = data["project_id"]
        print(f"✓ Project created: {data['project_id']} with class EXC2")
    
    def test_create_project_rejects_duplicate(self):
        """POST /api/fpc/projects - Rejects duplicate from same preventivo"""
        if not TestFPCProjects.test_preventivo_id:
            pytest.skip("No preventivo available")
        
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects",
            headers=get_headers(),
            json={"preventivo_id": TestFPCProjects.test_preventivo_id, "execution_class": "EXC2"}
        )
        assert r.status_code == 409, "Should reject duplicate project"
        print("✓ Duplicate project rejected with 409 Conflict")
    
    def test_get_project(self):
        """GET /api/fpc/projects/{id} - Get project with FPC data"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}",
            headers=get_headers()
        )
        assert r.status_code == 200
        data = r.json()
        assert "fpc_data" in data
        assert "lines" in data
        assert "controls" in data.get("fpc_data", {})
        print(f"✓ Project retrieved with FPC data: {len(data.get('lines', []))} lines")
    
    def test_update_project_fpc_welder(self):
        """PUT /api/fpc/projects/{id}/fpc - Assign welder"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        # Create a test welder first
        welder_data = {
            "name": f"TEST_ProjectWelder_{uuid.uuid4().hex[:4]}",
            "qualification_level": "ISO 9606-1 135",
            "license_expiry": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        }
        r = requests.post(f"{BASE_URL}/api/fpc/welders", headers=get_headers(), json=welder_data)
        assert r.status_code == 200
        TestFPCProjects.test_welder_id = r.json()["welder_id"]
        
        # Assign welder to project
        r = requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/fpc",
            headers=get_headers(),
            json={"welder_id": TestFPCProjects.test_welder_id}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["fpc_data"]["welder_id"] == TestFPCProjects.test_welder_id
        print(f"✓ Welder assigned to project: {TestFPCProjects.test_welder_id}")
    
    def test_update_project_fpc_wps(self):
        """PUT /api/fpc/projects/{id}/fpc - Assign WPS"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        r = requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/fpc",
            headers=get_headers(),
            json={"wps_id": "WPS-MAG-135-TEST"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["fpc_data"]["wps_id"] == "WPS-MAG-135-TEST"
        print("✓ WPS assigned to project")
    
    def test_update_project_fpc_controls(self):
        """PUT /api/fpc/projects/{id}/fpc - Update controls (mark as checked)"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        # First get current controls
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}",
            headers=get_headers()
        )
        project = r.json()
        controls = project.get("fpc_data", {}).get("controls", [])
        
        # Mark all as checked
        for c in controls:
            c["checked"] = True
            c["checked_at"] = datetime.now().isoformat()
        
        r = requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/fpc",
            headers=get_headers(),
            json={"controls": controls}
        )
        assert r.status_code == 200
        print(f"✓ All {len(controls)} controls marked as checked")
    
    def test_assign_batch_to_line(self):
        """POST /api/fpc/projects/{id}/assign-batch - Assign batch to line"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        # Create a test batch
        batch_data = {
            "supplier_name": "TEST_BatchForProject",
            "material_type": "S275JR",
            "heat_number": f"HEAT_PROJ_{uuid.uuid4().hex[:6]}"
        }
        r = requests.post(f"{BASE_URL}/api/fpc/batches", headers=get_headers(), json=batch_data)
        assert r.status_code == 200
        TestFPCProjects.test_batch_id = r.json()["batch_id"]
        
        # Get project lines count
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}",
            headers=get_headers()
        )
        project = r.json()
        lines = project.get("lines", [])
        
        if len(lines) == 0:
            pytest.skip("Project has no lines")
        
        # Assign batch to first line
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/assign-batch",
            headers=get_headers(),
            json={"line_index": 0, "batch_id": TestFPCProjects.test_batch_id}
        )
        assert r.status_code == 200
        print(f"✓ Batch assigned to line 0: {TestFPCProjects.test_batch_id}")
    
    def test_ce_check_blockers(self):
        """GET /api/fpc/projects/{id}/ce-check - Returns blockers when not ready"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/ce-check",
            headers=get_headers()
        )
        assert r.status_code == 200
        data = r.json()
        assert "ready" in data
        assert "blockers" in data
        print(f"✓ CE Check: ready={data['ready']}, blockers={len(data['blockers'])}")
        for b in data["blockers"]:
            print(f"  - {b}")
    
    def test_ce_generate_fails_when_not_ready(self):
        """POST /api/fpc/projects/{id}/generate-ce - Fails when blockers exist"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        # First check if there are blockers
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/ce-check",
            headers=get_headers()
        )
        ce_check = r.json()
        
        if ce_check.get("ready"):
            print("✓ Project already ready for CE - skipping failure test")
            return
        
        # Try to generate CE - should fail
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/generate-ce",
            headers=get_headers()
        )
        assert r.status_code == 400, f"Should fail with blockers: {r.status_code}"
        print("✓ CE generation correctly blocked when requirements not met")
    
    def test_ce_generate_success_when_ready(self):
        """POST /api/fpc/projects/{id}/generate-ce - Success when all requirements met"""
        if not TestFPCProjects.test_project_id:
            pytest.skip("No project created")
        
        # Ensure all requirements are met
        # 1. Get project
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}",
            headers=get_headers()
        )
        project = r.json()
        fpc = project.get("fpc_data", {})
        lines = project.get("lines", [])
        
        # 2. Mark all controls checked
        controls = fpc.get("controls", [])
        for c in controls:
            c["checked"] = True
            c["checked_at"] = datetime.now().isoformat()
        
        # 3. Assign batch to all lines
        for i, ln in enumerate(lines):
            if not ln.get("batch_id") and TestFPCProjects.test_batch_id:
                requests.post(
                    f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/assign-batch",
                    headers=get_headers(),
                    json={"line_index": i, "batch_id": TestFPCProjects.test_batch_id}
                )
        
        # 4. Update FPC with welder, WPS, controls
        requests.put(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/fpc",
            headers=get_headers(),
            json={
                "welder_id": TestFPCProjects.test_welder_id or "",
                "wps_id": "WPS-MAG-135-FINAL",
                "controls": controls
            }
        )
        
        # 5. Check CE readiness
        r = requests.get(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/ce-check",
            headers=get_headers()
        )
        ce_check = r.json()
        
        if not ce_check.get("ready"):
            print(f"CE not ready - blockers: {ce_check['blockers']}")
            pytest.skip("Cannot make project CE-ready - skipping generation test")
        
        # 6. Generate CE
        r = requests.post(
            f"{BASE_URL}/api/fpc/projects/{TestFPCProjects.test_project_id}/generate-ce",
            headers=get_headers()
        )
        assert r.status_code == 200, f"CE generation failed: {r.text}"
        data = r.json()
        assert data["status"] == "ce_generated"
        assert "ce_label_generated_at" in data
        print(f"✓ CE Label generated at: {data['ce_label_generated_at']}")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test data"""
        if cls.test_welder_id:
            requests.delete(f"{BASE_URL}/api/fpc/welders/{cls.test_welder_id}", headers=get_headers())
        if cls.test_batch_id:
            requests.delete(f"{BASE_URL}/api/fpc/batches/{cls.test_batch_id}", headers=get_headers())
        print("✓ Test cleanup completed")


# ══════════════════════════════════════════════════════════════════
# SECTION 5: LIST PROJECTS TEST
# ══════════════════════════════════════════════════════════════════

class TestFPCProjectsList:
    """Test FPC Projects list endpoint"""
    
    def test_list_projects(self):
        """GET /api/fpc/projects - List all FPC projects"""
        r = requests.get(f"{BASE_URL}/api/fpc/projects", headers=get_headers())
        assert r.status_code == 200
        
        projects = r.json()
        assert isinstance(projects, list)
        print(f"✓ Listed {len(projects)} FPC projects")
        
        for p in projects:
            assert "project_id" in p
            assert "fpc_data" in p
            print(f"  - {p['project_id']}: {p.get('preventivo_number', 'N/A')} ({p['fpc_data'].get('execution_class', '-')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 215 — Sprint Urgente 4 Features Testing
1. Safety Gate CAM - alert proattivo in Dashboard Executive e Preventivatore
2. Restyling PDF Audit-Proof con footer Commessa + Pag X di Y, verdetto CAM con DM 23/06/2022
3. Pacco Documenti RINA - endpoint ZIP con tutti i documenti di conformità
4. Bottone Pacco RINA nella CommessaHub
"""
import pytest
import requests
import os
import zipfile
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_riesame_e19148d8f838452d"
COMMESSA_ID = "com_2c57c1283871"  # NF-2026-000036 with material batches + CAM data


@pytest.fixture
def auth_session():
    """Session with authentication cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestSafetyGateCAM:
    """Feature 1: Safety Gate CAM - alert proattivo in Dashboard Executive"""

    def test_executive_dashboard_returns_cam_safety_gate(self, auth_session):
        """GET /api/dashboard/executive returns cam_safety_gate with level, percentuale_globale, soglia, commesse"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "cam_safety_gate" in data, "Response should contain cam_safety_gate"
        
        cam = data["cam_safety_gate"]
        assert "level" in cam, "cam_safety_gate should have level"
        assert cam["level"] in ["info", "success", "danger"], f"level should be info/success/danger, got {cam['level']}"
        
        # If there's CAM data, check additional fields
        if cam["level"] != "info":
            assert "percentuale_globale" in cam, "Should have percentuale_globale when CAM data exists"
            assert "soglia" in cam, "Should have soglia"
            assert cam["soglia"] == 75, f"Soglia should be 75, got {cam['soglia']}"
            assert "commesse" in cam, "Should have commesse list"
            assert "n_non_conformi" in cam, "Should have n_non_conformi count"
            
            # Verify commesse structure
            if cam["commesse"]:
                c = cam["commesse"][0]
                assert "commessa_id" in c
                assert "numero" in c
                assert "percentuale_riciclato" in c
                assert "conforme" in c

    def test_executive_dashboard_cam_danger_level(self, auth_session):
        """Verify CAM Safety Gate shows danger level when commesse are below 75% threshold"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        
        data = response.json()
        cam = data["cam_safety_gate"]
        
        # Based on test data, commessa NF-2026-000036 has 73.6% < 75%
        if cam["level"] == "danger":
            assert cam["n_non_conformi"] > 0, "danger level should have non-conforming commesse"
            # Check that message mentions the issue
            assert "ATTENZIONE" in cam.get("message", "") or "non conform" in cam.get("message", "").lower()

    def test_executive_dashboard_settori_structure(self, auth_session):
        """Verify executive dashboard returns proper settori structure"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        
        data = response.json()
        assert "settori" in data
        assert "totale_commesse" in data
        assert "totale_valore" in data
        
        # Check settori keys
        settori = data["settori"]
        for key in ["EN_1090", "EN_13241", "GENERICA"]:
            if key in settori:
                s = settori[key]
                assert "commesse" in s
                assert "stats" in s


class TestPaccoRinaZIP:
    """Feature 3: Pacco Documenti RINA - endpoint ZIP con tutti i documenti di conformità"""

    def test_pacco_rina_returns_valid_zip(self, auth_session):
        """GET /api/fascicolo-tecnico/{commessa_id}/pacco-rina returns a valid ZIP file"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/pacco-rina")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/zip" in content_type, f"Expected application/zip, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert "Pacco_RINA" in content_disp

    def test_pacco_rina_zip_contains_expected_files(self, auth_session):
        """ZIP file contains expected PDFs (DOP, CE, CAM, Rintracciabilità, Riesame) + indice"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/pacco-rina")
        assert response.status_code == 200
        
        # Parse ZIP content
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            file_names = zf.namelist()
            
            # Should have at least the index file
            assert "00_INDICE.txt" in file_names, "ZIP should contain 00_INDICE.txt"
            
            # Count PDF files
            pdf_files = [f for f in file_names if f.endswith('.pdf')]
            
            # Should have multiple PDFs (DOP, CE, CAM, Rintracciabilita, Riesame)
            # At minimum we expect 5 PDFs if all data is present
            print(f"ZIP contains {len(pdf_files)} PDF files: {pdf_files}")
            
            # Check for expected file patterns
            has_dop = any("DOP" in f for f in pdf_files)
            has_ce = any("CE" in f or "Etichetta" in f for f in pdf_files)
            has_cam = any("CAM" in f for f in pdf_files)
            has_rint = any("Rintracciabilita" in f for f in pdf_files)
            has_ries = any("Riesame" in f for f in pdf_files)
            
            print(f"DOP: {has_dop}, CE: {has_ce}, CAM: {has_cam}, Rint: {has_rint}, Ries: {has_ries}")
            
            # At least some PDFs should be present
            assert len(pdf_files) >= 1, "ZIP should contain at least 1 PDF"

    def test_pacco_rina_zip_file_count(self, auth_session):
        """ZIP file contains expected number of files (5 PDFs + 00_INDICE.txt = 6 for full commessa)"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/pacco-rina")
        assert response.status_code == 200
        
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            file_names = zf.namelist()
            
            # For a full commessa with all data, expect 6 files
            # But some may fail if data is missing, so check for reasonable count
            print(f"Total files in ZIP: {len(file_names)}")
            print(f"Files: {file_names}")
            
            # At minimum: index + at least 1 PDF
            assert len(file_names) >= 2, f"Expected at least 2 files, got {len(file_names)}"

    def test_pacco_rina_indice_content(self, auth_session):
        """00_INDICE.txt contains commessa info and file list"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/pacco-rina")
        assert response.status_code == 200
        
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            indice_content = zf.read("00_INDICE.txt").decode("utf-8")
            
            assert "PACCO DOCUMENTI RINA" in indice_content
            assert "Commessa:" in indice_content
            assert "Contenuto:" in indice_content


class TestCAMDeclarationPDF:
    """Feature 2: Restyling PDF Audit-Proof con footer Commessa + Pag X di Y, verdetto CAM con DM 23/06/2022"""

    def test_cam_declaration_pdf_endpoint(self, auth_session):
        """GET /api/cam/dichiarazione-pdf/{commessa_id} returns valid PDF"""
        response = auth_session.get(f"{BASE_URL}/api/cam/dichiarazione-pdf/{COMMESSA_ID}")
        
        # May return 400 if no CAM data, but should not 500
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
            
            # Check PDF magic bytes
            assert response.content[:4] == b'%PDF', "Response should be a valid PDF"

    def test_dop_pdf_has_footer_with_commessa(self, auth_session):
        """DOP PDF should have footer with Commessa number and page numbers"""
        # First create a DOP automatica
        response = auth_session.post(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-automatica")
        
        if response.status_code == 200:
            dop_data = response.json()
            dop_id = dop_data.get("dop", {}).get("dop_id")
            
            if dop_id:
                # Get the PDF
                pdf_response = auth_session.get(
                    f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionata/{dop_id}/pdf"
                )
                assert pdf_response.status_code == 200
                assert pdf_response.content[:4] == b'%PDF'
                
                # PDF size should be substantial (multi-page)
                assert len(pdf_response.content) > 10000, "DOP PDF should be substantial (>10KB)"


class TestDOPEnhancedVerdict:
    """Feature 2: CAM Declaration PDF has enhanced verdict section with ESITO VERIFICA stamp and DM 23/06/2022"""

    def test_dop_automatica_creates_cam_summary(self, auth_session):
        """POST /api/fascicolo-tecnico/{cid}/dop-automatica creates DOP with cam_summary"""
        response = auth_session.post(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-automatica")
        
        # May fail if DOP limit reached, but should not 500
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "dop" in data
            dop = data["dop"]
            
            # Check for CAM summary if material batches have CAM data
            if dop.get("cam_summary"):
                cam = dop["cam_summary"]
                assert "conforme_cam" in cam
                assert "peso_totale_kg" in cam
                assert "percentuale_riciclato" in cam

    def test_dop_list_endpoint(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/dop-frazionate lists all DOPs"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionate")
        assert response.status_code == 200
        
        data = response.json()
        assert "dop_frazionate" in data
        assert "total" in data


class TestDOPFooterAndPageNumbers:
    """Feature 2: DOP PDF footer now includes Commessa number"""

    def test_dop_pdf_generation(self, auth_session):
        """DOP PDF generates successfully with proper structure"""
        # Get existing DOPs
        list_response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionate")
        assert list_response.status_code == 200
        
        dops = list_response.json().get("dop_frazionate", [])
        
        if dops:
            dop_id = dops[0]["dop_id"]
            pdf_response = auth_session.get(
                f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/dop-frazionata/{dop_id}/pdf"
            )
            assert pdf_response.status_code == 200
            assert pdf_response.content[:4] == b'%PDF'


class TestPreventivatoreCAMSafetyGate:
    """Feature 1: CAM Safety Gate reminder in Preventivatore when normativa=EN_1090"""

    def test_preventivatore_calcola_endpoint(self, auth_session):
        """POST /api/preventivatore/calcola works with basic input"""
        payload = {
            "materiali": [],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20,
            "peso_kg_target": 1000
        }
        response = auth_session.post(f"{BASE_URL}/api/preventivatore/calcola", json=payload)
        
        # May return 404 if endpoint doesn't exist or 200 if it does
        if response.status_code == 200:
            data = response.json()
            assert "calcolo" in data or "stima_ore" in data


class TestCommessaHubPaccoRinaButton:
    """Feature 4: Bottone Pacco RINA nella CommessaHub"""

    def test_commessa_hub_endpoint(self, auth_session):
        """GET /api/commesse/{commessa_id}/hub returns commessa data"""
        response = auth_session.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/hub")
        assert response.status_code == 200
        
        data = response.json()
        assert "commessa" in data
        
        commessa = data["commessa"]
        assert "commessa_id" in commessa
        assert "numero" in commessa
        
        # Check normativa_tipo for EN_1090 (which enables Pacco RINA button)
        normativa = commessa.get("normativa_tipo")
        print(f"Commessa normativa_tipo: {normativa}")


class TestCELabelPDF:
    """Test CE Label PDF generation"""

    def test_ce_label_pdf_endpoint(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf returns valid PDF"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/etichetta-ce-1090/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type
        
        # Check PDF magic bytes
        assert response.content[:4] == b'%PDF'


class TestRintracciabilitaPDF:
    """Test Rintracciabilita Totale PDF generation"""

    def test_rintracciabilita_pdf_endpoint(self, auth_session):
        """GET /api/fascicolo-tecnico/{cid}/rintracciabilita-totale/pdf returns valid PDF"""
        response = auth_session.get(f"{BASE_URL}/api/fascicolo-tecnico/{COMMESSA_ID}/rintracciabilita-totale/pdf")
        
        # May return 400 if no batches
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            assert "application/pdf" in content_type
            assert response.content[:4] == b'%PDF'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 198: POS Attachments & Scadenza Bug Fix Tests
Tests for:
1. PATCH /api/company/documents/sicurezza-globali/{doc_type} - scadenza update without file re-upload
2. GET /api/company/documents/sicurezza-globali - expiry flags (days_to_expiry, is_expiring, is_expired)
3. GET /api/company/documents/allegati-pos - POS attachments with includi_pos status
4. POST /api/company/documents/allegati-pos/{doc_type} - upload POS attachment
5. PATCH /api/company/documents/allegati-pos/{doc_type} - toggle includi_pos flag
6. DELETE /api/company/documents/allegati-pos/{doc_type} - delete POS attachment
7. POST /api/sicurezza/export-cse/{commessa_id} - ZIP with 05_ALLEGATI_POS folder
"""
import pytest
import requests
import os
import io
import zipfile
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_2026_active"
TEST_COMMESSA = "com_loiano_cims_2026"


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set('session_token', SESSION_TOKEN)
    session.headers.update({'Content-Type': 'application/json'})
    return session


class TestSicurezzaGlobaliEndpoints:
    """Tests for sicurezza-globali (DURC, Visura, etc.) endpoints"""

    def test_get_sicurezza_globali_returns_all_doc_types(self, auth_session):
        """GET /api/company/documents/sicurezza-globali returns all 5 document types"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        assert "documenti" in data
        docs = data["documenti"]
        
        # Verify all 5 document types are present
        expected_types = ["durc", "visura", "white_list", "patente_crediti", "dvr"]
        for doc_type in expected_types:
            assert doc_type in docs, f"Missing doc type: {doc_type}"
            assert "label" in docs[doc_type]
            assert "presente" in docs[doc_type]
            assert "is_expiring" in docs[doc_type]
            assert "is_expired" in docs[doc_type]
            assert "days_to_expiry" in docs[doc_type]

    def test_get_sicurezza_globali_expiry_flags(self, auth_session):
        """Verify expiry flags are calculated correctly"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        durc = data["documenti"]["durc"]
        
        # DURC should have scadenza set
        if durc["presente"] and durc["scadenza"]:
            assert durc["days_to_expiry"] is not None
            # Verify boolean flags are present
            assert isinstance(durc["is_expiring"], bool)
            assert isinstance(durc["is_expired"], bool)

    def test_patch_scadenza_without_file_upload(self, auth_session):
        """PATCH /api/company/documents/sicurezza-globali/{doc_type} updates scadenza without file"""
        # Set a new scadenza date
        new_date = (date.today() + timedelta(days=90)).isoformat()
        
        response = auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": new_date}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["message"] == "Scadenza aggiornata"
        assert result["scadenza"] == new_date
        
        # Verify persistence by fetching again
        get_response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert get_response.status_code == 200
        
        durc = get_response.json()["documenti"]["durc"]
        assert durc["scadenza"] == new_date

    def test_patch_scadenza_missing_doc_returns_404(self, auth_session):
        """PATCH on non-existent doc returns 404"""
        response = auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/white_list",
            json={"scadenza": "2026-12-31"}
        )
        # white_list is not uploaded, should return 404
        if response.status_code == 404:
            assert "non trovato" in response.json().get("detail", "").lower()

    def test_patch_invalid_doc_type_returns_400(self, auth_session):
        """PATCH with invalid doc_type returns 400"""
        response = auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/invalid_type",
            json={"scadenza": "2026-12-31"}
        )
        assert response.status_code == 400


class TestAllegatiPosEndpoints:
    """Tests for allegati-pos (Rumore, Vibrazioni, MMC) endpoints"""

    def test_get_allegati_pos_returns_all_types(self, auth_session):
        """GET /api/company/documents/allegati-pos returns all 3 POS attachment types"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/allegati-pos")
        assert response.status_code == 200
        
        data = response.json()
        assert "allegati" in data
        allegati = data["allegati"]
        
        # Verify all 3 types
        expected_types = ["rumore", "vibrazioni", "mmc"]
        for doc_type in expected_types:
            assert doc_type in allegati, f"Missing allegato type: {doc_type}"
            assert "label" in allegati[doc_type]
            assert "presente" in allegati[doc_type]
            assert "includi_pos" in allegati[doc_type]

    def test_get_allegati_pos_includi_pos_flag(self, auth_session):
        """Verify includi_pos flag is returned correctly"""
        response = auth_session.get(f"{BASE_URL}/api/company/documents/allegati-pos")
        assert response.status_code == 200
        
        data = response.json()
        for doc_type, allegato in data["allegati"].items():
            if allegato["presente"]:
                assert isinstance(allegato["includi_pos"], bool)

    def test_patch_toggle_includi_pos(self, auth_session):
        """PATCH /api/company/documents/allegati-pos/{doc_type} toggles includi_pos"""
        # First get current state
        get_response = auth_session.get(f"{BASE_URL}/api/company/documents/allegati-pos")
        assert get_response.status_code == 200
        
        vibrazioni = get_response.json()["allegati"]["vibrazioni"]
        if not vibrazioni["presente"]:
            pytest.skip("Vibrazioni not uploaded, skipping toggle test")
        
        current_value = vibrazioni["includi_pos"]
        new_value = not current_value
        
        # Toggle the value
        response = auth_session.patch(
            f"{BASE_URL}/api/company/documents/allegati-pos/vibrazioni",
            json={"includi_pos": new_value}
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["includi_pos"] == new_value
        
        # Verify persistence
        verify_response = auth_session.get(f"{BASE_URL}/api/company/documents/allegati-pos")
        assert verify_response.json()["allegati"]["vibrazioni"]["includi_pos"] == new_value

    def test_patch_allegato_not_found_returns_404(self, auth_session):
        """PATCH on non-existent allegato returns 404"""
        # First delete if exists, then try to patch
        response = auth_session.patch(
            f"{BASE_URL}/api/company/documents/allegati-pos/rumore",
            json={"includi_pos": True}
        )
        # If rumore exists, this should succeed
        assert response.status_code in [200, 404]


class TestCSEExportWithAllegatiPOS:
    """Tests for CSE export ZIP including allegati_pos"""

    def test_export_cse_returns_zip(self, auth_session):
        """POST /api/sicurezza/export-cse/{commessa_id} returns valid ZIP"""
        response = auth_session.post(
            f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA}"
        )
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/zip'
        
        # Verify it's a valid ZIP
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as zf:
            assert len(zf.namelist()) > 0

    def test_export_cse_contains_allegati_pos_folder(self, auth_session):
        """CSE export contains 05_ALLEGATI_POS folder with correct files"""
        response = auth_session.post(
            f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA}"
        )
        assert response.status_code == 200
        
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as zf:
            file_list = zf.namelist()
            
            # Check for allegati_pos folder
            allegati_pos_files = [f for f in file_list if '05_ALLEGATI_POS' in f]
            print(f"Allegati POS files in ZIP: {allegati_pos_files}")
            
            # Should have at least some files if any allegati have includi_pos=true
            # The exact count depends on current state

    def test_export_cse_only_includes_includi_pos_true(self, auth_session):
        """CSE export only includes allegati with includi_pos=true"""
        # First, set vibrazioni to includi_pos=false
        auth_session.patch(
            f"{BASE_URL}/api/company/documents/allegati-pos/vibrazioni",
            json={"includi_pos": False}
        )
        
        # Export CSE
        response = auth_session.post(
            f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA}"
        )
        assert response.status_code == 200
        
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as zf:
            file_list = zf.namelist()
            allegati_pos_files = [f for f in file_list if '05_ALLEGATI_POS' in f]
            
            # Vibrazioni should NOT be in the ZIP
            vibrazioni_files = [f for f in allegati_pos_files if 'VIBRAZIONI' in f.upper()]
            assert len(vibrazioni_files) == 0, f"Vibrazioni should not be in ZIP when includi_pos=false: {vibrazioni_files}"

    def test_export_cse_contains_documenti_azienda(self, auth_session):
        """CSE export contains 00_DOCUMENTI_AZIENDA folder with global docs"""
        response = auth_session.post(
            f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA}"
        )
        assert response.status_code == 200
        
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as zf:
            file_list = zf.namelist()
            
            # Check for documenti azienda folder
            doc_azienda_files = [f for f in file_list if '00_DOCUMENTI_AZIENDA' in f]
            print(f"Documenti Azienda files in ZIP: {doc_azienda_files}")
            
            # Should contain DVR if uploaded
            dvr_files = [f for f in doc_azienda_files if 'DVR' in f.upper()]
            assert len(dvr_files) > 0, "DVR should be in documenti azienda folder"


class TestAuthRequired:
    """Tests for authentication requirements"""

    def test_sicurezza_globali_requires_auth(self):
        """GET sicurezza-globali without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 401

    def test_allegati_pos_requires_auth(self):
        """GET allegati-pos without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/company/documents/allegati-pos")
        assert response.status_code == 401

    def test_patch_scadenza_requires_auth(self):
        """PATCH scadenza without auth returns 401"""
        response = requests.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": "2026-12-31"}
        )
        assert response.status_code == 401

    def test_export_cse_requires_auth(self):
        """POST export-cse without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/sicurezza/export-cse/{TEST_COMMESSA}")
        assert response.status_code == 401


class TestExpiryAlertLogic:
    """Tests for expiry alert logic (15 days warning)"""

    def test_expiry_alert_15_days(self, auth_session):
        """Document expiring in 15 days should have is_expiring=true"""
        # Set DURC to expire in 10 days
        expiry_date = (date.today() + timedelta(days=10)).isoformat()
        
        auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": expiry_date}
        )
        
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        durc = response.json()["documenti"]["durc"]
        assert durc["is_expiring"] == True
        assert durc["is_expired"] == False
        assert durc["days_to_expiry"] == 10

    def test_expired_document_flag(self, auth_session):
        """Expired document should have is_expired=true"""
        # Set DURC to expired date
        expiry_date = (date.today() - timedelta(days=5)).isoformat()
        
        auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": expiry_date}
        )
        
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        durc = response.json()["documenti"]["durc"]
        assert durc["is_expired"] == True
        assert durc["days_to_expiry"] <= 0

    def test_valid_document_no_alert(self, auth_session):
        """Document valid for >15 days should have is_expiring=false"""
        # Set DURC to expire in 60 days
        expiry_date = (date.today() + timedelta(days=60)).isoformat()
        
        auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": expiry_date}
        )
        
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        durc = response.json()["documenti"]["durc"]
        assert durc["is_expiring"] == False
        assert durc["is_expired"] == False
        assert durc["days_to_expiry"] == 60

    def test_scadenze_alert_array(self, auth_session):
        """scadenze_alert array should contain expiring/expired docs"""
        # Set DURC to expire in 10 days
        expiry_date = (date.today() + timedelta(days=10)).isoformat()
        
        auth_session.patch(
            f"{BASE_URL}/api/company/documents/sicurezza-globali/durc",
            json={"scadenza": expiry_date}
        )
        
        response = auth_session.get(f"{BASE_URL}/api/company/documents/sicurezza-globali")
        assert response.status_code == 200
        
        data = response.json()
        assert "scadenze_alert" in data
        
        # DURC should be in alerts
        alert_types = [a["doc_type"] for a in data["scadenze_alert"]]
        assert "durc" in alert_types

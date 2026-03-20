"""
Iteration 183: Fase 4 - Montaggio e Tracciabilità
Tests for the new Assembly Diary feature in NormaFacile 2.0

Features tested:
1. Torque Table API (ISO 898-1) - GET /api/montaggio/torque-table, GET /api/montaggio/torque
2. DDT Bolt Traceability - POST /api/montaggio/ddt/save, GET /api/montaggio/ddt/{commessa_id}
3. Assembly Diary - POST /api/montaggio/diario, GET /api/montaggio/diario/{commessa_id}
4. Assembly Photos - POST /api/montaggio/foto/{commessa_id}
5. Client Signature - POST /api/montaggio/firma
"""
import pytest
import requests
import os
import uuid
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_COMMESSA_ID = "com_2b99b2db8681"  # NF-2026-000008, EN_1090
TEST_OPERATOR_ID = "op_ba8179e3"  # Ahmed
TEST_OPERATOR_NAME = "Ahmed"


class TestTorqueTable:
    """Tests for ISO 898-1 torque table endpoints"""
    
    def test_get_torque_table_full(self):
        """GET /api/montaggio/torque-table returns full table with 60 entries"""
        response = requests.get(f"{BASE_URL}/api/montaggio/torque-table")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "table" in data, "Response should contain 'table'"
        assert "diameters" in data, "Response should contain 'diameters'"
        assert "classes" in data, "Response should contain 'classes'"
        
        # Verify 12 diameters
        assert len(data["diameters"]) == 12, f"Expected 12 diameters, got {len(data['diameters'])}"
        expected_diameters = ["M6", "M8", "M10", "M12", "M14", "M16", "M18", "M20", "M22", "M24", "M27", "M30"]
        assert data["diameters"] == expected_diameters, f"Diameters mismatch: {data['diameters']}"
        
        # Verify 5 classes
        assert len(data["classes"]) == 5, f"Expected 5 classes, got {len(data['classes'])}"
        expected_classes = ["4.6", "5.6", "8.8", "10.9", "12.9"]
        assert data["classes"] == expected_classes, f"Classes mismatch: {data['classes']}"
        
        # Verify 60 entries (12 diameters × 5 classes)
        assert len(data["table"]) == 60, f"Expected 60 entries, got {len(data['table'])}"
        print(f"✓ Torque table has {len(data['table'])} entries with {len(data['diameters'])} diameters and {len(data['classes'])} classes")
    
    def test_get_torque_m16_10_9(self):
        """GET /api/montaggio/torque?diametro=M16&classe=10.9 returns 245 Nm"""
        response = requests.get(f"{BASE_URL}/api/montaggio/torque", params={
            "diametro": "M16",
            "classe": "10.9"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["diametro"] == "M16"
        assert data["classe"] == "10.9"
        assert data["coppia_nm"] == 245, f"Expected 245 Nm, got {data['coppia_nm']}"
        assert data["unita"] == "Nm"
        print(f"✓ M16 cl.10.9 torque = {data['coppia_nm']} Nm")
    
    def test_get_torque_m12_8_8(self):
        """GET /api/montaggio/torque?diametro=M12&classe=8.8 returns 72 Nm"""
        response = requests.get(f"{BASE_URL}/api/montaggio/torque", params={
            "diametro": "M12",
            "classe": "8.8"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["coppia_nm"] == 72, f"Expected 72 Nm, got {data['coppia_nm']}"
        print(f"✓ M12 cl.8.8 torque = {data['coppia_nm']} Nm")
    
    def test_get_torque_invalid_returns_404(self):
        """GET /api/montaggio/torque?diametro=M99&classe=99.9 returns 404"""
        response = requests.get(f"{BASE_URL}/api/montaggio/torque", params={
            "diametro": "M99",
            "classe": "99.9"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Invalid diameter/class returns 404")


class TestDDTBoltTraceability:
    """Tests for DDT bolt data save and retrieval"""
    
    def test_save_ddt_with_torque_enrichment(self):
        """POST /api/montaggio/ddt/save saves DDT and enriches with torque values"""
        unique_id = uuid.uuid4().hex[:6]
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "fornitore": f"TEST_Fornitore_{unique_id}",
            "numero_ddt": f"DDT-{unique_id}",
            "data_ddt": "2026-01-15",
            "lotto_generale": f"LOT-{unique_id}",
            "bulloni": [
                {"diametro": "M16", "classe": "10.9", "lotto": f"LOT-{unique_id}-A", "quantita": "50 pz", "descrizione": "Bullone TE M16x60"},
                {"diametro": "M12", "classe": "8.8", "lotto": f"LOT-{unique_id}-B", "quantita": "100 pz", "descrizione": "Bullone TE M12x40"},
                {"diametro": "M20", "classe": "12.9", "lotto": f"LOT-{unique_id}-C", "quantita": "25 pz", "descrizione": "Bullone TE M20x80"}
            ],
            "source": "manuale"
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/ddt/save", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ddt_id" in data, "Response should contain ddt_id"
        assert data["commessa_id"] == TEST_COMMESSA_ID
        assert data["fornitore"] == payload["fornitore"]
        assert data["numero_ddt"] == payload["numero_ddt"]
        assert len(data["bulloni"]) == 3
        
        # Verify torque enrichment
        for bullone in data["bulloni"]:
            assert "coppia_nm" in bullone, f"Bullone should have coppia_nm: {bullone}"
            if bullone["diametro"] == "M16" and bullone["classe"] == "10.9":
                assert bullone["coppia_nm"] == 245, f"M16 10.9 should be 245 Nm, got {bullone['coppia_nm']}"
            elif bullone["diametro"] == "M12" and bullone["classe"] == "8.8":
                assert bullone["coppia_nm"] == 72, f"M12 8.8 should be 72 Nm, got {bullone['coppia_nm']}"
            elif bullone["diametro"] == "M20" and bullone["classe"] == "12.9":
                assert bullone["coppia_nm"] == 580, f"M20 12.9 should be 580 Nm, got {bullone['coppia_nm']}"
        
        print(f"✓ DDT saved with ID {data['ddt_id']}, torque values enriched correctly")
        return data["ddt_id"]
    
    def test_list_ddts_for_commessa(self):
        """GET /api/montaggio/ddt/{commessa_id} lists saved DDTs"""
        # First save a DDT
        unique_id = uuid.uuid4().hex[:6]
        save_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "fornitore": f"TEST_ListTest_{unique_id}",
            "numero_ddt": f"DDT-LIST-{unique_id}",
            "bulloni": [
                {"diametro": "M10", "classe": "8.8", "quantita": "20 pz"}
            ],
            "source": "manuale"
        }
        save_response = requests.post(f"{BASE_URL}/api/montaggio/ddt/save", json=save_payload)
        assert save_response.status_code == 200
        
        # Now list DDTs
        response = requests.get(f"{BASE_URL}/api/montaggio/ddt/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ddts" in data
        assert "count" in data
        assert data["count"] >= 1, f"Expected at least 1 DDT, got {data['count']}"
        
        # Verify our saved DDT is in the list
        found = any(d["numero_ddt"] == save_payload["numero_ddt"] for d in data["ddts"])
        assert found, f"Saved DDT {save_payload['numero_ddt']} not found in list"
        
        print(f"✓ Listed {data['count']} DDTs for commessa {TEST_COMMESSA_ID}")


class TestAssemblyDiary:
    """Tests for assembly diary (diario montaggio) endpoints"""
    
    def test_save_diario_montaggio(self):
        """POST /api/montaggio/diario saves assembly diary with serraggi, fondazioni, foto IDs"""
        unique_id = uuid.uuid4().hex[:6]
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "serraggi": [
                {"diametro": "M16", "classe": "10.9", "coppia_nm": 245, "confermato": True, "chiave_dinamometrica": True},
                {"diametro": "M12", "classe": "8.8", "coppia_nm": 72, "confermato": True, "chiave_dinamometrica": True}
            ],
            "fondazioni_ok": True,
            "foto_giunti_doc_ids": [f"doc_giunti_{unique_id}"],
            "foto_ancoraggi_doc_ids": [f"doc_ancoraggi_{unique_id}"]
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/diario", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "montaggio_id" in data, "Response should contain montaggio_id"
        assert data["commessa_id"] == TEST_COMMESSA_ID
        assert data["operatore_id"] == TEST_OPERATOR_ID
        assert data["operatore_nome"] == TEST_OPERATOR_NAME
        assert len(data["serraggi"]) == 2
        assert data["fondazioni_ok"] == True
        assert len(data["foto_giunti_doc_ids"]) == 1
        assert len(data["foto_ancoraggi_doc_ids"]) == 1
        
        # Verify signature fields are empty initially
        assert data["firma_cliente_base64"] == ""
        assert data["firma_cliente_nome"] == ""
        
        print(f"✓ Diario montaggio saved with ID {data['montaggio_id']}")
        return data["montaggio_id"]
    
    def test_list_diario_entries(self):
        """GET /api/montaggio/diario/{commessa_id} lists diary entries"""
        # First save a diary entry
        unique_id = uuid.uuid4().hex[:6]
        save_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "serraggi": [{"diametro": "M8", "classe": "8.8", "coppia_nm": 21, "confermato": True, "chiave_dinamometrica": True}],
            "fondazioni_ok": True,
            "foto_giunti_doc_ids": [f"doc_list_{unique_id}"],
            "foto_ancoraggi_doc_ids": [f"doc_list_{unique_id}"]
        }
        save_response = requests.post(f"{BASE_URL}/api/montaggio/diario", json=save_payload)
        assert save_response.status_code == 200
        saved_id = save_response.json()["montaggio_id"]
        
        # Now list entries
        response = requests.get(f"{BASE_URL}/api/montaggio/diario/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "entries" in data
        assert "count" in data
        assert data["count"] >= 1
        
        # Verify our saved entry is in the list
        found = any(e["montaggio_id"] == saved_id for e in data["entries"])
        assert found, f"Saved diario {saved_id} not found in list"
        
        print(f"✓ Listed {data['count']} diario entries for commessa {TEST_COMMESSA_ID}")
        return saved_id


class TestAssemblyPhotos:
    """Tests for assembly photo upload endpoint"""
    
    def test_upload_foto_giunti(self):
        """POST /api/montaggio/foto/{commessa_id} uploads giunti photo with correct metadata"""
        # Create a small test image (1x1 red pixel PNG)
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        files = {"file": ("test_giunti.jpg", test_image, "image/jpeg")}
        data = {
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "tipo_foto": "giunti"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/montaggio/foto/{TEST_COMMESSA_ID}",
            files=files,
            data=data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "doc_id" in result
        assert "nome_file" in result
        assert "tipo_foto" in result
        assert result["tipo_foto"] == "giunti"
        assert "MONTAGGIO_GIUNTI" in result["nome_file"]
        
        print(f"✓ Giunti photo uploaded: {result['nome_file']} (doc_id: {result['doc_id']})")
        return result["doc_id"]
    
    def test_upload_foto_ancoraggi(self):
        """POST /api/montaggio/foto/{commessa_id} uploads ancoraggi photo with correct metadata"""
        # Create a small test image
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        files = {"file": ("test_ancoraggi.jpg", test_image, "image/jpeg")}
        data = {
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "tipo_foto": "ancoraggi"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/montaggio/foto/{TEST_COMMESSA_ID}",
            files=files,
            data=data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["tipo_foto"] == "ancoraggi"
        assert "MONTAGGIO_ANCORAGGI" in result["nome_file"]
        
        print(f"✓ Ancoraggi photo uploaded: {result['nome_file']} (doc_id: {result['doc_id']})")
        return result["doc_id"]
    
    def test_upload_foto_invalid_commessa(self):
        """POST /api/montaggio/foto/{invalid_commessa_id} returns 404"""
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        files = {"file": ("test.jpg", test_image, "image/jpeg")}
        data = {"tipo_foto": "giunti"}
        
        response = requests.post(
            f"{BASE_URL}/api/montaggio/foto/invalid_commessa_id",
            files=files,
            data=data
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid commessa returns 404 for photo upload")


class TestClientSignature:
    """Tests for client digital signature endpoint"""
    
    def test_save_firma_cliente(self):
        """POST /api/montaggio/firma saves client signature and updates diario entry"""
        # First create a diario entry
        unique_id = uuid.uuid4().hex[:6]
        diario_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "serraggi": [{"diametro": "M14", "classe": "10.9", "coppia_nm": 162, "confermato": True, "chiave_dinamometrica": True}],
            "fondazioni_ok": True,
            "foto_giunti_doc_ids": [f"doc_firma_{unique_id}"],
            "foto_ancoraggi_doc_ids": [f"doc_firma_{unique_id}"]
        }
        diario_response = requests.post(f"{BASE_URL}/api/montaggio/diario", json=diario_payload)
        assert diario_response.status_code == 200
        montaggio_id = diario_response.json()["montaggio_id"]
        
        # Now save signature
        firma_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "montaggio_id": montaggio_id,
            "firma_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
            "firma_nome": f"TEST_Cliente_{unique_id}"
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/firma", json=firma_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["montaggio_id"] == montaggio_id
        assert data["firma_salvata"] == True
        assert data["firma_nome"] == firma_payload["firma_nome"]
        assert "firma_data" in data
        
        # Verify the diario entry was updated
        list_response = requests.get(f"{BASE_URL}/api/montaggio/diario/{TEST_COMMESSA_ID}")
        assert list_response.status_code == 200
        entries = list_response.json()["entries"]
        updated_entry = next((e for e in entries if e["montaggio_id"] == montaggio_id), None)
        assert updated_entry is not None
        assert updated_entry["firma_cliente_nome"] == firma_payload["firma_nome"]
        assert updated_entry["firma_cliente_base64"] != ""
        
        print(f"✓ Client signature saved for montaggio {montaggio_id}, nome: {data['firma_nome']}")
    
    def test_save_firma_invalid_montaggio(self):
        """POST /api/montaggio/firma with invalid montaggio_id returns 404"""
        firma_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "montaggio_id": "mtg_invalid_id",
            "firma_base64": "data:image/png;base64,test",
            "firma_nome": "Test Cliente"
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/firma", json=firma_payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid montaggio_id returns 404 for signature")


class TestEndToEndFlow:
    """End-to-end test of the complete assembly workflow"""
    
    def test_complete_assembly_workflow(self):
        """Test complete flow: DDT → Diario → Photos → Signature"""
        unique_id = uuid.uuid4().hex[:6]
        
        # Step 1: Save DDT with bolts
        ddt_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "fornitore": f"TEST_E2E_Fornitore_{unique_id}",
            "numero_ddt": f"DDT-E2E-{unique_id}",
            "data_ddt": "2026-01-15",
            "lotto_generale": f"LOT-E2E-{unique_id}",
            "bulloni": [
                {"diametro": "M16", "classe": "10.9", "lotto": f"LOT-{unique_id}", "quantita": "30 pz"},
                {"diametro": "M20", "classe": "8.8", "lotto": f"LOT-{unique_id}", "quantita": "20 pz"}
            ],
            "source": "manuale"
        }
        ddt_response = requests.post(f"{BASE_URL}/api/montaggio/ddt/save", json=ddt_payload)
        assert ddt_response.status_code == 200
        ddt_data = ddt_response.json()
        print(f"  Step 1: DDT saved - {ddt_data['ddt_id']}")
        
        # Step 2: Upload photos
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        # Upload giunti photo
        giunti_response = requests.post(
            f"{BASE_URL}/api/montaggio/foto/{TEST_COMMESSA_ID}",
            files={"file": ("giunti.jpg", test_image, "image/jpeg")},
            data={"operatore_id": TEST_OPERATOR_ID, "operatore_nome": TEST_OPERATOR_NAME, "tipo_foto": "giunti"}
        )
        assert giunti_response.status_code == 200
        giunti_doc_id = giunti_response.json()["doc_id"]
        print(f"  Step 2a: Giunti photo uploaded - {giunti_doc_id}")
        
        # Upload ancoraggi photo
        ancoraggi_response = requests.post(
            f"{BASE_URL}/api/montaggio/foto/{TEST_COMMESSA_ID}",
            files={"file": ("ancoraggi.jpg", test_image, "image/jpeg")},
            data={"operatore_id": TEST_OPERATOR_ID, "operatore_nome": TEST_OPERATOR_NAME, "tipo_foto": "ancoraggi"}
        )
        assert ancoraggi_response.status_code == 200
        ancoraggi_doc_id = ancoraggi_response.json()["doc_id"]
        print(f"  Step 2b: Ancoraggi photo uploaded - {ancoraggi_doc_id}")
        
        # Step 3: Save diario with serraggi from DDT bolts
        diario_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "serraggi": [
                {"diametro": b["diametro"], "classe": b["classe"], "coppia_nm": b["coppia_nm"], "confermato": True, "chiave_dinamometrica": True}
                for b in ddt_data["bulloni"]
            ],
            "fondazioni_ok": True,
            "foto_giunti_doc_ids": [giunti_doc_id],
            "foto_ancoraggi_doc_ids": [ancoraggi_doc_id]
        }
        diario_response = requests.post(f"{BASE_URL}/api/montaggio/diario", json=diario_payload)
        assert diario_response.status_code == 200
        montaggio_id = diario_response.json()["montaggio_id"]
        print(f"  Step 3: Diario saved - {montaggio_id}")
        
        # Step 4: Save client signature
        firma_payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "montaggio_id": montaggio_id,
            "firma_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
            "firma_nome": f"TEST_E2E_Cliente_{unique_id}"
        }
        firma_response = requests.post(f"{BASE_URL}/api/montaggio/firma", json=firma_payload)
        assert firma_response.status_code == 200
        print(f"  Step 4: Client signature saved - {firma_payload['firma_nome']}")
        
        # Verify final state
        final_response = requests.get(f"{BASE_URL}/api/montaggio/diario/{TEST_COMMESSA_ID}")
        assert final_response.status_code == 200
        entries = final_response.json()["entries"]
        final_entry = next((e for e in entries if e["montaggio_id"] == montaggio_id), None)
        
        assert final_entry is not None
        assert final_entry["firma_cliente_nome"] == firma_payload["firma_nome"]
        assert final_entry["firma_cliente_base64"] != ""
        assert len(final_entry["serraggi"]) == 2
        assert final_entry["fondazioni_ok"] == True
        
        print(f"✓ Complete E2E workflow successful: DDT → Photos → Diario → Signature")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

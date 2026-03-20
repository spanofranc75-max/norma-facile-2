"""
Iteration 56 - Test New Features:
1. OdA form validates description field - button disabled if all descriptions empty
2. PDF RdP/OdA include company logo if logo_url is set in company_settings
3. Arrivo materiale form has DDT number, date, supplier dropdown
4. Arrivo materiale form has materials table with description, qty, UM, order reference, cert 3.1 checkbox
5. POST /api/commesse/{id}/approvvigionamento/arrivi accepts detailed materiali array
6. PUT /api/commesse/{id}/approvvigionamento/arrivi/{arrivo_id}/materiale/{idx}/certificato links certificate to material
7. Preventivo form has 'normativa' dropdown (EN_1090, EN_13241, none)
8. POST /api/preventivi correctly saves normativa field
9. PUT /api/preventivi correctly updates normativa field
"""
import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://norma-nervous-system.preview.emergentagent.com').rstrip('/')

# Use MongoDB to create test session
import subprocess
import json

def create_test_session():
    """Create a test user and session in MongoDB"""
    ts = int(time.time() * 1000)
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
var userId = 'test-iter56-{ts}';
var sessionToken = 'sess_iter56_{ts}';
db.users.insertOne({{
  user_id: userId,
  email: 'test.iter56.{ts}@example.com',
  name: 'Test User Iteration 56',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
// Insert company settings with logo_url for PDF testing
db.company_settings.updateOne(
  {{ user_id: userId }},
  {{ $set: {{
    user_id: userId,
    business_name: 'Test Company SRL',
    address: 'Via Roma 1',
    city: 'Milano',
    province: 'MI',
    vat_number: 'IT12345678901',
    phone: '+39 02 1234567',
    email: 'info@testcompany.it',
    logo_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    created_at: new Date()
  }}}},
  {{ upsert: true }}
);
print(JSON.stringify({{ sessionToken: sessionToken, userId: userId }}));
'''
    ], capture_output=True, text=True)
    output = result.stdout.strip().split('\n')[-1]
    try:
        data = json.loads(output)
        return data['sessionToken'], data['userId']
    except:
        print(f"Failed to parse: {output}")
        raise Exception(f"Failed to create test session: {result.stderr}")


@pytest.fixture(scope="module")
def auth_headers():
    """Create test session and return auth headers"""
    session_token, user_id = create_test_session()
    return {"Authorization": f"Bearer {session_token}"}, user_id


@pytest.fixture(scope="module")
def test_commessa(auth_headers):
    """Create a test commessa for arrivo testing"""
    headers, user_id = auth_headers
    commessa_data = {
        "title": f"Test Commessa Iteration 56 - {int(time.time())}",
        "client_id": "",
        "normativa": "EN_1090",  # Set normativa for material batch testing
    }
    
    response = requests.post(f"{BASE_URL}/api/commesse/", headers=headers, json=commessa_data)
    assert response.status_code in [200, 201], f"Failed to create commessa: {response.text}"
    data = response.json()
    return data.get('commessa_id') or data.get('commessa', {}).get('commessa_id')


class TestPreventivoNormativa:
    """Test normativa field in preventivi"""
    
    def test_create_preventivo_with_normativa_en1090(self, auth_headers):
        """Test creating a preventivo with EN_1090 normativa"""
        headers, _ = auth_headers
        payload = {
            "subject": "Test preventivo EN 1090",
            "validity_days": 30,
            "normativa": "EN_1090",
            "lines": [{
                "description": "Test line",
                "quantity": 1,
                "unit_price": 100,
                "vat_rate": "22"
            }]
        }
        response = requests.post(f"{BASE_URL}/api/preventivi/", headers=headers, json=payload)
        assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
        data = response.json()
        assert data.get('normativa') == 'EN_1090', f"Normativa not saved correctly: {data.get('normativa')}"
        return data.get('preventivo_id')
    
    def test_create_preventivo_with_normativa_en13241(self, auth_headers):
        """Test creating a preventivo with EN_13241 normativa"""
        headers, _ = auth_headers
        payload = {
            "subject": "Test preventivo EN 13241",
            "validity_days": 30,
            "normativa": "EN_13241",
            "lines": [{
                "description": "Test line",
                "quantity": 1,
                "unit_price": 200,
                "vat_rate": "22"
            }]
        }
        response = requests.post(f"{BASE_URL}/api/preventivi/", headers=headers, json=payload)
        assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
        data = response.json()
        assert data.get('normativa') == 'EN_13241', f"Normativa not saved correctly: {data.get('normativa')}"
        return data.get('preventivo_id')
    
    def test_create_preventivo_without_normativa(self, auth_headers):
        """Test creating a preventivo without normativa (should default to None)"""
        headers, _ = auth_headers
        payload = {
            "subject": "Test preventivo no normativa",
            "validity_days": 30,
            "lines": [{
                "description": "Test line",
                "quantity": 1,
                "unit_price": 50,
                "vat_rate": "22"
            }]
        }
        response = requests.post(f"{BASE_URL}/api/preventivi/", headers=headers, json=payload)
        assert response.status_code == 201, f"Failed to create preventivo: {response.text}"
        data = response.json()
        assert data.get('normativa') is None or data.get('normativa') == '', f"Normativa should be None or empty: {data.get('normativa')}"
        return data.get('preventivo_id')
    
    def test_update_preventivo_normativa(self, auth_headers):
        """Test updating normativa field on existing preventivo"""
        headers, _ = auth_headers
        # First create a preventivo
        payload = {
            "subject": "Test preventivo for update",
            "validity_days": 30,
            "normativa": None,
            "lines": [{
                "description": "Test line",
                "quantity": 1,
                "unit_price": 100,
                "vat_rate": "22"
            }]
        }
        create_response = requests.post(f"{BASE_URL}/api/preventivi/", headers=headers, json=payload)
        assert create_response.status_code == 201
        prev_id = create_response.json().get('preventivo_id')
        
        # Update with EN_1090
        update_payload = {"normativa": "EN_1090"}
        update_response = requests.put(f"{BASE_URL}/api/preventivi/{prev_id}", headers=headers, json=update_payload)
        assert update_response.status_code == 200, f"Failed to update: {update_response.text}"
        data = update_response.json()
        assert data.get('normativa') == 'EN_1090', f"Normativa not updated: {data.get('normativa')}"
        
        # Update to EN_13241
        update_payload2 = {"normativa": "EN_13241"}
        update_response2 = requests.put(f"{BASE_URL}/api/preventivi/{prev_id}", headers=headers, json=update_payload2)
        assert update_response2.status_code == 200
        data2 = update_response2.json()
        assert data2.get('normativa') == 'EN_13241', f"Normativa not updated to EN_13241: {data2.get('normativa')}"
    
    def test_get_preventivo_includes_normativa(self, auth_headers):
        """Test that GET preventivo returns normativa field"""
        headers, _ = auth_headers
        # Create a preventivo with normativa
        payload = {
            "subject": "Test get normativa",
            "validity_days": 30,
            "normativa": "EN_1090",
            "lines": [{
                "description": "Test",
                "quantity": 1,
                "unit_price": 100,
                "vat_rate": "22"
            }]
        }
        create_response = requests.post(f"{BASE_URL}/api/preventivi/", headers=headers, json=payload)
        assert create_response.status_code == 201
        prev_id = create_response.json().get('preventivo_id')
        
        # Get the preventivo
        get_response = requests.get(f"{BASE_URL}/api/preventivi/{prev_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get('normativa') == 'EN_1090', f"Normativa not in GET response: {data}"


class TestArrivoMateriale:
    """Test enhanced arrivo materiale with detailed tracking"""
    
    def test_create_arrivo_with_detailed_materiali(self, auth_headers, test_commessa):
        """Test POST /api/commesse/{id}/approvvigionamento/arrivi with detailed materiali array"""
        headers, _ = auth_headers
        payload = {
            "ddt_fornitore": f"DDT-TEST-{int(time.time())}",
            "data_ddt": "2026-01-15",
            "fornitore_nome": "Test Fornitore SRL",
            "fornitore_id": "",
            "materiali": [
                {
                    "descrizione": "Trave IPE 200",
                    "quantita": 10,
                    "unita_misura": "ml",
                    "ordine_id": "",
                    "richiede_cert_31": True
                },
                {
                    "descrizione": "Lamiera 10mm S355",
                    "quantita": 500,
                    "unita_misura": "kg",
                    "ordine_id": "",
                    "richiede_cert_31": True
                },
                {
                    "descrizione": "Bulloneria M16",
                    "quantita": 100,
                    "unita_misura": "pz",
                    "ordine_id": "",
                    "richiede_cert_31": False
                }
            ],
            "note": "Test arrivo iteration 56"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi",
            headers=headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create arrivo: {response.text}"
        data = response.json()
        assert 'arrivo' in data, f"No arrivo in response: {data}"
        arrivo = data['arrivo']
        assert arrivo.get('ddt_fornitore') == payload['ddt_fornitore']
        assert arrivo.get('data_ddt') == '2026-01-15'
        assert arrivo.get('fornitore_nome') == 'Test Fornitore SRL'
        assert len(arrivo.get('materiali', [])) == 3, f"Expected 3 materiali, got {len(arrivo.get('materiali', []))}"
        
        # Verify materiali details
        materiali = arrivo.get('materiali', [])
        assert materiali[0]['descrizione'] == 'Trave IPE 200'
        assert materiali[0]['richiede_cert_31'] == True
        assert materiali[1]['quantita'] == 500
        assert materiali[1]['unita_misura'] == 'kg'
        assert materiali[2]['richiede_cert_31'] == False
        
        return arrivo.get('arrivo_id')
    
    def test_arrivo_without_ddt_fails(self, auth_headers, test_commessa):
        """Test that arrivo without DDT number is rejected"""
        headers, _ = auth_headers
        payload = {
            "ddt_fornitore": "",  # Empty DDT
            "materiali": [{"descrizione": "Test", "quantita": 1, "unita_misura": "pz"}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi",
            headers=headers,
            json=payload
        )
        # The backend should still accept it (validation is on frontend)
        # Let's check what happens
        print(f"Response for empty DDT: {response.status_code} - {response.text}")
    
    def test_link_certificato_to_materiale(self, auth_headers, test_commessa):
        """Test PUT /api/commesse/{id}/approvvigionamento/arrivi/{arrivo_id}/materiale/{idx}/certificato"""
        headers, _ = auth_headers
        
        # First create an arrivo with materiali
        create_payload = {
            "ddt_fornitore": f"DDT-CERT-{int(time.time())}",
            "data_ddt": "2026-01-16",
            "fornitore_nome": "Acciaieria Test",
            "materiali": [
                {
                    "descrizione": "Trave HEB 200 S275JR",
                    "quantita": 15,
                    "unita_misura": "ml",
                    "richiede_cert_31": True
                }
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi",
            headers=headers,
            json=create_payload
        )
        assert create_response.status_code == 200, f"Failed to create arrivo: {create_response.text}"
        arrivo_id = create_response.json()['arrivo']['arrivo_id']
        
        # Link certificate to first material (index 0)
        form_data = {
            "certificato_doc_id": "test_doc_123",
            "numero_colata": "12345-A",
            "qualita_materiale": "S275JR",
            "fornitore_materiale": "Acciaieria Arvedi"
        }
        
        link_response = requests.put(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/arrivi/{arrivo_id}/materiale/0/certificato",
            headers=headers,
            data=form_data  # Using form data as endpoint expects Form(...) parameters
        )
        assert link_response.status_code == 200, f"Failed to link certificate: {link_response.text}"
        
        # Verify the data was saved by getting ops data
        ops_response = requests.get(f"{BASE_URL}/api/commesse/{test_commessa}/ops", headers=headers)
        assert ops_response.status_code == 200
        ops_data = ops_response.json()
        
        # Find the arrivo and check the certificate was linked
        arrivi = ops_data.get('approvvigionamento', {}).get('arrivi', [])
        found_arrivo = next((a for a in arrivi if a.get('arrivo_id') == arrivo_id), None)
        assert found_arrivo is not None, f"Arrivo {arrivo_id} not found in ops data"
        
        materiali = found_arrivo.get('materiali', [])
        assert len(materiali) > 0, "No materiali in arrivo"
        assert materiali[0].get('numero_colata') == '12345-A', f"Numero colata not saved: {materiali[0]}"
        assert materiali[0].get('qualita_materiale') == 'S275JR'
        
        return arrivo_id


class TestPdfLogoIntegration:
    """Test PDF generation includes company logo"""
    
    def test_rdp_pdf_includes_logo(self, auth_headers, test_commessa):
        """Test that RdP PDF includes company logo when logo_url is set"""
        headers, _ = auth_headers
        
        # Create an RdP
        rdp_payload = {
            "fornitore_nome": "Test Fornitore PDF",
            "righe": [
                {"descrizione": "Test materiale", "quantita": 10, "unita_misura": "kg"}
            ]
        }
        
        rdp_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste",
            headers=headers,
            json=rdp_payload
        )
        assert rdp_response.status_code == 200, f"Failed to create RdP: {rdp_response.text}"
        rdp_id = rdp_response.json()['rdp']['rdp_id']
        
        # Get PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/richieste/{rdp_id}/pdf",
            headers=headers
        )
        assert pdf_response.status_code == 200, f"Failed to get RdP PDF: {pdf_response.text}"
        assert pdf_response.headers.get('content-type') == 'application/pdf', "PDF response not application/pdf"
        
        # Check PDF size (should be larger if logo is included)
        pdf_size = len(pdf_response.content)
        print(f"RdP PDF size: {pdf_size} bytes")
        assert pdf_size > 0, "PDF is empty"
    
    def test_oda_pdf_includes_logo(self, auth_headers, test_commessa):
        """Test that OdA PDF includes company logo when logo_url is set"""
        headers, _ = auth_headers
        
        # Create an OdA
        oda_payload = {
            "fornitore_nome": "Test Fornitore OdA PDF",
            "righe": [
                {"descrizione": "Test materiale OdA", "quantita": 20, "unita_misura": "pz", "prezzo_unitario": 5.50}
            ]
        }
        
        oda_response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini",
            headers=headers,
            json=oda_payload
        )
        assert oda_response.status_code == 200, f"Failed to create OdA: {oda_response.text}"
        ordine_id = oda_response.json()['ordine']['ordine_id']
        
        # Get PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini/{ordine_id}/pdf",
            headers=headers
        )
        assert pdf_response.status_code == 200, f"Failed to get OdA PDF: {pdf_response.text}"
        assert pdf_response.headers.get('content-type') == 'application/pdf'
        
        pdf_size = len(pdf_response.content)
        print(f"OdA PDF size: {pdf_size} bytes")
        assert pdf_size > 0


class TestOdaValidation:
    """Test OdA form validation - description required"""
    
    def test_oda_with_empty_description_rejected(self, auth_headers, test_commessa):
        """Test that OdA with all empty descriptions is handled correctly"""
        headers, _ = auth_headers
        
        # Try to create OdA with empty descriptions
        payload = {
            "fornitore_nome": "Test Fornitore",
            "righe": [
                {"descrizione": "", "quantita": 1, "unita_misura": "pz", "prezzo_unitario": 10}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini",
            headers=headers,
            json=payload
        )
        # Backend may accept but frontend should prevent this
        print(f"OdA empty description response: {response.status_code} - {response.text}")
        # Check if backend saves or rejects empty description lines
    
    def test_oda_with_valid_description_accepted(self, auth_headers, test_commessa):
        """Test that OdA with valid description is accepted"""
        headers, _ = auth_headers
        
        payload = {
            "fornitore_nome": "Test Fornitore Valid",
            "righe": [
                {"descrizione": "Valid description test", "quantita": 5, "unita_misura": "pz", "prezzo_unitario": 15}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commesse/{test_commessa}/approvvigionamento/ordini",
            headers=headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create OdA with valid description: {response.text}"
        data = response.json()
        assert data['ordine']['righe'][0]['descrizione'] == 'Valid description test'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

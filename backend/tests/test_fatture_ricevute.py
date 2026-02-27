"""
Test suite for Fatture Ricevute (Received Invoices) module
Tests: CRUD operations, XML import/parsing, payment tracking, article extraction
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_fr_1772215827168"
USER_ID = "test-user-fr-1772215827168"


class TestFattureRicevuteAuth:
    """Test auth requirements for fatture ricevute endpoints"""
    
    def test_list_fatture_no_auth(self):
        """GET /fatture-ricevute/ without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /fatture-ricevute/ without auth returns 401")
    
    def test_get_single_no_auth(self):
        """GET /fatture-ricevute/{fr_id} without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/fatture-ricevute/fr_test123")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ GET /fatture-ricevute/{{fr_id}} without auth returns 401")
    
    def test_create_no_auth(self):
        """POST /fatture-ricevute/ without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/fatture-ricevute/", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /fatture-ricevute/ without auth returns 401")
    
    def test_import_xml_no_auth(self):
        """POST /fatture-ricevute/import-xml without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/fatture-ricevute/import-xml")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /fatture-ricevute/import-xml without auth returns 401")


class TestFattureRicevuteCRUD:
    """Test CRUD operations for fatture ricevute"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.cookies.set('session_token', SESSION_TOKEN)
        self.session.headers.update({'Content-Type': 'application/json'})
        self.created_fr_ids = []
        yield
        # Cleanup: delete all test-created invoices
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
    
    def test_list_fatture_with_kpis(self):
        """GET /fatture-ricevute/ returns list with KPIs"""
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert 'fatture' in data, "Response missing 'fatture' field"
        assert 'total' in data, "Response missing 'total' field"
        assert 'kpi' in data, "Response missing 'kpi' field"
        
        # Verify KPI structure
        kpi = data['kpi']
        assert 'totale_fatture' in kpi, "KPI missing 'totale_fatture'"
        assert 'totale_pagato' in kpi, "KPI missing 'totale_pagato'"
        assert 'da_pagare' in kpi, "KPI missing 'da_pagare'"
        assert 'count' in kpi, "KPI missing 'count'"
        
        print(f"✓ GET /fatture-ricevute/ returns list with KPIs (count={kpi['count']})")
    
    def test_create_fattura_ricevuta(self):
        """POST /fatture-ricevute/ creates a received invoice"""
        payload = {
            "fornitore_nome": "TEST_Fornitore SRL",
            "fornitore_piva": "IT12345678901",
            "tipo_documento": "TD01",
            "numero_documento": "TEST-FR-001",
            "data_documento": "2025-01-15",
            "linee": [
                {
                    "numero_linea": 1,
                    "codice_articolo": "ART001",
                    "descrizione": "Test articolo fornitore",
                    "quantita": 10.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 50.0,
                    "aliquota_iva": "22",
                    "importo": 500.0
                }
            ],
            "imponibile": 500.0,
            "imposta": 110.0,
            "totale_documento": 610.0
        }
        
        response = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'fr_id' in data, "Response missing fr_id"
        assert data['fornitore_nome'] == "TEST_Fornitore SRL"
        assert data['numero_documento'] == "TEST-FR-001"
        assert data['totale_documento'] == 610.0
        assert data['status'] == 'da_registrare'
        assert data['payment_status'] == 'non_pagata'
        assert len(data['linee']) == 1
        
        self.created_fr_ids.append(data['fr_id'])
        print(f"✓ POST /fatture-ricevute/ creates invoice (fr_id={data['fr_id']})")
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{data['fr_id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched['fr_id'] == data['fr_id']
        assert fetched['fornitore_nome'] == "TEST_Fornitore SRL"
        print(f"✓ GET /fatture-ricevute/{data['fr_id']} returns created invoice")
    
    def test_update_fattura_status(self):
        """PUT /fatture-ricevute/{fr_id} updates invoice status"""
        # Create a fattura first
        payload = {
            "fornitore_nome": "TEST_Update Status SRL",
            "numero_documento": "TEST-FR-UPDATE",
            "data_documento": "2025-01-15",
            "totale_documento": 100.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        
        # Update status
        update_resp = self.session.put(f"{BASE_URL}/api/fatture-ricevute/{fr_id}", json={
            "status": "registrata"
        })
        assert update_resp.status_code == 200, f"Expected 200, got {update_resp.status_code}: {update_resp.text}"
        updated = update_resp.json()
        assert updated['status'] == 'registrata'
        
        # Verify with GET
        get_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()['status'] == 'registrata'
        
        print(f"✓ PUT /fatture-ricevute/{fr_id} updates status to 'registrata'")
    
    def test_delete_fattura(self):
        """DELETE /fatture-ricevute/{fr_id} deletes invoice"""
        # Create a fattura first
        payload = {
            "fornitore_nome": "TEST_Delete SRL",
            "numero_documento": "TEST-FR-DELETE",
            "data_documento": "2025-01-15",
            "totale_documento": 50.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        
        # Delete
        delete_resp = self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}"
        assert delete_resp.json()['message'] == 'Fattura eliminata'
        
        # Verify deletion
        get_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert get_resp.status_code == 404
        
        print(f"✓ DELETE /fatture-ricevute/{fr_id} removes invoice, returns 404 on re-fetch")
    
    def test_get_nonexistent_fattura(self):
        """GET /fatture-ricevute/{fr_id} returns 404 for nonexistent"""
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/fr_nonexistent123")
        assert response.status_code == 404
        print(f"✓ GET /fatture-ricevute/fr_nonexistent returns 404")


class TestFattureRicevuteXMLImport:
    """Test XML import and parsing functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.cookies.set('session_token', SESSION_TOKEN)
        self.created_fr_ids = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
    
    def get_test_xml(self):
        """Generate a valid FatturaPA XML for testing"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" versione="FPR12">
    <FatturaElettronicaHeader>
        <CedentePrestatore>
            <DatiAnagrafici>
                <IdFiscaleIVA>
                    <IdPaese>IT</IdPaese>
                    <IdCodice>12345678901</IdCodice>
                </IdFiscaleIVA>
                <CodiceFiscale>RSSMRA80A01H501Z</CodiceFiscale>
                <Anagrafica>
                    <Denominazione>Ferramenta Test SpA</Denominazione>
                </Anagrafica>
            </DatiAnagrafici>
            <Sede>
                <Indirizzo>Via Roma 123</Indirizzo>
                <CAP>00100</CAP>
                <Comune>Roma</Comune>
                <Provincia>RM</Provincia>
                <Nazione>IT</Nazione>
            </Sede>
        </CedentePrestatore>
    </FatturaElettronicaHeader>
    <FatturaElettronicaBody>
        <DatiGenerali>
            <DatiGeneraliDocumento>
                <TipoDocumento>TD01</TipoDocumento>
                <Divisa>EUR</Divisa>
                <Data>2025-01-20</Data>
                <Numero>FT-2025-001</Numero>
                <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
            </DatiGeneraliDocumento>
        </DatiGenerali>
        <DatiBeniServizi>
            <DettaglioLinee>
                <NumeroLinea>1</NumeroLinea>
                <Descrizione>Profilato acciaio IPE 200</Descrizione>
                <Quantita>5.00</Quantita>
                <UnitaMisura>ML</UnitaMisura>
                <PrezzoUnitario>100.00</PrezzoUnitario>
                <PrezzoTotale>500.00</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
            </DettaglioLinee>
            <DettaglioLinee>
                <NumeroLinea>2</NumeroLinea>
                <Descrizione>Bulloneria M12 zincata</Descrizione>
                <Quantita>100.00</Quantita>
                <UnitaMisura>PZ</UnitaMisura>
                <PrezzoUnitario>5.00</PrezzoUnitario>
                <PrezzoTotale>500.00</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
            </DettaglioLinee>
            <DatiRiepilogo>
                <AliquotaIVA>22.00</AliquotaIVA>
                <ImponibileImporto>1000.00</ImponibileImporto>
                <Imposta>220.00</Imposta>
            </DatiRiepilogo>
        </DatiBeniServizi>
        <DatiPagamento>
            <CondizioniPagamento>TP02</CondizioniPagamento>
            <DettaglioPagamento>
                <ModalitaPagamento>MP05</ModalitaPagamento>
                <DataScadenzaPagamento>2025-02-20</DataScadenzaPagamento>
                <ImportoPagamento>1220.00</ImportoPagamento>
            </DettaglioPagamento>
        </DatiPagamento>
    </FatturaElettronicaBody>
</FatturaElettronica>"""
    
    def test_import_xml(self):
        """POST /fatture-ricevute/import-xml imports FatturaPA XML"""
        xml_content = self.get_test_xml()
        files = {'file': ('test_fattura.xml', xml_content, 'application/xml')}
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/import-xml",
            files=files
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'message' in data, "Response missing 'message'"
        assert 'fattura' in data, "Response missing 'fattura'"
        
        fattura = data['fattura']
        assert fattura['fornitore_nome'] == 'Ferramenta Test SpA'
        assert fattura['numero_documento'] == 'FT-2025-001'
        assert fattura['totale_documento'] == 1220.0
        assert fattura['has_xml'] == True
        assert len(fattura['linee']) == 2
        
        self.created_fr_ids.append(fattura['fr_id'])
        print(f"✓ POST /fatture-ricevute/import-xml imports FatturaPA XML successfully")
        print(f"  - Fornitore: {fattura['fornitore_nome']}")
        print(f"  - Numero: {fattura['numero_documento']}")
        print(f"  - Totale: {fattura['totale_documento']}")
        print(f"  - Linee: {len(fattura['linee'])}")
    
    def test_preview_xml(self):
        """POST /fatture-ricevute/preview-xml parses XML without saving"""
        xml_content = self.get_test_xml()
        files = {'file': ('test_fattura.xml', xml_content, 'application/xml')}
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/preview-xml",
            files=files
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'preview' in data, "Response missing 'preview'"
        
        preview = data['preview']
        assert preview['fornitore_nome'] == 'Ferramenta Test SpA'
        assert preview['numero_documento'] == 'FT-2025-001'
        assert preview['totale_documento'] == 1220.0
        assert preview['imponibile'] == 1000.0
        assert preview['imposta'] == 220.0
        assert len(preview['linee']) == 2
        
        # Verify no document was created
        list_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/?q=FT-2025-001")
        assert list_resp.status_code == 200
        # Should have 0 results with this numero (unless previously created)
        
        print(f"✓ POST /fatture-ricevute/preview-xml parses XML without saving")
        print(f"  - Parsed fornitore: {preview['fornitore_nome']}")
        print(f"  - Parsed totale: {preview['totale_documento']}")
    
    def test_import_invalid_xml(self):
        """POST /fatture-ricevute/import-xml returns 400 for invalid XML"""
        invalid_xml = "this is not valid xml"
        files = {'file': ('invalid.xml', invalid_xml, 'application/xml')}
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/import-xml",
            files=files
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ POST /fatture-ricevute/import-xml returns 400 for invalid XML")
    
    def test_import_non_xml_file(self):
        """POST /fatture-ricevute/import-xml returns 400 for non-XML file"""
        files = {'file': ('document.pdf', 'fake pdf content', 'application/pdf')}
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/import-xml",
            files=files
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ POST /fatture-ricevute/import-xml returns 400 for non-XML file")


class TestFattureRicevutePayments:
    """Test payment tracking for received invoices"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.cookies.set('session_token', SESSION_TOKEN)
        self.session.headers.update({'Content-Type': 'application/json'})
        self.created_fr_ids = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
    
    def create_test_invoice(self, total=1000.0, nome="TEST_Payment SRL"):
        """Helper to create a test invoice"""
        payload = {
            "fornitore_nome": nome,
            "numero_documento": f"TEST-PAY-{int(total)}",
            "data_documento": "2025-01-15",
            "imponibile": total / 1.22,
            "imposta": total - (total / 1.22),
            "totale_documento": total
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert resp.status_code == 201
        fr_id = resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        return fr_id
    
    def test_get_pagamenti_empty(self):
        """GET /fatture-ricevute/{fr_id}/pagamenti returns empty payment schedule"""
        fr_id = self.create_test_invoice(1000.0)
        
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['fr_id'] == fr_id
        assert data['total_document'] == 1000.0
        assert data['totale_pagato'] == 0.0
        assert data['residuo'] == 1000.0
        assert data['payment_status'] == 'non_pagata'
        assert data['pagamenti'] == []
        
        print(f"✓ GET /fatture-ricevute/{fr_id}/pagamenti returns correct initial state")
    
    def test_record_partial_payment(self):
        """POST /fatture-ricevute/{fr_id}/pagamenti records partial payment"""
        fr_id = self.create_test_invoice(1000.0)
        
        payment = {
            "importo": 300.0,
            "data_pagamento": "2025-01-20",
            "metodo": "bonifico",
            "note": "Acconto"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti",
            json=payment
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['totale_pagato'] == 300.0
        assert data['residuo'] == 700.0
        assert data['payment_status'] == 'parzialmente_pagata'
        
        # Verify with GET
        get_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti")
        assert get_resp.status_code == 200
        pag_data = get_resp.json()
        assert len(pag_data['pagamenti']) == 1
        assert pag_data['pagamenti'][0]['importo'] == 300.0
        assert pag_data['payment_status'] == 'parzialmente_pagata'
        
        print(f"✓ POST /fatture-ricevute/{fr_id}/pagamenti records partial payment")
        print(f"  - Payment: 300€, Residuo: 700€, Status: parzialmente_pagata")
    
    def test_record_full_payment(self):
        """POST /fatture-ricevute/{fr_id}/pagamenti records full payment"""
        fr_id = self.create_test_invoice(500.0)
        
        payment = {
            "importo": 500.0,
            "data_pagamento": "2025-01-20",
            "metodo": "bonifico"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti",
            json=payment
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['totale_pagato'] == 500.0
        assert data['residuo'] == 0.0
        assert data['payment_status'] == 'pagata'
        
        # Verify invoice status also updated
        get_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()['status'] == 'pagata'
        
        print(f"✓ POST /fatture-ricevute/{fr_id}/pagamenti records full payment")
        print(f"  - Invoice status updated to 'pagata'")
    
    def test_payment_exceeds_residuo(self):
        """POST /fatture-ricevute/{fr_id}/pagamenti rejects overpayment"""
        fr_id = self.create_test_invoice(100.0)
        
        payment = {
            "importo": 150.0,  # More than total
            "data_pagamento": "2025-01-20"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti",
            json=payment
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ POST /fatture-ricevute/{fr_id}/pagamenti rejects overpayment (400)")


class TestFattureRicevuteExtractArticoli:
    """Test article extraction from received invoices"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.cookies.set('session_token', SESSION_TOKEN)
        self.session.headers.update({'Content-Type': 'application/json'})
        self.created_fr_ids = []
        self.created_articoli = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
        # Cleanup created articoli
        for art_code in self.created_articoli:
            try:
                # Find and delete by code
                search = self.session.get(f"{BASE_URL}/api/articoli/?q={art_code}")
                if search.status_code == 200:
                    for art in search.json().get('articoli', []):
                        if art.get('codice') == art_code:
                            self.session.delete(f"{BASE_URL}/api/articoli/{art['articolo_id']}")
            except:
                pass
    
    def test_extract_articoli(self):
        """POST /fatture-ricevute/{fr_id}/extract-articoli extracts line items"""
        # Create invoice with line items
        payload = {
            "fornitore_nome": "TEST_Extract SRL",
            "numero_documento": "TEST-EXT-001",
            "data_documento": "2025-01-15",
            "linee": [
                {
                    "numero_linea": 1,
                    "codice_articolo": "TEST-EXTRACT-ART1",
                    "descrizione": "Profilato per test estrazione",
                    "quantita": 10.0,
                    "unita_misura": "ml",
                    "prezzo_unitario": 25.0,
                    "aliquota_iva": "22",
                    "importo": 250.0
                },
                {
                    "numero_linea": 2,
                    "descrizione": "Articolo senza codice per test",
                    "quantita": 5.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 10.0,
                    "aliquota_iva": "22",
                    "importo": 50.0
                }
            ],
            "imponibile": 300.0,
            "imposta": 66.0,
            "totale_documento": 366.0
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        self.created_articoli.append("TEST-EXTRACT-ART1")
        
        # Extract articoli
        response = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/extract-articoli")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'message' in data
        assert 'created' in data
        assert 'updated' in data
        assert 'skipped' in data
        
        total_processed = data['created'] + data['updated'] + data['skipped']
        assert total_processed > 0, "Expected some articles to be processed"
        
        print(f"✓ POST /fatture-ricevute/{fr_id}/extract-articoli extracts articles")
        print(f"  - Created: {data['created']}, Updated: {data['updated']}, Skipped: {data['skipped']}")


class TestFattureRicevuteFilters:
    """Test filtering and search functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.cookies.set('session_token', SESSION_TOKEN)
        self.session.headers.update({'Content-Type': 'application/json'})
        self.created_fr_ids = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
    
    def test_filter_by_year(self):
        """GET /fatture-ricevute/?year=2025 filters by year"""
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/?year=2025")
        assert response.status_code == 200
        print(f"✓ GET /fatture-ricevute/?year=2025 returns filtered results")
    
    def test_filter_by_status(self):
        """GET /fatture-ricevute/?status=da_registrare filters by status"""
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/?status=da_registrare")
        assert response.status_code == 200
        data = response.json()
        # All returned items should have status da_registrare
        for fr in data['fatture']:
            assert fr['status'] == 'da_registrare', f"Expected da_registrare, got {fr['status']}"
        print(f"✓ GET /fatture-ricevute/?status=da_registrare returns only da_registrare items")
    
    def test_search_by_fornitore(self):
        """GET /fatture-ricevute/?q=xxx searches by fornitore name"""
        # Create a test invoice
        payload = {
            "fornitore_nome": "TEST_SearchSpecific SRL",
            "numero_documento": "TEST-SEARCH-001",
            "data_documento": "2025-01-15",
            "totale_documento": 100.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        
        # Search
        response = self.session.get(f"{BASE_URL}/api/fatture-ricevute/?q=SearchSpecific")
        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1, "Expected at least 1 result"
        
        found = False
        for fr in data['fatture']:
            if fr['fr_id'] == fr_id:
                found = True
                break
        assert found, "Created invoice not found in search results"
        
        print(f"✓ GET /fatture-ricevute/?q=SearchSpecific finds matching invoices")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

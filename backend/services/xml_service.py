"""XML generation service for SDI export."""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class XMLService:
    """Service for generating FatturaPA XML format."""
    
    # Namespace for FatturaPA
    NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
    
    @staticmethod
    def prettify(elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    @staticmethod
    def generate_fattura_xml(
        invoice: dict,
        client: dict,
        company: dict,
        progressive_number: str = "00001"
    ) -> str:
        """
        Generate FatturaPA XML format for SDI.
        
        This is a simplified version - full SDI compliance requires
        additional validation and digital signature.
        """
        # Root element
        root = ET.Element("p:FatturaElettronica", {
            "xmlns:p": XMLService.NS,
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
            "versione": "FPR12"  # Formato privati
        })
        
        # ========== HEADER ==========
        header = ET.SubElement(root, "FatturaElettronicaHeader")
        
        # Dati Trasmissione
        dati_trasm = ET.SubElement(header, "DatiTrasmissione")
        id_trasm = ET.SubElement(dati_trasm, "IdTrasmittente")
        ET.SubElement(id_trasm, "IdPaese").text = "IT"
        ET.SubElement(id_trasm, "IdCodice").text = company.get('codice_fiscale', '')
        ET.SubElement(dati_trasm, "ProgressivoInvio").text = progressive_number
        ET.SubElement(dati_trasm, "FormatoTrasmissione").text = "FPR12"
        ET.SubElement(dati_trasm, "CodiceDestinatario").text = client.get('codice_sdi', '0000000')
        
        # PEC if no SDI code
        if client.get('pec') and client.get('codice_sdi') == '0000000':
            ET.SubElement(dati_trasm, "PECDestinatario").text = client.get('pec')
        
        # Cedente Prestatore (Supplier)
        cedente = ET.SubElement(header, "CedentePrestatore")
        dati_anag_ced = ET.SubElement(cedente, "DatiAnagrafici")
        id_fiscale_ced = ET.SubElement(dati_anag_ced, "IdFiscaleIVA")
        ET.SubElement(id_fiscale_ced, "IdPaese").text = "IT"
        ET.SubElement(id_fiscale_ced, "IdCodice").text = company.get('partita_iva', '')
        ET.SubElement(dati_anag_ced, "CodiceFiscale").text = company.get('codice_fiscale', '')
        anag_ced = ET.SubElement(dati_anag_ced, "Anagrafica")
        ET.SubElement(anag_ced, "Denominazione").text = company.get('business_name', '')
        ET.SubElement(dati_anag_ced, "RegimeFiscale").text = company.get('regime_fiscale', 'RF01')
        
        sede_ced = ET.SubElement(cedente, "Sede")
        ET.SubElement(sede_ced, "Indirizzo").text = company.get('address', '')
        ET.SubElement(sede_ced, "CAP").text = company.get('cap', '')
        ET.SubElement(sede_ced, "Comune").text = company.get('city', '')
        ET.SubElement(sede_ced, "Provincia").text = company.get('province', '')
        ET.SubElement(sede_ced, "Nazione").text = company.get('country', 'IT')
        
        # Cessionario Committente (Client)
        cessionario = ET.SubElement(header, "CessionarioCommittente")
        dati_anag_ces = ET.SubElement(cessionario, "DatiAnagrafici")
        
        if client.get('partita_iva'):
            id_fiscale_ces = ET.SubElement(dati_anag_ces, "IdFiscaleIVA")
            ET.SubElement(id_fiscale_ces, "IdPaese").text = "IT"
            ET.SubElement(id_fiscale_ces, "IdCodice").text = client.get('partita_iva', '')
        
        if client.get('codice_fiscale'):
            ET.SubElement(dati_anag_ces, "CodiceFiscale").text = client.get('codice_fiscale', '')
        
        anag_ces = ET.SubElement(dati_anag_ces, "Anagrafica")
        ET.SubElement(anag_ces, "Denominazione").text = client.get('business_name', '')
        
        sede_ces = ET.SubElement(cessionario, "Sede")
        ET.SubElement(sede_ces, "Indirizzo").text = client.get('address', '')
        ET.SubElement(sede_ces, "CAP").text = client.get('cap', '')
        ET.SubElement(sede_ces, "Comune").text = client.get('city', '')
        ET.SubElement(sede_ces, "Provincia").text = client.get('province', '')
        ET.SubElement(sede_ces, "Nazione").text = client.get('country', 'IT')
        
        # ========== BODY ==========
        body = ET.SubElement(root, "FatturaElettronicaBody")
        
        # Dati Generali
        dati_gen = ET.SubElement(body, "DatiGenerali")
        dati_gen_doc = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
        
        # Document type mapping
        tipo_doc_map = {
            "FT": "TD01",  # Fattura
            "NC": "TD04",  # Nota di credito
            "PRV": "TD01",  # Preventivo as fattura
            "DDT": "TD01"  # DDT as fattura
        }
        ET.SubElement(dati_gen_doc, "TipoDocumento").text = tipo_doc_map.get(
            invoice.get('document_type', 'FT'), 'TD01'
        )
        ET.SubElement(dati_gen_doc, "Divisa").text = "EUR"
        
        # Format date
        issue_date = invoice.get('issue_date', '')
        if isinstance(issue_date, str):
            date_str = issue_date
        else:
            date_str = issue_date.isoformat() if issue_date else datetime.now().strftime('%Y-%m-%d')
        ET.SubElement(dati_gen_doc, "Data").text = date_str
        ET.SubElement(dati_gen_doc, "Numero").text = invoice.get('document_number', '')
        
        totals = invoice.get('totals', {})
        ET.SubElement(dati_gen_doc, "ImportoTotaleDocumento").text = f"{totals.get('total_document', 0):.2f}"
        
        # Dati Beni Servizi (Line items)
        dati_beni = ET.SubElement(body, "DatiBeniServizi")
        
        for idx, line in enumerate(invoice.get('lines', []), 1):
            det_linea = ET.SubElement(dati_beni, "DettaglioLinee")
            ET.SubElement(det_linea, "NumeroLinea").text = str(idx)
            
            if line.get('code'):
                ET.SubElement(det_linea, "CodiceArticolo")
                cod_art = ET.SubElement(det_linea, "CodiceArticolo")
                ET.SubElement(cod_art, "CodiceTipo").text = "INTERNO"
                ET.SubElement(cod_art, "CodiceValore").text = line.get('code', '')
            
            ET.SubElement(det_linea, "Descrizione").text = line.get('description', '')[:1000]
            ET.SubElement(det_linea, "Quantita").text = f"{line.get('quantity', 1):.2f}"
            ET.SubElement(det_linea, "PrezzoUnitario").text = f"{line.get('unit_price', 0):.2f}"
            
            if line.get('discount_percent', 0) > 0:
                sconto = ET.SubElement(det_linea, "ScontoMaggiorazione")
                ET.SubElement(sconto, "Tipo").text = "SC"
                ET.SubElement(sconto, "Percentuale").text = f"{line.get('discount_percent', 0):.2f}"
            
            ET.SubElement(det_linea, "PrezzoTotale").text = f"{line.get('line_total', 0):.2f}"
            
            vat_rate = line.get('vat_rate', '22')
            if vat_rate in ['N3', 'N4']:
                ET.SubElement(det_linea, "AliquotaIVA").text = "0.00"
                ET.SubElement(det_linea, "Natura").text = vat_rate
            else:
                ET.SubElement(det_linea, "AliquotaIVA").text = f"{float(vat_rate):.2f}"
        
        # VAT Summary
        vat_breakdown = totals.get('vat_breakdown', {})
        for rate, values in vat_breakdown.items():
            riepilogo = ET.SubElement(dati_beni, "DatiRiepilogo")
            
            if rate in ['N3', 'N4']:
                ET.SubElement(riepilogo, "AliquotaIVA").text = "0.00"
                ET.SubElement(riepilogo, "Natura").text = rate
            else:
                ET.SubElement(riepilogo, "AliquotaIVA").text = f"{float(rate):.2f}"
            
            ET.SubElement(riepilogo, "ImponibileImporto").text = f"{values.get('imponibile', 0):.2f}"
            ET.SubElement(riepilogo, "Imposta").text = f"{values.get('imposta', 0):.2f}"
            ET.SubElement(riepilogo, "EsigibilitaIVA").text = "I"  # Immediata
        
        # Dati Pagamento
        dati_pag = ET.SubElement(body, "DatiPagamento")
        ET.SubElement(dati_pag, "CondizioniPagamento").text = "TP02"  # Pagamento completo
        
        det_pag = ET.SubElement(dati_pag, "DettaglioPagamento")
        
        # Payment method mapping
        mod_pag_map = {
            "bonifico": "MP05",
            "contanti": "MP01",
            "carta": "MP08",
            "assegno": "MP02",
            "riba": "MP12",
            "altro": "MP05"
        }
        ET.SubElement(det_pag, "ModalitaPagamento").text = mod_pag_map.get(
            invoice.get('payment_method', 'bonifico'), 'MP05'
        )
        ET.SubElement(det_pag, "ImportoPagamento").text = f"{totals.get('total_to_pay', 0):.2f}"
        
        if invoice.get('due_date'):
            due_date = invoice.get('due_date')
            if isinstance(due_date, str):
                date_str = due_date
            else:
                date_str = due_date.isoformat()
            ET.SubElement(det_pag, "DataScadenzaPagamento").text = date_str
        
        # Add bank details if available
        bank = company.get('bank_details', {})
        if bank.get('iban'):
            ET.SubElement(det_pag, "IBAN").text = bank.get('iban', '').replace(' ', '')
        
        return XMLService.prettify(root)


xml_service = XMLService()

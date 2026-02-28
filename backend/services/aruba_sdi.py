"""
NormaFacile - Aruba SDI Integration
Fatturazione Elettronica via Aruba API (Sistema di Interscambio).
"""
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger(__name__)


class ArubaConfig:
    """Aruba SDI API configuration."""
    SANDBOX_URL = "https://demofatture.aruba.it/services/invoice/v2"
    PRODUCTION_URL = "https://fattureapi.aruba.it/services/invoice/v2"

    @staticmethod
    def get_base_url() -> str:
        if settings.sdi_environment == "production":
            return ArubaConfig.PRODUCTION_URL
        return ArubaConfig.SANDBOX_URL


# ── Payment Condition Mapping ──

CONDIZIONI_PAGAMENTO_MAP = {
    "30gg_dffm": "TP02",  # Pagamento completo a 30gg
    "60gg_dffm": "TP02",
    "90gg_dffm": "TP02",
    "rimessa_diretta": "TP02",
    "contanti": "TP02",
    "bonifico": "TP02",
    "riba_30": "TP01",  # Rate
    "riba_60": "TP01",
    "riba_30_60": "TP01",
    "riba_30_60_90": "TP01",
}

MODALITA_PAGAMENTO_MAP = {
    "contanti": "MP01",
    "assegno": "MP02",
    "bonifico": "MP05",
    "riba": "MP12",
    "carta_credito": "MP08",
    "domiciliazione": "MP19",
    "pagopa": "MP23",
}


def converti_condizioni_pagamento(payment_type: str) -> str:
    """Convert internal payment type to FatturaPA TP code."""
    return CONDIZIONI_PAGAMENTO_MAP.get(payment_type, "TP02")


def calcola_scadenza_pagamento(data_fattura: datetime, giorni: int) -> str:
    """Calculate payment due date (DFFM - dalla fine del mese)."""
    from calendar import monthrange
    year = data_fattura.year
    month = data_fattura.month
    last_day = monthrange(year, month)[1]
    fine_mese = datetime(year, month, last_day)

    from datetime import timedelta
    scadenza = fine_mese + timedelta(days=giorni)
    return scadenza.strftime("%Y-%m-%d")


class FatturaPA_Generator:
    """Generate FatturaPA XML 1.2 compliant documents."""

    @staticmethod
    def generate_xml(invoice: dict, company: dict, client: dict) -> str:
        """Generate FatturaPA XML from invoice, company and client data."""
        now = datetime.now(timezone.utc)

        # Header
        trasmittente_paese = "IT"
        trasmittente_codice = company.get("partita_iva", "")
        codice_destinatario = client.get("codice_sdi", "0000000")
        pec = client.get("pec", "")

        # Determine document type
        doc_type = invoice.get("document_type", "FT")
        tipo_documento_map = {"FT": "TD01", "NC": "TD04", "PRV": "TD01"}
        tipo_documento = tipo_documento_map.get(doc_type, "TD01")

        lines = invoice.get("lines", [])
        totals = invoice.get("totals", {})

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>{trasmittente_paese}</IdPaese>
        <IdCodice>{trasmittente_codice}</IdCodice>
      </IdTrasmittente>
      <ProgressivoInvio>{invoice.get('document_number', '')}</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{codice_destinatario}</CodiceDestinatario>
      {"<PECDestinatario>" + pec + "</PECDestinatario>" if pec and codice_destinatario == "0000000" else ""}
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{company.get('partita_iva', '')}</IdCodice>
        </IdFiscaleIVA>
        <CodiceFiscale>{company.get('codice_fiscale', company.get('partita_iva', ''))}</CodiceFiscale>
        <Anagrafica>
          <Denominazione>{company.get('business_name', '')}</Denominazione>
        </Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>{company.get('address', '')}</Indirizzo>
        <CAP>{company.get('cap', '00000')}</CAP>
        <Comune>{company.get('city', '')}</Comune>
        <Provincia>{company.get('province', '')}</Provincia>
        <Nazione>IT</Nazione>
      </Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{client.get('partita_iva', '')}</IdCodice>
        </IdFiscaleIVA>
        <CodiceFiscale>{client.get('codice_fiscale', client.get('partita_iva', ''))}</CodiceFiscale>
        <Anagrafica>
          <Denominazione>{client.get('business_name', '')}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>{client.get('address', '')}</Indirizzo>
        <CAP>{client.get('cap', '00000')}</CAP>
        <Comune>{client.get('city', '')}</Comune>
        <Provincia>{client.get('province', '')}</Provincia>
        <Nazione>{client.get('country', 'IT')}</Nazione>
      </Sede>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>{tipo_documento}</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>{now.strftime('%Y-%m-%d')}</Data>
        <Numero>{invoice.get('document_number', '')}</Numero>
        <ImportoTotaleDocumento>{totals.get('total_document', 0):.2f}</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>"""

        # Add lines
        for i, line in enumerate(lines, 1):
            aliquota = line.get("iva_rate", 22)
            xml += f"""
      <DettaglioLinee>
        <NumeroLinea>{i}</NumeroLinea>
        <Descrizione>{line.get('description', '')}</Descrizione>
        <Quantita>{line.get('quantity', 1):.2f}</Quantita>
        <PrezzoUnitario>{line.get('unit_price', 0):.2f}</PrezzoUnitario>
        <PrezzoTotale>{line.get('total', 0):.2f}</PrezzoTotale>
        <AliquotaIVA>{aliquota:.2f}</AliquotaIVA>
      </DettaglioLinee>"""

        # Riepilogo IVA
        iva_totale = totals.get("total_iva", 0)
        imponibile = totals.get("taxable_amount", totals.get("total_document", 0) - iva_totale)
        xml += f"""
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>{imponibile:.2f}</ImponibileImporto>
        <Imposta>{iva_totale:.2f}</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        return xml


class ArubaSDI_Client:
    """Client for Aruba SDI API."""

    def __init__(self):
        self.base_url = ArubaConfig.get_base_url()
        self.api_key = settings.sdi_api_key
        self.api_secret = settings.sdi_api_secret
        self._token = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    async def _get_token(self) -> Optional[str]:
        """Authenticate with Aruba and get access token."""
        if not self.is_configured:
            logger.warning("Aruba SDI not configured (missing API_KEY/SECRET)")
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/auth/signin",
                    json={"username": self.api_key, "password": self.api_secret},
                )
                resp.raise_for_status()
                data = resp.json()
                self._token = data.get("access_token")
                return self._token
        except Exception as e:
            logger.error(f"Aruba auth failed: {e}")
            return None

    async def _headers(self) -> Dict[str, str]:
        token = self._token or await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def send_invoice(self, xml_content: str, filename: str) -> Dict[str, Any]:
        """Send FatturaPA XML to SDI via Aruba."""
        if not self.is_configured:
            return {"success": False, "error": "Aruba SDI non configurato"}

        import base64
        encoded = base64.b64encode(xml_content.encode()).decode()

        try:
            headers = await self._headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/invoices/upload",
                    headers=headers,
                    json={
                        "dataFile": encoded,
                        "credential": "",
                        "domain": "",
                    },
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Invoice sent to SDI: {filename} -> {result}")
                return {"success": True, "sdi_id": result.get("uploadFileName"), "data": result}
        except Exception as e:
            logger.error(f"SDI send failed: {e}")
            return {"success": False, "error": str(e)}

    async def check_status(self, sdi_id: str) -> Dict[str, Any]:
        """Check the status of a sent invoice."""
        if not self.is_configured:
            return {"success": False, "error": "Aruba SDI non configurato"}

        try:
            headers = await self._headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/invoices/notifications",
                    headers=headers,
                    params={"invoiceId": sdi_id},
                )
                resp.raise_for_status()
                return {"success": True, "data": resp.json()}
        except Exception as e:
            logger.error(f"SDI status check failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton
aruba_sdi = ArubaSDI_Client()
fatturapa_generator = FatturaPA_Generator()

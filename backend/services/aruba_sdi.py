"""
NormaFacile - Aruba SDI Integration
Fatturazione Elettronica via Aruba API (Sistema di Interscambio).
Credentials are read from MongoDB company_settings (aruba_username, aruba_password, aruba_sandbox).
"""
import logging
import httpx
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


SANDBOX_URL = "https://demofatture.aruba.it/services/invoice/v2"
PRODUCTION_URL = "https://fattureapi.aruba.it/services/invoice/v2"

# ── Payment Condition Mapping ──
CONDIZIONI_PAGAMENTO_MAP = {
    "30gg_dffm": "TP02",
    "60gg_dffm": "TP02",
    "90gg_dffm": "TP02",
    "rimessa_diretta": "TP02",
    "contanti": "TP02",
    "bonifico": "TP02",
    "riba_30": "TP01",
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
    return CONDIZIONI_PAGAMENTO_MAP.get(payment_type, "TP02")


def calcola_scadenza_pagamento(data_fattura: datetime, giorni: int) -> str:
    from calendar import monthrange
    from datetime import timedelta
    last_day = monthrange(data_fattura.year, data_fattura.month)[1]
    fine_mese = datetime(data_fattura.year, data_fattura.month, last_day)
    scadenza = fine_mese + timedelta(days=giorni)
    return scadenza.strftime("%Y-%m-%d")


class FatturaPA_Generator:
    """Generate FatturaPA XML 1.2.2 compliant documents."""

    @staticmethod
    def generate_xml(invoice: dict, company: dict, client: dict) -> str:
        now = datetime.now(timezone.utc)
        trasmittente_paese = "IT"
        trasmittente_codice = company.get("partita_iva", "")
        codice_destinatario = client.get("codice_sdi", "0000000")
        pec = client.get("pec", "")

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


async def get_aruba_credentials(user_id: str) -> Dict[str, Any]:
    """Get Aruba SDI credentials from company_settings in MongoDB."""
    from core.database import db
    settings = await db.company_settings.find_one(
        {"user_id": user_id}, {"_id": 0, "aruba_username": 1, "aruba_password": 1, "aruba_sandbox": 1}
    )
    if not settings:
        return {}
    return {
        "username": settings.get("aruba_username", ""),
        "password": settings.get("aruba_password", ""),
        "sandbox": settings.get("aruba_sandbox", True),
    }


async def aruba_authenticate(username: str, password: str, sandbox: bool = True) -> Optional[str]:
    """Authenticate with Aruba OAuth2 and return access token."""
    base_url = SANDBOX_URL if sandbox else PRODUCTION_URL
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url}/auth/signin",
                json={"username": username, "password": password},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("access_token")
    except Exception as e:
        logger.error(f"Aruba auth failed: {e}")
        return None


async def send_invoice_to_sdi(xml_content: str, filename: str, user_id: str) -> Dict[str, Any]:
    """Send FatturaPA XML to SDI via Aruba. Reads credentials from DB."""
    creds = await get_aruba_credentials(user_id)
    if not creds.get("username") or not creds.get("password"):
        return {"success": False, "error": "Credenziali Aruba non configurate. Vai su Impostazioni > Integrazioni."}

    sandbox = creds.get("sandbox", True)
    base_url = SANDBOX_URL if sandbox else PRODUCTION_URL

    token = await aruba_authenticate(creds["username"], creds["password"], sandbox)
    if not token:
        return {"success": False, "error": "Autenticazione Aruba fallita. Verifica username e password."}

    encoded = base64.b64encode(xml_content.encode()).decode()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/invoices/upload",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"dataFile": encoded, "credential": "", "domain": ""},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Invoice sent to SDI: {filename} -> {result}")
            return {"success": True, "sdi_id": result.get("uploadFileName"), "data": result}
    except Exception as e:
        logger.error(f"SDI send failed: {e}")
        return {"success": False, "error": f"Errore invio SDI: {str(e)}"}


async def check_sdi_status(sdi_id: str, user_id: str) -> Dict[str, Any]:
    """Check the status of a sent invoice on Aruba SDI."""
    creds = await get_aruba_credentials(user_id)
    if not creds.get("username") or not creds.get("password"):
        return {"success": False, "error": "Credenziali Aruba non configurate."}

    sandbox = creds.get("sandbox", True)
    base_url = SANDBOX_URL if sandbox else PRODUCTION_URL

    token = await aruba_authenticate(creds["username"], creds["password"], sandbox)
    if not token:
        return {"success": False, "error": "Autenticazione Aruba fallita."}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{base_url}/invoices/notifications",
                headers={"Authorization": f"Bearer {token}"},
                params={"invoiceId": sdi_id},
            )
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
    except Exception as e:
        logger.error(f"SDI status check failed: {e}")
        return {"success": False, "error": str(e)}


# Keep singleton for backwards compatibility
fatturapa_generator = FatturaPA_Generator()

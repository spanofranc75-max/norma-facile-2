"""
NormaFacile - Fatture in Cloud API v2 Integration
Sync fatture, clienti, fornitori, prodotti with Fatture in Cloud.
"""
import logging
import httpx
from typing import Optional, Dict, Any, List
from core.config import settings

logger = logging.getLogger(__name__)


class FattureInCloudConfig:
    """FattureInCloud API v2 configuration."""
    BASE_URL = "https://api-v2.fattureincloud.it"


# ── Status Mapping ──

STATO_FIC_TO_INTERNO = {
    "not_sent": "bozza",
    "sent": "emessa",
    "accepted": "accettata",
    "rejected": "rifiutata",
    "delivered": "inviata_sdi",
    "paid": "pagata",
}

STATO_INTERNO_TO_FIC = {v: k for k, v in STATO_FIC_TO_INTERNO.items()}


def map_stato_fic_to_interno(stato_fic: str) -> str:
    return STATO_FIC_TO_INTERNO.get(stato_fic, "bozza")


def map_stato_interno_to_fic(stato: str) -> str:
    return STATO_INTERNO_TO_FIC.get(stato, "not_sent")


class FattureInCloudClient:
    """Client for Fatture in Cloud API v2."""

    def __init__(self, access_token: Optional[str] = None, company_id: Optional[int] = None):
        self.base_url = FattureInCloudConfig.BASE_URL
        self.access_token = access_token or settings.sdi_api_key
        self.company_id = company_id
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.company_id)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to FIC API."""
        url = f"{self.base_url}/c/{self.company_id}{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(method, url, headers=self._headers(), **kwargs)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"FIC API error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"FIC request failed: {e}")
            raise

    # ── Clients ──

    async def list_clients(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/entities/clients", params={"page": page, "per_page": per_page})

    async def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/entities/clients", json={"data": data})

    # ── Suppliers ──

    async def list_suppliers(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/entities/suppliers", params={"page": page, "per_page": per_page})

    # ── Products ──

    async def list_products(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/products", params={"page": page, "per_page": per_page})

    # ── Issued Invoices ──

    async def list_issued_invoices(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "invoice",
            "page": page,
            "per_page": per_page,
        })

    async def create_issued_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/issued_documents", json={"data": invoice_data})

    async def update_issued_invoice(self, document_id: int, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/issued_documents/{document_id}", json={"data": invoice_data})

    async def send_to_sdi(self, document_id: int) -> Dict[str, Any]:
        """Send an issued document to SDI via FattureInCloud."""
        return await self._request("POST", f"/issued_documents/{document_id}/e_invoice/send")

    async def get_sdi_status(self, document_id: int) -> Dict[str, Any]:
        """Get SDI status for a document."""
        return await self._request("GET", f"/issued_documents/{document_id}/e_invoice/xml")

    # ── Received Invoices ──

    async def list_received_invoices(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/received_documents", params={
            "type": "expense",
            "page": page,
            "per_page": per_page,
        })

    async def get_received_document_detail(self, document_id: str) -> Dict[str, Any]:
        """Get detailed received document including items_list."""
        return await self._request("GET", f"/received_documents/{document_id}", params={
            "fieldset": "detailed",
        })


    # ── DDT ──

    async def list_ddts(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "delivery_note",
            "page": page,
            "per_page": per_page,
        })

    # ── Quotes ──

    async def list_quotes(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "quote",
            "page": page,
            "per_page": per_page,
        })

    # ── IVA Rates ──

    async def list_vat_types(self) -> Dict[str, Any]:
        return await self._request("GET", "/info/vat_types")


def map_fattura_to_fic(invoice: dict, client: dict) -> Dict[str, Any]:
    """Map internal invoice format to FattureInCloud format."""
    items = []
    for line in invoice.get("lines", []):
        vat_val = line.get("vat_rate", 22)
        try:
            vat_val = float(vat_val) if str(vat_val) not in ("N3", "N4", "N1", "N2") else 0
        except (ValueError, TypeError):
            vat_val = 22
        items.append({
            "product_id": None,
            "code": line.get("code", ""),
            "name": line.get("description", ""),
            "net_price": line.get("unit_price", 0),
            "qty": line.get("quantity", 1),
            "vat": {"id": 0, "value": vat_val},
            "discount": line.get("discount_percent", 0),
        })

    # Extract numeric part from document_number (e.g. "16/2026" -> 16)
    doc_num_raw = invoice.get("document_number", "")
    try:
        doc_number_int = int(str(doc_num_raw).split("/")[0])
    except (ValueError, IndexError):
        doc_number_int = 0

    return {
        "type": "invoice",
        "entity": {
            "name": client.get("business_name", ""),
            "vat_number": client.get("partita_iva", ""),
            "tax_code": client.get("codice_fiscale", ""),
            "address_street": client.get("address", ""),
            "address_postal_code": client.get("cap", ""),
            "address_city": client.get("city", ""),
            "address_province": client.get("province", ""),
            "country": "Italia",
            "country_iso": client.get("country", "IT"),
            "ei_code": client.get("codice_sdi", "0000000"),
            "certified_email": client.get("pec", ""),
        },
        "date": invoice.get("issue_date") or (invoice.get("created_at", "").split("T")[0] if isinstance(invoice.get("created_at"), str) else None),
        "number": doc_number_int,
        "items_list": items,
        "payment_method": {"id": 0},
    }


# Factory
def get_fic_client(access_token: str = None, company_id: int = None) -> FattureInCloudClient:
    return FattureInCloudClient(access_token=access_token, company_id=company_id)

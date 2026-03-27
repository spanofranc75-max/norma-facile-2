"""
1090 Norma Facile - Fatture in Cloud API v2 Integration
Hardened: retry, error classification, idempotency, structured logging.
"""
import json
import logging
import hashlib
import asyncio
import httpx
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
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


# ── Error Classification ──

class FiCErrorCategory:
    AUTH = "auth"                 # 401 — token scaduto/invalido
    FORBIDDEN = "forbidden"      # 403 — permessi insufficienti
    NOT_FOUND = "not_found"      # 404 — risorsa non trovata
    VALIDATION = "validation"    # 422 — dati non validi
    RATE_LIMIT = "rate_limit"    # 429 — troppe richieste
    TRANSIENT = "transient"      # 500/502/503/504 — retry possibile
    TIMEOUT = "timeout"          # timeout di rete
    NETWORK = "network"          # errore di connessione
    UNKNOWN = "unknown"          # altro


def classify_error(exc: Exception) -> Tuple[str, str, bool]:
    """Classify an error into category, message, and whether it's retryable.
    Returns: (category, human_message, is_retryable)
    """
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        body_msg = _extract_error_body(exc)

        if code == 401:
            return (FiCErrorCategory.AUTH,
                    "Token FattureInCloud scaduto o non valido. "
                    "Genera un nuovo token dal tuo account FattureInCloud "
                    "(Impostazioni > Connessioni API).",
                    False)
        if code == 403:
            return (FiCErrorCategory.FORBIDDEN,
                    "Permessi insufficienti sul token FattureInCloud. "
                    "Verifica che il token abbia i permessi necessari.",
                    False)
        if code == 404:
            return (FiCErrorCategory.NOT_FOUND,
                    f"Risorsa non trovata su FattureInCloud. {body_msg}",
                    False)
        if code == 422:
            return (FiCErrorCategory.VALIDATION,
                    f"Dati non validi per FattureInCloud: {body_msg}",
                    False)
        if code == 429:
            return (FiCErrorCategory.RATE_LIMIT,
                    "Troppe richieste a FattureInCloud. Riprova tra 30 secondi.",
                    True)
        if code in (500, 502, 503, 504):
            return (FiCErrorCategory.TRANSIENT,
                    f"FattureInCloud temporaneamente non disponibile (HTTP {code}). Riprovo automaticamente.",
                    True)

        return (FiCErrorCategory.UNKNOWN, f"Errore FattureInCloud HTTP {code}: {body_msg}", False)

    if isinstance(exc, httpx.TimeoutException):
        return (FiCErrorCategory.TIMEOUT,
                "FattureInCloud non risponde (timeout). Riprovo automaticamente.",
                True)
    if isinstance(exc, httpx.ConnectError):
        return (FiCErrorCategory.NETWORK,
                "Impossibile connettersi a FattureInCloud. Verifica la connessione.",
                True)

    return (FiCErrorCategory.UNKNOWN, f"Errore imprevisto: {str(exc)}", False)


def _extract_error_body(exc: httpx.HTTPStatusError) -> str:
    """Extract human-readable message from FiC error response."""
    try:
        body = exc.response.json()
        error_obj = body.get("error", {})
        message = error_obj.get("message", "")
        validation = error_obj.get("validation_result", None)
        extra = body.get("extra", {})

        parts = []
        if message:
            parts.append(message)
        if validation:
            for field, msgs in validation.items():
                if isinstance(msgs, list):
                    parts.append(f"{field}: {', '.join(msgs)}")
                else:
                    parts.append(f"{field}: {msgs}")
        if extra and extra.get("totals"):
            t = extra["totals"]
            parts.append(f"(Netto: {t.get('amount_net')}, IVA: {t.get('amount_vat')}, Dovuto: {t.get('amount_due')})")

        return " | ".join(parts) if parts else str(exc)
    except Exception:
        return str(exc)


# Keep backward compat
def extract_fic_error_message(exc: httpx.HTTPStatusError) -> str:
    return _extract_error_body(exc)


class FattureInCloudClient:
    """Hardened client for Fatture in Cloud API v2.

    Features:
    - Automatic retry with exponential backoff for transient errors
    - Error classification (auth, validation, transient, etc.)
    - Idempotency key for write operations
    - Structured logging
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 3, 8]  # seconds between retries

    def __init__(self, access_token: Optional[str] = None, company_id: Optional[int] = None):
        self.base_url = FattureInCloudConfig.BASE_URL
        self.access_token = access_token or settings.fic_access_token
        self.company_id = company_id
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.company_id)

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return h

    async def _request(self, method: str, endpoint: str,
                       idempotency_key: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to FIC API with retry logic."""
        if settings.safe_mode:
            logger.info(f"[SAFE MODE] FiC {method} {endpoint} bloccata — SAFE_MODE attivo")
            return {"error": "safe_mode", "message": "SAFE MODE attivo: chiamate FattureInCloud disabilitate"}

        url = f"{self.base_url}/c/{self.company_id}{endpoint}"
        last_exc = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                    headers = self._headers(idempotency_key)
                    if 'json' in kwargs:
                        body = json.dumps(kwargs.pop('json'), ensure_ascii=True, default=str)
                        resp = await client.request(method, url, headers=headers, content=body, **kwargs)
                    else:
                        resp = await client.request(method, url, headers=headers, **kwargs)
                    resp.raise_for_status()

                    if attempt > 0:
                        logger.info(f"[FiC] {method} {endpoint} — OK al tentativo {attempt + 1}")
                    return resp.json()

            except Exception as e:
                last_exc = e
                category, human_msg, retryable = classify_error(e)

                if not retryable or attempt >= self.MAX_RETRIES - 1:
                    logger.error(f"[FiC] {method} {endpoint} — ERRORE [{category}] "
                                 f"tentativo {attempt + 1}/{self.MAX_RETRIES}: {human_msg}")
                    raise
                else:
                    wait = self.RETRY_BACKOFF[attempt] if attempt < len(self.RETRY_BACKOFF) else 8
                    logger.warning(f"[FiC] {method} {endpoint} — [{category}] "
                                   f"tentativo {attempt + 1}/{self.MAX_RETRIES}, "
                                   f"retry tra {wait}s: {human_msg}")
                    await asyncio.sleep(wait)

        raise last_exc

    # ── Clients ──

    async def list_clients(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/entities/clients", params={"page": page, "per_page": per_page})

    async def create_client(self, data: Dict[str, Any]) -> Dict[str, Any]:
        key = _idempotency_key("create_client", data)
        return await self._request("POST", "/entities/clients", idempotency_key=key, json={"data": data})

    # ── Suppliers ──

    async def list_suppliers(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/entities/suppliers", params={"page": page, "per_page": per_page})

    # ── Products ──

    async def list_products(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/products", params={"page": page, "per_page": per_page})

    # ── Issued Invoices ──

    async def list_issued_invoices(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "invoice", "page": page, "per_page": per_page,
        })

    async def create_issued_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        key = _idempotency_key("create_invoice", invoice_data)
        return await self._request("POST", "/issued_documents", idempotency_key=key, json={"data": invoice_data})

    async def update_issued_invoice(self, document_id: int, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/issued_documents/{document_id}", json={"data": invoice_data})

    async def send_to_sdi(self, document_id: int) -> Dict[str, Any]:
        """Send an issued document to SDI via FattureInCloud.
        Uses idempotency key to prevent double-send."""
        key = _idempotency_key("send_sdi", {"doc_id": document_id})
        logger.info(f"[FiC/SDI] Invio documento {document_id} a SDI (idempotency: {key[:12]}...)")
        return await self._request("POST", f"/issued_documents/{document_id}/e_invoice/send",
                                   idempotency_key=key)

    async def get_sdi_status(self, document_id: int) -> Dict[str, Any]:
        """Get SDI status for a document."""
        return await self._request("GET", f"/issued_documents/{document_id}/e_invoice/xml")

    # ── Received Invoices ──

    async def list_received_invoices(self, page: int = 1, per_page: int = 50, **extra_params) -> Dict[str, Any]:
        params = {"type": "expense", "page": page, "per_page": per_page}
        params.update(extra_params)
        return await self._request("GET", "/received_documents", params=params)

    async def get_received_document_detail(self, document_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/received_documents/{document_id}", params={
            "fieldset": "detailed",
        })

    # ── DDT ──

    async def list_ddts(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "delivery_note", "page": page, "per_page": per_page,
        })

    # ── Quotes ──

    async def list_quotes(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return await self._request("GET", "/issued_documents", params={
            "type": "quote", "page": page, "per_page": per_page,
        })

    # ── IVA Rates ──

    async def list_vat_types(self) -> Dict[str, Any]:
        return await self._request("GET", "/info/vat_types")


# ── IDEMPOTENCY KEY GENERATOR ──

def _idempotency_key(operation: str, data: Any) -> str:
    """Generate a stable idempotency key from operation + data.
    Same operation + same data = same key → prevents double-send."""
    raw = json.dumps({"op": operation, "d": data}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ── VALIDAZIONE PRE-INVIO SDI ──

def validate_invoice_for_sdi(invoice: dict, client: dict, company: dict) -> list:
    """
    Validates ALL required fields before sending to FIC/SDI.
    Returns a list of error strings. Empty list = validation passed.
    """
    errors = []

    # --- MITTENTE (Company) ---
    if not company.get("partita_iva"):
        errors.append("Mittente: manca la Partita IVA dell'azienda (Impostazioni)")
    if not company.get("codice_fiscale"):
        errors.append("Mittente: manca il Codice Fiscale dell'azienda (Impostazioni)")
    if not company.get("address"):
        errors.append("Mittente: manca l'Indirizzo dell'azienda (Impostazioni)")
    if not company.get("cap"):
        errors.append("Mittente: manca il CAP dell'azienda (Impostazioni)")
    if not company.get("city"):
        errors.append("Mittente: manca la Citta' dell'azienda (Impostazioni)")

    # --- DESTINATARIO (Client) ---
    if not client:
        errors.append("Destinatario: cliente non trovato")
        return errors

    if not client.get("partita_iva") and not client.get("codice_fiscale"):
        errors.append("Destinatario: manca P.IVA o Codice Fiscale del cliente")
    if not client.get("address"):
        errors.append("Destinatario: manca l'Indirizzo del cliente")
    if not client.get("cap"):
        errors.append("Destinatario: manca il CAP del cliente")
    if not client.get("city"):
        errors.append("Destinatario: manca la Citta' del cliente")
    if not client.get("codice_sdi") and not client.get("pec"):
        errors.append("Destinatario: manca il Codice SDI o la PEC del cliente")
    elif client.get("codice_sdi", "").strip() in ("", "0000000") and not client.get("pec"):
        errors.append("Destinatario: Codice SDI e '0000000' (generico) e la PEC e vuota. "
                       "SDI non puo recapitare senza almeno uno dei due. "
                       "Aggiungi un Codice SDI valido oppure la PEC del cliente.")

    # --- DOCUMENTO ---
    lines = invoice.get("lines", [])
    valid_lines = [ln for ln in lines if ln.get("description", "").strip()]
    if not valid_lines:
        errors.append("Documento: nessuna riga articolo con descrizione")

    totals = invoice.get("totals", {})
    total_doc = totals.get("total_document", 0)
    if total_doc is None or (total_doc <= 0 and invoice.get("document_type") != "NC"):
        errors.append(f"Documento: totale documento non valido ({total_doc})")

    if not invoice.get("issue_date"):
        errors.append("Documento: manca la data di emissione")

    doc_num = invoice.get("document_number", "")
    if not doc_num:
        errors.append("Documento: manca il numero documento")

    return errors


def _sanitize(text: str) -> str:
    """Remove non-ASCII characters that FIC API rejects."""
    if not text:
        return ""
    return text.encode('ascii', errors='ignore').decode('ascii').strip()


def map_fattura_to_fic(invoice: dict, client: dict) -> Dict[str, Any]:
    """Map internal invoice format to FattureInCloud format."""
    items = []
    for line in invoice.get("lines", []):
        desc = _sanitize(line.get("description", ""))
        if not desc:
            continue
        vat_val = line.get("vat_rate", 22)
        try:
            vat_val = float(vat_val) if str(vat_val) not in ("N3", "N4", "N1", "N2") else 0
        except (ValueError, TypeError):
            vat_val = 22
        items.append({
            "product_id": None,
            "code": _sanitize(line.get("code", "")),
            "name": desc,
            "net_price": float(line.get("unit_price") or 0),
            "qty": float(line.get("quantity") or 1),
            "vat": {"id": 0, "value": vat_val},
            "discount": float(line.get("discount_percent") or 0),
        })

    doc_num_raw = invoice.get("document_number", "")
    try:
        num_part = str(doc_num_raw).split("/")[0]
        num_part = num_part.split("-")[-1] if "-" in num_part else num_part
        doc_number_int = int(num_part)
    except (ValueError, IndexError):
        doc_number_int = 0

    totals = invoice.get("totals") or {}
    amount_due = float(totals.get("total_document", 0) or 0)
    if not amount_due:
        amount_due = sum(
            (float(line.get("line_total", 0)) + float(line.get("vat_amount", 0)))
            for line in invoice.get("lines", []) if line.get("description", "").strip()
        )

    payment_method_code = invoice.get("payment_method", "bonifico")
    ei_payment_map = {
        "bonifico": "MP05",
        "contanti": "MP01",
        "assegno": "MP02",
        "carta_credito": "MP08",
        "riba": "MP12",
        "rid": "MP09",
        "rimessa_diretta": "MP01",
    }
    ei_payment = ei_payment_map.get(payment_method_code, "MP05")

    doc_type = invoice.get("document_type", "FT")
    payload = {
        "type": "credit_note" if doc_type == "NC" else "invoice",
        "e_invoice": True,
        "ei_data": {
            "payment_method": ei_payment,
        },
        "entity": {
            "name": _sanitize(client.get("business_name") or ""),
            "vat_number": _sanitize(client.get("partita_iva") or ""),
            "tax_code": _sanitize(client.get("codice_fiscale") or ""),
            "address_street": _sanitize(client.get("address") or ""),
            "address_postal_code": _sanitize(client.get("cap") or ""),
            "address_city": _sanitize(client.get("city") or ""),
            "address_province": _sanitize(client.get("province") or ""),
            "country": "Italia",
            "country_iso": _sanitize(client.get("country") or "IT"),
            "ei_code": _sanitize(client.get("codice_sdi") or "0000000"),
            "certified_email": _sanitize(client.get("pec") or ""),
        },
        "date": invoice.get("issue_date") or None,
        "number": doc_number_int,
        "items_list": items,
        "payments_list": [
            {
                "amount": round(amount_due, 2),
                "due_date": invoice.get("due_date") or invoice.get("issue_date"),
                "paid_date": None,
                "status": "not_paid",
                "payment_account": None,
            }
        ],
    }

    logger.info(f"[FiC] Payload SDI preparato: doc_number={doc_num_raw}, "
                f"entity={payload['entity']['name']}, amount={amount_due:.2f}")

    return payload


# Factory
def get_fic_client(access_token: str = None, company_id: int = None) -> FattureInCloudClient:
    return FattureInCloudClient(access_token=access_token, company_id=company_id)

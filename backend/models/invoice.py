"""Invoice models for fatturazione elettronica."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
from decimal import Decimal


class DocumentType(str, Enum):
    """Tipo documento."""
    FATTURA = "FT"
    PREVENTIVO = "PRV"
    DDT = "DDT"
    NOTA_CREDITO = "NC"


class InvoiceStatus(str, Enum):
    """Stato documento."""
    BOZZA = "bozza"
    EMESSA = "emessa"
    INVIATA_SDI = "inviata_sdi"
    ACCETTATA = "accettata"
    RIFIUTATA = "rifiutata"
    PAGATA = "pagata"
    SCADUTA = "scaduta"
    ANNULLATA = "annullata"


class PaymentMethod(str, Enum):
    """Metodo di pagamento."""
    BONIFICO = "bonifico"
    CONTANTI = "contanti"
    CARTA = "carta"
    ASSEGNO = "assegno"
    RIBA = "riba"
    ALTRO = "altro"


class PaymentTerms(str, Enum):
    """Termini di pagamento."""
    IMMEDIATO = "immediato"
    GG_30 = "30gg"
    GG_60 = "60gg"
    GG_90 = "90gg"
    GG_30_60 = "30-60gg"
    GG_30_60_90 = "30-60-90gg"
    FINE_MESE = "fine_mese"
    FINE_MESE_30 = "fm+30"


class VATRate(str, Enum):
    """Aliquote IVA comuni."""
    IVA_22 = "22"
    IVA_10 = "10"
    IVA_4 = "4"
    IVA_0 = "0"
    ESENTE = "N4"  # Esente art. 10
    NON_IMPONIBILE = "N3"  # Non imponibile


# ============ LINE ITEMS ============

class InvoiceLineBase(BaseModel):
    """Base invoice line item."""
    code: Optional[str] = None
    description: str
    quantity: float = Field(default=1.0, ge=0)
    unit_price: float = Field(default=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    vat_rate: str = "22"  # Can be number or code like N4
    
    # Calculated fields (computed on save)
    line_total: Optional[float] = None
    vat_amount: Optional[float] = None


class InvoiceLineCreate(InvoiceLineBase):
    """Model for creating an invoice line."""
    pass


class InvoiceLine(InvoiceLineBase):
    """Full invoice line with computed values."""
    model_config = ConfigDict(extra="ignore")
    
    line_id: str
    line_total: float = 0.0
    vat_amount: float = 0.0


# ============ TAX SETTINGS ============

class TaxSettings(BaseModel):
    """Impostazioni fiscali aggiuntive."""
    # Rivalsa INPS (4% per professionisti)
    apply_rivalsa_inps: bool = False
    rivalsa_inps_rate: float = 4.0
    
    # Cassa Previdenza (es. Cassa Forense)
    apply_cassa: bool = False
    cassa_type: Optional[str] = None  # "forense", "geometri", etc.
    cassa_rate: float = 4.0
    
    # Ritenuta d'acconto
    apply_ritenuta: bool = False
    ritenuta_rate: float = 20.0
    ritenuta_base: str = "imponibile"  # "imponibile" or "totale"


# ============ INVOICE ============

class InvoiceBase(BaseModel):
    """Base invoice model."""
    document_type: DocumentType = DocumentType.FATTURA
    client_id: str
    
    # Date
    issue_date: date = Field(default_factory=date.today)
    due_date: Optional[date] = None
    
    # Payment
    payment_method: PaymentMethod = PaymentMethod.BONIFICO
    payment_terms: PaymentTerms = PaymentTerms.GG_30
    
    # Tax settings
    tax_settings: TaxSettings = Field(default_factory=TaxSettings)
    
    # Notes
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Model for creating an invoice."""
    lines: List[InvoiceLineCreate] = []
    document_number: Optional[str] = None  # If provided, use instead of auto-generated


class InvoiceUpdate(BaseModel):
    """Model for updating an invoice."""
    document_number: Optional[str] = None
    client_id: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_method: Optional[PaymentMethod] = None
    payment_terms: Optional[PaymentTerms] = None
    tax_settings: Optional[TaxSettings] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: Optional[List[InvoiceLineCreate]] = None


class InvoiceTotals(BaseModel):
    """Calculated invoice totals."""
    subtotal: float = 0.0  # Sum of line totals before tax
    
    # VAT breakdown by rate
    vat_breakdown: dict = {}  # {"22": {"imponibile": 100, "imposta": 22}, ...}
    total_vat: float = 0.0
    
    # Additional taxes
    rivalsa_inps: float = 0.0
    cassa: float = 0.0
    ritenuta: float = 0.0
    
    # Final total
    total_document: float = 0.0
    total_to_pay: float = 0.0  # total_document - ritenuta


class Invoice(InvoiceBase):
    """Full invoice model."""
    model_config = ConfigDict(extra="ignore")
    
    invoice_id: str
    user_id: str
    
    # Document number (FT-2026-001)
    document_number: str
    
    # Status
    status: InvoiceStatus = InvoiceStatus.BOZZA
    
    # Lines
    lines: List[InvoiceLine] = []
    
    # Totals
    totals: InvoiceTotals = Field(default_factory=InvoiceTotals)
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Conversion tracking
    converted_from: Optional[str] = None  # invoice_id of source document
    converted_to: Optional[List[str]] = None  # invoice_ids of converted documents


class InvoiceResponse(BaseModel):
    """Invoice response for API."""
    model_config = ConfigDict(extra="ignore")
    
    invoice_id: str
    document_type: DocumentType
    document_number: str
    client_id: str
    client_name: Optional[str] = None  # Populated from client
    
    issue_date: date
    due_date: Optional[date] = None
    
    status: InvoiceStatus
    
    payment_method: PaymentMethod
    payment_terms: PaymentTerms
    
    lines: List[InvoiceLine] = []
    totals: InvoiceTotals
    tax_settings: TaxSettings
    
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    converted_from: Optional[str] = None
    converted_to: Optional[List[str]] = None
    
    # Payment tracking fields
    pagamenti: Optional[List[dict]] = []
    totale_pagato: Optional[float] = 0.0
    residuo: Optional[float] = 0.0
    payment_status: Optional[str] = "non_pagata"


class InvoiceListResponse(BaseModel):
    """List of invoices response."""
    invoices: List[InvoiceResponse]
    total: int


class InvoiceStatusUpdate(BaseModel):
    """Model for updating invoice status."""
    status: InvoiceStatus


class ConvertInvoiceRequest(BaseModel):
    """Request to convert document (e.g., Preventivo -> Fattura)."""
    target_type: DocumentType
    source_ids: List[str]  # Can merge multiple DDTs into one invoice

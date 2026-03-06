"""Payment Type models — Tipi Pagamento personalizzabili stile Invoicex."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class QuotaItem(BaseModel):
    """Single installment: days from invoice date + percentage share."""
    giorni: int = Field(..., description="Giorni dalla data fattura")
    quota: float = Field(default=100.0, description="Percentuale della quota (%)")


class PaymentTypeBase(BaseModel):
    """Tipo di Pagamento — configurable payment method with installment schedule."""
    codice: str = Field(..., description="Codice univoco (es: BB30, RB60)")
    tipo: str = Field(default="BON", description="BON=Bonifico, RIB=Ricevuta Bancaria, CON=Contanti, ELE=Elettronico")
    descrizione: str = Field(..., description="Descrizione leggibile")
    codice_fe: str = Field(default="", description="Codice fatturazione elettronica SDI (MP01-MP23)")
    # Installment schedule — new quote-based system
    quote: List[QuotaItem] = Field(default_factory=list, description="Rate: lista di {giorni, quota}")
    divisione_automatica: bool = Field(default=True, description="Divisione quote automatica (equipartita)")
    # Legacy installment flags (backward compat)
    immediato: bool = False
    gg_30: bool = False
    gg_60: bool = False
    gg_90: bool = False
    gg_120: bool = False
    gg_150: bool = False
    gg_180: bool = False
    gg_210: bool = False
    gg_240: bool = False
    gg_270: bool = False
    gg_300: bool = False
    gg_330: bool = False
    gg_360: bool = False
    # Options
    fine_mese: bool = False
    extra_days: Optional[int] = Field(default=None, description="Giorni aggiuntivi dopo il calcolo fine mese (es: FM+10)")
    richiedi_giorno_scadenza: bool = False
    giorno_scadenza: Optional[int] = Field(default=None, description="Giorno fisso del mese per scadenza (1-31)")
    iva_30gg: bool = False
    # Extra
    note_documento: str = ""
    spese_incasso: float = 0.0
    banca_necessaria: bool = False


class PaymentTypeCreate(PaymentTypeBase):
    pass


class PaymentTypeUpdate(BaseModel):
    codice: Optional[str] = None
    tipo: Optional[str] = None
    descrizione: Optional[str] = None
    codice_fe: Optional[str] = None
    quote: Optional[List[QuotaItem]] = None
    divisione_automatica: Optional[bool] = None
    immediato: Optional[bool] = None
    gg_30: Optional[bool] = None
    gg_60: Optional[bool] = None
    gg_90: Optional[bool] = None
    gg_120: Optional[bool] = None
    gg_150: Optional[bool] = None
    gg_180: Optional[bool] = None
    gg_210: Optional[bool] = None
    gg_240: Optional[bool] = None
    gg_270: Optional[bool] = None
    gg_300: Optional[bool] = None
    gg_330: Optional[bool] = None
    gg_360: Optional[bool] = None
    fine_mese: Optional[bool] = None
    extra_days: Optional[int] = None
    richiedi_giorno_scadenza: Optional[bool] = None
    giorno_scadenza: Optional[int] = None
    iva_30gg: Optional[bool] = None
    note_documento: Optional[str] = None
    spese_incasso: Optional[float] = None
    banca_necessaria: Optional[bool] = None


class PaymentTypeResponse(PaymentTypeBase):
    payment_type_id: str
    label: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaymentTypeListResponse(BaseModel):
    items: List[PaymentTypeResponse]
    total: int


class SimulateRequest(BaseModel):
    data_fattura: str = Field(..., description="Data fattura YYYY-MM-DD")
    importo: float = Field(default=10000.0, description="Importo totale fattura")


class SimulateDeadlineItem(BaseModel):
    rata: int
    giorni: int
    data_scadenza: str
    quota_pct: float
    importo: float


class SimulateResponse(BaseModel):
    scadenze: List[SimulateDeadlineItem]
    totale_rate: int
    importo_totale: float

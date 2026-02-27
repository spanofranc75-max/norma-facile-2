"""Payment Type models — Tipi Pagamento personalizzabili."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PaymentTypeBase(BaseModel):
    """Tipo di Pagamento — configurable payment method with installment schedule."""
    codice: str = Field(..., description="Codice univoco (es: BB30, RB60)")
    tipo: str = Field(default="BON", description="BON=Bonifico, RIB=Ricevuta Bancaria, CON=Contanti, ELE=Elettronico")
    descrizione: str = Field(..., description="Descrizione leggibile")
    # Installment schedule flags
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
    fine_mese: bool = False
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
    iva_30gg: Optional[bool] = None
    note_documento: Optional[str] = None
    spese_incasso: Optional[float] = None
    banca_necessaria: Optional[bool] = None


class PaymentTypeResponse(PaymentTypeBase):
    payment_type_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaymentTypeListResponse(BaseModel):
    items: List[PaymentTypeResponse]
    total: int

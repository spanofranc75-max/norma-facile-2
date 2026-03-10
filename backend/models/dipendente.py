"""
Models for Personale module — Dipendenti, Presenze, Documenti.
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone


class DipendenteModel(BaseModel):
    dipendente_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    nome: str
    cognome: str
    codice_fiscale: str = ""
    ruolo: str = ""
    tipo_contratto: str = "dipendente"  # dipendente/amministratore/socio
    ore_settimanali: float = 40.0
    giorni_lavorativi: list = Field(default_factory=lambda: ["lun", "mar", "mer", "gio", "ven", "sab"])
    email: str = ""
    attivo: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PresenzaModel(BaseModel):
    presenza_id: str = Field(default_factory=lambda: str(uuid4()))
    dipendente_id: str
    user_id: str
    data: str  # yyyy-mm-dd
    tipo: str = "presente"  # presente/assente/ferie/permesso/malattia/straordinario
    ore_lavorate: float = 0.0
    ore_straordinario: float = 0.0
    note: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DocumentoPersonaleModel(BaseModel):
    documento_id: str = Field(default_factory=lambda: str(uuid4()))
    dipendente_id: str
    user_id: str
    tipo: str = "altro"  # busta_paga/rimborso_spese/contratto/altro
    mese: str = ""  # yyyy-mm, solo per busta_paga
    descrizione: str = ""
    importo: float = 0.0  # per rimborso_spese
    file_url: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

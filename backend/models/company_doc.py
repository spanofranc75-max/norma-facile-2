"""Company Document model for the Archivio Documentale Aziendale module."""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone

CATEGORIES = ["manuali", "procedure", "certificazioni", "template", "normative", "altro"]
CategoryType = Literal["manuali", "procedure", "certificazioni", "template", "normative", "altro"]


class CompanyDocumentCreate(BaseModel):
    title: str
    category: CategoryType
    tags: List[str] = []


class CompanyDocumentResponse(BaseModel):
    doc_id: str
    title: str
    category: CategoryType
    filename: str
    content_type: str
    size_kb: int = 0
    tags: List[str] = []
    uploaded_by: Optional[str] = None
    upload_date: str


class CompanyDocumentList(BaseModel):
    items: List[CompanyDocumentResponse]
    total: int

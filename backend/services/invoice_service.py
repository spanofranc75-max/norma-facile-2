"""Invoice calculation and business logic service."""
import uuid
from datetime import datetime, timezone, date
from typing import List, Optional
from core.database import db
from models.invoice import (
    Invoice, InvoiceCreate, InvoiceUpdate, InvoiceLine, InvoiceLineCreate,
    InvoiceTotals, DocumentType, InvoiceStatus, TaxSettings
)
import logging

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for invoice business logic."""
    
    @staticmethod
    def calculate_line(line: InvoiceLineCreate) -> dict:
        """Calculate line total and VAT amount."""
        # Base calculation
        gross = line.quantity * line.unit_price
        
        # Apply discount
        if line.discount_percent > 0:
            discount = gross * (line.discount_percent / 100)
            net = gross - discount
        else:
            net = gross
        
        # Calculate VAT
        try:
            vat_rate = float(line.vat_rate) if line.vat_rate not in ['N3', 'N4'] else 0
        except ValueError:
            vat_rate = 0
        
        vat_amount = net * (vat_rate / 100)
        
        return {
            "line_id": f"line_{uuid.uuid4().hex[:8]}",
            "code": line.code,
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "discount_percent": line.discount_percent,
            "vat_rate": line.vat_rate,
            "line_total": round(net, 2),
            "vat_amount": round(vat_amount, 2)
        }
    
    @staticmethod
    def calculate_totals(lines: List[dict], tax_settings: TaxSettings) -> InvoiceTotals:
        """Calculate invoice totals with VAT breakdown and additional taxes."""
        subtotal = 0.0
        vat_breakdown = {}
        total_vat = 0.0
        
        # Sum up lines and build VAT breakdown
        for line in lines:
            subtotal += line["line_total"]
            total_vat += line["vat_amount"]
            
            rate = line["vat_rate"]
            if rate not in vat_breakdown:
                vat_breakdown[rate] = {"imponibile": 0.0, "imposta": 0.0}
            vat_breakdown[rate]["imponibile"] += line["line_total"]
            vat_breakdown[rate]["imposta"] += line["vat_amount"]
        
        # Round VAT breakdown
        for rate in vat_breakdown:
            vat_breakdown[rate]["imponibile"] = round(vat_breakdown[rate]["imponibile"], 2)
            vat_breakdown[rate]["imposta"] = round(vat_breakdown[rate]["imposta"], 2)
        
        # Calculate additional taxes
        rivalsa_inps = 0.0
        cassa = 0.0
        ritenuta = 0.0
        
        if tax_settings.apply_rivalsa_inps:
            rivalsa_inps = round(subtotal * (tax_settings.rivalsa_inps_rate / 100), 2)
        
        if tax_settings.apply_cassa:
            cassa = round(subtotal * (tax_settings.cassa_rate / 100), 2)
        
        # Total before ritenuta
        total_document = round(subtotal + total_vat + rivalsa_inps + cassa, 2)
        
        # Ritenuta (withholding tax)
        if tax_settings.apply_ritenuta:
            if tax_settings.ritenuta_base == "imponibile":
                ritenuta_base = subtotal
            else:
                ritenuta_base = total_document
            ritenuta = round(ritenuta_base * (tax_settings.ritenuta_rate / 100), 2)
        
        # Total to pay
        total_to_pay = round(total_document - ritenuta, 2)
        
        return InvoiceTotals(
            subtotal=round(subtotal, 2),
            vat_breakdown=vat_breakdown,
            total_vat=round(total_vat, 2),
            rivalsa_inps=rivalsa_inps,
            cassa=cassa,
            ritenuta=ritenuta,
            total_document=total_document,
            total_to_pay=total_to_pay
        )
    
    @staticmethod
    async def get_next_number(user_id: str, doc_type: DocumentType, year: int) -> str:
        """
        Get next document number in format TYPE-YEAR-NUMBER.
        Resets counter every year.
        """
        counter_id = f"{user_id}_{doc_type.value}_{year}"
        
        # Find and increment counter
        result = await db.document_counters.find_one_and_update(
            {"counter_id": counter_id},
            {"$inc": {"counter": 1}},
            upsert=True,
            return_document=True,
            projection={"_id": 0}
        )
        
        counter = result["counter"] if result else 1
        
        # Format: FT-2026-001
        return f"{doc_type.value}-{year}-{str(counter).zfill(3)}"
    
    @staticmethod
    def calculate_due_date(issue_date: date, payment_terms: str) -> Optional[date]:
        """Calculate due date based on payment terms."""
        from datetime import timedelta
        
        terms_days = {
            "immediato": 0,
            "30gg": 30,
            "60gg": 60,
            "90gg": 90,
            "30-60gg": 30,  # First payment
            "30-60-90gg": 30,  # First payment
            "fine_mese": 0,
            "fm+30": 30
        }
        
        days = terms_days.get(payment_terms, 30)
        
        if payment_terms == "fine_mese":
            # End of current month
            if issue_date.month == 12:
                return date(issue_date.year + 1, 1, 1) - timedelta(days=1)
            return date(issue_date.year, issue_date.month + 1, 1) - timedelta(days=1)
        elif payment_terms == "fm+30":
            # End of month + 30 days
            if issue_date.month == 12:
                end_of_month = date(issue_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_of_month = date(issue_date.year, issue_date.month + 1, 1) - timedelta(days=1)
            return end_of_month + timedelta(days=30)
        else:
            return issue_date + timedelta(days=days)


invoice_service = InvoiceService()

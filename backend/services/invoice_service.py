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
    async def get_next_number(user_id: str, doc_type, year: int) -> str:
        """Get next document number using atomic MongoDB counters.

        FT and NC have SEPARATE numbering sequences (obbligo fiscale).
        Format:
            FT → "{num}/{year}"       (es. 1/2026, 2/2026)
            NC → "NC-{num}/{year}"    (es. NC-1/2026, NC-2/2026)

        On first call the counter is seeded from the real max found
        in the invoices collection, so it survives deletions and gaps.
        """
        # Normalize doc_type to string
        type_str = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
        is_nc = type_str == "NC"

        counter_id = f"{user_id}_{'NC' if is_nc else 'FT'}_{year}"

        # --- Seed the counter if it doesn't exist yet ---
        existing_counter = await db.document_counters.find_one({"counter_id": counter_id})
        if not existing_counter:
            max_num = 0
            async for inv_doc in db.invoices.find(
                {
                    "user_id": user_id,
                    "document_type": type_str,
                    "status": {"$nin": ["annullata", "cancellata"]},
                },
                {"document_number": 1, "_id": 0},
            ):
                dn = inv_doc.get("document_number", "")
                try:
                    # NC-3/2026 → 3  |  7/2026 → 7  |  FT-2026-004 → 4
                    raw = dn.replace("NC-", "") if is_nc else dn
                    if "/" in raw:
                        num = int(raw.split("/")[0])
                        inv_year = int(raw.split("/")[1])
                        if inv_year == year and num > max_num:
                            max_num = num
                    elif raw.startswith("FT-"):
                        num = int(raw.split("-")[-1])
                        if str(year) in raw and num > max_num:
                            max_num = num
                except (ValueError, IndexError):
                    pass
            if max_num > 0:
                await db.document_counters.update_one(
                    {"counter_id": counter_id},
                    {"$set": {"counter": max_num}},
                    upsert=True,
                )

        # --- Atomic increment ---
        result = await db.document_counters.find_one_and_update(
            {"counter_id": counter_id},
            {"$inc": {"counter": 1}},
            upsert=True,
            return_document=True,
        )
        next_num = result.get("counter", 1)

        if is_nc:
            return f"NC-{next_num}/{year}"
        return f"{next_num}/{year}"
    
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

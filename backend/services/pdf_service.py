"""PDF generation service for invoices."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating professional Italian invoices."""
    
    # Colors matching the app theme
    NAVY = colors.HexColor('#0F172A')
    SLATE_600 = colors.HexColor('#475569')
    SLATE_200 = colors.HexColor('#E2E8F0')
    SLATE_50 = colors.HexColor('#F8FAFC')
    AMBER_700 = colors.HexColor('#B45309')
    
    @staticmethod
    def create_styles():
        """Create custom paragraph styles."""
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=PDFService.NAVY,
            spaceAfter=6*mm,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=10,
            textColor=PDFService.SLATE_600,
            spaceBefore=4*mm,
            spaceAfter=2*mm,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='CompanyName',
            parent=styles['Normal'],
            fontSize=12,
            textColor=PDFService.NAVY,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='NormalText',
            parent=styles['Normal'],
            fontSize=9,
            textColor=PDFService.SLATE_600,
            leading=12
        ))
        
        styles.add(ParagraphStyle(
            name='SmallText',
            parent=styles['Normal'],
            fontSize=8,
            textColor=PDFService.SLATE_600,
            leading=10
        ))
        
        styles.add(ParagraphStyle(
            name='TotalLabel',
            parent=styles['Normal'],
            fontSize=10,
            textColor=PDFService.NAVY,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
        
        styles.add(ParagraphStyle(
            name='TotalValue',
            parent=styles['Normal'],
            fontSize=12,
            textColor=PDFService.NAVY,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
        
        return styles
    
    @staticmethod
    def format_currency(value: float) -> str:
        """Format number as Italian currency."""
        return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    @staticmethod
    def format_date(d) -> str:
        """Format date in Italian format."""
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d/%m/%Y")
    
    @staticmethod
    def generate_invoice_pdf(
        invoice: dict,
        client: dict,
        company: dict
    ) -> bytes:
        """
        Generate a professional Italian invoice PDF.
        
        Args:
            invoice: Invoice data dictionary
            client: Client data dictionary
            company: Company settings dictionary
            
        Returns:
            PDF as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=20*mm
        )
        
        styles = PDFService.create_styles()
        elements = []
        
        # ========== LOGO ==========
        logo_url = company.get('logo_url', '')
        if logo_url and logo_url.startswith('data:image'):
            try:
                import base64
                # Parse base64 data URI
                header_part, b64_data = logo_url.split(',', 1)
                img_bytes = base64.b64decode(b64_data)
                logo_buf = BytesIO(img_bytes)
                logo_img = Image(logo_buf, width=40*mm, height=15*mm)
                logo_img.hAlign = 'LEFT'
                elements.append(logo_img)
                elements.append(Spacer(1, 3*mm))
            except Exception as e:
                logger.warning(f"Could not render logo: {e}")
        
        # ========== HEADER ==========
        # Document type and number
        doc_type_names = {
            "FT": "FATTURA",
            "PRV": "PREVENTIVO",
            "DDT": "DOCUMENTO DI TRASPORTO",
            "NC": "NOTA DI CREDITO"
        }
        doc_type = invoice.get("document_type", "FT")
        doc_title = doc_type_names.get(doc_type, "DOCUMENTO")
        
        # Header table: Company (left) | Document info (right)
        company_info = f"""
        <b>{company.get('business_name', '')}</b><br/>
        {company.get('address', '')}<br/>
        {company.get('cap', '')} {company.get('city', '')} ({company.get('province', '')})<br/>
        P.IVA: {company.get('partita_iva', '')}<br/>
        C.F.: {company.get('codice_fiscale', '')}<br/>
        {f"Tel: {company.get('phone', '')}<br/>" if company.get('phone') else ''}
        {f"Email: {company.get('email', '')}" if company.get('email') else ''}
        """
        
        doc_info = f"""
        <b>{doc_title}</b><br/>
        N. {invoice.get('document_number', '')}<br/>
        Data: {PDFService.format_date(invoice.get('issue_date', ''))}<br/>
        {f"Scadenza: {PDFService.format_date(invoice.get('due_date', ''))}" if invoice.get('due_date') else ''}
        """
        
        header_table = Table(
            [[Paragraph(company_info, styles['SmallText']), 
              Paragraph(doc_info, styles['SmallText'])]],
            colWidths=[100*mm, 70*mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # ========== CLIENT BOX ==========
        elements.append(Paragraph("DESTINATARIO", styles['SectionTitle']))
        
        client_info = f"""
        <b>{client.get('business_name', '')}</b><br/>
        {client.get('address', '')}<br/>
        {client.get('cap', '')} {client.get('city', '')} ({client.get('province', '')})<br/>
        {f"P.IVA: {client.get('partita_iva', '')}<br/>" if client.get('partita_iva') else ''}
        {f"C.F.: {client.get('codice_fiscale', '')}<br/>" if client.get('codice_fiscale') else ''}
        {f"Cod. SDI: {client.get('codice_sdi', '')}" if client.get('codice_sdi') else ''}
        """
        
        client_table = Table(
            [[Paragraph(client_info, styles['NormalText'])]],
            colWidths=[90*mm]
        )
        client_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, PDFService.SLATE_200),
            ('BACKGROUND', (0, 0), (-1, -1), PDFService.SLATE_50),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 8*mm))
        
        # ========== LINE ITEMS TABLE ==========
        # Table header
        table_data = [[
            Paragraph('<b>Cod.</b>', styles['SmallText']),
            Paragraph('<b>Descrizione</b>', styles['SmallText']),
            Paragraph('<b>Q.tà</b>', styles['SmallText']),
            Paragraph('<b>Prezzo</b>', styles['SmallText']),
            Paragraph('<b>Sc.%</b>', styles['SmallText']),
            Paragraph('<b>IVA%</b>', styles['SmallText']),
            Paragraph('<b>Importo</b>', styles['SmallText']),
        ]]
        
        # Add lines
        for line in invoice.get('lines', []):
            table_data.append([
                Paragraph(str(line.get('code', '') or ''), styles['SmallText']),
                Paragraph(str(line.get('description', '')), styles['SmallText']),
                Paragraph(f"{line.get('quantity', 0):.2f}", styles['SmallText']),
                Paragraph(PDFService.format_currency(line.get('unit_price', 0)), styles['SmallText']),
                Paragraph(f"{line.get('discount_percent', 0):.0f}%", styles['SmallText']),
                Paragraph(str(line.get('vat_rate', '22')), styles['SmallText']),
                Paragraph(PDFService.format_currency(line.get('line_total', 0)), styles['SmallText']),
            ])
        
        lines_table = Table(
            table_data,
            colWidths=[15*mm, 70*mm, 15*mm, 25*mm, 12*mm, 15*mm, 25*mm]
        )
        lines_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), PDFService.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, PDFService.SLATE_200),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 4),
            # Alternate row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PDFService.SLATE_50]),
        ]))
        elements.append(lines_table)
        elements.append(Spacer(1, 6*mm))
        
        # ========== TOTALS ==========
        totals = invoice.get('totals', {})
        
        totals_data = []
        
        # Subtotal
        totals_data.append([
            '', '',
            Paragraph('Imponibile:', styles['NormalText']),
            Paragraph(PDFService.format_currency(totals.get('subtotal', 0)), styles['NormalText'])
        ])
        
        # VAT breakdown
        vat_breakdown = totals.get('vat_breakdown', {})
        for rate, values in vat_breakdown.items():
            if rate not in ['N3', 'N4'] and values.get('imposta', 0) > 0:
                totals_data.append([
                    '', '',
                    Paragraph(f"IVA {rate}%:", styles['NormalText']),
                    Paragraph(PDFService.format_currency(values.get('imposta', 0)), styles['NormalText'])
                ])
        
        # Additional taxes
        if totals.get('rivalsa_inps', 0) > 0:
            totals_data.append([
                '', '',
                Paragraph('Rivalsa INPS 4%:', styles['NormalText']),
                Paragraph(PDFService.format_currency(totals.get('rivalsa_inps', 0)), styles['NormalText'])
            ])
        
        if totals.get('cassa', 0) > 0:
            totals_data.append([
                '', '',
                Paragraph('Cassa Previdenza:', styles['NormalText']),
                Paragraph(PDFService.format_currency(totals.get('cassa', 0)), styles['NormalText'])
            ])
        
        # Total document
        totals_data.append([
            '', '',
            Paragraph('<b>TOTALE DOCUMENTO:</b>', styles['TotalLabel']),
            Paragraph(f"<b>{PDFService.format_currency(totals.get('total_document', 0))}</b>", styles['TotalValue'])
        ])
        
        # Ritenuta
        if totals.get('ritenuta', 0) > 0:
            totals_data.append([
                '', '',
                Paragraph('Ritenuta d\'acconto:', styles['NormalText']),
                Paragraph(f"- {PDFService.format_currency(totals.get('ritenuta', 0))}", styles['NormalText'])
            ])
            totals_data.append([
                '', '',
                Paragraph('<b>NETTO A PAGARE:</b>', styles['TotalLabel']),
                Paragraph(f"<b>{PDFService.format_currency(totals.get('total_to_pay', 0))}</b>", styles['TotalValue'])
            ])
        
        totals_table = Table(
            totals_data,
            colWidths=[70*mm, 30*mm, 45*mm, 35*mm]
        )
        totals_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('LINEABOVE', (-2, -1), (-1, -1), 1, PDFService.NAVY),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 10*mm))
        
        # ========== PAYMENT INFO ==========
        payment_method_names = {
            "bonifico": "Bonifico Bancario",
            "contanti": "Contanti",
            "carta": "Carta di Credito",
            "assegno": "Assegno",
            "riba": "RiBa",
            "altro": "Altro"
        }
        
        payment_info = f"""
        <b>MODALITÀ DI PAGAMENTO:</b> {payment_method_names.get(invoice.get('payment_method', ''), '')}
        """
        
        if company.get('bank_details', {}).get('iban'):
            bank = company.get('bank_details', {})
            payment_info += f"""
            <br/><br/>
            <b>Coordinate Bancarie:</b><br/>
            {bank.get('bank_name', '')}<br/>
            IBAN: {bank.get('iban', '')}<br/>
            {f"BIC/SWIFT: {bank.get('bic_swift', '')}" if bank.get('bic_swift') else ''}
            """
        
        elements.append(Paragraph(payment_info, styles['SmallText']))
        
        # ========== NOTES ==========
        if invoice.get('notes'):
            elements.append(Spacer(1, 6*mm))
            elements.append(Paragraph("<b>Note:</b>", styles['SmallText']))
            elements.append(Paragraph(invoice.get('notes', ''), styles['SmallText']))
        
        # ========== CONDIZIONI DI VENDITA ==========
        condizioni = company.get('condizioni_vendita', '')
        if condizioni:
            elements.append(Spacer(1, 8*mm))
            elements.append(Paragraph("<b>CONDIZIONI DI VENDITA</b>", styles['SectionTitle']))
            for line in condizioni.split('\n'):
                if line.strip():
                    elements.append(Paragraph(line.strip(), styles['SmallText']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


pdf_service = PDFService()

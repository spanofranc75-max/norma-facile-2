"""PDF generation service for Rilievi (On-Site Surveys)."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from datetime import datetime
import base64
import logging

logger = logging.getLogger(__name__)


class RilievoPDFService:
    """Service for generating Rilievo PDF summaries."""
    
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
            name='RilievoTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=RilievoPDFService.NAVY,
            spaceAfter=6*mm,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=RilievoPDFService.NAVY,
            spaceBefore=6*mm,
            spaceAfter=3*mm,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='NormalText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=RilievoPDFService.SLATE_600,
            leading=14
        ))
        
        styles.add(ParagraphStyle(
            name='SmallText',
            parent=styles['Normal'],
            fontSize=9,
            textColor=RilievoPDFService.SLATE_600,
            leading=12
        ))
        
        styles.add(ParagraphStyle(
            name='NotesText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=RilievoPDFService.SLATE_600,
            leading=14,
            spaceBefore=2*mm
        ))
        
        return styles
    
    @staticmethod
    def format_date(d) -> str:
        """Format date in Italian format."""
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        if hasattr(d, 'strftime'):
            return d.strftime("%d/%m/%Y")
        return str(d)
    
    @staticmethod
    def base64_to_image(base64_string: str, max_width: float = 160*mm, max_height: float = 120*mm):
        """Convert base64 string to ReportLab Image."""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            image_data = base64.b64decode(base64_string)
            image_buffer = BytesIO(image_data)
            
            img = Image(image_buffer)
            
            # Calculate aspect ratio and resize
            aspect = img.imageWidth / img.imageHeight
            
            if img.imageWidth > max_width:
                img.drawWidth = max_width
                img.drawHeight = max_width / aspect
            
            if img.drawHeight > max_height:
                img.drawHeight = max_height
                img.drawWidth = max_height * aspect
            
            return img
        except Exception as e:
            logger.error(f"Error converting base64 to image: {e}")
            return None
    
    @staticmethod
    def generate_rilievo_pdf(rilievo: dict, client: dict, company: dict) -> bytes:
        """
        Generate a professional Rilievo PDF summary.
        
        Args:
            rilievo: Rilievo data dictionary
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
        
        styles = RilievoPDFService.create_styles()
        elements = []
        
        # ========== HEADER ==========
        elements.append(Paragraph("SCHEDA RILIEVO MISURE", styles['RilievoTitle']))
        
        # Project info table
        info_data = [
            [
                Paragraph("<b>Progetto:</b>", styles['SmallText']),
                Paragraph(rilievo.get('project_name', ''), styles['NormalText']),
                Paragraph("<b>Data Rilievo:</b>", styles['SmallText']),
                Paragraph(RilievoPDFService.format_date(rilievo.get('survey_date', '')), styles['NormalText']),
            ],
            [
                Paragraph("<b>Cliente:</b>", styles['SmallText']),
                Paragraph(client.get('business_name', ''), styles['NormalText']),
                Paragraph("<b>Località:</b>", styles['SmallText']),
                Paragraph(rilievo.get('location', '') or '-', styles['NormalText']),
            ],
        ]
        
        info_table = Table(info_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), RilievoPDFService.SLATE_50),
            ('BOX', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
            ('GRID', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8*mm))
        
        # ========== SKETCHES ==========
        sketches = rilievo.get('sketches', [])
        if sketches:
            elements.append(Paragraph("SCHIZZI E MISURE", styles['SectionTitle']))
            
            for i, sketch in enumerate(sketches):
                sketch_name = sketch.get('name') or f"Schizzo {i + 1}"
                elements.append(Paragraph(f"<b>{sketch_name}</b>", styles['SmallText']))
                
                # Try to render background image with drawing overlay
                # For now, we'll render the background image if available
                bg_image = sketch.get('background_image')
                if bg_image:
                    img = RilievoPDFService.base64_to_image(bg_image)
                    if img:
                        elements.append(img)
                
                # Show dimensions if available
                dimensions = sketch.get('dimensions', {})
                if dimensions:
                    dim_text = ", ".join([f"{k}: {v}" for k, v in dimensions.items() if v])
                    if dim_text:
                        elements.append(Paragraph(f"<i>Dimensioni: {dim_text}</i>", styles['SmallText']))
                
                elements.append(Spacer(1, 4*mm))
        
        # ========== PHOTOS ==========
        photos = rilievo.get('photos', [])
        if photos:
            elements.append(Paragraph("FOTO SOPRALLUOGO", styles['SectionTitle']))
            
            # Create photo grid (2 columns)
            photo_rows = []
            current_row = []
            
            for i, photo in enumerate(photos):
                photo_name = photo.get('name') or photo.get('caption') or f"Foto {i + 1}"
                image_data = photo.get('image_data')
                
                if image_data:
                    img = RilievoPDFService.base64_to_image(
                        image_data, 
                        max_width=80*mm, 
                        max_height=60*mm
                    )
                    if img:
                        cell_content = [img, Paragraph(photo_name, styles['SmallText'])]
                        current_row.append(cell_content)
                        
                        if len(current_row) == 2:
                            photo_rows.append(current_row)
                            current_row = []
            
            # Add remaining photos
            if current_row:
                while len(current_row) < 2:
                    current_row.append(['', ''])
                photo_rows.append(current_row)
            
            if photo_rows:
                for row in photo_rows:
                    photo_table = Table(
                        [[row[0], row[1]]],
                        colWidths=[90*mm, 90*mm]
                    )
                    photo_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('PADDING', (0, 0), (-1, -1), 4),
                    ]))
                    elements.append(photo_table)
                    elements.append(Spacer(1, 4*mm))
        
        # ========== NOTES ==========
        notes = rilievo.get('notes')
        if notes:
            elements.append(Paragraph("NOTE TECNICHE", styles['SectionTitle']))
            
            # Create notes box
            notes_table = Table(
                [[Paragraph(notes, styles['NotesText'])]],
                colWidths=[170*mm]
            )
            notes_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(notes_table)
        
        # ========== FOOTER ==========
        elements.append(Spacer(1, 10*mm))
        
        footer_text = f"""
        <b>{company.get('business_name', '')}</b><br/>
        Documento generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        elements.append(Paragraph(footer_text, styles['SmallText']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


rilievo_pdf_service = RilievoPDFService()

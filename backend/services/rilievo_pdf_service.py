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

TIPOLOGIE_LABELS = {
    "inferriata_fissa": "Inferriata Fissa",
    "cancello_carrabile": "Cancello Carrabile",
    "cancello_pedonale": "Cancello Pedonale",
    "scala": "Scala",
    "recinzione": "Recinzione",
    "ringhiera": "Ringhiera",
}

MISURE_LABELS = {
    "luce_larghezza": ("Luce larghezza", "mm"),
    "luce_altezza": ("Luce altezza", "mm"),
    "interasse_montanti": ("Interasse montanti", "mm"),
    "profilo_montante": ("Profilo montante", ""),
    "profilo_traverso": ("Profilo traverso", ""),
    "numero_traversi": ("N. traversi", ""),
    "altezza_davanzale": ("Altezza davanzale", "mm"),
    "luce_netta": ("Luce netta", "mm"),
    "altezza": ("Altezza", "mm"),
    "profilo_telaio": ("Profilo telaio", ""),
    "profilo_infisso": ("Profilo infisso", ""),
    "interasse_infissi": ("Interasse infissi", "mm"),
    "larghezza_pilastro": ("Larghezza pilastro", "mm"),
    "motorizzazione": ("Motorizzazione", ""),
    "tipo_motore": ("Tipo motore", ""),
    "numero_gradini": ("N. gradini", ""),
    "larghezza": ("Larghezza", "mm"),
    "alzata": ("Alzata", "mm"),
    "pedata": ("Pedata", "mm"),
    "profilo_struttura": ("Profilo struttura", ""),
    "tipo_gradino": ("Tipo gradino", ""),
    "spessore_gradino": ("Spessore gradino", "mm"),
    "corrimano": ("Corrimano", ""),
    "lato_corrimano": ("Lato corrimano", ""),
    "profilo_corrimano": ("Profilo corrimano", ""),
    "montanti_corrimano": ("Montanti corrimano", ""),
    "lunghezza_totale": ("Lunghezza totale", "mm"),
    "interasse_pali": ("Interasse pali", "mm"),
    "profilo_palo": ("Profilo palo", ""),
    "numero_orizzontali": ("N. orizzontali", ""),
    "profilo_orizzontale": ("Profilo orizzontale", ""),
    "interasse_verticali": ("Interasse verticali", "mm"),
    "profilo_verticale": ("Profilo verticale", ""),
    "lunghezza": ("Lunghezza", "mm"),
    "profilo_corrente": ("Profilo corrente", ""),
    "tipo_infisso": ("Tipo infisso", ""),
    "lunghezza_campata": ("Lunghezza campata", "mm"),
}


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
            return RilievoPDFService._bytes_to_image(image_data, max_width, max_height)
        except Exception as e:
            logger.error(f"Error converting base64 to image: {e}")
            return None

    @staticmethod
    def _bytes_to_image(image_data: bytes, max_width: float = 160*mm, max_height: float = 120*mm):
        """Convert raw bytes to ReportLab Image with scaling."""
        try:
            image_buffer = BytesIO(image_data)
            img = Image(image_buffer)
            aspect = img.imageWidth / img.imageHeight
            if img.imageWidth > max_width:
                img.drawWidth = max_width
                img.drawHeight = max_width / aspect
            if img.drawHeight > max_height:
                img.drawHeight = max_height
                img.drawWidth = max_height * aspect
            return img
        except Exception as e:
            logger.error(f"Error creating image from bytes: {e}")
            return None

    @staticmethod
    def _load_photo_image(photo: dict, max_width: float = 80*mm, max_height: float = 60*mm):
        """Load a photo image from object storage or legacy base64."""
        # New format: object storage
        if isinstance(photo, dict) and photo.get('storage_path'):
            try:
                from services.object_storage import get_object
                data, _ = get_object(photo['storage_path'])
                return RilievoPDFService._bytes_to_image(data, max_width, max_height)
            except Exception as e:
                logger.warning(f"Failed to load photo from storage: {e}")
                return None
        # Legacy format: base64 in image_data
        if isinstance(photo, dict) and photo.get('image_data'):
            return RilievoPDFService.base64_to_image(photo['image_data'], max_width, max_height)
        return None

    @staticmethod
    def _load_sketch_bg(sketch: dict, max_width: float = 160*mm, max_height: float = 120*mm):
        """Load sketch background from object storage or legacy base64."""
        # New format: object storage
        if sketch.get('background_storage_path'):
            try:
                from services.object_storage import get_object
                data, _ = get_object(sketch['background_storage_path'])
                return RilievoPDFService._bytes_to_image(data, max_width, max_height)
            except Exception as e:
                logger.warning(f"Failed to load sketch bg from storage: {e}")
                return None
        # Legacy format: base64
        if sketch.get('background_image'):
            return RilievoPDFService.base64_to_image(sketch['background_image'], max_width, max_height)
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
        
        # ========== TIPOLOGIA & MISURE STRUTTURATE ==========
        tipologia = rilievo.get('tipologia', '')
        misure = rilievo.get('misure', {})
        
        if tipologia and misure:
            tip_label = TIPOLOGIE_LABELS.get(tipologia, tipologia)
            elements.append(Paragraph(f"TIPOLOGIA: {tip_label}", styles['SectionTitle']))
            
            # Build misure table
            misure_rows = [[
                Paragraph("<b>Parametro</b>", styles['SmallText']),
                Paragraph("<b>Valore</b>", styles['SmallText']),
            ]]
            for key, val in misure.items():
                if val is None or val == '':
                    continue
                label_info = MISURE_LABELS.get(key)
                if label_info:
                    label, unit = label_info
                else:
                    label, unit = key.replace('_', ' ').capitalize(), ''
                # Format booleans
                if isinstance(val, bool):
                    display_val = "Si" if val else "No"
                else:
                    display_val = f"{val} {unit}".strip() if unit else str(val)
                misure_rows.append([
                    Paragraph(label, styles['SmallText']),
                    Paragraph(display_val, styles['NormalText']),
                ])
            
            if len(misure_rows) > 1:
                m_table = Table(misure_rows, colWidths=[85*mm, 85*mm])
                m_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), RilievoPDFService.NAVY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('BACKGROUND', (0, 1), (-1, -1), RilievoPDFService.SLATE_50),
                    ('BOX', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
                    ('GRID', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
                    ('PADDING', (0, 0), (-1, -1), 5),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(m_table)
                elements.append(Spacer(1, 6*mm))
        
        # ========== VISTA 3D (screenshot separata dalle foto) ==========
        photos = rilievo.get('photos', [])
        vista_3d_photo = None
        other_photos = []
        for p in photos:
            caption = p.get('caption', '') or p.get('name', '') or ''
            if caption.startswith('Vista 3D'):
                vista_3d_photo = p
            else:
                other_photos.append(p)
        
        if vista_3d_photo:
            elements.append(Paragraph("VISTA 3D", styles['SectionTitle']))
            img_3d = RilievoPDFService._load_photo_image(vista_3d_photo, max_width=140*mm, max_height=100*mm)
            if img_3d:
                elements.append(img_3d)
                cap = vista_3d_photo.get('caption', '') or ''
                if cap:
                    elements.append(Paragraph(f"<i>{cap}</i>", styles['SmallText']))
                elements.append(Spacer(1, 6*mm))
        
        # ========== MATERIALI CALCOLATI ==========
        if tipologia and misure:
            try:
                from routes.rilievi import CALCOLA_FN
                if tipologia in CALCOLA_FN:
                    risultato = CALCOLA_FN[tipologia](misure)
                    mat_list = risultato.get('materiali', [])
                    peso_tot = risultato.get('peso_totale_kg', 0)
                    sup_vern = risultato.get('superficie_verniciatura_m2', 0)
                    
                    if mat_list:
                        elements.append(Paragraph("LISTA MATERIALI CALCOLATA", styles['SectionTitle']))
                        
                        mat_rows = [[
                            Paragraph("<b>Descrizione</b>", styles['SmallText']),
                            Paragraph("<b>Qtà</b>", styles['SmallText']),
                            Paragraph("<b>ML</b>", styles['SmallText']),
                            Paragraph("<b>Peso (kg)</b>", styles['SmallText']),
                        ]]
                        for item in mat_list:
                            mat_rows.append([
                                Paragraph(str(item.get('descrizione', '')), styles['SmallText']),
                                Paragraph(str(item.get('quantita', '')), styles['NormalText']),
                                Paragraph(str(item.get('ml', '')), styles['NormalText']),
                                Paragraph(str(item.get('peso_kg', '')), styles['NormalText']),
                            ])
                        # Totals row
                        mat_rows.append([
                            Paragraph("<b>TOTALE</b>", styles['SmallText']),
                            Paragraph("", styles['SmallText']),
                            Paragraph("", styles['SmallText']),
                            Paragraph(f"<b>{peso_tot} kg</b>", styles['NormalText']),
                        ])
                        
                        mat_table = Table(mat_rows, colWidths=[70*mm, 25*mm, 30*mm, 40*mm])
                        mat_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), RilievoPDFService.NAVY),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('BACKGROUND', (0, 1), (-1, -2), RilievoPDFService.SLATE_50),
                            ('BACKGROUND', (0, -1), (-1, -1), RilievoPDFService.SLATE_200),
                            ('BOX', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
                            ('GRID', (0, 0), (-1, -1), 0.5, RilievoPDFService.SLATE_200),
                            ('PADDING', (0, 0), (-1, -1), 5),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                        ]))
                        elements.append(mat_table)
                        
                        # Surface info
                        if sup_vern > 0:
                            elements.append(Spacer(1, 3*mm))
                            elements.append(Paragraph(
                                f"<b>Superficie verniciatura stimata:</b> {sup_vern} m²",
                                styles['NormalText']
                            ))
                        elements.append(Spacer(1, 6*mm))
            except Exception as e:
                logger.warning(f"Calcolo materiali PDF fallito: {e}")
        
        # ========== SKETCHES ==========
        sketches = rilievo.get('sketches', [])
        if sketches:
            elements.append(Paragraph("SCHIZZI E MISURE", styles['SectionTitle']))
            
            for i, sketch in enumerate(sketches):
                sketch_name = sketch.get('name') or f"Schizzo {i + 1}"
                elements.append(Paragraph(f"<b>{sketch_name}</b>", styles['SmallText']))
                
                # Try to render background image with drawing overlay
                bg_img = RilievoPDFService._load_sketch_bg(sketch)
                if bg_img:
                    elements.append(bg_img)
                
                # Show dimensions if available
                dimensions = sketch.get('dimensions', {})
                if dimensions:
                    dim_text = ", ".join([f"{k}: {v}" for k, v in dimensions.items() if v])
                    if dim_text:
                        elements.append(Paragraph(f"<i>Dimensioni: {dim_text}</i>", styles['SmallText']))
                
                elements.append(Spacer(1, 4*mm))
        
        # ========== PHOTOS (esclusa Vista 3D già mostrata sopra) ==========
        if not tipologia:
            # Se non c'è tipologia, other_photos non è definito, usa tutte le foto
            other_photos = rilievo.get('photos', [])
        if other_photos:
            elements.append(Paragraph("FOTO SOPRALLUOGO", styles['SectionTitle']))
            
            # Create photo grid (2 columns)
            photo_rows = []
            current_row = []
            
            for i, photo in enumerate(other_photos):
                photo_name = photo.get('name') or photo.get('caption') or f"Foto {i + 1}"
                
                img = RilievoPDFService._load_photo_image(photo, max_width=80*mm, max_height=60*mm)
                if img:
                        # Create a vertical layout with image and caption
                        cell_content = Table([[img], [Paragraph(photo_name, styles['SmallText'])]])
                        cell_content.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ]))
                        current_row.append(cell_content)
                        
                        if len(current_row) == 2:
                            photo_rows.append(current_row)
                            current_row = []
            
            # Add remaining photos
            if current_row:
                while len(current_row) < 2:
                    current_row.append(Paragraph('', styles['SmallText']))
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

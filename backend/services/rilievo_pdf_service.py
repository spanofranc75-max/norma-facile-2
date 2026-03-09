"""PDF generation service for Rilievi (On-Site Surveys) — Professional Studio Tecnico layout."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from datetime import datetime
import base64
import logging

logger = logging.getLogger(__name__)

# ── Colori istituzionali ──
COLOR_PRIMARY = colors.HexColor('#1a3a5c')
COLOR_ACCENT = colors.HexColor('#c8a96e')
COLOR_LIGHT = colors.HexColor('#f5f7fa')
COLOR_BORDER = colors.HexColor('#d0d7de')
COLOR_TEXT = colors.HexColor('#2c3e50')
COLOR_MUTED = colors.HexColor('#6b7280')
COLOR_WHITE = colors.white

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
    "finitura": ("Finitura", ""),
    "colore": ("Colore RAL", ""),
    "tipo_apertura": ("Tipo apertura", ""),
    "tipo": ("Tipo", ""),
    "tipo_struttura": ("Tipo struttura", ""),
    "tipo_pannello": ("Tipo pannello", ""),
    "tipo_attacco": ("Tipo attacco", ""),
    "numero_ante": ("N. ante", ""),
    "numero_campate": ("N. campate", ""),
}


class RilievoPDFService:
    """Service for generating professional Rilievo PDF reports."""

    @staticmethod
    def _styles():
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='DocTitle', parent=styles['Heading1'],
            fontSize=16, textColor=COLOR_PRIMARY,
            fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=0
        ))
        styles.add(ParagraphStyle(
            name='DocSubtitle', parent=styles['Normal'],
            fontSize=9, textColor=COLOR_MUTED,
            fontName='Helvetica', alignment=TA_CENTER, spaceAfter=0
        ))
        styles.add(ParagraphStyle(
            name='Section', parent=styles['Heading2'],
            fontSize=11, textColor=COLOR_PRIMARY,
            fontName='Helvetica-Bold', spaceBefore=6*mm, spaceAfter=3*mm
        ))
        styles.add(ParagraphStyle(
            name='Body', parent=styles['Normal'],
            fontSize=9, textColor=COLOR_TEXT, leading=13
        ))
        styles.add(ParagraphStyle(
            name='Small', parent=styles['Normal'],
            fontSize=8, textColor=COLOR_MUTED, leading=11
        ))
        styles.add(ParagraphStyle(
            name='SmallBold', parent=styles['Normal'],
            fontSize=8, textColor=COLOR_TEXT, leading=11, fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='FooterLeft', parent=styles['Normal'],
            fontSize=7, textColor=COLOR_MUTED, leading=9
        ))
        styles.add(ParagraphStyle(
            name='FooterRight', parent=styles['Normal'],
            fontSize=7, textColor=COLOR_MUTED, leading=9, alignment=TA_RIGHT
        ))
        styles.add(ParagraphStyle(
            name='Notes', parent=styles['Normal'],
            fontSize=9, textColor=COLOR_TEXT, leading=13, spaceBefore=2*mm
        ))
        return styles

    @staticmethod
    def _fmt_date(d) -> str:
        if isinstance(d, str):
            try:
                d = datetime.fromisoformat(d)
            except Exception:
                return str(d)
        if hasattr(d, 'strftime'):
            return d.strftime("%d/%m/%Y")
        return str(d)

    @staticmethod
    def _bytes_to_image(data: bytes, max_w: float, max_h: float):
        try:
            buf = BytesIO(data)
            img = Image(buf)
            aspect = img.imageWidth / img.imageHeight
            if img.imageWidth > max_w:
                img.drawWidth = max_w
                img.drawHeight = max_w / aspect
            if img.drawHeight > max_h:
                img.drawHeight = max_h
                img.drawWidth = max_h * aspect
            return img
        except Exception as e:
            logger.error(f"Image load error: {e}")
            return None

    @staticmethod
    def _load_photo(photo: dict, max_w=80*mm, max_h=60*mm):
        if isinstance(photo, dict) and photo.get('storage_path'):
            try:
                from services.object_storage import get_object
                data, _ = get_object(photo['storage_path'])
                return RilievoPDFService._bytes_to_image(data, max_w, max_h)
            except Exception as e:
                logger.warning(f"Photo storage load failed: {e}")
        if isinstance(photo, dict) and photo.get('image_data'):
            raw = photo['image_data']
            if ',' in raw:
                raw = raw.split(',')[1]
            try:
                return RilievoPDFService._bytes_to_image(base64.b64decode(raw), max_w, max_h)
            except Exception:
                pass
        return None

    @staticmethod
    def _load_sketch_bg(sketch: dict, max_w=160*mm, max_h=120*mm):
        if sketch.get('background_storage_path'):
            try:
                from services.object_storage import get_object
                data, _ = get_object(sketch['background_storage_path'])
                return RilievoPDFService._bytes_to_image(data, max_w, max_h)
            except Exception:
                pass
        if sketch.get('background_image'):
            raw = sketch['background_image']
            if ',' in raw:
                raw = raw.split(',')[1]
            try:
                return RilievoPDFService._bytes_to_image(base64.b64decode(raw), max_w, max_h)
            except Exception:
                pass
        return None

    @staticmethod
    def generate_rilievo_pdf(rilievo: dict, client: dict, company: dict) -> bytes:
        buffer = BytesIO()

        company_name = company.get('business_name', '')
        client_name = client.get('business_name', '')
        project_name = rilievo.get('project_name', '')
        survey_date = RilievoPDFService._fmt_date(rilievo.get('survey_date', ''))
        rilievo_id = rilievo.get('rilievo_id', '')

        # Footer callback: runs on every page
        def _footer(canvas, doc):
            canvas.saveState()
            w, h = A4
            # Separator line
            canvas.setStrokeColor(COLOR_BORDER)
            canvas.setLineWidth(0.5)
            canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
            # Left: company
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(COLOR_MUTED)
            canvas.drawString(15*mm, 10*mm, company_name)
            # Center: doc info
            center_text = f"Scheda rilievo {rilievo_id} — {client_name} — {survey_date}"
            canvas.drawCentredString(w / 2, 10*mm, center_text)
            # Right: page
            canvas.drawRightString(w - 15*mm, 10*mm, f"Pag. {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=15*mm, leftMargin=15*mm,
            topMargin=15*mm, bottomMargin=22*mm
        )

        S = RilievoPDFService._styles()
        els = []

        # ═══════════════ C1: INTESTAZIONE PROFESSIONALE ═══════════════
        # Top accent line
        accent_line = Table([['']], colWidths=[180*mm], rowHeights=[2*mm])
        accent_line.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COLOR_ACCENT)]))
        els.append(accent_line)
        els.append(Spacer(1, 4*mm))

        # Title row: Company | SCHEDA DI RILIEVO TECNICO | Date
        header_data = [[
            Paragraph(f"<b>{company_name}</b>", S['Small']),
            Paragraph("SCHEDA DI RILIEVO TECNICO", S['DocTitle']),
            Paragraph(f"<b>Data:</b> {survey_date}<br/><b>Rif.:</b> {rilievo_id[:12]}", S['Small']),
        ]]
        header_tbl = Table(header_data, colWidths=[45*mm, 90*mm, 45*mm])
        header_tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        els.append(header_tbl)
        els.append(Spacer(1, 2*mm))

        # Thick separator
        sep = Table([['']], colWidths=[180*mm], rowHeights=[1*mm])
        sep.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY)]))
        els.append(sep)
        els.append(Spacer(1, 3*mm))

        # Info row: Cliente | Cantiere | Progetto | Tecnico
        info_data = [
            [
                Paragraph("<b>Cliente</b>", S['SmallBold']),
                Paragraph(client_name, S['Body']),
                Paragraph("<b>Progetto</b>", S['SmallBold']),
                Paragraph(project_name, S['Body']),
            ],
            [
                Paragraph("<b>Cantiere</b>", S['SmallBold']),
                Paragraph(rilievo.get('location', '') or '-', S['Body']),
                Paragraph("<b>Data Rilievo</b>", S['SmallBold']),
                Paragraph(survey_date, S['Body']),
            ],
        ]
        info_tbl = Table(info_data, colWidths=[25*mm, 65*mm, 25*mm, 65*mm])
        info_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLOR_LIGHT),
            ('BACKGROUND', (2, 0), (2, -1), COLOR_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        els.append(info_tbl)
        els.append(Spacer(1, 6*mm))

        # ═══════════════ C2: MISURE STRUTTURATE (2 COLONNE) ═══════════════
        tipologia = rilievo.get('tipologia', '')
        misure = rilievo.get('misure', {})

        if tipologia and misure:
            tip_label = TIPOLOGIE_LABELS.get(tipologia, tipologia)
            # Tipologia badge
            tip_tbl = Table(
                [[Paragraph(f"<b>TIPOLOGIA: {tip_label.upper()}</b>", S['Body'])]],
                colWidths=[180*mm]
            )
            tip_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_WHITE),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            els.append(tip_tbl)
            els.append(Spacer(1, 2*mm))

            # Build 2-column misure table
            items = []
            for key, val in misure.items():
                if val is None or val == '':
                    continue
                info = MISURE_LABELS.get(key)
                label = info[0] if info else key.replace('_', ' ').capitalize()
                unit = info[1] if info else ''
                if isinstance(val, bool):
                    dv = "Si" if val else "No"
                else:
                    dv = f"{val} {unit}".strip() if unit else str(val)
                items.append((label, dv))

            if items:
                # Split into 2 columns
                half = (len(items) + 1) // 2
                col_l = items[:half]
                col_r = items[half:]

                rows = [[
                    Paragraph("<b>Parametro</b>", S['SmallBold']),
                    Paragraph("<b>Valore</b>", S['SmallBold']),
                    Paragraph("<b>Parametro</b>", S['SmallBold']),
                    Paragraph("<b>Valore</b>", S['SmallBold']),
                ]]
                for i in range(half):
                    l_label, l_val = col_l[i] if i < len(col_l) else ('', '')
                    r_label, r_val = col_r[i] if i < len(col_r) else ('', '')
                    rows.append([
                        Paragraph(l_label, S['Small']),
                        Paragraph(str(l_val), S['Body']),
                        Paragraph(r_label, S['Small']),
                        Paragraph(str(r_val), S['Body']),
                    ])

                m_tbl = Table(rows, colWidths=[35*mm, 45*mm, 35*mm, 45*mm])
                m_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT]),
                    ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('PADDING', (0, 0), (-1, -1), 4),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # Vertical separator between L and R columns
                    ('LINEAFTER', (1, 0), (1, -1), 1, COLOR_PRIMARY),
                ]))
                els.append(m_tbl)
                els.append(Spacer(1, 5*mm))

        # ═══════════════ C3: VISTA 3D IN BOX TECNICO ═══════════════
        photos = rilievo.get('photos', [])
        vista_3d_photo = None
        other_photos = []
        for p in photos:
            cap = p.get('caption', '') or p.get('name', '') or ''
            if cap.startswith('Vista 3D'):
                vista_3d_photo = p
            else:
                other_photos.append(p)

        if vista_3d_photo:
            img_3d = RilievoPDFService._load_photo(vista_3d_photo, max_w=145*mm, max_h=95*mm)
            if img_3d:
                cap_text = vista_3d_photo.get('caption', '') or ''
                title_3d = f"VISTA 3D — {TIPOLOGIE_LABELS.get(tipologia, tipologia).upper()}"

                # Header bar
                v3d_header = Table(
                    [[Paragraph(f"<b>{title_3d}</b>", S['Body'])]],
                    colWidths=[170*mm]
                )
                v3d_header.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
                    ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_WHITE),
                    ('PADDING', (0, 0), (-1, -1), 5),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]))
                els.append(v3d_header)

                # Image box with double border (cartiglio CAD)
                img_cell = Table([[img_3d]], colWidths=[170*mm])
                img_cell.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1.5, COLOR_PRIMARY),
                    ('INNERGRID', (0, 0), (-1, -1), 0, COLOR_WHITE),
                    ('PADDING', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, -1), COLOR_WHITE),
                ]))
                # Outer border wrapper for double-line effect
                outer = Table([[img_cell]], colWidths=[174*mm])
                outer.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ('PADDING', (0, 0), (-1, -1), 2),
                ]))
                els.append(outer)

                if cap_text:
                    els.append(Paragraph(f"<i>{cap_text}</i>", S['Small']))
                els.append(Spacer(1, 5*mm))

        # ═══════════════ MATERIALI CALCOLATI ═══════════════
        if tipologia and misure:
            try:
                from routes.rilievi import CALCOLA_FN
                if tipologia in CALCOLA_FN:
                    ris = CALCOLA_FN[tipologia](misure)
                    mat_list = ris.get('materiali', [])
                    peso_tot = ris.get('peso_totale_kg', 0)
                    sup_vern = ris.get('superficie_verniciatura_m2', 0)

                    if mat_list:
                        els.append(Paragraph("LISTA MATERIALI CALCOLATA", S['Section']))

                        rows = [[
                            Paragraph("<b>Descrizione</b>", S['SmallBold']),
                            Paragraph("<b>Qtà</b>", S['SmallBold']),
                            Paragraph("<b>ML</b>", S['SmallBold']),
                            Paragraph("<b>Peso (kg)</b>", S['SmallBold']),
                        ]]
                        for item in mat_list:
                            rows.append([
                                Paragraph(str(item.get('descrizione', '')), S['Small']),
                                Paragraph(str(item.get('quantita', '')), S['Body']),
                                Paragraph(str(item.get('ml', '')), S['Body']),
                                Paragraph(str(item.get('peso_kg', '')), S['Body']),
                            ])
                        # Total row
                        rows.append([
                            Paragraph("<b>TOTALE</b>", S['SmallBold']),
                            Paragraph("", S['Small']),
                            Paragraph("", S['Small']),
                            Paragraph(f"<b>{peso_tot} kg</b>", S['Body']),
                        ])

                        mat_tbl = Table(rows, colWidths=[70*mm, 25*mm, 35*mm, 40*mm])
                        mat_tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [COLOR_WHITE, COLOR_LIGHT]),
                            ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT),
                            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                            ('PADDING', (0, 0), (-1, -1), 4),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                            ('LINEABOVE', (0, -1), (-1, -1), 1, COLOR_PRIMARY),
                        ]))
                        els.append(mat_tbl)

                        if sup_vern > 0:
                            els.append(Spacer(1, 2*mm))
                            els.append(Paragraph(
                                f"<b>Superficie verniciatura stimata:</b> {sup_vern} m²",
                                S['Body']
                            ))
                        els.append(Spacer(1, 5*mm))
            except Exception as e:
                logger.warning(f"Calcolo materiali PDF fallito: {e}")

        # ═══════════════ SCHIZZI ═══════════════
        sketches = rilievo.get('sketches', [])
        if sketches:
            els.append(Paragraph("SCHIZZI E MISURE", S['Section']))
            for i, sk in enumerate(sketches):
                name = sk.get('name') or f"Schizzo {i + 1}"
                els.append(Paragraph(f"<b>{name}</b>", S['Small']))
                bg = RilievoPDFService._load_sketch_bg(sk)
                if bg:
                    els.append(bg)
                dims = sk.get('dimensions', {})
                if dims:
                    dt = ", ".join([f"{k}: {v}" for k, v in dims.items() if v])
                    if dt:
                        els.append(Paragraph(f"<i>Dimensioni: {dt}</i>", S['Small']))
                els.append(Spacer(1, 4*mm))

        # ═══════════════ FOTO SOPRALLUOGO ═══════════════
        if not tipologia:
            other_photos = rilievo.get('photos', [])
        if other_photos:
            els.append(Paragraph("FOTO SOPRALLUOGO", S['Section']))
            row_buf = []
            for i, photo in enumerate(other_photos):
                pname = photo.get('name') or photo.get('caption') or f"Foto {i + 1}"
                img = RilievoPDFService._load_photo(photo, max_w=80*mm, max_h=60*mm)
                if img:
                    cell = Table([[img], [Paragraph(pname, S['Small'])]])
                    cell.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    row_buf.append(cell)
                    if len(row_buf) == 2:
                        ptbl = Table([row_buf], colWidths=[90*mm, 90*mm])
                        ptbl.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('PADDING', (0, 0), (-1, -1), 4),
                        ]))
                        els.append(ptbl)
                        els.append(Spacer(1, 3*mm))
                        row_buf = []
            if row_buf:
                row_buf.append(Paragraph('', S['Small']))
                ptbl = Table([row_buf], colWidths=[90*mm, 90*mm])
                ptbl.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))
                els.append(ptbl)

        # ═══════════════ NOTE TECNICHE ═══════════════
        notes = rilievo.get('notes')
        if notes:
            els.append(Paragraph("NOTE TECNICHE", S['Section']))
            n_tbl = Table(
                [[Paragraph(notes, S['Notes'])]],
                colWidths=[170*mm]
            )
            n_tbl.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_WHITE),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            els.append(n_tbl)

        # ═══════════════ BUILD ═══════════════
        doc.build(els, onFirstPage=_footer, onLaterPages=_footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


rilievo_pdf_service = RilievoPDFService()

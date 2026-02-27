"""PDF service for CE Certifications - DOP + CE Label."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
from io import BytesIO
from datetime import datetime

BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT_BLUE = colors.HexColor("#EFF6FF")


def _create_ce_mark_drawing(size=30*mm):
    """Create a CE mark drawing."""
    d = Drawing(size, size)
    d.add(String(0, size * 0.15, "CE", fontSize=size * 0.7, fontName="Helvetica-Bold", fillColor=DARK))
    return d


def generate_dop_ce_pdf(cert: dict, company: dict = None) -> BytesIO:
    """Generate a PDF with DOP (Declaration of Performance) + CE Label."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCE", parent=styles["Heading1"], fontSize=18, textColor=DARK, alignment=TA_CENTER, spaceAfter=6 * mm)
    subtitle_style = ParagraphStyle("SubCE", parent=styles["Heading2"], fontSize=12, textColor=BLUE, spaceAfter=4 * mm, spaceBefore=6 * mm)
    normal = ParagraphStyle("NormCE", parent=styles["Normal"], fontSize=10, leading=14)
    bold_style = ParagraphStyle("BoldCE", parent=styles["Normal"], fontSize=10, leading=14, fontName="Helvetica-Bold")
    center_style = ParagraphStyle("CenterCE", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER)
    small_style = ParagraphStyle("SmallCE", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    specs = cert.get("technical_specs", {})
    standard = cert.get("standard", "EN 1090-1")
    company_name = (company or {}).get("business_name", "")
    company_addr = (company or {}).get("address", "")
    company_vat = (company or {}).get("vat_number", "")
    decl_num = cert.get("declaration_number", "")
    year = datetime.now().strftime("%Y")

    elements = []

    # ════════════════════════════════════════════════════
    # PAGE 1: DICHIARAZIONE DI PRESTAZIONE (DOP)
    # ════════════════════════════════════════════════════
    elements.append(Paragraph("DICHIARAZIONE DI PRESTAZIONE", title_style))
    elements.append(Paragraph(f"ai sensi del Regolamento UE 305/2011 (CPR)", center_style))
    elements.append(Spacer(1, 8 * mm))

    # Declaration number
    dop_data = [
        ["N. Dichiarazione:", decl_num or f"DOP-{year}-001"],
        ["Data:", datetime.now().strftime("%d/%m/%Y")],
    ]
    t = Table(dop_data, colWidths=[50 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))

    # Section 1: Product identification
    elements.append(Paragraph("1. Codice di identificazione unico del prodotto-tipo", subtitle_style))
    elements.append(Paragraph(cert.get("product_type", "-") or "-", normal))

    # Section 2: Use
    elements.append(Paragraph("2. Uso o usi previsti del prodotto", subtitle_style))
    if standard == "EN 13241":
        elements.append(Paragraph("Chiusure industriali, commerciali e da garage - Porte, cancelli e barriere.", normal))
    else:
        elements.append(Paragraph("Componenti strutturali in acciaio e alluminio per strutture.", normal))

    # Section 3: Manufacturer
    elements.append(Paragraph("3. Fabbricante", subtitle_style))
    mfg_text = f"<b>{company_name or '[Ragione Sociale]'}</b><br/>"
    mfg_text += f"{company_addr or '[Indirizzo]'}<br/>"
    if company_vat:
        mfg_text += f"P.IVA: {company_vat}"
    elements.append(Paragraph(mfg_text, normal))

    # Section 4: Authorized representative (optional)
    elements.append(Paragraph("4. Rappresentante autorizzato", subtitle_style))
    elements.append(Paragraph("Non applicabile", normal))

    # Section 5: System of assessment
    elements.append(Paragraph("5. Sistema di valutazione e verifica della costanza della prestazione", subtitle_style))
    if standard == "EN 13241":
        elements.append(Paragraph("Sistema 3", normal))
    else:
        exec_class = specs.get("execution_class", "EXC2")
        if exec_class in ("EXC1", "EXC2"):
            elements.append(Paragraph("Sistema 2+", normal))
        else:
            elements.append(Paragraph("Sistema 2+", normal))

    # Section 6: Harmonised standard
    elements.append(Paragraph("6. Norma armonizzata", subtitle_style))
    elements.append(Paragraph(f"<b>{standard}</b>", normal))

    # Section 7: Declared performances
    elements.append(Paragraph("7. Prestazioni dichiarate", subtitle_style))

    perf_header = ["Caratteristica essenziale", "Prestazione", "Specifica tecnica"]
    perf_data = [perf_header]

    if standard == "EN 13241":
        perf_data.extend([
            ["Resistenza meccanica", specs.get("mechanical_resistance", "Conforme") or "Conforme", "EN 13241"],
            ["Sicurezza apertura", specs.get("safe_opening", "Conforme") or "Conforme", "EN 13241"],
            ["Permeabilita' all'aria", specs.get("air_permeability", "Non determinata") or "Non determinata", "EN 12427"],
            ["Tenuta all'acqua", specs.get("water_tightness", "Non determinata") or "Non determinata", "EN 12425"],
            ["Resistenza al vento", specs.get("wind_resistance", "Non determinata") or "Non determinata", "EN 12424"],
            ["Durabilita'", specs.get("durability", "Classe C3") or "Classe C3", "EN 13241"],
            ["Sostanze pericolose", specs.get("dangerous_substances", "Nessuna") or "Nessuna", "Reg. UE 305/2011"],
        ])
    else:
        perf_data.extend([
            ["Classe di esecuzione", specs.get("execution_class", "EXC2") or "EXC2", "EN 1090-2"],
            ["Reazione al fuoco", specs.get("reaction_to_fire", "Classe A1") or "Classe A1", "EN 13501-1"],
            ["Durabilita'", specs.get("durability", "Classe C3") or "Classe C3", "ISO 12944"],
            ["Sostanze pericolose", specs.get("dangerous_substances", "Nessuna") or "Nessuna", "Reg. UE 305/2011"],
        ])

    col_w = [60 * mm, 55 * mm, 45 * mm]
    pt = Table(perf_data, colWidths=col_w, repeatRows=1)
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(pt)

    # Thermal transmittance section (if calculated)
    thermal_uw = specs.get("thermal_uw")
    if thermal_uw is not None and specs.get("thermal_enabled"):
        elements.append(Paragraph("7b. Trasmittanza termica (Uw) - EN ISO 10077-1", subtitle_style))
        uw_color = colors.HexColor("#DC2626") if thermal_uw > 1.3 else BLUE
        uw_style = ParagraphStyle("UwVal", parent=normal, fontSize=14, fontName="Helvetica-Bold", textColor=uw_color)

        elements.append(Paragraph(f"Uw = {thermal_uw} W/m<super>2</super>K", uw_style))
        elements.append(Spacer(1, 2 * mm))

        th_data = [
            ["Parametro", "Valore"],
            ["Vetro", f"{specs.get('thermal_glass_label', '-')}"],
            ["Telaio", f"{specs.get('thermal_frame_label', '-')}"],
            ["Canalina distanziale", f"{specs.get('thermal_spacer_label', '-')}"],
            ["Dimensioni (H x L)", f"{specs.get('thermal_height_mm', '-')} x {specs.get('thermal_width_mm', '-')} mm"],
        ]
        tht = Table(th_data, colWidths=[60 * mm, 100 * mm])
        tht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(tht)

        if thermal_uw > 1.3:
            warn = ParagraphStyle("WarnUw", parent=normal, fontSize=10, textColor=colors.HexColor("#DC2626"), fontName="Helvetica-Bold")
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph("ATTENZIONE: Uw supera 1.30 W/m2K (limite Zona E). NON detraibile per Ecobonus.", warn))
        else:
            ok = ParagraphStyle("OkUw", parent=normal, fontSize=10, textColor=colors.HexColor("#059669"), fontName="Helvetica-Bold")
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(f"Conforme per detrazione Ecobonus fino a Zona E (limite 1.30 W/m2K).", ok))

    # Section 8: Description
    elements.append(Paragraph("8. Descrizione del prodotto", subtitle_style))
    elements.append(Paragraph(cert.get("product_description", "-") or "-", normal))

    # Signature
    elements.append(Spacer(1, 12 * mm))
    sig_data = [
        [f"Firmato per conto del fabbricante da:", ""],
        [f"{company_name or '[Ragione Sociale]'}", f"Data: {datetime.now().strftime('%d/%m/%Y')}"],
        ["", ""],
        ["_________________________", ""],
        ["(Firma e timbro)", ""],
    ]
    st = Table(sig_data, colWidths=[90 * mm, 80 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(st)

    # ════════════════════════════════════════════════════
    # PAGE 2: ETICHETTA CE
    # ════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements.append(Paragraph("ETICHETTA CE", title_style))
    elements.append(Paragraph("Da apporre sul prodotto", center_style))
    elements.append(Spacer(1, 8 * mm))

    # CE label box
    label_data = [
        [_create_ce_mark_drawing(25 * mm), ""],
        ["", ""],
        [Paragraph(f"<b>{company_name or '[Ragione Sociale]'}</b>", normal), ""],
        [Paragraph(f"{company_addr or '[Indirizzo]'}", small_style), ""],
        ["", ""],
        [Paragraph(f"<b>Anno di marcatura:</b> {year}", normal), ""],
        [Paragraph(f"<b>N. DOP:</b> {decl_num or f'DOP-{year}-001'}", normal), ""],
        [Paragraph(f"<b>Norma:</b> {standard}", normal), ""],
        [Paragraph(f"<b>Prodotto:</b> {cert.get('product_type', '-') or '-'}", normal), ""],
        ["", ""],
    ]

    if standard == "EN 13241":
        label_data.extend([
            [Paragraph(f"<b>Sicurezza apertura:</b> {specs.get('safe_opening', 'Conforme')}", normal), ""],
            [Paragraph(f"<b>Resistenza meccanica:</b> {specs.get('mechanical_resistance', 'Conforme')}", normal), ""],
        ])
    else:
        label_data.extend([
            [Paragraph(f"<b>Classe esecuzione:</b> {specs.get('execution_class', 'EXC2')}", normal), ""],
            [Paragraph(f"<b>Reazione al fuoco:</b> {specs.get('reaction_to_fire', 'A1')}", normal), ""],
        ])

    label_data.append([Paragraph(f"<b>Durabilita':</b> {specs.get('durability', 'C3')}", normal), ""])
    label_data.append([Paragraph(f"<b>Sostanze pericolose:</b> {specs.get('dangerous_substances', 'Nessuna')}", normal), ""])

    lt = Table(label_data, colWidths=[130 * mm, 30 * mm])
    lt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
    ]))
    elements.append(lt)

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph("Ritagliare lungo il bordo e apporre sul prodotto.", small_style))

    # ════════════════════════════════════════════════════
    # PAGE 3: MANUALE D'USO E MANUTENZIONE
    # ════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements.append(Paragraph("MANUALE D'USO E MANUTENZIONE", title_style))
    elements.append(Paragraph(f"Prodotto: {cert.get('product_type', '-') or '-'}", center_style))
    elements.append(Spacer(1, 8 * mm))

    man_h2 = ParagraphStyle("ManH2", parent=subtitle_style, fontSize=12, textColor=BLUE, spaceBefore=6 * mm, spaceAfter=3 * mm)

    elements.append(Paragraph("1. INFORMAZIONI GENERALI", man_h2))
    elements.append(Paragraph(
        f"Il presente manuale e' parte integrante del prodotto <b>{cert.get('product_type', '-')}</b> "
        f"fabbricato da <b>{company_name}</b> in conformita' alla norma <b>{standard}</b>. "
        "Conservare questo documento per tutta la vita utile del prodotto.",
        normal,
    ))

    elements.append(Paragraph("2. USO PREVISTO", man_h2))
    if standard == "EN 13241":
        elements.append(Paragraph(
            "Il prodotto e' destinato ad essere utilizzato come chiusura industriale, commerciale o residenziale. "
            "L'uso e' limitato alle condizioni di installazione previste dal fabbricante. "
            "Non modificare la struttura o i componenti senza autorizzazione del fabbricante.",
            normal,
        ))
    else:
        elements.append(Paragraph(
            "Il prodotto e' un componente strutturale in acciaio destinato ad essere incorporato in opere di costruzione. "
            "L'installazione deve essere eseguita da personale qualificato secondo le indicazioni del progettista strutturale.",
            normal,
        ))

    elements.append(Paragraph("3. MANUTENZIONE ORDINARIA", man_h2))
    maint_data = [
        ["Operazione", "Frequenza", "Note"],
        ["Ispezione visiva generale", "Ogni 6 mesi", "Verificare integrita' strutturale"],
        ["Controllo bulloneria/saldature", "Annuale", "Serraggio e verifica visiva"],
        ["Lubrificazione parti mobili", "Ogni 6 mesi", "Grasso o olio specifico"],
        ["Controllo trattamento anticorrosione", "Annuale", "Ritoccare se danneggiato"],
        ["Pulizia superficiale", "Secondo necessita'", "Acqua e detergente neutro"],
    ]
    if standard == "EN 13241":
        maint_data.extend([
            ["Verifica dispositivi di sicurezza", "Ogni 6 mesi", "Fotocellule, costa sensibile"],
            ["Controllo bilanciamento molle", "Annuale", "Solo personale autorizzato"],
            ["Verifica impianto elettrico", "Annuale", "Tecnico abilitato"],
        ])

    mt = Table(maint_data, colWidths=[60 * mm, 40 * mm, 60 * mm], repeatRows=1)
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(mt)

    elements.append(Paragraph("4. AVVERTENZE DI SICUREZZA", man_h2))
    warn_style = ParagraphStyle("Warn", parent=normal, textColor=colors.HexColor("#DC2626"), fontName="Helvetica-Bold")
    elements.append(Paragraph("ATTENZIONE:", warn_style))
    warnings = [
        "Non apportare modifiche al prodotto senza autorizzazione del fabbricante.",
        "Non rimuovere o coprire l'etichetta CE e la targa identificativa.",
        "Gli interventi di manutenzione straordinaria devono essere eseguiti da personale qualificato.",
        "Segnalare immediatamente qualsiasi anomalia strutturale (deformazioni, corrosione avanzata, rotture).",
    ]
    if standard == "EN 13241":
        warnings.extend([
            "Non passare sotto il cancello/porta durante il movimento.",
            "Tenere i bambini lontani dal raggio d'azione del prodotto.",
            "In caso di malfunzionamento dei dispositivi di sicurezza, sospendere immediatamente l'uso.",
        ])
    for w in warnings:
        elements.append(Paragraph(f"- {w}", normal))

    elements.append(Paragraph("5. CONTATTI FABBRICANTE", man_h2))
    elements.append(Paragraph(f"<b>{company_name}</b>", normal))
    elements.append(Paragraph(company_addr, normal))
    if company_vat:
        elements.append(Paragraph(f"P.IVA: {company_vat}", normal))

    doc.build(elements)
    buffer.seek(0)
    return buffer

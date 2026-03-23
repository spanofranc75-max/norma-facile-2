"""Fascicolo Generator — Data-driven document generation from NormaConfig.

Generates DOP (Declaration of Performance), CE Label, and User Manual
dynamically from the NormaConfig JSON. Adding a new norm = new fascicolo template.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, String
from io import BytesIO
from datetime import datetime
import zipfile
import json

BLUE = colors.HexColor("#0055FF")
DARK = colors.HexColor("#1E293B")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D97706")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Title_CE", parent=s["Heading1"], fontSize=18, textColor=DARK, alignment=TA_CENTER, spaceAfter=6*mm))
    s.add(ParagraphStyle("H2_CE", parent=s["Heading2"], fontSize=12, textColor=BLUE, spaceBefore=6*mm, spaceAfter=3*mm))
    s.add(ParagraphStyle("Normal_CE", parent=s["Normal"], fontSize=10, leading=14))
    s.add(ParagraphStyle("Bold_CE", parent=s["Normal"], fontSize=10, leading=14, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Center_CE", parent=s["Normal"], fontSize=10, alignment=TA_CENTER))
    s.add(ParagraphStyle("Small_CE", parent=s["Normal"], fontSize=8, textColor=colors.grey))
    s.add(ParagraphStyle("Green_CE", parent=s["Normal"], fontSize=10, textColor=GREEN, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Red_CE", parent=s["Normal"], fontSize=10, textColor=RED, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("Uw_Big", parent=s["Normal"], fontSize=16, fontName="Helvetica-Bold", textColor=BLUE))
    return s


def _ce_mark(size=25*mm):
    d = Drawing(size, size)
    d.add(String(0, size * 0.15, "CE", fontSize=size * 0.7, fontName="Helvetica-Bold", fillColor=DARK))
    return d


def _table_style_header():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ])


def generate_fascicolo_pdf(
    norma_config: dict,
    calc_results: dict,
    product_config: dict,
    company: dict,
) -> BytesIO:
    """Generate a complete fascicolo (DOP + CE Label + User Manual) from NormaConfig."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    st = _styles()
    elements = []

    norma_id = norma_config.get("norma_id", "")
    standard_ref = norma_config.get("standard_ref", norma_id)
    norma_title = norma_config.get("title", "")
    required_perf = norma_config.get("required_performances", [])

    company_name = company.get("business_name", "[Ragione Sociale]")
    company_addr = company.get("address", "[Indirizzo]")
    company_vat = company.get("vat_number", "")
    year = datetime.now().strftime("%Y")
    date_str = datetime.now().strftime("%d/%m/%Y")

    product_type = product_config.get("product_type", "-")
    product_desc = product_config.get("description", product_type)
    decl_num = product_config.get("declaration_number", f"DOP-{year}-001")
    zona = product_config.get("zona_climatica", "")

    thermal = calc_results.get("results", {}).get("thermal", {})
    validation = calc_results.get("validation", {})
    compliant = calc_results.get("compliant", True)

    # ═══════════════════════════════════════════════════════════════
    # PAGE 1: DICHIARAZIONE DI PRESTAZIONE (DOP)
    # ═══════════════════════════════════════════════════════════════
    elements.append(Paragraph("DICHIARAZIONE DI PRESTAZIONE", st["Title_CE"]))
    elements.append(Paragraph("ai sensi del Regolamento UE 305/2011 (CPR)", st["Center_CE"]))
    elements.append(Spacer(1, 8*mm))

    # Header info
    header = [["N. Dichiarazione:", decl_num], ["Data:", date_str], ["Norma:", f"{standard_ref} — {norma_title}"]]
    ht = Table(header, colWidths=[50*mm, 120*mm])
    ht.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 4*mm))

    # 1. Product identification
    elements.append(Paragraph("1. Codice di identificazione unico del prodotto-tipo", st["H2_CE"]))
    elements.append(Paragraph(product_type, st["Normal_CE"]))

    # 2. Intended use
    elements.append(Paragraph("2. Uso o usi previsti del prodotto", st["H2_CE"]))
    uses = norma_config.get("notes", "Uso come indicato nella norma armonizzata di riferimento.")
    elements.append(Paragraph(uses, st["Normal_CE"]))

    # 3. Manufacturer
    elements.append(Paragraph("3. Fabbricante", st["H2_CE"]))
    mfg = f"<b>{company_name}</b><br/>{company_addr}"
    if company_vat:
        mfg += f"<br/>P.IVA: {company_vat}"
    elements.append(Paragraph(mfg, st["Normal_CE"]))

    # 4. Authorized representative
    elements.append(Paragraph("4. Rappresentante autorizzato", st["H2_CE"]))
    elements.append(Paragraph("Non applicabile", st["Normal_CE"]))

    # 5. Assessment system
    elements.append(Paragraph("5. Sistema di valutazione e verifica (AVCP)", st["H2_CE"]))
    avcp = "Sistema 2+" if "1090" in standard_ref else "Sistema 3"
    elements.append(Paragraph(avcp, st["Normal_CE"]))

    # 6. Harmonised standard
    elements.append(Paragraph("6. Norma armonizzata", st["H2_CE"]))
    elements.append(Paragraph(f"<b>{standard_ref}</b>", st["Normal_CE"]))

    # 7. Declared performances (FROM NORMACONFIG!)
    elements.append(Paragraph("7. Prestazioni dichiarate", st["H2_CE"]))

    perf_data = [["Caratteristica essenziale", "Metodo/Norma", "Prestazione"]]
    specs = product_config.get("specs", {})

    for perf in required_perf:
        code = perf.get("code", "")
        label = perf.get("label", code)
        ref = perf.get("test_reference", standard_ref)
        mandatory = perf.get("mandatory", False)
        calc_method = perf.get("calculation_method", "")

        # Get value from calculation results or specs
        value = "NPD"  # Not Performance Declared
        if code == "UW_VALUE" and thermal:
            value = f"Uw = {thermal.get('uw', 'N/D')} W/m²K"
        elif code == "AIR_PERMEABILITY":
            air = calc_results.get("results", {}).get("air_permeability", {})
            value = air.get("label", specs.get("air_class", "NPD"))
        elif code == "WATER_TIGHTNESS":
            water = calc_results.get("results", {}).get("water_tightness", {})
            value = water.get("label", specs.get("water_class", "NPD"))
        elif code == "WIND_RESISTANCE":
            wind = calc_results.get("results", {}).get("wind_resistance", {})
            value = wind.get("label", specs.get("wind_class", "NPD"))
        else:
            # Try to get from specs
            field_map = {
                "EXEC_CLASS": "execution_class",
                "DURABILITY": "durability",
                "FIRE_REACTION": "reaction_to_fire",
                "MECH_RESIST": "mechanical_resistance",
                "SAFE_OPENING": "safe_opening",
                "DANGEROUS_SUBST": "dangerous_substances",
                "SOUND_INSULATION": "sound_insulation",
            }
            spec_key = field_map.get(code, code.lower())
            value = specs.get(spec_key, "Conforme" if mandatory else "NPD")

        suffix = " *" if mandatory else ""
        perf_data.append([f"{label}{suffix}", ref or calc_method or standard_ref, str(value)])

    pt = Table(perf_data, colWidths=[60*mm, 45*mm, 55*mm], repeatRows=1)
    pt.setStyle(_table_style_header())
    elements.append(pt)
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph("* = Caratteristica obbligatoria", st["Small_CE"]))

    # 7b. Thermal detail (if present)
    if thermal:
        elements.append(Paragraph("7b. Dettaglio Trasmittanza Termica — ISO 10077-1", st["H2_CE"]))
        uw = thermal.get("uw", 0)
        uw_style = st["Green_CE"] if compliant else st["Red_CE"]
        elements.append(Paragraph(f"Uw = {uw} W/m²K", st["Uw_Big"]))
        elements.append(Spacer(1, 2*mm))

        th_info = [
            ["Parametro", "Valore"],
            ["Vetro", f"{thermal.get('vetro_label', '-')} (Ug = {thermal.get('ug', '-')})"],
            ["Telaio", f"{thermal.get('telaio_label', '-')} (Uf = {thermal.get('uf', '-')})"],
            ["Distanziatore", f"{thermal.get('distanziatore_label', '-')} (Ψ = {thermal.get('psi', '-')})"],
            ["Area vetro", f"{thermal.get('ag', 0):.3f} m²"],
            ["Area telaio", f"{thermal.get('af', 0):.3f} m²"],
            ["Perimetro vetro", f"{thermal.get('lg', 0):.3f} m"],
        ]
        tht = Table(th_info, colWidths=[60*mm, 100*mm])
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

        # Zone compliance table
        zone_comp = thermal.get("zone_compliance", {})
        if zone_comp:
            elements.append(Spacer(1, 3*mm))
            zdata = [["Zona Climatica", "Limite Uw", "Uw Calcolato", "Esito"]]
            for z in ["A", "B", "C", "D", "E", "F"]:
                info = zone_comp.get(z, {})
                limit = info.get("limit", "-")
                ok = info.get("compliant", False)
                selected = " (cantiere)" if z == zona else ""
                zdata.append([
                    f"Zona {z}{selected}",
                    f"{limit} W/m²K",
                    f"{uw} W/m²K",
                    "CONFORME" if ok else "NON CONFORME",
                ])
            zt = Table(zdata, colWidths=[45*mm, 35*mm, 35*mm, 45*mm], repeatRows=1)
            zt.setStyle(_table_style_header())
            # Color the esito column
            for i in range(1, len(zdata)):
                ok = zone_comp.get(["A", "B", "C", "D", "E", "F"][i-1], {}).get("compliant", False)
                zt.setStyle(TableStyle([
                    ("TEXTCOLOR", (3, i), (3, i), GREEN if ok else RED),
                    ("FONTNAME", (3, i), (3, i), "Helvetica-Bold"),
                ]))
            elements.append(zt)

        # Ecobonus note
        if thermal.get("ecobonus_eligible"):
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph("Prodotto idoneo per detrazione ECOBONUS.", st["Green_CE"]))
        else:
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph("ATTENZIONE: Uw NON conforme per Ecobonus nella zona selezionata.", st["Red_CE"]))

    # 8. Product description
    elements.append(Paragraph("8. Descrizione del prodotto", st["H2_CE"]))
    elements.append(Paragraph(product_desc, st["Normal_CE"]))

    # Validation warnings/errors
    val_warnings = validation.get("warnings", [])
    val_errors = validation.get("errors", [])
    if val_warnings or val_errors:
        elements.append(Paragraph("9. Note di validazione", st["H2_CE"]))
        for e in val_errors:
            elements.append(Paragraph(f"BLOCCO: {e.get('message', '')}", st["Red_CE"]))
        for w in val_warnings:
            elements.append(Paragraph(f"Avviso: {w.get('message', '')}", st["Normal_CE"]))

    # Signature
    elements.append(Spacer(1, 12*mm))
    sig = [
        ["Firmato per conto del fabbricante da:", ""],
        [f"{company_name}", f"Data: {date_str}"],
        ["", ""], ["_________________________", ""], ["(Firma e timbro)", ""],
    ]
    st_sig = Table(sig, colWidths=[90*mm, 80*mm])
    st_sig.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(st_sig)

    # ═══════════════════════════════════════════════════════════════
    # PAGE 2: ETICHETTA CE
    # ═══════════════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements.append(Paragraph("ETICHETTA CE", st["Title_CE"]))
    elements.append(Paragraph("Da apporre sul prodotto ai sensi del Reg. UE 305/2011", st["Center_CE"]))
    elements.append(Spacer(1, 8*mm))

    label_rows = [
        [_ce_mark(25*mm), ""],
        ["", ""],
        [Paragraph(f"<b>{company_name}</b>", st["Normal_CE"]), ""],
        [Paragraph(company_addr, st["Small_CE"]), ""],
        ["", ""],
        [Paragraph(f"<b>Anno:</b> {year}", st["Normal_CE"]), ""],
        [Paragraph(f"<b>N. DOP:</b> {decl_num}", st["Normal_CE"]), ""],
        [Paragraph(f"<b>Norma:</b> {standard_ref}", st["Normal_CE"]), ""],
        [Paragraph(f"<b>Prodotto:</b> {product_type}", st["Normal_CE"]), ""],
        ["", ""],
    ]
    # Add key performances from NormaConfig
    for perf in required_perf:
        if perf.get("mandatory"):
            code = perf["code"]
            label = perf["label"]
            value = "Conforme"
            if code == "UW_VALUE" and thermal:
                value = f"{thermal.get('uw', '-')} W/m²K"
            elif code == "AIR_PERMEABILITY":
                air = calc_results.get("results", {}).get("air_permeability", {})
                value = air.get("label", specs.get("air_class", "NPD"))
            elif code == "WIND_RESISTANCE":
                wind = calc_results.get("results", {}).get("wind_resistance", {})
                value = wind.get("label", specs.get("wind_class", "NPD"))
            elif code == "WATER_TIGHTNESS":
                water = calc_results.get("results", {}).get("water_tightness", {})
                value = water.get("label", specs.get("water_class", "NPD"))
            else:
                field_map = {"EXEC_CLASS": "execution_class", "DURABILITY": "durability",
                             "MECH_RESIST": "mechanical_resistance", "SAFE_OPENING": "safe_opening"}
                value = specs.get(field_map.get(code, code.lower()), "Conforme")
            label_rows.append([Paragraph(f"<b>{label}:</b> {value}", st["Normal_CE"]), ""])

    lt = Table(label_rows, colWidths=[130*mm, 30*mm])
    lt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(lt)
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("Ritagliare lungo il bordo e apporre sul prodotto.", st["Small_CE"]))

    # ═══════════════════════════════════════════════════════════════
    # PAGE 3: MANUALE D'USO E MANUTENZIONE
    # ═══════════════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements.append(Paragraph("MANUALE D'USO E MANUTENZIONE", st["Title_CE"]))
    elements.append(Paragraph(f"Prodotto: {product_type} — {standard_ref}", st["Center_CE"]))
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph("1. INFORMAZIONI GENERALI", st["H2_CE"]))
    elements.append(Paragraph(
        f"Il presente manuale e' parte integrante del prodotto <b>{product_type}</b> "
        f"fabbricato da <b>{company_name}</b> in conformita' alla norma <b>{standard_ref}</b>. "
        "Conservare questo documento per tutta la vita utile del prodotto.",
        st["Normal_CE"],
    ))

    elements.append(Paragraph("2. USO PREVISTO", st["H2_CE"]))
    elements.append(Paragraph(norma_config.get("notes", "Uso secondo le indicazioni della norma armonizzata."), st["Normal_CE"]))

    elements.append(Paragraph("3. PRESTAZIONI DICHIARATE", st["H2_CE"]))
    elements.append(Paragraph(
        "Le prestazioni dichiarate nella DOP allegata sono state determinate in conformita' "
        f"alla norma <b>{standard_ref}</b> e al Regolamento UE 305/2011.",
        st["Normal_CE"],
    ))
    if thermal:
        elements.append(Paragraph(
            f"Trasmittanza termica Uw = <b>{thermal.get('uw', '-')} W/m²K</b> "
            f"calcolata secondo ISO 10077-1.",
            st["Normal_CE"],
        ))

    elements.append(Paragraph("4. MANUTENZIONE ORDINARIA", st["H2_CE"]))
    maint = [
        ["Operazione", "Frequenza", "Note"],
        ["Ispezione visiva generale", "Ogni 6 mesi", "Verificare integrita' strutturale"],
        ["Controllo bulloneria/saldature", "Annuale", "Serraggio e verifica visiva"],
        ["Lubrificazione parti mobili", "Ogni 6 mesi", "Grasso specifico"],
        ["Controllo anticorrosione", "Annuale", "Ritoccare se danneggiato"],
        ["Pulizia superficiale", "Secondo necessita'", "Acqua e detergente neutro"],
    ]
    # Add norm-specific maintenance
    product_types = norma_config.get("product_types", [])
    if any(pt in product_types for pt in ["cancello", "portone"]):
        maint.extend([
            ["Verifica dispositivi sicurezza", "Ogni 6 mesi", "Fotocellule, costa sensibile"],
            ["Controllo bilanciamento molle", "Annuale", "Solo personale autorizzato"],
            ["Verifica impianto elettrico", "Annuale", "Tecnico abilitato"],
        ])
    if any(pt in product_types for pt in ["finestra", "portafinestra"]):
        maint.extend([
            ["Verifica tenuta guarnizioni", "Annuale", "Sostituire se deteriorate"],
            ["Pulizia canali drenaggio", "Ogni 6 mesi", "Evitare ostruzione scarichi"],
            ["Regolazione ferramenta", "Annuale", "Consultare manuale ferramenta"],
        ])

    mt = Table(maint, colWidths=[60*mm, 40*mm, 60*mm], repeatRows=1)
    mt.setStyle(_table_style_header())
    elements.append(mt)

    elements.append(Paragraph("5. AVVERTENZE DI SICUREZZA", st["H2_CE"]))
    elements.append(Paragraph("ATTENZIONE:", st["Red_CE"]))
    warnings_list = [
        "Non apportare modifiche senza autorizzazione del fabbricante.",
        "Non rimuovere l'etichetta CE e la targa identificativa.",
        "Manutenzione straordinaria: solo personale qualificato.",
        "Segnalare anomalie strutturali (deformazioni, corrosione, rotture).",
    ]
    if any(pt in product_types for pt in ["cancello", "portone"]):
        warnings_list.extend([
            "Non passare sotto il cancello/porta durante il movimento.",
            "Tenere i bambini lontani dal raggio d'azione.",
            "Malfunzionamento sicurezze: sospendere immediatamente l'uso.",
        ])
    for w in warnings_list:
        elements.append(Paragraph(f"- {w}", st["Normal_CE"]))

    elements.append(Paragraph("6. CONTATTI FABBRICANTE", st["H2_CE"]))
    elements.append(Paragraph(f"<b>{company_name}</b>", st["Normal_CE"]))
    elements.append(Paragraph(company_addr, st["Normal_CE"]))
    if company_vat:
        elements.append(Paragraph(f"P.IVA: {company_vat}", st["Normal_CE"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_fascicolo_zip(
    norma_config: dict,
    calc_results: dict,
    product_config: dict,
    company: dict,
) -> BytesIO:
    """Generate a ZIP containing all documents (PDF + JSON data)."""
    pdf_buffer = generate_fascicolo_pdf(norma_config, calc_results, product_config, company)

    product_type = product_config.get("product_type", "prodotto")
    decl_num = product_config.get("declaration_number", "DOP")
    prefix = f"{product_type}_{decl_num}".replace("/", "-").replace(" ", "_")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # PDF fascicolo
        zf.writestr(f"{prefix}_fascicolo_CE.pdf", pdf_buffer.getvalue())

        # JSON data (machine readable)
        data_json = {
            "declaration_number": decl_num,
            "date": datetime.now().isoformat(),
            "norma": {
                "norma_id": norma_config.get("norma_id"),
                "standard_ref": norma_config.get("standard_ref"),
                "title": norma_config.get("title"),
            },
            "manufacturer": {
                "name": company.get("business_name", ""),
                "address": company.get("address", ""),
                "vat": company.get("vat_number", ""),
            },
            "product": product_config,
            "calculation_results": calc_results.get("results", {}),
            "compliant": calc_results.get("compliant", False),
            "validation": calc_results.get("validation", {}),
        }
        zf.writestr(f"{prefix}_data.json", json.dumps(data_json, indent=2, ensure_ascii=False, default=str))

    zip_buffer.seek(0)
    return zip_buffer

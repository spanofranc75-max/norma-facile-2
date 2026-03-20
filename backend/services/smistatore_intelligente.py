"""
Smistatore Intelligente — AI per analisi e ritaglio certificati multi-pagina.

Funzionalità:
1. Prende un PDF cumulativo (es. Beltrami), lo spacchetta in pagine
2. Ogni pagina viene analizzata da GPT-4o Vision: estrae numero colata, materiale, dimensioni
3. Fa matching con gli ordini/batches della commessa
4. Tagga ogni pagina con metadata (matched/scorta/pending)
5. Gestisce la regola consumabili (filo ≥1.0mm → 1090, <1.0mm → 13241)
"""
import os
import io
import re
import json
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# Try to import Vision AI
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("emergentintegrations not available — AI analysis disabled")

# Try to import pdf2image for page rendering
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available — PDF page rendering disabled")


# ── Certificate analysis prompt ──
CERT_ANALYSIS_PROMPT = """Sei un analista documentale specializzato in certificati materiali per carpenteria metallica.

Analizza questa pagina di certificato e estrai le informazioni in formato JSON RIGOROSO.

INFORMAZIONI DA ESTRARRE:
1. numero_colata: Il numero di colata/heat number (es. "12345", "A1234-B")
2. tipo_materiale: Tipo di acciaio/materiale (es. "S275JR", "S355J2", "ER70S-6")
3. dimensioni: Dimensioni del prodotto (es. "IPE 200", "HEA 160", "Ø1.2mm", "L50x5")
4. acciaieria: Nome del produttore/acciaieria (es. "Beltrami", "ArcelorMittal")
5. norma_certificato: Norma del certificato (es. "EN 10204 3.1", "EN 10025-2")
6. quantita: Quantità indicata (es. "12 pz", "500 kg", "2400 mm")
7. tipo_prodotto: Categoria (es. "profilato", "lamiera", "tubo", "filo_saldatura", "gas")
8. diametro_mm: Se è filo di saldatura, diametro in mm (es. 1.2, 0.8). null se non applicabile.

Se non riesci a leggere un campo, metti null.
Se la pagina NON è un certificato materiale (es. è un indice, una nota, un DDT), metti tipo_prodotto: "non_certificato".

RISPONDI SOLO con JSON valido:
{
    "numero_colata": "...",
    "tipo_materiale": "...",
    "dimensioni": "...",
    "acciaieria": "...",
    "norma_certificato": "...",
    "quantita": "...",
    "tipo_prodotto": "...",
    "diametro_mm": null
}"""


async def analyze_certificate_page(page_image_b64: str) -> Dict:
    """Analyze a single certificate page using GPT-4o Vision."""
    if not AI_AVAILABLE:
        logger.warning("AI not available, returning empty analysis")
        return {"tipo_prodotto": "non_analizzato"}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"tipo_prodotto": "non_analizzato", "error": "EMERGENT_LLM_KEY missing"}

    chat = LlmChat(
        api_key=api_key,
        session_id=f"cert-{uuid.uuid4().hex[:8]}",
        system_message=CERT_ANALYSIS_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text="Analizza questa pagina di certificato e restituisci il JSON.",
        file_contents=[ImageContent(image_base64=page_image_b64)],
    )

    try:
        response_text = await chat.send_message(user_msg)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {"tipo_prodotto": "errore_analisi", "error": str(e)}


def split_pdf_to_pages(pdf_bytes: bytes) -> List[bytes]:
    """Split a multi-page PDF into individual page PDFs."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        pages.append(buf.getvalue())
    return pages


def pdf_page_to_image_b64(pdf_bytes: bytes, dpi: int = 150) -> Optional[str]:
    """Convert a single-page PDF to a base64-encoded JPEG image."""
    if not PDF2IMAGE_AVAILABLE:
        return None
    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="jpeg", first_page=1, last_page=1)
        if images:
            buf = io.BytesIO()
            images[0].save(buf, format="JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
    return None


def classify_consumable(analysis: Dict) -> Optional[str]:
    """
    Regola Consumabili:
    - Filo ≥ 1.0 mm → EN_1090 (tutte le commesse strutturali attive)
    - Filo < 1.0 mm → EN_13241 / GENERICA
    - Gas → EN_1090 (tutte le commesse strutturali)
    """
    tipo = (analysis.get("tipo_prodotto") or "").lower()
    diametro = analysis.get("diametro_mm")

    if tipo == "gas":
        return "EN_1090"

    if "filo" in tipo or tipo == "filo_saldatura":
        if diametro is not None:
            try:
                d = float(diametro)
                return "EN_1090" if d >= 1.0 else "EN_13241"
            except (ValueError, TypeError):
                pass
        # Default: if we can't determine diameter, assume structural
        return "EN_1090"

    return None  # Not a consumable


def match_page_to_batches(analysis: Dict, batches: List[Dict]) -> Optional[Dict]:
    """
    Match a certificate page to material batches by numero colata.
    Returns the matching batch or None.
    """
    colata = (analysis.get("numero_colata") or "").strip()
    if not colata:
        return None

    for batch in batches:
        batch_colata = (batch.get("numero_colata") or "").strip()
        if batch_colata and colata.lower() == batch_colata.lower():
            return batch

        # Partial match (colata contained in batch or vice versa)
        if batch_colata and (colata.lower() in batch_colata.lower() or batch_colata.lower() in colata.lower()):
            return batch

    return None


async def analyze_and_index_document(
    doc_id: str,
    pdf_bytes: bytes,
    commessa_id: str,
    user_id: str,
    db,
) -> Dict:
    """
    Main entry point: Analyze a multi-page certificate PDF.

    1. Splits the PDF into pages
    2. Analyzes each page with AI Vision
    3. Matches pages to material batches
    4. Applies consumable rules
    5. Stores page-level metadata in doc_page_index

    Returns summary of analysis.
    """
    from core.database import db as default_db
    if db is None:
        db = default_db

    now = datetime.now(timezone.utc)

    # 1. Split PDF
    page_pdfs = split_pdf_to_pages(pdf_bytes)
    total_pages = len(page_pdfs)
    logger.info(f"[SMISTATORE] Analyzing {total_pages} pages from doc {doc_id}")

    # Get material batches for matching
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(200)

    # Get voci and active commesse for future consumable cross-assignment
    _ = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0, "normativa_tipo": 1}
    )
    _ = await db.voci_lavoro.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(50)

    # Active EN_1090 commesse for consumable auto-assignment (future use)
    _ = await db.commesse.find(
        {"user_id": user_id, "normativa_tipo": "EN_1090", "stato": {"$in": ["in_lavorazione", "aperta", "attiva"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1}
    ).to_list(50)

    results = []
    matched_count = 0
    scorta_count = 0

    for page_num, page_pdf in enumerate(page_pdfs, 1):
        # Convert page to image for AI
        page_b64 = pdf_page_to_image_b64(page_pdf)
        if not page_b64:
            results.append({"pagina": page_num, "status": "errore_conversione"})
            continue

        # AI analysis
        analysis = await analyze_certificate_page(page_b64)
        tipo_prodotto = analysis.get("tipo_prodotto", "")

        if tipo_prodotto in ("non_certificato", "errore_analisi", "non_analizzato"):
            results.append({"pagina": page_num, "status": "non_certificato", "analysis": analysis})
            continue

        # Check consumable rule
        consumable_target = classify_consumable(analysis)

        # Try to match to a specific batch
        matched_batch = match_page_to_batches(analysis, batches)

        # Determine matching status
        if matched_batch:
            status = "matched"
            matched_voce = matched_batch.get("voce_id", "")
            matched_count += 1
        elif consumable_target:
            status = "consumabile_auto"
            matched_voce = ""
            matched_count += 1
        else:
            status = "scorta"
            matched_voce = ""
            scorta_count += 1

        # Store single-page PDF as base64
        page_b64_pdf = base64.b64encode(page_pdf).decode("utf-8")

        # Create page index entry
        index_entry = {
            "index_id": f"idx_{uuid.uuid4().hex[:10]}",
            "doc_id": doc_id,
            "commessa_id": commessa_id,
            "user_id": user_id,
            "pagina": page_num,
            "pagine_totali": total_pages,
            "numero_colata": analysis.get("numero_colata") or "",
            "tipo_materiale": analysis.get("tipo_materiale") or "",
            "dimensioni": analysis.get("dimensioni") or "",
            "acciaieria": analysis.get("acciaieria") or "",
            "norma_certificato": analysis.get("norma_certificato") or "",
            "tipo_prodotto": tipo_prodotto,
            "diametro_mm": analysis.get("diametro_mm"),
            "matching_status": status,
            "matched_to_voce": matched_voce,
            "matched_to_batch": matched_batch.get("batch_id", "") if matched_batch else "",
            "consumabile_target": consumable_target,
            "page_pdf_b64": page_b64_pdf,
            "analyzed_at": now.isoformat(),
        }

        await db.doc_page_index.insert_one(index_entry)
        index_entry.pop("_id", None)
        index_entry.pop("page_pdf_b64", None)  # Don't return heavy data

        results.append({
            "pagina": page_num,
            "status": status,
            "numero_colata": analysis.get("numero_colata"),
            "tipo_materiale": analysis.get("tipo_materiale"),
            "dimensioni": analysis.get("dimensioni"),
            "consumabile_target": consumable_target,
        })

    # Update the parent document with analysis summary
    await db.commessa_documents.update_one(
        {"doc_id": doc_id},
        {"$set": {
            "metadata_estratti.smistatore_analizzato": True,
            "metadata_estratti.pagine_totali": total_pages,
            "metadata_estratti.pagine_matched": matched_count,
            "metadata_estratti.pagine_scorta": scorta_count,
            "metadata_estratti.analyzed_at": now.isoformat(),
        }}
    )

    summary = {
        "doc_id": doc_id,
        "pagine_totali": total_pages,
        "pagine_matched": matched_count,
        "pagine_scorta": scorta_count,
        "pagine_non_certificato": total_pages - matched_count - scorta_count,
        "risultati": results,
    }

    logger.info(
        f"[SMISTATORE] Done: {total_pages} pages, {matched_count} matched, {scorta_count} scorta"
    )

    return summary


def get_matched_cert_pages_for_voce(
    page_index: List[Dict], voce_id: str, normativa: str
) -> List[Dict]:
    """
    Filtro Beltrami per il Pulsante Magico:
    Returns only the certificate pages that are relevant to a specific voce.
    Used during PDF generation to include only pertinent pages.
    """
    matched = []
    for entry in page_index:
        # Direct match to this voce
        if entry.get("matched_to_voce") == voce_id:
            matched.append(entry)
            continue

        # Consumable auto-assigned to this normativa
        if entry.get("matching_status") == "consumabile_auto":
            target = entry.get("consumabile_target", "")
            if target == normativa:
                matched.append(entry)
                continue

        # Unmatched pages for the principal voce
        if voce_id == "__principale__" and entry.get("matching_status") == "matched" and not entry.get("matched_to_voce"):
            matched.append(entry)

    return matched

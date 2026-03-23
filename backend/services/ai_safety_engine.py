"""
AI Safety Engine — S3 Motore AI Sicurezza
==========================================
Pipeline: Commessa/Istruttoria/Preventivo → Fasi → Rischi → DPI/Misure → Domande
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from core.database import db

logger = logging.getLogger(__name__)

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None
    logger.warning("emergentintegrations not available — AI safety engine disabled")


# ═══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════

SAFETY_SYSTEM_PROMPT = """Sei un esperto di sicurezza cantieri per aziende di carpenteria metallica.
Il tuo compito è analizzare i dati di una commessa e proporre le fasi lavorative pertinenti per il Piano Operativo di Sicurezza (POS) secondo D.Lgs. 81/2008.

Ti viene fornita una libreria di fasi lavorative con i relativi codici. Devi:
1. Analizzare il contesto della commessa (descrizione, lavorazioni, normativa, cantiere)
2. Selezionare le fasi lavorative pertinenti dalla libreria
3. Per ogni fase, indicare il livello di confidenza e la motivazione
4. Proporre dati cantiere mancanti come domande
5. Suggerire il contesto operativo (tipo cantiere, condizioni, interferenze)

IMPORTANTE:
- Usa SOLO i codici fase dalla libreria fornita (es. FL-001, FL-008)
- Non inventare fasi che non esistono nella libreria
- Segnala come "incerto" ciò che non è chiaro dal contesto
- Segnala come "mancante" ciò che serve ma non hai
- Genera domande SOLO su punti ad alto impatto per la sicurezza

Rispondi ESCLUSIVAMENTE in JSON valido, senza markdown o commenti."""


SAFETY_USER_TEMPLATE = """## Dati Commessa
{commessa_context}

## Libreria Fasi Disponibili
{fasi_library}

## Rispondi con questo schema JSON esatto:
{{
  "fasi_proposte": [
    {{
      "fase_codice": "FL-XXX",
      "confidence": "dedotto|confermato|incerto",
      "reasoning": "motivazione breve",
      "source_refs": ["commessa.description", "preventivo.voce_3"]
    }}
  ],
  "contesto_operativo": {{
    "tipo_cantiere": "officina|cantiere_esterno|misto",
    "interferenze_previste": true/false,
    "lavori_in_quota": true/false,
    "saldatura_in_opera": true/false,
    "mezzi_sollevamento": true/false,
    "verniciatura_prevista": true/false,
    "note_contesto": "breve descrizione contesto"
  }},
  "dati_cantiere_suggeriti": {{
    "attivita_cantiere": "descrizione attivita se deducibile, altrimenti stringa vuota"
  }},
  "domande_ai": [
    {{
      "testo": "domanda concreta",
      "impatto": "alto|medio|basso",
      "gate_critical": true/false,
      "target_campo": "campo che la risposta compilerebbe"
    }}
  ]
}}"""


def _clean_json_response(text: str) -> dict:
    """Extract JSON from AI response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])
    return json.loads(cleaned)


# ═══════════════════════════════════════════════════════════════════
#  CONTEXT GATHERING
# ═══════════════════════════════════════════════════════════════════

async def _gather_context(cantiere: dict, user_id: str) -> dict:
    """Gather all available context from commessa, istruttoria, preventivo, sopralluogo."""
    context = {
        "commessa": None,
        "preventivo": None,
        "istruttoria": None,
        "sopralluogo": None,
        "company": None,
    }

    # Company settings
    company = await db.company_settings.find_one({"user_id": user_id}, {"_id": 0})
    if company:
        context["company"] = {
            "business_name": company.get("business_name", ""),
            "responsabile_nome": company.get("responsabile_nome", ""),
            "classe_esecuzione_default": company.get("classe_esecuzione_default", ""),
        }

    # Commessa
    commessa_id = cantiere.get("parent_commessa_id")
    if commessa_id:
        commessa = await db.commesse.find_one(
            {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
        )
        if commessa:
            context["commessa"] = {
                "title": commessa.get("title", ""),
                "description": commessa.get("description", ""),
                "client_name": commessa.get("client_name", ""),
                "normativa_tipo": commessa.get("normativa_tipo", ""),
                "classe_exc": commessa.get("classe_exc", ""),
                "cantiere": commessa.get("cantiere", {}),
                "notes": commessa.get("notes", ""),
            }

            # Preventivo linked to commessa
            moduli = commessa.get("moduli", {})
            prev_id = moduli.get("preventivo_id") or commessa.get("linked_preventivo_id")
            if prev_id:
                prev = await db.preventivi.find_one(
                    {"preventivo_id": prev_id, "user_id": user_id}, {"_id": 0}
                )
                if prev:
                    lines_summary = []
                    for line in prev.get("lines", [])[:20]:
                        desc = line.get("description", "")
                        qty = line.get("quantity", "")
                        unit = line.get("unit", "")
                        if desc:
                            lines_summary.append(f"- {desc} (Qt: {qty} {unit})")
                    context["preventivo"] = {
                        "subject": prev.get("subject", ""),
                        "normativa": prev.get("normativa", ""),
                        "classe_esecuzione": prev.get("classe_esecuzione", ""),
                        "lines_summary": "\n".join(lines_summary),
                    }

            # Istruttoria AI linked to preventivo
            if prev_id:
                istr = await db.istruttorie.find_one(
                    {"preventivo_id": prev_id, "user_id": user_id}, {"_id": 0}
                )
                if istr:
                    et = istr.get("estrazione_tecnica", {})
                    context["istruttoria"] = {
                        "classificazione": istr.get("classificazione", {}),
                        "lavorazioni_rilevate": et.get("lavorazioni_rilevate", []),
                        "saldature": et.get("saldature", {}),
                        "trattamenti_superficiali": et.get("trattamenti_superficiali", {}),
                        "montaggio_posa": et.get("montaggio_posa", {}),
                        "fasi_produttive_attese": istr.get("fasi_produttive_attese", []),
                        "parole_chiave_rischio": et.get("parole_chiave_rischio", []),
                    }

    # Sopralluogo linked to commessa
    if commessa_id:
        sopr = await db.sopralluoghi.find_one(
            {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
        )
        if sopr:
            context["sopralluogo"] = {
                "luogo": sopr.get("luogo", ""),
                "note": sopr.get("note", ""),
                "criticita": sopr.get("criticita", ""),
            }

    return context


def _build_commessa_text(context: dict, cantiere: dict) -> str:
    """Build a human-readable context string for the AI prompt."""
    parts = []

    # Cantiere existing data
    dc = cantiere.get("dati_cantiere", {})
    if dc.get("attivita_cantiere"):
        parts.append(f"Attivita cantiere: {dc['attivita_cantiere']}")
    if dc.get("indirizzo_cantiere"):
        parts.append(f"Indirizzo: {dc['indirizzo_cantiere']} {dc.get('citta_cantiere', '')}")

    # Commessa
    comm = context.get("commessa")
    if comm:
        parts.append(f"\n### Commessa: {comm.get('title', '')}")
        if comm.get("description"):
            parts.append(f"Descrizione: {comm['description']}")
        if comm.get("client_name"):
            parts.append(f"Cliente: {comm['client_name']}")
        if comm.get("normativa_tipo"):
            parts.append(f"Normativa: {comm['normativa_tipo']}")
        if comm.get("classe_exc"):
            parts.append(f"Classe esecuzione: {comm['classe_exc']}")
        if comm.get("notes"):
            parts.append(f"Note commessa: {comm['notes']}")

    # Preventivo
    prev = context.get("preventivo")
    if prev:
        parts.append(f"\n### Preventivo: {prev.get('subject', '')}")
        if prev.get("lines_summary"):
            parts.append(f"Voci di lavoro:\n{prev['lines_summary']}")

    # Istruttoria AI
    istr = context.get("istruttoria")
    if istr:
        parts.append("\n### Analisi AI (Istruttoria)")
        cl = istr.get("classificazione", {})
        if cl.get("normativa_proposta"):
            parts.append(f"Normativa proposta: {cl['normativa_proposta']} (confidenza: {cl.get('confidenza', '')})")
        lavs = istr.get("lavorazioni_rilevate", [])
        if lavs:
            parts.append("Lavorazioni rilevate: " + ", ".join(l.get("tipo", "") for l in lavs))
        sald = istr.get("saldature", {})
        if sald.get("presenti"):
            parts.append(f"Saldature previste: SI - {sald.get('stato', '')}")
        tratt = istr.get("trattamenti_superficiali", {})
        if tratt.get("tipo") and tratt["tipo"] != "nessuno":
            parts.append(f"Trattamenti superficiali: {tratt['tipo']}")
        mont = istr.get("montaggio_posa", {})
        if mont.get("previsto"):
            parts.append(f"Montaggio in opera: SI - {mont.get('dettaglio', '')}")
        fasi = istr.get("fasi_produttive_attese", [])
        if fasi:
            parts.append("Fasi produttive attese: " + ", ".join(f.get("fase", "") for f in fasi))

    # Sopralluogo
    sopr = context.get("sopralluogo")
    if sopr:
        parts.append("\n### Sopralluogo")
        if sopr.get("luogo"):
            parts.append(f"Luogo: {sopr['luogo']}")
        if sopr.get("note"):
            parts.append(f"Note: {sopr['note']}")
        if sopr.get("criticita"):
            parts.append(f"Criticita: {sopr['criticita']}")

    # Company
    comp = context.get("company")
    if comp:
        if comp.get("classe_esecuzione_default"):
            parts.append(f"\nClasse esecuzione default azienda: {comp['classe_esecuzione_default']}")

    return "\n".join(parts) if parts else "Nessun dato aggiuntivo disponibile. Cantiere vuoto."


def _build_fasi_library_text(fasi: list) -> str:
    """Build a compact library reference for the AI."""
    lines = []
    for f in fasi:
        triggers = f.get("trigger", {}).get("keywords", [])
        lines.append(
            f"- {f['codice']}: {f['nome']} | cat: {f.get('categoria','')} | "
            f"contesto: {','.join(f.get('applicabile_a',[]))} | "
            f"keywords: {','.join(triggers[:5])}"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  RULES ENGINE — Expand rischi + DPI from fasi
# ═══════════════════════════════════════════════════════════════════

async def _expand_rischi_dpi(
    fasi_proposte: list, user_id: str, contesto: dict
) -> dict:
    """Rule-based expansion: fasi → rischi → DPI/misure/apprestamenti + domande."""
    # Load library
    fasi_lib = {f["codice"]: f async for f in db.lib_fasi_lavoro.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    )}
    rischi_lib = {r["codice"]: r async for r in db.lib_rischi_sicurezza.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    )}
    dpi_lib = {d["codice"]: d async for d in db.lib_dpi_misure.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    )}

    fasi_result = []
    dpi_set = {}
    misure_set = {}
    apprestamenti_set = {}
    domande = []

    for fp in fasi_proposte:
        codice = fp.get("fase_codice", "")
        fase_def = fasi_lib.get(codice)
        if not fase_def:
            continue

        rischi_attivati = []
        for rc in fase_def.get("rischi_ids", []):
            rischio = rischi_lib.get(rc)
            if not rischio:
                continue

            # Check exclusion conditions against contesto
            excluded = False
            for exc in rischio.get("condizioni_esclusione", []):
                if exc == "solo_lavorazioni_a_terra" and contesto.get("lavori_in_quota"):
                    continue
                if exc == "nessuna_saldatura" and contesto.get("saldatura_in_opera"):
                    continue
                if exc == "solo_officina" and contesto.get("tipo_cantiere") != "officina":
                    continue

            if excluded:
                continue

            rischi_attivati.append({
                "rischio_codice": rc,
                "confidence": "dedotto",
                "origin": "rules",
                "reasoning": f"Attivato da fase {codice} via libreria",
                "valutazione_override": None,
                "overridden_by_user": False,
            })

            # Expand DPI
            for d in rischio.get("dpi_ids", []):
                if d not in dpi_set:
                    dpi_set[d] = {"codice": d, "origin": "rules", "da_rischi": []}
                dpi_set[d]["da_rischi"].append(rc)

            # Expand Misure
            for m in rischio.get("misure_ids", []):
                if m not in misure_set:
                    misure_set[m] = {"codice": m, "origin": "rules", "da_rischi": []}
                misure_set[m]["da_rischi"].append(rc)

            # Expand Apprestamenti
            for a in rischio.get("apprestamenti_ids", []):
                if a not in apprestamenti_set:
                    apprestamenti_set[a] = {"codice": a, "origin": "rules", "da_rischi": [], "confidence": "dedotto"}
                apprestamenti_set[a]["da_rischi"].append(rc)

            # Collect domande
            for dv in rischio.get("domande_verifica", []):
                if not any(x["testo"] == dv["testo"] for x in domande):
                    domande.append({
                        "testo": dv["testo"],
                        "origine_rischio": rc,
                        "impatto": dv.get("impatto", "medio"),
                        "gate_critical": dv.get("gate_critical", False),
                        "risposta": None,
                        "stato": "aperta",
                    })

        fasi_result.append({
            "fase_codice": codice,
            "confidence": fp.get("confidence", "dedotto"),
            "origin": "ai",
            "reasoning": fp.get("reasoning", ""),
            "source_refs": fp.get("source_refs", []),
            "overridden_by_user": False,
            "rischi_attivati": rischi_attivati,
            "note_utente": "",
        })

    return {
        "fasi_lavoro_selezionate": fasi_result,
        "dpi_calcolati": list(dpi_set.values()),
        "misure_calcolate": list(misure_set.values()),
        "apprestamenti_calcolati": list(apprestamenti_set.values()),
        "domande_residue": domande,
    }


# ═══════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════

async def ai_precompila_cantiere(cantiere_id: str, user_id: str) -> dict:
    """Main S3 pipeline: AI precompilation of safety cantiere."""

    # 1. Load cantiere
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return {"error": "Cantiere non trovato"}

    # 2. Gather context
    context = await _gather_context(cantiere, user_id)
    logger.info(f"[S3] Context gathered for {cantiere_id}: commessa={'yes' if context['commessa'] else 'no'}, "
                f"preventivo={'yes' if context['preventivo'] else 'no'}, istruttoria={'yes' if context['istruttoria'] else 'no'}")

    # 3. Load fasi library
    fasi_lib = await db.lib_fasi_lavoro.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    ).sort("sort_order", 1).to_list(100)

    if not fasi_lib:
        # Seed if needed
        from services.cantieri_sicurezza_service import seed_libreria_v2
        await seed_libreria_v2(user_id)
        fasi_lib = await db.lib_fasi_lavoro.find(
            {"user_id": user_id, "active": True}, {"_id": 0}
        ).sort("sort_order", 1).to_list(100)

    # 4. Build prompt
    commessa_text = _build_commessa_text(context, cantiere)
    fasi_text = _build_fasi_library_text(fasi_lib)

    user_prompt = SAFETY_USER_TEMPLATE.format(
        commessa_context=commessa_text,
        fasi_library=fasi_text,
    )

    # 5. Call AI
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY mancante"}

    if not LlmChat:
        return {"error": "emergentintegrations non installato"}

    chat = LlmChat(
        api_key=api_key,
        session_id=f"s3-safety-{uuid.uuid4().hex[:8]}",
        system_message=SAFETY_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-4o")

    try:
        response_text = await chat.send_message(UserMessage(text=user_prompt))
        ai_result = _clean_json_response(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[S3] JSON parse error: {e}")
        return {"error": f"Errore parsing risposta AI: {e}"}
    except Exception as e:
        logger.error(f"[S3] AI call failed: {e}")
        return {"error": f"Errore AI: {e}"}

    # 6. Extract AI proposals
    fasi_proposte = ai_result.get("fasi_proposte", [])
    contesto_operativo = ai_result.get("contesto_operativo", {})
    dati_suggeriti = ai_result.get("dati_cantiere_suggeriti", {})
    domande_ai = ai_result.get("domande_ai", [])

    # 7. Rules engine: expand rischi → DPI/misure/apprestamenti
    expansion = await _expand_rischi_dpi(fasi_proposte, user_id, contesto_operativo)

    # 8. Merge AI domande with rules domande (deduplicate)
    all_domande = list(expansion["domande_residue"])
    for dq in domande_ai:
        if not any(x["testo"] == dq["testo"] for x in all_domande):
            all_domande.append({
                "testo": dq["testo"],
                "origine_rischio": "AI",
                "impatto": dq.get("impatto", "medio"),
                "gate_critical": dq.get("gate_critical", False),
                "risposta": None,
                "stato": "aperta",
            })
    expansion["domande_residue"] = all_domande

    # 9. Pre-fill soggetti from company settings
    from services.cantieri_sicurezza_service import _set_soggetto
    soggetti = cantiere.get("soggetti", [])
    company = await db.company_settings.find_one({"user_id": user_id}, {"_id": 0})
    if company:
        if company.get("responsabile_nome"):
            _set_soggetto(soggetti, "DATORE_LAVORO", nome=company["responsabile_nome"])
        for fig in company.get("figure_aziendali", []):
            if fig.get("ruolo") and fig.get("nome"):
                _set_soggetto(soggetti, fig["ruolo"],
                              nome=fig.get("nome", ""),
                              telefono=fig.get("telefono", ""),
                              email=fig.get("email", ""))

    # Pre-fill committente from commessa
    if context.get("commessa") and context["commessa"].get("client_name"):
        _set_soggetto(soggetti, "COMMITTENTE", nome=context["commessa"]["client_name"])

    # 10. Build update
    now = datetime.now(timezone.utc).isoformat()
    update = {
        **expansion,
        "soggetti": soggetti,
        "ai_precompilazione": {
            "timestamp": now,
            "modello": "gpt-4o",
            "contesto_operativo": contesto_operativo,
            "dati_cantiere_suggeriti": dati_suggeriti,
            "n_fasi_proposte": len(fasi_proposte),
            "n_rischi_attivati": sum(len(f.get("rischi_attivati", [])) for f in expansion["fasi_lavoro_selezionate"]),
            "n_dpi": len(expansion["dpi_calcolati"]),
            "n_misure": len(expansion["misure_calcolate"]),
            "n_apprestamenti": len(expansion["apprestamenti_calcolati"]),
            "n_domande": len(all_domande),
            "sources_used": [k for k, v in context.items() if v],
        },
        "updated_at": now,
    }

    # Apply dati_cantiere suggestions (only fill empty fields)
    dc = cantiere.get("dati_cantiere", {})
    if dati_suggeriti.get("attivita_cantiere") and not dc.get("attivita_cantiere"):
        update["dati_cantiere"] = {**dc, "attivita_cantiere": dati_suggeriti["attivita_cantiere"]}

    # 11. Save to DB
    await db.cantieri_sicurezza.update_one(
        {"cantiere_id": cantiere_id, "user_id": user_id},
        {"$set": update}
    )

    # 12. Recalculate gate
    from services.cantieri_sicurezza_service import calcola_gate_pos
    updated_doc = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}
    )
    gate = calcola_gate_pos(updated_doc)
    await db.cantieri_sicurezza.update_one(
        {"cantiere_id": cantiere_id},
        {"$set": {"gate_pos_status": gate}}
    )

    return {
        "success": True,
        "cantiere_id": cantiere_id,
        "ai_precompilazione": update["ai_precompilazione"],
        "gate_pos_status": gate,
        "fasi_proposte": len(expansion["fasi_lavoro_selezionate"]),
        "rischi_attivati": sum(len(f.get("rischi_attivati", [])) for f in expansion["fasi_lavoro_selezionate"]),
        "dpi_calcolati": len(expansion["dpi_calcolati"]),
        "misure_calcolate": len(expansion["misure_calcolate"]),
        "apprestamenti_calcolati": len(expansion["apprestamenti_calcolati"]),
        "domande_residue": len(all_domande),
    }

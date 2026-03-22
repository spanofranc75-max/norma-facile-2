# NormaFacile 2.0 — PRD

## Problema Originale
ERP per aziende di carpenteria metallica che gestisce commesse, compliance EN 1090/13241, generazione documenti (DoP, POS), fatturazione, pianificazione, tracciabilita materiali e sicurezza cantieri.

## Architettura
- **Frontend**: React + shadcn/ui + TailwindCSS (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **AI**: OpenAI GPT-4o via emergentintegrations (Emergent LLM Key)
- **PDF**: WeasyPrint per generazione server-side
- **Email**: Resend per notifiche

## Modello Dati Gerarchico (Fase A — COMPLETATO)
`Commessa Madre -> Ramo Normativo -> Emissione Documentale`
- Collezioni: `commesse_normative`, `emissioni_documentali`
- Legacy adapter per commesse vecchie

## Evidence Gate Avanzato (Fase B — COMPLETATO)
- Engine rule-based in `evidence_gate_engine.py`
- Logica condizionale EN 1090 / EN 13241
- Blocco generazione documenti se gate non superato

## Collegamento Segmentazione → Rami (Fase S0 — COMPLETATO)
- Auto-creazione rami normativi dopo conferma istruttoria
- Idempotenza garantita

## Safety Branch MVP (Fase S1 + S2 — COMPLETATO 2026-03-22)
### S1: Analisi Template POS
- Analizzato template `POS STEEL PROJECT.doc` (459 KB, 1760 righe, 31 sezioni)
- Prodotto `SPEC_POS_TEMPLATE_MAPPING.md` con mapping completo

### S2: Implementazione
- **Backend**: Collezioni `cantieri_sicurezza` e `libreria_rischi` con CRUD completo
- **Seed**: 20 entries iniziali (10 fasi lavoro + 10 DPI) per carpenteria metallica
- **Gate POS**: Engine di verifica completezza con campi obbligatori/opzionali
- **Frontend**: Pagina lista `/sicurezza` + form multi-step `/scheda-cantiere/{id}`
- **4 Steps**: Dati Cantiere, Fasi Lavoro, Macchine & DPI, Riepilogo & Gate
- **Testing**: 24/24 backend, 100% frontend

## File Chiave
- `/app/backend/services/cantieri_sicurezza_service.py` — Service Safety Branch
- `/app/backend/routes/cantieri_sicurezza.py` — API endpoints
- `/app/frontend/src/pages/SicurezzaPage.js` — Lista cantieri
- `/app/frontend/src/pages/SchedaCantierePage.js` — Form multi-step
- `/app/SPEC_POS_TEMPLATE_MAPPING.md` — Mapping template POS

## Backlog Prioritizzato

### P0 (Prossimi)
- Motore AI Sicurezza: analisi dati progetto → proposta rischi/fasi automatica
- Generazione DOCX: merge template POS + dati dinamici → bozza POS editabile

### P1
- Dashboard Cantiere Multilivello (Madre → Ramo → Emissione)
- Modulo Verifica Committenza / Contratti
- Stability Guard deterministico

### P2
- Multi-Tenant Architecture
- Automatic ML model training
- Intelligent cost overrun alerts

### P3
- Unificazione servizi PDF legacy
- Portale clienti read-only
- Fix warning minori (exhaustive-deps, hydration)

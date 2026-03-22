# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformita EN 1090-1. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilita materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

**Pivot strategico**: da generatore documentale a copilota tecnico-normativo AI-driven.

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalita Implementate

### Core EN 1090 + Multi-Normativa (Completo)
- Commesse CRUD, FPC, Saldatura, Riesame Tecnico, Ispezioni, DOP, CE Label
- CAM, PDF Executive, Scadenziario, DDT, Fatturazione, Notifiche, QR Code

### Motore di Istruttoria Automatica (Completo)
- P0.1-P0.3 Cockpit, dipendenze, domande, spiegabilita, box "Se confermi"

### P1 — Validazione Real-World (Completato)
- Score: 91% globale, 100% classificazione, 79% estrazione

### P1.1 — Segmentazione Normativa per Riga (Completato)
- Keyword + GPT-4o, review utente, conferma

### Phase 2 — Commessa Pre-Istruita Revisionata (Completato)
- 7 criteri eleggibilita, output con voci/controlli/documenti

### Fase A — Modello Gerarchico Commessa (Completato 22/03/2026)
- 4 livelli: Commessa Madre -> Ramo Normativo -> Emissione Documentale -> Evidence Gate
- Collezioni: `commesse_normative`, `emissioni_documentali`
- Numerazione: `NF-2026-000125-1090-D01`
- Legacy adapter centralizzato, creazione idempotente
- Test: 100% backend (21/21) + 100% frontend (iteration_227)

### Fase B — Evidence Gate Avanzato (Completato 22/03/2026)
- **B1: Motore gate completo** (`evidence_gate_engine.py`):
  - 3 check comuni (scope, ramo, gia emessa)
  - 10+ regole EN 1090 (materiali, cert 3.1, WPS/WPQR, saldatori, registro, VT, controllo finale, riesame tecnico, terzista/zincatura, strumenti/ITT)
  - 6 regole EN 13241 (identificazione, manuale uso, collaudo, dispositivi, posa)
  - Gate minimo GENERICA (scope + warning no DoP/CE)
  - Matrice condizionale: saldatura_attiva, zincatura_esterna, montaggio_attivo, has_automation, requires_force_test, has_safety_devices
  - Output standardizzato: checks[], blockers[], warnings[], completion_percent
  - completion_percent esclude not_applicable dal denominatore
  - Codici blocker/warning standardizzati (MATERIAL_CERT_MISSING, WPS_MISSING, etc.)
- **B2: UI EmissioneDetailPanel** (`EmissioneDetailPanel.js`):
  - 3 colonne: Cosa serve | Cosa c'e | Cosa manca
  - Barra progresso con colore (rosso<50, arancione<80, verde>=80)
  - Blockers e warnings con codici e messaggi
  - Pulsante "collega" per check mancanti linkabili
  - Pulsante "Emetti" solo se emittable=true
  - Click su emissione apre pannello dettaglio
- **B3: Blocco reale emissione**:
  - POST /emetti ricalcola SEMPRE il gate
  - 409 con dettaglio blockers se non emettibile
  - Emissione gia emessa = 409 EMISSION_ALREADY_ISSUED
  - Nessun bypass UI-only
- **Snapshot cache**: last_gate_status, last_gate_check_at, last_completion_percent, last_blockers_count
- Test: 100% backend (24/24) + 100% frontend (iteration_228)

## Backlog Prioritizzato

### P0 — Immediato
- **Auto-generazione rami da segmentazione confermata** — Collegare genera-da-istruttoria al flusso Phase 2 frontend
- **Fase C: Dashboard Cantiere Multilivello** — Vista commessa madre -> rami -> emissioni con progress tracker

### P1
- Progress Tracker per Commessa Pre-Istruita
- Stability guard deterministico per classificazione borderline

### P2
- Multi-Tenant SaaS
- ML Training automatico
- Alert costi reali > budget

### P3
- Unificazione PDF legacy
- Portale clienti read-only
- Fix warning minori (exhaustive-deps, hydration)
- Refactoring: split SettingsPage.js, commesse.py

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

## Collezioni DB
- `commesse_normative`: rami normativi per commessa madre
- `emissioni_documentali`: emissioni progressive per ramo + snapshot cache gate
- `counters`: contatori atomici (emission_{ramo_id}_{type})

## File Chiave Fase B
- `/app/backend/services/evidence_gate_engine.py` — Motore gate completo
- `/app/backend/services/commesse_normative_service.py` — Service layer + snapshot
- `/app/backend/routes/commesse_normative.py` — API endpoints
- `/app/frontend/src/components/EmissioneDetailPanel.js` — UI 3 colonne
- `/app/frontend/src/components/RamiNormativiSection.js` — Lista rami + emissioni

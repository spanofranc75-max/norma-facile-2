# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica. Copilota tecnico-normativo AI-driven per EN 1090, EN 13241, Generica.

## Funzionalita Implementate

### Core ERP (Completo)
Commesse, FPC, Saldatura, Riesame, Ispezioni, DOP, CE Label, CAM, PDF, DDT, Fatturazione, Notifiche, QR Code

### Motore Istruttoria AI (Completo)
Cockpit, dipendenze, domande, spiegabilita, box "Se confermi". Validazione: 91% globale, 100% classificazione.

### Segmentazione + Phase 2 (Completo)
Segmentazione per riga, commessa pre-istruita con 7 criteri eleggibilita.

### Fase A — Modello Gerarchico (Completato 22/03/2026)
4 livelli: Madre → Ramo → Emissione → Gate. Indici univoci, numerazione strutturata, legacy adapter.

### Fase B — Evidence Gate Avanzato (Completato 22/03/2026)
Motore gate con 13+ check EN 1090, 6 EN 13241. Matrice condizionale. UI 3 colonne. Blocco reale 409.

### S0 — Collegamento Segmentazione → Rami (Completato 22/03/2026)
Phase 2 auto-genera rami. genera-da-istruttoria cerca in commesse + commesse_preistruite. Idempotente.

## Backlog

### P0 — Prossimo: Ramo Sicurezza MVP
1. Design dati: scheda cantiere + libreria rischi iniziale
2. Parser template POS.docx
3. Motore AI Sicurezza
4. Generazione DOCX bozza

### P1
- Dashboard Cantiere Multilivello
- Progress Tracker Commessa Pre-Istruita
- Stability guard deterministico

### P2
- Multi-Tenant, ML Training, Alert costi

### P3
- Unificazione PDF, Portale Clienti, Fix warning minori, Refactoring

## Architettura
- Frontend: React + ShadCN/UI (3000) | Backend: FastAPI + MongoDB (8001) | PDF: WeasyPrint | AI: emergentintegrations + GPT-4o

## Collezioni DB Nuove
- `commesse_normative`, `emissioni_documentali`, `counters`

## File Chiave
- `/app/backend/services/evidence_gate_engine.py`
- `/app/backend/services/commesse_normative_service.py`
- `/app/backend/routes/commesse_normative.py`
- `/app/frontend/src/components/EmissioneDetailPanel.js`
- `/app/frontend/src/components/RamiNormativiSection.js`

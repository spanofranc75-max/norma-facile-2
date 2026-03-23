# NormaFacile 2.0 — PRD (Product Requirements Document)

## Problema originale
Sistema operativo verticale per carpenteria metallica / EN 1090 / EN 13241 / sicurezza cantiere / documentazione / committenza.

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI (porta 3000)
- **Backend**: FastAPI + Motor (porta 8001)
- **Database**: MongoDB (100+ collezioni, 49 indici)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **Email**: Resend (chiave configurata)
- **Storage**: Emergent Object Storage (PUT/GET verificati)
- **Auth**: Emergent Google OAuth + JWT + Download Tokens
- **SDI**: FattureInCloud (ATTIVO — 14 fatture inviate, token configurato)

## Completamenti principali

### Hardening (2026-03-23)
- TD-001/002/004/005/009/010, CR-001/002, Data Integrity: tutto completato

### UX (2026-03-23)
- UX-001: CommessaHubPage semplificata (accordion, NextStepCard, ActionsMenu)
- UX-003: Onboarding (checklist 4 step, SmartEmptyState, auto-detect)

### Admin Tools (2026-03-23)
- Data Integrity Tool (POST /run, GET /latest, GET /history — 20 check, admin-only)
- IntegrityWidget sulla Dashboard (semaforo verde/giallo/rosso)

### TD-003 Indici Fase 2 (2026-03-23)
- +22 indici su 15 collezioni (totale: 49 indici)

### Validation Sprint Output & Delivery (2026-03-23)
- **22/22 test passati** — collaudo E2E completo
- **12 PDF verificati**: DoP, CE, Piano Controllo, Fascicolo Completo, Rintracciabilita, Etichetta CE 1090, CAM Dichiarazione, Template 111, DDT, Fattura, Sopralluogo, Perizia
- **1 DOCX verificato**: POS (48KB, firma PK)
- **Object Storage**: PUT/GET funzionanti
- **Download Tokens**: Generazione OK
- **Error Handling**: 404 per ID inesistenti, 401 senza auth
- **Content-Disposition**: Nomi file corretti, nessun placeholder
- **SDI**: FattureInCloud ATTIVO (6/6 criteri, 14 fatture, endpoint funzionante)

## Backlog prioritizzato

### P1
- SmartEmptyState incrementale (Certificazioni, DDT, Fornitori)
- UX Fase 4: Copy diverso per ruolo (admin/tecnico)

### P2 — Business
- Stripe monetizzazione
- Email automatiche selettive
- Demo mode

### P3 — Architettura
- Refactoring file monolitici
- Multi-tenant architecture
- Stability Guard AI
- Pydantic V1 → V2 migration (flagged by testing agent)

## File chiave
- `/app/backend/routes/admin_integrity.py` — Data Integrity Tool
- `/app/backend/routes/onboarding.py` — Onboarding
- `/app/frontend/src/components/IntegrityWidget.js` — Widget DB health
- `/app/frontend/src/components/OnboardingChecklist.js` — Checklist
- `/app/frontend/src/components/SmartEmptyState.js` — Empty state
- `/app/frontend/src/pages/CommessaHubPage.js` — Hub commessa
- `/app/backend/main.py` — 49 indici + startup checks
- `/app/backend/services/object_storage.py` — Storage
- `/app/backend/services/fattureincloud_api.py` — SDI integration

# NormaFacile 2.0 — PRD (Product Requirements Document)

## Problema originale
Sistema operativo verticale per carpenteria metallica / EN 1090 / EN 13241 / sicurezza cantiere / documentazione / committenza. Copilota tecno-normativo-operativo.

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI (porta 3000)
- **Backend**: FastAPI + Motor (porta 8001)
- **Database**: MongoDB (100+ collezioni, 49 indici)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **Email**: Resend
- **Storage**: Object Storage S3
- **Auth**: Emergent Google OAuth + JWT

## Hardening completato (2026-03-23)
- TD-001: Indici MongoDB Fase 1 (27 indici su 12 collezioni critiche)
- TD-002: Router duplicato | TD-005: Rate limiting (slowapi) | TD-009: Background task safety
- TD-010: user_id multi-tenant (7 route) | TD-004: Cleanup dead code | CR-001/002: JWT + LLM key
- Data Integrity: 0 CRITICAL, 0 WARNING

## UX-001 Completato — CommessaHubPage semplificata
- Accordion, 2 colonne, lifecycle bar, CommessaActionsMenu, NextStepCard

## UX-003 Completato — Onboarding primo utilizzo
- OnboardingChecklist (Dashboard, auto-detect 4 step, progress, dismiss)
- SmartEmptyState riutilizzabile (PlanningPage, PreventiviPage)

## Data Integrity Tool Admin Completato
- POST /api/admin/data-integrity/run (20 check, 6 aree)
- GET /api/admin/data-integrity/latest + /history
- Protezione admin-only, report persistito

## TD-003 Completato — Indici MongoDB Fase 2
- **+22 indici nuovi** su 15 collezioni vive (totale: 49 indici)
- Gruppo A (alta priorita): company_settings, audits, non_conformities, voci_lavoro, articoli, gate_certifications, pos_documents, rilievi
- Gruppo B (media priorita): verbali_itt, componenti, dop_frazionate, fpc_projects, report_ispezioni, archivio_certificati, validazioni_p1, verbali_posa, data_integrity_reports
- Ogni indice giustificato da query reali (endpoint + filtro documentati)

## Widget Integrity Check Completato
- IntegrityWidget sulla Dashboard (solo admin): semaforo verde/giallo/rosso, conteggi, timestamp, pulsante "Esegui"

## Backlog prioritizzato

### P1 — Prossimi task
- SmartEmptyState incrementale (Certificazioni, DDT, Fornitori)
- UX Fase 4: Distinzione per ruolo (copy diverso admin/tecnico)

### P2 — Business
- Integrazione Stripe per monetizzazione
- Email automatiche selettive
- Demo mode

### P3 — Architettura
- Refactoring file monolitici
- Multi-tenant architecture
- Stability Guard AI
- Revisione collezioni zombie

## File chiave
- `/app/backend/routes/admin_integrity.py` — Data Integrity Tool
- `/app/backend/routes/onboarding.py` — Onboarding status
- `/app/frontend/src/components/IntegrityWidget.js` — Widget DB health
- `/app/frontend/src/components/OnboardingChecklist.js` — Checklist
- `/app/frontend/src/components/SmartEmptyState.js` — Empty state
- `/app/frontend/src/pages/CommessaHubPage.js` — Hub commessa
- `/app/backend/main.py` — 49 indici + startup checks

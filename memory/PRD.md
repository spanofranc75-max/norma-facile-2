# NormaFacile 2.0 — PRD

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI | **Backend**: FastAPI + Motor | **DB**: MongoDB (49 indici)
- **AI**: OpenAI GPT-4o (emergentintegrations) | **Email**: Resend | **Storage**: Object Storage | **SDI**: FattureInCloud (ATTIVO)
- **Auth**: Emergent Google OAuth + JWT + Download Tokens

## Completamenti

### Hardening (2026-03-23)
TD-001/002/004/005/009/010, CR-001/002, Data Integrity — tutto completato

### UX (2026-03-23)
- UX-001: CommessaHubPage semplificata | UX-003: Onboarding (checklist, SmartEmptyState)
- IntegrityWidget sulla Dashboard (admin-only, semaforo DB health)

### TD-003 Indici Fase 2 (2026-03-23)
+22 indici su 15 collezioni (totale: 49)

### Validation Sprint Output & Delivery (2026-03-23)
22/22 test — 12 PDF + 1 DOCX + storage + tokens + error handling + SDI

### Demo Mode (2026-03-23) — Business Sprint
- **Backend**: POST /api/demo/login (cookie-based), POST /api/demo/reset (admin), GET /api/demo/status
- **Seed Data**: 28 documenti in 10 collezioni — 3 commesse (EN1090+13241 mista, parapetti EXC1, cancello quasi pronto), 2 clienti, 3 preventivi, 7 obblighi, 1 cantiere, activity log
- **Demo Guard**: Email simulata (pacchetti_documentali), SDI simulato (invoices) — nessuna azione esterna reale
- **Frontend**: Banner ambra sticky "Ambiente Demo", bottone "Prova la Demo" su landing page
- **Reset**: POST /api/demo/reset ripristina tutti i dati demo
- **Testing**: 100% (17/17 backend + 5/5 frontend)

### Content Engine M1+M2 (2026-03-23) — Business Sprint
- **Backend**: CRUD sorgenti, generazione idee AI (GPT-4o), generazione bozze AI, coda editoriale, stats
- **Frontend**: Pagina `/contenuti` con 4 tab (Sorgenti, Idee, Bozze, Coda Editoriale)
- **Nav**: Voce "Contenuti" nella sidebar (admin-only, icona PenSquare)
- **Seed**: 10 sorgenti reali con code, category, value_claim, proof_points, suggested_formats
- **Seed upsert**: POST /api/content/seed-sources aggiorna sorgenti esistenti (upsert by title)
- **Tono AI**: 10 regole tassative — italiano B2B tecnico, no hype, no ERP, copilota operativo
- **Campi sorgente**: code, title, type, category, target_audience, pain_points, description, value_claim, proof_points, demo_route, suggested_formats, active
- **Testing**: 100% (16/16 backend + 100% frontend) — iteration_251

## Backlog prioritizzato

### P1 — Business Sprint (prossimi)
- Caso studio quantificato (narrativa commerciale)
- Pricing & Package (Pilot / Pro / Enterprise)
- Mini-hardening SDI/FiC (retry, token refresh, error classification)
- Stripe (dopo pricing definito)

### P2 — UX incrementale
- SmartEmptyState su altre pagine (Certificazioni, DDT, Fornitori)
- Guida Operativa persistente (contestuale, disattivabile, sempre disponibile)
- UX Fase 4: Copy per ruolo

### P3 — Architettura
- Refactoring file monolitici
- Multi-tenant | Stability Guard AI | Pydantic V2

## File chiave
- `/app/backend/routes/demo.py` + `/app/backend/scripts/demo_seed_data.py` — Demo Mode
- `/app/backend/core/demo_guard.py` — Guard azioni esterne
- `/app/frontend/src/components/DemoBanner.js` — Banner demo
- `/app/backend/routes/admin_integrity.py` — Data Integrity Tool
- `/app/frontend/src/components/OnboardingChecklist.js` + `SmartEmptyState.js` + `IntegrityWidget.js`
- `/app/backend/routes/content_engine.py` — Content Engine API (M1+M2)
- `/app/frontend/src/pages/ContentEnginePage.js` — Content Engine UI
- `/app/backend/scripts/content_sources_seed.py` — Seed 10 sorgenti marketing

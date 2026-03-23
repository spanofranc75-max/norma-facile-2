# NormaFacile 2.0 — PRD (Product Requirements Document)

## Problema originale
Sistema operativo verticale per carpenteria metallica / EN 1090 / EN 13241 / sicurezza cantiere / documentazione / committenza. Copilota tecno-normativo-operativo.

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI (porta 3000)
- **Backend**: FastAPI + Motor (porta 8001)
- **Database**: MongoDB (100+ collezioni)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **Email**: Resend
- **Storage**: Object Storage S3
- **Auth**: Emergent Google OAuth + JWT

## Moduli implementati (18)
1. Preventivi — 2. Istruttoria AI — 3. Segmentazione normativa — 4. Commessa pre-istruita
5. Commessa madre / rami normativi / emissioni — 6. Evidence Gate — 7. Sicurezza / Scheda cantiere
8. Motore AI Sicurezza — 9. Generazione POS DOCX — 10. Pacchetti Documentali
11. Invio email documenti — 12. Verifica Committenza — 13. Registro Obblighi (8 fonti)
14. Dashboard multilivello — 15. Audit Log (16 moduli) — 16. Profili documentali
17. Notifiche in-app — 18. Repository documentale

## Hardening completato (2026-03-23)
- TD-001: Indici MongoDB (24 su 12 collezioni) | TD-002: Router duplicato | TD-005: Rate limiting (slowapi)
- TD-009: Background task error handling | TD-010: user_id multi-tenant (7 route)
- TD-004: Cleanup dead code | CR-001/002: JWT + LLM key | Data Integrity: 0 CRITICAL, 0 WARNING

## UX-001 Completato (2026-03-23)
- CommessaHubPage refactorizzata con accordion, 2 colonne, lifecycle bar
- CommessaActionsMenu.js (dropdown) + NextStepCard.js (guida contestuale)

## UX-003 Completato (2026-03-23)
- OnboardingChecklist sulla Dashboard (auto-detect 4 step, progress bar, dismiss)
- SmartEmptyState riutilizzabile su PlanningPage e PreventiviPage
- Backend: GET /api/onboarding/status + POST /api/onboarding/dismiss

## Data Integrity Tool Admin Completato (2026-03-23)
- `POST /api/admin/data-integrity/run` — esegue 20 check su 6 aree, salva report
- `GET /api/admin/data-integrity/latest` — ultimo report completo
- `GET /api/admin/data-integrity/history` — storico report (summary only)
- Protezione admin-only (403 per non-admin)
- Summary leggibile: status (healthy/warning/critical), total_checks, critical/warning/ok count
- Report persistito in collezione `data_integrity_reports`

## Backlog prioritizzato

### P1 — Prossimo task
- **TD-003**: Indici MongoDB su collezioni rimanenti (solo vive + query ricorrenti)

### P2 — Backlog UX
- SmartEmptyState incrementale (Certificazioni, DDT, Fornitori)
- UX Fase 4: Distinzione per ruolo (copy diverso admin/tecnico)
- Tour guidato contestuale (backlog futuro)

### P3 — Business/Architettura
- Integrazione Stripe per monetizzazione
- Email automatiche selettive
- Demo mode
- Refactoring file monolitici
- Multi-tenant architecture
- Stability Guard AI

## File chiave
- `/app/backend/routes/admin_integrity.py` — Data Integrity Tool admin
- `/app/backend/routes/onboarding.py` — Onboarding status
- `/app/frontend/src/components/OnboardingChecklist.js` — Checklist Dashboard
- `/app/frontend/src/components/SmartEmptyState.js` — Empty state riutilizzabile
- `/app/frontend/src/pages/CommessaHubPage.js` — Hub commessa refactorizzato

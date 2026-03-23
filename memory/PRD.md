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
1. Preventivi
2. Istruttoria AI
3. Segmentazione normativa
4. Commessa pre-istruita
5. Commessa madre / rami normativi / emissioni documentali
6. Evidence Gate per emissione
7. Sicurezza / Scheda cantiere
8. Motore AI Sicurezza
9. Generazione POS DOCX
10. Pacchetti Documentali intelligenti
11. Invio email documenti
12. Verifica Committenza / Contratti
13. Registro Obblighi Commessa (8 fonti)
14. Dashboard Cantiere / Commessa multilivello
15. Audit Log (16 moduli)
16. Profili documentali per committente
17. Notifiche intelligenti in-app
18. Repository documentale interno alla commessa

## Hardening completato (2026-03-23)
- TD-001: Indici MongoDB (24 su 12 collezioni)
- TD-002: Router duplicato rimosso
- TD-005: Rate limiting (15 endpoint AI, slowapi)
- TD-009: Background task error handling
- TD-010: Filtro user_id multi-tenant (7 route)
- TD-004: Cleanup dead code
- CR-001/002: JWT + LLM key hardened
- Data Integrity: 0 CRITICAL, 0 WARNING

## UX-001 Completato (2026-03-23)
- CommessaHubPage refactorizzata: accordion, 2 colonne, lifecycle bar
- CommessaActionsMenu.js: dropdown per generazione documenti
- NextStepCard.js: guida contestuale "Cosa devo fare adesso?"
- CostRow fix: componente mancante ripristinato

## UX-003 Completato (2026-03-23)
- **Backend**: `GET /api/onboarding/status` (auto-detection 4 step), `POST /api/onboarding/dismiss`
- **OnboardingChecklist**: componente Dashboard con progress bar, step auto-detected, CTA contestuale, dismiss
- **SmartEmptyState**: componente riutilizzabile (titolo, descrizione, CTA, "cosa succede dopo")
- **Applicato a**: PlanningPage (kanban vuoto), PreventiviPage (lista vuota)
- **Testing**: 100% backend (12/12) + 100% frontend

## Backlog prioritizzato

### P0 — Prossimi task
- Nessun task P0 in coda

### P1 — Task tecnici
- Finalizzare Data Integrity Check come tool admin riutilizzabile
- TD-003: Indici MongoDB collezioni rimanenti

### P2 — Backlog futuro
- UX Fase 4: Distinzione per ruolo (copy diverso per admin/tecnico)
- Revisione collezioni "zombie"
- Refactoring altri file monolitici
- Email automatiche selettive
- Integrazione Stripe per monetizzazione
- Stability Guard AI
- Architettura Multi-Tenant

## File chiave
- `/app/backend/routes/onboarding.py` — Endpoint onboarding
- `/app/frontend/src/components/OnboardingChecklist.js` — Checklist Dashboard
- `/app/frontend/src/components/SmartEmptyState.js` — Empty state riutilizzabile
- `/app/frontend/src/components/CommessaActionsMenu.js` — Dropdown documenti
- `/app/frontend/src/components/NextStepCard.js` — Guida prossimo passo
- `/app/frontend/src/pages/CommessaHubPage.js` — Hub commessa refactorizzato

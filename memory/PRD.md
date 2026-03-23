# NormaFacile 2.0 — PRD

## Prodotto
Sistema operativo verticale / copilota operativo per carpenteria metallica.
Gestisce il ciclo completo: preventivo → istruttoria → commessa → sicurezza → documenti → consegna.

## Architettura
- **Frontend**: React 18 + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + Motor (async MongoDB)
- **DB**: MongoDB (49 indici ottimizzati)
- **AI**: OpenAI GPT-4o via emergentintegrations (EMERGENT_LLM_KEY)
- **Email**: Resend
- **Storage**: Emergent Object Storage
- **SDI**: FattureInCloud (ATTIVO, core)
- **Auth**: Emergent Google OAuth + JWT + session tokens + download tokens
- **PDF**: WeasyPrint | **DOCX**: python-docx
- **Rate Limiting**: slowapi

## Utenti target
- Titolari officina
- Uffici tecnici
- Responsabili sicurezza
- Responsabili qualita
- Amministrazione

## Normative coperte
- EN 1090 (strutture metalliche)
- EN 13241 (cancelli/portoni)
- D.Lgs 81/08 (sicurezza cantiere)

## Core funzionalita (tutte completate)
1. **Preventivi** — CRUD, analisi AI
2. **Istruttoria AI** — Analisi preventivo, classificazione normativa, domande residue
3. **Segmentazione commessa mista** — Rami normativi distinti (EN1090/13241/generico)
4. **Commesse** — Madre, rami, emissioni progressive
5. **Evidence Gate** — Blocco emissione se mancano evidenze
6. **Sicurezza/Cantiere** — Scheda cantiere, rischi 3 livelli, DPI
7. **POS DOCX** — Generazione bozza da commessa/cantiere
8. **Pacchetti documentali** — Matching, verifica scadenze, invio email tracciato
9. **Verifica Committenza AI** — Analisi contratto/capitolato/allegati
10. **Registro Obblighi** — Raccolta automatica da 8 fonti, auto-close/riapertura
11. **Dashboard multilivello** — Vista executive commessa
12. **Audit log** — Tracciamento azioni
13. **Demo Mode** — Login dedicato, seed realistici, guard azioni esterne
14. **Content Engine M1+M2** — Sorgenti, idee AI, bozze AI, coda editoriale
15. **Caso Studio** — Pagina pubblica /caso-studio

## File chiave
- `/app/backend/routes/content_engine.py` — Content Engine API
- `/app/frontend/src/pages/ContentEnginePage.js` — Content Engine UI
- `/app/frontend/src/pages/CaseStudyPage.js` — Caso Studio pubblico
- `/app/backend/routes/demo.py` — Demo Mode endpoints
- `/app/backend/core/demo_guard.py` — Guard azioni esterne
- `/app/backend/routes/admin_integrity.py` — Data Integrity Tool
- `/app/backend/scripts/content_sources_seed.py` — 11 sorgenti marketing
- `/app/backend/scripts/demo_seed_data.py` — Seed dati demo
- `/app/frontend/src/components/DemoBanner.js` — Banner demo
- `/app/frontend/src/components/OnboardingChecklist.js` — Onboarding
- `/app/frontend/src/components/SmartEmptyState.js` — Empty state contestuale
- `/app/frontend/src/components/IntegrityWidget.js` — Widget integrity admin

## Collezioni MongoDB principali
commesse, preventivi, emissioni_documentali, cantieri_sicurezza, obblighi_commessa,
pacchetti_documentali, pacchetti_committenza, analisi_committenza, documenti_archivio,
istruttorie, content_sources, content_ideas, content_drafts, data_integrity_reports,
users, user_sessions, audits, company_settings, voci_lavoro, pos_documents

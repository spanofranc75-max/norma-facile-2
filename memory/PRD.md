# 1090 Norma Facile — PRD

## Problema originale
Sistema gestionale per carpenteria metallica / acciaio strutturale conforme EN 1090.
Audit e hardening dell'app, UX improvements, onboarding, document pipeline, demo mode, Content Engine AI.

## Brand
**1090 Norma Facile** — "Sistema operativo di commessa, sicurezza e compliance per carpenteria metallica"

## Architettura
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Backend**: FastAPI + MongoDB (Motor async)
- **Integrazioni**: OpenAI GPT-4o, Resend, FattureInCloud, Emergent Object Storage
- **Deploy**: Emergent (canonical) + Vercel (backup/staging)

## Utente principale
Francesco Spano' — Steel Project Design Srls
- user_id: `user_97c773827822`
- Ambiente canonico: `content-engine-86.emergent.host` (dopo replace deployment)
- Dominio target: `app.1090normafacile.it` (Aruba, da configurare DNS)

## Struttura domini (decisa)
- `app.1090normafacile.it` = app produzione
- `www.1090normafacile.it` = landing/commerciale
- `demo.1090normafacile.it` = demo (futuro)
- Vercel = backup tecnico, non pubblico

## Stato attuale (24 Marzo 2026)

### Completato in questa sessione ✅
1. **P0 dati aziendali** — root cause: dati demo scritti da test automatici. Fix: dati corretti nel DB + 11 bug codice fixati
2. **3 protezioni** — audit trail before/after, seed guard, sanity check nomi sospetti
3. **Diagnostica** — endpoint + tab frontend per debug produzione
4. **Banner ambiente** — sempre visibile, color-coded per ambiente
5. **Rebranding** — "1090 Norma Facile" applicato ovunque (titolo, PDF, email, footer, content engine, onboarding)
6. **CORS** — dominio 1090normafacile.it aggiunto
7. **Mini-hardening SDI/FiC** — retry automatico (3 tentativi, backoff esponenziale), classificazione errori (auth/validation/transient/etc.), idempotency key anti doppio invio, logging strutturato
8. **System Health Widget** — endpoint `/api/dashboard/system-health` + componente `SystemHealthWidget.js` integrato nella Dashboard. Mostra: conteggi DB, stato azienda, attività outbound, warnings integrità dati
9. **Outbound Audit Log completo** — `log_outbound` aggiunto ai 4 moduli mancanti: sopralluogo (email_perizia), ddt (email_ddt), conto_lavoro (email_conto_lavoro), preventivi (email_preventivo). Tutti i moduli email ora tracciano nel `outbound_audit_log`
10. **Bug Fix: NC lines non persistenti** — Le Note di Credito ora salvano correttamente le modifiche alle righe anche quando lo status non è "bozza" (es. inviata_sdi, emessa). Fix applicato sia al frontend (handleSave invia le righe per NC) che al backend (NC escluse dal blocco modifiche strutturali)

### Feature completate (sessioni precedenti)
- Content Engine (M1+M2)
- Case Study Page
- Outbound Delivery Guard (9 moduli)
- Central Audit Log
- Demo Mode completo

## Backlog prioritizzato

### P1 — Prossimi
- Collegamento dominio Aruba `app.1090normafacile.it` → Emergent
- Caso studio quantificato

### P2 — Medio termine
- Caso studio quantificato
- Pricing & Packaging (Pilot / Pro / Enterprise)
- Calibrazione finale Content Engine

### P3 — Futuro (non toccare ora)
- Stripe integration
- Product Tour
- SmartEmptyState su più pagine
- Refactoring componenti frontend monolitici
- Architettura multi-tenancy
- Stability Guard AI
- Migrazione Pydantic v1 → v2
- Portale clienti

## File critici
- `/app/backend/routes/company.py` — settings + diagnostica + audit
- `/app/backend/routes/demo.py` — seed guard
- `/app/backend/services/fattureincloud_api.py` — FiC client hardened
- `/app/backend/services/email_preview.py` — P.IVA fix
- `/app/frontend/src/lib/utils.js` — rawResponse fix
- `/app/frontend/src/components/EnvironmentBanner.js` — banner ambiente
- `/app/frontend/src/components/settings/DiagnosticaTab.js` — diagnostica UI

## Schema DB chiave
- `company_settings`: {user_id, business_name, partita_iva, ...}
- `company_settings_audit`: {audit_id, user_id, action, before, after, changed_fields, timestamp}
- `outbound_audit_log`: {log_id, user_id, action_type, status, details, timestamp}

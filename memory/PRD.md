# NormaFacile 2.0 — PRD

## Problema originale
Applicazione gestionale per carpenteria metallica / acciaio strutturale conforme EN 1090.
Audit e hardening dell'app, UX improvements, onboarding, document pipeline, demo mode, Content Engine AI.

## Architettura
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Backend**: FastAPI + MongoDB (Motor async)
- **Integrazioni**: OpenAI GPT-4o, Resend, FattureInCloud, Emergent Object Storage
- **Deploy**: Emergent (preview) + Vercel (via GitHub) — DB separati per ambiente

## Utente principale
Francesco Spano' (spano.franc75@gmail.com) — Steel Project Design Srls
- user_id: `user_97c773827822`
- Ambiente canonico attuale: `production-debug-12.preview.emergentagent.com`

## Stato attuale (24 Marzo 2026)

### P0 Risolto ✅
- **Root cause**: dati demo ("Carpenteria Rossi") nel DB per l'account reale, scritti da test automatici di agenti precedenti
- **NON era**: seed demo, startup init, o bug nel codice
- **Fix applicati**:
  - Dati corretti nel DB condiviso
  - 3 query senza filtro user_id fixate (manuale.py, riesame_tecnico.py, verbale_posa.py)
  - 8 fallback hardcoded rimossi
  - 5 letture da collezione legacy `db.settings` migrate a `company_settings`
  - Bug PDF download (rawResponse) fixato in lib/utils.js
  - Bug P.IVA field name mismatch fixato (piva/vat_number → partita_iva)
  - Bug onboarding field name fixato

### Protezioni implementate ✅
- **Audit trail** before/after su company_settings (collezione `company_settings_audit`)
- **Seed Guard** nel demo reset (blocca se trova user_id non-demo)
- **Sanity check** nomi sospetti (warning automatico se business_name sembra test/demo)
- **Endpoint diagnostico** GET /api/company/settings/diagnostics
- **Tab Diagnostica** nel frontend (Impostazioni → Diagnostica)
- **Health check** con info ambiente/DB

### Problema ambiente multipli (da risolvere)
- content-engine-86: codice congelato (vecchia sessione)
- production-debug-12: tutto aggiornato (preview attuale)
- Vercel: codice aggiornato, DB separato
- **Raccomandazione**: consolidare su un solo ambiente operativo

## Feature completate (sessioni precedenti)
- Content Engine (M1+M2) con AI calibrata
- Case Study Page (/caso-studio)
- Outbound Delivery Guard (9 moduli)
- Central Audit Log
- Pre-deploy Hardening CORS
- Demo Mode completo

## Backlog prioritizzato

### P1 — Prossimi
- Mini-hardening SDI/FiC (retry, error classification, token refresh, idempotency)
- Consolidamento ambiente unico

### P2 — Medio termine
- Pricing & Packaging (Pilot / Pro / Enterprise)
- Stripe integration
- Product Tour

### P3 — Futuro
- SmartEmptyState su più pagine
- Audit log esteso a tutti i moduli esterni
- Refactoring componenti frontend monolitici
- Architettura multi-tenancy
- Stability Guard AI
- Migrazione Pydantic v1 → v2

## File critici
- `/app/backend/routes/company.py` — settings + diagnostica + audit
- `/app/backend/routes/demo.py` — seed guard
- `/app/backend/services/email_preview.py` — warning P.IVA fix
- `/app/backend/services/pdf_template_v2.py` — generazione PDF
- `/app/frontend/src/lib/utils.js` — rawResponse fix
- `/app/frontend/src/components/settings/DiagnosticaTab.js` — diagnostica UI
- `/app/frontend/src/pages/SettingsPage.js` — impostazioni con tab diagnostica

## Schema DB chiave
- `company_settings`: {user_id, business_name, partita_iva, codice_fiscale, address, ...}
- `company_settings_audit`: {audit_id, user_id, action, before, after, changed_fields, timestamp}
- `outbound_audit_log`: {log_id, user_id, action_type, status, details, timestamp}

# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenterie metalliche conforme EN 1090, EN 13241, ISO 3834. Gestione commesse, produzione, certificazioni, fatturazione, preventivi, qualita.

## Utenti
- Titolari/Admin di carpenterie metalliche
- Ufficio tecnico, officina, amministrazione

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI -> Vercel
- **Backend**: FastAPI + MongoDB -> Railway
- **Auth**: Google OAuth diretto (produzione) + Emergent Auth (preview)
- **Integrazioni**: FattureInCloud, Resend (email), WeasyPrint (PDF)

## Implementato

### Fix Deployment Vercel
- `.npmrc` con `legacy-peer-deps=true`
- `.nvmrc` con Node 20 LTS
- `vercel.json` con `yarn install` + `CI=false yarn build`

### Fix Login Produzione
- Supporto dual auth: Google OAuth diretto (produzione) + Emergent Auth (preview)

### Fix AI Certificati 3.1
- Backend: corretto URL endpoint + `apt-packages.txt`

### UI Miglioramenti
- Celle allargate nella tabella materiali
- Rimossi spinner arrows (CSS globale)
- Dialog "Registra Arrivo Materiale" quasi full-screen

### Diario di Produzione
- Backend: `routes/diario_produzione.py` — CRUD + riepilogo
- Frontend: `components/DiarioProduzione.js` — Calendario + registrazione ore
- Multi-operatore, multi-sessione per fase
- Anagrafica operatori semplificata (solo nome, no email)

### Fix Calcolo Margini con Diario (20 Mar 2026)
- `margin_service.py`: `get_all_margins()` ora pre-fetch ore dal `diario_produzione`
- Testato: 12/12 test PASSATI

### Fix Deployment Railway (20 Mar 2026)
- Rimosso `--extra-index-url` da `requirements.txt`
- Creato `nixpacks.toml` con config corretta

### Indici MongoDB Ottimizzati (20 Mar 2026)
- `diario_produzione`: idx_commessa_admin, idx_admin_data
- `operatori`: idx_admin
- `sessions`: idx_session_id (unique)
- `user_sessions`: idx_expires (TTL)

### Mobile Responsive (20 Mar 2026)
- **DashboardLayout**: hamburger menu su mobile, sidebar slide-out con backdrop
- **DiarioProduzione**: card fasi compatte, bottoni azione mobile dedicati, dialog touch-friendly
- **CommessaHubPage**: header icon-only su mobile, info card stackabile, KPI compatti
- Testato: 10/10 test PASSATI

### Refactoring Backend: Split commessa_ops.py (20 Mar 2026)
- Da 1 file 3.430 righe a 6 file modulari + 1 wrapper (29 righe)
- `commessa_ops_common.py` (96): helpers condivisi
- `approvvigionamento.py` (516): RdP, OdA, Arrivi, PDF, Email
- `produzione_ops.py` (109): fasi produzione
- `conto_lavoro.py` (477): verniciatura, zincatura, NCR, DDT
- `documenti_ops.py` (1.387): repository documenti + AI parsing cert 3.1
- `consegne_ops.py` (584): consegne, ops data, scheda rintracciabilita, fascicolo tecnico
- Zero breaking changes: main.py e test invariati
- Testato: 17/17 test PASSATI

## Endpoint API Chiave
- `POST /api/auth/callback` — Google OAuth code exchange
- `POST /api/auth/session` — Emergent Auth session exchange
- `GET /api/commesse/{cid}/diario` — Lista voci diario
- `POST /api/commesse/{cid}/diario` — Crea voce diario
- `GET /api/commesse/{cid}/diario/riepilogo` — Riepilogo ore/costi
- `GET /api/costs/commessa/{cid}/margin-full` — Margine singola commessa
- `GET /api/costs/margin-full` — Margine tutte le commesse
- `GET /api/commesse/{cid}/ops` — Dati operativi completi
- `POST /api/commesse/{cid}/approvvigionamento/richieste` — Crea RdP
- `POST /api/commesse/{cid}/consegne` — Crea consegna

## Backlog / Prossimi Task
- P1: Deploy su Railway e test in produzione
- P1: Verifica fix errore 500 analisi AI certificati
- P2: Spezzare CommessaOpsPanel.js frontend (2.959 righe)
- P2: Spezzare SettingsPage.js (1.731 righe)
- P2: Unificare 13 servizi PDF
- P2: Rimuovere placeholder vuoti (chat.py, documents.py)
- P2: Responsive 19 pagine rimanenti
- P2: Onboarding wizard
- P2: Vista "Officina" semplificata per operai
- P3: Sistema RBAC avanzato
- P3: Portale cliente read-only
- P3: Export Excel per commercialista
- P3: Notifiche WhatsApp scadenze

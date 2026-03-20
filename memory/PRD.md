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
- Backend: `POST /api/auth/callback` per Google OAuth code exchange
- Frontend: AuthContext rileva automaticamente quale sistema usare

### Fix AI Certificati 3.1
- Backend: corretto URL endpoint
- Backend: aggiunto `apt-packages.txt` e dipendenze necessarie

### UI Miglioramenti
- Celle allargate nella tabella materiali
- Rimossi spinner arrows (CSS globale)
- Dialog "Registra Arrivo Materiale" quasi full-screen

### Diario di Produzione
- Backend: `routes/diario_produzione.py` — CRUD + riepilogo
- Frontend: `components/DiarioProduzione.js` — Calendario + registrazione ore
- Multi-operatore, multi-sessione per fase
- Vista Calendario mensile + Vista Riepilogo
- Anagrafica operatori semplificata (solo nome, no email)

### Fix Calcolo Margini con Diario (20 Mar 2026)
- `margin_service.py`: `get_all_margins()` ora pre-fetch ore dal `diario_produzione` 
- `margin_service.py`: `get_commessa_margin_full()` gia includeva ore diario
- Testato con 12 test backend: tutti PASSATI

### Fix Deployment Railway (20 Mar 2026)
- Rimosso `--extra-index-url` da `requirements.txt` (causava build failure)
- Creato `nixpacks.toml` con config corretta per Railway:
  - `[phases.install]` usa `pip install -r requirements.txt --extra-index-url ...`
  - `[phases.setup]` include apt packages per WeasyPrint e poppler-utils

## Endpoint API Chiave
- `POST /api/auth/callback` — Google OAuth code exchange
- `POST /api/auth/session` — Emergent Auth session exchange
- `GET /api/commesse/{cid}/diario` — Lista voci diario
- `POST /api/commesse/{cid}/diario` — Crea voce diario
- `PUT /api/commesse/{cid}/diario/{entry_id}` — Modifica voce
- `DELETE /api/commesse/{cid}/diario/{entry_id}` — Elimina voce
- `GET /api/commesse/{cid}/diario/riepilogo` — Riepilogo ore/costi
- `GET /api/costs/commessa/{cid}/margin-full` — Margine completo singola commessa
- `GET /api/costs/margin-full` — Margine completo tutte le commesse

## Backlog / Prossimi Task
- P1: Test completo in produzione del Diario di Produzione + margini (dopo deploy Railway)
- P1: Verifica fix errore 500 analisi AI certificati (dopo deploy Railway)
- P2: Unificare servizi PDF
- P2: Sistema RBAC
- P2: Script migrazione dati per immagini Base64 legacy
- P3: Firme digitali su PDF
- P3: Portale cliente read-only
- P3: Report mensile automatico costi via email

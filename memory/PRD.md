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
- Creato `nixpacks.toml` con config corretta per Railway

### Indici MongoDB Ottimizzati (20 Mar 2026)
- `diario_produzione`: idx_commessa_admin, idx_admin_data
- `operatori`: idx_admin
- `sessions`: idx_session_id (unique)
- `user_sessions`: idx_expires (TTL)

### Mobile Responsive (20 Mar 2026)
- **DashboardLayout**: hamburger menu su mobile, sidebar slide-out con backdrop, breakpoint lg (1024px)
- **DiarioProduzione**: card fasi compatte, bottoni azione mobile dedicati, dialog registrazione touch-friendly (input h-10, 95vw), progress bar mobile
- **CommessaHubPage**: header con bottoni icon-only su mobile, info card stackabile, KPI compatti
- Testato su viewport 390x844 (iPhone 14) e 1920x800 (desktop): 10/10 test PASSATI

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
- P1: Deploy su Railway e test in produzione (nixpacks.toml pronto)
- P1: Verifica fix errore 500 analisi AI certificati (dopo deploy Railway)
- P2: Spezzare file monster (commessa_ops.py 3430 righe, CommessaOpsPanel.js 2959 righe)
- P2: Unificare 13 servizi PDF in un BasePDFService condiviso
- P2: Rimuovere placeholder vuoti (chat.py, documents.py)
- P2: Onboarding wizard primo accesso
- P2: Responsive per altre pagine (33/52 gia responsive, 19 da fare)
- P3: Sistema RBAC avanzato
- P3: Portale cliente read-only
- P3: Report mensile automatico costi via email
- P3: Integrazione WhatsApp per notifiche scadenze
- P3: Export Excel riepilogo costi per commercialista

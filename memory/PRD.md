# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenterie metalliche conforme EN 1090, EN 13241, ISO 3834. Gestione commesse, produzione, certificazioni, fatturazione, preventivi, qualità.

## Utenti
- Titolari/Admin di carpenterie metalliche
- Ufficio tecnico, officina, amministrazione

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI → Vercel
- **Backend**: FastAPI + MongoDB → Railway
- **Auth**: Google OAuth diretto (produzione) + Emergent Auth (preview)
- **Integrazioni**: FattureInCloud, Resend (email), WeasyPrint (PDF)

## Implementato (Sessione Corrente - 20 Mar 2026)

### Fix Deployment Vercel
- `.npmrc` con `legacy-peer-deps=true`
- `.nvmrc` con Node 20 LTS
- `vercel.json` con `yarn install` + `CI=false yarn build`
- `.env.production` con URL backend corretto
- `package.json` engines field

### Fix Login Produzione
- Supporto dual auth: Google OAuth diretto (produzione) + Emergent Auth (preview)
- Backend: aggiunto `POST /api/auth/callback` per Google OAuth code exchange
- Frontend: AuthContext rileva automaticamente quale sistema usare
- Frontend: AuthCallback gestisce sia `?code=` (Google) che `#session_id=` (Emergent)

### Fix AI Certificati 3.1
- Backend: corretto URL endpoint da `parse-certificate` a `parse-certificato` (fix 404)
- Backend: aggiunto `--extra-index-url` in requirements.txt per `emergentintegrations`
- Backend: aggiunto `apt-packages.txt` nella cartella backend
- Backend: migliore error handling con ImportError separato

### UI Miglioramenti
- Celle allargate: Q.tà (12%), U.M. (9%), €/unità (14%), Q.tà Usata (14%)
- Rimossi spinner arrows (CSS globale)
- Rimossi placeholder di esempio
- Rimosso testo suggerimento sotto tabella

### Diario di Produzione (NUOVO)
- Backend: `routes/diario_produzione.py` — CRUD + riepilogo
- Frontend: `components/DiarioProduzione.js` — Calendario + registrazione ore
- Registrazione: data, operatore, fase, ore lavorate, note
- Vista Calendario mensile con evidenziazione giorni con attività
- Vista Riepilogo: ore effettive vs preventivate, costo effettivo, scostamento, per fase e per operatore
- Ore preventivate configurabili per fase di produzione
- Barre progresso colorate per fase con indicazione sforamento

## Sessione Precedente — Fix Completati
- Fix email preventivi (TypeError 500)
- Fix encoding mojibake (ftfy + CI check)
- Fix stale PDF previews (auto-save)
- Fix PDF text readability (grey → black)
- Fix email CC bug
- Fix FattureInCloud 409 credit note
- WeasyPrint dependencies in apt-packages.txt
- Robust RESEND_API_KEY handling

## Backlog / Prossimi Task
- P0: Deploy e test del Diario di Produzione in produzione
- P0: Test completo analisi AI certificato 3.1 dopo deploy Railway
- P1: Unificare servizi PDF (pdf_invoice_modern.py, pdf_template.py)
- P2: Sistema RBAC (controllo accessi basato su ruoli)
- P2: Script migrazione dati per immagini Base64 legacy
- P3: Firme digitali su PDF
- P3: Portale cliente read-only

## Endpoint API Chiave
- `POST /api/auth/callback` — Google OAuth code exchange (NUOVO)
- `POST /api/auth/session` — Emergent Auth session exchange
- `GET /api/commesse/{cid}/diario` — Lista voci diario (NUOVO)
- `POST /api/commesse/{cid}/diario` — Crea voce diario (NUOVO)
- `PUT /api/commesse/{cid}/diario/{entry_id}` — Modifica voce (NUOVO)
- `DELETE /api/commesse/{cid}/diario/{entry_id}` — Elimina voce (NUOVO)
- `GET /api/commesse/{cid}/diario/riepilogo` — Riepilogo ore/costi (NUOVO)
- `PUT /api/commesse/{cid}/produzione/{fase}/ore-preventivate` — Ore stimate (NUOVO)

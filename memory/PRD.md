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
11. **Client Snapshot sui documenti** — Ogni fattura/DDT/preventivo/commessa ora salva una copia immutabile dei dati cliente (`client_snapshot`) al momento della creazione. I documenti storici non cambiano più se si modifica l'anagrafica cliente. Include: servizio `build_snapshot()`, modifica a invoices.py, preventivi.py, ddt.py, commesse.py. GET documenti legge da snapshot quando disponibile.
12. **Stato Cliente (active/archived/blocked)** — Nuovo campo `status` su tutti i clienti. Endpoint: archive, block, reactivate. I clienti archiviati/bloccati non appaiono nella selezione per nuovi documenti. Frontend: colonna Stato con badge colorati, checkbox "Mostra archiviati", pulsanti Archivia/Riattiva.
13. **Migrazione Snapshot** — Endpoint `/api/admin/migration/backfill-client-snapshots` per aggiungere snapshot a tutti i documenti esistenti. Endpoint `/api/admin/migration/snapshot-status` per verificare la copertura. Endpoint `/api/admin/migration/set-default-client-status` per impostare status=active su clienti senza status.
14. **Deploy fix** — Rimosso `litellm==1.80.0` da requirements.txt (pacchetto non usato che bloccava il build)
15. **PDF Preventivo — 7 fix** — (a) Rimosso numero preventivo duplicato, (b) sfondo bianco puro, (c) condizioni di vendita dinamiche (pagamento/validità/consegna da dati preventivo), (d) colonne CODICE/SCONTI visibili solo se valorizzate, (e) indirizzo aziendale dinamico nelle condizioni, (f) 5 errori di battitura corretti, (g) ottimizzazione impaginazione da 3 a 2 pagine
16. **Template Condizioni con Segnaposti** — L'utente puo usare segnaposti come `{pagamento}`, `{validita}`, `{ragione_sociale}`, etc. nel testo delle Condizioni Generali di Vendita (Impostazioni → Condizioni). I segnaposti vengono sostituiti automaticamente con i dati reali nel PDF. Frontend: legenda cliccabile + anteprima live.
17. **Fix Analisi AI pesi a zero** — Aggiunto endpoint `POST /api/preventivatore/analizza-righe` che usa GPT-4o per estrarre profili e pesi dalle descrizioni testuali delle righe preventivo. AnalisiAIPage ora chiama l'AI al caricamento invece di usare solo regex locale. Aggiunto pulsante "Ricalcola AI".
18. **Deploy in produzione** — Codice deployato su `app.1090normafacile.it` con tutti i fix recenti.
19. **Migrazione Snapshot eseguita** — 27 documenti aggiornati, 52 gia completi. Widget MigrationWidget aggiunto alla Dashboard + endpoint GET `/api/admin/migration/run-snapshot` per esecuzione via browser.
20. **Fix Analisi AI 4 errori critici** — (a) Grigliato: aggiunta tabella pesi kg/m2 e calcolo per superficie (13.722→882 kg), (b) Conto lavoro: riconosciuto e escluso dai costi, (c) Specchiature: estrazione dimensioni LxxxxHxxxx (0→682 kg), (d) Manodopera: estrazione ore dal prompt AI.

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

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

## Stato attuale (26 Marzo 2026)

### Completato in questa sessione

34. **Email Destinatari Multipli con Checkbox** (26 Mar 2026):
    - Dialog email mostra checkbox per ogni destinatario (email standard, PEC, contatti)
    - Email standard pre-selezionata come default (NON PEC)
    - Pulsante "Aggiungi email" per email manuali
    - Pulsante invio mostra conteggio destinatari ("Conferma invio a N")
    - Backend: `preview-email` ritorna `all_recipients` array, `send-email` gestisce `to_emails` array
    - Fix 3 bug: variabile `ccEmails` indefinita, sovrascrittura `cc_list`, logica disabilitazione pulsante
    - 17/17 test passati + UI Playwright (iteration_266)

35. **Collegamento Preventivi-Fatture con Indicatore** (26 Mar 2026):
    - Pannello "Documenti Collegati" nella sidebar del preventivo editor
    - Indicatore fatturato con barra di progresso: verde (completo), arancione (parziale)
    - FT vanno in + (verde), NC vanno in - (rosso) nell'indicatore
    - Traccia del collegamento visibile anche nella fattura (badge "P" in lista + sezione "Preventivi Collegati")
    - Supporto multi-preventivo → singola fattura con importo personalizzabile
    - Backend: `link-invoice`, `unlink-invoice`, `linked-documents` endpoints
    - `recalc_preventivo_invoiced` calcola da fonti progressive + manuali
    - `stato_fatturazione`: completo/parziale/non_fatturato
    - 20/20 test backend + tutti test UI Playwright (iteration_267)

36. **Nuovo Cliente Rapido da Rilievo** (26 Mar 2026):
    - Dialog "Nuovo Cliente Rapido" accessibile tramite "+" accanto al selettore clienti nel rilievo
    - Campi minimi: Ragione Sociale (o Cognome/Nome per persona fisica), Cellulare, Email, Indirizzo, Comune, Provincia, Note
    - Checkbox "Persona Fisica" alterna tra i due formati
    - Auto-selezione del cliente creato nel dropdown
    - Propagazione automatica dell'indirizzo al campo "Località/Indirizzo" del rilievo
    - Note prefissate con "[Dati parziali da rilievo]" per tracciare dati incompleti
    - Fix gestione 401: redirect automatico al login quando la sessione scade
    - 13/13 test backend + tutti test UI Playwright (iteration_268)

30. **DDT Numerazione Progressiva e Modificabile**:
    - Contatore atomico per tipo (DDT-2026-XXXX vendita, CL-2026-XXXX conto lavoro, RCL-2026-XXXX rientro)
    - Numero modificabile sia in creazione che in modifica DDT
    - Inizializzazione automatica contatori da dati esistenti al startup
    - 28/29 test passati (iteration_265)

31. **Fatture Collegate alla Commessa**:
    - Endpoint GET/POST/DELETE per collegare/scollegare fatture a una commessa
    - Sezione "Fatture Collegate" nella sidebar della CommessaHubPage
    - Dialog per selezionare e collegare multiple fatture

32. **Bug Fix SDI Preview**:
    - Corretto mapping dati in SdiPreviewDialog (numero, client_name, totale, iva, P.IVA, SDI code)


33. **Sprint 2 Fase B — Multi-Tenant Data Isolation (13 route + 4 service files)**:
    - Route aggiornate: diario_produzione, team, kpi_dashboard, activity_log, montaggio, officina, smart_assign, cantieri_sicurezza, committenza, profili_committente, obblighi_commessa
    - Service aggiornati: cantieri_sicurezza_service, committenza_analysis_service, profili_committente_service, obblighi_commessa_service
    - Tutte le query DB ora filtrano per `tenant_id`, tutti gli insert includono `tenant_id`

29. **Foglio Lavoro PDF — Stampabile per officina**:
    - Endpoint `GET /api/commesse/{id}/foglio-lavoro` genera PDF con QR code, tabella fasi produzione (11 fasi x 3 righe ciascuna), spazio firma e note
    - Nessun dato finanziario visibile (no prezzi, no totali)
    - QR code punta alla scheda produzione della commessa nell'app
    - Pulsante "Foglio Lavoro (Stampa)" aggiunto nel menu "Genera Documenti" della CommessaHubPage
    - 12/12 test passati (iteration_264)

28. **Sprint 2 Fase A — Multi-Tenant Fondamenta**:
    - `services/tenant_service.py`: CRUD tenant (create, get, update, deactivate, list) + auto-onboarding
    - `routes/admin_tenants.py`: API admin (GET/POST/PUT/DELETE /api/admin/tenants/) con RBAC
    - `services/tenant_counters.py`: Contatori isolati per-tenant (atomici, concurrency-safe)
    - `security.py`: Auto-onboarding — primo login admin crea tenant automaticamente
    - Piani: pilot (3 utenti, 50 commesse), pro (10, 500), enterprise (illimitato)
    - 4 nuovi indici MongoDB (tenants, tenant_counters)
    - 15/15 test passati (iteration_263)

27. **Fix collegamenti Cantiere Sicurezza** — Pre-compilazione automatica dalla commessa:
    - Attività cantiere da commessa.oggetto/description
    - Indirizzo/Città/Provincia da commessa.cantiere.indirizzo (parsing regex "Via X, Città (PROV)")
    - Fallback da preventivo.destinazione se indirizzo commessa mancante
    - Fallback da client address se nessun indirizzo disponibile
    - COMMITTENTE soggetto pre-compilato con dati cliente (nome, azienda, email, telefono)
    - Lista cantieri arricchita con commessa_numero, commessa_title, client_name
    - 10/10 test passati (iteration_262)

26. **Sprint 1 — Hardening Sicurezza** — Implementazione completa:
    - RBAC: `core/rbac.py` con decoratore `@require_role()` applicato a 76/89 route files (636 endpoint protetti)
    - Mapping ruoli: admin (wildcard), amministrazione (fatture/costi/clienti), ufficio_tecnico (tecnico/commesse), officina (produzione), guest (bloccato)
    - Audit Trail: `tenant_id` aggiunto a ogni record in `services/audit_trail.py`
    - Cleanup: 2 utenti test rimossi con `migrations/cleanup_test_users.py`
    - JWT_SECRET: rimosso da `core/config.py`, `main.py` lifespan, e `.env` (app usa solo cookie sessions)
    - 28/28 test passati (iteration_261)

### Completato nelle sessioni precedenti
22. **Multi-Tenant Step 1 — Fondamenta** — Implementazione completa del layer di isolamento dati multi-tenant:
    - Aggiunto `tenant_id` a `create_session`, `verify_session`, `get_current_user` in `security.py`
    - Creata collezione `tenants` con tenant "default" all'avvio (`main.py` lifespan)
    - Script di migrazione `migrations/add_tenant_id.py`: backfill 1203 documenti in 45+ collezioni
    - Aggiornati 90+ route files: tutti i filtri query e insert includono `tenant_id`
    - Aggiornati helper `_get_commessa`, `get_commessa_or_404`, `_detect_steps`, `_run_backup_job`
    - `UserResponse` model include `tenant_id`
    - Indici MongoDB creati su `(tenant_id, user_id)` per le collezioni ad alto traffico
    - Utenti invitati ereditano `tenant_id` dall'invitante
    - 16/16 test passati (iteration_258)
23. **Bug Fix: Dropdown clienti vuoto** — Root cause: 
    - Phase 1: backfill `tenant_id` solo su utenti, non dati → aggiunto backfill dinamico all'avvio (enumera TUTTE le collezioni)
    - Phase 2: `tenant_match(user)` restituiva operatore MongoDB `{"$in": [...]}` → rotto per INSERT. Fix: restituisce stringa semplice `"default"`, sicura per READ e WRITE
    - Import mancante in `demo.py` fixato
    - 12/12 test passati (iteration_260), dropdown verificato con 3 clienti visibili
24. **Fix Analisi AI Preventivo — 4 correzioni critiche**:
    - Fix 1+3: Peso grigliato/specchiature — detection by keywords + _estrai_area_da_testo() per dimensioni nel testo (LxxxxHxxxx). Da 13.722 kg → 883 kg, da 0 kg → 424 kg.
    - Fix 2: Conto lavoro server-side detection (keywords: "conto lavoro", "fornito dal cliente", ecc.) → peso=0, flag=true
    - Fix 4: Campo "ore_stimate" aggiunto a righe preventivo (frontend colonna "h" + backend campo + analisi AI)
25. **Bug Fix: Dropdown clienti vuoto (root cause finale)** — I 38 clienti reali importati da FattureInCloud non avevano il campo `status`. Il frontend passava `status=active` che in MongoDB matchava solo esattamente `"active"`, escludendo `null`. Fix: backend `/clients/` ora tratta `status=active` come `{"$in": ["active", null]}` → include anche clienti senza campo status. Verificato con screenshot: 4 clienti visibili incluso uno senza status.

### Completato nelle sessioni precedenti
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
21. **Navigazione Multi-Tab** — Sistema di tab persistenti nella barra superiore. Ogni sezione aperta resta come tab. Supporta max 8 tab. Tab mostra icona+label+X per chiudere. Editor di documenti creano tab dedicate con numero record. Salva posizione scroll. File: `TabContext.js`, `TabBar.js`, modifiche a `DashboardLayout.js` e `App.js`.

### Feature completate (sessioni precedenti)
- Content Engine (M1+M2)
- Case Study Page
- Outbound Delivery Guard (9 moduli)
- Central Audit Log
- Demo Mode completo

## Backlog prioritizzato

### P0 — Sprint 2: Multi-Tenant Reale (prossimo)
- Creare `services/tenant_service.py` (CRUD tenant)
- Creare `routes/admin_tenants.py` (API admin)
- Workflow onboarding: primo login crea tenant
- Aggiornare 27 service files con `tenant_id`
- Contatori per-tenant (commesse, fatture, preventivi)
- Piano & limiti (max commesse, utenti per piano)
- `team.py` migrazione da `team_owner_id` a `tenant_id`
- Backup per-tenant (scope isolato)

### P1 — Sprint 3: Operazioni & Monitoring
- Backup automatico nello scheduler
- Retention policy backup (30 giorni)
- JSON structured logging
- Admin dashboard tenant (frontend)
- Session management (lista/revoca sessioni)
- Health check avanzato con metriche

### P1 — Altre priorita
- Rotazione chiavi sensibili: Aruba SDI, FattureInCloud, Resend (USER ACTION)
- Protezione `.env` su GitHub (git rm --cached)
- Collegamento dominio Aruba `app.1090normafacile.it` → Emergent

### P2 — Sprint 4: Governance
- CSRF protection (double-submit cookie)
- Input sanitization (bleach/escape)
- Documentazione API completa
- Runbook operativo
- Rate limiting per-tenant
- Piano GDPR (data export/delete per tenant)

### P2 — Medio termine
- Caso studio quantificato
- Pricing & Packaging (Pilot / Pro / Enterprise)
- Calibrazione finale Content Engine

### P3 — Futuro (non toccare ora)
- Stripe integration
- Product Tour
- SmartEmptyState su piu pagine
- Refactoring componenti frontend monolitici
- Stability Guard AI
- Migrazione Pydantic v1 → v2
- Portale clienti
- "Registro Comunicazioni"
- `successor_client_id` con avvisi UI

## Schema DB chiave
- `tenants`: {tenant_id, nome_azienda, email_admin, piano, attivo, creato_il, impostazioni}
- `users`: {user_id, email, name, role, tenant_id, team_owner_id, ...}
- `user_sessions`: {session_token, user_id, tenant_id, expires_at, ...}
- `company_settings`: {user_id, tenant_id, business_name, partita_iva, ...}
- ALL data collections: include `tenant_id` field for isolation

## File critici
- `/app/backend/core/rbac.py` — RBAC centralizzato con `@require_role()`
- `/app/backend/services/audit_trail.py` — Audit log con tenant_id
- `/app/backend/core/config.py` — Settings (JWT rimosso)
- `/app/backend/routes/company.py` — settings + diagnostica + audit
- `/app/backend/routes/demo.py` — seed guard
- `/app/backend/services/fattureincloud_api.py` — FiC client hardened
- `/app/backend/services/email_preview.py` — P.IVA fix
- `/app/backend/migrations/apply_rbac.py` — Script applicazione RBAC
- `/app/backend/migrations/cleanup_test_users.py` — Script pulizia utenti test
- `/app/memory/SPRINT1_CHECKLIST.md` — Checklist completa Sprint 1
- `/app/frontend/src/lib/utils.js` — rawResponse fix
- `/app/frontend/src/components/EnvironmentBanner.js` — banner ambiente

## Schema DB chiave
- `company_settings`: {user_id, business_name, partita_iva, ...}
- `company_settings_audit`: {audit_id, user_id, action, before, after, changed_fields, timestamp}
- `outbound_audit_log`: {log_id, user_id, action_type, status, details, timestamp}

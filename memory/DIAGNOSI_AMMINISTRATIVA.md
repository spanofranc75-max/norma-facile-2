# DIAGNOSI COMPLETA — Area Amministrativa e Governance
## NormaFacile 2.0 — SaaS per Carpenteria Metallica
**Data**: 26 Marzo 2026 | **Versione**: 2.2.0

---

## 1) STATO ATTUALE (AS-IS)

### 1.1 Architettura Multi-Tenant

| Aspetto | Stato | Evidenza |
|---------|-------|----------|
| Modello | Single-DB, campo `tenant_id` | 108 collezioni, 1 tenant "default" |
| Mapping utenti | `users.tenant_id = "default"` per tutti i 22 utenti | Nessun workflow di creazione tenant |
| Scope query | `tenant_match(user)` in 89 route files (676 endpoint autenticati) | Funzione in `core/security.py` restituisce stringa |
| Collezione `tenants` | Schema: `{tenant_id, nome_azienda, piano, attivo, impostazioni}` | 1 solo record "default" |
| Backfill startup | Dinamico: enumera TUTTE le collezioni al boot | 1 doc residuo senza `tenant_id` (activity_log) |
| Isolamento reale | **NON ATTIVO** | Tutti i dati condividono tenant "default" |
| Ereditarieta inviti | Utente invitato eredita `tenant_id` dall'admin invitante | Implementato in `create_session()` |

**Modello Dati Chiave (108 collezioni, top 15 per volume):**

| Collezione | Documenti | Con tenant_id | Con user_id | Note |
|------------|-----------|---------------|-------------|------|
| activity_log | 303 | 302 | 303 | 1 doc senza tenant_id |
| fatture_ricevute | 131 | 131 | 131 | Fatture passive |
| preventivi | 112 | 112 | 112 | Core business |
| lib_dpi_misure | 93 | 93 | 93 | Libreria sicurezza |
| articoli | 88 | 88 | 88 | Catalogo |
| backup_log | 80 | 80 | 80 | Storico backup |
| notification_logs | 91 | 91 | 0 | Senza user_id |
| project_costs | 66 | 66 | 66 | Costi commessa |
| lib_rischi_sicurezza | 60 | 60 | 60 | Libreria rischi |
| invoices | 54 | 54 | 54 | Fatture attive |
| lib_tipi_documento | 52 | 52 | 52 | Tipologie doc |
| clients | 48 | 48 | 48 | Clienti |
| calcoli_cam | 48 | 48 | 48 | Calcoli EN 1090 |
| gate_certifications | 33 | 33 | 33 | Gate CE |
| commesse | 22 | 22 | 22 | Commesse produzione |

### 1.2 Autenticazione & Sessioni

| Aspetto | Implementazione |
|---------|----------------|
| Provider | Emergent Google OAuth + Google OAuth diretto |
| Sessione | Cookie `session_token` (httpOnly=true, Secure=true, SameSite=none) |
| Scadenza | 7 giorni (`session_expire_days` in config) |
| Storage | Collezione `user_sessions` in MongoDB |
| Token download | One-time token per iframe PDF (`download_tokens`) |
| Demo mode | Sessione mock con expire 365 giorni |
| Logout | `DELETE /api/auth/logout` — cancella sessione + cookie |
| Fallback | Header `Authorization: Bearer <session_token>` |

### 1.3 RBAC e Security

**Ruoli definiti (`ROLE_PERMISSIONS` in team.py):**

| Ruolo | Permessi | Scope |
|-------|----------|-------|
| `admin` | `["*"]` — tutto | Full access |
| `ufficio_tecnico` | operativo, certificazioni, perizie, impostazioni, commesse, preventivi, clienti | Tecnico |
| `officina` | operativo, commesse | Solo produzione |
| `amministrazione` | acquisti, impostazioni, commesse, preventivi, clienti, fatture, ddt | Amministrativo |
| `guest` | `[]` — nessuno | Read-only implicito |

**Enforcement:**

| Metrica | Valore | Dettaglio |
|---------|--------|-----------|
| Route files totali | 89 | |
| Endpoint totali | 721 | GET+POST+PUT+DELETE |
| Endpoint con autenticazione | 676 (93.7%) | `Depends(get_current_user)` |
| Route con check ruolo | **10 su 89 (11.2%)** | admin_integrity, team, demo, content_engine, ecc. |
| Route SENZA check ruolo | **63 su 89 (70.8%)** | Incluse fatturazione, costi, impostazioni |
| Endpoint pubblici | 45 (6.2%) | Health, auth callback, vendor API |

**Sicurezza infrastrutturale:**

| Aspetto | Stato |
|---------|-------|
| Rate limiting | slowapi: AI=10/min, Heavy=20/min, Standard=60/min |
| CORS | Regex per *.emergentagent.com, *.emergent.host, *.1090normafacile.it |
| CSRF | **ASSENTE** |
| Input validation | Pydantic su endpoint principali (~40%), raw dict su altri |
| XSS sanitization | **ASSENTE** |
| Secret management | .env file (rimosso da git tracking, `.gitignore` OK) |
| Password hashing | N/A (OAuth only) |

### 1.4 Audit & Logging

| Aspetto | Stato |
|---------|-------|
| Sistema | `log_activity()` in `services/audit_trail.py` — fire-and-forget |
| Campi tracciati | user_id, user_name, user_email, action, entity_type, entity_id, label, details, commessa_id, actor_type, timestamp |
| **tenant_id** | **ASSENTE nel record audit** |
| Copertura | **15 route files su 84 autenticati (17.8%)** |
| Entity types | 25 tipi (commessa, preventivo, fattura, ddt, ecc.) |
| Action types | 18 azioni (create, update, delete, ai_precompile, ecc.) |
| Volume | 303 record |

### 1.5 Backup & DR

| Aspetto | Stato |
|---------|-------|
| Sistema | Export JSON per-utente, download ZIP, restore |
| Trigger | Manuale (POST /api/backups/start) |
| Automazione | **Scheduler presente** nel notification_scheduler.py (loop 24h) |
| Scope | Per user_id (non per tenant) |
| Storage | Filesystem locale (/app/backend/uploads/) |
| Retention | Nessuna policy automatica |
| Restore | Merge o replace per collection |
| Volume | 80 backup storici |

### 1.6 Deploy & Infra

| Aspetto | Stato |
|---------|-------|
| Staging | Emergent Platform (preview) |
| Production | Railway.app |
| Frontend | React 18 + Tailwind + Shadcn/UI |
| Backend | FastAPI + Motor (async MongoDB) |
| Database | MongoDB (singolo, no replica set) |
| CI/CD | Nessuno (deploy manuale via Git push) |
| Monitoring | Nessuno (solo log su stdout) |
| Rollback | Emergent rollback feature |
| WeasyPrint | Mocked su Railway (manca GTK) |

### 1.7 Documentazione

| File | Contenuto |
|------|-----------|
| PRD.md | Stato progetto, backlog, feature completate |
| CHANGELOG.md | Storico modifiche |
| ROADMAP.md | Piano futuro |
| PROJECT_KNOWLEDGE.md | Conoscenza tecnica di dominio |
| ARCHITETTURA_TECNICA.md | Architettura di sistema |
| SPEC_PACCHETTI_DOCUMENTALI.md | Spec pacchetti doc CE/1090 |
| SPEC_FASE_A_MODELLO_GERARCHICO.md | Modello gerarchico norme |
| SPEC_LIBRERIA_RISCHI_3_LIVELLI.md | Libreria rischi sicurezza |
| SPEC_POS_RENDERING_MAP.md | Rendering POS |
| SPEC_POS_TEMPLATE_MAPPING.md | Template POS |

**Mancante:** API docs (Swagger c'e' auto-generato da FastAPI), test plan formale, diagrammi architetturali, runbook operativo.

---

## 2) GAP ANALYSIS

### GAP CRITICI (P0) — Rischio immediato

| # | Gap | Impatto | Evidenza |
|---|-----|---------|----------|
| G1 | **RBAC non enforced su 63/89 route** | Un utente `officina` puo accedere a fatture, costi, impostazioni via API diretta | `grep` mostra 0 check ruolo su clients.py, invoices.py, cost_control.py, company.py |
| G2 | **Audit trail senza tenant_id** | Impossibile audit per-tenant, non GDPR-compliant per multi-tenant | `audit_trail.py` non include `tenant_id` |
| G3 | **Audit trail copre solo 17.8% dei route** | 69 route files non loggano nessuna attivita | Solo 15/84 chiamano `log_activity()` |
| G4 | **Nessun tenant reale** | Il plumbing e' presente ma nessun workflow di registrazione/onboarding tenant | Solo 1 tenant "default" |

### GAP IMPORTANTI (P1) — Rischio a medio termine

| # | Gap | Impatto |
|---|-----|---------|
| G5 | **CSRF assente** | Cookie-based auth vulnerabile a cross-site request forgery |
| G6 | **XSS sanitization assente** | Campi testo libero non sanitizzati in 108 collezioni |
| G7 | **Backup non per-tenant** | Quando ci saranno piu tenant, il backup scarica TUTTO |
| G8 | **Nessun monitoring/alerting** | Zero visibilita su errori in produzione |
| G9 | **Service files (27) senza tenant_id** | Query in services/ filtrano solo per user_id |
| G10 | **22 utenti test nel DB** | 19 utenti creati dai test agent, tutti admin nel tenant default |
| G11 | **JWT_SECRET configurato ma non usato** | Confusione: l'app usa cookies, non JWT |
| G12 | **team.py non filtra per tenant** | Sistema team usa `team_owner_id` non `tenant_id` |

### GAP MIGLIORATIVI (P2) — Nice to have

| # | Gap | Impatto |
|---|-----|---------|
| G13 | Nessun JSON structured logging | Difficile analisi log in production |
| G14 | Nessun CI/CD pipeline | Deploy manuale, nessun test automatico pre-deploy |
| G15 | Nessuna retention policy per backup | Backup accumulati senza limiti |
| G16 | Nessun rate limiting per-tenant | Un tenant potrebbe monopolizzare risorse |
| G17 | Nessuna documentazione API formale | Solo Swagger auto-generato |
| G18 | Nessun session management avanzato | Impossibile revocare tutte le sessioni di un utente |

---

## 3) QUICK WINS E RISCHI

### Quick Wins (alto impatto, basso effort)

| # | Azione | Effort | Impatto |
|---|--------|--------|---------|
| QW1 | Aggiungere `tenant_id` a `log_activity()` | 15 min | Risolve G2 |
| QW2 | Script pulizia 19 utenti test | 15 min | Risolve G10 |
| QW3 | Creare decoratore `@require_role()` centralizzato | 1h | Base per risolvere G1 |
| QW4 | Rimuovere `JWT_SECRET` dal config (non usato) | 5 min | Risolve G11 |
| QW5 | Aggiungere backup automatico allo scheduler esistente | 30 min | Lo scheduler 24h esiste gia |
| QW6 | Backfill `tenant_id` sul 1 doc mancante in activity_log | 5 min | 100% coverage |

### Rischi se non si interviene

| Rischio | Probabilita | Impatto | Scenario |
|---------|-------------|---------|----------|
| **Data leakage tra ruoli** | ALTA | CRITICO | Utente `officina` accede a dati finanziari via curl/Postman |
| **Data leakage tra tenant** | MEDIA (se multi-tenant attivato) | CRITICO | Query senza tenant_id mostra dati di altri tenant |
| **CSRF attack** | BASSA | ALTO | Sito malevolo esegue operazioni per conto dell'utente loggato |
| **Perdita dati** | BASSA | CRITICO | Nessun backup automatico, solo manuale |
| **Non conformita GDPR** | MEDIA (con multi-tenant) | ALTO | Impossibile audit trail per-tenant, impossibile data export per-tenant |
| **Outage senza recovery** | BASSA | ALTO | No monitoring, no alerting, MTTR sconosciuto |

---

## 4) ROADMAP DI INTERVENTO

### Sprint 1 — Hardening Sicurezza (5 giorni)

**Obiettivo**: Chiudere i gap critici di sicurezza e audit.

| Task | File | Effort | Gap |
|------|------|--------|-----|
| 1.1 Creare `core/rbac.py` con decoratore `@require_role()` | Nuovo file | 2h | G1 |
| 1.2 Applicare `@require_role()` a tutti i 63 route senza check | 63 file | 4h | G1 |
| 1.3 Aggiungere `tenant_id` a `log_activity()` | audit_trail.py | 15min | G2 |
| 1.4 Estendere `log_activity()` a TUTTI i route CRUD | 69 route files | 3h | G3 |
| 1.5 Script pulizia utenti test | migrations/ | 15min | G10 |
| 1.6 Rimuovere JWT_SECRET dal config | config.py, .env | 5min | G11 |
| 1.7 Backfill 1 doc activity_log mancante | migrations/ | 5min | - |

**Deliverables Sprint 1:**
- `core/rbac.py` — Middleware RBAC centralizzato
- 63 route file patchati con `@require_role()`
- `audit_trail.py` aggiornato con `tenant_id`
- Script `migrations/cleanup_test_users.py`
- Test report RBAC enforcement (unit test per ogni ruolo)

### Sprint 2 — Multi-Tenant Reale (10 giorni)

**Obiettivo**: Abilitare la creazione di tenant indipendenti.

| Task | File | Effort | Gap |
|------|------|--------|-----|
| 2.1 Creare `services/tenant_service.py` (CRUD tenant) | Nuovo file | 3h | G4 |
| 2.2 Creare `routes/admin_tenants.py` (API admin) | Nuovo file | 2h | G4 |
| 2.3 Workflow onboarding: primo login crea tenant | security.py | 2h | G4 |
| 2.4 Aggiornare 27 service files con `tenant_id` | services/*.py | 4h | G9 |
| 2.5 Contatori per-tenant (commesse, fatture) | counters | 2h | G4 |
| 2.6 Piano & limiti (max commesse, utenti per piano) | tenant_service.py | 2h | G4 |
| 2.7 team.py migrazione da `team_owner_id` a `tenant_id` | team.py | 2h | G12 |
| 2.8 Backup per-tenant (scope isolato) | backup.py | 2h | G7 |

**Deliverables Sprint 2:**
- `services/tenant_service.py` — Business logic tenant
- `routes/admin_tenants.py` — API CRUD tenant
- 27 service files patchati
- Contatori isolati per tenant
- Test report isolamento dati (cross-tenant query test)
- `migrations/migrate_team_to_tenant.py`

### Sprint 3 — Operazioni & Monitoring (5 giorni)

**Obiettivo**: Stabilita operativa e visibilita.

| Task | File | Effort | Gap |
|------|------|--------|-----|
| 3.1 Backup automatico nello scheduler | notification_scheduler.py | 1h | G5 |
| 3.2 Retention policy backup (30 giorni) | backup.py | 1h | G15 |
| 3.3 JSON structured logging | core/logging.py | 2h | G13 |
| 3.4 Admin dashboard tenant (frontend) | AdminTenantPage.js | 4h | G4 |
| 3.5 Session management (lista/revoca sessioni) | security.py + UI | 2h | G18 |
| 3.6 Health check avanzato con metriche | main.py | 1h | G8 |

**Deliverables Sprint 3:**
- Backup automatico giornaliero con retention
- JSON logging con request_id e tenant_id
- Pagina admin gestione tenant
- Endpoint `/api/health/detailed` con metriche
- Test report backup/restore

### Sprint 4 — Governance & Documentazione (10 giorni)

**Obiettivo**: Pronto per vendite e onboarding clienti.

| Task | File | Effort | Gap |
|------|------|--------|-----|
| 4.1 CSRF protection (double-submit cookie) | middleware | 3h | G5 |
| 4.2 Input sanitization (bleach/escape) | middleware | 2h | G6 |
| 4.3 Documentazione API completa | /docs | 3h | G17 |
| 4.4 Runbook operativo | memory/ | 2h | - |
| 4.5 Diagrammi architetturali | memory/ | 2h | - |
| 4.6 Rate limiting per-tenant | rate_limiter.py | 2h | G16 |
| 4.7 Piano GDPR (data export/delete per tenant) | nuovo | 3h | - |

**Deliverables Sprint 4:**
- CSRF middleware
- Input sanitization middleware
- Documentazione API Swagger estesa
- Runbook operativo completo
- Diagrammi architettura (Markdown-friendly)
- CI/CD pipeline base

---

## 5) DELIVERABLES COMPLESSIVI

### Codice/Patches

| File | Tipo | Sprint |
|------|------|--------|
| `core/rbac.py` | Nuovo — RBAC middleware centralizzato | S1 |
| `services/audit_trail.py` | Patch — aggiunta tenant_id | S1 |
| `services/tenant_service.py` | Nuovo — Business logic tenant | S2 |
| `routes/admin_tenants.py` | Nuovo — API CRUD tenant | S2 |
| `core/logging.py` | Nuovo — JSON structured logging | S3 |
| `core/csrf.py` | Nuovo — CSRF middleware | S4 |
| `core/sanitizer.py` | Nuovo — Input sanitization | S4 |
| 63 route files | Patch — @require_role() | S1 |
| 27 service files | Patch — tenant_id queries | S2 |

### Script di Migrazione

| Script | Scopo | Sprint |
|--------|-------|--------|
| `migrations/cleanup_test_users.py` | Rimuovere 19 utenti test | S1 |
| `migrations/migrate_team_to_tenant.py` | team_owner_id -> tenant_id | S2 |
| `migrations/backfill_counters.py` | Contatori per-tenant | S2 |

### Documentazione

| Documento | Contenuto | Sprint |
|-----------|-----------|--------|
| `SPEC_RBAC.md` | Matrice permessi per ruolo/entita | S1 |
| `SPEC_MULTI_TENANT.md` | Architettura multi-tenant | S2 |
| `RUNBOOK.md` | Procedure operative | S4 |
| `API_DOCS.md` | Documentazione API estesa | S4 |
| Diagrammi architettura | Data model, flussi, deploy | S4 |

---

## 6) TESTING E KPI

### Test Scenarios per Sprint

**Sprint 1 — RBAC:**
- TS1.1: Utente `officina` chiama GET /api/invoices/ -> 403 Forbidden
- TS1.2: Utente `admin` chiama GET /api/invoices/ -> 200 OK
- TS1.3: Utente `amministrazione` chiama GET /api/invoices/ -> 200 OK
- TS1.4: Utente `guest` chiama qualsiasi endpoint CRUD -> 403 Forbidden
- TS1.5: Audit log contiene tenant_id per ogni operazione

**Sprint 2 — Tenant Isolation:**
- TS2.1: Creare tenant A e tenant B, inserire clienti in A -> B non li vede
- TS2.2: Utente di tenant A non puo accedere a commesse di tenant B
- TS2.3: Contatori fatture isolati (A:FT-001, B:FT-001 indipendenti)
- TS2.4: Onboarding: nuovo login crea automaticamente tenant

**Sprint 3 — Operazioni:**
- TS3.1: Backup automatico si esegue ogni 24h
- TS3.2: Restore da backup ripristina solo dati del tenant
- TS3.3: Health check avanzato restituisce metriche corrette

**Sprint 4 — Governance:**
- TS4.1: CSRF token richiesto per POST/PUT/DELETE
- TS4.2: Input con `<script>` viene sanitizzato
- TS4.3: Data export per tenant conforme GDPR

### KPI Suggeriti

| KPI | Target | Misurazione |
|-----|--------|-------------|
| Unauthorized access attempts | 0 al giorno | Log 403 per role violation |
| tenant_id coverage in audit | 100% | Query count docs without tenant_id |
| Time to create tenant | < 30 secondi | Onboarding flow timer |
| Time to generate DoP/CE | < 5 secondi | API response time |
| Backup success rate | 100% | backup_log.status == "completed" |
| Mean Time To Recovery (MTTR) | < 1 ora | Runbook + restore test |
| Audit trail coverage | 100% route CRUD | grep log_activity coverage |
| RBAC enforcement | 100% route autenticati | grep @require_role coverage |

---

## 7) RISORSE E INPUT NECESSARI

Per procedere con l'implementazione, conferma:

1. **Matrice RBAC desiderata** — L'attuale mappa 5 ruoli x sidebar groups. Vuoi una matrice piu granulare (per entita/azione)?
   - Esempio: `officina` puo LEGGERE commesse ma non CREARE? O blocco totale?

2. **Moduli interessati per RBAC prioritario** — Tutti i 89 route o focus su:
   - Fatturazione (invoices, fatture_ricevute, ddt)
   - Costi (cost_control, sal_acconti)
   - Impostazioni (company, payment_types)
   - EN 1090/13241 (cam, fpc, gate_certification, certificazioni)

3. **Policy backup** — Frequenza desiderata? (giornaliero/settimanale)
   - Retention: 30 giorni? 90 giorni?

4. **Monitoring** — Preferenze tool?
   - a) Semplice: health check + log file rotation
   - b) Medio: JSON logging + endpoint metriche
   - c) Avanzato: integrazione ELK/Grafana/Datadog (richiede infra)

5. **Formato output preferito** — Markdown nei file memoria o PDF esportabile?

---

## 8) NOTE OPERATIVE

- **Ordine di esecuzione**: Sprint 1 (hardening) PRIMA di Sprint 2 (multi-tenant). Non introdurre nuova logica business su fondamenta insicure.
- **Backward compatibility**: Tutti i fix sono retrocompatibili. Il decoratore @require_role() non rompe endpoint esistenti per admin.
- **Deploy strategy**: Ogni sprint si chiude con test automatici + deploy su staging, poi push a production dopo verifica manuale.
- **Branch naming**: `feature/sprint-1-rbac`, `feature/sprint-2-multitenant`, ecc.
- **Commit messages**: `[S1] RBAC: add @require_role to invoices.py`, `[S2] TENANT: create tenant_service.py`

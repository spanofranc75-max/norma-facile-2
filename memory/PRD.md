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

## Stato attuale (27 Marzo 2026)

### Completato in questa sessione

41. **Migrazione Auth da Cookie a Bearer Token** (27 Mar 2026):
    - Causa: CORS `Access-Control-Allow-Origin: *` di Kubernetes Ingress incompatibile con `credentials: 'include'`
    - Frontend: `utils.js` → token da `localStorage`, header `Authorization: Bearer`
    - Frontend: `AuthContext.js` → `setAuthUser` salva token in `localStorage`
    - Backend: `get_current_user` → legge cookie OPPURE header Bearer (fallback)
    - Backend: `delete_session` → corretto per leggere anche header Bearer (fix logout)
    - Test E2E completi: 15/15 backend + tutti frontend passati (iteration_270)

38. **RCA Integrazione Fatture in Cloud / SDI** (27 Mar 2026):
    - Root Cause Analysis completa salvata in `/app/docs/RCA_FIC_SDI.md`
    - Causa certa 502: Token OAuth FIC scaduto (prefisso `a/`, scadenza 24h)
    - Causa probabile 400: SDI=0000000 + PEC vuota su alcuni clienti
    - Evidenza diretta: curl HTTP 401 `invalid_token`
    - Report approvato dall'utente con 4 integrazioni richieste completate

39. **Fix Chirurgici FIC/SDI — Fase 1** (27 Mar 2026):
    - Fix 1: Constructor `FattureInCloudClient` fallback corretto (`fic_access_token` al posto di `sdi_api_key`)
    - Fix 2: Helper centralizzato `_get_fic_credentials()` usato da `send-sdi` e `stato-sdi`
    - Fix 3: Endpoint `stato-sdi` allineato — stessa lettura credenziali + errore 502 (non 500)
    - Fix 4: Endpoint `stato-sdi` corretto — usa `?fieldset=detailed` per leggere `ei_status` (prima usava `/e_invoice/xml` che restituiva XML non parsabile)
    - Fix 5: Mappatura `ei_status` → stato locale fattura (sent, pending, error, discarded)
    - Fix 6: Logging SDI persistente in `sdi_audit_log` — ogni chiamata FIC tracciata nel DB
    - Fix 7: Validazione potenziata — blocca invio se SDI=0000000 E PEC vuota
    - Fix 8: Pulsante "Aggiorna Stato SDI" nel dropdown lista fatture
    - Test end-to-end: Fattura 28/2026 inviata a SDI con successo (fic_id: 513739446)
    - Test stato: ei_status "sent" confermato per fatture 17/2026 e 28/2026
    - 8 record audit log creati con traccia completa

40. **Token Manuale FIC Definitivo** (27 Mar 2026):
    - Creata nuova app "NormaFacileSDI" su FIC con autenticazione "Token personale"
    - App ID: 17571, Client ID: `mrHhZ4Mk3KH9Sai29S2gSwvE4cK4FRi4`
    - Token personale generato — JWT senza campo `exp` (nessuna scadenza)
    - Token salvato nel DB `company_settings` (source of truth) + `.env` (fallback)
    - Procedura operativa documentata in `/app/docs/PROCEDURA_FIC_SDI.md`

### Completato nelle sessioni precedenti

34. **Email Destinatari Multipli con Checkbox** (26 Mar 2026)
35. **Collegamento Preventivi-Fatture con Indicatore** (26 Mar 2026)
36. **Nuovo Cliente Rapido da Rilievo** (26 Mar 2026)
37. **Hardening Sessioni e Gestione Auth** (26 Mar 2026)
30. **DDT Numerazione Progressiva e Modificabile**
31. **Fatture Collegate alla Commessa**
32. **Bug Fix SDI Preview**
33. **Sprint 2 Fase B — Multi-Tenant Data Isolation**
29. **Foglio Lavoro PDF**
28. **Sprint 2 Fase A — Multi-Tenant Fondamenta**
27. **Fix collegamenti Cantiere Sicurezza**
26. **Sprint 1 — Hardening Sicurezza**
25. **Multi-Tenant Routing + Middleware**
1-24. **Funzionalita core** (commesse, fatture, preventivi, DDT, rilievi, documenti, notifiche, etc.)

## Integrazione FIC/SDI — Stato definitivo

### Token
- Tipo: Token personale (app "NormaFacileSDI", ID 17571)
- Scadenza: Mai (token personale FIC)
- Source of truth: DB `company_settings.fic_access_token`
- Fallback: `.env` `FIC_ACCESS_TOKEN`

### Flusso SDI
1. Frontend → `POST /api/invoices/{id}/send-sdi`
2. Backend valida dati (SDI/PEC, campi obbligatori)
3. Backend crea/aggiorna fattura su FIC
4. Backend invia a SDI via FIC
5. Stato salvato nel DB + audit log

### Verifica Stato
- Endpoint: `GET /api/invoices/{id}/stato-sdi`
- Legge `ei_status` da FIC (`fieldset=detailed`)
- Aggiorna stato locale se cambiato
- Pulsante "Aggiorna Stato SDI" nel dropdown fatture

### Audit Log
- Collezione: `sdi_audit_log`
- Campi: log_id, invoice_id, document_number, action, fic_endpoint, timestamp, response_status, response_summary, error_category, error_message, fic_document_id, user_id

## Task Pending / Upcoming

### P1 — Fase 2 Stabilizzazione (dopo conferma stabilita token)
1. Spostamento credenziali FIC a livello tenant/company (non user_id)
2. Polling schedulato stati SDI (ogni 15 min)
3. Stati fattura intermedi (`invio_in_corso`, `errore_invio`)
4. Mappatura ID tipi IVA dal catalogo FIC
5. Riproduzione documentata di caso reale 400

### P2 — Sprint 2 Fase C/D
- Backup scheduler per tenant
- RBAC su nuove route onboarding
- Documentazione `SPEC_MULTI_TENANT.md`

### P3 — Sprint 3+
- JSON logging, admin dashboard per tenant
- CSRF, input sanitization, rate limiting per-tenant, GDPR
- Stripe integration
- Product Tour

## Regole NON negoziabili

1. **Token FIC nel DB, non nell'env** — L'env serve solo come fallback iniziale
2. **Lettura token centralizzata** — `_get_fic_credentials()` usato ovunque
3. **Ogni chiamata FIC loggata nel DB** — `sdi_audit_log`
4. **Errori FIC SEMPRE mappati a 502/503** — MAI 401 verso il frontend
5. **Validazione PRIMA della chiamata** — Zero chiamate API con dati incompleti
6. **Nessun deploy SDI con modifiche collaterali** — Solo fix mirati e verificabili
7. **Non toccare auth/sessioni/UI** senza necessita assoluta

## Documenti creati
- `/app/docs/RCA_FIC_SDI.md` — Root Cause Analysis completa
- `/app/docs/PROCEDURA_FIC_SDI.md` — Procedura operativa token/invio/stato
- `/app/docs/SESSION_POLICY.md` — Policy sessioni

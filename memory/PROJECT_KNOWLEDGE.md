# PROJECT_KNOWLEDGE.md — Norma Facile 2.0
## QUESTO FILE È OBBLIGATORIO. OGNI AGENTE DEVE LEGGERLO PRIMA DI FARE QUALSIASI COSA.

---

## 1. CHI È L'UTENTE

- **Nome**: Francesco Spano
- **Ruolo**: Fabbro / Titolare di Steel Project Design Srls (carpenteria metallica)
- **NON è un programmatore** — Ogni istruzione deve essere chiara, passo passo, senza gergo tecnico
- **Lingua**: Italiano (SEMPRE rispondere in italiano)
- **Email aziendale**: fatture@steelprojectdesign.it

---

## 2. INFRASTRUTTURA — PUNTI FERMI

### 2.1 Ambienti

| Ambiente | URL | Tipo |
|----------|-----|------|
| **PRODUZIONE** | `https://app.1090normafacile.it` | Deploy Emergent — UNICO AMBIENTE DI FRANCESCO |

**NON ESISTONO ALTRI AMBIENTI.** Qualsiasi altro URL (preview, content-engine-86, vercel) è OBSOLETO. Francesco lavora SOLO su `app.1090normafacile.it`.

### 2.2 DATABASE — MongoDB Atlas

- **Cluster**: Cluster0 su MongoDB Atlas (`cluster0.aypz9f1.mongodb.net`)
- **Database**: `normafacile` (63 collezioni)
- **Utente DB**: `spanofranc75_db_user`
- **Network**: 0.0.0.0/0 (accesso da ovunque)
- **Tenant di Francesco**: `ten_1cf1a865bf20`
- **OGNI DEPLOY** deve usare questa connection string Atlas nel Secret `MONGO_URL` e `DB_NAME=normafacile`

### 2.3 Flusso di deploy

```
Sviluppo nel Preview → "Salva su GitHub" → Re-deploy su Emergent → app.1090normafacile.it aggiornato
```

### 2.4 Secrets obbligatori nel deploy Emergent

Questi Secrets DEVONO essere presenti su ogni deploy:
- `MONGO_URL`: connection string Atlas (mongodb+srv://...)
- `DB_NAME`: normafacile
- `REACT_APP_BACKEND_URL`: https://app.1090normafacile.it

### 2.4 Autenticazione

- **Google OAuth** via Emergent-managed auth (NO JWT, NO token)
- Cookie-based sessions
- L'utente ha ESPLICITAMENTE rifiutato JWT in passato — NON proporre mai JWT

### 2.5 Chiavi e Secrets

| Chiave | Dove | Stato |
|--------|------|-------|
| EMERGENT_LLM_KEY | backend/.env | Attiva |
| RESEND_API_KEY | backend/.env | Attiva |
| GOOGLE_CLIENT_ID/SECRET | backend/.env | Attivo |
| FIC_ACCESS_TOKEN | backend/.env | Attivo (FattureInCloud) |
| SDI_API_KEY | backend/.env | Test (vuoto) |
| JWT_SECRET | RIMOSSO in Sprint 1 | Non usare |

---

## 3. COSA È STATO FATTO — CRONOLOGIA

### Sprint 1 — Hardening Sicurezza (26 Marzo 2026) — COMPLETATO
- RBAC: `@require_role()` su 76/89 route files (636 endpoint)
- Audit trail con `tenant_id`
- JWT_SECRET rimosso
- 2 utenti test rimossi
- 28/28 test passati

### Migrazione dati tenant_id (26 Marzo 2026) — COMPLETATO
- Tutti i documenti migrati da `tenant_id: "default"` a `tenant_id: "ten_1cf1a865bf20"` (Francesco)
- 39+ collezioni aggiornate (100 preventivi, 54 fatture, 43 clienti, 14 commesse, 28 DDT, 78 fatture ricevute, ecc.)
- Tenant placeholder "default" rimosso

### Collegamento MongoDB Atlas (26 Marzo 2026) — COMPLETATO
- Backend collegato a MongoDB Atlas (Cluster0)
- Produzione attiva su `app.1090normafacile.it`
- Secrets configurati nel deploy Emergent (MONGO_URL, DB_NAME, REACT_APP_BACKEND_URL)

### Sprint 2 Fase A — Multi-Tenant Fondamenta (26 Marzo 2026) — COMPLETATO
- `services/tenant_service.py`: CRUD tenant + auto-onboarding
- `routes/admin_tenants.py`: API admin
- `services/tenant_counters.py`: Contatori isolati per-tenant
- `security.py`: Auto-creazione tenant al primo login admin
- 15/15 test passati

### Fix Cantiere Sicurezza (26 Marzo 2026) — COMPLETATO
- Pre-compilazione automatica Scheda Cantiere da commessa/cliente/preventivo
- 10/10 test passati

### Precedenti (sessioni prima del 26 Marzo)
- Multi-Tenant Step 1: `tenant_id` aggiunto a tutte le collezioni
- Fix AI Preventivatore: pesi grigliato, conto lavoro, specchiature, ore stimate
- Fix dropdown clienti vuoto
- Fix MigrationWidget che si ripeteva
- Pulizia .gitignore

---

## 4. COSA RESTA DA FARE — BACKLOG PRIORITIZZATO

### P0 — URGENTE
- **Unificare ambienti**: Migrare DB a MongoDB Atlas per persistenza dati
- **Sprint 2 Fase B**: Aggiornamento 27 service files con filtro `tenant_id`
- **Verifica E2E pipeline produttiva**: Preventivo → Commessa → DoP/CE → DDT → Fattura
- **Backfill tenant_id** su documenti esistenti nello staging reale

### P1 — Sprint 2 restante
- Sprint 2 Fase C: Backup scheduler per-tenant, test E2E multi-tenant
- Sprint 2 Fase D: Documentazione SPEC_MULTI_TENANT.md
- Migrazione `team.py` da `team_owner_id` a `tenant_id`
- Rotazione chiavi sensibili (Aruba SDI, FattureInCloud, Resend)

### P2 — Sprint 3-4
- Backup automatico + retention policy
- JSON structured logging
- Admin dashboard tenant (frontend)
- CSRF protection, input sanitization
- Rate limiting per-tenant

### P3 — Futuro
- Stripe integration
- Product Tour
- Portale clienti

---

## 5. REGOLE PER GLI AGENTI — NON IGNORARE

1. **LEGGERE QUESTO FILE** prima di qualsiasi azione
2. **AGGIORNARE QUESTO FILE** ad ogni sessione con le modifiche fatte
3. **Rispondere SEMPRE in italiano**
4. **Non chiedere a Francesco di fare cose tecniche** — guidarlo passo passo con screenshot/istruzioni semplici
5. **Non proporre JWT** — l'app usa cookie sessions via Google OAuth
6. **Non usare `$in` in `$set`** — solo per filtri di lettura
7. **tenant_id** è il nome standard — NON usare organization_id
8. **Il preview ha DB vuoto** — non confonderlo con lo staging reale
9. **"Salva su GitHub"** pusha su branch `main` — Vercel deploya automaticamente il frontend
10. **Per il backend**: serve un "Deploy" su Emergent o Railway

---

## 6. FILE CRITICI

| File | Scopo |
|------|-------|
| `/app/backend/core/rbac.py` | RBAC centralizzato |
| `/app/backend/core/security.py` | Cookie auth + tenant_match + auto-onboarding |
| `/app/backend/services/tenant_service.py` | CRUD tenant |
| `/app/backend/services/tenant_counters.py` | Contatori per-tenant |
| `/app/backend/services/audit_trail.py` | Audit con tenant_id |
| `/app/backend/routes/admin_tenants.py` | API gestione tenant |
| `/app/backend/services/cantieri_sicurezza_service.py` | Pre-fill cantiere da commessa |
| `/app/backend/main.py` | App entry + startup migrations + indexes |
| `/app/memory/PROJECT_KNOWLEDGE.md` | QUESTO FILE — leggere sempre |
| `/app/memory/PRD.md` | Requisiti prodotto |
| `/app/memory/DIAGNOSI_AMMINISTRATIVA.md` | Roadmap governance |

---

## 7. INTEGRAZIONI ESTERNE

| Servizio | SDK/Metodo | Stato |
|----------|-----------|-------|
| OpenAI GPT-4o | `emergentintegrations` + Emergent LLM Key | Attivo (Preventivatore AI) |
| FattureInCloud | REST API + `FIC_ACCESS_TOKEN` | Attivo |
| Resend | REST API + `RESEND_API_KEY` | Attivo (email fatture) |
| Google OAuth | Emergent-managed | Attivo |
| Aruba SDI | REST API (test mode) | Da configurare |

---

**Ultimo aggiornamento**: 26 Marzo 2026 — Sessione Sprint 1 + Sprint 2 Fase A + Foglio Lavoro PDF

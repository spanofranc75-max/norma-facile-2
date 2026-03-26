# Sprint 1 — Checklist Hardening Sicurezza
## NormaFacile 2.0 | Data: 26 Marzo 2026

---

## Completato

### 1. RBAC Enforcement
- [x] `core/rbac.py` — Decoratore `@require_role()` centralizzato
- [x] 76 route files patchati con `@require_role()`
- [x] 636 endpoint ora protetti da controllo ruolo
- [x] Admin bypassa sempre (wildcard)
- [x] Logging RBAC DENIED con user_id, tenant_id, role

**Mapping ruoli applicato:**

| Dominio | Route Files | Ruoli ammessi |
|---------|-------------|---------------|
| Fatturazione | invoices, fatture_ricevute, ddt | admin, amministrazione |
| Costi | cost_control, sal_acconti | admin, amministrazione |
| Clienti | clients | admin, amministrazione, ufficio_tecnico |
| Impostazioni | company, payment_types | admin, amministrazione |
| Preventivi | preventivi, preventivatore | admin, amministrazione, ufficio_tecnico |
| Commesse | commesse, commessa_ops, consegne_ops | admin, amministrazione, ufficio_tecnico, officina |
| Tecnico | cam, fpc, certificazioni, gate_certification, ecc. | admin, ufficio_tecnico |
| Produzione | produzione_ops, diario_produzione, officina | admin, ufficio_tecnico, officina |
| Admin-only | backup, migration, db_cleanup, admin_integrity | admin |
| Audit | activity_log, audits | admin (+ amministrazione per audits) |

**File skippati (13 — motivi legittimi):**
- `auth.py` — endpoint pubblici di autenticazione
- `vendor_api.py` — callback API esterne
- `demo.py` — auth speciale demo mode
- `team.py` — gia con check ruolo
- `content_engine.py` — gia con check ruolo
- `search.py` — accesso ampio necessario
- `onboarding.py` — workflow speciale
- `qrcode_gen.py` — utility
- `commessa_ops.py`, `commessa_ops_common.py`, `montaggio.py`, `officina.py` — non importano get_current_user direttamente

### 2. Audit Trail con tenant_id
- [x] `services/audit_trail.py` aggiornato
- [x] Campo `tenant_id` presente in ogni record audit
- [x] Retrocompatibile (default="default" per utenti senza tenant)

### 3. Cleanup Utenti Test
- [x] Script `migrations/cleanup_test_users.py` creato
- [x] 2 utenti test rimossi: test@normafacile.it, test@test.com
- [x] Sessioni associate cancellate
- [x] Azione loggata nel activity_log

### 4. Rimozione JWT_SECRET
- [x] `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes` rimossi da `core/config.py`
- [x] Check JWT_SECRET rimosso da `main.py` lifespan
- [x] L'app usa esclusivamente cookie sessions

### 5. Verifiche
- [x] Backend si avvia senza errori
- [x] Health check: 200 OK
- [x] Endpoint protetti: 401 senza auth
- [x] 49 indici MongoDB confermati

---

## Procedura di Rollback

In caso di problemi post-deploy:

1. **Rollback rapido** (Emergent): Usare la funzione "Rollback" nella UI di Emergent per tornare al checkpoint pre-Sprint 1
2. **Rollback manuale DB**: Restore da `/app/backend/uploads/sprint1_backup/`
3. **Rollback RBAC solo**: Rimuovere `from core.rbac import require_role` e ripristinare `Depends(get_current_user)` nei route files

---

## Test Scenarios da Verificare

| # | Test | Risultato Atteso |
|---|------|------------------|
| TS1 | Admin chiama GET /api/invoices/ | 200 OK |
| TS2 | Utente senza auth chiama GET /api/invoices/ | 401 |
| TS3 | Utente `officina` chiama GET /api/invoices/ | 403 |
| TS4 | Utente `amministrazione` chiama GET /api/invoices/ | 200 |
| TS5 | Utente `officina` chiama GET /api/commesse/ | 200 (ha accesso) |
| TS6 | Nuovo audit log contiene tenant_id | Verifica campo presente |
| TS7 | JWT_SECRET non piu in config | grep conferma 0 occorrenze |
| TS8 | Utenti test rimossi | 0 utenti nel DB |

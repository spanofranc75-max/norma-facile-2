# NormaFacile 2.0 — PRD (Product Requirements Document)

## Problema originale
Sistema operativo verticale per carpenteria metallica / EN 1090 / EN 13241 / sicurezza cantiere / documentazione / committenza. Copilota tecno-normativo-operativo.

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI (porta 3000)
- **Backend**: FastAPI + Motor (porta 8001)
- **Database**: MongoDB (100 collezioni)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **Email**: Resend
- **Storage**: Object Storage S3
- **Auth**: Emergent Google OAuth + JWT

## Moduli implementati (18)
1. Preventivi
2. Istruttoria AI
3. Segmentazione normativa
4. Commessa pre-istruita
5. Commessa madre / rami normativi / emissioni documentali
6. Evidence Gate per emissione
7. Sicurezza / Scheda cantiere
8. Motore AI Sicurezza
9. Generazione POS DOCX
10. Pacchetti Documentali intelligenti
11. Invio email documenti
12. Verifica Committenza / Contratti
13. Registro Obblighi Commessa (8 fonti)
14. Dashboard Cantiere / Commessa multilivello
15. Audit Log (16 moduli)
16. Profili documentali per committente
17. Notifiche intelligenti in-app
18. Repository documentale interno alla commessa

## Stato attuale — Post-Audit (2026-03-23)

### Audit completato
Prodotti 7 report di audit approfondito:
- `MASTER_AUDIT_REPORT.md` — Executive summary
- `CODEBASE_INVENTORY.md` — Inventario 100 collezioni, 78 routes, 58 services
- `FLOW_GAPS_REPORT.md` — 7 flussi analizzati, mappa collegamenti
- `TECH_DEBT_BACKLOG.md` — 15 issue prioritizzate
- `UX_AND_PRODUCT_GAPS.md` — 12 gap UX/prodotto
- `CLEANUP_LIST.md` — Dead code, directory, collezioni da eliminare
- `COMPLIANCE_RISKS.md` — 10 rischi sicurezza/GDPR/AI

### Finding critici
1. ~~**BLOCKER**: Indici MongoDB non creati (lifespan/on_event conflict)~~ **RISOLTO (2026-03-23)**
2. ~~**Alta**: Router sicurezza duplicato in main.py~~ **RISOLTO (2026-03-23)**
3. ~~**Alta**: Nessun rate limiting~~ **RISOLTO (2026-03-23)** — 15 endpoint AI protetti (10/min per user)
4. **Alta**: ~3.200 righe dead code
5. **Alta**: 78/100 collezioni senza indici (12 critiche ora indicizzate con 24 indici)

### Fix completati (2026-03-23)
- **TD-001 RISOLTO**: Spostato startup da `on_event("startup")` a `lifespan()`. 24 indici creati su 12 collezioni critiche (9 unique + 15 lookup). Indici idempotenti — safe ad ogni restart.
- **TD-002 RISOLTO**: Rimosso import + registrazione duplicata `sicurezza_router` da main.py.
- **TD-005 RISOLTO**: Rate limiting su 15 endpoint AI (10/min per user, 5/min batch). slowapi con key_func basata su user_id.
- **TD-009 RISOLTO**: Error handling su asyncio.create_task() — 5 fire-and-forget wrappati con safe_background_task + crash callback sullo scheduler.
- **TD-010 RISOLTO**: Filtro user_id aggiunto su audits.py, instruments.py, welders.py, quality_hub.py, verbale_posa.py, montaggio.py. Protezione multi-tenant su read/write/delete.
- **Endpoint /api/health/indexes**: Nuovo endpoint per verifica runtime degli indici critici.

### Data Integrity (2026-03-23)
- **Check script**: `/app/backend/scripts/data_integrity_check.py` — verifica 6 aree (duplicati, ref rotti, stati, campi, snapshot, legacy)
- **Fix script**: `/app/backend/scripts/data_integrity_fix.py` — fix batch a-e
- **Risultato finale**: 0 CRITICAL, 0 WARNING su 20 check
- **Fix applicati**:
  - Backfill `user_id` su 4 non_conformities legacy
  - Eliminati 4 commesse_normative + 24 obblighi_commessa orfani (backup salvato)
  - Eliminati 1 instrument + 1 welder corrotti (backup salvato)
  - Eliminati 21 pacchetti_documentali di test senza commessa_id (backup salvato)
  - Ricalcolati 24 summary pacchetti documentali
  - Regola `documenti_archivio`: commessa_id opzionale per entity_type azienda/persona/mezzo
### Sicurezza Credenziali CR-001/002 (2026-03-23)
- **JWT_SECRET**: rimosso default fallback pericoloso, generato secret crittografico 86 char (secrets.token_urlsafe(64)), startup check con fail fast se mancante o < 32 char
- **Chiave LLM unificata**: allineato `committenza_analysis_service.py` a `EMERGENT_LLM_KEY`, rimosso `EMERGENT_API_KEY` duplicato da .env
- **Indici auth**: `uq_session_token` e `uq_download_token` (unique) + expiry indexes
- **Cleanup periodico**: scheduler pulisce sessioni/token scaduti ogni 24h
- **Startup security checks**: verifica JWT_SECRET, EMERGENT_LLM_KEY, RESEND_API_KEY all'avvio
- **Scoperta**: `download_tokens` NON è zombie — attivamente usata da `create_download_token()`
- **Nota**: `user_sessions` aveva già TTL index (`idx_expires`) — auto-cleanup MongoDB nativo

### Scoperte importanti dall'audit
- Le 6 route "orfane" nel report di audit erano ERRATE — sono sub-moduli di `commessa_ops.py`, attivamente registrati
- Le 6 collezioni "zombie" nel report erano ERRATE — tutte referenziate dal codice attivo
- Solo 2 vere collezioni zombie: `download_tokens`, `sessions`
- Il vero dead code confermato era: 2 service (aruba_sdi, pos_pdf_service), 5 file root legacy, 158 import inutilizzati

### Backlog prioritizzato (in attesa approvazione utente)
- TD-001 a TD-015: Tech debt (TECH_DEBT_BACKLOG.md)
- UX-001 a UX-012: Gap UX (UX_AND_PRODUCT_GAPS.md)
- CR-001 a CR-010: Compliance (COMPLIANCE_RISKS.md)

## Task ON HOLD (fino ad approvazione post-audit)
- Email automatiche selettive
- Monetizzazione / Stripe
- Stability Guard AI
- Multi-Tenant Architecture
- Fix warning minori

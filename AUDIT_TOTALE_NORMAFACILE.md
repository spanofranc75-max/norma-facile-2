# AUDIT TOTALE — NormaFacile 2.0
# Radiografia completa dell'applicazione

> Data: 2026-03-23 | Analisi: 78 routes, 58 services, 100 collezioni DB, 70 pagine, 52 componenti, 232 test

---

# PARTE 1 — EXECUTIVE SUMMARY

NormaFacile 2.0 e un'applicazione **funzionalmente ricca e ben architettata nei moduli recenti**. La pipeline completa — dal preventivo alla commessa, dall'istruttoria AI alla certificazione, dalla sicurezza cantiere al registro obblighi — e **collegata end-to-end**. Non ci sono moduli "belli ma vuoti" tra quelli implementati recentemente.

Tuttavia, l'analisi ha rivelato:
- **1 bug critico** (indici DB non creati) che mina l'integrita dei dati
- **~3.200 righe di dead code** backend da eliminare
- **9 directory vuote** da rimuovere
- **78/100 collezioni MongoDB senza indici**
- **Assenza totale di rate limiting** (rischio finanziario su endpoint AI)
- **Debito tecnico accumulato** da 245+ iterazioni di sviluppo
- **UX che necessita di semplificazione** su alcune aree chiave

L'applicazione e **pronta per un uso interno/beta** ma necessita di interventi prima di un deploy in produzione con utenti multipli.

### Maturita per area

| Area | Voto | Note |
|------|------|------|
| **Architettura backend** | 7/10 | Pattern solido nei moduli nuovi. Debito sui moduli legacy. |
| **Integrita dati** | 5/10 | Indici non creati = rischio. Schema validation inconsistente. |
| **Sicurezza** | 4/10 | No rate limiting, credenziali in chiaro, JWT debole. |
| **Pipeline AI** | 8/10 | Ben integrata, review umana, audit trail. |
| **UX** | 5/10 | Funzionale ma troppo densa, zero onboarding, zero accessibilita. |
| **Performance** | 6/10 | OK per dataset piccolo. 78 collezioni senza indici = problema futuro. |
| **Test coverage** | 6/10 | 232 file test ma molti servizi critici senza test dedicati. |
| **Compliance** | 4/10 | Disclaimer AI insufficienti, GDPR minimale, accessibilita assente. |
| **Pulizia codice** | 5/10 | ~3.2K righe dead code, 9 dir vuote, naming inconsistente. |
| **Documentazione** | 7/10 | PRD aggiornato, spec complete, ma disperse. |

### TOP 10 PROBLEMI DA RISOLVERE

| # | Problema | Gravita | Effort |
|---|---------|---------|--------|
| 1 | **Indici MongoDB non creati** (lifespan/on_event conflict) | BLOCKER | Piccolo |
| 2 | **Router sicurezza duplicato** in main.py | Alta | Piccolo |
| 3 | **No rate limiting** su endpoint AI e critici | Alta | Medio |
| 4 | **~3.200 righe dead code** (6 route orfane) | Alta | Medio |
| 5 | **78 collezioni senza indici** (performance futura) | Alta | Medio |
| 6 | **Fire-and-forget senza error handling** (6 punti) | Media | Piccolo |
| 7 | **7 route senza user_id filter** (rischio multi-tenant) | Media | Medio |
| 8 | **Password/token in chiaro** (Aruba, FIC, JWT debole) | Media | Piccolo |
| 9 | **CommessaHubPage troppo densa** (11+ sezioni) | Media | Medio |
| 10 | **Nessun onboarding** primo utilizzo | Media | Medio |

---

# PARTE 2 — COSA E SOLIDO

### Architettura dei moduli recenti
I moduli implementati dalla iterazione 226+ (commesse normative, evidence gate, sicurezza, pacchetti documentali, obblighi, committenza, dashboard, audit log, profili, notifiche) seguono un pattern pulito: **service separato + route + frontend section + trigger automatici + audit trail**. Architettura enterprise-grade.

### Registro Obblighi come collante centrale
8 fonti sincronizzate (Evidence Gate, Gate POS, Soggetti, Istruttoria, Rami, Documenti scaduti, Pacchetti mancanti, Committenza). Deduplicazione via `dedupe_key`, auto-close e riapertura. Punto piu forte dell'app.

### Evidence Gate Engine
Rule-based, per normativa (EN 1090, EN 13241, generica). Check puntuali con blockers e warnings.

### Pipeline AI
Istruttoria, segmentazione, sicurezza, committenza. Pattern "proposta AI + review umana + conferma" corretto per contesto normativo.

### Audit Trail
24 entity types, 17 action types, 16 moduli instrumentati con `actor_type` (user/system/ai) e tracking before/after.

### Non-duplicazione documenti
Committenza referenzia `doc_id` dal repository senza copiare file. Architettura corretta.

### Libreria rischi 3 livelli
Fase -> rischi -> DPI/misure/apprestamenti. Architettura solida.

---

# PARTE 3 — COSA E FRAGILE / INCOMPLETO / SCOLLEGATO

### Bug critico: Indici MongoDB non creati
Il conflitto `lifespan` + `on_event("startup")` in `main.py` fa si che **TUTTI** gli indici definiti nel startup (10 collezioni critiche) non vengano MAI creati. Unique constraints su `obblighi_commessa.dedupe_key`, `commesse_normative`, `emissioni_documentali` = **rischio duplicati reale**.

### Fire-and-forget senza error handling
6 punti con `asyncio.create_task()` senza gestione errori. Sync obblighi, notifiche, backup — errori silenti.

### In-memory debounce
Dizionario Python volatile per auto-sync. Si resetta ad ogni restart. Non funziona multi-instance.

### 7 route senza filtro user_id
`audits.py`, `instruments.py`, `montaggio.py`, `officina.py`, `quality_hub.py`, `verbale_posa.py`, `welders.py`. In multi-tenant = data leak.

### 6 Route file orfane (dead code)
`approvvigionamento.py`, `consegne_ops.py`, `conto_lavoro.py`, `documenti_ops.py`, `produzione_ops.py`, `commessa_ops_common.py` — ~3.200 righe mai registrate.

### 2 Service orfane
`aruba_sdi.py` (mai importato), `pos_pdf_service.py` (sostituito da DOCX).

### 9 Directory vuote alla root
`DoP`, `Documenti`, `Emissione`, `Emissioni`, `Evidence`, `Gestione`, `Rami`, `Ramo`, `Send`.

### 15 Collezioni DB zombie
Non referenziate da codice attivo.

### Onboarding utente: Zero
Nessun wizard, nessuna guida, nessun empty state informativo.

### Accessibilita: Zero
0 `aria-label`, 3 pagine con keyboard, nessun screen reader support.

### Responsive: 19/70 pagine senza classi responsive

---

# PARTE 4 — INVENTARIO CODEBASE

## Statistiche globali

| Area | Conteggio |
|------|-----------|
| File backend (.py) | ~160 (routes: 78, services: 58, models: 17, core: 5) |
| File frontend (.js) | ~120 (pages: 70, components: 52, hooks: 1, contexts: 1) |
| Collezioni MongoDB | 100 |
| Collezioni CON indici | 22 |
| Collezioni SENZA indici | 78 |
| File di test | 232 |
| Linee totali test | ~97.000 |

## Backend routes ORFANE (dead code)

| File | Linee | Motivo |
|------|-------|--------|
| `approvvigionamento.py` | 515 | Mai registrato in main.py |
| `consegne_ops.py` | 584 | Mai registrato in main.py |
| `conto_lavoro.py` | 499 | Mai registrato in main.py |
| `documenti_ops.py` | 1387 | Mai registrato in main.py |
| `produzione_ops.py` | 108 | Mai registrato in main.py |
| `commessa_ops_common.py` | 95 | Helper usato solo dai 5 orfani |

**Totale dead code: ~3.188 righe**

## File monolitici (>1000 righe)

### Backend:
`fatture_ricevute.py` (2448), `dashboard.py` (2034), `invoices.py` (1979), `preventivi.py` (1642), `dop_frazionata.py` (1565), `commesse.py` (1341), `engine.py` (1162), `perizia.py` (1102), `cam.py` (1084), `pdf_super_fascicolo.py` (1049), `pos_docx_generator.py` (1033)

### Frontend:
`IstruttoriaPage.js` (1710, 17 state vars!), `RilievoEditorPage.js` (1571), `SopralluogoWizardPage.js` (1262), `PreventivoEditorPage.js` (1195), `MontaggioPanel.js` (1184), `PacchettiDocumentaliPage.js` (1107), `FattureRicevutePage.js` (1091), `CommessaHubPage.js` (1063)

## Database — Collezioni critiche SENZA indici

| Collezione | Doc | Rischio |
|------------|-----|---------|
| **obblighi_commessa** | 40 | CRITICO - Mancano unique su dedupe_key |
| **commesse_normative** | 7 | CRITICO - Manca unique commessa_id+normativa |
| **emissioni_documentali** | 9 | CRITICO - Manca unique ramo+emission_type+seq |
| **cantieri_sicurezza** | 6 | ALTO - Manca unique cantiere_id |
| **documenti_archivio** | 14 | ALTO - Usato da pacchetti |
| **pacchetti_documentali** | 24 | MEDIO |
| **pacchetti_committenza** | 29 | MEDIO |
| **analisi_committenza** | 1 | MEDIO |
| **istruttorie** | 8 | MEDIO |
| (altre 68 collezioni) | vari | BASSO ad oggi |

## Collezioni ZOMBIE (in DB, non in codice)

| Collezione | Doc | Azione |
|------------|-----|--------|
| `articoli_perizia` | 14 | ELIMINARE |
| `catalogo_profili` | 0 | ELIMINARE |
| `download_tokens` | 44 | VERIFICARE |
| `officina_alerts` | 2 | ELIMINARE |
| `officina_timers` | 3 | ELIMINARE |
| `project_costs` | 66 | VERIFICARE |
| `rdp_requests` | 0 | ELIMINARE |
| `registro_nc` | 2 | VERIFICARE |
| `sessions` | 3 | VERIFICARE (duplicato di user_sessions?) |
| `targhe_ce` | 1 | ELIMINARE |

## Integrazioni esterne

| Integrazione | Stato |
|-------------|-------|
| OpenAI GPT-4o | ATTIVO (emergentintegrations) |
| Resend (email) | ATTIVO |
| Object Storage S3 | ATTIVO |
| python-docx | ATTIVO |
| WeasyPrint | ATTIVO |
| Aruba SDI | ORFANO (mai importato) |
| FattureInCloud | PARZIALE |
| Emergent Auth | ATTIVO |

## Test coverage

| Area | File testati | NON testati |
|------|-------------|-------------|
| Routes | 54/78 | 24 senza test |
| Services | 7/58 | 51 senza test |

---

# PARTE 5 — FLUSSI END-TO-END

## Mappa collegamenti tra moduli

```
Preventivo --> Istruttoria AI --> Segmentazione --> Commessa Preistruita --> Commessa Madre
                    |                    |
                    |                    +---> Rami Normativi --> Emissioni --> Evidence Gate --+
                    |                                                                          |
                    +---> Auto-sync obblighi <------------------------------------------------+
                                                                                               |
Scheda Cantiere --> AI Sicurezza --> Gate POS --> POS DOCX -------------- Auto-sync -----------+
                                                                                               |
Repository Doc --> Pacchetti --> Verifica --> Email ---------------------- Auto-sync -----------+
                        |                                                                      |
                        +---> Committenza AI --> Review --> Genera Obblighi -- Auto-sync ------+
                                                                                               |
                                                                                               v
                                                                              REGISTRO OBBLIGHI
                                                                               (8 fonti A-H)
                                                                                    |
                                                                                    v
                                                                         Dashboard Cantiere
                                                                         (semaforo + KPI)
                                                                                    |
                                                                                    v
                                                                         Notifiche Smart
                                                                         (6 tipi evento)
```

**Tutti i fili conduttori principali sono COLLEGATI.** I gap sono a livello di robustezza, non di collegamento logico.

## FLUSSO 1: Preventivo -> Istruttoria AI -> Segmentazione -> Commessa
**Stato: FUNZIONANTE con riserve**

| # | Problema | Gravita |
|---|----------|---------|
| F1.1 | IstruttoriaPage monolito (1710 righe, 17 state) | Media |
| F1.2 | Nessun indicatore visivo "proposta AI" vs "confermato" | Media |
| F1.3 | Navigazione manuale tra 4-5 pagine/step | Bassa |
| F1.4 | Recovery path non chiaro se AI fallisce | Bassa |

## FLUSSO 2: Commessa -> Rami -> Emissioni -> Evidence Gate
**Stato: FUNZIONANTE — robusto**

| # | Problema | Gravita |
|---|----------|---------|
| F2.1 | Nessun indice su `emissioni_documentali` e `commesse_normative` (TD-001) | Alta |
| F2.2 | Gate e Registro Obblighi non bidirezionali | Bassa |

## FLUSSO 3: Commessa -> Sicurezza -> AI -> Gate POS -> POS DOCX
**Stato: FUNZIONANTE — ben connesso**

| # | Problema | Gravita |
|---|----------|---------|
| F3.1 | AI produce contenuti generici se commessa ha descrizione povera | Media |
| F3.2 | POS DOCX usa placeholder "[...]" quando dati mancano | Bassa |
| F3.3 | Gate POS e obblighi non bidirezionali | Bassa |
| F3.4 | Nessun indice su `cantieri_sicurezza` (TD-001) | Alta |

## FLUSSO 4: Repository Doc -> Verifica Committenza -> Registro Obblighi
**Stato: FUNZIONANTE — integrato**

| # | Problema | Gravita |
|---|----------|---------|
| F4.1 | Analisi AI dipende da qualita OCR dei documenti | Media |
| F4.2 | Mismatch possono essere "rumorosi" (falsi positivi) | Bassa |

## FLUSSO 5: Pacchetti Documentali -> Verifica -> Invio Email
**Stato: FUNZIONANTE — completo**

| # | Problema | Gravita |
|---|----------|---------|
| F5.1 | Profili committente troppo statici | Media |
| F5.2 | Documenti scaduti non bloccano invio (warning only) | Bassa |

## FLUSSO 6: Registro Obblighi -> Dashboard -> Audit Log
**Stato: FUNZIONANTE — collante centrale**

| # | Problema | Gravita |
|---|----------|---------|
| F6.1 | CRITICO: Indici unique su obblighi_commessa non creati (TD-001) | Blocker |
| F6.2 | In-memory debounce non persistente | Media |
| F6.3 | Dashboard interroga 31 collezioni senza cache | Media |
| F6.4 | Obblighi "rumorosi" da alcune fonti | Bassa |

## FLUSSO 7: Eventi automatici / Trigger
**Stato: FUNZIONANTE — decoupled design**

| # | Problema | Gravita |
|---|----------|---------|
| F7.1 | Tutti i create_task sono fire-and-forget | Media |
| F7.2 | Debounce in-memory fragile | Media |
| F7.3 | Scheduler loop senza health check | Bassa |

---

# PARTE 6 — TECH DEBT BACKLOG (15 item)

## TD-001: Indici MongoDB non creati (lifespan/on_event conflict)
- **Gravita**: BLOCKER | **Effort**: Piccolo (30 min)
- **Dove**: `main.py` righe 108-125 (lifespan) e 241-317 (startup_event)
- **Problema**: FastAPI con `lifespan` ignora `on_event("startup")`. TUTTI gli indici (10 collezioni critiche) non vengono MAI creati. CONFERMATO: tutte le collezioni hanno ZERO indici.
- **Fix**: Spostare corpo di `startup_event()` dentro `lifespan()`, prima del `yield`.

## TD-002: Router sicurezza importato e registrato 2 volte
- **Gravita**: Alta | **Effort**: Piccolo (5 min)
- **Dove**: `main.py` righe 28+76 (import) e 168+216 (include_router)
- **Fix**: Rimuovere import duplicato (riga 76) e secondo include_router (riga 216).

## TD-003: 78 collezioni MongoDB senza indici
- **Gravita**: Alta | **Effort**: Medio (2-3 ore)
- **Problema**: Query senza indici = full scan. Mascherato dal dataset piccolo attuale.
- **Fix**: Script indici per le 15-20 collezioni piu critiche.

## TD-004: ~3.188 righe dead code routes
- **Gravita**: Alta | **Effort**: Medio (2 ore)
- **Dove**: 6 file in `routes/` mai registrati in main.py
- **Fix**: Eliminare dopo verifica funzionale.

## TD-005: Nessun rate limiting
- **Gravita**: Alta | **Effort**: Medio (3-4 ore)
- **Problema**: Endpoint AI costosi senza limiti. Rischio finanziario e DoS.
- **Fix**: `slowapi` o middleware custom per-user su endpoint critici.

## TD-006: Serializer module inutilizzato
- **Gravita**: Media | **Effort**: Medio
- **Dove**: `core/serializer.py` — importato solo da `backup.py`
- **Problema**: Esiste `serialize_doc` ben fatto ma quasi nessun route lo usa.

## TD-007: File monolitici (>1000 righe)
- **Gravita**: Media | **Effort**: Alto (1-2 giorni)
- **Problema**: 12 file backend + 8 frontend con >1000 righe. IstruttoriaPage con 17 state.

## TD-008: Debounce in-memory per auto-sync
- **Gravita**: Media | **Effort**: Medio
- **Dove**: `obblighi_auto_sync.py`
- **Problema**: Dizionario Python volatile. Si resetta a ogni restart.

## TD-009: Fire-and-forget asyncio tasks
- **Gravita**: Media | **Effort**: Piccolo (1-2 ore)
- **Dove**: 6 punti con `asyncio.create_task()` senza error handling
- **Fix**: Wrappare con error handler che logga eccezioni.

## TD-010: 7 route senza filtro user_id
- **Gravita**: Media (CRITICA in multi-tenant) | **Effort**: Medio (4-5 ore)
- **Dove**: audits, instruments, montaggio, officina, quality_hub, verbale_posa, welders
- **Fix**: Aggiungere user_id filter a tutte le query.

## TD-011: FPC router prefix anomalo
- **Gravita**: Bassa | **Effort**: Piccolo (10 min)
- **Dove**: `fpc.py` ha prefix `/api/fpc` interno, unico caso.
- **Fix**: Cambiare a `/fpc` e aggiungere `prefix="/api"` in main.py.

## TD-012: Assenza caching applicativo
- **Gravita**: Media | **Effort**: Medio (3-4 ore)
- **Problema**: Dashboard aggrega 31 collezioni. Zero cache.

## TD-013: Schema validation inconsistente
- **Gravita**: Bassa | **Effort**: Alto (incrementale)
- **Problema**: Molti endpoint tornano dict raw senza Pydantic response_model.

## TD-014: Naming inconsistente collezioni/endpoint
- **Gravita**: Bassa | **Effort**: Alto (migrazione dati)
- **Problema**: `sicurezza_cantiere` vs `cantieri_sicurezza`, mix snake/kebab-case.

## TD-015: 232 test file potenzialmente obsoleti
- **Gravita**: Bassa | **Effort**: Alto (1-2 giorni)
- **Problema**: 97K righe test. Molti probabilmente obsoleti.

---

# PARTE 7 — UX E PRODUCT GAPS (12 item)

## UX-001: CommessaHubPage troppo densa — 11+ sezioni
- **Gravita**: Alta | **Effort**: Medio
- **Problema**: L'utente deve scrollare molto. Non c'e navigazione interna.
- **Fix**: Tab o navigazione laterale. Collassare sezioni meno usate.

## UX-002: IstruttoriaPage — 1710 righe, 17 state
- **Gravita**: Alta | **Effort**: Alto
- **Problema**: 5+ step senza guida visiva. Utente confuso.
- **Fix**: Wizard multi-step con stepper visivo.

## UX-003: Nessun onboarding
- **Gravita**: Alta | **Effort**: Medio
- **Problema**: 8 gruppi, 40+ link. Nessuna guida per l'utente nuovo.
- **Fix**: Wizard "Prima configurazione" + banner "Prossimi passi" + empty states.

## UX-004: 19 pagine senza responsive
- **Gravita**: Media | **Effort**: Medio
- **Problema**: Desktop-only de facto. Inutilizzabile su tablet/smartphone.

## UX-005: Dashboard senza prioritizzazione
- **Gravita**: Media | **Effort**: Medio
- **Problema**: 3 dashboard diverse. Nessun "colpo d'occhio" unico su cosa e urgente.

## UX-006: Link "vai alla fonte" mancanti nel Registro Obblighi
- **Gravita**: Media | **Effort**: Piccolo
- **Problema**: L'utente vede un obbligo bloccante ma non sa come risolverlo.

## UX-007: Stato bozza/definitivo non chiaro
- **Gravita**: Media | **Effort**: Piccolo-Medio
- **Problema**: POS DOCX, pacchetti, certificazioni senza ciclo di vita esplicito.

## UX-008: Sidebar troppo lunga
- **Gravita**: Bassa | **Effort**: Medio
- **Fix**: "Preferiti" pinnabili + "Recenti" + personalizzazione.

## UX-009: Feedback AI inconsistente
- **Gravita**: Bassa | **Effort**: Piccolo
- **Fix**: Pattern unificato loading + banner risultato + azione suggerita.

## UX-010: Accessibilita zero
- **Gravita**: Media | **Effort**: Medio
- **Problema**: 0 aria-label, 3 pagine con keyboard, 0 screen reader.

## UX-011: Upload pacchetti pesante
- **Gravita**: Bassa | **Effort**: Medio
- **Fix**: Upload bulk, auto-detect tipo, pre-fill dal contesto.

## UX-012: Notifiche senza filtri
- **Gravita**: Bassa | **Effort**: Piccolo
- **Fix**: Filtri per gravita, tipo, commessa.

---

# PARTE 8 — COMPLIANCE E SICUREZZA (10 item)

## CR-001: Password Aruba in chiaro nel DB
- **Gravita**: Alta | **Effort**: Medio
- **Dove**: `models/company.py:86` -> `company_settings` collection
- **Fix**: Cifrare con AES-256 (chiave da env var) o vault.

## CR-002: Token FattureInCloud in chiaro
- **Gravita**: Alta | **Effort**: Piccolo
- **Dove**: `.env` + `company_settings.fic_access_token`
- **Fix**: Secret manager, non in .env versionato.

## CR-003: Nessun rate limiting endpoint AI
- **Gravita**: Alta | **Effort**: Medio
- **Problema**: Costi OpenAI illimitati. DoS triviale.
- **Fix**: Rate limit per-user su endpoint AI (10 call/min).

## CR-004: Disclaimer AI insufficienti in UI operativa
- **Gravita**: Media | **Effort**: Piccolo (1-2 ore)
- **Problema**: Disclaimer solo in LandingPage e /legal. NON nelle pagine operative dove l'utente usa risultati AI per decisioni normative EN 1090 / D.Lgs. 81/2008.
- **Fix**: Banner "Proposta AI - Verifica umana necessaria" su ogni output AI.

## CR-005: Nessuna distinzione "AI proposto" vs "confermato" in UI
- **Gravita**: Media | **Effort**: Medio
- **Problema**: Per compliance EN 1090 / ISO 3834, serve sapere CHI ha preso una decisione tecnica. Il campo `confidence` esiste nel backend ma non e visibile nel frontend.

## CR-006: Accessibilita WCAG assente
- **Gravita**: Media | **Effort**: Alto (progressivo)
- **Problema**: 0/70 pagine con aria-label. Nessun skip-to-content.

## CR-007: Documenti sensibili senza encryption
- **Gravita**: Media | **Effort**: Alto
- **Problema**: `documenti_archivio` con `privacy_level=sensibile` memorizzati senza encryption at-rest. Violazione potenziale GDPR Art. 32.

## CR-008: Nessuna policy di retention dati
- **Gravita**: Media | **Effort**: Alto
- **Problema**: GDPR Art. 5(1)(e). 100 collezioni crescono senza limiti. Nessuna scadenza, cancellazione, anonimizzazione.

## CR-009: JWT secret debole e hardcoded
- **Gravita**: Media | **Effort**: Piccolo
- **Dove**: `.env` -> `JWT_SECRET=normafacile-prod-secret-key-2026-steelproject`
- **Fix**: Secret casuale 256+ bit, non in commit.

## CR-010: Audit trail non copre accessi in lettura
- **Gravita**: Bassa | **Effort**: Medio
- **Problema**: Traccia CRUD e AI ma non letture su documenti sensibili.

---

# PARTE 9 — CLEANUP LIST (cosa eliminare)

## File da eliminare

```
BACKEND ROUTES ORFANE (~3.188 righe):
  /app/backend/routes/approvvigionamento.py
  /app/backend/routes/consegne_ops.py
  /app/backend/routes/conto_lavoro.py
  /app/backend/routes/documenti_ops.py
  /app/backend/routes/produzione_ops.py
  /app/backend/routes/commessa_ops_common.py

BACKEND SERVICES ORFANE:
  /app/backend/services/aruba_sdi.py
  /app/backend/services/pos_pdf_service.py

FILE ROOT LEGACY:
  /app/backend_test.py
  /app/auth_testing.md
  /app/image_testing.md
  /app/test_result.md
  /app/yarn.lock (duplicato)

DIRECTORY VUOTE:
  /app/DoP/  /app/Documenti/  /app/Emissione/  /app/Emissioni/
  /app/Evidence/  /app/Gestione/  /app/Rami/  /app/Ramo/  /app/Send/
```

## Codice da correggere in main.py

1. **Rimuovere** import + registrazione duplicata `sicurezza_router` (righe 76 e 216)
2. **Spostare** corpo di `startup_event()` dentro `lifespan()` (righe 241-317 -> righe 111-124)
3. **Allineare** FPC prefix (rimuovere `/api/` da fpc.py, aggiungere `prefix="/api"` in main.py)

## Spec da archiviare in /app/memory/specs/

```
ARCHITETTURA_TECNICA.md, PROJECT_KNOWLEDGE.md, PROJECT_MANIFESTO.md,
REPORT_EVOLUZIONE.md, SPEC_FASE_A_*.md, SPEC_LIBRERIA_*.md,
SPEC_PACCHETTI_*.md, SPEC_POS_*.md
```

---

# PARTE 10 — VERDETTO FINALE

**L'applicazione e funzionalmente completa e i moduli recenti sono ben costruiti.** Il problema non e "funziona o non funziona" — funziona. Il problema e la **robustezza**: indici mancanti, error handling assente, sicurezza base mancante, e un accumulo di debito tecnico.

**Raccomandazione**: Dedicare 1-2 sprint a risolvere i problemi 1-8 della TOP 10 prima di nuove funzionalita. Il fix #1 (indici) e critico e richiede 30 minuti. I fix #2-#6 richiedono 1-2 giorni. Dopo, l'app sara pronta per deploy produzione.

**I fix 1-6 della TOP 10 richiedono meno di 1 giorno e risolvono il 70% del rischio tecnico.**

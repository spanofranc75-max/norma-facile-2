# MASTER AUDIT REPORT — NormaFacile 2.0

> Executive Summary — Radiografia totale dell'applicazione
> Data: 2026-03-23

---

## 1. EXECUTIVE SUMMARY

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

---

## 2. COSA E SOLIDO

### Architettura dei moduli recenti
I moduli implementati dalla iterazione 226+ (commesse normative, evidence gate, sicurezza, pacchetti documentali, obblighi, committenza, dashboard, audit log, profili, notifiche) seguono un pattern pulito: **service separato + route + frontend section + trigger automatici + audit trail**. Questa e un'architettura enterprise-grade.

### Registro Obblighi come collante centrale
Il Registro Obblighi con 8 fonti sincronizzate (Evidence Gate, Gate POS, Soggetti, Istruttoria, Rami, Documenti scaduti, Pacchetti mancanti, Committenza) e il punto piu forte dell'applicazione. Il meccanismo di deduplicazione, auto-close e riapertura e sofisticato e funzionante.

### Evidence Gate Engine
Rule-based, ben organizzato per normativa (EN 1090, EN 13241, generica). Check puntuali con blockers e warnings. Buona separazione delle responsabilita.

### Pipeline AI
L'integrazione AI (istruttoria, segmentazione, sicurezza, committenza) aggiunge valore reale. L'architettura con "proposta AI + review umana + conferma" e corretta per un contesto normativo.

### Audit Trail
24 entity types, 17 action types, 16 moduli instrumentati con `actor_type` (user/system/ai) e tracking before/after. Copertura buona.

### Non-duplicazione documenti
Committenza referenzia `doc_id` dal repository senza copiare file. Pacchetti verificano lo stato dall'archivio. Architettura corretta.

---

## 3. COSA E FRAGILE

### Bug critico: Indici MongoDB non creati (TD-001)
Il conflitto `lifespan` + `on_event("startup")` in `main.py` fa si che **TUTTI** gli indici definiti nel startup (10 collezioni critiche) non vengano MAI creati. Questo include unique constraints su `obblighi_commessa.dedupe_key`, `commesse_normative`, `emissioni_documentali`. **Il rischio di duplicati e reale.**

### Fire-and-forget senza error handling (TD-009)
6 punti nel codice usano `asyncio.create_task()` senza gestione errori. Se il sync obblighi fallisce, se una notifica non viene creata, se il backup non riesce — nessuno lo sa. Gli errori vengono silenziosamente persi.

### In-memory debounce (TD-008)
Il debounce per l'auto-sync obblighi usa un dizionario Python in-memory. Si resetta ad ogni restart del server. Non funzionera in deploy multi-instance.

### 7 route senza filtro user_id (TD-010)
`audits.py`, `instruments.py`, `montaggio.py`, `officina.py`, `quality_hub.py`, `verbale_posa.py`, `welders.py` eseguono query MongoDB senza filtrare per `user_id`. In single-tenant non crea problemi visibili, ma in multi-tenant espone dati di altri utenti.

---

## 4. COSA E INCOMPLETO

### Onboarding utente
Zero. Nessun wizard primo utilizzo, nessuna guida, nessun empty state informativo. Un utente nuovo e completamente abbandonato davanti a 40+ voci di menu.

### Accessibilita
Zero `aria-label` su 70 pagine. 3 pagine con gestione tastiera. Nessun supporto screen reader.

### Responsive mobile
19/70 pagine senza classi responsive. L'app e essenzialmente desktop-only.

### Stato bozza vs definitivo
POS DOCX, pacchetti, email non hanno un ciclo di vita chiaro (bozza -> review -> definitivo). Il documento generato e "una bozza" ma non c'e modo di promuoverlo a "definitivo".

---

## 5. COSA E SCOLLEGATO

### 6 Route file orfane (dead code)
`approvvigionamento.py`, `consegne_ops.py`, `conto_lavoro.py`, `documenti_ops.py`, `produzione_ops.py`, `commessa_ops_common.py` — mai registrate in `main.py`. ~3.200 righe di codice morto.

### 2 Service orfane
`aruba_sdi.py` (mai importato), `pos_pdf_service.py` (sostituito da DOCX generator).

### 9 Directory vuote alla root
`DoP`, `Documenti`, `Emissione`, `Emissioni`, `Evidence`, `Gestione`, `Rami`, `Ramo`, `Send` — residui di test/prototipi.

### 15 Collezioni DB zombie
Collezioni nel database non referenziate da nessun codice attivo (`articoli_perizia`, `catalogo_profili`, `download_tokens`, `officina_alerts`, `officina_timers`, ecc.).

---

## 6. COSA E LEGACY / INUTILE

### Spec files obsolete
9 file `.md` alla root sono specifiche di funzionalita gia completate. Utili come storico ma non per lo sviluppo attivo. Dovrebbero essere archiviate in `/app/memory/specs/`.

### 232 file di test accumulati
97.000 righe di test da 245+ iterazioni. Molti probabilmente obsoleti o ridondanti. La suite andrebbe consolidata.

### Router sicurezza duplicato
Importato e registrato 2 volte in `main.py`. Bug silenzioso.

### FPC prefix anomalo
Unico router con prefix `/api/fpc` interno invece di usare il pattern standard.

---

## 7. TOP 10 PROBLEMI DA RISOLVERE (in ordine di priorita)

| # | Problema | Gravita | Effort | Report |
|---|---------|---------|--------|--------|
| 1 | **Indici MongoDB non creati** (lifespan/on_event conflict) | BLOCKER | Piccolo | TECH_DEBT |
| 2 | **Router sicurezza duplicato** in main.py | Alta | Piccolo | TECH_DEBT |
| 3 | **No rate limiting** su endpoint AI e critici | Alta | Medio | COMPLIANCE |
| 4 | **~3.200 righe dead code** (6 route orfane) | Alta | Medio | CLEANUP |
| 5 | **78 collezioni senza indici** (performance futura) | Alta | Medio | TECH_DEBT |
| 6 | **Fire-and-forget senza error handling** (6 punti) | Media | Piccolo | TECH_DEBT |
| 7 | **7 route senza user_id filter** (rischio multi-tenant) | Media | Medio | TECH_DEBT |
| 8 | **Password/token in chiaro** (Aruba, FIC, JWT debole) | Media | Piccolo | COMPLIANCE |
| 9 | **CommessaHubPage troppo densa** (11+ sezioni) | Media | Medio | UX_GAPS |
| 10 | **Nessun onboarding** primo utilizzo | Media | Medio | UX_GAPS |

---

## 8. ASSESSMENT COMPLESSIVO

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

### Verdetto

**L'applicazione e funzionalmente completa e i moduli recenti sono ben costruiti.** Il problema non e "funziona o non funziona" — funziona. Il problema e la robustezza: indici mancanti, error handling assente, sicurezza base mancante, e un accumulo di debito tecnico che rende ogni futura modifica piu rischiosa.

**Raccomandazione**: Dedicare 1-2 sprint a risolvere i problemi 1-8 della TOP 10 prima di aggiungere nuove funzionalita. Il fix #1 (indici) e critico e richiede 30 minuti. I fix #2-#6 richiedono 1-2 giorni. Dopo, l'app sara pronta per deploy in produzione.

---

## REPORT COLLEGATI

| Report | Contenuto |
|--------|-----------|
| [`CODEBASE_INVENTORY.md`](./CODEBASE_INVENTORY.md) | Inventario completo file/moduli/collezioni |
| [`CLEANUP_LIST.md`](./CLEANUP_LIST.md) | Lista secca di cosa eliminare |
| [`FLOW_GAPS_REPORT.md`](./FLOW_GAPS_REPORT.md) | Analisi flussi end-to-end |
| [`TECH_DEBT_BACKLOG.md`](./TECH_DEBT_BACKLOG.md) | Backlog tecnico prioritizzato (15 item) |
| [`UX_AND_PRODUCT_GAPS.md`](./UX_AND_PRODUCT_GAPS.md) | Gap UX e prodotto (12 item) |
| [`COMPLIANCE_RISKS.md`](./COMPLIANCE_RISKS.md) | Rischi sicurezza/GDPR/AI (10 item) |

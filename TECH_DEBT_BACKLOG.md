# TECH DEBT BACKLOG — NormaFacile 2.0

> Backlog tecnico prioritizzato — ordinato per gravita e impatto

---

## TD-001: Indici MongoDB non creati (lifespan/on_event conflict)

- **Gravita**: BLOCKER
- **Area**: backend / db / infra
- **Dove si trova**: `/app/backend/main.py` righe 108-125 (lifespan) e 241-317 (startup_event)
- **Perche e un problema**: FastAPI con `lifespan` context manager ignora `@app.on_event("startup")`. TUTTI gli indici definiti in `startup_event` (unique constraints per `obblighi_commessa`, `commesse_normative`, `emissioni_documentali`, `cantieri_sicurezza`, `lib_fasi_lavoro`, `lib_rischi_sicurezza`, `lib_dpi_misure`, `pacchetti_committenza`, `analisi_committenza`) non vengono MAI creati.
- **Impatto reale**: 1) Nessun vincolo unique su `dedupe_key` degli obblighi = possibili duplicati. 2) Nessun indice su query frequenti = performance degradata su dataset grandi. 3) Nessuna migrazione `role` su utenti legacy. 4) CONFERMATO: tutte e 10 le collezioni verificate hanno ZERO indici.
- **Prova dal codice**: Query DB conferma `obblighi_commessa`, `commesse_normative`, `emissioni_documentali`, `cantieri_sicurezza`, `lib_fasi_lavoro`, `lib_rischi_sicurezza`, `lib_dpi_misure`, `pacchetti_committenza`, `analisi_committenza` = NO INDEXES.
- **Correzione consigliata**: Spostare tutto il corpo di `startup_event()` dentro il `lifespan()` context manager, prima del `yield`.
- **Effort stimato**: Piccolo (30 min)

---

## TD-002: Router sicurezza importato e registrato 2 volte

- **Gravita**: Alta
- **Area**: backend
- **Dove si trova**: `/app/backend/main.py` righe 28+76 (import) e 168+216 (include_router)
- **Perche e un problema**: Lo stesso router viene montato due volte. FastAPI le tratta come rotte duplicate. Ogni richiesta a `/api/sicurezza/*` viene processata due volte. Non causa errori visibili ma e un bug silenzioso che spreca risorse e potrebbe causare comportamenti imprevisti su middleware.
- **Impatto reale**: Overhead su ogni richiesta sicurezza. Confusione nella documentazione OpenAPI (/docs).
- **Prova dal codice**: `grep "sicurezza_router" main.py` mostra 2 import e 2 include_router.
- **Correzione consigliata**: Rimuovere l'import duplicato (riga 76) e il secondo `include_router` (riga 216).
- **Effort stimato**: Piccolo (5 min)

---

## TD-003: 78 collezioni MongoDB senza indici

- **Gravita**: Alta
- **Area**: db / performance
- **Dove si trova**: Database `test_database`, 78/100 collezioni
- **Perche e un problema**: Query senza indici eseguono full collection scan. Con dataset piccoli non si nota, ma con crescita produzione diventa un bottleneck. Collezioni critiche come `obblighi_commessa` (40 doc, crescera rapidamente) e `documenti_archivio` (14 doc) sono usate in aggregazioni pesanti.
- **Impatto reale**: Latenza crescente su dashboard, sync obblighi, ricerche pacchetti. Il problema e mascherato dal dataset piccolo attuale.
- **Prova dal codice**: `db.obblighi_commessa.index_information()` = solo `_id_`.
- **Correzione consigliata**: Creare script indici per le 15-20 collezioni piu critiche. Priorita: `obblighi_commessa`, `commesse_normative`, `emissioni_documentali`, `cantieri_sicurezza`, `documenti_archivio`, `pacchetti_documentali`, `istruttorie`, `notifiche_smart`.
- **Effort stimato**: Medio (2-3 ore per analisi + creazione indici corretti)

---

## TD-004: ~3.188 righe di backend routes dead code

- **Gravita**: Alta
- **Area**: backend
- **Dove si trova**: 6 file in `/app/backend/routes/` (approvvigionamento.py, consegne_ops.py, conto_lavoro.py, documenti_ops.py, produzione_ops.py, commessa_ops_common.py)
- **Perche e un problema**: Codice morto aumenta la superficie di manutenzione, confonde nuovi sviluppatori, puo contenere bug latenti se accidentalmente riattivato, aumenta il tempo di ricerca grep.
- **Impatto reale**: Nessun impatto funzionale immediato. Rischio di confusione e manutenzione errata.
- **Prova dal codice**: Nessuno dei 6 file e importato in `main.py`.
- **Correzione consigliata**: Eliminare i 6 file dopo aver verificato che le funzionalita (RdP, OdA, consegne, documenti, fasi produzione) siano coperte da `commessa_ops.py` e moduli attivi.
- **Effort stimato**: Medio (2 ore — serve verifica funzionale prima della cancellazione)

---

## TD-005: Nessun rate limiting

- **Gravita**: Alta
- **Area**: infra / sicurezza
- **Dove si trova**: Assente nell'intera applicazione
- **Perche e un problema**: Endpoint come AI precompilazione, generazione POS, analisi committenza chiamano OpenAI e sono costosi. Senza rate limiting: 1) Un utente puo generare costi AI illimitati. 2) Attacco DoS triviale. 3) Un loop frontend puo saturare il backend.
- **Impatto reale**: Rischio finanziario (costi AI) e rischio disponibilita.
- **Prova dal codice**: `grep -rn "rate_limit" backend/` = 0 risultati.
- **Correzione consigliata**: Aggiungere `slowapi` o middleware custom con rate limit per-user su endpoint critici (AI, PDF generation, email).
- **Effort stimato**: Medio (3-4 ore)

---

## TD-006: Serializer module inutilizzato

- **Gravita**: Media
- **Area**: backend
- **Dove si trova**: `/app/backend/core/serializer.py` (40 righe) — importato solo da `backup.py`
- **Perche e un problema**: Esiste un serializer ben fatto (`serialize_doc`) per gestire ObjectId e datetime, ma quasi nessun route lo usa. Ogni route gestisce `_id` a modo suo (quasi tutti con `{"_id": 0}` nelle proiezioni). Inconsistenza nell'approccio.
- **Impatto reale**: Rischio di bug _id serialization su nuovi endpoint che dimenticano `{"_id": 0}`.
- **Prova dal codice**: `grep -rn "serializer" routes/` = 0 risultati (escluso backup).
- **Correzione consigliata**: Due opzioni: a) Adottare `serialize_doc` come standard e applicarlo nei response handler. b) Mantenere l'approccio `{"_id": 0}` e documentarlo come convenzione ufficiale.
- **Effort stimato**: Medio

---

## TD-007: File monolitici (>1000 righe)

- **Gravita**: Media
- **Area**: backend / frontend
- **Dove si trova**: 
  - Backend: `fatture_ricevute.py` (2448), `dashboard.py` (2034), `invoices.py` (1979), `preventivi.py` (1642), `dop_frazionata.py` (1565), `documenti_ops.py` (1387), `commesse.py` (1341), `engine.py` (1162), `perizia.py` (1102), `cam.py` (1084), `pdf_super_fascicolo.py` (1049), `pos_docx_generator.py` (1033)
  - Frontend: `IstruttoriaPage.js` (1710, 17 state vars!), `RilievoEditorPage.js` (1571), `SopralluogoWizardPage.js` (1262), `PreventivoEditorPage.js` (1195), `MontaggioPanel.js` (1184), `PacchettiDocumentaliPage.js` (1107), `FattureRicevutePage.js` (1091), `CommessaHubPage.js` (1063)
- **Perche e un problema**: Difficolta di manutenzione, review, testing. IstruttoriaPage con 17 state variables e praticamente non-testabile in isolamento.
- **Impatto reale**: Ogni modifica a questi file rischia effetti collaterali. Bug piu difficili da isolare.
- **Correzione consigliata**: Split progressivo per i file peggiori. Priorita: IstruttoriaPage (estrarre step in sub-componenti), fatture_ricevute.py (separare sync FIC, scadenziario, CRUD), dashboard.py (separare endpoint per tipo).
- **Effort stimato**: Alto (1-2 giorni per i piu critici)

---

## TD-008: Debounce in-memory per auto-sync obblighi

- **Gravita**: Media
- **Area**: backend / architettura
- **Dove si trova**: `/app/backend/services/obblighi_auto_sync.py` righe 20-22
- **Perche e un problema**: Il debounce usa un dizionario in-memory (`_last_sync`). Funziona solo con una singola istanza del backend. In deploy multi-instance o con restart frequenti, il debounce si resetta e sync duplicati vengono eseguiti.
- **Impatto reale**: Oggi nessun impatto (single instance). Domani: sync duplicati, overhead DB, possibili race condition.
- **Prova dal codice**: `_last_sync: dict[str, float] = {}` — volatile, non persistito.
- **Correzione consigliata**: v1: accettabile. v2: migrare a lock MongoDB o Redis-based debounce.
- **Effort stimato**: Medio

---

## TD-009: Fire-and-forget asyncio tasks senza error handling

- **Gravita**: Media
- **Area**: backend
- **Dove si trova**: `obblighi_commessa.py` (righe 57-58), `pacchetti_documentali.py` (riga 175), `obblighi_auto_sync.py` (riga 76), `notification_scheduler.py` (riga 803), `backup.py` (riga 175)
- **Perche e un problema**: `asyncio.create_task()` senza error handling = eccezioni silenti. Se il sync obblighi fallisce, nessuno lo sa. Se il backup fallisce, nessun alert.
- **Impatto reale**: Bug silenti. Obblighi non sincronizzati. Notifiche non generate. Nessun modo di sapere che qualcosa e andato storto.
- **Prova dal codice**: `asyncio.create_task(check_and_notify_post_sync(...))` — nessun try/except, nessun callback on error.
- **Correzione consigliata**: Wrappare ogni create_task con error handler che logga le eccezioni e opzionalmente crea una notifica di errore.
- **Effort stimato**: Piccolo (1-2 ore)

---

## TD-010: 7 route senza filtro user_id

- **Gravita**: Media (diventa CRITICA in multi-tenant)
- **Area**: backend / sicurezza
- **Dove si trova**: `audits.py`, `instruments.py`, `montaggio.py`, `officina.py`, `quality_hub.py`, `verbale_posa.py`, `welders.py`
- **Perche e un problema**: Query DB senza filtro `user_id` espongono dati di tutti gli utenti. Oggi con single-tenant non visibile. In multi-tenant = data leak critico.
- **Impatto reale**: Oggi limitato (single tenant de facto). Domani: violazione privacy tra tenant.
- **Prova dal codice**: `grep -c 'user_id.*user["user_id"]' routes/audits.py` = 0.
- **Correzione consigliata**: Aggiungere `user_id` filter a tutte le query DB in questi 7 file.
- **Effort stimato**: Medio (4-5 ore — serve verifica per ogni query)

---

## TD-011: FPC router prefix anomalo

- **Gravita**: Bassa
- **Area**: backend
- **Dove si trova**: `/app/backend/routes/fpc.py` riga 17 e `/app/backend/main.py` riga 182
- **Perche e un problema**: FPC e l'UNICO router che dichiara il prefix `/api/fpc` internamente invece di usare `prefix="/api"` in main.py. Funziona, ma e inconsistente con tutti gli altri 77 router.
- **Impatto reale**: Confusione per sviluppatori. Se qualcuno aggiunge `prefix="/api"` in main.py, le rotte diventano `/api/api/fpc/`.
- **Correzione consigliata**: Cambiare prefix in fpc.py a `/fpc` e aggiungere `prefix="/api"` in main.py.
- **Effort stimato**: Piccolo (10 min)

---

## TD-012: Assenza totale di caching applicativo

- **Gravita**: Media
- **Area**: performance / infra
- **Dove si trova**: Intero backend
- **Perche e un problema**: Dashboard aggregate dati da 9+ collezioni. Ogni caricamento CommessaHubPage fa 5+ API call. Ogni chiamata dashboard fa aggregazioni pesanti. Zero caching.
- **Impatto reale**: Latenza percepita dall'utente. Carico DB inutile per dati che cambiano raramente.
- **Correzione consigliata**: Cache in-memory (TTL 30-60s) per: dashboard stats, gate POS, librerie rischi (cambiano raramente).
- **Effort stimato**: Medio (3-4 ore)

---

## TD-013: Schema validation inconsistente

- **Gravita**: Bassa
- **Area**: backend
- **Dove si trova**: Molti route file (es. `invoices.py` ha 25 raw dict returns vs 7 pydantic, `fatture_ricevute.py` 19 vs 8)
- **Perche e un problema**: Risposte API senza schema definito = nessuna garanzia sul formato. Il frontend deve gestire campi undefined. Errori di serializzazione (_id) piu probabili.
- **Impatto reale**: Bug sottili frontend per campi mancanti/inattesi.
- **Correzione consigliata**: Progressivamente aggiungere `response_model` Pydantic sui nuovi endpoint. Non serve refactor totale.
- **Effort stimato**: Alto (incrementale)

---

## TD-014: Naming inconsistente collezioni/endpoint

- **Gravita**: Bassa
- **Area**: architettura
- **Dove si trova**: Varie
- **Perche e un problema**: 
  - DB: `sicurezza_cantiere` (singolare) vs `cantieri_sicurezza` (plurale)
  - DB: `dop_frazionate` (codice) vs `dop_frazionata` (riferimento)
  - Route: mix snake_case e kebab-case nei prefix
  - Collezione `scadenzario_manutenzioni` vs `scadenziario_manutenzioni` (possibile typo)
- **Impatto reale**: Confusione, bug sottili su query a collezione sbagliata.
- **Correzione consigliata**: Definire convenzione di naming e applicarla progressivamente.
- **Effort stimato**: Alto (richiede migrazione dati)

---

## TD-015: 232 test file potenzialmente obsoleti

- **Gravita**: Bassa
- **Area**: qualita
- **Dove si trova**: `/app/backend/tests/`
- **Perche e un problema**: 97.000 righe di test accumulati iterazione dopo iterazione. Molti probabilmente testano codice che non esiste piu o che e stato refactorato. Mantenerli tutti rallenta CI e crea falsi positivi/negativi.
- **Impatto reale**: Suite test lenta e inaffidabile.
- **Correzione consigliata**: Audit dei test, rimozione obsoleti, consolidamento test critici in suite stabili.
- **Effort stimato**: Alto (1-2 giorni)

---

## RIEPILOGO PRIORITA

| ID | Titolo | Gravita | Effort |
|----|--------|---------|--------|
| TD-001 | Indici non creati (lifespan) | BLOCKER | Piccolo |
| TD-002 | Sicurezza router duplicato | Alta | Piccolo |
| TD-005 | No rate limiting | Alta | Medio |
| TD-003 | 78 collezioni senza indici | Alta | Medio |
| TD-004 | 3K righe dead code routes | Alta | Medio |
| TD-009 | Fire-and-forget senza error handling | Media | Piccolo |
| TD-010 | 7 route senza user_id filter | Media | Medio |
| TD-006 | Serializer inutilizzato | Media | Medio |
| TD-008 | Debounce in-memory | Media | Medio |
| TD-012 | No caching | Media | Medio |
| TD-007 | File monolitici | Media | Alto |
| TD-011 | FPC prefix anomalo | Bassa | Piccolo |
| TD-013 | Schema validation inconsistente | Bassa | Alto |
| TD-014 | Naming inconsistente | Bassa | Alto |
| TD-015 | Test obsoleti | Bassa | Alto |

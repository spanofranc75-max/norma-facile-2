# FLOW GAPS REPORT — NormaFacile 2.0

> Analisi dei flussi utente end-to-end — dove tengono, dove si rompono

---

## FLUSSO 1: Preventivo -> Istruttoria AI -> Segmentazione -> Commessa

### Stato: FUNZIONANTE con riserve

**Percorso tecnico**:
1. `PreventivoEditorPage` -> crea preventivo via `POST /api/preventivi`
2. `IstruttoriaPage` -> `POST /api/istruttoria/analizza-preventivo/{id}` (AI GPT-4o)
3. AI ritorna analisi -> utente fa review + risposte a domande
4. `POST /api/istruttoria/{id}/conferma` -> checkpoint obbligatorio
5. `POST /api/istruttoria/segmenta/{id}` -> segmentazione normativa (AI)
6. `POST /api/istruttoria/segmenta/{id}/review` -> utente conferma segmenti
7. `POST /api/istruttoria/phase2/genera/{id}` -> genera commessa preistruita

**Cosa funziona**:
- Il flusso end-to-end e collegato. La commessa preistruita viene generata con i dati dell'istruttoria.
- Il trigger auto-sync obblighi si attiva dopo risposte e conferma segmentazione.
- Il resolve `commessa_from_preventivo` funziona via `commesse_preistruite`.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F1.1 | IstruttoriaPage e un monolito (1710 righe, 17 state) | Media | Difficile da mantenere e testare. 31 hook calls. Qualsiasi modifica rischia regressioni. |
| F1.2 | I risultati AI non hanno indicatore visivo chiaro "proposta AI" vs "confermato" | Media | Il campo `confidence` (dedotto/confermato/incerto) esiste nel backend ma non e chiaramente esposto nel frontend. L'utente non distingue facilmente cosa e AI e cosa e stato verificato. |
| F1.3 | Manca passaggio manuali inutili: l'utente deve navigare manualmente tra 4-5 pagine/step | Bassa | La navigazione preventivo -> istruttoria -> segmentazione richiede click manuali. Un wizard guidato sarebbe piu fluido. |
| F1.4 | Se l'AI fallisce (timeout, errore LLM), il recovery path non e chiaro | Bassa | L'errore viene mostrato, ma non c'e un "riprova" evidente o un fallback manuale. |

---

## FLUSSO 2: Commessa -> Rami Normativi -> Emissioni -> Evidence Gate

### Stato: FUNZIONANTE — robusto

**Percorso tecnico**:
1. Commessa madre creata (da fase 1 o manualmente)
2. `POST /api/commesse-normative/genera-da-istruttoria/{preventivo_id}` -> crea rami da segmentazione
3. oppure `POST /api/commesse-normative/{commessa_id}` -> creazione manuale ramo
4. `POST /api/emissioni/{ramo_id}` -> crea emissione per ramo
5. `GET /api/emissioni/{ramo_id}/{emissione_id}/gate` -> evidence gate check
6. `POST /api/emissioni/{ramo_id}/{emissione_id}/emetti` -> emissione finale (se gate OK)

**Cosa funziona**:
- La catena rami -> emissioni e ben strutturata.
- L'evidence gate engine (`evidence_gate_engine.py`) e rule-based, ben organizzato per EN 1090, EN 13241, e norme generiche.
- Il trigger auto-sync obblighi si attiva su creazione emissione, emissione gate check, e emissione finale.
- La UI (RamiNormativiSection + EmissioneDetailPanel) mostra lo stato gate con colori chiari.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F2.1 | Nessun indice su `emissioni_documentali` e `commesse_normative` | Alta | Le unique constraints definite in `main.py` startup_event NON vengono create (bug TD-001). Un'emissione duplicata potrebbe essere inserita. |
| F2.2 | L'evidence gate non fa parte del Registro Obblighi in modo bidirezionale | Bassa | Il gate genera obblighi nel registro (Source A), ma il registro non aggiorna direttamente lo stato del gate. Il gate ricalcola indipendentemente. Questo e corretto architetturalmente, ma significa che "chiudere un obbligo nel registro" non sblocca automaticamente il gate. |

---

## FLUSSO 3: Commessa -> Sicurezza -> AI Sicurezza -> Gate POS -> POS DOCX

### Stato: FUNZIONANTE — ben connesso

**Percorso tecnico**:
1. `POST /api/cantieri-sicurezza` -> crea scheda cantiere legata a commessa
2. SchedaCantierePage 4-step wizard: dati cantiere -> soggetti -> rischi -> generazione
3. `POST /api/cantieri-sicurezza/{id}/ai-precompila` -> AI pre-compilazione (GPT-4o)
4. AI raccoglie contesto da: commessa, preventivo, istruttoria, sopralluogo, company_settings
5. Utente fa review e conferma fasi/rischi/DPI
6. `GET /api/cantieri-sicurezza/{id}/gate` -> Gate POS check
7. `POST /api/cantieri-sicurezza/{id}/genera-pos` -> genera DOCX POS
8. Trigger auto-sync obblighi su update sostanziale e su gate POS

**Cosa funziona**:
- Il flusso e completo end-to-end. La catena fase -> rischi -> DPI/misure/apprestamenti funziona con la libreria 3 livelli.
- Il POS DOCX generator produce 15 sezioni e 21 tabelle.
- I soggetti vengono pre-compilati dalle figure aziendali.
- Il gate POS controlla campi obbligatori, soggetti, rischi gate_critical.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F3.1 | L'AI tende a produrre contenuti generici ("boilerplate") | Media | Il prompt e buono ma dipende dalla qualita del contesto. Se la commessa ha descrizione povera, l'output AI sara generico. Non c'e scoring della qualita dell'output AI. |
| F3.2 | Il POS DOCX usa placeholder quando i dati mancano | Bassa | Il generatore usa `_placeholder(mode, "testo")` per campi vuoti. Il risultato e un documento con "[...]" che l'utente deve completare. Funzionale ma non sempre evidente dove intervenire. |
| F3.3 | Gate POS e obblighi non bidirezionali | Bassa | Come per F2.2: il gate genera obblighi (Source B) ma chiudere un obbligo non modifica il gate. Il gate ricalcola da zero. Corretto ma non intuitivo per l'utente. |
| F3.4 | Nessun indice su `cantieri_sicurezza` | Alta | Manca l'unique constraint su `cantiere_id` (bug TD-001). |

---

## FLUSSO 4: Repository Documentale -> Verifica Committenza -> Registro Obblighi

### Stato: FUNZIONANTE — integrato

**Percorso tecnico**:
1. Documenti caricati in `documenti_archivio` via `POST /api/pacchetti-documentali/upload`
2. `POST /api/committenza/packages` -> crea package di analisi committenza
3. `POST /api/committenza/packages/{id}/documents` -> collega documenti dal repository (per referenza, senza duplicazione!)
4. `POST /api/committenza/analizza/{package_id}` -> AI analizza documenti (GPT-4o)
5. Utente fa review: conferma/rifiuta obblighi, anomalie, mismatch
6. `POST /api/committenza/analisi/{id}/approve` -> approva come snapshot ufficiale
7. `POST /api/committenza/analisi/{id}/genera-obblighi` -> inserisce nel Registro Obblighi
8. Source H sync raccoglie obblighi da analisi approvate

**Cosa funziona**:
- Il modulo NON duplica i file. Referenzia `doc_id` dal repository. Architettura corretta.
- L'analisi AI produce obblighi, anomalie, mismatch con categorie strutturate.
- La review umana (conferma/rifiuta) e il checkpoint prima dell'inserimento nel registro.
- I dedupe_key prevengono duplicati nel registro.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F4.1 | Analisi AI dipende dalla qualita OCR dei documenti | Media | Se il documento caricato e un PDF scansionato di bassa qualita, l'AI potrebbe non estrarre correttamente gli obblighi. Non c'e feedback sulla qualita dell'input. |
| F4.2 | I mismatch preventivo/commessa possono essere "rumorosi" | Bassa | L'AI trova molti mismatch che possono essere falsi positivi. Non c'e modo di marcare un mismatch come "non rilevante" per ridurre il rumore nelle analisi successive. |

---

## FLUSSO 5: Pacchetti Documentali -> Verifica -> Invio Email

### Stato: FUNZIONANTE — completo

**Percorso tecnico**:
1. Upload documenti in archivio (D1)
2. Creazione pacchetto da template predefinito (D2)
3. `POST /api/pacchetti-documentali/{id}/verifica` -> matching documenti (D3)
4. `POST /api/pacchetti-documentali/{id}/prepara-invio` -> preview email (D4)
5. `POST /api/pacchetti-documentali/{id}/invia` -> invio via Resend (D5)
6. Profili committente per riutilizzo (D6)

**Cosa funziona**:
- Il flusso D1-D6 e completo e testato.
- La verifica matching trova attached/missing/expired/in_scadenza.
- L'email preview include warning su documenti sensibili e scaduti.
- Il trigger notifiche si attiva su pacchetto incompleto.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F5.1 | I profili committente sono troppo statici | Media | Un profilo salva `rules[]` con tipo documento e entity_type. Non c'e logica per suggerire automaticamente regole basate sullo storico invii. Utile ma poco "intelligente". |
| F5.2 | Documenti scaduti non bloccano automaticamente l'invio | Bassa | L'invio mostra warning ma non blocca. L'utente puo inviare documenti scaduti. Questo potrebbe essere una scelta di design (fiducia all'utente), ma andrebbe documentato. |

---

## FLUSSO 6: Registro Obblighi -> Dashboard -> Audit Log

### Stato: FUNZIONANTE — collante centrale

**Percorso tecnico**:
1. `POST /api/obblighi/sync/{commessa_id}` -> sync da 8 fonti (A-H)
2. Auto-sync trigger da 4 moduli (cantiere, emissioni, istruttoria, rami)
3. `GET /api/obblighi/commessa/{commessa_id}` -> lista per commessa
4. `PATCH /api/obblighi/{id}` -> cambio stato manuale (con audit trail)
5. `GET /api/dashboard/cantiere-multilivello` -> semaforo basato su obblighi
6. Notifiche smart trigger su: semaforo peggiorato, nuovo hard block

**Cosa funziona**:
- Il registro e veramente il "collante" dell'applicazione. 8 fonti sincronizzate.
- Deduplicazione via `dedupe_key` previene duplicati.
- Auto-close e riapertura automatica funzionano.
- Il semaforo della dashboard si basa su dati reali (obblighi bloccanti e warning).

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F6.1 | CRITICO: Indici unique su obblighi_commessa non creati | Blocker | Bug TD-001. Senza indice unique su `dedupe_key`, il dedup funziona via query (find + insert), ma in caso di race condition (due sync simultanei), possono nascere duplicati. |
| F6.2 | In-memory debounce non persistente | Media | Se il server si riavvia, il debounce si resetta. Possibili sync duplicati. |
| F6.3 | Dashboard interroga 31 collezioni senza cache | Media | Il dashboard.py accede a 31 collezioni diverse. Senza caching, ogni refresh e pesante. |
| F6.4 | Obblighi "rumorosi" da alcune fonti | Bassa | Source F (documenti scaduti) e Source G (pacchetti mancanti) possono generare molti obblighi che sono piu "avvisi" che reali bloccanti. Servirebbe un livello "informativo" distinto. |

---

## FLUSSO 7: Eventi automatici / Sync / Trigger tra moduli

### Stato: FUNZIONANTE — decoupled design

**Trigger attivi**:
1. Cantiere sicurezza update -> trigger_sync_obblighi
2. Emissione PATCH/gate/emetti -> trigger_sync_obblighi
3. Istruttoria risposte + conferma -> trigger_sync_obblighi
4. Rami normativi creazione -> trigger_sync_obblighi
5. Obblighi sync -> notify_post_sync + check_semaforo
6. Pacchetti verifica -> notify_pacchetto_incompleto
7. Scheduler periodico: scadenze saldatori, strumenti, ITT, pagamenti, backup

**Cosa funziona**:
- Il design decoupled con `asyncio.create_task()` e buono. I trigger non bloccano la response.
- Il notification scheduler gira in background con intervalli configurati.
- Le notifiche smart hanno deduplicazione via `dedupe_key`.

**Gap e problemi trovati**:

| # | Problema | Gravita | Dettaglio |
|---|----------|---------|-----------|
| F7.1 | Tutti i create_task sono fire-and-forget | Media | Se un sync o una notifica fallisce, nessuno lo sa. Nessun retry, nessun alert, nessun log di errore (l'errore viene swallowed). |
| F7.2 | Debounce in-memory | Media | Come F6.2. Fragile in deploy multi-instance. |
| F7.3 | Scheduler loop senza health check | Bassa | Il `_scheduler_loop` in `notification_scheduler.py` gira indefinitamente. Se va in crash, non c'e recovery automatico ne alert. |

---

## AREA FORTE: Cosa funziona davvero bene

1. **Architettura dei moduli**: Il pattern "service separato + route + frontend section" e ben applicato nei moduli nuovi (obblighi, committenza, pacchetti, sicurezza).
2. **Deduplicazione obblighi**: Il meccanismo `dedupe_key` e robusto e ben pensato.
3. **Evidence Gate Engine**: Rule-based, ben organizzato per normativa, con check puntuali.
4. **Non-duplicazione documenti**: Committenza referenzia doc_id senza copiare file. Corretto.
5. **Audit Trail**: 16 moduli instrumentati con `actor_type` (user/system/ai). Buona copertura.
6. **Notifiche trigger**: Design decoupled, 6 tipi di evento, deduplicazione.
7. **Libreria rischi 3 livelli**: Architettura solida fase -> rischi -> DPI/misure/apprestamenti.

---

## MAPPA COLLEGAMENTI TRA MODULI

```
Preventivo ──> Istruttoria AI ──> Segmentazione ──> Commessa Preistruita ──> Commessa Madre
                    │                    │
                    │                    └──> Rami Normativi ──> Emissioni ──> Evidence Gate ──┐
                    │                                                                          │
                    └──> Auto-sync obblighi <─────────────────────────────────────────────────┘
                                                                                               │
Scheda Cantiere ──> AI Sicurezza ──> Gate POS ──> POS DOCX ──────────────── Auto-sync ────────┘
                                                                                               │
Repository Doc ──> Pacchetti ──> Verifica ──> Email ──────────────────────── Auto-sync ────────┘
                        │                                                                      │
                        └──> Committenza AI ──> Review ──> Genera Obblighi ── Auto-sync ───────┘
                                                                                               │
                                                                                               v
                                                                              REGISTRO OBBLIGHI
                                                                               (8 fonti A-H)
                                                                                    │
                                                                                    v
                                                                         Dashboard Cantiere
                                                                         (semaforo + KPI)
                                                                                    │
                                                                                    v
                                                                         Notifiche Smart
                                                                         (6 tipi evento)
```

Tutti i fili conduttori principali sono COLLEGATI. Non ci sono moduli "isolati" tra quelli implementati recentemente. I gap principali sono a livello di robustezza (indici mancanti, error handling) piuttosto che di collegamento logico.

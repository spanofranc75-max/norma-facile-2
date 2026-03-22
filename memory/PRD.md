# NormaFacile 2.0 — PRD

## Problema Originale
ERP per aziende di carpenteria metallica: commesse, compliance EN 1090/13241, generazione documenti, fatturazione, pianificazione, tracciabilita materiali e sicurezza cantieri.

## Architettura
- **Frontend**: React + shadcn/ui + TailwindCSS (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **PDF**: WeasyPrint | **Email**: Resend

## Modello Gerarchico (Fase A — COMPLETATO)
`Commessa Madre -> Ramo Normativo -> Emissione Documentale`

## Evidence Gate Avanzato (Fase B — COMPLETATO)
Engine rule-based in `evidence_gate_engine.py`

## Collegamento Segmentazione-Rami (S0 — COMPLETATO)
Auto-creazione rami normativi dopo conferma istruttoria

## Safety Branch MVP (S1 + S2 — COMPLETATO 2026-03-22)
- S1: Analizzato template POS (459 KB, 31 sezioni) -> `SPEC_POS_TEMPLATE_MAPPING.md`
- S2: Backend + Frontend con 4-step wizard

## Libreria Rischi 3 Livelli (Step 0 + Step 1 — COMPLETATO 2026-03-23)
Refactor completo da modello flat a 3 collezioni separate:

### Livello 1: `lib_fasi_lavoro` (11 fasi)
- Codice, nome, descrizione, categoria, trigger.keywords, rischi_ids[]
- Ogni fase attiva N rischi tramite codici

### Livello 2: `lib_rischi_sicurezza` (20 rischi)
- Codice, nome, categoria, sottocategoria, gate_critical
- trigger.keywords + condizioni_esclusione
- valutazione_default (P, D, Classe)
- dpi_ids[], misure_ids[], apprestamenti_ids[] (separati)
- documenti_richiesti[], domande_verifica[] con impatto e gate_critical

### Livello 3: `lib_dpi_misure` (31 entries)
- 12 DPI, 11 Misure organizzative, 8 Apprestamenti
- Tipo, sottotipo, norma UNI EN, obbligatorieta
- Campi governance: active, version, source, sort_order

### Catena automatica
Fase -> rischi_ids -> dpi_ids + misure_ids + apprestamenti_ids + domande_verifica
- Deduplicazione automatica
- Confidenza: dedotto | confermato | incerto | mancante
- Gate POS con blockers per domande gate_critical aperte

### Testing: 29/29 backend, 100% frontend

## S2.5 — Modello Soggetti & Ruoli (COMPLETATO 2026-03-22)
Gestione strutturata del personale chiave per sicurezza cantiere (POS).

### Architettura a 2 livelli:
1. **Livello azienda** (`company_settings.figure_aziendali`): default RSPP, Datore Lavoro, Medico Competente ecc.
2. **Livello cantiere** (`cantieri_sicurezza.soggetti`): 14 ruoli in 3 categorie

### Ruoli (14 totali):
- **Azienda (5)**: DATORE_LAVORO*, RSPP*, MEDICO_COMPETENTE*, PREPOSTO_CANTIERE, DIRETTORE_TECNICO
- **Committente (6)**: COMMITTENTE*, REFERENTE_COMMITTENTE, RESPONSABILE_LAVORI, DIRETTORE_LAVORI, CSP, CSE
- **Tecnico (3)**: PROGETTISTA, STRUTTURISTA, COLLAUDATORE
(* = obbligatorio per Gate POS)

### Pre-fill automatico:
company_settings.figure_aziendali -> cantiere.soggetti (status: "precompilato")

### Frontend:
- Tab "Sicurezza" in Impostazioni con form Figure Aziendali
- Sezione "Soggetti & Referenti" in SchedaCantierePage Step 1 con 3 categorie

### Bug fix applicato:
- Rimosso campo duplicato figure_aziendali in CompanySettings
- Aggiunto figure_aziendali a CompanySettingsUpdate
- Aggiunta gestione esplicita in PUT /api/company/settings

### Testing: 16/16 backend, 100% frontend (iteration_232)

## File Chiave
- `/app/backend/services/cantieri_sicurezza_service.py` — Service 3 livelli + soggetti
- `/app/backend/routes/cantieri_sicurezza.py` — API (libreria + cantieri + gate + ruoli)
- `/app/backend/routes/company.py` — Settings con figure_aziendali
- `/app/backend/models/company.py` — Modello CompanySettings + Update
- `/app/frontend/src/pages/SchedaCantierePage.js` — Form 4-step con catena + soggetti
- `/app/frontend/src/pages/SicurezzaPage.js` — Lista cantieri
- `/app/frontend/src/pages/SettingsPage.js` — Impostazioni con tab Sicurezza
- `/app/frontend/src/components/settings/FigureAziendaliTab.js` — Form figure aziendali
- `/app/backend/services/ai_safety_engine.py` — Motore AI S3
- `/app/backend/services/pos_docx_generator.py` — Generatore DOCX S4
- `/app/backend/services/pacchetti_documentali_service.py` — D1+D2+D3 service
- `/app/backend/routes/pacchetti_documentali.py` — API pacchetti documentali
- `/app/frontend/src/pages/PacchettiDocumentaliPage.js` — Pagina pacchetti documentali
- `/app/SPEC_LIBRERIA_RISCHI_3_LIVELLI.md` — Spec definitiva v2
- `/app/SPEC_POS_TEMPLATE_MAPPING.md` — Mapping template POS
- `/app/SPEC_PACCHETTI_DOCUMENTALI.md` — Spec pacchetti documentali

## S3 — Motore AI Sicurezza (COMPLETATO 2026-03-22)
Pipeline AI per pre-compilazione intelligente della scheda cantiere sicurezza.

### Pipeline 5 step:
1. **Raccolta contesto**: commessa, istruttoria, preventivo, sopralluogo, company_settings
2. **AI GPT-4o**: Analisi semantica → propone fasi lavorative + contesto operativo
3. **Rules engine**: Espansione catena fasi → rischi → DPI/misure/apprestamenti
4. **Merge domande**: AI + libreria deduplicati con gate_critical
5. **Pre-fill soggetti**: Da figure aziendali + committente da commessa

### Endpoint: `POST /api/cantieri-sicurezza/{id}/ai-precompila`
### Output salvato in cantiere:
- fasi_lavoro_selezionate (con confidence: dedotto/confermato/incerto, origin: ai/rules)
- rischi_attivati (per ogni fase)
- dpi_calcolati, misure_calcolate, apprestamenti_calcolati
- domande_residue (con gate_critical)
- ai_precompilazione (metadata: timestamp, modello, sources_used, contesto_operativo)
- soggetti precompilati
- Gate POS ricalcolato automaticamente

### Frontend: Bottone "Pre-compila con AI" + banner risultato + review/conferma dati

### Testing: 26/26 backend, 100% frontend (iteration_233)

## S4 — Generazione DOCX POS (COMPLETATO 2026-03-22)
Generatore bozza POS DOCX modificabile (Allegato XV D.Lgs. 81/2008).

### 15 sezioni, 21 tabelle:
Copertina, Intro, Anagrafica, Mansionario, Dati Cantiere, Soggetti, Turni, Subappalti,
Misure Prevenzione, DPI, Macchine, Valutazione Rischi, **Schede Rischio per Fase** (CORE),
Emergenza, Dichiarazione.

### Endpoint: `POST /api/cantieri-sicurezza/{id}/genera-pos` (DOCX binary)
### Storico: `GET /api/cantieri-sicurezza/{id}/pos-generazioni`
### Frontend: Card "Genera bozza POS" in Step 4 con download + warning gate

### Testing: 23/23 backend, 100% frontend (iteration_234)


## D1+D2+D3 — Pacchetti Documentali (COMPLETATO 2026-03-22)
Archivio documenti + template pacchetti + motore verifica.
- D1: 26 tipi documento, archivio con upload/metadati/scadenza/privacy, API CRUD
- D2: 5 template (Ingresso Cantiere, Qualifica, Personale, Mezzi, Sicurezza), espansione scope
- D3: Verifica matching archivio->items, stato attached/missing/expired/in_scadenza, blocking, summary
- Frontend: `/pacchetti-documentali`, 2 tab (Archivio+Pacchetti), upload, checklist 3 colonne
### Testing: 38/38 backend, 100% frontend (iteration_235)

## D4+D5 — Preview Invio, Email & Log (COMPLETATO 2026-03-22)
Preparazione, invio email con allegati, e tracciabilita invii.
- D4: `POST /prepara-invio` genera email_draft (oggetto, testo, allegati, warnings privacy/scadenza)
- D5: `POST /invia` invio via Resend + log in `pacchetti_invii`, gestione errori graceful
- `GET /invii` storico invii per pacchetto, `PATCH /{id}` aggiornamento destinatari
- Bug fix: `get_object()` ritornava tupla (bytes, content_type) — ora correttamente destrutturato
- Frontend: PackageDetailView con checklist, form destinatari To/CC, preview email editabile, warnings sensibili/scaduti, dialog conferma invio, storico invii
### Testing: 21/21 backend, 100% frontend (iteration_237)

## Registro Obblighi Commessa MVP (COMPLETATO 2026-03-22)
Modulo "collante" che centralizza tutti gli obblighi, blockers e requisiti per ogni commessa.
- Sync engine con 5 fonti: Evidence Gate, Gate POS, Soggetti, Istruttoria, Rami Normativi
- Deduplicazione via `dedupe_key` (formato: `{commessa_id}|{source_module}|{source_entity_id}|{code}`)
- Auto-close con `resolution_note` quando la condizione sorgente sparisce
- Riapertura automatica se un obbligo chiuso torna attivo
- 7 API: CRUD + sync + commessa + bloccanti + summary
- UI: Sezione collapsabile in CommessaHubPage con 4 gruppi (Bloccanti/Da completare/Da verificare/Chiusi)
- Filtri per fonte e categoria, cambio stato inline, link navigazione ai moduli sorgente
- Indici MongoDB: dedupe_key unique, commessa_id+status, priority sort
### Testing: 23/23 backend, 100% frontend (iteration_238)

## Backlog Prioritizzato

### P0 (Prossimi — COMPLETATI)
- ~~S3: Motore AI Sicurezza~~ — COMPLETATO
- ~~S4: Generazione DOCX~~ — COMPLETATO
- ~~Registro Obblighi Commessa MVP~~ — COMPLETATO

### P1 (Prossimi)
- **D1-D5: Pacchetti Documentali Intelligenti** — COMPLETATO (D1-D5)
  - ~~D1: Libreria tipi documento + archivio documenti~~ COMPLETATO
  - ~~D2: Template pacchetti~~ COMPLETATO
  - ~~D3: Matching automatico + verifica presenza/scadenza~~ COMPLETATO
  - ~~D4: UI pacchetto documentale (preview invio)~~ COMPLETATO
  - ~~D5: Invio email one-click + log invii (via Resend)~~ COMPLETATO
  - D6: Profili documentali per committente ricorrente
- **Registro Obblighi Fase 2**: aggiungere pacchetti documentali, verifica committenza, documenti scaduti, assegnazione responsabili, scadenze
- Modulo Verifica Committenza / Contratti (si integra con Pacchetti Documentali)
- Dashboard Cantiere Multilivello
- Stability Guard deterministico

### P2-P3
- Multi-Tenant, ML Training, Alert costi
- Unificazione PDF, Portale Clienti
- Fix warning minori (exhaustive-deps, hydration)

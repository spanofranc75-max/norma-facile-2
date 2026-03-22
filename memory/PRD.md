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
- `/app/SPEC_LIBRERIA_RISCHI_3_LIVELLI.md` — Spec definitiva v2
- `/app/SPEC_POS_TEMPLATE_MAPPING.md` — Mapping template POS

## Backlog Prioritizzato

### P0 (Prossimi)
- **S3: Motore AI Sicurezza** — precompilazione da commessa (fasi, rischi, DPI, domande residue)
- **S4: Generazione DOCX** — merge template POS + dati strutturati

### P1 (Subito dopo S3/S4)
- **D1-D5: Pacchetti Documentali Intelligenti** — Cabina di regia documenti da mandare al cliente. Spec completa in `/app/SPEC_PACCHETTI_DOCUMENTALI.md`
  - D1: Libreria tipi documento + archivio documenti centralizzato (azienda, persona, mezzo, cantiere)
  - D2: Template pacchetti (ingresso cantiere, qualifica fornitore, personale, mezzi, sicurezza)
  - D3: Matching automatico + verifica presenza/scadenza (valido, mancante, scaduto, in_scadenza)
  - D4: UI pacchetto documentale (checklist 3 colonne: richiesto/trovato/problemi)
  - D5: Invio email one-click + log invii (via Resend)
  - D6: Profili documentali per committente ricorrente
- Modulo Verifica Committenza / Contratti (si integra con Pacchetti Documentali)
- Dashboard Cantiere Multilivello
- Stability Guard deterministico

### P2-P3
- Multi-Tenant, ML Training, Alert costi
- Unificazione PDF, Portale Clienti
- Fix warning minori (exhaustive-deps, hydration)

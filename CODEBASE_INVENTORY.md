# CODEBASE INVENTORY — NormaFacile 2.0

> Generato il 2026-03-23 | Audit Totale Livello A

---

## 1. STATISTICHE GLOBALI

| Area | Conteggio |
|------|-----------|
| File backend (.py) | ~160 (routes: 78, services: 58, models: 17, core: 5) |
| File frontend (.js) | ~120 (pages: 70, components: 52, hooks: 1, contexts: 1) |
| Collezioni MongoDB | 100 |
| Collezioni CON indici | 22 |
| Collezioni SENZA indici | 78 |
| File di test | 232 |
| Linee totali test | ~97.000 |
| File spec/doc root | 12 |
| File memory/ | 6 |

---

## 2. BACKEND — ROUTES (78 file)

### 2.1 Route ATTIVE e registrate in main.py

| File | Prefix | Linee | Stato |
|------|--------|-------|-------|
| `auth.py` | `/auth` | ~180 | ATTIVO |
| `clients.py` | `/clients` | ~350 | ATTIVO |
| `invoices.py` | `/invoices` | 1979 | ATTIVO - MONOLITICO |
| `company.py` | `/company` | ~300 | ATTIVO |
| `rilievi.py` | (nessuno) | 733 | ATTIVO |
| `distinta.py` | `/distinte` | ~400 | ATTIVO |
| `certificazioni.py` | `/certificazioni` | ~400 | ATTIVO |
| `sicurezza.py` | `/sicurezza` | ~200 | ATTIVO - DUPLICATO (importato 2 volte) |
| `dashboard.py` | `/dashboard` | 2034 | ATTIVO - MONOLITICO |
| `catalogo.py` | `/catalogo` | ~200 | ATTIVO |
| `verbale_posa.py` | (nessuno) | ~350 | ATTIVO |
| `vendor_api.py` | (nessuno) | ~150 | ATTIVO |
| `preventivi.py` | `/preventivi` | 1642 | ATTIVO - MONOLITICO |
| `payment_types.py` | `/payment-types` | ~200 | ATTIVO |
| `ddt.py` | `/ddt` | 682 | ATTIVO |
| `perizia.py` | (nessuno) | 1102 | ATTIVO |
| `articoli.py` | `/articoli` | ~200 | ATTIVO |
| `fatture_ricevute.py` | `/fatture-ricevute` | 2448 | ATTIVO - MONOLITICO (il piu grande) |
| `sopralluogo.py` | (nessuno) | ~500 | ATTIVO |
| `movimenti.py` | `/movimenti` | ~300 | ATTIVO |
| `engine.py` | `/engine` | 1162 | ATTIVO |
| `commesse.py` | `/commesse` | 1341 | ATTIVO |
| `commessa_ops.py` | `/commesse` | ~500 | ATTIVO |
| `fpc.py` | `/api/fpc` | 841 | ATTIVO - PREFIX ANOMALO |
| `cam.py` | `/cam` | 1084 | ATTIVO |
| `fascicolo_tecnico.py` | `/fascicolo-tecnico` | ~200 | ATTIVO |
| `company_docs.py` | `/company/documents` | ~300 | ATTIVO |
| `instruments.py` | `/instruments` | ~200 | ATTIVO |
| `welders.py` | (nessuno) | ~400 | ATTIVO |
| `audits.py` | (nessuno) | ~400 | ATTIVO |
| `quality_hub.py` | (nessuno) | ~150 | ATTIVO |
| `smart_assign.py` | (nessuno) | ~150 | ATTIVO |
| `migrazione.py` | `/migrazione` | ~200 | ATTIVO |
| `gate_certification.py` | `/gate-cert` | ~300 | ATTIVO |
| `consumables.py` | `/consumables` | ~200 | ATTIVO |
| `cost_control.py` | `/costs` | 728 | ATTIVO |
| `backup.py` | `/admin/backup` | ~400 | ATTIVO |
| `team.py` | (nessuno) | ~200 | ATTIVO |
| `notifications.py` | `/notifications` | ~200 | ATTIVO |
| `diario_produzione.py` | `/commesse` | ~300 | ATTIVO |
| `qrcode_gen.py` | (nessuno) | ~100 | ATTIVO |
| `db_cleanup.py` | `/admin/cleanup` | ~150 | ATTIVO |
| `wps.py` | (nessuno) | ~300 | ATTIVO |
| `rdp.py` | (nessuno) | ~300 | ATTIVO |
| `search.py` | (nessuno) | ~200 | ATTIVO |
| `activity_log.py` | `/activity-log` | ~120 | ATTIVO |
| `voci_lavoro.py` | (nessuno) | ~200 | ATTIVO |
| `officina.py` | `/officina` | ~350 | ATTIVO |
| `pacco_documenti.py` | (nessuno) | ~300 | ATTIVO |
| `smistatore.py` | (nessuno) | ~200 | ATTIVO |
| `sfridi.py` | (nessuno) | ~200 | ATTIVO |
| `qualita.py` | (nessuno) | ~200 | ATTIVO |
| `montaggio.py` | `/montaggio` | ~400 | ATTIVO |
| `attrezzature.py` | `/attrezzature` | ~100 | ATTIVO |
| `archivio.py` | `/archivio` | ~200 | ATTIVO |
| `dop_frazionata.py` | `/fascicolo-tecnico` | 1565 | ATTIVO - MONOLITICO |
| `sal_acconti.py` | (nessuno) | ~200 | ATTIVO |
| `preventivatore.py` | (nessuno) | 717 | ATTIVO |
| `kpi_dashboard.py` | `/kpi` | ~200 | ATTIVO |
| `calibrazione.py` | `/calibrazione` | ~100 | ATTIVO |
| `manuale.py` | (nessuno) | ~200 | ATTIVO |
| `riesame_tecnico.py` | (nessuno) | 737 | ATTIVO |
| `registro_saldatura.py` | (nessuno) | ~300 | ATTIVO |
| `controllo_finale.py` | `/controllo-finale` | ~300 | ATTIVO |
| `template_111.py` | (nessuno) | ~200 | ATTIVO |
| `report_ispezioni.py` | (nessuno) | ~300 | ATTIVO |
| `scadenziario_manutenzioni.py` | (nessuno) | ~200 | ATTIVO |
| `verbali_itt.py` | (nessuno) | ~300 | ATTIVO |
| `istruttoria.py` | `/istruttoria` | ~600 | ATTIVO |
| `validation.py` | (nessuno) | ~200 | ATTIVO |
| `commesse_normative.py` | (nessuno) | ~350 | ATTIVO |
| `cantieri_sicurezza.py` | (nessuno) | ~280 | ATTIVO |
| `pacchetti_documentali.py` | (nessuno) | ~400 | ATTIVO |
| `obblighi_commessa.py` | (nessuno) | ~200 | ATTIVO |
| `committenza.py` | (nessuno) | ~300 | ATTIVO |
| `profili_committente.py` | (nessuno) | ~200 | ATTIVO |
| `notifiche_smart.py` | `/notifiche-smart` | ~100 | ATTIVO |

### 2.2 Route ORFANE (non registrate in main.py) - DEAD CODE

| File | Linee | Motivo |
|------|-------|--------|
| `approvvigionamento.py` | 515 | Mai registrato. Usa `commessa_ops_common.py` |
| `consegne_ops.py` | 584 | Mai registrato. Usa `commessa_ops_common.py` |
| `conto_lavoro.py` | 499 | Mai registrato. Usa `commessa_ops_common.py` |
| `documenti_ops.py` | 1387 | Mai registrato. Usa `commessa_ops_common.py` |
| `produzione_ops.py` | 108 | Mai registrato. Usa `commessa_ops_common.py` |
| `commessa_ops_common.py` | 95 | Helper per i 5 file orfani sopra |

**Totale dead code backend routes: ~3.188 linee**

---

## 3. BACKEND — SERVICES (58 file)

### 3.1 Services ATTIVI

| File | Linee | Funzione |
|------|-------|----------|
| `ai_safety_engine.py` | ~400 | Pipeline AI per sicurezza cantiere |
| `pos_docx_generator.py` | 1033 | Generazione DOCX POS |
| `pacchetti_documentali_service.py` | 764 | Engine pacchetti documentali |
| `obblighi_commessa_service.py` | 864 | Sync engine obblighi 8 fonti |
| `committenza_analysis_service.py` | 804 | Analisi AI committenza |
| `cantieri_sicurezza_service.py` | 789 | Service 3 livelli sicurezza |
| `evidence_gate_engine.py` | ~530 | Engine evidence gate |
| `segmentation_engine.py` | ~200 | Segmentazione normativa AI |
| `notification_scheduler.py` | 812 | Scheduler scadenze/backup |
| `notifiche_smart_service.py` | ~200 | CRUD notifiche smart |
| `notifiche_trigger.py` | ~300 | Trigger notifiche eventi |
| `obblighi_auto_sync.py` | ~100 | Debounce auto-sync |
| `profili_committente_service.py` | ~200 | Service profili committente |
| `audit_trail.py` | ~100 | Log attivita |
| `email_service.py` | 446 | Invio email via Resend |
| `object_storage.py` | ~200 | Object storage S3 |
| `pdf_super_fascicolo.py` | 1049 | PDF super fascicolo |
| `pacco_documenti.py` | 938 | Motore pacco documenti |
| `pdf_perizia_sopralluogo.py` | 892 | PDF perizie |
| (altri ~40 service PDF, calcolo, XML...) | vari | ATTIVI |

### 3.2 Services ORFANI

| File | Linee | Motivo |
|------|-------|--------|
| `aruba_sdi.py` | ~250 | Mai importato da nessun route/service |
| `pos_pdf_service.py` | ~200 | Mai importato (sostituito da pos_docx_generator) |

---

## 4. BACKEND — MODELS (17 file)

Tutti i model Pydantic risultano importati da almeno un route. Nessun model orfano.

| File | Descrizione | Stato |
|------|-------------|-------|
| `user.py` | Modello utente + auth | ATTIVO |
| `company.py` | Settings azienda (contiene aruba_password) | ATTIVO |
| `invoice.py` | Fatture | ATTIVO |
| `client.py` | Clienti | ATTIVO |
| `ddt.py` | DDT | ATTIVO |
| `sicurezza.py` | Modello sicurezza | ATTIVO |
| `cam.py` | Modello CAM | ATTIVO |
| `audit.py` | Modello audit/NC | ATTIVO |
| `certificazione.py` | Certificazioni CE | ATTIVO |
| `distinta.py` | Distinte | ATTIVO |
| `fpc.py` | FPC EN 1090 | ATTIVO |
| `gate_certification.py` | Gate cert | ATTIVO |
| `instrument.py` | Strumenti | ATTIVO |
| `welder.py` | Saldatori | ATTIVO |
| `perizia.py` | Perizie | ATTIVO |
| `rilievo.py` | Rilievi | ATTIVO |
| `sopralluogo.py` | Sopralluoghi | ATTIVO |
| `payment_type.py` | Tipi pagamento | ATTIVO |
| `company_doc.py` | Documenti azienda | ATTIVO |

---

## 5. FRONTEND — PAGES (70 file)

Tutte le 70 pagine risultano importate in `App.js` e ruotate. Nessuna pagina orfana.

### File monolitici (>800 linee):

| File | Linee | Commento |
|------|-------|----------|
| `IstruttoriaPage.js` | 1710 | 17 state, 31 hook calls. MOLTO COMPLESSO |
| `RilievoEditorPage.js` | 1571 | Editor rilievi pesante |
| `SopralluogoWizardPage.js` | 1262 | Wizard multi-step |
| `PreventivoEditorPage.js` | 1195 | Editor preventivi |
| `PacchettiDocumentaliPage.js` | 1107 | 3 tab (Archivio + Pacchetti + Profili) |
| `FattureRicevutePage.js` | 1091 | Gestione fatture ricevute |
| `CommessaHubPage.js` | 1063 | Hub commessa con 11 sections |
| `PeriziaEditorPage.js` | 1037 | Editor perizie |
| `DistintaEditorPage.js` | 1026 | Editor distinte |
| `InvoiceEditorPage.js` | 993 | Editor fatture |
| `PlanningPage.js` | 833 | Planning cantieri |
| `SchedaCantierePage.js` | 824 | Scheda cantiere 4-step |
| `CoreEnginePage.js` | 812 | Core engine norme |

---

## 6. FRONTEND — COMPONENTS (52 file)

Tutti i 52 componenti risultano importati da almeno 1 pagina. Nessun componente completamente orfano.

### Componenti monolitici (>500 linee):

| File | Linee | Importato da |
|------|-------|-------------|
| `MontaggioPanel.js` | 1184 | CommessaHubPage |
| `FascicoloTecnicoSection.js` | 909 | CommessaHubPage |
| `RilievoViewer3D.js` | 702 | RilievoEditorPage |
| `DiarioProduzione.js` | 686 | CommessaHubPage |
| `DashboardLayout.js` | 652 | 65 pagine |
| `ApprovvigionamentoSection.js` | 568 | CommessaHubPage |
| `VerificaCommittenzaSection.js` | 574 | CommessaHubPage |
| `RepositoryDocumentiSection.js` | 516 | CommessaHubPage |

---

## 7. DATABASE — COLLEZIONI (100)

### 7.1 Collezioni CON indici (22)

| Collezione | Doc | Indici |
|------------|-----|--------|
| activity_log | 194 | 4 indici |
| clients | 44 | 1 (user_id + business_name) |
| commesse | 19 | 5 indici |
| ddt_documents | 29 | 2 indici |
| diario_produzione | 7 | 2 indici |
| document_counters | 4 | 1 (counter_id) |
| fatture_ricevute | 131 | 5 indici |
| instruments | 3 | 1 (instrument_id) |
| invoices | 51 | 2 indici |
| material_batches | 12 | 2 indici |
| movimenti_bancari | 0 | 2 indici |
| notification_logs | 88 | 1 (checked_at) |
| operatori | 7 | 1 indice |
| preventivi | 109 | 3 indici |
| sessions | 3 | 1 (session_id) |
| user_sessions | 16 | 3 indici |
| users | 20 | 2 (email, user_id) |
| welders | 4 | 1 (welder_id) |

### 7.2 Collezioni SENZA indici (78) - SELEZIONE CRITICA

| Collezione | Doc | Rischio |
|------------|-----|---------|
| **obblighi_commessa** | 40 | CRITICO - Usato intensamente, mancano unique su dedupe_key |
| **commesse_normative** | 7 | CRITICO - Manca unique su commessa_id+normativa |
| **emissioni_documentali** | 9 | CRITICO - Manca unique su ramo+emission_type+seq |
| **cantieri_sicurezza** | 6 | ALTO - Manca unique su cantiere_id |
| **documenti_archivio** | 14 | ALTO - Usato da pacchetti documentali |
| **pacchetti_documentali** | 24 | MEDIO - Nessun indice |
| **pacchetti_committenza** | 29 | MEDIO - Manca unique su package_id |
| **analisi_committenza** | 1 | MEDIO - Manca unique su analysis_id |
| **istruttorie** | 8 | MEDIO - Nessun indice |
| **notifiche_smart** | 2 | BASSO - Pochi dati oggi ma crescera |
| (altre 68 collezioni) | vari | BASSO ad oggi |

### 7.3 Collezioni ZOMBIE (in DB, non referenziate in codice)

| Collezione | Doc | Valutazione |
|------------|-----|-------------|
| activity_log | 194 | Referenziata come `activity_log` ma grep non cattura la variabile |
| articoli_perizia | 14 | ZOMBIE - Probabile residuo perizie |
| catalogo_profili | 0 | ZOMBIE - Vuota, rimossa funzionalita |
| download_tokens | 44 | ZOMBIE - Token temporanei mai puliti |
| magazzino_sfridi | 1 | ZOMBIE |
| officina_alerts | 2 | ZOMBIE |
| officina_timers | 3 | ZOMBIE |
| project_costs | 66 | ZOMBIE - 66 documenti orfani |
| rdp_requests | 0 | ZOMBIE - Vuota |
| registro_nc | 2 | ZOMBIE |
| scadenzario_manutenzioni | 2 | Nota: diverso dal plurale usato in codice |
| sessions | 3 | Duplicato di user_sessions? |
| targhe_ce | 1 | ZOMBIE |

---

## 8. DIRECTORY ORFANE (root)

| Directory | Contenuto | Stato |
|-----------|-----------|-------|
| `/app/DoP` | VUOTA | DA ELIMINARE |
| `/app/Documenti` | VUOTA | DA ELIMINARE |
| `/app/Emissione` | VUOTA | DA ELIMINARE |
| `/app/Emissioni` | VUOTA | DA ELIMINARE |
| `/app/Evidence` | VUOTA | DA ELIMINARE |
| `/app/Gestione` | VUOTA | DA ELIMINARE |
| `/app/Rami` | VUOTA | DA ELIMINARE |
| `/app/Ramo` | VUOTA | DA ELIMINARE |
| `/app/Send` | VUOTA | DA ELIMINARE |

---

## 9. FILE LEGACY / SPEC / DOC (root)

| File | Dimensione | Stato |
|------|-----------|-------|
| `ARCHITETTURA_TECNICA.md` | 46 KB | LEGACY - Potenzialmente obsoleto |
| `PROJECT_KNOWLEDGE.md` | 42 KB | LEGACY - Grande, da verificare attualita |
| `PROJECT_MANIFESTO.md` | 410 B | LEGACY - Molto piccolo |
| `REPORT_EVOLUZIONE.md` | 6 KB | LEGACY - Report storico |
| `SPEC_FASE_A_MODELLO_GERARCHICO.md` | 10 KB | SPEC COMPLETATA |
| `SPEC_LIBRERIA_RISCHI_3_LIVELLI.md` | 13 KB | SPEC COMPLETATA |
| `SPEC_PACCHETTI_DOCUMENTALI.md` | 8 KB | SPEC COMPLETATA |
| `SPEC_POS_RENDERING_MAP.md` | 1.5 KB | SPEC COMPLETATA |
| `SPEC_POS_TEMPLATE_MAPPING.md` | 21 KB | SPEC COMPLETATA |
| `auth_testing.md` | 2 KB | LEGACY |
| `image_testing.md` | 1 KB | LEGACY |
| `backend_test.py` | ~100 | LEGACY - File test orfano |
| `test_result.md` | 5 KB | LEGACY |
| `yarn.lock` (root) | grande | DUPLICATO - Esiste gia in frontend/ |

---

## 10. INTEGRAZIONI ESTERNE

| Integrazione | Stato | File |
|-------------|-------|------|
| OpenAI GPT-4o | ATTIVO | via emergentintegrations |
| Resend (email) | ATTIVO | `email_service.py` |
| Object Storage | ATTIVO | `object_storage.py` |
| python-docx | ATTIVO | `pos_docx_generator.py` |
| WeasyPrint | ATTIVO | servizi PDF vari |
| Aruba SDI | ORFANO | `aruba_sdi.py` (mai importato) |
| FattureInCloud | PARZIALE | `fattureincloud_api.py` |
| Emergent Auth | ATTIVO | Google OAuth |

---

## 11. TEST (232 file, ~97K linee)

### Copertura per modulo:

| Area | File testati | File NON testati |
|------|-------------|-----------------|
| Routes | 54/78 | 24 senza test dedicati |
| Services | 7/58 | 51 senza test dedicati |
| Models | 0/17 | Coperti indirettamente via routes |

### Route critiche senza test dedicati:
- `auth.py`, `cantieri_sicurezza.py`, `commessa_ops_common.py`
- `invoices.py` (1979 linee!), `rilievi.py`, `dop_frazionata.py`
- `activity_log.py`, `db_cleanup.py`, `search.py`

### Service critici senza test dedicati:
- `evidence_gate_engine.py`, `segmentation_engine.py`
- `obblighi_commessa_service.py`, `pacchetti_documentali_service.py`
- `committenza_analysis_service.py`, `notification_scheduler.py`
- `email_service.py`, `object_storage.py`

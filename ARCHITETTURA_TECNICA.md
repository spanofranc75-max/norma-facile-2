# Norma Facile 2.0 — Documento di Architettura Tecnica

## Revisione per Analista Esterno

**Azienda:** Steel Project Design Srls  
**Dominio:** Carpenteria metallica — ERP per commesse, fatturazione, tracciabilità EN 1090 / EN 13241  
**Stack:** FastAPI (Python) + React + MongoDB + Emergent Cloud  
**Ultimo aggiornamento:** Marzo 2026

---

## INDICE

1. [Albero dei File](#1-albero-dei-file)
2. [Schema Database (Collezioni MongoDB)](#2-schema-database-collezioni-mongodb)
3. [Relazioni tra Entità](#3-relazioni-tra-entità-fk-logiche)
4. [Mappa dei Flussi (Logica di Business)](#4-mappa-dei-flussi-logica-di-business)
5. [Elenco Endpoint / Funzioni Chiave](#5-elenco-endpoint--funzioni-chiave)
6. [Regole Fondamentali](#6-regole-fondamentali)

---

## 1. Albero dei File

```
/app/
├── backend/
│   ├── main.py                          # Entry point FastAPI + middleware + router mounting
│   ├── server.py                        # Uvicorn launcher (supervisor-managed)
│   ├── core/
│   │   ├── config.py                    # Env vars, settings
│   │   ├── database.py                  # MongoDB connection (motor async)
│   │   └── security.py                  # Auth middleware (Google OAuth via Emergent)
│   │
│   ├── models/                          # Pydantic models (validazione I/O)
│   │   ├── invoice.py                   # Fattura attiva (FT, NC) + righe + totali
│   │   ├── client.py                    # Anagrafica clienti/fornitori
│   │   ├── ddt.py                       # Documento di Trasporto
│   │   ├── distinta.py                  # Bill of Materials (BOM) + optimizer
│   │   ├── certificazione.py            # Certificazione CE (EN 1090 / EN 13241)
│   │   ├── gate_certification.py        # Certificazione cancelli EN 13241 + EN 12453
│   │   ├── cam.py                       # Criteri Ambientali Minimi (DM 256/2022)
│   │   ├── fpc.py                       # Factory Production Control + lotti materiale
│   │   ├── perizia.py                   # Perizia/ispezione AI
│   │   ├── welder.py                    # Qualifica saldatori
│   │   ├── rilievo.py                   # Rilievo misure
│   │   ├── sopralluogo.py               # Sopralluogo
│   │   ├── audit.py                     # Audit non conformità
│   │   ├── instrument.py                # Registro strumenti di misura
│   │   ├── sicurezza.py                 # Sicurezza cantiere / POS
│   │   └── company_doc.py               # Documenti aziendali (ISO, ecc.)
│   │
│   ├── routes/                          # API endpoints (FastAPI routers)
│   │   ├── auth.py                      # /api/auth — Login Google OAuth
│   │   ├── commesse.py                  # /api/commesse — CRUD + lifecycle a stati
│   │   ├── commessa_ops.py              # /api/commesse/{id}/... — Approvvigionamento, produzione, conto lavoro, consegne, documenti, tracciabilità, prelievo magazzino
│   │   ├── preventivi.py                # /api/preventivi — CRUD + fatturazione progressiva (acconto/SAL/saldo)
│   │   ├── invoices.py                  # /api/invoices — Fatture attive (FT/NC)
│   │   ├── fatture_ricevute.py          # /api/fatture-ricevute — Fatture passive + imputazione + annulla imputazione
│   │   ├── ddt.py                       # /api/ddt — Documenti di Trasporto
│   │   ├── clients.py                   # /api/clients — Anagrafica + condizioni pagamento
│   │   ├── articoli.py                  # /api/articoli — Catalogo articoli + giacenza magazzino
│   │   ├── certificazioni.py            # /api/certificazioni — Dichiarazioni CE
│   │   ├── gate_certification.py        # /api/gate-cert — EN 13241 cancelli
│   │   ├── fpc.py                       # /api/fpc — Factory Production Control EN 1090 (saldatori, lotti, progetti)
│   │   ├── fascicolo_tecnico.py         # /api/fascicolo-tecnico — Fascicolo tecnico completo (DoP, CE, piano controllo, VT, registro saldatura)
│   │   ├── distinta.py                  # /api/distinte — Bill of Materials
│   │   ├── rilievi.py                   # /api/rilievi — Rilievi misure
│   │   ├── perizia.py                   # /api/perizie — Perizia AI (ispezione fotografica)
│   │   ├── cam.py                       # /api/cam — Criteri Ambientali Minimi
│   │   ├── cost_control.py              # /api/costs — Analisi margini + costi aziendali
│   │   ├── welders.py                   # /api/welders — Registro saldatori qualificati
│   │   ├── wps.py                       # /api/wps — Welding Procedure Specifications
│   │   ├── instruments.py               # /api/instruments — Registro strumenti taratura
│   │   ├── audits.py                    # /api/audits — Non conformità + report
│   │   ├── sicurezza.py                 # /api/sicurezza — Moduli sicurezza cantiere
│   │   ├── sopralluogo.py               # /api/sopralluoghi — Sopralluoghi
│   │   ├── company.py                   # /api/company — Impostazioni aziendali
│   │   ├── company_docs.py              # /api/company/documents — Documenti aziendali
│   │   ├── payment_types.py             # /api/payment-types — Condizioni pagamento
│   │   ├── dashboard.py                 # /api/dashboard — Statistiche globali
│   │   ├── backup.py                    # /api/admin/backup — Backup e ripristino
│   │   ├── notifications.py             # /api/notifications — Notifiche + scadenziario
│   │   ├── team.py                      # /api/team — Gestione team/utenti
│   │   ├── rdp.py                       # /api/preventivi/{id}/rdp — Richiesta Preventivo Fornitore
│   │   ├── consumables.py               # /api/consumables — Consumabili da fatture ricevute
│   │   ├── smart_assign.py              # /api/smart-assign — Assegnazione intelligente lotti
│   │   ├── quality_hub.py               # /api/quality-hub — Hub qualità
│   │   ├── catalogo.py                  # /api/catalogo — Catalogo profili acciaio
│   │   ├── engine.py                    # /api/engine — Motore normativo (regole EN 1090, EN 13241)
│   │   ├── vendor_api.py                # /api/vendor — API chiavi vendor
│   │   ├── qrcode_gen.py                # /api/qrcode — Generatore QR Code
│   │   ├── migrazione.py                # /api/migrazione — Tool migrazione dati
│   │   └── db_cleanup.py                # /api/admin/cleanup — Pulizia DB
│   │
│   └── services/                        # Logica di business, PDF, email
│       ├── margin_service.py            # Aggregatore costi commessa (margini)
│       ├── financial_service.py         # Servizi finanziari
│       ├── cost_calculator.py           # Calcolo costi
│       ├── payment_calculator.py        # Calcolo scadenze pagamento
│       ├── invoice_service.py           # Logica fatturazione
│       ├── invoice_line_processor.py    # Processore righe fattura
│       ├── email_service.py             # Invio email (Resend)
│       ├── email_preview.py             # Preview email nel browser
│       ├── vision_analysis.py           # Analisi AI immagini (GPT-4o Vision)
│       ├── fattureincloud_api.py        # Integrazione FattureInCloud (SDI)
│       ├── xml_service.py               # Generazione XML fattura elettronica
│       ├── object_storage.py            # Storage oggetti (Emergent S3)
│       ├── notification_scheduler.py    # Scheduler notifiche
│       ├── optimizer.py                 # Ottimizzatore taglio barre
│       ├── thermal_calc.py              # Calcolo trasmittanza termica Uw
│       ├── fascicolo_generator.py       # Generatore fascicolo tecnico
│       ├── dossier_generator.py         # Generatore dossier commessa
│       ├── pdf_service.py               # Base PDF engine
│       ├── pdf_template.py              # Template PDF v1
│       ├── pdf_template_v2.py           # Template PDF v2
│       ├── pdf_invoice_modern.py        # PDF fattura moderna
│       ├── pdf_fascicolo_tecnico.py     # PDF fascicolo tecnico
│       ├── pdf_super_fascicolo.py       # PDF super-fascicolo
│       ├── pdf_scheda_rintracciabilita.py # PDF Mod.07 tracciabilità materiali
│       ├── pdf_cam_declaration.py       # PDF dichiarazione CAM
│       ├── pdf_cam_report.py            # PDF report CAM aziendale
│       ├── pdf_green_certificate.py     # Certificato green
│       ├── pdf_ncr.py                   # PDF non conformità
│       ├── pdf_procurement.py           # PDF ordini/RdP
│       ├── perizia_pdf_service.py       # PDF perizia
│       ├── certificazione_pdf_service.py # PDF certificazione CE
│       └── ...altri PDF services
│
└── frontend/
    └── src/
        ├── App.js                       # Routing principale
        ├── contexts/AuthContext.js       # Contesto autenticazione
        ├── components/
        │   ├── CommessaOpsPanel.js       # Pannello operativo commessa (2800+ righe)
        │   ├── InvoiceGenerationModal.js # Modale fatturazione progressiva
        │   ├── DashboardLayout.js        # Layout con sidebar
        │   ├── ConfirmProvider.js        # Provider conferme (sostituisce window.confirm)
        │   ├── GateCertificationPanel.js # Pannello certificazione cancelli
        │   ├── FascicoloTecnicoSection.js # Sezione fascicolo tecnico
        │   ├── PDFPreviewModal.js        # Preview PDF (react-pdf)
        │   ├── EmailPreviewDialog.js     # Preview email
        │   └── ui/                       # Componenti Shadcn/UI
        │
        └── pages/
            ├── Dashboard.js              # Homepage/cruscotto
            ├── CommessaHubPage.js         # Hub commessa (dettaglio + moduli)
            ├── PlanningPage.js            # Planning/Kanban board
            ├── PreventiviPage.js          # Lista preventivi
            ├── PreventivoEditorPage.js    # Editor preventivo
            ├── InvoicesPage.js            # Lista fatture emesse
            ├── InvoiceEditorPage.js       # Editor fattura
            ├── FattureRicevutePage.js     # Fatture ricevute (passive)
            ├── DDTListPage.js             # Lista DDT
            ├── DDTEditorPage.js           # Editor DDT
            ├── ArticoliPage.js            # Catalogo articoli + giacenza
            ├── ClientsPage.js             # Anagrafica clienti/fornitori
            ├── CertificazioniPage.js      # Certificazioni CE
            ├── TracciabilitaPage.js        # Tracciabilità materiali
            ├── DistintePage.js            # Distinte base
            ├── DistintaEditorPage.js      # Editor BOM
            ├── CostControlPage.js         # Controllo costi
            ├── MarginAnalysisPage.js      # Analisi margini predittiva
            ├── ScadenziarioPage.js        # Scadenziario pagamenti
            ├── WeldersPage.js             # Registro saldatori
            ├── WPSPage.js                 # Specifiche procedura saldatura
            ├── InstrumentsPage.js         # Registro strumenti
            ├── QualityHubPage.js          # Hub qualità
            ├── PeriziaListPage.js         # Lista perizie
            ├── PeriziaEditorPage.js       # Editor perizia AI
            ├── RilieviPage.js             # Rilievi
            ├── SopralluoghiPage.js        # Sopralluoghi
            ├── AuditPage.js               # Non conformità
            ├── SettingsPage.js            # Impostazioni
            └── ...altre pagine
```

---

## 2. Schema Database (Collezioni MongoDB)

### 2.1 Anagrafica

#### `clients` — Clienti e Fornitori
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `client_id` | string (PK) | ID univoco `cli_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `business_name` | string | Ragione sociale |
| `client_type` | enum | `cliente`, `fornitore`, `cliente_fornitore` |
| `persona_fisica` | bool | Persona fisica vs giuridica |
| `partita_iva` | string | P.IVA |
| `codice_fiscale` | string | C.F. |
| `codice_sdi` | string | Codice destinatario SDI (default `0000000`) |
| `pec` | string | PEC per fattura elettronica |
| `address`, `cap`, `city`, `province`, `country` | string | Sede legale |
| `phone`, `cellulare`, `email` | string | Contatti |
| `contacts[]` | array | Persone di riferimento (tipo, nome, email, preferenze invio) |
| `payment_type_id` | string (FK → payment_types) | Condizione pagamento come cliente |
| `supplier_payment_type_id` | string (FK → payment_types) | Condizione pagamento come fornitore |
| `iban`, `banca` | string | Coordinate bancarie |
| `created_at`, `updated_at` | datetime | Timestamp |

#### `payment_types` — Condizioni di Pagamento
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `pt_id` | string (PK) | ID univoco |
| `user_id` | string (FK → users) | Proprietario |
| `label` | string | Es: "Bonifico 30gg DFFM" |
| `method` | enum | `bonifico`, `riba`, `contanti`, `carta` |
| `installments[]` | array | Rate: `{days, percentage}` |
| `fine_mese` | bool | Scadenza a fine mese |

---

### 2.2 Commessa (Cuore del Sistema)

#### `commesse` — Commesse / Lavori
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `commessa_id` | string (PK) | ID univoco `comm_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `numero` | int | Numero progressivo commessa |
| `title` | string | Titolo/descrizione lavoro |
| `client_id` | string (FK → clients) | Cliente |
| `client_name` | string | Nome cliente (denormalizzato) |
| `description` | string | Descrizione estesa |
| `riferimento` | string | Riferimento esterno |
| `value` | float | **Valore preventivo (IMPONIBILE)** |
| `stato` | enum | Lifecycle: `richiesta → bozza → rilievo_completato → firmato → in_produzione → fatturato → chiuso` |
| `status` | string | Kanban column: `preventivo`, `approvvigionamento`, `lavorazione`, `verniciatura`, `pronto_consegna`, `completato` |
| `priority` | enum | `bassa`, `media`, `alta`, `urgente` |
| `deadline` | string | Data consegna prevista |
| `cantiere` | object | `{indirizzo, citta, cap, contesto, ambiente}` |
| `classe_exc` | string | Classe di esecuzione EN 1090: `EXC1`-`EXC4` |
| `tipologia_chiusura` | string | Tipo prodotto: cancello, ringhiera, porta, scala, struttura |
| `moduli` | object | Collegamenti a moduli *(vedi sotto)* |
| `approvvigionamento` | object | **Sub-documento: procurement** *(vedi 2.2a)* |
| `fasi_produzione[]` | array | **Fasi di produzione** *(vedi 2.2b)* |
| `conto_lavoro[]` | array | **Lavorazioni esterne** *(vedi 2.2c)* |
| `consegne[]` | array | **Consegne effettuate** |
| `costi_reali[]` | array | **Costi diretti imputati** *(vedi 2.2d)* |
| `ore_lavorate` | float | Ore manodopera interna |
| `eventi[]` | array | Storico eventi (event-driven lifecycle) |
| `created_at`, `updated_at` | datetime | Timestamp |

##### `commesse.moduli` — Collegamenti a Moduli
```json
{
  "rilievo_id":         "ril_xxxx",      // FK → rilievi
  "distinta_id":        "dist_xxxx",     // FK → distinte
  "preventivo_id":      "prev_xxxx",     // FK → preventivi
  "fatture_ids":        ["inv_xxxx"],    // FK[] → invoices
  "ddt_ids":            ["ddt_xxxx"],    // FK[] → ddt
  "fpc_project_id":     "fpc_xxxx",      // FK → fpc_projects
  "certificazione_id":  "cert_xxxx"      // FK → certificazioni
}
```

##### 2.2a — `commesse.approvvigionamento` (Procurement)
```json
{
  "richieste": [{
    "rdp_id": "rdp_xxxx",
    "fornitore_id": "cli_xxxx",     // FK → clients (fornitore)
    "fornitore_nome": "string",
    "materiali": [{ "descrizione", "quantita", "unita_misura" }],
    "stato": "bozza|inviata|risposta|ordinata",
    "created_at": "datetime"
  }],
  "ordini": [{
    "ordine_id": "oda_xxxx",
    "rdp_id": "rdp_xxxx",          // FK → richieste (opzionale)
    "fornitore_id": "cli_xxxx",     // FK → clients
    "fornitore_nome": "string",
    "righe": [{ "descrizione", "quantita", "prezzo_unitario", "importo" }],
    "importo_totale": 1500.00,
    "stato": "emesso|confermato|consegnato",
    "created_at": "datetime"
  }],
  "arrivi": [{
    "arrivo_id": "arr_xxxx",
    "ddt_fornitore": "string",      // Numero DDT fornitore
    "data_ddt": "date",
    "fornitore_nome": "string",
    "ordine_id": "oda_xxxx",        // FK → ordini (opzionale)
    "materiali": [{
      "descrizione": "string",
      "quantita": 100,               // Quantità arrivata
      "quantita_utilizzata": 75,     // Quantità usata per la commessa (opzionale)
      "prezzo_unitario": 12.50,      // Prezzo unitario (opzionale)
      "unita_misura": "kg",
      "ordine_id": "oda_xxxx",
      "richiede_cert_31": true,
      "numero_colata": "C12345",     // Heat number (EN 1090)
      "material_batch_id": "batch_xxxx",  // FK → material_batches
      "certificato_doc_id": "doc_xxxx"    // FK → commessa_documents
    }],
    "note": "string",
    "verificato": false,
    "created_at": "datetime"
  }]
}
```

##### 2.2b — `commesse.fasi_produzione[]`
```json
{
  "tipo": "taglio|piegatura|saldatura|assemblaggio|finitura|verniciatura",
  "label": "Taglio",
  "stato": "non_iniziato|in_corso|completato",
  "percentuale": 0-100,
  "data_inizio": "datetime",
  "data_fine": "datetime",
  "note": "string"
}
```

##### 2.2c — `commesse.conto_lavoro[]` (Subcontracting)
```json
{
  "cl_id": "cl_xxxx",
  "tipo": "verniciatura|zincatura|trattamento_termico|lavorazione_meccanica|...",
  "fornitore_id": "cli_xxxx",   // FK → clients (fornitore)
  "fornitore_nome": "string",
  "importo": 500.00,
  "stato": "da_inviare|inviato|in_lavorazione|rientrato|verificato",
  "ddt_invio_id": "ddt_xxxx",   // FK → ddt (DDT di invio)
  "rientro": { "data", "ddt_numero", "stato_qualita", "difetti[]", "certificati_ids[]" },
  "created_at": "datetime"
}
```

##### 2.2d — `commesse.costi_reali[]`
```json
{
  "cost_id": "cost_xxxx",
  "tipo": "materiali|manodopera|conto_lavoro|trasporto|materiale_magazzino|altro",
  "descrizione": "string",
  "fornitore": "string",
  "importo": 1234.56,
  "quantita": 100,
  "prezzo_unitario": 12.35,
  "unita_misura": "kg",
  "articolo_id": "art_xxxx",   // FK → articoli (se prelievo da magazzino)
  "fr_id": "fr_xxxx",          // FK → fatture_ricevute (se da imputazione fattura)
  "data": "datetime",
  "note": "string"
}
```

---

### 2.3 Fatturazione

#### `preventivi` — Preventivi
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `preventivo_id` | string (PK) | ID univoco `prev_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `number` | string | Numero: `PRV-2026-0001` |
| `client_id` | string (FK → clients) | Cliente |
| `status` | enum | `bozza`, `inviato`, `accettato`, `rifiutato`, `scaduto` |
| `lines[]` | array | Righe: `{description, quantity, unit_price, discount_percent, vat_rate, line_total, vat_amount}` |
| `totals` | object | `{subtotal, imponibile, total_vat, total}` |
| `acconto` | float | % acconto richiesto |
| `valid_days` | int | Giorni validità |
| `created_at`, `updated_at` | datetime | |

> **REGOLA FATTURAZIONE PROGRESSIVA:**  
> Il campo `totals.imponibile` è SEMPRE la base per il calcolo di acconti e SAL.  
> `totals.total` include l'IVA ed è solo per visualizzazione.

#### `invoices` — Fatture Emesse (Attive)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `invoice_id` | string (PK) | ID univoco `inv_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `document_type` | enum | `FT` (fattura), `NC` (nota credito) |
| `document_number` | string | Numero: `FT-2026-001` |
| `client_id` | string (FK → clients) | Cliente |
| `status` | enum | `bozza → emessa → inviata_sdi → accettata → pagata` |
| `lines[]` | array | Righe fattura (stessa struttura preventivo) |
| `totals` | object | `{subtotal, vat_breakdown, total_vat, total_document, total_to_pay}` |
| `tax_settings` | object | Rivalsa INPS, cassa, ritenuta d'acconto |
| `payment_method` | enum | `bonifico`, `riba`, `contanti`, `carta` |
| `payment_terms` | string | `30gg`, `60gg`, `30-60gg`, ecc. |
| `payment_type_id` | string (FK → payment_types) | |
| `progressive_from_preventivo` | string (FK → preventivi) | Se fattura progressiva |
| `progressive_type` | string | `acconto`, `sal`, `saldo` |
| `progressive_amount` | float | **Importo IMPONIBILE della rata** |
| `pagamenti[]` | array | Registrazioni pagamento |
| `issue_date`, `due_date` | date | Date |
| `converted_from` | string (FK → invoices/ddt) | Origine conversione |
| `created_at`, `updated_at` | datetime | |

#### `fatture_ricevute` — Fatture Passive (Ricevute)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `fr_id` | string (PK) | ID univoco `fr_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `fornitore_id` | string (FK → clients) | Fornitore |
| `fornitore_nome` | string | Nome fornitore |
| `numero_documento` | string | Numero fattura fornitore |
| `data_documento` | date | Data fattura |
| `totale_documento` | float | Totale IVA inclusa |
| `imponibile` | float | Imponibile |
| `iva` | float | IVA |
| `status` | enum | `da_registrare`, `registrata`, `pagata` |
| `imputazione` | object | **Assegnazione costo** *(vedi sotto)* |
| `xml_raw` | string | XML FattureInCloud originale |
| `righe[]` | array | Righe fattura estratte |
| `created_at`, `updated_at` | datetime | |

##### `fatture_ricevute.imputazione` — Assegnazione Costo
```json
{
  "destinazione": "commessa|magazzino|generale",
  "commessa_id": "comm_xxxx",    // FK → commesse (se destinazione=commessa)
  "target_id": "comm_xxxx",      // Alias per retrocompatibilità
  "importo": 1500.00,
  "data": "datetime"
}
```

#### `ddt` — Documenti di Trasporto
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `ddt_id` | string (PK) | ID univoco `ddt_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `document_number` | string | Numero: `DDT-2026-001` |
| `ddt_type` | enum | `vendita`, `conto_lavoro`, `rientro_conto_lavoro` |
| `client_id` | string (FK → clients) | Destinatario |
| `lines[]` | array | `{codice_articolo, description, quantity, unit_price, vat_rate}` |
| `destinazione` | object | Sede destinazione merce |
| `causale_trasporto` | string | Causale (Vendita, C/Lavorazione, Reso) |
| `peso_lordo_kg`, `peso_netto_kg` | float | Pesi |
| `status` | string | `bozza`, `emesso`, `fatturato` |
| `converted_to_invoice` | string (FK → invoices) | Se convertito in fattura |
| `created_at`, `updated_at` | datetime | |

---

### 2.4 Magazzino e Articoli

#### `articoli` — Catalogo Articoli / Magazzino
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `articolo_id` | string (PK) | ID univoco `art_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `codice` | string | Codice articolo |
| `descrizione` | string | Descrizione |
| `categoria` | string | `profilo`, `accessorio`, `ferramenta`, `materiale`, `altro` |
| `unita_misura` | string | `kg`, `pz`, `m`, `mq` |
| `prezzo_unitario` | float | Ultimo prezzo noto |
| `aliquota_iva` | string | `22`, `10`, `4`, `0` |
| `giacenza` | float | **Quantità in magazzino** |
| `fornitore_nome` | string | Fornitore abituale |
| `fornitore_id` | string (FK → clients) | |
| `storico_prezzi[]` | array | `{prezzo, data, fonte}` |
| `created_at`, `updated_at` | datetime | |

---

### 2.5 Tracciabilità e Normativa EN 1090

#### `material_batches` — Lotti Materiale (Tracciabilità EN 1090)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `batch_id` | string (PK) | ID univoco `batch_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `commessa_id` | string (FK → commesse) | Commessa di riferimento |
| `supplier_name` | string | Fornitore materiale |
| `material_type` | string | Tipo acciaio: `S275JR`, `S355J2`, ecc. |
| `heat_number` | string | **Numero colata** (dalla certa 3.1) |
| `dimensions` | string | Profilo: `IPE 100`, `HEB 120` |
| `posizione` | string | Posizione nel disegno |
| `n_pezzi` | int | Numero pezzi |
| `numero_certificato` | string | Numero cert. 3.1 |
| `ddt_numero` | string | DDT fornitore |
| `disegno_numero` | string | Riferimento disegno |
| `has_certificate` | bool | Certificato 3.1 caricato |
| `certificate_filename` | string | Nome file certificato |
| `source_doc_id` | string (FK → commessa_documents) | Doc sorgente caricato |
| `source_arrivo_id` | string | FK → arrivo in approvvigionamento |
| `received_date` | string | Data ricezione |
| `created_at` | datetime | |

#### `fpc_projects` — Progetti FPC (Factory Production Control)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `project_id` | string (PK) | ID univoco `fpc_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `preventivo_id` | string (FK → preventivi) | Preventivo collegato |
| `status` | enum | `in_progress`, `completed`, `archived` |
| `fpc_data` | object | Classe esecuzione, WPS, saldatore, lotti, controlli |
| `fpc_data.execution_class` | string | `EXC1`-`EXC4` |
| `fpc_data.wps_id` | string (FK → wps_documents) | |
| `fpc_data.welder_id` | string (FK → welders) | |
| `fpc_data.material_batches[]` | string[] | FK[] → material_batches |
| `fpc_data.controls[]` | array | Controlli FPC effettuati |
| `fpc_data.ce_label_generated` | bool | Etichetta CE generata |

#### `certificazioni` — Dichiarazioni di Prestazione (CE)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `cert_id` | string (PK) | ID univoco `cert_xxxx` |
| `user_id` | string (FK → users) | Proprietario |
| `distinta_id` | string (FK → distinte) | BOM collegata |
| `client_id` | string (FK → clients) | Cliente |
| `standard` | enum | `EN 1090-1`, `EN 13241` |
| `product_description` | string | Descrizione prodotto |
| `declaration_number` | string | Numero dichiarazione DoP |
| `technical_specs` | object | Specifiche tecniche (classe esecuzione, durabilità, reazione fuoco, ecc.) |
| `status` | enum | `bozza`, `emessa`, `revisionata` |

#### `gate_certifications` — Certificazione Cancelli (EN 13241 + EN 12453)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `cert_id` | string (PK) | ID univoco `gc_xxxx` |
| `commessa_id` | string (FK → commesse) | Commessa |
| `user_id` | string (FK → users) | |
| `tipo_chiusura` | enum | Tipo cancello/portone |
| `azionamento` | enum | `manuale`, `motorizzato` |
| `resistenza_vento` | enum | Classe 0-5 |
| `analisi_rischi[]` | array | Rischi e misure adottate |
| `prove_forza[]` | array | Prove forza dinamica/statica (< 400N / < 150N) |
| `motore_marca/modello/matricola` | string | Dati automazione |
| `strumento_id` | string (FK → instruments) | Strumento usato per prove |

---

### 2.6 CAM (Criteri Ambientali Minimi)

#### `calcoli_cam` — Calcoli CAM per Commessa
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `calcolo_id` | string (PK) | |
| `commessa_id` | string (FK → commesse) | |
| `peso_totale_kg` | float | Peso totale acciaio |
| `peso_riciclato_kg` | float | Peso acciaio riciclato |
| `percentuale_riciclato_totale` | float | % riciclato (deve superare soglia) |
| `conforme_cam` | bool | Conforme DM 256/2022 |
| `righe[]` | array | Dettaglio per materiale: peso, %, metodo produttivo, certificazione |

#### `lotti_cam` — Lotti Materiale con Dati CAM
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `lotto_id` | string (PK) | |
| `commessa_id` | string (FK → commesse) | |
| `batch_id` | string (FK → material_batches) | Lotto materiale EN 1090 |
| `percentuale_riciclato` | float | % acciaio riciclato |
| `metodo_produttivo` | enum | `forno_elettrico_non_legato/legato`, `ciclo_integrale` |
| `tipo_certificazione` | enum | `epd`, `remade_in_italy`, `dichiarazione_produttore` |
| `km_approvvigionamento` | float | Distanza fornitore (km) |

---

### 2.7 Qualità e Strumenti

#### `welders` — Registro Saldatori Qualificati
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `welder_id` | string (PK) | |
| `name` | string | Nome saldatore |
| `qualification_level` | string | Es: `ISO 9606-1 135 P BW` |
| `license_expiry` | date | Scadenza patentino |
| `has_certificate` | bool | Certificato caricato |

#### `wps_documents` — Welding Procedure Specifications
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `wps_id` | string (PK) | |
| `codice` | string | Codice WPS (es: WPS-001) |
| `processo` | string | Processo saldatura (135, 136, 111...) |
| `materiale_base` | string | Materiale |
| `posizioni` | string | Posizioni di saldatura |

#### `instruments` — Registro Strumenti di Misura
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `instrument_id` | string (PK) | |
| `name` | string | Nome strumento |
| `serial_number` | string | Matricola |
| `last_calibration` | date | Ultima taratura |
| `next_calibration` | date | Prossima taratura |
| `certificate_doc_id` | string | Certificato taratura |

#### `audits` — Non Conformità
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `audit_id` | string (PK) | |
| `commessa_id` | string (FK → commesse) | |
| `tipo` | string | `nc_interna`, `nc_fornitore`, `nc_cliente`, `reclamo` |
| `gravita` | enum | `minore`, `maggiore`, `critica` |
| `stato` | enum | `aperta`, `in_trattamento`, `chiusa` |
| `azione_correttiva` | string | Descrizione azione |

---

### 2.8 Altre Collezioni

| Collezione | Descrizione |
|------------|-------------|
| `users` | Utenti (Google OAuth) |
| `user_profiles` | Profili utente |
| `company_settings` | Impostazioni aziendali (logo, dati, costo orario) |
| `company_costs` | Costi aziendali (costo orario pieno per calcolo margini) |
| `company_docs` | Documenti aziendali (ISO, attestazioni) |
| `rilievi` | Rilievi misure in cantiere |
| `distinte` | Distinte base (Bill of Materials) |
| `commessa_documents` | Repository documenti per commessa (cert. 3.1, foto, ecc.) |
| `notification_logs` | Log notifiche inviate |
| `backup_log` | Storico backup |
| `document_counters` | Contatori progressivi documenti (FT, NC, DDT, PRV) |
| `norme_config` | Configurazione normative (regole motore EN 1090) |
| `vendor_catalogs` | Cataloghi fornitori |
| `pos_documents` | Documenti POS (Piano Operativo Sicurezza) |

---

## 3. Relazioni tra Entità (FK Logiche)

```
users
  └─── clients (clienti e fornitori)
  └─── commesse (lavori)
         ├─── moduli.preventivo_id ──→ preventivi
         ├─── moduli.rilievo_id ────→ rilievi
         ├─── moduli.distinta_id ───→ distinte
         ├─── moduli.fatture_ids[] ─→ invoices
         ├─── moduli.ddt_ids[] ─────→ ddt
         ├─── moduli.fpc_project_id → fpc_projects
         ├─── moduli.certificazione_id → certificazioni
         │
         ├─── approvvigionamento.richieste[].fornitore_id → clients
         ├─── approvvigionamento.ordini[].fornitore_id ──→ clients
         ├─── approvvigionamento.arrivi[].materiali[].material_batch_id → material_batches
         ├─── approvvigionamento.arrivi[].materiali[].certificato_doc_id → commessa_documents
         │
         ├─── conto_lavoro[].fornitore_id → clients
         ├─── conto_lavoro[].ddt_invio_id → ddt
         │
         ├─── costi_reali[].fr_id ──→ fatture_ricevute
         ├─── costi_reali[].articolo_id → articoli
         │
         ├─── gate_certifications (1:1) ──→ gate_certifications
         └─── calcoli_cam ──→ calcoli_cam

  └─── preventivi
         ├─── client_id ──→ clients
         └─── (fatturazione progressiva) ──→ invoices.progressive_from_preventivo

  └─── invoices (fatture emesse)
         ├─── client_id ──→ clients
         ├─── payment_type_id ──→ payment_types
         ├─── progressive_from_preventivo ──→ preventivi
         └─── converted_from ──→ ddt / invoices

  └─── fatture_ricevute (fatture passive)
         ├─── fornitore_id ──→ clients
         └─── imputazione.commessa_id ──→ commesse

  └─── ddt
         ├─── client_id ──→ clients
         └─── converted_to_invoice ──→ invoices

  └─── material_batches (tracciabilità)
         ├─── commessa_id ──→ commesse
         └─── source_doc_id ──→ commessa_documents

  └─── fpc_projects
         ├─── preventivo_id ──→ preventivi
         ├─── fpc_data.wps_id ──→ wps_documents
         ├─── fpc_data.welder_id ──→ welders
         └─── fpc_data.material_batches[] ──→ material_batches

  └─── certificazioni (CE)
         ├─── distinta_id ──→ distinte
         └─── client_id ──→ clients

  └─── gate_certifications
         ├─── commessa_id ──→ commesse
         └─── strumento_id ──→ instruments
```

---

## 4. Mappa dei Flussi (Logica di Business)

### FLUSSO 1: Dalla Richiesta alla Fattura Finale

```
1. RICHIESTA/SOPRALLUOGO
   └→ Creazione commessa (stato: "richiesta" o "bozza")
   └→ [Opzionale] Sopralluogo con rilievo misure
   └→ [Opzionale] Creazione BOM (distinta materiali)
   └→ Collegamento moduli: rilievo_id, distinta_id

2. PREVENTIVO
   └→ Creazione preventivo dal rilievo/BOM
   └→ Calcolo totali: subtotal → sconto → IMPONIBILE → IVA → TOTALE
   └→ Invio al cliente (email con PDF)
   └→ Accettazione → stato commessa: "firmato"
   └→ Collegamento: commessa.moduli.preventivo_id = prev_id

3. APPROVVIGIONAMENTO
   └→ RdP (Richiesta Preventivo Fornitore) → invio email fornitore
   └→ OdA (Ordine di Acquisto) → conferma e invio
   └→ Arrivo materiale → registrazione DDT + certificati 3.1
       ├→ Se EN 1090: creazione lotto in material_batches (heat_number)
       ├→ Se quantita_utilizzata < quantita: resto → giacenza in articoli
       └→ Costi → approvvigionamento.ordini[].importo_totale

4. PRODUZIONE
   └→ Inizializzazione fasi: taglio → saldatura → assemblaggio → finitura
   └→ Tracciamento avanzamento % per fase
   └→ Registrazione ore lavorate → calcolo costo manodopera
   └→ Stato commessa: "in_produzione"

5. CONTO LAVORO (Lavorazioni Esterne)
   └→ Creazione DDT conto lavoro (invio a verniciatore/zincatore)
   └→ Rientro con verifica qualità
   └→ Costo → conto_lavoro[].importo → margini

6. FATTURAZIONE (Progressiva o Diretta)
   └→ Acconto %: percentuale calcolata su IMPONIBILE preventivo (MAI su totale con IVA)
   └→ SAL: per righe selezionate del preventivo
   └→ Saldo: rimanenza dopo acconti + SAL
   └→ Ogni fattura registra progressive_amount (= IMPONIBILE della rata)
   └→ Invio SDI tramite FattureInCloud
   └→ Stato commessa: "fatturato"

7. CONSEGNA E CHIUSURA
   └→ Creazione DDT vendita → conversione opzionale in fattura
   └→ Generazione fascicolo tecnico completo (DoP + CE + controlli)
   └→ Stato commessa: "chiuso"
```

### FLUSSO 2: Tracciabilità Materiale EN 1090 (dal Fornitore alla Marcatura CE)

```
1. RICEZIONE MATERIALE
   └→ commessa_ops: POST /{cid}/approvvigionamento/arrivi
   └→ Per ogni materiale con numero_colata:
       └→ Creazione record in material_batches
           { batch_id, commessa_id, heat_number, material_type, supplier_name }

2. CARICAMENTO CERTIFICATO 3.1
   └→ commessa_ops: POST /{cid}/documenti (upload file)
   └→ commessa_ops: POST /{cid}/documenti/{doc_id}/parse-certificato
       └→ AI (GPT-4o Vision) analizza il PDF del certificato
       └→ Estrae: numero colata, tipo acciaio, proprietà meccaniche
       └→ Collega certificato al material_batch

3. SCHEDA RINTRACCIABILITA' (MOD. 07)
   └→ commessa_ops: GET /{cid}/scheda-rintracciabilita-pdf
       └→ Genera PDF con tabella:
           | Materiale | Colata | Fornitore | DDT | Cert. | Posizione | Pezzi |
   └→ Aggrega dati da: material_batches + approvvigionamento.arrivi

4. PROGETTO FPC (Factory Production Control)
   └→ fpc: POST /projects → crea progetto collegato al preventivo
   └→ fpc: PUT /projects/{id}/fpc → associa:
       ├→ Classe esecuzione (EXC1-EXC4)
       ├→ WPS (procedura saldatura)
       ├→ Saldatore qualificato
       ├→ Lotti materiale (batch_ids)
       └→ Controlli FPC completati (dimensionale, visivo, NDT, ecc.)
   └→ Quando tutti i controlli OK → ce_label_generated = true

5. CERTIFICAZIONE CE (DoP)
   └→ certificazioni: POST / → crea dichiarazione di prestazione
       ├→ Standard: EN 1090-1 o EN 13241
       ├→ Specifiche tecniche: classe esecuzione, durabilità, reazione fuoco
       ├→ Per EN 13241 (cancelli): anche prove forza, analisi rischi
       └→ Collega a distinta_id per lista materiali

6. FASCICOLO TECNICO COMPLETO
   └→ fascicolo_tecnico: GET /{cid}/fascicolo-completo-pdf
       └→ Genera PDF unico con:
           ├→ DoP (Dichiarazione di Prestazione)
           ├→ Etichetta CE
           ├→ Piano di Controllo Qualità
           ├→ Rapporto VT (Visual Testing)
           ├→ Registro Saldature
           ├→ Riesame Tecnico
           └→ Scheda Rintracciabilità Materiali
```

### FLUSSO 3: Gestione Costi e Margini

```
FONTI DI COSTO (aggregati da margin_service.py):
├→ costi_reali[] sulla commessa (inclusi prelievi magazzino)
├→ fatture_ricevute con imputazione.commessa_id = commessa_id
├→ conto_lavoro[].importo
├→ ore_lavorate × costo_orario_pieno (da company_costs)
└→ approvvigionamento.ordini[].importo_totale (OdA)

FONTI DI RICAVO:
├→ commessa.value (valore preventivo)
└→ Fatture emesse collegate

MARGINE = Ricavo - Costi Totali
MARGINE % = (Margine / Ricavo) × 100
+ Previsione AI: rischio e margine stimato a fine commessa
```

### FLUSSO 4: Fatture Ricevute e Imputazione

```
1. IMPORTAZIONE
   └→ Upload XML (singolo o batch) da FattureInCloud/SDI
   └→ Parser XML estrae: fornitore, righe, importi, IVA
   └→ Stato: "da_registrare"

2. REGISTRAZIONE
   └→ Operatore verifica dati e conferma
   └→ Stato: "registrata"

3. IMPUTAZIONE COSTI
   └→ POST /{fr_id}/imputa
       ├→ destinazione: "commessa" → aggiunge costo a costi_reali[]
       ├→ destinazione: "magazzino" → aggiunge a giacenza articoli
       └→ destinazione: "generale" → solo flag, nessun collegamento

4. ANNULLA IMPUTAZIONE
   └→ POST /{fr_id}/annulla-imputazione
       ├→ Rimuove costo da commessa.costi_reali[] (pull by fr_id)
       ├→ Pulisce campo imputazione dalla fattura
       └→ Ripristina stato a "da_registrare"

5. PAGAMENTO
   └→ Registrazione pagamento → stato: "pagata"
   └→ Scadenziario calcola rate secondo condizioni pagamento fornitore
```

### FLUSSO 5: Gestione Magazzino

```
1. ENTRATA MERCE (da arrivo materiale)
   └→ Se quantita_utilizzata < quantita:
       └→ resto = quantita - quantita_utilizzata
       └→ Se articolo esiste in catalogo: incrementa giacenza
       └→ Se non esiste: crea nuovo articolo con giacenza = resto

2. PRELIEVO DA MAGAZZINO
   └→ POST /commesse/{cid}/preleva-da-magazzino
       ├→ Verifica giacenza sufficiente
       ├→ Decrementa giacenza in articoli
       ├→ Aggiunge costo in commessa.costi_reali[]
       │   tipo: "materiale_magazzino"
       │   importo: quantita × prezzo_unitario
       └→ Evento: "PRELIEVO_MAGAZZINO"

3. ESTRAZIONE CONSUMABILI
   └→ Da fatture ricevute → estrazione automatica righe come articoli
   └→ Aggiornamento storico prezzi
```

---

## 5. Elenco Endpoint / Funzioni Chiave

### 5.1 Commesse e Operazioni

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/commesse` | Lista commesse (filtri per stato, kanban) |
| POST | `/api/commesse` | Crea commessa |
| GET | `/api/commesse/{id}` | Dettaglio commessa |
| PUT | `/api/commesse/{id}` | Aggiorna commessa |
| DELETE | `/api/commesse/{id}` | Elimina commessa |
| POST | `/api/commesse/{id}/eventi` | Registra evento lifecycle |
| POST | `/api/commesse/{id}/link-module` | Collega modulo |
| GET | `/api/commesse/{id}/ops` | **Dati operativi completi** |
| POST | `/api/commesse/{id}/approvvigionamento/richieste` | Crea RdP |
| POST | `/api/commesse/{id}/approvvigionamento/ordini` | Crea OdA |
| POST | `/api/commesse/{id}/approvvigionamento/arrivi` | **Registra arrivo materiale** (con partial usage) |
| POST | `/api/commesse/{id}/produzione/init` | Inizializza fasi produzione |
| PUT | `/api/commesse/{id}/produzione/{fase}` | Aggiorna fase produzione |
| POST | `/api/commesse/{id}/conto-lavoro` | Crea lavorazione esterna |
| POST | `/api/commesse/{id}/conto-lavoro/{cl_id}/rientro` | Registra rientro |
| POST | `/api/commesse/{id}/consegne` | Crea consegna |
| POST | `/api/commesse/{id}/documenti` | Upload documento |
| POST | `/api/commesse/{id}/documenti/{doc_id}/parse-certificato` | **AI analisi certificato 3.1** |
| POST | `/api/commesse/{id}/preleva-da-magazzino` | **Prelievo da stock → commessa** |
| GET | `/api/commesse/{id}/scheda-rintracciabilita-pdf` | **PDF Mod.07 tracciabilità** |
| GET | `/api/commesse/{id}/fascicolo-tecnico-completo` | **PDF fascicolo completo** |

### 5.2 Fatturazione

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/preventivi` | Lista preventivi |
| POST | `/api/preventivi` | Crea preventivo |
| GET | `/api/preventivi/{id}` | Dettaglio |
| PUT | `/api/preventivi/{id}` | Aggiorna |
| GET | `/api/preventivi/{id}/invoicing-status` | **Stato fatturazione (base: IMPONIBILE)** |
| POST | `/api/preventivi/{id}/progressive-invoice` | **Genera fattura progressiva** |
| GET | `/api/invoices` | Lista fatture emesse |
| POST | `/api/invoices` | Crea fattura |
| PUT | `/api/invoices/{id}` | Aggiorna fattura |
| POST | `/api/invoices/{id}/send-sdi` | Invio a SDI |
| GET | `/api/fatture-ricevute` | Lista fatture passive |
| POST | `/api/fatture-ricevute/{id}/imputa` | **Imputa costi a commessa** |
| POST | `/api/fatture-ricevute/{id}/annulla-imputazione` | **Annulla imputazione** |

### 5.3 Tracciabilità e Normativa

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/fpc/batches` | Lista lotti materiale |
| POST | `/api/fpc/batches` | Crea lotto (heat_number) |
| GET | `/api/fpc/batches/{id}/certificate` | Download cert. 3.1 |
| POST | `/api/fpc/projects` | Crea progetto FPC |
| PUT | `/api/fpc/projects/{id}/fpc` | Aggiorna dati FPC (controlli, saldatore, WPS) |
| GET | `/api/certificazioni` | Lista certificazioni CE |
| POST | `/api/certificazioni` | Crea dichiarazione CE |
| GET | `/api/fascicolo-tecnico/{cid}` | Dati fascicolo tecnico |
| GET | `/api/fascicolo-tecnico/{cid}/dop-pdf` | PDF Dichiarazione di Prestazione |
| GET | `/api/fascicolo-tecnico/{cid}/ce-pdf` | PDF Etichetta CE |
| GET | `/api/fascicolo-tecnico/{cid}/piano-controllo-pdf` | PDF Piano Controllo Qualità |
| GET | `/api/fascicolo-tecnico/{cid}/rapporto-vt-pdf` | PDF Rapporto Visual Testing |
| GET | `/api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf` | **PDF Fascicolo Completo** |
| GET | `/api/gate-cert/{commessa_id}` | Certificazione cancello EN 13241 |
| GET | `/api/cam/commessa/{cid}/calcolo` | Calcolo CAM (riciclato %, CO2) |

### 5.4 Servizi di Calcolo Chiave

| Funzione | File | Descrizione |
|----------|------|-------------|
| `get_commessa_margin_full()` | `margin_service.py` | **Aggrega TUTTI i costi** da 5 fonti diverse |
| `calcola_conformita_cam()` | `cam.py` | Verifica soglia % riciclato per tipo acciaio |
| `calcola_co2_risparmiata()` | `cam.py` | Calcolo CO2 evitata (World Steel 2023) |
| `calc_totals()` | `preventivi.py` | Calcolo totali preventivo (IMPONIBILE → IVA → TOTALE) |
| `generate_scheda_rintracciabilita_pdf()` | `pdf_scheda_rintracciabilita.py` | PDF tracciabilità materiali |
| `generate_fascicolo_pdf()` | `pdf_fascicolo_tecnico.py` | Fascicolo tecnico completo |
| `analyze_certificate_with_ai()` | `vision_analysis.py` | OCR + AI su certificato 3.1 |

---

## 6. Regole Fondamentali

### Fatturazione
- **REGOLA #1:** Percentuali e importi si calcolano SEMPRE sull'**IMPONIBILE** (base senza IVA). L'IVA si aggiunge SOLO alla fine come riga separata.
- `progressive_amount` salvato su ogni fattura progressiva rappresenta l'**IMPONIBILE** della rata.
- Il campo `invoicing-status.total_preventivo` restituisce l'**IMPONIBILE**, non il totale con IVA.

### Tracciabilità EN 1090
- Ogni lotto materiale deve avere un `heat_number` (numero colata) dal certificato 3.1.
- La catena tracciabile è: **Fornitore → Colata → DDT → Lotto → Posizione → Commessa → Marcatura CE**.
- Il Mod. 07 (Scheda Rintracciabilità) aggrega i dati da `material_batches` + `approvvigionamento.arrivi`.

### Magazzino
- `giacenza` è SEMPRE aggiornata atomicamente (decremento al prelievo, incremento al reso/arrivo parziale).
- Il prelievo da magazzino genera un costo di tipo `materiale_magazzino` nella commessa.
- L'utilizzo parziale (`quantita_utilizzata < quantita`) crea/aggiorna automaticamente un articolo nel catalogo.

### Lifecycle Commessa
- La macchina a stati è **event-driven**: ogni transizione è registrata come evento con timestamp e utente.
- Il campo `stato` (lifecycle) e `status` (kanban) sono sincronizzati automaticamente.
- Non è possibile saltare stati: le transizioni sono validate da `EVENTO_TRANSITIONS`.

---

*Documento generato automaticamente dall'analisi del codebase Norma Facile 2.0 — Marzo 2026*

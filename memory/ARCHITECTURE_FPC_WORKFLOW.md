# PROMPT PER AGENTE SUCCESSIVO — Architettura Completa NormaFacile 2.0

## Scopo di questo documento
Questo documento spiega in dettaglio come sono strutturate e collegate le commesse, i documenti commerciali (preventivi, fatture, DDT) e il sistema FPC EN 1090, coprendo tutti i passaggi dalla scelta della normativa fino alla consegna del fascicolo tecnico completo. L'obiettivo e' consentire all'agente successivo di capire la logica esistente per migliorarla senza rifarla da zero.

---

## 1. MAPPA GENERALE DEI FLUSSI

L'applicazione ha 4 flussi principali che si intersecano:

```
RILIEVO (Sopralluogo)
    |
    v
DISTINTA (BOM / Lista Taglio)
    |  [markup %]
    v
PREVENTIVO (Offerta Commerciale)
    |
    +---> FATTURA (Documento fiscale)
    +---> COMMESSA (Kanban / Gestione Lavoro)
    +---> PROGETTO FPC EN 1090 (Tracciabilita' + CE)
              |
              +---> Assegnazione Materiali (Lotti con N. Colata)
              +---> Assegnazione Saldatore (Qualifica ISO 9606)
              +---> Controlli FPC (7 checklist)
              +---> Generazione CE Label
              +---> FASCICOLO TECNICO COMPLETO (PDF unico)
```

---

## 2. FLUSSO COMMERCIALE DETTAGLIATO

### 2.1 Rilievo → Distinta
- **Rilievo** (`/api/rilievi`): Sopralluogo in cantiere con misure, foto, disegni
- **Collegamento**: Un rilievo puo' essere linkato a una distinta tramite i dati misurati
- **Tabelle DB**: `rilievi` collection

### 2.2 Distinta → Preventivo
- **Distinta** (`/api/distinte`): Lista materiali (BOM) con profili, pesi, costi
- **Conversione**: `POST /api/preventivi/from-distinta/{distinta_id}?markup_percent=30`
  - Prende gli items della distinta
  - Applica un markup percentuale (default 30%)
  - Crea righe preventivo automaticamente
  - Se items <= 8: una riga per item
  - Se items > 8: riga riepilogativa unica
- **Collegamento DB**: `preventivi.linked_distinta_id` → `distinta_id`
- **File**: `/app/backend/routes/preventivi.py` linee 174-286

### 2.3 Preventivo → Fattura
Due endpoint fanno la stessa cosa (uno nei preventivi, uno nelle fatture):
- `POST /api/preventivi/{id}/convert-to-invoice` (in `preventivi.py` L472-615)
- `POST /api/invoices/from-preventivo/{id}` (in `invoices.py` L139-231)

**Cosa succede nella conversione:**
1. Verifica che il preventivo esista e non sia gia' convertito
2. Verifica che ci sia un `client_id` assegnato
3. Genera un nuovo `invoice_id` e `document_number` (formato `FT-YYYY/NNNN`)
4. Mappa le righe: `preventivo.lines[]` → `invoice.lines[]`
   - `codice_articolo` → `code`
   - `prezzo_netto` (post-sconti) → `unit_price`
   - `sconto_1/sconto_2` vengono gia' applicati, nel preventivo il `discount_percent` fattura = 0
   - `vat_rate` copiato direttamente
5. Calcola totali fattura: subtotal, taxable_amount, total_vat, total_document
6. Gestisce sconto globale se presente
7. Mappa il metodo di pagamento dalla label del preventivo
8. Aggiorna il preventivo: `status = "accettato"`, `converted_to = invoice_id`
9. La fattura ha `converted_from = preventivo_id` per il backlink

**Collegamento DB:**
```
preventivi.converted_to  ←→  invoices.converted_from
(preventivo_id)                (invoice_id)
```

### 2.4 DDT → Fattura
- I DDT possono essere convertiti in fattura
- Endpoint: nel file `/app/backend/routes/ddt.py`
- Quick fill: `GET /api/invoices/quick-fill/sources` ritorna sia preventivi che DDT disponibili per compilazione rapida fattura

### 2.5 Preventivo → Commessa (Kanban)
- `POST /api/commesse/from-preventivo/{preventivo_id}`
- Crea una card nel Kanban con:
  - `title` = subject del preventivo
  - `client_id/client_name` dal preventivo
  - `value` = totale del preventivo
  - `linked_preventivo_id` = preventivo_id
  - `status` = "preventivo" (prima colonna)
- **File**: `/app/backend/routes/commesse.py` L215-252

**Le 7 colonne Kanban:**
```
preventivo → approvvigionamento → lavorazione → conto_lavoro → pronto_consegna → montaggio → completato
```

**Collegamento DB della commessa:**
```json
{
  "commessa_id": "com_xxx",
  "linked_preventivo_id": "prev_xxx",   // ← Link al preventivo di origine
  "linked_distinta_id": null,            // ← Opzionale, link a una distinta
  "linked_rilievo_id": null,             // ← Opzionale, link a un rilievo
  "status": "lavorazione",
  "status_history": [...]                // ← Storico spostamenti
}
```

---

## 3. FLUSSO FPC EN 1090 — DALLA NORMATIVA AL FASCICOLO

Questo e' il cuore del sistema di compliance. Ecco ogni passaggio:

### 3.1 Scelta della Normativa
Il sistema supporta due normative principali:
- **EN 1090-1** → Strutture in acciaio (questo e' il flusso FPC)
- **EN 13241** → Porte e cancelli industriali (flusso separato in certificazioni)

Per EN 1090, il punto di partenza e' un **preventivo accettato** che deve diventare un **progetto FPC**.

### 3.2 Conversione Preventivo → Progetto FPC
- **Endpoint**: `POST /api/fpc/projects`
- **Body**: `{ "preventivo_id": "prev_xxx", "execution_class": "EXC2" }`
- **File**: `/app/backend/routes/fpc.py` L173-225

**Cosa succede:**
1. Verifica che il preventivo esista
2. Verifica che non esista gia' un progetto FPC per quel preventivo (vincolo 1:1)
3. Richiede la **classe di esecuzione** (EXC1-EXC4) — campo obbligatorio
4. Crea il progetto con:
   - Copia le `lines` dal preventivo (le stesse righe articolo)
   - Inizializza `fpc_data` con i 7 controlli default vuoti
   - Status: `in_progress`

**Struttura DB del progetto FPC:**
```json
{
  "project_id": "prj_xxx",
  "preventivo_id": "prev_xxx",        // ← Link di origine
  "preventivo_number": "PRV-2026-0001",
  "client_id": "cl_xxx",
  "client_name": "Rossi Srl",
  "subject": "Pensilina acciaio",
  "status": "in_progress",            // in_progress → completed → archived
  "lines": [                           // ← Copiate dal preventivo
    {
      "line_id": "ln_xxx",
      "description": "IPE 200 S275JR",
      "quantity": 4,
      "batch_id": null,                // ← Verra' assegnato dopo
      "heat_number": null,             // ← Verra' popolato da batch
      "material_type": null
    }
  ],
  "fpc_data": {
    "execution_class": "EXC2",
    "wps_id": null,                    // ← Procedura di saldatura
    "welder_id": null,                 // ← ID saldatore assegnato
    "welder_name": null,
    "material_batches": [],            // ← Lista batch_id usati
    "controls": [                      // ← 7 controlli checklist
      {"control_type": "dimensional", "label": "Controllo dimensionale", "checked": false},
      {"control_type": "visual", "label": "Controllo visivo saldature (EN ISO 5817)", "checked": false},
      {"control_type": "material_cert", "label": "Verifica certificati materiale 3.1", "checked": false},
      {"control_type": "welder_cert", "label": "Verifica qualifica saldatore", "checked": false},
      {"control_type": "wps_compliance", "label": "Conformita' WPS", "checked": false},
      {"control_type": "surface_prep", "label": "Preparazione superfici", "checked": false},
      {"control_type": "marking", "label": "Marcatura e identificazione pezzi", "checked": false}
    ],
    "ce_label_generated": false,
    "ce_label_generated_at": null
  }
}
```

### 3.3 Registrazione Saldatori (prerequisito)
- **Endpoint**: `POST/GET /api/fpc/welders`
- Registro indipendente dal progetto — i saldatori sono dell'azienda, non del singolo progetto
- Ogni saldatore ha: nome, qualifica ISO 9606-1, data scadenza, note
- Il sistema calcola `is_expired` confrontando la data di scadenza con oggi
- **Tabella DB**: `welders`

### 3.4 Registrazione Lotti Materiale (prerequisito)
- **Endpoint**: `POST/GET /api/fpc/batches`
- Registro indipendente — i lotti sono dell'azienda
- Ogni lotto ha: fornitore, tipo materiale (es. S275JR), **numero colata** (heat number), certificato 3.1
- Il certificato 3.1 (PDF) viene salvato come **stringa Base64** nel campo `certificate_base64` di MongoDB
- Nella lista, il campo pesante viene escluso dalla query (proiezione `{"certificate_base64": 0}`)
- Per scaricare il certificato: `GET /api/fpc/batches/{id}/certificate`
- **Tabella DB**: `material_batches`

### 3.5 Compilazione del Progetto FPC
Una volta creato il progetto, l'utente deve completare questi passaggi sulla pagina del progetto FPC:

#### a) Assegnare il Saldatore
- `PUT /api/fpc/projects/{id}/fpc` con `{ "welder_id": "wld_xxx" }`
- Il backend recupera automaticamente il nome del saldatore
- Se il saldatore ha la qualifica scaduta, ritorna un `warning`

#### b) Impostare il WPS
- `PUT /api/fpc/projects/{id}/fpc` con `{ "wps_id": "WPS-001" }`
- Campo di testo libero (identificativo della procedura di saldatura)

#### c) Collegare i Materiali alle Righe
- `POST /api/fpc/projects/{id}/assign-batch` con `{ "line_index": 0, "batch_id": "bat_xxx" }`
- Ogni riga del preventivo (ora riga progetto) viene collegata a un lotto specifico
- Il backend copia `heat_number` e `material_type` dal lotto alla riga
- Il `batch_id` viene anche aggiunto alla lista `fpc_data.material_batches`

#### d) Completare i 7 Controlli FPC
- `PUT /api/fpc/projects/{id}/fpc` con aggiornamento array `controls`
- Ogni controllo va spuntato con: `checked: true`, `checked_by`, `checked_at`
- I 7 controlli sono:
  1. Controllo dimensionale
  2. Controllo visivo saldature (EN ISO 5817)
  3. Verifica certificati materiale 3.1
  4. Verifica qualifica saldatore
  5. Conformita' WPS
  6. Preparazione superfici
  7. Marcatura e identificazione pezzi

### 3.6 Verifica Requisiti CE
- **Endpoint**: `GET /api/fpc/projects/{id}/ce-check`
- **File**: `/app/backend/routes/fpc.py` L353-402

Controlla 5 condizioni bloccanti (`blockers`):
1. Classe di esecuzione selezionata
2. Saldatore assegnato (e non scaduto)
3. Tutte le righe collegate a un lotto materiale
4. Tutti i 7 controlli completati
5. WPS assegnata

Ritorna: `{ "ready": true/false, "blockers": [...] }`

### 3.7 Generazione Etichetta CE
- **Endpoint**: `POST /api/fpc/projects/{id}/generate-ce`
- Rivalidazione backend di: saldatore, materiali collegati, controlli
- Se tutto OK: `fpc_data.ce_label_generated = true`, `status = "completed"`
- Questo passaggio "sigilla" il progetto

### 3.8 Generazione Fascicolo Tecnico (One-Click)
- **Endpoint**: `GET /api/fpc/projects/{id}/dossier`
- **File**: `/app/backend/services/dossier_generator.py`
- Genera un unico PDF con 7 sezioni, ciascuna costruita come HTML e renderizzata con WeasyPrint:

| # | Sezione | Fonte dati |
|---|---------|-----------|
| 1 | **Copertina** | project + company_settings |
| 2 | **DoP (Dichiarazione di Prestazione)** | project.fpc_data + company |
| 3 | **Etichetta CE** | project.fpc_data.execution_class + company |
| 4 | **Riepilogo Tracciabilita' Materiali** | project.lines + material_batches |
| 5 | **Certificati 3.1 allegati** | material_batches.certificate_base64 (decodificati) |
| 6 | **Qualifica Saldatore** | welders[welder_id] |
| 7 | **Checklist Controlli FPC** | project.fpc_data.controls |

**Come funziona il merge dei PDF:**
1. Ogni sezione genera un PDF tramite `render_pdf()` (WeasyPrint HTML→PDF)
2. I certificati 3.1 sono decodificati da Base64 in bytes
3. `pypdf.PdfWriter` + `PdfReader` unisce tutto in un unico file
4. Il risultato e' un `BytesIO` restituito come `StreamingResponse`

---

## 4. SCHEMA COMPLETO DELLE CONNESSIONI DB

```
CLIENTS (clients)
    |
    +--- preventivi.client_id
    +--- invoices.client_id
    +--- ddt_documents.client_id
    +--- commesse.client_id
    +--- fpc_projects.client_id
    +--- rilievi.client_id
    +--- certificazioni.client_id

RILIEVI (rilievi)
    |
    +--→ distinte (link manuale)
    +--→ commesse.linked_rilievo_id
    +--→ sicurezza/POS (link manuale)

DISTINTE (distinte)
    |
    +--→ preventivi.linked_distinta_id (via /api/preventivi/from-distinta)
    +--→ commesse.linked_distinta_id

PREVENTIVI (preventivi)
    |
    +--→ invoices.converted_from (via convert-to-invoice)
    |    ↕ preventivi.converted_to = invoice_id
    |
    +--→ commesse.linked_preventivo_id (via /api/commesse/from-preventivo)
    |
    +--→ fpc_projects.preventivo_id (via /api/fpc/projects POST)

COMMESSE (commesse) — Kanban
    |
    linked_preventivo_id → preventivi
    linked_distinta_id   → distinte
    linked_rilievo_id    → rilievi

FPC_PROJECTS (fpc_projects)
    |
    preventivo_id         → preventivi
    fpc_data.welder_id    → welders
    fpc_data.material_batches[] → material_batches
    lines[].batch_id      → material_batches

WELDERS (welders) — Registro aziendale
    |
    Riferiti da fpc_projects.fpc_data.welder_id

MATERIAL_BATCHES (material_batches) — Registro aziendale
    |
    Riferiti da fpc_projects.fpc_data.material_batches[]
    Riferiti da fpc_projects.lines[].batch_id
    Contengono certificate_base64 (PDF 3.1)

INVOICES (invoices)
    |
    converted_from → preventivi
    pagamenti[] — array di pagamenti registrati
    Generano PDF, XML (FatturaPA), invio email, invio SDI

DDT (ddt_documents)
    |
    Convertibili in fattura
    Disponibili come "quick-fill" per nuove fatture
```

---

## 5. FILE DI RIFERIMENTO PER OGNI MODULO

| Modulo | Backend Route | Backend Service | Frontend Page |
|--------|--------------|-----------------|---------------|
| Preventivi | `routes/preventivi.py` | `services/pdf_template.py` | `PreventiviPage.js`, `PreventivoEditorPage.js` |
| Fatture | `routes/invoices.py` | `services/pdf_service.py`, `services/invoice_service.py` | `InvoicesPage.js`, `InvoiceEditorPage.js` |
| DDT | `routes/ddt.py` | `services/ddt_pdf_service.py` | `DDTListPage.js`, `DDTEditorPage.js` |
| Commesse | `routes/commesse.py` | — | `PlanningPage.js` |
| FPC EN 1090 | `routes/fpc.py` | `services/dossier_generator.py` | `TracciabilitaPage.js`, `FPCProjectPage.js` |
| Certificazioni CE | `routes/certificazioni.py` | `services/certificazione_pdf_service.py`, `services/fascicolo_generator.py` | `CertificazioniPage.js`, `CertificazioneWizardPage.js` |
| Distinte | `routes/distinta.py` | `services/distinta_pdf_service.py` | `DistintePage.js`, `DistintaEditorPage.js` |
| Rilievi | `routes/rilievi.py` | `services/rilievo_pdf_service.py` | `RilieviPage.js`, `RilievoEditorPage.js` |
| Clienti | `routes/clients.py` | — | `ClientsPage.js` |
| Sicurezza/POS | `routes/sicurezza.py` | `services/pos_pdf_service.py` | `SicurezzaPage.js`, `PosWizardPage.js` |

---

## 6. FLUSSO OPERATIVO COMPLETO (Caso d'uso reale)

Ecco il percorso tipico di un fabbro che deve realizzare una pensilina in acciaio:

### Fase 1: Sopralluogo
1. L'operatore va in cantiere e crea un **Rilievo** con misure, foto, GPS
2. Dal rilievo genera una **Distinta** con i profili necessari (IPE 200, HEB 160, ecc.)

### Fase 2: Offerta Commerciale
3. Dalla distinta genera un **Preventivo** con markup del 30%
4. Il preventivo viene inviato al cliente via email (`POST /api/preventivi/{id}/send-email`)
5. Il cliente accetta

### Fase 3: Avvio Lavori
6. Dal preventivo accettato:
   - Crea una **Commessa** nel Kanban (`POST /api/commesse/from-preventivo/{id}`)
   - Converte in **Progetto FPC** se necessita marcatura CE (`POST /api/fpc/projects`)

### Fase 4: Produzione + Tracciabilita' EN 1090
7. Il materiale arriva in officina → Registra i **lotti** con numero di colata e certificato 3.1
8. Assegna ogni riga del progetto a un **lotto specifico** (tracciabilita' dal certificato al pezzo finito)
9. Assegna il **saldatore qualificato** al progetto
10. Inserisce il numero **WPS** utilizzata
11. Durante la produzione, spunta i **7 controlli FPC** man mano che vengono eseguiti

### Fase 5: Certificazione CE
12. Il sistema verifica che tutto sia completo (`/ce-check`)
13. Genera l'**etichetta CE** (`/generate-ce`)
14. Stampa il **Fascicolo Tecnico completo** in un click (`/dossier`) — PDF con tutto dentro

### Fase 6: Consegna + Fatturazione
15. Sposta la commessa nel Kanban a "Pronto / Consegna"
16. Crea un **DDT** per il trasporto
17. Converte il preventivo in **Fattura** (`/convert-to-invoice`)
18. Invia la fattura via email o al **SDI** per la fatturazione elettronica
19. Registra il **pagamento** quando arriva

---

## 7. COSA MANCA / DA MIGLIORARE

### Collegamento Commessa ↔ FPC Project
Attualmente la commessa e il progetto FPC sono creati indipendentemente dallo stesso preventivo. Non c'e' un link diretto `commessa.fpc_project_id` ↔ `fpc_project.commessa_id`. Miglioramento possibile: quando si crea un progetto FPC, collegarlo automaticamente alla commessa associata (se esiste), e viceversa.

### Avanzamento Commessa Automatico
Quando si completano step nel progetto FPC (es. tutti i controlli superati), lo status della commessa potrebbe aggiornarsi automaticamente nel Kanban.

### Collegamento DDT al Progetto FPC
Per la consegna di prodotti EN 1090, il DDT dovrebbe referenziare il progetto FPC e includere il numero di fascicolo tecnico.

### Storico Modifiche
I documenti non hanno un vero audit log. Per la conformita' EN 1090, sarebbe utile tracciare chi ha modificato cosa e quando.

### Duplicazione Conversioni Preventivo→Fattura
Ci sono due endpoint che fanno la stessa cosa (`preventivi.py` e `invoices.py`). Sarebbe meglio unificarli.

---

## 8. TECNOLOGIE CHIAVE

- **PDF Generation**: WeasyPrint (HTML/CSS → PDF) per tutti i documenti
- **PDF Merging**: `pypdf` (PdfWriter/PdfReader) per il fascicolo tecnico
- **Template condiviso**: `/app/backend/services/pdf_template.py` — CSS/HTML comuni per fatture, preventivi, DDT
- **Certificati 3.1**: Salvati come Base64 in MongoDB, decodificati al volo per il merge
- **Navigazione Frontend**: Sidebar accordion con gruppi (Commerciale, Produzione, Certificazioni, ecc.)
- **Kanban**: Drag-and-drop con 7 colonne, API PATCH per spostamento status

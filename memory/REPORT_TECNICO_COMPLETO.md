# NORMA FACILE 2.0 — Report Tecnico Completo
## Per handoff ad altra AI di supporto

---

## 1. PANORAMICA PROGETTO

**Nome**: Norma Facile 2.0
**Tipo**: SaaS CRM/ERP per fabbri e carpenterie metalliche italiane
**Target**: Aziende metalliche che producono serramenti, cancelli, scale, ringhiere in acciaio
**Lingua UI**: Italiano
**URL Preview**: `https://tenant-isolation-19.preview.emergentagent.com`

### Stack Tecnologico
| Layer | Tecnologia | Versione |
|-------|-----------|----------|
| Frontend | React + TailwindCSS + Shadcn/UI | React 18, TW 3 |
| Backend | FastAPI (Python) | 0.110.1 |
| Database | MongoDB (via Motor async) | Motor 3.3.1 |
| PDF | WeasyPrint | 68.1 |
| Email | Resend | 2.23.0 |
| AI/OCR | OpenAI GPT-4o Vision (via emergentintegrations) | 1.99.9 |
| Auth | Emergent-managed Google OAuth → Session cookies | - |
| SDI | Aruba SDI / FattureInCloud (INATTIVO) | - |

### Variabili Ambiente (backend/.env)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS=...
EMERGENT_LLM_KEY=...
JWT_SECRET=normafacile-prod-secret-key-2026-steelproject
DOMAIN_URL=...
RESEND_API_KEY=...
SENDER_EMAIL=...
SENDER_NAME=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SDI_API_KEY=... (inattivo)
SDI_API_SECRET=... (inattivo)
SDI_ENVIRONMENT=test
```

---

## 2. ARCHITETTURA

### 2.1 Struttura Cartelle
```
/app/
├── backend/
│   ├── core/
│   │   ├── config.py          # Settings da .env (Pydantic BaseSettings)
│   │   ├── database.py        # Connessione MongoDB (motor async)
│   │   ├── security.py        # Auth: session exchange, verify, get_current_user
│   │   └── engine/            # Core Engine (normative, calcoli)
│   ├── models/                # Pydantic models per request/response
│   │   ├── invoice.py (249 righe) — InvoiceResponse, InvoiceCreate, etc.
│   │   ├── cam.py (232)       — Modelli CAM (lotti, batches, report)
│   │   ├── distinta.py (187)  — Distinta base prodotto
│   │   ├── client.py (156)    — Anagrafica clienti/fornitori
│   │   ├── perizia.py (146)   — Perizia sinistro
│   │   ├── sicurezza.py (120) — POS sicurezza cantiere
│   │   ├── fpc.py (103)       — Fascicolo Produzione EN 1090
│   │   ├── certificazione.py (97) — Certificazione CE
│   │   ├── rilievo.py (95)    — Rilievo in cantiere
│   │   ├── ddt.py (80)        — Documento di Trasporto
│   │   ├── company.py (74)    — Impostazioni azienda
│   │   └── ...
│   ├── routes/                # FastAPI router files
│   │   ├── commessa_ops.py (1646 righe) ⚠️ IL PIU' GRANDE — Procurement, CL, AI parsing
│   │   ├── preventivi.py (1163) — Preventivi + fatturazione progressiva
│   │   ├── engine.py (1162)   — Core Engine normativo
│   │   ├── invoices.py (1099) — Fatture attive
│   │   ├── perizia.py (813)   — Perizie sinistro
│   │   ├── commesse.py (782)  — CRUD commesse + Hub + Link moduli
│   │   ├── fatture_ricevute.py (697) — Fatture passive
│   │   ├── cam.py (640)       — Modulo CAM
│   │   ├── ddt.py (607)       — DDT
│   │   ├── dashboard.py (524) — Dashboard stats
│   │   ├── fpc.py (484)       — EN 1090
│   │   ├── distinta.py (461)  — Distinte base
│   │   └── ... (altri 12 file)
│   ├── services/              # Business logic, PDF, email
│   │   ├── pdf_procurement.py (623) — PDF per RdP, OdA, CL DDT
│   │   ├── pdf_template_v2.py (619) — Template PDF v2 (fatture, preventivi)
│   │   ├── pdf_template.py (537)    — Template PDF v1
│   │   ├── fascicolo_generator.py (471)
│   │   ├── email_service.py (400)   — Invio email con Resend
│   │   ├── email_preview.py (166)   — Builder HTML per anteprima email
│   │   ├── certificate_parser.py    — AI OCR certificati materiale
│   │   ├── aruba_sdi.py (279)       — SDI (inattivo)
│   │   ├── fattureincloud_api.py (183) — FattureInCloud (inattivo)
│   │   └── ... (altri 14 file)
│   └── tests/                 # 50+ file di test pytest
└── frontend/
    └── src/
        ├── components/
        │   ├── CommessaOpsPanel.js (2032 righe) ⚠️ MONOLITE — Procurement, CL, Produzione, Docs
        │   ├── InvoiceGenerationModal.js (369)
        │   ├── DashboardLayout.js (336) — Sidebar + layout
        │   ├── EmailPreviewDialog.js (222) — Anteprima email con edit
        │   ├── PDFPreviewModal.js (85)
        │   └── ui/             # Shadcn/UI components
        ├── pages/              # 38 pagine
        │   ├── DistintaEditorPage.js (1026)
        │   ├── PeriziaEditorPage.js (861)
        │   ├── InvoiceEditorPage.js (854)
        │   ├── RilievoEditorPage.js (845)
        │   ├── CoreEnginePage.js (810)
        │   ├── CertificazioneWizardPage.js (719)
        │   ├── PreventivoEditorPage.js (718)
        │   ├── InvoicesPage.js (697)
        │   ├── CommessaHubPage.js (521) — Hub centrale commessa
        │   └── ... (altre 29 pagine)
        └── contexts/
            └── AuthContext.js   — Google OAuth flow
```

### 2.2 Autenticazione
```
Flow: Login Google → Emergent Auth → session_id → Backend exchange → session_token (cookie httpOnly)
- Cookie: session_token (httpOnly, samesite=none)
- Fallback: Authorization: Bearer {session_token}
- Collection: user_sessions (session_token, user_id, expires_at)
- Collection: users (user_id, email, name)
```

### 2.3 Collezioni MongoDB (27 totali)
```
CORE:
  commesse              — Commessa (Job Order) — ENTITA' CENTRALE
  clients               — Anagrafica clienti e fornitori
  invoices              — Fatture attive emesse
  preventivi            — Preventivi / Offerte
  ddt                   — Documenti di Trasporto
  fatture_ricevute      — Fatture passive ricevute

TECNICO:
  distinte              — Distinte base prodotto (BOM)
  rilievi               — Rilievi in cantiere
  certificazioni        — Certificazioni CE
  fpc_projects          — Progetti EN 1090
  articoli              — Catalogo articoli

PROCUREMENT & MATERIALI:
  material_batches      — Lotti materiale (da certificati)
  lotti_cam             — Lotti CAM (contenuto riciclato)
  calcoli_cam           — Calcoli CAM per commessa
  archivio_certificati  — Certificati non abbinati
  commessa_documents    — Documenti allegati a commessa

SICUREZZA:
  pos_documents         — POS (Piano Operativo Sicurezza)

CONFIGURAZIONE:
  company_settings      — Dati azienda
  user_sessions         — Sessioni autenticate
  users                 — Utenti registrati
  user_profiles         — Profili utente
  document_counters     — Contatori numerazione documenti
  vendor_catalogs       — Cataloghi fornitori
  vendor_keys           — Chiavi API fornitori
  componenti            — Componenti normativa
  norme_config          — Configurazione norme
  welders               — Registro saldatori
```

---

## 3. MODULI FUNZIONALI

### 3.1 COMMESSA (Hub Centrale)
**File backend**: `commesse.py` (CRUD, Hub, Link), `commessa_ops.py` (Ops, Procurement, CL, AI)
**File frontend**: `CommessaHubPage.js`, `CommessaOpsPanel.js`
**Route**: `/commesse/:commessaId`

La commessa è l'entità centrale. Tutto il sistema ruota attorno ad essa.

**Schema commessa in MongoDB:**
```json
{
  "commessa_id": "com_xxx",
  "user_id": "user_xxx",
  "numero": "NF-2026-000001",
  "title": "Cancello Via Roma",
  "status": "in_corso",  // pianificata, in_corso, completata, fatturata, annullata
  "cliente": { "client_id": "...", "nome": "..." },
  "cantiere": { "indirizzo": "...", "citta": "...", "cap": "..." },
  "importo_preventivo": 15000,
  "data_inizio": "2026-01-15",
  "data_consegna": "2026-03-01",
  "linked_preventivo_id": "prev_xxx",
  "moduli": {
    "preventivo_id": "prev_xxx",
    "fatture_ids": ["inv_xxx", "inv_yyy"],
    "ddt_ids": [],
    "rilievo_id": null,
    "distinta_id": null,
    "fpc_project_id": null,
    "certificazione_id": null
  },
  "approvvigionamento": {
    "richieste": [...],   // RdP - Richieste di Preventivo a fornitori
    "ordini": [...],      // OdA - Ordini di Acquisto
    "arrivi": [...]       // Arrivi materiale con certificati
  },
  "conto_lavoro": [{      // Lavorazioni esterne (verniciatura, zincatura, etc.)
    "cl_id": "cl_xxx",
    "tipo": "verniciatura",
    "fornitore_nome": "Vern Srl",
    "fornitore_id": "client_xxx",
    "stato": "da_inviare", // da_inviare → inviato → in_lavorazione → rientrato → verificato
    "ral": "RAL 9010",
    "righe": [{"descrizione": "...", "quantita": 5, "unita": "pz", "peso_kg": 150}],
    "causale_trasporto": "Conto Lavorazione",
    "note": "..."
  }],
  "produzione": { ... },  // Fasi produttive (taglio, saldatura, montaggio)
  "eventi": [...]          // Timeline eventi
}
```

**Flusso di lavoro:**
```
1. Rilievo → 2. Preventivo → 3. Commessa (se accettato)
   ↓                              ↓
4. Distinta Base          5. Approvvigionamento (RdP → OdA → Arrivi)
   ↓                              ↓
6. Produzione             7. Conto Lavoro (verniciatura, zincatura)
   ↓                              ↓
8. Certificazione CE      9. DDT consegna
   ↓
10. Fatturazione Progressiva (acconto, SAL, saldo)
```

### 3.2 APPROVVIGIONAMENTO (dentro commessa_ops.py)
**Endpoint chiave:**
- `POST /api/commesse/{cid}/approvvigionamento/richieste` — Crea RdP
- `GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/pdf` — PDF RdP
- `POST /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/send-email` — Invia email RdP
- `GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email` — Anteprima
- `POST /api/commesse/{cid}/approvvigionamento/ordini` — Crea OdA
- (stessi endpoint pdf/email/preview per OdA)
- `POST /api/commesse/{cid}/approvvigionamento/arrivi` — Registra arrivo materiale
- `POST /api/commesse/{cid}/documenti/{doc_id}/parse-certificato` — AI OCR certificato

### 3.3 CONTO LAVORO (dentro commessa_ops.py)
**Endpoint:**
- `POST /api/commesse/{cid}/conto-lavoro` — Crea CL
- `PUT /api/commesse/{cid}/conto-lavoro/{cl_id}` — Aggiorna stato
- `GET /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-pdf` — PDF DDT CL
- `POST /api/commesse/{cid}/conto-lavoro/{cl_id}/send-email` — Email DDT CL
- `GET /api/commesse/{cid}/conto-lavoro/{cl_id}/preview-email` — Anteprima email

### 3.4 FATTURAZIONE
**Backend**: `invoices.py`, `preventivi.py` (fatturazione progressiva)
**Frontend**: `InvoicesPage.js`, `InvoiceEditorPage.js`, `PreventivoEditorPage.js`

**Flusso fatturazione progressiva:**
```
Preventivo (accettato) → Genera Fattura Progressiva (acconto/SAL/saldo)
  → Fattura creata con link a preventivo
  → Auto-collegata alla commessa (moduli.fatture_ids)
```

**Formato numeri:** `FT-2026/0001` (anno con `/` separatore, NON `-`)

**BUG CRITICO FIXATO**: Il filtro anno nella lista fatture usava regex `-{year}-` che non matchava il formato `FT-{year}/xxxx`. Corretto a `-{year}[-/]`.

**Endpoint chiave:**
- `GET /api/invoices?year=2026` — Lista fatture con filtro anno
- `POST /api/invoices` — Crea fattura
- `GET /api/invoices/{id}/pdf` — PDF fattura
- `POST /api/invoices/{id}/send-email` — Invia email (supporta custom_subject/custom_body)
- `GET /api/invoices/{id}/preview-email` — Anteprima email
- `POST /api/preventivi/{id}/progressive-invoice` — Genera fattura progressiva

### 3.5 ANTEPRIMA EMAIL (sistema globale)
**Backend**: `email_preview.py` (builder HTML), endpoint `preview-email` in ogni route
**Frontend**: `EmailPreviewDialog.js`

Tutti i 6 tipi di invio email hanno:
1. `GET .../preview-email` → restituisce `{to_email, to_name, subject, html_body, has_attachment, attachment_name}`
2. `POST .../send-email` → accetta opzionale `{custom_subject, custom_body}` per personalizzare
3. Frontend: dialog con anteprima HTML in iframe, toggle "Modifica testo", bottone expand fullscreen

Tipi: RdP, OdA, Conto Lavoro, Fattura, DDT, Preventivo

### 3.6 AI — PARSING CERTIFICATI MATERIALE
**Backend**: `services/certificate_parser.py`, `commessa_ops.py`
**Integrazione**: GPT-4o Vision via `emergentintegrations`

**Flusso:**
```
PDF certificato 3.1 → pdf2image (poppler-utils) → immagine → GPT-4o Vision
  → Estrae: numero colata, qualità acciaio, fornitore, dimensioni, composizione chimica
  → Cross-reference con OdA aperti in TUTTE le commesse
  → Match trovato: crea material_batch + cam_lot nella commessa giusta
  → Match NON trovato: salva in archivio_certificati
```

**Dipendenza sistema**: `poppler-utils` (apt-get install) per pdf2image

### 3.7 MODULO CAM (Criteri Ambientali Minimi)
**Backend**: `cam.py`, `services/pdf_cam_declaration.py`, `services/pdf_cam_report.py`
**Frontend**: parte di `CommessaOpsPanel.js`, `ReportCAMPage.js`

Traccia contenuto riciclato dei materiali, genera dichiarazione CAM per commessa, report aziendale con stima CO2.

### 3.8 ALTRI MODULI
| Modulo | Backend Route | Frontend Page | Descrizione |
|--------|--------------|---------------|-------------|
| Clienti/Fornitori | `clients.py` | `ClientsPage.js`, `FornitoriPage.js` | Anagrafica unificata |
| Rilievi | `rilievi.py` | `RilieviPage.js`, `RilievoEditorPage.js` | Rilievo misure cantiere |
| Distinte | `distinta.py` | `DistintePage.js`, `DistintaEditorPage.js` | BOM con ottimizzatore taglio barre |
| DDT | `ddt.py` | `DDTListPage.js`, `DDTEditorPage.js` | Documenti di Trasporto |
| Certificazioni CE | `certificazioni.py` | `CertificazioniPage.js`, `CertificazioneWizardPage.js` | Marcatura CE EN 1090 |
| Sicurezza POS | `sicurezza.py` | `SicurezzaPage.js`, `PosWizardPage.js` | Piano Operativo Sicurezza |
| Perizie Sinistro | `perizia.py` | `PeriziaListPage.js`, `PeriziaEditorPage.js` | Perizie danni con AI foto |
| Core Engine | `engine.py` | `CoreEnginePage.js` | Motore normativo EN 13241 etc. |
| Catalogo Profili | `catalogo.py` | `CatalogoPage.js` | Profili acciaio (IPE, HEB, etc.) |
| Catalogo Articoli | `articoli.py` | `ArticoliPage.js` | Articoli con prezzi |
| Fatture Ricevute | `fatture_ricevute.py` | `FattureRicevutePage.js` | Fatture passive con XML import |
| Tracciabilità | `fpc.py` | `TracciabilitaPage.js`, `FPCProjectPage.js` | EN 1090 FPC |
| Planning | `dashboard.py` | `PlanningPage.js` | Vista Kanban commesse |
| EBITDA | `dashboard.py` | `EBITDAPage.js` | Dashboard finanziaria (WIP) |
| Settings | `company.py` | `SettingsPage.js` | Dati azienda |

---

## 4. BUG NOTI E PATTERN PROBLEMATICI

### 4.1 ⚠️ CRITICO: Radix UI Select/Combobox dentro Dialog
**Pattern**: Quando un componente Radix `<Select>`, `<Combobox>` o `<Popover>` è dentro un `<Dialog>`, il layer `pointer-events: none` del Dialog blocca il dropdown.
**Soluzione adottata**: Sostituire con `<select>` nativo HTML dentro i Dialog.
**File affetti**: CommessaOpsPanel.js (7 istanze), CommessaHubPage.js (2 istanze)
**REGOLA**: In futuro, MAI usare Radix Select/Combobox dentro Dialog. Usare sempre `<select>` nativo.

### 4.2 ⚠️ CRITICO: Formato numeri documenti
I documenti usano formati DIVERSI:
- Fatture: `FT-2026/0001` (slash)
- Preventivi: `PRV-2026/0001` (slash)
- DDT: `DDT-2026/0001` (slash)
- Commesse: `NF-2026-000001` (dash)
I filtri anno devono gestire ENTRAMBI i separatori (`/` e `-`).

### 4.3 ⚠️ MEDIO: CommessaOpsPanel.js è un monolite (2032 righe)
Contiene: Approvvigionamento (RdP, OdA, Arrivi), Conto Lavoro, Produzione, Repository Documenti, AI Parsing, CAM.
**Da fare**: Spezzare in sotto-componenti.

### 4.4 ⚠️ MEDIO: ObjectId MongoDB
Ogni query che restituisce dati da MongoDB DEVE escludere `_id` dalla proiezione, o convertirlo a stringa. Altrimenti `ObjectId is not JSON serializable`.

### 4.5 Integrazioni INATTIVE
- **Aruba SDI / FattureInCloud**: Codice presente ma chiavi API non configurate. Endpoint `send-sdi` esiste ma non invia realmente.

---

## 5. ENDPOINT API COMPLETI (raggruppati)

### Auth
```
POST /api/auth/session          — Exchange session_id per session_token
POST /api/auth/logout           — Logout
GET  /api/auth/me               — Utente corrente
```

### Commesse
```
GET    /api/commesse/                     — Lista commesse
POST   /api/commesse/                     — Crea commessa
GET    /api/commesse/{id}                 — Dettaglio
PUT    /api/commesse/{id}                 — Aggiorna
DELETE /api/commesse/{id}                 — Elimina
PATCH  /api/commesse/{id}/status          — Cambia stato
GET    /api/commesse/{id}/hub             — Hub dati aggregati
GET    /api/commesse/{id}/available-modules?tipo=fattura — Moduli collegabili
POST   /api/commesse/{id}/link-module     — Collega modulo
POST   /api/commesse/{id}/unlink-module   — Scollega modulo
POST   /api/commesse/{id}/eventi          — Aggiungi evento timeline
GET    /api/commesse/{id}/dossier         — Genera dossier commessa
```

### Commessa Ops (Procurement, CL, AI)
```
GET    /api/commesse/{id}/ops             — Dati operativi
POST   /api/commesse/{id}/approvvigionamento/richieste              — Crea RdP
PUT    /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}     — Aggiorna RdP
GET    /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}/pdf — PDF RdP
POST   /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}/send-email
GET    /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}/preview-email
POST   /api/commesse/{id}/approvvigionamento/ordini                 — Crea OdA
PUT    /api/commesse/{id}/approvvigionamento/ordini/{oid}           — Aggiorna OdA
GET    /api/commesse/{id}/approvvigionamento/ordini/{oid}/pdf
POST   /api/commesse/{id}/approvvigionamento/ordini/{oid}/send-email
GET    /api/commesse/{id}/approvvigionamento/ordini/{oid}/preview-email
POST   /api/commesse/{id}/approvvigionamento/arrivi                 — Registra arrivo
PUT    /api/commesse/{id}/approvvigionamento/arrivi/{aid}/verifica  — Verifica arrivo
PUT    /api/commesse/{id}/approvvigionamento/arrivi/{aid}/materiale/{idx}/certificato — Upload cert
POST   /api/commesse/{id}/documenti                                 — Upload documento
GET    /api/commesse/{id}/documenti                                 — Lista documenti
GET    /api/commesse/{id}/documenti/{did}/download                  — Download
DELETE /api/commesse/{id}/documenti/{did}                           — Elimina (cascade delete!)
POST   /api/commesse/{id}/documenti/{did}/parse-certificato         — AI OCR certificato
POST   /api/commesse/{id}/conto-lavoro                              — Crea CL
PUT    /api/commesse/{id}/conto-lavoro/{cl_id}                      — Aggiorna stato CL
GET    /api/commesse/{id}/conto-lavoro/{cl_id}/preview-pdf          — PDF DDT CL
POST   /api/commesse/{id}/conto-lavoro/{cl_id}/send-email
GET    /api/commesse/{id}/conto-lavoro/{cl_id}/preview-email
POST   /api/commesse/{id}/produzione/init                           — Inizializza fasi produzione
PUT    /api/commesse/{id}/produzione/{fase}                         — Aggiorna fase
GET    /api/commesse/{id}/produzione                                — Stato produzione
```

### Fatture
```
GET    /api/invoices?year=2026&status=...  — Lista con filtri
POST   /api/invoices                        — Crea
GET    /api/invoices/{id}                   — Dettaglio
PUT    /api/invoices/{id}                   — Aggiorna
DELETE /api/invoices/{id}                   — Elimina
PATCH  /api/invoices/{id}/status            — Cambia stato
GET    /api/invoices/{id}/pdf               — PDF
GET    /api/invoices/{id}/xml               — XML per SDI
POST   /api/invoices/{id}/send-email        — Invia (custom_subject/body opzionali)
GET    /api/invoices/{id}/preview-email      — Anteprima
POST   /api/invoices/{id}/send-sdi          — Invio SDI (inattivo)
POST   /api/invoices/{id}/duplicate         — Duplica
GET    /api/invoices/{id}/scadenze          — Scadenze pagamento
POST   /api/invoices/{id}/scadenze/pagamento — Registra pagamento
```

### Preventivi
```
GET    /api/preventivi                      — Lista
POST   /api/preventivi                      — Crea
GET    /api/preventivi/{id}                 — Dettaglio
PUT    /api/preventivi/{id}                 — Aggiorna
DELETE /api/preventivi/{id}                 — Elimina
GET    /api/preventivi/{id}/pdf             — PDF
POST   /api/preventivi/{id}/send-email      — Invia (custom)
GET    /api/preventivi/{id}/preview-email    — Anteprima
POST   /api/preventivi/{id}/convert-to-invoice — Converti in fattura
POST   /api/preventivi/{id}/progressive-invoice — Fattura progressiva
GET    /api/preventivi/{id}/invoicing-status    — Stato fatturazione
POST   /api/preventivi/{id}/check-compliance    — Verifica CAM
```

### DDT
```
GET    /api/ddt                     — Lista
POST   /api/ddt                     — Crea
GET    /api/ddt/{id}                — Dettaglio
PUT    /api/ddt/{id}                — Aggiorna
DELETE /api/ddt/{id}                — Elimina
GET    /api/ddt/{id}/pdf            — PDF
POST   /api/ddt/{id}/send-email     — Invia
GET    /api/ddt/{id}/preview-email   — Anteprima
POST   /api/ddt/{id}/convert-to-invoice — Converti in fattura
```

### CAM
```
GET    /api/cam/lotti                          — Lista lotti CAM
POST   /api/cam/lotti                          — Crea lotto
PUT    /api/cam/lotti/{id}                     — Aggiorna
GET    /api/cam/batches                        — Material batches
POST   /api/cam/batches                        — Crea batch
GET    /api/cam/calcolo/{commessa_id}          — Calcolo CAM commessa
POST   /api/cam/calcola/{commessa_id}          — Esegui calcolo
GET    /api/cam/dichiarazione-pdf/{commessa_id} — PDF dichiarazione
GET    /api/cam/report-aziendale               — Report aziendale
GET    /api/cam/report-aziendale/pdf           — PDF report
GET    /api/cam/archivio-certificati           — Certificati non abbinati
POST   /api/cam/archivio-certificati/{id}/assegna — Assegna a commessa
POST   /api/cam/import-da-certificato/{doc_id} — Import da certificato
```

### FPC / Tracciabilità EN 1090
```
GET    /api/fpc/projects                     — Lista progetti
POST   /api/fpc/projects                     — Crea
GET    /api/fpc/projects/{id}                — Dettaglio
PUT    /api/fpc/projects/{id}/fpc            — Aggiorna FPC
POST   /api/fpc/projects/{id}/assign-batch   — Assegna batch
POST   /api/fpc/projects/{id}/generate-ce    — Genera certificato CE
GET    /api/fpc/projects/{id}/ce-check       — Verifica CE
GET    /api/fpc/projects/{id}/dossier        — Dossier
GET    /api/fpc/welders                      — Registro saldatori
POST   /api/fpc/welders                      — Aggiungi saldatore
GET    /api/fpc/norme                        — Norme configurate
```

### (Tutti gli altri endpoint seguono lo stesso pattern CRUD)

---

## 6. NAVIGAZIONE SIDEBAR (DashboardLayout.js)

```
COMMERCIALE:
  /clients              — Clienti
  /preventivi           — Preventivi
  /invoices             — Fatturazione
  /fatture-ricevute     — Fatture Ricevute
  /ddt                  — DDT

PRODUZIONE:
  /planning             — Planning Cantieri (Kanban)
  /rilievi              — Rilievi
  /distinte             — Distinte Base
  /tracciabilita        — Tracciabilità EN 1090
  /sicurezza            — Sicurezza POS

CONFORMITA':
  /certificazioni       — Certificazioni CE
  /core-engine          — Core Engine Normativo
  /validazione-foto     — Validazione Foto AI
  /report-cam           — Report CAM / CO2

CATALOGO:
  /fornitori            — Fornitori
  /catalogo             — Catalogo Profili
  /articoli             — Catalogo Articoli
  /archivio-certificati — Archivio Certificati

SINISTRI:
  /perizie              — Perizie Sinistro
  /archivio-sinistri    — Archivio Sinistri

IMPOSTAZIONI:
  /settings             — Dati Azienda
  /impostazioni/pagamenti — Tipi Pagamento

PAGINA SPECIALE (non in sidebar):
  /commesse/:id         — Hub Commessa
  /ebitda               — Dashboard EBITDA
```

---

## 7. SERVIZI PDF

Ogni tipo documento ha il suo generatore PDF:
- **Fatture/Note Credito**: `pdf_template_v2.py` → `generate_invoice_pdf_v2()`
- **Preventivi**: `pdf_template_v2.py` → `generate_preventivo_pdf_v2()`
- **DDT**: `ddt_pdf_service.py`
- **RdP/OdA**: `pdf_procurement.py` → `generate_rdp_pdf()`, `generate_oda_pdf()`
- **CL DDT**: `pdf_procurement.py` → `generate_cl_pdf()`
- **Certificazione CE**: `certificazione_pdf_service.py`
- **POS Sicurezza**: `pos_pdf_service.py`
- **Rilievo**: `rilievo_pdf_service.py`
- **Perizia**: `perizia_pdf_service.py`
- **Distinta taglio**: `distinta_pdf_service.py`
- **Ottimizzatore**: `optimizer_pdf_service.py`
- **CAM Dichiarazione**: `pdf_cam_declaration.py`
- **CAM Report**: `pdf_cam_report.py`
- **Fascicolo Cantiere**: `fascicolo_generator.py`
- **Dossier Commessa**: `commessa_dossier.py`

Tutti usano **WeasyPrint** con template HTML + CSS inline.

---

## 8. FIX APPLICATI IN QUESTA SESSIONE

1. **FT-2026/0001 non trovato** — Regex anno corretto da `-{year}-` a `-{year}[-/]` in `invoices.py`
2. **PDF CL rotto** — Endpoint cambiato da POST a GET (`commessa_ops.py`)
3. **PDF CL iframe rotto** — Blob URL invalidato da `?token=` appendato (`CommessaOpsPanel.js`)
4. **PDF CL CSS mancante** — Aggiunto `COMMON_CSS` al template (`pdf_procurement.py`)
5. **Email CL senza funzione** — Creata `send_email_with_attachment` in `email_service.py`
6. **Query fornitore sbagliata** — Corretto `"id"` → `"client_id"` (`commessa_ops.py`)
7. **Fatture non collegate alla commessa** — Auto-link in `preventivi.py` → `moduli.fatture_ids`
8. **"Allega Modulo" con ID manuale** — Rifatto con dropdown + endpoint `available-modules`
9. **Select rotto nei Dialog** — Sostituito con `<select>` nativo
10. **Anteprima email** — Creato sistema completo per 6 tipi con edit testo
11. **Dialog expand** — Aggiunto fullscreen per email e PDF preview

---

## 9. TASK FUTURI (PRIORITIZZATI)

### P0 — Urgente
- Dashboard EBITDA: collegare calcoli finanziari (costi materiali vs vendita) ai grafici

### P1 — Importante
- Attivazione SDI con chiavi API Aruba/FattureInCloud
- Refactoring CommessaOpsPanel.js (2032 righe → sotto-componenti)

### P2 — Miglioramenti
- UX: tooltip su pulsanti disabilitati
- PWA per uso offline in cantiere
- Migrazione certificati da Base64 a object storage
- Export distinta taglio CSV per CNC
- Versioning fatture/dossier

### P3 — Backlog
- Stato "SOSPESA" per commesse
- Estendere "Distinta Facile"
- Categoria "CANCELLI" nel listino
- Migrazione dati EN 13241
- Integrazione Stripe pagamenti
- App mobile nativa

---

## 10. CREDENZIALI E CONFIGURAZIONE

- **MongoDB**: `mongodb://localhost:27017`, DB: `test_database`
- **Utente reale**: `user_97c773827822` (spano.franc75@gmail.com)
- **Auth**: Google OAuth via Emergent → cookie `session_token`
- **AI**: GPT-4o Vision via `EMERGENT_LLM_KEY`
- **Email**: Resend via `RESEND_API_KEY`
- **PDF**: WeasyPrint (richiede `poppler-utils` per pdf2image)

---

## 11. REGOLE PER L'AI DI SUPPORTO

1. **RISPONDI SEMPRE IN ITALIANO** — L'utente comunica solo in italiano
2. **NON usare Radix Select/Combobox dentro Dialog** — Usa `<select>` nativo HTML
3. **Escludi sempre `_id` dalle query MongoDB** — `{"_id": 0}` nelle proiezioni
4. **Testa con dati REALI** — I test con dati fittizi non coprono i flussi utente
5. **Formato numeri**: le fatture usano `/` (FT-2026/0001), le commesse usano `-` (NF-2026-000001)
6. **La commessa è l'entità centrale** — Tutto deve collegarsi ad essa
7. **Ogni send-email accetta custom_subject/custom_body** — Per personalizzazione
8. **CommessaOpsPanel.js è fragile** — 2032 righe, modificare con estrema cautela
9. **L'utente vuole un'app "collegata"** — Ogni modulo deve parlare con gli altri, niente silos
10. **pdf2image richiede poppler-utils** — Installare con `apt-get install poppler-utils`

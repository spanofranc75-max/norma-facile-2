# Norma Facile 2.0 — Project State Report

> **Data:** 2026-02-28 | **Versione:** Fase 29 | **Ambiente:** Kubernetes Preview

---

## 1. Struttura Progetto e Tech Stack

### 1.1 Tech Stack Confermato

| Layer | Tecnologia | Versione/Dettaglio |
|-------|-----------|-------------------|
| **Frontend** | React | CRA (Create React App) |
| **Routing** | react-router-dom | 7.5.1 |
| **UI** | Tailwind CSS + Shadcn/UI | 48 componenti UI in `/components/ui/` |
| **Grafici** | Recharts | 3.6.0 |
| **Mappe** | Leaflet + react-leaflet | 1.9.4 / 5.0.0 |
| **Disegno** | react-canvas-draw | 1.2.1 |
| **Backend** | FastAPI (Python) | via Uvicorn, gestito da Supervisor |
| **Database** | MongoDB | Locale, `test_database` |
| **PDF (Legale)** | WeasyPrint | 68.1 (HTML→PDF con CSS3) |
| **PDF (Generico)** | ReportLab | 4.4.10 |
| **AI/LLM** | OpenAI GPT-4o (Vision) | via `emergentintegrations` 0.1.0 + Emergent LLM Key |
| **Immagini** | Pillow | 12.1.1 |
| **Auth** | Google OAuth | Emergent-managed |

### 1.2 Struttura Backend — `/app/backend/`

```
backend/
├── main.py                          # FastAPI app, router mounting, CORS
├── server.py                        # Uvicorn entry point
├── requirements.txt
├── core/
│   ├── config.py                    # Env vars
│   ├── database.py                  # Motor MongoDB async client
│   ├── security.py                  # JWT/session auth middleware
│   └── engine/                      # NormaCore Engine (calcoli normativi)
│       ├── ce.py                    # Logica marcatura CE
│       ├── climate_zones.py         # Zone climatiche A-F con limiti Uw
│       ├── router.py                # Routing prodotto → norma applicabile
│       ├── safety.py                # Calcoli sicurezza
│       └── thermal.py               # ThermalValidator (ISO 10077-1)
├── models/                          # Pydantic schemas (14 files)
│   ├── certificazione.py
│   ├── chat.py
│   ├── client.py
│   ├── company.py
│   ├── ddt.py
│   ├── distinta.py
│   ├── document.py
│   ├── invoice.py
│   ├── payment_type.py
│   ├── perizia.py
│   ├── rilievo.py
│   ├── sicurezza.py
│   └── user.py
├── routes/                          # API routers (17 files, ~7.5k LOC)
│   ├── articoli.py        (279 LOC) # Catalogo Articoli CRUD + search + bulk-import
│   ├── auth.py             (60 LOC) # Google OAuth callback
│   ├── catalogo.py        (277 LOC) # Profili Utente custom CRUD + catalogo merged
│   ├── certificazioni.py  (211 LOC) # Certificazioni CE wizard + PDF + thermal
│   ├── chat.py                      # AI chat
│   ├── clients.py         (181 LOC) # Clienti + Fornitori CRUD
│   ├── company.py          (84 LOC) # Dati azienda
│   ├── dashboard.py       (252 LOC) # Stats + Fascicolo Cantiere
│   ├── ddt.py             (494 LOC) # DDT CRUD + PDF + stats/registro
│   ├── distinta.py        (461 LOC) # BOM CRUD + calcolo barre + optimizer + import rilievo
│   ├── documents.py        (30 LOC) # Upload generico (legacy)
│   ├── engine.py         (1162 LOC) # NormaCore: norme CRUD, componenti CRUD, calcolo, fascicolo, AI foto
│   ├── fatture_ricevute.py(697 LOC) # Fatture fornitori + XML FatturaPA import
│   ├── invoices.py        (830 LOC) # Fatture emesse + scadenze + quick-fill sources
│   ├── payment_types.py   (138 LOC) # Condizioni pagamento CRUD
│   ├── perizia.py         (813 LOC) # Perizia Sinistro wizard + AI foto analisi + PDF
│   ├── preventivi.py      (695 LOC) # Preventivi + compliance termica + convert-to-invoice + PDF
│   ├── rilievi.py         (350 LOC) # Rilievi CRUD + sketches + photos + PDF
│   ├── sicurezza.py       (250 LOC) # POS CRUD + AI risk assessment (GPT-4o)
│   └── vendor_api.py     (267 LOC)  # Vendor catalog + API keys
├── services/                        # Business logic e PDF generators (14 files, ~3.2k LOC)
│   ├── certificazione_pdf_service.py  (349 LOC) # PDF fascicolo CE (EN 1090 / EN 13241)
│   ├── ddt_pdf_service.py             (186 LOC) # PDF DDT
│   ├── distinta_pdf_service.py        (138 LOC) # PDF lista taglio
│   ├── fascicolo_generator.py         (471 LOC) # Generatore fascicolo universale (DoP, CE, Manuale)
│   ├── invoice_service.py             (166 LOC) # Calcoli fattura
│   ├── optimizer.py                   (165 LOC) # 1D Bin Packing (FFD)
│   ├── optimizer_pdf_service.py       (188 LOC) # PDF ottimizzazione taglio
│   ├── pdf_service.py                 (356 LOC) # Base PDF service (Preventivi)
│   ├── perizia_pdf_service.py         (217 LOC) # PDF perizia sinistro
│   ├── pos_pdf_service.py             (292 LOC) # PDF POS
│   ├── profiles_data.py              (122 LOC) # Database 49 profili standard
│   ├── rilievo_pdf_service.py         (283 LOC) # PDF rilievo misure
│   ├── thermal_calc.py                (22 LOC) # Wrapper → core/engine/thermal.py
│   └── xml_service.py                (213 LOC) # FatturaPA XML parser
└── tests/                           # Pytest suite (25 files)
```

### 1.3 Struttura Frontend — `/app/frontend/src/`

```
frontend/src/
├── App.js                           # Router principale (21 route protette)
├── App.css
├── index.js / index.css             # Entry + Industrial Blue CSS vars
├── contexts/
│   └── AuthContext.js               # Google OAuth context
├── hooks/
│   └── use-toast.js
├── lib/
│   └── utils.js                     # apiRequest helper, cn(), formatters
├── components/
│   ├── DashboardLayout.js           # Sidebar layout (19 nav items)
│   ├── ArticleSearch.js             # Autocomplete articoli in fattura
│   ├── EmptyState.js                # Empty state generico
│   ├── ErrorBoundary.js             # Global error boundary
│   ├── ProtectedRoute.js            # Auth guard
│   ├── QuickActionFAB.js            # Floating action button
│   ├── QuickFillModal.js            # Modale import da Preventivo/DDT
│   └── ui/                          # 48 Shadcn/UI components
├── pages/                           # 28 pagine (~13k LOC)
│   ├── LandingPage.js               # Landing + Google OAuth
│   ├── AuthCallback.js              # OAuth callback handler
│   ├── Dashboard.js            (313 LOC) # KPI + grafici Recharts
│   ├── ClientsPage.js         (525 LOC) # Gestione clienti/fornitori
│   ├── FornitoriPage.js       (520 LOC) # Gestione fornitori dedicata
│   ├── PreventiviPage.js            # Lista preventivi
│   ├── PreventivoEditorPage.js (548 LOC) # Editor preventivo + compliance termica
│   ├── InvoicesPage.js        (648 LOC) # Lista fatture + KPI pagamenti
│   ├── InvoiceEditorPage.js   (810 LOC) # Editor fattura + Quick Fill + Article Search
│   ├── FattureRicevutePage.js (672 LOC) # Fatture fornitori + import XML
│   ├── ArticoliPage.js        (483 LOC) # Catalogo articoli CRUD
│   ├── DDTListPage.js         (248 LOC) # Registro DDT + KPI + filtri
│   ├── DDTEditorPage.js       (474 LOC) # Editor DDT
│   ├── RilieviPage.js         (300 LOC) # Lista rilievi
│   ├── RilievoEditorPage.js   (814 LOC) # Editor rilievo + CanvasDraw + foto
│   ├── DistintePage.js        (280 LOC) # Lista distinte
│   ├── DistintaEditorPage.js (1001 LOC) # Editor BOM + optimizer
│   ├── CatalogoPage.js        (412 LOC) # Catalogo profili standard + custom
│   ├── CertificazioniPage.js        # Lista certificazioni CE
│   ├── CertificazioneWizardPage.js (719 LOC) # Wizard certificazione CE
│   ├── SicurezzaPage.js             # Lista POS
│   ├── PosWizardPage.js      (476 LOC) # Wizard POS + AI risk assessment
│   ├── CoreEnginePage.js      (810 LOC) # Configuratore prodotti + norme + componenti
│   ├── ValidazioneFotoPage.js (340 LOC) # AI validazione foto posa (GPT-4o Vision)
│   ├── PeriziaListPage.js           # Lista perizie
│   ├── PeriziaEditorPage.js   (861 LOC) # Editor perizia + AI analisi foto
│   ├── ArchivioSinistriPage.js(215 LOC) # Archivio/statistiche sinistri
│   ├── FascicoloCantierePage.js(206 LOC) # Fascicolo cantiere per cliente
│   ├── PaymentTypesPage.js    (297 LOC) # Condizioni pagamento
│   └── SettingsPage.js        (310 LOC) # Impostazioni azienda
```

---

## 2. Stato Completamento Moduli

### 2.1 Rilievo Misure — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Connesso a DB | **SI** | Collection `rilievi` (3 documenti attuali) |
| CRUD completo | **SI** | `GET/POST/PUT/DELETE /api/rilievi/` |
| Disegno (Drawing) | **SI** | `react-canvas-draw` integrato in `RilievoEditorPage.js` (riga 52) |
| Sketches con dimensioni | **SI** | `SketchEditor` component con `name`, `width`, `height`, `depth` |
| Foto allegati | **SI** | Upload foto con `base64` encoding via `POST /api/rilievi/{id}` (add_photo) |
| PDF export | **SI** | `rilievo_pdf_service.py` (283 LOC) |
| Import in Distinta | **SI** | `POST /api/distinte/{distinta_id}/import-rilievo/{rilievo_id}` |
| Filtri per cliente/stato | **SI** | Parametri query `client_id`, `status` |

**Endpoint attivi:**
- `GET /api/rilievi/` — lista con filtri
- `POST /api/rilievi/` — crea rilievo
- `GET /api/rilievi/{id}` — dettaglio
- `PUT /api/rilievi/{id}` — aggiorna
- `DELETE /api/rilievi/{id}` — elimina
- `GET /api/rilievi/{id}/pdf` — export PDF

---

### 2.2 Distinta Materiali (BOM) — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Connessa a DB | **SI** | Collection `distinte` (2 documenti attuali) |
| CRUD completo | **SI** | `GET/POST/PUT/DELETE /api/distinte/` |
| Calcolo pesi | **SI** | `calculate_item()` in `distinta.py:29` — `length_m × quantity × weight_per_meter` |
| Calcolo superfici | **SI** | `surface_per_meter × length_m × quantity` |
| Calcolo costi | **SI** | `quantity × cost_per_unit` |
| Totali aggregati | **SI** | `calculate_totals()` — peso totale, superficie, costo, breakdown per categoria |
| Optimizer (Bin Packing) | **SI** | `optimizer.py` (165 LOC) — FFD (First Fit Decreasing) 1D bin packing |
| Barra standard | **SI** | Default 6000mm, kerf 3mm (configurabile) |
| Lista taglio PDF | **SI** | `distinta_pdf_service.py` + `optimizer_pdf_service.py` |
| Import da Rilievo | **SI** | `POST /api/distinte/{id}/import-rilievo/{rilievo_id}` |

**Endpoint attivi:**
- `GET /api/distinte/` — lista
- `POST /api/distinte/` — crea
- `PUT /api/distinte/{id}` — aggiorna con ricalcolo
- `DELETE /api/distinte/{id}` — elimina
- `GET /api/distinte/{id}/calcola-barre` — calcolo barre necessarie
- `POST /api/distinte/{id}/ottimizza-taglio` — esegue bin packing FFD
- `GET /api/distinte/{id}/lista-taglio-pdf` — PDF lista taglio
- `GET /api/distinte/{id}/ottimizza-taglio-pdf` — PDF ottimizzazione

---

### 2.3 Certificazioni CE — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Connessa a DB | **SI** | Collection `certificazioni` (0 documenti — pronta per uso) |
| Template EN 1090-1 | **SI** | `certificazione_pdf_service.py` — DoP, etichetta CE, manuale specifico per strutture acciaio |
| Template EN 13241 | **SI** | `certificazione_pdf_service.py:79-332` — Logica condizionale per cancelli/portoni (sicurezza apertura, forza chiusura, EN 12453) |
| Template UNI EN 14351-1 | **SI** | Via NormaCore engine: configurazione JSON, calcolo Uw, validazione zone climatiche |
| Wizard multi-step | **SI** | `CertificazioneWizardPage.js` (719 LOC) |
| Calcolo termico | **SI** | `ThermalValidator` in `core/engine/thermal.py` — formula ISO 10077-1: `(Ag×Ug + Af×Uf + lg×Ψ) / (Ag+Af)` |
| Validazione compliance | **SI** | `POST /api/certificazioni/{id}/validate` |
| PDF fascicolo | **SI** | `GET /api/certificazioni/{id}/pdf` → WeasyPrint |
| Routing prodotto→norma | **SI** | `GET /api/certificazioni/router/{product_type}` |

**Endpoint attivi:**
- `GET/POST /api/certificazioni/` — CRUD
- `GET /api/certificazioni/{id}/pdf` — PDF fascicolo completo
- `POST /api/certificazioni/{id}/validate` — validazione
- `GET /api/certificazioni/thermal/reference` — dati riferimento (vetri, telai, distanziatori)
- `POST /api/certificazioni/thermal/calculate` — calcolo Uw
- `GET /api/certificazioni/router/{product_type}` — routing norma

---

### 2.4 Sicurezza (POS) — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Connesso a DB | **SI** | Collection `pos_documents` (0 documenti — pronto per uso) |
| CRUD completo | **SI** | `GET/POST/PUT/DELETE /api/sicurezza/` |
| AI Risk Assessment | **SI** | `POST /api/sicurezza/{id}/generate-risk-assessment` → GPT-4o via `emergentintegrations` |
| Modello AI | **GPT-4o** | `LlmChat(...).with_model("openai", "gpt-4o")` in `sicurezza.py:185` |
| PDF POS | **SI** | `pos_pdf_service.py` (292 LOC) |
| Suggerimento DPI | **SI** | `POST /api/sicurezza/{id}/suggest-dpi` |
| Validazione | **SI** | `POST /api/sicurezza/{id}/validate` |
| Rischi precaricati | **SI** | `GET /api/sicurezza/rischi` — lista rischi standard metallurgia |

**Endpoint attivi:**
- `GET/POST /api/sicurezza/` — CRUD
- `POST /api/sicurezza/{id}/generate-risk-assessment` — **AI genera valutazione rischi**
- `GET /api/sicurezza/{id}/pdf` — PDF POS
- `POST /api/sicurezza/{id}/validate` — validazione completezza
- `POST /api/sicurezza/{id}/suggest-dpi` — suggerimento DPI

---

### 2.5 Preventivi — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Connesso a DB | **SI** | Collection `preventivi` (0 documenti — pronto per uso) |
| CRUD completo | **SI** | `GET/POST/PUT/DELETE /api/preventivi/` |
| Smart Quote (Thermal) | **SI** | `run_compliance()` in `preventivi.py:132` — calcola Uw per ogni riga con `thermal_data` |
| Validazione zone climatiche | **SI** | Importa `ThermalValidator` e `ClimateZone` da `core.engine` |
| Compliance auto | **SI** | Calcolata alla creazione (`preventivi.py:236`) e salvata in `compliance_status` + `compliance_detail` |
| Sconto globale + acconto | **SI** | Campi `sconto_globale`, `acconto` |
| Conversione in Fattura | **SI** | `POST /api/preventivi/{id}/convert-to-invoice` |
| PDF export | **SI** | `GET /api/preventivi/{id}/pdf` via ReportLab |

**Dettaglio calcolo compliance:**
```python
# preventivi.py:133-166
for item in lines:
    td = item.get("thermal_data")
    if td and td.get("glass_type") and td.get("frame_type"):
        inp = ThermalInput(glass_type=..., frame_type=..., ...)
        result = ThermalValidator.calculate(inp)
        # Verifica vs limite zona climatica
        zone_check = ThermalValidator.check_zone(result.uw, zona)
        results.append({item, uw, zone, compliant, ...})
```

**Endpoint attivi:**
- `GET/POST /api/preventivi/` — CRUD
- `POST /api/preventivi/{id}/check-compliance` — verifica compliance termica
- `POST /api/preventivi/{id}/convert-to-invoice` — converti in fattura
- `GET /api/preventivi/{id}/pdf` — PDF preventivo

---

### 2.6 Catalogo Profili — **100%**

| Aspetto | Stato | Dettaglio |
|---------|-------|-----------|
| Profili standard | **SI** | 49 profili in `profiles_data.py` (tubolari, rettangolari, piatti, angolari, IPE/HEA/UPN, tondi, lamiere) |
| Profili custom utente | **SI** | `POST /api/catalogo/profiles` → collection `user_profiles` |
| CRUD custom | **SI** | `GET/POST/PUT/DELETE /api/catalogo/profiles/` |
| Catalogo merged | **SI** | `GET /api/catalogo/merged` — standard + custom in un'unica lista |
| Aggiornamento prezzi bulk | **SI** | `POST /api/catalogo/profiles/bulk-price-update` |
| Filtri per tipo | **SI** | Parametri `profile_type`, `search`, `source` |

**Endpoint attivi:**
- `GET /api/catalogo/profiles` — lista custom con filtri
- `POST /api/catalogo/profiles` — crea profilo custom
- `PUT /api/catalogo/profiles/{id}` — aggiorna
- `DELETE /api/catalogo/profiles/{id}` — elimina
- `POST /api/catalogo/profiles/bulk-price-update` — aggiornamento prezzi
- `GET /api/catalogo/merged` — catalogo completo (standard + custom)

---

### 2.7 Moduli Aggiuntivi Completati

| Modulo | Stato | Dettaglio chiave |
|--------|-------|-----------------|
| **Fatturazione** | 100% | CRUD + scadenze + pagamenti parziali + KPI + Quick Fill da Preventivo/DDT |
| **DDT (Registro)** | 100% | CRUD + numerazione auto + PDF + convert-to-invoice + KPI mensile + filtri data |
| **Fatture Ricevute** | 100% | Import XML FatturaPA + estrazione articoli in catalogo + pagamenti |
| **Catalogo Articoli** | 100% | CRUD + search + storico prezzi + bulk import da fatture |
| **Perizia Sinistro** | 100% | Wizard AI + analisi foto (GPT-4o Vision) + smart algorithm (7 voci costo) + PDF + archivio |
| **Core Engine** | 100% | Norme JSON-driven + componenti + calcolo universale + fascicolo auto (DoP+CE+Manuale) |
| **Validazione Foto AI** | 100% | Upload + GPT-4o Vision + checklist per tipo prodotto + report strutturato |
| **Dashboard** | 100% | KPI (fatturato, DDT, preventivi, clienti) + grafici Recharts |
| **Fornitori** | 100% | CRUD dedicato con categorizzazione |
| **Impostazioni** | 100% | Dati azienda + condizioni pagamento CRUD |

---

## 3. Schema Database MongoDB

**Database:** `test_database` | **Collections attive:** 21

| Collection | Documenti | Campi principali |
|-----------|-----------|------------------|
| `users` | 23 | `user_id`, `email`, `name`, `picture`, `created_at` |
| `sessions` | 1 | `session_id`, `user_id`, `email`, `name`, `picture`, `expires_at` |
| `user_sessions` | 23 | `user_id`, `session_token`, `expires_at`, `created_at` |
| `clients` | 4 | `client_id`, `user_id`, `business_name`, `client_type`, `codice_fiscale`, `partita_iva`, `codice_sdi`, `pec`, `address`, `cap`, `city`, `province` |
| `invoices` | 7 | `invoice_id`, `user_id`, `document_type`, `document_number`, `client_id`, `issue_date`, `due_date`, `status`, `payment_method`, `lines`, `tax_settings`, `payment_installments` |
| `preventivi` | 0 | `preventivo_id`, `user_id`, `number`, `client_id`, `subject`, `lines[]` (con `thermal_data`), `totals`, `compliance_status`, `sconto_globale`, `acconto` |
| `ddt_documents` | 3 | `ddt_id`, `user_id`, `number`, `ddt_type`, `client_id`, `client_name`, `destinazione`, `causale_trasporto`, `aspetto_beni`, `lines`, `totals`, `status` |
| `document_counters` | 3 | `counter_id`, `counter` — numerazione progressiva (FT, PRV, DDT) |
| `rilievi` | 3 | `rilievo_id`, `user_id`, `client_id`, `project_name`, `survey_date`, `location`, `status`, `sketches[]`, `photos[]`, `notes` |
| `distinte` | 2 | `distinta_id`, `user_id`, `name`, `rilievo_id`, `client_id`, `status`, `items[]` (profilo, lunghezza, quantità, peso), `totals` |
| `certificazioni` | 0 | `cert_id`, `user_id`, `client_id`, `standard` (EN 1090-1/EN 13241), `product_description`, `specifications{}`, `thermal_data{}`, `declaration_number` |
| `pos_documents` | 0 | `pos_id`, `user_id`, `client_id`, `cantiere_name`, `cantiere_indirizzo`, `data_inizio/fine`, `rischi[]`, `dpi[]`, `misure_prevenzione[]`, `risk_assessment_ai` |
| `perizie` | 7 | `perizia_id`, `user_id`, `number`, `client_id`, `tipo_danno`, `localizzazione`, `moduli[]`, `voci_costo[]`, `foto_analisi_ai`, `totale_perizia` |
| `articoli` | 1 | `articolo_id`, `user_id`, `codice`, `descrizione`, `categoria`, `unita_misura`, `prezzo_unitario`, `aliquota_iva`, `fornitore_nome`, `storico_prezzi[]` |
| `fatture_ricevute` | 0 | `fattura_id`, `user_id`, `fornitore_info{}`, `numero`, `data`, `totale`, `lines[]`, `xml_filename`, `pagamenti[]` |
| `norme_config` | 3 | `norma_id`, `title`, `standard_ref`, `product_types[]`, `required_performances[]`, `mandatory_fields[]`, `validation_rules[]`, `calculation_methods[]` |
| `componenti` | 21 | `comp_id`, `codice`, `label`, `tipo` (vetro/telaio/distanziatore), `ug`/`uf`/`psi`, `thickness_mm`, `produttore` |
| `user_profiles` | 0 | `profile_id`, `user_id`, `code`, `type`, `label`, `dimensions`, `weight_per_meter`, `surface_per_meter`, `price_per_meter` |
| `vendor_catalogs` | 0 | `catalog_id`, `vendor_id`, `profiles[]` |
| `vendor_keys` | 0 | `key_id`, `user_id`, `vendor_name`, `api_key` |
| `payment_types` | 1 | `payment_type_id`, `user_id`, `codice`, `tipo`, `descrizione`, `immediato`, `gg_30`...`gg_180` |

**Norme seed presenti (`norme_config`):**
1. **EN 1090-1** — Strutture in acciaio (classe esecuzione EXC1-EXC4, reazione fuoco, tolleranze)
2. **EN 13241** — Cancelli e portoni industriali (sicurezza apertura EN 12453, forza, permeabilità)
3. **UNI EN 14351-1** — Finestre e porte esterne (Uw, permeabilità aria, tenuta acqua, resistenza vento)

**Componenti seed presenti (`componenti`):**
- 8 Vetri (4/16/4 standard → triplo basso-emissivo)
- 8 Telai (PVC, alluminio, legno, alluminio-legno, con/senza taglio termico)
- 5 Distanziatori (alluminio, acciaio, warm-edge, super warm-edge, TGI)

---

## 4. Stato UI/UX

### 4.1 Tema "Industrial Blue" — **IMPLEMENTATO**

Definito in `/app/frontend/src/index.css`:

```css
:root {
    --industrial-blue: #0055FF;    /* Accent primario */
    --sidebar-bg: #1E293B;         /* Sidebar scura (Slate 800) */
    --text-primary: #334155;       /* Testo principale */
    --primary: 220 100% 50%;       /* HSL per Shadcn */
}
```

| Elemento | Colore | Implementazione |
|---------|--------|----------------|
| Sidebar background | `#1E293B` | `DashboardLayout.js:81` — `bg-[#1E293B]` |
| Active nav item | `#0055FF` | `bg-[#0055FF] text-white font-medium` |
| Button primario | `#0055FF` | CSS class `.btn-industrial` |
| Table header | `#1E293B` | `bg-[#1E293B] text-white` su tutti i `<TableHeader>` |
| Numeri documento | `#0055FF` | `font-mono text-[#0055FF] font-semibold` |
| Icona logo | Scale | `text-[#0055FF]` |
| Landing CTA | `#0055FF` | `bg-[#0055FF] hover:bg-[#0044CC]` |

### 4.2 Sidebar — 19 Voci di Navigazione

| # | Path | Label | Icona |
|---|------|-------|-------|
| 1 | `/dashboard` | Dashboard | Sparkles |
| 2 | `/preventivi` | Preventivi | ClipboardList |
| 3 | `/invoices` | Fatturazione | Receipt |
| 4 | `/fatture-ricevute` | Fatture Ricevute | FileInput |
| 5 | `/clients` | Clienti | Users |
| 6 | `/fornitori` | Fornitori | Factory |
| 7 | `/articoli` | Catalogo Articoli | BoxIcon |
| 8 | `/core-engine` | Core Engine | Shield |
| 9 | `/validazione-foto` | Validazione Foto AI | Camera |
| 10 | `/rilievi` | Rilievi | Ruler |
| 11 | `/distinte` | Distinte | Package |
| 12 | `/catalogo` | Catalogo Profili | Warehouse |
| 13 | `/certificazioni` | Certificazioni CE | Shield |
| 14 | `/sicurezza` | Sicurezza (POS) | HardHat |
| 15 | `/ddt` | DDT | Truck |
| 16 | `/perizie` | Perizie Sinistro | ShieldAlert |
| 17 | `/archivio-sinistri` | Archivio Sinistri | BarChart3 |
| 18 | `/impostazioni/pagamenti` | Tipi Pagamento | CreditCard |
| 19 | `/settings` | Impostazioni | Settings |

### 4.3 Componenti UI Custom

| Componente | File | Funzione |
|-----------|------|----------|
| `DashboardLayout` | `DashboardLayout.js` | Layout con sidebar collapsible + user avatar |
| `ArticleSearch` | `ArticleSearch.js` | Autocomplete catalogo articoli per fattura |
| `QuickFillModal` | `QuickFillModal.js` | Modale selezione Preventivo/DDT per Quick Fill |
| `EmptyState` | `EmptyState.js` | Stato vuoto personalizzabile per ogni modulo |
| `ErrorBoundary` | `ErrorBoundary.js` | Catch globale errori React (risolve crash `removeChild`) |
| `QuickActionFAB` | `QuickActionFAB.js` | Bottone azione rapida floating |
| `ProtectedRoute` | `ProtectedRoute.js` | Guard autenticazione OAuth |

---

## 5. Mappa Endpoint API Completa

### Autenticazione
- `POST /api/auth/google` — Google OAuth callback

### Dashboard
- `GET /api/dashboard/stats` — KPI globali
- `GET /api/dashboard/fascicolo/{client_id}` — Fascicolo cantiere per cliente

### Clienti & Fornitori
- `GET/POST /api/clients/` — CRUD (filtro `client_type`)
- `GET/PUT/DELETE /api/clients/{id}`

### Preventivi
- `GET/POST /api/preventivi/` — CRUD
- `POST /api/preventivi/{id}/check-compliance` — Verifica termica
- `POST /api/preventivi/{id}/convert-to-invoice` — Converti in fattura
- `GET /api/preventivi/{id}/pdf` — Export PDF

### Fatturazione
- `GET/POST /api/invoices/` — CRUD
- `GET /api/invoices/quick-fill/sources` — Sorgenti Quick Fill (preventivi + DDT)
- `GET /api/invoices/{id}/scadenze` — Piano scadenze
- `POST /api/invoices/{id}/scadenze/pagamento` — Registra pagamento
- `POST /api/invoices/{id}/duplicate` — Duplica come bozza
- `GET /api/invoices/{id}/pdf` — Export PDF

### Fatture Ricevute
- `GET/POST /api/fatture-ricevute/` — CRUD + KPI
- `POST /api/fatture-ricevute/import-xml` — Import FatturaPA XML
- `POST /api/fatture-ricevute/preview-xml` — Anteprima XML
- `POST /api/fatture-ricevute/{id}/extract-articoli` — Estrai in catalogo
- `GET/POST /api/fatture-ricevute/{id}/pagamenti` — Pagamenti

### DDT
- `GET/POST /api/ddt/` — CRUD (filtri: `ddt_type`, `status`, `search`, `date_from`, `date_to`)
- `GET /api/ddt/stats/registro` — KPI mensili (params: `year`, `month`)
- `POST /api/ddt/{id}/convert-to-invoice` — Converti in fattura
- `GET /api/ddt/{id}/pdf` — Export PDF

### Articoli
- `GET/POST /api/articoli/` — CRUD
- `GET /api/articoli/search?q=...` — Ricerca autocomplete
- `POST /api/articoli/bulk-import` — Import da fattura ricevuta

### Rilievi
- `GET/POST /api/rilievi/` — CRUD
- `PUT /api/rilievi/{id}` — Aggiorna (sketches + photos)
- `GET /api/rilievi/{id}/pdf` — Export PDF

### Distinte (BOM)
- `GET/POST /api/distinte/` — CRUD
- `GET /api/distinte/{id}/calcola-barre` — Calcolo barre
- `POST /api/distinte/{id}/ottimizza-taglio` — Bin Packing FFD
- `GET /api/distinte/{id}/lista-taglio-pdf` — PDF lista taglio
- `GET /api/distinte/{id}/ottimizza-taglio-pdf` — PDF ottimizzazione
- `POST /api/distinte/{id}/import-rilievo/{rilievo_id}` — Import da rilievo

### Catalogo Profili
- `GET/POST /api/catalogo/profiles` — CRUD custom
- `POST /api/catalogo/profiles/bulk-price-update` — Aggiornamento prezzi
- `GET /api/catalogo/merged` — Standard (49) + custom unificati

### Certificazioni CE
- `GET/POST /api/certificazioni/` — CRUD
- `POST /api/certificazioni/{id}/validate` — Validazione
- `GET /api/certificazioni/{id}/pdf` — PDF fascicolo
- `GET /api/certificazioni/thermal/reference` — Dati riferimento
- `POST /api/certificazioni/thermal/calculate` — Calcolo Uw
- `GET /api/certificazioni/router/{product_type}` — Routing norma

### Sicurezza (POS)
- `GET/POST /api/sicurezza/` — CRUD
- `POST /api/sicurezza/{id}/generate-risk-assessment` — **AI risk assessment (GPT-4o)**
- `GET /api/sicurezza/{id}/pdf` — PDF POS
- `POST /api/sicurezza/{id}/validate` — Validazione
- `POST /api/sicurezza/{id}/suggest-dpi` — Suggerimento DPI
- `GET /api/sicurezza/rischi` — Lista rischi standard

### Core Engine (Norme + Componenti)
- `GET/POST /api/engine/norme` — CRUD norme (JSON config)
- `POST /api/engine/norme/seed` — Seed 3 norme standard
- `GET/POST /api/engine/componenti` — CRUD componenti
- `POST /api/engine/componenti/seed` — Seed 21 componenti
- `POST /api/engine/calculate` — Calcolo universale
- `POST /api/engine/generate-fascicolo` — Genera DoP + CE + Manuale (PDF/ZIP)
- `POST /api/engine/validate-installation-photos` — **AI validazione foto (GPT-4o Vision)**

### Perizia Sinistro
- `GET/POST /api/perizie/` — CRUD
- `POST /api/perizie/{id}/analyze-photos` — **AI analisi danni (GPT-4o Vision)**
- `POST /api/perizie/{id}/generate-lettera` — AI genera lettera legale
- `POST /api/perizie/{id}/recalc` — Ricalcolo smart algorithm
- `GET /api/perizie/{id}/pdf` — PDF perizia
- `GET /api/perizie/archivio/stats` — Statistiche archivio

### Azienda & Pagamenti
- `GET/PUT /api/company/settings` — Dati azienda
- `GET/POST /api/payment-types/` — CRUD condizioni pagamento
- `POST /api/payment-types/seed-defaults` — Seed condizioni standard

---

## 6. Test Suite

**Cartella:** `/app/backend/tests/` — **25 file pytest**

| File | Copertura |
|------|-----------|
| `test_articoli_payments.py` | Catalogo articoli + pagamenti |
| `test_catalogo_profili.py` | Profili custom |
| `test_certificazioni.py` | Certificazioni CE |
| `test_codici_danno_archivio.py` | Codici danno + archivio |
| `test_convert_to_invoice.py` | Conversione preventivo → fattura |
| `test_core_engine.py` | NormaCore engine |
| `test_dashboard_stats.py` | Dashboard KPI |
| `test_ddt.py` | DDT CRUD |
| `test_ddt_convert_to_invoice.py` | DDT → fattura |
| `test_fascicolo_generation.py` | Generazione fascicolo |
| `test_fatture_ricevute.py` | Fatture ricevute + XML import |
| `test_fornitori.py` | Fornitori |
| `test_genera_lettera.py` | AI lettera legale |
| `test_import_rilievo.py` | Import rilievo in distinta |
| `test_norma_core_engine.py` | NormaCore avanzato |
| `test_norma_router_vendor_api.py` | Router norma + vendor |
| `test_optimizer.py` | Bin packing optimizer |
| `test_p1_features.py` | Feature P1 (DDT stats, Quick Fill, AI foto) |
| `test_payment_types_clients.py` | Pagamenti + clienti |
| `test_perizia_sinistro.py` | Perizia sinistro |
| `test_preventivi.py` / `test_preventivi_v2.py` | Preventivi |
| `test_sicurezza.py` | POS |
| `test_sinistro_smart_algorithm.py` | Smart algorithm perizia |
| `test_smart_bom.py` | BOM smart |
| `test_thermal_calculator.py` | Calcolo termico |

**Report di test:** `/app/test_reports/` — 37 iterazioni, tutti 100% pass rate.

---

*Report generato il 2026-02-28. Norma Facile 2.0 — Fase 29.*

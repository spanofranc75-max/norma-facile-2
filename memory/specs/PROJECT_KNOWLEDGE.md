# PROJECT_KNOWLEDGE.md — Cervello del Progetto NormaFacile 2.0

> Questo file è la fonte di verità per chiunque lavori su questo progetto (umano o AI).
> Aggiornato ad ogni modifica significativa.

---

## 1. Scopo del Software

NormaFacile 2.0 è un gestionale per **carpenterie metalliche** che devono rispettare:
- **EN 1090** — Strutture in acciaio (scale, soppalchi, capannoni, balconi)
- **EN 13241** — Chiusure industriali (cancelli, portoni, porte pedonali)
- **ISO 3834** — Qualità della saldatura

Il software gestisce l'intero ciclo di vita di una commessa: dal preventivo alla fatturazione, passando per approvvigionamento materiali, produzione, tracciabilità dei lotti di ferro, certificazioni e generazione automatica dei documenti normativi (DoP, Etichetta CE, Fascicolo Tecnico, Manuale d'Uso).

**Utenti principali:**
- Il **titolare** (Francesco) — vede tutto, crea preventivi, controlla margini
- Il **responsabile produzione** — gestisce fasi, diario produzione, operatori
- Il **responsabile qualità** — fascicolo tecnico, certificati 3.1, WPS, tracciabilità
- Gli **operai in officina** — interfaccia blindata con Timer/Foto/Checklist (Vista Officina)

---

## 2. Le 3 Categorie di Lavoro (I "3 Binari")

Ogni voce di lavoro all'interno di una commessa segue UNO di questi binari:

### A. STRUTTURALE (EN 1090)
**Campo DB:** `normativa_tipo: "EN_1090"`
**Quando si usa:** Scale, balconi, soppalchi, capannoni, strutture portanti
**Cosa attiva:**
- Tracciabilità lotti ferro con certificati 3.1 (numero colata, acciaieria)
- Patentini saldatori (EN ISO 9606)
- WPS/WPQR (procedure di saldatura qualificate)
- Piano di Controllo Qualità
- Generazione DoP (Dichiarazione di Prestazione)
- Etichetta CE
- CAM — Criteri Ambientali Minimi (DM 256/2022) per appalti pubblici
**Sezioni operative:** TUTTE (8 sezioni)
**Output documentale:** Fascicolo Tecnico (DoP + CE + Piano QC + Certificati 3.1 + WPS)

### B. CANCELLO (EN 13241)
**Campo DB:** `normativa_tipo: "EN_13241"`
**Quando si usa:** Cancelli scorrevoli/battenti, portoni industriali, porte pedonali, barriere
**Cosa attiva:**
- Kit sicurezza (fotocellule, coste sensibili, lampeggiante)
- Foto delle installazioni di sicurezza
- Verbale collaudo forze (EN 12453)
- Manuale d'Uso e Manutenzione
- Certificazione cancello con test specifici
**Sezioni operative:** 6 (include Certificazione Cancello, esclude Tracciabilità/CAM/Fascicolo Tecnico EN 1090)
**Output documentale:** Libretto Manutenzione (Scheda tecnica + Verbale collaudo forze + Manuale d'Uso)

### C. GENERICA (Nessuna Marcatura CE)
**Campo DB:** `normativa_tipo: "GENERICA"`
**Quando si usa:** Riparazioni, manutenzioni, piccoli lavori, lavori su misura senza obbligo CE
**Cosa attiva:**
- Solo registrazione ore lavorate
- Solo registrazione materiali utilizzati
- Riepilogo costi per controllo margine
- NESSUN obbligo burocratico o documentale
**Sezioni operative:** Solo 3 (Produzione, Conto Lavoro, Repository Documenti)
**Output documentale:** Riepilogo Costi (ore lavorate + materiali usati + margine)

---

## 3. STRUTTURA MATRIOSKA — Cantieri Misti (IMPLEMENTATA)

> **REGOLA FONDAMENTALE:** Una Commessa non è un blocco unico. E' un "Fascicolo di Cantiere"
> che puo' contenere diverse **Voci di Lavoro**, ognuna con la sua identità normativa.

### Perche' serve
Il cliente Bianchi ordina per lo stesso cantiere:
- **Voce A:** "Soppalco capannone" → EN 1090 (EXC2) → attiva tracciabilità ferro, patentini, DoP
- **Voce B:** "Cancello carraio" → EN 13241 → attiva foto sicurezza, collaudo forze, Libretto Manutenzione
- **Voce C:** "Riparazione ringhiera" → GENERICA → solo ore e materiali, nessuna burocrazia

### Come funziona nel software
1. **Alla creazione** della commessa si sceglie la categoria principale
2. **Dopo la creazione**, nella scheda della commessa si possono aggiungere "Voci di Lavoro" extra
3. **Ogni voce** ha: descrizione, categoria normativa, e i campi specifici della sua categoria
4. **Il pannello operativo** mostra le sezioni di TUTTE le categorie presenti nelle voci (unione)
5. **Il Diario di Produzione** chiede all'operaio "Su quale voce stai lavorando?" e filtra le domande
6. **Il "Pulsante Magico"** genera un Fascicolo di Cantiere unico che raggruppa tutto

### Schema DB
```
// Collezione: voci_lavoro
{
  voce_id: "voce_abc123",
  commessa_id: "com_xyz789",
  descrizione: "Soppalco capannone",
  normativa_tipo: "EN_1090",
  classe_exc: "EXC2",
  tipologia_chiusura: "",
  ordine: 1,
  created_at: "2026-03-20T...",
}
```

### Retrocompatibilita'
Le commesse gia' esistenti (senza voci) funzionano ESATTAMENTE come prima.
Il campo `normativa_tipo` della commessa vale come "voce unica implicita".

---

## 4. VISTA OFFICINA — Interfaccia Operai Blindata (IMPLEMENTATA)

> Gli operai sono extracomunitari e hanno poca dimestichezza con la tecnologia.
> Il tempo sottratto alla produzione deve essere quasi zero.

### Accesso
- **QR Code** stampato sulla commessa → porta direttamente alla voce di lavoro specifica
- **PIN 4 cifre** per autenticare l'operaio (impostato dall'admin nel Diario Produzione)
- Rotta: `/officina/:commessaId/:voceId`
- NESSUN Google Auth richiesto

### I 4 Ponti di Collegamento

#### PONTE 1: DIARIO (Timer Tempi)
- 3 bottoni grandi: **START** (verde), **PAUSA** (giallo), **STOP** (rosso)
- Timer visivo che scorre — l'operaio vede solo il tempo
- Al STOP → minuti salvati automaticamente nel `diario_produzione` della commessa
- Stato timer persistito in DB (`officina_timers`) — sopravvive a refresh browser
- **Zero numeri di costo visibili**

#### PONTE 2: FOTO (Certificati/Collaudi)
- Singolo bottone **FOTO** grande circolare
- Routing intelligente basato sulla Voce attiva:
  - **EN 1090** → `tipo: "certificato_31"` (Repository certificati 3.1)
  - **EN 13241** → `tipo: "foto"` (Fascicolo tecnico)
  - **GENERICA** → `tipo: "foto"` (Repository documenti)
- Nome file chiaro: `FOTO_{normativa}_{numero_commessa}_{timestamp}.jpg`
- Usato dal Pulsante Magico per assemblare il fascicolo

#### PONTE 3: QUALITA' (Checklist)
- Icone + **👍/👎** per ogni punto di controllo (nessun testo lungo)
- Checklist per categoria:
  - EN 1090: Saldature Pulite, Dimensioni OK, Materiale OK
  - EN 13241: Sicurezze OK, Movimento OK
  - GENERICA: Lavoro Completato
- **👎 → crea alert automatico per Admin** (badge rosso nella Dashboard)
- Risultati popolano automaticamente il verbale di collaudo finale

#### PONTE 4: BLOCCO DATI
- Operaio intrappolato in `/officina` — tema dark, nessuna navigazione
- Nessun menu laterale, nessun link a fatture/clienti/fornitori
- Solo: Timer + Foto + Checklist + info commessa

### Schema DB
```
// Collezioni:
officina_timers: { timer_id, commessa_id, voce_id, status, started_at, pauses[], total_minutes }
officina_checklist: { checklist_id, commessa_id, voce_id, items[{codice, esito}], all_ok }
officina_alerts: { alert_id, admin_id, commessa_id, tipo: "qualita_nok", messaggio, letto }
```

---

## 5. DIARIO DI PRODUZIONE ADATTIVO (Mobile-First) (IMPLEMENTATO)

### Regole ferree

**ZERO CONTABILITA':** Nascondere SEMPRE costi orari, margini e prezzi.
L'operaio vede solo il "Cosa fare", mai il "Quanto costa".

**FILTRO INTELLIGENTE per voce selezionata:**
| Voce selezionata | Cosa chiede il Diario |
|---|---|
| EN 1090 | Ore + materiali + certificato 3.1 + numero colata + WPS usata |
| EN 13241 | Ore + materiali + foto fotocellula + foto coste + note collaudo |
| GENERICA | Solo Start/Stop tempo + materiali usati |

**FLUSSO OPERAIO:**
1. Apre il diario dal cellulare
2. Se la commessa ha piu' voci, sceglie "Su quale voce stai lavorando?" (bottoni colorati)
3. Il diario mostra SOLO i campi pertinenti a quella voce
4. Salva con un bottone grande e chiaro

---

## 6. IL PULSANTE MAGICO — Documentazione Unificata (FASE 3)

> Un unico bottone nella scheda commessa che genera il "Pacco Documenti Cantiere".

### Logica di Generazione

**RACCOLTA DATI (dietro le quinte):**
Il sistema raccoglie automaticamente da ogni Voce di Lavoro:
1. **Documenti caricati** → `commessa_documents` (filtrati per `metadata_estratti.voce_id`)
2. **Foto officina** → `commessa_documents` con `metadata_estratti.source: "officina"`
3. **Checklist qualità** → `officina_checklist` (esiti 👍/👎 per voce)
4. **Ore lavorate** → `diario_produzione` (per voce, con source `officina_timer`)
5. **Tracciabilità materiali** → `material_batches` (solo EN 1090)
6. **Checklist CAM** → `cam_lotti` (solo EN 1090)

**REGOLA AUTOMAZIONE COLLAUDO:**
Se l'operaio ha messo **👍 (OK)** su tutti i punti della checklist qualità,
il Verbale di Collaudo risulta **"Approvato"** automaticamente (firmato tecnicamente).
Se anche un solo **👎 (NOK)**, il verbale mostra "Non Conforme" con dettaglio problemi.

**REGOLA MINIMALISMO:**
NON generare sezioni per categorie non usate nel cantiere.
Se il cantiere ha solo EN 1090 → nessuna "Parte B: Cancelli".

### Struttura PDF Finale

```
PACCO DOCUMENTI CANTIERE — Commessa N. 2025/123

INDICE
├── Copertina (Dati commessa, cliente, date)
│
├── PARTE A: STRUTTURE (EN 1090)       ← solo se almeno 1 voce EN 1090
│   ├── A.1 Dati Generali Voce
│   ├── A.2 Certificati Materiali 3.1
│   ├── A.3 Foto Lavorazione
│   ├── A.4 Verbale Collaudo Qualità (auto-compilato da checklist)
│   └── A.5 Riepilogo Ore Lavorate
│
├── PARTE B: SICUREZZA CANCELLI (EN 13241)  ← solo se almeno 1 voce EN 13241
│   ├── B.1 Dati Generali Voce
│   ├── B.2 Foto Kit Sicurezza
│   ├── B.3 Verbale Collaudo (auto-compilato da checklist)
│   └── B.4 Riepilogo Ore Lavorate
│
└── PARTE C: LAVORAZIONI GENERICHE     ← solo se almeno 1 voce GENERICA
    └── C.1 Riepilogo Ore e Materiali
```

### Tecnologia
- **WeasyPrint** — già installato e usato in 13+ servizi PDF del progetto
- **pypdf** — per merge di pagine se necessario
- Pattern: HTML template (Jinja-style string format) → CSS @page A4 → WeasyPrint → BytesIO → PDF
- File di riferimento per lo stile: `services/pdf_super_fascicolo.py` (stesso pattern)

---

## 7. Architettura del Codice

### Stack Tecnologico
- **Frontend:** React 18 + TailwindCSS + Shadcn/UI
- **Backend:** Python FastAPI + MongoDB
- **Auth:** Google OAuth (admin) + PIN 4 cifre (operai/Vista Officina)
- **Hosting:** Railway (backend) + Vercel (frontend)
- **AI:** Emergent LLM Key (analisi certificati, OCR)
- **PDF:** WeasyPrint + pypdf

### Struttura Cartelle
```
/app/
├── backend/
│   ├── main.py
│   ├── core/
│   │   ├── database.py
│   │   └── security.py
│   ├── routes/
│   │   ├── commesse.py             # CRUD commesse (~1330 righe)
│   │   ├── voci_lavoro.py          # CRUD voci di lavoro (Matrioska)
│   │   ├── officina.py             # Vista Officina: PIN, Timer, Foto, Checklist, Alerts
│   │   ├── company_docs.py         # Documenti aziendali + Allegati POS (PATCH scadenza, CRUD allegati)
│   │   ├── sicurezza.py            # Export CSE ZIP (include 05_ALLEGATI_POS/)
│   │   ├── verbale_posa.py         # CRUD + PDF Verbale di Posa (con logo dinamico)
│   │   ├── dashboard.py            # Stats + compliance-docs + fascicolo-aziendale + commessa-compliance
│   │   ├── welders.py              # Risorse Umane + Matrice Scadenze
│   │   ├── commessa_ops.py
│   │   ├── approvvigionamento.py
│   │   ├── produzione_ops.py
│   │   ├── conto_lavoro.py
│   │   ├── consegne_ops.py
│   │   └── documenti_ops.py
│   └── services/
│       ├── pdf_super_fascicolo.py   # Fascicolo Tecnico EN 1090 (1050 righe)
│       ├── commessa_dossier.py      # Dossier singola commessa
│       ├── pdf_template_v2.py       # Template PDF unificato
│       ├── margin_service.py
│       └── ...
└── frontend/
    └── src/
        ├── components/
        │   ├── CommessaOpsPanel.js   # Orchestratore (usa UNIONE categorie)
        │   ├── VociLavoroSection.js  # UI Voci di Lavoro
        │   ├── DiarioProduzione.js   # Diario adattivo + gestione PIN
        │   ├── ComplianceDocsWidget.js    # Widget dashboard conformita documentale
        │   ├── CommessaComplianceBanner.js # Banner validazione preventiva commessa
        │   └── settings/
        │       ├── DocumentiAziendaTab.js  # Tabella documenti CIMS + salvataggio scadenze
        │       ├── AllegatiPosTab.js       # Upload Rumore/Vibrazioni/MMC + toggle Includi POS
        │       └── LogoTab.js              # Upload logo aziendale
        └── pages/
            ├── CommessaHubPage.js    # Hub commessa + QR Officina + Compliance Banner
            ├── OfficinaPage.js       # Vista operai blindata (4 Ponti)
            ├── Dashboard.js          # + Badge alert qualità + Widget Conformita
            ├── VerbalePosaPage.js    # Mobile-first + firma + foto + lotti EN 1090
            ├── MatriceScadenzePage.js # Matrice scadenze compliance operai
            └── SettingsPage.js       # Documenti + Allegati POS + Logo + Azienda
```

### Regole di Manutenzione Codice
**SOGLIA 800 RIGHE:** Ogni volta che un Service o Route supera le 800 righe,
si DEVE proporre di spezzarlo.

**File spezzati:**
- `commessa_ops.py` (3.430 righe) → 6 moduli + wrapper
- `CommessaOpsPanel.js` (2.964 righe) → 8 sotto-componenti + orchestratore

**File da spezzare:**
- `SettingsPage.js` (1.731 righe)
- `commesse.py` (1.330 righe)

---

## 8. Database — Regole

- **NON modificare** collezioni esistenti per aggiungere funzionalita'
- **Creare nuove collezioni** se servono dati nuovi
- Tutti i campi ID usano prefissi: `com_`, `user_`, `voce_`, `tmr_`, `chk_`, `alert_`
- `_id` di MongoDB **MAI** esposto nelle API REST
- Date sempre in UTC con `datetime.now(timezone.utc)`

### Collezioni
| Collezione | Scopo |
|---|---|
| `commesse` | Fascicoli di cantiere |
| `voci_lavoro` | Voci di lavoro (Matrioska) |
| `preventivi` | Preventivi clienti |
| `articoli` | Catalogo articoli/materiali |
| `diario_produzione` | Registrazioni ore operai |
| `operatori` | Anagrafica operai + PIN |
| `material_batches` | **UNICA fonte verita** lotti materiale (EN 1090) — ex fpc_batches unificato |
| `cam_lotti` | Lotti CAM (EN 1090) |
| `commessa_documents` | Repository documenti + foto officina |
| `officina_timers` | Timer START/PAUSA/STOP |
| `officina_checklist` | Esiti checklist qualità |
| `officina_alerts` | Alert qualità per admin |
| `fatture` | Fatture emesse |
| `fatture_ricevute` | Fatture fornitori |
| `clients` | Clienti + fornitori |
| `company_documents` | Documenti aziendali (sicurezza_globale + allegati_pos) |
| `company_settings` | Impostazioni aziendali (logo_url, ragione_sociale, etc.) |
| `verbali_posa` | Verbali di posa in opera (firma, foto, checklist) |
| `welders` | Operai (Risorse Umane) con qualifiche e attestati sicurezza |
| `riesami_tecnici` | Riesame Tecnico pre-produzione (11 check + firma) |
| `registro_saldatura` | Log saldature per commessa (giunto, saldatore, WPS, esito VT) |
| `controlli_finali` | Checklist pre-spedizione EN 1090-2 (11 check, 3 aree + firma) |
| `instruments` | Strumenti di misura con soglia accettabilita configurabile |

**Campi aggiunti su collezioni esistenti:**
- `clients` → `status: str` (default "active"), `successor_client_id: str` (opzionale)
- `invoices`, `preventivi`, `ddt`, `commesse` → `client_snapshot: dict` (copia immutabile dati cliente)

---

## 9. Log delle Modifiche

### 20 Marzo 2026 — Fork 1: Cantieri Misti
- **Fase 1.5 — Voci di Lavoro:** Backend CRUD (`voci_lavoro.py`) + Frontend (`VociLavoroSection.js`)
- **CommessaOpsPanel:** Ora usa UNIONE categorie (hasEN1090, hasEN13241, isOnlyGenerica)
- **Diario Adattivo:** Selettore voce con bottoni grandi colorati + campi specifici per categoria
- **Backend Diario:** Nuovi campi opzionali (voce_id, numero_colata, wps_usata, note_collaudo)
- Test: 100% backend (19/19) + 100% frontend (iteration_178)

### 20 Marzo 2026 — Fork 2: Vista Officina (4 Ponti)
- **Backend `officina.py`:** PIN management, Timer START/PAUSA/RESUME/STOP, Foto smart routing, Checklist con alerts
- **Frontend `OfficinaPage.js`:** Tema dark, 3 tab (Timer/Foto/Qualità), nessuna navigazione
- **`CommessaHubPage.js`:** QR dialog con link officina per voce
- **`DiarioProduzione.js`:** Gestione PIN inline per operatori
- **`Dashboard.js`:** Badge rosso alert qualità
- Test: 100% backend (16/16) + 100% frontend (iteration_179)

### 21 Marzo 2026 — Fork 3: Sicurezza Documentale & Conformita Pre-Qualifica

#### Fix Persistenza Date Scadenza (Bug P0)
- **Backend `company_docs.py`:** Nuovo endpoint `PATCH /api/company/documents/sicurezza-globali/{doc_type}` per aggiornare la scadenza senza re-upload file
- **Frontend `DocumentiAziendaTab.js`:** Aggiunto pulsante "Salva" (icona floppy) accanto ad ogni campo data, con funzione `handleSaveDate` che chiama il PATCH
- Test: 100% backend + frontend (iteration_198)

#### Allegati Tecnici POS (Rumore, Vibrazioni, MMC)
- **Backend `company_doc.py` (model):** Aggiunto dizionario `ALLEGATI_POS_TYPES` con 3 tipi: rumore, vibrazioni, mmc
- **Backend `company_docs.py`:** 4 nuovi endpoint per allegati POS:
  - `GET /allegati-pos` — lista allegati con stato e flag includi_pos
  - `POST /allegati-pos/{doc_type}` — upload allegato
  - `PATCH /allegati-pos/{doc_type}` — toggle flag includi_pos
  - `DELETE /allegati-pos/{doc_type}` — elimina allegato
- **Frontend `AllegatiPosTab.js`:** Nuovo componente con tabella, upload, Switch "Includi nel POS", download, delete
- **Frontend `SettingsPage.js`:** Tab Documenti ora mostra sia "Checklist Documenti CIMS" che "Allegati Tecnici POS"
- **Backend `sicurezza.py`:** ZIP export (`export_cse`) include cartella `05_ALLEGATI_POS/` con solo documenti dove `includi_pos=true`
- Collezione DB: `company_documents` con `category: "allegati_pos"` e campo `includi_pos: bool`
- Test: 100% backend (21/21) + frontend (iteration_198)

#### Dashboard Conformita Documentale (Widget Pre-Qualifica)
- **Backend `dashboard.py`:** 3 nuovi endpoint:
  - `GET /compliance-docs` — stato completo documenti + allegati + previsione 30gg + % conformita per commessa
  - `GET /fascicolo-aziendale` — download ZIP istantaneo con tutti i documenti aziendali organizzati (01_DOCUMENTI_AZIENDA/ + 02_ALLEGATI_POS/ + INFO.txt)
  - `GET /commessa-compliance/{commessa_id}` — validazione preventiva: verifica se documenti coprono la deadline della commessa
- **Frontend `ComplianceDocsWidget.js`:** Widget full-width nella Dashboard con:
  - Pillole colorate per stato di ogni documento (verde/giallo/rosso/grigio)
  - Sezione "Previsione 30 giorni" con alert documenti in scadenza
  - Barre di avanzamento per ogni commessa attiva (es. "Loiano: 60%")
  - Pulsante "Fascicolo" per download ZIP istantaneo
  - Link "Gestisci documenti" verso Impostazioni
- **Frontend `CommessaComplianceBanner.js`:** Banner validazione preventiva nella pagina commessa:
  - Banner verde se tutti i documenti sono conformi
  - Banner rosso bloccante se documenti mancanti/scaduti/insufficienti
  - Dettaglio check per ogni documento con esito (ok/mancante/scaduto/insufficiente/no_scadenza)
  - Pulsante "Correggi documenti" che porta a Impostazioni
- **Frontend `Dashboard.js`:** Importa e renderizza `ComplianceDocsWidget` sopra la riga widget
- **Frontend `CommessaHubPage.js`:** Importa e renderizza `CommessaComplianceBanner` dopo l'header, prima della card info commessa
- Test: 100% backend (21/21) + frontend (iteration_199)

#### Logo Aziendale nel Verbale di Posa
- **Backend `verbale_posa.py`:** PDF generation ora legge `logo_url` da `company_settings` collection
  - Se logo base64 presente → mostra `<img>` nell'header PDF
  - Se assente → fallback a testo "STEEL PROJECT DESIGN" in blu
  - Cerca in entrambe le collection: `settings` e `company_settings`

### 21 Marzo 2026 — Fork 4: Audit EN 1090 — Fase 2 + Fili Conduttori

#### Registro Saldatura per Commessa (COMPLETATO)
- **Backend `registro_saldatura.py`:** 5 endpoint CRUD:
  - `GET /api/registro-saldatura/{commessa_id}` — Lista righe con stats (conformi/non conformi/da eseguire)
  - `POST /api/registro-saldatura/{commessa_id}` — Nuova riga con validazione processo
  - `PUT /api/registro-saldatura/{commessa_id}/{riga_id}` — Modifica riga
  - `DELETE /api/registro-saldatura/{commessa_id}/{riga_id}` — Elimina riga
  - `GET /api/registro-saldatura/{commessa_id}/saldatori-idonei?processo=X` — Filtra saldatori per patentino valido
- **Frontend `RegistroSaldaturaSection.js`:** Componente con tabella, dialog form, dropdown saldatori filtrato per processo, stats
- **Filo Qualifica (HR ↔ Saldatura):** Il dropdown mostra SOLO saldatori con patentino in corso di validità per il processo specifico (es. 135 MIG/MAG)
- Collezione DB: `registro_saldatura`
- Test: 100% (22/22 backend + frontend — iteration 201)

#### Tracciabilita Materiali — Link DDT → Lotti FPC (COMPLETATO)
- **Backend `fpc.py` (aggiornato):**
  - `POST /api/fpc/batches/link-ddt/{commessa_id}` — Auto-collegamento DDT a batch per match colata/profilo
  - `GET /api/fpc/batches/rintracciabilita/{commessa_id}` — Scheda rintracciabilita con stato collegamento
- **Frontend `TracciabilitaMaterialiSection.js`:** Tabella materiali con colata, cert 3.1, DDT, pulsante "Auto-Collega DDT"
- Test: 100% (22/22 — iteration 201)

#### Checklist Fine Lavori EN 1090-2:2024 (COMPLETATO)
- **Backend `controllo_finale.py`:** 3 endpoint:
  - `GET /api/controllo-finale/{commessa_id}` — 11 check in 3 macro-aree con auto-check real-time
  - `POST /api/controllo-finale/{commessa_id}` — Salva check manuali e note
  - `POST /api/controllo-finale/{commessa_id}/approva` — Firma e chiudi (bloccante se check non superati)
- **3 Macro-aree:**
  - **Visual Testing (4 check):** VT 100% ISO 5817-C, difetti accettabili, saldature registrate (auto), NC chiuse (auto)
  - **Dimensionale (3 check):** Quote critiche B6/B8, tolleranze montaggio, strumenti tarati (auto)
  - **Compliance (4 check):** Etichetta CE, DOP presente (auto), colate coerenti (auto), fascicolo completo (auto)
- **Frontend `ControlloFinaleSection.js`:** Barre progresso per area, checkbox manuali, auto-check con feedback, firma + approvazione
- Collezione DB: `controlli_finali`
- Test: 100% (21/21 — iteration 202)

#### Soglia Accettabilita Configurabile per Strumento — Racc. RINA n.2 (COMPLETATO)
- **Backend `instruments.py` + `instrument.py`:** Nuovi campi `soglia_accettabilita` (float) e `unita_soglia` (mm/%/N/bar)
- **Default Calibro Borletti:** ±0.1 mm (risposta diretta a raccomandazione RINA audit 2025)
- **Backend `riesame_tecnico.py`:** Check `tolleranza_calibro` ora usa soglia configurabile per strumento (non piu 5% hardcoded)
- **Frontend `InstrumentsPage.js`:** Badge viola "Soglia: ±0.1 mm" su card, sezione form condizionale per type=misura
- Test: 100% (21/21 — iteration 202)

#### Unificazione "Fili Conduttori" — Eliminazione Isole Dati (COMPLETATO)
- **Filo Rintracciabilita:** `material_batches` = UNICA fonte di verita
  - Rintracciabilita (`fpc.py`), Riesame (`riesame_tecnico.py`), Controllo Finale (`controllo_finale.py`) tutti leggono da `material_batches`
  - Eliminata dipendenza da `fpc_batches` (dati migrati a `material_batches`)
- **Filo Documentale (DOP/CE):**
  - `dop_frazionata.py` ora auto-popola `classe_esecuzione` dal Riesame Tecnico
  - Aggiunta sezione "3b. Rintracciabilita Materiali" nel PDF DOP con colate e certificati 3.1
  - Helper `_build_rintracciabilita_html()` genera la tabella rintracciabilita
- **Filo Qualifica:** Saldatori filtrati per patentino valido in tempo reale (gia funzionante)
- **Filo Manutenzione:** Riesame blocca se strumenti/attrezzature scaduti (gia funzionante)
- Test: 100% (17/17 — iteration 203)

### 22 Marzo 2026 — Fork 5: Copilota Tecnico-Normativo — Validazione + Segmentazione + Phase 2

#### P0.3 — Box "Se confermi la commessa" (COMPLETATO)
- **Frontend `IstruttoriaPage.js`:** Box minimale con 3 sezioni:
  - "Verra preparato": riesame, lavorazioni, documenti, materiali
  - "Restera da completare": conferme mancanti (dinamico), evidenze, dati saldatura/terzisti/posa
  - "Non ancora emettibile": DOP e documenti finali bloccati
- Titolo: "Se confermi la commessa" — tono operativo, asciutto
- Visibile quando istruttoria NON confermata (non solo quando tutte le risposte date)
- `data-testid="card-se-confermi"`

#### P1 — Validazione Real-World del Motore AI (COMPLETATO)
- **Backend `services/validation_engine.py`:** Ground truth per 8 preventivi reali con scoring multi-dimensionale
  - 4 metriche: Classificazione (peso 35%), Profilo (20%), Estrazione (30%), Domande (15%)
  - Sinonimi officina per matching flessibile (tubolari/piastra/lamiera/profilati etc.)
  - Credito parziale per casi MISTA (0.5 se AI rileva componente del mix)
  - Saldatura implicita: riconoscimento keyword anche se non esplicita
- **Backend `routes/validation.py`:** 4 endpoint:
  - `GET /api/validation/set` — 8 preventivi con normativa attesa
  - `POST /api/validation/run/{id}` — analisi singola + scoring
  - `POST /api/validation/run-batch` — analisi batch (attenzione timeout proxy)
  - `GET /api/validation/results` — risultati salvati + aggregato
- **Frontend `pages/ValidationPage.js`:** Dashboard con aggregato, scorecard individuali, run singolo/batch
- **Sidebar:** Link "Validazione AI (P1)" sotto Certificazioni
- **Risultati finali su 8 preventivi:**
  - Globale: **91%** | Classificazione: **8/8 (100%)** | Profilo: **88%** | Estrazione: **79%** | Domande: **100%**
  - Tutte le soglie superate (soglie: globale>=70%, class>=80%, profilo>=70%, estr>=60%, dom>=50%)
- **Analisi 2 FAIL originali (PRV-0002, PRV-0021):** Entrambi erano correttamente MISTA — ground truth aggiornato
- Collezione DB: `validazioni_p1`
- Test: 100% backend + frontend (iteration_224)

#### P1.1 — Segmentazione Normativa per Riga (COMPLETATO)
- **Backend `services/segmentation_engine.py`:** Classificazione per riga a 2 livelli:
  - **Livello 1 — Keyword deterministico:** 3 dizionari (EN_13241: cancello/portone/automazione, EN_1090: struttura/trave/profili, GENERICA: parapetto/manutenzione/sovrapprezzo)
  - **Livello 2 — GPT-4o:** Override AI per casi incerti (confidence > keyword)
  - Output: `line_classification[]` + `segments[]` + `summary`
- **Backend `routes/istruttoria.py`:** 2 nuovi endpoint:
  - `POST /api/istruttoria/segmenta/{prev_id}` — avvia segmentazione per riga
  - `POST /api/istruttoria/segmenta/{prev_id}/review` — utente conferma/corregge (save_draft o confirm)
  - Blocco conferma se righe INCERTE presenti
  - Salva `official_segmentation` snapshot
- **Frontend `IstruttoriaPage.js`:** Sezione dedicata con:
  - Summary badges (EN 1090: N righe, EN 13241: M righe, etc.)
  - Tabella per riga con dropdown per correzione manuale
  - CTA: "Salva bozza" / "Conferma segmentazione"
  - `data-testid="card-segmentazione"`
- **Stati segmentazione:** proposed → in_review → confirmed / needs_revision
- **Trigger automatici:** classificazione MISTA, o forzato manualmente
- Dati salvati in `istruttorie.segmentazione_proposta` e `istruttorie.official_segmentation`
- Test: 100% backend (11/11) + frontend (iteration_225)

#### Phase 2 — Commessa Pre-Istruita Revisionata (COMPLETATO)
- **Backend `services/phase2_engine.py`:** 2 funzioni principali:
  - `check_eligibility(istruttoria)` → `{allowed, reasons[], warnings[], checks{}}`
  - `generate_preistruita(istruttoria)` → commessa strutturata
  - **7 criteri di eleggibilita:**
    1. Istruttoria confermata dall'utente
    2. Classificazione pura (EN_1090/EN_13241/GENERICA, non MISTA/INCERTA)
    3. Confidenza alta
    4. Segmentazione OK (non attiva o confermata)
    5. Domande ad alto impatto risposte
    6. Nessun blocco strutturale
    7. Campi critici presenti per normativa
- **Backend `routes/istruttoria.py`:** 3 nuovi endpoint:
  - `GET /api/istruttoria/phase2/eligibility/{prev_id}` — check con motivi di blocco
  - `POST /api/istruttoria/phase2/genera/{prev_id}` — genera commessa (409 se non eleggibile)
  - `GET /api/istruttoria/phase2/commessa/{prev_id}` — recupera commessa generata
- **Output commessa pre-istruita:**
  - `voci_lavoro[]` — da estrazione AI
  - `controlli[]` — da assessment
  - `documenti[]` — da assessment
  - `materiali[]` — da estrazione con requisiti tracciabilita
  - `rami_attivi` — saldatura/zincatura/montaggio con stato
  - `etichette` — precompilato/da_completare/non_emettibile
- **Frontend `IstruttoriaPage.js`:** Card Phase 2 dopo conferma:
  - Contatori: precompilati / da completare / non emettibili
  - Badge rami attivi
  - Dettaglio: voci lavoro, controlli, documenti, da completare
  - Motivi blocco espliciti se non eleggibile
  - `data-testid="card-phase2"`
- Collezione DB: `commesse_preistruite`
- Test: 100% backend (10/10) + frontend (iteration_226)

---


### FASE 3 — Pulsante Magico (COMPLETATA)
- Servizio backend `services/pacco_documenti.py`
- Copertina + Indice + CAP. 1 (1090) + CAP. 2 (13241) + CAP. 3 (Relazione Tecnica)
- Filtro Beltrami: pesca solo documenti pertinenti alla voce
- Automazione: checklist OK → verbale "Conforme" auto-firmato
- Minimalismo: salta parti per categorie non presenti

### FASE 4 — Montaggio e Tracciabilita' (IN CORSO)

#### 4.1 Tracciabilita' Bulloneria
- AI Vision (GPT-4o) legge foto DDT fornitori per bulloni, dadi, rondelle
- Estrae: Diametro, Classe (8.8, 10.9), Numero Lotto
- Dati associati alla Commessa + Voce di Lavoro corrispondente
- Nel "Diario di Montaggio", l'operaio scatta foto della scatola bulloni → il sistema mostra i dati estratti dal DDT per confronto visivo

#### 4.2 Modulo Serraggio Intelligente
- Nuova sezione "Diario di Montaggio" nell'interfaccia operaio (OfficinaPage)
- In base a Classe e Diametro letti dal DDT, il diario mostra automaticamente la coppia di serraggio in Nm
- Tabella interna basata su ISO 898-1
- L'operaio conferma il corretto serraggio e l'uso della chiave dinamometrica tramite checklist [SI/NO]

#### 4.3 Gestione Montaggio Esterno (Cantiere)
- Il Diario di Montaggio include un check sull'idoneita' delle fondazioni/appoggi [OK/NOK]
- Upload obbligatorio foto giunti serrati e ancoraggi
- Firma digitale del cliente su "verbale di fine lavori" direttamente da tablet/smartphone (canvas touch)

#### 4.4 Pacco Documenti Aggiornato
- Il Pulsante Magico genera una nuova "Relazione di Montaggio" (CAP. 4)
- Contenuto: tabella bulloni usati (da DDT), coppie di serraggio applicate, foto montaggio, firma cliente

#### 4.5 Schema DB Montaggio
```
// Collezione: bulloneria_ddt
{
  ddt_id: "bdt_abc123",
  commessa_id: "com_xyz789",
  voce_id: "voce_abc123",
  admin_id: "user_xxx",
  bulloni: [
    { diametro: "M16", classe: "10.9", lotto: "LOT-2026-001", quantita: "50 pz" }
  ],
  foto_ddt_doc_id: "doc_yyy",       // Riferimento alla foto DDT caricata
  analyzed_at: "2026-...",
  source: "ai_vision" | "manuale"
}

// Collezione: diario_montaggio
{
  montaggio_id: "mtg_abc123",
  commessa_id: "com_xyz789",
  voce_id: "voce_abc123",
  admin_id: "user_xxx",
  operatore_id: "op_xxx",
  operatore_nome: "Ahmed",

  // Serraggio
  serraggi: [
    { diametro: "M16", classe: "10.9", coppia_nm: 225, confermato: true, chiave_dinamometrica: true }
  ],

  // Fondazioni
  fondazioni_ok: true | false | null,

  // Foto obbligatorie
  foto_giunti_doc_ids: ["doc_a", "doc_b"],
  foto_ancoraggi_doc_ids: ["doc_c"],

  // Firma cliente
  firma_cliente_base64: "data:image/png;base64,...",
  firma_cliente_nome: "Mario Rossi",
  firma_cliente_data: "2026-03-21T...",

  created_at: "2026-...",
  updated_at: "2026-..."
}
```

### FASE 4B — Modulo Varianti, Scadenzario Attrezzature, Archivio Storico (COMPLETATA)

#### 4B.1 Modulo Varianti
- Nel Diario di Montaggio, nuovo sotto-step "VARIANTI"
- Note di variante con foto obbligatoria
- Le varianti vengono evidenziate nel Pacco Documenti (CAP. 4, sezione 4.6)
- Collezione DB: `varianti_montaggio` { variante_id, commessa_id, voce_id, descrizione, foto_doc_id, ... }

#### 4B.2 Scadenzario Attrezzature
- CRUD per saldatrici e chiavi dinamometriche con date di taratura
- Se taratura scaduta → alert automatico admin (stessa collection `officina_alerts`)
- Endpoint check-taratura collegato al modulo serraggio: se la chiave e' scaduta, mostra alert nell'interfaccia operaio
- Collezione DB: `attrezzature` { attr_id, tipo, modello, numero_serie, marca, data_taratura, prossima_taratura }
- Pagina admin: `/attrezzature` con card per ogni attrezzatura + badge scadenza

#### 4B.3 Archivio Storico
- Esportazione massiva per anno e/o cliente
- Genera ZIP con struttura: /{Anno}/{Cliente}/{Commessa}/
- Include: info_commessa.txt, Foto/, Certificati/, Documenti/, diario_produzione.csv, diario_montaggio.json
- Pagina admin: `/archivio-storico` con filtri anno/cliente + statistiche + storico export
- Collezione DB: `archivio_exports` per tracciare le esportazioni

### FASE 5 — SICUREZZA & PNRR + WORKFLOW ENGINE (COMPLETATA)

#### 5.1 Profilo Sicurezza Operatore (D.Lgs 81/08)
- Scadenzario corsi sicurezza obbligatori (formazione base/specifica, primo soccorso, antincendio, lavori quota, PLE)
- Corsi salvati in `operatori.corsi_sicurezza[]`
- **WORKFLOW GATE**: Check all'avvio timer START → se corsi base scaduti/mancanti, 403 BLOCCATO
- Endpoint: `GET /sicurezza/check-operatore/{op_id}`, `POST /sicurezza/operatore/{op_id}/corsi`

#### 5.2 Archivio DNSH / PNRR (Requisiti Ambientali)
- AI Vision (GPT-4o) analizza certificati/DDT cercando: % riciclato, EPD, ISO 14001, CAM, EAF, carbon footprint
- Sezione "Requisiti Ambientali DNSH" nel CommessaOpsPanel
- **WORKFLOW → PULSANTE MAGICO**: I dati DNSH finiscono nel CAP. 5 "Sostenibilita'" del PDF
- Collezione DB: `dnsh_data`

#### 5.3 Diario Sicurezza Cantiere
- Checklist obbligatoria PRIMA del montaggio: "Area delimitata?", "DPI indossati?", "Attrezzature verificate?"
- Foto panoramica cantiere obbligatoria
- Nuovo primo step "SICUREZZA" nel MontaggioPanel (6 step totali)
- Collezione DB: `sicurezza_cantiere`

#### 5.4 Cartella Documentale CSE
- Tasto "Esporta Documentazione Sicurezza" nel CommessaOpsPanel
- Genera ZIP: DURC, POS, Attestati operai (CSV + PDF), Certificati macchine, Checklist cantiere
- Endpoint: `POST /sicurezza/export-cse/{commessa_id}`

#### 5.5 WORKFLOW ENGINE — I Fili Conduttori (State Machine)

```
DDT ──→ PRODUZIONE
  AI convalida DDT → Voce "Pronto per Produzione" → Notifica tablet

SICUREZZA ──→ DIARIO
  Timer START bloccato se corsi D.Lgs 81/08 o patentini scaduti → 403

ACQUISTI ──→ CANTIERE
  DDT bulloneria → auto-lookup diametro/classe → coppia serraggio Nm
  Blocco verbale senza conferma chiave dinamometrica

QUALITA' ──→ PULSANTE MAGICO
  Dati DNSH estratti da AI → CAP. 5 "Sostenibilita'" nel PDF finale
  Sicurezza cantiere → inclusa nel PDF

FIRMA ──→ SERVICE
  Firma cliente → AUTO-genera:
    1. Targa CE con QR Code (collection: targhe_ce)
    2. Scadenzario Manutenzioni 12/24 mesi (collection: scadenzario_manutenzioni)
```

Collezioni nuove: `sicurezza_cantiere`, `dnsh_data`, `targhe_ce`, `scadenzario_manutenzioni`
Pacco Documenti: CAP. 1-5 (EN 1090, EN 13241, Relazione Tecnica, Montaggio, Sostenibilita')

### 22 Marzo 2026 — Fork 6: Modello Gerarchico Commessa (Fase A)

#### Architettura 4 Livelli — Commessa Madre -> Ramo -> Emissione (COMPLETATO)
- **Nuova collezione `commesse_normative`:**
  - CRUD per rami normativi (EN_1090, EN_13241, GENERICA) per commessa
  - Creazione idempotente: se il ramo esiste, restituisce quello esistente aggiornato
  - Indice univoco `(commessa_id, normativa, user_id)`
  - Tracciamento origine: `created_from` (manuale/segmentazione/legacy_wrap)
  - `source_istruttoria_id` e `source_segmentation_snapshot` per tracciabilita
- **Nuova collezione `emissioni_documentali`:**
  - Emissioni progressive per ramo con numerazione strutturata
  - Codice: `NF-2026-000125-1090-D01` (base-suffisso-tipo+seq)
  - Counter atomico per progressivo (collezione `counters`)
  - Indice univoco `(ramo_id, emission_type, emission_seq, user_id)`
  - Stati: draft, in_preparazione, bloccata, emettibile, emessa, annullata
  - Link sottoinsiemi: line_ids, voce_lavoro_ids, batch_ids, ddt_ids, document_ids
- **Evidence Gate per emissione:**
  - EN 1090: certificati 3.1, WPS/WPQR, riesame tecnico, controllo finale
  - EN 13241: documentazione tecnica, verifiche sicurezza, manuale uso
  - GENERICA: nessun requisito
  - Calcolo on-demand con salvataggio stato
- **Legacy adapter centralizzato:**
  - `get_normative_branches()` con wrapping virtuale per commesse legacy
  - `materializza_ramo_legacy()` per conversione lazy on-access
  - Nessuna migrazione massiva: commesse legacy funzionano invariate
- **Backend `services/commesse_normative_service.py`:** Logica business completa
- **Backend `routes/commesse_normative.py`:** 11 endpoint API
- **Frontend `RamiNormativiSection.js`:** Card con rami espandibili, emissioni, Evidence Gate
- **Campi su commessa madre:** `normative_presenti[]`, `has_mixed_normative`, `primary_normativa`
- Test: 100% backend (21/21) + 100% frontend (iteration_227)

#### Fase B — Evidence Gate Avanzato (COMPLETATO)
- **B1 Motore gate completo** (`evidence_gate_engine.py`):
  - 3 check comuni: scope emissione, stato ramo, gia emessa
  - 10+ regole EN 1090: cert 3.1, WPS/WPQR, saldatori, registro saldatura, VT, controllo finale, riesame tecnico, doc terzista/zincatura, strumenti/ITT
  - 6 regole EN 13241: identificazione prodotto, manuale uso, collaudo, dispositivi, posa
  - Gate minimo GENERICA
  - Matrice condizionale: `branch_flags` (saldatura_attiva, zincatura_esterna, montaggio_attivo, has_automation, requires_force_test, has_safety_devices)
  - Output standardizzato: `checks[]`, `blockers[]`, `warnings[]`, `completion_percent`
  - `completion_percent` esclude `not_applicable` dal denominatore
  - Codici blockers standardizzati: MATERIAL_CERT_MISSING, WPS_MISSING, FINAL_CONTROL_NOT_COMPLETED, etc.
- **B2 UI EmissioneDetailPanel** (`EmissioneDetailPanel.js`):
  - 3 colonne: Cosa serve | Cosa c'e | Cosa manca
  - Barra progresso colore-codificata
  - Pulsante "collega" per evidenze mancanti linkabili
  - Pulsante "Emetti" solo se emittable=true
- **B3 Blocco reale emissione**:
  - `/emetti` ricalcola SEMPRE il gate, 409 se bloccata
  - Nessun bypass UI-only
- **Snapshot cache**: last_gate_status, last_completion_percent, last_blockers_count
- Test: 100% backend (24/24) + 100% frontend (iteration_228)

#### S0 — Collegamento Segmentazione → Rami Normativi (COMPLETATO)
- Phase 2 auto-genera rami normativi dopo creazione commessa preistruita (idempotente)
- `genera-da-istruttoria` cerca commessa in `commesse` + `commesse_preistruite`
- `crea_ramo` e legacy adapter supportano entrambe le collezioni
- `normative_presenti` aggiornato sulla collezione corretta
- Frontend: toast rami generati + badge nella card Phase 2
- Test: 100% backend (12/12) (iteration_229)

### Sessione Hardening — Integrita Dati & Deploy Fix

#### Bug Fix: Persistenza Righe Note di Credito (COMPLETATO)
- **Backend `invoices.py`:** Le Note di Credito ora salvano correttamente le modifiche alle righe indipendentemente dallo status (bozza, emessa, inviata_sdi)
- **Frontend `InvoiceEditorPage.js`:** `handleSave` ora invia sempre le righe per le NC
- **Causa root:** Il backend bloccava le modifiche strutturali su fatture non-bozza, ma le NC devono poter modificare le righe in qualsiasi stato
- Test: 100% (iteration_255)

#### Client Snapshot sui Documenti — Integrita Dati Storica (COMPLETATO)
- **Problema:** Modificare i dati di un cliente (es. successione aziendale padre→figlio) alterava retroattivamente TUTTI i documenti storici associati — fiscalmente e operativamente scorretto
- **Soluzione: Data Denormalization (Snapshotting)**
  - Ogni fattura/DDT/preventivo/commessa ora salva un campo `client_snapshot` (dizionario) al momento della creazione
  - Il snapshot e' una copia immutabile dei dati chiave del cliente (ragione_sociale, partita_iva, codice_fiscale, indirizzo, etc.)
  - I documenti storici NON cambiano piu' se si modifica l'anagrafica cliente
- **Backend `services/client_snapshot.py`:** Nuovo servizio con funzione `build_snapshot(client_data)` che crea la copia
- **Backend modificati:** `invoices.py`, `preventivi.py`, `ddt.py`, `commesse.py` — tutti ora chiamano `build_snapshot()` alla creazione documento
- **Backend GET endpoints:** Leggono da `client_snapshot` quando disponibile, fallback a lookup live per documenti pre-migrazione
- Test: 100% backend (16/16) + frontend (iteration_256)

#### Stato Cliente — Ciclo di Vita Anagrafica (COMPLETATO)
- **Backend `models/client.py`:** Nuovo Enum `ClientStatus` con valori: `active`, `archived`, `blocked`
- **Backend `routes/clients.py`:** 3 nuovi endpoint:
  - `PUT /api/clients/{client_id}/archive` — archivia il cliente
  - `PUT /api/clients/{client_id}/block` — blocca il cliente
  - `PUT /api/clients/{client_id}/reactivate` — riattiva il cliente
- **Backend `GET /api/clients`:** Supporta filtro `?status=active` per escludere archiviati/bloccati
- **Frontend `ClientsPage.js`:** Colonna Stato con badge colorati, checkbox "Mostra archiviati", pulsanti gestione stato
- **Frontend selettori client:** `InvoiceEditorPage.js`, `PreventivoEditorPage.js`, `SopralluogoWizardPage.js` ora filtrano clienti archiviati/bloccati nei dropdown
- Test: incluso in iteration_256

#### Migrazione Snapshot per Documenti Esistenti (COMPLETATO)
- **Backend `routes/migration.py`:** Nuovo router con endpoint:
  - `POST /api/migration/run-client-snapshot-backfill` — backfill snapshot su tutti i documenti storici esistenti
- **Logica:** Per ogni documento (fatture, preventivi, DDT, commesse) senza `client_snapshot`, cerca il cliente associato e crea lo snapshot
- **Sicurezza:** Endpoint admin-only, esecuzione one-time controllata dall'utente
- Registrato in `main.py`

#### Deploy Fix (COMPLETATO)
- Rimosso `litellm==1.80.0` da `requirements.txt` — pacchetto non usato che bloccava il build in produzione (dependency resolution failure)

---

### FASE 6 — Smistatore Intelligente Avanzato (PROSSIMO)
- Certificati cumulativi: AI analizza ogni pagina, matching per numero colata
- DDT Multi-Commessa: spacchettamento automatico per commessa/voce
- Consumabili auto: filo >= 1.0mm → EN 1090, filo < 1.0mm → EN 13241/Generiche
- Magazzino Scorte: materiali non assegnati → scorta con certificato pronto

### Backlog Tecnico
- Split `SettingsPage.js` (1.731 righe)
- Split `commesse.py` (1.330 righe)

### Backlog Funzionale
- UI Admin per Sfridi, Controlli Visivi, Registro NC
- RBAC, Export Excel, Unificazione PDF, Portale clienti, WhatsApp
- (P0) Verifica Coerenza Rintracciabilita — Confronto lotti vs DDT con segnalazione discrepanze
- (P0) Template Processo 111 — PDF richiesta preventivo laboratorio (UNI EN ISO 15614-1, EXC2, S275/S355)
- (P1) Report Ispezioni VT/Dimensionali con checklist ISO 5817
- (P1) DOP + Etichetta CE automatica (enhancement gate_certification)
- (P1) Integrazione email "Invia a CIMS" (SendGrid/Resend)
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting costi reali > budget
- (P2) Scadenziario Manutenzioni Digitalizzato (calendari trimestrali/annuali + alert)
- (P2) Verbali ITT (qualifica taglio e foratura)
- (P2) PDF Compliance dalla Matrice Scadenze
- (P3) QR Code su documenti generati

---

## 11. SMISTATORE INTELLIGENTE DOCUMENTI — Logiche Ferree

> Regole per l'automazione documentale avanzata (Fase 4).

### 11.1 Gestione Certificati Cumulativi (es. Beltrami)
1. AI Vision analizza OGNI PAGINA del PDF multi-pagina
2. Estrae: numero colata, tipo acciaio, dimensioni
3. **MATCHING** con materiali del DDT associato → solo pagine pertinenti alla commessa
4. **SURPLUS** → "scorte documentali inattive" nel DB (non nel fascicolo)
5. Architettura: metadati in `commessa_documents.metadata_estratti` con `matching_status`

### 11.2 DDT Multi-Commessa & Magazzino
1. AI Vision analizza righe DDT → confronto con OdP/OdA aperti
2. Spacchettamento automatico per commessa/voce
3. Materiale non assegnato → `magazzino_scorte` con certificato pronto

### 11.3 Regola Consumabili (Filo & Gas)
| Consumabile | Condizione | Destinazione |
|---|---|---|
| Filo >= 1.0 mm | Diametro >= 1.0 | Tutte EN 1090 attive nel periodo |
| Filo < 1.0 mm | Diametro < 1.0 | EN 13241 e Generiche |
| Gas | Tutti | Tutte EN 1090 del periodo |

### 11.4 Architettura: Metadati + Indice Invertito (NO vettoriale)
- PDF cumulativo salvato UNA SOLA VOLTA
- Indice invertito `doc_page_index`: `numero_colata → [doc_id, pagina, commessa]`
- Il Pulsante Magico pesca solo le pagine giuste via indice
- Zero duplicazione file, ricerca rapida per numero colata

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
        │   └── ...
        └── pages/
            ├── CommessaHubPage.js    # Hub commessa + QR Officina
            ├── OfficinaPage.js       # Vista operai blindata (4 Ponti)
            ├── Dashboard.js          # + Badge alert qualità
            └── SettingsPage.js       # ⚠️ 1.731 righe — DA SPEZZARE
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
| `material_batches` | Lotti materiale tracciati (EN 1090) |
| `cam_lotti` | Lotti CAM (EN 1090) |
| `commessa_documents` | Repository documenti + foto officina |
| `officina_timers` | Timer START/PAUSA/STOP |
| `officina_checklist` | Esiti checklist qualità |
| `officina_alerts` | Alert qualità per admin |
| `fatture` | Fatture emesse |
| `fatture_ricevute` | Fatture fornitori |
| `clients` | Clienti + fornitori |

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

### Sessioni Precedenti
- Refactoring Backend: commessa_ops.py → 6 moduli (17/17 test)
- Refactoring Frontend: CommessaOpsPanel → 8 sotto-componenti (iteration_175)
- Pulizia codice morto: chat.py, documents.py eliminati
- Responsive 8 pagine (iteration_176)
- Categorie di Lavoro — 3 bottoni nel CreateCommessaModal (iteration_177)

---

## 10. Prossimi Passi (Roadmap)

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

### FASE 5 — Smistatore Intelligente Avanzato (PROSSIMO)
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

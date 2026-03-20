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
- Gli **operai in officina** — registrano ore e avanzamento dal cellulare (bottoni grandi, zero burocrazia)

---

## 2. Le 3 Categorie di Lavoro

Ogni commessa appartiene a UNA di queste categorie. La scelta avviene alla creazione e determina cosa il software mostra e cosa nasconde.

### A. STRUTTURALE (EN 1090)
**Campo DB:** `normativa_tipo: "EN_1090"`
**Quando si usa:** Scale, balconi, soppalchi, capannoni, strutture portanti
**Cosa richiede:**
- Tracciabilità lotti ferro con certificati 3.1 (numero colata, acciaieria)
- Patentini saldatori (EN ISO 9606)
- WPS/WPQR (procedure di saldatura qualificate)
- Piano di Controllo Qualità
- Generazione DoP (Dichiarazione di Prestazione)
- Etichetta CE
- CAM — Criteri Ambientali Minimi (DM 256/2022) per appalti pubblici
**Sezioni operative visibili:** TUTTE (8 sezioni)

### B. CANCELLO (EN 13241)
**Campo DB:** `normativa_tipo: "EN_13241"`
**Quando si usa:** Cancelli scorrevoli/battenti, portoni industriali, porte pedonali, barriere
**Cosa richiede:**
- Kit sicurezza (fotocellule, coste sensibili, lampeggiante)
- Foto delle installazioni di sicurezza
- Verbale collaudo forze (EN 12453)
- Manuale d'Uso e Manutenzione
- Certificazione cancello con test specifici
**Sezioni operative visibili:** 6 (include Certificazione Cancello, esclude Tracciabilità/CAM/Fascicolo Tecnico EN 1090)

### C. GENERICA (Nessuna Marcatura CE)
**Campo DB:** `normativa_tipo: "GENERICA"`
**Quando si usa:** Riparazioni, manutenzioni, piccoli lavori, lavori su misura senza obbligo CE
**Cosa richiede:**
- Solo registrazione ore lavorate
- Solo registrazione materiali utilizzati
- Riepilogo costi per controllo margine
- NESSUN obbligo burocratico o documentale
**Sezioni operative visibili:** Solo 3 (Produzione, Conto Lavoro, Repository Documenti)

### REGOLA CANTIERI MISTI

> Una singola commessa PUO' contenere più **Voci di Lavoro** con normative diverse.

**Esempio reale:** Il cliente Bianchi ordina per lo stesso cantiere:
- Voce 1: "Soppalco capannone" → EN 1090 (EXC2)
- Voce 2: "Cancello carraio" → EN 13241
- Voce 3: "Riparazione ringhiera" → GENERICA

**Come funziona nel software:**

1. **Alla creazione** della commessa si sceglie la categoria principale (come oggi)
2. **Dopo la creazione**, nella scheda della commessa si possono aggiungere "Voci di Lavoro" extra con categorie diverse
3. **Il pannello operativo** mostra le sezioni di TUTTE le categorie presenti nelle voci (unione)
4. **Il Diario di Produzione** chiede all'operaio "Su quale voce stai lavorando?" e filtra le domande:
   - Se lavora sulla voce EN 1090 → chiede certificati, colata, WPS
   - Se lavora sulla voce EN 13241 → chiede foto fotocellule, note collaudo
   - Se lavora sulla voce GENERICA → chiede solo ore e materiali
5. **Il "Pulsante Magico"** genera un **Fascicolo di Cantiere unico** che raggruppa:
   - Fascicolo Tecnico per le voci EN 1090
   - Libretto Manutenzione per le voci EN 13241
   - Riepilogo Costi per le voci GENERICHE

**Schema DB delle Voci di Lavoro:**
```
// Nuova collezione: voci_lavoro
{
  voce_id: "voce_abc123",
  commessa_id: "com_xyz789",
  descrizione: "Soppalco capannone",
  normativa_tipo: "EN_1090",        // categoria specifica della voce
  classe_exc: "EXC2",               // solo per EN_1090
  tipologia_chiusura: "",            // solo per EN_13241
  ordine: 1,                         // ordine di visualizzazione
  created_at: "2026-03-20T...",
}
```

**Regola di retrocompatibilità:** Le commesse esistenti (senza voci) continuano a funzionare come prima — il campo `normativa_tipo` della commessa vale come "voce unica implicita".

---

## 3. Architettura del Codice

### Stack Tecnologico
- **Frontend:** React 18 + TailwindCSS + Shadcn/UI
- **Backend:** Python FastAPI + MongoDB
- **Auth:** Google OAuth via Emergent Platform
- **Hosting:** Railway (backend) + Vercel (frontend)
- **AI:** Emergent LLM Key (analisi certificati, OCR)

### Struttura Cartelle
```
/app/
├── backend/
│   ├── main.py                     # Entry point FastAPI
│   ├── core/
│   │   ├── database.py             # MongoDB connection
│   │   └── security.py             # Auth, session, cookies
│   ├── routes/
│   │   ├── commesse.py             # CRUD commesse (~1330 righe)
│   │   ├── commessa_ops.py         # Wrapper sottile per ops
│   │   ├── commessa_ops_common.py  # Helper condivisi
│   │   ├── approvvigionamento.py   # RdP, OdA, Arrivi
│   │   ├── produzione_ops.py       # Fasi produzione
│   │   ├── conto_lavoro.py         # Verniciatura, zincatura
│   │   ├── consegne_ops.py         # DDT, consegne
│   │   └── documenti_ops.py        # Repository documenti
│   └── services/
│       ├── margin_service.py       # Calcolo margini
│       └── ...
└── frontend/
    └── src/
        ├── components/
        │   ├── CommessaOpsPanel.js         # Orchestratore (161 righe)
        │   ├── ApprovvigionamentoSection.js # RdP, OdA, Arrivi (568 righe)
        │   ├── ProduzioneSection.js         # Fasi + Diario (120 righe)
        │   ├── ConsegneSection.js           # DDT + DoP (149 righe)
        │   ├── ContoLavoroSection.js        # Vern/Zinc/Sabb (358 righe)
        │   ├── TracciabilitaSection.js      # Lotti EN 1090 (113 righe)
        │   ├── CAMSection.js                # Criteri Ambientali (243 righe)
        │   ├── RepositoryDocumentiSection.js # Upload + AI (369 righe)
        │   └── DiarioProduzione.js          # Diario ore operai
        └── pages/
            ├── CommessaHubPage.js   # Hub singola commessa
            ├── PlanningPage.js      # Planning + CreateCommessaModal
            ├── SettingsPage.js      # ⚠️ 1.731 righe — DA SPEZZARE
            └── ...
```

### Regola sui "File Monster"
Il progetto aveva file enormi che rendevano impossibile manutenere il codice:
- `commessa_ops.py` (3.430 righe) → **SPEZZATO** in 6 moduli + wrapper
- `CommessaOpsPanel.js` (2.964 righe) → **SPEZZATO** in 8 sotto-componenti + orchestratore
- `SettingsPage.js` (1.731 righe) → **DA FARE** — prossimo candidato allo split

**Regola:** Nessun file deve superare le 500 righe. Se cresce troppo, si spezza chirurgicamente in moduli autonomi con interfacce pulite (props/callback per il frontend, router separati per il backend).

---

## 4. UX Officina — Regole di Design

### Bottoni Grandi e Chiari
Il titolare e gli operai usano l'app con le **mani sporche di ferro** e spesso **di fretta**. Le regole sono:
- Bottoni grandi (min h-11, testo leggibile)
- Colori distintivi per ogni azione (blu = strutturale, ambra = cancello, grigio = generico)
- Icone sempre presenti accanto al testo
- Touch target minimo 44x44px per mobile

### Accesso Separato per Operai
Gli operai NON devono vedere:
- Dati contabili (preventivi, fatture, margini, prezzi)
- Impostazioni aziendali
- Anagrafica clienti/fornitori

Gli operai DEVONO vedere solo:
- Diario di Produzione (registrazione ore)
- Fasi di lavorazione (avanzamento)
- Foto del lavoro in corso

> **Vista Officina** (da implementare): un'interfaccia semplificata mobile-first per gli operai, accessibile con PIN o QR code, che mostra solo le commesse attive e il diario di produzione.

### Responsive Mobile
Tutte le pagine devono funzionare su mobile (375px). Pattern usati:
- `flex-col sm:flex-row` per header con bottoni
- `hidden md:table-cell` per colonne secondarie nelle tabelle
- `overflow-x-auto` wrapper attorno alle tabelle
- `w-full sm:w-auto` per bottoni che diventano full-width su mobile
- `grid-cols-1 sm:grid-cols-N` per form nei dialog

---

## 5. Database — Regole

- **NON modificare** tabelle/collezioni esistenti per aggiungere funzionalità
- **Creare nuove collezioni** se servono dati nuovi (es. `kit_sicurezza_13241`)
- Tutti i campi ID usano prefissi: `com_` (commesse), `user_` (utenti), `rdp_` (richieste preventivo)
- `_id` di MongoDB **MAI** esposto nelle API REST — sempre escluso nelle proiezioni
- Date sempre in UTC con `datetime.now(timezone.utc)`

### Collezioni Principali
| Collezione | Scopo | Note |
|---|---|---|
| `commesse` | Commesse di lavoro | Campo chiave: `normativa_tipo` |
| `preventivi` | Preventivi clienti | Possono generare commesse |
| `articoli` | Catalogo articoli/materiali | Con giacenza magazzino |
| `diario_produzione` | Registrazioni ore operai | Per commessa |
| `material_batches` | Lotti materiale tracciati | Solo EN 1090 |
| `cam_lotti` | Lotti CAM per DM 256/2022 | Solo EN 1090 |
| `fatture` | Fatture emesse | Collegabili a commesse |
| `fatture_ricevute` | Fatture fornitori | Per calcolo costi |
| `clients` | Clienti + fornitori | Campo `client_type` distingue |

---

## 6. Log delle Modifiche

### 20 Marzo 2026 — Sessione di Stabilizzazione

**Refactoring Backend (completato nelle sessioni precedenti)**
- `commessa_ops.py` (3.430 righe) → 6 moduli separati + wrapper sottile
- Verificato con 17/17 test passati

**Refactoring Frontend CommessaOpsPanel**
- `CommessaOpsPanel.js` da 2.964 → 161 righe (orchestratore)
- Creati 3 nuovi componenti: `ApprovvigionamentoSection.js`, `TracciabilitaSection.js`, `CAMSection.js`
- Si aggiungono ai 4 esistenti: `ProduzioneSection`, `ConsegneSection`, `ContoLavoroSection`, `RepositoryDocumentiSection`
- Test: 100% backend + frontend (iteration_175)

**Pulizia Codice Morto**
- Eliminati `chat.py`, `documents.py` (route placeholder) + relativi model
- Rimossi import da `__init__.py` di routes e models

**Responsive Fase 2**
- Rese responsive 8 pagine: PreventiviPage, ClientsPage, FornitoriPage, ArticoliPage, InvoicesPage, ScadenziarioPage, MarginAnalysisPage, CostControlPage
- Test: 100% desktop + mobile (iteration_176)

**FASE 1 — Categorie di Lavoro (completata)**
- 3 bottoni grandi nel `CreateCommessaModal` (PlanningPage.js)
- Campi condizionali: Classe EXC per EN 1090, Tipologia per EN 13241, solo info per Generica
- `CommessaOpsPanel` nasconde sezioni non pertinenti alla categoria scelta
- `NORMATIVA_CONFIG` aggiornato con la voce GENERICA nel `CommessaHubPage`
- Test: 100% backend (13/13) + frontend (iteration_177)

---

## 7. Prossimi Passi (Roadmap)

### In Coda — Flusso Categorie
- **FASE 1.5 (NUOVA):** Voci di Lavoro per Cantieri Misti
  - Nuova collezione `voci_lavoro` + API CRUD
  - Sezione "Voci di Lavoro" nella scheda commessa
  - CommessaOpsPanel mostra sezioni basate su unione delle categorie delle voci
  - Retrocompatibilità: commesse senza voci funzionano come prima
- **FASE 2:** Diario Produzione adattivo per categoria/voce
  - Operaio seleziona la voce su cui lavora
  - GENERICA: solo ore e materiali
  - EN 13241: aggiunge foto collaudo
  - EN 1090: mostra tutto (certificati, WPS, tracciabilità)
- **FASE 3:** "Pulsante Magico" per generare il Fascicolo di Cantiere
  - Raggruppa automaticamente le certificazioni per ogni voce
  - EN 1090 → Fascicolo Tecnico (DoP + CE + Piano QC + Certificati + WPS)
  - EN 13241 → Libretto Manutenzione (Scheda tecnica + Verbale collaudo + Manuale d'Uso)
  - GENERICA → Riepilogo Costi (ore + materiali + margine)

### Backlog Tecnico
- Split `SettingsPage.js` (1.731 righe)
- Vista Officina mobile-first per operai
- Responsive restanti pagine
- Onboarding Wizard per nuovi utenti

### Backlog Funzionale
- RBAC granulare (ruoli personalizzati)
- Export Excel per analisi costi
- Unificazione 13 servizi PDF
- Firme digitali su PDF
- Portale clienti read-only
- Notifiche WhatsApp scadenze

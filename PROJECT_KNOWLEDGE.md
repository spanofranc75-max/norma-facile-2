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

## 3. STRUTTURA MATRIOSKA — Cantieri Misti

> **REGOLA FONDAMENTALE:** Una Commessa non è un blocco unico. E' un "Fascicolo di Cantiere"
> che puo' contenere diverse **Voci di Lavoro**, ognuna con la sua identità normativa.

### Perche' serve
Il cliente Bianchi ordina per lo stesso cantiere:
- **Voce A:** "Soppalco capannone" → EN 1090 (EXC2) → attiva tracciabilità ferro, patentini, DoP
- **Voce B:** "Cancello carraio" → EN 13241 → attiva foto sicurezza, collaudo forze, Libretto Manutenzione
- **Voce C:** "Riparazione ringhiera" → GENERICA → solo ore e materiali, nessuna burocrazia

Senza la Matrioska, bisognerebbe creare 3 commesse separate. Tre numeri, tre cartelle, tre contabilità. Un casino.

### Come funziona nel software

1. **Alla creazione** della commessa si sceglie la categoria principale
2. **Dopo la creazione**, nella scheda della commessa si possono aggiungere "Voci di Lavoro" extra
3. **Ogni voce** ha: descrizione, categoria normativa, e i campi specifici della sua categoria
4. **Il pannello operativo** mostra le sezioni di TUTTE le categorie presenti nelle voci (unione)
5. **Il Diario di Produzione** chiede all'operaio "Su quale voce stai lavorando?" e filtra le domande
6. **Il "Pulsante Magico"** genera un Fascicolo di Cantiere unico che raggruppa tutto

### Schema DB

```
// Nuova collezione: voci_lavoro
{
  voce_id: "voce_abc123",
  commessa_id: "com_xyz789",
  descrizione: "Soppalco capannone",
  normativa_tipo: "EN_1090",
  classe_exc: "EXC2",               // solo per EN_1090
  tipologia_chiusura: "",            // solo per EN_13241
  ordine: 1,
  created_at: "2026-03-20T...",
}
```

### Retrocompatibilita'
Le commesse gia' esistenti (senza voci) funzionano ESATTAMENTE come prima.
Il campo `normativa_tipo` della commessa vale come "voce unica implicita".

---

## 4. DIARIO DI PRODUZIONE ADATTIVO (Mobile-First)

> L'operaio accede dal telefono (tramite QR o link rapido).
> Il diario si adatta alla voce di lavoro selezionata.

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
2. Seleziona la commessa (o la trova gia' preselezionata dal QR)
3. Se la commessa ha piu' voci, sceglie "Su quale voce stai lavorando?"
4. Il diario mostra SOLO i campi pertinenti a quella voce
5. Salva con un bottone grande e chiaro

---

## 5. IL PULSANTE MAGICO (Output Documentale)

> Un unico bottone nella scheda commessa che genera il "Pacco Documenti Cantiere".

### Output per tipo

**EN 1090 → Fascicolo Tecnico:**
- Dichiarazione di Prestazione (DoP)
- Etichetta CE
- Piano di Controllo Qualita'
- Certificati materiali 3.1
- WPS/WPQR
- Scheda Rintracciabilita' Materiali
- CAM (se applicabile)

**EN 13241 → Libretto Manutenzione:**
- Scheda tecnica prodotto
- Verbale collaudo forze (EN 12453)
- Foto kit sicurezza (fotocellule, coste, lampeggiante)
- Manuale d'Uso e Manutenzione
- Dichiarazione di Prestazione (DoP)

**GENERICA → Riepilogo Lavorazioni:**
- Ore lavorate per operaio
- Materiali utilizzati
- Riepilogo costi (solo per il titolare, MAI per l'operaio)

### Per Cantieri Misti (Matrioska)
Il Pulsante Magico genera un **unico file PDF** (o cartella ZIP) che separa ordinatamente:
1. Sezione "Documenti Strutturali (EN 1090)" — per ogni voce strutturale
2. Sezione "Documenti Sicurezza Cancelli (EN 13241)" — per ogni voce cancello
3. Sezione "Riepilogo Lavorazioni Generiche" — per le voci senza marcatura

---

## 6. Architettura del Codice

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

### Regole di Manutenzione Codice

**SOGLIA 800 RIGHE:** Ogni volta che un Service o Route supera le 800 righe,
si DEVE proporre di spezzarlo in file piu' piccoli (es. `service_1090.py`, `service_13241.py`, `service_generica.py`).

**File gia' spezzati:**
- `commessa_ops.py` (3.430 righe) → **FATTO** → 6 moduli + wrapper
- `CommessaOpsPanel.js` (2.964 righe) → **FATTO** → 8 sotto-componenti + orchestratore

**File da spezzare:**
- `SettingsPage.js` (1.731 righe)
- `commesse.py` (1.330 righe)

**Non eliminare dati esistenti.** Se la struttura cambia, mappare i dati vecchi verso la nuova struttura a 3 binari.

---

## 7. UX Officina — Regole di Design

### Bottoni Grandi e Chiari
Il titolare e gli operai usano l'app con le **mani sporche di ferro** e spesso **di fretta**:
- Bottoni grandi (min h-11, testo leggibile)
- Colori distintivi: blu = strutturale, ambra = cancello, grigio = generico
- Icone sempre presenti accanto al testo
- Touch target minimo 44x44px per mobile

### Accesso Separato per Operai
**L'operaio NON deve MAI vedere:** costi orari, margini, prezzi, preventivi, fatture, impostazioni, anagrafica clienti/fornitori.
**L'operaio DEVE vedere solo:** Diario di Produzione, Fasi di lavorazione, Foto del lavoro.

> **Vista Officina** (da implementare): interfaccia mobile-first, accessibile con PIN o QR code,
> che mostra solo le commesse attive e il diario di produzione.

### Responsive Mobile
Pattern TailwindCSS usati su tutte le pagine:
- `flex-col sm:flex-row` per header con bottoni
- `hidden md:table-cell` per colonne secondarie nelle tabelle
- `overflow-x-auto` wrapper attorno alle tabelle
- `w-full sm:w-auto` per bottoni full-width su mobile
- `grid-cols-1 sm:grid-cols-N` per form nei dialog

---

## 8. Database — Regole

- **NON modificare** tabelle/collezioni esistenti per aggiungere funzionalita'
- **Creare nuove collezioni** se servono dati nuovi (es. `voci_lavoro`, `kit_sicurezza_13241`)
- Tutti i campi ID usano prefissi: `com_` (commesse), `user_` (utenti), `voce_` (voci di lavoro)
- `_id` di MongoDB **MAI** esposto nelle API REST
- Date sempre in UTC con `datetime.now(timezone.utc)`

### Collezioni Principali
| Collezione | Scopo | Note |
|---|---|---|
| `commesse` | Fascicoli di cantiere | Campo chiave: `normativa_tipo` (categoria principale) |
| `voci_lavoro` | Voci di lavoro dentro una commessa | **NUOVA** — Struttura Matrioska |
| `preventivi` | Preventivi clienti | Possono generare commesse |
| `articoli` | Catalogo articoli/materiali | Con giacenza magazzino |
| `diario_produzione` | Registrazioni ore operai | Per commessa + voce |
| `material_batches` | Lotti materiale tracciati | Solo EN 1090 |
| `cam_lotti` | Lotti CAM per DM 256/2022 | Solo EN 1090 |
| `fatture` | Fatture emesse | Collegabili a commesse |
| `fatture_ricevute` | Fatture fornitori | Per calcolo costi |
| `clients` | Clienti + fornitori | Campo `client_type` distingue |

---

## 9. Log delle Modifiche

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

**Master Plan integrato nel PROJECT_KNOWLEDGE.md**
- Aggiunta regola Cantieri Misti (Struttura Matrioska)
- Aggiunta specifica Diario Produzione Adattivo (sezione 4)
- Aggiunta specifica Pulsante Magico (sezione 5)
- Aggiunta regola 800 righe per manutenzione codice

---

## 10. Prossimi Passi (Roadmap)

### Fase 1.5 — Voci di Lavoro (Cantieri Misti)
- Backend: Nuova collezione `voci_lavoro` + API CRUD
- Frontend: Sezione "Voci di Lavoro" nella scheda commessa
- CommessaOpsPanel mostra sezioni basate su unione delle categorie delle voci
- Retrocompatibilita': commesse senza voci funzionano come prima

### Fase 2 — Diario Produzione Adattivo
- Operaio seleziona la voce su cui lavora
- Filtro intelligente: EN 1090 → certificati | EN 13241 → foto collaudo | GENERICA → solo Start/Stop
- Zero contabilita' per l'operaio

### Fase 3 — Pulsante Magico
- Genera Fascicolo di Cantiere unico (PDF o ZIP)
- Separazione automatica: Strutturali | Cancelli | Generiche

### Backlog Tecnico
- Split `SettingsPage.js` (1.731 righe)
- Split `commesse.py` (1.330 righe)
- Vista Officina mobile-first per operai (QR + PIN)
- Responsive restanti pagine
- Onboarding Wizard per nuovi utenti

### Backlog Funzionale
- RBAC granulare (ruoli personalizzati)
- Export Excel per analisi costi
- Unificazione 13 servizi PDF
- Firme digitali su PDF
- Portale clienti read-only
- Notifiche WhatsApp scadenze

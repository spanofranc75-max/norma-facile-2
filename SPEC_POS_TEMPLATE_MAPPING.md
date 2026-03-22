# SPEC_POS_TEMPLATE_MAPPING.md
## Mappatura Template POS STEEL PROJECT → Modelli Dati NormaFacile 2.0

**Data**: 2026-03-23
**Versione**: 1.0
**Scopo**: Mappare ogni sezione del template `POS STEEL PROJECT.doc` ai modelli dati proposti (`cantieri_sicurezza`, `libreria_rischi`) e classificarle come FISSA / VARIABILE / IBRIDA.

---

## 1. Struttura Macro del Template

Il documento POS analizzato (459 KB, ~1760 righe) segue la struttura dell'**Allegato XV del D.Lgs. 81/2008**. Si compone di **31 sezioni logiche** raggruppate in 6 macroaree:

| # | Macroarea | Sezioni | Tipo Prevalente |
|---|-----------|---------|-----------------|
| A | Copertina & Revisioni | 1-2 | VARIABILE |
| B | Presentazione Impresa | 3-6 | VARIABILE (da DB aziendale) |
| C | Dati Cantiere & Organizzazione | 7-12 | VARIABILE (da `cantieri_sicurezza`) |
| D | Misure Prevenzione & DPI | 13-19 | IBRIDA (testo fisso + tabelle variabili) |
| E | Valutazione Rischi | 20-28 | IBRIDA (metodologia fissa + schede da `libreria_rischi`) |
| F | Emergenza & Dichiarazione | 29-31 | IBRIDA (testo fisso + numeri/firme variabili) |

---

## 2. Mapping Dettagliato Sezione per Sezione

### MACROAREA A — Copertina & Revisioni

#### A.1 — Copertina (pagina 1)
- **Tipo**: VARIABILE
- **Contenuto**: Titolo "PIANO OPERATIVO DI SICUREZZA", riferimenti normativi, tabella azienda, tabella revisioni
- **Fonte dati**:
  - `company_settings.business_name` → "Azienda"
  - `company_settings.address` → "Sede"
  - `company_settings.attivita_ateco` → "Attivita"
  - `company_settings.indirizzo_capannone` → "Indirizzo del capannone"
  - `cantieri_sicurezza.revisioni[]` → Tabella revisioni (rev, motivazione, data)

#### A.2 — Indice
- **Tipo**: FISSA (auto-generata)
- **Note**: L'indice viene generato automaticamente dal motore DOCX. Non richiede dati.

---

### MACROAREA B — Presentazione Impresa

#### B.3 — Introduzione
- **Tipo**: FISSA
- **Contenuto**: Testo normativo boilerplate (riferimento D.Lgs. 81/2008)
- **Fonte dati**: Nessuna. Testo fisso dal template.

#### B.4 — Elenco Documentazione da conservare in cantiere
- **Tipo**: FISSA
- **Contenuto**: Elenco puntato di documenti obbligatori (Patente a Crediti, POS, UNILAV, INAIL, etc.)
- **Fonte dati**: Nessuna. Testo fisso normativo.
- **Nota AI**: Il motore AI potrebbe verificare cross-reference con `company_documents` per segnalare documenti mancanti/scaduti.

#### B.5 — Presentazione dell'azienda
- **Tipo**: FISSA
- **Contenuto**: Testo introduttivo generico. Contiene anche il ruolo "DIRETTORE TECNICO DI CANTIERE" e "CAPOCANTIERE" con mansioni descritte.
- **Fonte dati**: Nessuna. Testo boilerplate.

#### B.6 — Anagrafica Aziendale
- **Tipo**: VARIABILE
- **Contenuto**: Tabella con dati aziendali
- **Fonte dati**:
  - `company_settings.business_name` → "Impresa"
  - `company_settings.address` → "Sede Legale"
  - `company_settings.phone` → "Tel."
  - `company_settings.datore_lavoro` → "Datore di Lavoro"
  - `company_settings.rspp` → "RSPP"
  - `company_settings.medico_competente` → "Medico Competente"
  - `company_settings.rls` → "RLS"

---

### MACROAREA C — Dati Cantiere & Organizzazione

#### C.7 — Mansionario
- **Tipo**: VARIABILE
- **Contenuto**: Tabella con nominativo, mansione, addetto primo soccorso, addetto antincendio
- **Fonte dati**: `cantieri_sicurezza.lavoratori_coinvolti[]`
  - Ogni entry: `{ nominativo, mansione, addetto_primo_soccorso: bool, addetto_antincendio: bool }`
- **Cross-ref**: `welders` collection (anagrafica operai esistente)

#### C.8 — Dati relativi al cantiere
- **Tipo**: VARIABILE
- **Contenuto**: Attivita, date inizio/fine, indirizzo cantiere, citta, provincia
- **Fonte dati**: `cantieri_sicurezza`
  - `.attivita_cantiere` → "Attivita"
  - `.data_inizio_lavori` → "Data inizio lavori"
  - `.data_fine_prevista` → "Data presunta di fine lavori"
  - `.indirizzo_cantiere` → "Indirizzo"
  - `.citta_cantiere` → "Citta"
  - `.provincia_cantiere` → "Provincia"

#### C.9 — Soggetti di riferimento
- **Tipo**: VARIABILE
- **Contenuto**: Tabella committente, responsabile lavori, DL, progettista, CSP, CSE
- **Fonte dati**: `cantieri_sicurezza.soggetti_riferimento`
  - `{ committente, responsabile_lavori, direttore_lavori, progettista, csp, cse }`
- **Cross-ref**: Il committente potrebbe derivare dalla `commessa.client_name`

#### C.10 — Turni di lavoro
- **Tipo**: IBRIDA
- **Contenuto**: Orari standard (mattina 08:00-13:00, pomeriggio 14:00-17:00) + nota su rumore
- **Fonte dati**: `cantieri_sicurezza.turni_lavoro`
  - Default: `{ mattina: "08:00-13:00", pomeriggio: "14:00-17:00" }`
  - Override possibile per cantiere

#### C.11 — Lavorazioni in subappalto
- **Tipo**: VARIABILE
- **Contenuto**: Tabella con lavorazione, impresa/lavoratore autonomo, durata prevista
- **Fonte dati**: `cantieri_sicurezza.subappalti[]`
  - Ogni entry: `{ lavorazione, impresa, durata_prevista }`

#### C.12 — Principali misure di prevenzione
- **Tipo**: FISSA
- **Contenuto**: ~4 pagine di testo normativo su: obblighi lavoratori, investimento, scivolamenti, rumori, punture/tagli, cesoiamento, lavori in elevazione, cadute, scale, vernici, movimentazione, polveri, getti, allergeni, murature, macchine, attrezzi, demolizioni, sorveglianza sanitaria
- **Fonte dati**: Nessuna. Testo fisso boilerplate.
- **Nota**: Questo e il blocco piu grande di testo fisso del template (~40% del documento).

---

### MACROAREA D — Misure Prevenzione & DPI

#### D.13 — Attivita Formativa
- **Tipo**: FISSA
- **Contenuto**: Elenco argomenti corsi di formazione obbligatori
- **Fonte dati**: Nessuna. Testo fisso.

#### D.14 — Sorveglianza Sanitaria
- **Tipo**: IBRIDA
- **Contenuto**: Testo fisso + tabella programma sanitario variabile
- **Fonte dati**: `cantieri_sicurezza.programma_sanitario`
  - Potenzialmente cross-ref con `welders.scadenza_visita_medica`

#### D.15 — DPI (Dispositivi di Protezione Individuale)
- **Tipo**: IBRIDA
- **Contenuto**: 
  - Testo fisso: Descrizione dettagliata di ogni tipo DPI (casco, guanti, calzature, cuffie, maschere, occhiali, cinture, indumenti)
  - Tabella variabile: Lista DPI presenti in cantiere con flag SI/NO
- **Fonte dati**: 
  - Descrizioni DPI → `libreria_rischi` (tipo: "dpi")
  - Tabella presenza → `cantieri_sicurezza.dpi_presenti[]`
    - `{ tipo_dpi, presente: bool }`

#### D.16 — Segnaletica di sicurezza
- **Tipo**: IBRIDA
- **Contenuto**:
  - Testo fisso: definizione, obblighi, scopo
  - Tabella variabile: tipologia cartello, posizionamento
- **Fonte dati**: Tabella segnaletica standard da `libreria_rischi` (tipo: "segnaletica"), filtrabile per contesto cantiere.

#### D.17 — Macchine / Attrezzature / Impianti
- **Tipo**: VARIABILE
- **Contenuto**: Tabella con nome macchina, marcata CE (Si/No), verifiche periodiche (Si/No)
- **Fonte dati**: `cantieri_sicurezza.macchine_attrezzature[]`
  - Ogni entry: `{ nome, marcata_ce: bool, verifiche_periodiche: bool }`
- **Nota**: Il template elenca: Avvitatore, Flessibile, Martello demolitore, Sega circolare, Trapano, Utensili elettrici portatili, Utensili manuali.

#### D.18 — Sostanze chimiche / Prodotti chimici
- **Tipo**: VARIABILE
- **Contenuto**: Nota "Si allegano in formato cartaceo le schede di sicurezza..."
- **Fonte dati**: `cantieri_sicurezza.sostanze_chimiche[]`
  - Ogni entry: `{ nome_sostanza, scheda_sicurezza_allegata: bool }`

#### D.19 — Agenti biologici
- **Tipo**: IBRIDA
- **Contenuto**: Tabella agenti + INTEGRAZIONE COVID-19 (9 sezioni dettagliate)
- **Fonte dati**: 
  - Tabella agenti → `cantieri_sicurezza.agenti_biologici[]`
  - COVID-19 → testo fisso (legacy/normativo)
- **Nota**: La sezione COVID-19 occupa ~3 pagine. Potrebbe essere marcata come "includibile" con un flag, dato che le norme COVID potrebbero essere superate.

---

### MACROAREA E — Valutazione Rischi

#### E.20 — Stoccaggio materiali e/o rifiuti
- **Tipo**: VARIABILE
- **Contenuto**: Campo di testo libero (template ha "......")
- **Fonte dati**: `cantieri_sicurezza.stoccaggio_materiali` (text)

#### E.21 — Servizi Igienico-Assistenziali
- **Tipo**: VARIABILE
- **Contenuto**: Campo di testo libero (template ha "......")
- **Fonte dati**: `cantieri_sicurezza.servizi_igienici` (text)

#### E.22 — Obiettivo della valutazione
- **Tipo**: FISSA
- **Contenuto**: Testo normativo sulla metodologia di valutazione del rischio
- **Fonte dati**: Nessuna.

#### E.23 — Criteri adottati (I = 2*D + P)
- **Tipo**: FISSA
- **Contenuto**: Formula I = 2*D + P, scale P (1-4), scale D (1-4), classificazione rischio
- **Fonte dati**: Nessuna. Metodologia standard.

#### E.24 — Elenco fattori di rischio
- **Tipo**: FISSA
- **Contenuto**: 3 macro-tabelle (Rischi Sicurezza, Rischi Salute, Rischi Trasversali)
- **Fonte dati**: Nessuna. Checklist normativa standard.

#### E.25 — Individuazione Soggetti Esposti
- **Tipo**: FISSA
- **Contenuto**: Testo normativo su categorie soggetti esposti
- **Fonte dati**: Nessuna.

#### E.26 — Valutazione Rischio Rumore
- **Tipo**: IBRIDA
- **Contenuto**: Metodologia fissa + risultati per mansione variabili
- **Fonte dati**: 
  - `cantieri_sicurezza.valutazione_rumore` (risultati)
  - Cross-ref con `company_documents` (allegato rumore)

#### E.27 — Valutazione Rischio Vibrazioni
- **Tipo**: IBRIDA
- **Contenuto**: Metodologia fissa + risultati per mansione variabili
- **Fonte dati**: `cantieri_sicurezza.valutazione_vibrazioni`

#### E.28 — Valutazione Rischio Chimico
- **Tipo**: IBRIDA
- **Contenuto**: Metodologia fissa (algoritmo Piemonte IG x IFU x IEU) + risultati variabili
- **Fonte dati**: `cantieri_sicurezza.valutazione_chimico`

#### E.29 — Movimentazione Manuale Carichi
- **Tipo**: IBRIDA
- **Contenuto**: Metodologia NIOSH fissa + risultati variabili
- **Fonte dati**: `cantieri_sicurezza.valutazione_mmc`

#### E.30 — Schede Rischio per Fase di Lavoro
- **Tipo**: VARIABILE (core del motore AI)
- **Contenuto**: Per ogni fase di lavoro:
  - Descrizione fase
  - Macchine/attrezzature utilizzate
  - Tabella rischi (descrizione, probabilita, entita danno, classe)
  - Interventi/disposizioni/procedure
  - Tabella DPI (rischio, DPI, descrizione, rif. normativo)
- **Fonte dati**: `libreria_rischi` (tipo: "fase_lavoro")
  - Il template include un esempio: "CONSOLIDAMENTO APERTURE MEDIANTE CERCHIATURA"
  - Il motore AI selezionera le fasi pertinenti in base all'analisi tecnica della commessa
- **Questo e il cuore della generazione intelligente del POS.**

---

### MACROAREA F — Emergenza & Dichiarazione

#### F.31 — Gestione Emergenza
- **Tipo**: IBRIDA
- **Contenuto**: Testo fisso su mezzi antincendio, estintori (tabella classi A-E), precauzioni, compiti squadra emergenza
- **Fonte dati**: Testo prevalentemente fisso. La tabella estintori e standard.

#### F.32 — Pronto soccorso
- **Tipo**: FISSA
- **Contenuto**: Testo normativo sugli obblighi del datore di lavoro

#### F.33 — Numeri utili
- **Tipo**: IBRIDA
- **Contenuto**: Tabella numeri standard (VVF 115, PS 118, CC 112, PS 113) + eventuali numeri locali
- **Fonte dati**: `cantieri_sicurezza.numeri_utili[]` (override possibile)

#### F.34 — Dichiarazione finale
- **Tipo**: VARIABILE
- **Contenuto**: Dichiarazione firmata dal DdL, RSPP, RLS con data
- **Fonte dati**:
  - `company_settings.datore_lavoro`
  - `company_settings.rspp`
  - `company_settings.rls`
  - `cantieri_sicurezza.data_dichiarazione`

---

## 3. Riepilogo Statistico

| Classificazione | N. Sezioni | % Template | Note |
|-----------------|-----------|-----------|------|
| **FISSA** | 14 | ~55% | Testo normativo/boilerplate copiato dal template |
| **VARIABILE** | 10 | ~25% | Dati da `cantieri_sicurezza` + `company_settings` |
| **IBRIDA** | 10 | ~20% | Struttura fissa + dati variabili da DB + `libreria_rischi` |

---

## 4. Modello Dati Proposto: `cantieri_sicurezza`

```json
{
  "cantiere_id": "string (uuid)",
  "tenant_id": "string",
  "parent_commessa_id": "string (ref commesse)",
  "ramo_id": "string (ref commesse_normative, opzionale)",
  "status": "bozza | in_compilazione | completo | approvato",

  "revisioni": [
    { "rev": "00", "motivazione": "Emissione", "data": "2026-01-15" }
  ],

  "dati_cantiere": {
    "attivita_cantiere": "string",
    "data_inizio_lavori": "date",
    "data_fine_prevista": "date",
    "indirizzo_cantiere": "string",
    "citta_cantiere": "string",
    "provincia_cantiere": "string"
  },

  "soggetti_riferimento": {
    "committente": "string",
    "responsabile_lavori": "string",
    "direttore_lavori": "string",
    "progettista": "string",
    "csp": "string",
    "cse": "string"
  },

  "lavoratori_coinvolti": [
    {
      "nominativo": "string",
      "mansione": "string",
      "addetto_primo_soccorso": "bool",
      "addetto_antincendio": "bool",
      "worker_id": "string (ref welders, opzionale)"
    }
  ],

  "turni_lavoro": {
    "mattina": "08:00-13:00",
    "pomeriggio": "14:00-17:00",
    "note": "string"
  },

  "subappalti": [
    { "lavorazione": "string", "impresa": "string", "durata_prevista": "string" }
  ],

  "dpi_presenti": [
    { "tipo_dpi": "string", "presente": "bool" }
  ],

  "macchine_attrezzature": [
    { "nome": "string", "marcata_ce": "bool", "verifiche_periodiche": "bool" }
  ],

  "sostanze_chimiche": [
    { "nome_sostanza": "string", "scheda_sicurezza_allegata": "bool" }
  ],

  "agenti_biologici": [
    { "agente": "string", "rischi": "string", "misure_prevenzione": "string" }
  ],

  "stoccaggio_materiali": "string (testo libero)",
  "servizi_igienici": "string (testo libero)",

  "valutazione_rumore": { "esito_generale": "string", "dettagli_per_mansione": [] },
  "valutazione_vibrazioni": { "esito_generale": "string", "dettagli_per_mansione": [] },
  "valutazione_chimico": { "esito_generale": "string", "dettagli_per_sostanza": [] },
  "valutazione_mmc": { "esito_generale": "string", "indice_rischio": "number" },

  "fasi_lavoro_selezionate": [
    {
      "fase_id": "string (ref libreria_rischi)",
      "nome_fase": "string",
      "rischi_valutati": [
        { "descrizione": "string", "probabilita": "string", "entita_danno": "string", "classe": "string" }
      ],
      "dpi_richiesti": ["string"],
      "misure_aggiuntive": "string"
    }
  ],

  "numeri_utili": [
    { "servizio": "Vigili del fuoco", "numero": "115" },
    { "servizio": "Pronto soccorso", "numero": "118" },
    { "servizio": "Carabinieri", "numero": "112" }
  ],

  "includi_covid19": "bool (default: false)",
  "data_dichiarazione": "date",
  "note_aggiuntive": "string",

  "gate_pos_status": {
    "completezza_percentuale": "number",
    "campi_mancanti": ["string"],
    "pronto_per_generazione": "bool"
  },

  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 5. Modello Dati Proposto: `libreria_rischi`

```json
{
  "risk_id": "string (uuid)",
  "tenant_id": "string",
  "tipo": "fase_lavoro | dpi | segnaletica | macchina",
  "codice": "string (es: FL-001, DPI-CASCO, SEG-VIETATO_FUMARE)",
  "nome": "string",
  "descrizione": "string",
  "categoria": "string (es: carpenteria_metallica, saldatura, montaggio, demolizione)",

  "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],

  "rischi_associati": [
    {
      "descrizione": "string",
      "probabilita_default": "Bassa | Medio Bassa | Medio Alta | Elevata",
      "danno_default": "Trascurabile | Modesta | Notevole | Ingente",
      "classe_default": "Accettabile | Modesto | Grave | Gravissimo"
    }
  ],

  "misure_prevenzione": ["string"],

  "dpi_richiesti": [
    {
      "tipo_dpi": "string",
      "descrizione": "string",
      "rif_normativo": "string (es: UNI EN 397, Art 75-77-78 D.Lgs 81/08)"
    }
  ],

  "macchine_tipiche": ["string"],

  "testo_template": "string (testo fisso associato, es. descrizione dettagliata DPI)",

  "is_default": "bool (true = seed iniziale, false = aggiunto dal tenant)",
  "attivo": "bool",

  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 6. Seed Iniziale `libreria_rischi` (MVP)

Per l'MVP, basandoci sulle attivita tipiche di STEEL PROJECT (carpenteria metallica), il seed include:

### Fasi di Lavoro

| Codice | Nome | Categoria | Rischi Chiave |
|--------|------|-----------|---------------|
| FL-001 | Taglio e preparazione lamiere/profili | carpenteria_metallica | Proiezione schegge, rumore, vibrazioni, tagli |
| FL-002 | Saldatura (MIG/MAG, TIG, Elettrodo) | saldatura | Radiazioni UV/IR, fumi, ustioni, incendio |
| FL-003 | Montaggio strutture in cantiere | montaggio | Caduta dall'alto, caduta materiali, urti, schiacciamento |
| FL-004 | Movimentazione e trasporto materiali | movimentazione | MMC, investimento, schiacciamento |
| FL-005 | Verniciatura / Trattamenti superficiali | verniciatura | Chimico (solventi/vapori), incendio, inalazione |
| FL-006 | Foratura e lavorazione meccanica | lavorazione_meccanica | Proiezione trucioli, impigliamento, rumore |
| FL-007 | Piegatura e calandratura | lavorazione_meccanica | Schiacciamento, cesoiamento, vibrazioni |
| FL-008 | Consolidamento aperture / cerchiatura | edilizia_strutturale | Rumore, proiezione schegge, vibrazioni, MMC |
| FL-009 | Installazione cancelli/portoni | montaggio_en13241 | Caduta, schiacciamento, elettrico, taglio |
| FL-010 | Collaudo e messa in esercizio | collaudo | Elettrico, schiacciamento, movimentazione |

### DPI Standard

| Codice | Nome | Rif. Normativo |
|--------|------|----------------|
| DPI-CASCO | Casco protettivo | UNI EN 397 |
| DPI-GUANTI-CROSTA | Guanti in crosta | UNI EN 388 |
| DPI-GUANTI-CALORE | Guanti protezione calore | UNI EN 407 |
| DPI-SCARPE | Scarpe antinfortunistiche | UNI EN ISO 20344 |
| DPI-OCCHIALI | Occhiali di protezione | UNI EN 166 |
| DPI-SCHERMO-SALD | Schermo saldatura | UNI EN 169/175 |
| DPI-CUFFIE | Cuffie/tappi auricolari | UNI EN 352 |
| DPI-MASCHERA | Maschera antipolvere/filtro | UNI EN 149 |
| DPI-CINTURA | Cintura anticaduta | UNI EN 361/362 |
| DPI-TUTA | Tuta di protezione | UNI EN 340 |

### Segnaletica

| Codice | Tipologia | Cartello |
|--------|-----------|----------|
| SEG-001 | Divieto | Vietato Fumare |
| SEG-002 | Divieto | Vietato Fumare o usare fiamme libere |
| SEG-003 | Pericolo | Attenzione schegge |
| SEG-004 | Pericolo | Attenzione alle mani |
| SEG-005 | Pericolo | Attenzione ai carichi sospesi |
| SEG-006 | Obbligo | Protezione occhi |
| SEG-007 | Obbligo | Guanti obbligatori |
| SEG-008 | Obbligo | Calzature obbligatorie |
| SEG-009 | Obbligo | Casco obbligatorio |
| SEG-010 | Salvataggio | Pronto soccorso |
| SEG-011 | Antincendio | Estintore |

---

## 7. Flusso Generazione DOCX

```
1. Utente apre "Scheda Cantiere Sicurezza" per una commessa
2. Il sistema pre-compila:
   - Dati aziendali da `company_settings`
   - Dati commessa da `commesse` (cliente, indirizzo)
   - Lavoratori da `welders`
   - Macchine default da `libreria_rischi`
   - DPI default da `libreria_rischi`
3. Il Motore AI analizza:
   - Tipo lavorazioni (da istruttoria/segmentazione)
   - Normative coinvolte (EN 1090, EN 13241)
   - Propone fasi di lavoro pertinenti da `libreria_rischi`
   - Propone rischi aggiuntivi specifici
4. L'utente rivede, modifica, integra
5. `gate_pos` verifica completezza
6. Generazione DOCX:
   - Sezioni FISSE → copiate dal template
   - Sezioni VARIABILI → populate da `cantieri_sicurezza`
   - Sezioni IBRIDE → merge template + dati
   - Schede rischio → iterate da `fasi_lavoro_selezionate`
```

---

## 8. Cross-Reference con Collezioni Esistenti

| Campo POS | Collezione Fonte | Campo Fonte |
|-----------|------------------|-------------|
| Azienda, Sede, DdL, RSPP | `company_settings` | business_name, address, ... |
| Committente | `commesse` / `preventivi` | client_name |
| Lavoratori | `welders` | nome, cognome, mansione |
| Documenti aziendali | `company_documents` | categoria: sicurezza_globale |
| Allegati POS (Rumore, Vibrazioni) | `company_documents` | categoria: allegati_pos |
| Tipo lavorazioni | `commesse_preistruite` | segmentation, normative |
| Normative coinvolte | `commesse_normative` | normativa |

---

## 9. Note Implementative

1. **python-docx vs WeasyPrint**: Per generare il POS come `.docx` editabile (requisito utente), usare `python-docx`. WeasyPrint genera PDF non editabili.
2. **Template base**: Convertire il `.doc` in `.docx` e usarlo come template base per `python-docx`, iniettando i dati variabili nelle posizioni corrette.
3. **Sezione COVID-19**: Flag opzionale `includi_covid19` perche le norme potrebbero non essere piu vigenti.
4. **Schede rischio per fase**: Queste sono il vero valore aggiunto dell'AI. La libreria rischi fornisce i default, l'AI personalizza in base al contesto specifico della commessa.
5. **Gate POS**: Simile all'Evidence Gate per le emissioni, ma con regole specifiche per la completezza del POS (campi obbligatori compilati, fasi di lavoro selezionate, DPI confermati).

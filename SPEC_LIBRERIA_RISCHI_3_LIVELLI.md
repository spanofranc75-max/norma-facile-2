# SPEC_LIBRERIA_RISCHI_3_LIVELLI.md
## Modello Libreria Sicurezza a 3 Livelli — NormaFacile 2.0

**Data**: 2026-03-23
**Versione**: 1.0 — BOZZA PER REVISIONE UTENTE
**Scopo**: Definire il modello dati a 3 livelli separati (Fasi → Rischi → DPI/Misure) per la libreria sicurezza, sostituendo il modello flat attuale.

---

## 1. Principio Architetturale

```
FASE LAVORATIVA ──attiva──> RISCHIO SICUREZZA ──richiede──> DPI / MISURA / APPRESTAMENTO
     (cosa fai)              (cosa puoi subire)              (come ti proteggi)
```

**Regola fondamentale**: Ogni livello e un'entita indipendente.
- Una **fase** puo attivare N rischi
- Un **rischio** puo essere attivato da N fasi
- Un **rischio** richiede N DPI/misure
- Un **DPI/misura** puo servire per N rischi

Relazione **many-to-many** gestita tramite array di codici (non embedding).

---

## 2. Collezione 1: `lib_fasi_lavoro`

Rappresenta le attivita lavorative concrete svolte in cantiere.

```json
{
  "codice": "FL-001",
  "user_id": "string (owner)",
  "nome": "Taglio e preparazione profili",
  "descrizione": "Taglio di lamiere e profili metallici con utensili manuali e automatici",
  "categoria": "carpenteria_metallica",
  "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],

  "trigger": {
    "keywords": ["taglio", "lamiera", "profilo", "cesoia", "plasma"],
    "contesto": ["officina", "cantiere"]
  },

  "rischi_ids": ["RS-PROIEZIONE", "RS-RUMORE", "RS-VIBRAZIONI", "RS-TAGLI"],

  "macchine_tipiche": ["Sega circolare", "Flessibile", "Cesoie", "Taglio plasma"],

  "is_default": true,
  "attivo": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Campi chiave:
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `codice` | string | Identificativo univoco (FL-001, FL-002, ...) |
| `nome` | string | Label leggibile |
| `descrizione` | string | Descrizione estesa per l'AI |
| `categoria` | string | Raggruppamento logico |
| `applicabile_a` | string[] | Normative pertinenti |
| `trigger.keywords` | string[] | Parole chiave che l'AI usa per matchare la fase con i dati della commessa |
| `trigger.contesto` | string[] | Dove si svolge (officina / cantiere / entrambi) |
| `rischi_ids` | string[] | Codici rischi attivati da questa fase |
| `macchine_tipiche` | string[] | Macchine/attrezzature tipicamente usate |

---

## 3. Collezione 2: `lib_rischi_sicurezza`

Rappresenta i pericoli concreti a cui il lavoratore e esposto.

```json
{
  "codice": "RS-CADUTA-ALTO",
  "user_id": "string (owner)",
  "nome": "Caduta dall'alto",
  "categoria": "sicurezza",
  "sottocategoria": "cadute",
  "descrizione": "Rischio di caduta da altezza superiore a 2 metri durante lavori in quota",

  "trigger": {
    "keywords": ["quota", "altezza", "ponteggio", "trabattello", "copertura", "tetto"],
    "condizioni": ["montaggio_cantiere", "lavori_quota"]
  },

  "valutazione_default": {
    "probabilita": "Medio Alta",
    "danno": "Ingente",
    "classe": "Gravissimo"
  },

  "misure_prevenzione": [
    "Utilizzo di ponteggi e trabattelli conformi",
    "Parapetti provvisori su bordi non protetti",
    "Cintura di sicurezza con fune di trattenuta",
    "Formazione specifica lavori in quota"
  ],

  "dpi_ids": ["DPI-CASCO", "DPI-CINTURA", "DPI-SCARPE"],
  "apprestamenti_ids": ["APP-PONTEGGIO", "APP-TRABATTELLO", "APP-PARAPETTI", "APP-LINEAVITA"],

  "documenti_correlati": ["formazione_lavori_quota", "idoneita_sanitaria"],
  "domande_verifica": [
    "Sono previsti lavori ad altezza superiore a 2 m?",
    "Quale sistema anticaduta e previsto?"
  ],

  "rif_normativo": "D.Lgs. 81/08 Titolo IV Capo II",
  "is_default": true,
  "attivo": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Campi chiave:
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `codice` | string | Identificativo univoco (RS-XXX) |
| `nome` | string | Label leggibile |
| `categoria` | string | Macro-famiglia: `sicurezza`, `salute`, `trasversale` |
| `sottocategoria` | string | Sotto-gruppo: `cadute`, `meccanico`, `chimico`, `fisico`, `elettrico`, `biologico`, `ergonomico`, `incendio` |
| `trigger.keywords` | string[] | L'AI usa queste per capire se il rischio e pertinente |
| `trigger.condizioni` | string[] | Condizioni operative che attivano il rischio |
| `valutazione_default` | object | P x D → Classe di rischio pre-calcolata |
| `misure_prevenzione` | string[] | Testo delle misure da inserire nel POS |
| `dpi_ids` | string[] | Codici DPI richiesti |
| `apprestamenti_ids` | string[] | Codici apprestamenti/attrezzature di sicurezza |
| `documenti_correlati` | string[] | Documenti/formazione necessari |
| `domande_verifica` | string[] | Domande che l'AI pone all'utente per confermare |
| `rif_normativo` | string | Riferimento normativo |

---

## 4. Collezione 3: `lib_dpi_misure`

Raggruppa DPI, misure organizzative e apprestamenti di sicurezza.

```json
{
  "codice": "DPI-CASCO",
  "user_id": "string (owner)",
  "nome": "Casco protettivo",
  "tipo": "dpi",
  "sottotipo": "protezione_capo",
  "descrizione": "Casco di protezione per il capo contro la caduta di oggetti e urti",
  "rif_normativo": "UNI EN 397 - Art 75-77-78 D.Lgs 81/08",
  "obbligatorieta": "sempre",
  "condizioni": [],

  "is_default": true,
  "attivo": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Valori `tipo`:
| Tipo | Descrizione | Prefisso codice |
|------|-------------|-----------------|
| `dpi` | Dispositivo di Protezione Individuale | DPI-XXX |
| `misura` | Misura organizzativa / procedurale | MIS-XXX |
| `apprestamento` | Attrezzatura/opera provvisionale di sicurezza | APP-XXX |

### Valori `obbligatorieta`:
- `sempre` — richiesto in ogni cantiere
- `condizionale` — richiesto solo se attivato da un rischio specifico
- `raccomandato` — suggerito ma non obbligatorio

---

## 5. Seed Data MVP

### 5.1 Fasi di Lavoro (11 fasi)

| Codice | Nome | Categoria | Contesto | Rischi attivati |
|--------|------|-----------|----------|-----------------|
| FL-001 | Scarico e movimentazione materiali | movimentazione | cantiere | RS-MMC, RS-INVESTIMENTO, RS-SCHIACCIAMENTO |
| FL-002 | Tracciamento e predisposizione area | preparazione | cantiere | RS-URTI, RS-INVESTIMENTO |
| FL-003 | Taglio e preparazione profili | carpenteria_metallica | officina, cantiere | RS-PROIEZIONE, RS-RUMORE, RS-VIBRAZIONI, RS-TAGLI |
| FL-004 | Foratura e lavorazione meccanica | lavorazione_meccanica | officina | RS-PROIEZIONE, RS-IMPIGLIAMENTO, RS-RUMORE |
| FL-005 | Piegatura e calandratura | lavorazione_meccanica | officina | RS-SCHIACCIAMENTO, RS-CESOIAMENTO, RS-VIBRAZIONI |
| FL-006 | Saldatura | saldatura | officina, cantiere | RS-RADIAZIONI-UV, RS-FUMI, RS-USTIONI, RS-INCENDIO |
| FL-007 | Verniciatura / Trattamenti superficiali | verniciatura | officina | RS-CHIMICO, RS-INCENDIO, RS-INALAZIONE |
| FL-008 | Montaggio strutture in cantiere | montaggio | cantiere | RS-CADUTA-ALTO, RS-CADUTA-MATERIALI, RS-URTI, RS-SCHIACCIAMENTO |
| FL-009 | Sollevamento con mezzi meccanici | sollevamento | cantiere | RS-CADUTA-MATERIALI, RS-INVESTIMENTO, RS-SCHIACCIAMENTO, RS-RIBALTAMENTO |
| FL-010 | Installazione cancelli/portoni | montaggio_en13241 | cantiere | RS-CADUTA-ALTO, RS-SCHIACCIAMENTO, RS-ELETTRICO, RS-TAGLI |
| FL-011 | Collaudo e messa in esercizio | collaudo | cantiere | RS-ELETTRICO, RS-SCHIACCIAMENTO |

### 5.2 Rischi Sicurezza (15 rischi)

| Codice | Nome | Categoria | Sottocategoria | P | D | Classe | DPI richiesti | Apprestamenti |
|--------|------|-----------|----------------|---|---|--------|---------------|---------------|
| RS-CADUTA-ALTO | Caduta dall'alto | sicurezza | cadute | Medio Alta | Ingente | Gravissimo | DPI-CASCO, DPI-CINTURA, DPI-SCARPE | APP-PONTEGGIO, APP-TRABATTELLO, APP-PARAPETTI, APP-LINEAVITA |
| RS-CADUTA-MATERIALI | Caduta materiali dall'alto | sicurezza | cadute | Medio Alta | Notevole | Grave | DPI-CASCO, DPI-SCARPE | APP-RETI-PROTEZIONE |
| RS-URTI | Urti, colpi, impatti | sicurezza | meccanico | Medio Alta | Modesta | Modesto | DPI-CASCO, DPI-GUANTI-CROSTA, DPI-SCARPE | — |
| RS-SCHIACCIAMENTO | Schiacciamento | sicurezza | meccanico | Medio Bassa | Ingente | Grave | DPI-SCARPE, DPI-GUANTI-CROSTA, DPI-CASCO | — |
| RS-CESOIAMENTO | Cesoiamento | sicurezza | meccanico | Medio Bassa | Ingente | Grave | DPI-GUANTI-CROSTA, DPI-SCARPE | — |
| RS-PROIEZIONE | Proiezione schegge/detriti | sicurezza | meccanico | Medio Alta | Notevole | Grave | DPI-OCCHIALI, DPI-GUANTI-CROSTA, DPI-TUTA | — |
| RS-TAGLI | Tagli e abrasioni | sicurezza | meccanico | Medio Alta | Modesta | Modesto | DPI-GUANTI-CROSTA, DPI-TUTA | — |
| RS-IMPIGLIAMENTO | Impigliamento | sicurezza | meccanico | Medio Bassa | Notevole | Modesto | DPI-TUTA | MIS-INDUMENTI-ADERENTI |
| RS-RUMORE | Rumore | salute | fisico | Elevata | Modesta | Grave | DPI-CUFFIE | MIS-VALUTAZIONE-RUMORE |
| RS-VIBRAZIONI | Vibrazioni meccaniche | salute | fisico | Medio Alta | Modesta | Modesto | DPI-GUANTI-CROSTA | MIS-VALUTAZIONE-VIBRAZIONI |
| RS-RADIAZIONI-UV | Radiazioni UV/IR (saldatura) | salute | fisico | Elevata | Notevole | Gravissimo | DPI-SCHERMO-SALD, DPI-TUTA | MIS-SCHERMATURA-AREA |
| RS-FUMI | Fumi di saldatura / polveri | salute | chimico | Elevata | Notevole | Gravissimo | DPI-MASCHERA, DPI-TUTA | MIS-ASPIRAZIONE-FUMI |
| RS-CHIMICO | Rischio chimico (solventi, vernici) | salute | chimico | Medio Alta | Notevole | Grave | DPI-MASCHERA, DPI-GUANTI-CROSTA, DPI-OCCHIALI, DPI-TUTA | MIS-VENTILAZIONE-FORZATA |
| RS-INALAZIONE | Inalazione vapori/solventi | salute | chimico | Medio Alta | Notevole | Grave | DPI-MASCHERA | MIS-VENTILAZIONE-FORZATA |
| RS-ELETTRICO | Rischio elettrico | sicurezza | elettrico | Medio Bassa | Ingente | Grave | DPI-GUANTI-ISOLANTI, DPI-SCARPE | MIS-SEZIONAMENTO-LINEA |
| RS-INCENDIO | Incendio / esplosione | sicurezza | incendio | Medio Bassa | Ingente | Grave | — | APP-ESTINTORE, MIS-ALLONTANARE-INFIAMMABILI |
| RS-INVESTIMENTO | Investimento da mezzi | sicurezza | meccanico | Medio Bassa | Ingente | Grave | DPI-GILET-AV, DPI-SCARPE, DPI-CASCO | MIS-PERCORSI-SEGNALATI |
| RS-RIBALTAMENTO | Ribaltamento mezzo | sicurezza | meccanico | Bassa | Ingente | Grave | DPI-CASCO | MIS-VERIFICA-PORTATA |
| RS-MMC | Movimentazione manuale carichi | salute | ergonomico | Medio Alta | Modesta | Modesto | DPI-GUANTI-CROSTA, DPI-SCARPE | MIS-AUSILI-MECCANICI |
| RS-USTIONI | Ustioni | sicurezza | termico | Medio Alta | Modesta | Modesto | DPI-GUANTI-CALORE, DPI-TUTA, DPI-SCARPE | — |

### 5.3 DPI / Misure / Apprestamenti (30 entries)

#### DPI (12)
| Codice | Nome | Sottotipo | Norma | Obbligatorieta |
|--------|------|-----------|-------|----------------|
| DPI-CASCO | Casco protettivo | protezione_capo | UNI EN 397 | sempre |
| DPI-GUANTI-CROSTA | Guanti in crosta | protezione_mani | UNI EN 388 | sempre |
| DPI-GUANTI-CALORE | Guanti protezione calore | protezione_mani | UNI EN 407 | condizionale |
| DPI-GUANTI-ISOLANTI | Guanti isolanti elettrici | protezione_mani | UNI EN 60903 | condizionale |
| DPI-SCARPE | Scarpe antinfortunistiche | protezione_piedi | UNI EN ISO 20344 | sempre |
| DPI-OCCHIALI | Occhiali di protezione | protezione_occhi | UNI EN 166 | condizionale |
| DPI-SCHERMO-SALD | Schermo saldatura | protezione_occhi | UNI EN 169/175 | condizionale |
| DPI-CUFFIE | Cuffie/tappi auricolari | protezione_udito | UNI EN 352 | condizionale |
| DPI-MASCHERA | Maschera antipolvere/filtro | protezione_vie_resp | UNI EN 149 | condizionale |
| DPI-CINTURA | Cintura anticaduta | protezione_caduta | UNI EN 361/362 | condizionale |
| DPI-TUTA | Tuta di protezione | protezione_corpo | UNI EN 340 | sempre |
| DPI-GILET-AV | Gilet alta visibilita | protezione_visibilita | UNI EN ISO 20471 | condizionale |

#### Misure organizzative (10)
| Codice | Nome | Descrizione |
|--------|------|-------------|
| MIS-INDUMENTI-ADERENTI | Indumenti aderenti | Non indossare abiti larghi, anelli, catene vicino a organi in movimento |
| MIS-VALUTAZIONE-RUMORE | Valutazione rischio rumore | Allegare valutazione fonometrica al POS |
| MIS-VALUTAZIONE-VIBRAZIONI | Valutazione rischio vibrazioni | Allegare valutazione vibrometrica al POS |
| MIS-SCHERMATURA-AREA | Schermatura area saldatura | Schermare l'area con teli ignifughi per proteggere terzi |
| MIS-ASPIRAZIONE-FUMI | Aspirazione localizzata fumi | Predisporre aspirazione forzata nell'area di saldatura |
| MIS-VENTILAZIONE-FORZATA | Ventilazione forzata | Garantire ricambio aria in area verniciatura/chimici |
| MIS-SEZIONAMENTO-LINEA | Sezionamento linea elettrica | Sezionare e verificare assenza tensione prima di operare |
| MIS-ALLONTANARE-INFIAMMABILI | Allontanare materiali infiammabili | Rimuovere materiali combustibili dall'area di lavoro |
| MIS-PERCORSI-SEGNALATI | Percorsi obbligati e segnalati | Segnalare con segnaletica i percorsi pedonali e veicolari |
| MIS-AUSILI-MECCANICI | Utilizzo ausili meccanici | Utilizzare mezzi meccanici per carichi > 25 kg |
| MIS-VERIFICA-PORTATA | Verifica portata terreno/mezzo | Verificare la portata del mezzo e del terreno prima del sollevamento |

#### Apprestamenti (8)
| Codice | Nome | Descrizione |
|--------|------|-------------|
| APP-PONTEGGIO | Ponteggio regolamentare | Ponteggio metallico conforme D.Lgs. 81/08 Allegato XVIII |
| APP-TRABATTELLO | Trabattello | Ponte su ruote conforme UNI EN 1004 |
| APP-PARAPETTI | Parapetti provvisori | Parapetti temporanei su bordi non protetti (h >= 100 cm) |
| APP-LINEAVITA | Linea vita | Sistema anticaduta fisso o temporaneo conforme UNI EN 795 |
| APP-RETI-PROTEZIONE | Reti di protezione | Reti sotto area di lavoro per caduta oggetti |
| APP-ESTINTORE | Estintore | Estintore a polvere o CO2 nelle vicinanze dell'area di lavoro |
| APP-PLE | PLE (Piattaforma Elevabile) | Piattaforma di lavoro elevabile conforme a norme specifiche |
| APP-BARRIERE | Barriere di delimitazione | Recinzione/nastro per delimitare area di lavoro |

---

## 6. Matrice Relazionale Fase → Rischi → DPI

Questa e la tabella che l'AI usa per ragionare:

```
FL-001 Scarico materiali
  └── RS-MMC ──── DPI-GUANTI-CROSTA, DPI-SCARPE + MIS-AUSILI-MECCANICI
  └── RS-INVESTIMENTO ──── DPI-GILET-AV, DPI-SCARPE, DPI-CASCO + MIS-PERCORSI-SEGNALATI
  └── RS-SCHIACCIAMENTO ──── DPI-SCARPE, DPI-GUANTI-CROSTA, DPI-CASCO

FL-006 Saldatura
  └── RS-RADIAZIONI-UV ──── DPI-SCHERMO-SALD, DPI-TUTA + MIS-SCHERMATURA-AREA
  └── RS-FUMI ──── DPI-MASCHERA, DPI-TUTA + MIS-ASPIRAZIONE-FUMI
  └── RS-USTIONI ──── DPI-GUANTI-CALORE, DPI-TUTA, DPI-SCARPE
  └── RS-INCENDIO ──── APP-ESTINTORE + MIS-ALLONTANARE-INFIAMMABILI

FL-008 Montaggio strutture
  └── RS-CADUTA-ALTO ──── DPI-CASCO, DPI-CINTURA, DPI-SCARPE + APP-PONTEGGIO, APP-LINEAVITA
  └── RS-CADUTA-MATERIALI ──── DPI-CASCO, DPI-SCARPE + APP-RETI-PROTEZIONE
  └── RS-URTI ──── DPI-CASCO, DPI-GUANTI-CROSTA, DPI-SCARPE
  └── RS-SCHIACCIAMENTO ──── DPI-SCARPE, DPI-GUANTI-CROSTA, DPI-CASCO
```

---

## 7. Come il Motore AI usa i 3 livelli

### Flusso logico:

```
1. AI legge dati commessa (istruttoria, segmentazione, preventivo)
2. AI matcha trigger.keywords delle FASI con il contesto della commessa
3. Per ogni fase attivata, raccoglie i rischi_ids
4. Per ogni rischio, raccoglie dpi_ids + apprestamenti_ids + misure
5. Deduplica DPI/misure (un DPI appare una sola volta anche se richiesto da 3 rischi)
6. Classifica ogni elemento come: dedotto | incerto | mancante
7. Genera domande_verifica dai rischi incerti
8. Output strutturato pronto per precompilare la scheda cantiere
```

### Esempio concreto:

**Input**: Commessa "Fornitura e posa struttura metallica capannone industriale - Verona"
- Istruttoria: acciaio S355, saldatura MIG, EXC2
- Segmentazione: EN 1090 + montaggio previsto
- Preventivo: include voci "montaggio cantiere", "verniciatura"

**AI ragiona**:
1. **FL-008 Montaggio** → dedotto (da "montaggio cantiere" nel preventivo)
2. **FL-006 Saldatura** → dedotto (da istruttoria: saldatura MIG)
3. **FL-003 Taglio profili** → dedotto (carpenteria metallica standard)
4. **FL-007 Verniciatura** → dedotto (da voce preventivo)
5. **FL-009 Sollevamento** → incerto (probabile per montaggio capannone, da confermare)
6. **FL-001 Scarico materiali** → dedotto (sempre presente in cantiere)

**Rischi attivati**: RS-CADUTA-ALTO, RS-RADIAZIONI-UV, RS-FUMI, RS-PROIEZIONE, RS-CHIMICO, RS-CADUTA-MATERIALI, ...
**DPI raccolti** (deduplicati): Casco, Cintura, Scarpe, Schermo saldatura, Maschera, Occhiali, ...
**Apprestamenti**: Ponteggio/trabattello, Estintore, Aspirazione fumi, ...

**Domande residue**:
1. Sono previsti lavori in quota > 2m? → per confermare RS-CADUTA-ALTO
2. E previsto l'uso di autogrù o carroponte? → per confermare FL-009
3. Sono previste saldature in opera (non solo officina)? → per RS-INCENDIO in cantiere
4. Il cantiere e in area con interferenze (altri lavori)? → per RS-INVESTIMENTO
5. Sono previsti subappalti? → per documentazione aggiuntiva

---

## 8. Differenze dal Modello Attuale

| Aspetto | Modello attuale (v1) | Modello proposto (v2) |
|---------|---------------------|----------------------|
| Collezioni | 1 (`libreria_rischi`) | 3 (`lib_fasi_lavoro`, `lib_rischi_sicurezza`, `lib_dpi_misure`) |
| Rischi | Annidati dentro le fasi | Entita indipendenti con codice proprio |
| DPI | Lista di codici nelle fasi | Entita indipendenti con norma, tipo, obbligatorieta |
| Misure | Stringhe nelle fasi | Entita indipendenti, referenziabili |
| Relazioni | Implicite (embedded) | Esplicite (tramite `_ids[]`) |
| Trigger AI | Nessuno | Keywords + condizioni per fase e rischio |
| Domande | Nessuna | `domande_verifica[]` per rischio |
| Valutazione | Dentro il rischio embedded | Campo `valutazione_default` con P, D, Classe |

---

## 9. Indici MongoDB

```javascript
// lib_fasi_lavoro
db.lib_fasi_lavoro.createIndex({ user_id: 1, codice: 1 }, { unique: true })
db.lib_fasi_lavoro.createIndex({ user_id: 1, categoria: 1 })

// lib_rischi_sicurezza
db.lib_rischi_sicurezza.createIndex({ user_id: 1, codice: 1 }, { unique: true })
db.lib_rischi_sicurezza.createIndex({ user_id: 1, categoria: 1, sottocategoria: 1 })

// lib_dpi_misure
db.lib_dpi_misure.createIndex({ user_id: 1, codice: 1 }, { unique: true })
db.lib_dpi_misure.createIndex({ user_id: 1, tipo: 1 })
```

---

## 10. Impatto su `cantieri_sicurezza`

Il campo `fasi_lavoro_selezionate` nella scheda cantiere cambia da:

**PRIMA (v1)**:
```json
{
  "fasi_lavoro_selezionate": [
    {
      "fase_id": "FL-001",
      "nome_fase": "Taglio...",
      "rischi_valutati": [{ embedded }],
      "dpi_richiesti": ["DPI-..."]
    }
  ]
}
```

**DOPO (v2)**:
```json
{
  "fasi_lavoro_selezionate": [
    {
      "fase_codice": "FL-003",
      "confidenza": "dedotto",
      "rischi_attivati": [
        {
          "rischio_codice": "RS-PROIEZIONE",
          "confidenza": "dedotto",
          "valutazione_override": null
        }
      ],
      "note_utente": ""
    }
  ],
  "dpi_calcolati": ["DPI-CASCO", "DPI-OCCHIALI", "DPI-GUANTI-CROSTA", ...],
  "apprestamenti_calcolati": ["APP-ESTINTORE", ...],
  "misure_calcolate": ["MIS-VALUTAZIONE-RUMORE", ...],
  "domande_residue": [
    {
      "testo": "Sono previsti lavori in quota > 2m?",
      "origine_rischio": "RS-CADUTA-ALTO",
      "risposta": null,
      "stato": "aperta"
    }
  ]
}
```

---

## 11. Prossimi Passi (dopo approvazione)

1. **Refactor backend**: Creare le 3 collezioni, migrare il seed, aggiornare gli endpoint
2. **Refactor frontend**: Aggiornare SchedaCantierePage Step 2 per mostrare la catena Fase→Rischi→DPI
3. **Motore AI**: Implementare l'endpoint `ai-precompila` che usa trigger + dati commessa
4. **DOCX**: Generare il documento usando i 3 livelli come fonte dati strutturata

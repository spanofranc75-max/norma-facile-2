# SPEC_LIBRERIA_RISCHI_3_LIVELLI.md
## Modello Libreria Sicurezza a 3 Livelli — NormaFacile 2.0

**Data**: 2026-03-23  |  **Versione**: 2.0 — DEFINITIVA (con 7 integrazioni utente)

---

## 1. Principio Architetturale

```
FASE LAVORATIVA ──attiva──> RISCHIO SICUREZZA ──richiede──> DPI / MISURA / APPRESTAMENTO
     (cosa fai)              (cosa puoi subire)              (come ti proteggi)
```

Relazione **many-to-many** gestita tramite array di codici.

---

## 2. Collezione 1: `lib_fasi_lavoro`

```json
{
  "codice": "FL-001",
  "user_id": "string",
  "nome": "Scarico e movimentazione materiali",
  "descrizione": "Scarico materiali dal mezzo di trasporto e movimentazione in area cantiere",
  "categoria": "movimentazione",
  "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],

  "trigger": {
    "keywords": ["scarico", "movimentazione", "trasporto", "consegna"],
    "contesto": ["cantiere"]
  },
  "condizioni_esclusione": ["solo_officina"],

  "rischi_ids": ["RS-MMC", "RS-INVESTIMENTO", "RS-SCHIACCIAMENTO"],
  "macchine_tipiche": ["Carrello elevatore", "Carroponte", "Transpallet"],

  "active": true,
  "version": 1,
  "source": "seed",
  "sort_order": 10,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 3. Collezione 2: `lib_rischi_sicurezza`

```json
{
  "codice": "RS-CADUTA-ALTO",
  "user_id": "string",
  "nome": "Caduta dall'alto",
  "categoria": "sicurezza",
  "sottocategoria": "cadute",
  "descrizione_breve": "Rischio di caduta da altezza superiore a 2 metri",

  "trigger": {
    "keywords": ["quota", "altezza", "ponteggio", "trabattello", "copertura", "tetto"],
    "condizioni": ["montaggio_cantiere", "lavori_quota"]
  },
  "condizioni_esclusione": ["solo_lavorazioni_a_terra", "altezza_inferiore_2m"],

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
  "note_pos_template": "Valutare necessita di piano di montaggio ponteggio (Pi.M.U.S.)",

  "dpi_ids": ["DPI-CASCO", "DPI-CINTURA", "DPI-SCARPE"],
  "misure_ids": [],
  "apprestamenti_ids": ["APP-PONTEGGIO", "APP-TRABATTELLO", "APP-PARAPETTI", "APP-LINEAVITA"],

  "documenti_richiesti": [
    { "codice": "DOC-FORMAZIONE-QUOTA", "nome": "Attestato formazione lavori in quota", "obbligatorio": true, "condizione": null },
    { "codice": "DOC-IDONEITA", "nome": "Idoneita sanitaria", "obbligatorio": true, "condizione": null },
    { "codice": "DOC-PIMUS", "nome": "Pi.M.U.S.", "obbligatorio": false, "condizione": "uso_ponteggio" }
  ],

  "domande_verifica": [
    { "testo": "Sono previsti lavori ad altezza superiore a 2 m?", "impatto": "alto", "gate_critical": true },
    { "testo": "Quale sistema anticaduta e previsto?", "impatto": "alto", "gate_critical": true }
  ],

  "rif_normativo": "D.Lgs. 81/08 Titolo IV Capo II",
  "gate_critical": true,

  "active": true,
  "version": 1,
  "source": "seed",
  "sort_order": 10,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 4. Collezione 3: `lib_dpi_misure`

```json
{
  "codice": "DPI-CASCO",
  "user_id": "string",
  "nome": "Casco protettivo",
  "tipo": "dpi",
  "sottotipo": "protezione_capo",
  "descrizione": "Casco di protezione per il capo contro la caduta di oggetti e urti",
  "rif_normativo": "UNI EN 397 - Art 75-77-78 D.Lgs 81/08",
  "obbligatorieta": "sempre",
  "condizioni": [],

  "active": true,
  "version": 1,
  "source": "seed",
  "sort_order": 10,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Valori `tipo`:  `dpi | misura | apprestamento`
### Valori `obbligatorieta`:  `sempre | condizionale | raccomandato`

---

## 5. Seed Data MVP

### 5.1 Fasi di Lavoro (11)

| Codice | Nome | Categoria | Contesto | Rischi |
|--------|------|-----------|----------|--------|
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

### 5.2 Rischi Sicurezza (18)

| Codice | Nome | Cat. | Sotto | P | D | Classe | gate_critical | DPI | Misure | Appr. |
|--------|------|------|-------|---|---|--------|---------------|-----|--------|-------|
| RS-CADUTA-ALTO | Caduta dall'alto | sicurezza | cadute | MedioAlta | Ingente | Gravissimo | true | CASCO,CINTURA,SCARPE | — | PONTEGGIO,TRABATTELLO,PARAPETTI,LINEAVITA |
| RS-CADUTA-MAT | Caduta materiali dall'alto | sicurezza | cadute | MedioAlta | Notevole | Grave | true | CASCO,SCARPE | — | RETI-PROTEZIONE |
| RS-URTI | Urti, colpi, impatti | sicurezza | meccanico | MedioAlta | Modesta | Modesto | false | CASCO,GUANTI-CROSTA,SCARPE | — | — |
| RS-SCHIACCIAMENTO | Schiacciamento | sicurezza | meccanico | MedioBassa | Ingente | Grave | true | SCARPE,GUANTI-CROSTA,CASCO | — | — |
| RS-CESOIAMENTO | Cesoiamento | sicurezza | meccanico | MedioBassa | Ingente | Grave | false | GUANTI-CROSTA,SCARPE | — | — |
| RS-PROIEZIONE | Proiezione schegge/detriti | sicurezza | meccanico | MedioAlta | Notevole | Grave | false | OCCHIALI,GUANTI-CROSTA,TUTA | — | — |
| RS-TAGLI | Tagli e abrasioni | sicurezza | meccanico | MedioAlta | Modesta | Modesto | false | GUANTI-CROSTA,TUTA | — | — |
| RS-IMPIGLIAMENTO | Impigliamento | sicurezza | meccanico | MedioBassa | Notevole | Modesto | false | TUTA | INDUMENTI-ADERENTI | — |
| RS-RUMORE | Rumore | salute | fisico | Elevata | Modesta | Grave | false | CUFFIE | VALUTAZIONE-RUMORE | — |
| RS-VIBRAZIONI | Vibrazioni meccaniche | salute | fisico | MedioAlta | Modesta | Modesto | false | GUANTI-CROSTA | VALUTAZIONE-VIBRAZIONI | — |
| RS-RADIAZIONI-UV | Radiazioni UV/IR | salute | fisico | Elevata | Notevole | Gravissimo | true | SCHERMO-SALD,TUTA | SCHERMATURA-AREA | — |
| RS-FUMI | Fumi saldatura/polveri | salute | chimico | Elevata | Notevole | Gravissimo | true | MASCHERA,TUTA | ASPIRAZIONE-FUMI | — |
| RS-CHIMICO | Rischio chimico | salute | chimico | MedioAlta | Notevole | Grave | false | MASCHERA,GUANTI-CROSTA,OCCHIALI,TUTA | VENTILAZIONE-FORZATA | — |
| RS-INALAZIONE | Inalazione vapori | salute | chimico | MedioAlta | Notevole | Grave | false | MASCHERA | VENTILAZIONE-FORZATA | — |
| RS-ELETTRICO | Rischio elettrico | sicurezza | elettrico | MedioBassa | Ingente | Grave | true | GUANTI-ISOLANTI,SCARPE | SEZIONAMENTO-LINEA | — |
| RS-INCENDIO | Incendio/esplosione | sicurezza | incendio | MedioBassa | Ingente | Grave | true | — | ALLONTANARE-INFIAMMABILI | ESTINTORE |
| RS-INVESTIMENTO | Investimento da mezzi | sicurezza | meccanico | MedioBassa | Ingente | Grave | true | GILET-AV,SCARPE,CASCO | PERCORSI-SEGNALATI | — |
| RS-RIBALTAMENTO | Ribaltamento mezzo | sicurezza | meccanico | Bassa | Ingente | Grave | true | CASCO | VERIFICA-PORTATA | — |
| RS-MMC | Movimentazione manuale carichi | salute | ergonomico | MedioAlta | Modesta | Modesto | false | GUANTI-CROSTA,SCARPE | AUSILI-MECCANICI | — |
| RS-USTIONI | Ustioni | sicurezza | termico | MedioAlta | Modesta | Modesto | false | GUANTI-CALORE,TUTA,SCARPE | — | — |

### 5.3 DPI (12) + Misure (11) + Apprestamenti (8) = 31

#### DPI
| Codice | Nome | Sottotipo | Norma | Obbl. |
|--------|------|-----------|-------|-------|
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

#### Misure organizzative
| Codice | Nome |
|--------|------|
| MIS-INDUMENTI-ADERENTI | Indumenti aderenti obbligatori |
| MIS-VALUTAZIONE-RUMORE | Valutazione rischio rumore allegata |
| MIS-VALUTAZIONE-VIBRAZIONI | Valutazione rischio vibrazioni allegata |
| MIS-SCHERMATURA-AREA | Schermatura area saldatura |
| MIS-ASPIRAZIONE-FUMI | Aspirazione localizzata fumi |
| MIS-VENTILAZIONE-FORZATA | Ventilazione forzata area |
| MIS-SEZIONAMENTO-LINEA | Sezionamento e verifica assenza tensione |
| MIS-ALLONTANARE-INFIAMMABILI | Allontanamento materiali infiammabili |
| MIS-PERCORSI-SEGNALATI | Percorsi obbligati e segnalati |
| MIS-AUSILI-MECCANICI | Utilizzo ausili meccanici per carichi > 25 kg |
| MIS-VERIFICA-PORTATA | Verifica portata terreno e mezzo |

#### Apprestamenti
| Codice | Nome |
|--------|------|
| APP-PONTEGGIO | Ponteggio regolamentare |
| APP-TRABATTELLO | Trabattello UNI EN 1004 |
| APP-PARAPETTI | Parapetti provvisori |
| APP-LINEAVITA | Linea vita UNI EN 795 |
| APP-RETI-PROTEZIONE | Reti di protezione |
| APP-ESTINTORE | Estintore |
| APP-PLE | PLE (Piattaforma Elevabile) |
| APP-BARRIERE | Barriere di delimitazione |

---

## 6. Schema istanziato in `cantieri_sicurezza`

Quando l'AI (o l'utente) attiva fasi/rischi, nella scheda cantiere si salva:

```json
{
  "fasi_lavoro_selezionate": [
    {
      "fase_codice": "FL-008",
      "confidence": "dedotto",
      "origin": "ai",
      "reasoning": "Rilevato 'montaggio cantiere' nel preventivo e segmentazione EN 1090",
      "source_refs": ["preventivo.voce_3", "istruttoria.segmentazione"],
      "overridden_by_user": false,
      "rischi_attivati": [
        {
          "rischio_codice": "RS-CADUTA-ALTO",
          "confidence": "incerto",
          "origin": "ai",
          "reasoning": "Montaggio strutture implica possibile lavoro in quota, da confermare altezza",
          "valutazione_override": null,
          "overridden_by_user": false
        }
      ],
      "note_utente": ""
    }
  ],
  "dpi_calcolati": [
    { "codice": "DPI-CASCO", "origin": "rules", "da_rischi": ["RS-CADUTA-ALTO", "RS-URTI"] }
  ],
  "misure_calcolate": [
    { "codice": "MIS-VALUTAZIONE-RUMORE", "origin": "rules", "da_rischi": ["RS-RUMORE"] }
  ],
  "apprestamenti_calcolati": [
    { "codice": "APP-PONTEGGIO", "origin": "ai", "da_rischi": ["RS-CADUTA-ALTO"], "confidence": "incerto" }
  ],
  "domande_residue": [
    {
      "testo": "Sono previsti lavori ad altezza superiore a 2 m?",
      "origine_rischio": "RS-CADUTA-ALTO",
      "impatto": "alto",
      "gate_critical": true,
      "risposta": null,
      "stato": "aperta"
    }
  ]
}
```

---

## 7. Le 7 integrazioni applicate

| # | Integrazione | Dove applicata |
|---|-------------|----------------|
| 1 | Campi governance (active, version, source, sort_order, timestamps) | Tutte e 3 le collezioni |
| 2 | `documenti_richiesti[]` con obbligatorieta e condizione | `lib_rischi_sicurezza` |
| 3 | Separazione netta `dpi_ids[]`, `misure_ids[]`, `apprestamenti_ids[]` | `lib_rischi_sicurezza` |
| 4 | `condizioni_esclusione[]` | `lib_fasi_lavoro` e `lib_rischi_sicurezza` |
| 5 | `impatto` (alto/medio/basso) + `gate_critical` su domande | `domande_verifica[]` nei rischi |
| 6 | `origin`, `reasoning`, `source_refs`, `confidence`, `overridden_by_user` | Schema istanziato in `cantieri_sicurezza` |
| 7 | `gate_critical` a livello rischio | `lib_rischi_sicurezza` + `domande_residue` nel cantiere |

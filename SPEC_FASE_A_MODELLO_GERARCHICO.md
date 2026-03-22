# Mini-Specifica Tecnica — Fase A: Modello Gerarchico Commessa

> Documento vincolante per lo sviluppo. Da approvare prima del coding.

---

## 1. ENTITA

### 1A. Commessa Madre (`commesse` — collezione esistente)
La commessa commerciale/operativa. Resta com'e. Nessuna modifica strutturale.
Rappresenta il "fascicolo di cantiere" nel suo insieme.

```json
{
  "commessa_id": "com_abc123",
  "numero": "NF-2026-000125",
  "title": "Lavori Bianchi - Capannone + Cancello",
  "client_id": "...",
  "normativa_tipo": "EN_1090",
  "stato": "firmato",
  "...": "campi esistenti invariati"
}
```

**Nota:** Il campo `normativa_tipo` della commessa madre diventa informativo (tipo "prevalente" o "originale"). La vera separazione normativa avviene nei rami.

---

### 1B. Ramo Normativo (`commesse_normative` — NUOVA collezione)
Separa i flussi normativi distinti dentro la stessa commessa madre.
Ogni ramo ha le sue evidenze, i suoi controlli, la sua tracciabilita.

```json
{
  "ramo_id": "ramo_a1b2c3",
  "commessa_id": "com_abc123",
  "user_id": "user_xxx",

  "normativa": "EN_1090",
  "codice_ramo": "NF-2026-000125-1090",

  "commessa_base_code": "NF-2026-000125",
  "branch_type": "EN_1090",

  "line_ids": ["r1", "r2", "r5"],

  "status": "attivo",
  "created_at": "2026-...",
  "created_from": "segmentazione_confermata",
  "istruttoria_id": "istr_xxx"
}
```

**Valori `normativa`:** `EN_1090`, `EN_13241`, `GENERICA`
**Valori `status`:** `attivo`, `completato`, `sospeso`
**Max 1 ramo per normativa per commessa madre** (non duplicati)

---

### 1C. Emissione Documentale (`emissioni_documentali` — NUOVA collezione)
Rappresenta una singola emissione (DOP, CE, certificazione) dentro un ramo normativo.
Puo essere creata solo quando ci sono presupposti reali.

```json
{
  "emissione_id": "em_x1y2z3",
  "ramo_id": "ramo_a1b2c3",
  "commessa_id": "com_abc123",
  "user_id": "user_xxx",

  "codice_emissione": "NF-2026-000125-1090-D01",

  "commessa_base_code": "NF-2026-000125",
  "branch_type": "EN_1090",
  "emission_type": "DOP",
  "emission_seq": 1,

  "stato": "draft",
  "descrizione": "Prima fornitura - Travi HEB200",

  "material_batch_ids": ["b1", "b2"],
  "ddt_ids": ["ddt_44"],
  "element_ids": ["el_1", "el_2"],
  "voce_ids": ["voce_abc"],

  "evidence_gate": {
    "emittable": false,
    "checked_at": "2026-...",
    "blocking_reasons": [
      "Manca certificato 3.1 per batch b2"
    ],
    "checks": {
      "certificati_31": false,
      "wps_wpqr": true,
      "riesame_tecnico": true,
      "controllo_finale": false
    }
  },

  "created_at": "2026-...",
  "emessa_il": null,
  "emessa_da": null
}
```

**Valori `stato`:** `draft`, `in_preparazione`, `pronta`, `emessa`, `annullata`
**Valori `emission_type`:**
- EN 1090: `DOP` (suffisso `-D`)
- EN 13241: `CE` (suffisso `-C`)
- GENERICA: `LOT` (suffisso `-L`, solo se serve)

---

### 1D. Voci di Lavoro (`voci_lavoro` — COLLEZIONE ESISTENTE, aggiornamento minimo)
Aggiunta di un campo opzionale `ramo_id` per collegare la voce al ramo normativo.

```json
{
  "voce_id": "voce_abc123",
  "commessa_id": "com_xyz789",
  "ramo_id": "ramo_a1b2c3",
  "...": "campi esistenti invariati"
}
```

**Retrocompatibilita:** Se `ramo_id` e null/assente, la voce funziona come prima.

---

## 2. CHIAVI E RELAZIONI

```
commesse (1)
  |
  +--< commesse_normative (N, max 3: uno per EN_1090, EN_13241, GENERICA)
  |     |
  |     +--< emissioni_documentali (N per ramo)
  |     |
  |     +--< voci_lavoro (N, link opzionale via ramo_id)
  |
  +--< voci_lavoro (N, link diretto via commessa_id — retrocompatibile)
```

### Indici DB necessari
- `commesse_normative`: unique(`commessa_id`, `normativa`, `user_id`)
- `emissioni_documentali`: unique(`ramo_id`, `emission_seq`, `user_id`)
- `emissioni_documentali`: index(`commessa_id`)

### Link a entita esistenti
- `material_batch_ids` → `material_batches.batch_id`
- `ddt_ids` → `ddt` collection
- `element_ids` → elementi specifici dentro la voce/commessa
- `istruttoria_id` → `istruttorie.istruttoria_id`

---

## 3. NUMERAZIONE

### Regola base
Il numero della commessa madre resta invariato: `NF-YYYY-NNNNNN`

### Codice ramo
`{numero_commessa}-{suffisso_normativa}`

| Normativa | Suffisso |
|-----------|----------|
| EN_1090   | `-1090`  |
| EN_13241  | `-13241` |
| GENERICA  | `-GEN`   |

Esempio: `NF-2026-000125-1090`

### Codice emissione
`{codice_ramo}-{tipo}{progressivo_2cifre}`

| Normativa | Tipo emissione | Prefisso |
|-----------|---------------|----------|
| EN_1090   | DOP           | `D`      |
| EN_13241  | CE            | `C`      |
| GENERICA  | LOT (opz.)    | `L`      |

Esempio: `NF-2026-000125-1090-D01`, `NF-2026-000125-13241-C01`

### Campi strutturali (non parsing di stringhe)
Ogni entita mantiene campi separati per evitare parsing:
- `commessa_base_code`: `NF-2026-000125`
- `branch_type`: `EN_1090`
- `emission_type`: `DOP`
- `emission_seq`: `1`
- `codice_ramo` / `codice_emissione`: stringa leggibile (calcolata, non unica chiave logica)

---

## 4. REGOLE DI CREAZIONE

### 4A. Quando nasce un ramo normativo
**Trigger automatici (da Phase 2 — segmentazione confermata):**
- Dopo conferma istruttoria + segmentazione confermata
- Il sistema crea 1 ramo per ogni normativa presente nella segmentazione

**Trigger manuale:**
- L'utente crea un ramo esplicitamente dalla UI della commessa

**Regole:**
- Max 1 ramo per normativa per commessa (non duplicati)
- Se la commessa e "pura" (solo EN_1090): 1 solo ramo
- Se mista (segmentazione): N rami, uno per normativa trovata
- Le righe (`line_ids`) vengono assegnate automaticamente dalla segmentazione

### 4B. Quando nasce un'emissione
**NON automaticamente dalla Phase 2.**

**Trigger per creazione:**
1. L'utente clicca "Nuova emissione" nel ramo
2. Il sistema rileva un set di batch/DDT/elementi pronti (suggerimento)
3. Il progressivo e calcolato atomicamente (counter per ramo)

**Regole:**
- L'emissione nasce in stato `draft`
- L'Evidence Gate viene calcolato on-demand (ogni volta che si apre o si chiede "posso emettere?")
- L'emissione diventa `emessa` solo quando l'Evidence Gate dice `emittable: true` E l'utente conferma

### 4C. Quando si blocca un'emissione
L'Evidence Gate calcola `emittable: false` quando mancano evidenze obbligatorie.
Le regole specifiche (Fase B) dipendono dal tipo di normativa:

**EN 1090 — Evidenze obbligatorie per emissione DOP:**
- Certificati 3.1 per ogni batch materiale assegnato
- WPS/WPQR validi per saldature
- Riesame Tecnico completato
- Controllo Finale approvato
- Tracciabilita colata completa

**EN 13241 — Evidenze obbligatorie per emissione CE:**
- Verifiche sicurezza (fotocellule, coste, collaudo forze)
- Documentazione tecnica completa
- Manuale d'Uso compilato

**GENERICA:**
- Nessuna emissione normativa richiesta di default
- Solo riepilogo costi/ore (emissione `LOT` opzionale)

---

## 5. RETROCOMPATIBILITA

### Principio
**Nuovo modello subito per nuove commesse. Legacy gestito con wrapping logico, non migrazione massiva.**

### Strategia: Wrapping Logico per commesse esistenti

Quando si accede a una commessa esistente (pre-modello gerarchico):
1. Se `commesse_normative` non ha record per quella `commessa_id`:
   - La commessa funziona ESATTAMENTE come prima
   - Il campo `normativa_tipo` della commessa madre vale come "ramo implicito"
   - Nessun ramo creato in DB finche l'utente non agisce esplicitamente
2. Se l'utente vuole generare documenti normativi su una commessa legacy:
   - Il sistema crea il ramo normativo coerente (lazy on-access)
   - Crea una prima emissione `draft` se richiesto

### Cosa NON fare
- Non migrare tutte le commesse
- Non riscrivere ID storici
- Non forzare la creazione di rami su commesse gia chiuse

### Compatibilita codice
- Tutti gli endpoint esistenti (`/api/commesse/*`) funzionano invariati
- I nuovi endpoint (`/api/commesse-normative/*`, `/api/emissioni/*`) sono addizionali
- Il frontend aggiunge sezioni SOLO quando esistono rami nel DB

---

## 6. ENDPOINT API (Fase A)

### Rami Normativi
```
GET    /api/commesse-normative/{commessa_id}              → lista rami
POST   /api/commesse-normative/{commessa_id}              → crea ramo manuale
GET    /api/commesse-normative/{commessa_id}/{ramo_id}    → dettaglio ramo
POST   /api/commesse-normative/genera-da-istruttoria/{preventivo_id}  → auto-genera rami da segmentazione
```

### Emissioni Documentali
```
GET    /api/emissioni/{ramo_id}                           → lista emissioni del ramo
POST   /api/emissioni/{ramo_id}                           → crea nuova emissione
GET    /api/emissioni/{ramo_id}/{emissione_id}            → dettaglio emissione
PATCH  /api/emissioni/{ramo_id}/{emissione_id}            → aggiorna (descrizione, batch, ddt)
GET    /api/emissioni/{ramo_id}/{emissione_id}/gate       → check Evidence Gate
POST   /api/emissioni/{ramo_id}/{emissione_id}/emetti     → emetti (se gate OK)
```

### Vista aggregata (per Dashboard)
```
GET    /api/commesse/{commessa_id}/gerarchia              → commessa + rami + emissioni (vista completa)
```

---

## 7. CRITERI DI TEST (Fase A)

### Backend
1. Creazione manuale ramo per commessa esistente → OK, codice generato correttamente
2. Creazione ramo duplicato (stessa normativa) → 409 Conflict
3. Auto-generazione rami da istruttoria confermata con segmentazione → N rami creati
4. Creazione emissione dentro ramo → progressivo corretto (D01, D02, ...)
5. Vista gerarchia → commessa + rami + emissioni annidati
6. Commessa legacy senza rami → endpoint esistenti funzionano invariati

### Frontend
7. Card rami normativi visibile nella pagina commessa (solo se rami esistono)
8. Creazione emissione da UI → form minimale
9. Vista gerarchia: commessa madre → rami → emissioni con contatori

---

## SEQUENZA DI IMPLEMENTAZIONE

1. **DB + Models**: Collezioni `commesse_normative` e `emissioni_documentali` con indici
2. **Backend CRUD rami**: 4 endpoint + logica numerazione
3. **Backend auto-genera rami**: Endpoint che legge segmentazione confermata e crea rami
4. **Backend CRUD emissioni**: 6 endpoint + counter atomico
5. **Backend vista gerarchia**: Endpoint aggregato
6. **Frontend CommessaHubPage**: Sezione rami normativi + emissioni
7. **Retrocompatibilita**: Test su commesse legacy senza rami

---

*Spec pronta per review. Nessun codice scritto fino ad approvazione.*

# CLEANUP LIST — NormaFacile 2.0

> Lista secca di file, codice e risorse da eliminare o ristrutturare

---

## 1. FILE DA ELIMINARE (DEAD CODE)

### 1.1 Backend Routes — Orfane (non registrate in main.py)

```
ELIMINARE:
  /app/backend/routes/approvvigionamento.py        (515 righe)
  /app/backend/routes/consegne_ops.py               (584 righe)
  /app/backend/routes/conto_lavoro.py               (499 righe)
  /app/backend/routes/documenti_ops.py              (1387 righe)
  /app/backend/routes/produzione_ops.py             (108 righe)
  /app/backend/routes/commessa_ops_common.py        (95 righe)
```

**Totale: ~3.188 righe di dead code**

**Motivo**: Questi file non sono mai stati importati in `main.py`. Definiscono router mai montati. Le loro funzionalita sono state probabilmente migrate/duplicate in `commessa_ops.py` e sub-moduli attivi. `commessa_ops_common.py` e un helper usato SOLO da questi 5 file orfani.

**Verifica prima della cancellazione**: Controllare che nessuna delle funzionalita specifiche (RdP, OdA, consegne, documenti commessa, fasi produzione) sia andata persa nella migrazione.

### 1.2 Backend Services — Orfane

```
ELIMINARE:
  /app/backend/services/aruba_sdi.py                (~250 righe)
  /app/backend/services/pos_pdf_service.py          (~200 righe)
```

**Motivo**: `aruba_sdi.py` non e importato da nessun file. `pos_pdf_service.py` e stato sostituito da `pos_docx_generator.py`.

### 1.3 File Root — Legacy/Orfani

```
ELIMINARE:
  /app/backend_test.py                              (file test orfano)
  /app/auth_testing.md                              (doc testing obsoleta)
  /app/image_testing.md                             (doc testing obsoleta)
  /app/test_result.md                               (risultato test storico)
  /app/yarn.lock                                    (duplicato di frontend/yarn.lock)
```

### 1.4 Directory Vuote

```
ELIMINARE:
  /app/DoP/
  /app/Documenti/
  /app/Emissione/
  /app/Emissioni/
  /app/Evidence/
  /app/Gestione/
  /app/Rami/
  /app/Ramo/
  /app/Send/
```

**Motivo**: 9 directory completamente vuote. Probabilmente create durante test manuali o prototipi mai completati.

---

## 2. CODICE DA CORREGGERE IN FILE ATTIVI

### 2.1 main.py — Import duplicato sicurezza

```python
# RIGA 28 e 76: import duplicato
from routes.sicurezza import router as sicurezza_router   # riga 28
from routes.sicurezza import router as sicurezza_router   # riga 76 DUPLICATO

# RIGA 168 e 216: router registrato 2 volte
app.include_router(sicurezza_router, prefix="/api")       # riga 168
app.include_router(sicurezza_router, prefix="/api")       # riga 216 DUPLICATO
```

**Azione**: Rimuovere la seconda importazione (riga 76) e la seconda registrazione (riga 216).

### 2.2 main.py — FPC prefix inconsistente

```python
# Riga 182: FPC e l'UNICO router senza prefix="/api"
app.include_router(fpc_router)

# Ma in fpc.py:
router = APIRouter(prefix="/api/fpc", tags=["FPC - EN 1090"])
```

**Azione**: Allineare con tutti gli altri router. Cambiare prefix in `fpc.py` a `/fpc` e aggiungere `prefix="/api"` in main.py.

### 2.3 main.py — Conflitto lifespan + on_event

```python
# Riga 108-125: lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...

# Riga 241-317: on_event("startup") — NON VIENE ESEGUITO!
@app.on_event("startup")
async def startup_event():
    # Tutto il codice qui dentro (migrazione utenti + creazione indici)
    # NON viene eseguito perche lifespan ha la precedenza
```

**Azione**: Spostare TUTTO il contenuto di `startup_event()` dentro il `lifespan` context manager (prima del `yield`).

### 2.4 obblighi_auto_sync.py — Variabile dichiarata 2 volte

```python
# Riga ~20 e ~49: _last_sync dichiarato due volte
_last_sync: dict[str, float] = {}    # prima volta
DEBOUNCE_SECONDS = 5.0

# ... funzione resolve_commessa_from_preventivo ...

_last_sync: dict[str, float] = {}    # seconda volta DUPLICATA
DEBOUNCE_SECONDS = 5.0
```

**Azione**: Rimuovere la seconda dichiarazione.

---

## 3. COLLEZIONI DB ZOMBIE (da eliminare o verificare)

| Collezione | Doc | Azione |
|------------|-----|--------|
| `articoli_perizia` | 14 | ELIMINARE - Non referenziata |
| `catalogo_profili` | 0 | ELIMINARE - Vuota, non referenziata |
| `download_tokens` | 44 | VERIFICARE - Token temporanei, serve cleanup job? |
| `magazzino_sfridi` | 1 | VERIFICARE - Il codice usa `sfridi`? |
| `officina_alerts` | 2 | ELIMINARE - Non referenziata |
| `officina_timers` | 3 | ELIMINARE - Non referenziata |
| `rdp_requests` | 0 | ELIMINARE - Vuota, non referenziata |
| `registro_nc` | 2 | VERIFICARE - Il codice usa `non_conformities`? |
| `sessions` | 3 | VERIFICARE - Possibile duplicato di `user_sessions` |
| `targhe_ce` | 1 | ELIMINARE - Non referenziata |
| `project_costs` | 66 | VERIFICARE - 66 doc, ma non referenziata da codice attivo |

---

## 4. DOCUMENTI SPEC DA ARCHIVIARE

Questi file root sono spec storiche per funzionalita gia completate. Non piu necessari per lo sviluppo attivo.

```
ARCHIVIARE in /app/memory/specs/:
  /app/ARCHITETTURA_TECNICA.md
  /app/PROJECT_KNOWLEDGE.md
  /app/PROJECT_MANIFESTO.md
  /app/REPORT_EVOLUZIONE.md
  /app/SPEC_FASE_A_MODELLO_GERARCHICO.md
  /app/SPEC_LIBRERIA_RISCHI_3_LIVELLI.md
  /app/SPEC_PACCHETTI_DOCUMENTALI.md
  /app/SPEC_POS_RENDERING_MAP.md
  /app/SPEC_POS_TEMPLATE_MAPPING.md
```

---

## 5. TEST FILE POTENZIALMENTE OBSOLETI

Con 232 file di test e ~97.000 righe, molti test sono probabilmente obsoleti o ridondanti. Una pulizia progressiva e consigliata:

**Criteri per identificazione**:
- Test che referenziano endpoint non piu esistenti
- Test con naming `test_iteration_XXX` dove la funzionalita e stata gia refactorata
- Test duplicati che coprono la stessa funzionalita

**Stima**: Almeno 30-40% dei test file (70-90 file) potrebbe essere obsoleto o ridondante.

---

## 6. IMPORT SUPERFLUI (SPOT CHECK)

Da verificare sistematicamente con un linter:

```bash
# Eseguire per trovare import inutilizzati
cd /app/backend && ruff check --select F401 routes/ services/
```

---

## RIEPILOGO IMPATTO PULIZIA

| Categoria | Righe/File | Effort |
|-----------|-----------|--------|
| Route orfane backend | ~3.188 righe, 6 file | Piccolo |
| Service orfane | ~450 righe, 2 file | Piccolo |
| File root legacy | ~5 file | Piccolo |
| Directory vuote | 9 directory | Piccolo |
| Fix main.py (duplicato + lifespan) | ~100 righe da spostare | Medio |
| Collezioni zombie DB | 11 collezioni | Medio (serve verifica) |
| Spec da archiviare | 9 file | Piccolo |
| Test obsoleti | ~70-90 file stimati | Alto (serve analisi singola) |

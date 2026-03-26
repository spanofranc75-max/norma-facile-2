# RCA — Integrazione Fatture in Cloud / SDI

**Data**: 2026-02-XX (analisi eseguita su ambiente preview Emergent)
**Autore**: Agente E1 — Root Cause Analysis
**Perimetro**: SOLO modulo FIC/SDI. Nessuna modifica ad auth, UI, sessioni, altri moduli.

---

## A. REPORT TECNICO

### A.1 Architettura attuale del flusso SDI

```
[Frontend]                    [Backend]                    [Fatture in Cloud API v2]         [SDI]
    |                             |                                  |                         |
    | 1. Click "Invia SDI"        |                                  |                         |
    |---> SdiPreviewDialog        |                                  |                         |
    |     (validazione locale)    |                                  |                         |
    | 2. Conferma checkbox        |                                  |                         |
    |---> POST /api/invoices/     |                                  |                         |
    |     {id}/send-sdi           |                                  |                         |
    |                             | 3. Fetch fattura dal DB          |                         |
    |                             | 4. Fetch client dal DB           |                         |
    |                             | 5. Fetch company_settings dal DB |                         |
    |                             | 6. Validazione pre-invio         |                         |
    |                             |    (validate_invoice_for_sdi)    |                         |
    |                             | 7. Legge token FIC:              |                         |
    |                             |    company.fic_access_token      |                         |
    |                             |    || env FIC_ACCESS_TOKEN        |                         |
    |                             | 8. map_fattura_to_fic()          |                         |
    |                             |---> POST /c/{id}/issued_documents|                         |
    |                             |     (crea fattura su FIC)        |                         |
    |                             |<--- fic_document_id              |                         |
    |                             | 9. Se 409: cerca e aggiorna     |                         |
    |                             |---> POST /c/{id}/issued_documents|                         |
    |                             |     /{fic_id}/e_invoice/send     |--->  Invio XML a SDI    |
    |                             |<--- Risultato                    |                         |
    |                             | 10. Salva status="inviata_sdi"   |                         |
    |                             |     + fic_document_id nel DB     |                         |
    |                             | 11. Audit log outbound           |                         |
    |<--- Risposta                |                                  |                         |
```

### A.2 Endpoint coinvolti

| # | Endpoint | File | Linea | Scopo |
|---|----------|------|-------|-------|
| 1 | `POST /api/invoices/{id}/send-sdi` | `routes/invoices.py` | 1459 | Crea/aggiorna fattura su FIC + invia a SDI |
| 2 | `GET /api/invoices/{id}/stato-sdi` | `routes/invoices.py` | 1705 | Controlla stato SDI via FIC |
| 3 | `POST /c/{cid}/issued_documents` | FIC API v2 | esterno | Crea fattura su FattureInCloud |
| 4 | `PUT /c/{cid}/issued_documents/{id}` | FIC API v2 | esterno | Aggiorna fattura esistente |
| 5 | `POST /c/{cid}/issued_documents/{id}/e_invoice/send` | FIC API v2 | esterno | Invia a SDI |
| 6 | `GET /c/{cid}/issued_documents/{id}/e_invoice/xml` | FIC API v2 | esterno | Legge stato SDI |

### A.3 File coinvolti

| File | Responsabilita |
|------|---------------|
| `backend/services/fattureincloud_api.py` | Client HTTP, retry, error classification, mappatura payload |
| `backend/routes/invoices.py` (righe 1459-1731) | Logica invio SDI, gestione 409, stato |
| `backend/core/config.py` | Lettura env vars (con @lru_cache) |
| `backend/models/company.py` | Modello CompanySettings (fic_access_token, fic_company_id) |
| `backend/routes/company.py` | Salvataggio/lettura impostazioni aziendali |
| `frontend/src/components/SdiPreviewDialog.js` | UI anteprima/invio |
| `frontend/src/components/settings/IntegrazioniTab.js` | UI inserimento credenziali FIC |

---

## B. ANALISI DEGLI ERRORI

### B.1 CAUSA CERTA #1 — Token FIC scaduto/invalido

**Dove**: File `.env` backend, campo `FIC_ACCESS_TOKEN`
**Prova diretta**:
```bash
curl -H "Authorization: Bearer a/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
     "https://api-v2.fattureincloud.it/c/1398737/issued_documents?type=invoice&per_page=2"

# Risposta:
# {"error":"invalid_token","error_description":"The token is expired, revoked, malformed or invalid for other reasons."}
# HTTP_STATUS: 401
```

**Impatto**: OGNI chiamata a FIC fallisce con 401 (che il backend converte in 502 per il frontend).
**Perche**: Il token OAuth2 di Fatture in Cloud ha scadenza. Il token attuale in `.env` e scaduto.

### B.2 CAUSA CERTA #2 — Credenziali FIC assenti nel database

**Dove**: Collezione `company_settings`, documento per `user_97c773827822`
**Prova diretta**:
```
fic_access_token: "" (stringa vuota)
fic_company_id: "" (stringa vuota)
```

**Impatto**: Il codice in `invoices.py` riga 1508:
```python
fic_token = company.get("fic_access_token") or os.environ.get("FIC_ACCESS_TOKEN")
```
Primo fallisce su DB (vuoto), poi ricade su env var (token scaduto) = 401.

**Perche**: L'utente non ha mai salvato le credenziali FIC tramite Impostazioni > Integrazioni, oppure il salvataggio non ha funzionato. L'app si e sempre basata sulla env var.

### B.3 CAUSA CERTA #3 — Inconsistenza lettura token tra endpoint

**Dove**: `routes/invoices.py`

| Endpoint | Come legge il token | Fallback env? |
|----------|-------------------|---------------|
| `send-sdi` (riga 1508) | `company.get("fic_access_token") or os.environ.get("FIC_ACCESS_TOKEN")` | SI |
| `stato-sdi` (riga 1719) | `company.get("fic_access_token") if company else None` | NO |

**Impatto**: `stato-sdi` fallisce SEMPRE con "Credenziali Fatture in Cloud non configurate" perche non ha il fallback env.
**Rischio**: Se l'utente salva il token nel DB, `send-sdi` funzionera ma `stato-sdi` potrebbe ancora fallire se il campo DB non e `"fic_access_token"` esatto.

### B.4 PROBLEMA — FattureInCloudClient constructor ha fallback sbagliato

**Dove**: `services/fattureincloud_api.py`, riga 155
```python
self.access_token = access_token or settings.sdi_api_key
```

**Prova**: `settings.sdi_api_key` corrisponde a `SDI_API_KEY` env var che e **VUOTA**.
**Impatto attuale**: NESSUNO, perche `invoices.py` passa il token esplicitamente. Ma e un bug latente: se qualcuno chiama `get_fic_client()` senza parametri, il client avra token=None.
**Correzione**: Dovrebbe essere `settings.fic_access_token` come fallback.

### B.5 PROBLEMA — Nessun meccanismo di ricezione esiti SDI

**Dove**: Mancante nell'intera codebase.
**Prova**: 
- Nessun endpoint webhook per ricevere callback da FIC
- Nessun polling periodico per aggiornare stati SDI
- L'unico modo e il click manuale su `stato-sdi` (che comunque fallisce per B.3)

**Impatto**: Dopo l'invio, lo stato resta "inviata_sdi" per sempre. L'utente non vede mai "accettata", "rifiutata", etc. a meno di aggiornamento manuale. Delle 13 fatture con status `inviata_sdi`, probabilmente molte sono gia accettate/rifiutate da SDI senza che l'app lo sappia.

### B.6 PROBLEMA — Nessun log persistente SDI nel database

**Dove**: `outbound_audit_log` per `action_type=sdi_send`
**Prova**: 0 record trovati nella collezione.
**Perche**: Il modulo `log_outbound` e stato aggiunto (riga 1632) MA le chiamate SDI reali (10 fatture inviate con successo tra 5 Mar e 20 Mar) sono avvenute PRIMA dell'aggiunta del logging, oppure il logging non era ancora attivo al momento dell'invio.
**Impatto**: Non c'e traccia storica delle richieste/risposte FIC nel DB. Solo nei log stdout del backend (non persistenti).

### B.7 PROBLEMA — Stati fattura incompleti

**Dove**: Schema `invoices` e logica in `invoices.py`

| Stato attuale | Significato |
|---------------|------------|
| `bozza` | Non emessa |
| `emessa` | Emessa ma non inviata a SDI |
| `inviata_sdi` | Inviata a SDI (ma non si sa l'esito) |
| `accettata` | SDI accettata (aggiornamento manuale) |
| `rifiutata` | SDI rifiutata (aggiornamento manuale) |
| `pagata` | Pagata (impostato manualmente) |

**Mancano**:
- `invio_in_corso` — mentre l'invio e in corso (evita doppi click)
- `errore_invio` — invio fallito con errore correggibile (400)
- `errore_temporaneo` — invio fallito per errore tecnico (502/timeout)

**Impatto**: Se l'invio fallisce, lo stato resta `emessa` senza traccia dell'errore. L'utente non sa cosa e successo.

### B.8 PROBLEMA — Configurazione @lru_cache su Settings

**Dove**: `core/config.py`, riga 67
```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**Impatto**: La classe Settings viene istanziata UNA SOLA VOLTA. Se l'env var `FIC_ACCESS_TOKEN` viene cambiata a runtime (es. su Vercel con nuovo deploy), serve un RESTART del processo. Non basta cambiare la variabile.
**Nota**: Questo e irrilevante per il flusso `send-sdi` che legge direttamente `os.environ.get()`, ma causa confusione se qualcuno si aspetta che `settings.fic_access_token` si aggiorni.

---

## C. TABELLA PROBLEMI -> CORREZIONI

| # | Problema | Evidenza | Impatto | Correzione Proposta | Rischio | Priorita |
|---|---------|---------|---------|-------------------|---------|----------|
| 1 | Token FIC in .env scaduto | curl -> HTTP 401 `invalid_token` | BLOCCO TOTALE invio SDI | Utente deve generare nuovo token da FIC e salvarlo in Impostazioni > Integrazioni | Zero (azione utente) | P0 |
| 2 | Token FIC vuoto in DB (company_settings) | Query DB: `fic_access_token: ""` | Fallback continuo su env var (scaduta) | L'utente DEVE salvare token+company_id nelle Impostazioni | Zero (azione utente) | P0 |
| 3 | `stato-sdi` non ha fallback env | Codice riga 1719 vs riga 1508 | Endpoint stato sempre fallisce | Allineare lettura token: stessa logica di `send-sdi` | Basso | P1 |
| 4 | Constructor FIC usa `sdi_api_key` vuota come fallback | Codice riga 155 | Bug latente (non impatta ora) | Cambiare in `settings.fic_access_token` | Basso | P2 |
| 5 | Nessun polling/webhook per esiti SDI | Assenza totale nel codice | Stato fattura mai aggiornato automaticamente | Aggiungere polling periodico o pulsante "Aggiorna stato" | Medio (nuova feature) | P1 |
| 6 | Nessun log SDI persistente nel DB | 0 record in outbound_audit_log | Impossibile fare debug retroattivo | Aggiungere logging dettagliato (req/resp FIC) su ogni invio | Basso | P1 |
| 7 | Stati fattura incompleti | Manca `errore_invio`, `invio_in_corso` | Utente non capisce cosa e successo | Aggiungere stati intermedi | Medio | P2 |
| 8 | Validazione frontend solo locale | SdiPreviewDialog fa check JS-side | Non verifica campi backend obbligatori | Aggiungere endpoint `validate-sdi` lato backend | Basso | P2 |

---

## D. PIANO ESECUTIVO CHIRURGICO

### Prerequisito utente (PRIMA di qualsiasi fix)
L'utente deve:
1. Accedere a **Fatture in Cloud > Impostazioni > App collegate**
2. Generare un **nuovo Access Token** con permessi completi (lettura+scrittura fatture emesse, e-invoice)
3. Salvare il token nell'app: **Impostazioni > Integrazioni > Access Token** + **Company ID** (1398737)
4. Cliccare "Salva"

Questo e il **PRIMO PASSO OBBLIGATORIO**. Senza un token valido, nessun fix tecnico risolvera il problema.

### Fix 1 — Allineamento lettura token (P1, basso rischio)
**File**: `backend/routes/invoices.py`
**Riga**: 1719-1722
**Cosa cambia**: L'endpoint `stato-sdi` leggera il token con la stessa logica di `send-sdi` (DB prima, env fallback dopo).
**Come testare**: `curl GET /api/invoices/{id}/stato-sdi` con autenticazione valida.
**Rollback**: Revert della singola funzione.

### Fix 2 — Fallback constructor FattureInCloudClient (P2, basso rischio)
**File**: `backend/services/fattureincloud_api.py`
**Riga**: 155
**Cosa cambia**: `settings.sdi_api_key` → `settings.fic_access_token`
**Come testare**: Unit test: `get_fic_client()` senza parametri restituisce client con token corretto.
**Rollback**: Revert singola riga.

### Fix 3 — Logging SDI persistente nel DB (P1, basso rischio)
**File**: `backend/routes/invoices.py`
**Cosa cambia**: Ad ogni chiamata FIC (create/send/check), salva un record in `sdi_audit_log` con: invoice_id, timestamp, endpoint, request_payload (senza token), response_status, response_body, error_message.
**Come testare**: Invio fattura → verificare record in sdi_audit_log.
**Rollback**: Rimozione insert nel log.

### Fix 4 — Pulsante "Aggiorna Stato SDI" (P1, medio rischio)
**File frontend**: `InvoiceEditorPage.js` o `InvoicesPage.js`
**File backend**: `routes/invoices.py` (endpoint `stato-sdi` gia esistente)
**Cosa cambia**: Pulsante visibile su fatture con status `inviata_sdi` che chiama `stato-sdi`, interpreta la risposta FIC e aggiorna lo stato locale.
**Come testare**: Click pulsante su fattura inviata → stato si aggiorna.
**Rollback**: Rimozione pulsante frontend.

### Fix 5 — Stati fattura intermedi (P2, medio rischio)
**File**: `backend/routes/invoices.py`, `backend/services/fattureincloud_api.py`
**Cosa cambia**: Aggiunta stati `errore_invio` e transizione chiara.
**Come testare**: Invio con dati mancanti → stato = `errore_invio` con messaggio.
**Rollback**: Revert degli update status.

---

## E. ANALISI AUTENTICAZIONE FIC

### Come viene memorizzato il token
1. **Database** (`company_settings.fic_access_token`): Campo opzionale. Attualmente **VUOTO** per l'utente reale.
2. **Env var** (`FIC_ACCESS_TOKEN`): Impostato in `.env` backend. Attualmente **SCADUTO**.

### Come viene letto
- `send-sdi`: DB prima, poi env fallback → usa token scaduto da env
- `stato-sdi`: SOLO da DB → fallisce con "non configurate"
- `FattureInCloudClient.__init__`: Se nessun token passato, usa `settings.sdi_api_key` (SDI_API_KEY, VUOTA)

### Validita del token
- Token FIC OAuth2 ha scadenza variabile (tipicamente 365 giorni, rinnovabile)
- Il token attuale e un JWT che inizia con `a/eyJ0eX...` — formato corretto per FIC v2
- La risposta FIC dice `"error":"invalid_token"` — il token e stato revocato o e scaduto

### Race condition / caching
- `@lru_cache()` su Settings: token env cachato al primo import. Irrilevante per `send-sdi` che usa `os.environ.get()` direttamente
- Nessun caching del token DB (viene letto fresh ad ogni richiesta)

### Staging vs Production
- **Preview (Emergent)**: Token in `.env` = scaduto
- **Production (Vercel)**: Token nelle env vars Vercel — stato sconosciuto da qui, l'utente dice di averlo cambiato 2h fa
- **Nota**: Se l'utente ha cambiato il token su Vercel ma NON nel DB, il backend su Vercel legge ancora la env var scaduta a meno che non abbia fatto un redeploy

---

## F. RICEZIONE ESITI SDI — Stato attuale

### Meccanismo attuale: **NESSUNO**
- Non c'e webhook configurato per ricevere callback da FIC
- Non c'e polling periodico
- L'unico meccanismo e il click manuale su "Controlla Stato" (endpoint `stato-sdi`)
- Ma `stato-sdi` non funziona perche legge token solo da DB (vuoto)

### Conseguenza
- 13 fatture con status `inviata_sdi` potrebbero avere stati aggiornati su FIC ma l'app non lo sa
- L'utente deve verificare manualmente su fattureincloud.it

### Raccomandazione
Implementare un polling ogni 15 minuti per fatture con `status=inviata_sdi` che:
1. Legge lo stato da FIC
2. Aggiorna lo stato locale
3. Logga l'aggiornamento in `sdi_audit_log`

---

## G. AUDIT DEL LOGGING

### Cosa viene loggato oggi
- `logger.info/error/warning` in `fattureincloud_api.py` e `invoices.py` — va su stdout/stderr
- `outbound_audit_log` con `action_type=sdi_send` — **0 record** (modulo aggiunto dopo gli invii reali)

### Cosa manca
- **Persistenza**: I log stdout si perdono al restart del container
- **Payload completo**: Non viene salvato il body della richiesta/risposta FIC
- **Correlazione**: Non c'e un `request_id` che colleghi la richiesta all'esito
- **Timestamp precisi**: Manca il tempo di risposta (latenza FIC)

### Raccomandazione
Creare collezione `sdi_audit_log` con schema:
```json
{
  "log_id": "sdi_xxx",
  "invoice_id": "inv_xxx",
  "document_number": "17/2026",
  "action": "create|send|check_status",
  "fic_endpoint": "/c/1398737/issued_documents",
  "request_timestamp": "2026-...",
  "response_timestamp": "2026-...",
  "response_status": 200,
  "response_body_summary": "...",
  "error_category": null,
  "error_message": null,
  "fic_document_id": 508917281,
  "user_id": "user_97c..."
}
```

---

## H. VERIFICA CONFIGURAZIONE AMBIENTI

| Parametro | Preview (Emergent .env) | DB (company_settings) | Produzione (Vercel) |
|-----------|------------------------|----------------------|-------------------|
| FIC_ACCESS_TOKEN | `a/eyJ0eXAi...` (SCADUTO) | `""` (vuoto) | Sconosciuto* |
| FIC_COMPANY_ID | `1398737` | `""` (vuoto) | Sconosciuto* |
| FIC Base URL | `api-v2.fattureincloud.it` | N/A | Uguale |
| CORS | Configurato | N/A | Da verificare |

*L'utente dichiara di aver aggiornato il token su Vercel 2h fa. Se non ha fatto redeploy, il container potrebbe usare ancora il vecchio token.

---

## I. ROOT CAUSE ANALYSIS — RIEPILOGO PRIORITIZZATO

| # | Causa | Tipo | Impatto | Priorita |
|---|-------|------|---------|----------|
| 1 | Token FIC scaduto/revocato | CERTA | SDI bloccato al 100% | P0 CRITICO |
| 2 | Token non salvato nel DB (company_settings) | CERTA | Fallback perpetuo su env var scaduta | P0 CRITICO |
| 3 | Endpoint `stato-sdi` non legge da env | CERTA | Impossibile verificare stato SDI | P1 ALTO |
| 4 | Nessun polling/webhook esiti SDI | CERTA | Stato fatture mai aggiornato | P1 ALTO |
| 5 | Logging SDI non persistente | CERTA | Debug impossibile dopo il fatto | P1 MEDIO |
| 6 | Constructor FIC fallback sbagliato | CERTA | Bug latente | P2 BASSO |
| 7 | Stati fattura incompleti | CERTA | UX confusa su errori | P2 BASSO |

---

## J. REGOLE DEFINITIVE INTEGRAZIONE FIC/SDI

### Regola 1 — Token sempre da DB, env solo come ultimo fallback
Il token FIC DEVE essere salvato nel database (`company_settings`). L'env var serve solo come fallback temporaneo per la prima configurazione.

### Regola 2 — Ogni endpoint FIC usa la stessa funzione di lettura token
Creare helper `get_fic_credentials(company_settings)` usato da TUTTI gli endpoint che comunicano con FIC.

### Regola 3 — Ogni chiamata FIC viene loggata nel DB
Nessuna chiamata FIC senza un record in `sdi_audit_log`.

### Regola 4 — Errori FIC SEMPRE mappati a 502/503, MAI 401
Gia implementato per `send-sdi`, da applicare anche a `stato-sdi`.

### Regola 5 — Validazione PRIMA della chiamata FIC
Non sprecare chiamate API se i dati non sono completi.

### Regola 6 — Idempotenza su tutte le operazioni di scrittura
Gia implementato con `_idempotency_key`. Mantenere.

### Regola 7 — Retry solo su errori transient (500/502/503/timeout)
Gia implementato con backoff esponenziale. Mantenere. MAI retry su 400/401/422.

### Regola 8 — Stato fattura deterministico
Ogni transizione di stato deve essere esplicita e loggata.

---

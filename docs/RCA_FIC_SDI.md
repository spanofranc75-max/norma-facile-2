# RCA COMPLETA — Integrazione Fatture in Cloud / SDI

**Data**: Febbraio 2026
**Versione**: 2.0 (con le 4 integrazioni richieste)
**Perimetro**: SOLO modulo FIC/SDI

---

## A. ARCHITETTURA ATTUALE DEL FLUSSO SDI

```
[Frontend]                    [Backend]                    [Fatture in Cloud API v2]         [SDI]
    |                             |                                  |                         |
    | 1. Click "Invia SDI"        |                                  |                         |
    |---> SdiPreviewDialog        |                                  |                         |
    |     (validazione locale)    |                                  |                         |
    | 2. Conferma checkbox        |                                  |                         |
    |---> POST /api/invoices/     |                                  |                         |
    |     {id}/send-sdi           |                                  |                         |
    |                             | 3. Fetch fattura+client+company  |                         |
    |                             | 4. validate_invoice_for_sdi()    |                         |
    |                             | 5. Legge token FIC:              |                         |
    |                             |    DB company_settings OPPURE    |                         |
    |                             |    env FIC_ACCESS_TOKEN           |                         |
    |                             | 6. map_fattura_to_fic()          |                         |
    |                             |---> POST /c/{cid}/issued_docs    |                         |
    |                             |<--- fic_document_id (o 409)      |                         |
    |                             |---> POST /{fic_id}/e_invoice/send|---> XML a SDI           |
    |                             |<--- Risultato                    |                         |
    |                             | 7. Salva status+fic_document_id  |                         |
    |<--- Risposta JSON           |                                  |                         |
    |                             |                                  |                         |
    | [MANCA] Polling/Webhook     |   [MANCA] Ricezione esiti        |<--- Esito SDI          |
```

### Endpoint coinvolti

| Endpoint | File:Riga | Scopo |
|----------|-----------|-------|
| `POST /api/invoices/{id}/send-sdi` | invoices.py:1459 | Crea su FIC + invia a SDI |
| `GET /api/invoices/{id}/stato-sdi` | invoices.py:1705 | Controlla stato (solo da DB, NO env fallback) |
| FIC `POST /c/{cid}/issued_documents` | esterno | Crea fattura su FIC |
| FIC `PUT /c/{cid}/issued_documents/{id}` | esterno | Aggiorna fattura |
| FIC `POST /c/{cid}/issued_documents/{id}/e_invoice/send` | esterno | Invia a SDI |
| FIC `GET /c/{cid}/issued_documents/{id}/e_invoice/xml` | esterno | Legge stato SDI |

---

## B. ROOT CAUSE ANALYSIS — ERRORI 502

### Causa certa: Token OAuth FIC scaduto

**Evidenza diretta:**
```bash
$ curl -H "Authorization: Bearer a/eyJ0eXAi..." \
       "https://api-v2.fattureincloud.it/c/1398737/issued_documents?type=invoice&per_page=2"

# Risposta HTTP 401:
{"error":"invalid_token","error_description":"The token is expired, revoked, malformed or invalid for other reasons."}
```

**Perche e scaduto:**
Il token inizia con **`a/`** = e un **OAuth Access Token** di FattureInCloud.
Dalla documentazione FIC ufficiale:
- **Access Token (prefisso `a/`)**: scade dopo **24 ore**
- **Refresh Token (prefisso `r/`)**: scade dopo **1 anno** dall'ultimo utilizzo
- **Token manuale**: NON scade mai (generato da Impostazioni > App collegate)

Il nostro sistema **non ha mai implementato il refresh del token OAuth**.
Non esiste nessun Refresh Token ne nell'env ne nel DB ne nel codice.

**Catena dell'errore 502:**
```
1. Frontend chiama POST /api/invoices/{id}/send-sdi
2. Backend legge token da env (DB e vuoto)
3. Backend chiama FIC con token scaduto
4. FIC risponde HTTP 401 "invalid_token"
5. Backend converte 401 FIC → HTTP 502 (correttamente, per non confondere auth frontend)
6. Frontend mostra errore 502 generico
```

### Credenziali nel database: VUOTE

```
company_settings per user_97c773827822:
  fic_access_token: "" (vuoto)
  fic_company_id: "" (vuoto)
```

Il codice ricade SEMPRE sull'env var, che contiene il token scaduto.

### Inconsistenza lettura token

| Endpoint | Legge da DB? | Fallback env? | Risultato |
|----------|-------------|--------------|-----------|
| `send-sdi` (riga 1508) | Si | Si | Usa env scaduta |
| `stato-sdi` (riga 1719) | Si | **NO** | Errore "non configurate" |

---

## C. ANALISI ERRORI 400 — CASO REALE DOCUMENTATO

### C.1 Simulazione payload per fattura 14/2026 (Stanzani Spa)

**invoice_id**: `inv_fa3decf4d9f2`
**document_number**: `14/2026`
**Tipo**: FT (Fattura)

**Payload generato da `map_fattura_to_fic()`:**
```json
{
  "type": "invoice",
  "e_invoice": true,
  "ei_data": {"payment_method": "MP05"},
  "entity": {
    "name": "Stanzani Spa",
    "vat_number": "00549431203",
    "tax_code": "02125530374",
    "address_street": "Via della Pace 2/E",
    "address_postal_code": "40010",
    "address_city": "Sala Bolognese",
    "address_province": "BO",
    "country": "Italia",
    "country_iso": "IT",
    "ei_code": "0000000",
    "certified_email": ""
  },
  "date": "2026-02-28",
  "number": 14,
  "items_list": [{
    "product_id": null,
    "code": "",
    "name": "Come da preventivo n. PRV-2026-0003...",
    "net_price": 6000.0,
    "qty": 1.0,
    "vat": {"id": 0, "value": 22.0},
    "discount": 0.0
  }],
  "payments_list": [{
    "amount": 7320.0,
    "due_date": "2026-03-30",
    "paid_date": null,
    "status": "not_paid",
    "payment_account": null
  }]
}
```

### C.2 Potenziali cause di 400 identificate

| # | Campo | Valore | Problema | Rischio 400 |
|---|-------|--------|----------|-------------|
| 1 | `entity.ei_code` | `"0000000"` | Codice SDI generico | ALTO se PEC vuota |
| 2 | `entity.certified_email` | `""` | PEC mancante | ALTO con SDI=0000000 |
| 3 | `vat.id` | `0` | FIC potrebbe richiedere un ID valido dal proprio catalogo VAT | MEDIO |
| 4 | `entity.country` | `"Italia"` | FIC potrebbe richiedere `"Italy"` o solo `country_iso` | BASSO |
| 5 | `product_id` | `null` | Potrebbe essere richiesto per e-invoice | BASSO |

### C.3 Causa 400 piu probabile: SDI=0000000 + PEC vuota

Per la fattura Stanzani Spa:
- `ei_code` = `"0000000"` (codice SDI generico — significa "non ho codice SDI")
- `certified_email` = `""` (PEC mancante)

**Quando si usa SDI `0000000`, il sistema SDI consegna tramite PEC.** Se anche la PEC e vuota, SDI non sa dove recapitare e FIC potrebbe rifiutare l'invio con 400.

### C.4 Causa 400 possibile: vat.id=0

FIC usa un sistema di **tipi IVA con ID numerico**. Il nostro codice mappa sempre `"id": 0` che significa "tipo IVA di default". Questo potrebbe causare 400 se:
- Il tipo IVA default non e configurato nell'account FIC
- Per aliquote speciali (N3, N4, ecc.) serve un ID specifico dal catalogo FIC

**Raccomandazione**: Chiamare `GET /c/{cid}/info/vat_types` per ottenere gli ID corretti e mapparli.

### C.5 Nota importante

**Non posso riprodurre un 400 reale** perche il token e scaduto (ogni chiamata restituisce 401).
Per confermare la causa esatta del 400, serve:
1. Un token valido
2. Una chiamata reale a FIC con il payload sopra
3. La response body completa del 400

---

## D. CONFERMA MODELLO AUTENTICAZIONE FIC

### Situazione attuale: OAuth con token scaduto e SENZA refresh

**Tipo token in uso**: OAuth Access Token (prefisso `a/`)
**Scadenza**: 24 ore dalla generazione
**Refresh Token salvato**: **NESSUNO** — ne in env, ne in DB, ne nel codice
**Refresh Token nel codice**: **NON IMPLEMENTATO** — nessuna riga di codice gestisce il refresh

### Opzioni disponibili (dalla documentazione FIC ufficiale)

| Opzione | Tipo token | Scadenza | Complessita | Pro | Contro |
|---------|-----------|----------|-------------|-----|--------|
| A. Token manuale | Senza prefisso | **Mai** (solo revoca manuale) | ZERO | Funziona subito, zero codice | Meno sicuro, l'utente deve rigenerare se compromesso |
| B. OAuth + Refresh | `a/` + `r/` | 24h access, 1 anno refresh | ALTA | Standard OAuth2, rinnovo auto | Serve implementare tutto il flusso refresh |
| C. OAuth senza refresh | `a/` | 24h | N/A | Nessuno | **Situazione attuale — non funziona** |

### Raccomandazione

**FASE 1 (sblocco immediato)**: Usare **Token Manuale** (Opzione A).
- Generabile da: FattureInCloud > Impostazioni > App collegate > "Connetti" > Token manuale
- Non scade mai
- Non richiede nessuna modifica al codice
- L'utente lo salva una volta nelle Impostazioni dell'app

**FASE 2 (definitiva, opzionale)**: Implementare **OAuth con Refresh Token** (Opzione B).
- Richiede: client_id, client_secret, endpoint di autorizzazione
- Rinnovo automatico ogni 23 ore
- Persistenza sicura del refresh token nel DB
- Complessita stimata: 2-3 file nuovi, ~150 righe di codice

---

## E. CONFERMA MODELLO DATI COMPANY_SETTINGS

### Stato attuale: per user_id (NON per tenant)

La collezione `company_settings` usa `user_id` come chiave primaria:
```python
# routes/company.py, riga 34
settings = await db.company_settings.find_one(
    {"user_id": uid, "tenant_id": tenant_match(user)}
)
```

**Dati nel DB:**
- Tenant `ten_1cf1a865bf20` ha **13 documenti** company_settings
- Di cui solo 1 e l'utente reale (`user_97c773827822`)
- Gli altri 12 sono utenti di test creati dal testing agent

### Problema

Se un altro utente (es. `amministrazione`) prova a inviare a SDI, il sistema cerca `company_settings` con il SUO `user_id` e non trova le credenziali FIC.

### Raccomandazione

Per il flusso FIC/SDI, le credenziali dovrebbero essere lette a **livello tenant**, non utente:
```python
# Proposta: leggere company_settings per tenant, non per user
company = await db.company_settings.find_one(
    {"tenant_id": tenant_match(user)},  # NON user_id
    {"_id": 0}
)
```

**Ma attenzione**: oggi i dati aziendali reali (P.IVA, indirizzo, ecc.) sono nel documento dell'admin. Cambiare la query senza migrare i dati potrebbe trovare un documento di test.

**Raccomandazione chirurgica**: 
1. Per FASE 1: tenere la query per `user_id` (funziona perche solo l'admin invia SDI)
2. Per FASE 2: migrare verso query per `tenant_id` + pulire i documenti test

---

## F. STRATEGIA RICEZIONE ESITI SDI

### Stato attuale: NESSUN meccanismo

| Meccanismo | Implementato? | Note |
|-----------|--------------|------|
| Webhook FIC | NO | Endpoint non esiste |
| Polling periodico | NO | Nessun scheduler per stati SDI |
| Controllo manuale | SI (rotto) | `stato-sdi` non legge token da env |

### Conseguenza

13 fatture con status `inviata_sdi` non hanno stato aggiornato. Potrebbero essere accettate, rifiutate o scartate senza che l'app lo sappia.

### Opzioni con pro/contro

| Opzione | Complessita | Affidabilita | Latenza | Dipendenze |
|---------|------------|-------------|---------|------------|
| **A. Webhook FIC** | ALTA | ALTA | Real-time | URL pubblico stabile, HTTPS, gestione retry FIC |
| **B. Polling schedulato** | MEDIA | ALTA | 15-30 min | Solo backend, nessuna dipendenza esterna |
| **C. Pulsante manuale** | BASSA | BASSA | On-demand | Dipende dall'utente |

### Raccomandazione

**FASE 1**: Implementare **Opzione C (pulsante manuale)** — il fix e minimo:
1. Correggere `stato-sdi` per leggere token correttamente
2. Aggiungere pulsante "Aggiorna Stato" nella lista fatture
3. Interpretare risposta FIC e aggiornare stato locale

**FASE 2**: Implementare **Opzione B (polling schedulato)** — piu affidabile:
1. Scheduler ogni 15 minuti
2. Query: fatture con `status=inviata_sdi` e `sdi_sent_at` > 5 minuti fa
3. Per ognuna: chiama `stato-sdi`, aggiorna DB
4. Log ogni aggiornamento

**FASE 3 (opzionale)**: **Opzione A (webhook)** — richiede URL pubblico stabile.
- L'URL di produzione cambia con ogni deploy su Emergent/Vercel?
- Se si, il webhook si rompe ad ogni deploy
- Meglio aspettare un dominio stabile

---

## G. TABELLA COMPLETA PROBLEMI → CORREZIONI

| # | Problema | Evidenza | Impatto | Correzione | Rischio | Fase |
|---|---------|---------|---------|-----------|---------|------|
| 1 | Token OAuth FIC scaduto (24h) | curl → 401 `invalid_token` | BLOCCO TOTALE | Generare token manuale (non scade) | Zero | F1 |
| 2 | Nessun token nel DB | company_settings vuote | Fallback perenne su env | Salvare in Impostazioni > Integrazioni | Zero | F1 |
| 3 | `stato-sdi` senza fallback env | Codice riga 1719 | Impossibile controllare stato | Allineare a `send-sdi` | Basso | F1 |
| 4 | SDI=0000000 + PEC vuota | Payload fattura 14/2026 | Probabile causa 400 | Validazione pre-invio potenziata | Basso | F1 |
| 5 | `vat.id=0` potrebbe essere rifiutato | Payload generato | Possibile causa 400 | Mappare ID VAT reali da FIC | Medio | F1 |
| 6 | Nessun log SDI persistente | 0 record in outbound_audit_log | Debug impossibile | Aggiungere `sdi_audit_log` | Basso | F1 |
| 7 | Constructor FIC fallback sbagliato | `sdi_api_key` vuota | Bug latente | Cambiare in `fic_access_token` | Basso | F1 |
| 8 | Nessun polling/webhook esiti | Assenza nel codice | Stato mai aggiornato | Pulsante manuale + polling | Medio | F1+F2 |
| 9 | Stati fattura incompleti | Manca `errore_invio` | UX confusa | Aggiungere stati intermedi | Medio | F2 |
| 10 | Token OAuth senza refresh | Nessun refresh_token | Scade ogni 24h | Token manuale O implementare refresh | Alto | F2 |
| 11 | company_settings per user non tenant | Query con user_id | Multi-utente fragile | Migrare a tenant_id | Medio | F2 |

---

## H. PIANO ESECUTIVO CHIRURGICO

### FASE 1 — Sblocco operativo (6 fix atomici)

**Prerequisito utente**: Generare **token manuale** da FIC (non OAuth).
> FattureInCloud > Impostazioni > App collegate > Genera token manuale
> Questo token NON scade e NON richiede refresh.

| Step | File | Righe | Cosa cambia | Come testare | Rollback |
|------|------|-------|-------------|-------------|----------|
| 1.1 | `fattureincloud_api.py` | 155 | Fallback `sdi_api_key` → `fic_access_token` | Unit test `get_fic_client()` | Revert 1 riga |
| 1.2 | `invoices.py` | 1719-1722 | `stato-sdi` legge token come `send-sdi` | curl `GET stato-sdi` | Revert 4 righe |
| 1.3 | `invoices.py` | nuovo | Helper `_get_fic_credentials(company)` usato da tutti gli endpoint | Test invio fattura | Revert funzione |
| 1.4 | `invoices.py` | nuovo | Logging SDI persistente: ogni chiamata FIC salva record in `sdi_audit_log` | Verificare DB dopo invio | Rimuovere insert |
| 1.5 | `fattureincloud_api.py` | validate | Potenziare validazione: blocca se SDI=0000000 E PEC vuota | Test con fattura Stanzani | Revert check |
| 1.6 | `InvoiceEditorPage.js` | nuovo | Pulsante "Aggiorna Stato SDI" per fatture inviata_sdi | Click su fattura inviata | Rimuovere pulsante |

**Test end-to-end OBBLIGATORIO dopo Fase 1:**
- 1 fattura reale con dati completi → deve andare su FIC e SDI
- 1 fattura con SDI=0000000 e PEC vuota → deve dare errore chiaro pre-invio

### FASE 2 — Stabilizzazione (dopo approvazione esplicita)

| Step | Cosa | Complessita |
|------|------|------------|
| 2.1 | Polling schedulato stati SDI (ogni 15 min) | Media |
| 2.2 | Stati fattura intermedi (`errore_invio`, `invio_in_corso`) | Media |
| 2.3 | Mappatura corretta ID tipi IVA da catalogo FIC | Media |
| 2.4 | Refresh token OAuth automatico (alternativa a token manuale) | Alta |
| 2.5 | Migrazione company_settings da user_id a tenant_id | Alta |

---

## I. MAPPING ERRORI DEFINITIVO

| Sorgente | Status ricevuto | Status mostrato all'utente | Azione | Retry? |
|----------|----------------|---------------------------|--------|--------|
| FIC auth | 401 | "Token FIC scaduto/invalido" | Rigenerare token | NO |
| FIC permessi | 403 | "Permessi FIC insufficienti" | Verificare scope token | NO |
| FIC validazione | 422 | "Dati non validi: [dettaglio campo]" | Correggere dati fattura | NO |
| FIC conflitto | 409 | "Documento gia presente su FIC" | Auto-recovery (cerca e aggiorna) | SI |
| FIC server | 500/502/503 | "FIC temporaneamente non disponibile" | Retry automatico (3x, backoff) | SI |
| FIC timeout | timeout | "FIC non risponde" | Retry automatico | SI |
| SDI gia inviata | 400 + "already" | "Fattura gia inviata a SDI" | Allinea stato locale | NO |
| Payload invalido | 400 | "Errore invio: [dettaglio]" | Correggere dati | NO |
| App validazione | 422 | "Validazione fallita: [lista errori]" | Correggere dati prima dell'invio | NO |
| Credenziali mancanti | 400 | "Configura credenziali FIC in Impostazioni" | Inserire token+company_id | NO |

---

## J. REGOLE DEFINITIVE (NON NEGOZIABILI)

1. **Token FIC nel DB, non nell'env** — L'env serve solo come fallback iniziale
2. **Lettura token centralizzata** — Un solo helper, usato ovunque
3. **Ogni chiamata FIC loggata nel DB** — `sdi_audit_log` con request/response
4. **Errori FIC SEMPRE mappati a 502/503** — MAI 401 verso il frontend
5. **Validazione PRIMA della chiamata** — Zero chiamate API con dati incompleti
6. **Idempotenza** — Doppio click/retry non crea duplicati
7. **Retry solo su transient** — 500/502/503/timeout. MAI su 400/401/422
8. **Stato fattura deterministico** — Ogni transizione esplicita e loggata

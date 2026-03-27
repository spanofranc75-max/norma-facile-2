# Procedura Operativa FIC/SDI — NormaFacile 2.0

**Ultimo aggiornamento**: 27 Marzo 2026
**Stato**: OPERATIVO

---

## 1. Token Attuale

- **Tipo**: Token personale (generato da app "NormaFacileSDI" con autenticazione "Token personale")
- **Prefisso**: `a/` (il prefisso e presente anche nei token manuali FIC)
- **JWT payload**: contiene solo `ref`, NESSUN campo `exp` (scadenza)
- **Scadenza prevista**: Mai (token personale FIC, revocabile solo manualmente)
- **Company ID**: `1398737`
- **App ID FIC**: 17571
- **Client ID**: `mrHhZ4Mk3KH9Sai29S2gSwvE4cK4FRi4`

## 2. Dove e salvato il token

| Posizione | Valore | Priorita lettura |
|-----------|--------|-----------------|
| DB `company_settings` (user_97c773827822) | `fic_access_token` | PRIMA (source of truth) |
| `.env` backend `FIC_ACCESS_TOKEN` | Backup | FALLBACK (se DB vuoto) |

Il codice usa l'helper `_get_fic_credentials()` che legge prima dal DB, poi dall'env.

## 3. Come verificare che il token funziona

```bash
# Test rapido da terminale
curl -H "Authorization: Bearer [TOKEN]" \
     "https://api-v2.fattureincloud.it/c/1398737/issued_documents?type=invoice&per_page=5"
# Se HTTP 200 -> token valido
# Se HTTP 401 -> token scaduto/revocato
```

## 4. Se un invio SDI fallisce

### Errore 502 "Token scaduto"
1. Andare su fattureincloud.it > Impostazioni > Applicazioni collegate
2. Trovare "NormaFacileSDI" > cliccare "Gestisci"
3. Cliccare "Rigenera token"
4. Copiare il nuovo token
5. In NormaFacile: Impostazioni > Integrazioni > incollare il nuovo token
6. Salvare

### Errore 422 "Validazione SDI fallita"
Il sistema blocca l'invio se:
- Il cliente ha SDI=0000000 E PEC vuota
- Mancano dati obbligatori (P.IVA/CF, indirizzo, etc.)

**Azione**: Completare i dati del cliente prima di riprovare.

### Errore 422 "Errore Fatture in Cloud"
Errore di validazione da FIC. Controllare:
- I dati della fattura sono completi e coerenti
- L'aliquota IVA e corretta
- Il numero fattura non e duplicato su FIC

## 5. Cose da NON toccare

1. **Non modificare** `AuthContext.js`, `ProtectedRoute.js`, `security.py`
2. **Non modificare** moduli non correlati a FIC/SDI
3. **Non scollegare** l'app "HUB NormaFacile" (vecchia OAuth) — lasciarla per sicurezza
4. **Non cambiare** la logica di lettura token (`_get_fic_credentials()`)

## 6. Audit Log SDI

Ogni chiamata FIC viene registrata nella collezione `sdi_audit_log`:
- `action`: create_on_fic, send_to_sdi, check_status
- `response_status`: HTTP status della risposta FIC
- `error_category`: tipo di errore (se presente)
- `timestamp`: quando e avvenuta la chiamata

## 7. Cronologia token

| Data | Tipo token | Stato | Note |
|------|-----------|-------|------|
| Pre-23 Mar | OAuth `a/` (HUB NormaFacile) | SCADUTO | Scadeva ogni 24h |
| 27 Mar (mattina) | OAuth `a/` rigenerato | SCADUTO | Stessa app, stessa scadenza |
| 27 Mar (ora) | Personale `a/` (NormaFacileSDI) | ATTIVO | App nuova, Token personale, senza exp |

# Policy Sessioni — NormaFacile 2.0

## Regole

| Parametro | Valore |
|---|---|
| Sessioni max per utente | 5 |
| Durata sessione | 7 giorni |
| Rinnovo automatico | Sì, quando mancano < 2 giorni alla scadenza |
| Health check frontend | Ogni 3 minuti |
| Cosa succede al login da altro dispositivo | Sessione precedente resta valida (multi-sessione) |
| Cosa succede se si superano 5 sessioni | Si eliminano SOLO le più vecchie |

## Cosa succede quando la sessione scade

### Backend
- `verify_session()` restituisce `401 Unauthorized` con messaggio "Sessione scaduta"
- Logga l'evento: `Session expired: user=xxx, expired_at=xxx`

### Frontend
- `apiRequest` intercetta il 401 (tranne su `/auth/*`)
- Chiama `onAuthExpired(detail)` → `AuthContext` setta `sessionExpired=true`
- `ProtectedRoute` mostra schermata "Sessione scaduta" con pulsante "Accedi di nuovo"
- **MAI svuotare i dati già caricati nei componenti**
- **MAI mostrare liste vuote come dato reale**

## Errori di servizi esterni (FIC/SDI)

| Errore FIC | Nostro HTTP Status | Messaggio |
|---|---|---|
| 401 (token scaduto) | **502** | "Token FattureInCloud scaduto o non valido..." |
| 403 (permessi) | **502** | "Permessi insufficienti sul token FIC..." |
| 500/502/503 | **502** | "FIC temporaneamente non disponibile..." |
| 400/422 (validazione) | **422** | "Errore Fatture in Cloud: [dettaglio]" |

> **Regola**: MAI restituire 401 o 403 per errori di servizi esterni. Usare sempre 502 o 422.

## Checklist Pre-Deploy

- [ ] Login da un tab funziona
- [ ] Login da due tab non slogga il primo
- [ ] Refresh pagina mantiene sessione
- [ ] Sessione scaduta mostra schermata chiara (non dati vuoti)
- [ ] Nessuna pagina mostra dati vuoti dopo 401
- [ ] Logout funziona
- [ ] Cookie/token presenti correttamente in produzione
- [ ] Environment variables corrette su Vercel
- [ ] `FIC_ACCESS_TOKEN` valido

## File di riferimento

| File | Ruolo |
|---|---|
| `backend/core/security.py` | Creazione/verifica/rinnovo sessioni |
| `frontend/src/lib/utils.js` | Layer API centralizzato + interceptor 401 |
| `frontend/src/contexts/AuthContext.js` | Stato auth + health check + onAuthExpired |
| `frontend/src/components/ProtectedRoute.js` | Schermata "Sessione scaduta" |
| `backend/tests/test_session_policy.py` | Test automatici policy sessioni |

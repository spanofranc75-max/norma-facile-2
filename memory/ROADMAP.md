# NormaFacile 2.0 — ROADMAP

Ultimo aggiornamento: 2026-03-23

---

## CHIUSO (tutto completato e testato)

### Core prodotto
- [x] Preventivi + Istruttoria AI + Segmentazione
- [x] Commesse madre / rami / emissioni
- [x] Evidence Gate (EN 1090 + EN 13241)
- [x] Sicurezza / Scheda cantiere / AI Sicurezza
- [x] POS DOCX generato da commessa
- [x] Pacchetti documentali + invio email
- [x] Verifica Committenza AI
- [x] Registro Obblighi Commessa
- [x] Dashboard multilivello
- [x] Audit log

### Hardening tecnico
- [x] Indici critici MongoDB (49 totali)
- [x] Rate limiting AI
- [x] Error handling async
- [x] Filtro user_id su route esposte
- [x] Cleanup dead code
- [x] Data integrity check + fix
- [x] Hardening credenziali / JWT / sessioni / token
- [x] Validation sprint output & delivery (22/22)

### Business Sprint
- [x] Demo Mode (login, seed, guard, banner, reset)
- [x] Content Engine M1+M2 (sorgenti, idee AI, bozze AI, coda editoriale)
- [x] Calibrazione prompt AI (3 benchmark reali)
- [x] Caso Studio Quantificato (pagina pubblica + sorgente CE)
- [x] Copy to Clipboard (bozze)

### Deploy readiness
- [x] CORS pulito (solo domini produzione, regex per emergent)
- [x] SAFE_MODE attivo (email e FiC bloccate)
- [x] Cookie sicuri (httponly, secure, samesite)
- [x] Deployment agent check passed

---

## P0 — PROSSIMI (alto impatto business)

### 1. Pricing & Packaging
- Definire 3 tier: Pilot / Pro / Enterprise
- Cosa include ogni tier, per chi e, come raccontarlo
- Pagina /pricing pubblica
- Prerequisito per Stripe

### 2. Mini-hardening SDI / FattureInCloud
- Retry strategy su chiamate FiC
- Gestione FiC down (circuit breaker)
- Token refresh automatico
- Classificazione errori (transient vs permanent)
- Log strutturato e chiaro

---

## P1 — MEDIO IMPATTO

### 3. Stripe / Monetizzazione
- Dopo pricing definito
- Checkout, subscription management, webhook
- Test key gia disponibile nel pod

### 4. SmartEmptyState incrementale
- Certificazioni, DDT, Fornitori, altre pagine secondarie
- Componente gia pronto, solo da estendere

### 5. Guida operativa persistente
- Aiuto contestuale sempre disponibile e disattivabile
- Non solo onboarding iniziale

### 6. Product Tour guidato
- Overlay interattivo sull'ambiente demo
- Dopo caso studio + pricing

---

## P2 — BACKLOG STRATEGICO

### 7. Email automatiche selettive
- Dopo sistema notifiche e uso reale

### 8. Refactoring file monolitici
- CommessaHub, IstruttoriaPage, altri > 1000 righe
- Breakup in componenti piu piccoli

### 9. Stability Guard AI
- Monitoraggio qualita output AI
- Fallback e alert su risposte degradate

### 10. Multi-tenant
- Isolamento dati per organizzazione
- Blocco architetturale importante

### 11. Pydantic V1 → V2
- Migrazione tecnica pianificata

### 12. Portale clienti
- Accesso esterno per committenti
- Dopo multi-tenant

---

## Note
- Il prodotto NON va descritto come "ERP" ma come sistema operativo verticale / copilota operativo
- Tono contenuti: italiano B2B tecnico, concreto, zero hype
- Metriche: sempre prudenziali, dichiarate come stime/caso pilota
- SDI/FattureInCloud: confermato core e attivo (non legacy)

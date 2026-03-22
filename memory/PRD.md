# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformità EN 1090-1. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilità materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

**Pivot strategico**: da generatore documentale a copilota tecnico-normativo AI-driven.

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalità Implementate

### Core EN 1090 + Multi-Normativa (Completo)
- Commesse CRUD, FPC, Saldatura, Riesame Tecnico, Ispezioni, DOP, CE Label
- CAM, PDF Executive, Scadenziario, DDT, Fatturazione, Notifiche, QR Code

### Motore di Istruttoria Automatica (Completo)
- P0.1 Cockpit operativo, P0.15 Dipendenze dinamiche, P0.25 Domande contestuali
- P0.2 Spiegabilità, P0.3 Box "Se confermi la commessa"

### P1 — Validazione Real-World (Completato 22/03/2026)
- 8 preventivi reali validati
- **Score finale: 91% globale, 8/8 classificazioni (100%), estrazione 79%, domande 100%**
- Tutte le soglie superate

### P1.1 — Segmentazione Normativa per Riga (Completato 22/03/2026)
- Keyword deterministico + GPT-4o per casi incerti
- Frontend con review utente e conferma

### Phase 2 — Commessa Pre-Istruita Revisionata (Completato 22/03/2026)
- **Criteri di eleggibilità** (7 check):
  1. Istruttoria confermata dall'utente
  2. Classificazione pura (EN_1090/EN_13241/GENERICA, non MISTA/INCERTA)
  3. Confidenza alta
  4. Segmentazione OK (non attiva o confermata)
  5. Domande ad alto impatto risposte
  6. Nessun blocco strutturale
  7. Campi critici presenti per normativa
- **Output**: commessa con voci lavoro, controlli, documenti, materiali, rami attivi (saldatura/zincatura/montaggio)
- **Motivo di blocco esplicito** quando non eleggibile
- **Frontend**: card con contatori (precompilati/da completare/non emettibili) + dettaglio

## Backlog Prioritizzato

### P0 — Immediato
- **Evidence Gate**: Gate che blocca emissione DOP/CE/dichiarazioni senza evidenze obbligatorie

### P1 — Prossimo
- Stability guard deterministico per classificazione borderline
- Consensus mode opzionale per casi dubbi

### P2
- Multi-Tenant, ML Training, Alerting

### P3
- Unificazione PDF, Portale Clienti
- Fix warning minori (exhaustive-deps, hydration)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformita EN 1090-1. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilita materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

**Pivot strategico**: da generatore documentale a copilota tecnico-normativo AI-driven.

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalita Implementate

### Core EN 1090 + Multi-Normativa (Completo)
- Commesse CRUD, FPC, Saldatura, Riesame Tecnico, Ispezioni, DOP, CE Label
- CAM, PDF Executive, Scadenziario, DDT, Fatturazione, Notifiche, QR Code

### Motore di Istruttoria Automatica (Completo)
- P0.1 Cockpit operativo, P0.15 Dipendenze dinamiche, P0.25 Domande contestuali
- P0.2 Spiegabilita, P0.3 Box "Se confermi la commessa"

### P1 — Validazione Real-World (Completato 22/03/2026)
- 8 preventivi reali validati
- **Score finale: 91% globale, 8/8 classificazioni (100%), estrazione 79%, domande 100%**
- Tutte le soglie superate

### P1.1 — Segmentazione Normativa per Riga (Completato 22/03/2026)
- Keyword deterministico + GPT-4o per casi incerti
- Frontend con review utente e conferma

### Phase 2 — Commessa Pre-Istruita Revisionata (Completato 22/03/2026)
- 7 criteri di eleggibilita
- Output: commessa con voci lavoro, controlli, documenti, materiali, rami attivi
- Frontend: card con contatori (precompilati/da completare/non emettibili)

### Fase A — Modello Gerarchico Commessa (Completato 22/03/2026)
- **Architettura a 4 livelli**: Commessa Madre -> Ramo Normativo -> Emissione Documentale -> Evidence Gate
- **Nuova collezione `commesse_normative`**: rami EN_1090, EN_13241, GENERICA per commessa
  - Indice univoco `(commessa_id, normativa, user_id)`
  - Creazione idempotente (upsert se gia esiste)
  - Tracciamento origine: `created_from` (manuale/segmentazione/legacy_wrap)
- **Nuova collezione `emissioni_documentali`**: emissioni progressive per ramo
  - Numerazione: `NF-2026-000125-1090-D01`, `-D02`, `...-13241-C01`
  - Counter atomico per progressivo
  - Indice univoco `(ramo_id, emission_type, emission_seq, user_id)`
  - Stati espliciti: draft -> in_preparazione -> bloccata/emettibile -> emessa
- **Evidence Gate a livello emissione**:
  - EN 1090: certificati 3.1, WPS/WPQR, riesame tecnico, controllo finale
  - EN 13241: documentazione tecnica, verifiche sicurezza
  - GENERICA: nessun requisito normativo
- **Legacy adapter centralizzato**: `get_normative_branches()` con wrapping virtuale
- **Materializzazione lazy**: commesse legacy convertite in rami solo su azione utente
- **Vista gerarchia**: endpoint aggregato commessa + rami + emissioni
- **11 endpoint API**: 4 rami + 6 emissioni + 1 gerarchia
- **Frontend**: componente RamiNormativiSection nella CommessaHubPage
- **Test: 100% backend (21/21) + 100% frontend**

## Backlog Prioritizzato

### P0 — Immediato
- **Fase B: Evidence Gate avanzato** — Check reali per evidenze obbligatorie per emissione
  - Completare i check EN 13241 (collaudo forze, manuale uso)
  - UI upload/collegamento evidenze per emissione
  - Blocco emissione DOP/CE se gate NON OK
- **Auto-generazione rami da segmentazione confermata** — Integrazione Phase 2 con Fase A
  - Endpoint `genera-da-istruttoria` gia pronto, collegare al flusso Phase 2 frontend

### P1 — Prossimo
- **Fase C: Dashboard Cantiere Multilivello** — Vista commessa madre + rami + emissioni con progress tracker
- **Progress Tracker per Commessa Pre-Istruita** — Dashboard visuale con stato evidenze e controlli
- **Stability guard** deterministico per classificazione borderline

### P2
- Multi-Tenant SaaS
- ML Training automatico
- Alert costi reali > budget

### P3
- Unificazione PDF legacy
- Portale clienti read-only
- Fix warning minori (exhaustive-deps, hydration)
- Refactoring: split SettingsPage.js (1731 righe), split commesse.py (1330 righe)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

## Collezioni DB Nuove (Fase A)
- `commesse_normative`: rami normativi per commessa madre
- `emissioni_documentali`: emissioni progressive per ramo
- `counters`: contatori atomici (emission_{ramo_id}_{type})

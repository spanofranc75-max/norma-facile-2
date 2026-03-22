# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformità EN 1090-1 e viabilità commerciale come prodotto startup. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilità materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

**Pivot strategico**: da generatore documentale a copilota tecnico-normativo AI-driven.

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalità Implementate

### Core EN 1090 (Completo)
- Commesse CRUD con voci lavoro multi-normativa
- FPC: lotti materiale con tracciabilità colata -> cert 3.1 -> DDT
- Registro saldatura con WPS e qualifiche saldatori
- Riesame Tecnico (gate pre-produzione) con 12 check automatici
- Ispezioni, Controllo Finale, Fascicolo Tecnico
- DOP frazionata e automatica con PDF professionale

### CAM — Criteri Ambientali Minimi (Completato)
- Campi CAM su material_batches, calcolo conformità, CAM Alert, form frontend

### PDF Executive Professional (Completato)
- DOP EN 1090 (4 pagine), Etichetta CE, Dichiarazione CAM PNRR, Scheda Rintracciabilità

### Multi-Normativa (Completo)
- Executive Dashboard, Riesame Tecnico Selettivo

### Moduli Aggiuntivi (Completato)
- Scadenziario, Verbali ITT, Sopralluoghi, Perizie, Preventivatore AI
- DDT, Fatturazione, Analisi finanziaria, Notifiche, QR Code, Team management

### Motore di Istruttoria Automatica — Fasi P0.x (Completato)
- **P0.1 — Cockpit operativo**: Card Esito dominante, progress bar, bottoni rapidi contestuali
- **P0.15 — Dipendenze dinamiche**: applicabilita_engine.py, 4 rami
- **P0.25 — Domande contestuali**: 6 regole rule-based, stale management
- **P0.2 — Spiegabilità**: Box "Perché propone", "Punti da chiarire", linguaggio officina
- **P0.3 — Box "Se confermi la commessa"** (22/03/2026): 3 sezioni dinamiche

### P1 — Validazione Real-World (Completato 22/03/2026)
- Sistema completo di validazione su 8 preventivi reali
- Score globale: **81%** (dopo correzione ground truth)
- Classificazione: **7/8 (88%)** — sopra soglia 80%
- 1 FAIL residuo: PRV-2026-0002 (classificazione instabile su caso borderline)

### P1.1 — Segmentazione Normativa per Riga (Completato 22/03/2026)
- **segmentation_engine.py**: Classificazione per riga (keyword deterministico + GPT-4o)
  - Keyword rules: EN_13241 (cancello, portone, motorizzazione...), EN_1090 (struttura, trave, profili...), GENERICA (parapetto, manutenzione, sovrapprezzo...)
  - AI override per casi incerti
- **API**: POST /segmenta/{id} (analisi), POST /segmenta/{id}/review (conferma/bozza)
- **Frontend**: Sezione in IstruttoriaPage con:
  - Summary badges per normativa
  - Tabella per riga con dropdown per correzione manuale
  - Blocco conferma se righe INCERTE presenti
  - Official segmentation snapshot al salvataggio
- **Risultati test su PRV-2026-0021 (10 righe)**: EN_1090: 2, EN_13241: 3, GENERICA: 4, INCERTA: 1
- **Analisi 2 FAIL**: I 2 casi FAIL erano correttamente MISTA (ground truth aggiornato)

## Backlog Prioritizzato

### P0 — Immediato
- Migliorare estrazione tecnica (59%, soglia 60%) — parsing righe, vocabolario officina

### P1 — Prossimo
- **Phase 2 — Commessa Pre-Istruita** (limitata ai casi chiari: EN_1090, EN_13241, GENERICA puri)
  - NON per MISTA/borderline/classificazione incerta
- **Phase 3 — Evidence Gate**: Gate documenti finali

### P2
- Multi-Tenant, ML Training, Alerting

### P3
- Unificazione PDF, Portale Clienti, fix warning minori

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

## Issue Minori Pendenti
- (P3) Warning `exhaustive-deps` in WeldersPage.js
- (P3) Warning hydration in SopralluogoWizardPage.js e TracciabilitaMaterialiSection.js

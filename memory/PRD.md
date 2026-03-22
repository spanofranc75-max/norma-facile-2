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
- **P0.15 — Dipendenze dinamiche**: applicabilita_engine.py, 4 rami (saldatura/zincatura/montaggio/mista)
- **P0.25 — Domande contestuali**: 6 regole rule-based, stale management, endpoint dedicato
- **P0.2 — Spiegabilità**: Box "Perché propone", "Punti da chiarire", linguaggio officina
- **P0.3 — Box "Se confermi la commessa"** (Completato 22/03/2026):
  - 3 sezioni: "Verrà preparato" / "Resterà da completare" / "Non ancora emettibile"
  - Contenuto dinamico: mostra conferme mancanti, dati saldatura/terzista/posa se previsti
  - Titolo: "Se confermi la commessa" — tono operativo, asciutto
  - Visibile sempre quando l'istruttoria non è confermata (non solo quando tutte le risposte date)

### P1 — Validazione Real-World Motore AI (Completato 22/03/2026)
- **Infrastruttura di validazione** completa:
  - `validation_engine.py`: Ground truth per 8 preventivi reali, scoring multi-dimensionale
  - `routes/validation.py`: API endpoints (GET /set, POST /run/{id}, POST /run-batch, GET /results)
  - `ValidationPage.js`: UI con aggregato, scorecard individuali, run singolo/batch
  - Sidebar link "Validazione AI (P1)" sotto Certificazioni
- **Risultati validazione su 8 preventivi reali**:
  - Score globale: **75%**
  - Classificazione corretta: **6/8 (75%)**
  - Profilo: 81% | Estrazione: 59% | Domande: 100%
  - 2 FAIL: PRV-2026-0002 (Recinzione+cancelli→MISTA) e PRV-2026-0021 (Parapetti→MISTA) — casi borderline
- **Metriche e soglie**:
  - Classificazione: >=80% per produzione (attuale: 75%)
  - Profilo: >=70% per produzione (attuale: 81% OK)
  - Estrazione: >=60% per produzione (attuale: 59% borderline)
  - Domande: >=50% per produzione (attuale: 100% OK)

## Backlog Prioritizzato

### P0 — Immediato
- Analizzare i 2 FAIL della validazione P1 e migliorare il motore per i casi borderline (recinzione+cancelli, parapetti)
- Migliorare l'estrazione tecnica (attualmente 59%, soglia 60%)

### P1 — Prossimo
- **Phase 2 — Commessa Pre-Istruita Revisionata**: Generare commessa pre-compilata dalla conferma istruttoria
- **Phase 3 — Evidence Gate**: Gate che blocca emissione documenti finali senza evidenze

### P2
- Architettura Multi-Tenant: tenant_id su tutte le collection
- Training ML: Modello di stima dal Diario Produzione
- Alerting Intelligente: Notifica sforamento costi

### P3
- Unificazione PDF legacy (13 servizi)
- Portale Clienti (read-only)
- RBAC avanzato, QR Code migliorati
- Split file grandi (SettingsPage.js, commesse.py)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

## Issue Minori Pendenti
- (P3) Warning `exhaustive-deps` in WeldersPage.js
- (P3) Warning hydration in SopralluogoWizardPage.js e TracciabilitaMaterialiSection.js

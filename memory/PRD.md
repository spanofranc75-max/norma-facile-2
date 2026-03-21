# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Francesco vuole vendere l'app in abbonamento.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + qrcode

## Flusso Audit EN 1090 Completo (Testato)

### 1. Perizia AI → Preventivo → Commessa
- Upload foto → AI estrae materiali → Calcolo predittivo → Accetta → Commessa EN_1090 EXC2 auto
- **Filo**: preventivi → commesse (normativa, classe EXC, budget, distinta)

### 2. Riesame Tecnico (Safety Gate) — 12 checks
- 8 auto-checks: strumenti_tarati, attrezzature_idonee, saldatori_qualificati, wps_assegnate, materiali_confermati, consumabili_disponibili, documenti_aziendali, **itt_processi_qualificati**
- 4 manuali: disegni_approvati, normativa_verificata, tolleranza_calibro, exc_class
- **BLOCCA** approvazione se qualsiasi check fallisce
- **Fili**: instruments, attrezzature, welders, wps, material_batches, consumable_batches, company_documents, verbali_itt

### 3. Registro Saldatura
- CRUD con filtro saldatori per qualifica/processo valido
- **Filo**: welders → registro (solo saldatori idonei)

### 4. Tracciabilita Materiali
- Lotti con colata, certificato 3.1, DDT, fornitore
- Link DDT → batch automatico
- Verifica Coerenza (discrepanze colata/DDT)
- **Filo**: material_batches → riesame, DOP, verifica coerenza
- **BUG CORRETTO**: commessa_id non veniva salvato nel lotto (iteration 209)

### 5. Controllo Finale Pre-Spedizione
- 11 checks in 3 aree (VT, Dimensionale, Compliance)
- Auto-checks: vt_saldature_registro, vt_nc_chiuse, dim_strumenti_tarati
- **Filo**: registro_saldatura, report_ispezioni, instruments

### 6. Report Ispezioni VT/Dimensionali
- 10 checks VT (ISO 5817-C) + 8 checks DIM (EN 1090-2 B6/B8)
- PDF + firma digitale

### 7. DOP + Etichetta CE automatica
- DOP Auto: zero input manuale, raccoglie da riesame + batches + ispezioni + controllo_finale
- Etichetta CE 148x105mm: norma, certificato FPC, ente, EXC, DoP rif.
- **Fili**: riesame → DOP (EXC), material_batches → DOP (colate), ispezioni → DOP, controllo → DOP

### 8. Scadenziario Manutenzioni Unificato
- Aggrega instruments + attrezzature + ITT
- Badge impatto: Riesame, Controllo Finale
- **Filo**: instruments/attrezzature/ITT → scadenziario → visibilita proattiva

### 9. Verbali ITT
- CRUD per taglio_termico, taglio_meccanico, foratura, piegatura, punzonatura, raddrizzatura
- **Filo**: verbali_itt → Riesame (check itt_processi_qualificati)

## Test Eseguiti
- Iteration 206: DOP/CE unit tests — 12/12 pass
- Iteration 207: Scadenziario/ITT unit tests — 19/19 pass
- Iteration 208: E2E integration (10 flussi cross-module) — 34/34 pass
- Iteration 209: STRESS TEST RINA (4 scenari audit) — 28/28 pass
- **Bug corretto**: POST /api/fpc/batches non salvava commessa_id (catena rintracciabilita rotta)

## Credenziali Test
- User: user_e4012a8f48
- Session: d36a500823254076b5c583d6c1d903fa
- Commessa EN 1090: comm_sasso_marconi (C-2026-0012)

## Backlog

### P2 — Miglioramenti
- Training automatico ML dal Diario Produzione
- Alerting costi reali > budget

### P3 — Backlog Generale
- Unificazione PDF legacy, Export Excel, Portale clienti, RBAC, QR Code
- Split SettingsPage.js (1.731 righe)
- Split commesse.py (1.330 righe)

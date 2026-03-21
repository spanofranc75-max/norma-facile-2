# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Francesco vuole vendere l'app in abbonamento.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + qrcode

## Moduli Implementati
- Core: Commesse, Clienti, Preventivi, DDT, Fatturazione, Diario Produzione, Fascicolo CE, WPS, Magazzino
- AI Vision Disegni, Preventivatore Predittivo (+ Stima Rapida Manuale)
- KPI Dashboard + Calibrazione ML

### Flusso Audit EN 1090

#### FASE 1 — Riesame Tecnico (completata)
- 11 check (7 auto + 4 manuali), Gate AVVIO_PRODUZIONE bloccante, Firma digitale + PDF

#### FASE 2 — Registro Saldatura + Link DDT (completata)
- Registro Saldatura CRUD con filtro saldatori per processo/patentino
- Tracciabilita Materiali con auto-link DDT → batch

#### Checklist Fine Lavori + Soglia Calibro (completata)
- 11 check in 3 aree (VT ISO 5817-C, Dimensionale B6/B8, Compliance CE/DOP)
- Soglia accettabilita configurabile per strumento (default Calibro ±0.1mm)

#### Fili Conduttori — Unificazione Dati (21 Mar 2026)
- **Filo Rintracciabilita**: `material_batches` = unica fonte di verita (non piu `fpc_batches` separato)
  - Rintracciabilita, Riesame, Controllo Finale tutti leggono da `material_batches`
- **Filo Qualifica**: Saldatori filtrati per patentino valido nel Registro Saldatura
- **Filo Manutenzione**: Riesame Tecnico blocca se strumenti/attrezzature scaduti
  - Soglia tolleranza configurabile per strumento
- **Filo Documentale**: DOP auto-popola classe_esecuzione dal Riesame + rintracciabilita da `material_batches`
  - Sezione "3b. Rintracciabilita Materiali" aggiunta automaticamente nel PDF DOP

## Credenziali Test
- User: user_97c773827822
- Session: d36a500823254076b5c583d6c1d903fa (user_sessions collection)
- Commessa test: com_loiano_cims_2026

## Backlog Prioritario

### P0 — Richiesti dall'utente (prossimi)
- Verifica Coerenza Rintracciabilita — Pulsante confronto lotti vs DDT con segnalazione discrepanze
- Template Processo 111 — PDF richiesta preventivo laboratorio prove (UNI EN ISO 15614-1, EXC2, S275/S355)

### P1 — Fase 3 Audit
- Report Ispezioni VT/Dimensionali con checklist ISO 5817
- DOP + Etichetta CE automatica (enhancement gate_certification)

### P2 — Fase 4 + Miglioramenti
- Verbali ITT (qualifica taglio e foratura)
- Scadenziario Manutenzioni Digitalizzato (calendari trimestrali/annuali + alert)
- Training automatico ML
- Alerting costi > budget

### P3 — Backlog Generale
- Unificazione PDF, Export Excel
- Portale clienti, RBAC, QR Code
- Onboarding Wizard

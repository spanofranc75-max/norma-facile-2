# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Francesco vuole vendere l'app in abbonamento.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + qrcode

## Moduli Implementati — Flusso Audit EN 1090

### FASE 1 — Riesame Tecnico (completata)
- 12 check (8 auto + 4 manuali), Gate AVVIO_PRODUZIONE bloccante, Firma digitale + PDF
- Nuovo check: `itt_processi_qualificati` (auto) verifica ITT validi per taglio/foratura

### FASE 2 — Registro Saldatura + Link DDT (completata)
- Registro Saldatura CRUD con filtro saldatori per processo/patentino
- Tracciabilita Materiali con auto-link DDT -> batch

### Checklist Fine Lavori + Soglia Calibro (completata)
- 11 check in 3 aree (VT, Dimensionale, Compliance), firma
- Soglia accettabilita configurabile (Calibro +/-0.1mm)

### Fili Conduttori — Unificazione Dati (completata)
- `material_batches` = unica fonte di verita
- DOP auto-popola EXC + rintracciabilita
- Tutti i fili (Rintracciabilita, Qualifica, Manutenzione, Documentale) connessi

### Verifica Coerenza + Template 111 (completata)
- Confronto automatico lotti vs DDT con discrepanze
- PDF richiesta preventivo laboratorio per processo 111

### Report Ispezioni VT/Dimensionali (completata)
- 10 check VT (ISO 5817-C) + 8 check DIM (EN 1090-2 B6/B8)
- PDF rapporto con tabelle VT+DIM + firma

### DOP + Etichetta CE automatica EN 1090 (21 Mar 2026)
- `POST /api/fascicolo-tecnico/{cid}/dop-automatica` — DOP senza input manuale
- `GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf` — Etichetta CE 148x105mm
- Frontend: bottoni "DOP Auto" + "Etichetta CE" solo per EN_1090
- Test: 100% (iteration 206)

### Scadenziario Manutenzioni Unificato (21 Mar 2026)
- `GET /api/scadenziario-manutenzioni` — Aggrega instruments + attrezzature + ITT
- KPI: totale/scaduti/in_scadenza/prossimi/conformi
- Badge impatto: mostra quali moduli sono bloccati (Riesame, Controllo Finale)
- Frontend: `/manutenzioni` con KPI cliccabili come filtro + tabella urgenza
- Fili: instruments -> Riesame + Controllo Finale, attrezzature -> Riesame, ITT -> Riesame
- Test: 100% (iteration 207)

### Verbali ITT — Initial Type Testing (21 Mar 2026)
- `POST/GET/DELETE /api/verbali-itt` — CRUD con prove, esito, processo
- `POST /api/verbali-itt/{id}/firma` — Firma digitale
- `GET /api/verbali-itt/{id}/pdf` — PDF WeasyPrint
- `GET /api/verbali-itt/check-validita` — Report processi qualificati/scaduti
- Processi: taglio_termico, taglio_meccanico, foratura, piegatura, punzonatura, raddrizzatura
- **Filo conduttore**: Riesame Tecnico (check `itt_processi_qualificati`) verifica che taglio e foratura siano qualificati
- Frontend: `/verbali-itt` con form, tabella, PDF, banner filo conduttore
- Test: 100% (iteration 207)

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

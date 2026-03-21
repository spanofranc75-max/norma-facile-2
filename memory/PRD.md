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
- 11 check (7 auto + 4 manuali), Gate AVVIO_PRODUZIONE bloccante, Firma digitale + PDF

### FASE 2 — Registro Saldatura + Link DDT (completata)
- Registro Saldatura CRUD con filtro saldatori per processo/patentino
- Tracciabilita Materiali con auto-link DDT → batch

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

### Report Ispezioni VT/Dimensionali (21 Mar 2026)
- 10 check VT (ISO 5817-C) + 8 check DIM (EN 1090-2 B6/B8)
- PDF rapporto con tabelle VT+DIM + firma
- Integrazione con Controllo Finale (auto-check)

### DOP + Etichetta CE automatica EN 1090 (21 Mar 2026)
- **POST /api/fascicolo-tecnico/{cid}/dop-automatica** — Crea DOP con zero input manuale
  - Auto-raccoglie: EXC da Riesame, lotti da material_batches, stato Riesame/Ispezioni/Controllo Finale
  - Flag `automatica: true` abilita sezioni extra nel PDF (Riesame, Ispezioni VT/DIM, Controllo Finale)
- **GET /api/fascicolo-tecnico/{cid}/etichetta-ce-1090/pdf** — Genera Etichetta CE 148x105mm
  - Auto-popola: norma, certificato FPC, ente notificato, classe EXC, DoP riferimento
- **Frontend:** Bottoni "DOP Auto" (indigo) e "Etichetta CE" (slate) visibili solo per EN_1090
- Test: 100% (12/12 backend + frontend — iteration 206)

## Credenziali Test
- User: user_e4012a8f48
- Session: d36a500823254076b5c583d6c1d903fa
- Commessa EN 1090: comm_sasso_marconi (C-2026-0012)

## Backlog

### P1 — Prossimi
- Scadenziario Manutenzioni Digitalizzato (calendario trimestrali/annuali + alert)
- Verbali ITT (qualifica taglio e foratura)

### P2 — Miglioramenti
- Training automatico ML dal Diario Produzione
- Alerting costi reali > budget

### P3 — Backlog Generale
- Unificazione PDF legacy, Export Excel, Portale clienti, RBAC, QR Code
- Split SettingsPage.js (1.731 righe)
- Split commesse.py (1.330 righe)

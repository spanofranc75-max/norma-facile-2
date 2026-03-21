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

### Flusso Audit EN 1090 (Completo Fase 1-2 + Operativo)

#### FASE 1 — Riesame Tecnico
- 11 check (7 auto + 4 manuali), Gate AVVIO_PRODUZIONE bloccante, Firma digitale + PDF

#### FASE 2 — Registro Saldatura + Link DDT
- Registro Saldatura CRUD con filtro saldatori per processo/patentino
- Tracciabilita Materiali con auto-link DDT → batch

#### Checklist Fine Lavori + Soglia Calibro
- 11 check in 3 aree (VT ISO 5817-C, Dimensionale B6/B8, Compliance CE/DOP)
- Soglia accettabilita configurabile per strumento (default Calibro ±0.1mm)

#### Fili Conduttori — Unificazione Dati
- `material_batches` = unica fonte di verita
- DOP auto-popola classe EXC dal Riesame + rintracciabilita da material_batches
- Tutti i fili (Rintracciabilita, Qualifica, Manutenzione, Documentale) connessi

#### Verifica Coerenza Rintracciabilita (21 Mar 2026)
- **Backend `fpc.py`:** `GET /api/fpc/batches/verifica-coerenza/{commessa_id}`
  - Confronto automatico lotti vs DDT
  - Rileva: colata mancante, certificato 3.1 mancante, DDT non collegato, descrizione mismatch, quantita mismatch, colata mismatch
  - Riepilogo con totale/conformi/critici/attenzione/pct_conforme
- **Frontend `TracciabilitaMaterialiSection.js`:** Pulsante "Verifica Coerenza" + pannello risultati con stats e dettaglio per lotto

#### Template PDF Processo 111 (21 Mar 2026)
- **Backend `template_111.py`:** 2 endpoint:
  - `GET /api/template-111/preview/{commessa_id}` — Preview dati
  - `GET /api/template-111/pdf/{commessa_id}` — Download PDF professionale
- Contenuto: richiesta preventivo laboratorio prove per qualifica processo 111 (SMAW)
  - UNI EN ISO 15614-1, EXC2, acciai S275/S355
  - Tabella prove richieste (VT, RT/UT, piega, trazione, resilienza, macro, durezza)
  - Auto-population dati aziendali da company_settings e classe EXC da Riesame
- **Frontend:** Pulsante "Template 111" nella barra azioni CommessaHubPage

## Credenziali Test
- User: user_97c773827822
- Session: d36a500823254076b5c583d6c1d903fa (user_sessions collection)
- Commessa test: com_loiano_cims_2026

## Backlog

### P1 — Fase 3 Audit
- Report Ispezioni VT/Dimensionali con checklist ISO 5817
- DOP + Etichetta CE automatica (enhancement gate_certification)

### P2 — Miglioramenti
- Scadenziario Manutenzioni Digitalizzato (calendari trimestrali/annuali + alert)
- Verbali ITT (qualifica taglio e foratura)
- Training automatico ML
- Alerting costi > budget

### P3 — Backlog Generale
- Unificazione PDF, Export Excel
- Portale clienti, RBAC, QR Code
- Onboarding Wizard

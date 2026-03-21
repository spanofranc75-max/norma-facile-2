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
- Soglia accettabilita configurabile (Calibro ±0.1mm)

### Fili Conduttori — Unificazione Dati (completata)
- `material_batches` = unica fonte di verita
- DOP auto-popola EXC + rintracciabilita
- Tutti i fili (Rintracciabilita, Qualifica, Manutenzione, Documentale) connessi

### Verifica Coerenza + Template 111 (completata)
- Confronto automatico lotti vs DDT con discrepanze
- PDF richiesta preventivo laboratorio per processo 111

### Report Ispezioni VT/Dimensionali (21 Mar 2026)
- **Backend `report_ispezioni.py`:** 4 endpoint:
  - `GET /api/report-ispezioni/{commessa_id}` — 10 check VT (ISO 5817-C) + 8 check DIM (EN 1090-2 B6/B8)
  - `POST /api/report-ispezioni/{commessa_id}` — Salva risultati ispezioni
  - `POST /api/report-ispezioni/{commessa_id}/approva` — Firma (validazione: tutti i 18 check compilati)
  - `GET /api/report-ispezioni/{commessa_id}/pdf` — PDF rapporto con tabelle VT+DIM + firma
- **VT Checks (10):** Cricche, Porosita, Inclusioni, Fusione, Penetrazione, Sottosquadro, Sovrametallo, Slivellamento, Spruzzi, Aspetto generale
- **DIM Checks (8):** Lunghezze B6, Rettilineita B6, Squadratura B6, Interassi fori B8, Diametro fori, Posizione piastre, Altezza sezione, Gola saldatura
- **Frontend `ReportIspezioniSection.js`:** Aree tab VT/DIM, bottoni OK/NOK, campi Misura+Note, Save/Approve/PDF
- **Integrazione Controllo Finale:** Il check `vt_nc_chiuse` ora legge da `report_ispezioni` (auto-check "Report VT approvato")
- DB Collection: `report_ispezioni`
- Test: 100% (22/22 — iteration 205)

## Credenziali Test
- User: user_97c773827822
- Session: d36a500823254076b5c583d6c1d903fa
- Commessa test: com_loiano_cims_2026

## Backlog

### P1 — Fase 3 (prossimo)
- DOP + Etichetta CE automatica (enhancement gate_certification)

### P2 — Miglioramenti
- Scadenziario Manutenzioni Digitalizzato
- Verbali ITT (qualifica taglio e foratura)
- Training automatico ML, Alerting costi > budget

### P3 — Backlog Generale
- Unificazione PDF, Export Excel, Portale clienti, RBAC, QR Code

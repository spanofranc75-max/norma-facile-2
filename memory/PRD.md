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
- 11 check (7 auto + 4 manuali) raggruppati per sezione
- Gate AVVIO_PRODUZIONE bloccante
- Firma digitale + PDF Verbale

#### FASE 2 — Registro Saldatura + Link DDT (21 Mar 2026)
- **Registro Saldatura**: CRUD completo con filtro saldatori per processo/patentino
  - Backend: `/api/registro-saldatura/{commessa_id}` (GET/POST/PUT/DELETE) + `/saldatori-idonei`
  - Frontend: `RegistroSaldaturaSection` in CommessaHubPage
- **Tracciabilita Materiali**: Auto-collegamento DDT → batch FPC
  - Backend: `/api/fpc/batches/link-ddt/{commessa_id}` + `/rintracciabilita/{commessa_id}`
  - Frontend: `TracciabilitaMaterialiSection` in CommessaHubPage

#### Blocco Audit — Checklist + Soglia Calibro (21 Mar 2026)
- **Controllo Finale Pre-Spedizione EN 1090-2:2024**: 11 check in 3 macro-aree:
  - Visual Testing (4): VT 100% ISO 5817-C, difetti accettabili, saldature registrate, NC chiuse
  - Dimensionale (3): Quote critiche B6/B8, tolleranze montaggio, strumenti tarati
  - Compliance (4): Etichetta CE, DOP, colate coerenti, fascicolo completo
  - 5 check manuali (checkbox) + 6 auto (verifiche real-time su DB)
  - Firma digitale + approvazione bloccante
  - Backend: `/api/controllo-finale/{commessa_id}` (GET/POST/POST approva)
  - Frontend: `ControlloFinaleSection` in CommessaHubPage
  - DB Collection: `controlli_finali`
- **Soglia Accettabilita Configurabile per Strumento** (Racc. RINA n.2):
  - Campo `soglia_accettabilita` + `unita_soglia` (mm/% /N/bar) nel modello Instrument
  - Default Calibro Borletti: ±0.1 mm
  - Alert "Fuori Tolleranza" nel Riesame Tecnico (check dinamico per strumento)
  - Badge viola sulle card strumenti nella InstrumentsPage
  - Sezione form soglia visibile solo per type=misura

### Sicurezza & Conformita
- Documenti globali con scadenze persistenti (PATCH)
- Allegati Tecnici POS (Rumore, Vibrazioni, MMC) con toggle
- Dashboard Conformita + Fascicolo Aziendale ZIP + Validazione Preventiva Commessa

### Manuale Utente PDF
- 7 capitoli navigabili + 8 FAQ + PDF white-label con QR Code

## Credenziali Test
- User: user_97c773827822
- Session: d36a500823254076b5c583d6c1d903fa (user_sessions collection)
- Commessa test: com_loiano_cims_2026

## Backlog Prioritario

### P0 — Richiesti dall'utente (prossimi)
- (P0) Verifica Coerenza Rintracciabilita — Pulsante che confronta lotti FPC vs DDT e segnala discrepanze
- (P0) Template Processo 111 — PDF richiesta preventivo laboratorio (UNI EN ISO 15614-1, EXC2, S275/S355)

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

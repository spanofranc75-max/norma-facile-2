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

### Flusso Audit EN 1090 (21 Mar 2026)
- **Riesame Tecnico Bloccante**: 11 check (7 auto + 4 manuali) raggruppati per sezione:
  - Contratto: Classe EXC, Materiali confermati
  - Progettazione: Disegni validati, Tolleranze EN 1090-2
  - Saldatura: WPS assegnate, Saldatori qualificati
  - Attrezzature: Manutenzione valida, Strumenti tarati, Tolleranza calibro RINA <5%
  - Sicurezza: Documenti aziendali validi
  - Approvvigionamento: Consumabili disponibili
- **Gate AVVIO_PRODUZIONE**: Commessa non avviabile senza riesame approvato
- **Firma digitale**: Nome, ruolo, timestamp — immutabile dopo approvazione
- **PDF Verbale di Riesame**: Con logo, checklist, firma, prova documentale per audit
- Backend: `/api/riesame/{id}` (GET/POST), `/approva` (POST), `/pdf` (GET)
- DB Collection: `riesami_tecnici`

### FASE 2 — Registro Saldatura + Link DDT (21 Mar 2026)
- **Registro Saldatura per Commessa**: Log completo saldature con giunto, saldatore, WPS, data, esito VT
  - Filtro saldatori idonei per processo/patentino valido
  - Statistiche: conformi/non conformi/da eseguire
  - CRUD completo con validazione
  - Backend: `/api/registro-saldatura/{commessa_id}` (GET/POST/PUT/DELETE), `/saldatori-idonei` (GET)
  - DB Collection: `registro_saldatura`
  - Frontend: `RegistroSaldaturaSection` integrato in CommessaHubPage
- **Link DDT → Lotti FPC**: Auto-associazione colata da DDT di carico a batch FPC
  - Matching per numero colata (forte) e profilo descrizione (debole)
  - Scheda rintracciabilita materiali con stato collegamento
  - Backend: `/api/fpc/batches/link-ddt/{commessa_id}` (POST), `/rintracciabilita/{commessa_id}` (GET)
  - Frontend: `TracciabilitaMaterialiSection` integrato in CommessaHubPage

### Sicurezza & Conformita
- Documenti globali con scadenze persistenti (PATCH)
- Allegati Tecnici POS (Rumore, Vibrazioni, MMC) con toggle
- Dashboard Conformita + Fascicolo Aziendale ZIP + Validazione Preventiva Commessa
- Risorse Umane + Matrice Scadenze

### Manuale Utente PDF
- 7 capitoli navigabili + 8 FAQ + PDF white-label con QR Code

### Moduli gia esistenti da VALORIZZARE (non ricostruire):
- `instruments.py`: Strumenti con scadenze taratura
- `attrezzature.py`: Attrezzature + check taratura
- `qualita.py`: Controlli visivi ISO 5817 + Registro NC
- `gate_certification.py`: DOP + Etichetta CE + Dichiarazione CE
- `consumables.py`: Consumabili con lotto e assegnazione commessa
- `distinta.py`: Distinta base con profili

## Credenziali Test
- User: user_97c773827822
- Session: d36a500823254076b5c583d6c1d903fa (user_sessions collection)
- Commessa test: com_loiano_cims_2026

## Backlog — Piano Audit EN 1090
- (P1-FASE3) Report Ispezioni VT/Dimensionali con checklist ISO 5817
- (P1-FASE3) DOP + Etichetta CE automatica (enhancement del gate_certification esistente)
- (P2-FASE4) Verbali ITT (qualifica taglio e foratura)

## Backlog Generale
- (P1) Integrazione email "Invia a CIMS"
- (P1) Training automatico ML
- (P1) Alerting costi > budget
- (P2) Unificazione PDF, Export Excel
- (P3) Portale clienti, RBAC, QR Code

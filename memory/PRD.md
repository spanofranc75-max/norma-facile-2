# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale completo per carpenterie metalliche conformi EN 1090, EN 13241 e ISO 3834.

## Architettura
- **Frontend**: React + Tailwind CSS + Shadcn UI (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **AI**: GPT-4o Vision tramite emergentintegrations (Emergent LLM Key)
- **PDF**: WeasyPrint
- **Firma**: react-signature-canvas

## Funzionalita Implementate

### Core
- CRUD Commesse, Preventivi, Fatture, DDT, Clienti, Fornitori
- FPC, DOP, Etichette CE, Qualifica Saldatori, WPS, Strumenti

### Produzione
- Diario produzione PIN, Timer START/STOP, Safety Gate D.Lgs 81/08

### Montaggio (Fase 4)
- Diario 6 step, Serraggio Nm automatico, Firma digitale, Varianti, Scadenzario Attrezzature

### Sicurezza & PNRR
- Profilo Sicurezza, DNSH AI, Checklist cantiere, Export CSE

### Workflow Engine
- Safety Gate, Post-Sales (firma -> CE + QR + Manutenzione), Pulsante Magico

### Amministrazione
- Backup/Restore, Migrazione, Team RBAC, Notifiche email, Archivio Storico

### Refactoring (2026-03-20)
- SettingsPage.js: 1732 -> 185 righe (11 componenti)

### AI Vision Disegni (2026-03-20)
- Estrazione bulloneria da disegni + proposta RdP automatica

### DoP Frazionata (2026-03-20)
- DoP multiple /A /B /C, blocco se C/L non rientrati

### SAL e Acconti (2026-03-20)
- SAL automatico (ore 50%, fasi 30%, C/L 20%), fatturazione acconto

### Conto Lavoro Migliorato (2026-03-20)
- DDT Out/In + certificato trattamento -> Pulsante Magico cap. Trattamenti Superficiali

### Preventivatore Predittivo AI (2026-03-20)
- **Upload disegno -> AI Vision** estrae profili, piastre, bulloneria con pesi
- **Motore Prezzi Storici**: incrocio con DDT/fatture acquisto per costo/kg reale
- **ML Stima Ore**: regressione lineare su commesse chiuse + tabella parametrica (leggera/media/complessa/speciale)
- **Margini Differenziati**: percentuali separate per Materiali, Manodopera, C/L con margine globale medio
- **Workflow**: Preventivo accettato -> Commessa auto-generata con Budget, Ore, Distinta Materiali (RdP)
- **Frontend**: Wizard 4-step, pagina /preventivatore, sidebar "AI Predittivo"

## Schema DB Chiave
- commesse, preventivi, invoices, clients, fornitori
- fpc_projects, welders, instruments, ddt
- diario_produzione, diario_montaggio, bulloneria_ddt
- sicurezza_corsi_operatore, attrezzature, manutenzioni_programmate, targhe_ce
- commessa_documents, doc_page_index, archivio_exports
- dop_frazionate, sal_acconti
- **preventivatore_analyses**: analisi AI temporanee disegni
- **company_costs**: costo orario aziendale

## Backlog

### P0 (Completato)
- [x] Refactoring SettingsPage
- [x] AI Vision Disegni + RdP
- [x] DoP Frazionata
- [x] SAL e Acconti
- [x] Conto Lavoro completo
- [x] Preventivatore Predittivo AI

### P2
- [ ] RBAC granulare
- [ ] Portale clienti read-only
- [ ] Smistatore Avanzato scorte/sfridi

### P3
- [ ] Export Excel analisi costi
- [ ] Unificazione 13 servizi PDF legacy
- [ ] Notifiche WhatsApp
- [ ] Dashboard KPI tempo reale

## Credenziali Test
- Operatori Officina: Ahmed (PIN 1234), Karim (PIN 5678)
- Auth: Google OAuth tramite Emergent

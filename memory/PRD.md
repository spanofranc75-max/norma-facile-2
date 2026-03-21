# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale completo per carpenterie metalliche conformi EN 1090, EN 13241 e ISO 3834.

## Architettura
- **Frontend**: React + Tailwind CSS + Shadcn UI + Recharts (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **AI**: GPT-4o Vision tramite emergentintegrations (Emergent LLM Key)
- **PDF**: WeasyPrint | **Firma**: react-signature-canvas

## Funzionalita Implementate (Completo)

### Core ERP
- CRUD Commesse, Preventivi, Fatture, DDT, Clienti, Fornitori
- FPC, DOP, Etichette CE, Saldatori, WPS, Strumenti, Catalogo Profili

### Produzione
- Diario produzione PIN, Timer, Safety Gate D.Lgs 81/08

### Montaggio (Fase 4)
- Diario 6 step, Serraggio Nm auto, Firma digitale, Varianti, Scadenzario Attrezzature

### Sicurezza & PNRR
- Profilo Sicurezza, DNSH AI, Checklist cantiere, Export CSE

### Workflow Engine
- Safety Gate, Post-Sales (CE + QR + Manutenzione), Pulsante Magico, Blocco DoP se C/L non rientrati

### Amministrazione
- Backup/Restore, Migrazione, Team RBAC, Notifiche, Archivio Storico
- SettingsPage refactorizzato (11 componenti)

### AI Vision (2026-03-20)
- Estrazione bulloneria da disegni + RdP automatica
- Smistatore Intelligente certificati multi-pagina

### Contabilita Industriale (2026-03-20)
- **DoP Frazionata**: Multiple /A /B /C, blocco se C/L non rientrati
- **SAL e Acconti**: SAL automatico + fatturazione acconto
- **Conto Lavoro**: DDT Out/In + certificato trattamento -> Pulsante Magico

### Preventivatore Predittivo AI (2026-03-20)
- Upload disegno -> AI estrae materiali con pesi da tabella 60+ profili
- Motore Prezzi Storici da DDT/fatture acquisto
- ML Stima Ore: regressione lineare + tabella parametrica
- Margini Differenziati: Mat / Mano / C/L separati
- Workflow: Preventivo accettato -> Commessa auto con Budget + Ore + RdP

### Dashboard KPI con Confidence Score (2026-03-21)
- **Accuracy Score AI**: Gauge circolare con punteggio globale (ore 60% + costi 40%)
- **Trend Accuratezza**: Grafico lineare evoluzione mensile
- **Top 3 Scostamenti**: Commesse dove le stime AI hanno sbagliato di piu
- **Marginalita Reale**: Grafico a barre fatturato vs costo reale per commessa
- **Performance Fornitori C/L**: Lavorazioni totali, in corso, giorni medi per fornitore
- **Tempi Medi**: h/ton per tipologia struttura (leggera/media/complessa)
- **Overview**: 7 KPI principali (commesse, preventivi AI, fatturato, C/L attivi, score)
- Pagina `/kpi` con 7 endpoint backend dedicati

## Schema DB
- commesse, preventivi, invoices, clients, fornitori, fpc_projects
- welders, instruments, ddt, diario_produzione, diario_montaggio
- bulloneria_ddt, sicurezza_corsi_operatore, attrezzature
- manutenzioni_programmate, targhe_ce, commessa_documents
- doc_page_index, archivio_exports
- dop_frazionate, sal_acconti
- preventivatore_analyses, company_costs

## Backlog

### P0 (Tutto Completato)
- [x] Tutti i moduli core, workflow, AI, contabilita, preventivatore, KPI

### P2
- [ ] RBAC granulare
- [ ] Portale clienti read-only
- [ ] Smistatore Avanzato scorte/sfridi

### P3
- [ ] Export Excel analisi costi
- [ ] Unificazione 13 servizi PDF legacy
- [ ] Notifiche WhatsApp

## Credenziali Test
- Operatori: Ahmed (PIN 1234), Karim (PIN 5678)
- Auth: Google OAuth

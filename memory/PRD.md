# Norma Facile 2.0 — Product Requirements Document

## Problema Originale
CRM/ERP per fabbri e carpenterie metalliche. Gestione completa di commesse, fatturazione, certificazioni CE (EN 1090 per strutture, EN 13241 per cancelli), tracciabilita' materiali, quality hub.

## Utente Target
Titolari e responsabili di officine di carpenteria metallica in Italia.

## Lingua
Italiano (l'utente comunica esclusivamente in italiano).

---

## Architettura
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + pypdf
- **AI OCR**: OpenAI GPT-4o Vision (Emergent LLM Key)
- **Email**: Resend
- **Invoicing**: Fatture in Cloud (SDI) — parzialmente integrato, in attesa di token API utente

---

## Funzionalita' Implementate

### Core
- Gestione commesse con macchina a stati event-driven + Kanban
- Preventivi con calcolo termico (Ecobonus), fatturazione progressiva
- Clienti/Fornitori CRM
- Fatturazione con numerazione fiscale
- DDT (vendita, conto lavoro)
- Distinta materiali con catalogo profili
- Rilievi in cantiere

### Qualita' e Compliance
- **Quality Hub**: Documenti, Strumenti, Saldatori, Audit/NC
- **EN 1090 (Strutture)**: FPC, WPS, qualifiche saldatori, tracciabilita' materiali, CAM
- **EN 13241 (Cancelli)**: DoP, analisi rischi, prove forza, etichetta CE, registro manutenzione
- **Smart Quote Analysis**: Analisi automatica keyword preventivo per routing normativa
- **Split Commessa**: Gestione preventivi misti EN 1090 + EN 13241 con creazione 2 commesse separate (2026-03-02)
- **Smart ISO 3834 Consumables**: Auto-rilevamento consumabili saldatura da fatture con assegnazione a commesse (2026-03-02)
- **Quality Score adattivo**
- **Dashboard Sostenibilita' CO2**

### Controllo Costi e Finanza
- **Controllo Costi**: Pagina 2 colonne con inbox fatture (mock + reali) + form imputazione a commesse/magazzino/spese generali (2026-03-02)
- **Analisi Finanziaria Commessa**: Card nel CommessaHub con Preventivo vs Costi Reali = Margine (2026-03-02)
- **Categorie Costo**: Materiale Ferroso, Lavorazione Esterna, Consumabili, Trasporti
- **Mock Data**: 5 fatture simulate realistiche (Acciaierie Venete, Ferramenta Rossi, Zincatura Nord, ServiceSaldatura, Trasporti Bianchi)

### Operativita'
- Approvvigionamento (RdP, OdA, arrivi materiale con Cert. 3.1)
- Produzione (fasi, avanzamento)
- Conto Lavoro (verniciatura, zincatura, sabbiatura) con DDT automatico
- Consegne con pacchetto PDF (DDT + DoP + CE)
- AI OCR certificati 3.1 con GPT-4o Vision
- Fascicolo Tecnico Unico (PDF aggregato)
- Scheda Rintracciabilita' Materiali EN 1090

### Migrazione e Import
- Sistema migrazione dati one-click da vecchia app Emergent
- UI migrazione in pagina Impostazioni

---

## Backlog Prioritizzato

### P0 — In Attesa
- Integrazione Fatture in Cloud (Scadenziario) — BLOCCATO su token API utente

### P1 — Prossimi
- Attivazione import reale fatture quando token disponibile (switch da mock a reale)

### P2 — Futuri
- Export CSV distinta di taglio per CNC
- Stato "SOSPESA" per commesse
- PWA per modalita' offline
- Migrazione certificati Base64 → object storage
- Versionamento fatture e fascicoli tecnici

---

## Ultimo Aggiornamento: 2026-03-02
- Implementata feature "Controllo Costi" con pagina dedicata, mock data, e imputazione a commesse
- Implementata "Analisi Finanziaria" nel CommessaHub (Preventivo - Costi = Margine)
- 19/22 test backend + frontend E2E per Controllo Costi (3 skipped)
- Split Commessa: 15/15 test
- Smart Consumables: 27/27 test

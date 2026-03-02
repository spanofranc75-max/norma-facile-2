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
- **Split Commessa**: Gestione preventivi misti EN 1090 + EN 13241 con creazione automatica di 2 commesse separate (2026-03-02)
- **Smart ISO 3834 Consumables**: Auto-rilevamento consumabili saldatura (fili, gas, elettrodi) da fatture fornitore con assegnazione automatica a commesse compatibili (2026-03-02)
- **Quality Score adattivo**
- **Dashboard Sostenibilita' CO2**

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
- UI per Imputazione Costi (modale su FattureRicevutePage, endpoint POST /api/fatture-ricevute/{id}/imputa gia' presente)

### P2 — Futuri
- Export CSV distinta di taglio per CNC
- Stato "SOSPESA" per commesse
- PWA per modalita' offline
- Migrazione certificati Base64 → object storage
- Versionamento fatture e fascicoli tecnici

---

## Ultimo Aggiornamento: 2026-03-02
- Implementata feature "Split Commessa" per preventivi misti (EN 1090 + EN 13241)
- Implementata feature "Smart ISO 3834 Consumable Traceability" — auto-import consumabili da fatture con assegnazione intelligente
- 27/27 test backend + frontend E2E verificato per consumabili
- 15/15 test backend per Split Commessa
- Bug fix: normativa_target default, analyze-invoice query fr_id

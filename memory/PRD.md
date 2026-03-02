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
- **Invoicing**: Fatture in Cloud (SDI) — ATTIVO, Company ID 1398737

---

## Funzionalita' Implementate

### Core
- Gestione commesse con macchina a stati event-driven + Kanban
- Preventivi con calcolo termico (Ecobonus), fatturazione progressiva
- Clienti/Fornitori CRM, Fatturazione, DDT, Distinte, Rilievi

### Qualita' e Compliance
- Quality Hub, EN 1090 (Strutture), EN 13241 (Cancelli)
- Smart Quote Analysis + Split Commessa per preventivi misti
- Smart ISO 3834 Consumables (auto-import da fatture)
- Quality Score adattivo, Dashboard Sostenibilita' CO2

### Controllo Costi e Finanza
- Controllo Costi con pagina dedicata (mock + reali)
- Analisi Finanziaria Commessa (Margine Reale)
- Scadenziario (dashboard scadenze)

### Amministrazione
- **Backup & Restore**: Export JSON completo di 19 collezioni, restore con merge sicuro (2026-03-02)
- Migrazione dati da vecchia app
- Integrazione Fatture in Cloud ATTIVA (Company ID 1398737, token aggiornato 2026-03-02)

---

## Backlog Prioritizzato

### P1 — Prossimi
- Import reale fatture ricevute da FIC (endpoint sync-fic gia' implementato)

### P2 — Futuri
- Export CSV distinta di taglio per CNC
- Stato "SOSPESA" per commesse
- PWA per modalita' offline
- Migrazione certificati Base64 → object storage
- Versionamento fatture e fascicoli tecnici

---

## Ultimo Aggiornamento: 2026-03-02
- Token Fatture in Cloud aggiornato e verificato (STEEL PROJECT DESIGN S.R.L.S.)
- Company ID corretto: 1398737
- Implementato modulo Backup & Restore (26/26 test)
- Controllo Costi (19/22 test), Split Commessa (15/15), Consumabili (27/27)

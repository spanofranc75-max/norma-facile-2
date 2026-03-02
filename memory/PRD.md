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

## Brand Identity
- **Palette**: Navy #0F172A, Steel Grey #64748B, Lime Accent #84CC16
- **Logo**: "1090" con "10" bianco e "90" grigio acciaio + "NORMA FACILE" in lime/grigio
- **Stile**: Dark & Industrial, B2B, Split Screen login

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
- Backup & Restore: Export JSON completo 19 collezioni
- Migrazione dati da vecchia app
- Fatture in Cloud ATTIVA (Company ID 1398737)

### UI/UX
- **Landing Page redesign**: Split Screen Dark Industrial con palette Navy/Steel/Lime (2026-03-02)

---

## Backlog Prioritizzato

### P1 — Prossimi
- Import reale fatture ricevute da FIC (endpoint sync-fic implementato)

### P2 — Futuri
- Export CSV distinta di taglio per CNC
- Stato "SOSPESA" per commesse
- PWA per modalita' offline
- Migrazione certificati Base64 → object storage
- Versionamento fatture e fascicoli tecnici

---

## Ultimo Aggiornamento: 2026-03-02
- Redesign completo Landing Page con tema Dark & Industrial Split Screen
- Palette allineata al nuovo logo: Navy #0F172A, Steel #64748B, Lime #84CC16

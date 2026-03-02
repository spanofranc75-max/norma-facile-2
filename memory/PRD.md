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
- **Dominio Produzione**: www.1090normafacile.it

## Brand Identity
- **Palette**: Navy #0F172A, Steel Grey #64748B, Lime Accent #84CC16
- **Logo**: logo-1090.jpeg (public folder)
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
- Controllo Costi con pagina dedicata
- Analisi Finanziaria Commessa (Margine Reale)
- Scadenziario (dashboard scadenze)

### Amministrazione
- Backup & Restore: Export/Import JSON completo
- Migrazione dati da vecchia app
- Fatture in Cloud ATTIVA
- Ruoli & Permessi (RBAC): admin, ufficio_tecnico, officina, amministrazione, guest
- Gestione Team con inviti email

### Notifiche & Monitoraggio (v2.1.0)
- "Il Cane da Guardia": scheduler background (12h) scadenze saldatori/strumenti
- Email automatiche via Resend a admin/ufficio_tecnico
- Dashboard /notifiche con allarmi live, storico, trigger manuale
- Badge notifiche nella sidebar con conteggio allarmi attivi
- QR Code Commesse: generazione PNG + dialog download

### Deploy & Manutenzione (v2.1.0)
- Tab Deploy in Impostazioni: pulizia dati test, preview, opzioni mantieni clienti/fornitori
- Indici MongoDB ottimizzati per performance produzione
- Pulizia utenti e sessioni test completata

### Legal & Compliance
- Disclaimer EN 1090, Termini di Servizio, Privacy Policy GDPR
- LegalFooter riutilizzabile, Checkbox accettazione ToS

### UI/UX
- Landing Page Dark & Industrial Split Screen con logo reale
- Responsive (mobile stacking)

---

## Produzione — Checklist
- [x] Dominio: www.1090normafacile.it (configurato in DOMAIN_URL e CORS)
- [x] Email: Resend con fatture@steelprojectdesign.it (verificato funzionante)
- [x] Credenziali: Tutte configurate (Google OAuth, FIC, Resend, LLM)
- [x] Indici MongoDB creati per performance
- [x] Utenti test eliminati (solo admin reale rimasto)
- [x] Sessioni test eliminate
- [x] Scheduler notifiche attivo
- [ ] Pulizia dati operativi test (da fare manualmente via tab Deploy)
- [ ] Backup "Punto Zero" dopo pulizia

---

## Backlog Prioritizzato

### P1
- Export CSV distinta di taglio per CNC
- Stato "SOSPESA" per commesse

### P2
- PWA per modalita' offline
- Migrazione certificati Base64 -> object storage
- Versionamento fatture e fascicoli tecnici

---

## Ultimo Aggiornamento: 2026-03-02
- v2.1.0: Notifiche automatiche, QR Code, Deploy prep, ottimizzazioni produzione

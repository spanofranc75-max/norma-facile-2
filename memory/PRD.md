# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale completo per carpenterie metalliche conformi EN 1090, EN 13241 e ISO 3834.
Include: commesse, preventivi, fatture, FPC, saldatori, controllo qualita, produzione, montaggio, sicurezza, PNRR e workflow automatizzati.

## Architettura
- **Frontend**: React + Tailwind CSS + Shadcn UI (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **AI**: GPT-4o Vision tramite emergentintegrations (Emergent LLM Key)
- **PDF**: WeasyPrint
- **Firma**: react-signature-canvas

## Utenti
- Admin (gestione completa)
- Ufficio Tecnico (commesse, FPC, qualita)
- Amministrazione (fatture, costi, clienti)
- Officina (solo produzione via PIN)
- Guest (in attesa)

## Funzionalita Implementate

### Core
- CRUD Commesse, Preventivi, Fatture (vendita/acquisto), DDT, Clienti, Fornitori
- FPC (Fascicolo Tecnico CE), DOP, Etichette CE
- Qualifica Saldatori, WPS, Strumenti
- Catalogo Profili e Articoli
- Distinte materiali e rilievi

### Produzione (Officina)
- Diario di produzione con PIN operatore
- Timer lavorazione con START/STOP
- Safety Gate: blocco operatori con corsi scaduti

### Montaggio e Tracciabilita (Fase 4)
- Diario di Montaggio (6 step)
- Analisi DDT bulloneria con AI Vision
- Serraggio intelligente con calcolo coppia Nm automatico
- Controlli fondazioni e ancoraggi con foto
- Firma cliente digitale
- Modulo Varianti con foto obbligatorie
- Scadenzario Attrezzature (tarature)

### Sicurezza & PNRR
- Profilo Sicurezza Operatore (D.Lgs 81/08)
- Archivio DNSH con analisi AI
- Checklist sicurezza cantiere
- Export CSE (Coordinatore Sicurezza)

### Workflow Engine ("Fili Conduttori")
- Safety Gate: blocco diary se corsi scaduti
- Post-Sales: firma -> Targa CE + QR + Manutenzione programmata
- Pulsante Magico: pacchetto PDF completo

### Amministrazione
- Backup & Restore (manuale + automatico)
- Import da vecchia app (Migrazione)
- Team management con RBAC
- Deploy / Pulizia DB
- Notifiche email configurabili
- Archivio Storico con export ZIP

### Refactoring Completato (2026-03-20)
- **SettingsPage.js**: Da 1732 righe a ~185 righe. Estratti 11 componenti tab in `/components/settings/`:
  - CompanyTab, BankTab, LogoTab, CondizioniTab, IntegrazioniTab
  - CertificazioniTab, MigrazioneTab, TeamTab, BackupTab, DeployTab, NotificheTab

### AI Vision per Disegni Tecnici (2026-03-20)
- **POST /api/smistatore/analyze-drawing/{doc_id}**: Analizza disegni tecnici (PDF/immagini) con GPT-4o Vision
  - Estrae bulloneria: diametro, classe, quantita, tipo, norma
  - Supporta multi-pagina con deduplicazione
- **POST /api/smistatore/drawing-to-rdp/{doc_id}**: Crea RdP automatica dalla bulloneria estratta
- Frontend: pulsante "Analizza Disegno" nel Repository Documenti con dialog di conferma e selezione

## Backlog Prioritizzato

### P0 (Fatto)
- [x] Refactoring SettingsPage.js
- [x] AI Vision per disegni tecnici (DWG/PDF -> RdP)
- [x] Workflow Engine completo
- [x] Safety Gate operatori

### P2 (Prossimi)
- [ ] RBAC granulare (Role-Based Access Control)
- [ ] Portale clienti read-only
- [ ] Smistatore Avanzato per scorte e sfridi

### P3 (Futuri)
- [ ] Export Excel analisi costi
- [ ] Unificare 13 servizi PDF legacy in "Pulsante Magico"
- [ ] Notifiche WhatsApp
- [ ] Client Portal con accesso diretto

## Schema DB Chiave
- commesse, preventivi, invoices, clients, fornitori
- fpc_projects, welders, instruments, ddt
- diario_produzione, diario_montaggio
- bulloneria_ddt, varianti_montaggio
- sicurezza_corsi_operatore, sicurezza_checklist_cantiere
- attrezzature, manutenzioni_programmate, targhe_ce
- commessa_documents, doc_page_index
- archivio_exports

## Credenziali Test
- Operatori Officina: Ahmed (PIN 1234), Karim (PIN 5678)
- Auth: Google OAuth tramite Emergent

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
- Blocco DoP se C/L non rientrati

### Amministrazione
- Backup & Restore (manuale + automatico)
- Import da vecchia app (Migrazione)
- Team management con RBAC
- Deploy / Pulizia DB
- Notifiche email configurabili
- Archivio Storico con export ZIP

### Refactoring Completato (2026-03-20)
- **SettingsPage.js**: Da 1732 righe a ~185 righe. 11 componenti tab in `/components/settings/`

### AI Vision per Disegni Tecnici (2026-03-20)
- Analisi disegni tecnici (PDF/immagini) con GPT-4o Vision
- Estrazione bulloneria: diametro, classe, quantita, tipo, norma
- Proposta RdP automatica dalla bulloneria estratta

### DoP Frazionata (2026-03-20)
- Generazione DoP multiple per commessa con suffissi (/A, /B, /C)
- Ogni DoP traccia solo i materiali dei DDT specifici
- PDF DoP professionale con dichiarazione EN 1090
- Blocco generazione PDF se conto lavoro non rientrato

### SAL e Acconti (2026-03-20)
- Calcolo SAL automatico da: ore lavorate (50%), fasi produzione (30%), conto lavoro (20%)
- Creazione acconti con percentuale
- Generazione fattura acconto automatica con IVA
- Storico SAL per commessa

### Circuito Conto Lavoro Migliorato (2026-03-20)
- DDT Out (invio a terzisti) e DDT In (rientro)
- Upload certificato trattamento obbligatorio al rientro
- Certificato salvato automaticamente nel repository commessa
- Nuovo capitolo "Trattamenti Superficiali" nel Pulsante Magico
- Monitoraggio materiale fuori sede

### Report Evoluzione Sistema
- Documento comparativo REPORT_EVOLUZIONE.md con tabella before/after
- Diagramma completo State Machine dei workflow

## Backlog Prioritizzato

### P0 (Tutto completato)
- [x] Refactoring SettingsPage.js
- [x] AI Vision per disegni tecnici (DWG/PDF -> RdP)
- [x] Workflow Engine completo
- [x] Safety Gate operatori
- [x] DoP Frazionata
- [x] SAL e Acconti
- [x] Circuito Conto Lavoro completo

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
- **dop_frazionate**: DoP con suffissi, materiali, cert_pages
- **sal_acconti**: acconti SAL con percentuale, importo, fattura_id

## Credenziali Test
- Operatori Officina: Ahmed (PIN 1234), Karim (PIN 5678)
- Auth: Google OAuth tramite Emergent

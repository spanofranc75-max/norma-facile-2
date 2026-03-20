# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834.

## Implementato

### Cantieri Misti (Matrioska)
- Voci di Lavoro CRUD, CommessaOpsPanel unione categorie, Diario Adattivo

### Vista Officina (4 Ponti)
- Timer START/PAUSA/STOP, Foto smart routing, Checklist thumbs up/down, Blocco Dati, PIN + QR

### Pulsante Magico + Smistatore Intelligente
- PDF con CAP. 1 (EN 1090), CAP. 2 (EN 13241), CAP. 3 (Relazione Tecnica), CAP. 4 (Relazione di Montaggio)
- AI Vision per ritaglio certificati multi-pagina, regola consumabili
- Automazione verbali: ESITO POSITIVO/NEGATIVO

### Casi Reali d'Officina (20/03/2026)
- **Gestione Sfridi**: CRUD + prelievo + stato esaurito + link certificato 3.1 cliccabile
- **Blocco Patentini**: EN 1090 richiede patentino valido. Scaduto = 403.
- **Controlli Visivi obbligatori**: EN 1090 e EN 13241 richiedono controllo visivo finale.
- **Registro Non Conformita'**: Ogni thumbs down crea NC + alert immediato dashboard admin.

### Admin UI per Sfridi, Controlli Visivi, Registro NC (20/03/2026)
- **SfridiSection**: Form creazione con dropdown certificato 3.1, link cliccabile al PDF certificato, prelievo, esaurito
- **ControlliVisiviSection**: Banner stato completezza, form OK/NOK con note, auto-creazione NC su NOK
- **RegistroNCSection**: Lista NC con badge stato (aperta/in_corso/chiusa), azione correttiva, chiusura NC
- Integrati in **CommessaOpsPanel** come sezioni collassabili
- **Dashboard NC Alert Banner**: Card rossa con lista NC non lette e navigazione diretta alla commessa
- Test: 100% backend (18/18) + 100% frontend — iteration_184

### Fase 4: Montaggio e Tracciabilita' (20/03/2026)
- **Tracciabilita' Bulloneria**: AI Vision (GPT-4o) analizza DDT, estrae Diametro/Classe/Lotto
- **Serraggio Intelligente**: Tabella ISO 898-1 (60 coppie), auto-calcolo coppia Nm, checklist SI/NO
- **Gestione Cantiere**: Check fondazioni, upload foto giunti/ancoraggi obbligatorie
- **Firma Digitale Cliente**: Canvas touch per verbale fine lavori
- **Relazione di Montaggio (CAP. 4)**: Nuovo capitolo nel Pulsante Magico
- Test: 100% backend (14/14) + 100% frontend — iteration_183

## Backlog

### P1
- Trigger UI "Analizza con AI" per Smistatore Intelligente
- Split SettingsPage.js (>1700 righe)

### P2
- Smistatore Intelligente Avanzato (DDT Multi-Commessa, Magazzino Scorte)
- Split commesse.py, Onboarding Wizard, Export Excel, RBAC

### P3
- Portale clienti read-only, Notifiche WhatsApp, Unificazione 13 servizi PDF

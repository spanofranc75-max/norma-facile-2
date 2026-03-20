# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834.

## Implementato

### Cantieri Misti (Matrioska)
- Voci di Lavoro CRUD, CommessaOpsPanel unione categorie, Diario Adattivo

### Vista Officina (4 Ponti)
- Timer START/PAUSA/STOP, Foto smart routing, Checklist thumbs up/down, Blocco Dati, PIN + QR

### Pulsante Magico + Smistatore Intelligente
- PDF con CAP. 1 (EN 1090), CAP. 2 (EN 13241), CAP. 3 (Relazione Tecnica)
- AI Vision per ritaglio certificati multi-pagina, regola consumabili
- Automazione verbali: ESITO POSITIVO/NEGATIVO

### Casi Reali d'Officina (20/03/2026)
- **Gestione Sfridi**: Materiale avanzato con link certificato 3.1. CRUD + prelievo + stato esaurito.
- **Blocco Patentini**: EN 1090 richiede patentino valido. Scaduto = 403.
- **Controlli Visivi obbligatori**: EN 1090 e EN 13241 richiedono controllo visivo finale.
- **Registro Non Conformita'**: Ogni thumbs down crea NC + alert admin.
- Test: 100% backend (26/26 — iteration_182)

### Fase 4: Montaggio e Tracciabilita' (20/03/2026)
- **Tracciabilita' Bulloneria**: AI Vision (GPT-4o) analizza foto DDT fornitori, estrae Diametro/Classe/Lotto. Dati associati a Commessa/Voce.
- **Serraggio Intelligente**: Tabella ISO 898-1 (60 coppie: 12 diametri x 5 classi). Auto-calcolo coppia Nm. Checklist conferma SI/NO + chiave dinamometrica.
- **Gestione Cantiere**: Check fondazioni OK/NOK. Upload obbligatorio foto giunti serrati e ancoraggi.
- **Firma Digitale Cliente**: Canvas touch per verbale fine lavori con nome + firma.
- **Relazione di Montaggio (CAP. 4)**: Nuovo capitolo nel Pulsante Magico con tabella bulloni, serraggi, foto, firma cliente.
- Backend: 9 endpoint in `routes/montaggio.py`, servizio in `services/montaggio_service.py`
- Frontend: Nuovo tab MONTAGGIO in OfficinaPage con 4 sotto-step (DDT, SERRAGGIO, CANTIERE, FIRMA)
- Collezioni DB: `bulloneria_ddt`, `diario_montaggio`
- Test: 100% backend (14/14) + 100% frontend (iteration_183)

## Backlog

### P1
- Frontend per Sfridi, Controlli Visivi, Registro NC (UI nelle pagine admin)
- Trigger UI "Analizza con AI" per Smistatore Intelligente
- Split SettingsPage.js (>1700 righe)

### P2
- Smistatore Intelligente Avanzato (DDT Multi-Commessa, Magazzino Scorte)
- Split commesse.py, Onboarding Wizard, Export Excel, RBAC

### P3
- Portale clienti read-only, Notifiche WhatsApp, Unificazione 13 servizi PDF

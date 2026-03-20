# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834.

## Implementato

### Cantieri Misti (Matrioska)
- Voci di Lavoro CRUD, CommessaOpsPanel unione categorie, Diario Adattivo

### Vista Officina (4 Ponti)
- Timer START/PAUSA/STOP, Foto smart routing, Checklist thumbs up/down, Blocco Dati, PIN + QR

### Pulsante Magico + Smistatore Intelligente
- PDF con CAP. 1-4: EN 1090, EN 13241, Relazione Tecnica, Relazione di Montaggio
- AI Vision per certificati multi-pagina + analisi DDT bulloneria

### Casi Reali d'Officina
- Sfridi (CRUD + prelievo + link cert 3.1 cliccabile), Blocco Patentini, Controlli Visivi, Registro NC + alert admin

### Admin UI per Sfridi, Controlli Visivi, Registro NC
- SfridiSection, ControlliVisiviSection, RegistroNCSection integrati in CommessaOpsPanel
- Dashboard NC Alert Banner con navigazione diretta

### Fase 4: Montaggio e Tracciabilita'
- Tracciabilita' Bulloneria (AI Vision GPT-4o), Serraggio ISO 898-1, Cantiere, Firma cliente
- CAP. 4 nel Pulsante Magico

### Fase 4B: Varianti, Scadenzario Attrezzature, Archivio Storico (20/03/2026)
- **Modulo Varianti**: Sotto-step VARIANTI nel MontaggioPanel, nota + foto obbligatoria, evidenziate in CAP. 4 (sezione 4.6)
- **Scadenzario Attrezzature**: CRUD saldatrici/chiavi dinamometriche con date taratura. Alert admin se taratura scaduta. Alert nel modulo serraggio operaio. Pagina `/attrezzature`.
- **Archivio Storico**: Esportazione massiva ZIP per anno/cliente. Struttura /{Anno}/{Cliente}/{Commessa}/ con tutti documenti. Pagina `/archivio-storico`.
- Collezioni DB: `varianti_montaggio`, `attrezzature`, `archivio_exports`
- Test: 100% backend (19/19) + 100% frontend — iteration_185

## Backlog

### P1
- Trigger UI "Analizza con AI" per Smistatore Intelligente
- Split SettingsPage.js (>1700 righe)

### P2
- Smistatore Avanzato (DDT Multi-Commessa, Magazzino Scorte)
- Split commesse.py, Export Excel, RBAC

### P3
- Portale clienti read-only, Notifiche WhatsApp, Unificazione 13 servizi PDF

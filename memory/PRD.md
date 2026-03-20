# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834.

## Implementato

### Cantieri Misti (Matrioska)
- Voci di Lavoro CRUD, CommessaOpsPanel unione categorie, Diario Adattivo

### Vista Officina (4 Ponti + Montaggio)
- Timer START/PAUSA/STOP, Foto smart routing, Checklist thumbs up/down, Blocco Dati, PIN + QR
- Tab MONTAGGIO con 6 step: SICUREZZA → DDT → SERRAGGIO → VARIANTI → CANTIERE → FIRMA

### Pulsante Magico + Smistatore Intelligente
- PDF con CAP. 1-5: EN 1090, EN 13241, Relazione Tecnica, Montaggio, Sostenibilita' DNSH
- AI Vision per certificati multi-pagina + analisi DDT bulloneria + analisi DNSH

### Casi Reali d'Officina
- Sfridi (CRUD + link cert 3.1 cliccabile), Blocco Patentini, Controlli Visivi, Registro NC + alert admin

### Admin UI (Sfridi, Controlli Visivi, NC, DNSH, CSE)
- Sezioni integrate in CommessaOpsPanel
- Dashboard NC Alert Banner

### Fase 4: Montaggio e Tracciabilita'
- Tracciabilita' Bulloneria AI, Serraggio ISO 898-1, Cantiere, Firma cliente, Varianti con foto
- CAP. 4 nel Pulsante Magico

### Scadenzario Attrezzature + Archivio Storico
- Pagina `/attrezzature` con tarature saldatrici/chiavi + alert scadenze
- Pagina `/archivio-storico` con export ZIP per anno/cliente

### Sicurezza & PNRR + Workflow Engine (20/03/2026)
- **Profilo Sicurezza Operatore**: 6 corsi D.Lgs 81/08, CRUD, blocco diario se scaduti
- **Archivio DNSH/PNRR**: AI Vision analizza certificati per sostenibilita', CAP. 5 nel PDF
- **Diario Sicurezza Cantiere**: Checklist obbligatoria + foto panoramica PRIMA del montaggio
- **Cartella CSE**: Export ZIP (DURC, POS, Attestati, Certificati macchine)
- **WORKFLOW ENGINE (I Fili Conduttori)**:
  - SICUREZZA → DIARIO: Timer START bloccato se corsi/patentini scaduti (403)
  - ACQUISTI → CANTIERE: DDT → auto coppia serraggio Nm, blocco senza conferma
  - QUALITA' → PDF: Dati DNSH → CAP. 5 Sostenibilita'
  - FIRMA → SERVICE: Auto-genera Targa CE con QR + Manutenzioni 12/24 mesi
- Collezioni: sicurezza_cantiere, dnsh_data, targhe_ce, scadenzario_manutenzioni
- Test: 100% backend (17/17) + 100% frontend — iteration_186

## Backlog

### P1
- Trigger UI "Analizza con AI" per Smistatore Intelligente
- Split SettingsPage.js (>1700 righe)

### P2
- Smistatore Avanzato (DDT Multi-Commessa, Magazzino Scorte)
- Split commesse.py, Export Excel, RBAC

### P3
- Portale clienti read-only, Notifiche WhatsApp, Unificazione 13 servizi PDF

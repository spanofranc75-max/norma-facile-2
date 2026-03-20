# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834.

## Implementato

### Cantieri Misti (Matrioska)
- Voci di Lavoro CRUD, CommessaOpsPanel unione categorie, Diario Adattivo

### Vista Officina (4 Ponti)
- Timer START/PAUSA/STOP, Foto smart routing, Checklist 👍/👎, Blocco Dati, PIN + QR

### Pulsante Magico + Smistatore Intelligente
- PDF con CAP. 1 (EN 1090), CAP. 2 (EN 13241), CAP. 3 (Relazione Tecnica)
- AI Vision per ritaglio certificati multi-pagina, regola consumabili
- Automazione verbali: ESITO POSITIVO/NEGATIVO

### Casi Reali d'Officina (20/03/2026)
- **Gestione Sfridi**: Materiale avanzato → magazzino con link cliccabile al certificato 3.1 originale. CRUD + prelievo + stato esaurito.
- **Blocco Patentini**: EN 1090 richiede patentino valido. Scaduto → 403 "Contattare il responsabile". EN 13241/GENERICA: nessun blocco.
- **Controlli Visivi obbligatori**: EN 1090 e EN 13241 richiedono controllo visivo finale (👍/👎 + foto). Senza → Pulsante Magico blocca PDF.
- **Registro Non Conformità**: Ogni 👎 (checklist O controllo visivo) crea automaticamente NC + alert admin immediato (badge rosso dashboard).
- Test: 100% backend (26/26 — iteration_182)

## Backlog

### P1
- Frontend per Sfridi, Controlli Visivi, Registro NC (UI nelle pagine admin)
- Split SettingsPage.js (>1700 righe)

### P2
- DDT Multi-Commessa & Magazzino Scorte
- Split commesse.py, Onboarding Wizard, Export Excel, RBAC

### P3
- Firme digitali, Portale clienti, Notifiche WhatsApp

# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformità EN 1090-1 e viabilità commerciale come prodotto startup. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilità materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalità Implementate

### Core EN 1090 (Completo)
- Commesse CRUD con voci lavoro multi-normativa
- FPC: lotti materiale con tracciabilità colata → cert 3.1 → DDT
- Registro saldatura con WPS e qualifiche saldatori
- Riesame Tecnico (gate pre-produzione) con 12 check automatici
- Ispezioni, Controllo Finale, Fascicolo Tecnico
- DOP frazionata e automatica con PDF professionale

### CAM — Criteri Ambientali Minimi (Completato 21/03/2026)
- Campi CAM su `material_batches`: `peso_kg`, `percentuale_riciclato`, `metodo_produttivo`, `distanza_trasporto_km`, `certificazione_epd`, `ente_certificatore_epd`
- Calcolo conformità CAM da material_batches (bridge FPC ↔ CAM senza duplicazione)
- Sezione CAM integrata nella DOP EN 1090 con badge PNRR DM 256/2022
- Dichiarazione CAM dedicata con riferimenti normativi e firma
- Form frontend batch con sezione CAM (Peso, % Riciclato, Metodo Produttivo, Distanza)
- Colonne Peso e % Riciclato nella tabella rintracciabilità

### PDF Professionali (Completato 21/03/2026)
- DOP EN 1090: 4 pagine, intestazione aziendale, tabella prestazioni ZA.1-ZA.7, tracciabilità, allegato CAM PNRR, dichiarazione conformità con firma
- Etichetta CE: formato compatto 148x105mm, stampa adesivo, badge EN 1090-1
- Dichiarazione CAM PNRR: summary boxes, dettaglio materiali con fornitore/colata/distanza, riferimento DM 256/2022
- Scheda Rintracciabilità Totale: A4 landscape, catena Disegno → DDT → Colata → Cert 3.1 con 12 colonne

### Multi-Normativa (Parziale)
- Executive Dashboard con vista EN 1090 / EN 13241 / Generica
- `normativa_tipo` su voci_lavoro
- Riesame Selettivo: DA IMPLEMENTARE

### Moduli Aggiuntivi (Completato)
- Scadenziario Manutenzioni Digitalizzato
- Verbali ITT (Initial Type Testing)
- Sopralluoghi, Perizie, Preventivatore con AI
- DDT, Fatturazione attiva/passiva, Analisi finanziaria
- Notifiche (base), QR Code, Team management

## Backlog Prioritizzato

### P0 (Nessuno — task corrente completato)

### P1
1. **Riesame Tecnico Selettivo**: Check condizionali per normativa nelle commesse miste
2. **Ponte Perizie → Preventivatore**: Trasferimento auto dati AI perizia → preventivo
3. **Sistema Notifiche Proattive**: Email 30/7/1gg prima di scadenze

### P2
4. **Architettura Multi-Tenant**: `tenant_id` su tutte le collection
5. **Training ML**: Modello di stima dal Diario Produzione
6. **Alerting Intelligente**: Notifica sforamento costi

### P3
7. Unificazione PDF legacy (13 servizi)
8. Portale Clienti (read-only)
9. RBAC avanzato, QR Code migliorati
10. Split file grandi (SettingsPage.js, commesse.py)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB, porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

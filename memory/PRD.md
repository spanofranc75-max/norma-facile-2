# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformità EN 1090-1 e viabilità commerciale come prodotto startup. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilità materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalità Implementate

### Core EN 1090 (Completo)
- Commesse CRUD con voci lavoro multi-normativa
- FPC: lotti materiale con tracciabilità colata -> cert 3.1 -> DDT
- Registro saldatura con WPS e qualifiche saldatori
- Riesame Tecnico (gate pre-produzione) con 12 check automatici
- Ispezioni, Controllo Finale, Fascicolo Tecnico
- DOP frazionata e automatica con PDF professionale

### CAM — Criteri Ambientali Minimi (Completato 21/03/2026)
- Campi CAM su material_batches: peso_kg, percentuale_riciclato, metodo_produttivo, distanza_trasporto_km, certificazione_epd, ente_certificatore_epd
- Calcolo conformità CAM da material_batches (bridge FPC <-> CAM senza duplicazione)
- CAM Alert pre-generazione: endpoint /api/cam/alert/{cid} con livello danger/success/warning e suggerimenti actionable
- Form frontend batch con sezione CAM dedicata (Peso, % Riciclato, Metodo Produttivo, Distanza)
- Colonne Peso e % Riciclato nella tabella rintracciabilità

### PDF Executive Professional (Completato 21/03/2026)
- DOP EN 1090 (4 pagine):
  - Intestazione professionale con barra gradient blu scuro e dati aziendali
  - Tabella prestazioni ZA.1-ZA.7 arricchita da Riesame Tecnico (no NPD: ZA.3 mostra WPS/saldatori, ZA.4 n. certificati, ZA.5-ZA.7 dati reali da Riesame)
  - Tracciabilità materiali con zebra striping e N. Colata monospace
  - Verifiche condizionali: Riesame, Registro Saldatura (con righe esempio), Ispezioni VT/Dim, Controllo Finale — sezioni vuote nascoste
  - Allegato CAM PNRR con badge DM 256/2022, 4 summary boxes, tabella dettaglio, riferimenti CO2
  - Dichiarazione Conformità con box gradient e firma nominativa
  - Timbro Professionale Circolare: "VERIFICATO CONFORME" + nome azienda + FPC + città/data
- Etichetta CE: formato 148x105mm, badge EN 1090-1, pronta stampa adesivo
- Dichiarazione CAM PNRR: badge "Art. 57 D.Lgs. 36/2023", dettaglio con fornitore/colata/distanza
- Scheda Rintracciabilità Totale: A4 landscape, 12 colonne, catena completa, legenda tecnica
- Banner CAM Alert nel CommessaHub: rosso (danger), verde (success), arancio (warning) con suggerimenti

### Multi-Normativa (Completo)
- Executive Dashboard con vista EN 1090 / EN 13241 / Generica
- normativa_tipo su voci_lavoro
- Riesame Tecnico Selettivo: check condizionali per normativa (completato 22/03/2026)
  - CHECKS_DEFINITION con campo `normativa` per ogni check
  - Filtraggio automatico basato su normativa_tipo delle voci lavoro della commessa
  - Check non applicabili marcati N/A con `applicabile: false` e motivo esclusione
  - Approvazione valida solo check applicabili (non-applicable auto-superati)
  - PDF con badge normative attive e riepilogo applicabili/N/A
  - Frontend: check N/A grayed out, strikethrough, icona "—", badge normativa nell'header

### Moduli Aggiuntivi (Completato)
- Scadenziario Manutenzioni Digitalizzato, Verbali ITT
- Sopralluoghi, Perizie, Preventivatore con AI
- DDT, Fatturazione attiva/passiva, Analisi finanziaria
- Notifiche (base), QR Code, Team management

## Backlog Prioritizzato

### P1
1. Ponte Perizie -> Preventivatore: Trasferimento auto dati AI perizia -> preventivo
2. Sistema Notifiche Proattive: Email 30/7/1gg prima di scadenze
3. Pacco Documenti RINA: ZIP con pacchetto conformità completo (DOP, CE, CAM, Rintracciabilità, Riesame)

### P2
4. Architettura Multi-Tenant: tenant_id su tutte le collection
5. Training ML: Modello di stima dal Diario Produzione
6. Alerting Intelligente: Notifica sforamento costi

### P3
7. Unificazione PDF legacy (13 servizi)
8. Portale Clienti (read-only)
9. RBAC avanzato, QR Code migliorati
10. Split file grandi (SettingsPage.js, commesse.py)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie

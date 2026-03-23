# NormaFacile 2.0 — PRD (Product Requirements Document)

## Problema originale
Sistema operativo verticale per carpenteria metallica / EN 1090 / EN 13241 / sicurezza cantiere / documentazione / committenza. Copilota tecno-normativo-operativo.

## Architettura
- **Frontend**: React + Tailwind + Shadcn/UI (porta 3000)
- **Backend**: FastAPI + Motor (porta 8001)
- **Database**: MongoDB (100 collezioni)
- **AI**: OpenAI GPT-4o via emergentintegrations
- **Email**: Resend
- **Storage**: Object Storage S3
- **Auth**: Emergent Google OAuth + JWT

## Moduli implementati (18)
1. Preventivi
2. Istruttoria AI
3. Segmentazione normativa
4. Commessa pre-istruita
5. Commessa madre / rami normativi / emissioni documentali
6. Evidence Gate per emissione
7. Sicurezza / Scheda cantiere
8. Motore AI Sicurezza
9. Generazione POS DOCX
10. Pacchetti Documentali intelligenti
11. Invio email documenti
12. Verifica Committenza / Contratti
13. Registro Obblighi Commessa (8 fonti)
14. Dashboard Cantiere / Commessa multilivello
15. Audit Log (16 moduli)
16. Profili documentali per committente
17. Notifiche intelligenti in-app
18. Repository documentale interno alla commessa

## Stato attuale — Post-Audit e Post-Hardening

### Hardening completato (2026-03-23)
- **TD-001**: Indici MongoDB — 24 indici su 12 collezioni critiche
- **TD-002**: Rimosso router sicurezza duplicato
- **TD-005**: Rate limiting su 15 endpoint AI (slowapi)
- **TD-009**: Error handling su background tasks (safe_background_task)
- **TD-010**: Filtro user_id su 7 route multi-tenant
- **TD-004**: Cleanup dead code (2 service, 5 file legacy, 158 import)
- **CR-001/002**: JWT secret hardened, chiave LLM unificata, cleanup sessioni
- **Data Integrity**: 0 CRITICAL, 0 WARNING — backfill user_id, eliminati orfani

### UX-001 Completato (2026-03-23)
- **Semplificazione CommessaHubPage**: Refactoring da 1063 a ~975 righe
- **CommessaActionsMenu.js**: Dropdown menu per generazione documenti (Dossier, Pacco, Template 111, DoP, Etichetta CE, Rintracciabilita, CAM, Pacco RINA)
- **NextStepCard.js**: Guida contestuale "Cosa devo fare adesso?" basata sullo stato della commessa
- **Layout migliorato**: Accordion collassabili (Dati Economici, Rami Normativi, Qualita), layout 2 colonne, lifecycle bar visuale
- **Bug fix**: Componente CostRow mancante ripristinato
- **Testing**: 100% frontend pass (3 commesse diverse, 11 componenti, 3 dialog)

## Backlog prioritizzato

### P0 — Prossimi task
- **UX-003**: Onboarding primo utilizzo (empty states intelligenti, percorsi guidati per nuovi utenti)

### P1 — Task tecnici
- Finalizzare Data Integrity Check come tool admin riutilizzabile (endpoint protetto o job periodico)
- **TD-003**: Aggiungere indici MongoDB alle collezioni rimanenti non critiche

### P2 — Backlog futuro
- Revisione collezioni "zombie" (download_tokens, sessions)
- Refactoring altri file monolitici
- Email automatiche selettive
- Integrazione Stripe per monetizzazione
- Stability Guard AI
- Architettura Multi-Tenant

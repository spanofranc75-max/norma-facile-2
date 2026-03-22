# SPEC_POS_RENDERING_MAP.md

## Obiettivo
Il generatore POS deve produrre un documento che:
- imiti fedelmente la struttura, il tono e il carattere del POS aziendale storico
- utilizzi i dati strutturati del modulo sicurezza
- distingua tra parti fisse, dinamiche e ibride
- supporti 3 modalita di output: bozza_interna, bozza_revisione, finale_stampabile

## Sezioni POS (30 sezioni)
1. Frontespizio
2. Indice
3. Introduzione
4. Elenco documentazione da conservare in cantiere
5. Presentazione dell'azienda
6. Anagrafica aziendale
7. Mansionario
8. Dati relativi al cantiere
9. Soggetti di riferimento
10. Turni di lavoro
11. Lavorazioni in subappalto
12. Principali misure di prevenzione
13. Attivita formativa
14. Sorveglianza sanitaria
15. Programma sanitario
16. DPI
17. Segnaletica di sicurezza
18. Macchine/Attrezzature/Impianti
19. Sostanze chimiche
20. Agenti biologici
21. Stoccaggio materiali/rifiuti
22. Servizi igienico-assistenziali
23. Valutazione rischi
24. Individuazione soggetti esposti
25. Rischio rumore
26. Rischio vibrazioni
27. Rischio chimico
28. Movimentazione manuale carichi
29. Schede rischio per fase
30. Gestione emergenza + Dichiarazione

## Regole di rendering
- Modalita bozza_interna: ammessi placeholder [DA COMPLETARE]
- Modalita bozza_revisione: "Da completare prima dell'emissione finale"
- Modalita finale_stampabile: nessun placeholder, solo dati confermati

## Regole di blocco finale_stampabile
Bloccante se mancano: committente, indirizzo, oggetto lavori, soggetti principali, fasi e rischi confermati.

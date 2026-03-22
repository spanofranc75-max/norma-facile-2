"""
Cantieri Sicurezza Service — Safety Branch v2
================================================
Libreria a 3 livelli: lib_fasi_lavoro → lib_rischi_sicurezza → lib_dpi_misure
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from core.database import db

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  SEED DATA — Livello 3: DPI / Misure / Apprestamenti (31 entries)
# ═══════════════════════════════════════════════════════════════════

DPI_MISURE_SEED = [
    # ── DPI (12) ──
    {"codice": "DPI-CASCO", "nome": "Casco protettivo", "tipo": "dpi", "sottotipo": "protezione_capo", "descrizione": "Casco di protezione per il capo contro la caduta di oggetti e urti", "rif_normativo": "UNI EN 397 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "sempre", "condizioni": [], "sort_order": 10},
    {"codice": "DPI-GUANTI-CROSTA", "nome": "Guanti in crosta", "tipo": "dpi", "sottotipo": "protezione_mani", "descrizione": "Guanti di protezione contro rischi meccanici", "rif_normativo": "UNI EN 388 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "sempre", "condizioni": [], "sort_order": 20},
    {"codice": "DPI-GUANTI-CALORE", "nome": "Guanti protezione calore", "tipo": "dpi", "sottotipo": "protezione_mani", "descrizione": "Guanti per protezione dal calore e dalla fiamma", "rif_normativo": "UNI EN 407 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["saldatura", "taglio_termico"], "sort_order": 21},
    {"codice": "DPI-GUANTI-ISOLANTI", "nome": "Guanti isolanti elettrici", "tipo": "dpi", "sottotipo": "protezione_mani", "descrizione": "Guanti per protezione da rischio elettrico", "rif_normativo": "UNI EN 60903 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["rischio_elettrico"], "sort_order": 22},
    {"codice": "DPI-SCARPE", "nome": "Scarpe antinfortunistiche", "tipo": "dpi", "sottotipo": "protezione_piedi", "descrizione": "Calzature di sicurezza con puntale e suola anti-perforazione", "rif_normativo": "UNI EN ISO 20344 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "sempre", "condizioni": [], "sort_order": 30},
    {"codice": "DPI-OCCHIALI", "nome": "Occhiali di protezione", "tipo": "dpi", "sottotipo": "protezione_occhi", "descrizione": "Occhiali per protezione da schegge e proiezioni", "rif_normativo": "UNI EN 166 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["taglio", "molatura", "foratura"], "sort_order": 40},
    {"codice": "DPI-SCHERMO-SALD", "nome": "Schermo saldatura", "tipo": "dpi", "sottotipo": "protezione_occhi", "descrizione": "Maschera/schermo per protezione da radiazioni UV/IR di saldatura", "rif_normativo": "UNI EN 169/175 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["saldatura"], "sort_order": 41},
    {"codice": "DPI-CUFFIE", "nome": "Cuffie/tappi auricolari", "tipo": "dpi", "sottotipo": "protezione_udito", "descrizione": "Otoprotettori per riduzione esposizione al rumore", "rif_normativo": "UNI EN 352 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["rumore"], "sort_order": 50},
    {"codice": "DPI-MASCHERA", "nome": "Maschera antipolvere/filtro", "tipo": "dpi", "sottotipo": "protezione_vie_resp", "descrizione": "Facciale filtrante per polveri, fumi e vapori", "rif_normativo": "UNI EN 149 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["fumi", "polveri", "vapori"], "sort_order": 60},
    {"codice": "DPI-CINTURA", "nome": "Cintura anticaduta", "tipo": "dpi", "sottotipo": "protezione_caduta", "descrizione": "Imbracatura per il corpo con sistema di arresto caduta", "rif_normativo": "UNI EN 361/362 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota"], "sort_order": 70},
    {"codice": "DPI-TUTA", "nome": "Tuta di protezione", "tipo": "dpi", "sottotipo": "protezione_corpo", "descrizione": "Indumento di protezione per il corpo", "rif_normativo": "UNI EN 340 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "sempre", "condizioni": [], "sort_order": 80},
    {"codice": "DPI-GILET-AV", "nome": "Gilet alta visibilita", "tipo": "dpi", "sottotipo": "protezione_visibilita", "descrizione": "Indumento ad alta visibilita per lavori con mezzi in movimento", "rif_normativo": "UNI EN ISO 20471 - Art 75-77-78 D.Lgs 81/08", "obbligatorieta": "condizionale", "condizioni": ["mezzi_cantiere", "viabilita"], "sort_order": 90},
    # ── Misure organizzative (11) ──
    {"codice": "MIS-INDUMENTI-ADERENTI", "nome": "Indumenti aderenti obbligatori", "tipo": "misura", "sottotipo": "organizzativa", "descrizione": "Non indossare abiti larghi, anelli, catene vicino a organi in movimento", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["organi_in_movimento"], "sort_order": 100},
    {"codice": "MIS-VALUTAZIONE-RUMORE", "nome": "Valutazione rischio rumore allegata", "tipo": "misura", "sottotipo": "documentale", "descrizione": "Allegare al POS la valutazione fonometrica del rischio rumore", "rif_normativo": "D.Lgs. 81/08 Titolo VIII Capo II", "obbligatorieta": "condizionale", "condizioni": ["rumore"], "sort_order": 101},
    {"codice": "MIS-VALUTAZIONE-VIBRAZIONI", "nome": "Valutazione rischio vibrazioni allegata", "tipo": "misura", "sottotipo": "documentale", "descrizione": "Allegare al POS la valutazione vibrometrica", "rif_normativo": "D.Lgs. 81/08 Titolo VIII Capo III", "obbligatorieta": "condizionale", "condizioni": ["vibrazioni"], "sort_order": 102},
    {"codice": "MIS-SCHERMATURA-AREA", "nome": "Schermatura area saldatura", "tipo": "misura", "sottotipo": "organizzativa", "descrizione": "Schermare l'area con teli ignifughi per proteggere terzi da radiazioni", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["saldatura"], "sort_order": 103},
    {"codice": "MIS-ASPIRAZIONE-FUMI", "nome": "Aspirazione localizzata fumi", "tipo": "misura", "sottotipo": "tecnica", "descrizione": "Predisporre aspirazione forzata localizzata nell'area di saldatura", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["saldatura", "fumi"], "sort_order": 104},
    {"codice": "MIS-VENTILAZIONE-FORZATA", "nome": "Ventilazione forzata area", "tipo": "misura", "sottotipo": "tecnica", "descrizione": "Garantire ricambio aria forzato in area verniciatura o con agenti chimici", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["verniciatura", "chimico"], "sort_order": 105},
    {"codice": "MIS-SEZIONAMENTO-LINEA", "nome": "Sezionamento e verifica assenza tensione", "tipo": "misura", "sottotipo": "tecnica", "descrizione": "Sezionare alimentazione elettrica e verificare assenza tensione prima di operare", "rif_normativo": "CEI 11-27", "obbligatorieta": "condizionale", "condizioni": ["rischio_elettrico"], "sort_order": 106},
    {"codice": "MIS-ALLONTANARE-INFIAMMABILI", "nome": "Allontanamento materiali infiammabili", "tipo": "misura", "sottotipo": "organizzativa", "descrizione": "Rimuovere tutti i materiali combustibili dall'area di lavoro", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["saldatura", "taglio_termico", "incendio"], "sort_order": 107},
    {"codice": "MIS-PERCORSI-SEGNALATI", "nome": "Percorsi obbligati e segnalati", "tipo": "misura", "sottotipo": "organizzativa", "descrizione": "Segnalare con segnaletica i percorsi pedonali e veicolari in cantiere", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["mezzi_cantiere"], "sort_order": 108},
    {"codice": "MIS-AUSILI-MECCANICI", "nome": "Utilizzo ausili meccanici per carichi > 25 kg", "tipo": "misura", "sottotipo": "tecnica", "descrizione": "Utilizzare mezzi meccanici per la movimentazione di carichi superiori a 25 kg", "rif_normativo": "D.Lgs. 81/08 Titolo VI", "obbligatorieta": "condizionale", "condizioni": ["movimentazione_carichi"], "sort_order": 109},
    {"codice": "MIS-VERIFICA-PORTATA", "nome": "Verifica portata terreno e mezzo", "tipo": "misura", "sottotipo": "tecnica", "descrizione": "Verificare la portata del mezzo di sollevamento e la stabilita del terreno", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["sollevamento"], "sort_order": 110},
    # ── Apprestamenti (8) ──
    {"codice": "APP-PONTEGGIO", "nome": "Ponteggio regolamentare", "tipo": "apprestamento", "sottotipo": "opera_provvisionale", "descrizione": "Ponteggio metallico conforme D.Lgs. 81/08 Allegato XVIII", "rif_normativo": "D.Lgs. 81/08 All. XVIII", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota"], "sort_order": 200},
    {"codice": "APP-TRABATTELLO", "nome": "Trabattello UNI EN 1004", "tipo": "apprestamento", "sottotipo": "opera_provvisionale", "descrizione": "Ponte su ruote per lavori in quota", "rif_normativo": "UNI EN 1004", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota"], "sort_order": 201},
    {"codice": "APP-PARAPETTI", "nome": "Parapetti provvisori", "tipo": "apprestamento", "sottotipo": "protezione_collettiva", "descrizione": "Parapetti temporanei su bordi non protetti (h >= 100 cm)", "rif_normativo": "D.Lgs. 81/08 All. XVIII", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota", "bordi_non_protetti"], "sort_order": 202},
    {"codice": "APP-LINEAVITA", "nome": "Linea vita UNI EN 795", "tipo": "apprestamento", "sottotipo": "protezione_collettiva", "descrizione": "Sistema anticaduta fisso o temporaneo", "rif_normativo": "UNI EN 795", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota", "coperture"], "sort_order": 203},
    {"codice": "APP-RETI-PROTEZIONE", "nome": "Reti di protezione", "tipo": "apprestamento", "sottotipo": "protezione_collettiva", "descrizione": "Reti sotto area di lavoro per caduta oggetti", "rif_normativo": "UNI EN 1263", "obbligatorieta": "condizionale", "condizioni": ["caduta_materiali"], "sort_order": 204},
    {"codice": "APP-ESTINTORE", "nome": "Estintore", "tipo": "apprestamento", "sottotipo": "antincendio", "descrizione": "Estintore a polvere o CO2 nelle vicinanze dell'area di lavoro", "rif_normativo": "D.M. 10/03/98", "obbligatorieta": "sempre", "condizioni": [], "sort_order": 205},
    {"codice": "APP-PLE", "nome": "PLE (Piattaforma Elevabile)", "tipo": "apprestamento", "sottotipo": "opera_provvisionale", "descrizione": "Piattaforma di lavoro elevabile per lavori in quota puntuali", "rif_normativo": "D.Lgs. 81/08 All. VI", "obbligatorieta": "condizionale", "condizioni": ["lavori_quota"], "sort_order": 206},
    {"codice": "APP-BARRIERE", "nome": "Barriere di delimitazione", "tipo": "apprestamento", "sottotipo": "protezione_collettiva", "descrizione": "Recinzione/nastro per delimitare area di lavoro da terzi", "rif_normativo": "", "obbligatorieta": "condizionale", "condizioni": ["interferenze", "area_pubblica"], "sort_order": 207},
]

# ═══════════════════════════════════════════════════════════════════
#  SEED DATA — Livello 2: Rischi Sicurezza (18 entries)
# ═══════════════════════════════════════════════════════════════════

RISCHI_SEED = [
    {
        "codice": "RS-CADUTA-ALTO", "nome": "Caduta dall'alto", "categoria": "sicurezza", "sottocategoria": "cadute",
        "descrizione_breve": "Rischio di caduta da altezza superiore a 2 metri",
        "trigger": {"keywords": ["quota", "altezza", "ponteggio", "trabattello", "copertura", "tetto", "solaio"], "condizioni": ["montaggio_cantiere", "lavori_quota"]},
        "condizioni_esclusione": ["solo_lavorazioni_a_terra", "altezza_inferiore_2m"],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Ingente", "classe": "Gravissimo"},
        "misure_prevenzione": ["Utilizzo di ponteggi e trabattelli conformi", "Parapetti provvisori su bordi non protetti", "Cintura di sicurezza con fune di trattenuta", "Formazione specifica lavori in quota"],
        "note_pos_template": "Valutare necessita di Pi.M.U.S. se previsto ponteggio",
        "dpi_ids": ["DPI-CASCO", "DPI-CINTURA", "DPI-SCARPE"], "misure_ids": [], "apprestamenti_ids": ["APP-PONTEGGIO", "APP-TRABATTELLO", "APP-PARAPETTI", "APP-LINEAVITA"],
        "documenti_richiesti": [
            {"codice": "DOC-FORMAZIONE-QUOTA", "nome": "Attestato formazione lavori in quota", "obbligatorio": True, "condizione": None},
            {"codice": "DOC-IDONEITA", "nome": "Idoneita sanitaria", "obbligatorio": True, "condizione": None},
            {"codice": "DOC-PIMUS", "nome": "Pi.M.U.S.", "obbligatorio": False, "condizione": "uso_ponteggio"},
        ],
        "domande_verifica": [
            {"testo": "Sono previsti lavori ad altezza superiore a 2 m?", "impatto": "alto", "gate_critical": True},
            {"testo": "Quale sistema anticaduta e previsto (ponteggio, trabattello, PLE, linea vita)?", "impatto": "alto", "gate_critical": True},
        ],
        "rif_normativo": "D.Lgs. 81/08 Titolo IV Capo II", "gate_critical": True, "sort_order": 10,
    },
    {
        "codice": "RS-CADUTA-MAT", "nome": "Caduta materiali dall'alto", "categoria": "sicurezza", "sottocategoria": "cadute",
        "descrizione_breve": "Rischio di caduta di oggetti/materiali dall'alto sulle persone",
        "trigger": {"keywords": ["sollevamento", "montaggio", "gru", "carroponte"], "condizioni": ["montaggio_cantiere", "sollevamento"]},
        "condizioni_esclusione": ["solo_lavorazioni_a_terra"],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Notevole", "classe": "Grave"},
        "misure_prevenzione": ["Delimitare la zona sottostante il montaggio", "Imbracatura sicura dei carichi", "Vietare la sosta sotto carichi sospesi"],
        "note_pos_template": "", "dpi_ids": ["DPI-CASCO", "DPI-SCARPE"], "misure_ids": [], "apprestamenti_ids": ["APP-RETI-PROTEZIONE"],
        "documenti_richiesti": [], "domande_verifica": [{"testo": "Sono previsti sollevamenti di materiali con mezzi meccanici?", "impatto": "alto", "gate_critical": True}],
        "rif_normativo": "D.Lgs. 81/08 Art. 115", "gate_critical": True, "sort_order": 11,
    },
    {
        "codice": "RS-URTI", "nome": "Urti, colpi, impatti", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di urti contro ostacoli fissi o mobili",
        "trigger": {"keywords": ["montaggio", "assemblaggio", "struttura"], "condizioni": ["cantiere"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Modesta", "classe": "Modesto"},
        "misure_prevenzione": ["Mantenere ordine e pulizia nell'area di lavoro", "Segnalare ostacoli e sporgenze"],
        "note_pos_template": "", "dpi_ids": ["DPI-CASCO", "DPI-GUANTI-CROSTA", "DPI-SCARPE"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 All. IV", "gate_critical": False, "sort_order": 20,
    },
    {
        "codice": "RS-SCHIACCIAMENTO", "nome": "Schiacciamento", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di schiacciamento da mezzi, materiali o parti meccaniche",
        "trigger": {"keywords": ["pressa", "piegatura", "montaggio", "mezzo", "sollevamento"], "condizioni": ["mezzi_cantiere", "macchine"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Rispettare le distanze di sicurezza dai mezzi", "Verificare funzionamento dispositivi di arresto emergenza"],
        "note_pos_template": "", "dpi_ids": ["DPI-SCARPE", "DPI-GUANTI-CROSTA", "DPI-CASCO"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 All. V", "gate_critical": True, "sort_order": 21,
    },
    {
        "codice": "RS-CESOIAMENTO", "nome": "Cesoiamento", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di cesoiamento da parti meccaniche in movimento",
        "trigger": {"keywords": ["cesoia", "pressa", "piegatura", "calandra"], "condizioni": ["macchine"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Non introdurre le mani nella zona operativa", "Verificare protezioni organi lavoratori"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-CROSTA", "DPI-SCARPE"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 All. V", "gate_critical": False, "sort_order": 22,
    },
    {
        "codice": "RS-PROIEZIONE", "nome": "Proiezione schegge/detriti", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di proiezione di schegge, trucioli o detriti durante lavorazioni",
        "trigger": {"keywords": ["taglio", "molatura", "foratura", "flessibile", "sega"], "condizioni": ["lavorazioni_meccaniche"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Notevole", "classe": "Grave"},
        "misure_prevenzione": ["Utilizzare schermi e protezioni sugli utensili", "Delimitare l'area di lavoro"],
        "note_pos_template": "", "dpi_ids": ["DPI-OCCHIALI", "DPI-GUANTI-CROSTA", "DPI-TUTA"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 All. V", "gate_critical": False, "sort_order": 23,
    },
    {
        "codice": "RS-TAGLI", "nome": "Tagli e abrasioni", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di tagli e abrasioni da materiali e utensili",
        "trigger": {"keywords": ["taglio", "lamiera", "profilo", "bordi"], "condizioni": []},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Modesta", "classe": "Modesto"},
        "misure_prevenzione": ["Sbavare i bordi taglienti dei pezzi lavorati", "Utilizzare guanti e indumenti protettivi"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-CROSTA", "DPI-TUTA"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "", "gate_critical": False, "sort_order": 24,
    },
    {
        "codice": "RS-IMPIGLIAMENTO", "nome": "Impigliamento", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di impigliamento di indumenti o parti del corpo in organi rotanti",
        "trigger": {"keywords": ["tornio", "trapano", "fresatrice", "rotante"], "condizioni": ["macchine"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Notevole", "classe": "Modesto"},
        "misure_prevenzione": ["Indossare indumenti aderenti", "Rimuovere anelli, catene, bracciali", "Non utilizzare guanti vicino a organi rotanti"],
        "note_pos_template": "", "dpi_ids": ["DPI-TUTA"], "misure_ids": ["MIS-INDUMENTI-ADERENTI"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 All. V", "gate_critical": False, "sort_order": 25,
    },
    {
        "codice": "RS-RUMORE", "nome": "Rumore", "categoria": "salute", "sottocategoria": "fisico",
        "descrizione_breve": "Esposizione a livelli di rumore superiori ai limiti di legge",
        "trigger": {"keywords": ["taglio", "molatura", "martello", "compressore", "rumore"], "condizioni": ["lavorazioni_meccaniche"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Elevata", "danno": "Modesta", "classe": "Grave"},
        "misure_prevenzione": ["Utilizzare DPI uditivi nei reparti rumorosi", "Turnazione dei lavoratori esposti"],
        "note_pos_template": "Allegare valutazione fonometrica al POS", "dpi_ids": ["DPI-CUFFIE"], "misure_ids": ["MIS-VALUTAZIONE-RUMORE"], "apprestamenti_ids": [],
        "documenti_richiesti": [{"codice": "DOC-VAL-RUMORE", "nome": "Valutazione rischio rumore", "obbligatorio": True, "condizione": None}],
        "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 Titolo VIII Capo II", "gate_critical": False, "sort_order": 30,
    },
    {
        "codice": "RS-VIBRAZIONI", "nome": "Vibrazioni meccaniche", "categoria": "salute", "sottocategoria": "fisico",
        "descrizione_breve": "Esposizione a vibrazioni trasmesse al sistema mano-braccio o al corpo intero",
        "trigger": {"keywords": ["flessibile", "martello", "demolizione", "vibrazioni"], "condizioni": ["utensili_vibranti"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Modesta", "classe": "Modesto"},
        "misure_prevenzione": ["Limitare i tempi di esposizione", "Utilizzare utensili con sistemi antivibranti"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-CROSTA"], "misure_ids": ["MIS-VALUTAZIONE-VIBRAZIONI"], "apprestamenti_ids": [],
        "documenti_richiesti": [{"codice": "DOC-VAL-VIBRAZIONI", "nome": "Valutazione rischio vibrazioni", "obbligatorio": True, "condizione": None}],
        "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 Titolo VIII Capo III", "gate_critical": False, "sort_order": 31,
    },
    {
        "codice": "RS-RADIAZIONI-UV", "nome": "Radiazioni UV/IR (saldatura)", "categoria": "salute", "sottocategoria": "fisico",
        "descrizione_breve": "Esposizione a radiazioni ultraviolette e infrarosse da saldatura",
        "trigger": {"keywords": ["saldatura", "saldare", "MIG", "MAG", "TIG", "elettrodo"], "condizioni": ["saldatura"]},
        "condizioni_esclusione": ["nessuna_saldatura"],
        "valutazione_default": {"probabilita": "Elevata", "danno": "Notevole", "classe": "Gravissimo"},
        "misure_prevenzione": ["Utilizzare schermi e maschere omologate", "Schermare l'area per proteggere terzi"],
        "note_pos_template": "", "dpi_ids": ["DPI-SCHERMO-SALD", "DPI-TUTA"], "misure_ids": ["MIS-SCHERMATURA-AREA"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [{"testo": "Sono previste saldature in opera (non solo in officina)?", "impatto": "alto", "gate_critical": True}],
        "rif_normativo": "D.Lgs. 81/08 Titolo VIII Capo V", "gate_critical": True, "sort_order": 32,
    },
    {
        "codice": "RS-FUMI", "nome": "Fumi di saldatura / polveri", "categoria": "salute", "sottocategoria": "chimico",
        "descrizione_breve": "Esposizione a fumi metallici e polveri durante saldatura o taglio",
        "trigger": {"keywords": ["saldatura", "fumi", "polveri", "taglio_termico"], "condizioni": ["saldatura"]},
        "condizioni_esclusione": ["nessuna_saldatura"],
        "valutazione_default": {"probabilita": "Elevata", "danno": "Notevole", "classe": "Gravissimo"},
        "misure_prevenzione": ["Garantire aspirazione localizzata dei fumi", "Ventilazione adeguata dell'ambiente"],
        "note_pos_template": "", "dpi_ids": ["DPI-MASCHERA", "DPI-TUTA"], "misure_ids": ["MIS-ASPIRAZIONE-FUMI"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 Titolo IX", "gate_critical": True, "sort_order": 33,
    },
    {
        "codice": "RS-CHIMICO", "nome": "Rischio chimico (solventi, vernici)", "categoria": "salute", "sottocategoria": "chimico",
        "descrizione_breve": "Esposizione a sostanze chimiche pericolose",
        "trigger": {"keywords": ["verniciatura", "solvente", "vernice", "chimico", "resina"], "condizioni": ["verniciatura", "chimico"]},
        "condizioni_esclusione": ["nessuna_verniciatura"],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Notevole", "classe": "Grave"},
        "misure_prevenzione": ["Ventilazione forzata nell'area", "Utilizzare solo quantitativi necessari", "Conservare recipienti chiusi"],
        "note_pos_template": "Allegare schede di sicurezza (SDS) delle sostanze utilizzate",
        "dpi_ids": ["DPI-MASCHERA", "DPI-GUANTI-CROSTA", "DPI-OCCHIALI", "DPI-TUTA"], "misure_ids": ["MIS-VENTILAZIONE-FORZATA"], "apprestamenti_ids": [],
        "documenti_richiesti": [{"codice": "DOC-SDS", "nome": "Schede di sicurezza (SDS) sostanze", "obbligatorio": True, "condizione": None}],
        "domande_verifica": [{"testo": "Quali sostanze chimiche saranno utilizzate in cantiere?", "impatto": "medio", "gate_critical": False}],
        "rif_normativo": "D.Lgs. 81/08 Titolo IX", "gate_critical": False, "sort_order": 34,
    },
    {
        "codice": "RS-INALAZIONE", "nome": "Inalazione vapori/solventi", "categoria": "salute", "sottocategoria": "chimico",
        "descrizione_breve": "Rischio inalazione vapori organici e solventi",
        "trigger": {"keywords": ["solvente", "vapori", "verniciatura", "sgrassaggio"], "condizioni": ["verniciatura"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Notevole", "classe": "Grave"},
        "misure_prevenzione": ["Vietare fiamme libere nella zona", "Utilizzare maschere con filtro adeguato"],
        "note_pos_template": "", "dpi_ids": ["DPI-MASCHERA"], "misure_ids": ["MIS-VENTILAZIONE-FORZATA"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 Titolo IX", "gate_critical": False, "sort_order": 35,
    },
    {
        "codice": "RS-ELETTRICO", "nome": "Rischio elettrico", "categoria": "sicurezza", "sottocategoria": "elettrico",
        "descrizione_breve": "Rischio di elettrocuzione da contatto con parti in tensione",
        "trigger": {"keywords": ["elettrico", "quadro", "cablaggio", "impianto", "tensione"], "condizioni": ["impianti_elettrici"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Sezionare e verificare assenza tensione", "Solo personale qualificato PES/PAV"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-ISOLANTI", "DPI-SCARPE"], "misure_ids": ["MIS-SEZIONAMENTO-LINEA"], "apprestamenti_ids": [],
        "documenti_richiesti": [{"codice": "DOC-PES-PAV", "nome": "Attestato PES/PAV operatore", "obbligatorio": True, "condizione": "lavori_elettrici"}],
        "domande_verifica": [{"testo": "Sono previsti interventi su impianti elettrici o in prossimita di linee in tensione?", "impatto": "alto", "gate_critical": True}],
        "rif_normativo": "D.Lgs. 81/08 Titolo III Capo III", "gate_critical": True, "sort_order": 40,
    },
    {
        "codice": "RS-INCENDIO", "nome": "Incendio / esplosione", "categoria": "sicurezza", "sottocategoria": "incendio",
        "descrizione_breve": "Rischio di innesco incendio o esplosione da lavorazioni a caldo o sostanze infiammabili",
        "trigger": {"keywords": ["saldatura", "fiamma", "incendio", "esplosione", "infiammabile"], "condizioni": ["saldatura", "verniciatura"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Predisporre estintore nelle vicinanze", "Allontanare materiali infiammabili"],
        "note_pos_template": "Se saldatura/taglio in opera, valutare permesso lavoro a caldo",
        "dpi_ids": [], "misure_ids": ["MIS-ALLONTANARE-INFIAMMABILI"], "apprestamenti_ids": ["APP-ESTINTORE"],
        "documenti_richiesti": [{"codice": "DOC-PERMESSO-CALDO", "nome": "Permesso di lavoro a caldo", "obbligatorio": False, "condizione": "saldatura_in_opera"}],
        "domande_verifica": [{"testo": "Il cantiere e in area con materiali infiammabili o rischio esplosione?", "impatto": "medio", "gate_critical": False}],
        "rif_normativo": "D.Lgs. 81/08 Titolo XI", "gate_critical": True, "sort_order": 41,
    },
    {
        "codice": "RS-INVESTIMENTO", "nome": "Investimento da mezzi", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di investimento da parte di mezzi in movimento in cantiere",
        "trigger": {"keywords": ["mezzo", "camion", "carrello", "autogrù", "viabilita"], "condizioni": ["mezzi_cantiere"]},
        "condizioni_esclusione": ["solo_officina"],
        "valutazione_default": {"probabilita": "Medio Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Segnalare percorsi pedonali e veicolari", "Indossare gilet alta visibilita"],
        "note_pos_template": "", "dpi_ids": ["DPI-GILET-AV", "DPI-SCARPE", "DPI-CASCO"], "misure_ids": ["MIS-PERCORSI-SEGNALATI"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [{"testo": "Il cantiere prevede circolazione di mezzi (camion, autogrù, carrelli)?", "impatto": "alto", "gate_critical": True}],
        "rif_normativo": "D.Lgs. 81/08 All. IV", "gate_critical": True, "sort_order": 42,
    },
    {
        "codice": "RS-RIBALTAMENTO", "nome": "Ribaltamento mezzo di sollevamento", "categoria": "sicurezza", "sottocategoria": "meccanico",
        "descrizione_breve": "Rischio di ribaltamento di gru, autogrù o piattaforme elevabili",
        "trigger": {"keywords": ["autogrù", "gru", "sollevamento", "PLE"], "condizioni": ["sollevamento"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Bassa", "danno": "Ingente", "classe": "Grave"},
        "misure_prevenzione": ["Verificare portata del mezzo e del terreno", "Stabilizzatori sempre estesi", "Rispettare diagramma di carico"],
        "note_pos_template": "", "dpi_ids": ["DPI-CASCO"], "misure_ids": ["MIS-VERIFICA-PORTATA"], "apprestamenti_ids": [],
        "documenti_richiesti": [{"codice": "DOC-LIBRETTO-MEZZO", "nome": "Libretto d'uso e manutenzione mezzo", "obbligatorio": True, "condizione": None}],
        "domande_verifica": [{"testo": "E previsto l'uso di autogrù o mezzi di sollevamento?", "impatto": "alto", "gate_critical": True}],
        "rif_normativo": "D.Lgs. 81/08 All. VI", "gate_critical": True, "sort_order": 43,
    },
    {
        "codice": "RS-MMC", "nome": "Movimentazione manuale carichi", "categoria": "salute", "sottocategoria": "ergonomico",
        "descrizione_breve": "Rischio da movimentazione manuale di carichi superiori ai limiti",
        "trigger": {"keywords": ["movimentazione", "sollevamento_manuale", "carico", "trasporto_manuale"], "condizioni": ["movimentazione_carichi"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Modesta", "classe": "Modesto"},
        "misure_prevenzione": ["Utilizzare ausili meccanici per carichi > 25 kg", "Formazione corretta movimentazione"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-CROSTA", "DPI-SCARPE"], "misure_ids": ["MIS-AUSILI-MECCANICI"], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "D.Lgs. 81/08 Titolo VI", "gate_critical": False, "sort_order": 50,
    },
    {
        "codice": "RS-USTIONI", "nome": "Ustioni", "categoria": "sicurezza", "sottocategoria": "termico",
        "descrizione_breve": "Rischio di ustioni da materiali caldi, scintille o fiamma",
        "trigger": {"keywords": ["saldatura", "taglio_termico", "caldo", "fiamma"], "condizioni": ["saldatura", "taglio_termico"]},
        "condizioni_esclusione": [],
        "valutazione_default": {"probabilita": "Medio Alta", "danno": "Modesta", "classe": "Modesto"},
        "misure_prevenzione": ["Utilizzare DPI resistenti al calore", "Segnalare le superfici calde"],
        "note_pos_template": "", "dpi_ids": ["DPI-GUANTI-CALORE", "DPI-TUTA", "DPI-SCARPE"], "misure_ids": [], "apprestamenti_ids": [],
        "documenti_richiesti": [], "domande_verifica": [],
        "rif_normativo": "", "gate_critical": False, "sort_order": 51,
    },
]

# ═══════════════════════════════════════════════════════════════════
#  SEED DATA — Livello 1: Fasi di Lavoro (11 entries)
# ═══════════════════════════════════════════════════════════════════

FASI_SEED = [
    {
        "codice": "FL-001", "nome": "Scarico e movimentazione materiali", "descrizione": "Scarico materiali dal mezzo di trasporto e movimentazione in area cantiere/officina",
        "categoria": "movimentazione", "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "trigger": {"keywords": ["scarico", "movimentazione", "trasporto", "consegna", "materiali"], "contesto": ["cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-MMC", "RS-INVESTIMENTO", "RS-SCHIACCIAMENTO"],
        "macchine_tipiche": ["Carrello elevatore", "Carroponte", "Transpallet"],
        "sort_order": 10,
    },
    {
        "codice": "FL-002", "nome": "Tracciamento e predisposizione area", "descrizione": "Tracciamento a terra, predisposizione dell'area di lavoro, posizionamento segnaletica",
        "categoria": "preparazione", "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "trigger": {"keywords": ["tracciamento", "predisposizione", "area", "segnaletica"], "contesto": ["cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-URTI", "RS-INVESTIMENTO"],
        "macchine_tipiche": ["Attrezzi manuali", "Livella laser"],
        "sort_order": 20,
    },
    {
        "codice": "FL-003", "nome": "Taglio e preparazione profili", "descrizione": "Taglio di lamiere, profili e tubolari metallici con utensili manuali e automatici",
        "categoria": "carpenteria_metallica", "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "trigger": {"keywords": ["taglio", "lamiera", "profilo", "cesoia", "plasma", "ossitaglio", "sega"], "contesto": ["officina", "cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-PROIEZIONE", "RS-RUMORE", "RS-VIBRAZIONI", "RS-TAGLI"],
        "macchine_tipiche": ["Sega circolare", "Flessibile", "Cesoie", "Taglio plasma"],
        "sort_order": 30,
    },
    {
        "codice": "FL-004", "nome": "Foratura e lavorazione meccanica", "descrizione": "Foratura, fresatura e lavorazioni meccaniche su profili e lamiere",
        "categoria": "lavorazione_meccanica", "applicabile_a": ["EN_1090", "GENERICA"],
        "trigger": {"keywords": ["foratura", "fresatura", "trapano", "fresa", "lavorazione_meccanica"], "contesto": ["officina"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-PROIEZIONE", "RS-IMPIGLIAMENTO", "RS-RUMORE"],
        "macchine_tipiche": ["Trapano a colonna", "Fresatrice", "Trapano elettrico"],
        "sort_order": 40,
    },
    {
        "codice": "FL-005", "nome": "Piegatura e calandratura", "descrizione": "Piegatura lamiere/profili con pressa piegatrice e calandratura",
        "categoria": "lavorazione_meccanica", "applicabile_a": ["EN_1090", "GENERICA"],
        "trigger": {"keywords": ["piegatura", "calandra", "pressa", "piegare"], "contesto": ["officina"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-SCHIACCIAMENTO", "RS-CESOIAMENTO", "RS-VIBRAZIONI"],
        "macchine_tipiche": ["Pressa piegatrice", "Calandra"],
        "sort_order": 50,
    },
    {
        "codice": "FL-006", "nome": "Saldatura", "descrizione": "Saldatura MIG/MAG, TIG, ad elettrodo in officina o in opera",
        "categoria": "saldatura", "applicabile_a": ["EN_1090", "GENERICA"],
        "trigger": {"keywords": ["saldatura", "saldare", "MIG", "MAG", "TIG", "elettrodo", "giunto_saldato"], "contesto": ["officina", "cantiere"]},
        "condizioni_esclusione": ["nessuna_saldatura"],
        "rischi_ids": ["RS-RADIAZIONI-UV", "RS-FUMI", "RS-USTIONI", "RS-INCENDIO"],
        "macchine_tipiche": ["Saldatrice MIG/MAG", "Saldatrice TIG", "Saldatrice ad elettrodo"],
        "sort_order": 60,
    },
    {
        "codice": "FL-007", "nome": "Verniciatura / Trattamenti superficiali", "descrizione": "Verniciatura a spruzzo, trattamenti antiruggine, zincatura, sabbiatura",
        "categoria": "verniciatura", "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "trigger": {"keywords": ["verniciatura", "vernice", "antiruggine", "trattamento", "sabbiatura", "zincatura"], "contesto": ["officina"]},
        "condizioni_esclusione": ["nessuna_verniciatura"],
        "rischi_ids": ["RS-CHIMICO", "RS-INCENDIO", "RS-INALAZIONE"],
        "macchine_tipiche": ["Pistola a spruzzo", "Compressore", "Sabbiatrice"],
        "sort_order": 70,
    },
    {
        "codice": "FL-008", "nome": "Montaggio strutture in cantiere", "descrizione": "Montaggio e assemblaggio strutture metalliche in cantiere, bullonatura e fissaggio",
        "categoria": "montaggio", "applicabile_a": ["EN_1090", "GENERICA"],
        "trigger": {"keywords": ["montaggio", "posa", "assemblaggio", "struttura", "cantiere", "bullonatura"], "contesto": ["cantiere"]},
        "condizioni_esclusione": ["solo_officina"],
        "rischi_ids": ["RS-CADUTA-ALTO", "RS-CADUTA-MAT", "RS-URTI", "RS-SCHIACCIAMENTO"],
        "macchine_tipiche": ["Autogrù", "Avvitatore elettrico", "Trapano", "Chiave dinamometrica"],
        "sort_order": 80,
    },
    {
        "codice": "FL-009", "nome": "Sollevamento con mezzi meccanici", "descrizione": "Sollevamento e movimentazione carichi con autogrù, gru, carroponte",
        "categoria": "sollevamento", "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "trigger": {"keywords": ["sollevamento", "autogrù", "gru", "carroponte", "imbracatura", "tirante"], "contesto": ["cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-CADUTA-MAT", "RS-INVESTIMENTO", "RS-SCHIACCIAMENTO", "RS-RIBALTAMENTO"],
        "macchine_tipiche": ["Autogrù", "Gru a torre", "Carroponte", "Fasce di imbracatura"],
        "sort_order": 90,
    },
    {
        "codice": "FL-010", "nome": "Installazione cancelli/portoni", "descrizione": "Montaggio, installazione e regolazione di cancelli industriali e portoni automatici",
        "categoria": "montaggio_en13241", "applicabile_a": ["EN_13241"],
        "trigger": {"keywords": ["cancello", "portone", "automazione", "EN_13241", "chiusura"], "contesto": ["cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-CADUTA-ALTO", "RS-SCHIACCIAMENTO", "RS-ELETTRICO", "RS-TAGLI"],
        "macchine_tipiche": ["Avvitatore elettrico", "Trapano", "Flessibile", "Saldatrice"],
        "sort_order": 100,
    },
    {
        "codice": "FL-011", "nome": "Collaudo e messa in esercizio", "descrizione": "Collaudo funzionale, test di sicurezza e messa in esercizio dell'opera",
        "categoria": "collaudo", "applicabile_a": ["EN_13241"],
        "trigger": {"keywords": ["collaudo", "test", "messa_in_esercizio", "verifica_funzionale"], "contesto": ["cantiere"]},
        "condizioni_esclusione": [],
        "rischi_ids": ["RS-ELETTRICO", "RS-SCHIACCIAMENTO"],
        "macchine_tipiche": ["Strumenti di misura", "Tester elettrici"],
        "sort_order": 110,
    },
]

# ── Defaults per cantiere ──
MACCHINE_DEFAULT = [
    {"nome": "Avvitatore elettrico", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Flessibile (smerigliatrice)", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Martello demolitore", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Sega circolare", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Trapano elettrico", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Utensili elettrici portatili", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Utensili manuali", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Saldatrice MIG/MAG", "marcata_ce": True, "verifiche_periodiche": True},
]
DPI_CANTIERE_DEFAULT = [
    {"tipo_dpi": "Tuta lavoro", "presente": True},
    {"tipo_dpi": "Scarpe antinfortunistiche", "presente": True},
    {"tipo_dpi": "Guanti", "presente": True},
    {"tipo_dpi": "Occhiali di protezione", "presente": True},
    {"tipo_dpi": "Mascherine antipolvere", "presente": True},
    {"tipo_dpi": "Otoprotettori", "presente": True},
    {"tipo_dpi": "Casco", "presente": True},
    {"tipo_dpi": "Cinture di sicurezza", "presente": True},
]
NUMERI_UTILI_DEFAULT = [
    {"servizio": "Vigili del fuoco", "numero": "115"},
    {"servizio": "Pronto soccorso", "numero": "118"},
    {"servizio": "Carabinieri", "numero": "112"},
    {"servizio": "Commissariato di P.S.", "numero": "113"},
]


# ═══════════════════════════════════════════════════════════════════
#  SEED — 3 collections
# ═══════════════════════════════════════════════════════════════════

async def seed_libreria_v2(user_id: str):
    """Seed the 3-level risk library for a user (idempotent)."""
    fasi_count = await db.lib_fasi_lavoro.count_documents({"user_id": user_id})
    rischi_count = await db.lib_rischi_sicurezza.count_documents({"user_id": user_id})
    dpi_count = await db.lib_dpi_misure.count_documents({"user_id": user_id})

    if fasi_count > 0 and rischi_count > 0 and dpi_count > 0:
        return {"seeded": False, "fasi": fasi_count, "rischi": rischi_count, "dpi_misure": dpi_count}

    now = datetime.now(timezone.utc).isoformat()
    results = {}

    # Seed DPI/Misure/Apprestamenti
    if dpi_count == 0:
        docs = []
        for item in DPI_MISURE_SEED:
            docs.append({**item, "user_id": user_id, "active": True, "version": 1, "source": "seed", "created_at": now, "updated_at": now})
        await db.lib_dpi_misure.insert_many(docs)
        results["dpi_misure"] = len(docs)
    else:
        results["dpi_misure"] = dpi_count

    # Seed Rischi
    if rischi_count == 0:
        docs = []
        for item in RISCHI_SEED:
            docs.append({**item, "user_id": user_id, "active": True, "version": 1, "source": "seed", "created_at": now, "updated_at": now})
        await db.lib_rischi_sicurezza.insert_many(docs)
        results["rischi"] = len(docs)
    else:
        results["rischi"] = rischi_count

    # Seed Fasi
    if fasi_count == 0:
        docs = []
        for item in FASI_SEED:
            docs.append({**item, "user_id": user_id, "active": True, "version": 1, "source": "seed", "created_at": now, "updated_at": now})
        await db.lib_fasi_lavoro.insert_many(docs)
        results["fasi"] = len(docs)
    else:
        results["fasi"] = fasi_count

    results["seeded"] = True
    return results


# ═══════════════════════════════════════════════════════════════════
#  LIBRERIA — Read APIs (3 collections)
# ═══════════════════════════════════════════════════════════════════

async def get_fasi_lavoro(user_id: str, normativa: Optional[str] = None) -> list:
    query = {"user_id": user_id, "active": True}
    if normativa:
        query["applicabile_a"] = normativa
    return await db.lib_fasi_lavoro.find(query, {"_id": 0}).sort("sort_order", 1).to_list(100)


async def get_rischi_sicurezza(user_id: str, categoria: Optional[str] = None) -> list:
    query = {"user_id": user_id, "active": True}
    if categoria:
        query["categoria"] = categoria
    return await db.lib_rischi_sicurezza.find(query, {"_id": 0}).sort("sort_order", 1).to_list(200)


async def get_dpi_misure(user_id: str, tipo: Optional[str] = None) -> list:
    query = {"user_id": user_id, "active": True}
    if tipo:
        query["tipo"] = tipo
    return await db.lib_dpi_misure.find(query, {"_id": 0}).sort("sort_order", 1).to_list(200)


async def get_rischi_per_codici(user_id: str, codici: list) -> list:
    """Get rischi by their codice list — used to resolve fase.rischi_ids."""
    return await db.lib_rischi_sicurezza.find(
        {"user_id": user_id, "codice": {"$in": codici}, "active": True}, {"_id": 0}
    ).to_list(100)


async def get_dpi_per_codici(user_id: str, codici: list) -> list:
    """Get DPI/misure by their codice list — used to resolve rischio.dpi_ids."""
    return await db.lib_dpi_misure.find(
        {"user_id": user_id, "codice": {"$in": codici}, "active": True}, {"_id": 0}
    ).to_list(100)


# ═══════════════════════════════════════════════════════════════════
#  CANTIERI SICUREZZA — CRUD (updated schema v2)
# ═══════════════════════════════════════════════════════════════════

def _new_cantiere_template(cantiere_id: str, user_id: str, commessa_id: Optional[str] = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "cantiere_id": cantiere_id,
        "user_id": user_id,
        "parent_commessa_id": commessa_id,
        "status": "bozza",
        "revisioni": [{"rev": "00", "motivazione": "Emissione", "data": ""}],
        "dati_cantiere": {
            "attivita_cantiere": "", "data_inizio_lavori": "", "data_fine_prevista": "",
            "indirizzo_cantiere": "", "citta_cantiere": "", "provincia_cantiere": "",
        },
        "soggetti_riferimento": {
            "committente": "", "responsabile_lavori": "", "direttore_lavori": "",
            "progettista": "", "csp": "", "cse": "",
        },
        "lavoratori_coinvolti": [],
        "turni_lavoro": {"mattina": "08:00-13:00", "pomeriggio": "14:00-17:00", "note": ""},
        "subappalti": [],
        "dpi_presenti": list(DPI_CANTIERE_DEFAULT),
        "macchine_attrezzature": list(MACCHINE_DEFAULT),
        "sostanze_chimiche": [],
        "stoccaggio_materiali": "",
        "servizi_igienici": "",
        # ── v2: structured safety data ──
        "fasi_lavoro_selezionate": [],
        "dpi_calcolati": [],
        "misure_calcolate": [],
        "apprestamenti_calcolati": [],
        "domande_residue": [],
        # ── general ──
        "numeri_utili": list(NUMERI_UTILI_DEFAULT),
        "includi_covid19": False,
        "data_dichiarazione": "",
        "note_aggiuntive": "",
        "ai_precompilazione": None,
        "gate_pos_status": {"completezza_percentuale": 0, "campi_mancanti": [], "pronto_per_generazione": False},
        "created_at": now,
        "updated_at": now,
    }


async def crea_cantiere(user_id: str, commessa_id: Optional[str] = None, pre_fill: Optional[dict] = None) -> dict:
    cantiere_id = f"cant_{uuid.uuid4().hex[:12]}"
    doc = _new_cantiere_template(cantiere_id, user_id, commessa_id)

    if commessa_id:
        commessa = await db.commesse.find_one({"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0})
        if commessa:
            doc["dati_cantiere"]["attivita_cantiere"] = commessa.get("description", "")
            doc["soggetti_riferimento"]["committente"] = commessa.get("client_name", "")

    if pre_fill:
        for key in ["dati_cantiere", "soggetti_riferimento", "turni_lavoro"]:
            if key in pre_fill and isinstance(pre_fill[key], dict):
                doc[key].update(pre_fill[key])
        for key in ["lavoratori_coinvolti", "subappalti", "sostanze_chimiche", "fasi_lavoro_selezionate"]:
            if key in pre_fill and isinstance(pre_fill[key], list):
                doc[key] = pre_fill[key]

    await db.cantieri_sicurezza.insert_one(doc)
    doc.pop("_id", None)
    await seed_libreria_v2(user_id)
    return doc


async def get_cantiere(cantiere_id: str, user_id: str) -> Optional[dict]:
    return await db.cantieri_sicurezza.find_one({"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0})


async def get_cantieri_by_commessa(commessa_id: str, user_id: str) -> list:
    return await db.cantieri_sicurezza.find({"parent_commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}).to_list(100)


async def list_cantieri(user_id: str) -> list:
    return await db.cantieri_sicurezza.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


async def aggiorna_cantiere(cantiere_id: str, user_id: str, updates: dict) -> Optional[dict]:
    for key in ["cantiere_id", "user_id", "_id", "created_at"]:
        updates.pop(key, None)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.cantieri_sicurezza.find_one_and_update(
        {"cantiere_id": cantiere_id, "user_id": user_id},
        {"$set": updates}, return_document=True,
    )
    if not result:
        return None

    gate = calcola_gate_pos(result)
    await db.cantieri_sicurezza.update_one({"cantiere_id": cantiere_id}, {"$set": {"gate_pos_status": gate}})
    result["gate_pos_status"] = gate
    result.pop("_id", None)
    return result


async def elimina_cantiere(cantiere_id: str, user_id: str) -> bool:
    r = await db.cantieri_sicurezza.delete_one({"cantiere_id": cantiere_id, "user_id": user_id})
    return r.deleted_count > 0


# ═══════════════════════════════════════════════════════════════════
#  GATE POS — Completeness Check (v2 with gate_critical)
# ═══════════════════════════════════════════════════════════════════

CAMPI_OBBLIGATORI = [
    ("dati_cantiere.indirizzo_cantiere", "Indirizzo cantiere"),
    ("dati_cantiere.citta_cantiere", "Citta cantiere"),
    ("dati_cantiere.data_inizio_lavori", "Data inizio lavori"),
    ("soggetti_riferimento.committente", "Committente"),
    ("lavoratori_coinvolti", "Almeno un lavoratore"),
    ("fasi_lavoro_selezionate", "Almeno una fase di lavoro"),
]
CAMPI_OPZIONALI = [
    ("dati_cantiere.data_fine_prevista", "Data fine prevista"),
    ("dati_cantiere.attivita_cantiere", "Attivita cantiere"),
    ("soggetti_riferimento.direttore_lavori", "Direttore lavori"),
    ("soggetti_riferimento.cse", "Coordinatore sicurezza esecuzione"),
    ("data_dichiarazione", "Data dichiarazione"),
]


def _get_nested(doc: dict, path: str):
    keys = path.split(".")
    val = doc
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return None
    return val


def calcola_gate_pos(cantiere: dict) -> dict:
    campi_mancanti = []
    blockers = []
    total_checks = len(CAMPI_OBBLIGATORI) + len(CAMPI_OPZIONALI)
    passed = 0

    for path, label in CAMPI_OBBLIGATORI:
        val = _get_nested(cantiere, path)
        if isinstance(val, list) and len(val) > 0:
            passed += 1
        elif val:
            passed += 1
        else:
            campi_mancanti.append(label)

    for path, label in CAMPI_OPZIONALI:
        val = _get_nested(cantiere, path)
        if (isinstance(val, list) and len(val) > 0) or val:
            passed += 1

    # Check gate_critical domande_residue
    for domanda in cantiere.get("domande_residue", []):
        if domanda.get("gate_critical") and domanda.get("stato") == "aperta":
            blockers.append(f"Domanda critica aperta: {domanda.get('testo', '')[:60]}...")

    pct = round((passed / total_checks) * 100) if total_checks > 0 else 0
    pronto = len(campi_mancanti) == 0 and len(blockers) == 0

    return {
        "completezza_percentuale": pct,
        "campi_mancanti": campi_mancanti,
        "blockers": blockers,
        "pronto_per_generazione": pronto,
    }

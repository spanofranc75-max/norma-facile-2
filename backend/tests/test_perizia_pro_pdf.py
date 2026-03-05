"""Test PDF Perizia Pro - verifica generazione con dati mock."""
import sys
sys.path.insert(0, "/app/backend")

from services.pdf_perizia_sopralluogo import generate_perizia_pdf

# Mock data
sopralluogo = {
    "sopralluogo_id": "sop_test123",
    "document_number": "SOP-2026/0001",
    "client_name": "Industrie Rossi S.r.l.",
    "indirizzo": "Via Roma 15",
    "comune": "Modena",
    "provincia": "MO",
    "tipo_intervento": "messa_a_norma",
    "descrizione_utente": "Cancello scorrevole industriale senza protezioni",
    "note_tecnico": "Verificare anche la struttura portante del binario.",
    "created_at": "2026-03-05T10:00:00Z",
    "analisi_ai": {
        "tipo_chiusura": "scorrevole",
        "descrizione_generale": "Cancello scorrevole industriale di circa 6 metri, motorizzato con motore laterale. La struttura appare in buone condizioni ma mancano diversi dispositivi di sicurezza obbligatori.",
        "conformita_percentuale": 28,
        "rischi": [
            {
                "zona": "Bordo chiusura lato muro",
                "tipo_rischio": "schiacciamento",
                "gravita": "alta",
                "problema": "Assenza totale di costa sensibile sul bordo di chiusura principale. Il punto di schiacciamento tra anta e stipite non è protetto.",
                "norma_riferimento": "EN 12453 par. 5.1.1",
                "soluzione": "Installare costa sensibile 8K2 resistiva di lunghezza adeguata (min 2m) sul bordo di chiusura principale.",
                "confermato": True,
            },
            {
                "zona": "Zona di passaggio pedonale",
                "tipo_rischio": "impatto",
                "gravita": "alta",
                "problema": "Nessun rilevamento di presenza nell'area di apertura/chiusura. Rischio di impatto con pedoni.",
                "norma_riferimento": "EN 12453 par. 5.1.2",
                "soluzione": "Installare coppia di fotocellule orientabili ad altezza 40cm e 100cm.",
                "confermato": True,
            },
            {
                "zona": "Parte alta cancello / Zona cesoiamento",
                "tipo_rischio": "cesoiamento",
                "gravita": "media",
                "problema": "Spazi tra le maglie del cancello superiori a 25mm possono causare cesoiamento delle dita.",
                "norma_riferimento": "EN 13241 par. 4.3",
                "soluzione": "Applicare rete anti-cesoiamento con maglia massimo 25x25mm nella zona a rischio.",
                "confermato": True,
            },
            {
                "zona": "Motore / Sistema di azionamento",
                "tipo_rischio": "impatto",
                "gravita": "media",
                "problema": "Motore privo di encoder o limitatore di coppia. In caso di ostacolo il cancello non si arresta.",
                "norma_riferimento": "EN 12453 par. 5.4",
                "soluzione": "Installare encoder sul motore scorrevole per il rilevamento degli ostacoli e la limitazione della forza.",
                "confermato": True,
            },
        ],
        "dispositivi_presenti": ["Lampeggiante", "Selettore a chiave"],
        "dispositivi_mancanti": [
            "Costa sensibile di sicurezza",
            "Fotocellule",
            "Encoder motore",
            "Rete anti-cesoiamento",
            "Finecorsa di apertura",
        ],
        "materiali_suggeriti": [
            {"keyword": "costa", "descrizione": "Costa sensibile 8K2 resistiva 2m", "quantita": 1, "prezzo": 180, "priorita": "obbligatorio", "descrizione_catalogo": "Costa sensibile di sicurezza 8K2 (2m)"},
            {"keyword": "fotocellula", "descrizione": "Coppia fotocellule orientabili", "quantita": 2, "prezzo": 85, "priorita": "obbligatorio", "descrizione_catalogo": "Coppia fotocellule orientabili"},
            {"keyword": "rete", "descrizione": "Rete anti-cesoiamento 25x25mm", "quantita": 4, "prezzo": 28, "priorita": "obbligatorio", "descrizione_catalogo": "Rete anti-cesoiamento 25x25mm (al mq)"},
            {"keyword": "encoder", "descrizione": "Encoder per motore scorrevole", "quantita": 1, "prezzo": 95, "priorita": "obbligatorio", "descrizione_catalogo": "Encoder per motore scorrevole"},
            {"keyword": "finecorsa", "descrizione": "Finecorsa magnetico", "quantita": 1, "prezzo": 40, "priorita": "consigliato", "descrizione_catalogo": "Finecorsa magnetico (coppia)"},
        ],
        "note_tecniche": "Si consiglia un intervento completo di messa a norma. La struttura portante è in buone condizioni.",
    },
}

company = {
    "company_name": "Metal Works S.r.l.",
    "address": "Via dell'Industria 42",
    "cap": "41100",
    "city": "Modena",
    "province": "MO",
    "partita_iva": "02345678901",
    "phone": "+39 059 123456",
    "email": "info@metalworks.it",
}

print("Generating PDF...")
pdf_bytes = generate_perizia_pdf(sopralluogo, company, photos_b64=None)
out_path = "/tmp/test_perizia_pro.pdf"
with open(out_path, "wb") as f:
    f.write(pdf_bytes)
print(f"PDF generated: {out_path} ({len(pdf_bytes):,} bytes, {len(pdf_bytes)//1024} KB)")

# Also test with low conformity
sopralluogo["analisi_ai"]["conformita_percentuale"] = 72
pdf2 = generate_perizia_pdf(sopralluogo, company, photos_b64=None)
with open("/tmp/test_perizia_pro_green.pdf", "wb") as f:
    f.write(pdf2)
print(f"PDF (green) generated: {len(pdf2):,} bytes")

sopralluogo["analisi_ai"]["conformita_percentuale"] = 50
pdf3 = generate_perizia_pdf(sopralluogo, company, photos_b64=None)
with open("/tmp/test_perizia_pro_amber.pdf", "wb") as f:
    f.write(pdf3)
print(f"PDF (amber) generated: {len(pdf3):,} bytes")

print("\nAll 3 PDFs generated successfully!")

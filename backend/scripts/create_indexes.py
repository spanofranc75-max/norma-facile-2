"""Create MongoDB indexes for critical collections."""

from pymongo import MongoClient, ASCENDING, DESCENDING

client = MongoClient("mongodb://localhost:27017")
db = client["test_database"]

indexes = [
    # Commesse
    ("commesse", [("user_id", ASCENDING), ("status", ASCENDING)]),
    ("commesse", [("user_id", ASCENDING), ("numero", ASCENDING)]),
    ("commesse", [("user_id", ASCENDING), ("created_at", DESCENDING)]),

    # Preventivi
    ("preventivi", [("user_id", ASCENDING), ("status", ASCENDING)]),
    ("preventivi", [("user_id", ASCENDING), ("number", ASCENDING)]),
    ("preventivi", [("user_id", ASCENDING), ("created_at", DESCENDING)]),

    # DDT
    ("ddt_documents", [("user_id", ASCENDING), ("commessa_id", ASCENDING)]),
    ("ddt_documents", [("user_id", ASCENDING), ("created_at", DESCENDING)]),

    # Fatture ricevute (passive)
    ("fatture_ricevute", [("user_id", ASCENDING), ("payment_status", ASCENDING)]),
    ("fatture_ricevute", [("user_id", ASCENDING), ("data_scadenza_pagamento", ASCENDING)]),

    # Fatture emesse (attive)
    ("invoices", [("user_id", ASCENDING), ("payment_status", ASCENDING)]),
    ("invoices", [("user_id", ASCENDING), ("created_at", DESCENDING)]),

    # Material batches
    ("material_batches", [("commessa_id", ASCENDING), ("heat_number", ASCENDING)]),
    ("material_batches", [("user_id", ASCENDING)]),

    # Movimenti bancari
    ("movimenti_bancari", [("user_id", ASCENDING), ("stato_riconciliazione", ASCENDING)]),
    ("movimenti_bancari", [("user_id", ASCENDING), ("data", DESCENDING)]),

    # Clienti
    ("clients", [("user_id", ASCENDING), ("business_name", ASCENDING)]),

    # Counters
    ("document_counters", [("counter_id", ASCENDING)], True),
]

print("Creating indexes...")
for entry in indexes:
    coll_name = entry[0]
    keys = entry[1]
    unique = entry[2] if len(entry) > 2 else False
    try:
        result = db[coll_name].create_index(keys, unique=unique)
        print(f"  {coll_name}: {result}")
    except Exception as e:
        print(f"  {coll_name}: ERROR - {e}")

# Show index info for main collections
print("\n--- Index verification ---")
for coll in ["commesse", "preventivi", "fatture_ricevute", "invoices", "movimenti_bancari"]:
    info = db[coll].index_information()
    print(f"\n{coll}:")
    for name, details in info.items():
        print(f"  {name}: {details['key']}")

client.close()
print("\nDone.")

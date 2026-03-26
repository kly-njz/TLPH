# clear_and_seed_quotations.py
"""
Clears the 'quotations' collection and seeds it with 10 new documents
matching the current workflow schema. Includes:
- 4 for Victoria (municipality, REGION-IV-B)
- 4 for Calapan (municipality, REGION-IV-B)
- 2 for REGION-IV-B (regional only, no municipality)
"""
from firebase_config import get_firestore_db
from datetime import datetime
import random

REGION = "REGION-IV-B"
MUNICIPALITIES = ["Victoria", "Calapan"]

# Example clients and descriptions
CLIENTS = ["ABC Corp", "XYZ Trading", "Delta Inc", "Omega Ltd"]
DESCRIPTIONS = [
    "Supply of office equipment",
    "Consultancy services",
    "Construction materials",
    "IT infrastructure upgrade",
    "Environmental survey",
    "Community outreach",
]
SCOPES = ["municipal", "regional"]


def clear_quotations_collection():
    db = get_firestore_db()
    batch = db.batch()
    docs = db.collection("quotations").stream()
    for doc in docs:
        batch.delete(doc.reference)
    batch.commit()
    print("Cleared 'quotations' collection.")


def seed_quotations():
    db = get_firestore_db()
    now = datetime.utcnow().isoformat()
    quotations = []
    # 4 for Victoria, 4 for Calapan (municipal)
    for m in MUNICIPALITIES:
        for i in range(4):
            client = random.choice(CLIENTS)
            desc = random.choice(DESCRIPTIONS)
            amount = random.randint(10000, 100000)
            q = {
                "number": f"Q-{m[:3].upper()}-{i+1:02d}",
                "client": client,
                "amount": amount,
                "date": now,
                "status": "PENDING",
                "region": REGION,
                "municipality": m,
                "description": desc,
                "scope": "municipal",
                "created_by": f"{m.lower()}_admin@demo.com",
                "created_by_role": "municipal_admin",
                "created_at": now,
                "updated_at": now,
                "deliver_from": "MUNICIPAL",
                "deliver_to": m,
                "deliver_to_type": "municipality",
                "history": [
                    {
                        "action": "created",
                        "by": f"{m.lower()}_admin@demo.com",
                        "timestamp": now,
                        "notes": "Initial creation"
                    }
                ]
            }
            quotations.append(q)
    # 2 for REGION-IV-B (regional only)
    for i in range(2):
        client = random.choice(CLIENTS)
        desc = random.choice(DESCRIPTIONS)
        amount = random.randint(20000, 120000)
        q = {
            "number": f"Q-REG-{i+1:02d}",
            "client": client,
            "amount": amount,
            "date": now,
            "status": "PENDING",
            "region": REGION,
            "municipality": "",
            "description": desc,
            "scope": "regional",
            "created_by": "regional_admin@demo.com",
            "created_by_role": "regional_admin",
            "created_at": now,
            "updated_at": now,
            "deliver_from": "REGIONAL",
            "deliver_to": REGION,
            "deliver_to_type": "region",
            "history": [
                {
                    "action": "created",
                    "by": "regional_admin@demo.com",
                    "timestamp": now,
                    "notes": "Initial creation"
                }
            ]
        }
        quotations.append(q)
    # Insert all
    for q in quotations:
        ref = db.collection("quotations").document()
        q["id"] = ref.id
        ref.set(q)
    print(f"Seeded {len(quotations)} quotations.")


if __name__ == "__main__":
    clear_quotations_collection()
    seed_quotations()
    print("Done.")

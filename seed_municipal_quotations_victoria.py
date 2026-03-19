from datetime import datetime, timedelta

from firebase_config import get_firestore_db, initialize_firebase_admin


def main():
    initialize_firebase_admin()
    db = get_firestore_db()

    municipality = "Victoria"
    region = "MIMAROPA"

    seed_rows = [
        ("MQ-2026-101", "Municipal ENRO - Procurement", "Alcate", 25000.00, "PENDING", -30),
        ("MQ-2026-102", "Solid Waste Management Office", "Bagong Silang", 18250.00, "APPROVED", -24),
        ("MQ-2026-103", "Municipal Planning Office", "Bethel", 47200.00, "APPROVED", -16),
        ("MQ-2026-104", "Community Watershed Program", "Loyal", 15800.00, "REJECTED", -11),
        ("MQ-2026-105", "Barangay Materials Recovery Facility", "San Antonio", 33000.00, "PENDING", -6),
    ]

    for i, (number, client, barangay, amount, status, offset_days) in enumerate(seed_rows, start=1):
        doc_id = f"VIC-QUOTE-{datetime.now().strftime('%Y%m%d')}-{i:02d}"
        filing_date = (datetime.now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")
        db.collection("municipal_quotations").document(doc_id).set(
            {
                "number": number,
                "client": client,
                "barangay": barangay,
                "amount": amount,
                "status": status,
                "date": filing_date,
                "municipality": municipality,
                "region": region,
                "municipality_key": "VICTORIA",
                "region_key": "MIMAROPA",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "seeded": True,
            },
            merge=True,
        )

    count_after_seed = sum(
        1 for _ in db.collection("municipal_quotations").where("municipality", "==", municipality).stream()
    )
    print(
        {
            "seeded": len(seed_rows),
            "municipality": municipality,
            "count_after_seed": count_after_seed,
        }
    )


if __name__ == "__main__":
    main()

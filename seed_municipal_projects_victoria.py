from datetime import datetime, timedelta

from firebase_config import get_firestore_db, initialize_firebase_admin


def main():
    initialize_firebase_admin()
    db = get_firestore_db()

    municipality = "Victoria"
    region = "MIMAROPA"

    seed_rows = [
        ("Watershed Protection Project", "Alcate", "IN PROGRESS", -20),
        ("Municipal Waste Transfer Station Upgrade", "Bagong Silang", "PENDING", -10),
        ("Community Tree Planting Program", "Bethel", "COMPLETED", -35),
        ("Creek Rehabilitation Initiative", "Loyal", "IN PROGRESS", -5),
        ("Barangay Materials Recovery Facility", "San Antonio", "PENDING", -2),
    ]

    for i, (name, barangay, status, offset_days) in enumerate(seed_rows, start=1):
        doc_id = f"VIC-PROJ-{datetime.now().strftime('%Y%m%d')}-{i:02d}"
        start_date = (datetime.now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")
        db.collection("municipal_projects").document(doc_id).set(
            {
                "name": name,
                "barangay": barangay,
                "municipality": municipality,
                "region": region,
                "municipality_key": "VICTORIA",
                "region_key": "MIMAROPA",
                "start_date": start_date,
                "status": status,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "seeded": True,
            },
            merge=True,
        )

    count_after_seed = sum(
        1 for _ in db.collection("municipal_projects").where("municipality", "==", municipality).stream()
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

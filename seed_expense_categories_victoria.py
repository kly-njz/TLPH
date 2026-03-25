from firebase_config import get_firestore_db, initialize_firebase_admin


def main():
    initialize_firebase_admin()
    db = get_firestore_db()

    municipality = "Victoria"
    seed_rows = [
        {
            "name": "Fuel and Lubricants",
            "coa_code": "5-02-03-090",
            "coa_name": "Fuel, Oil and Lubricants Expenses",
            "expense_type": "VAT",
            "tax_rate": 12,
            "office": "TREASURY",
            "fund_type": "GENERAL",
            "status": "ACTIVE",
            "description": "Fuel and lubricant expenses for LGU vehicles",
            "municipality": municipality,
        },
        {
            "name": "Office Supplies",
            "coa_code": "5-02-03-010",
            "coa_name": "Office Supplies Expenses",
            "expense_type": "Withholding",
            "tax_rate": 2,
            "office": "ACCOUNTING",
            "fund_type": "GENERAL",
            "status": "ACTIVE",
            "description": "Consumables and office supplies",
            "municipality": municipality,
        },
        {
            "name": "Vehicle Maintenance",
            "coa_code": "5-02-04-020",
            "coa_name": "Repairs and Maintenance - Transportation Equipment",
            "expense_type": "VAT",
            "tax_rate": 12,
            "office": "ENGINEERING",
            "fund_type": "SPECIAL",
            "status": "ACTIVE",
            "description": "Routine and corrective vehicle maintenance",
            "municipality": municipality,
        },
        {
            "name": "Professional Services",
            "coa_code": "5-02-11-990",
            "coa_name": "Other Professional Services",
            "expense_type": "None",
            "tax_rate": 0,
            "office": "BUDGET",
            "fund_type": "TRUST",
            "status": "ACTIVE",
            "description": "Consultancy and technical support services",
            "municipality": municipality,
        },
        {
            "name": "Utilities",
            "coa_code": "5-02-13-010",
            "coa_name": "Utilities Expenses",
            "expense_type": "VAT",
            "tax_rate": 12,
            "office": "TREASURY",
            "fund_type": "GENERAL",
            "status": "ACTIVE",
            "description": "Electricity, water, and telecom services",
            "municipality": municipality,
        },
    ]

    for row in seed_rows:
        db.collection("expense_categories").add(row)

    count_after_seed = sum(
        1 for _ in db.collection("expense_categories").where("municipality", "==", municipality).stream()
    )
    print({"seeded": len(seed_rows), "municipality": municipality, "count_after_seed": count_after_seed})


if __name__ == "__main__":
    main()

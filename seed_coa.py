#!/usr/bin/env python
"""Quick seed script for COA templates"""
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Add templates
print("Adding COA templates...")
templates = [
    {"id": "municipality_std", "name": "Municipal Standard v1.0", "description": "Default municipal master chart of accounts", "municipality": "municipality", "status": "active", "account_count": 0, "locked_count": 0},
    {"id": "municipality_ext", "name": "Municipal Extended", "description": "Expanded version with additional sub-accounts", "municipality": "municipality", "status": "active", "account_count": 0, "locked_count": 0}
]

for t in templates:
    db.collection("coa_templates").document(t["id"]).set({
        "id": t["id"],
        "name": t["name"],
        "description": t["description"],
        "municipality": t["municipality"],
        "status": t["status"],
        "account_count": 0,
        "locked_count": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    })
    print(f"  ✓ {t['name']}")

# Add accounts to standard template
print("\nAdding COA accounts...")
standard_template = "municipality_std"
accounts = [
    # Assets
    ("1001", "Cash on Hand", "asset", True),
    ("1005", "Cash in Bank", "asset", False),
    ("1010", "Petty Cash", "asset", False),
    ("1100", "Accounts Receivable - Local", "asset", False),
    ("1200", "Office Equipment", "asset", False),
    ("1210", "Accumulated Depreciation - Equipment", "asset", False),
    ("1300", "Land", "asset", False),
    ("1400", "Building", "asset", False),
    ("1410", "Accumulated Depreciation - Building", "asset", False),
    # Liabilities
    ("2001", "Accounts Payable", "liability", False),
    ("2100", "Interest Payable", "liability", False),
    ("2200", "Lease Obligations", "liability", False),
    # Equity
    ("3001", "Municipal Capital", "equity", True),
    ("3100", "Retained Earnings", "equity", False),
    # Revenue
    ("4001", "Local Revenue - Fees", "revenue", True),
    ("4010", "Business Permit Fees", "revenue", False),
    ("4050", "Regulatory Fees", "revenue", False),
    ("4100", "Local Revenue - Tax", "revenue", False),
    ("4110", "Real Property Tax", "revenue", False),
    ("4130", "Business Tax", "revenue", False),
    # Expenses
    ("5001", "Personnel Services", "expense", True),
    ("5010", "Salaries and Wages", "expense", False),
    ("5020", "Office Supplies", "expense", False),
    ("5030", "Travel Expenses", "expense", False),
    ("5040", "Utilities", "expense", False),
    ("5050", "Maintenance and Repairs", "expense", False),
    ("5060", "Professional Services", "expense", False),
]

locked_count = 0
for code, name, acct_type, locked in accounts:
    doc_id = f"{standard_template}_{code}"
    db.collection("coa_accounts").document(doc_id).set({
        "id": doc_id,
        "template_id": standard_template,
        "code": code,
        "name": name,
        "account_type": acct_type,
        "locked": locked,
        "description": "",
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    })
    if locked:
        locked_count += 1
    print(f"  ✓ {code} - {name} ({acct_type})")

# Update template account counts
db.collection("coa_templates").document(standard_template).update({
    "account_count": len(accounts),
    "locked_count": locked_count,
    "updated_at": firestore.SERVER_TIMESTAMP
})

print(f"\n✓ Seeding complete! Added {len(templates)} templates with {len(accounts)} accounts ({locked_count} locked)")

#!/usr/bin/env python3
"""
Seed sample expense categories to Firestore for testing
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Sample expense categories
sample_categories = [
    {
        'name': 'Office Supplies',
        'coa_code': '5-02-03-010',
        'tax_type': 'VAT',
        'default_rate': 12,
        'status': 'active',
        'municipality': None  # For national view
    },
    {
        'name': 'Professional Services',
        'coa_code': '5-02-11-990',
        'tax_type': 'Withholding Tax',
        'default_rate': 2,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Fuel & Lubricants',
        'coa_code': '5-02-03-090',
        'tax_type': 'VAT',
        'default_rate': 12,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Travel & Transportation',
        'coa_code': '5-02-04-010',
        'tax_type': 'None',
        'default_rate': 0,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Utilities',
        'coa_code': '5-02-05-010',
        'tax_type': 'VAT',
        'default_rate': 12,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Communications',
        'coa_code': '5-02-06-010',
        'tax_type': 'Percentage Tax',
        'default_rate': 2.5,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Repairs & Maintenance',
        'coa_code': '5-02-07-010',
        'tax_type': 'VAT',
        'default_rate': 12,
        'status': 'active',
        'municipality': None
    },
    {
        'name': 'Training & Development',
        'coa_code': '5-02-08-010',
        'tax_type': 'Withholding Tax',
        'default_rate': 1.5,
        'status': 'active',
        'municipality': None
    }
]

try:
    print("[INFO] Adding sample expense categories to Firestore...")
    
    collection_ref = db.collection('expense_categories')
    count = 0
    
    for category in sample_categories:
        category['created_at'] = firestore.SERVER_TIMESTAMP
        category['updated_at'] = firestore.SERVER_TIMESTAMP
        
        result = collection_ref.add(category)
        doc_id = result[1].id
        count += 1
        print(f"  ✓ Added: {category['name']} (ID: {doc_id})")
    
    print(f"\n[SUCCESS] Added {count} sample expense categories")
    
except Exception as e:
    print(f"[ERROR] Failed to seed data: {e}")
    import traceback
    traceback.print_exc()

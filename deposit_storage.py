"""
Deposit category storage and management for municipal accounting.
Handles CRUD operations for deposit categories in Firestore.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

def get_db():
    """Get Firestore database reference"""
    return firestore.client()

def get_deposits_collection():
    """Get deposits collection reference"""
    return get_db().collection('deposit_categories')

def add_deposit_category(name, coa_code, coa_name, revenue_type, tax_type, tax_rate=None, 
                         budget_code=None, fund_type='GENERAL', status='ACTIVE', 
                         description='', municipality=None):
    """Add a new deposit category to Firestore"""
    try:
        deposits_ref = get_deposits_collection()
        
        category = {
            'name': name,
            'coa_code': coa_code,
            'coa_name': coa_name,
            'revenue_type': revenue_type,
            'tax_type': tax_type,
            'tax_rate': tax_rate,
            'budget_code': budget_code,
            'fund_type': fund_type or 'GENERAL',
            'status': status or 'ACTIVE',
            'description': description,
            'municipality': municipality,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        # Add document to Firestore
        doc_ref = deposits_ref.add(category)
        doc_id = doc_ref[1].id
        
        # Get the created document with server timestamp
        created_doc = deposits_ref.document(doc_id).get()
        result = created_doc.to_dict()
        result['id'] = doc_id
        
        return result
    except Exception as e:
        print(f"Error adding deposit category: {e}")
        return None

def get_all_deposit_categories(municipality=None):
    """Get all deposit categories, optionally filtered by municipality"""
    try:
        deposits_ref = get_deposits_collection()
        
        if municipality:
            query = deposits_ref.where('municipality', '==', municipality).order_by('created_at', direction=firestore.Query.DESCENDING)
            docs = query.stream()
        else:
            docs = deposits_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        categories = []
        for doc in docs:
            category = doc.to_dict()
            category['id'] = doc.id
            categories.append(category)
        
        return categories
    except Exception as e:
        print(f"Error fetching deposit categories: {e}")
        return []

def update_deposit_category(category_id, **updates):
    """Update a deposit category"""
    try:
        deposits_ref = get_deposits_collection()
        doc_ref = deposits_ref.document(category_id)
        
        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        doc_ref.update(updates)
        
        updated_doc = doc_ref.get()
        result = updated_doc.to_dict()
        result['id'] = category_id
        
        return result
    except Exception as e:
        print(f"Error updating deposit category: {e}")
        return None

def delete_deposit_category(category_id):
    """Delete a deposit category"""
    try:
        deposits_ref = get_deposits_collection()
        deposits_ref.document(category_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting deposit category: {e}")
        return False

def seed_sample_deposits(municipality='Sample Municipality'):
    """Add sample deposit categories for testing"""
    sample_categories = [
        {
            'name': 'Business Permit Fees',
            'coa_code': '4101',
            'coa_name': 'Permit Revenue',
            'revenue_type': 'Permit Fees',
            'tax_type': 'No Tax',
            'tax_rate': None,
            'budget_code': 'REV-001',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Business permit application fees',
            'municipality': municipality
        },
        {
            'name': 'Environmental Compliance Certificate',
            'coa_code': '4102',
            'coa_name': 'Environmental Revenue',
            'revenue_type': 'Service Revenue',
            'tax_type': 'VAT',
            'tax_rate': 12.0,
            'budget_code': 'REV-002',
            'fund_type': 'SPECIAL',
            'status': 'ACTIVE',
            'description': 'ECC processing fees',
            'municipality': municipality
        },
        {
            'name': 'Wildlife Permit Fees',
            'coa_code': '4103',
            'coa_name': 'Wildlife Management Revenue',
            'revenue_type': 'Permit Fees',
            'tax_type': 'No Tax',
            'tax_rate': None,
            'budget_code': 'REV-003',
            'fund_type': 'TRUST',
            'status': 'ACTIVE',
            'description': 'Wildlife transport and possession permits',
            'municipality': municipality
        },
        {
            'name': 'Chainsaw Registration',
            'coa_code': '4104',
            'coa_name': 'Forestry Revenue',
            'revenue_type': 'Service Revenue',
            'tax_type': 'Withholding',
            'tax_rate': 5.0,
            'budget_code': 'REV-004',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Chainsaw registration and renewal',
            'municipality': municipality
        },
        {
            'name': 'Tree Cutting Permit',
            'coa_code': '4105',
            'coa_name': 'Forestry Permits',
            'revenue_type': 'Permit Fees',
            'tax_type': 'No Tax',
            'tax_rate': None,
            'budget_code': 'REV-005',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Tree cutting and transport permits',
            'municipality': municipality
        },
        {
            'name': 'Government Grants',
            'coa_code': '4201',
            'coa_name': 'Grant Revenue',
            'revenue_type': 'Grants',
            'tax_type': 'No Tax',
            'tax_rate': None,
            'budget_code': 'REV-006',
            'fund_type': 'SPECIAL',
            'status': 'ACTIVE',
            'description': 'National and regional grants',
            'municipality': municipality
        },
    ]
    
    for category in sample_categories:
        add_deposit_category(**category)
    
    print(f"Added {len(sample_categories)} sample deposit categories")

def clear_all_deposits():
    """Clear all deposit categories (use with caution)"""
    try:
        deposits_ref = get_deposits_collection()
        docs = deposits_ref.stream()
        
        count = 0
        batch = get_db().batch()
        
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            
            if count % 400 == 0:
                batch.commit()
                batch = get_db().batch()
        
        if count % 400 != 0:
            batch.commit()
        
        print(f"Cleared {count} deposit categories")
        return count
    except Exception as e:
        print(f"Error clearing deposits: {e}")
        return 0

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'seed':
            municipality = sys.argv[2] if len(sys.argv) > 2 else 'Sample Municipality'
            seed_sample_deposits(municipality)
        elif command == 'clear':
            clear_all_deposits()
        elif command == 'list':
            categories = get_all_deposit_categories()
            print(f"Total deposit categories: {len(categories)}")
            for cat in categories:
                print(f"  - {cat['name']} ({cat['coa_code']}) - {cat['revenue_type']}")
    else:
        print("Usage:")
        print("  python deposit_storage.py seed [municipality]  - Add sample deposits")
        print("  python deposit_storage.py clear                - Clear all deposits")
        print("  python deposit_storage.py list                 - List all deposits")

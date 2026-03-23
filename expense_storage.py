"""
Expense category storage and management for municipal accounting.
Handles CRUD operations for expense categories in Firestore.
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

def get_expenses_collection():
    """Get expenses collection reference"""
    return get_db().collection('expense_categories')

def add_expense_category(name, coa_code, coa_name, expense_type, office, 
                         budget_code=None, fund_type='GENERAL', status='ACTIVE', 
                         description='', municipality=None):
    """Add a new expense category to Firestore"""
    try:
        expenses_ref = get_expenses_collection()
        # Ensure municipality is always uppercase if provided
        muni_upper = municipality.upper() if municipality else None
        category = {
            'name': name,
            'coa_code': coa_code,
            'coa_name': coa_name,
            'expense_type': expense_type,
            'office': office,
            'budget_code': budget_code,
            'fund_type': fund_type or 'GENERAL',
            'status': status or 'ACTIVE',
            'description': description,
            'municipality': muni_upper,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        # Add document to Firestore
        doc_ref = expenses_ref.add(category)
        doc_id = doc_ref[1].id
        # Get the created document with server timestamp
        created_doc = expenses_ref.document(doc_id).get()
        result = created_doc.to_dict()
        result['id'] = doc_id
        return result
    except Exception as e:
        print(f"Error adding expense category: {e}")
        return None

def get_all_expense_categories(region=None, municipality=None):
    """Get all expense categories, optionally filtered by region or municipality."""
    try:
        expenses_ref = get_expenses_collection()
        categories = []
        if municipality:
            docs = expenses_ref.where('municipality', '==', municipality).stream()
            for doc in docs:
                category = doc.to_dict()
                category['id'] = doc.id
                categories.append(category)
        elif region:
            # Get all categories for all municipalities in the region
            from models.ph_locations import philippineLocations
            from models.region_province_map import region_province_map
            muni_set = set()
            provinces = region_province_map.get(region, [])
            for prov in provinces:
                muni_set.update(philippineLocations.get(prov, []))
            muni_set = set(m.strip().upper() for m in muni_set)
            docs = expenses_ref.stream()
            for doc in docs:
                category = doc.to_dict()
                category['id'] = doc.id
                muni = (category.get('municipality') or '').strip().upper()
                if muni in muni_set:
                    categories.append(category)
        else:
            # National: get all
            docs = expenses_ref.stream()
            for doc in docs:
                category = doc.to_dict()
                category['id'] = doc.id
                categories.append(category)

        def to_sort_key(item):
            ts = item.get('created_at')
            if hasattr(ts, 'timestamp'):
                try:
                    return ts.timestamp()
                except Exception:
                    return 0
            return 0

        categories.sort(key=to_sort_key, reverse=True)
        return categories
    except Exception as e:
        print(f"Error fetching expense categories: {e}")
        return []

def update_expense_category(category_id, **updates):
    """Update an expense category"""
    try:
        expenses_ref = get_expenses_collection()
        doc_ref = expenses_ref.document(category_id)
        
        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        doc_ref.update(updates)
        
        updated_doc = doc_ref.get()
        result = updated_doc.to_dict()
        result['id'] = category_id
        
        return result
    except Exception as e:
        print(f"Error updating expense category: {e}")
        return None

def delete_expense_category(category_id):
    """Delete an expense category"""
    try:
        expenses_ref = get_expenses_collection()
        expenses_ref.document(category_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting expense category: {e}")
        return False

def seed_sample_expenses(municipality='Sample Municipality'):
    """Add sample expense categories for testing"""
    sample_categories = [
        {
            'name': 'Office Supplies',
            'coa_code': '6201',
            'coa_name': 'Supplies & Materials',
            'expense_type': 'Supplies',
            'office': 'ACCOUNTING',
            'budget_code': 'EXP-001',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Office supplies and consumables',
            'municipality': municipality
        },
        {
            'name': 'Utilities',
            'coa_code': '6301',
            'coa_name': 'Utilities & Communications',
            'expense_type': 'Utilities',
            'office': 'TREASURY',
            'budget_code': 'EXP-002',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Water, electricity, telephone',
            'municipality': municipality
        },
        {
            'name': 'Travel & Transportation',
            'coa_code': '6401',
            'coa_name': 'Travel & Transportation',
            'expense_type': 'Travel',
            'office': 'BUDGET',
            'budget_code': 'EXP-003',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Gasoline, repairs, travel expenses',
            'municipality': municipality
        },
        {
            'name': 'Professional Services',
            'coa_code': '6501',
            'coa_name': 'Professional Services',
            'expense_type': 'Contractual',
            'office': 'ENGINEERING',
            'budget_code': 'EXP-004',
            'fund_type': 'SPECIAL',
            'status': 'ACTIVE',
            'description': 'Consultant and professional fees',
            'municipality': municipality
        },
        {
            'name': 'Equipment',
            'coa_code': '6601',
            'coa_name': 'Equipment & Machinery',
            'expense_type': 'Capital',
            'office': 'ACCOUNTING',
            'budget_code': 'EXP-005',
            'fund_type': 'SPECIAL',
            'status': 'ACTIVE',
            'description': 'Office equipment and machinery',
            'municipality': municipality
        },
        {
            'name': 'Repairs & Maintenance',
            'coa_code': '6701',
            'coa_name': 'Repairs & Maintenance',
            'expense_type': 'Maintenance',
            'office': 'TREASURY',
            'budget_code': 'EXP-006',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Building and equipment repairs',
            'municipality': municipality
        },
        {
            'name': 'Training & Development',
            'coa_code': '6801',
            'coa_name': 'Training & Development',
            'expense_type': 'Training',
            'office': 'BUDGET',
            'budget_code': 'EXP-007',
            'fund_type': 'GENERAL',
            'status': 'ACTIVE',
            'description': 'Employee training and seminars',
            'municipality': municipality
        },
    ]
    
    for category in sample_categories:
        add_expense_category(**category)
    
    print(f"Added {len(sample_categories)} sample expense categories")

def clear_all_expenses():
    """Clear all expense categories (use with caution)"""
    try:
        expenses_ref = get_expenses_collection()
        docs = expenses_ref.stream()
        
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
        
        print(f"Cleared {count} expense categories")
        return count
    except Exception as e:
        print(f"Error clearing expenses: {e}")
        return 0

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'seed':
            municipality = sys.argv[2] if len(sys.argv) > 2 else 'Sample Municipality'
            seed_sample_expenses(municipality)
        elif command == 'clear':
            clear_all_expenses()
        elif command == 'list':
            categories = get_all_expense_categories()
            print(f"Total expense categories: {len(categories)}")
            for cat in categories:
                print(f"  - {cat['name']} ({cat['coa_code']}) - {cat['expense_type']}")
    else:
        print("Usage:")
        print("  python expense_storage.py seed [municipality]  - Add sample expenses")
        print("  python expense_storage.py clear                - Clear all expenses")
        print("  python expense_storage.py list                 - List all expenses")

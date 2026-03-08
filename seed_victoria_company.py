#!/usr/bin/env python3
"""
Seed script to create Victoria municipality company record in Firestore
Run with: python seed_victoria_company.py
"""

import sys
print("Python path:", sys.executable)
print("Python version:", sys.version)

try:
    import firebase_admin
    print("✓ firebase_admin imported successfully")
    from firebase_admin import credentials, firestore
    print("✓ firebase modules imported")
    
    # Initialize Firebase
    try:
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred)
        print("✓ Firebase initialized")
    except ValueError:
        print("✓ Firebase already initialized")
    
    db = firestore.client()
    
    # Victoria company data
    victoria_company = {
        'office_name': 'Municipal Environment and Natural Resources Office',
        'municipality': 'Victoria',
        'province': 'Oriental Mindoro',
        'region': 'Region IV-B (MIMAROPA)',
        'lgu_class': '1st Class Municipality',
        'physical_address': 'Victoria Municipal Hall, Poblacion, Victoria, Oriental Mindoro 5208',
        'email': 'menro.victoria@mindoro.gov.ph',
        'contact_number': '(+63 42) 288-1234 | Mobile: (+63 945) 432-1098',
        'office_hours': '8:00 AM - 5:00 PM (Monday-Friday)',
        'verification_status': 'Authenticated',
        'linked_users': 0,
        'pending_requests': 0,
        'active_programs': 0,
        'status': 'Active',
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    # Check if Victoria company already exists
    query = db.collection('companies').where('municipality', '==', 'Victoria')
    docs = list(query.stream())
    
    if docs:
        print("⚠️  Victoria company record already exists")
        print(f"Document ID: {docs[0].id}")
        print("Skipping creation...")
    else:
        # Add to Firestore
        result = db.collection('companies').add(victoria_company)
        print(f'✅ Created company: {victoria_company["office_name"]}')
        print(f'✅ Municipality: {victoria_company["municipality"]}')
        print(f'✅ Province: {victoria_company["province"]}')
        print(f'✅ Region: {victoria_company["region"]}')
        print(f'✅ Document ID: {result[1].id}')
        print('✅ Victoria company record seeded successfully')
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        db.close()
    except:
        pass

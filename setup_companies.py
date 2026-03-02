#!/usr/bin/env python3
"""
Simple script to create companies collection - no launcher issues
Run with: /path/to/venv/python.exe script.py
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
    
    # Company data
    company_data = {
        'office_name': 'San Juan Del Monte DENR Office',
        'municipality': 'San Juan Del Monte',
        'province': 'Batangas',
        'region': 'Region IV-A (CALABARZON)',
        'lgu_class': '1st Class Municipality',
        'physical_address': 'Floor 2, Environmental Unit, New Government Center, Brgy. Poblacion, San Juan, Batangas',
        'email': 'admin-sanjuan@denr-muni.gov.ph',
        'contact_number': '(+63) 43-552-1922',
        'office_hours': '8:00 AM - 5:00 PM (Monday-Friday)',
        'verification_status': 'Authenticated',
        'linked_users': 1240,
        'pending_requests': 14,
        'active_programs': 8,
        'status': 'Active',
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    # Add to Firestore
    result = db.collection('companies').add(company_data)
    print(f'✓ Created company: {company_data["office_name"]}')
    print(f'✓ Document ID: {result[1].id}')
    print('✅ Companies collection created successfully')
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    try:
        db.close()
    except:
        pass

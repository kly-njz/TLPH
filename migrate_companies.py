#!/usr/bin/env python3
"""
Firestore Companies Collection Migration Script
Creates and populates the companies collection with municipal office data
"""

from firebase_admin import credentials, firestore, initialize_app
import os

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
app = initialize_app(cred)
db = firestore.client()

# Company data structure
companies_data = [
    {
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
]

# Create companies collection
try:
    print('Creating Companies Collection...\n')
    
    for idx, company_data in enumerate(companies_data, 1):
        doc = db.collection('companies').add(company_data)
        print(f'✓ Created company: {company_data["office_name"]} (ID: {doc[1].id})')
    
    print(f'\n✅ Companies collection created successfully with {len(companies_data)} document(s)')

except Exception as e:
    print(f'❌ Error creating companies collection: {str(e)}')
    raise
finally:
    db.close()

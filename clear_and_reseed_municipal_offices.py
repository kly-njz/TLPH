# clear_and_reseed_municipal_offices.py
"""
Script to clear and reseed the 'municipal_offices' collection in Firestore.
Make sure your firebase-credentials.json is configured and accessible.
"""

import firebase_admin
from firebase_admin import credentials, firestore
region_municipalities = {
    'CALABARZON': [
        # ...existing code for CALABARZON...
    ],
    'MIMAROPA': [
        # Marinduque Province
        {'name': 'Boac', 'province': 'Marinduque', 'code': 'MUN-MAR-001', 'status': 'Active'},
        {'name': 'Santa Cruz', 'province': 'Marinduque', 'code': 'MUN-MAR-002', 'status': 'Active'},
        {'name': 'Buenavista', 'province': 'Marinduque', 'code': 'MUN-MAR-003', 'status': 'Active'},
        {'name': 'Gasan', 'province': 'Marinduque', 'code': 'MUN-MAR-004', 'status': 'Active'},
        {'name': 'Mogpog', 'province': 'Marinduque', 'code': 'MUN-MAR-005', 'status': 'Active'},

        # Occidental Mindoro Province
        {'name': 'San Jose', 'province': 'Occidental Mindoro', 'code': 'MUN-OCM-001', 'status': 'Active'},
        {'name': 'Mamburao', 'province': 'Occidental Mindoro', 'code': 'MUN-OCM-002', 'status': 'Active'},

        # Oriental Mindoro Province (full list)
        {'name': 'Baco', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-001', 'status': 'Active'},
        {'name': 'Bansud', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-002', 'status': 'Active'},
        {'name': 'Bongabong', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-003', 'status': 'Active'},
        {'name': 'Bulalacao', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-004', 'status': 'Active'},
        {'name': 'Calapan', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-005', 'status': 'Active'},
        {'name': 'Gloria', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-006', 'status': 'Active'},
        {'name': 'Mansalay', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-007', 'status': 'Active'},
        {'name': 'Naujan', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-008', 'status': 'Active'},
        {'name': 'Pinamalayan', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-009', 'status': 'Active'},
        {'name': 'Pola', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-010', 'status': 'Active'},
        {'name': 'Puerto Galera', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-011', 'status': 'Active'},
        {'name': 'Roxas', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-012', 'status': 'Active'},
        {'name': 'San Teodoro', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-013', 'status': 'Active'},
        {'name': 'Socorro', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-014', 'status': 'Active'},
        {'name': 'Victoria', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-015', 'status': 'Active'},

        # Palawan Province
        {'name': 'Puerto Princesa', 'province': 'Palawan', 'code': 'MUN-PAL-001', 'status': 'Active'},
        {'name': 'Coron', 'province': 'Palawan', 'code': 'MUN-PAL-002', 'status': 'Active'},
        {'name': 'El Nido', 'province': 'Palawan', 'code': 'MUN-PAL-003', 'status': 'Active'},
        {'name': "Brooke's Point", 'province': 'Palawan', 'code': 'MUN-PAL-004', 'status': 'Active'},

        # Romblon Province
        {'name': 'Odiongan', 'province': 'Romblon', 'code': 'MUN-ROM-001', 'status': 'Active'},
        {'name': 'Calatrava', 'province': 'Romblon', 'code': 'MUN-ROM-002', 'status': 'Active'},
        {'name': 'San Andres', 'province': 'Romblon', 'code': 'MUN-ROM-003', 'status': 'Active'},
    ]
}
import sys

REGION = 'MIMAROPA'  # Change if needed

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Clear the collection
def clear_collection(collection_name):
    docs = db.collection(collection_name).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    print(f"Deleted {deleted} documents from {collection_name}")

# Reseed the collection
def reseed_municipal_offices(region_name):
    municipalities = region_municipalities.get(region_name, [])
    added = 0
    for mun in municipalities:
        office_doc = {
            'office_code': mun['code'],
            'municipality_name': mun['name'],
            'province': mun['province'],
            'region': region_name,
            'status': mun['status']
        }
        db.collection('municipal_offices').add(office_doc)
        added += 1
    print(f"Added {added} municipalities for region {region_name}")

if __name__ == "__main__":
    clear_collection('municipal_offices')
    reseed_municipal_offices(REGION)
    print("Done.")

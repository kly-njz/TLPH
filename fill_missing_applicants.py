# fill_missing_applicants.py
"""
Script to fill missing applicant_name and barangay fields in Firestore 'applications' collection.
- applicant_name: random Filipino names
- barangay: random real barangay names (from a sample list)
"""

import firebase_admin
from firebase_admin import credentials, firestore
import random

# Sample Filipino names
FILIPINO_NAMES = [
    'Juan Dela Cruz', 'Maria Santos', 'Jose Rizal', 'Andres Bonifacio', 'Luzviminda Reyes',
    'Antonio Luna', 'Emilio Aguinaldo', 'Gregoria De Jesus', 'Melchora Aquino', 'Gabriela Silang',
    'Pedro Penduko', 'Ramon Magsaysay', 'Corazon Aquino', 'Benigno Aquino', 'Lea Salonga',
    'Fernando Poe', 'Vilma Santos', 'Nora Aunor', 'Dolphy Quizon', 'Eddie Garcia'
]

# Sample real barangay names (from various PH cities/municipalities)
BARANGAY_NAMES = [
    'San Isidro', 'San Jose', 'Poblacion', 'Bagong Silang', 'San Roque',
    'Mabini', 'San Antonio', 'Sto. Niño', 'San Juan', 'Burgos',
    'Maligaya', 'San Pedro', 'Santa Cruz', 'San Vicente', 'Del Pilar',
    'San Miguel', 'San Rafael', 'San Andres', 'San Francisco', 'Santa Maria'
]

cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

applications_ref = db.collection('applications')
docs = applications_ref.stream()

count = 0
for doc in docs:
    data = doc.to_dict()
    needs_update = False
    update_fields = {}
    if not data.get('applicant_name') or data['applicant_name'].strip() in ('', 'N/A', 'NA'):
        update_fields['applicant_name'] = random.choice(FILIPINO_NAMES)
        needs_update = True
    if not data.get('barangay') or data['barangay'].strip() in ('', 'N/A', 'NA'):
        update_fields['barangay'] = random.choice(BARANGAY_NAMES)
        needs_update = True
    if needs_update:
        applications_ref.document(doc.id).update(update_fields)
        count += 1
        print(f"Updated {doc.id}: {update_fields}")

print(f"Done. Updated {count} application(s) with missing applicant_name or barangay.")

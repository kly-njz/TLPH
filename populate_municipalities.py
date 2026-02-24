import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase app
cred = credentials.Certificate('firebase-credentials.json')
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Example region and municipalities (edit as needed)

region = 'REGION IV-B'
municipalities = [
    'Mamburao', 'San Jose', 'Sablayan', 'Abra de Ilog', 'Calintaan', 'Looc', 'Lubang', 'Paluan', 'Rizal', 'Sta. Cruz', 'Tilik'
]

doc_ref = db.collection('municipalities').document(region)
doc_ref.set({'municipalities': municipalities})
print(f"Municipalities for {region} set in Firestore.")

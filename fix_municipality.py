import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Fix: Update pagaduanjohnmark29@gmail.com municipality to 'Naujan' to match their logs
print("Fixing municipality mismatch...")

# Find the user by email
docs = db.collection('users').where('email', '==', 'pagaduanjohnmark29@gmail.com').limit(1).stream()
for doc in docs:
    print(f"Found user: {doc.id}")
    print(f"  Current municipality: {doc.to_dict().get('municipality')}")
    
    # Update municipality to 'Naujan' to match their logs
    db.collection('users').document(doc.id).update({
        'municipality': 'Naujan'
    })
    print(f"  Updated municipality to: 'Naujan'")
    print()

print("Done! Municipality has been fixed.")

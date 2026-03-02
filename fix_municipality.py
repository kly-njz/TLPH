import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Revert: Update pagaduanjohnmark29@gmail.com municipality back to 'Victoria'
print("Reverting municipality back to Victoria...")

# Find the user by email
docs = db.collection('users').where('email', '==', 'pagaduanjohnmark29@gmail.com').limit(1).stream()
for doc in docs:
    print(f"Found user: {doc.id}")
    print(f"  Current municipality: {doc.to_dict().get('municipality')}")
    
    # Update municipality back to 'Victoria'
    db.collection('users').document(doc.id).update({
        'municipality': 'Victoria'
    })
    print(f"  Updated municipality back to: 'Victoria'")
    print()

print("Done! Municipality has been reverted to Victoria.")


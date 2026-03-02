import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Check users collection
print('=== USERS COLLECTION ===')
docs = db.collection('users').limit(10).stream()
for doc in docs:
    data = doc.to_dict() or {}
    email = data.get('email', 'no-email')
    municipality = data.get('municipality', 'N/A')
    municipality_name = data.get('municipality_name', 'N/A')
    print(f"Email: {email}")
    print(f"  municipality: '{municipality}'")
    print(f"  municipality_name: '{municipality_name}'")
    print()

# Check system_logs collection
print('\n=== SYSTEM_LOGS COLLECTION (Last 20) ===')
docs = db.collection('system_logs').order_by('created_at', direction=firestore.Query.DESCENDING).limit(20).stream()
for doc in docs:
    data = doc.to_dict() or {}
    user = data.get('user', 'unknown')
    municipality = data.get('municipality', 'unknown')
    action = data.get('action', 'unknown')
    print(f"User: {user}")
    print(f"  municipality: '{municipality}'")
    print(f"  action: {action}")
    print()

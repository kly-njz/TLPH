import firebase_admin
from firebase_admin import credentials, firestore
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Check for Victoria municipal admins
docs = db.collection('users').where('municipality', '==', 'Victoria').stream()
admins = list(docs)
print(f'Found {len(admins)} users for Victoria:\n')
for doc in admins:
    data = doc.to_dict() or {}
    print(f"Email: {data.get('email', 'N/A')}")
    print(f"  Role: {data.get('role', 'N/A')}")
    print(f"  Region: {data.get('region', 'N/A')}")
    print(f"  RegionName: {data.get('regionName', 'N/A')}")
    print()

# Check regional_system_logs collection
print("\nChecking regional_system_logs collection:")
docs = db.collection('regional_system_logs').limit(100).stream()
logs = list(docs)
print(f"Total entries: {len(logs)}")
if logs:
    for log in logs[:3]:
        data = log.to_dict() or {}
        print(f"  Action: {data.get('action')}, Region: {data.get('region')}, Municipality: {data.get('municipality')}")

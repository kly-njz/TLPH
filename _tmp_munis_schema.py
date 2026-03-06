from firebase_config import initialize_firebase_admin, get_firestore_db

initialize_firebase_admin()
db = get_firestore_db()

for d in db.collection('municipalities').stream():
    x = d.to_dict() or {}
    print('DOC', d.id)
    print('KEYS', sorted(list(x.keys())))
    print('MUNICIPALITIES_LEN', len(x.get('municipalities', []) or []))
    print('SAMPLE', (x.get('municipalities', []) or [])[:5])

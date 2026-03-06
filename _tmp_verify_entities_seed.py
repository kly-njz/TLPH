from firebase_config import initialize_firebase_admin, get_firestore_db

initialize_firebase_admin()
db = get_firestore_db()

docs = list(db.collection('entities').stream())
print('TOTAL', len(docs))
for d in docs:
    x = d.to_dict() or {}
    print(d.id, {
        'name': x.get('name') or x.get('entity_name'),
        'type': x.get('type'),
        'entity_level': x.get('entity_level'),
        'municipality': x.get('municipality') or x.get('municipality_name'),
        'region': x.get('region') or x.get('region_name'),
        'status': x.get('status')
    })

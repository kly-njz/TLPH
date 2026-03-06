from firebase_config import initialize_firebase_admin, get_firestore_db

initialize_firebase_admin()
db = get_firestore_db()

for col_name in ['municipal_offices','municipalities']:
    print('\nCOL', col_name)
    docs = list(db.collection(col_name).limit(20).stream())
    print('COUNT', len(docs))
    for d in docs[:10]:
        x = d.to_dict() or {}
        print('DOC', d.id)
        print({k:x.get(k) for k in ['municipality','municipality_name','region','region_name','province','office_name','name','status','is_active','bank_account','bank_account_number','entity_level','type']})

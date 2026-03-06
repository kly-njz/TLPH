from firebase_config import initialize_firebase_admin, get_firestore_db

initialize_firebase_admin()
db = get_firestore_db()

cols = list(db.collections())
print('COLLECTIONS', len(cols))
for c in cols:
    name = c.id
    cnt = sum(1 for _ in c.limit(2000).stream())
    print(name, cnt)

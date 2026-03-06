from firebase_config import get_firestore_db

db = get_firestore_db()
col = db.collection('entities')
docs = list(col.limit(20).stream())
print('COUNT_SAMPLE', len(docs))
levels = {}
for d in docs:
    x = d.to_dict() or {}
    lvl = str(x.get('entity_level') or x.get('level') or ('municipal' if (x.get('municipality') or x.get('municipality_name')) else 'regional')).lower()
    levels[lvl] = levels.get(lvl, 0) + 1
    print('DOC', d.id, '|', {k: x.get(k) for k in ['name','entity_name','office_name','entity_level','level','municipality','municipality_name','region','region_name','status']})
print('LEVELS', levels)

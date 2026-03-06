from firebase_config import initialize_firebase_admin, get_firestore_db

initialize_firebase_admin()
db = get_firestore_db()

entities = list(db.collection('entities').stream())
print('TOTAL_ENTITIES', len(entities))

level_counts = {}
nonempty_name = 0
for d in entities[:30]:
    x = d.to_dict() or {}
    name = x.get('entity_name') or x.get('name') or x.get('office_name')
    if name:
        nonempty_name += 1
    lvl = str(x.get('entity_level') or x.get('level') or ('municipal' if (x.get('municipality') or x.get('municipality_name')) else 'regional')).lower()
    level_counts[lvl] = level_counts.get(lvl, 0) + 1
    print('DOC', d.id, '|', {k: x.get(k) for k in ['entity_name','name','entity_level','level','municipality','municipality_name','region','region_name','status']})

print('LEVEL_COUNTS_SAMPLE', level_counts)
print('NONEMPTY_NAME_SAMPLE', nonempty_name)

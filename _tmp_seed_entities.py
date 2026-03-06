import entities_storage

seed_rows = [
    ('Binangonan', 'Municipal Accounting Office', 'OFFICE', 'ACCOUNTING', 'LBP-BIN-1001', 'ACTIVE'),
    ('Cainta', 'Municipal Budget Office', 'OFFICE', 'BUDGET', 'LBP-CAI-1002', 'ACTIVE'),
    ('Boac', 'Municipal Treasury Unit', 'UNIT', 'TREASURY', '', 'ACTIVE'),
    ('El Nido', 'Municipal Depository Account', 'BANK', '', 'LBP-ELN-2001', 'ACTIVE'),
    ('Cavite City', 'Municipal HR Office', 'OFFICE', 'HRM', '', 'PENDING'),
]

created = []
for municipality, name, entity_type, office_or_unit, bank_account, status in seed_rows:
    row = entities_storage.add_entity(
        municipality=municipality,
        name=name,
        entity_type=entity_type,
        office_or_unit=office_or_unit,
        bank_account=bank_account,
        status=status,
    )
    created.append(row.get('id'))

# Seed explicit regional-level entities used by national management view
regional_rows = [
    {
        'id': 'region_iv_a_main_office',
        'entity_name': 'REGION-IV-A MAIN OFFICE',
        'entity_level': 'regional',
        'region_name': 'REGION-IV-A',
        'municipality_name': '',
        'bank_account_number': 'LBP-R4A-0001',
        'status': 'active'
    },
    {
        'id': 'region_iv_b_main_office',
        'entity_name': 'REGION-IV-B MAIN OFFICE',
        'entity_level': 'regional',
        'region_name': 'REGION-IV-B',
        'municipality_name': '',
        'bank_account_number': 'LBP-R4B-0001',
        'status': 'active'
    }
]

for row in regional_rows:
    doc_id = row.pop('id')
    entities_storage.db.collection('entities').document(doc_id).set(row, merge=True)

print('SEEDED_MUNICIPAL_IDS', created)
print('SEEDED_REGIONAL_IDS', ['region_iv_a_main_office', 'region_iv_b_main_office'])
print('TOTAL_ENTITIES_NOW', sum(1 for _ in entities_storage.db.collection('entities').stream()))

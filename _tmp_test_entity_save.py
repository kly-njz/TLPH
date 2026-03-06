from firebase_config import initialize_firebase_admin
import entities_storage
from firebase_admin import firestore

initialize_firebase_admin()

created = entities_storage.add_entity(
    municipality='Binangonan',
    name='TEST ENTITY UI CHECK',
    entity_type='OFFICE',
    office_or_unit='ACCOUNTING',
    bank_account='LBP-TEST-0001',
    status='ACTIVE'
)
print('CREATED_ID', created.get('id'))

# verify read back from entities collection
from entities_storage import db
ref = db.collection('entities').document(created.get('id')).get()
print('EXISTS', ref.exists)
print('DATA', ref.to_dict())

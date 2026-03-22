def get_all_quotations():
    db = get_firestore_db()
    q = db.collection('quotations')
    return [dict(doc.to_dict(), id=doc.id) for doc in q.stream()]
# quotation_storage.py
# Unified storage for quotations (municipal, regional, national)
from firebase_config import get_firestore_db
from datetime import datetime

def add_quotation(data):
    db = get_firestore_db()
    data = dict(data)
    data['created_at'] = datetime.utcnow().isoformat()
    data['updated_at'] = datetime.utcnow().isoformat()
    ref = db.collection('quotations').document()
    data['id'] = ref.id
    ref.set(data)
    return data

def update_quotation(quotation_id, updates):
    db = get_firestore_db()
    updates['updated_at'] = datetime.utcnow().isoformat()
    ref = db.collection('quotations').document(quotation_id)
    ref.update(updates)
    return ref.get().to_dict()

def delete_quotation(quotation_id):
    db = get_firestore_db()
    ref = db.collection('quotations').document(quotation_id)
    ref.delete()
    return True

def get_quotations(scope=None, region=None, municipality=None, status=None):
    db = get_firestore_db()
    q = db.collection('quotations')
    if scope:
        q = q.where('scope', '==', scope)
    if region:
        q = q.where('region', '==', region)
    if municipality:
        q = q.where('municipality', '==', municipality)
    if status:
        q = q.where('status', '==', status)
    return [dict(doc.to_dict(), id=doc.id) for doc in q.stream()]

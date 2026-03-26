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
    now = datetime.utcnow().isoformat()
    data['created_at'] = now
    data['updated_at'] = now
    data['status'] = data.get('status', 'pending')
    data['history'] = [{
        'action': 'created',
        'by': data.get('created_by', ''),
        'timestamp': now,
        'notes': ''
    }]
    # New workflow fields
    data['deliver_from'] = data.get('deliver_from', 'NATIONAL')
    data['deliver_to'] = data.get('deliver_to', '')
    data['deliver_to_type'] = data.get('deliver_to_type', '')
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

def get_quotations(deliver_to=None, deliver_to_type=None, status=None):
    db = get_firestore_db()
    q = db.collection('quotations')
    if deliver_to:
        q = q.where('deliver_to', '==', deliver_to)
    if deliver_to_type:
        q = q.where('deliver_to_type', '==', deliver_to_type)
    if status:
        q = q.where('status', '==', status)
    return [dict(doc.to_dict(), id=doc.id) for doc in q.stream()]

# Helper to update status and append to history
def update_quotation_status(quotation_id, new_status, user_email, notes=''):
    db = get_firestore_db()
    ref = db.collection('quotations').document(quotation_id)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    now = datetime.utcnow().isoformat()
    history = data.get('history', [])
    history.append({
        'action': new_status,
        'by': user_email,
        'timestamp': now,
        'notes': notes
    })
    ref.update({'status': new_status, 'updated_at': now, 'history': history})
    return ref.get().to_dict()

# Script to clear the Firestore 'quotations' collection for new workflow
from firebase_config import get_firestore_db

def clear_quotations_collection():
    db = get_firestore_db()
    batch = db.batch()
    docs = db.collection('quotations').stream()
    count = 0
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    print(f"Cleared {count} quotations from the collection.")

if __name__ == "__main__":
    clear_quotations_collection()

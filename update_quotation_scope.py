# update_quotation_scope.py
"""
Script to update the 'scope' field for all quotations in the 'quotations' collection.
Sets scope to 'regional' for all documents matching your region (e.g., MIMAROPA).
"""

from firebase_config import get_firestore_db

def update_scope_for_region(region_value, new_scope='regional'):
    db = get_firestore_db()
    quotations_ref = db.collection('quotations')
    # Query for quotations with the specified region
    docs = quotations_ref.where('region', '==', region_value).stream()
    count = 0
    for doc in docs:
        data = doc.to_dict()
        if data.get('scope') != new_scope:
            quotations_ref.document(doc.id).update({'scope': new_scope})
            print(f"Updated quotation {doc.id}: set scope='{new_scope}'")
            count += 1
    print(f"Done. Updated {count} quotations.")

if __name__ == '__main__':
    # Set your region value here (must match the 'region' field in your quotations)
    update_scope_for_region('MIMAROPA')

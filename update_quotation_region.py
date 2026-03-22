# update_quotation_region.py
"""
Script to update the 'region' field for all quotations in the 'quotations' collection where region is 'unknown'.
Sets region to 'MIMAROPA'.
"""

from firebase_config import get_firestore_db

def update_region_unknown_to_mimaropa():
    db = get_firestore_db()
    quotations_ref = db.collection('quotations')
    # Query for quotations with region 'unknown'
    docs = quotations_ref.where('region', '==', 'unknown').stream()
    count = 0
    for doc in docs:
        quotations_ref.document(doc.id).update({'region': 'MIMAROPA'})
        print(f"Updated quotation {doc.id}: set region='MIMAROPA'")
        count += 1
    print(f"Done. Updated {count} quotations.")

if __name__ == '__main__':
    update_region_unknown_to_mimaropa()

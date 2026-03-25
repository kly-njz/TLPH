# Script to seed missing payroll fields for all employees in Firestore
# Usage: python seed_payroll_fields.py

from firebase_config import get_firestore_db

def seed_payroll_fields():
    db = get_firestore_db()
    employees_ref = db.collection('employees')
    docs = employees_ref.stream()
    updated = 0
    for doc in docs:
        data = doc.to_dict() or {}
        update_data = {}
        # Payroll fields to ensure
        if 'gross_pay' not in data or data['gross_pay'] is None:
            update_data['gross_pay'] = float(data.get('basic_pay', 0)) + float(data.get('allowances', 0))
        if 'deductions' not in data or data['deductions'] is None:
            update_data['deductions'] = 0
        if 'net_pay' not in data or data['net_pay'] is None:
            gross = update_data.get('gross_pay', data.get('gross_pay', 0))
            deductions = update_data.get('deductions', data.get('deductions', 0))
            update_data['net_pay'] = float(gross) - float(deductions)
        if 'status_payment' not in data or not data['status_payment']:
            update_data['status_payment'] = 'DRAFT'
        if update_data:
            employees_ref.document(doc.id).set(update_data, merge=True)
            updated += 1
    print(f"Seeded payroll fields for {updated} employees.")

if __name__ == '__main__':
    seed_payroll_fields()

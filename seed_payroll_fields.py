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
        # Set defaults if missing or zero
        basic_pay = float(data.get('basic_pay', 15000))  # Default 15,000 if missing
        allowances = float(data.get('allowances', 2000))  # Default 2,000 if missing
        deductions = float(data.get('deductions', 0))
        gross_pay = float(data.get('gross_pay', basic_pay + allowances))
        if not gross_pay or gross_pay == 0:
            gross_pay = basic_pay + allowances
        if 'gross_pay' not in data or data['gross_pay'] != gross_pay:
            update_data['gross_pay'] = gross_pay
        if 'deductions' not in data or data['deductions'] is None:
            update_data['deductions'] = deductions
        net_pay = float(data.get('net_pay', gross_pay - deductions))
        if not net_pay or net_pay == 0:
            net_pay = gross_pay - deductions
        if 'net_pay' not in data or data['net_pay'] != net_pay:
            update_data['net_pay'] = net_pay
        if 'status_payment' not in data or not data['status_payment']:
            update_data['status_payment'] = 'DRAFT'
        # Also backfill basic_pay and allowances if missing
        if 'basic_pay' not in data or data['basic_pay'] != basic_pay:
            update_data['basic_pay'] = basic_pay
        if 'allowances' not in data or data['allowances'] != allowances:
            update_data['allowances'] = allowances
        if update_data:
            employees_ref.document(doc.id).set(update_data, merge=True)
            updated += 1
    print(f"Seeded payroll fields and values for {updated} employees.")

if __name__ == '__main__':
    seed_payroll_fields()

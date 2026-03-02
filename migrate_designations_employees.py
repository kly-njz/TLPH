"""
Migration script to separate designation and employee data into proper collections.

This script will:
1. Create a 'designations' collection with unique position definitions
2. Create an 'employees' collection with personnel records
3. Link employees to designations via the designation field
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase (if not already initialized)
try:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
except ValueError:
    # Already initialized
    pass

db = firestore.client()

def create_sample_designations():
    """Create sample designation records"""
    print("\n=== Creating Sample Designations ===")
    
    designations = [
        {
            'designation': 'Field Officer',
            'Department_name': 'TECHNICAL OPERATIONS BUREAU',
            'division': 'Field Operations',
            'description': 'Responsible for field inspections, environmental assessments, and on-site compliance monitoring.',
            'required_qualifications': 'Bachelor\'s degree in Environmental Science, Forestry, or related field. Minimum 2 years field experience.',
            'basic_pay': 35000,
            'duty_type': 'field duty',
            'overtime_status': 'eligible',
            'authority_level': 'Field Authorization - Level 2',
            'field_service': 'Required - 80% field work',
            'status': 'Active',
            'municipality': 'Naujan',
            'refField_title': 'Environmental Field Operations',
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        },
        {
            'designation': 'Administrative Officer',
            'Department_name': 'ADMINISTRATIVE DIVISION',
            'division': 'Office Management',
            'description': 'Handles administrative tasks, document processing, and office coordination.',
            'required_qualifications': 'Bachelor\'s degree in Business Administration or Public Administration.',
            'basic_pay': 28000,
            'duty_type': 'fixed office hours',
            'overtime_status': 'eligible',
            'authority_level': 'Administrative Approval - Level 1',
            'field_service': 'Minimal - Office based',
            'status': 'Active',
            'municipality': 'All',
            'refField_title': 'General Administration',
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        },
        {
            'designation': 'Senior Forester',
            'Department_name': 'FORESTRY SERVICES',
            'division': 'Forest Management',
            'description': 'Oversees forest management programs, reforestation projects, and forestry compliance.',
            'required_qualifications': 'Licensed Forester with minimum 5 years experience. Master\'s degree preferred.',
            'basic_pay': 45000,
            'duty_type': 'flexible',
            'overtime_status': 'exempt',
            'authority_level': 'Senior Technical Authority - Level 3',
            'field_service': 'Mixed - 50% field, 50% office',
            'status': 'Active',
            'municipality': 'Region-wide',
            'refField_title': 'Forestry Management',
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        }
    ]
    
    for desg in designations:
        doc_ref = db.collection('designations').add(desg)
        print(f"✓ Created designation: {desg['designation']} (ID: {doc_ref[1].id})")
    
    print(f"\nCreated {len(designations)} designation records")
    return designations

def create_sample_employees():
    """Create sample employee records"""
    print("\n=== Creating Sample Employees ===")
    
    employees = [
        {
            'employee_id': 'EMP-0001',
            'first_name': 'Juan',
            'middle_name': 'Dela',
            'last_name': 'Cruz',
            'designation': 'Field Officer',
            'department_name': 'TECHNICAL OPERATIONS BUREAU',
            'division': 'Field Operations',
            'municipality': 'Naujan',
            'province': 'Oriental Mindoro',
            'region': 'MIMAROPA',
            'contact_Number': '09171234567',
            'email': 'juan.delacruz@denr.gov.ph',
            'hire_date': datetime(2024, 2, 19),
            'status': 'Active',
            'attendance_status': 'On Duty',
            'basic_pay': 35000,
            'allowances': 8000,
            'duty_type': 'field duty',
            'overtime_status': 'eligible',
            'office_address': 'DENR Provincial Office, Calapan City',
            'municipal_address': 'Naujan Municipal Office',
            'role': 'municipal',
            'refField_title': 'Environmental Field Operations',
            'time_in': None,
            'time_out': None,
            'leaves_taken': 0,
            'rated_status': 'Satisfactory',
            'time_Init': firestore.SERVER_TIMESTAMP
        },
        {
            'employee_id': 'EMP-0002',
            'first_name': 'Maria',
            'middle_name': 'Santos',
            'last_name': 'Reyes',
            'designation': 'Administrative Officer',
            'department_name': 'ADMINISTRATIVE DIVISION',
            'division': 'Office Management',
            'municipality': 'Calapan',
            'province': 'Oriental Mindoro',
            'region': 'MIMAROPA',
            'contact_Number': '09187654321',
            'email': 'maria.reyes@denr.gov.ph',
            'hire_date': datetime(2023, 6, 15),
            'status': 'Active',
            'attendance_status': 'On Duty',
            'basic_pay': 28000,
            'allowances': 5000,
            'duty_type': 'fixed office hours',
            'overtime_status': 'eligible',
            'office_address': 'DENR Provincial Office, Calapan City',
            'municipal_address': 'Calapan City Hall',
            'role': 'municipal',
            'refField_title': 'General Administration',
            'time_in': None,
            'time_out': None,
            'leaves_taken': 3,
            'rated_status': 'Outstanding',
            'time_Init': firestore.SERVER_TIMESTAMP
        },
        {
            'employee_id': 'EMP-0003',
            'first_name': 'Roberto',
            'middle_name': 'Garcia',
            'last_name': 'Lopez',
            'designation': 'Senior Forester',
            'department_name': 'FORESTRY SERVICES',
            'division': 'Forest Management',
            'municipality': 'Victoria',
            'province': 'Oriental Mindoro',
            'region': 'MIMAROPA',
            'contact_Number': '09198765432',
            'email': 'roberto.lopez@denr.gov.ph',
            'hire_date': datetime(2019, 3, 1),
            'status': 'Active',
            'attendance_status': 'On Field',
            'basic_pay': 45000,
            'allowances': 12000,
            'duty_type': 'flexible',
            'overtime_status': 'exempt',
            'office_address': 'DENR Provincial Office, Calapan City',
            'municipal_address': 'Victoria Municipal Office',
            'role': 'municipal',
            'refField_title': 'Forestry Management',
            'time_in': None,
            'time_out': None,
            'leaves_taken': 5,
            'rated_status': 'Outstanding',
            'time_Init': firestore.SERVER_TIMESTAMP
        }
    ]
    
    for emp in employees:
        doc_ref = db.collection('employees').add(emp)
        print(f"✓ Created employee: {emp['first_name']} {emp['last_name']} - {emp['designation']} (ID: {doc_ref[1].id})")
    
    print(f"\nCreated {len(employees)} employee records")
    return employees

def verify_collections():
    """Verify the created collections"""
    print("\n=== Verifying Collections ===")
    
    # Count designations
    designations = db.collection('designations').stream()
    desg_count = sum(1 for _ in designations)
    print(f"✓ Designations collection: {desg_count} documents")
    
    # Count employees
    employees = db.collection('employees').stream()
    emp_count = sum(1 for _ in employees)
    print(f"✓ Employees collection: {emp_count} documents")
    
    # Show sample data
    print("\n=== Sample Designation ===")
    first_desg = db.collection('designations').limit(1).stream()
    for doc in first_desg:
        data = doc.to_dict()
        print(f"ID: {doc.id}")
        print(f"Title: {data.get('designation')}")
        print(f"Department: {data.get('Department_name')}")
        print(f"Basic Pay: ₱{data.get('basic_pay', 0):,.2f}")
    
    print("\n=== Sample Employee ===")
    first_emp = db.collection('employees').limit(1).stream()
    for doc in first_emp:
        data = doc.to_dict()
        print(f"ID: {doc.id}")
        print(f"Name: {data.get('first_name')} {data.get('last_name')}")
        print(f"Employee ID: {data.get('employee_id')}")
        print(f"Designation: {data.get('designation')}")
        print(f"Municipality: {data.get('municipality')}")

def main():
    """Main migration function"""
    print("=" * 60)
    print("DENR HR MANAGEMENT - DATA MIGRATION SCRIPT")
    print("=" * 60)
    
    response = input("\nThis will create sample designations and employees collections.\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Migration cancelled.")
        return
    
    try:
        # Create sample data
        create_sample_designations()
        create_sample_employees()
        
        # Verify
        verify_collections()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Refresh the designation-municipal.html page")
        print("2. You should see the designations and employees")
        print("3. Add more records as needed through the admin interface")
        
    except Exception as e:
        print(f"\n✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

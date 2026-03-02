"""
Migration script to create departments collection.

This script will:
1. Create a 'departments' collection with bureau/department definitions
2. Link to existing employees and designations
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

def create_sample_departments():
    """Create sample department records"""
    print("\n=== Creating Sample Departments ===")
    
    departments = [
        {
            'department_name': 'TECHNICAL OPERATIONS BUREAU',
            'department_code': 'TOB',
            'mandate': 'Field operations, environmental assessments, and technical compliance monitoring',
            'region': 'MIMAROPA',
            'municipality': 'Regional',
            'office_location': 'DENR Provincial Office, Calapan City, Oriental Mindoro',
            'head_of_department': 'Engr. Roberto M. Santos',
            'status': 'Active',
            'contact_email': 'tob@denr.gov.ph',
            'contact_number': '09171234567',
            'established_date': datetime(2018, 1, 15),
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        },
        {
            'department_name': 'ADMINISTRATIVE DIVISION',
            'department_code': 'ADMIN',
            'mandate': 'Administrative support, human resources, and office management',
            'region': 'MIMAROPA',
            'municipality': 'Regional',
            'office_location': 'DENR Provincial Office, Calapan City, Oriental Mindoro',
            'head_of_department': 'Atty. Maria Elena Reyes',
            'status': 'Active',
            'contact_email': 'admin@denr.gov.ph',
            'contact_number': '09187654321',
            'established_date': datetime(2015, 6, 1),
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        },
        {
            'department_name': 'FORESTRY SERVICES',
            'department_code': 'FS',
            'mandate': 'Forest management, reforestation programs, and forestry compliance',
            'region': 'MIMAROPA',
            'municipality': 'Regional',
            'office_location': 'DENR Provincial Office, Calapan City, Oriental Mindoro',
            'head_of_department': 'For. Juan Carlos Domingo',
            'status': 'Active',
            'contact_email': 'forestry@denr.gov.ph',
            'contact_number': '09198765432',
            'established_date': datetime(2016, 3, 20),
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        },
        {
            'department_name': 'ENVIRONMENTAL MANAGEMENT',
            'department_code': 'EMB',
            'mandate': 'Environmental impact assessments, pollution control, waste management',
            'region': 'MIMAROPA',
            'municipality': 'Regional',
            'office_location': 'DENR Provincial Office, Calapan City, Oriental Mindoro',
            'head_of_department': 'Dr. Sofia P. Villanueva',
            'status': 'Active',
            'contact_email': 'emb@denr.gov.ph',
            'contact_number': '09176543210',
            'established_date': datetime(2017, 9, 10),
            'time_Init': firestore.SERVER_TIMESTAMP,
            'created_by': 'System Migration'
        }
    ]
    
    for dept in departments:
        doc_ref = db.collection('departments').add(dept)
        print(f"✓ Created department: {dept['department_name']} (ID: {doc_ref[1].id})")
    
    print(f"\nCreated {len(departments)} department records")
    return departments

def verify_collections():
    """Verify the created collections and show relationships"""
    print("\n=== Verifying Collections ===")
    
    # Count departments
    departments = list(db.collection('departments').stream())
    print(f"✓ Departments collection: {len(departments)} documents")
    
    # Count employees
    employees = list(db.collection('employees').stream())
    print(f"✓ Employees collection: {len(employees)} documents")
    
    # Count designations
    designations = list(db.collection('designations').stream())
    print(f"✓ Designations collection: {len(designations)} documents")
    
    # Show relationships
    print("\n=== Department-Employee Relationships ===")
    for dept_doc in departments:
        dept_data = dept_doc.to_dict()
        dept_name = dept_data.get('department_name')
        
        # Count employees in this department
        emp_count = sum(1 for emp in employees if emp.to_dict().get('department_name') == dept_name)
        
        # Count designations in this department
        desg_count = sum(1 for desg in designations if desg.to_dict().get('Department_name') == dept_name)
        
        print(f"\n{dept_name}:")
        print(f"  - Employees: {emp_count}")
        print(f"  - Designations: {desg_count}")
        print(f"  - Head: {dept_data.get('head_of_department', 'N/A')}")
        print(f"  - Status: {dept_data.get('status', 'N/A')}")

def main():
    """Main migration function"""
    print("=" * 60)
    print("DENR HR MANAGEMENT - DEPARTMENTS MIGRATION SCRIPT")
    print("=" * 60)
    
    response = input("\nThis will create sample departments collection.\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Migration cancelled.")
        return
    
    try:
        # Create sample data
        create_sample_departments()
        
        # Verify
        verify_collections()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Refresh the department-municipal.html page")
        print("2. You should see the departments with employee counts")
        print("3. Click 'View' to see employees in each department")
        
    except Exception as e:
        print(f"\n✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

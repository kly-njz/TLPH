#!/usr/bin/env python3
"""
Seed Victoria Leave Requests
This script creates sample leave requests for Victoria, Oriental Mindoro in Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

print("✓ firebase_admin imported successfully")

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("✓ Firebase initialized")

# First, fetch employees from Victoria to create realistic leave requests
try:
    employees_query = db.collection('employees').where('municipality', '==', 'Victoria').stream()
    victoria_employees = []
    
    for doc in employees_query:
        emp = doc.to_dict()
        emp['id'] = doc.id
        victoria_employees.append(emp)
    
    print(f"✓ Found {len(victoria_employees)} employees from Victoria in employees collection")
    
    if len(victoria_employees) == 0:
        print("❌ ERROR: No employees found for Victoria!")
        print("⚠ Please run 'py -3 seed_employees_victoria.py' first to create employee records")
        exit(1)
    
    # Leave request template data
    leave_types = ['Sick Leave', 'Vacation Leave', 'Privilege Leave', 'Maternity Leave', 'Emergency Leave']
    statuses = ['Pending', 'Approved', 'Approved', 'Denied']  # More approved than denied
    
    # Check if leave requests already exist for Victoria
    existing = db.collection('leave_requests').where('municipality', '==', 'Victoria').stream()
    existing_docs = list(existing)
    
    if len(existing_docs) >= 10:
        print(f"✓ {len(existing_docs)} leave requests already exist for Victoria (sufficient records)")
        for idx, doc in enumerate(existing_docs[:5]):
            leave = doc.to_dict()
            print(f"  - {leave.get('employee_name')} - {leave.get('leave_type')} ({leave.get('status')})")
        if len(existing_docs) > 5:
            print(f"  ... and {len(existing_docs) - 5} more")
    else:
        print(f"⚠ Found {len(existing_docs)} leave requests for Victoria, creating more...")
        
        leave_requests = []
        
        # Create leave requests for each employee
        for idx, emp in enumerate(victoria_employees):  # Use all available employees
            # Random leave dates in the past 3 months
            days_ago = random.randint(1, 90)
            start_date = datetime.now() - timedelta(days=days_ago)
            duration = random.randint(1, 10)
            end_date = start_date + timedelta(days=duration)
            
            leave_type = random.choice(leave_types)
            status = random.choice(statuses)
            
            leave_request = {
                "employee_id": emp.get('employee_id', f'DENR-VIC-{2024000+idx}'),
                "employee_name": f"{emp.get('first_name', 'Employee')} {emp.get('last_name', str(idx))}",
                "employee_ref": emp['id'],
                "leave_type": leave_type,
                "from_date": start_date.strftime('%Y-%m-%d'),
                "to_date": end_date.strftime('%Y-%m-%d'),
                "days": duration,
                "status": status,
                "reason": f"Personal {leave_type.lower()} request",
                "municipality": "Victoria",
                "province": "Oriental Mindoro",
                "region": "Region IV-B (MIMAROPA)",
                "filed_date": (start_date - timedelta(days=random.randint(5, 15))).isoformat(),
                "approved_by": "Regional Director" if status == "Approved" else None,
                "approved_date": start_date.isoformat() if status == "Approved" else None,
                "remarks": f"Leave request {status.lower()}",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            leave_requests.append(leave_request)
        
        # Insert into Firestore
        created_count = 0
        for leave in leave_requests:
            doc_ref = db.collection('leave_requests').add(leave)
            created_count += 1
            if created_count <= 5:  # Show first 5
                print(f"✅ Created: {leave['employee_name']} - {leave['leave_type']}")
                print(f"   Dates: {leave['from_date']} to {leave['to_date']} ({leave['days']} days)")
                print(f"   Status: {leave['status']}")
                print(f"   Document ID: {doc_ref[1].id}")
        
        if created_count > 5:
            print(f"   ... and {created_count - 5} more leave requests")
        
        print(f"\n✅ Total {created_count} leave requests seeded successfully for Victoria!")
        
        # Show statistics
        pending_count = sum(1 for l in leave_requests if l['status'] == 'Pending')
        approved_count = sum(1 for l in leave_requests if l['status'] == 'Approved')
        denied_count = sum(1 for l in leave_requests if l['status'] == 'Denied')
        
        print(f"\n📊 Statistics:")
        print(f"   Pending: {pending_count}")
        print(f"   Approved: {approved_count}")
        print(f"   Denied: {denied_count}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

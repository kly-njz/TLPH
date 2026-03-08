#!/usr/bin/env python3
"""
Seed Victoria Employees
This script creates employee records for Victoria, Oriental Mindoro in Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random

print("✓ firebase_admin imported successfully")

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("✓ Firebase initialized")

# Employee data for Victoria
employee_data = [
    {"first_name": "Maria", "last_name": "Santos", "position": "Environment Officer", "department": "Administration"},
    {"first_name": "Juan", "last_name": "Cruz", "position": "Land Monitor", "department": "Field Operations"},
    {"first_name": "Rosa", "last_name": "Garcia", "position": "Field Inspector", "department": "Field Operations"},
    {"first_name": "Pedro", "last_name": "Reyes", "position": "Coordinator", "department": "Administration"},
    {"first_name": "Ana", "last_name": "Lopez", "position": "Natural Resources Specialist", "department": "Technical Services"},
    {"first_name": "Carlos", "last_name": "Mendoza", "position": "Forest Ranger", "department": "Field Operations"},
    {"first_name": "Elena", "last_name": "Ramos", "position": "Administrative Assistant", "department": "Administration"},
    {"first_name": "Jose", "last_name": "Fernandez", "position": "GIS Specialist", "department": "Technical Services"},
    {"first_name": "Carmen", "last_name": "Torres", "position": "Wildlife Monitor", "department": "Field Operations"},
    {"first_name": "Miguel", "last_name": "Diaz", "position": "Permits Officer", "department": "Administration"},
    {"first_name": "Sofia", "last_name": "Rivera", "position": "Environmental Analyst", "department": "Technical Services"},
    {"first_name": "Rafael", "last_name": "Gomez", "position": "Coastal Resources Officer", "department": "Field Operations"}
]

try:
    # Check existing employees
    existing = db.collection('employees').where('municipality', '==', 'Victoria').stream()
    existing_docs = list(existing)
    
    if len(existing_docs) >= 10:
        print(f"✓ {len(existing_docs)} employees already exist for Victoria (sufficient records)")
        for idx, doc in enumerate(existing_docs[:5]):
            emp = doc.to_dict()
            print(f"  - {emp.get('first_name')} {emp.get('last_name')} - {emp.get('position', 'N/A')}")
        if len(existing_docs) > 5:
            print(f"  ... and {len(existing_docs) - 5} more")
    else:
        print(f"⚠ Found {len(existing_docs)} employees for Victoria, creating more...")
        
        created_count = 0
        for idx, emp_data in enumerate(employee_data, 1):
            employee = {
                "employee_id": f"DENR-VIC-{2024100 + idx}",
                "first_name": emp_data["first_name"],
                "last_name": emp_data["last_name"],
                "full_name": f"{emp_data['first_name']} {emp_data['last_name']}",
                "email": f"{emp_data['first_name'].lower()}.{emp_data['last_name'].lower()}@victoria.denr.gov.ph",
                "position": emp_data["position"],
                "designation": emp_data["position"],
                "department_name": emp_data["department"],
                "municipality": "Victoria",
                "province": "Oriental Mindoro",
                "region": "Region IV-B (MIMAROPA)",
                "status": "Active",
                "employment_type": random.choice(["Permanent", "Permanent", "Contractual"]),
                "hire_date": f"202{random.randint(0,5)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "contact_number": f"09{random.randint(100000000, 999999999)}",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            doc_ref = db.collection('employees').add(employee)
            created_count += 1
            
            if created_count <= 5:
                print(f"✅ Created: {employee['full_name']}")
                print(f"   ID: {employee['employee_id']}")
                print(f"   Position: {employee['position']}")
                print(f"   Department: {employee['department_name']}")
                print(f"   Document ID: {doc_ref[1].id}")
        
        if created_count > 5:
            print(f"   ... and {created_count - 5} more employees")
        
        print(f"\n✅ Total {created_count} employees created for Victoria!")
        print(f"📊 Total employees in Victoria: {len(existing_docs) + created_count}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

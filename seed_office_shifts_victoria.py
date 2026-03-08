#!/usr/bin/env python3
"""
Seed Victoria Office Shifts
This script creates office shift schedules for Victoria, Oriental Mindoro in Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

print("✓ firebase_admin imported successfully")

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("✓ Firebase initialized")

# Office shifts data for Victoria
office_shifts = [
    {
        "code": "SHFT-REG-01",
        "name": "REGULAR DAY SHIFT (ADMINISTRATIVE STAFF)",
        "municipality": "Victoria",
        "province": "Oriental Mindoro",
        "region": "Region IV-B (MIMAROPA)",
        "duty_type": "Fixed Office Hours",
        "start_time": "08:00 AM",
        "end_time": "05:00 PM",
        "grace_period": 15,
        "lunch_break_start": "12:00 PM",
        "lunch_break_end": "01:00 PM",
        "break_duration": 60,
        "days_per_week": 5,
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "description": "Standard office hours for administrative and indoor office personnel",
        "status": "Active",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "code": "SHFT-FLD-02",
        "name": "FIELD OPERATIONS SHIFT",
        "municipality": "Victoria",
        "province": "Oriental Mindoro",
        "region": "Region IV-B (MIMAROPA)",
        "duty_type": "Flexible Field Hours",
        "start_time": "06:00 AM",
        "end_time": "04:00 PM",
        "grace_period": 20,
        "lunch_break_start": "11:30 AM",
        "lunch_break_end": "12:30 PM",
        "break_duration": 60,
        "days_per_week": 5,
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "description": "Field officers, inspectors, and field personnel conducting on-site assessments",
        "status": "Active",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "code": "SHFT-EVE-03",
        "name": "EVENING/EVENING OPERATIONS SHIFT",
        "municipality": "Victoria",
        "province": "Oriental Mindoro",
        "region": "Region IV-B (MIMAROPA)",
        "duty_type": "Evening Shift",
        "start_time": "02:00 PM",
        "end_time": "11:00 PM",
        "grace_period": 15,
        "lunch_break_start": "06:00 PM",
        "lunch_break_end": "07:00 PM",
        "break_duration": 60,
        "days_per_week": 5,
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "description": "Evening shift for surveillance, documentation, and extended coverage",
        "status": "Active",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "code": "SHFT-WKD-04",
        "name": "WEEKEND/HOLIDAY DUTY",
        "municipality": "Victoria",
        "province": "Oriental Mindoro",
        "region": "Region IV-B (MIMAROPA)",
        "duty_type": "Rotating/On-Call",
        "start_time": "08:00 AM",
        "end_time": "05:00 PM",
        "grace_period": 15,
        "lunch_break_start": "12:00 PM",
        "lunch_break_end": "01:00 PM",
        "break_duration": 60,
        "days_per_week": 2,
        "working_days": ["Saturday", "Sunday"],
        "description": "Rotating weekend and holiday duty for emergency response and urgent matters",
        "status": "Active",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]

# Check if collection exists and has data for Victoria
try:
    existing = db.collection('office_shifts').where('municipality', '==', 'Victoria').limit(1).stream()
    existing_docs = list(existing)
    
    if existing_docs:
        print(f"✓ Office shifts already exist for Victoria")
        for doc in existing_docs:
            print(f"  - {doc.get('name')} ({doc.id})")
    else:
        print(f"⚠ No shifts found for Victoria, creating collection...")
        
        for shift in office_shifts:
            doc_ref = db.collection('office_shifts').add(shift)
            print(f"✅ Created shift: {shift['name']}")
            print(f"   Code: {shift['code']}")
            print(f"   Hours: {shift['start_time']} - {shift['end_time']}")
            print(f"   Status: {shift['status']}")
            print(f"   Document ID: {doc_ref[1].id}")
        
        print(f"\n✅ All {len(office_shifts)} shifts seeded successfully for Victoria!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""
Seed regional system logs for Victoria municipality.
This creates realistic system log entries visible to regional admins in MIMAROPA/REGION-IV-B.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

print("✓ firebase_admin imported successfully")

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass  # App already initialized

db = firestore.client()
print("✓ Firebase initialized")

# Regional admin and municipal admin users for Victoria
victoria_admins = [
    {
        'email': 'victoria.admin@denr.gov.ph',
        'name': 'Maria Santos',
        'role': 'municipal_admin',
        'user_id': 'user-victoria-001'
    },
    {
        'email': 'victoria.secondary@denr.gov.ph',
        'name': 'Juan Dela Cruz',
        'role': 'municipal_admin',
        'user_id': 'user-victoria-002'
    },
    {
        'email': 'regional.admin@denr.gov.ph',
        'name': 'Pedro Reyes',
        'role': 'regional_admin',
        'user_id': 'user-regional-001'
    }
]

# Sample system log entries for Victoria
timestamp_base = datetime.utcnow()
log_entries = [
    # LOGIN/LOGOUT sequences
    {
        'action': 'LOGIN',
        'actorEmail': 'victoria.admin@denr.gov.ph',
        'actorName': 'Maria Santos',
        'actorId': 'user-victoria-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed in.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.100',
        'timestamp': (timestamp_base - timedelta(hours=8)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=8)).isoformat(),
    },
    {
        'action': 'LOGOUT',
        'actorEmail': 'victoria.admin@denr.gov.ph',
        'actorName': 'Maria Santos',
        'actorId': 'user-victoria-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed out.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.100',
        'timestamp': (timestamp_base - timedelta(hours=7)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=7)).isoformat(),
    },
    # Second admin login
    {
        'action': 'LOGIN',
        'actorEmail': 'victoria.secondary@denr.gov.ph',
        'actorName': 'Juan Dela Cruz',
        'actorId': 'user-victoria-002',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed in.',
        'outcome': 'SUCCESS',
        'device_type': 'Laptop',
        'ip': '192.168.1.101',
        'timestamp': (timestamp_base - timedelta(hours=6, minutes=30)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=6, minutes=30)).isoformat(),
    },
    # Approval action
    {
        'action': 'APPROVED',
        'actorEmail': 'victoria.admin@denr.gov.ph',
        'actorName': 'Maria Santos',
        'actorId': 'user-victoria-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUDIT',
        'target': 'Permit PR-2026-001',
        'targetId': 'permit-001',
        'message': 'Municipal admin approved permit PR-2026-001.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.100',
        'timestamp': (timestamp_base - timedelta(hours=5)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=5)).isoformat(),
    },
    # Another login
    {
        'action': 'LOGIN',
        'actorEmail': 'maria.santos@victoria.gov.ph',
        'actorName': 'Maria Santos - Treasury',
        'actorId': 'user-treasury-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed in.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.102',
        'timestamp': (timestamp_base - timedelta(hours=4)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=4)).isoformat(),
    },
    # Financial action
    {
        'action': 'APPROVED',
        'actorEmail': 'maria.santos@victoria.gov.ph',
        'actorName': 'Maria Santos - Treasury',
        'actorId': 'user-treasury-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'FINANCE',
        'target': 'Check Voucher #2026-001',
        'targetId': 'cv-2026-001',
        'message': 'Municipal admin approved financial document.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.102',
        'timestamp': (timestamp_base - timedelta(hours=3, minutes=45)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=3, minutes=45)).isoformat(),
    },
    # Login from second user
    {
        'action': 'LOGIN',
        'actorEmail': 'juan.dela.cruz@victoria.gov.ph',
        'actorName': 'Juan Dela Cruz - Assessment',
        'actorId': 'user-assessment-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed in.',
        'outcome': 'SUCCESS',
        'device_type': 'Tablet',
        'ip': '192.168.1.103',
        'timestamp': (timestamp_base - timedelta(hours=2)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=2)).isoformat(),
    },
    # Assessment approval
    {
        'action': 'APPROVED',
        'actorEmail': 'juan.dela.cruz@victoria.gov.ph',
        'actorName': 'Juan Dela Cruz - Assessment',
        'actorId': 'user-assessment-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'ASSESSMENT',
        'target': 'Property Assessment #VIC-2026-0001',
        'targetId': 'assessment-001',
        'message': 'Municipal admin approved property assessment.',
        'outcome': 'SUCCESS',
        'device_type': 'Tablet',
        'ip': '192.168.1.103',
        'timestamp': (timestamp_base - timedelta(hours=1, minutes=30)).isoformat(),
        'created_at': (timestamp_base - timedelta(hours=1, minutes=30)).isoformat(),
    },
    # Recent login
    {
        'action': 'LOGIN',
        'actorEmail': 'victoria.admin@denr.gov.ph',
        'actorName': 'Maria Santos',
        'actorId': 'user-victoria-001',
        'actorRole': 'municipal_admin',
        'municipality': 'Victoria',
        'municipality_name': 'Victoria',
        'region': 'Region IV-B (MIMAROPA)',
        'region_name': 'REGION-IV-B',
        'regionName': 'MIMAROPA',
        'module': 'AUTH',
        'message': 'Municipal admin signed in.',
        'outcome': 'SUCCESS',
        'device_type': 'Desktop',
        'ip': '192.168.1.100',
        'timestamp': (timestamp_base - timedelta(minutes=15)).isoformat(),
        'created_at': (timestamp_base - timedelta(minutes=15)).isoformat(),
    },
]

# Add logs to Firestore
try:
    collection_ref = db.collection('regional_system_logs')
    count = 0
    
    for log in log_entries:
        doc_ref = collection_ref.document()
        log['id'] = doc_ref.id
        doc_ref.set(log)
        count += 1
        print(f"  ✓ Added log {count}: {log.get('action', 'UNKNOWN')} by {log.get('actorName', 'Unknown')}")
    
    print(f"\n✅ Successfully seeded {count} regional system logs for Victoria")
    print(f"   Municipality: Victoria")
    print(f"   Region: REGION-IV-B (MIMAROPA)")
    print(f"   Logs visible to: Regional Admins")
    
except Exception as e:
    print(f"❌ Error seeding regional system logs: {e}")
    import traceback
    traceback.print_exc()

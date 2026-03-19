"""Seed login/logout events for Victoria municipal admins to test regional system logs display"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Victoria municipality details
VICTORIA_REGION = "REGION-IV-B"
VICTORIA_MUNICIPALITY = "Victoria"

# Sample municipal admin emails for Victoria
ADMIN_EMAILS = [
    "victoria_admin@denr.gov.ph",
    "victoria_hrm@denr.gov.ph"
]

def seed_login_logout_events():
    """Create realistic login/logout events for Victoria municipal admins"""
    events_created = 0
    
    # Create events for the last 7 days, multiple per day
    for days_ago in range(7, -1, -1):
        event_date = datetime.utcnow() - timedelta(days=days_ago)
        
        for admin_email in ADMIN_EMAILS:
            # Morning login
            login_time = event_date.replace(hour=8, minute=random.randint(0, 59))
            events_created += 1
            db.collection('regional_system_logs').document().set({
                "id": f"login_{events_created}",
                "region": VICTORIA_REGION,
                "municipality": VICTORIA_MUNICIPALITY,
                "user": admin_email,
                "actorEmail": admin_email,
                "actorId": f"user_{admin_email.split('@')[0]}",
                "role": "municipal_admin",
                "actorRole": "municipal_admin",
                "action": "LOGIN",
                "target": "Authentication",
                "targetId": f"user_{admin_email.split('@')[0]}",
                "module": "AUTH",
                "outcome": "SUCCESS",
                "message": f"Municipal admin {admin_email} logged in.",
                "ip": f"192.168.1.{random.randint(100, 200)}",
                "ipAddress": f"192.168.1.{random.randint(100, 200)}",
                "device_type": random.choice(["Windows", "MacOS", "Linux", "Mobile"]),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "scope": "MUNICIPAL",
                "metadata": {"source": "seed_script"},
                "created_at": login_time,
                "timestamp": login_time.isoformat(),
                "expires_at": login_time + timedelta(days=180)
            })
            print(f"✅ Created LOGIN event for {admin_email} at {login_time}")
            
            # Evening logout
            logout_time = event_date.replace(hour=17, minute=random.randint(0, 59))
            events_created += 1
            db.collection('regional_system_logs').document().set({
                "id": f"logout_{events_created}",
                "region": VICTORIA_REGION,
                "municipality": VICTORIA_MUNICIPALITY,
                "user": admin_email,
                "actorEmail": admin_email,
                "actorId": f"user_{admin_email.split('@')[0]}",
                "role": "municipal_admin",
                "actorRole": "municipal_admin",
                "action": "LOGOUT",
                "target": "Authentication",
                "targetId": f"user_{admin_email.split('@')[0]}",
                "module": "AUTH",
                "outcome": "SUCCESS",
                "message": f"Municipal admin {admin_email} logged out.",
                "ip": f"192.168.1.{random.randint(100, 200)}",
                "ipAddress": f"192.168.1.{random.randint(100, 200)}",
                "device_type": random.choice(["Windows", "MacOS", "Linux", "Mobile"]),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "scope": "MUNICIPAL",
                "metadata": {"source": "seed_script"},
                "created_at": logout_time,
                "timestamp": logout_time.isoformat(),
                "expires_at": logout_time + timedelta(days=180)
            })
            print(f"✅ Created LOGOUT event for {admin_email} at {logout_time}")
    
    print(f"\n✅ Successfully created {events_created} login/logout events for Victoria")
    print(f"Region: {VICTORIA_REGION}")
    print(f"Municipality: {VICTORIA_MUNICIPALITY}")
    print(f"Admins: {', '.join(ADMIN_EMAILS)}")

if __name__ == "__main__":
    print("🌱 Seeding login/logout events for Victoria municipal admins...\n")
    seed_login_logout_events()
    print("\n✨ Seed complete!")

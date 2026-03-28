# notification_storage.py
# Firestore logic for notifications collection
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

NOTIFICATION_TYPES = [
    "system", "user", "transactional", "promotional", "reminder", "security", "administrative"
]

def create_notification(type, content, post_date, end_date, created_by, target_users=None):
    assert type in NOTIFICATION_TYPES, "Invalid notification type"
    doc = {
        "type": type,
        "content": content,
        "post_date": post_date,
        "end_date": end_date,
        "created_by": created_by,
        "status": "scheduled" if post_date > datetime.utcnow() else "active",
        "target_users": target_users or [],
        "created_at": datetime.utcnow(),
    }
    ref = db.collection("notifications").add(doc)
    return ref

def get_active_notifications(now=None):
    now = now or datetime.utcnow()
    docs = db.collection("notifications") \
        .where("post_date", "<=", now) \
        .where("end_date", ">=", now) \
        .where("status", "in", ["active", "scheduled"]) \
        .stream()
    return [d.to_dict() | {"id": d.id} for d in docs]

def expire_old_notifications():
    now = datetime.utcnow()
    docs = db.collection("notifications") \
        .where("end_date", "<", now) \
        .where("status", "!=", "expired") \
        .stream()
    for d in docs:
        d.reference.update({"status": "expired"})
    # Optionally, delete expired notifications
    # for d in docs:
    #     d.reference.delete()

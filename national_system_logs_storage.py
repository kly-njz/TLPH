"""National System Logs Management"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import Optional, List, Dict, Any

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
NATIONAL_SYSTEM_LOGS_COLLECTION = "national_system_logs"


def add_national_system_log(
    user: str,
    action: str,
    target: str = "",
    target_id: str = "",
    module: str = "SYSTEM",
    outcome: str = "SUCCESS",
    message: str = "",
    ip_address: str = "",
    device_type: str = "Unknown",
    user_agent: str = "",
    metadata: dict = None,
) -> Dict[str, Any]:
    """Add a national system log entry"""
    doc_ref = db.collection(NATIONAL_SYSTEM_LOGS_COLLECTION).document()
    log_entry = {
        "id": doc_ref.id,
        "user": user,
        "action": action,
        "target": target,
        "target_id": target_id,
        "module": module or "SYSTEM",
        "outcome": outcome,
        "message": message,
        "ip": str(ip_address or "").strip(),
        "device_type": device_type,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "created_at": firestore.SERVER_TIMESTAMP,
        "timestamp": datetime.utcnow().isoformat()
    }
    doc_ref.set(log_entry)
    return {**log_entry, "id": doc_ref.id}


def list_national_system_logs(limit: int = 500) -> List[Dict[str, Any]]:
    """List entries from the national system logs collection."""
    result: List[Dict[str, Any]] = []
    try:
        query = db.collection(NATIONAL_SYSTEM_LOGS_COLLECTION)
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)
        for doc in query.stream():
            log_entry = doc.to_dict()
            if log_entry:
                result.append(log_entry)
        return result
    except Exception as e:
        print(f"[WARN] National system logs query failed: {e}")
    return result

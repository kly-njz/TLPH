"""System Logs Management for Municipal Scope"""
import firebase_admin
from firebase_admin import credentials, firestore
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


def _slugify(value: str) -> str:
    """Convert string to slug format"""
    return re.sub(r'[^a-z0-9]+', '_', (value or '').lower()).strip('_')


# ==================== SYSTEM LOGS ====================

def add_system_log(
    municipality: str,
    user: str,
    action: str,
    target: str = "",
    target_id: str = "",
    module: str = "",
    outcome: str = "SUCCESS",
    message: str = "",
    device_type: str = "Unknown",
    user_agent: str = "",
    metadata: dict = None,
) -> Dict[str, Any]:
    """Add a system log entry"""
    doc_ref = db.collection("system_logs").document()
    log_entry = {
        "id": doc_ref.id,
        "municipality": municipality,
        "user": user,
        "action": action,
        "target": target,
        "target_id": target_id,
        "module": module or "SYSTEM",
        "outcome": outcome,
        "message": message,
        "device_type": device_type,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "created_at": firestore.SERVER_TIMESTAMP,
        "timestamp": datetime.utcnow().isoformat()
    }
    doc_ref.set(log_entry)
    return {**log_entry, "id": doc_ref.id}


def get_system_log(log_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific system log"""
    doc = db.collection("system_logs").document(log_id).get()
    return doc.to_dict() if doc.exists else None


def list_system_logs(municipality: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    """List system logs, optionally filtered by municipality"""
    query = db.collection("system_logs")
    if municipality:
        query = query.where("municipality", "==", municipality)
    
    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    query = query.limit(limit)
    
    docs = query.stream()
    result = []
    for doc in docs:
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)
    return result


def list_system_logs_by_action(
    municipality: str,
    action: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List system logs filtered by action"""
    query = db.collection("system_logs").where(
        "municipality", "==", municipality
    ).where(
        "action", "==", action.upper()
    ).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).limit(limit)
    
    docs = query.stream()
    result = []
    for doc in docs:
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)
    return result


def get_login_logs(municipality: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Get login logs for a municipality in the last X hours"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.collection("system_logs").where(
        "municipality", "==", municipality
    ).where(
        "action", "==", "LOGIN"
    ).where(
        "created_at", ">=", cutoff
    ).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    )
    
    docs = query.stream()
    result = []
    for doc in docs:
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)
    return result


def get_approval_logs(municipality: str, hours: int = 72) -> List[Dict[str, Any]]:
    """Get approval logs for a municipality in the last X hours"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.collection("system_logs").where(
        "municipality", "==", municipality
    ).where(
        "action", "==", "APPROVE"
    ).where(
        "created_at", ">=", cutoff
    ).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    )
    
    docs = query.stream()
    result = []
    for doc in docs:
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)
    return result


def get_system_log_stats(municipality: str) -> Dict[str, Any]:
    """Get statistics for system logs"""
    logs = list_system_logs(municipality, limit=1000)
    
    stats = {
        "total": len(logs),
        "by_action": {},
        "by_outcome": {},
        "by_device": {},
        "by_module": {},
        "logins_24h": len(get_login_logs(municipality, 24)),
        "approvals_72h": len(get_approval_logs(municipality, 72))
    }
    
    for log in logs:
        action = log.get("action", "UNKNOWN")
        outcome = log.get("outcome", "UNKNOWN")
        device = log.get("device_type", "Unknown")
        module = log.get("module", "UNKNOWN")
        
        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
        stats["by_outcome"][outcome] = stats["by_outcome"].get(outcome, 0) + 1
        stats["by_device"][device] = stats["by_device"].get(device, 0) + 1
        stats["by_module"][module] = stats["by_module"].get(module, 0) + 1
    
    return stats


def detect_device_type(user_agent: str) -> str:
    """Detect device type from User-Agent string"""
    ua = (user_agent or "").lower()
    
    if "mobile" in ua or "android" in ua or "iphone" in ua or "ipad" in ua:
        if "iphone" in ua or "ipad" in ua:
            return "Apple iOS"
        elif "android" in ua:
            return "Android"
        else:
            return "Mobile"
    elif "windows" in ua:
        return "Windows"
    elif "mac" in ua:
        return "macOS"
    elif "linux" in ua:
        return "Linux"
    else:
        return "Unknown"

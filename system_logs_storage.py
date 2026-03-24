"""System Logs Management for Municipal Scope"""
import firebase_admin
from firebase_admin import credentials, firestore

# Fix for FieldFilter NameError
from google.cloud.firestore_v1 import FieldFilter

import re
from datetime import datetime, timedelta
import random
from typing import Optional, List, Dict, Any

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
REGIONAL_SYSTEM_LOGS_COLLECTION = "regional_system_logs"
REGIONAL_SYSTEM_LOGS_RETENTION_DAYS = 180
REGIONAL_SYSTEM_LOGS_CLEANUP_SAMPLE_RATE = 0.02
REGIONAL_SYSTEM_LOGS_CLEANUP_BATCH = 200


def _slugify(value: str) -> str:
    """Convert string to slug format"""
    return re.sub(r'[^a-z0-9]+', '_', (value or '').lower()).strip('_')


def _where(query, field: str, op: str, value):
    """Apply Firestore query filter using keyword-based syntax."""
    return query.where(filter=FieldFilter(field, op, value))


def _to_sort_key(value: Any) -> datetime:
    """Best-effort datetime conversion for stable Python-side sorting."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return datetime.min
    return datetime.min


def extract_request_ip(req) -> str:
    """Best-effort client IP extraction from a Flask request."""
    if req is None:
        return ""

    candidates = [
        req.headers.get("X-Forwarded-For", ""),
        req.headers.get("X-Real-IP", ""),
        req.headers.get("CF-Connecting-IP", ""),
        req.headers.get("True-Client-IP", ""),
        req.headers.get("Fly-Client-IP", ""),
        getattr(req, "remote_addr", ""),
    ]

    for raw in candidates:
        value = str(raw or "").strip()
        if not value:
            continue
        if "," in value:
            value = value.split(",", 1)[0].strip()
        return value
    return ""


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
    ip_address: str = "",
    device_type: str = "Unknown",
    user_agent: str = "",
    metadata: dict = None,
) -> Dict[str, Any]:
    """Add a system log entry"""
    print(f"[DEBUG] add_system_log - municipality: '{municipality}', user: '{user}', action: '{action}'")
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
        "ip": str(ip_address or "").strip(),
        "ipAddress": str(ip_address or "").strip(),
        "device_type": device_type,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "created_at": firestore.SERVER_TIMESTAMP,
        "timestamp": datetime.utcnow().isoformat()
    }
    doc_ref.set(log_entry)
    print(f"[DEBUG] Log saved with ID: {doc_ref.id}")
    return {**log_entry, "id": doc_ref.id}


def add_regional_system_log(
    region: str,
    municipality: str,
    user: str,
    action: str,
    user_id: str = "",
    role: str = "municipal",
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
    """Add a region-visible municipal operational log entry to a dedicated collection."""
    doc_ref = db.collection(REGIONAL_SYSTEM_LOGS_COLLECTION).document()
    expires_at = datetime.utcnow() + timedelta(days=REGIONAL_SYSTEM_LOGS_RETENTION_DAYS)
    log_entry = {
        "id": doc_ref.id,
        "region": str(region or "").strip(),
        "municipality": str(municipality or "").strip(),
        "user": str(user or "").strip(),
        "actorEmail": str(user or "").strip(),
        "actorId": str(user_id or "").strip(),
        "role": str(role or "municipal").strip(),
        "actorRole": str(role or "municipal").strip(),
        "action": str(action or "").strip().upper(),
        "target": str(target or "").strip(),
        "target_id": str(target_id or "").strip(),
        "targetId": str(target_id or "").strip(),
        "module": module or "SYSTEM",
        "outcome": outcome or "SUCCESS",
        "message": message or "",
        "ip": str(ip_address or "").strip(),
        "ipAddress": str(ip_address or "").strip(),
        "device_type": device_type or "Unknown",
        "user_agent": user_agent or "",
        "scope": "MUNICIPAL",
        "metadata": metadata or {},
        # Enables optional Firestore TTL policy and supports fallback app-level cleanup.
        "expires_at": expires_at,
        "created_at": firestore.SERVER_TIMESTAMP,
        "timestamp": datetime.utcnow().isoformat(),
    }
    doc_ref.set(log_entry)

    # Best-effort retention cleanup: low-frequency and non-blocking for callers.
    if random.random() < REGIONAL_SYSTEM_LOGS_CLEANUP_SAMPLE_RATE:
        try:
            prune_expired_regional_system_logs()
        except Exception as cleanup_err:
            print(f"[WARN] Regional system log cleanup skipped: {cleanup_err}")

    return {**log_entry, "id": doc_ref.id}


def prune_expired_regional_system_logs(batch_size: int = REGIONAL_SYSTEM_LOGS_CLEANUP_BATCH) -> int:
    """Delete expired docs from dedicated regional system logs collection."""
    deleted = 0
    cutoff = datetime.utcnow()

    query = db.collection(REGIONAL_SYSTEM_LOGS_COLLECTION)
    query = _where(query, "expires_at", "<=", cutoff)
    query = query.limit(batch_size)

    docs = list(query.stream())
    if not docs:
        return 0

    batch = db.batch()
    for doc in docs:
        batch.delete(doc.reference)
        deleted += 1
    batch.commit()
    return deleted


def list_regional_system_logs(limit: int = 500, db_override=None) -> List[Dict[str, Any]]:
    """List entries from the dedicated regional system logs collection."""
    _db = db_override or db
    result: List[Dict[str, Any]] = []

    try:
        query = _db.collection(REGIONAL_SYSTEM_LOGS_COLLECTION)
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        for doc in query.stream():
            log_entry = doc.to_dict()
            if log_entry:
                result.append(log_entry)
        return result
    except Exception as e:
        print(f"[WARN] Indexed regional system logs query failed, falling back: {e}")

    for doc in _db.collection(REGIONAL_SYSTEM_LOGS_COLLECTION).stream():
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)

    result.sort(
        key=lambda row: _to_sort_key(row.get("created_at") or row.get("timestamp")),
        reverse=True,
    )
    return result[:limit]


def list_regional_system_logs_by_region(region: str, limit: int = 200) -> List[Dict[str, Any]]:
    """List dedicated regional system logs for one region, newest first.

    Uses a region+created_at index when available and falls back to Python-side filtering.
    """
    target_region = str(region or "").strip()
    if not target_region:
        return list_regional_system_logs(limit=limit)

    result: List[Dict[str, Any]] = []

    try:
        query = db.collection(REGIONAL_SYSTEM_LOGS_COLLECTION)
        query = _where(query, "region", "==", target_region)
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)
        for doc in query.stream():
            row = doc.to_dict()
            if row:
                result.append(row)
        return result
    except Exception as e:
        print(f"[WARN] Indexed regional logs by region query failed, falling back: {e}")

    for row in list_regional_system_logs(limit=1000):
        if str(row.get("region") or "").strip() == target_region:
            result.append(row)

    result.sort(
        key=lambda row: _to_sort_key(row.get("created_at") or row.get("timestamp")),
        reverse=True,
    )
    return result[:limit]


def get_system_log(log_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific system log"""
    doc = db.collection("system_logs").document(log_id).get()
    return doc.to_dict() if doc.exists else None


def list_system_logs(municipality: Optional[str] = None, limit: int = 500, db_override=None) -> List[Dict[str, Any]]:
    """List system logs, optionally filtered by municipality"""
    _db = db_override or db
    result: List[Dict[str, Any]] = []

    # Preferred path: indexed query with server-side order/limit.
    try:
        query = _db.collection("system_logs")
        if municipality:
            query = _where(query, "municipality", "==", municipality)

        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        for doc in query.stream():
            log_entry = doc.to_dict()
            if log_entry:
                result.append(log_entry)
        return result
    except Exception as e:
        print(f"[WARN] Indexed system_logs query failed, falling back: {e}")

    # Fallback path: avoid order_by to prevent composite-index requirement.
    query = _db.collection("system_logs")
    if municipality:
        query = _where(query, "municipality", "==", municipality)

    for doc in query.stream():
        log_entry = doc.to_dict()
        if log_entry:
            result.append(log_entry)

    result.sort(
        key=lambda row: _to_sort_key(row.get("created_at") or row.get("timestamp")),
        reverse=True
    )
    return result[:limit]


def list_system_logs_by_action(
    municipality: str,
    action: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List system logs filtered by action"""
    query = db.collection("system_logs")
    query = _where(query, "municipality", "==", municipality)
    query = _where(query, "action", "==", action.upper())
    query = query.order_by(
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
    result: List[Dict[str, Any]] = []

    try:
        query = db.collection("system_logs")
        query = _where(query, "municipality", "==", municipality)
        query = _where(query, "action", "==", "LOGIN")
        query = _where(query, "created_at", ">=", cutoff)
        query = query.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )

        for doc in query.stream():
            log_entry = doc.to_dict()
            if log_entry:
                result.append(log_entry)
        return result
    except Exception as e:
        print(f"[WARN] Indexed login logs query failed, falling back: {e}")

    query = db.collection("system_logs")
    query = _where(query, "municipality", "==", municipality)
    query = _where(query, "action", "==", "LOGIN")

    for doc in query.stream():
        log_entry = doc.to_dict()
        if not log_entry:
            continue
        current_dt = _to_sort_key(log_entry.get("created_at") or log_entry.get("timestamp"))
        if current_dt >= cutoff:
            result.append(log_entry)

    result.sort(
        key=lambda row: _to_sort_key(row.get("created_at") or row.get("timestamp")),
        reverse=True
    )
    return result


def get_approval_logs(municipality: str, hours: int = 72) -> List[Dict[str, Any]]:
    """Get approval logs for a municipality in the last X hours"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result: List[Dict[str, Any]] = []

    try:
        query = db.collection("system_logs")
        query = _where(query, "municipality", "==", municipality)
        query = _where(query, "action", "==", "APPROVE")
        query = _where(query, "created_at", ">=", cutoff)
        query = query.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )

        for doc in query.stream():
            log_entry = doc.to_dict()
            if log_entry:
                result.append(log_entry)
        return result
    except Exception as e:
        print(f"[WARN] Indexed approval logs query failed, falling back: {e}")

    query = db.collection("system_logs")
    query = _where(query, "municipality", "==", municipality)
    query = _where(query, "action", "==", "APPROVE")

    for doc in query.stream():
        log_entry = doc.to_dict()
        if not log_entry:
            continue
        current_dt = _to_sort_key(log_entry.get("created_at") or log_entry.get("timestamp"))
        if current_dt >= cutoff:
            result.append(log_entry)

    result.sort(
        key=lambda row: _to_sort_key(row.get("created_at") or row.get("timestamp")),
        reverse=True
    )
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

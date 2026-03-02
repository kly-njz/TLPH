"""Entity Management for Municipal Scope"""
import firebase_admin
from firebase_admin import credentials, firestore
import os
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


# ==================== ENTITIES ====================

def add_entity(
    municipality: str,
    name: str,
    entity_type: str,
    office_or_unit: str = "",
    bank_account: str = "",
    status: str = "ACTIVE",
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new entity for a municipality"""
    doc_id = entity_id or f"{_slugify(municipality)}_{_slugify(name)}"
    data = {
        "id": doc_id,
        "municipality": municipality,
        "name": name,
        "type": entity_type,
        "office_or_unit": office_or_unit,
        "bank_account": bank_account,
        "status": status,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    db.collection("entities").document(doc_id).set(data)
    return {"id": doc_id, **data}


def get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific entity"""
    doc = db.collection("entities").document(entity_id).get()
    return doc.to_dict() if doc.exists else None


def list_entities(municipality: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all entities, optionally filtered by municipality"""
    query = db.collection("entities")
    if municipality:
        query = query.where("municipality", "==", municipality)
    
    docs = query.stream()
    result = []
    for doc in docs:
        entity = doc.to_dict()
        if entity:
            result.append(entity)
    return result


def update_entity(entity_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Update entity information"""
    kwargs["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("entities").document(entity_id).update(kwargs)
    return get_entity(entity_id)


def delete_entity(entity_id: str) -> bool:
    """Delete an entity"""
    db.collection("entities").document(entity_id).delete()
    return True


def get_entity_stats(municipality: str) -> Dict[str, Any]:
    """Get statistics for entities in a municipality"""
    entities = list_entities(municipality)
    
    stats = {
        "total": len(entities),
        "by_type": {},
        "by_status": {},
        "offices": 0,
        "banks": 0,
        "units": 0
    }
    
    for entity in entities:
        entity_type = entity.get("type", "OFFICE")
        status = entity.get("status", "ACTIVE")
        
        # Count by type
        stats["by_type"][entity_type] = stats["by_type"].get(entity_type, 0) + 1
        
        # Count by status
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        # Quick counts
        if entity_type == "OFFICE":
            stats["offices"] += 1
        elif entity_type == "BANK":
            stats["banks"] += 1
        elif entity_type == "UNIT":
            stats["units"] += 1
    
    return stats

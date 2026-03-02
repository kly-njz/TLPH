"""COA (Chart of Accounts) Management for Municipal Scope"""
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from typing import Optional, List, Dict, Any

db = firestore.client()

# ==================== TEMPLATES ====================

def add_coa_template(municipality: str, name: str, description: str = "", status: str = "active") -> Dict[str, Any]:
    """Add a new COA template for a municipality"""
    doc_id = f"{municipality}_{name.lower().replace(' ', '_')}"
    data = {
        "id": doc_id,
        "municipality": municipality,
        "name": name,
        "description": description,
        "status": status,
        "account_count": 0,
        "locked_count": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    db.collection("coa_templates").document(doc_id).set(data)
    return {"id": doc_id, **data}

def get_coa_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific COA template"""
    doc = db.collection("coa_templates").document(template_id).get()
    return doc.to_dict() if doc.exists else None

def list_coa_templates(municipality: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all COA templates, optionally filtered by municipality"""
    query = db.collection("coa_templates")
    if municipality:
        query = query.where("municipality", "==", municipality)
    
    docs = query.stream()
    return [doc.to_dict() for doc in docs]

def update_coa_template(template_id: str, **kwargs) -> Dict[str, Any]:
    """Update COA template metadata"""
    kwargs["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("coa_templates").document(template_id).update(kwargs)
    return get_coa_template(template_id)

def delete_coa_template(template_id: str) -> bool:
    """Delete a COA template and all its accounts"""
    # Delete all accounts in this template
    accounts = db.collection("coa_accounts").where("template_id", "==", template_id).stream()
    for doc in accounts:
        db.collection("coa_accounts").document(doc.id).delete()
    
    # Delete template
    db.collection("coa_templates").document(template_id).delete()
    return True

# ==================== ACCOUNTS ====================

def add_coa_account(template_id: str, code: str, name: str, account_type: str, 
                   locked: bool = False, description: str = "") -> Dict[str, Any]:
    """Add an account to a COA template"""
    doc_id = f"{template_id}_{code}"
    data = {
        "id": doc_id,
        "template_id": template_id,
        "code": code,
        "name": name,
        "account_type": account_type.lower(),
        "locked": locked,
        "description": description,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    db.collection("coa_accounts").document(doc_id).set(data)
    
    # Update template account count
    template = get_coa_template(template_id)
    if template:
        locked_count = 1 if locked else 0
        update_coa_template(template_id,
                           account_count=firestore.Increment(1),
                           locked_count=firestore.Increment(locked_count))
    
    return {"id": doc_id, **data}

def get_coa_account(account_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific COA account"""
    doc = db.collection("coa_accounts").document(account_id).get()
    return doc.to_dict() if doc.exists else None

def list_coa_accounts(template_id: str, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all accounts in a COA template, optionally filtered by type"""
    query = db.collection("coa_accounts").where("template_id", "==", template_id)
    if account_type:
        query = query.where("account_type", "==", account_type.lower())
    
    docs = query.order_by("code").stream()
    return [doc.to_dict() for doc in docs]

def update_coa_account(account_id: str, **kwargs) -> Dict[str, Any]:
    """Update a COA account"""
    kwargs["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("coa_accounts").document(account_id).update(kwargs)
    return get_coa_account(account_id)

def delete_coa_account(account_id: str) -> bool:
    """Delete a COA account"""
    db.collection("coa_accounts").document(account_id).delete()
    return True

# ==================== SEED & UTILITY ====================

def seed_sample_templates():
    """Seed sample COA templates for municipalities"""
    templates = [
        {
            "code": "STD",
            "name": "Municipal Standard v1.0",
            "description": "Default municipal master chart of accounts"
        },
        {
            "code": "EXT",
            "name": "Municipal Extended",
            "description": "Expanded version with additional sub-accounts"
        }
    ]
    
    for tmpl in templates:
        template_id = f"municipality_{tmpl['code'].lower()}"
        add_coa_template("municipality", tmpl["name"], tmpl["description"], "active")
    
    # Add sample accounts to Standard template
    standard_template = "municipality_std"
    accounts = [
        # Assets
        ("1001", "Cash on Hand", "asset"),
        ("1005", "Cash in Bank", "asset"),
        ("1010", "Petty Cash", "asset"),
        ("1100", "Accounts Receivable - Local", "asset"),
        ("1200", "Office Equipment", "asset"),
        ("1210", "Accumulated Depreciation - Equipment", "asset"),
        ("1300", "Land", "asset"),
        ("1400", "Building", "asset"),
        ("1410", "Accumulated Depreciation - Building", "asset"),
        
        # Liabilities
        ("2001", "Accounts Payable", "liability"),
        ("2100", "Interest Payable", "liability"),
        ("2200", "Lease Obligations", "liability"),
        
        # Equity
        ("3001", "Municipal Capital", "equity"),
        ("3100", "Retained Earnings", "equity"),
        
        # Revenue
        ("4001", "Local Revenue - Fees", "revenue"),
        ("4010", "Business Permit Fees", "revenue"),
        ("4050", "Regulatory Fees", "revenue"),
        ("4100", "Local Revenue - Tax", "revenue"),
        ("4110", "Real Property Tax", "revenue"),
        ("4130", "Business Tax", "revenue"),
        
        # Expenses
        ("5001", "Personnel Services", "expense"),
        ("5010", "Salaries and Wages", "expense"),
        ("5020", "Office Supplies", "expense"),
        ("5030", "Travel Expenses", "expense"),
        ("5040", "Utilities", "expense"),
        ("5050", "Maintenance and Repairs", "expense"),
        ("5060", "Professional Services", "expense"),
    ]
    
    for code, name, acct_type in accounts:
        locked = code in ["1001", "3001", "4001", "5001"]  # Lock some accounts
        add_coa_account(standard_template, code, name, acct_type, locked)
    
    print("Added 2 sample COA templates with 27 accounts")

def clear_all_coa():
    """Clear all COA templates and accounts"""
    # Delete all accounts
    accounts = db.collection("coa_accounts").stream()
    for doc in accounts:
        db.collection("coa_accounts").document(doc.id).delete()
    
    # Delete all templates
    templates = db.collection("coa_templates").stream()
    for doc in templates:
        db.collection("coa_templates").document(doc.id).delete()
    
    print("Cleared all COA templates and accounts")

# ==================== CLI ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py coa_storage.py seed                     - Add sample COA templates & accounts")
        print("  py coa_storage.py clear                    - Clear all COA data")
        print("  py coa_storage.py list_templates           - List all templates")
        print("  py coa_storage.py list_accounts <tmpl_id>  - List accounts in template")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "seed":
        seed_sample_templates()
    elif cmd == "clear":
        clear_all_coa()
    elif cmd == "list_templates":
        templates = list_coa_templates()
        for t in templates:
            print(f"  {t.get('name')} ({t.get('id')}): {t.get('account_count')} accounts")
    elif cmd == "list_accounts" and len(sys.argv) > 2:
        template_id = sys.argv[2]
        accounts = list_coa_accounts(template_id)
        for a in accounts:
            status = "LOCKED" if a.get('locked') else "Editable"
            print(f"  {a.get('code')} - {a.get('name')} ({a.get('account_type')}) [{status}]")

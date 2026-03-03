from flask import Blueprint, jsonify, request, session
from firebase_auth_middleware import role_required
from transaction_storage import get_all_transactions
from firebase_config import get_firestore_db
from firebase_admin import firestore
import deposit_storage
import expense_storage
import coa_storage
import entities_storage
import system_logs_storage

bp = Blueprint('municipal_api', __name__, url_prefix='/api/municipal')


def _normalize_scope(value):
    return ' '.join(str(value or '').strip().lower().split())


def _resolve_user_municipality_by_email(email):
    if not email:
        return None
    try:
        db = get_firestore_db()
        docs = db.collection('users').where('email', '==', email).limit(1).stream()
        for doc in docs:
            user_data = doc.to_dict() or {}
            municipality = user_data.get('municipality') or user_data.get('municipality_name')
            if municipality:
                return municipality
    except Exception as e:
        print(f"[WARN] Could not resolve user municipality by email: {e}")
    return None


def _resolve_municipality_from_user_context():
    """Resolve municipality - ALWAYS fetch from users collection in Firestore, never rely on session"""
    print(f"\n[DEBUG] _resolve_municipality_from_user_context starting")
    print(f"[DEBUG] Session user_id: {session.get('user_id')}")
    print(f"[DEBUG] Session user_email: {session.get('user_email')}")
    
    try:
        db = get_firestore_db()
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        # PRIMARY: Try user_id first (most reliable)
        if user_id:
            print(f"[DEBUG] Looking up user document by user_id: {user_id}")
            try:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    print(f"[DEBUG] Found user document by user_id")
                    print(f"[DEBUG] User document municipality field: {user_data.get('municipality')}")
                    
                    municipality = user_data.get('municipality') or user_data.get('municipality_name')
                    if municipality:
                        municipality = str(municipality).strip()
                        print(f"[DEBUG] ✓ RESOLVED municipality from user_id: '{municipality}'")
                        return municipality
                    else:
                        print(f"[ERROR] User document has no municipality field!")
                else:
                    print(f"[ERROR] User document does not exist for user_id: {user_id}")
            except Exception as e:
                print(f"[ERROR] Error looking up user_id: {e}")

        # FALLBACK: Try user_email (if user_id failed)
        if user_email:
            print(f"[DEBUG] Looking up user document by user_email: {user_email}")
            try:
                query = db.collection('users').where('email', '==', user_email).limit(1)
                docs = list(query.stream())
                
                if docs:
                    user_data = docs[0].to_dict() or {}
                    print(f"[DEBUG] Found user document by user_email")
                    print(f"[DEBUG] User document municipality field: {user_data.get('municipality')}")
                    
                    municipality = user_data.get('municipality') or user_data.get('municipality_name')
                    if municipality:
                        municipality = str(municipality).strip()
                        print(f"[DEBUG] ✓ RESOLVED municipality from user_email: '{municipality}'")
                        return municipality
                    else:
                        print(f"[ERROR] User document has no municipality field!")
                else:
                    print(f"[ERROR] No user document found for email: {user_email}")
            except Exception as e:
                print(f"[ERROR] Error looking up user_email: {e}")
        
        print(f"[ERROR] Could not resolve municipality - no valid user_id or user_email in session")
        return None
        
    except Exception as e:
        print(f"[ERROR] Critical error in municipality resolution: {e}")
        import traceback
        traceback.print_exc()
        return None


def _get_current_municipality_scope():
    return _resolve_municipality_from_user_context() or (
        session.get('municipality')
        or session.get('user_municipality')
        or request.args.get('municipality')
        or None
    )

@bp.route('/logs/audit-logs-municipal', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_logs_audit_logs_municipal():
    """
    Returns all payment and fund transfer transactions for audit logs (municipal).
    """
    db = get_firestore_db()
    # Get all payment transactions
    transactions = get_all_transactions()
    # Get all fund transfer logs
    fund_transfers = []
    try:
        docs = db.collection('municipal_fund_distribution').order_by('created_at', direction=2).stream()
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            fund_transfers.append(d)
    except Exception as e:
        print(f"[ERROR] Fetching fund transfers: {e}")
    # Combine and tag logs
    logs = []
    for t in transactions:
        logs.append({
            'id': t.get('id'),
            'ts': t.get('created_at'),
            'user': t.get('user_email', '—'),
            'role': 'User',
            'module': 'PAYMENTS',
            'action': t.get('status', '—').upper(),
            'target': t.get('transaction_name', t.get('description', 'Payment')),
            'targetId': t.get('invoice_id', t.get('external_id', '')),
            'ip': t.get('ip', ''),
            'outcome': 'SUCCESS' if t.get('status', '').upper() == 'PAID' else ('FAIL' if t.get('status', '').upper() == 'FAILED' else 'WARN'),
            'message': t.get('description', ''),
            'diff': t
        })
    for f in fund_transfers:
        logs.append({
            'id': f.get('id'),
            'ts': f.get('created_at'),
            'user': f.get('initiated_by', 'Regional Office'),
            'role': 'Regional',
            'module': 'FUND_TRANSFER',
            'action': f.get('status', '—').upper(),
            'target': f.get('target_municipality', ''),
            'targetId': f.get('reference', ''),
            'ip': '',
            'outcome': 'SUCCESS' if f.get('status', '').upper() == 'COMPLETED' else ('FAIL' if f.get('status', '').upper() == 'FAILED' else 'WARN'),
            'message': f.get('description', ''),
            'diff': f
        })
    # Sort by timestamp desc
    logs = [l for l in logs if l['ts']]  # filter missing ts
    logs.sort(key=lambda x: x['ts'], reverse=True)
    return jsonify({'logs': logs})

@bp.route('/logs/financial-logs', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_logs_financial_logs():
    """Get financial logs for audit display — filtered by the admin's municipality"""
    try:
        db = firestore.client()

        # Resolve admin's municipality scope from Firestore
        municipality_scope = _resolve_municipality_from_user_context()
        print(f"[DEBUG] api_logs_financial_logs - municipality_scope: '{municipality_scope}'")

        # Build a set of user emails that belong to this municipality (for payment filtering)
        emails_in_scope = set()
        if municipality_scope:
            try:
                users_snap = db.collection('users').where('municipality', '==', municipality_scope).stream()
                for u in users_snap:
                    email = (u.to_dict() or {}).get('email', '')
                    if email:
                        emails_in_scope.add(email.strip().lower())
                print(f"[DEBUG] Found {len(emails_in_scope)} user emails in municipality '{municipality_scope}'")
            except Exception as e:
                print(f"[WARN] Could not build email scope set: {e}")

        logs = []

        # Fetch payment transactions — filter to current municipality's users
        try:
            all_transactions = get_all_transactions()
            print(f"[DEBUG] Found {len(all_transactions)} transactions total")

            for t in all_transactions:
                t_email = (t.get('user_email') or '').strip().lower()
                # If we have a scope, only include transactions from users in this municipality
                if municipality_scope and emails_in_scope and t_email not in emails_in_scope:
                    continue
                logs.append({
                    'id': t.get('id'),
                    'ts': t.get('created_at'),
                    'user': t.get('user_email', '—'),
                    'role': 'User',
                    'module': 'PAYMENTS',
                    'action': t.get('status', '—').upper(),
                    'target': t.get('transaction_name', t.get('description', 'Payment')),
                    'targetId': t.get('invoice_id', t.get('external_id', '')),
                    'device_type': t.get('device_type', ''),
                    'ip': t.get('ip', ''),
                    'outcome': 'SUCCESS' if (t.get('status', '').upper() == 'PAID') else ('FAIL' if t.get('status', '').upper() == 'FAILED' else 'WARN'),
                    'message': t.get('description', ''),
                    'diff': t
                })
        except Exception as e:
            print(f"[ERROR] Fetching transactions: {e}")

        # Fetch fund transfers — only include transfers targeted at this municipality
        try:
            fund_query = db.collection('municipal_fund_distribution')
            if municipality_scope:
                fund_query = fund_query.where('target_municipality', '==', municipality_scope)
            docs = fund_query.stream()
            for doc in docs:
                d = doc.to_dict()
                d['id'] = doc.id
                logs.append({
                    'id': d.get('id'),
                    'ts': d.get('created_at'),
                    'user': d.get('initiated_by', 'Regional Office'),
                    'role': 'Regional',
                    'module': 'FUND_TRANSFER',
                    'action': d.get('status', '—').upper(),
                    'target': d.get('target_municipality', ''),
                    'targetId': d.get('reference', ''),
                    'ip': '',
                    'outcome': 'SUCCESS' if d.get('status', '').upper() == 'COMPLETED' else ('FAIL' if d.get('status', '').upper() == 'FAILED' else 'WARN'),
                    'message': d.get('description', ''),
                    'diff': d
                })
        except Exception as e:
            print(f"[ERROR] Fetching fund transfers: {e}")

        print(f"[DEBUG] Final financial logs count after municipality filter: {len(logs)}")

        # Sort by timestamp descending
        logs = [l for l in logs if l['ts']]
        logs.sort(key=lambda x: x['ts'], reverse=True)

        return jsonify({'logs': logs, 'municipality': municipality_scope}), 200
    except Exception as e:
        print(f"[ERROR] Getting financial logs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'logs': []}), 200

@bp.route('/deposits', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_deposits():
    """Get all deposit categories for the municipal admin - FILTERED BY MUNICIPALITY SCOPE"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            print(f"[ERROR] Could not resolve municipality for deposits")
            return jsonify({'status': 'error', 'message': 'Could not determine your municipality', 'categories': []}), 403
        
        # ALWAYS use municipality from session scope, not from request params
        print(f"[DEBUG] api_get_deposits - fetching for municipality: '{municipality_scope}'")
        categories = deposit_storage.get_all_deposit_categories(municipality_scope)
        
        # Calculate stats
        total_categories = len(categories)
        active_categories = len([c for c in categories if c.get('status') == 'ACTIVE'])
        
        return jsonify({
            'status': 'success',
            'categories': categories,
            'stats': {
                'total': total_categories,
                'active': active_categories
            }
        }), 200
    except Exception as e:
        print(f"[ERROR] Fetching deposits: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'categories': [], 'stats': {'total': 0, 'active': 0}}), 500

@bp.route('/deposits', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_add_deposit():
    """Add a new deposit category"""
    try:
        data = request.get_json()
        result = deposit_storage.add_deposit_category(
            name=data.get('name'),
            coa_code=data.get('coa_code'),
            coa_name=data.get('coa_name'),
            revenue_type=data.get('revenue_type'),
            tax_type=data.get('tax_type'),
            tax_rate=data.get('tax_rate'),
            budget_code=data.get('budget_code'),
            fund_type=data.get('fund_type'),
            status=data.get('status'),
            description=data.get('description'),
            municipality=data.get('municipality')
        )
        return jsonify({'status': 'success', 'category': result}), 201
    except Exception as e:
        print(f"[ERROR] Adding deposit: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/deposits/<category_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def api_delete_deposit(category_id):
    """Delete a deposit category"""
    try:
        result = deposit_storage.delete_deposit_category(category_id)
        if result:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete'}), 500
    except Exception as e:
        print(f"[ERROR] Deleting deposit: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/expenses', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_expenses():
    """Get all expense categories for the municipal admin - FILTERED BY MUNICIPALITY SCOPE"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            print(f"[ERROR] Could not resolve municipality for expenses")
            return jsonify({'status': 'error', 'message': 'Could not determine your municipality', 'categories': []}), 403
        
        # ALWAYS use municipality from session scope, not from request params
        print(f"[DEBUG] api_get_expenses - fetching for municipality: '{municipality_scope}'")
        categories = expense_storage.get_all_expense_categories(municipality_scope)
        
        # Calculate stats
        total_categories = len(categories)
        active_categories = len([c for c in categories if c.get('status') == 'ACTIVE'])
        
        return jsonify({
            'status': 'success',
            'categories': categories,
            'stats': {
                'total': total_categories,
                'active': active_categories
            }
        }), 200
    except Exception as e:
        print(f"[ERROR] Fetching expenses: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'categories': [], 'stats': {'total': 0, 'active': 0}}), 500

@bp.route('/expenses', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_add_expense():
    """Add a new expense category"""
    try:
        data = request.get_json()
        result = expense_storage.add_expense_category(
            name=data.get('name'),
            coa_code=data.get('coa_code'),
            coa_name=data.get('coa_name'),
            expense_type=data.get('expense_type'),
            office=data.get('office'),
            budget_code=data.get('budget_code'),
            fund_type=data.get('fund_type'),
            status=data.get('status'),
            description=data.get('description'),
            municipality=data.get('municipality')
        )
        return jsonify({'status': 'success', 'category': result}), 201
    except Exception as e:
        print(f"[ERROR] Adding expense: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/expenses/<category_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def api_delete_expense(category_id):
    """Delete an expense category"""
    try:
        result = expense_storage.delete_expense_category(category_id)
        if result:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete'}), 500
    except Exception as e:
        print(f"[ERROR] Deleting expense: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ==================== COA TEMPLATES ====================

@bp.route('/coa/templates', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_coa_templates():
    """Get COA templates for municipality"""
    try:
        municipality_scope = _get_current_municipality_scope()
        templates = coa_storage.list_coa_templates(municipality_scope)
        return jsonify({
            'status': 'success',
            'templates': templates,
            'count': len(templates)
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting COA templates: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/coa/templates', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_create_coa_template():
    """Create a new COA template"""
    try:
        data = request.get_json()
        municipality_scope = _get_current_municipality_scope()
        result = coa_storage.add_coa_template(
            municipality=municipality_scope,
            name=data.get('name'),
            description=data.get('description', ''),
            status=data.get('status', 'active')
        )
        return jsonify({'status': 'success', 'template': result}), 201
    except Exception as e:
        print(f"[ERROR] Creating COA template: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== COA ACCOUNTS ====================

@bp.route('/coa/accounts/<template_id>', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_coa_accounts(template_id):
    """Get all accounts in a COA template"""
    try:
        municipality_scope = _get_current_municipality_scope()
        template = coa_storage.get_coa_template(template_id)
        if not template or template.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Template not found in municipality scope'}), 404

        accounts = coa_storage.list_coa_accounts(template_id)
        
        # Calculate stats
        locked_count = sum(1 for a in accounts if a.get('locked'))
        type_counts = {}
        for a in accounts:
            atype = a.get('account_type', 'unknown')
            type_counts[atype] = type_counts.get(atype, 0) + 1
        
        return jsonify({
            'status': 'success',
            'accounts': accounts,
            'stats': {
                'total': len(accounts),
                'locked': locked_count,
                'editable': len(accounts) - locked_count,
                'by_type': type_counts
            }
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting COA accounts: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/coa/accounts/<template_id>', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_add_coa_account(template_id):
    """Add an account to a COA template"""
    try:
        municipality_scope = _get_current_municipality_scope()
        template = coa_storage.get_coa_template(template_id)
        if not template or template.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Template not found in municipality scope'}), 404

        data = request.get_json()
        result = coa_storage.add_coa_account(
            template_id=template_id,
            code=data.get('code'),
            name=data.get('name'),
            account_type=data.get('account_type'),
            locked=data.get('locked', False),
            description=data.get('description', '')
        )
        return jsonify({'status': 'success', 'account': result}), 201
    except Exception as e:
        print(f"[ERROR] Adding COA account: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/coa/accounts/<account_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def api_delete_coa_account(account_id):
    """Delete a COA account"""
    try:
        municipality_scope = _get_current_municipality_scope()
        account = coa_storage.get_coa_account(account_id)
        if not account:
            return jsonify({'status': 'error', 'message': 'Account not found'}), 404

        template = coa_storage.get_coa_template(account.get('template_id'))
        if not template or template.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Account not found in municipality scope'}), 404

        result = coa_storage.delete_coa_account(account_id)
        if result:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete'}), 500
    except Exception as e:
        print(f"[ERROR] Deleting COA account: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ENTITIES API ====================

@bp.route('/entities', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_entities():
    """Get all entities for the municipality"""
    try:
        municipality_scope = _get_current_municipality_scope()
        entities = entities_storage.list_entities(municipality_scope)
        stats = entities_storage.get_entity_stats(municipality_scope)
        return jsonify({
            'status': 'success',
            'entities': entities,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting entities: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/entities', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_create_entity():
    """Create a new entity"""
    try:
        municipality_scope = _get_current_municipality_scope()
        data = request.get_json()
        
        result = entities_storage.add_entity(
            municipality=municipality_scope,
            name=data.get('name'),
            entity_type=data.get('type'),
            office_or_unit=data.get('office_or_unit', ''),
            bank_account=data.get('bank_account', ''),
            status=data.get('status', 'ACTIVE')
        )
        return jsonify({'status': 'success', 'entity': result}), 201
    except Exception as e:
        print(f"[ERROR] Creating entity: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@bp.route('/entities/<entity_id>', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_entity(entity_id):
    """Get a specific entity"""
    try:
        municipality_scope = _get_current_municipality_scope()
        entity = entities_storage.get_entity(entity_id)
        
        if not entity or entity.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Entity not found'}), 404
        
        return jsonify({'status': 'success', 'entity': entity}), 200
    except Exception as e:
        print(f"[ERROR] Getting entity: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/entities/<entity_id>', methods=['PUT'])
@role_required('municipal','municipal_admin')
def api_update_entity(entity_id):
    """Update an entity"""
    try:
        municipality_scope = _get_current_municipality_scope()
        entity = entities_storage.get_entity(entity_id)
        
        if not entity or entity.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Entity not found'}), 404
        
        data = request.get_json()
        update_fields = {}
        
        if 'name' in data:
            update_fields['name'] = data['name']
        if 'type' in data:
            update_fields['type'] = data['type']
        if 'office_or_unit' in data:
            update_fields['office_or_unit'] = data['office_or_unit']
        if 'bank_account' in data:
            update_fields['bank_account'] = data['bank_account']
        if 'status' in data:
            update_fields['status'] = data['status']
        
        result = entities_storage.update_entity(entity_id, **update_fields)
        return jsonify({'status': 'success', 'entity': result}), 200
    except Exception as e:
        print(f"[ERROR] Updating entity: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/entities/<entity_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def api_delete_entity(entity_id):
    """Delete an entity"""
    try:
        municipality_scope = _get_current_municipality_scope()
        entity = entities_storage.get_entity(entity_id)
        
        if not entity or entity.get('municipality') != municipality_scope:
            return jsonify({'status': 'error', 'message': 'Entity not found'}), 404
        
        result = entities_storage.delete_entity(entity_id)
        if result:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete'}), 500
    except Exception as e:
        print(f"[ERROR] Deleting entity: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== SYSTEM LOGS API ====================

@bp.route('/system-logs', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_system_logs():
    """Get system logs for the municipality - FETCHES FROM USER'S MUNICIPALITY FIELD"""
    try:
        # Get municipality DIRECTLY from user's document
        municipality_scope = _resolve_municipality_from_user_context()
        current_user_email = session.get('user_email', '').lower()
        
        print(f"\n[DEBUG] ===== api_get_system_logs START =====")
        print(f"[DEBUG] Current user email: '{current_user_email}'")
        print(f"[DEBUG] Resolved municipality from user document: '{municipality_scope}'")

        if not municipality_scope:
            print(f"[ERROR] Could not resolve municipality from user document for {current_user_email}")
            return jsonify({'status': 'error', 'message': 'Could not determine your municipality'}), 403

        logs = []
        
        # Fetch logs by municipality from Firestore
        print(f"[DEBUG] Fetching system logs from Firestore for municipality: '{municipality_scope}'")
        logs = system_logs_storage.list_system_logs(municipality_scope, limit=500)
        print(f"[DEBUG] Firestore returned {len(logs)} logs")

        # CRITICAL: Validate all returned logs match the exact municipality
        # This prevents any cross-municipality data leakage
        final_logs = []
        filtered_out = 0
        
        for i, log in enumerate(logs):
            log_municipality = log.get('municipality', '')
            
            # Exact string comparison (after stripping whitespace)
            if log_municipality.strip() == municipality_scope.strip():
                final_logs.append(log)
                print(f"[DEBUG] Log {i+1}: ✓ VALID municipality '{log_municipality}'")
            else:
                filtered_out += 1
                print(f"[WARN] Log {i+1}: ✗ INVALID municipality '{log_municipality}' (expected '{municipality_scope}')")
        
        print(f"[DEBUG] Final validation: {len(final_logs)} valid logs, {filtered_out} filtered out")
        print(f"[DEBUG] ===== api_get_system_logs END =====\n")

        # Build stats from validated logs only
        stats = {
            'total': len(final_logs),
            'by_action': {},
            'by_outcome': {},
            'by_device': {},
            'by_module': {},
            'logins_24h': 0,
            'approvals_72h': 0
        }

        for log in final_logs:
            action = log.get('action', 'UNKNOWN')
            outcome = log.get('outcome', 'UNKNOWN')
            device = log.get('device_type', 'Unknown')
            module = log.get('module', 'UNKNOWN')
            stats['by_action'][action] = stats['by_action'].get(action, 0) + 1
            stats['by_outcome'][outcome] = stats['by_outcome'].get(outcome, 0) + 1
            stats['by_device'][device] = stats['by_device'].get(device, 0) + 1
            stats['by_module'][module] = stats['by_module'].get(module, 0) + 1

            if action == 'LOGIN':
                stats['logins_24h'] += 1
            if action == 'APPROVE':
                stats['approvals_72h'] += 1

        return jsonify({
            'status': 'success',
            'municipality': municipality_scope,
            'logs': final_logs,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting system logs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/system-logs', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_create_system_log():
    """Create a system log entry"""
    try:
        municipality_scope = _get_current_municipality_scope()
        data = request.get_json()
        user_agent = request.headers.get('User-Agent', '')
        device_type = system_logs_storage.detect_device_type(user_agent)
        
        result = system_logs_storage.add_system_log(
            municipality=municipality_scope,
            user=data.get('user', 'Unknown'),
            action=data.get('action', 'UNKNOWN'),
            target=data.get('target', ''),
            target_id=data.get('target_id', ''),
            module=data.get('module', 'SYSTEM'),
            outcome=data.get('outcome', 'SUCCESS'),
            message=data.get('message', ''),
            device_type=device_type,
            user_agent=user_agent,
            metadata=data.get('metadata', {})
        )
        return jsonify({'status': 'success', 'log': result}), 201
    except Exception as e:
        print(f"[ERROR] Creating system log: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@bp.route('/system-logs/<action>', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_system_logs_by_action(action):
    """Get system logs filtered by action (e.g., LOGIN, APPROVE)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        logs = system_logs_storage.list_system_logs_by_action(
            municipality_scope,
            action,
            limit=100
        )
        return jsonify({
            'status': 'success',
            'action': action,
            'logs': logs,
            'count': len(logs)
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting system logs by action: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
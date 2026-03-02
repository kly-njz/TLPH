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
    municipality = session.get('municipality') or session.get('user_municipality')
    print(f"[DEBUG] _resolve_municipality_from_user_context - session value: '{municipality}'")
    if municipality and str(municipality).lower() not in ('unknown', 'municipality', ''):
        print(f"[DEBUG] Using session municipality: '{municipality}'")
        return municipality

    try:
        db = get_firestore_db()
        user_id = session.get('user_id')
        if user_id:
            print(f"[DEBUG] Looking up user_id: {user_id}")
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    print(f"[DEBUG] Found municipality from user_id: '{municipality}'")
                    session['municipality'] = municipality
                    session['user_municipality'] = municipality
                    return municipality

        user_email = session.get('user_email')
        if user_email:
            print(f"[DEBUG] Looking up user_email: {user_email}")
            docs = db.collection('users').where('email', '==', user_email).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    print(f"[DEBUG] Found municipality from user_email: '{municipality}'")
                    session['municipality'] = municipality
                    session['user_municipality'] = municipality
                    return municipality
    except Exception as e:
        print(f"[WARN] Could not resolve municipality from user context: {e}")

    print(f"[DEBUG] Could not resolve municipality from context")
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
    db = firestore.client()
    logs = []
    try:
        docs = db.collection('financial_logs').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        for doc in docs:
            log = doc.to_dict()
            log['id'] = doc.id
            # Map Firestore fields to frontend audit log fields
            logs.append({
                'id': log.get('id'),
                'ts': log.get('created_at'),
                'user': log.get('user_email', '—'),
                'role': 'User',
                'module': 'PAYMENTS',
                'action': (log.get('status') or '').upper(),
                'target': log.get('transaction_name', log.get('description', 'Payment')),
                'targetId': log.get('invoice_id', log.get('external_id', '')),
                'device_type': log.get('device_type', ''),
                'ip': '',
                'outcome': 'SUCCESS' if (log.get('status', '').upper() == 'PAID') else ('FAIL' if log.get('status', '').upper() == 'FAILED' else 'WARN'),
                'message': log.get('description', ''),
                'diff': log
            })
    except Exception as e:
        print(f"[ERROR] Fetching financial logs: {e}")
    return jsonify({'logs': logs})

@bp.route('/deposits', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_deposits():
    """Get all deposit categories for the municipal admin"""
    try:
        # You can filter by municipality if needed
        municipality = request.args.get('municipality')
        categories = deposit_storage.get_all_deposit_categories(municipality)
        
        # Calculate stats
        total_categories = len(categories)
        active_categories = len([c for c in categories if c.get('status') == 'ACTIVE'])
        
        return jsonify({
            'categories': categories,
            'stats': {
                'total': total_categories,
                'active': active_categories
            }
        })
    except Exception as e:
        print(f"[ERROR] Fetching deposits: {e}")
        return jsonify({'categories': [], 'stats': {'total': 0, 'active': 0}}), 500

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
    """Get all expense categories for the municipal admin"""
    try:
        # You can filter by municipality if needed
        municipality = request.args.get('municipality')
        categories = expense_storage.get_all_expense_categories(municipality)
        
        # Calculate stats
        total_categories = len(categories)
        active_categories = len([c for c in categories if c.get('status') == 'ACTIVE'])
        
        return jsonify({
            'categories': categories,
            'stats': {
                'total': total_categories,
                'active': active_categories
            }
        })
    except Exception as e:
        print(f"[ERROR] Fetching expenses: {e}")
        return jsonify({'categories': [], 'stats': {'total': 0, 'active': 0}}), 500

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
    """Get system logs for the municipality"""
    try:
        municipality_scope = _get_current_municipality_scope()
        current_user_email = session.get('user_email', '').lower()
        
        print(f"\n[DEBUG] api_get_system_logs - municipality_scope: '{municipality_scope}', user_email: '{current_user_email}'")

        logs = []
        
        # Primary: Try direct municipality query
        if municipality_scope:
            logs = system_logs_storage.list_system_logs(municipality_scope, limit=500)
            print(f"[DEBUG] Direct query returned {len(logs)} logs")

        # Fallback #1: If no logs found, get ALL logs and filter by current user's email
        # This ensures users always see their own logs even if municipality is mismatched
        if not logs and current_user_email:
            print(f"[DEBUG] Direct query failed, getting logs for current user: {current_user_email}")
            all_logs = system_logs_storage.list_system_logs(None, limit=2000)
            logs = [
                log for log in all_logs
                if (log.get('user') or '').lower() == current_user_email
            ][:500]
            print(f"[DEBUG] User-filtered query found {len(logs)} logs")

        # Fallback #2: If still no logs, try normalized municipality match
        if not logs and municipality_scope:
            all_logs = system_logs_storage.list_system_logs(None, limit=2000)
            scope_norm = _normalize_scope(municipality_scope)
            print(f"[DEBUG] Trying fallback #2 - normalized scope: '{scope_norm}'")
            print(f"[DEBUG] Checking {len(all_logs)} total logs for normalized match")
            logs = [
                log for log in all_logs
                if _normalize_scope(log.get('municipality')) == scope_norm
            ][:500]
            print(f"[DEBUG] Normalized match found {len(logs)} logs")

        # Build stats from returned logs to avoid additional scope/index issues.
        stats = {
            'total': len(logs),
            'by_action': {},
            'by_outcome': {},
            'by_device': {},
            'by_module': {},
            'logins_24h': 0,
            'approvals_72h': 0
        }

        for log in logs:
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
            'logs': logs,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"[ERROR] Getting system logs: {e}")
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
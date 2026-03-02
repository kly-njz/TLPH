from flask import Blueprint, jsonify, request
from firebase_auth_middleware import role_required
from transaction_storage import get_all_transactions
from firebase_config import get_firestore_db
from firebase_admin import firestore
import deposit_storage
import expense_storage

bp = Blueprint('municipal_api', __name__, url_prefix='/api/municipal')

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

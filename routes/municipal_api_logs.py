from flask import Blueprint, jsonify, request
from firebase_auth_middleware import role_required
from transaction_storage import get_all_transactions
from firebase_config import get_firestore_db
from firebase_admin import firestore

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

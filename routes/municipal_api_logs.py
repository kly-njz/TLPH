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


REGION_MAPPING = {
    'MIMAROPA': 'REGION-IV-B',
    'CALABARZON': 'REGION-IV-A',
    'BICOL': 'REGION-V',
    'WESTERN-VISAYAS': 'REGION-VI',
    'EASTERN-VISAYAS': 'REGION-VIII',
    'CENTRAL-VISAYAS': 'REGION-VII',
    'DAVAO': 'REGION-XI',
    'SOCCSKSARGEN': 'REGION-XII',
    'ZAMBOANGA': 'REGION-IX',
    'CARAGA': 'REGION-XIII',
    'CORDILLERA': 'CAR',
    'ILOCOS': 'REGION-I',
    'CAGAYAN-VALLEY': 'REGION-II',
    'CENTRAL-LUZON': 'REGION-III',
    'NCR': 'NCR',
    'ARMM': 'REGION-BANGSAMORO'
}


def _canonical_region_name(value):
    if not value:
        return ''
    region = str(value).strip().upper()
    if region in REGION_MAPPING:
        return REGION_MAPPING[region]
    reverse_mapping = {v: k for k, v in REGION_MAPPING.items()}
    if region in reverse_mapping:
        return region
    return region


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


def _resolve_region_from_user_context():
    if session.get('region'):
        return str(session.get('region')).strip()
    if session.get('user_region'):
        return str(session.get('user_region')).strip()

    try:
        db = get_firestore_db()
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                region = user_data.get('region') or user_data.get('region_name') or user_data.get('regionName')
                if region:
                    return str(region).strip()

        if user_email:
            docs = db.collection('users').where('email', '==', user_email).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                region = user_data.get('region') or user_data.get('region_name') or user_data.get('regionName')
                if region:
                    return str(region).strip()
    except Exception as e:
        print(f"[WARN] Could not resolve user region by context: {e}")

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

                status_value = (t.get('status') or '—').upper()
                regional_approved = status_value == 'APPROVED' and (
                    str(t.get('approvedByLevel') or '').strip().lower() == 'regional'
                    or bool(t.get('approvedByRegional'))
                )
                regional_rejected = status_value == 'REJECTED' and (
                    str(t.get('rejectedByLevel') or '').strip().lower() == 'regional'
                    or bool(t.get('rejectedByRegional'))
                )
                regional_decision = 'APPROVED' if regional_approved else ('REJECTED' if regional_rejected else '')

                outcome_value = 'SUCCESS' if status_value in {'PAID', 'APPROVED', 'COMPLETED'} else (
                    'FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN'
                )

                logs.append({
                    'id': t.get('id'),
                    'ts': t.get('updated_at') or t.get('forwarded_at') or t.get('created_at'),
                    'user': t.get('user_email', '—'),
                    'role': 'User',
                    'module': 'PAYMENTS',
                    'action': status_value,
                    'target': t.get('transaction_name', t.get('description', 'Payment')),
                    'targetId': t.get('invoice_id', t.get('external_id', '')),
                    'device_type': t.get('device_type', ''),
                    'ip': t.get('ip', ''),
                    'outcome': outcome_value,
                    'message': t.get('description', ''),
                    'forwarded_message': t.get('forwarded_message') or t.get('forwardMessage') or '',
                    'regional_decision': regional_decision,
                    'regional_decision_by': t.get('regional_reviewed_by') or t.get('approvedByRegional') or t.get('rejectedByRegional') or '',
                    'regional_decision_at': t.get('regional_reviewed_at') or t.get('approvedAtRegional') or t.get('rejectedAtRegional') or '',
                    'regional_decision_note': t.get('regional_decision_note') or '',
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

@bp.route('/logs/update-status', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_update_audit_log_status():
    """Update the status (outcome) of an audit log entry"""
    try:
        data = request.get_json()
        log_id = data.get('id')
        new_status = data.get('status')
        module = data.get('module')
        request_ip = system_logs_storage.extract_request_ip(request)

        if not log_id or not new_status:
            return jsonify({'success': False, 'error': 'Missing log_id or status'}), 400

        db = get_firestore_db()

        # Determine which collection to update based on module
        if module == 'PAYMENTS':
            # Update transaction status in Firestore (transactions collection)
            try:
                tx_ref = db.collection('transactions').document(log_id)
                tx_doc = tx_ref.get()
                if not tx_doc.exists:
                    return jsonify({'success': False, 'error': 'Transaction not found'}), 404

                update_payload = {
                    'status': new_status,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'updated_by': session.get('user_email', 'system')
                }

                # If forwarded, include message and forwarding metadata
                if new_status == 'FORWARDED':
                    forward_msg = (data.get('forwardMessage') or '').strip()
                    update_payload.update({
                        'forwarded_to_region': True,
                        'forwarded_message': forward_msg,
                        'forwarded_by': session.get('user_email', 'system'),
                        'forwarded_at': firestore.SERVER_TIMESTAMP,
                        'forwarded_region': _resolve_region_from_user_context()
                    })

                tx_ref.update(update_payload)
            except Exception as e:
                print(f"[ERROR] Updating transaction status: {e}")
                return jsonify({'success': False, 'error': 'Failed to update transaction status'}), 500

        elif module == 'FUND_TRANSFER':
            # Update fund transfer status
            doc_ref = db.collection('municipal_fund_distribution').document(log_id)
            doc = doc_ref.get()
            if doc.exists:
                # Map status to the appropriate field
                status_mapping = {
                    'SUCCESS': 'COMPLETED',
                    'WARN': 'PENDING',
                    'FAIL': 'FAILED'
                }
                doc_ref.update({
                    'status': status_mapping.get(new_status, new_status),
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'updated_by': session.get('user_email', 'system')
                })
            else:
                return jsonify({'success': False, 'error': 'Fund transfer not found'}), 404
        else:
            # For other modules, create/update an audit status override
            audit_status_ref = db.collection('audit_log_status_overrides').document(log_id)
            audit_status_ref.set({
                'log_id': log_id,
                'status': new_status,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'updated_by': session.get('user_email', 'system'),
                'module': module
            }, merge=True)

        if str(new_status).strip().upper() == 'APPROVED':
            actor_email = session.get('user_email', 'system')
            actor_id = session.get('user_id', '')
            actor_role = session.get('user_role', 'municipal')
            municipality_scope = _get_current_municipality_scope() or ''
            region_scope = _resolve_region_from_user_context() or ''
            target_label = 'Transaction Approval' if module == 'PAYMENTS' else f'{module or "Audit"} Approval'

            system_logs_storage.add_regional_system_log(
                region=region_scope,
                municipality=municipality_scope,
                user=actor_email,
                user_id=actor_id,
                role=actor_role,
                action='APPROVED',
                target=target_label,
                target_id=log_id,
                module=module or 'AUDIT',
                outcome='SUCCESS',
                message=f'Municipal admin {actor_email} approved {module or "audit"} item {log_id}.',
                ip_address=request_ip,
                device_type=system_logs_storage.detect_device_type(request.headers.get('User-Agent', '')),
                user_agent=request.headers.get('User-Agent', ''),
                metadata={'status': new_status, 'source': 'municipal_api_logs.update-status'}
            )

        return jsonify({'success': True, 'message': 'Status updated successfully'}), 200

    except Exception as e:
        print(f"[ERROR] Updating audit log status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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


# =============================================
# MUNICIPAL PAYMENT DEPOSITS TRACKING
# =============================================
@bp.route('/deposits/payments', methods=['GET'])
@role_required('municipal','municipal_admin')
def api_get_municipal_payment_deposits():
    """Get all payment transactions/deposits for the municipality (from transactions collection)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        region_scope = _resolve_region_from_user_context()
        if not municipality_scope:
            return jsonify({'success': False, 'error': 'Cannot determine municipality'}), 403

        normalized_municipality_scope = _normalize_scope(municipality_scope)
        normalized_region_scope = _normalize_scope(_canonical_region_name(region_scope))
        
        print(f"[DEBUG] Fetching payment deposits for municipality: '{municipality_scope}', region: '{region_scope}'")
        
        db = get_firestore_db()
        
        # Step 1: Get all users that belong to this municipality
        user_emails = set()
        user_ids = set()
        try:
            users_docs = db.collection('users').limit(1000).stream()
            
            for user_doc in users_docs:
                user_data = user_doc.to_dict() or {}
                user_municipality = _normalize_scope(user_data.get('municipality') or user_data.get('municipality_name'))
                user_region = _normalize_scope(_canonical_region_name(
                    user_data.get('region') or user_data.get('region_name') or user_data.get('regionName')
                ))

                if user_municipality != normalized_municipality_scope:
                    continue
                if normalized_region_scope and user_region and user_region != normalized_region_scope:
                    continue

                email = user_data.get('email')
                if email:
                    user_emails.add(email.lower())

                user_ids.add(str(user_doc.id))
                for uid in [user_data.get('uid'), user_data.get('user_id'), user_data.get('userId'), user_data.get('id')]:
                    if uid:
                        user_ids.add(str(uid))
            
            print(f"[DEBUG] Found {len(user_emails)} users for municipality '{municipality_scope}' under region '{region_scope}'")
        except Exception as e:
            print(f"[WARNING] Failed to fetch municipality users: {e}")
        
        deposits = []
        paid_markers = {'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'}

        def parse_amount(raw_value):
            try:
                return float(raw_value or 0)
            except (ValueError, TypeError):
                return 0.0

        def is_paid(status_value):
            return str(status_value or '').strip().lower() in paid_markers

        def in_scope(email_value=None, user_id_value=None, muni_value=None, region_value=None):
            normalized_email = str(email_value or '').strip().lower()
            normalized_uid = str(user_id_value or '').strip()
            normalized_muni = _normalize_scope(muni_value)
            normalized_region = _normalize_scope(_canonical_region_name(region_value))

            by_user = (normalized_email in user_emails) or (normalized_uid and normalized_uid in user_ids)
            by_fields = (
                normalized_muni == normalized_municipality_scope
                and (not normalized_region_scope or not normalized_region or normalized_region == normalized_region_scope)
            )
            return by_user or by_fields

        def append_deposit(record_id, invoice_id, external_id, amount, description, payer_email, payment_method, status, created_at, paid_at, reference, source, municipality_name, region_name):
            deposits.append({
                'id': record_id,
                'transaction_type': 'Payment Deposit',
                'payment_type': 'Online Payment',
                'invoice_id': invoice_id,
                'external_id': external_id,
                'amount': amount,
                'description': description,
                'payer_email': payer_email,
                'payment_method': payment_method,
                'status': str(status or '').strip().upper(),
                'created_at': created_at,
                'paid_at': paid_at,
                'reference': reference,
                'source': source,
                'municipality': municipality_name,
                'region': region_name,
            })
        
        # Step 2: Fetch all transactions from 'transactions' collection
        try:
            all_transactions = db.collection('transactions').limit(1000).stream()
            
            transaction_count = 0
            for doc in all_transactions:
                trans = doc.to_dict()
                user_email = (trans.get('user_email') or '').lower()
                user_id = trans.get('userId') or trans.get('user_id') or trans.get('uid')

                if in_scope(
                    user_email,
                    user_id,
                    trans.get('municipality') or trans.get('municipality_name'),
                    trans.get('region') or trans.get('region_name') or trans.get('regionName')
                ):
                    status = trans.get('status') or trans.get('paymentStatus') or trans.get('payment_status')
                    paid_by_status = is_paid(status)
                    paid_by_method = bool(trans.get('payment_method')) and str(status or '').strip().lower() not in {'pending', 'failed', 'expired', 'cancelled'}
                    amount = parse_amount(trans.get('amount'))

                    if amount > 0 and (paid_by_status or paid_by_method):
                        append_deposit(
                            doc.id,
                            trans.get('invoice_id', ''),
                            trans.get('external_id', ''),
                            amount,
                            trans.get('description', trans.get('transaction_name', 'Payment')),
                            user_email,
                            trans.get('payment_method', 'Online Payment'),
                            status or 'PAID',
                            trans.get('created_at'),
                            trans.get('paid_at'),
                            trans.get('reference', trans.get('external_id', '')),
                            'transactions',
                            trans.get('municipality') or trans.get('municipality_name') or municipality_scope,
                            _canonical_region_name(trans.get('region') or trans.get('region_name') or trans.get('regionName') or region_scope)
                        )
                    transaction_count += 1
            
            print(f"[DEBUG] Loaded {transaction_count} payment deposits for municipality '{municipality_scope}'")
        except Exception as e:
            print(f"[ERROR] Failed to fetch transactions: {e}")
            import traceback
            traceback.print_exc()

        # Step 3: Merge paid applications and service requests that may not exist in transactions collection
        try:
            application_docs = db.collection('applications').limit(3000).stream()
            for doc in application_docs:
                app = doc.to_dict() or {}
                payer_email = (app.get('userEmail') or app.get('user_email') or app.get('email') or '').lower()
                app_user_id = app.get('userId') or app.get('user_id') or app.get('uid')

                if not in_scope(
                    payer_email,
                    app_user_id,
                    app.get('municipality') or app.get('municipality_name'),
                    app.get('region') or app.get('region_name') or app.get('regionName')
                ):
                    continue

                status = app.get('paymentStatus') or app.get('payment_status') or app.get('status')
                amount = parse_amount(app.get('amount') or app.get('paymentAmount') or app.get('serviceFee') or app.get('processingFee'))
                if amount <= 0 or not is_paid(status):
                    continue

                append_deposit(
                    doc.id,
                    app.get('invoiceId') or app.get('invoice_id') or app.get('externalId') or app.get('external_id') or doc.id,
                    app.get('externalId') or app.get('external_id') or '',
                    amount,
                    app.get('description') or app.get('applicationType') or app.get('permitType') or 'Application Payment',
                    payer_email,
                    app.get('paymentMethod') or app.get('payment_method') or 'Online Payment',
                    status,
                    app.get('createdAt') or app.get('created_at') or app.get('dateFiled'),
                    app.get('updatedAt') or app.get('updated_at'),
                    app.get('reference') or '',
                    'applications',
                    app.get('municipality') or app.get('municipality_name') or municipality_scope,
                    _canonical_region_name(app.get('region') or app.get('region_name') or app.get('regionName') or region_scope)
                )
        except Exception as e:
            print(f"[WARNING] Failed to merge applications payment records: {e}")

        try:
            service_docs = db.collection('service_requests').limit(3000).stream()
            for doc in service_docs:
                service = doc.to_dict() or {}
                payer_email = (service.get('userEmail') or service.get('user_email') or service.get('email') or '').lower()
                service_user_id = service.get('userId') or service.get('user_id') or service.get('uid')

                if not in_scope(
                    payer_email,
                    service_user_id,
                    service.get('municipality') or service.get('municipality_name'),
                    service.get('region') or service.get('region_name') or service.get('regionName')
                ):
                    continue

                status = service.get('paymentStatus') or service.get('payment_status') or service.get('status')
                amount = parse_amount(service.get('amount') or service.get('paymentAmount') or service.get('serviceFee') or service.get('fee'))
                if amount <= 0 or not is_paid(status):
                    continue

                append_deposit(
                    doc.id,
                    service.get('invoiceId') or service.get('invoice_id') or service.get('externalId') or service.get('external_id') or doc.id,
                    service.get('externalId') or service.get('external_id') or '',
                    amount,
                    service.get('serviceType') or service.get('description') or 'Service Payment',
                    payer_email,
                    service.get('paymentMethod') or service.get('payment_method') or 'Online Payment',
                    status,
                    service.get('createdAt') or service.get('created_at') or service.get('submittedAt'),
                    service.get('updatedAt') or service.get('updated_at'),
                    service.get('reference') or '',
                    'service_requests',
                    service.get('municipality') or service.get('municipality_name') or municipality_scope,
                    _canonical_region_name(service.get('region') or service.get('region_name') or service.get('regionName') or region_scope)
                )
        except Exception as e:
            print(f"[WARNING] Failed to merge service payment records: {e}")

        # Deduplicate by invoice/reference/id
        deduped = {}
        for row in deposits:
            dedupe_key = str(row.get('invoice_id') or row.get('reference') or row.get('id'))
            deduped[dedupe_key] = row
        deposits = list(deduped.values())
        
        # Sort by date (most recent first)
        try:
            deposits.sort(
                key=lambda x: str(x.get('created_at', '')) or '',
                reverse=True
            )
        except Exception as e:
            print(f"[WARNING] Failed to sort deposits: {e}")
        
        print(f"[DEBUG] Returning {len(deposits)} total deposits for municipality '{municipality_scope}'")
        
        return jsonify({
            'success': True,
            'municipality': municipality_scope,
            'region': region_scope,
            'deposits': deposits,
            'count': len(deposits)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Fetching municipal payment deposits: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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
        if not municipality_scope:
            return jsonify({'status': 'error', 'message': 'Municipality scope is missing'}), 400

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
        if not municipality_scope:
            return jsonify({'status': 'error', 'message': 'Municipality scope is missing'}), 400

        data = request.get_json() or {}

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


# ==================== COA TEMPLATES API (Frontend-compatible) ====================

@bp.route('/coa-templates', methods=['GET'])
def api_get_coa_templates_frontend():
    """Get all COA templates for the municipality (frontend-compatible endpoint)"""
    try:
        # Try to get municipality scope
        municipality_scope = _get_current_municipality_scope()
        
        # If no municipality scope, fetch ALL templates (for national admin)
        if not municipality_scope:
            try:
                db = get_firestore_db()
                templates = []
                print(f"[INFO] Fetching ALL COA templates from Firestore...")
                query_result = db.collection('coa_templates').stream()
                for doc in query_result:
                    data = doc.to_dict() or {}
                    templates.append({
                        'id': doc.id,
                        'name': data.get('name'),
                        'description': data.get('description', ''),
                        'status': data.get('status', 'active'),
                        'account_count': data.get('account_count', 0),
                        'municipality': data.get('municipality')
                    })
                print(f"[INFO] Fetched {len(templates)} COA templates")
                return jsonify(templates), 200
            except Exception as e:
                print(f"[ERROR] Getting all COA templates: {e}")
                import traceback
                traceback.print_exc()
                return jsonify([]), 200
        
        # Municipality-specific fetch
        templates = coa_storage.list_coa_templates(municipality_scope)
        
        # Normalize response format
        result = []
        for t in templates:
            result.append({
                'id': t.get('id'),
                'name': t.get('name'),
                'description': t.get('description', ''),
                'status': t.get('status', 'active'),
                'account_count': t.get('account_count', 0),
                'municipality': t.get('municipality')
            })
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[ERROR] Getting COA templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 200

@bp.route('/coa-templates', methods=['POST'])
def api_create_coa_template_frontend():
    """Create a new COA template (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        data = request.get_json()
        
        result = coa_storage.add_coa_template(
            municipality=municipality_scope,
            name=data.get('name'),
            description=data.get('description', ''),
            status=data.get('status', 'active')
        )
        
        return jsonify({
            'id': result.get('id'),
            'name': result.get('name'),
            'description': result.get('description'),
            'status': result.get('status'),
            'account_count': 0
        }), 201
    except Exception as e:
        print(f"[ERROR] Creating COA template: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== COA ACCOUNTS API (Frontend-compatible) ====================

@bp.route('/coa-accounts', methods=['GET'])
def api_get_coa_accounts_frontend():
    """Get COA accounts, optionally filtered by template (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        template_id = request.args.get('template')
        
        # If no municipality scope, fetch ALL accounts (for national admin)
        if not municipality_scope:
            try:
                db = get_firestore_db()
                accounts = []
                print(f"[INFO] Fetching ALL COA accounts from Firestore...")
                
                if template_id:
                    # Get accounts for specific template
                    query_result = db.collection('coa_accounts').where('template_id', '==', template_id).stream()
                    for doc in query_result:
                        data = doc.to_dict() or {}
                        accounts.append({
                            'id': doc.id,
                            'code': data.get('code'),
                            'name': data.get('name'),
                            'type': data.get('account_type', 'Asset'),
                            'locked': data.get('locked', False),
                            'description': data.get('description', '')
                        })
                else:
                    # Get all accounts
                    query_result = db.collection('coa_accounts').stream()
                    for doc in query_result:
                        data = doc.to_dict() or {}
                        accounts.append({
                            'id': doc.id,
                            'code': data.get('code'),
                            'name': data.get('name'),
                            'type': data.get('account_type', 'Asset'),
                            'locked': data.get('locked', False),
                            'description': data.get('description', '')
                        })
                print(f"[INFO] Fetched {len(accounts)} COA accounts")
                return jsonify(accounts), 200
            except Exception as e:
                print(f"[ERROR] Getting all COA accounts: {e}")
                import traceback
                traceback.print_exc()
                return jsonify([]), 200
        
        # Municipality-specific fetch
        if template_id:
            # Get accounts for specific template
            accounts = coa_storage.list_coa_accounts(template_id)
        else:
            # Get all accounts for the municipality
            templates = coa_storage.list_coa_templates(municipality_scope)
            accounts = []
            for t in templates:
                template_accounts = coa_storage.list_coa_accounts(t.get('id'))
                accounts.extend(template_accounts)
        
        # Normalize response format
        result = []
        for a in accounts:
            result.append({
                'id': a.get('id'),
                'code': a.get('code'),
                'name': a.get('name'),
                'type': a.get('account_type', 'Asset'),
                'locked': a.get('locked', False),
                'description': a.get('description', '')
            })
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[ERROR] Getting COA accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 200

@bp.route('/coa-accounts', methods=['POST'])
def api_create_coa_account_frontend():
    """Create a new COA account (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        data = request.get_json()
        
        # If no template_id provided, create a default template first
        template_id = data.get('template_id')
        if not template_id:
            # Create a default template
            templates = coa_storage.list_coa_templates(municipality_scope)
            if templates:
                template_id = templates[0].get('id')
            else:
                template = coa_storage.add_coa_template(
                    municipality=municipality_scope,
                    name=f"{municipality_scope} Default COA",
                    description="Default Chart of Accounts",
                    status='active'
                )
                template_id = template.get('id')
        
        result = coa_storage.add_coa_account(
            template_id=template_id,
            code=data.get('code'),
            name=data.get('name'),
            account_type=data.get('type', 'Asset'),
            locked=data.get('locked', False),
            description=data.get('description', '')
        )
        
        return jsonify({
            'id': result.get('id'),
            'code': result.get('code'),
            'name': result.get('name'),
            'type': result.get('account_type'),
            'locked': result.get('locked'),
            'description': result.get('description')
        }), 201
    except Exception as e:
        print(f"[ERROR] Creating COA account: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/coa-accounts/<account_id>', methods=['PUT'])
def api_update_coa_account_frontend(account_id):
    """Update a COA account (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        data = request.get_json()
        
        # Verify account belongs to municipality
        account = coa_storage.get_coa_account(account_id)
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get template to verify municipality scope
        template = coa_storage.get_coa_template(account.get('template_id'))
        if not template or template.get('municipality') != municipality_scope:
            return jsonify({'error': 'Not authorized'}), 403
        
        # Update the account with kwargs
        update_kwargs = {}
        if 'code' in data:
            update_kwargs['code'] = data.get('code')
        if 'name' in data:
            update_kwargs['name'] = data.get('name')
        if 'type' in data:
            update_kwargs['account_type'] = data.get('type')
        if 'locked' in data:
            update_kwargs['locked'] = data.get('locked')
        
        result = coa_storage.update_coa_account(account_id, **update_kwargs)
        
        return jsonify({
            'id': result.get('id'),
            'code': result.get('code'),
            'name': result.get('name'),
            'type': result.get('account_type'),
            'locked': result.get('locked')
        }), 200
    except Exception as e:
        print(f"[ERROR] Updating COA account: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== EXPENSE CATEGORIES API (Frontend-compatible) ====================

@bp.route('/expense-categories', methods=['GET'])
def api_get_expense_categories_frontend():
    """Get all expense categories (frontend-compatible endpoint)"""
    try:
        # Try to get municipality scope
        municipality_scope = _get_current_municipality_scope()
        
        # If no municipality scope, fetch ALL categories (for national admin)
        if not municipality_scope:
            try:
                db = get_firestore_db()
                categories = []
                print(f"[INFO] Fetching ALL expense categories from Firestore...")
                query_result = db.collection('expense_categories').stream()
                for doc in query_result:
                    data = doc.to_dict() or {}
                    categories.append({
                        'id': doc.id,
                        'name': data.get('name'),
                        'coa_code': data.get('coa_code'),
                        'tax_type': data.get('tax_type', 'None'),
                        'default_rate': data.get('default_rate', 0),
                        'status': data.get('status', 'active'),
                        'municipality': data.get('municipality')
                    })
                print(f"[INFO] Fetched {len(categories)} expense categories")
                return jsonify(categories), 200
            except Exception as e:
                print(f"[ERROR] Getting all expense categories: {e}")
                import traceback
                traceback.print_exc()
                return jsonify([]), 200
        
        # Municipality-specific fetch
        db = get_firestore_db()
        categories = []
        try:
            query_result = db.collection('expense_categories').where('municipality', '==', municipality_scope).stream()
            for doc in query_result:
                data = doc.to_dict() or {}
                categories.append({
                    'id': doc.id,
                    'name': data.get('name'),
                    'coa_code': data.get('coa_code'),
                    'tax_type': data.get('tax_type', 'None'),
                    'default_rate': data.get('default_rate', 0),
                    'status': data.get('status', 'active'),
                    'municipality': data.get('municipality')
                })
        except Exception as e:
            print(f"[WARN] Error querying municipality-specific categories: {e}")
        
        return jsonify(categories), 200
    except Exception as e:
        print(f"[ERROR] Getting expense categories: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 200

@bp.route('/expense-categories', methods=['POST'])
def api_create_expense_category_frontend():
    """Create a new expense category (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        data = request.get_json()
        db = get_firestore_db()
        
        category_data = {
            'name': data.get('name'),
            'coa_code': data.get('coa_code'),
            'tax_type': data.get('tax_type', 'None'),
            'default_rate': data.get('default_rate', 0),
            'status': data.get('status', 'active'),
            'municipality': municipality_scope,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        result = db.collection('expense_categories').add(category_data)
        doc_id = result[1].id
        
        return jsonify({
            'id': doc_id,
            'name': category_data['name'],
            'coa_code': category_data['coa_code'],
            'tax_type': category_data['tax_type'],
            'default_rate': category_data['default_rate'],
            'status': category_data['status']
        }), 201
    except Exception as e:
        print(f"[ERROR] Creating expense category: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/expense-categories/<category_id>', methods=['PUT'])
def api_update_expense_category_frontend(category_id):
    """Update an expense category (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        data = request.get_json()
        db = get_firestore_db()
        
        # Verify category belongs to municipality
        category_doc = db.collection('expense_categories').document(category_id).get()
        if not category_doc.exists:
            return jsonify({'error': 'Category not found'}), 404
        
        category = category_doc.to_dict() or {}
        if category.get('municipality') != municipality_scope:
            return jsonify({'error': 'Not authorized'}), 403
        
        # Update the category
        update_data = {
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        if 'name' in data:
            update_data['name'] = data.get('name')
        if 'coa_code' in data:
            update_data['coa_code'] = data.get('coa_code')
        if 'tax_type' in data:
            update_data['tax_type'] = data.get('tax_type')
        if 'default_rate' in data:
            update_data['default_rate'] = data.get('default_rate')
        if 'status' in data:
            update_data['status'] = data.get('status')
        
        db.collection('expense_categories').document(category_id).update(update_data)
        
        # Get updated document
        updated_doc = db.collection('expense_categories').document(category_id).get()
        updated_data = updated_doc.to_dict() or {}
        
        return jsonify({
            'id': updated_doc.id,
            'name': updated_data.get('name'),
            'coa_code': updated_data.get('coa_code'),
            'tax_type': updated_data.get('tax_type'),
            'default_rate': updated_data.get('default_rate'),
            'status': updated_data.get('status')
        }), 200
    except Exception as e:
        print(f"[ERROR] Updating expense category: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/expense-categories/<category_id>', methods=['DELETE'])
def api_delete_expense_category_frontend(category_id):
    """Delete an expense category (frontend-compatible endpoint)"""
    try:
        municipality_scope = _get_current_municipality_scope()
        
        if not municipality_scope:
            return jsonify({'error': 'Municipality scope required'}), 403
        
        db = get_firestore_db()
        
        # Verify category belongs to municipality
        category_doc = db.collection('expense_categories').document(category_id).get()
        if not category_doc.exists:
            return jsonify({'error': 'Category not found'}), 404
        
        category = category_doc.to_dict() or {}
        if category.get('municipality') != municipality_scope:
            return jsonify({'error': 'Not authorized'}), 403
        
        db.collection('expense_categories').document(category_id).delete()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"[ERROR] Deleting expense category: {e}")
        return jsonify({'error': str(e)}), 500
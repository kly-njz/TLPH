from flask import Blueprint, render_template, jsonify, request, session
from firebase_config import get_firestore_db
from firebase_auth_middleware import role_required

from datetime import datetime
from firebase_admin import firestore
import system_logs_storage

bp = Blueprint('regional', __name__, url_prefix='/regional')

# Region name mapping (session name -> Firestore name)
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

def get_firestore_region_name(session_region):
    """Convert session region name to Firestore region name"""
    if not session_region:
        return None
    session_region_upper = str(session_region).strip().upper()
    # Try direct mapping
    if session_region_upper in REGION_MAPPING:
        return REGION_MAPPING[session_region_upper]
    # Try reverse mapping (in case Firestore name is passed)
    reverse_mapping = {v: k for k, v in REGION_MAPPING.items()}
    if session_region_upper in reverse_mapping:
        return session_region_upper
    # Return as-is if no mapping found
    return session_region_upper


def _canonical_region(value):
    """Normalize region strings from mixed formats to a comparable canonical value."""
    raw = str(value or '').strip().upper()
    if not raw:
        return ''

    # Handle common aliases/labels seen in Firestore/session data.
    if 'MIMAROPA' in raw or 'IV-B' in raw or 'REGION IV-B' in raw or 'REGION-IV-B' in raw:
        return 'REGION-IV-B'
    if 'CALABARZON' in raw or 'IV-A' in raw or 'REGION IV-A' in raw or 'REGION-IV-A' in raw:
        return 'REGION-IV-A'
    if 'BICOL' in raw or 'REGION-V' in raw or 'REGION V' in raw:
        return 'REGION-V'
    if 'NCR' in raw:
        return 'NCR'
    if 'CARAGA' in raw:
        return 'REGION-XIII'
    if 'BANGSAMORO' in raw or 'ARMM' in raw:
        return 'REGION-BANGSAMORO'

    return raw.replace(' ', '').replace('_', '').replace('.', '')


def _same_region(left, right):
    """Best-effort region equality for mixed naming conventions."""
    l = _canonical_region(left)
    r = _canonical_region(right)
    if not l or not r:
        return False
    return l == r


def _resolve_regional_scope(db):
    """Resolve region + municipality scope for the current regional admin."""
    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)

    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve regional scope: {e}")

    municipalities = []
    try:
        # Try multiple possible document IDs, since stored IDs may use
        # session names (e.g. MIMAROPA) or Firestore names (e.g. REGION-IV-B).
        candidates = []
        if user_region:
            candidates.append(str(user_region).strip())

        session_region = session.get('region') or session.get('user_region')
        if session_region:
            candidates.append(str(session_region).strip())

        # Add reverse-mapped key when possible.
        reverse_mapping = {v: k for k, v in REGION_MAPPING.items()}
        if user_region and user_region in reverse_mapping:
            candidates.append(reverse_mapping[user_region])

        seen = set()
        ordered_candidates = []
        for c in candidates:
            cu = str(c).strip()
            if cu and cu not in seen:
                seen.add(cu)
                ordered_candidates.append(cu)

        for key in ordered_candidates:
            muni_doc = db.collection('municipalities').document(key).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []
                if municipalities:
                    break
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities for region {user_region}: {e}")

    municipality_set = {str(m).strip().lower() for m in municipalities if m}
    return user_region, municipality_set


def _normalize_ts_for_json(value):
    if not value:
        return None
    try:
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        if hasattr(value, 'to_datetime'):
            return value.to_datetime().isoformat()
        return str(value)
    except Exception:
        return str(value)


def _extract_ip_value(record):
    """Best-effort IP extraction across varying field names/formats."""
    if not isinstance(record, dict):
        return ''

    metadata = record.get('metadata') if isinstance(record.get('metadata'), dict) else {}

    candidates = [
        record.get('ip'),
        record.get('ip_address'),
        record.get('ipAddress'),
        record.get('client_ip'),
        record.get('clientIp'),
        record.get('remote_addr'),
        record.get('remoteAddr'),
        record.get('x_forwarded_for'),
        record.get('xForwardedFor'),
        record.get('request_ip'),
        record.get('requestIp'),
        record.get('requester_ip'),
        record.get('requesterIp'),
        metadata.get('ip'),
        metadata.get('ip_address'),
        metadata.get('ipAddress'),
        metadata.get('request_ip'),
        metadata.get('requestIp'),
    ]

    for raw in candidates:
        value = str(raw or '').strip()
        if not value:
            continue
        # If coming from X-Forwarded-For chain, use first IP.
        if ',' in value:
            value = value.split(',')[0].strip()
        return value
    return ''


def _transaction_in_regional_scope(tx_data, user_region, municipality_set):
    tx_municipality = str(
        tx_data.get('municipality')
        or tx_data.get('municipality_name')
        or tx_data.get('target_municipality')
        or ''
    ).strip().lower()
    tx_region = get_firestore_region_name(
        tx_data.get('region') or tx_data.get('region_name') or tx_data.get('regionName')
    )
    tx_region_norm = str(tx_region or '').strip().upper()
    user_region_norm = str(user_region or '').strip().upper()

    # If regional scope cannot be resolved, avoid hard-failing to empty results.
    if not user_region_norm and not municipality_set:
        return True

    in_scope_by_municipality = bool(municipality_set and tx_municipality and tx_municipality in municipality_set)
    in_scope_by_region = bool(user_region_norm and tx_region_norm and tx_region_norm == user_region_norm)

    return in_scope_by_municipality or in_scope_by_region

@bp.route('/profile')
@role_required('regional','regional_admin')
def profile_view():
    return render_template('regional/profile.html')

@bp.route('/application-list')
@role_required('regional','regional_admin')
def application_list_view():
    return render_template('regional/application-regional-list.html')

@bp.route('/service-list')
@role_required('regional','regional_admin')
def service_list_view():
    return render_template('regional/service-regional-list.html')

@bp.route('/service-view', defaults={'doc_id': None})
@bp.route('/service-view/<doc_id>')
@role_required('regional','regional_admin')
def service_info_view(doc_id=None):
    return render_template('regional/service-regional-view.html', doc_id=doc_id)

@bp.route('/inventory-view')
@role_required('regional','regional_admin')
def inventory_view():
    return render_template('regional/inventory-regional-list.html')

@bp.route('/inventory/api/<inventory_id>/status', methods=['POST'])
@role_required('regional','regional_admin')
def update_inventory_status_regional(inventory_id):
    """Regional inventory action endpoint: approve, reject, or forward to national."""
    try:
        db = get_firestore_db()
        payload = request.get_json(silent=True) or {}
        requested_status = str(payload.get('status') or '').strip().lower()

        valid_statuses = {'approved', 'rejected', 'forwarded-to-national'}
        if requested_status not in valid_statuses:
            return jsonify({
                'status': 'error',
                'message': 'Invalid status action.'
            }), 400

        inv_ref = db.collection('inventory_registrations').document(inventory_id)
        inv_doc = inv_ref.get()
        if not inv_doc.exists:
            return jsonify({
                'status': 'error',
                'message': 'Inventory registration not found.'
            }), 404

        inv_data = inv_doc.to_dict() or {}
        user_region, municipality_set = _resolve_regional_scope(db)

        current_status = str(inv_data.get('status') or '').strip().lower()
        current_regional = str(inv_data.get('regionalStatus') or '').strip().lower()
        current_national = str(inv_data.get('nationalStatus') or '').strip().lower()

        is_final = (
            current_status in {'approved', 'rejected', 'forwarded-to-national'}
            or current_regional in {'approved', 'rejected'}
            or current_national in {'approved', 'rejected'}
        )
        if is_final:
            return jsonify({
                'status': 'error',
                'message': 'This inventory record already has a final action and can no longer be updated.'
            }), 409

        inv_municipality = str(inv_data.get('municipality') or '').strip().lower()
        inv_region = get_firestore_region_name(
            inv_data.get('region') or inv_data.get('region_name') or inv_data.get('regionName')
        )

        # Fallback: derive scope fields from owner profile for legacy records
        # where municipality/region were not persisted on inventory document.
        if (not inv_municipality or not inv_region) and inv_data.get('userId'):
            try:
                owner_doc = db.collection('users').document(str(inv_data.get('userId'))).get()
                if owner_doc.exists:
                    owner_data = owner_doc.to_dict() or {}
                    if not inv_municipality:
                        inv_municipality = str(owner_data.get('municipality') or '').strip().lower()
                    if not inv_region:
                        inv_region = get_firestore_region_name(
                            owner_data.get('region') or owner_data.get('region_name') or owner_data.get('regionName')
                        )
            except Exception:
                pass

        in_scope = True
        if user_region or municipality_set:
            has_loc_data = bool(inv_municipality or inv_region)
            if not has_loc_data:
                # Keep legacy records actionable if regional location metadata is missing.
                in_scope = True
            else:
                in_scope = (
                    bool(municipality_set and inv_municipality and inv_municipality in municipality_set)
                    or _same_region(inv_region, user_region)
                )

        if not in_scope:
            return jsonify({
                'status': 'error',
                'message': 'Inventory item is outside your regional scope.'
            }), 403

        update_data = {
            'status': requested_status,
            'updatedAt': datetime.utcnow(),
        }

        if requested_status == 'approved':
            update_data.update({
                'regionalStatus': 'approved',
                'approvedByLevel': 'Regional',
                'approvedAt': datetime.utcnow(),
                'rejectedByLevel': '',
                'rejectedByEmail': ''
            })
        elif requested_status == 'rejected':
            update_data.update({
                'regionalStatus': 'rejected',
                'rejectedByLevel': 'Regional',
                'rejectedAt': datetime.utcnow(),
                'approvedByLevel': '',
                'approvedByEmail': ''
            })
        elif requested_status == 'forwarded-to-national':
            update_data.update({
                'regionalStatus': 'approved',
                'forwardedByLevel': 'Regional',
                'forwardedToLevel': 'National',
                'forwardedAt': datetime.utcnow(),
                'nationalStatus': 'pending'
            })

        inv_ref.update(update_data)
        return jsonify({
            'status': 'success',
            'message': 'Inventory status updated successfully.'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/license-view')
@role_required('regional','regional_admin')
def license_view():
    return render_template('regional/license-regional-list.html')

@bp.route('/transaction-view')
@role_required('regional','regional_admin')
def transaction_view():
    return render_template('regional/transaction-regional-list.html')

@bp.route('/user-management-regional-list')
@role_required('regional','regional_admin')
def regional_account_management_view():
    return render_template('regional/user-management-regional-list.html')

@bp.route('/municipal-accounts')
@role_required('regional','regional_admin')
def municipal_accounts_view():
    return render_template('regional/municipal-accounts.html')

@bp.route('/municipal-accounts/create', methods=['POST'])
@role_required('regional','regional_admin')
def municipal_accounts_create():
    from flask import request, jsonify, session
    from firebase_admin import auth as admin_auth, firestore
    import datetime

    data = request.get_json()
    email        = (data.get('email')        or '').strip()
    password     = (data.get('password')     or '').strip()
    firstName    = (data.get('firstName')    or '').strip()
    lastName     = (data.get('lastName')     or '').strip()
    phone        = (data.get('phone')        or '').strip()
    municipality = (data.get('municipality') or '').strip()
    province     = (data.get('province')     or '').strip()
    region       = (data.get('region')       or '').strip()
    regionName   = (data.get('regionName')   or '').strip()

    if not all([email, password, firstName, lastName, municipality, province]):
        return jsonify({'success': False, 'error': 'All required fields must be filled.'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters.'}), 400

    try:
        # Create user in Firebase Auth using Admin SDK (server-side, no network issue)
        user_record = admin_auth.create_user(
            email=email,
            password=password,
            display_name=f'{firstName} {lastName}'.strip()
        )
        uid = user_record.uid

        # Write Firestore profile
        db = firestore.client()
        db.collection('users').document(uid).set({
            'firstName'    : firstName,
            'lastName'     : lastName,
            'email'        : email,
            'phone'        : phone,
            'municipality' : municipality,
            'province'     : province,
            'region'       : region,
            'regionName'   : regionName,
            'role'         : 'municipal_admin',
            'applicationType': 'municipal',
            'status'       : 'active',
            'createdAt'    : datetime.datetime.utcnow().isoformat(),
            'createdByRegion': region
        })

        return jsonify({'success': True, 'uid': uid})

    except admin_auth.EmailAlreadyExistsError:
        return jsonify({'success': False, 'error': 'An account with that email already exists.'}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@bp.route('/audit-logs')
@bp.route('/audit-logs-view')
@role_required('regional','regional_admin')
def audit_logs_view():
    return render_template('regional/audit-logs-regional-view.html')


@bp.route('/api/audit/financial-logs', methods=['GET'])
@role_required('regional','regional_admin')
def api_regional_financial_audit_logs():
    """Return region-scoped financial audit logs similar to municipal audit payload."""
    try:
        db = get_firestore_db()
        user_region, municipality_set = _resolve_regional_scope(db)

        logs = []

        # Build fallback user scope using users in this regional coverage.
        scoped_emails = set()
        scoped_user_ids = set()
        try:
            users_docs = db.collection('users').limit(5000).stream()
            user_region_norm = str(user_region or '').strip().upper()
            for user_doc in users_docs:
                ud = user_doc.to_dict() or {}
                u_email = str(ud.get('email') or '').strip().lower()
                u_muni = str(ud.get('municipality') or ud.get('municipality_name') or '').strip().lower()
                u_region = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
                u_region_norm = str(u_region or '').strip().upper()

                in_scope_by_muni = bool(municipality_set and u_muni and u_muni in municipality_set)
                in_scope_by_region = bool(user_region_norm and u_region_norm and u_region_norm == user_region_norm)
                in_scope = in_scope_by_muni or in_scope_by_region or (not user_region_norm and not municipality_set)
                if not in_scope:
                    continue

                if u_email:
                    scoped_emails.add(u_email)

                scoped_user_ids.add(str(user_doc.id).strip())
                for pid in (ud.get('uid'), ud.get('user_id'), ud.get('userId'), ud.get('id')):
                    if pid:
                        scoped_user_ids.add(str(pid).strip())
        except Exception as e:
            print(f"[WARN] Failed building fallback regional user scope: {e}")

        # Source 1: transactions
        tx_docs = db.collection('transactions').limit(5000).stream()
        for tx_doc in tx_docs:
            tx = tx_doc.to_dict() or {}

            tx_email = str(
                tx.get('user_email')
                or tx.get('userEmail')
                or tx.get('email')
                or tx.get('payer_email')
                or tx.get('payerEmail')
                or tx.get('customer_email')
                or tx.get('customerEmail')
                or ''
            ).strip().lower()
            tx_user_id = str(tx.get('userId') or tx.get('user_id') or tx.get('uid') or '').strip()

            in_scope_by_fields = _transaction_in_regional_scope(tx, user_region, municipality_set)
            in_scope_by_user = bool((tx_email and tx_email in scoped_emails) or (tx_user_id and tx_user_id in scoped_user_ids))

            if not (in_scope_by_fields or in_scope_by_user):
                continue

            status_value = str(tx.get('status') or '').strip().upper() or 'PENDING'
            ts_value = (
                tx.get('updated_at')
                or tx.get('forwarded_at')
                or tx.get('created_at')
                or tx.get('createdAt')
                or tx.get('updatedAt')
            )
            outcome_value = 'SUCCESS' if status_value in {'PAID', 'APPROVED', 'COMPLETED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')

            logs.append({
                'id': tx_doc.id,
                'ts': _normalize_ts_for_json(ts_value),
                'user': tx.get('updated_by') or tx.get('forwarded_by') or tx.get('user_email') or 'User',
                'role': 'Municipal',
                'module': 'PAYMENTS',
                'action': status_value,
                'target': tx.get('transaction_name') or tx.get('description') or 'Payment',
                'targetId': tx.get('invoice_id') or tx.get('external_id') or tx_doc.id,
                'device_type': tx.get('device_type') or tx.get('device') or '',
                'ip': _extract_ip_value(tx),
                'outcome': outcome_value,
                'message': tx.get('description') or '',
                'forwarded_message': tx.get('forwarded_message') or tx.get('forwardMessage') or '',
                'forwarded_by': tx.get('forwarded_by') or '',
                'municipality': tx.get('municipality') or tx.get('municipality_name') or tx.get('target_municipality') or '',
                'region': get_firestore_region_name(tx.get('region') or tx.get('region_name') or tx.get('regionName')),
                'canReview': status_value == 'FORWARDED',
                'diff': tx,
            })

        # Source 2: municipal fund distribution
        fund_docs = db.collection('municipal_fund_distribution').limit(5000).stream()
        for fund_doc in fund_docs:
            fund = fund_doc.to_dict() or {}

            fund_muni = str(fund.get('target_municipality') or '').strip().lower()
            fund_region = get_firestore_region_name(fund.get('region') or fund.get('region_name') or fund.get('regionName'))
            fund_region_norm = str(fund_region or '').strip().upper()
            user_region_norm = str(user_region or '').strip().upper()

            in_scope_by_muni = bool(municipality_set and fund_muni and fund_muni in municipality_set)
            in_scope_by_region = bool(user_region_norm and fund_region_norm and fund_region_norm == user_region_norm)
            if not (in_scope_by_muni or in_scope_by_region or (not user_region_norm and not municipality_set)):
                continue

            status_value = str(fund.get('status') or '').strip().upper() or 'PENDING'
            ts_value = fund.get('updated_at') or fund.get('created_at')
            outcome_value = 'SUCCESS' if status_value in {'COMPLETED', 'APPROVED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')

            logs.append({
                'id': fund_doc.id,
                'ts': _normalize_ts_for_json(ts_value),
                'user': fund.get('updated_by') or fund.get('initiated_by') or 'Regional Office',
                'role': 'Regional',
                'module': 'FUND_TRANSFER',
                'action': status_value,
                'target': fund.get('target_municipality') or 'Municipality',
                'targetId': fund.get('reference') or fund_doc.id,
                'device_type': '',
                'ip': _extract_ip_value(fund),
                'outcome': outcome_value,
                'message': fund.get('description') or '',
                'forwarded_message': '',
                'forwarded_by': '',
                'municipality': fund.get('target_municipality') or '',
                'region': fund_region,
                'canReview': False,
                'diff': fund,
            })

        # Source 3: auditLogs collection (municipal admin sign-ins and decision actions)
        try:
            audit_docs = db.collection('auditLogs').limit(5000).stream()
            tracked_actions = {'LOGIN', 'LOGOUT', 'APPROVE', 'APPROVED', 'REJECT', 'REJECTED'}
            for audit_doc in audit_docs:
                entry = audit_doc.to_dict() or {}
                actor_role = str(entry.get('actorRole') or '').strip().lower()
                action_raw = str(entry.get('action') or entry.get('event') or entry.get('type') or '').strip().upper()
                if not action_raw:
                    continue

                # Normalize variants like USER_LOGIN, SIGNIN, LOG_IN, etc.
                if 'LOGIN' in action_raw or 'SIGNIN' in action_raw or action_raw in {'LOG_IN'}:
                    action_value = 'LOGIN'
                elif 'LOGOUT' in action_raw or 'SIGNOUT' in action_raw or action_raw in {'LOG_OUT'}:
                    action_value = 'LOGOUT'
                elif 'APPROV' in action_raw:
                    action_value = 'APPROVED'
                elif 'REJECT' in action_raw or 'DENY' in action_raw:
                    action_value = 'REJECTED'
                else:
                    action_value = action_raw

                if action_value not in tracked_actions:
                    continue

                actor_email = str(
                    entry.get('actorEmail')
                    or entry.get('user_email')
                    or entry.get('email')
                    or entry.get('user')
                    or ''
                ).strip().lower()
                actor_id = str(
                    entry.get('actorId')
                    or entry.get('userId')
                    or entry.get('uid')
                    or entry.get('user_id')
                    or ''
                ).strip()

                is_municipal_actor = actor_role in {'municipal_admin', 'municipal'}
                in_scope_by_actor = bool(
                    (actor_email and actor_email in scoped_emails)
                    or (actor_id and actor_id in scoped_user_ids)
                )
                if not (is_municipal_actor or in_scope_by_actor):
                    continue

                entry_muni = str(entry.get('municipality') or entry.get('municipality_name') or '').strip().lower()
                entry_region = get_firestore_region_name(
                    entry.get('region') or entry.get('region_name') or entry.get('regionName') or entry.get('province')
                )
                entry_region_norm = str(entry_region or '').strip().upper()
                user_region_norm = str(user_region or '').strip().upper()

                in_scope_by_muni = bool(municipality_set and entry_muni and entry_muni in municipality_set)
                in_scope_by_region = bool(user_region_norm and entry_region_norm and entry_region_norm == user_region_norm)
                if not (in_scope_by_muni or in_scope_by_region or in_scope_by_actor or (not user_region_norm and not municipality_set)):
                    continue

                ts_value = entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt')
                outcome_value = 'SUCCESS' if action_value in {'LOGIN', 'APPROVE', 'APPROVED'} else ('FAIL' if action_value in {'REJECT', 'REJECTED'} else 'WARN')

                logs.append({
                    'id': audit_doc.id,
                    'ts': _normalize_ts_for_json(ts_value),
                    'user': entry.get('actorName') or entry.get('actor') or entry.get('user') or 'Municipal Admin',
                    'role': 'Municipal',
                    'module': 'AUTH' if action_value in {'LOGIN', 'LOGOUT'} else 'AUDIT',
                    'action': action_value,
                    'target': entry.get('target') or entry.get('targetId') or entry.get('module') or 'System',
                    'targetId': entry.get('targetId') or audit_doc.id,
                    'device_type': entry.get('device') or entry.get('device_type') or '',
                    'ip': _extract_ip_value(entry),
                    'outcome': outcome_value,
                    'message': entry.get('detail') or entry.get('description') or '',
                    'forwarded_message': '',
                    'forwarded_by': '',
                    'municipality': entry.get('municipality') or entry.get('municipality_name') or '',
                    'region': entry_region,
                    'canReview': False,
                    'diff': entry,
                })
        except Exception as e:
            print(f"[WARN] Failed loading auditLogs source for regional financial logs: {e}")

        # Keep entries even if timestamp is missing; frontend handles N/A.
        logs.sort(key=lambda x: x.get('ts') or '', reverse=True)

        print(f"[DEBUG] Regional financial audit logs -> region={user_region}, municipalities={len(municipality_set)}, scoped_users={len(scoped_emails)}, returned={len(logs)}")

        return jsonify({'success': True, 'logs': logs, 'region': user_region}), 200
    except Exception as e:
        print(f"[ERROR] Regional financial audit logs failed: {e}")
        return jsonify({'success': False, 'error': str(e), 'logs': []}), 200


@bp.route('/api/system-logs', methods=['GET'])
@role_required('regional','regional_admin')
def api_regional_system_logs():
    """Return only municipal admin login/logout and approval events for the current region."""
    try:
        db = get_firestore_db()
        user_region, municipality_set = _resolve_regional_scope(db)

        scoped_emails = set()
        scoped_user_ids = set()
        try:
            users_docs = db.collection('users').limit(5000).stream()
            user_region_norm = str(user_region or '').strip().upper()
            for user_doc in users_docs:
                ud = user_doc.to_dict() or {}
                role_value = str(ud.get('role') or '').strip().lower()
                if role_value not in {'municipal_admin', 'municipal'}:
                    continue

                u_email = str(ud.get('email') or '').strip().lower()
                u_muni = str(ud.get('municipality') or ud.get('municipality_name') or '').strip().lower()
                u_region = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
                u_region_norm = str(u_region or '').strip().upper()

                in_scope = bool(
                    (municipality_set and u_muni and u_muni in municipality_set)
                    or (user_region_norm and u_region_norm and _same_region(u_region_norm, user_region_norm))
                    or (not user_region_norm and not municipality_set)
                )
                if not in_scope:
                    continue

                if u_email:
                    scoped_emails.add(u_email)
                scoped_user_ids.add(str(user_doc.id).strip())
                for pid in (ud.get('uid'), ud.get('user_id'), ud.get('userId'), ud.get('id')):
                    if pid:
                        scoped_user_ids.add(str(pid).strip())
        except Exception as e:
            print(f"[WARN] Failed building scoped municipal users for system logs: {e}")

        logs = []
        regional_source_count = 0
        audit_fallback_count = 0
        system_fallback_count = 0
        regional_log_rows = system_logs_storage.list_regional_system_logs_by_region(user_region, limit=300)
        user_region_norm = str(user_region or '').strip().upper()

        for entry in regional_log_rows:
            action_value = str(entry.get('action') or '').strip().upper()
            if not action_value:
                continue

            actor_email = str(entry.get('actorEmail') or entry.get('user') or '').strip().lower()
            actor_id = str(entry.get('actorId') or '').strip()
            actor_role = str(entry.get('actorRole') or entry.get('role') or '').strip().lower()
            is_municipal_actor = actor_role in {'municipal_admin', 'municipal'} if actor_role else False
            in_scope_by_actor = bool(
                (actor_email and actor_email in scoped_emails)
                or (actor_id and actor_id in scoped_user_ids)
            )

            entry_region = get_firestore_region_name(
                entry.get('region') or entry.get('region_name') or entry.get('regionName') or user_region
            )
            entry_region_norm = str(entry_region or '').strip().upper()
            entry_muni = str(entry.get('municipality') or entry.get('municipality_name') or '').strip()
            entry_muni_norm = entry_muni.lower()
            in_scope_by_location = bool(
                (municipality_set and entry_muni_norm and entry_muni_norm in municipality_set)
                or (user_region_norm and entry_region_norm and _same_region(entry_region_norm, user_region_norm))
                or (not user_region_norm and not municipality_set)
            )

            # Accept entries when either actor OR location is in scope.
            # Do not require role metadata because many legacy logs don't store actorRole.
            if not (in_scope_by_actor or in_scope_by_location or is_municipal_actor):
                continue

            ts_value = entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt')
            details = entry.get('message') or ('Municipal admin signed in.' if action_value == 'LOGIN' else 'Municipal admin signed out.' if action_value == 'LOGOUT' else 'Municipal admin approved an item.')

            # Extract IP and device info
            ip_addr = _extract_ip_value(entry)
            device_info = entry.get('device_type') or entry.get('device') or ''
            
            logs.append({
                'id': entry.get('id') or '',
                'ts': _normalize_ts_for_json(ts_value),
                'user': entry.get('user') or actor_email or 'Municipal Admin',
                'role': 'Municipal',
                'module': entry.get('module') or ('AUTH' if action_value in {'LOGIN', 'LOGOUT'} else 'AUDIT'),
                'action': action_value,
                'target': entry.get('target') or entry.get('targetId') or entry.get('module') or 'System',
                'targetId': entry.get('targetId') or entry.get('target_id') or entry.get('id') or '',
                'device_type': device_info,
                'ip': ip_addr,
                'outcome': entry.get('outcome') or 'SUCCESS',
                'message': details,
                'municipality': entry_muni,
                'region': entry_region,
                'scope': 'MUNICIPAL',
            })
            regional_source_count += 1

        # Fallback source: auditLogs collection (common source for auth/decision events)
        # This keeps the UI populated even when dedicated regional_system_logs is empty.
        try:
            audit_docs = db.collection('auditLogs').limit(5000).stream()
            for audit_doc in audit_docs:
                entry = audit_doc.to_dict() or {}
                action_raw = str(entry.get('action') or entry.get('event') or entry.get('type') or '').strip().upper()
                if not action_raw:
                    continue

                if 'LOGIN' in action_raw or 'SIGNIN' in action_raw or action_raw in {'LOG_IN'}:
                    action_value = 'LOGIN'
                elif 'LOGOUT' in action_raw or 'SIGNOUT' in action_raw or action_raw in {'LOG_OUT'}:
                    action_value = 'LOGOUT'
                elif 'APPROV' in action_raw:
                    action_value = 'APPROVED'
                else:
                    action_value = action_raw

                actor_email = str(
                    entry.get('actorEmail')
                    or entry.get('user_email')
                    or entry.get('email')
                    or entry.get('user')
                    or ''
                ).strip().lower()
                actor_id = str(
                    entry.get('actorId')
                    or entry.get('userId')
                    or entry.get('uid')
                    or entry.get('user_id')
                    or ''
                ).strip()
                actor_role = str(entry.get('actorRole') or entry.get('role') or '').strip().lower()

                in_scope_by_actor = bool(
                    (actor_email and actor_email in scoped_emails)
                    or (actor_id and actor_id in scoped_user_ids)
                )
                # If role is absent, still allow location-based scoped entries.
                if not in_scope_by_actor and actor_role and actor_role not in {'municipal_admin', 'municipal'}:
                    continue

                entry_muni = str(entry.get('municipality') or entry.get('municipality_name') or '').strip()
                entry_muni_norm = entry_muni.lower()
                entry_region = get_firestore_region_name(
                    entry.get('region') or entry.get('region_name') or entry.get('regionName') or user_region
                )
                entry_region_norm = str(entry_region or '').strip().upper()

                in_scope_by_location = bool(
                    (municipality_set and entry_muni_norm and entry_muni_norm in municipality_set)
                    or (user_region_norm and entry_region_norm and _same_region(entry_region_norm, user_region_norm))
                    or (not user_region_norm and not municipality_set)
                )
                if not (in_scope_by_actor or in_scope_by_location):
                    continue

                ts_value = entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt')
                details = entry.get('detail') or entry.get('description') or entry.get('message') or ''

                logs.append({
                    'id': audit_doc.id,
                    'ts': _normalize_ts_for_json(ts_value),
                    'user': entry.get('actorName') or entry.get('actor') or entry.get('user') or actor_email or 'Municipal Admin',
                    'role': 'Municipal',
                    'module': 'AUTH' if action_value in {'LOGIN', 'LOGOUT'} else 'AUDIT',
                    'action': action_value,
                    'target': entry.get('target') or entry.get('targetId') or entry.get('module') or 'System',
                    'targetId': entry.get('targetId') or entry.get('target_id') or audit_doc.id,
                    'device_type': entry.get('device_type') or entry.get('device') or '',
                    'ip': _extract_ip_value(entry),
                    'outcome': entry.get('outcome') or 'SUCCESS',
                    'message': details,
                    'municipality': entry_muni,
                    'region': entry_region,
                    'scope': 'MUNICIPAL',
                })
                audit_fallback_count += 1
        except Exception as e:
            print(f"[WARN] Failed loading fallback auditLogs source for regional system logs: {e}")

        # Fallback source 2: system_logs collection used by some app modules.
        try:
            sys_docs = db.collection('system_logs').limit(5000).stream()
            for sys_doc in sys_docs:
                entry = sys_doc.to_dict() or {}
                action_raw = str(entry.get('action') or entry.get('event') or entry.get('type') or '').strip().upper()
                if not action_raw:
                    continue

                if 'LOGIN' in action_raw or 'SIGNIN' in action_raw or action_raw in {'LOG_IN'}:
                    action_value = 'LOGIN'
                elif 'LOGOUT' in action_raw or 'SIGNOUT' in action_raw or action_raw in {'LOG_OUT'}:
                    action_value = 'LOGOUT'
                elif 'APPROV' in action_raw:
                    action_value = 'APPROVED'
                else:
                    action_value = action_raw

                actor_email = str(
                    entry.get('actorEmail')
                    or entry.get('user_email')
                    or entry.get('email')
                    or entry.get('user')
                    or ''
                ).strip().lower()
                actor_id = str(
                    entry.get('actorId')
                    or entry.get('userId')
                    or entry.get('uid')
                    or entry.get('user_id')
                    or ''
                ).strip()

                in_scope_by_actor = bool(
                    (actor_email and actor_email in scoped_emails)
                    or (actor_id and actor_id in scoped_user_ids)
                )

                entry_muni = str(entry.get('municipality') or entry.get('municipality_name') or '').strip()
                entry_muni_norm = entry_muni.lower()
                entry_region = get_firestore_region_name(
                    entry.get('region') or entry.get('region_name') or entry.get('regionName') or user_region
                )
                entry_region_norm = str(entry_region or '').strip().upper()

                in_scope_by_location = bool(
                    (municipality_set and entry_muni_norm and entry_muni_norm in municipality_set)
                    or (user_region_norm and entry_region_norm and _same_region(entry_region_norm, user_region_norm))
                    or (not user_region_norm and not municipality_set)
                )
                if not (in_scope_by_actor or in_scope_by_location):
                    continue

                ts_value = entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt')
                details = entry.get('message') or entry.get('detail') or entry.get('description') or entry.get('target') or ''

                logs.append({
                    'id': sys_doc.id,
                    'ts': _normalize_ts_for_json(ts_value),
                    'user': entry.get('actorName') or entry.get('actor') or entry.get('user') or actor_email or 'Municipal Admin',
                    'role': 'Municipal',
                    'module': entry.get('module') or ('AUTH' if action_value in {'LOGIN', 'LOGOUT'} else 'AUDIT'),
                    'action': action_value,
                    'target': entry.get('target') or entry.get('targetId') or entry.get('module') or 'System',
                    'targetId': entry.get('targetId') or entry.get('target_id') or sys_doc.id,
                    'device_type': entry.get('device_type') or entry.get('device') or '',
                    'ip': _extract_ip_value(entry),
                    'outcome': entry.get('outcome') or 'SUCCESS',
                    'message': details,
                    'municipality': entry_muni,
                    'region': entry_region,
                    'scope': 'MUNICIPAL',
                })
                system_fallback_count += 1
        except Exception as e:
            print(f"[WARN] Failed loading fallback system_logs source for regional system logs: {e}")

        # De-duplicate entries that can appear in both sources.
        deduped = []
        seen = set()
        for row in logs:
            key = (
                str(row.get('id') or ''),
                str(row.get('ts') or ''),
                str(row.get('user') or '').lower(),
                str(row.get('action') or '').upper(),
                str(row.get('targetId') or ''),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        logs = deduped

        logs.sort(key=lambda x: x.get('ts') or '', reverse=True)
        logs = logs[:40]
        print(
            f"[DEBUG] Regional system logs -> region={user_region}, municipalities={len(municipality_set)}, "
            f"scoped_users={len(scoped_emails)}, regional_source={regional_source_count}, "
            f"audit_fallback={audit_fallback_count}, system_fallback={system_fallback_count}, returned={len(logs)}"
        )
        return jsonify({'success': True, 'logs': logs, 'region': user_region}), 200
    except Exception as e:
        print(f"[ERROR] Regional system logs failed: {e}")
        return jsonify({'success': False, 'error': str(e), 'logs': []}), 200


@bp.route('/api/system-logs/cleanup', methods=['POST'])
@role_required('regional','regional_admin')
def api_regional_system_logs_cleanup():
    """Manually run retention cleanup for expired regional system logs."""
    try:
        body = request.get_json(silent=True) or {}

        # Safe bounds to prevent expensive accidental runs.
        requested_batch = int(body.get('batch_size', 200) or 200)
        requested_rounds = int(body.get('rounds', 1) or 1)

        batch_size = max(1, min(requested_batch, 500))
        rounds = max(1, min(requested_rounds, 20))

        total_deleted = 0
        for _ in range(rounds):
            deleted = system_logs_storage.prune_expired_regional_system_logs(batch_size=batch_size)
            total_deleted += deleted
            if deleted < batch_size:
                break

        return jsonify({
            'success': True,
            'deleted': total_deleted,
            'batch_size': batch_size,
            'rounds': rounds,
        }), 200
    except Exception as e:
        print(f"[ERROR] Regional system logs cleanup failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/forwarded-logs', methods=['GET'])
@role_required('regional','regional_admin')
def api_regional_forwarded_audit_logs():
    """Return forwarded municipal transaction logs for regional review/audit."""
    try:
        db = get_firestore_db()
        user_region, municipality_set = _resolve_regional_scope(db)

        logs = []
        tx_docs = db.collection('transactions').limit(5000).stream()

        for tx_doc in tx_docs:
            tx = tx_doc.to_dict() or {}

            if not _transaction_in_regional_scope(tx, user_region, municipality_set):
                continue

            status = str(tx.get('status') or '').strip().upper()
            forwarded_message = str(tx.get('forwarded_message') or tx.get('forwardMessage') or '').strip()
            forwarded_flag = bool(tx.get('forwarded_to_region')) or status == 'FORWARDED' or bool(forwarded_message)
            reviewed_flag = (
                status in {'APPROVED', 'REJECTED'}
                and (
                    str(tx.get('approvedByLevel') or '').strip().lower() == 'regional'
                    or str(tx.get('rejectedByLevel') or '').strip().lower() == 'regional'
                    or bool(tx.get('reviewed_from_forwarded'))
                )
            )

            if not (forwarded_flag or reviewed_flag):
                continue

            ts_value = (
                tx.get('forwarded_at')
                or tx.get('updated_at')
                or tx.get('created_at')
                or tx.get('createdAt')
                or tx.get('updatedAt')
            )
            status_value = status or 'FORWARDED'
            outcome_value = 'SUCCESS' if status_value == 'APPROVED' else ('FAIL' if status_value == 'REJECTED' else 'WARN')

            logs.append({
                'id': tx_doc.id,
                'ts': _normalize_ts_for_json(ts_value),
                'user': tx.get('forwarded_by') or tx.get('updated_by') or tx.get('user_email') or 'Municipal Admin',
                'role': 'Municipal',
                'module': 'PAYMENTS',
                'action': status_value,
                'target': tx.get('transaction_name') or tx.get('description') or 'Payment',
                'targetId': tx.get('invoice_id') or tx.get('external_id') or tx_doc.id,
                'ip': _extract_ip_value(tx),
                'outcome': outcome_value,
                'message': tx.get('description') or '',
                'forwarded_message': forwarded_message,
                'forwarded_by': tx.get('forwarded_by') or tx.get('updated_by') or '',
                'forwarded_at': _normalize_ts_for_json(tx.get('forwarded_at')),
                'municipality': tx.get('municipality') or tx.get('municipality_name') or tx.get('target_municipality') or '',
                'region': get_firestore_region_name(tx.get('region') or tx.get('region_name') or tx.get('regionName')),
                'diff': tx,
            })

        logs = [l for l in logs if l.get('ts')]
        logs.sort(key=lambda x: x.get('ts') or '', reverse=True)
        return jsonify({'success': True, 'logs': logs, 'region': user_region}), 200
    except Exception as e:
        print(f"[ERROR] Regional forwarded audit logs failed: {e}")
        return jsonify({'success': False, 'error': str(e), 'logs': []}), 200


@bp.route('/api/audit/forwarded-logs/<log_id>/decision', methods=['POST'])
@role_required('regional','regional_admin')
def api_regional_forwarded_audit_decision(log_id):
    """Approve or reject a forwarded municipal transaction from regional audit."""
    try:
        payload = request.get_json(silent=True) or {}
        decision = str(payload.get('decision') or '').strip().upper()
        decision_note = str(payload.get('note') or '').strip()

        if decision not in {'APPROVED', 'REJECTED'}:
            return jsonify({'success': False, 'error': 'decision must be APPROVED or REJECTED'}), 400

        db = get_firestore_db()
        user_region, municipality_set = _resolve_regional_scope(db)

        tx_ref = db.collection('transactions').document(log_id)
        tx_doc = tx_ref.get()
        if not tx_doc.exists:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404

        tx_data = tx_doc.to_dict() or {}

        # Robust scope validation: do not rely on municipality/region fields alone.
        in_scope_by_fields = _transaction_in_regional_scope(tx_data, user_region, municipality_set)

        tx_forwarded_region = get_firestore_region_name(
            tx_data.get('forwarded_region') or tx_data.get('forwardedRegion')
        )
        tx_forwarded_region_norm = str(tx_forwarded_region or '').strip().upper()
        user_region_norm = str(user_region or '').strip().upper()
        in_scope_by_forwarded_region = bool(user_region_norm and tx_forwarded_region_norm and tx_forwarded_region_norm == user_region_norm)

        tx_email = str(
            tx_data.get('user_email')
            or tx_data.get('userEmail')
            or tx_data.get('email')
            or tx_data.get('payer_email')
            or tx_data.get('payerEmail')
            or tx_data.get('customer_email')
            or tx_data.get('customerEmail')
            or ''
        ).strip().lower()
        tx_user_id = str(tx_data.get('userId') or tx_data.get('user_id') or tx_data.get('uid') or '').strip()

        scoped_emails = set()
        scoped_user_ids = set()
        try:
            users_docs = db.collection('users').limit(5000).stream()
            for user_doc in users_docs:
                ud = user_doc.to_dict() or {}
                u_email = str(ud.get('email') or '').strip().lower()
                u_muni = str(ud.get('municipality') or ud.get('municipality_name') or '').strip().lower()
                u_region = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
                u_region_norm = str(u_region or '').strip().upper()

                in_scope_user = bool(
                    (municipality_set and u_muni and u_muni in municipality_set)
                    or (user_region_norm and u_region_norm and u_region_norm == user_region_norm)
                    or (not user_region_norm and not municipality_set)
                )
                if not in_scope_user:
                    continue

                if u_email:
                    scoped_emails.add(u_email)
                scoped_user_ids.add(str(user_doc.id).strip())
                for pid in (ud.get('uid'), ud.get('user_id'), ud.get('userId'), ud.get('id')):
                    if pid:
                        scoped_user_ids.add(str(pid).strip())
        except Exception as e:
            print(f"[WARN] Failed building decision user scope: {e}")

        in_scope_by_user = bool((tx_email and tx_email in scoped_emails) or (tx_user_id and tx_user_id in scoped_user_ids))

        if not (in_scope_by_fields or in_scope_by_forwarded_region or in_scope_by_user):
            print(
                f"[WARN] Regional decision blocked by scope: tx={log_id}, user_region={user_region}, "
                f"tx_region={tx_data.get('region')}, tx_muni={tx_data.get('municipality')}, "
                f"forwarded_region={tx_data.get('forwarded_region')}, tx_email={tx_email}, tx_user_id={tx_user_id}"
            )
            return jsonify({'success': False, 'error': 'Out of regional scope'}), 403

        current_status = str(tx_data.get('status') or '').strip().upper()
        is_forwarded_context = bool(tx_data.get('forwarded_to_region')) or bool(tx_data.get('forwarded_message')) or current_status == 'FORWARDED'
        if not is_forwarded_context:
            return jsonify({'success': False, 'error': 'Transaction is not in forwarded-to-region context'}), 400

        update_payload = {
            'status': decision,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': session.get('user_email', 'system'),
            'reviewed_from_forwarded': True,
            'regional_reviewed_at': firestore.SERVER_TIMESTAMP,
            'regional_reviewed_by': session.get('user_email', 'system'),
        }

        if decision_note:
            update_payload['regional_decision_note'] = decision_note

        if decision == 'APPROVED':
            update_payload.update({
                'approvedByRegional': session.get('user_email', 'system'),
                'approvedByLevel': 'Regional',
                'approvedAtRegional': firestore.SERVER_TIMESTAMP,
            })
        else:
            update_payload.update({
                'rejectedByRegional': session.get('user_email', 'system'),
                'rejectedByLevel': 'Regional',
                'rejectedAtRegional': firestore.SERVER_TIMESTAMP,
            })

        tx_ref.update(update_payload)
        return jsonify({'success': True, 'id': log_id, 'status': decision}), 200
    except Exception as e:
        print(f"[ERROR] Regional forwarded decision failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/system-logs') 
@role_required('regional','regional_admin')
def system_logs_view():
    db = get_firestore_db()
    user_region, municipality_set = _resolve_regional_scope(db)
    municipalities = sorted({m.title() for m in municipality_set})

    # Optional user filter list in UI; derived from scoped municipal users.
    system_users = []
    try:
        user_region_norm = str(user_region or '').strip().upper()
        users_docs = db.collection('users').limit(5000).stream()
        for user_doc in users_docs:
            ud = user_doc.to_dict() or {}
            role_value = str(ud.get('role') or '').strip().lower()
            if role_value not in {'municipal_admin', 'municipal'}:
                continue

            u_email = str(ud.get('email') or '').strip()
            u_muni = str(ud.get('municipality') or ud.get('municipality_name') or '').strip().lower()
            u_region = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
            u_region_norm = str(u_region or '').strip().upper()

            in_scope = bool(
                (municipality_set and u_muni and u_muni in municipality_set)
                or (user_region_norm and u_region_norm and _same_region(u_region_norm, user_region_norm))
                or (not user_region_norm and not municipality_set)
            )
            if in_scope and u_email:
                system_users.append(u_email)
    except Exception as e:
        print(f"[WARN] Failed loading scoped system users for logs view: {e}")

    return render_template(
        'regional/logs/system-logs.html',
        user_region=user_region,
        municipalities=municipalities,
        system_users=sorted(set(system_users)),
    )

@bp.route('/application-view/<application_id>')
@role_required('regional','regional_admin')
def application_view(application_id):
    return render_template('regional/application-regional-view.html')

@bp.route('/hrm/company')
@role_required('regional','regional_admin')
def company_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] company_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch company region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/company-regional.html', region_name=region_name)

@bp.route('/hrm/departments')
@role_required('regional','regional_admin')
def departments_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] departments_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch department region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/department-regional.html', region_name=region_name)

@bp.route('/hrm/designations')
@role_required('regional','regional_admin')
def designations_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] designations_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch designation region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/designation-regional.html', region_name=region_name)

@bp.route('/hrm/office-shifts')
@role_required('regional','regional_admin')
def office_shifts_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] office_shifts_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch office-shift region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/office-shift-regional.html', region_name=region_name)

@bp.route('/api/hrm/office-shifts', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_office_shifts():
    db = get_firestore_db()
    shifts = []

    try:
        docs = db.collection('office_shifts').stream()
    except Exception:
        docs = []

    for doc in docs:
        item = doc.to_dict() or {}
        shifts.append({
            'id': doc.id,
            'shift_code': item.get('shift_code') or item.get('code') or '',
            'shift_name': item.get('shift_name') or item.get('name') or '',
            'scope': (item.get('scope') or 'REGIONAL').upper(),
            'shift_type': item.get('shift_type') or item.get('type') or 'Fixed',
            'time_in': item.get('time_in') or '',
            'time_out': item.get('time_out') or '',
            'time_in_early': item.get('time_in_early') or '',
            'time_in_late': item.get('time_in_late') or '',
            'time_out_early': item.get('time_out_early') or '',
            'time_out_late': item.get('time_out_late') or '',
            'grace_minutes': item.get('grace_minutes') if item.get('grace_minutes') is not None else 15,
            'break_policy': item.get('break_policy') or '1 HOUR',
            'status': item.get('status') or 'Active'
        })

    # Seed from employees collection when office_shifts has no records yet
    if not shifts:
        try:
            employee_docs = list(db.collection('employees').stream())
            generated_shifts = {}

            def infer_scope(emp):
                explicit_scope = (emp.get('scope') or '').strip().upper()
                if explicit_scope in ('REGIONAL', 'MUNICIPAL'):
                    return explicit_scope
                role = (emp.get('role') or '').strip().lower()
                if 'municipal' in role:
                    return 'MUNICIPAL'
                return 'REGIONAL'

            def infer_type(emp):
                duty_type = (emp.get('duty_type') or '').strip().lower()
                if 'flex' in duty_type:
                    return 'Flexi'
                return 'Fixed'

            def default_times(shift_type):
                if shift_type == 'Flexi':
                    return {
                        'time_in': '',
                        'time_out': '',
                        'time_in_early': '07:00',
                        'time_in_late': '09:00',
                        'time_out_early': '16:00',
                        'time_out_late': '18:00',
                        'grace_minutes': 0,
                        'break_policy': '1 HOUR',
                    }
                return {
                    'time_in': '08:00',
                    'time_out': '17:00',
                    'time_in_early': '',
                    'time_in_late': '',
                    'time_out_early': '',
                    'time_out_late': '',
                    'grace_minutes': 15,
                    'break_policy': '1 HOUR',
                }

            reg_count = 0
            mun_count = 0

            for employee_doc in employee_docs:
                emp = employee_doc.to_dict() or {}
                scope = infer_scope(emp)
                shift_type = infer_type(emp)
                key = f"{scope}|{shift_type}"

                if key not in generated_shifts:
                    if scope == 'REGIONAL':
                        reg_count += 1
                        shift_code = f"R-SFT-{reg_count:03d}" if shift_type == 'Fixed' else f"R-SFT-F{reg_count:02d}"
                    else:
                        mun_count += 1
                        shift_code = f"M-SFT-{mun_count:03d}" if shift_type == 'Fixed' else f"M-SFT-F{mun_count:02d}"

                    timing = default_times(shift_type)
                    generated_shifts[key] = {
                        'shift_code': shift_code,
                        'shift_name': f"{scope.title()} {shift_type} Schedule",
                        'scope': scope,
                        'shift_type': shift_type,
                        'time_in': timing['time_in'],
                        'time_out': timing['time_out'],
                        'time_in_early': timing['time_in_early'],
                        'time_in_late': timing['time_in_late'],
                        'time_out_early': timing['time_out_early'],
                        'time_out_late': timing['time_out_late'],
                        'grace_minutes': timing['grace_minutes'],
                        'break_policy': timing['break_policy'],
                        'status': 'Active'
                    }

                chosen_shift = generated_shifts[key]
                employee_doc.reference.set({
                    'shift_code': chosen_shift['shift_code'],
                    'shift_name': chosen_shift['shift_name'],
                    'shift_scope': chosen_shift['scope'],
                    'shift_type': chosen_shift['shift_type'],
                    'shift_time_in': chosen_shift['time_in'],
                    'shift_time_out': chosen_shift['time_out'],
                    'shift_time_in_early': chosen_shift['time_in_early'],
                    'shift_time_in_late': chosen_shift['time_in_late'],
                    'shift_time_out_early': chosen_shift['time_out_early'],
                    'shift_time_out_late': chosen_shift['time_out_late'],
                    'shift_grace_minutes': chosen_shift['grace_minutes'],
                    'shift_break_policy': chosen_shift['break_policy'],
                }, merge=True)

            for seed in generated_shifts.values():
                existing = db.collection('office_shifts').where(filter=FieldFilter('shift_code', '==', seed['shift_code'])).limit(1).stream()
                if not any(True for _ in existing):
                    db.collection('office_shifts').document().set(seed)

            # If employees collection is empty, still seed minimum demo records for UI
            if not generated_shifts:
                demo = [
                    {
                        'shift_code': 'R-SFT-001',
                        'shift_name': 'Regional Fixed Schedule',
                        'scope': 'REGIONAL',
                        'shift_type': 'Fixed',
                        'time_in': '08:00',
                        'time_out': '17:00',
                        'time_in_early': '',
                        'time_in_late': '',
                        'time_out_early': '',
                        'time_out_late': '',
                        'grace_minutes': 15,
                        'break_policy': '1 HOUR',
                        'status': 'Active'
                    },
                    {
                        'shift_code': 'R-SFT-F01',
                        'shift_name': 'Regional Flexi Schedule',
                        'scope': 'REGIONAL',
                        'shift_type': 'Flexi',
                        'time_in': '',
                        'time_out': '',
                        'time_in_early': '07:00',
                        'time_in_late': '09:00',
                        'time_out_early': '16:00',
                        'time_out_late': '18:00',
                        'grace_minutes': 0,
                        'break_policy': '1 HOUR',
                        'status': 'Active'
                    },
                    {
                        'shift_code': 'M-SFT-001',
                        'shift_name': 'Municipal Fixed Schedule',
                        'scope': 'MUNICIPAL',
                        'shift_type': 'Fixed',
                        'time_in': '08:00',
                        'time_out': '17:00',
                        'time_in_early': '',
                        'time_in_late': '',
                        'time_out_early': '',
                        'time_out_late': '',
                        'grace_minutes': 15,
                        'break_policy': '1 HOUR',
                        'status': 'Active'
                    }
                ]
                for seed in demo:
                    db.collection('office_shifts').document().set(seed)

            # Reload seeded shifts
            shifts = []
            for doc in db.collection('office_shifts').stream():
                item = doc.to_dict() or {}
                shifts.append({
                    'id': doc.id,
                    'shift_code': item.get('shift_code') or item.get('code') or '',
                    'shift_name': item.get('shift_name') or item.get('name') or '',
                    'scope': (item.get('scope') or 'REGIONAL').upper(),
                    'shift_type': item.get('shift_type') or item.get('type') or 'Fixed',
                    'time_in': item.get('time_in') or '',
                    'time_out': item.get('time_out') or '',
                    'time_in_early': item.get('time_in_early') or '',
                    'time_in_late': item.get('time_in_late') or '',
                    'time_out_early': item.get('time_out_early') or '',
                    'time_out_late': item.get('time_out_late') or '',
                    'grace_minutes': item.get('grace_minutes') if item.get('grace_minutes') is not None else 15,
                    'break_policy': item.get('break_policy') or '1 HOUR',
                    'status': item.get('status') or 'Active'
                })
        except Exception as e:
            print(f"[ERROR] Failed seeding office shifts from employees: {e}")

    shifts.sort(key=lambda item: item.get('shift_code') or '')
    return jsonify({'success': True, 'shifts': shifts})

@bp.route('/api/hrm/office-shifts', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_office_shift():
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    shift_code = (data.get('shift_code') or '').strip().upper()
    shift_name = (data.get('shift_name') or '').strip()

    if not shift_code or not shift_name:
        return jsonify({'success': False, 'error': 'Shift code and shift name are required'}), 400

    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'

    db = get_firestore_db()
    duplicate = db.collection('office_shifts').where(filter=FieldFilter('shift_code', '==', shift_code)).limit(1).stream()
    if any(True for _ in duplicate):
        return jsonify({'success': False, 'error': 'Shift code already exists'}), 409

    payload = {
        'shift_code': shift_code,
        'shift_name': shift_name,
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'shift_type': (data.get('shift_type') or 'Fixed').strip(),
        'time_in': (data.get('time_in') or '').strip(),
        'time_out': (data.get('time_out') or '').strip(),
        'time_in_early': (data.get('time_in_early') or '').strip(),
        'time_in_late': (data.get('time_in_late') or '').strip(),
        'time_out_early': (data.get('time_out_early') or '').strip(),
        'time_out_late': (data.get('time_out_late') or '').strip(),
        'grace_minutes': int(data.get('grace_minutes') or 0),
        'break_policy': (data.get('break_policy') or '1 HOUR').strip(),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }

    ref = db.collection('office_shifts').document()
    ref.set(payload)
    return jsonify({'success': True, 'id': ref.id})

@bp.route('/api/hrm/office-shifts/<shift_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_office_shift(shift_id):
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    shift_code = (data.get('shift_code') or '').strip().upper()
    shift_name = (data.get('shift_name') or '').strip()

    if not shift_code or not shift_name:
        return jsonify({'success': False, 'error': 'Shift code and shift name are required'}), 400

    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'

    db = get_firestore_db()
    payload = {
        'shift_code': shift_code,
        'shift_name': shift_name,
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'shift_type': (data.get('shift_type') or 'Fixed').strip(),
        'time_in': (data.get('time_in') or '').strip(),
        'time_out': (data.get('time_out') or '').strip(),
        'time_in_early': (data.get('time_in_early') or '').strip(),
        'time_in_late': (data.get('time_in_late') or '').strip(),
        'time_out_early': (data.get('time_out_early') or '').strip(),
        'time_out_late': (data.get('time_out_late') or '').strip(),
        'grace_minutes': int(data.get('grace_minutes') or 0),
        'break_policy': (data.get('break_policy') or '1 HOUR').strip(),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }

    db.collection('office_shifts').document(shift_id).set(payload, merge=True)
    return jsonify({'success': True})

@bp.route('/api/hrm/designations', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_designations():
    db = get_firestore_db()
    designations = []

    # First check if designations collection exists and has data
    desig_docs = list(db.collection('designations').limit(1).stream())
    
    if not desig_docs:
        # Auto-seed from employees collection
        employee_docs = list(db.collection('employees').stream())
        
        # Group employees by designation to count headcount
        desig_map = {}
        
        for employee_doc in employee_docs:
            emp = employee_doc.to_dict() or {}
            
            # Infer designation details from employee
            designation_title = emp.get('designation') or emp.get('position') or 'Staff'
            
            # Infer scope
            scope = (emp.get('scope') or '').strip().upper()
            if scope not in ('REGIONAL', 'MUNICIPAL'):
                role = (emp.get('role') or '').strip().lower()
                scope = 'MUNICIPAL' if 'municipal' in role else 'REGIONAL'
            
            # Infer salary grade from employee
            salary_grade = emp.get('salary_grade') or 'SG-15'
            
            # Infer category from designation title
            title_lower = designation_title.lower()
            if any(word in title_lower for word in ['director', 'chief', 'manager', 'head', 'officer']):
                category = 'Executive'
            elif any(word in title_lower for word in ['accountant', 'cashier', 'budget', 'finance']):
                category = 'Financial'
            elif any(word in title_lower for word in ['engineer', 'technician', 'specialist', 'analyst', 'it']):
                category = 'Technical'
            else:
                category = 'Administrative'
            
            # Create unique key for this designation
            key = f"{scope}|{designation_title}|{salary_grade}"
            
            if key not in desig_map:
                desig_map[key] = {
                    'title': designation_title,
                    'scope': scope,
                    'salary_grade': salary_grade,
                    'category': category,
                    'headcount': 0
                }
            
            desig_map[key]['headcount'] += 1
            
            # Backfill designation fields to employee document
            employee_doc.reference.set({
                'designation_title': designation_title,
                'designation_scope': scope,
                'designation_salary_grade': salary_grade,
                'designation_category': category,
                'designation_status': 'Active'
            }, merge=True)
        
        # Generate unique codes and save to designations collection
        reg_count = 0
        mun_count = 0
        
        for key, desig_data in desig_map.items():
            scope = desig_data['scope']
            
            if scope == 'REGIONAL':
                reg_count += 1
                code = f"R-DSG-{reg_count:03d}"
            else:
                mun_count += 1
                code = f"M-DSG-{mun_count:03d}"
            
            designation_doc = {
                'designation_code': code,
                'designation_title': desig_data['title'],
                'scope': scope,
                'salary_grade': desig_data['salary_grade'],
                'category': desig_data['category'],
                'headcount': desig_data['headcount'],
                'status': 'Active'
            }
            
            db.collection('designations').add(designation_doc)
    
    # Now fetch all designations
    for doc in db.collection('designations').stream():
        item = doc.to_dict() or {}
        
        designations.append({
            'id': doc.id,
            'designation_code': item.get('designation_code', ''),
            'designation_title': item.get('designation_title', ''),
            'scope': (item.get('scope') or 'REGIONAL').upper(),
            'salary_grade': item.get('salary_grade', 'SG-15'),
            'category': item.get('category', 'Administrative'),
            'headcount': item.get('headcount', 0),
            'status': item.get('status', 'Active')
        })
    
    designations.sort(key=lambda d: d.get('designation_code') or '')
    return jsonify({'success': True, 'designations': designations})

@bp.route('/api/hrm/designations', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_designation():
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    designation_code = (data.get('designation_code') or '').strip()
    designation_title = (data.get('designation_title') or '').strip()
    
    if not designation_code or not designation_title:
        return jsonify({'success': False, 'error': 'Designation code and title are required'}), 400
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'designation_code': designation_code,
        'designation_title': designation_title,
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'salary_grade': (data.get('salary_grade') or 'SG-15').strip(),
        'category': (data.get('category') or 'Administrative').strip(),
        'headcount': int(data.get('headcount') or 0),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('designations').add(payload)
    return jsonify({'success': True})

@bp.route('/api/hrm/designations/<designation_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_designation(designation_id):
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'designation_code': (data.get('designation_code') or '').strip(),
        'designation_title': (data.get('designation_title') or '').strip(),
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'salary_grade': (data.get('salary_grade') or 'SG-15').strip(),
        'category': (data.get('category') or 'Administrative').strip(),
        'headcount': int(data.get('headcount') or 0),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('designations').document(designation_id).set(payload, merge=True)
    return jsonify({'success': True})

@bp.route('/api/hrm/departments', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_departments():
    db = get_firestore_db()
    departments = []

    # First check if departments collection exists and has data
    dept_docs = list(db.collection('departments').limit(1).stream())
    
    if not dept_docs:
        # Auto-seed from employees collection
        employee_docs = list(db.collection('employees').stream())
        
        # Group employees by department to count headcount
        dept_map = {}
        
        for employee_doc in employee_docs:
            emp = employee_doc.to_dict() or {}
            
            # Infer department details from employee
            department_name = emp.get('department_name') or emp.get('division') or emp.get('section') or 'General Office'
            
            # Infer scope
            scope = (emp.get('scope') or '').strip().upper()
            if scope not in ('REGIONAL', 'MUNICIPAL'):
                role = (emp.get('role') or '').strip().lower()
                scope = 'MUNICIPAL' if 'municipal' in role else 'REGIONAL'
            
            # Infer parent department (most departments report to main office)
            parent_code = 'REG-RO' if scope == 'REGIONAL' else 'MUN-RO'
            
            # Infer head from employee (if they have 'director', 'chief', 'head', 'manager' in designation)
            designation = (emp.get('designation') or '').lower()
            is_head = any(word in designation for word in ['director', 'chief', 'head', 'manager', 'officer'])
            
            # Create unique key for this department
            key = f"{scope}|{department_name}"
            
            if key not in dept_map:
                dept_map[key] = {
                    'name': department_name,
                    'scope': scope,
                    'parent_code': parent_code,
                    'head_name': '',
                    'headcount': 0,
                    'status': 'Active'
                }
            
            dept_map[key]['headcount'] += 1
            
            # Assign head if this employee looks like a department head
            if is_head and not dept_map[key]['head_name']:
                full_name = f"{emp.get('first_name', '')} {emp.get('middle_name', '')} {emp.get('last_name', '')}".strip()
                dept_map[key]['head_name'] = full_name
            
            # Backfill department fields to employee document
            employee_doc.reference.set({
                'department_code': f"{scope[:3]}-{department_name[:3].upper()}",
                'department_name': department_name,
                'department_scope': scope,
                'department_parent': parent_code,
                'department_status': 'Active'
            }, merge=True)
        
        # Generate unique codes and save to departments collection
        reg_count = 0
        mun_count = 0
        
        for key, dept_data in dept_map.items():
            scope = dept_data['scope']
            name = dept_data['name']
            
            if scope == 'REGIONAL':
                reg_count += 1
                code = f"R-DPT-{reg_count:03d}"
            else:
                mun_count += 1
                code = f"M-DPT-{mun_count:03d}"
            
            department_doc = {
                'department_code': code,
                'department_name': name,
                'scope': scope,
                'parent_code': dept_data['parent_code'],
                'head_name': dept_data['head_name'] or 'TBA',
                'headcount': dept_data['headcount'],
                'status': dept_data['status']
            }
            
            db.collection('departments').add(department_doc)
    
    # Now fetch all departments
    for doc in db.collection('departments').stream():
        item = doc.to_dict() or {}
        
        departments.append({
            'id': doc.id,
            'department_code': item.get('department_code', ''),
            'department_name': item.get('department_name', ''),
            'scope': (item.get('scope') or 'REGIONAL').upper(),
            'parent_code': item.get('parent_code', ''),
            'head_name': item.get('head_name', 'TBA'),
            'headcount': item.get('headcount', 0),
            'status': item.get('status', 'Active')
        })
    
    departments.sort(key=lambda d: d.get('department_code') or '')
    return jsonify({'success': True, 'departments': departments})

@bp.route('/api/hrm/departments', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_department():
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    department_code = (data.get('department_code') or '').strip()
    department_name = (data.get('department_name') or '').strip()
    
    if not department_code or not department_name:
        return jsonify({'success': False, 'error': 'Department code and name are required'}), 400
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'department_code': department_code,
        'department_name': department_name,
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'parent_code': (data.get('parent_code') or '').strip(),
        'head_name': (data.get('head_name') or 'TBA').strip(),
        'headcount': int(data.get('headcount') or 0),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('departments').add(payload)
    return jsonify({'success': True})

@bp.route('/api/hrm/departments/<department_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_department(department_id):
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'department_code': (data.get('department_code') or '').strip(),
        'department_name': (data.get('department_name') or '').strip(),
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
        'parent_code': (data.get('parent_code') or '').strip(),
        'head_name': (data.get('head_name') or 'TBA').strip(),
        'headcount': int(data.get('headcount') or 0),
        'region': region_name,
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('departments').document(department_id).set(payload, merge=True)
    return jsonify({'success': True})

@bp.route('/api/hrm/municipal-offices', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_municipal_offices():
    from firebase_admin import firestore

    db = get_firestore_db()
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    offices = []

    # Check if there are any municipal offices for this region
    existing_docs = list(db.collection('municipal_offices').where(filter=FieldFilter('region', '==', region_name)).limit(1).stream())
    
    if not existing_docs:
        # Auto-seed municipalities based on region
        region_municipalities = {
            'CALABARZON': [
                # Cavite Province
                {'name': 'Bacoor', 'province': 'Cavite', 'code': 'MUN-CAV-001', 'status': 'Active'},
                {'name': 'Imus', 'province': 'Cavite', 'code': 'MUN-CAV-002', 'status': 'Active'},
                {'name': 'Dasmariñas', 'province': 'Cavite', 'code': 'MUN-CAV-003', 'status': 'Active'},
                {'name': 'Cavite City', 'province': 'Cavite', 'code': 'MUN-CAV-004', 'status': 'Active'},
                {'name': 'Tagaytay', 'province': 'Cavite', 'code': 'MUN-CAV-005', 'status': 'Active'},
                {'name': 'Trece Martires', 'province': 'Cavite', 'code': 'MUN-CAV-006', 'status': 'Active'},
                
                # Laguna Province
                {'name': 'Santa Rosa', 'province': 'Laguna', 'code': 'MUN-LAG-001', 'status': 'Active'},
                {'name': 'Calamba', 'province': 'Laguna', 'code': 'MUN-LAG-002', 'status': 'Active'},
                {'name': 'Biñan', 'province': 'Laguna', 'code': 'MUN-LAG-003', 'status': 'Active'},
                {'name': 'San Pedro', 'province': 'Laguna', 'code': 'MUN-LAG-004', 'status': 'Active'},
                {'name': 'Cabuyao', 'province': 'Laguna', 'code': 'MUN-LAG-005', 'status': 'Active'},
                {'name': 'Los Baños', 'province': 'Laguna', 'code': 'MUN-LAG-006', 'status': 'Active'},
                
                # Batangas Province
                {'name': 'Batangas City', 'province': 'Batangas', 'code': 'MUN-BAT-001', 'status': 'Active'},
                {'name': 'Lipa', 'province': 'Batangas', 'code': 'MUN-BAT-002', 'status': 'Active'},
                {'name': 'Tanauan', 'province': 'Batangas', 'code': 'MUN-BAT-003', 'status': 'Active'},
                {'name': 'Santo Tomas', 'province': 'Batangas', 'code': 'MUN-BAT-004', 'status': 'Active'},
                {'name': 'Taal', 'province': 'Batangas', 'code': 'MUN-BAT-005', 'status': 'Active'},
                
                # Rizal Province
                {'name': 'Antipolo', 'province': 'Rizal', 'code': 'MUN-RIZ-001', 'status': 'Active'},
                {'name': 'Cainta', 'province': 'Rizal', 'code': 'MUN-RIZ-002', 'status': 'Active'},
                {'name': 'Taytay', 'province': 'Rizal', 'code': 'MUN-RIZ-003', 'status': 'Active'},
                {'name': 'Binangonan', 'province': 'Rizal', 'code': 'MUN-RIZ-004', 'status': 'Active'},
                {'name': 'Rodriguez', 'province': 'Rizal', 'code': 'MUN-RIZ-005', 'status': 'Active'},
                
                # Quezon Province
                {'name': 'Lucena City', 'province': 'Quezon', 'code': 'MUN-QUE-001', 'status': 'Active'},
                {'name': 'Tayabas', 'province': 'Quezon', 'code': 'MUN-QUE-002', 'status': 'Active'},
                {'name': 'Sariaya', 'province': 'Quezon', 'code': 'MUN-QUE-003', 'status': 'Active'},
                {'name': 'Candelaria', 'province': 'Quezon', 'code': 'MUN-QUE-004', 'status': 'Active'},
                {'name': 'Tiaong', 'province': 'Quezon', 'code': 'MUN-QUE-005', 'status': 'Active'},
            ],
            'MIMAROPA': [
                # Marinduque Province
                {'name': 'Boac', 'province': 'Marinduque', 'code': 'MUN-MAR-001', 'status': 'Active'},
                {'name': 'Santa Cruz', 'province': 'Marinduque', 'code': 'MUN-MAR-002', 'status': 'Active'},
                {'name': 'Buenavista', 'province': 'Marinduque', 'code': 'MUN-MAR-003', 'status': 'Active'},
                {'name': 'Gasan', 'province': 'Marinduque', 'code': 'MUN-MAR-004', 'status': 'Active'},
                {'name': 'Mogpog', 'province': 'Marinduque', 'code': 'MUN-MAR-005', 'status': 'Active'},
                
                # Occidental Mindoro Province
                {'name': 'Puerto Princesa', 'province': 'Occidental Mindoro', 'code': 'MUN-OCM-001', 'status': 'Active'},
                {'name': 'San Jose', 'province': 'Occidental Mindoro', 'code': 'MUN-OCM-002', 'status': 'Active'},
                {'name': 'Mamburao', 'province': 'Occidental Mindoro', 'code': 'MUN-OCM-003', 'status': 'Active'},
                
                # Oriental Mindoro Province
                {'name': 'Calapan', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-001', 'status': 'Active'},
                {'name': 'Roxas', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-002', 'status': 'Active'},
                {'name': 'Bongabong', 'province': 'Oriental Mindoro', 'code': 'MUN-ORM-003', 'status': 'Active'},
                
                # Palawan Province
                {'name': 'Puerto Princesa', 'province': 'Palawan', 'code': 'MUN-PAL-001', 'status': 'Active'},
                {'name': 'Coron', 'province': 'Palawan', 'code': 'MUN-PAL-002', 'status': 'Active'},
                {'name': 'El Nido', 'province': 'Palawan', 'code': 'MUN-PAL-003', 'status': 'Active'},
                {'name': 'Brooke\'s Point', 'province': 'Palawan', 'code': 'MUN-PAL-004', 'status': 'Active'},
                
                # Romblon Province
                {'name': 'Odiongan', 'province': 'Romblon', 'code': 'MUN-ROM-001', 'status': 'Active'},
                {'name': 'Calatrava', 'province': 'Romblon', 'code': 'MUN-ROM-002', 'status': 'Active'},
                {'name': 'San Andres', 'province': 'Romblon', 'code': 'MUN-ROM-003', 'status': 'Active'},
            ]
        }
        
        municipalities = region_municipalities.get(region_name, [])
        
        for mun in municipalities:
            office_doc = {
                'office_code': mun['code'],
                'municipality_name': mun['name'],
                'province': mun['province'],
                'region': region_name,
                'status': mun['status']
            }
            db.collection('municipal_offices').add(office_doc)
    
    # Now fetch municipal offices for this region only
    for doc in db.collection('municipal_offices').where(filter=FieldFilter('region', '==', region_name)).stream():
        item = doc.to_dict() or {}
        
        offices.append({
            'id': doc.id,
            'office_code': item.get('office_code', ''),
            'municipality_name': item.get('municipality_name', ''),
            'province': item.get('province', ''),
            'region': item.get('region', region_name),
            'status': item.get('status', 'Active')
        })
    
    offices.sort(key=lambda o: (o.get('province') or '', o.get('municipality_name') or ''))
    return jsonify({'success': True, 'offices': offices})

@bp.route('/api/hrm/municipal-offices', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_municipal_office():
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    office_code = (data.get('office_code') or '').strip()
    municipality_name = (data.get('municipality_name') or '').strip()
    
    if not office_code or not municipality_name:
        return jsonify({'success': False, 'error': 'Office code and municipality name are required'}), 400
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'office_code': office_code,
        'municipality_name': municipality_name,
        'province': (data.get('province') or '').strip(),
        'region': region_name,  # Force user's region
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('municipal_offices').add(payload)
    return jsonify({'success': True})

@bp.route('/api/hrm/municipal-offices/<office_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_municipal_office(office_id):
    from firebase_admin import firestore

    data = request.get_json(silent=True) or {}
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    db = get_firestore_db()
    payload = {
        'office_code': (data.get('office_code') or '').strip(),
        'municipality_name': (data.get('municipality_name') or '').strip(),
        'province': (data.get('province') or '').strip(),
        'region': region_name,  # Force user's region
        'status': (data.get('status') or 'Active').strip()
    }
    
    db.collection('municipal_offices').document(office_id).set(payload, merge=True)
    return jsonify({'success': True})

@bp.route('/hrm/employees')
@role_required('regional','regional_admin')
def employees_view():
    from firebase_admin import firestore

    # Try to get region from session first
    region_name = session.get('region') or session.get('user_region')

    # If not in session, fetch from Firestore users collection
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] employees_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch employee region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/employee-regional.html', region_name=region_name)

@bp.route('/api/hrm/employees', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_employees():
    db = get_firestore_db()
    employees = []

    for doc in db.collection('employees').stream():
        item = doc.to_dict() or {}
        hire_date = item.get('hire_date')

        if isinstance(hire_date, str):
            item['hire_date'] = hire_date.split('T')[0]
        elif hasattr(hire_date, 'strftime'):
            item['hire_date'] = hire_date.strftime('%Y-%m-%d')
        elif hasattr(hire_date, 'isoformat'):
            item['hire_date'] = hire_date.isoformat().split('T')[0]
        elif hasattr(hire_date, 'to_datetime'):
            item['hire_date'] = hire_date.to_datetime().strftime('%Y-%m-%d')
        else:
            item['hire_date'] = ''

        employees.append({
            'id': doc.id,
            'employee_id': item.get('employee_id', ''),
            'first_name': item.get('first_name', ''),
            'middle_name': item.get('middle_name', ''),
            'last_name': item.get('last_name', ''),
            'email': item.get('email', ''),
            'designation': item.get('designation', ''),
            'department_name': item.get('department_name', ''),
            'division': item.get('division', ''),
            'scope': (item.get('scope') or 'REGIONAL').upper(),
            'employment_type': item.get('employment_type') or item.get('employmentType') or '',
            'status': item.get('status', 'Active'),
            'municipality': item.get('municipality', ''),
            'province': item.get('province', ''),
            'region': item.get('region') or item.get('regionName') or item.get('region_name') or '',
            'hire_date': item.get('hire_date', '')
        })

    employees.sort(key=lambda item: item.get('employee_id') or '')
    return jsonify({'success': True, 'employees': employees})

@bp.route('/api/hrm/employees', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_employee():
    data = request.get_json(silent=True) or {}

    employee_id = (data.get('employee_id') or '').strip()
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()

    if not employee_id or not first_name or not last_name:
        return jsonify({'success': False, 'error': 'Employee ID, First Name, and Last Name are required'}), 400

    db = get_firestore_db()
    duplicate = db.collection('employees').where(filter=FieldFilter('employee_id', '==', employee_id)).limit(1).stream()
    if any(True for _ in duplicate):
        return jsonify({'success': False, 'error': 'Employee ID already exists'}), 409

    region_name = session.get('region') or session.get('user_region') or ''

    payload = {
        'employee_id': employee_id,
        'first_name': first_name,
        'middle_name': (data.get('middle_name') or '').strip(),
        'last_name': last_name,
        'email': (data.get('email') or '').strip().lower(),
        'designation': (data.get('designation') or '').strip(),
        'department_name': (data.get('department_name') or '').strip(),
        'division': (data.get('division') or '').strip(),
        'scope': ((data.get('scope') or 'REGIONAL').strip().upper()),
        'employment_type': (data.get('employment_type') or '').strip(),
        'status': (data.get('status') or 'Active').strip(),
        'municipality': (data.get('municipality') or '').strip(),
        'province': (data.get('province') or '').strip(),
        'region': (data.get('region') or region_name or '').strip(),
        'hire_date': (data.get('hire_date') or '').strip(),
    }

    ref = db.collection('employees').document()
    ref.set(payload)
    return jsonify({'success': True, 'id': ref.id})

@bp.route('/hrm/attendance')
@role_required('regional','regional_admin')
def attendance_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] attendance_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch attendance region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/attendance-regional.html', region_name=region_name)

@bp.route('/api/hrm/attendance', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_attendance():
    from datetime import date

    db = get_firestore_db()
    records = []
    today_str = date.today().isoformat()

    employee_docs = db.collection('employees').stream()
    for employee_doc in employee_docs:
        emp = employee_doc.to_dict() or {}

        defaults = {}
        if 'attendance_date' not in emp:
            defaults['attendance_date'] = today_str
        if 'attendance_status' not in emp:
            defaults['attendance_status'] = 'Present'
        if 'attendance_remarks' not in emp:
            defaults['attendance_remarks'] = 'Regular'
        if 'time_in' not in emp:
            defaults['time_in'] = ''
        if 'time_out' not in emp:
            defaults['time_out'] = ''
        if 'working_hours' not in emp:
            defaults['working_hours'] = 0

        if defaults:
            employee_doc.reference.set(defaults, merge=True)
            emp.update(defaults)

        scope = (emp.get('scope') or '').strip().upper()
        if scope not in ('REGIONAL', 'MUNICIPAL'):
            role = (emp.get('role') or '').strip().lower()
            scope = 'MUNICIPAL' if 'municipal' in role else 'REGIONAL'

        status_raw = (emp.get('attendance_status') or '').strip()
        status_map = {
            'On Duty': 'Present',
            'Active': 'Present',
            'Present': 'Present',
            'Late': 'Late',
            'Undertime': 'Undertime',
            'Absent': 'Absent',
            'On Leave': 'Leave',
            'Leave': 'Leave'
        }
        status = status_map.get(status_raw, status_raw or 'Present')

        records.append({
            'id': employee_doc.id,
            'employee_id': emp.get('employee_id', ''),
            'full_name': f"{emp.get('last_name', '')}, {emp.get('first_name', '')} {emp.get('middle_name', '')}".strip().strip(','),
            'assignment': emp.get('department_name') or emp.get('division') or emp.get('designation') or '',
            'sub_assignment': f"{scope.title()} Office",
            'scope': scope,
            'date': emp.get('attendance_date') or today_str,
            'time_in': emp.get('time_in') or '',
            'time_out': emp.get('time_out') or '',
            'hours': emp.get('working_hours') or 0,
            'status': status,
            'remarks': emp.get('attendance_remarks') or 'Regular'
        })

    records.sort(key=lambda r: r.get('employee_id') or '')
    return jsonify({'success': True, 'records': records})

@bp.route('/api/hrm/attendance/adjust', methods=['PUT'])
@role_required('regional','regional_admin')
def adjust_regional_attendance():
    data = request.get_json(silent=True) or {}
    employee_doc_id = (data.get('employee_doc_id') or '').strip()
    attendance_date = (data.get('attendance_date') or '').strip()
    scope = (data.get('scope') or '').strip()
    time_in = (data.get('time_in') or '').strip()
    time_out = (data.get('time_out') or '').strip()
    reason = (data.get('reason') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not employee_doc_id:
        return jsonify({'success': False, 'error': 'Employee is required'}), 400

    # Compute working hours when time_in and time_out are both present
    working_hours = 0
    try:
        if time_in and time_out:
            from datetime import datetime
            in_dt = datetime.strptime(time_in, '%H:%M')
            out_dt = datetime.strptime(time_out, '%H:%M')
            delta = (out_dt - in_dt).total_seconds() / 3600
            working_hours = round(max(delta, 0), 2)
    except Exception:
        working_hours = 0

    status = 'Present'
    if not time_in and not time_out:
        status = 'Absent'

    db = get_firestore_db()
    payload = {
        'attendance_date': attendance_date,
        'scope': scope,
        'time_in': time_in,
        'time_out': time_out,
        'working_hours': working_hours,
        'attendance_status': status,
        'attendance_remarks': notes or reason or 'Adjusted',
    }

    db.collection('employees').document(employee_doc_id).set(payload, merge=True)
    return jsonify({'success': True})

@bp.route('/hrm/holidays')
@role_required('regional','regional_admin')
def holidays_view():
    from config import Config
    from firebase_admin import firestore
    
    # Try to get region from session first
    region_name = session.get('region') or session.get('user_region')
    
    # If not in session, fetch from Firestore users collection
    if not region_name or region_name == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None
                
                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break
                
                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] holidays_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch region from Firestore: {e}")
    
    if not region_name:
        region_name = 'Unknown Region'
    
    return render_template('regional/HR/holiday-regional.html', firebase_config=Config.FIREBASE_CONFIG, region_name=region_name)

@bp.route('/api/hrm/holidays', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_holidays():
    db = get_firestore_db()
    holidays = []

    try:
        docs = db.collection('holidays').order_by('date').stream()
    except Exception:
        docs = db.collection('holidays').stream()

    for doc in docs:
        item = doc.to_dict() or {}
        date_value = item.get('date')

        if isinstance(date_value, str):
            item['date'] = date_value.split('T')[0]
        elif hasattr(date_value, 'strftime'):
            item['date'] = date_value.strftime('%Y-%m-%d')
        elif hasattr(date_value, 'isoformat'):
            item['date'] = date_value.isoformat().split('T')[0]
        elif hasattr(date_value, 'to_datetime'):
            item['date'] = date_value.to_datetime().strftime('%Y-%m-%d')
        else:
            item['date'] = ''

        holidays.append({
            'id': doc.id,
            'name': item.get('name', ''),
            'date': item.get('date', ''),
            'type': item.get('type', 'Regular Holiday'),
            'basis': item.get('basis', ''),
            'description': item.get('description', ''),
            'scope': item.get('scope', 'REGIONAL')
        })

    return jsonify({'success': True, 'holidays': holidays})

@bp.route('/api/hrm/holidays', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_holiday():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    date = (data.get('date') or '').strip()

    if not name or not date:
        return jsonify({'success': False, 'error': 'Name and date are required'}), 400

    payload = {
        'name': name,
        'date': date,
        'type': (data.get('type') or 'Regular Holiday').strip(),
        'basis': (data.get('basis') or '').strip(),
        'description': (data.get('description') or '').strip(),
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
    }

    db = get_firestore_db()
    ref = db.collection('holidays').document()
    ref.set(payload)

    return jsonify({'success': True, 'id': ref.id})

@bp.route('/api/hrm/holidays/<holiday_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_holiday(holiday_id):
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    date = (data.get('date') or '').strip()

    if not name or not date:
        return jsonify({'success': False, 'error': 'Name and date are required'}), 400

    payload = {
        'name': name,
        'date': date,
        'type': (data.get('type') or 'Regular Holiday').strip(),
        'basis': (data.get('basis') or '').strip(),
        'description': (data.get('description') or '').strip(),
        'scope': (data.get('scope') or 'REGIONAL').strip().upper(),
    }

    db = get_firestore_db()
    db.collection('holidays').document(holiday_id).set(payload, merge=True)

    return jsonify({'success': True})

@bp.route('/hrm/leave-requests')
@role_required('regional','regional_admin')
def leave_requests_view():
    from firebase_admin import firestore

    region_name = session.get('region') or session.get('user_region')

    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                elif user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    print(f"[DEBUG] leave_requests_view fetched region from Firestore: {region_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch leave-request region from Firestore: {e}")

    if not region_name:
        region_name = 'Unknown Region'

    return render_template('regional/HR/leave-request-regional.html', region_name=region_name)

@bp.route('/api/hrm/leave-requests', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_leave_requests():
    db = get_firestore_db()
    leave_requests = []

    try:
        docs = db.collection('leave_requests').stream()
    except Exception:
        docs = []

    for doc in docs:
        item = doc.to_dict() or {}

        def normalize_date(value):
            if isinstance(value, str):
                return value.split('T')[0]
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d')
            if hasattr(value, 'isoformat'):
                return value.isoformat().split('T')[0]
            if hasattr(value, 'to_datetime'):
                return value.to_datetime().strftime('%Y-%m-%d')
            return ''

        leave_requests.append({
            'id': doc.id,
            'date_filed': normalize_date(item.get('date_filed') or item.get('filed_date') or item.get('created_at')),
            'applicant_name': item.get('applicant_name') or item.get('employee_name') or '',
            'assignment': item.get('assignment') or item.get('designation') or '',
            'leave_type': item.get('leave_type') or item.get('type') or '',
            'purpose': item.get('purpose') or item.get('reason') or '',
            'from_date': normalize_date(item.get('from_date') or item.get('start_date')),
            'to_date': normalize_date(item.get('to_date') or item.get('end_date')),
            'days': item.get('days') or item.get('total_days') or 0,
            'status': item.get('status') or 'Pending',
            'scope': (item.get('scope') or 'REGIONWIDE').upper(),
            'municipality': item.get('municipality') or ''
        })

    leave_requests.sort(key=lambda item: item.get('date_filed') or '', reverse=True)
    return jsonify({'success': True, 'leave_requests': leave_requests})

@bp.route('/api/hrm/leave-requests', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_leave_request():
    from datetime import datetime

    data = request.get_json(silent=True) or {}

    applicant_name = (data.get('applicant_name') or '').strip()
    leave_type = (data.get('leave_type') or '').strip()
    from_date = (data.get('from_date') or '').strip()
    to_date = (data.get('to_date') or '').strip()

    if not applicant_name or not leave_type or not from_date or not to_date:
        return jsonify({'success': False, 'error': 'Applicant, leave type, from date, and to date are required'}), 400

    total_days = data.get('days')
    if total_days in [None, '']:
        try:
            d_from = datetime.fromisoformat(from_date).date()
            d_to = datetime.fromisoformat(to_date).date()
            total_days = max((d_to - d_from).days + 1, 1)
        except Exception:
            total_days = 1

    payload = {
        'applicant_name': applicant_name,
        'assignment': (data.get('assignment') or '').strip(),
        'leave_type': leave_type,
        'purpose': (data.get('purpose') or '').strip(),
        'from_date': from_date,
        'to_date': to_date,
        'days': float(total_days) if str(total_days).strip() else 1,
        'status': (data.get('status') or 'Pending').strip(),
        'scope': (data.get('scope') or 'REGIONWIDE').strip().upper(),
        'municipality': (data.get('municipality') or '').strip(),
        'date_filed': datetime.utcnow().date().isoformat(),
        'remarks': (data.get('remarks') or '').strip(),
        'updated_by': session.get('user_email') or ''
    }

    db = get_firestore_db()
    ref = db.collection('leave_requests').document()
    ref.set(payload)

    return jsonify({'success': True, 'id': ref.id})

@bp.route('/api/hrm/leave-requests/<request_id>/status', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_leave_request_status(request_id):
    from datetime import datetime

    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    remarks = (data.get('remarks') or '').strip()

    if not status:
        return jsonify({'success': False, 'error': 'Status is required'}), 400

    db = get_firestore_db()
    db.collection('leave_requests').document(request_id).set({
        'status': status,
        'remarks': remarks,
        'updated_at': datetime.utcnow().isoformat(),
        'updated_by': session.get('user_email') or ''
    }, merge=True)

    return jsonify({'success': True})

@bp.route('/hrm/payroll-system')
@role_required('regional','regional_admin')
def payroll_system_view():
    return render_template('regional/HR/payroll-regional.html')

@bp.route('/accounting/accounting-dashboard')
@role_required('regional','regional_admin')
def accounting_dashboard_view():
    from firebase_admin import firestore
    from flask import session
    from datetime import datetime, timedelta
    db = firestore.client()
    finance_data = {}
    user_region = (session.get('region') or session.get('user_region') or '').upper().replace('–', '-').replace('—', '-').replace('  ', ' ').replace(' ', '-')
    # If user_region is empty, fetch from Firestore user document
    if not user_region:
        user_email = session.get('user_email')
        if user_email:
            user_docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).stream()
            for user_doc in user_docs:
                user_data = user_doc.to_dict()
                region_field = user_data.get('region', '')
                if isinstance(region_field, list):
                    region_str = region_field[0] if region_field else ''
                else:
                    region_str = region_field
                user_region = region_str.upper().replace('–', '-').replace('—', '-').replace('  ', ' ').replace(' ', '-')
                break
    try:
        docs = db.collection('finance').stream()
        for doc in docs:
            finance_data[doc.id] = doc.to_dict()
    except Exception:
        pass

    # Calculate and update received_from_national for the region
    try:
        reg_funds_query = db.collection('regional_fund_distribution').where(filter=FieldFilter('region', '==', user_region)).stream()
        total_received = 0
        for fund_doc in reg_funds_query:
            fund = fund_doc.to_dict()
            try:
                total_received += float(fund.get('amount', 0))
            except Exception:
                pass
        # Update the finance document for the region
        db.collection('finance').document(user_region).set({'received_from_national': total_received}, merge=True)
        # Also update in finance_data for template rendering
        if user_region not in finance_data:
            finance_data[user_region] = {}
        finance_data[user_region]['received_from_national'] = total_received
    except Exception as e:
        print(f"[DEBUG] Error calculating received_from_national: {e}")
    municipalities = []
    try:
        doc = db.collection('municipalities').document(user_region).get()
        print("user_region:", user_region)
        print("Firestore doc:", doc.to_dict())
        if doc.exists:
            municipalities = doc.to_dict().get('municipalities', [])
        print("municipalities:", municipalities)
    except Exception as e:
        print("[DEBUG] Error fetching municipalities:", e)
    # Fetch only municipal fund distributions for this region
    municipal_funds = []
    try:
        print(f"[DEBUG] Fetching municipal fund distributions for region: {user_region}")
        muni_funds_query = db.collection('municipal_fund_distribution').where(filter=FieldFilter('region', '==', user_region)).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        for fund_doc in muni_funds_query:
            fund = fund_doc.to_dict()
            municipal_funds.append(fund)
        print(f"[DEBUG] Fetched municipal_fund_distributions: {municipal_funds}")
    except Exception as e:
        print(f"[DEBUG] Error fetching municipal fund distributions: {e}")

    # Fetch funds transferred from national to this region
    regional_funds = []
    try:
        print(f"[DEBUG] Fetching regional fund distributions for region: {user_region}")
        reg_funds_query = db.collection('regional_fund_distribution').where(filter=FieldFilter('region', '==', user_region)).order_by('date', direction=firestore.Query.DESCENDING).stream()
        for fund_doc in reg_funds_query:
            fund = fund_doc.to_dict()
            regional_funds.append(fund)
        print(f"[DEBUG] Fetched regional_fund_distributions: {regional_funds}")
    except Exception as e:
        print(f"[DEBUG] Error fetching regional fund distributions: {e}")

    def _to_float(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace('₱', '').replace(',', '').strip()
            return float(cleaned) if cleaned else 0.0
        except Exception:
            return 0.0

    def _format_currency(value):
        return f"₱ {value:,.2f}"

    def _parse_ts(value):
        if not value:
            return None
        if hasattr(value, 'to_datetime'):
            try:
                return value.to_datetime()
            except Exception:
                return None
        if hasattr(value, 'strftime'):
            return value
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None

    # Normalize finance documents into known department buckets so template cards
    # don't show N/A when document IDs/structures vary.
    department_keys = ['treasury', 'accounting', 'budget', 'engineering']
    department_finance = {k: {} for k in department_keys}

    for doc_id, payload in finance_data.items():
        if not isinstance(payload, dict):
            continue

        lower_id = str(doc_id or '').strip().lower()
        if lower_id in department_finance:
            department_finance[lower_id] = payload

        for dept in department_keys:
            # Pattern 1: document contains nested department key.
            nested = payload.get(dept)
            if isinstance(nested, dict) and nested:
                department_finance[dept] = nested

            # Pattern 2: document has "department" field + values in same object.
            doc_dept = str(payload.get('department') or payload.get('dept') or '').strip().lower()
            if doc_dept == dept:
                department_finance[dept] = payload

    # Build per-department display values.
    department_cards = {}
    for dept in department_keys:
        row = department_finance.get(dept) or {}
        gf = (
            row.get('general_fund')
            if row.get('general_fund') is not None
            else row.get('generalFund')
        )
        gf_value = _to_float(gf)
        department_cards[dept] = {
            'general_fund_display': _format_currency(gf_value) if gf_value else 'N/A'
        }

    # Aggregate real stats for snapshot cards.
    total_deposits = 0.0
    total_expenses = 0.0

    for dept in department_keys:
        row = department_finance.get(dept) or {}
        total_deposits += _to_float(
            row.get('total_deposit')
            if row.get('total_deposit') is not None
            else row.get('total_deposits')
            if row.get('total_deposits') is not None
            else row.get('deposits')
        )
        total_expenses += _to_float(
            row.get('total_expenses')
            if row.get('total_expenses') is not None
            else row.get('expenses')
        )

    # Fallback to transferred fund records when finance totals are not populated.
    if total_deposits == 0.0:
        total_deposits = sum(_to_float(f.get('amount')) for f in regional_funds)
    if total_expenses == 0.0:
        total_expenses = sum(_to_float(f.get('amount')) for f in municipal_funds)

    net_movement = total_deposits - total_expenses

    # Growth rate: compare recent 30 days vs previous 30 days using fund movement data.
    now = datetime.utcnow()
    current_cutoff = now - timedelta(days=30)
    previous_cutoff = now - timedelta(days=60)
    current_period_total = 0.0
    previous_period_total = 0.0

    for row in (regional_funds + municipal_funds):
        ts = _parse_ts(row.get('timestamp') or row.get('date') or row.get('created_at'))
        amount = _to_float(row.get('amount'))
        if not ts:
            continue
        if ts >= current_cutoff:
            current_period_total += amount
        elif ts >= previous_cutoff:
            previous_period_total += amount

    if previous_period_total > 0:
        growth_rate = ((current_period_total - previous_period_total) / previous_period_total) * 100.0
    else:
        growth_rate = 0.0

    dashboard_stats = {
        'total_deposits_display': _format_currency(total_deposits),
        'total_expenses_display': _format_currency(total_expenses),
        'net_movement_display': _format_currency(net_movement),
        'growth_rate_display': f"{growth_rate:+.1f}%",
    }

    return render_template(
        'regional/accounting/dashboard-regional.html',
        finance=finance_data,
        municipalities=municipalities,
        regional_funds=regional_funds,
        municipal_funds=municipal_funds,
        user_region=user_region,
        department_cards=department_cards,
        dashboard_stats=dashboard_stats,
    )

@bp.route('/accounting/distribute-fund', methods=['POST'])
@role_required('regional','regional_admin')
def distribute_fund():
    from flask import request, jsonify
    from firebase_admin import firestore

    db = firestore.client()
    data = request.json
    muni = data.get('municipality', '').strip()
    province = data.get('province', '').strip()
    try:
        amount = float(data.get('amount', 0))
    except:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400
    fund_type = data.get('fund_type', 'national')
    transfer_id = data.get('transfer_id', '')
    region = data.get('region', '').strip()
    
    # Validate input
    if not muni or not province or amount <= 0 or not region or not transfer_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    print(f"[DEBUG] Incoming fund distribution request: region={region}, municipality={muni}, province={province}, amount={amount}, fund_type={fund_type}, transfer_id={transfer_id}")
    
    # Get region finance
    try:
        region_finance_ref = db.collection('finance').document(region)
        region_finance_doc = region_finance_ref.get()
        if not region_finance_doc.exists:
            # Create it if not exists
            region_finance_ref.set({'received_from_national': 0}, merge=True)
            available_fund = 0
        else:
            region_finance = region_finance_doc.to_dict()
            available_fund = float(region_finance.get('received_from_national', 0))
    except Exception as e:
        print(f"[DEBUG] Error getting region finance: {e}")
        return jsonify({'success': False, 'error': 'Unable to access region finance'}), 500
    
    # Check if sufficient funds (optional - allow distribution even if insufficient, for testing)
    if available_fund < amount:
        print(f"[WARNING] Distributing despite insufficient fund: available={available_fund}, required={amount}")
    
    try:
        # Save to municipal_fund_distribution collection
        record = {
            'municipality': muni,
            'province': province,
            'amount': amount,
            'fund_type': fund_type,
            'transfer_id': transfer_id,
            'region': region,
            'status': 'Released',
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        db.collection('municipal_fund_distribution').add(record)
        print(f"[DEBUG] Successfully saved fund distribution: {record}")
        
        # Update general fund for municipality (optional)
        try:
            doc_id = f"{muni.upper().replace(' ', '_')}_{province.upper().replace(' ', '_')}"
            muni_finance_ref = db.collection('finance').document(doc_id)
            muni_finance_doc = muni_finance_ref.get()
            current_general = 0
            if muni_finance_doc.exists:
                current_general = float(muni_finance_doc.to_dict().get('general_fund', 0))
            muni_finance_ref.set({'general_fund': current_general + amount}, merge=True)
            print(f"[DEBUG] Updated municipality finance: {doc_id}")
        except Exception as e:
            print(f"[WARNING] Could not update municipality finance: {e}")
        
        # Deduct from regional fund (optional - if available)
        try:
            if available_fund >= amount:
                region_finance_ref.update({'received_from_national': available_fund - amount})
            print(f"[DEBUG] Updated regional fund")
        except Exception as e:
            print(f"[WARNING] Could not update regional fund: {e}")
        
        return jsonify({'success': True, 'message': f'Fund of ₱{amount:.2f} distributed to {muni}, {province}'}), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in distribute_fund: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/accounting/sync-municipalities', methods=['POST'])
@role_required('regional','regional_admin')
def sync_municipalities():
    from firebase_admin import firestore
    db = firestore.client()
    import json
    # Load municipalities from ph-locations.js (simulate import)
    # In production, pass the mapping from frontend or keep a JSON copy
    with open('static/js/municipalities.json', 'r') as f:
        locations = json.load(f)
    for region, municipalities in locations.items():
        db.collection('municipalities').document(region).set({'municipalities': municipalities})
    return 'Municipalities synced', 200
@bp.route('/accounting/coa-templates')
@role_required('regional','regional_admin')
def accounting_coa_templates_view():
    db = get_firestore_db()
    
    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)
    
    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve region for COA templates view: {e}")
    
    municipalities = []
    try:
        if user_region:
            muni_doc = db.collection('municipalities').document(user_region).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities for COA view: {e}")
    
    return render_template('regional/accounting/coa-templates-regional.html',
                         user_region=user_region,
                         municipalities=municipalities)

@bp.route('/api/coa/templates', methods=['GET'])
@role_required('regional','regional_admin')
def api_get_regional_coa_templates():
    """Get all COA templates and accounts for municipalities in this region"""
    db = get_firestore_db()
    
    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)
    
    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email',  '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve region for COA API: {e}")
    
    if not user_region:
        return jsonify({'success': False, 'error': 'Cannot determine region'}), 403
    
    municipalities = []
    try:
        muni_doc = db.collection('municipalities').document(user_region).get()
        if muni_doc.exists:
            municipalities = muni_doc.to_dict().get('municipalities', []) or []
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities: {e}")
    
    templates = []
    accounts = []
    stats = {
        'total_templates': 0,
        'total_accounts': 0,
        'total_locked': 0,
        'municipalities_count': len(municipalities)
    }
    
    try:
        all_templates = db.collection('coa_templates').limit(5000).stream()
        
        for doc in all_templates:
            template = doc.to_dict() or {}
            template_municipality = template.get('municipality', '')
            
            if municipalities and template_municipality in municipalities:
                template['id'] = doc.id
                templates.append(template)
                stats['total_accounts'] += template.get('account_count', 0)
                stats['total_locked'] += template.get('locked_count', 0)
        
        stats['total_templates'] = len(templates)
        
        if templates:
            template_ids = [t['id'] for t in templates]
            for template_id in template_ids:
                template_accounts = db.collection('coa_accounts').where('template_id', '==', template_id).limit(1000).stream()
                for acc_doc in template_accounts:
                    acc = acc_doc.to_dict() or {}
                    acc['id'] = acc_doc.id
                    accounts.append(acc)
    
    except Exception as e:
        print(f"[ERROR] Failed to fetch COA templates: {e}")
        import traceback
        traceback.print_exc()
    
    return jsonify({
        'success': True,
        'region': user_region,
        'templates': templates,
        'accounts': accounts,
        'stats': stats
    }), 200

@bp.route('/accounting/accounting-entities')
@role_required('regional','regional_admin')
def accounting_entities_view():
    db = get_firestore_db()
    
    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)
    
    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve region for entities view: {e}")
    
    municipalities = []
    try:
        if user_region:
            muni_doc = db.collection('municipalities').document(user_region).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities for entities view: {e}")
    
    return render_template('regional/accounting/entities-regional.html',
                         user_region=user_region,
                         municipalities=municipalities)

@bp.route('/accounting/accounting-deposits')
@role_required('regional','regional_admin')
def accounting_deposits_view():
    db = get_firestore_db()

    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)

    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve region for accounting deposits view: {e}")

    municipalities = []
    municipality_set = set()

    try:
        if user_region:
            muni_doc = db.collection('municipalities').document(user_region).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []

        if not municipalities:
            users_docs = db.collection('users').limit(2000).stream()
            normalized_region = str(user_region or '').strip().upper()
            for user_doc in users_docs:
                ud = user_doc.to_dict() or {}
                region_val = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
                municipality_val = ud.get('municipality') or ud.get('municipality_name')
                if municipality_val and str(region_val or '').strip().upper() == normalized_region:
                    municipality_set.add(str(municipality_val).strip())
            municipalities = sorted(municipality_set)
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities for accounting deposits view: {e}")

    municipality_set = set(str(m).strip().lower() for m in municipalities if m)

    scoped_users = {}
    user_id_to_email = {}
    scoped_user_ids = set()
    try:
        users_docs = db.collection('users').limit(4000).stream()
        normalized_region = str(user_region or '').strip().upper()
        for user_doc in users_docs:
            ud = user_doc.to_dict() or {}
            region_val = get_firestore_region_name(ud.get('region') or ud.get('region_name') or ud.get('regionName'))
            municipality_val = str(ud.get('municipality') or ud.get('municipality_name') or '').strip()
            email_val = str(ud.get('email') or '').strip().lower()

            if not email_val:
                continue

            in_scope_by_municipality = bool(
                municipality_set and municipality_val and municipality_val.lower() in municipality_set
            )
            in_scope_by_region = bool(
                normalized_region and str(region_val or '').strip().upper() == normalized_region
            )

            if not (in_scope_by_municipality or in_scope_by_region):
                continue

            scoped_users[email_val] = {
                'municipality': municipality_val,
                'region': str(region_val or '').strip().upper()
            }
            scoped_user_ids.add(str(user_doc.id).strip())
            user_id_to_email[str(user_doc.id).strip()] = email_val

            possible_ids = [
                ud.get('uid'),
                ud.get('user_id'),
                ud.get('userId'),
                ud.get('id')
            ]
            for pid in possible_ids:
                if pid:
                    pid_str = str(pid).strip()
                    scoped_user_ids.add(pid_str)
                    user_id_to_email[pid_str] = email_val
    except Exception as e:
        print(f"[WARN] Unable to resolve scoped users for accounting deposits view: {e}")

    paid_status_markers = {
        'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'
    }

    def parse_amount(raw_value):
        try:
            return float(raw_value or 0)
        except (ValueError, TypeError):
            return 0.0

    def is_paid_status(value):
        normalized = str(value or '').strip().lower()
        if not normalized:
            return False
        return normalized in paid_status_markers

    def normalize_date_value(value):
        if not value:
            return '-'
        try:
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            if hasattr(value, 'to_datetime'):
                return value.to_datetime().isoformat()
            return str(value)
        except Exception:
            return str(value) or '-'

    def resolve_payer_email(record, fallback_user_id=None):
        candidates = [
            record.get('user_email'),
            record.get('userEmail'),
            record.get('email'),
            record.get('payer_email'),
            record.get('payerEmail'),
            record.get('customer_email'),
            record.get('customerEmail'),
            record.get('billing_email'),
            record.get('billingEmail')
        ]
        for candidate in candidates:
            normalized = str(candidate or '').strip().lower()
            if normalized:
                return normalized
        fallback_id = str(fallback_user_id or '').strip()
        if fallback_id and fallback_id in user_id_to_email:
            return user_id_to_email[fallback_id]
        return '-'

    def user_in_scope(email_value=None, user_id_value=None):
        normalized_email = str(email_value or '').strip().lower()
        normalized_user_id = str(user_id_value or '').strip()
        return (
            (normalized_email and normalized_email in scoped_users)
            or (normalized_user_id and normalized_user_id in scoped_user_ids)
        )

    def municipality_region_match(record_municipality=None, record_region=None):
        rec_muni = str(record_municipality or '').strip().lower()
        rec_region = str(record_region or '').strip().upper()
        if municipality_set and rec_muni and rec_muni not in municipality_set:
            return False
        if user_region and rec_region and rec_region != str(user_region or '').strip().upper():
            return False
        return bool(rec_muni or rec_region)

    def append_record(target, record_id, invoice_id, description, amount, status, payment_method, municipality, payer_email, created_at, source):
        target.append({
            'id': record_id,
            'invoice_id': invoice_id,
            'description': description,
            'amount': amount,
            'status': str(status or 'PAID').strip().upper(),
            'payment_method': payment_method or 'Online Payment',
            'municipality': municipality or 'UNKNOWN',
            'payer_email': payer_email or '-',
            'created_at': normalize_date_value(created_at),
            'source': source,
        })

    payment_deposits = []
    try:
        # Source 1: transactions collection
        tx_docs = db.collection('transactions').limit(5000).stream()
        for tx_doc in tx_docs:
            tx = tx_doc.to_dict() or {}
            payer_email = resolve_payer_email(tx, tx.get('userId') or tx.get('user_id') or tx.get('uid'))
            tx_user_id = tx.get('userId') or tx.get('user_id') or tx.get('uid')
            tx_municipality = str(tx.get('municipality') or tx.get('municipality_name') or '').strip()
            tx_region = get_firestore_region_name(tx.get('region') or tx.get('region_name') or tx.get('regionName'))

            in_scope_by_user = user_in_scope(payer_email, tx_user_id)
            in_scope_by_fields = municipality_region_match(tx_municipality, tx_region)

            if not (in_scope_by_user or in_scope_by_fields):
                continue

            status = tx.get('status') or tx.get('paymentStatus') or tx.get('payment_status') or tx.get('payment_state')
            paid_by_status = is_paid_status(status)
            paid_by_method = bool(tx.get('payment_method')) and str(status or '').strip().lower() not in {'pending', 'failed', 'expired', 'cancelled'}
            if not (paid_by_status or paid_by_method):
                continue

            amount = parse_amount(tx.get('amount'))
            if amount <= 0:
                continue

            scoped_user = scoped_users.get(payer_email, {})
            municipality_name = tx_municipality or scoped_user.get('municipality') or 'UNKNOWN'

            append_record(
                payment_deposits,
                tx_doc.id,
                tx.get('invoice_id') or tx.get('external_id') or tx_doc.id,
                tx.get('description') or tx.get('transaction_name') or 'User Payment',
                amount,
                status or 'PAID',
                tx.get('payment_method') or 'Online Payment',
                municipality_name,
                payer_email,
                tx.get('paid_at') or tx.get('updated_at') or tx.get('created_at') or tx.get('createdAt'),
                'transactions'
            )

        # Source 2: applications collection with payment fields
        app_docs = db.collection('applications').limit(5000).stream()
        for app_doc in app_docs:
            app = app_doc.to_dict() or {}
            payer_email = resolve_payer_email(app, app.get('userId') or app.get('user_id') or app.get('uid'))
            app_user_id = app.get('userId') or app.get('user_id') or app.get('uid')
            app_municipality = str(app.get('municipality') or app.get('municipality_name') or '').strip()
            app_region = get_firestore_region_name(app.get('region') or app.get('region_name') or app.get('regionName'))

            if not (user_in_scope(payer_email, app_user_id) or municipality_region_match(app_municipality, app_region)):
                continue

            payment_status = app.get('paymentStatus') or app.get('payment_status') or app.get('status') or app.get('payment_state')
            if not is_paid_status(payment_status):
                continue

            amount = parse_amount(app.get('amount') or app.get('paymentAmount') or app.get('serviceFee') or app.get('processingFee'))
            if amount <= 0:
                continue

            scoped_user = scoped_users.get(payer_email, {})
            municipality_name = app_municipality or scoped_user.get('municipality') or 'UNKNOWN'

            append_record(
                payment_deposits,
                app_doc.id,
                app.get('invoiceId') or app.get('invoice_id') or app.get('externalId') or app.get('external_id') or app_doc.id,
                app.get('description') or app.get('applicationType') or app.get('permitType') or 'Application Payment',
                amount,
                payment_status,
                app.get('paymentMethod') or app.get('payment_method') or 'Online Payment',
                municipality_name,
                payer_email,
                app.get('paidAt') or app.get('paymentDate') or app.get('updatedAt') or app.get('updated_at') or app.get('createdAt') or app.get('created_at') or app.get('dateFiled'),
                'applications'
            )

        # Source 3: service_requests collection with payment fields
        service_docs = db.collection('service_requests').limit(5000).stream()
        for service_doc in service_docs:
            service = service_doc.to_dict() or {}
            payer_email = resolve_payer_email(service, service.get('userId') or service.get('user_id') or service.get('uid'))
            service_user_id = service.get('userId') or service.get('user_id') or service.get('uid')
            service_municipality = str(service.get('municipality') or service.get('municipality_name') or '').strip()
            service_region = get_firestore_region_name(service.get('region') or service.get('region_name') or service.get('regionName'))

            if not (user_in_scope(payer_email, service_user_id) or municipality_region_match(service_municipality, service_region)):
                continue

            payment_status = service.get('paymentStatus') or service.get('payment_status') or service.get('status') or service.get('payment_state')
            if not is_paid_status(payment_status):
                continue

            amount = parse_amount(service.get('amount') or service.get('paymentAmount') or service.get('serviceFee') or service.get('fee'))
            if amount <= 0:
                continue

            scoped_user = scoped_users.get(payer_email, {})
            municipality_name = service_municipality or scoped_user.get('municipality') or 'UNKNOWN'

            append_record(
                payment_deposits,
                service_doc.id,
                service.get('invoiceId') or service.get('invoice_id') or service.get('externalId') or service.get('external_id') or service_doc.id,
                service.get('serviceType') or service.get('description') or 'Service Payment',
                amount,
                payment_status,
                service.get('paymentMethod') or service.get('payment_method') or 'Online Payment',
                municipality_name,
                payer_email,
                service.get('paidAt') or service.get('paymentDate') or service.get('updatedAt') or service.get('updated_at') or service.get('createdAt') or service.get('created_at') or service.get('submittedAt'),
                'service_requests'
            )
    except Exception as e:
        print(f"[WARN] Unable to load transactions for accounting deposits view: {e}")

    deduped = {}
    for row in payment_deposits:
        dedupe_key = str(row.get('invoice_id') or row.get('id'))
        existing = deduped.get(dedupe_key)
        if not existing or str(row.get('created_at') or '') >= str(existing.get('created_at') or ''):
            deduped[dedupe_key] = row
    payment_deposits = list(deduped.values())

    payment_deposits.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    total_amount = sum(float(d.get('amount', 0) or 0) for d in payment_deposits)
    unique_payers = len(set(d.get('payer_email') for d in payment_deposits if d.get('payer_email') and d.get('payer_email') != '-'))

    return render_template(
        'regional/accounting/deposit-category-regional.html',
        user_region=user_region,
        municipalities=municipalities,
        payment_deposits=payment_deposits,
        total_payments=len(payment_deposits),
        total_amount=total_amount,
        unique_payers=unique_payers
    )

@bp.route('/api/entities', methods=['GET'])
@role_required('regional','regional_admin')
def api_get_regional_entities():
    """Get all entities across municipalities in the regional admin's region"""
    db = get_firestore_db()
    
    session_region = session.get('region') or session.get('user_region')
    user_region = get_firestore_region_name(session_region)
    
    if not user_region:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        try:
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
            if not user_region and user_email:
                docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                for doc in docs:
                    user_data = doc.to_dict() or {}
                    user_region = get_firestore_region_name(
                        user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                    )
                    break
        except Exception as e:
            print(f"[WARN] Unable to resolve region for entities API: {e}")
    
    if not user_region:
        return jsonify({'success': False, 'error': 'Cannot determine region'}), 403
    
    municipalities = []
    try:
        muni_doc = db.collection('municipalities').document(user_region).get()
        if muni_doc.exists:
            municipalities = muni_doc.to_dict().get('municipalities', []) or []
    except Exception as e:
        print(f"[WARN] Unable to resolve municipalities: {e}")
    
    entities = []
    stats = {
        'total': 0,
        'by_type': {},
        'by_status': {},
        'municipalities_count': len(municipalities)
    }
    
    try:
        all_entities = db.collection('entities').limit(5000).stream()
        
        for doc in all_entities:
            entity = doc.to_dict() or {}
            entity_municipality = entity.get('municipality', '')
            
            if municipalities and entity_municipality in municipalities:
                entity['id'] = doc.id
                entities.append(entity)
                
                entity_type = entity.get('type', 'OFFICE')
                entity_status = entity.get('status', 'ACTIVE')
                
                stats['by_type'][entity_type] = stats['by_type'].get(entity_type, 0) + 1
                stats['by_status'][entity_status] = stats['by_status'].get(entity_status, 0) + 1
        
        stats['total'] = len(entities)

        # Fallback: if entities collection has no records for this region, derive from municipal_offices
        if stats['total'] == 0:
            office_docs = db.collection('municipal_offices').limit(5000).stream()
            for doc in office_docs:
                office = doc.to_dict() or {}
                municipality_name = office.get('municipality_name') or office.get('municipality') or office.get('name')
                office_region = office.get('region_name') or office.get('region')
                status = office.get('status') or ('ACTIVE' if office.get('is_active') is True else 'UNKNOWN')

                include_row = False
                if municipalities and municipality_name in municipalities:
                    include_row = True
                elif not municipalities and office_region and str(office_region).strip().upper() in str(session_region or '').strip().upper():
                    include_row = True

                if not include_row:
                    continue

                entity = {
                    'id': doc.id,
                    'name': municipality_name or 'N/A',
                    'type': 'OFFICE',
                    'municipality': municipality_name or 'N/A',
                    'status': status,
                    'bank_account': office.get('bank_account_number') or office.get('bank_account') or 'N/A'
                }
                entities.append(entity)

                stats['by_type']['OFFICE'] = stats['by_type'].get('OFFICE', 0) + 1
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

            stats['total'] = len(entities)
    except Exception as e:
        print(f"[ERROR] Failed to fetch entities: {e}")
    
    return jsonify({
        'success': True,
        'region': user_region,
        'entities': entities,
        'stats': stats
    }), 200

@bp.route('/accounting/accounting-expenses')
@role_required('regional','regional_admin')
def accounting_expenses_view():
    return render_template('regional/accounting/expense-category-regional.html')

@bp.route('/accounting/topup-fund', methods=['POST'])
@role_required('regional','regional_admin','superadmin')
def topup_fund():
    from flask import request, jsonify
    from firebase_admin import firestore
    db = firestore.client()
    data = request.json
    region = data.get('region')
    amount = float(data.get('amount', 0))
    if not region or amount <= 0:
        return jsonify({'success': False, 'error': 'Region and positive amount required'}), 400
    region_finance_ref = db.collection('finance').document(region)
    region_finance_doc = region_finance_ref.get()
    if not region_finance_doc.exists:
        return jsonify({'success': False, 'error': 'Regional fund not found'}), 404
    current = float(region_finance_doc.to_dict().get('available_fund', 0))
    region_finance_ref.update({'available_fund': current + amount})
    return jsonify({'success': True, 'region': region, 'new_available_fund': current + amount})

# ============================================
# REGIONAL EXPENSE TRACKING APIs
# ============================================

@bp.route('/api/accounting/expenses', methods=['GET'])
@role_required('regional','regional_admin')
def get_regional_expenses():
    from firebase_admin import firestore
    import datetime

    db = get_firestore_db()
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception as e:
                print(f"[WARNING] Failed to fetch region from user doc: {e}")
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    region_name = str(region_name).strip().upper()
    
    # Map session region name to Firestore region name
    firestore_region = get_firestore_region_name(region_name)
    
    print(f"[DEBUG] Session region: '{region_name}' -> Firestore region: '{firestore_region}'")

    transactions = []
    
    # ===================================
    # Fetch REAL transactions from 3 sources
    # ===================================
    
    # 1️⃣ Regional Expenses (direct spending)
    try:
        expense_docs = db.collection('regional_expenses').where(
            filter=FieldFilter('region', '==', firestore_region)
        ).stream()
        
        expense_count = 0
        for doc in expense_docs:
            expense = doc.to_dict()
            expense['id'] = doc.id
            expense['transaction_type'] = 'Expense'
            expense['transaction_date'] = expense.get('expense_date', '')
            transactions.append(expense)
            expense_count += 1
        
        print(f"[DEBUG] Loaded {expense_count} expenses from regional_expenses for region '{firestore_region}'")
    except Exception as e:
        print(f"[ERROR] Failed to fetch regional expenses: {e}")
    
    # 2️⃣ Municipal Fund Distributions (transfers TO municipalities)
    try:
        muni_fund_docs = list(db.collection('municipal_fund_distribution').where(
            filter=FieldFilter('region', '==', firestore_region)
        ).limit(50).stream())
        
        transfer_count = 0
        for doc in muni_fund_docs:
            fund = doc.to_dict()
            fund['id'] = doc.id
            fund['transaction_type'] = 'Fund Transfer to Municipality'
            fund['expense_type'] = f"Fund Transfer to {fund.get('municipality', 'Municipality')}"
            fund['category'] = 'Project'
            # Ensure amount is properly converted to a number
            try:
                fund['amount'] = float(fund.get('amount', 0))
            except (ValueError, TypeError):
                fund['amount'] = 0
            fund['recipient'] = fund.get('municipality', 'N/A')
            fund['payment_method'] = 'Bank Transfer'
            fund['description'] = f"Fund allocation to {fund.get('municipality')} ({fund.get('province')})"
            
            # Handle timestamp properly
            timestamp = fund.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    fund['transaction_date'] = timestamp.split('T')[0]
                else:
                    fund['transaction_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            else:
                fund['transaction_date'] = ''
            
            fund['expense_date'] = fund['transaction_date']
            fund['reference_number'] = fund.get('transfer_id', '')
            fund['status'] = fund.get('status', 'Released')
            transactions.append(fund)
            transfer_count += 1
        
        print(f"[DEBUG] Loaded {transfer_count} municipal fund distributions for region '{firestore_region}'")
    except Exception as e:
        print(f"[ERROR] Failed to fetch municipal fund distributions: {e}")
        import traceback
        traceback.print_exc()
    
    # 3️⃣ Regional Fund Distributions (funds received FROM national)
    try:
        reg_fund_docs = db.collection('regional_fund_distribution').where(
            filter=FieldFilter('region', '==', firestore_region)
        ).stream()
        
        received_count = 0
        for doc in reg_fund_docs:
            fund = doc.to_dict()
            fund['id'] = doc.id
            fund['transaction_type'] = 'Fund Received'
            fund['expense_type'] = f"Fund Received from National"
            fund['category'] = 'Project'
            # Ensure amount is properly converted to a number
            try:
                fund['amount'] = float(fund.get('amount', 0))
            except (ValueError, TypeError):
                fund['amount'] = 0
            fund['recipient'] = 'National Government'
            fund['payment_method'] = 'Bank Transfer'
            fund['description'] = f"Allocation from national for {fund.get('fund_type', 'regional operations')}"
            
            # Handle date properly
            date_field = fund.get('date')
            if date_field:
                if isinstance(date_field, str):
                    fund['transaction_date'] = date_field.split('T')[0]
                else:
                    fund['transaction_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            else:
                fund['transaction_date'] = ''
            
            fund['expense_date'] = fund['transaction_date']
            fund['reference_number'] = fund.get('transfer_id', '')
            fund['status'] = fund.get('status', 'Received')
            transactions.append(fund)
            received_count += 1
        
        print(f"[DEBUG] Loaded {received_count} regional fund distributions for region '{firestore_region}'")
    except Exception as e:
        print(f"[ERROR] Failed to fetch regional fund distributions: {e}")
    
    # Sort by date (most recent first)
    try:
        transactions.sort(
            key=lambda x: x.get('transaction_date', '') or x.get('expense_date', ''),
            reverse=True
        )
    except Exception as e:
        print(f"[WARNING] Failed to sort transactions: {e}")
    
    print(f"[DEBUG] Total transactions returned for {firestore_region}: {len(transactions)}")
    print(f"[DEBUG] Transaction types: {[t.get('transaction_type') for t in transactions]}")
    
    return jsonify({'success': True, 'expenses': transactions})

@bp.route('/api/accounting/expenses', methods=['POST'])
@role_required('regional','regional_admin')
def create_regional_expense():
    from firebase_admin import firestore
    import datetime

    data = request.get_json(silent=True) or {}
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    region_name = str(region_name).strip().upper()
    firestore_region = get_firestore_region_name(region_name)
    
    # Validate required fields
    expense_type = (data.get('expense_type') or '').strip()
    amount = data.get('amount')
    expense_date = (data.get('expense_date') or '').strip()
    description = (data.get('description') or '').strip()
    
    if not all([expense_type, amount, expense_date]):
        return jsonify({'success': False, 'error': 'Expense type, amount, and date are required'}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be positive'}), 400
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400
    
    db = get_firestore_db()
    
    payload = {
        'expense_type': expense_type,
        'category': (data.get('category') or 'General').strip(),
        'amount': amount,
        'expense_date': expense_date,
        'description': description,
        'payment_method': (data.get('payment_method') or 'Check').strip(),
        'recipient': (data.get('recipient') or 'N/A').strip(),
        'reference_number': (data.get('reference_number') or '').strip(),
        'municipality': (data.get('municipality') or 'REGIONAL').strip(),
        'region': firestore_region,
        'recorded_by': session.get('user_email') or session.get('user_id') or 'System',
        'status': 'Recorded',
        'created_at': datetime.datetime.utcnow().isoformat(),
        'updated_at': datetime.datetime.utcnow().isoformat()
    }
    
    try:
        ref = db.collection('regional_expenses').add(payload)
        return jsonify({'success': True, 'id': ref[1].id})
    except Exception as e:
        print(f"[ERROR] Failed to record expense: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== PROJECT MANAGEMENT ====================

@bp.route('/operations/projects')
@role_required('regional', 'regional_admin')
def projects_regional():
    """Regional admin project management view"""
    try:
        import projects_storage
        user_region = session.get('user_region', '')
        projects = projects_storage.get_projects_regional(user_region)
        pending_approval = projects_storage.get_projects_for_approval('regional', user_region)
        
        return render_template(
            'regional/operations/projects-regional.html',
            projects=projects,
            pending_approval=pending_approval,
            user_email=session.get('user_email', 'Unknown'),
            user_region=user_region
        )
    except Exception as e:
        print(f"[ERROR] Loading regional projects: {e}")
        return render_template(
            'regional/operations/projects-regional.html',
            projects=[],
            pending_approval=[],
            user_email=session.get('user_email', 'Unknown'),
            user_region=session.get('user_region', '')
        )


# --- API: Mark Project as DONE by Regional ---
@bp.route('/api/projects/<project_id>/status', methods=['POST'])
@role_required('regional', 'regional_admin')
def api_regional_project_mark_done(project_id):
    """Mark a project as DONE by regional admin."""
    from firebase_admin import firestore
    db = get_firestore_db()
    data = request.get_json(silent=True) or {}
    new_status = str(data.get('status', '')).strip().upper()
    if new_status not in {'DONE', 'COMPLETED', 'DONE_BY_REGIONAL'}:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    # Only allow marking as DONE/COMPLETED
    try:
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()
        if not project_doc.exists:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_doc.to_dict() or {}
        # Optionally: check if user is allowed to update this project (region match)
        user_region = session.get('user_region', '').strip().upper()
        project_region = str(project.get('region', '')).strip().upper()
        if user_region and project_region and user_region != project_region:
            return jsonify({'success': False, 'error': 'Region mismatch'}), 403

        update_payload = {
            'status': 'Completed',
            'status_code': 'DONE_BY_REGIONAL',
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': session.get('user_email', 'system'),
        }
        project_ref.update(update_payload)
        return jsonify({'success': True, 'id': project_id, 'status': 'Completed'}), 200
    except Exception as e:
        print(f"[ERROR] Failed to update project status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/operations/applicants')
@role_required('regional', 'regional_admin')
def applicants_regional():
    return render_template('regional/operations/applicants-regional.html')


@bp.route('/operations/quotation')
@role_required('regional', 'regional_admin')
def quotation_regional():
    return render_template('regional/operations/quotation-regional.html')


@bp.route('/operations/task')
@role_required('regional', 'regional_admin')
def task_regional():
    return render_template('regional/operations/task-regional.html')

@bp.route('/api/accounting/expenses/<expense_id>', methods=['PUT'])
@role_required('regional','regional_admin')
def update_regional_expense(expense_id):
    from firebase_admin import firestore
    import datetime

    data = request.get_json(silent=True) or {}
    
    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    region_name = str(region_name).strip().upper()
    firestore_region = get_firestore_region_name(region_name)
    
    db = get_firestore_db()
    
    # Verify expense belongs to user's region
    try:
        expense_doc = db.collection('regional_expenses').document(expense_id).get()
        if not expense_doc.exists:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404
        
        expense = expense_doc.to_dict()
        if expense.get('region') != firestore_region:
            return jsonify({'success': False, 'error': 'Cannot modify expenses from other regions'}), 403
    except Exception as e:
        print(f"[ERROR] Failed to verify expense: {e}")
        return jsonify({'success': False, 'error': 'Verification failed'}), 500
    
    # Build update payload
    payload = {
        'updated_at': datetime.datetime.utcnow().isoformat()
    }
    
    if 'expense_type' in data:
        payload['expense_type'] = (data.get('expense_type') or '').strip()
    if 'category' in data:
        payload['category'] = (data.get('category') or 'General').strip()
    if 'amount' in data:
        try:
            amount = float(data.get('amount', 0))
            if amount <= 0:
                return jsonify({'success': False, 'error': 'Amount must be positive'}), 400
            payload['amount'] = amount
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
    if 'expense_date' in data:
        payload['expense_date'] = (data.get('expense_date') or '').strip()
    if 'description' in data:
        payload['description'] = (data.get('description') or '').strip()
    if 'payment_method' in data:
        payload['payment_method'] = (data.get('payment_method') or 'Check').strip()
    if 'recipient' in data:
        payload['recipient'] = (data.get('recipient') or 'N/A').strip()
    if 'reference_number' in data:
        payload['reference_number'] = (data.get('reference_number') or '').strip()
    if 'municipality' in data:
        payload['municipality'] = (data.get('municipality') or 'REGIONAL').strip()
    if 'status' in data:
        payload['status'] = (data.get('status') or 'Recorded').strip()
    
    try:
        db.collection('regional_expenses').document(expense_id).set(payload, merge=True)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Failed to update expense: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/accounting/expenses/<expense_id>', methods=['DELETE'])
@role_required('regional','regional_admin')
def delete_regional_expense(expense_id):
    from firebase_admin import firestore

    # Get the user's region
    region_name = session.get('region') or session.get('user_region')
    
    if not region_name or str(region_name).strip().lower() == 'unknown':
        user_id = session.get('user_id')
        user_email = session.get('user_email')

        if user_id or user_email:
            try:
                db_client = firestore.client()
                user_doc = None

                if user_id:
                    user_doc = db_client.collection('users').document(user_id).get()
                elif user_email:
                    docs = db_client.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_doc = doc
                        break

                if user_doc and user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    region_name = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
            except Exception:
                pass

    if not region_name:
        region_name = 'CALABARZON'
    
    region_name = str(region_name).strip().upper()
    firestore_region = get_firestore_region_name(region_name)
    
    db = get_firestore_db()
    
    # Verify expense belongs to user's region
    try:
        expense_doc = db.collection('regional_expenses').document(expense_id).get()
        if not expense_doc.exists:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404
        
        expense = expense_doc.to_dict()
        if expense.get('region') != firestore_region:
            return jsonify({'success': False, 'error': 'Cannot delete expenses from other regions'}), 403
    except Exception as e:
        print(f"[ERROR] Failed to verify expense: {e}")
        return jsonify({'success': False, 'error': 'Verification failed'}), 500
    
    try:
        db.collection('regional_expenses').document(expense_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Failed to delete expense: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================
# DEBUG ENDPOINT - Check what's in Firestore
# =====================================
@bp.route('/api/accounting/debug/collections', methods=['GET'])
@role_required('regional','regional_admin')
def debug_collections():
    """Debug endpoint to see what's actually in the collections"""
    from firebase_admin import firestore
    
    db = get_firestore_db()
    region_name = session.get('region') or session.get('user_region') or 'CALABARZON'
    region_name = str(region_name).strip().upper()
    firestore_region = get_firestore_region_name(region_name)
    
    debug_info = {
        'session_region': region_name,
        'firestore_region': firestore_region,
        'session_data': {
            'region': session.get('region'),
            'user_region': session.get('user_region'),
            'user_id': session.get('user_id'),
            'user_email': session.get('user_email')
        },
        'collections': {}
    }
    
    # Check each collection
    collections_to_check = [
        'regional_expenses',
        'municipal_fund_distribution', 
        'regional_fund_distribution'
    ]
    
    for collection_name in collections_to_check:
        try:
            # Fetch ALL docs from collection (no filter)
            all_docs = list(db.collection(collection_name).limit(100).stream())
            
            # Fetch docs with region filter (using firestore_region)
            region_docs = list(db.collection(collection_name).where(
                filter=FieldFilter('region', '==', firestore_region)
            ).limit(100).stream())
            
            debug_info['collections'][collection_name] = {
                'total_count': len(all_docs),
                'region_filtered_count': len(region_docs),
                'sample_docs': [
                    {
                        'id': doc.id,
                        'fields': list(doc.to_dict().keys()),
                        'region': doc.to_dict().get('region'),
                    }
                    for doc in all_docs[:3]
                ]
            }
            
            # Show any unique region values found
            if all_docs:
                regions_found = set()
                for doc in all_docs:
                    regions_found.add(doc.to_dict().get('region'))
                debug_info['collections'][collection_name]['regions_in_collection'] = list(regions_found)
                
        except Exception as e:
            debug_info['collections'][collection_name] = {
                'error': str(e)
            }
    
    return jsonify(debug_info)


# ==================== COA ENDPOINTS (Frontend-compatible paths) ====================

@bp.route('/api/coa-templates', methods=['GET'])
def api_get_coa_templates_wrapped():
    """Wrapper for /api/coa/templates with normalized response"""
    try:
        db = get_firestore_db()
        
        # Fetch ALL templates (no role check)
        templates = []
        try:
            print(f"[INFO] Regional endpoint fetching ALL COA templates from Firestore...")
            all_templates = db.collection('coa_templates').stream()
            for doc in all_templates:
                template = doc.to_dict() or {}
                templates.append({
                    'id': doc.id,
                    'name': template.get('name'),
                    'description': template.get('description', ''),
                    'status': template.get('status', 'active'),
                    'account_count': template.get('account_count', 0),
                    'municipality': template.get('municipality')
                })
            print(f"[INFO] Fetched {len(templates)} COA templates from regional endpoint")
        except Exception as e:
            print(f"[ERROR] Failed to fetch all COA templates: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify(templates), 200
        
        # Regional admin: filter by region
        session_region = session.get('region') or session.get('user_region')
        user_region = get_firestore_region_name(session_region)
        
        if not user_region:
            user_id = session.get('user_id')
            user_email = session.get('user_email')
            try:
                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict() or {}
                        user_region = get_firestore_region_name(
                            user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                        )
                if not user_region and user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email',  '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_data = doc.to_dict() or {}
                        user_region = get_firestore_region_name(
                            user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                        )
                        break
            except Exception as e:
                print(f"[WARN] Unable to resolve region: {e}")
        
        if not user_region:
            return jsonify([]), 200
        
        municipalities = []
        try:
            muni_doc = db.collection('municipalities').document(user_region).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []
        except Exception as e:
            print(f"[WARN] Unable to resolve municipalities: {e}")
        
        templates = []
        try:
            all_templates = db.collection('coa_templates').limit(5000).stream()
            
            for doc in all_templates:
                template = doc.to_dict() or {}
                template_municipality = template.get('municipality', '')
                
                if municipalities and template_municipality in municipalities:
                    template['id'] = doc.id
                    templates.append({
                        'id': template.get('id'),
                        'name': template.get('name'),
                        'description': template.get('description', ''),
                        'status': template.get('status', 'active'),
                        'account_count': template.get('account_count', 0),
                        'municipality': template.get('municipality')
                    })
        except Exception as e:
            print(f"[ERROR] Failed to fetch COA templates: {e}")
        
        return jsonify(templates), 200
    except Exception as e:
        print(f"[ERROR] Getting COA templates: {e}")
        return jsonify([]), 200


@bp.route('/api/coa-accounts', methods=['GET'])
def api_get_coa_accounts_wrapped():
    """Get COA accounts for the region"""
    try:
        db = get_firestore_db()
        template_id = request.args.get('template')
        
        # Fetch ALL accounts (no role check)
        accounts = []
        try:
            print(f"[INFO] Regional endpoint fetching ALL COA accounts from Firestore...")
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
            print(f"[INFO] Fetched {len(accounts)} COA accounts from regional endpoint")
        except Exception as e:
            print(f"[ERROR] Failed to fetch all COA accounts: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify(accounts), 200
        
        # Regional admin: filter by region
        session_region = session.get('region') or session.get('user_region')
        user_region = get_firestore_region_name(session_region)
        
        if not user_region:
            user_id = session.get('user_id')
            user_email = session.get('user_email')
            try:
                if user_id:
                    user_doc = db.collection('users').document(user_id).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict() or {}
                        user_region = get_firestore_region_name(
                            user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                        )
                if not user_region and user_email:
                    docs = db.collection('users').where(filter=FieldFilter('email',  '==', user_email)).limit(1).stream()
                    for doc in docs:
                        user_data = doc.to_dict() or {}
                        user_region = get_firestore_region_name(
                            user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                        )
                        break
            except Exception as e:
                print(f"[WARN] Unable to resolve region: {e}")
        
        if not user_region:
            return jsonify([]), 200
        
        municipalities = []
        try:
            muni_doc = db.collection('municipalities').document(user_region).get()
            if muni_doc.exists:
                municipalities = muni_doc.to_dict().get('municipalities', []) or []
        except Exception as e:
            print(f"[WARN] Unable to resolve municipalities: {e}")
        
        accounts = []
        
        try:
            if template_id:
                # Get accounts for specific template
                template_accounts = db.collection('coa_accounts').where('template_id', '==', template_id).limit(1000).stream()
                for acc_doc in template_accounts:
                    acc = acc_doc.to_dict() or {}
                    accounts.append({
                        'id': acc_doc.id,
                        'code': acc.get('code'),
                        'name': acc.get('name'),
                        'type': acc.get('account_type', 'Asset'),
                        'locked': acc.get('locked', False),
                        'description': acc.get('description', '')
                    })
            else:
                # Get all accounts from all municipalities in the region
                all_templates = db.collection('coa_templates').limit(5000).stream()
                for template_doc in all_templates:
                    template = template_doc.to_dict() or {}
                    template_municipality = template.get('municipality', '')
                    
                    if municipalities and template_municipality in municipalities:
                        template_id_iter = template_doc.id
                        template_accounts = db.collection('coa_accounts').where('template_id', '==', template_id_iter).limit(1000).stream()
                        for acc_doc in template_accounts:
                            acc = acc_doc.to_dict() or {}
                            accounts.append({
                                'id': acc_doc.id,
                                'code': acc.get('code'),
                                'name': acc.get('name'),
                                'type': acc.get('account_type', 'Asset'),
                                'locked': acc.get('locked', False),
                                'description': acc.get('description', '')
                            })
        except Exception as e:
            print(f"[ERROR] Failed to fetch COA accounts: {e}")
        
        return jsonify(accounts), 200
    except Exception as e:
        print(f"[ERROR] Getting COA accounts: {e}")
        return jsonify([]), 200


# ==================== EXPENSE CATEGORIES API (Frontend-compatible) ====================

@bp.route('/api/expense-categories', methods=['GET'])
def api_get_expense_categories_wrapped():
    """Get all expense categories (frontend-compatible endpoint)"""
    try:
        db = get_firestore_db()
        
        # Fetch ALL categories (no role check)
        categories = []
        try:
            print(f"[INFO] Regional endpoint fetching ALL expense categories from Firestore...")
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
            print(f"[INFO] Fetched {len(categories)} expense categories from regional endpoint")
        except Exception as e:
            print(f"[ERROR] Failed to fetch all expense categories: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify(categories), 200
    except Exception as e:
        print(f"[ERROR] Getting expense categories: {e}")
        return jsonify([]), 200
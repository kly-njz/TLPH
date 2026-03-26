from flask import Blueprint, render_template, redirect, url_for, session
from firebase_auth_middleware import role_required, firebase_auth_required

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    print("HOME.HTML IS BEING RENDERED")  # Debug line
    # Server-side check for disabled user
    user_id = session.get('user_id')
    if user_id:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            if data.get('status', '').lower() == 'disabled':
                return redirect(url_for('account_disabled'))
    return render_template('home.html')

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/register')
def register():
    return render_template('signup.html')

@bp.route('/create-municipal-admin')
@role_required('regional','regional_admin')
def create_municipal_admin():
    return render_template('create-municipal-admin.html')

@bp.route('/create-regional-account')   
@role_required('super-admin','superadmin','national','national_admin')
def create_regional_account():
    return render_template('create_regional_account.html')

# Landing pages for different roles
@bp.route('/national/dashboard')
@role_required('national','national_admin')
def national_dashboard():
    from firebase_config import get_firestore_db
    from datetime import datetime
    from collections import defaultdict
    import calendar

    def _parse_ts(raw):
        """Convert Firestore Timestamp / ISO string / datetime to (datetime, str) tuple."""
        if not raw:
            return None, 'N/A'
        try:
            if hasattr(raw, 'ToDatetime'):
                dt = raw.ToDatetime()
            elif hasattr(raw, 'strftime'):
                dt = raw
            elif isinstance(raw, str):
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            else:
                return None, 'N/A'
            return dt, dt.strftime('%b %d, %Y')
        except Exception:
            return None, 'N/A'

    try:
        db = get_firestore_db()

        # ── 1. Applications ───────────────────────────────────────────────
        applications = []
        app_region_count = defaultdict(int)
        app_monthly = defaultdict(int)
        app_approved = app_pending = app_rejected = 0

        for doc in db.collection('applications').stream():
            data = doc.to_dict()
            status = (data.get('status') or 'pending').lower()
            if status not in ['approved', 'to review', 'review']:
                continue

            nat_status = (data.get('nationalStatus') or 'pending').lower()
            if nat_status == 'approved':
                app_approved += 1
            elif nat_status == 'rejected':
                app_rejected += 1
            else:
                app_pending += 1

            created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed')
            date_obj, date_str = _parse_ts(created_at)
            if date_obj:
                app_monthly[date_obj.strftime('%Y-%m')] += 1

            region = data.get('region') or 'N/A'
            if region and region != 'N/A':
                app_region_count[region] += 1

            applications.append({
                'id': doc.id,
                'created_at': date_str,
                '_sort_key': date_obj.isoformat() if date_obj else '',
                'reference_id': doc.id[:10].upper(),
                'applicant_name': data.get('applicantName') or data.get('fullName') or data.get('name') or 'N/A',
                'category': data.get('category') or data.get('applicantCategory') or 'N/A',
                'region': region,
                'status': nat_status,
            })
        applications.sort(key=lambda x: x['_sort_key'], reverse=True)

        # ── 2. Service Requests ───────────────────────────────────────────
        service_requests = []
        sr_type_count = defaultdict(int)
        sr_region_count = defaultdict(int)
        sr_monthly = defaultdict(int)
        sr_approved = sr_pending = sr_rejected = 0

        for doc in db.collection('service_requests').stream():
            data = doc.to_dict()
            nat_status = (data.get('nationalStatus') or 'pending').lower()
            if nat_status == 'approved':
                sr_approved += 1
            elif nat_status == 'rejected':
                sr_rejected += 1
            else:
                sr_pending += 1
            created_at = data.get('createdAt')
            date_obj, date_str = _parse_ts(created_at)
            if date_obj:
                sr_monthly[date_obj.strftime('%Y-%m')] += 1

            stype = data.get('serviceType') or data.get('type') or data.get('category') or 'N/A'
            sr_type_count[stype] += 1
            region = data.get('region') or data.get('province') or 'N/A'
            if region and region != 'N/A':
                sr_region_count[region] += 1

            service_requests.append({
                'id': doc.id,
                'date_filed': date_str,
                '_sort_key': date_obj.isoformat() if date_obj else '',
                'reference_id': doc.id[-6:].upper(),
                'service_type': stype,
                'region': region,
                'status': nat_status,
            })
        service_requests.sort(key=lambda x: x['_sort_key'], reverse=True)

        # ── 3. Transactions / Collections ────────────────────────────────
        transactions = []
        total_collections = 0.0

        for doc in db.collection('transactions').stream():
            data = doc.to_dict()
            raw_status = (data.get('status') or '').upper()
            amount_val = float(data.get('amount') or 0)
            if raw_status == 'PAID':
                total_collections += amount_val

            _, date_str2 = _parse_ts(data.get('created_at') or data.get('createdAt'))

            transactions.append({
                'ref': (data.get('external_id') or doc.id[:8]).upper(),
                'date': date_str2,
                'payor': data.get('user_email') or data.get('fullName') or 'N/A',
                'description': data.get('transaction_name') or data.get('description') or 'Payment',
                'amount': f"{amount_val:,.2f}",
                'status': raw_status,
            })
        transactions.reverse()  # most recent first
        transactions = transactions[:20]

        # ── 4 & 5. Permits + Inventory Items (single query) ─────────────
        permits = []
        inventory_items = []
        cat_map = {
            'farm-visit': 'Chemicals', 'fishery-permit': 'Marine Res.',
            'livestock': 'Livestock', 'forest': 'Forest Res.',
            'wildlife': 'Wildlife', 'environment': 'Environment'
        }
        for doc in db.collection('license_applications').stream():
            data = doc.to_dict()
            fd = data.get('formData') or {}
            region = fd.get('region') or data.get('region') or 'N/A'
            status_raw = (data.get('status') or 'pending').lower()
            disp = 'Valid' if status_raw == 'approved' else ('Expired' if status_raw == 'rejected' else 'Pending')
            permits.append({
                'ref': 'LIC-' + doc.id[-6:].upper(),
                'region': region,
                'status': disp,
                'status_raw': status_raw,
            })
            atype = data.get('applicationType') or 'N/A'
            cat = cat_map.get(str(atype).lower(), 'General')
            inventory_items.append({
                'category': cat,
                'quantity': data.get('quantity') or 1,
                'hub': region,
            })
        permits = permits[:15]
        inventory_items = inventory_items[:15]

        # ── 6. Trend (last 6 months, combined apps + SR) ─────────────────
        now = datetime.now()
        trend_labels = []
        trend_data = []
        for i in range(5, -1, -1):
            yr = now.year
            mo = now.month - i
            while mo <= 0:
                mo += 12
                yr -= 1
            key = f"{yr}-{mo:02d}"
            trend_labels.append(calendar.month_abbr[mo] + ' ' + str(yr))
            trend_data.append(app_monthly.get(key, 0) + sr_monthly.get(key, 0))

        # ── 7. Category chart (service request types) ───────────────────
        cat_keywords = {
            'Farm Visit': ['farm', 'crop', 'pest'],
            'Chemical/Fert.': ['chemical', 'fertilizer', 'pesticide'],
            'Financial Aid': ['subsidy', 'grant', 'loan', 'startup', 'financial'],
            'Seminar': ['seminar', 'training', 'workshop'],
            'Wildlife': ['wildlife', 'animal'],
            'Fisheries': ['fish', 'aqua'],
            'Forestry': ['forest', 'timber', 'tree'],
        }
        cat_counts = {k: 0 for k in cat_keywords}
        for stype, cnt in sr_type_count.items():
            sl = stype.lower()
            matched = False
            for cat, kws in cat_keywords.items():
                if any(k in sl for k in kws):
                    cat_counts[cat] += cnt
                    matched = True
                    break
            if not matched:
                cat_counts['Farm Visit'] += cnt
        category_labels = list(cat_counts.keys())
        category_data = list(cat_counts.values())

        # ── 8. Regional chart ─────────────────────────────────────────────
        combined_region = defaultdict(int)
        for r, c in app_region_count.items():
            combined_region[r] += c
        for r, c in sr_region_count.items():
            combined_region[r] += c
        top_regions = sorted(combined_region.items(), key=lambda x: x[1], reverse=True)[:8]
        region_labels = [r[0] for r in top_regions] if top_regions else ['N/A']
        region_data = [r[1] for r in top_regions] if top_regions else [0]

        # ── 9. Totals ─────────────────────────────────────────────────────
        total_applications = len(applications)
        total_service_requests = len(service_requests)
        total_count = total_applications + total_service_requests
        approved_count = app_approved + sr_approved
        pending_count = app_pending + sr_pending
        rejected_count = app_rejected + sr_rejected

    except Exception as e:
        print(f"[national_dashboard] Error: {e}")
        import traceback; traceback.print_exc()
        applications = service_requests = transactions = permits = inventory_items = []
        total_collections = total_count = approved_count = pending_count = rejected_count = 0
        total_applications = total_service_requests = 0
        trend_labels = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
        trend_data = category_data = region_data = [0] * 6
        category_labels = ['Farm Visit', 'Chemical/Fert.', 'Financial Aid', 'Seminar', 'Wildlife', 'Fisheries', 'Forestry']
        region_labels = ['N/A']
        as_of = datetime.now().strftime('%b %d, %Y %I:%M %p')

    return render_template(
        'national/landing-national.html',
        applications=applications,
        service_requests=service_requests,
        transactions=transactions,
        permits=permits,
        inventory_items=inventory_items,
        total_collections=total_collections,
        total_count=total_count,
        total_applications=total_applications,
        total_service_requests=total_service_requests,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        trend_labels=trend_labels,
        trend_data=trend_data,
        category_labels=category_labels,
        category_data=category_data,
        region_labels=region_labels,
        region_data=region_data,
        as_of=datetime.now().strftime('%b %d, %Y %I:%M %p'),
    )


@bp.route('/national/system-logs')
@role_required('national', 'national_admin')
def national_system_logs_fallback():
    """
    Show only regional transactions and fund transfers in the national audit log page.
    """
    from firebase_config import get_firestore_db
    from datetime import datetime
    db = get_firestore_db()
    regional_logs = []
    try:
        # Fetch all transactions (regional scope)
        tx_docs = db.collection('transactions').limit(5000).stream()
        for tx_doc in tx_docs:
            tx = tx_doc.to_dict() or {}
            status_value = str(tx.get('status') or '').strip().upper() or 'PENDING'
            ts_value = (
                tx.get('updated_at')
                or tx.get('forwarded_at')
                or tx.get('created_at')
                or tx.get('createdAt')
                or tx.get('updatedAt')
            )
            outcome_value = 'SUCCESS' if status_value in {'PAID', 'APPROVED', 'COMPLETED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')
            regional_logs.append({
                'id': tx_doc.id,
                'ts': ts_value,
                'user': tx.get('updated_by') or tx.get('forwarded_by') or tx.get('user_email') or 'User',
                'role': 'Municipal',
                'module': 'PAYMENTS',
                'action': status_value,
                'target': tx.get('transaction_name') or tx.get('description') or 'Payment',
                'targetId': tx.get('invoice_id') or tx.get('external_id') or tx_doc.id,
                'device_type': tx.get('device_type') or tx.get('device') or '',
                'ip': tx.get('ip') or '',
                'outcome': outcome_value,
                'message': tx.get('description') or '',
                'forwarded_message': tx.get('forwarded_message') or tx.get('forwardMessage') or '',
                'forwarded_by': tx.get('forwarded_by') or '',
                'municipality': tx.get('municipality') or tx.get('municipality_name') or tx.get('target_municipality') or '',
                'region': tx.get('region') or tx.get('region_name') or tx.get('regionName') or '',
                'canReview': status_value == 'FORWARDED',
                'diff': tx,
            })

        # Fetch all regional fund transfers
        fund_docs = db.collection('regional_fund_distribution').limit(5000).stream()
        for fund_doc in fund_docs:
            fund = fund_doc.to_dict() or {}
            status_value = str(fund.get('status') or '').strip().upper() or 'PENDING'
            ts_value = fund.get('updated_at') or fund.get('created_at') or fund.get('date')
            outcome_value = 'SUCCESS' if status_value in {'COMPLETED', 'APPROVED', 'RELEASED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')
            regional_logs.append({
                'id': fund_doc.id,
                'ts': ts_value,
                'user': fund.get('updated_by') or fund.get('initiated_by') or 'Regional Office',
                'role': 'Regional',
                'module': 'FUND_TRANSFER',
                'action': status_value,
                'target': fund.get('region') or 'Region',
                'targetId': fund.get('reference') or fund_doc.id,
                'device_type': '',
                'ip': fund.get('ip') or '',
                'outcome': outcome_value,
                'message': fund.get('description') or '',
                'forwarded_message': '',
                'forwarded_by': '',
                'municipality': '',
                'region': fund.get('region') or fund.get('region_name') or fund.get('regionName') or '',
                'canReview': False,
                'diff': fund,
            })

        # Sort logs by timestamp descending (most recent first)
        def _parse_ts(ts):
            if not ts:
                return datetime.min
            try:
                if isinstance(ts, datetime):
                    return ts
                if isinstance(ts, str):
                    return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                pass
            return datetime.min
        regional_logs.sort(key=lambda x: _parse_ts(x.get('ts')), reverse=True)
    except Exception as e:
        print(f"[national_system_logs_fallback] Error: {e}")
        regional_logs = []

    # Map 'ts' to 'timestamp' and 'message' to 'details' for frontend compatibility
    for log in regional_logs:
        log['timestamp'] = log.get('ts', '')
        log['details'] = log.get('message', '')
    # Debug: Print the number of logs and a sample log
    print(f"[DEBUG] regional_logs count: {len(regional_logs)}")
    if regional_logs:
        print(f"[DEBUG] Sample regional_log: {regional_logs[0]}")
    return render_template('national/system/system-logs.html',
        regional_logs=regional_logs,
        municipal_logs=[],
        user_logs=[]
    )

# Add budget endpoint (must be top-level)
@bp.route('/national/accounting/add-budget', methods=['POST'])
@role_required('national','national_admin')
def add_budget():
    from flask import request, jsonify
    from firebase_config import get_firestore_db
    db = get_firestore_db()
    amount = request.json.get('amount')
    try:
        db.collection('finance').document('national').set({'budget': amount}, merge=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Accounting dashboard endpoint (must be top-level)
@bp.route('/national/accounting/dashboard')
@role_required('national','national_admin')
def national_accounting_dashboard_view():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        finance_data = {}
        regional_funds = []
        try:
            doc = db.collection('finance').document('national').get()
            if doc.exists:
                finance_data['national'] = doc.to_dict()
            else:
                finance_data['national'] = {}
            # Fetch regional fund distribution records
            funds_query = db.collection('regional_fund_distribution').order_by('date', direction='DESCENDING').stream()
            for fund_doc in funds_query:
                fund = fund_doc.to_dict()
                regional_funds.append(fund)
            # Sum all municipalities' general funds
            muni_docs = db.collection('finance').stream()
            total_general_fund = 0
            for mdoc in muni_docs:
                mdata = mdoc.to_dict()
                if mdoc.id not in ['national']:
                    try:
                        total_general_fund += float(mdata.get('general_fund', 0))
                    except Exception:
                        pass
            finance_data['national']['municipal_general_fund_total'] = total_general_fund
        except Exception:
            finance_data['national'] = {}
        return render_template('national/accounting/accounting-dashboard.html', finance=finance_data, regional_funds=regional_funds)
    except Exception as e:
        print(f"Error in national accounting dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('national/accounting/accounting-dashboard.html', finance={}, regional_funds=[])

@bp.route('/regional/dashboard')
@role_required('regional','regional_admin')
def regional_dashboard():
    return render_template('regional/landing-regional.html')

@bp.route('/super-admin/dashboard')
@role_required('super-admin','superadmin')
def superadmin_dashboard():
    return render_template('super-admin/landing-superadmin.html')

@bp.route('/farmer/dashboard')
@firebase_auth_required
def farmer_dashboard():
    return render_template('farmer_dashboard.html')

@bp.route('/dashboard')
@firebase_auth_required
def dashboard():
    return render_template('dashboard.html')

@bp.route('/user/dashboard')
@role_required('user')
def user_dashboard():
    return render_template('user/dashboard.html')

@bp.route('/user/profile')
@role_required('user')
def user_profile():
    return render_template('user/profile.html')

@bp.route('/user/transaction')
@role_required('user')
def user_transaction():
    return render_template('user/transaction.html')

@bp.route('/user/my-documents')
@role_required('user')
def user_my_documents():
    return render_template('user/my-documents.html')

@bp.route('/user/transaction-history')
@role_required('user')
def user_transaction_history():
    return render_template('user/transaction-history.html')

@bp.route('/user/history')
@role_required('user')
def user_history():
    return render_template('user/history.html')

@bp.route('/user/application')
@role_required('user')
def user_application():
    return render_template('user/application.html')

@bp.route('/user/application/apply')
@role_required('user')
def user_application_apply():
    return render_template('user/app-form.html')

@bp.route('/approval-status')
@firebase_auth_required
def approval_status():
    return render_template('approval_status.html')

@bp.route('/payment-success')
@firebase_auth_required
def payment_success():
    return render_template('payment-success.html')

@bp.route('/payment-failed')
@firebase_auth_required
def payment_failed():
    return render_template('payment-failed.html')

# Inventory routes
@bp.route('/user/inventory')
@role_required('user')
def user_inventory():
    return render_template('user/inventory/stock-list.html')

@bp.route('/user/inventory/add')
@role_required('user')
def user_inventory_add():
    return render_template('user/inventory/stock-form.html')


# Updated route to accept app_id as path parameter
@bp.route('/user/inventory/stock-info/<app_id>')
@role_required('user')
def inventory_stock_info(app_id):
     """Shows inventory stock info page for a specific item"""
     return render_template('user/inventory/stock-info.html')

@bp.route('/user/inventory/history')
@role_required('user')
def user_inventory_history():
    return render_template('user/inventory/stock-history.html')


@bp.route('/national/accounting/accounting-dashboard')
@role_required('national','national_admin')
def national_accounting_dashboard():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        finance_data = {}
        try:
            docs = db.collection('finance').stream()
            for doc in docs:
                finance_data.update(doc.to_dict())
        except Exception:
            pass
        return render_template('national/accounting/accounting-dashboard.html', finance=finance_data)
    except Exception as e:
        print(f"Error in national accounting dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('national/accounting/accounting-dashboard.html', finance={})
    
    # Fund distribution endpoint for national admin
@bp.route('/national/accounting/distribute-fund', methods=['POST'])
@role_required('national','national_admin')
def distribute_fund_to_region():
    from flask import request, jsonify
    from firebase_config import get_firestore_db
    import datetime
    db = get_firestore_db()
    data = request.get_json()
    region = str(data.get('region', '')).upper().replace('–', '-').replace('—', '-').replace('  ', ' ').replace(' ', '-')
    amount = data.get('amount')
    fund_type = data.get('fundType')
    # Add record to regional_fund_distribution
    try:
        record = {
            'region': region,
            'amount': amount,
            'fund_type': fund_type,
            'date': datetime.datetime.utcnow().isoformat(),
            'status': 'Released'
        }
        db.collection('regional_fund_distribution').add(record)
        # Also record in finance_transfers collection
        db.collection('finance_transfers').add({
            'region': region,
            'amount': amount,
            'fund_type': fund_type,
            'date': record['date'],
            'status': 'Released',
            'source': 'national',
            'type': 'national_to_regional'
        })
        # Deduct from national budget
        national_doc = db.collection('finance').document('national').get()
        if national_doc.exists:
            national_data = national_doc.to_dict()
            current_budget = float(national_data.get('budget', 0))
            new_budget = current_budget - float(amount)
            db.collection('finance').document('national').set({'budget': new_budget}, merge=True)

        # Record funds received by region in finance collection
        regional_finance_doc = db.collection('finance').document(region).get()
        if regional_finance_doc.exists:
            regional_data = regional_finance_doc.to_dict()
            prev_received = float(regional_data.get('received_from_national', 0))
            db.collection('finance').document(region).set({
                'received_from_national': prev_received + float(amount)
            }, merge=True)
        else:
            db.collection('finance').document(region).set({
                'received_from_national': float(amount)
            })
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@bp.route('/announcement')
@role_required('user')
def announcement_main():
    return render_template('user/announcement.html')

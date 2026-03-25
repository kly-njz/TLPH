from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from firebase_auth_middleware import role_required, firebase_auth_required
import time
from datetime import datetime
from collections import defaultdict
import calendar

bp = Blueprint('main', __name__)

# ✅ Centralized Firestore access
def get_db():
    from firebase_config import get_firestore_db
    return get_firestore_db()


# 🔥 OPTIMIZED HOME ROUTE (NO SPAM READS)
@bp.route('/')
def index():
    print("HOME.HTML IS BEING RENDERED")

    user_id = session.get('user_id')

    if user_id:
        # Refresh every 5 minutes only
        if (
            'user_status' not in session or
            'user_status_time' not in session or
            time.time() - session['user_status_time'] > 300
        ):
            try:
                db = get_db()
                user_doc = db.collection('users').document(user_id).get()

                if user_doc.exists:
                    data = user_doc.to_dict()
                    session['user_status'] = data.get('status', 'active').lower()
                    session['role'] = data.get('role', '').lower()
                else:
                    session['user_status'] = 'active'

                session['user_status_time'] = time.time()

            except Exception as e:
                print("[Firestore ERROR - index]:", e)

        if session.get('user_status') == 'disabled':
            return redirect(url_for('account_disabled'))

    return render_template('home.html')


@bp.route('/login')
def login():
    return render_template('login.html')


@bp.route('/register')
def register():
    return render_template('signup.html')


# ===========================
# 🔥 NATIONAL DASHBOARD (OPTIMIZED)
# ===========================
@bp.route('/national/dashboard')
@role_required('national','national_admin')
def national_dashboard():

    def _parse_ts(raw):
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
        except:
            return None, 'N/A'

    try:
        db = get_db()

        # 🔥 LIMIT applied (VERY IMPORTANT)
        applications_ref = db.collection('applications').limit(100)
        service_ref = db.collection('service_requests').limit(100)
        transactions_ref = db.collection('transactions').limit(100)
        license_ref = db.collection('license_applications').limit(100)

        applications = []
        service_requests = []
        transactions = []
        permits = []
        inventory_items = []

        total_collections = 0.0

        # ================= APPLICATIONS =================
        app_monthly = defaultdict(int)
        for doc in applications_ref.stream():
            data = doc.to_dict()
            created_at = data.get('createdAt')
            date_obj, date_str = _parse_ts(created_at)

            if date_obj:
                app_monthly[date_obj.strftime('%Y-%m')] += 1

            applications.append({
                'id': doc.id,
                'created_at': date_str,
                'reference_id': doc.id[:10].upper(),
                'applicant_name': data.get('applicantName', 'N/A'),
                'region': data.get('region', 'N/A'),
                'status': data.get('status', 'pending')
            })

        # ================= SERVICE REQUESTS =================
        sr_monthly = defaultdict(int)
        for doc in service_ref.stream():
            data = doc.to_dict()

            date_obj, date_str = _parse_ts(data.get('createdAt'))
            if date_obj:
                sr_monthly[date_obj.strftime('%Y-%m')] += 1

            service_requests.append({
                'id': doc.id,
                'date_filed': date_str,
                'reference_id': doc.id[-6:].upper(),
                'service_type': data.get('serviceType', 'N/A'),
                'region': data.get('region', 'N/A'),
                'status': data.get('nationalStatus', 'pending')
            })

        # ================= TRANSACTIONS =================
        for doc in transactions_ref.stream():
            data = doc.to_dict()
            amount = float(data.get('amount', 0))

            if data.get('status') == 'PAID':
                total_collections += amount

            transactions.append({
                'ref': doc.id[:8].upper(),
                'amount': f"{amount:,.2f}",
                'status': data.get('status', 'N/A')
            })

        # ================= LICENSE =================
        for doc in license_ref.stream():
            data = doc.to_dict()
            permits.append({
                'ref': doc.id[-6:].upper(),
                'status': data.get('status', 'pending')
            })

            inventory_items.append({
                'category': data.get('applicationType', 'General'),
                'quantity': data.get('quantity', 1)
            })

        # ================= TREND =================
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
            trend_labels.append(calendar.month_abbr[mo])
            trend_data.append(app_monthly.get(key, 0) + sr_monthly.get(key, 0))

    except Exception as e:
        print("[Dashboard ERROR]:", e)
        applications = service_requests = transactions = permits = inventory_items = []
        total_collections = 0
        trend_labels = ['Jan','Feb','Mar','Apr','May','Jun']
        trend_data = [0]*6

    return render_template(
        'national/landing-national.html',
        applications=applications,
        service_requests=service_requests,
        transactions=transactions,
        permits=permits,
        inventory_items=inventory_items,
        total_collections=total_collections,
        trend_labels=trend_labels,
        trend_data=trend_data
    )


# ===========================
# OTHER ROUTES (UNCHANGED)
# ===========================
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


# ===========================
# ACCOUNTING (OPTIMIZED)
# ===========================
@bp.route('/national/accounting/dashboard')
@role_required('national','national_admin')
def accounting_dashboard():
    try:
        db = get_db()

        finance_doc = db.collection('finance').document('national').get()
        finance = finance_doc.to_dict() if finance_doc.exists else {}

        return render_template('national/accounting/accounting-dashboard.html', finance=finance)

    except Exception as e:
        print("[Accounting ERROR]:", e)
        return render_template('national/accounting/accounting-dashboard.html', finance={})


@bp.route('/national/accounting/add-budget', methods=['POST'])
@role_required('national','national_admin')
def add_budget():
    try:
        db = get_db()
        amount = request.json.get('amount')

        db.collection('finance').document('national').set({'budget': amount}, merge=True)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
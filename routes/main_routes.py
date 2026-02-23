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
    # TODO: Replace with real Firestore/database queries
    total_collections = 0
    total_applications = 0
    total_service_requests = 0
    total_count = 0
    approved_count = 0
    pending_count = 0
    return render_template(
        'national/landing-national.html',
        total_collections=total_collections,
        total_applications=total_applications,
        total_service_requests=total_service_requests,
        total_count=total_count,
        approved_count=approved_count,
        pending_count=pending_count
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
        # Deduct from national budget
        national_doc = db.collection('finance').document('national').get()
        if national_doc.exists:
            national_data = national_doc.to_dict()
            current_budget = float(national_data.get('budget', 0))
            new_budget = current_budget - float(amount)
            db.collection('finance').document('national').set({'budget': new_budget}, merge=True)
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

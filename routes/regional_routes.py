from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('regional', __name__, url_prefix='/regional')

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

@bp.route('/service-view')
@role_required('regional','regional_admin')
def service_info_view():
    return render_template('regional/service-regional-view.html')

@bp.route('/inventory-view')
@role_required('regional','regional_admin')
def inventory_view():
    return render_template('regional/inventory-regional-list.html')

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

@bp.route('/audit-logs-view')
@role_required('regional','regional_admin')
def audit_logs_view():
    return render_template('regional/audit-logs-regional-view.html')

@bp.route('/application-view/<application_id>')
@role_required('regional','regional_admin')
def application_view(application_id):
    return render_template('regional/application-regional-view.html')

@bp.route('/hrm/company')
@role_required('regional','regional_admin')
def company_view():
    return render_template('regional/HR/company-regional.html')

@bp.route('/hrm/departments')
@role_required('regional','regional_admin')
def departments_view():
    return render_template('regional/HR/department-regional.html')

@bp.route('/hrm/designations')
@role_required('regional','regional_admin')
def designations_view():
    return render_template('regional/HR/designation-regional.html')

@bp.route('/hrm/office-shifts')
@role_required('regional','regional_admin')
def office_shifts_view():
    return render_template('regional/HR/office-shift-regional.html')

@bp.route('/hrm/employees')
@role_required('regional','regional_admin')
def employees_view():
    return render_template('regional/HR/employee-regional.html')

@bp.route('/hrm/attendance')
@role_required('regional','regional_admin')
def attendance_view():
    return render_template('regional/HR/attendance-regional.html')

@bp.route('/hrm/holidays')
@role_required('regional','regional_admin')
def holidays_view():
    return render_template('regional/HR/holiday-regional.html')

@bp.route('/hrm/leave-requests')
@role_required('regional','regional_admin')
def leave_requests_view():
    return render_template('regional/HR/leave-request-regional.html')

@bp.route('/hrm/payroll-system')
@role_required('regional','regional_admin')
def payroll_system_view():
    return render_template('regional/HR/payroll-regional.html')

@bp.route('/accounting/accounting-dashboard')
@role_required('regional','regional_admin')
def accounting_dashboard_view():
    from firebase_admin import firestore
    db = firestore.client()
    finance_data = {}
    try:
        docs = db.collection('finance').stream()
        for doc in docs:
            finance_data.update(doc.to_dict())
    except Exception:
        pass
    municipalities = []
    try:
        docs = db.collection('municipalities').stream()
        for doc in docs:
            municipalities.append(doc.id)
    except Exception:
        pass
    return render_template('regional/accounting/dashboard-regional.html', finance=finance_data, municipalities=municipalities)

@bp.route('/accounting/distribute-fund', methods=['POST'])
@role_required('regional','regional_admin')
def distribute_fund():
    from flask import request, jsonify
    from firebase_admin import firestore
    db = firestore.client()
    data = request.json
    muni = data.get('municipality')
    amount = data.get('amount')
    fund_type = data.get('fund_type')
    transfer_id = data.get('transfer_id')
    region = data.get('region')
    # Validate municipality belongs to region
    allowed_munis = []
    try:
        doc = db.collection('municipalities').document(region).get()
        if doc.exists:
            allowed_munis = doc.to_dict().get('municipalities', [])
    except Exception:
        pass
    if muni == 'ALL':
        # Distribute to all municipalities under this region
        for m in allowed_munis:
            record = {
                'municipality': m,
                'amount': amount,
                'fund_type': fund_type,
                'transfer_id': transfer_id + '-' + m,
                'region': region,
                'status': 'Released',
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            db.collection('municipal_fund_distribution').add(record)
        return jsonify({'success': True, 'distributed': allowed_munis})
    else:
        if muni not in allowed_munis:
            return jsonify({'success': False, 'error': 'Municipality not under your region'}), 403
        record = {
            'municipality': muni,
            'amount': amount,
            'fund_type': fund_type,
            'transfer_id': transfer_id,
            'region': region,
            'status': 'Released',
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        db.collection('municipal_fund_distribution').add(record)
        return jsonify({'success': True, 'distributed': [muni]})

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
    return render_template('regional/accounting/coa-templates-regional.html')

@bp.route('/accounting/accounting-entities')
@role_required('regional','regional_admin')
def accounting_entities_view():
    return render_template('regional/accounting/entities-regional.html')

@bp.route('/accounting/accounting-deposits')
@role_required('regional','regional_admin')
def accounting_deposits_view():
    return render_template('regional/accounting/deposit-category-regional.html')

@bp.route('/accounting/accounting-expenses')
@role_required('regional','regional_admin')
def accounting_expenses_view():
    return render_template('regional/accounting/expense-category-regional.html')
from flask import Blueprint, render_template, request, jsonify
from firebase_auth_middleware import role_required
from firebase_config import get_firestore_db

bp = Blueprint('municipal', __name__, url_prefix='/municipal')

@bp.route('/dashboard')
@role_required('municipal','municipal_admin')
def dashboard():
    return render_template('municipal/home-municipal/home-municipal.html')

@bp.route('/applications')
@role_required('municipal','municipal_admin')
def applications():
    return render_template('municipal/application-municipal/application-municipal-dashboard.html')

@bp.route('/applications/view/<application_id>')
@role_required('municipal','municipal_admin')
def view_application(application_id):
    return render_template('municipal/application-municipal/application-municipal-view-profile.html')

@bp.route('/applications/details/<application_id>')
@role_required('municipal','municipal_admin')
def application_details(application_id):
    return render_template('municipal/application-municipal/application-details.html')

@bp.route('/services')
@role_required('municipal','municipal_admin')
def services():
    return render_template('municipal/service-municipal/service-municipal-dashboard.html')

@bp.route('/services/view/<service_id>')
@role_required('municipal','municipal_admin')
def view_service(service_id):
    return render_template('municipal/service-municipal/service-municipal-view-profile.html')

@bp.route('/services/details/<service_id>')
@role_required('municipal','municipal_admin')
def service_details(service_id):
    return render_template('municipal/service-municipal/service-details.html')

@bp.route('/inventory')
@role_required('municipal','municipal_admin')
def inventory():
    return render_template('municipal/inventory/inventory-dashboard.html')

@bp.route('/user-inventory')
@role_required('municipal','municipal_admin')
def user_inventory():
    return render_template('municipal/user-inventory-municipal/user-inventory-municipal.html')

@bp.route('/license-permit')
@role_required('municipal','municipal_admin')
def license_permit():
    return render_template('municipal/license-permit-municapal/license-permit-municipal.html')

@bp.route('/license-permit/details/<license_id>')
@role_required('municipal','municipal_admin')
def license_details(license_id):
    return render_template('municipal/license-permit-municapal/license-details.html')

@bp.route('/transactions')
@role_required('municipal','municipal_admin')
def transactions():
    return render_template('municipal/transaction-municipal/transaction-municipal.html')

@bp.route('/users')
@role_required('municipal','municipal_admin')
def users():
    return render_template('municipal/user-management-municipal/user-management-municipal.html')

@bp.route('/profile')
@role_required('municipal','municipal_admin')
def profile():
    return render_template('municipal/municipal-profile.html')

@bp.route('/notification')
@role_required('municipal','municipal_admin')
def notification():
    return render_template('municipal/notification.html')

@bp.route('/company')
@role_required('municipal','municipal_admin')
def hrm_company():
    return render_template('municipal/hrm/company-municipal.html')

@bp.route('/department')
@role_required('municipal','municipal_admin')
def hrm_department():
    return render_template('municipal/hrm/department-municipal.html')

@bp.route('/designation')
@role_required('municipal','municipal_admin')
def hrm_designation():
    return render_template('municipal/hrm/designation-municipal.html')

@bp.route('/office-shift')
@role_required('municipal','municipal_admin')
def hrm_office_shift():
    return render_template('municipal/hrm/office-shift-municipal.html')

@bp.route('/employees')
@role_required('municipal','municipal_admin')
def hrm_employees():
    return render_template('municipal/hrm/employees-municipal.html')

@bp.route('/attendance')
@role_required('municipal','municipal_admin')
def hrm_attendance():
    return render_template('municipal/hrm/attendance-municipal.html')

@bp.route('/holiday')
@role_required('municipal','municipal_admin')
def hrm_holiday():

    # Fetch holidays directly from Firestore
    db = get_firestore_db()
    holidays = []
    try:
        docs = db.collection('holidays').stream()
        for doc in docs:
            holidays.append(doc.to_dict())
    except Exception:
        pass
    from datetime import datetime
    year = datetime.now().year
    return render_template(
        'municipal/hrm/holiday-municipal.html',
        holidays=holidays,
        year=year
    )

# API endpoint to update office status/hours for a holiday
@bp.route('/api/municipal/holiday/office-status', methods=['POST'])
@role_required('municipal','municipal_admin')
def update_holiday_office_status():
    db = get_firestore_db()
    data = request.json
    date = data.get('date')
    name = data.get('name')
    office_status = data.get('office_status')
    open_time = data.get('open_time')
    close_time = data.get('close_time')
    if not date or not name:
        return jsonify({'success': False, 'error': 'Missing date or name'}), 400
    doc_id = f"{date}|{name}"
    db.collection('holidays').document(doc_id).set({
        'date': date,
        'name': name,
        'office_status': office_status,
        'open_time': open_time,
        'close_time': close_time
    })
    return jsonify({'success': True})

@bp.route('/leave-request')
@role_required('municipal','municipal_admin')
def hrm_leave():
    return render_template('municipal/hrm/leave-municipal.html')

@bp.route('/payroll')
@role_required('municipal','municipal_admin')
def hrm_payroll():
    return render_template('municipal/hrm/payroll-municipal.html')

@bp.route('/municipal-profile-update')
@role_required('municipal','municipal_admin')
def municipal_profile_update():
    return render_template('municipal/municipal-profile-update.html')
@bp.route('/products/products-municipal')
@role_required('municipal','municipal_admin')
def products_municipal():
    return render_template('municipal/products/products-municipal.html')

@bp.route('/products/purchases-municipal')
@role_required('municipal','municipal_admin')
def purchases_municipal():
    return render_template('municipal/products/purchases-municipal.html')

@bp.route('/products/sales-municipal')
@role_required('municipal','municipal_admin')
def sales_municipal():
    return render_template('municipal/products/sales-municipal.html')

@bp.route('/products/sales-return-municipal')
@role_required('municipal','municipal_admin')
def sales_return_municipal():
    return render_template('municipal/products/sales-return-municipal.html')

@bp.route('/products/distributed-products-municipal')
@role_required('municipal','municipal_admin')
def distributed_products_municipal():
    return render_template('municipal/products/distributed-products-municipal.html')

@bp.route('/products/damage-products-municipal')
@role_required('municipal','municipal_admin')
def damage_products_municipal():
    return render_template('municipal/products/damage-products-municipal.html')

@bp.route('/products/transfer-products-municipal')
@role_required('municipal','municipal_admin')
def transfer_products_municipal():
    return render_template('municipal/products/transfer-products-municipal.html')

@bp.route('/products/stock-list-municipal')
@role_required('municipal','municipal_admin')
def stock_list_municipal():
    return render_template('municipal/products/stock-list-municipal.html')

@bp.route('/products/stock-movement-municipal')
@role_required('municipal','municipal_admin')
def stock_movement_municipal():
    return render_template('municipal/products/stock-movement-municipal.html')

@bp.route('/products/stock-adjustment-municipal')
@role_required('municipal','municipal_admin')
def stock_adjustment_municipal():
    return render_template('municipal/products/stock-adjustment-municipal.html')

@bp.route('/products/stock-reorder-municipal')
@role_required('municipal','municipal_admin')
def stock_reorder_municipal():
    return render_template('municipal/products/stock-reorder-municipal.html')

# --- Operations (Superadmin Extra) ---
@bp.route('/operations/quotations-municipal')
@role_required('municipal','municipal_admin')
def quotations_municipal():
    return render_template('municipal/operations/quotations-municipal.html')

@bp.route('/operations/projects-municipal')
@role_required('municipal','municipal_admin')
def projects_municipal():
    return render_template('municipal/operations/projects-municipal.html')

@bp.route('/operations/tasks-municipal')
@role_required('municipal','municipal_admin')
def tasks_municipal():
    return render_template('municipal/operations/task-municipal.html')

@bp.route('/operations/applicants-municipal')
@role_required('municipal','municipal_admin')
def applicants_municipal():
    return render_template('municipal/operations/applicants-municipal.html')

# --- Accounting ---
@bp.route('/accounting/dashboard-municipal')
@role_required('municipal','municipal_admin')
def accounting_dashboard_municipal():
    from flask import session
    from firebase_admin import firestore
    db = get_firestore_db()
    finance_data = {}
    municipality_name = None
    region_name = None
    province_name = None
    # Try to get municipality from session
    municipality_name = session.get('municipality') or session.get('user_municipality')
    region_name = session.get('region') or session.get('user_region')
    province_name = session.get('province') or session.get('user_province')
    # If not in session, try to get from user document
    if not municipality_name:
        user_id = session.get('user_id')
        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                municipality_name = user_data.get('municipality') or user_data.get('municipality_name')
                region_name = user_data.get('region') or user_data.get('region_name')
                province_name = user_data.get('province') or user_data.get('province_name')
    # Fetch finance data for this municipality only
    try:
        if municipality_name and province_name:
            doc_id = f"{municipality_name.upper().replace(' ', '_')}_{province_name.upper().replace(' ', '_')}"
            doc = db.collection('finance').document(doc_id).get()
            if doc.exists:
                finance_data = doc.to_dict()
        elif municipality_name:
            # fallback: try old style (just municipality name)
            doc = db.collection('finance').document(municipality_name).get()
            if doc.exists:
                finance_data = doc.to_dict()
        else:
            # fallback: fetch all (should not happen)
            docs = db.collection('finance').stream()
            for doc in docs:
                finance_data.update(doc.to_dict())
    except Exception:
        pass
    revenue_mix = []
    try:
        if municipality_name:
            docs = db.collection('revenue_mix').where('municipality', '==', municipality_name).stream()
            for doc in docs:
                revenue_mix.append(doc.to_dict())
        else:
            docs = db.collection('revenue_mix').stream()
            for doc in docs:
                revenue_mix.append(doc.to_dict())
    except Exception:
        pass
    # Fetch regional-to-municipal fund transfer activity for this municipality
    fund_activity = []
    try:
        if municipality_name and province_name:
            docs = db.collection('municipal_fund_distribution') \
                .where('municipality', '==', municipality_name) \
                .where('province', '==', province_name) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .stream()
            for doc in docs:
                fund_activity.append(doc.to_dict())
    except Exception as e:
        print(f"[DEBUG] Error fetching fund_activity: {e}")

    return render_template(
        'municipal/accounting/dashboard-municipal.html',
        finance=finance_data,
        revenue_mix=revenue_mix,
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name,
        fund_activity=fund_activity
    )

@bp.route('/accounting/entities-municipal')
@role_required('municipal','municipal_admin')
def accounting_entities_municipal():
    from flask import session
    municipality_name = session.get('municipality') or session.get('user_municipality')
    region_name = session.get('region') or session.get('user_region')
    province_name = session.get('province') or session.get('user_province')
    return render_template('municipal/accounting/entities-municipal.html',
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name
    )

@bp.route('/accounting/coa-templates-municipal')
@role_required('municipal','municipal_admin')
def accounting_coa_templates_municipal():
    from flask import session
    municipality_name = session.get('municipality') or session.get('user_municipality')
    region_name = session.get('region') or session.get('user_region')
    province_name = session.get('province') or session.get('user_province')
    return render_template('municipal/accounting/coa-templates-municipal.html',
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name
    )

@bp.route('/accounting/expense-category-municipal')
@role_required('municipal','municipal_admin')
def accounting_expense_category_municipal():
    return render_template('municipal/accounting/expense-category-municipal.html')

@bp.route('/accounting/deposit-category-municipal')
@role_required('municipal','municipal_admin')
def accounting_deposit_category_municipal():
    return render_template('municipal/accounting/deposit-category-municipal.html')

# --- Logs ---
@bp.route('/logs/audit-logs-municipal')
@role_required('municipal','municipal_admin')
def logs_audit_logs_municipal():
    return render_template('municipal/logs/audit-logs-municipal.html')

# API endpoint for audit logs (real payment/fund transfer logs)
from routes.municipal_api_logs import bp as municipal_api_logs_bp

@bp.route('/api/municipal/holiday/import-calendarific', methods=['POST'])
@role_required('municipal','municipal_admin')
def import_calendarific_holidays():
    import requests
    from datetime import datetime
    api_key = "IXURogg3lF44kINLW5AxDlIH0Pd33BGl"
    year = datetime.now().year
    url = f"https://calendarific.com/api/v2/holidays?api_key={api_key}&country=PH&year={year}&type=national"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({'success': False, 'error': 'Calendarific API error'}), 500
    holidays = resp.json().get('response', {}).get('holidays', [])
    imported = []
    for h in holidays:
        date_iso = h['date']['iso'] if 'date' in h and 'iso' in h['date'] else h.get('date', {}).get('datetime', {}).get('iso', '')
        name = h.get('name', '')
        description = h.get('description', '')
        holiday_type = h['type'][0] if 'type' in h and h['type'] else 'National Holiday'
        if date_iso and name:
            from transaction_storage import add_holiday_to_firestore
            doc_id = add_holiday_to_firestore(date_iso, name, description, holiday_type)
            imported.append(doc_id)
    return jsonify({'success': True, 'imported': imported})
from transaction_storage import add_holiday_to_firestore

@bp.route('/api/municipal/holiday/add', methods=['POST'])
@role_required('municipal','municipal_admin')
def add_holiday():
    data = request.json
    date_iso = data.get('date')
    name = data.get('name')
    description = data.get('description', '')
    holiday_type = data.get('type', 'National Holiday')
    office_status = data.get('office_status', 'closed')
    open_time = data.get('open_time', '')
    close_time = data.get('close_time', '')
    if not date_iso or not name:
        return jsonify({'success': False, 'error': 'Missing date or name'}), 400
    doc_id = add_holiday_to_firestore(date_iso, name, description, holiday_type, office_status, open_time, close_time)
    return jsonify({'success': True, 'doc_id': doc_id})
# Add this route at the end of the file:
#
# @bp.route('/municipal-profile-update')
# @role_required('municipal','municipal_admin')
# def municipal_profile_update():
#     return render_template('municipal/municipal-profile-update.html')
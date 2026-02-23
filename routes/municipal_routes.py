# Add this route at the end of the file:
#
# @bp.route('/municipal-profile-update')
# @role_required('municipal','municipal_admin')
# def municipal_profile_update():
#     return render_template('municipal/municipal-profile-update.html')
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

    # --- Calendarific integration ---
    import requests
    api_key = "IXURogg3lF44kINLW5AxDlIH0Pd33BGl"
    from datetime import datetime
    year = datetime.now().year
    holidays = []
    try:
        url = f"https://calendarific.com/api/v2/holidays?api_key={api_key}&country=PH&year={year}&type=national"
        resp = requests.get(url)
        if resp.status_code == 200:
            holidays = resp.json().get('response', {}).get('holidays', [])
    except Exception as e:
        holidays = []

    # Fetch office status/hours from Firestore and merge
    db = get_firestore_db()
    office_status_map = {}
    try:
        docs = db.collection('holidays').stream()
        for doc in docs:
            data = doc.to_dict()
            key = data.get('date') + '|' + data.get('name')
            office_status_map[key] = data
    except Exception:
        pass
    # Merge office status/hours into holidays
    for h in holidays:
        date_str = h['date']['iso'] if 'date' in h and 'iso' in h['date'] else h.get('date', {}).get('datetime', {}).get('iso', '')
        key = date_str + '|' + h.get('name', '')
        if key in office_status_map:
            h['office_status'] = office_status_map[key].get('office_status', 'closed')
            h['open_time'] = office_status_map[key].get('open_time', '')
            h['close_time'] = office_status_map[key].get('close_time', '')
        else:
            h['office_status'] = 'closed'
            h['open_time'] = ''
            h['close_time'] = ''
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
    return render_template('municipal/accounting/dashboard-municipal.html')

@bp.route('/accounting/entities-municipal')
@role_required('municipal','municipal_admin')
def accounting_entities_municipal():
    return render_template('municipal/accounting/entities-municipal.html')

@bp.route('/accounting/coa-templates-municipal')
@role_required('municipal','municipal_admin')
def accounting_coa_templates_municipal():
    return render_template('municipal/accounting/coa-templates-municipal.html')

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


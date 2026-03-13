from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from firebase_auth_middleware import role_required
from firebase_config import get_firestore_db
from .municipal_api_logs import _resolve_municipality_from_user_context
import json
from datetime import datetime

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
    return redirect(url_for('municipal.inventory'))

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
    db = get_firestore_db()
    companies = []

    try:
        # Get the logged-in user's municipality
        user_municipality = _resolve_municipality_from_user_context()
        
        if user_municipality:
            # Fetch only the company for the user's municipality
            query = db.collection('companies').where('municipality', '==', user_municipality).limit(1)
            for doc in query.stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                companies.append(item)
            
            if not companies:
                print(f"[WARN] No company found for municipality: {user_municipality}")
        else:
            print(f"[WARN] Could not resolve user municipality")
    except Exception as e:
        print(f"Error fetching companies: {e}")
        import traceback
        traceback.print_exc()

    # Convert all datetime objects to ISO format strings and serialize with proper JSON encoder
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    # Convert companies to JSON string, then back to dict for Jinja2
    companies_json = json.dumps(companies, default=json_serializer, separators=(',', ':'))
    print(f"[DEBUG] Serialized JSON length: {len(companies_json)}")
    print(f"[DEBUG] First 200 chars: {companies_json[:200]}")
    
    return render_template('municipal/hrm/company-municipal.html', companies_json=companies_json)

@bp.route('/department')
@role_required('municipal','municipal_admin')
def hrm_department():
    db = get_firestore_db()
    departments = []
    employees = []
    designations = []

    try:
        for doc in db.collection('departments').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            departments.append(item)
    except Exception:
        pass

    try:
        for doc in db.collection('employees').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            employees.append(item)
    except Exception:
        pass

    try:
        for doc in db.collection('designations').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            designations.append(item)
    except Exception:
        pass

    return render_template(
        'municipal/hrm/department-municipal.html',
        departments_data=departments,
        employees_data=employees,
        designations_data=designations
    )

@bp.route('/designation')
@role_required('municipal','municipal_admin')
def hrm_designation():
    db = get_firestore_db()
    designations = []
    employees = []

    try:
        for doc in db.collection('designations').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            designations.append(item)
    except Exception:
        pass

    try:
        for doc in db.collection('employees').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            employees.append(item)
    except Exception:
        pass

    return render_template(
        'municipal/hrm/designation-municipal.html',
        designations_data=designations,
        employees_data=employees
    )

@bp.route('/office-shift')
@role_required('municipal','municipal_admin')
def hrm_office_shift():
    db = get_firestore_db()
    shifts = []

    try:
        # Get the logged-in user's municipality
        user_municipality = _resolve_municipality_from_user_context()
        
        if user_municipality:
            # Fetch shifts for the user's municipality
            query = db.collection('office_shifts').where('municipality', '==', user_municipality).limit(10)
            for doc in query.stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                shifts.append(item)
            
            if not shifts:
                print(f"[WARN] No shifts found for municipality: {user_municipality}")
        else:
            print(f"[WARN] Could not resolve user municipality")
    except Exception as e:
        print(f"Error fetching shifts: {e}")
        import traceback
        traceback.print_exc()

    # Convert all datetime objects to ISO format strings
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    shifts_json = json.dumps(shifts, default=json_serializer, separators=(',', ':'))
    print(f"[DEBUG] Shifts JSON length: {len(shifts_json)}")
    
    return render_template('municipal/hrm/office-shift-municipal.html', shifts_json=shifts_json)

@bp.route('/employees')
@role_required('municipal','municipal_admin')
def hrm_employees():
    db = get_firestore_db()
    employees = []
    departments = []
    designations = []

    try:
        # Get the logged-in user's municipality
        user_municipality = _resolve_municipality_from_user_context()
        
        if user_municipality:
            # Fetch employees for the user's municipality
            query = db.collection('employees').where('municipality', '==', user_municipality)
            for doc in query.stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                employees.append(item)
            
            if not employees:
                print(f"[WARN] No employees found for municipality: {user_municipality}")
        else:
            # Fallback: fetch all employees if municipality can't be resolved
            for doc in db.collection('employees').stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                employees.append(item)
    except Exception as e:
        print(f"Error fetching employees: {e}")

    try:
        for doc in db.collection('departments').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            departments.append(item)
    except Exception as e:
        print(f"Error fetching departments: {e}")

    try:
        for doc in db.collection('designations').stream():
            item = doc.to_dict() or {}
            item['id'] = doc.id
            designations.append(item)
    except Exception as e:
        print(f"Error fetching designations: {e}")

    return render_template('municipal/hrm/employees-municipal.html', 
                          employees_data=employees,
                          departments_data=departments,
                          designations_data=designations)

@bp.route('/attendance')
@role_required('municipal','municipal_admin')
def hrm_attendance():
    db = get_firestore_db()
    employees = []

    try:
        # Get the logged-in user's municipality
        user_municipality = _resolve_municipality_from_user_context()
        
        if user_municipality:
            # Fetch employees for the user's municipality
            query = db.collection('employees').where('municipality', '==', user_municipality)
            for doc in query.stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                employees.append(item)
        else:
            # Fallback: fetch all
            for doc in db.collection('employees').stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                employees.append(item)
    except Exception:
        pass

    return render_template(
        'municipal/hrm/attendance-municipal.html',
        employees_data=employees
    )

@bp.route('/holiday')
@role_required('municipal','municipal_admin')
def hrm_holiday():

    # Fetch holidays directly from Firestore
    db = get_firestore_db()
    holidays = []
    try:
        docs = db.collection('holidays').stream()
        for doc in docs:
            holiday = doc.to_dict() or {}
            holiday['id'] = doc.id

            date_value = holiday.get('date')
            if isinstance(date_value, str):
                holiday['date'] = date_value.split('T')[0]
            elif hasattr(date_value, 'strftime'):
                holiday['date'] = date_value.strftime('%Y-%m-%d')
            elif hasattr(date_value, 'isoformat'):
                holiday['date'] = date_value.isoformat().split('T')[0]
            else:
                holiday['date'] = ''

            holidays.append(holiday)
    except Exception:
        pass
    from datetime import datetime
    year = datetime.now().year
    return render_template(
        'municipal/hrm/holiday-municipal.html',
        holidays=holidays,
        year=year
    )

@bp.route('/api/context')
@role_required('municipal','municipal_admin')
def municipal_context():
    municipality = session.get('municipality') or session.get('user_municipality')

    if not municipality:
        try:
            user_id = session.get('user_id')
            if user_id:
                db = get_firestore_db()
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    municipality = user_data.get('municipality') or user_data.get('municipality_name')
                    if municipality:
                        session['municipality'] = municipality
                        session['user_municipality'] = municipality
        except Exception:
            municipality = None

    return jsonify({
        'municipality': municipality or 'Municipality',
        'user_email': session.get('user_email', '')
    })

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
    db = get_firestore_db()
    leave_records = []
    employees = []

    try:
        # Get the logged-in user's municipality
        user_municipality = _resolve_municipality_from_user_context()
        
        if user_municipality:
            # Fetch leave requests for the user's municipality
            query = db.collection('leave_requests').where('municipality', '==', user_municipality).limit(100)
            for doc in query.stream():
                item = doc.to_dict() or {}
                item['id'] = doc.id
                leave_records.append(item)
            
            if not leave_records:
                print(f"[WARN] No leave requests found for municipality: {user_municipality}")

            # Fetch employees for the user's municipality
            emp_query = db.collection('employees').where('municipality', '==', user_municipality)
            for doc in emp_query.stream():
                emp = doc.to_dict() or {}
                emp['id'] = doc.id
                employees.append({'id': doc.id, 'name': emp.get('full_name', emp.get('name', '')), 'employee_id': emp.get('employee_id', doc.id)})
        else:
            print(f"[WARN] Could not resolve user municipality")
    except Exception as e:
        print(f"Error fetching leave data: {e}")
        import traceback
        traceback.print_exc()

    # Convert all datetime objects to ISO format strings
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    leave_json = json.dumps(leave_records, default=json_serializer, separators=(',', ':'))
    employees_json = json.dumps(employees, default=json_serializer, separators=(',', ':'))
    print(f"[DEBUG] Leave records JSON length: {len(leave_json)}")
    
    return render_template('municipal/hrm/leave-municipal.html', leave_json=leave_json, employees_json=employees_json)


@bp.route('/leave-request/create', methods=['POST'])
@role_required('municipal','municipal_admin')
def hrm_leave_create():
    db = get_firestore_db()
    try:
        data = request.get_json(force=True) or {}
        user_municipality = _resolve_municipality_from_user_context()

        if not user_municipality:
            return jsonify({'success': False, 'error': 'Could not resolve municipality'}), 400

        required = ['employee_name', 'employee_id', 'leave_type', 'from_date', 'to_date', 'days']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

        record = {
            'employee_name': data['employee_name'],
            'employee_id': data['employee_id'],
            'leave_type': data['leave_type'],
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            'days': float(data['days']),
            'reason': data.get('reason', ''),
            'status': 'Pending',
            'municipality': user_municipality,
            'created_at': datetime.utcnow().isoformat(),
        }

        doc_ref = db.collection('leave_requests').add(record)
        record['id'] = doc_ref[1].id
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        print(f"Error creating leave request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/leave-request/update', methods=['POST'])
@role_required('municipal','municipal_admin')
def hrm_leave_update():
    db = get_firestore_db()
    try:
        data = request.get_json(force=True) or {}
        record_id = data.get('id')
        status = data.get('status')

        if not record_id:
            return jsonify({'success': False, 'error': 'Missing record id'}), 400
        if status not in ('Approved', 'Denied'):
            return jsonify({'success': False, 'error': 'Invalid status value'}), 400

        update_data = {
            'status': status,
            'reviewed_at': datetime.utcnow().isoformat(),
        }
        if data.get('remarks'):
            update_data['remarks'] = data['remarks']

        db.collection('leave_requests').document(record_id).update(update_data)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating leave request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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
    # If missing any info, try to get from user document
    user_id = session.get('user_id')
    if user_id and (not municipality_name or not province_name or not region_name):
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if not municipality_name:
                municipality_name = user_data.get('municipality') or user_data.get('municipality_name')
            if not province_name:
                province_name = user_data.get('province') or user_data.get('province_name')
            if not region_name:
                region_name = user_data.get('region') or user_data.get('region_name')
    # Fetch finance data for this municipality only
    doc_id = None
    try:
        if municipality_name and province_name:
            doc_id = f"{municipality_name.upper().replace(' ', '_')}_{province_name.upper().replace(' ', '_')}"
            print(f"[DEBUG] Fetching finance for doc_id: {doc_id}")
            doc = db.collection('finance').document(doc_id).get()
            if doc.exists:
                finance_data = doc.to_dict()
                print(f"[DEBUG] Finance data found: {finance_data}")
            else:
                print(f"[DEBUG] Finance document not found for {doc_id}, initializing...")
                # Initialize with default structure if document doesn't exist
                finance_data = {
                    'general_fund': 0,
                    'treasury': {
                        'special_fund': 0,
                        'total_deposit': 0,
                        'total_expenses': 0
                    },
                    'accounting': {
                        'general_fund': 0
                    }
                }
                db.collection('finance').document(doc_id).set(finance_data, merge=True)
        elif municipality_name:
            # fallback: try old style (just municipality name)
            print(f"[DEBUG] Trying fallback fetch for municipality: {municipality_name}")
            doc = db.collection('finance').document(municipality_name).get()
            if doc.exists:
                finance_data = doc.to_dict()
                print(f"[DEBUG] Finance data found (fallback): {finance_data}")
            else:
                print(f"[DEBUG] Finance document not found for {municipality_name}, initializing...")
                # Initialize with default structure
                finance_data = {
                    'general_fund': 0,
                    'treasury': {
                        'special_fund': 0,
                        'total_deposit': 0,
                        'total_expenses': 0
                    },
                    'accounting': {
                        'general_fund': 0
                    }
                }
                db.collection('finance').document(municipality_name).set(finance_data, merge=True)
        else:
            print(f"[DEBUG] No municipality found, skipping finance fetch")
            # fallback: fetch all (should not happen)
            docs = db.collection('finance').stream()
            for doc in docs:
                finance_data.update(doc.to_dict())
    except Exception as e:
        print(f"[ERROR] Error fetching/initializing finance data: {e}")
        finance_data = {
            'general_fund': 0,
            'treasury': {
                'special_fund': 0,
                'total_deposit': 0,
                'total_expenses': 0
            },
            'accounting': {
                'general_fund': 0
            }
        }
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

    print(f"[DEBUG] Rendering dashboard with municipality_name={municipality_name}, province_name={province_name}")
    print(f"[DEBUG] Finance data being passed to template: {finance_data}")
    
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
    municipality_name, region_name, province_name = _get_municipality_from_firestore()
    return render_template(
        'municipal/accounting/payment-deposits-municipal.html',
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name
    )

# --- Logs ---
def _get_municipality_from_firestore():
    """Resolve municipality/province/region for the current logged-in admin from Firestore."""
    from flask import session
    db = get_firestore_db()
    municipality_name = None
    region_name = None
    province_name = None
    user_id = session.get('user_id')
    if user_id:
        try:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                ud = user_doc.to_dict() or {}
                municipality_name = ud.get('municipality') or ud.get('municipality_name')
                region_name = ud.get('region') or ud.get('regionName')
                province_name = ud.get('province')
        except Exception as e:
            print(f"[WARN] Could not fetch admin doc for log route: {e}")
    if not municipality_name:
        municipality_name = session.get('municipality') or session.get('user_municipality')
    if not region_name:
        region_name = session.get('region') or session.get('user_region')
    if not province_name:
        province_name = session.get('province') or session.get('user_province')
    return municipality_name, region_name, province_name

@bp.route('/logs/audit-logs-municipal')
@role_required('municipal','municipal_admin')
def logs_audit_logs_municipal():
    municipality_name, region_name, province_name = _get_municipality_from_firestore()
    return render_template('municipal/logs/audit-logs-municipal.html',
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name
    )

@bp.route('/logs/system-logs-municipal')
@role_required('municipal','municipal_admin')
def logs_system_logs_municipal():
    municipality_name, region_name, province_name = _get_municipality_from_firestore()
    return render_template('municipal/logs/system-logs-municipal.html',
        municipality_name=municipality_name,
        region_name=region_name,
        province_name=province_name
    )

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
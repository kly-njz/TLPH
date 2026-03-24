# --- API: Mark Project as Completed by Municipal ---
@bp.route('/api/projects/<project_id>/status', methods=['POST'])
@role_required('municipal','municipal_admin')
def api_municipal_project_mark_completed(project_id):
    """Mark a project as COMPLETED by municipal admin."""
    from firebase_admin import firestore
    db = get_firestore_db()
    data = request.get_json(silent=True) or {}
    new_status = str(data.get('status', '')).strip().upper()
    if new_status != 'COMPLETED':
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    try:
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()
        if not project_doc.exists:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = project_doc.to_dict() or {}
        # Only allow marking as completed if status is 'active'
        if str(project.get('status', '')).lower() != 'active':
            return jsonify({'success': False, 'error': 'Project is not active'}), 400

        update_payload = {
            'status': 'completed',
            'status_code': 'DONE_BY_MUNICIPAL',
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': session.get('user_email', 'system'),
        }
        project_ref.update(update_payload)
        return jsonify({'success': True, 'id': project_id, 'status': 'completed'}), 200
    except Exception as e:
        print(f"[ERROR] Failed to update project status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
# Unified expense categories API for municipal admin

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from firebase_auth_middleware import role_required
from firebase_config import get_firestore_db
from config import Config
from .municipal_api_logs import _resolve_municipality_from_user_context, _resolve_region_from_user_context, api_get_municipal_payment_deposits, api_get_expenses
import json
from datetime import datetime
from collections import Counter

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

@bp.route('/inventory/api/<inventory_id>/status', methods=['POST'])
@role_required('municipal','municipal_admin')
def update_inventory_status(inventory_id):
    """Update inventory registration status (approve/reject/forward)"""
    try:
        db = get_firestore_db()
        data = request.get_json()
        new_status = data.get('status', '').lower()
        
        # Validate status
        valid_statuses = ['approved', 'rejected', 'to-review']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Get the inventory document
        inv_ref = db.collection('inventory_registrations').document(inventory_id)
        inv_doc = inv_ref.get()
        
        if not inv_doc.exists:
            return jsonify({'error': 'Inventory registration not found'}), 404
        
        # Get current user info for audit trail
        user_municipality = _resolve_municipality_from_user_context()
        
        # Build update payload
        update_payload = {
            'status': new_status,
            'updatedAt': datetime.utcnow(),
            'updatedByMunicipality': user_municipality
        }
        
        if new_status == 'approved':
            update_payload['approvedByLevel'] = 'Municipal'
            update_payload['approvedAt'] = datetime.utcnow()
            update_payload['rejectedByLevel'] = ''
            update_payload['rejectedByEmail'] = ''
        
        elif new_status == 'rejected':
            update_payload['rejectedByLevel'] = 'Municipal'
            update_payload['rejectedAt'] = datetime.utcnow()
            update_payload['approvedByLevel'] = ''
            update_payload['approvedByEmail'] = ''
        
        elif new_status == 'to-review':
            update_payload['forwardedAt'] = datetime.utcnow()
            update_payload['forwardedByLevel'] = 'Municipal'
            update_payload['forwardedToLevel'] = 'Regional'
            update_payload['regionalStatus'] = 'pending'
        
        # Update the document
        inv_ref.update(update_payload)
        
        return jsonify({
            'success': True,
            'message': f'Inventory registration {new_status.replace("-", " ")} successfully',
            'status': new_status
        }), 200
        
    except Exception as e:
        print(f'Error updating inventory status: {str(e)}')
        return jsonify({'error': f'Failed to update inventory status: {str(e)}'}), 500

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

# Unified quotations view using quotations collection
@bp.route('/operations/quotations-municipal')
@role_required('municipal','municipal_admin')
def quotations_municipal():
    from quotation_storage import get_quotations
    import json
    from collections import Counter
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    from quotation_storage import get_all_quotations
    all_quotations = get_all_quotations()
    muni_upper = user_municipality.upper() if user_municipality else ''
    quotations = [
        q for q in all_quotations
        if str(q.get('municipality', '')).strip().upper() == muni_upper
    ]
    def to_float(value):
        try:
            return float(value)
        except Exception:
            return 0.0
    for q in quotations:
        q['amount_value'] = to_float(q.get('amount'))
        q['amount'] = f"{q['amount_value']:,.2f}"
        q['status'] = str(q.get('status') or 'Pending').capitalize()

    total_quotes = len(quotations)
    approved_quotes = len([q for q in quotations if str(q.get('status')).upper() == 'APPROVED'])
    pending_quotes = len([q for q in quotations if str(q.get('status')).upper() == 'PENDING'])
    rejected_quotes = len([q for q in quotations if str(q.get('status')).upper() == 'REJECTED'])
    total_value_number = sum([to_float(q.get('amount_value')) for q in quotations])
    total_value = f"{total_value_number:,.2f}"
    barangay_options = sorted(list({(q.get('barangay') or '').strip() for q in quotations if (q.get('barangay') or '').strip()}))
    # If no barangays found in quotations, fallback to all barangays for the user's municipality
    if not barangay_options:
        try:
            from models.ph_locations import philippineLocations
            user_muni = user_municipality.strip()
            user_province = None
            # Try to find the province for the user's municipality
            for province, munis in philippineLocations.items():
                if user_muni in munis:
                    user_province = province
                    break
            if user_province:
                barangay_options = sorted(munis)
        except Exception:
            pass
    monthly_amounts = Counter()
    for q in quotations:
        date_raw = str(q.get('date') or '').strip()
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_raw)
            monthly_amounts[dt.strftime('%b')] += to_float(q.get('amount_value'))
        except Exception:
            continue
    ordered_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    trend_labels = [m for m in ordered_months if monthly_amounts.get(m)]
    trend_values = [round(monthly_amounts[m], 2) for m in trend_labels]
    if not trend_labels:
        trend_labels = ['No Data']
        trend_values = [0]
    return render_template(
        'municipal/operations/quotations-municipal.html',
        quotations=quotations,
        total_quotes=total_quotes,
        approved_quotes=approved_quotes,
        pending_quotes=pending_quotes,
        rejected_quotes=rejected_quotes,
        total_value=total_value,
        barangay_options=barangay_options,
        user_municipality=user_municipality,
        trend_labels_json=json.dumps(trend_labels),
        trend_values_json=json.dumps(trend_values)
    )



# Unified quotation create endpoint
@bp.route('/operations/quotations-municipal/api/create', methods=['POST'])
@role_required('municipal','municipal_admin')
def quotations_municipal_create():
    from quotation_storage import add_quotation
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()
    data = request.get_json(silent=True) or {}
    number = str(data.get('number') or '').strip()
    client = str(data.get('client') or '').strip()
    barangay = str(data.get('barangay') or '').strip()
    date = str(data.get('date') or '').strip()
    try:
        amount = float(data.get('amount'))
    except Exception:
        amount = 0.0
    status = str(data.get('status') or 'PENDING').strip().upper()
    if status not in {'PENDING', 'APPROVED', 'REJECTED'}:
        status = 'PENDING'
    if not number or not client or not barangay or not date:
        return jsonify({'success': False, 'error': 'Missing required quotation fields'}), 400
    payload = {
        'number': number,
        'client': client,
        'barangay': barangay,
        'date': date,
        'amount': amount,
        'status': status,
        'municipality': user_municipality,
        'region': user_region,
        'scope': 'municipal'
    }
    try:
        quotation = add_quotation(payload)
        return jsonify({'success': True, 'quotation': {
            'id': quotation['id'],
            'number': number,
            'client': client,
            'barangay': barangay,
            'date': date,
            'amount': f"{amount:,.2f}",
            'amount_value': amount,
            'status': status
        }})
    except Exception as e:
        print(f"[ERROR] quotations_municipal_create failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to create quotation'}), 500



# Unified quotation status update endpoint
@bp.route('/operations/quotations-municipal/api/<quotation_id>/status', methods=['POST'])
@role_required('municipal','municipal_admin')
def quotations_municipal_update_status(quotation_id):
    from quotation_storage import update_quotation
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    data = request.get_json(silent=True) or {}
    status = str(data.get('status') or '').strip().upper()
    if status not in {'PENDING', 'APPROVED', 'REJECTED'}:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    try:
        updated = update_quotation(quotation_id, {'status': status, 'municipality': user_municipality})
        if not updated:
            return jsonify({'success': False, 'error': 'Quotation not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] quotations_municipal_update_status failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to update quotation status'}), 500



# Unified quotation delete endpoint
@bp.route('/operations/quotations-municipal/api/<quotation_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def quotations_municipal_delete(quotation_id):
    from quotation_storage import delete_quotation
    try:
        delete_quotation(quotation_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] quotations_municipal_delete failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete quotation'}), 500

@bp.route('/operations/projects-municipal')
@role_required('municipal','municipal_admin')
def projects_municipal():
    """Municipal admin project management view"""
    try:
        import projects_storage
        user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
        user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()
        
        # Get projects for this municipal admin
        projects = projects_storage.get_projects_municipal(user_municipality, user_region, session.get('user_email', ''))

        # Map backend status to display status for UI
        def map_status(status):
            s = (status or '').lower()
            if s == 'active':
                return 'In Progress'
            if s == 'completed':
                return 'Completed'
            if s.startswith('pending'):
                return 'Pending'
            return s.title() if s else 'Pending'

        for p in projects:
            p['status'] = map_status(p.get('status'))

        # Calculate stats
        total_projects = len(projects)
        in_progress = len([p for p in projects if p.get('status') == 'In Progress'])
        pending = len([p for p in projects if p.get('status') == 'Pending'])
        completed = len([p for p in projects if p.get('status') == 'Completed'])

        # Build filter options and chart data from real projects
        barangay_options = sorted(list({
            (p.get('barangay') or '').strip()
            for p in projects
            if (p.get('barangay') or '').strip()
        }))

        monthly_counts = Counter()
        for p in projects:
            date_raw = str(p.get('start_date') or '').strip()
            if not date_raw:
                continue
            try:
                dt = datetime.fromisoformat(date_raw)
            except Exception:
                try:
                    dt = datetime.fromisoformat(date_raw[:10])
                except Exception:
                    continue
            monthly_counts[dt.strftime('%b')] += 1

        ordered_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        trend_labels = [m for m in ordered_months if monthly_counts.get(m)]
        trend_values = [monthly_counts[m] for m in trend_labels]

        area_counts = Counter([
            (p.get('barangay') or p.get('municipality') or 'N/A')
            for p in projects
        ])
        top_areas = area_counts.most_common(6)
        area_labels = [x[0] for x in top_areas] if top_areas else []
        area_values = [x[1] for x in top_areas] if top_areas else []

        return render_template(
            'municipal/operations/projects-municipal.html',
            projects=projects,
            total_projects=total_projects,
            in_progress=in_progress,
            completed=completed,
            pending=pending,
            barangay_options=barangay_options,
            user_municipality=user_municipality,
            user_region=user_region,
            user_email=session.get('user_email', 'Unknown'),
            trend_labels_json=json.dumps(trend_labels),
            trend_values_json=json.dumps(trend_values),
            area_labels_json=json.dumps(area_labels),
            area_values_json=json.dumps(area_values)
        )
    except Exception as e:
        print(f"[ERROR] Loading municipal projects: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            'municipal/operations/projects-municipal.html',
            projects=[],
            total_projects=0,
            in_progress=0,
            completed=0,
            pending=0,
            barangay_options=[],
            user_municipality=session.get('user_municipality', 'Unknown'),
            user_region=session.get('user_region', 'Unknown'),
            user_email=session.get('user_email', 'Unknown'),
            trend_labels_json=json.dumps([]),
            trend_values_json=json.dumps([]),
            area_labels_json=json.dumps([]),
            area_values_json=json.dumps([])
        )


@bp.route('/operations/projects-municipal/api/create', methods=['POST'])
@role_required('municipal','municipal_admin')
def projects_municipal_create():
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    barangay = str(data.get('barangay') or '').strip()
    start_date = str(data.get('start_date') or '').strip()
    status = str(data.get('status') or 'PENDING').strip().upper()
    if status not in {'PENDING', 'IN PROGRESS', 'COMPLETED'}:
        status = 'PENDING'

    if not name or not barangay or not start_date:
        return jsonify({'success': False, 'error': 'Missing required project fields'}), 400

    try:
        # Save directly to the main 'projects' collection for unified workflow
        payload = {
            'name': name,
            'barangay': barangay,
            'municipality': user_municipality.upper(),
            'region': user_region.upper(),
            'start_date': start_date,
            'status': 'active' if status == 'IN PROGRESS' else status.lower(),
            'created_by': session.get('user_email', ''),
            'created_by_role': 'municipal_admin',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'approval_chain': ['municipal'],
        }
        ref = db.collection('projects').document()
        ref.set(payload)
        return jsonify({'success': True, 'project': {
            'id': ref.id,
            'name': name,
            'barangay': barangay,
            'municipality': user_municipality,
            'start_date': start_date,
            'status': payload['status']
        }})
    except Exception as e:
        print(f"[ERROR] projects_municipal_create failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to create project'}), 500


@bp.route('/operations/projects-municipal/api/<project_id>/update', methods=['POST'])
@role_required('municipal','municipal_admin')
def projects_municipal_update(project_id):
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    barangay = str(data.get('barangay') or '').strip()
    start_date = str(data.get('start_date') or '').strip()
    status = str(data.get('status') or '').strip().upper()
    if status not in {'PENDING', 'IN PROGRESS', 'COMPLETED'}:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    if not name or not barangay or not start_date:
        return jsonify({'success': False, 'error': 'Missing required project fields'}), 400

    try:
        ref = db.collection('municipal_projects').document(project_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        existing = doc.to_dict() or {}
        if normalize_scope(existing.get('municipality_key') or existing.get('municipality')) != normalize_scope(user_municipality):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403

        ref.set({
            'name': name,
            'barangay': barangay,
            'start_date': start_date,
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] projects_municipal_update failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to update project'}), 500


@bp.route('/operations/projects-municipal/api/<project_id>/archive', methods=['POST'])
@role_required('municipal','municipal_admin')
def projects_municipal_archive(project_id):
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    try:
        ref = db.collection('municipal_projects').document(project_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        existing = doc.to_dict() or {}
        if normalize_scope(existing.get('municipality_key') or existing.get('municipality')) != normalize_scope(user_municipality):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403

        ref.set({'status': 'ARCHIVED', 'updated_at': firestore.SERVER_TIMESTAMP}, merge=True)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] projects_municipal_archive failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to archive project'}), 500

@bp.route('/operations/tasks-municipal')
@role_required('municipal','municipal_admin')
def tasks_municipal():
    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    def get_region_variants(value):
        aliases = {
            'MIMAROPA': 'REGION-IV-B',
            'REGION IV-B': 'REGION-IV-B',
            'REGION-IV-B': 'REGION-IV-B',
            'CALABARZON': 'REGION-IV-A',
            'REGION IV-A': 'REGION-IV-A',
            'REGION-IV-A': 'REGION-IV-A',
        }
        normalized = normalize_scope(value)
        canonical = aliases.get(normalized, normalized)
        variants = {canonical, normalized}
        for k, v in aliases.items():
            if v == canonical:
                variants.add(k)
        return {x for x in variants if x}

    def get_municipality_variants(value):
        normalized = normalize_scope(value)
        variants = {normalized} if normalized else set()
        if ',' in normalized:
            variants.add(normalize_scope(normalized.split(',', 1)[0]))
        if ' - ' in normalized:
            variants.add(normalize_scope(normalized.split(' - ', 1)[0]))
        if '(' in normalized:
            variants.add(normalize_scope(normalized.split('(', 1)[0]))
        if normalized.startswith('CITY OF '):
            variants.add(normalize_scope(normalized.replace('CITY OF ', '', 1)))
        if normalized.startswith('MUNICIPALITY OF '):
            variants.add(normalize_scope(normalized.replace('MUNICIPALITY OF ', '', 1)))
        if normalized.endswith(' MUNICIPALITY'):
            variants.add(normalize_scope(normalized.replace(' MUNICIPALITY', '')))
        return {x for x in variants if x}

    def get_municipality_query_values(value):
        raw = str(value or '').strip()
        if not raw:
            return []
        candidates = {raw}
        if ',' in raw:
            candidates.add(raw.split(',', 1)[0].strip())
        if ' - ' in raw:
            candidates.add(raw.split(' - ', 1)[0].strip())
        if '(' in raw:
            candidates.add(raw.split('(', 1)[0].strip())
        raw_upper = raw.upper()
        if raw_upper.startswith('CITY OF '):
            candidates.add(raw[8:].strip())
        if raw_upper.startswith('MUNICIPALITY OF '):
            candidates.add(raw[16:].strip())
        if raw_upper.endswith(' MUNICIPALITY'):
            candidates.add(raw[:-13].strip())
        return [c for c in candidates if c]

    def municipality_matches(item_value, accepted_variants):
        item_key = normalize_scope(item_value)
        if not accepted_variants:
            return False
        if item_key in accepted_variants:
            return True
        for v in accepted_variants:
            if item_key.startswith(v + ',') or item_key.startswith(v + ' - ') or item_key.startswith(v + ' ('):
                return True
        return False

    municipality_key = normalize_scope(user_municipality)
    region_key = normalize_scope(user_region)
    municipality_variants = get_municipality_variants(user_municipality)
    municipality_query_values = get_municipality_query_values(user_municipality)
    region_variants = get_region_variants(user_region)

    print(f"[DEBUG] tasks_municipal scope -> municipality='{user_municipality}', region='{user_region}'")
    print(f"[DEBUG] tasks_municipal query values -> municipality_query_values={municipality_query_values}, region_variants={sorted(list(region_variants)) if region_variants else []}")

    tasks = []
    try:
        seen_ids = set()

        # Primary fetch: use municipality field directly as requested.
        for municipality_value in municipality_query_values:
            query = db.collection('municipal_tasks').where('municipality', '==', municipality_value).stream()
            for doc in query:
                if doc.id in seen_ids:
                    continue
                item = doc.to_dict() or {}
                item_region_key = normalize_scope(item.get('region_key') or item.get('region'))
                if region_variants and item_region_key not in region_variants:
                    continue
                item['id'] = doc.id
                item['title'] = item.get('title') or 'N/A'
                item['assigned_to'] = item.get('assigned_to') or 'N/A'
                item['barangay'] = item.get('barangay') or 'N/A'
                item['status'] = str(item.get('status') or 'PENDING').upper()
                item['due_date'] = item.get('due_date') or 'N/A'
                created_at = item.get('created_at')
                if isinstance(created_at, datetime):
                    item['_created_at'] = created_at
                elif hasattr(created_at, 'to_datetime'):
                    try:
                        item['_created_at'] = created_at.to_datetime()
                    except Exception:
                        item['_created_at'] = datetime.min
                else:
                    item['_created_at'] = datetime.min
                tasks.append(item)
                seen_ids.add(doc.id)

        # Fallback: if no results via municipality field, try broader matching.
        if not tasks:
            query = db.collection('municipal_tasks').stream()
            for doc in query:
                item = doc.to_dict() or {}
                item_muni_key = item.get('municipality_key') or item.get('municipality')
                if not municipality_matches(item_muni_key, municipality_variants):
                    continue
                item_region_key = normalize_scope(item.get('region_key') or item.get('region'))
                if region_variants and item_region_key not in region_variants:
                    continue
                item['id'] = doc.id
                item['title'] = item.get('title') or 'N/A'
                item['assigned_to'] = item.get('assigned_to') or 'N/A'
                item['barangay'] = item.get('barangay') or 'N/A'
                item['status'] = str(item.get('status') or 'PENDING').upper()
                item['due_date'] = item.get('due_date') or 'N/A'
                created_at = item.get('created_at')
                if isinstance(created_at, datetime):
                    item['_created_at'] = created_at
                elif hasattr(created_at, 'to_datetime'):
                    try:
                        item['_created_at'] = created_at.to_datetime()
                    except Exception:
                        item['_created_at'] = datetime.min
                else:
                    item['_created_at'] = datetime.min
                tasks.append(item)

        # Safety fallback: municipality-only fetch without region filtering.
        if not tasks and municipality_query_values:
            seen_ids = set()
            for municipality_value in municipality_query_values:
                query = db.collection('municipal_tasks').where('municipality', '==', municipality_value).stream()
                for doc in query:
                    if doc.id in seen_ids:
                        continue
                    item = doc.to_dict() or {}
                    item['id'] = doc.id
                    item['title'] = item.get('title') or 'N/A'
                    item['assigned_to'] = item.get('assigned_to') or 'N/A'
                    item['barangay'] = item.get('barangay') or 'N/A'
                    item['status'] = str(item.get('status') or 'PENDING').upper()
                    item['due_date'] = item.get('due_date') or 'N/A'
                    created_at = item.get('created_at')
                    if isinstance(created_at, datetime):
                        item['_created_at'] = created_at
                    elif hasattr(created_at, 'to_datetime'):
                        try:
                            item['_created_at'] = created_at.to_datetime()
                        except Exception:
                            item['_created_at'] = datetime.min
                    else:
                        item['_created_at'] = datetime.min
                    tasks.append(item)
                    seen_ids.add(doc.id)
    except Exception as e:
        print(f"[WARN] tasks_municipal scoped query failed, trying fallback: {e}")
        try:
            for doc in db.collection('municipal_tasks').stream():
                item = doc.to_dict() or {}
                if not municipality_matches(item.get('municipality_key') or item.get('municipality'), municipality_variants):
                    continue
                item_region_key = normalize_scope(item.get('region_key') or item.get('region'))
                if region_variants and item_region_key not in region_variants:
                    continue
                item['id'] = doc.id
                item['title'] = item.get('title') or 'N/A'
                item['assigned_to'] = item.get('assigned_to') or 'N/A'
                item['barangay'] = item.get('barangay') or 'N/A'
                item['status'] = str(item.get('status') or 'PENDING').upper()
                item['due_date'] = item.get('due_date') or 'N/A'
                created_at = item.get('created_at')
                if isinstance(created_at, datetime):
                    item['_created_at'] = created_at
                elif hasattr(created_at, 'to_datetime'):
                    try:
                        item['_created_at'] = created_at.to_datetime()
                    except Exception:
                        item['_created_at'] = datetime.min
                else:
                    item['_created_at'] = datetime.min
                tasks.append(item)
        except Exception as fallback_error:
            print(f"[ERROR] tasks_municipal fallback query failed: {fallback_error}")

    print(f"[DEBUG] tasks_municipal fetched tasks count={len(tasks)}")

    tasks.sort(key=lambda t: t.get('_created_at') or datetime.min, reverse=True)

    total_tasks = len(tasks)
    pending_tasks = len([t for t in tasks if t.get('status') == 'PENDING'])
    in_progress_tasks = len([t for t in tasks if t.get('status') == 'IN PROGRESS'])
    completed_tasks = len([t for t in tasks if t.get('status') == 'COMPLETED'])

    barangay_options = sorted(list({(t.get('barangay') or '').strip() for t in tasks if (t.get('barangay') or '').strip()}))

    unit_counts = Counter()
    for t in tasks:
        unit_counts[(t.get('assigned_to') or 'N/A').strip()] += 1
    top_units = unit_counts.most_common(6)
    unit_labels = [u[0] for u in top_units] if top_units else ['No Data']
    unit_values = [u[1] for u in top_units] if top_units else [0]

    return render_template(
        'municipal/operations/task-municipal.html',
        tasks=tasks,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks,
        barangay_options=barangay_options,
        unit_labels_json=json.dumps(unit_labels),
        unit_values_json=json.dumps(unit_values)
    )


@bp.route('/operations/tasks-municipal/api/create', methods=['POST'])
@role_required('municipal','municipal_admin')
def tasks_municipal_create():
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    def canonical_region(value):
        aliases = {
            'MIMAROPA': 'REGION-IV-B',
            'REGION IV-B': 'REGION-IV-B',
            'REGION-IV-B': 'REGION-IV-B',
            'CALABARZON': 'REGION-IV-A',
            'REGION IV-A': 'REGION-IV-A',
            'REGION-IV-A': 'REGION-IV-A',
        }
        normalized = normalize_scope(value)
        return aliases.get(normalized, normalized)

    def get_municipality_variants(value):
        normalized = normalize_scope(value)
        variants = {normalized} if normalized else set()
        if ',' in normalized:
            variants.add(normalize_scope(normalized.split(',', 1)[0]))
        if ' - ' in normalized:
            variants.add(normalize_scope(normalized.split(' - ', 1)[0]))
        if '(' in normalized:
            variants.add(normalize_scope(normalized.split('(', 1)[0]))
        if normalized.startswith('CITY OF '):
            variants.add(normalize_scope(normalized.replace('CITY OF ', '', 1)))
        if normalized.startswith('MUNICIPALITY OF '):
            variants.add(normalize_scope(normalized.replace('MUNICIPALITY OF ', '', 1)))
        if normalized.endswith(' MUNICIPALITY'):
            variants.add(normalize_scope(normalized.replace(' MUNICIPALITY', '')))
        return {x for x in variants if x}

    municipality_variants = get_municipality_variants(user_municipality)
    municipality_key = min(municipality_variants, key=len) if municipality_variants else normalize_scope(user_municipality)
    region_key = canonical_region(user_region)

    data = request.get_json(silent=True) or {}
    title = str(data.get('title') or '').strip()
    assigned_to = str(data.get('assigned_to') or '').strip()
    barangay = str(data.get('barangay') or '').strip()
    due_date = str(data.get('due_date') or '').strip()
    status = str(data.get('status') or 'PENDING').strip().upper()

    if status not in {'PENDING', 'IN PROGRESS', 'COMPLETED'}:
        status = 'PENDING'

    if not title or not assigned_to or not barangay or not due_date:
        return jsonify({'success': False, 'error': 'Missing required task fields'}), 400

    if not user_region:
        try:
            # Reuse existing scoped tasks to infer missing region for this municipality.
            for d in db.collection('municipal_tasks').stream():
                existing = d.to_dict() or {}
                existing_muni = normalize_scope(existing.get('municipality_key') or existing.get('municipality'))
                if existing_muni != municipality_key and not existing_muni.startswith(municipality_key + ','):
                    continue
                inferred = existing.get('region_key') or existing.get('region')
                if inferred:
                    user_region = str(inferred).strip()
                    break
        except Exception:
            pass
    if not user_region:
        user_region = 'MIMAROPA'
    region_key = canonical_region(user_region)

    try:
        payload = {
            'title': title,
            'assigned_to': assigned_to,
            'barangay': barangay,
            'status': status,
            'due_date': due_date,
            'municipality': user_municipality,
            'region': user_region,
            'municipality_key': municipality_key,
            'region_key': region_key,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        ref = db.collection('municipal_tasks').document()
        ref.set(payload)
        return jsonify({'success': True, 'task': {
            'id': ref.id,
            'title': title,
            'assigned_to': assigned_to,
            'barangay': barangay,
            'status': status,
            'due_date': due_date
        }})
    except Exception as e:
        print(f"[ERROR] tasks_municipal_create failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to create task'}), 500


@bp.route('/operations/tasks-municipal/api/<task_id>/status', methods=['POST'])
@role_required('municipal','municipal_admin')
def tasks_municipal_update_status(task_id):
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    def get_region_variants(value):
        aliases = {
            'MIMAROPA': 'REGION-IV-B',
            'REGION IV-B': 'REGION-IV-B',
            'REGION-IV-B': 'REGION-IV-B',
            'CALABARZON': 'REGION-IV-A',
            'REGION IV-A': 'REGION-IV-A',
            'REGION-IV-A': 'REGION-IV-A',
        }
        normalized = normalize_scope(value)
        canonical = aliases.get(normalized, normalized)
        variants = {canonical, normalized}
        for k, v in aliases.items():
            if v == canonical:
                variants.add(k)
        return {x for x in variants if x}

    def get_municipality_variants(value):
        normalized = normalize_scope(value)
        variants = {normalized} if normalized else set()
        if ',' in normalized:
            variants.add(normalize_scope(normalized.split(',', 1)[0]))
        if ' - ' in normalized:
            variants.add(normalize_scope(normalized.split(' - ', 1)[0]))
        if '(' in normalized:
            variants.add(normalize_scope(normalized.split('(', 1)[0]))
        if normalized.startswith('CITY OF '):
            variants.add(normalize_scope(normalized.replace('CITY OF ', '', 1)))
        if normalized.startswith('MUNICIPALITY OF '):
            variants.add(normalize_scope(normalized.replace('MUNICIPALITY OF ', '', 1)))
        if normalized.endswith(' MUNICIPALITY'):
            variants.add(normalize_scope(normalized.replace(' MUNICIPALITY', '')))
        return {x for x in variants if x}

    def municipality_matches(item_value, accepted_variants):
        item_key = normalize_scope(item_value)
        if not accepted_variants:
            return False
        if item_key in accepted_variants:
            return True
        for v in accepted_variants:
            if item_key.startswith(v + ',') or item_key.startswith(v + ' - ') or item_key.startswith(v + ' ('):
                return True
        return False

    municipality_variants = get_municipality_variants(user_municipality)
    region_variants = get_region_variants(user_region)

    data = request.get_json(silent=True) or {}
    status = str(data.get('status') or '').strip().upper()
    if status not in {'PENDING', 'IN PROGRESS', 'COMPLETED'}:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    try:
        ref = db.collection('municipal_tasks').document(task_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        existing = doc.to_dict() or {}
        if not municipality_matches(existing.get('municipality_key') or existing.get('municipality'), municipality_variants):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403
        existing_region = normalize_scope(existing.get('region_key') or existing.get('region'))
        if region_variants and existing_region not in region_variants:
            return jsonify({'success': False, 'error': 'Access denied for region'}), 403

        ref.set({'status': status, 'updated_at': firestore.SERVER_TIMESTAMP}, merge=True)
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        print(f"[ERROR] tasks_municipal_update_status failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to update task status'}), 500


@bp.route('/operations/tasks-municipal/api/<task_id>', methods=['DELETE'])
@role_required('municipal','municipal_admin')
def tasks_municipal_delete(task_id):
    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or session.get('municipality') or session.get('user_municipality') or '').strip()
    user_region = (_resolve_region_from_user_context() or session.get('region') or session.get('user_region') or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    def get_region_variants(value):
        aliases = {
            'MIMAROPA': 'REGION-IV-B',
            'REGION IV-B': 'REGION-IV-B',
            'REGION-IV-B': 'REGION-IV-B',
            'CALABARZON': 'REGION-IV-A',
            'REGION IV-A': 'REGION-IV-A',
            'REGION-IV-A': 'REGION-IV-A',
        }
        normalized = normalize_scope(value)
        canonical = aliases.get(normalized, normalized)
        variants = {canonical, normalized}
        for k, v in aliases.items():
            if v == canonical:
                variants.add(k)
        return {x for x in variants if x}

    def get_municipality_variants(value):
        normalized = normalize_scope(value)
        variants = {normalized} if normalized else set()
        if ',' in normalized:
            variants.add(normalize_scope(normalized.split(',', 1)[0]))
        if ' - ' in normalized:
            variants.add(normalize_scope(normalized.split(' - ', 1)[0]))
        if '(' in normalized:
            variants.add(normalize_scope(normalized.split('(', 1)[0]))
        if normalized.startswith('CITY OF '):
            variants.add(normalize_scope(normalized.replace('CITY OF ', '', 1)))
        if normalized.startswith('MUNICIPALITY OF '):
            variants.add(normalize_scope(normalized.replace('MUNICIPALITY OF ', '', 1)))
        if normalized.endswith(' MUNICIPALITY'):
            variants.add(normalize_scope(normalized.replace(' MUNICIPALITY', '')))
        return {x for x in variants if x}

    def municipality_matches(item_value, accepted_variants):
        item_key = normalize_scope(item_value)
        if not accepted_variants:
            return False
        if item_key in accepted_variants:
            return True
        for v in accepted_variants:
            if item_key.startswith(v + ',') or item_key.startswith(v + ' - ') or item_key.startswith(v + ' ('):
                return True
        return False

    municipality_variants = get_municipality_variants(user_municipality)
    region_variants = get_region_variants(user_region)

    try:
        ref = db.collection('municipal_tasks').document(task_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        existing = doc.to_dict() or {}
        if not municipality_matches(existing.get('municipality_key') or existing.get('municipality'), municipality_variants):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403
        existing_region = normalize_scope(existing.get('region_key') or existing.get('region'))
        if region_variants and existing_region not in region_variants:
            return jsonify({'success': False, 'error': 'Access denied for region'}), 403

        ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] tasks_municipal_delete failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete task'}), 500

@bp.route('/operations/applicants-municipal')
@role_required('municipal','municipal_admin')
def applicants_municipal():
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or '').strip()
    user_region = (_resolve_region_from_user_context() or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    municipality_key = normalize_scope(user_municipality)
    region_key = normalize_scope(user_region)

    # If nothing can be resolved from user context, render gracefully.
    if not municipality_key or not region_key:
        return render_template(
            'municipal/operations/applicants-municipal.html',
            applications=[],
            total_count=0,
            approved_count=0,
            pending_count=0,
            rejected_count=0,
            barangay_options=[],
            trend_labels_json=json.dumps([]),
            trend_values_json=json.dumps([]),
            status_values_json=json.dumps([0, 0, 0]),
            barangay_labels_json=json.dumps([]),
            barangay_values_json=json.dumps([]),
            user_region=user_region,
            user_municipality=user_municipality
        )

    def _safe_datetime(value):
        if isinstance(value, datetime):
            return value
        if hasattr(value, 'to_datetime'):
            try:
                return value.to_datetime()
            except Exception:
                return None
        return None

    # Ensure Firestore collection exists and has DENR applicant jobs for this scope.
    # This creates/updates a denormalized jobs collection scoped by region + municipality.
    try:
        source_docs = list(
            db.collection('applications')
            .where('municipality', '==', user_municipality)
            .stream()
        )
        if not source_docs:
            source_docs = list(db.collection('applications').stream())

        for source_doc in source_docs:
            src = source_doc.to_dict() or {}
            src_municipality = normalize_scope(
                src.get('municipality')
                or src.get('municipality_name')
                or src.get('municipalityName')
                or src.get('target_municipality')
            )
            src_region = normalize_scope(
                src.get('region')
                or src.get('region_name')
                or src.get('regionName')
                or src.get('target_region')
            )

            if src_municipality and src_municipality != municipality_key:
                continue
            if src_region and src_region != region_key:
                continue

            applicant_name = (
                src.get('applicant_name')
                or src.get('applicantName')
                or src.get('fullName')
                or src.get('name')
                or 'N/A'
            )
            category = (
                src.get('category')
                or src.get('application_type')
                or src.get('applicantCategory')
                or 'DENR Application'
            )
            status = str(src.get('status') or 'PENDING').strip().upper()
            barangay = (
                src.get('barangay')
                or src.get('barangay_name')
                or src.get('address_barangay')
                or 'N/A'
            )
            reference_id = (
                src.get('reference_id')
                or src.get('referenceId')
                or src.get('ref_code')
                or source_doc.id[:8].upper()
            )
            reference_id = str(reference_id).strip()
            if reference_id.upper().startswith('APP-'):
                reference_id = reference_id[4:]
            created_raw = src.get('date_filed') or src.get('created_at') or src.get('timestamp')
            created_dt = _safe_datetime(created_raw)

            denr_job = {
                'source_id': source_doc.id,
                'source_collection': 'applications',
                'applicant_name': str(applicant_name).strip(),
                'category': str(category).strip(),
                'job_title': f"{str(category).strip()} Review",
                'job_description': 'Validate DENR applicant documents and requirements for municipal processing.',
                'status': status,
                'barangay': str(barangay).strip(),
                'reference_id': reference_id,
                'municipality': user_municipality,
                'region': user_region,
                'municipality_key': municipality_key,
                'region_key': region_key,
                'date_filed': created_dt.strftime('%Y-%m-%d') if created_dt else datetime.utcnow().strftime('%Y-%m-%d'),
                'created_at': created_dt or firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }

            db.collection('municipal_denr_applicant_jobs').document(f"APP-{source_doc.id}").set(denr_job, merge=True)
    except Exception as e:
        print(f"[WARN] Could not sync municipal_denr_applicant_jobs from applications: {e}")

    applications = []
    try:
        query = (
            db.collection('municipal_denr_applicant_jobs')
            .where('municipality_key', '==', municipality_key)
            .where('region_key', '==', region_key)
            .stream()
        )
        for doc in query:
            item = doc.to_dict() or {}
            item['id'] = doc.id
            raw_created = item.get('created_at')
            created_dt = _safe_datetime(raw_created)
            item['created_at_dt'] = created_dt
            item['date_filed'] = item.get('date_filed') or (created_dt.strftime('%Y-%m-%d') if created_dt else 'N/A')
            ref_value = str(item.get('reference_id') or doc.id[:8].upper()).strip()
            if ref_value.upper().startswith('APP-'):
                ref_value = ref_value[4:]
            item['reference_id'] = ref_value
            item['applicant_name'] = item.get('applicant_name') or 'N/A'
            item['category'] = item.get('category') or 'DENR Application'
            item['barangay'] = item.get('barangay') or 'N/A'
            item['status'] = str(item.get('status') or 'PENDING').upper()
            applications.append(item)
    except Exception as e:
        print(f"[WARN] Scoped query failed, fallback filtering in-memory: {e}")
        try:
            fallback_docs = db.collection('municipal_denr_applicant_jobs').stream()
            for doc in fallback_docs:
                item = doc.to_dict() or {}
                item['id'] = doc.id
                if normalize_scope(item.get('municipality_key') or item.get('municipality')) != municipality_key:
                    continue
                if normalize_scope(item.get('region_key') or item.get('region')) != region_key:
                    continue
                raw_created = item.get('created_at')
                created_dt = _safe_datetime(raw_created)
                item['created_at_dt'] = created_dt
                item['date_filed'] = item.get('date_filed') or (created_dt.strftime('%Y-%m-%d') if created_dt else 'N/A')
                ref_value = str(item.get('reference_id') or doc.id[:8].upper()).strip()
                if ref_value.upper().startswith('APP-'):
                    ref_value = ref_value[4:]
                item['reference_id'] = ref_value
                item['applicant_name'] = item.get('applicant_name') or 'N/A'
                item['category'] = item.get('category') or 'DENR Application'
                item['barangay'] = item.get('barangay') or 'N/A'
                item['status'] = str(item.get('status') or 'PENDING').upper()
                applications.append(item)
        except Exception as fallback_error:
            print(f"[ERROR] Fallback query failed for municipal_denr_applicant_jobs: {fallback_error}")

    applications.sort(key=lambda x: x.get('created_at_dt') or datetime.min, reverse=True)

    total_count = len(applications)
    approved_count = len([a for a in applications if a.get('status') == 'APPROVED'])
    pending_count = len([a for a in applications if a.get('status') == 'PENDING'])
    rejected_count = len([a for a in applications if a.get('status') == 'REJECTED'])

    barangay_counts = Counter([(a.get('barangay') or 'N/A') for a in applications])
    barangay_options = sorted([b for b in barangay_counts.keys() if b and b != 'N/A'])

    monthly_counts = Counter()
    for app in applications:
        month_key = 'N/A'
        dt = app.get('created_at_dt')
        if dt:
            month_key = dt.strftime('%b')
        monthly_counts[month_key] += 1
    ordered_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    trend_labels = [m for m in ordered_months if monthly_counts.get(m)]
    trend_values = [monthly_counts[m] for m in trend_labels]
    if not trend_labels:
        trend_labels = ['No Data']
        trend_values = [0]

    status_values = [approved_count, pending_count, rejected_count]

    top_barangays = barangay_counts.most_common(5)
    barangay_labels = [x[0] for x in top_barangays] if top_barangays else ['No Data']
    barangay_values = [x[1] for x in top_barangays] if top_barangays else [0]

    return render_template(
        'municipal/operations/applicants-municipal.html',
        applications=applications,
        total_count=total_count,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        barangay_options=barangay_options,
        trend_labels_json=json.dumps(trend_labels),
        trend_values_json=json.dumps(trend_values),
        status_values_json=json.dumps(status_values),
        barangay_labels_json=json.dumps(barangay_labels),
        barangay_values_json=json.dumps(barangay_values),
        user_region=user_region,
        user_municipality=user_municipality
    )


@bp.route('/operations/applicants-municipal/job/<job_id>', methods=['GET'])
@role_required('municipal','municipal_admin')
def applicants_municipal_job_detail(job_id):
    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or '').strip()
    user_region = (_resolve_region_from_user_context() or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    try:
        doc = db.collection('municipal_denr_applicant_jobs').document(job_id).get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Applicant job not found'}), 404

        data = doc.to_dict() or {}
        if normalize_scope(data.get('municipality_key') or data.get('municipality')) != normalize_scope(user_municipality):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403
        if normalize_scope(data.get('region_key') or data.get('region')) != normalize_scope(user_region):
            return jsonify({'success': False, 'error': 'Access denied for region'}), 403

        return jsonify({'success': True, 'job': {
            'id': doc.id,
            'reference_id': data.get('reference_id') or doc.id,
            'applicant_name': data.get('applicant_name') or 'N/A',
            'category': data.get('category') or 'DENR Application',
            'barangay': data.get('barangay') or 'N/A',
            'status': str(data.get('status') or 'PENDING').upper(),
            'date_filed': data.get('date_filed') or 'N/A',
            'job_title': data.get('job_title') or 'DENR Applicant Job',
            'job_description': data.get('job_description') or ''
        }})
    except Exception as e:
        print(f"[ERROR] Failed to fetch applicant job detail: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch applicant job detail'}), 500


@bp.route('/operations/applicants-municipal/job/<job_id>/status', methods=['POST'])
@role_required('municipal','municipal_admin')
def applicants_municipal_job_update_status(job_id):
    from firebase_admin import firestore

    db = get_firestore_db()
    user_municipality = (_resolve_municipality_from_user_context() or '').strip()
    user_region = (_resolve_region_from_user_context() or '').strip()

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    data = request.get_json(silent=True) or {}
    new_status = str(data.get('status') or '').strip().upper()
    if new_status not in {'APPROVED', 'REJECTED', 'PENDING'}:
        return jsonify({'success': False, 'error': 'Invalid status value'}), 400

    try:
        doc_ref = db.collection('municipal_denr_applicant_jobs').document(job_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Applicant job not found'}), 404

        existing = doc.to_dict() or {}
        if normalize_scope(existing.get('municipality_key') or existing.get('municipality')) != normalize_scope(user_municipality):
            return jsonify({'success': False, 'error': 'Access denied for municipality'}), 403
        if normalize_scope(existing.get('region_key') or existing.get('region')) != normalize_scope(user_region):
            return jsonify({'success': False, 'error': 'Access denied for region'}), 403

        doc_ref.set({
            'status': new_status,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)

        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        print(f"[ERROR] Failed to update applicant job status: {e}")
        return jsonify({'success': False, 'error': 'Failed to update applicant job status'}), 500

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

    # Keep dashboard Total Deposit aligned with Accounting > Payment Deposits page source.
    try:
        deposits_response = api_get_municipal_payment_deposits()
        if isinstance(deposits_response, tuple):
            response_obj, status_code = deposits_response
        else:
            response_obj = deposits_response
            status_code = getattr(response_obj, 'status_code', 200)

        if status_code == 200 and hasattr(response_obj, 'get_json'):
            payload = response_obj.get_json(silent=True) or {}
            deposits = payload.get('deposits') or []
            total_deposit_amount = 0.0
            for row in deposits:
                try:
                    total_deposit_amount += float(row.get('amount') or 0)
                except Exception:
                    continue

            if not isinstance(finance_data, dict):
                finance_data = {}
            if not isinstance(finance_data.get('treasury'), dict):
                finance_data['treasury'] = {}
            finance_data['treasury']['total_deposit'] = total_deposit_amount
            print(f"[DEBUG] Dashboard total_deposit synced from municipal payment deposits: {total_deposit_amount}")
        else:
            print(f"[WARN] Could not sync dashboard total_deposit from payment deposits (status={status_code})")
    except Exception as e:
        print(f"[WARN] Failed syncing dashboard total_deposit from payment deposits: {e}")

    # Keep dashboard Total Expenses aligned with Accounting > Expense Categories page source.
    try:
        expenses_response = api_get_expenses()
        if isinstance(expenses_response, tuple):
            response_obj, status_code = expenses_response
        else:
            response_obj = expenses_response
            status_code = getattr(response_obj, 'status_code', 200)

        if status_code == 200 and hasattr(response_obj, 'get_json'):
            payload = response_obj.get_json(silent=True) or {}
            categories = payload.get('categories') or []

            total_expenses_amount = 0.0
            has_amount = False
            for row in categories:
                raw_amount = row.get('amount')
                if raw_amount is None:
                    raw_amount = row.get('expense_amount')
                if raw_amount is None:
                    raw_amount = row.get('total_amount')
                try:
                    amount_val = float(raw_amount or 0)
                    if amount_val:
                        has_amount = True
                    total_expenses_amount += amount_val
                except Exception:
                    continue

            # Expense category records usually have no amount field; fallback to record count.
            total_expenses_value = total_expenses_amount if has_amount else len(categories)

            if not isinstance(finance_data, dict):
                finance_data = {}
            if not isinstance(finance_data.get('treasury'), dict):
                finance_data['treasury'] = {}
            finance_data['treasury']['total_expenses'] = total_expenses_value
            print(f"[DEBUG] Dashboard total_expenses synced from municipal expenses source: {total_expenses_value}")
        else:
            print(f"[WARN] Could not sync dashboard total_expenses from expenses source (status={status_code})")
    except Exception as e:
        print(f"[WARN] Failed syncing dashboard total_expenses from expenses source: {e}")

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
        province_name=province_name,
        firebase_config=Config.FIREBASE_CONFIG
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
    # Always set status to 'pending' for municipal/regional proposals
    status = 'pending'
    if not date_iso or not name:
        return jsonify({'success': False, 'error': 'Missing date or name'}), 400
    doc_id = add_holiday_to_firestore(date_iso, name, description, holiday_type, office_status, open_time, close_time, status)
    return jsonify({'success': True, 'doc_id': doc_id})
# Add this route at the end of the file:
#
# @bp.route('/municipal-profile-update')
# @role_required('municipal','municipal_admin')
# def municipal_profile_update():
#     return render_template('municipal/municipal-profile-update.html')


from expense_storage import get_all_expense_categories

@bp.route('/api/expense-categories', methods=['GET'])
@role_required('municipal', 'municipal_admin')
def api_get_municipal_expense_categories():
    """Get all expense categories for this municipality only"""
    try:
        municipality = request.args.get('municipality')
        if not municipality:
            # Try to resolve from session
            municipality = session.get('municipality') or session.get('user_municipality')
        if not municipality:
            return jsonify({'error': 'Municipality not specified'}), 400
        categories = get_all_expense_categories(municipality=municipality)
        return jsonify(categories), 200
    except Exception as e:
        print(f"[ERROR] Municipal: Failed to get expense categories: {e}")
        return jsonify({'error': str(e)}), 500
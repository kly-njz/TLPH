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

@bp.route('/service-view', defaults={'doc_id': None})
@bp.route('/service-view/<doc_id>')
@role_required('regional','regional_admin')
def service_info_view(doc_id=None):
    return render_template('regional/service-regional-view.html', doc_id=doc_id)

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
@role_required('regional','regional_admin')
def audit_logs_view():
    return render_template('regional/audit-logs-regional-view.html')

@bp.route('/system-logs')
@bp.route('/system-logs-view')
@role_required('regional','regional_admin')
def system_logs_view():
    return render_template('regional/logs/system-logs.html')

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
    from flask import session
    db = firestore.client()
    finance_data = {}
    user_region = (session.get('region') or session.get('user_region') or '').upper().replace('–', '-').replace('—', '-').replace('  ', ' ').replace(' ', '-')
    # If user_region is empty, fetch from Firestore user document
    if not user_region:
        user_email = session.get('user_email')
        if user_email:
            user_docs = db.collection('users').where('email', '==', user_email).stream()
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
        reg_funds_query = db.collection('regional_fund_distribution').where('region', '==', user_region).stream()
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
        muni_funds_query = db.collection('municipal_fund_distribution').where('region', '==', user_region).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
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
        reg_funds_query = db.collection('regional_fund_distribution').where('region', '==', user_region).order_by('date', direction=firestore.Query.DESCENDING).stream()
        for fund_doc in reg_funds_query:
            fund = fund_doc.to_dict()
            regional_funds.append(fund)
        print(f"[DEBUG] Fetched regional_fund_distributions: {regional_funds}")
    except Exception as e:
        print(f"[DEBUG] Error fetching regional fund distributions: {e}")

    return render_template('regional/accounting/dashboard-regional.html', finance=finance_data, municipalities=municipalities, regional_funds=regional_funds, municipal_funds=municipal_funds, user_region=user_region)

@bp.route('/accounting/distribute-fund', methods=['POST'])
@role_required('regional','regional_admin')
def distribute_fund():
    from flask import request, jsonify
    from firebase_admin import firestore
    db = firestore.client()
    data = request.json
    muni = data.get('municipality')
    province = data.get('province')
    amount = float(data.get('amount'))
    fund_type = data.get('fund_type')
    transfer_id = data.get('transfer_id')
    region = data.get('region')
    print(f"[DEBUG] Incoming fund distribution request: region={region}, municipality={muni}, province={province}, amount={amount}, fund_type={fund_type}, transfer_id={transfer_id}")
    # Validate municipality belongs to region
    allowed_munis = []
    allowed_pairs = set()
    try:
        doc = db.collection('municipalities').document(region).get()
        if doc.exists:
            allowed_munis = doc.to_dict().get('municipalities', [])
            # allowed_munis is a list of municipality names, but we need province info
            # Try to get province-municipality pairs from frontend or static mapping
            # For now, build pairs from the region definition in dashboard-regional.html
            from models.ph_locations import philippineLocations
            for prov, munis in philippineLocations.items():
                for m in munis:
                    allowed_pairs.add((m, prov))
        print(f"[DEBUG] Allowed municipalities for region {region}: {allowed_munis}")
        print(f"[DEBUG] Allowed muni-province pairs: {allowed_pairs}")
    except Exception as e:
        print(f"[DEBUG] Error fetching allowed municipalities: {e}")
    # Deduct from regional fund (available_fund in finance collection)
    region_finance_ref = db.collection('finance').document(region)
    region_finance_doc = region_finance_ref.get()
    if not region_finance_doc.exists:
        return jsonify({'success': False, 'error': 'Regional fund not found'}), 404
    region_finance = region_finance_doc.to_dict()
    available_fund = float(region_finance.get('received_from_national', 0))

    if muni == 'ALL':
        # Distribute to all municipalities under this region
        total_amount = amount * len(allowed_munis)
        if available_fund < total_amount:
            print(f"[ERROR] Insufficient regional fund: available={available_fund}, required={total_amount}")
            return jsonify({'success': False, 'error': f'Insufficient regional fund: available={available_fund}, required={total_amount}'}), 400
        for m in allowed_munis:
            # Province must be provided for each m
            if (m, province) not in allowed_pairs:
                return jsonify({'success': False, 'error': f'Municipality {m} with province {province} not under your region'}), 403
            record = {
                'municipality': m,
                'province': province,
                'amount': amount,
                'fund_type': fund_type,
                'transfer_id': transfer_id + '-' + m,
                'region': region,
                'status': 'Released',
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            db.collection('municipal_fund_distribution').add(record)
            # Update general fund for municipality
            doc_id = f"{m.upper().replace(' ', '_')}_{province.upper().replace(' ', '_')}"
            muni_finance_ref = db.collection('finance').document(doc_id)
            muni_finance_doc = muni_finance_ref.get()
            current_general = 0
            if muni_finance_doc.exists:
                current_general = float(muni_finance_doc.to_dict().get('general_fund', 0))
            muni_finance_ref.set({'general_fund': current_general + amount}, merge=True)
        # Deduct total from regional fund
        region_finance_ref.update({'received_from_national': available_fund - total_amount})
        return jsonify({'success': True, 'distributed': allowed_munis})
    else:
        if (muni, province) not in allowed_pairs:
            return jsonify({'success': False, 'error': f'Municipality {muni} with province {province} not under your region'}), 403
        if available_fund < amount:
            print(f"[ERROR] Insufficient regional fund: available={available_fund}, required={amount}")
            return jsonify({'success': False, 'error': f'Insufficient regional fund: available={available_fund}, required={amount}'}), 400
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
        # Update general fund for municipality
        doc_id = f"{muni.upper().replace(' ', '_')}_{province.upper().replace(' ', '_')}"
        muni_finance_ref = db.collection('finance').document(doc_id)
        muni_finance_doc = muni_finance_ref.get()
        current_general = 0
        if muni_finance_doc.exists:
            current_general = float(muni_finance_doc.to_dict().get('general_fund', 0))
        muni_finance_ref.set({'general_fund': current_general + amount}, merge=True)
        # Deduct from regional fund
        region_finance_ref.update({'received_from_national': available_fund - amount})
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
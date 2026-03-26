from flask import Blueprint, render_template, request, jsonify
from firebase_auth_middleware import role_required
from firebase_config import get_firestore_db
from datetime import datetime
from collections import defaultdict

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

@bp.route('/inventory')
@role_required('super-admin','superadmin')
def inventory_view():
    inventory_records = []
    summary = {
        'total_assets': 0,
        'chemicals': 0,
        'natural_assets': 0,
        'protected_areas': 0,
        'low_stock': 0
    }
    trend_labels = []
    trend_data = []
    category_labels = []
    category_data = []
    region_options = []

    try:
        db = get_firestore_db()
        from models.region_province_map import region_province_map
        docs = db.collection('inventory_registrations').stream()
        monthly_totals = defaultdict(float)
        category_totals = defaultdict(float)
        regions_set = set()

        users_map = {}
        try:
            users_map = {u.id: (u.to_dict() or {}) for u in db.collection('users').stream()}
        except Exception:
            users_map = {}

        def to_number(value):
            try:
                if value is None or value == '':
                    return 0.0
                return float(value)
            except Exception:
                return 0.0

        def normalize_category(raw):
            text = str(raw or '').strip().lower()
            if any(k in text for k in ['chemical', 'fertilizer', 'pesticide', 'ammonium', 'nitrogen']):
                return 'CHEMICAL RESOURCES'
            if any(k in text for k in ['protected', 'sanctuary', 'park', 'conservation', 'eco-zone', 'ecozone']):
                return 'PROTECTED AREAS'
            if any(k in text for k in ['natural', 'forest', 'mangrove', 'biodiversity', 'wildlife', 'resource']):
                return 'NATURAL ASSETS'
            if any(k in text for k in ['equipment', 'tool', 'device', 'machinery', 'kit', 'gps']):
                return 'EQUIPMENT'
            return ''

        def category_from_sector(raw_sector):
            sector = str(raw_sector or '').strip().lower()
            if sector == 'farming':
                return 'CHEMICAL RESOURCES'
            if sector in {'fisheries', 'forestry', 'environment'}:
                return 'NATURAL ASSETS'
            if sector in {'wildlife'}:
                return 'PROTECTED AREAS'
            if sector in {'livestock'}:
                return 'NATURAL ASSETS'
            return ''

        def category_from_app_type(raw_app_type):
            app_type = str(raw_app_type or '').strip().lower()
            if any(k in app_type for k in ['farm', 'crop', 'soil', 'pest', 'fertilizer', 'chemical']):
                return 'CHEMICAL RESOURCES'
            if any(k in app_type for k in ['forest', 'fish', 'fisher', 'marine', 'environment']):
                return 'NATURAL ASSETS'
            if any(k in app_type for k in ['wildlife', 'protected', 'sanctuary']):
                return 'PROTECTED AREAS'
            if any(k in app_type for k in ['equipment', 'device', 'tool']):
                return 'EQUIPMENT'
            return ''

        def region_from_province(province_name):
            p = str(province_name or '').strip().lower()
            if not p:
                return ''
            for region_label, provinces in (region_province_map or {}).items():
                for prov in (provinces or []):
                    if str(prov or '').strip().lower() == p:
                        return region_label
            return ''

        def parse_dt(raw):
            if not raw:
                return None
            if isinstance(raw, datetime):
                return raw
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw.replace('Z', '+00:00'))
                except Exception:
                    return None
            if hasattr(raw, 'to_datetime'):
                try:
                    return raw.to_datetime()
                except Exception:
                    return None
            if hasattr(raw, 'strftime'):
                return raw
            return None

        for doc in docs:
            data = doc.to_dict() or {}
            form_data = data.get('formData') or {}
            user_data = users_map.get(data.get('userId', ''), {})

            quantity = to_number(
                data.get('stockAvailable')
                or data.get('quantity')
                or data.get('volume')
                or data.get('availableStock')
                or form_data.get('quantity')
                or form_data.get('stockAvailable')
                or 0
            )

            raw_category = (
                data.get('category')
                or data.get('classification')
                or data.get('itemType')
                or data.get('inventoryType')
            )

            created_at_raw = data.get('createdAt') or data.get('submittedAt')
            created_at = parse_dt(created_at_raw)

            municipality = (
                data.get('municipality')
                or data.get('location')
                or form_data.get('municipality')
                or user_data.get('municipality')
                or 'N/A'
            )

            province = (
                data.get('province')
                or form_data.get('province')
                or user_data.get('province')
                or ''
            )

            region = (
                data.get('region')
                or data.get('regionName')
                or form_data.get('region')
                or user_data.get('region')
                or user_data.get('regionName')
                or region_from_province(province)
                or 'N/A'
            )

            description = (
                data.get('resourceName')
                or data.get('notes')
                or data.get('description')
                or data.get('itemName')
                or data.get('itemDescription')
                or form_data.get('resourceName')
                or form_data.get('description')
                or 'N/A'
            )

            normalized_category = (
                normalize_category(raw_category)
                or category_from_sector(data.get('sector'))
                or category_from_app_type(data.get('applicationType'))
                or normalize_category(description)
                or 'NATURAL ASSETS'
            )

            # Skip placeholder/empty records to avoid all-N/A rows.
            if str(description).strip().upper() in {'', 'N/A'} and quantity <= 0 and str(region).strip().upper() == 'N/A' and str(municipality).strip().upper() == 'N/A':
                continue

            inventory_records.append({
                'id': doc.id,
                'category': normalized_category,
                'description': str(description).strip(),
                'quantity': quantity,
                'region': str(region).strip(),
                'municipality': str(municipality).strip(),
                'created_at': created_at,
                'status': (data.get('status') or '').strip()
            })

            summary['total_assets'] += quantity
            if normalized_category == 'CHEMICAL RESOURCES':
                summary['chemicals'] += quantity
            elif normalized_category == 'NATURAL ASSETS':
                summary['natural_assets'] += quantity
            elif normalized_category == 'PROTECTED AREAS':
                summary['protected_areas'] += quantity

            status_text = str(data.get('status') or '').lower()
            if 'low stock' in status_text or quantity <= 20:
                summary['low_stock'] += 1

            if created_at:
                monthly_totals[created_at.strftime('%Y-%m')] += quantity
            category_totals[normalized_category] += quantity
            regions_set.add(region)

        inventory_records.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)

        inventory_rows = []
        for rec in inventory_records:
            qty = rec.get('quantity', 0)
            try:
                qty = float(qty)
                if qty.is_integer():
                    qty = int(qty)
            except Exception:
                qty = 0

            inventory_rows.append({
                'cat': rec.get('category', 'UNCATEGORIZED'),
                'desc': rec.get('description', 'N/A'),
                'qty': qty,
                'reg': rec.get('region', 'N/A'),
                'mun': rec.get('municipality', 'N/A')
            })

        now = datetime.now()
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            month_key = f'{year}-{month:02d}'
            trend_labels.append(datetime(year, month, 1).strftime('%b'))
            trend_data.append(round(monthly_totals.get(month_key, 0), 2))

        category_priority = ['CHEMICAL RESOURCES', 'NATURAL ASSETS', 'PROTECTED AREAS', 'EQUIPMENT', 'UNCATEGORIZED']
        category_labels = [c for c in category_priority if category_totals.get(c, 0) > 0]
        category_data = [round(category_totals[c], 2) for c in category_labels]
        if not category_labels:
            category_labels = ['UNCATEGORIZED']
            category_data = [0]

        region_options = sorted([r for r in regions_set if r and str(r).strip().upper() != 'N/A'])
    except Exception as e:
        print(f'[ERROR] superadmin inventory_view: {e}')
        inventory_rows = []

    return render_template(
        'super-admin/inventory-superadmin/inventory-superadmin.html',
        inventory_records=inventory_records,
        summary=summary,
        trend_labels=trend_labels,
        trend_data=trend_data,
        category_labels=category_labels,
        category_data=category_data,
        region_options=region_options,
        inventory_rows=inventory_rows
    )

@bp.route('/user-application')
@role_required('super-admin','superadmin')
def user_application_view():
    stats = {
        'total': 0, 'pending': 0, 'approved': 0,
        'rejected': 0, 'to_review': 0, 'cancelled': 0, 'approval_rate': 0,
    }
    categories = []
    regions = []

    try:
        db = get_firestore_db()
        docs = list(db.collection('applications').limit(5000).stream())

        def sector_label(value):
            raw = str(value or '').strip()
            key = raw.lower()
            mapping = {
                'farming': 'Crop & Plant',
                'livestock': 'Fisheries & Agriculture',
                'agribusiness': 'Agribusiness & Agro-Processing',
                'trade': 'Agricultural Trade',
                'infrastructure': 'Infrastructure',
            }
            return mapping.get(key, raw)

        cat_set = set()
        reg_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict() or {}
            form_data = data.get('formData') or {}
            stats['total'] += 1

            national_status = (data.get('nationalStatus') or '').lower()
            status = (data.get('status') or 'pending').lower()
            effective = national_status if national_status else status

            if effective in ['canceled']:
                effective = 'cancelled'
            if effective.startswith('forwarded'):
                effective = 'to_review'

            if effective in ['approved']:
                stats['approved'] += 1
            elif effective in ['rejected']:
                stats['rejected'] += 1
            elif effective in ['cancelled']:
                stats['cancelled'] += 1
            elif effective in ['to review', 'review']:
                stats['to_review'] += 1
            else:
                stats['pending'] += 1

            cat = (
                data.get('categoryType')
                or data.get('category')
                or data.get('applicantCategory')
                or data.get('sector')
                or form_data.get('categoryType')
                or form_data.get('category')
                or form_data.get('sector')
                or ''
            ).strip()
            if cat:
                cat_set.add(sector_label(cat))

            reg = (
                data.get('region')
                or data.get('regionName')
                or form_data.get('region')
                or ''
            ).strip()
            if reg:
                reg_count[reg] += 1

        if stats['total'] > 0:
            stats['approval_rate'] = round(stats['approved'] / stats['total'] * 100, 1)

        categories = sorted(cat_set)
        regions = sorted(reg_count.keys())

    except Exception as e:
        print(f'[ERROR] user_application_view: {e}')

    return render_template(
        'super-admin/application-superadmin/application-superadmin.html',
        stats=stats,
        categories=categories,
        regions=regions,
    )

@bp.route('/user-service-request')
@role_required('super-admin','superadmin')
def user_request_view():
    return render_template('super-admin/service-request-superadmin/service-request-superadmin.html')

@bp.route('/user-inventory')
@role_required('super-admin','superadmin')
def user_inventory_view():
    return render_template('super-admin/user-inventory-superadmin/user-inventory-superadmin.html')

@bp.route('/permits')
@role_required('super-admin','superadmin')
def permits_view():
    return render_template('super-admin/permits-license-superadmin/permits-license-superadmin.html')

@bp.route('/accounting/transaction')
@role_required('super-admin','superadmin')
def transaction_permits_view():
    return render_template('super-admin/transaction-permit-superadmin/transaction-permit-superadmin.html')

@bp.route('/account')
@role_required('super-admin','superadmin')
def accounts_view():
    return render_template('super-admin/superadmin-account/superadmin-account.html')

@bp.route('/audit-logs')
@role_required('super-admin','superadmin')
def audit_logs_view():
    return render_template('super-admin/audit-logs-superadmin/audit-logs-superadmin.html')

@bp.route('/system-logs')
@role_required('super-admin','superadmin')
def system_logs_view():
    return render_template('super-admin/system-logs/system-logs.html')

@bp.route('/superadmin-profile')
@role_required('super-admin','superadmin')
def superadmin_profile():
    return render_template('super-admin/superadmin-profile.html')

@bp.route('/superadmin-notification')
@role_required('super-admin','superadmin')
def superadmin_notification():
    return render_template('super-admin/superadmin-notification.html')

# --- Added stubs for additional superadmin UI pages requested by product owner ---
@bp.route('/regions')
@role_required('super-admin','superadmin')
def regions_list_view():
    return render_template('super-admin/regions/regions-list.html')


@bp.route('/regions/<region_id>')
@role_required('super-admin','superadmin')
def regions_detail_view(region_id):
    return render_template('super-admin/regions/region-detail.html', region_id=region_id)

@bp.route('/user-groups')
@role_required('super-admin','superadmin')
def user_groups_view():
    return render_template('super-admin/user-groups/user-groups.html')

@bp.route('/products-national')
@role_required('super-admin','superadmin')
def products_national_view():
    return render_template('super-admin/products/products-national.html')

@bp.route('/purchases')
@role_required('super-admin','superadmin')
def purchases_view():
    return render_template('super-admin/products/purchases-supplier.html')

@bp.route('/sales')
@role_required('super-admin','superadmin')
def sales_view():
    return render_template('super-admin/products/sales-list.html')

@bp.route('/sales-return')
@role_required('super-admin','superadmin')
def sales_return_view():
    return render_template('super-admin/products/sales-return.html')

@bp.route('/distributed-products')
@role_required('super-admin','superadmin')
def distributed_products_view():
    return render_template('super-admin/products/distributed-products.html')

@bp.route('/damage-products')
@role_required('super-admin','superadmin')
def damage_products_view():
    return render_template('super-admin/products/damage-products.html')

@bp.route('/transfer-products')
@role_required('super-admin','superadmin')
def transfer_products_view():
    return render_template('super-admin/products/transfer-products.html')

@bp.route('/quotation')
@role_required('super-admin','superadmin')
def quotation_view():
    return render_template('super-admin/finance/quotation.html')

@bp.route('/projects')
@role_required('super-admin','superadmin')
def projects_view():
    return render_template('super-admin/projects/projects-region.html')

@bp.route('/tasks')
@role_required('super-admin','superadmin')
def tasks_view():
    return render_template('super-admin/projects/tasks-region.html')

@bp.route('/applicants')
@role_required('super-admin','superadmin')
def applicants_view():
    return render_template('super-admin/applicants/applicants.html')

# --- Accounting Module Routes ---
@bp.route('/accounting/dashboard')
def accounting_dashboard():
    return render_template('super-admin/accounting/accounting-dashboard.html')

@bp.route('/accounting/entities')
def accounting_entities():
    return render_template('super-admin/accounting/entities.html')

@bp.route('/accounting/coa-templates')
def accounting_coa_templates():
    return render_template('super-admin/accounting/coa-templates.html')

@bp.route('/accounting/expense-categories')
def accounting_expense_categories():
    return render_template('super-admin/accounting/expense-categories.html')

@bp.route('/accounting/deposit-categories')
def accounting_deposit_categories():
    return render_template('super-admin/accounting/deposit-categories.html')

@bp.route('/permissions')
def accounting_permissions():
    return render_template('super-admin/accounting/permissions.html')

@bp.route('/accounting/audit')
def accounting_audit():
    return render_template('super-admin/accounting/audit.html')

# --- SUPERADMIN PAYROLL ACTIONS ---
@bp.route('/api/hrm/payroll/<payroll_id>/approve', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_approve_payroll(payroll_id):
    """Approve any payroll record as superadmin."""
    # TODO: Integrate with payroll storage logic
    # Example: payroll_storage.superadmin_approve(payroll_id, user=session['user_email'])
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} approved by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/reject', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_reject_payroll(payroll_id):
    """Reject any payroll record as superadmin."""
    # TODO: Integrate with payroll storage logic
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} rejected by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/override', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_override_payroll(payroll_id):
    """Override payroll status as superadmin."""
    # TODO: Integrate with payroll storage logic
    data = request.get_json() or {}
    new_status = data.get('status')
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} status overridden to {new_status} by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/audit-log', methods=['GET'])
@role_required('super-admin','superadmin')
def superadmin_payroll_audit_log(payroll_id):
    """Fetch audit log for a payroll record."""
    # TODO: Integrate with audit log storage
    # Example: logs = payroll_storage.get_audit_log(payroll_id)
    logs = [
        {'action': 'created', 'by': 'user@example.com', 'at': '2026-03-01T10:00:00Z'},
        {'action': 'approved', 'by': 'regional_admin@example.com', 'at': '2026-03-02T12:00:00Z'},
        {'action': 'approved', 'by': 'national_admin@example.com', 'at': '2026-03-03T15:00:00Z'},
    ]
    return jsonify({'success': True, 'logs': logs})

@bp.route('/hrm/payroll')
@role_required('super-admin','superadmin')
def hr_payroll_view():
    return render_template('super-admin/human-resource-superadmin/payroll-superadmin.html')


@bp.route('/api/hrm/payroll', methods=['GET'])
@role_required('super-admin','superadmin')
def api_get_superadmin_payroll():
    """Fetch all payroll records for superadmin payroll registry (all regions/municipalities)."""
    try:
        db = get_firestore_db()
        employees_ref = db.collection('employees')
        docs = employees_ref.stream()
        employees = []
        required_fields = [
            'employee_id', 'first_name', 'middle_name', 'last_name', 'email',
            'designation', 'department_name', 'division', 'role', 'region', 'municipality',
            'basic_pay', 'allowances', 'gross_pay', 'deductions', 'net_pay',
            'status', 'hire_date', 'period', 'month', 'payroll_no'
        ]
        for doc in docs:
            data = doc.to_dict() or {}
            data['id'] = doc.id
            # Compose full name if missing
            if not data.get('name'):
                fn = data.get('first_name', '')
                mn = data.get('middle_name', '')
                ln = data.get('last_name', '')
                data['name'] = f"{fn} {mn} {ln}".replace('  ', ' ').strip()
            # Fill missing payroll fields with defaults
            for field in required_fields:
                if field not in data or data[field] is None:
                    if field in ['basic_pay', 'allowances', 'gross_pay', 'deductions', 'net_pay']:
                        data[field] = 0
                    elif field == 'status':
                        data[field] = 'DRAFT'
                    elif field == 'period':
                        data[field] = 'MONTHLY'
                    elif field == 'month':
                        data[field] = ''
                    elif field == 'payroll_no':
                        data[field] = ''
                    else:
                        data[field] = ''
            employees.append(data)
        return jsonify({'success': True, 'payrolls': employees, 'count': len(employees)})
    except Exception as e:
        print(f'[ERROR] Failed to fetch employees for payroll: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
    

@bp.route('/api/hrm/employee', methods=['POST'])
@role_required('super-admin','superadmin')
def api_create_employee():
    """Create a new employee in the employees collection."""
    try:
        db = get_firestore_db()
        data = request.get_json() or {}
        # Auto-generate employee_id if not provided
        employee_id = data.get('employee_id') or f"EMP-{int(datetime.utcnow().timestamp())}-{str(hash(str(data)))[:6]}"
        data['employee_id'] = employee_id
        # Set default payroll fields if missing
        for field, default in [
            ('basic_pay', 0), ('allowances', 0), ('gross_pay', 0), ('deductions', 0), ('net_pay', 0),
            ('status', 'DRAFT'), ('period', 'MONTHLY'), ('month', ''), ('payroll_no', ''), ('name', ''),
            ('region', ''), ('municipality', ''), ('designation', ''), ('department_name', ''), ('division', ''), ('role', ''), ('email', ''), ('first_name', ''), ('middle_name', ''), ('last_name', ''), ('remarks', '')
        ]:
            if field not in data:
                data[field] = default
        # Compose full name if missing
        if not data.get('name'):
            fn = data.get('first_name', '')
            mn = data.get('middle_name', '')
            ln = data.get('last_name', '')
            data['name'] = f"{fn} {mn} {ln}".replace('  ', ' ').strip()
        db.collection('employees').document(employee_id).set(data)
        return jsonify({'success': True, 'employee_id': employee_id})
    except Exception as e:
        print(f'[ERROR] Failed to create employee: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# --- HRM SUPERADMIN PAGES ---
from flask import abort

@bp.route('/hrm/attendance')
@role_required('super-admin','superadmin')
def hrm_attendance_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/attendance-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/company')
@role_required('super-admin','superadmin')
def hrm_company_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/company-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/department')
@role_required('super-admin','superadmin')
def hrm_department_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/department-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/designation')
@role_required('super-admin','superadmin')
def hrm_designation_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/designation-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/employee')
@role_required('super-admin','superadmin')
def hrm_employee_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/employee-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/holiday')
@role_required('super-admin','superadmin')
def hrm_holiday_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/holiday-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/leave-request')
@role_required('super-admin','superadmin')
def hrm_leave_request_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/leave-request-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/shift')
@role_required('super-admin','superadmin')
def hrm_shift_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/shift-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/api/hrm/holidays', methods=['GET'])
@role_required('super-admin','superadmin')
def get_superadmin_holidays():
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
            'scope': item.get('scope', 'NATIONAL'),
            'status': item.get('status', 'approved'),
            'office_status': item.get('office_status', ''),
            'open_time': item.get('open_time', ''),
            'close_time': item.get('close_time', '')
        })

    return jsonify({'success': True, 'holidays': holidays})
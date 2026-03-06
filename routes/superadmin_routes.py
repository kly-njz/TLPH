from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

@bp.route('/inventory')
@role_required('super-admin','superadmin')
def inventory_view():
    return render_template('super-admin/inventory-superadmin/inventory-superadmin.html')

@bp.route('/user-application')
@role_required('super-admin','superadmin')
def user_application_view():
    from firebase_config import get_firestore_db
    from collections import defaultdict
    from datetime import datetime

    stats = {
        'total': 0, 'pending': 0, 'approved': 0,
        'rejected': 0, 'to_review': 0, 'approval_rate': 0,
    }
    categories = []
    regions = []

    try:
        db = get_firestore_db()
        docs = db.collection('applications').limit(5000).stream()

        cat_set = set()
        reg_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict() or {}
            stats['total'] += 1

            national_status = (data.get('nationalStatus') or '').lower()
            status = (data.get('status') or 'pending').lower()
            effective = national_status if national_status else status

            if effective in ['approved']:
                stats['approved'] += 1
            elif effective in ['rejected']:
                stats['rejected'] += 1
            elif effective in ['to review', 'review']:
                stats['to_review'] += 1
            else:
                stats['pending'] += 1

            cat = (data.get('category') or data.get('applicantCategory') or '').strip()
            if cat:
                cat_set.add(cat)

            reg = (data.get('region') or data.get('regionName') or '').strip()
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

# -------------------------
# Human Resource (match sidebar URLs)
# URL: /superadmin/human-resource-superadmin/<page>
# Template: templates/super-admin/human-resource-superadmin/<file>.html
# -------------------------

@bp.route('/hrm/company')
@role_required('super-admin','superadmin')
def hr_company_view():
    return render_template('super-admin/human-resource-superadmin/company-superadmin.html')

@bp.route('/hrm/department')
@role_required('super-admin','superadmin')
def hr_department_view():
    return render_template('super-admin/human-resource-superadmin/department-superadmin.html')

@bp.route('/hrm/designation')

@role_required('super-admin','superadmin')
def hr_designation_view():
    return render_template('super-admin/human-resource-superadmin/designation-superadmin.html')

@bp.route('/hrm/shift')
@role_required('super-admin','superadmin')
def hr_shift_view():
    return render_template('super-admin/human-resource-superadmin/shift-superadmin.html')

@bp.route('/hrm/employee')
@role_required('super-admin','superadmin')
def hr_employee_view():
    return render_template('super-admin/human-resource-superadmin/employee-superadmin.html')

@bp.route('/hrm/attendance')
@role_required('super-admin','superadmin')
def hr_attendance_view():
    return render_template('super-admin/human-resource-superadmin/attendance-superadmin.html')

@bp.route('/hrm/holiday')
@role_required('super-admin','superadmin')
def hr_holiday_view():
    return render_template('super-admin/human-resource-superadmin/holiday-superadmin.html')

@bp.route('/hrm/leave-request')
@role_required('super-admin','superadmin')
def hr_leave_request_view():
    return render_template('super-admin/human-resource-superadmin/leave-request-superadmin.html')

@bp.route('/hrm/payroll')
@role_required('super-admin','superadmin')
def hr_payroll_view():
    return render_template('super-admin/human-resource-superadmin/payroll-superadmin.html')

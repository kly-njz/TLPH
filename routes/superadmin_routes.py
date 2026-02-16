from flask import Blueprint, render_template

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

@bp.route('/inventory')
def inventory_view():
    return render_template('super-admin/inventory-superadmin/inventory-superadmin.html')

@bp.route('/user-application')
def user_application_view():
    return render_template('super-admin/application-superadmin/application-superadmin.html')

@bp.route('/user-service-request')
def user_request_view():
    return render_template('super-admin/service-request-superadmin/service-request-superadmin.html')

@bp.route('/user-inventory')
def user_inventory_view():
    return render_template('super-admin/user-inventory-superadmin/user-inventory-superadmin.html')

@bp.route('/permits')
def permits_view():
    return render_template('super-admin/permits-license-superadmin/permits-license-superadmin.html')

@bp.route('/transaction')
def transaction_permits_view():
    return render_template('super-admin/transaction-permit-superadmin/transaction-permit-superadmin.html')

@bp.route('/account')
def accounts_view():
    return render_template('super-admin/superadmin-account/superadmin-account.html')

@bp.route('/audit-logs')
def audit_logs_view():
    return render_template('super-admin/audit-logs-superadmin/audit-logs-superadmin.html')

@bp.route('/superadmin-profile')
def superadmin_profile():
    return render_template('super-admin/superadmin-profile.html')

@bp.route('/superadmin-notification')
def superadmin_notification():
    return render_template('super-admin/superadmin-notification.html')

# --- Added stubs for additional superadmin UI pages requested by product owner ---
@bp.route('/regions')
def regions_list_view():
    return render_template('super-admin/regions/regions-list.html')


@bp.route('/regions/<region_id>')
def regions_detail_view(region_id):
    return render_template('super-admin/regions/region-detail.html', region_id=region_id)

@bp.route('/user-groups')
def user_groups_view():
    return render_template('super-admin/user-groups/user-groups.html')

@bp.route('/products-national')
def products_national_view():
    return render_template('super-admin/products/products-national.html')

@bp.route('/purchases')
def purchases_view():
    return render_template('super-admin/products/purchases-supplier.html')

@bp.route('/sales')
def sales_view():
    return render_template('super-admin/products/sales-list.html')

@bp.route('/sales-return')
def sales_return_view():
    return render_template('super-admin/products/sales-return.html')

@bp.route('/distributed-products')
def distributed_products_view():
    return render_template('super-admin/products/distributed-products.html')

@bp.route('/damage-products')
def damage_products_view():
    return render_template('super-admin/products/damage-products.html')

@bp.route('/transfer-products')
def transfer_products_view():
    return render_template('super-admin/products/transfer-products.html')

@bp.route('/quotation')
def quotation_view():
    return render_template('super-admin/finance/quotation.html')

@bp.route('/projects')
def projects_view():
    return render_template('super-admin/projects/projects-region.html')

@bp.route('/tasks')
def tasks_view():
    return render_template('super-admin/projects/tasks-region.html')

@bp.route('/applicants')
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

@bp.route('/accounting/permissions')
def accounting_permissions():
    return render_template('super-admin/accounting/permissions.html')

@bp.route('/accounting/audit')
def accounting_audit():
    return render_template('super-admin/accounting/audit.html')
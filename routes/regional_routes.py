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

@bp.route('/municipal-account-management-view')
@role_required('regional','regional_admin')
def municipal_account_management_view():
    return render_template('regional/user-management-regional-list.html')

@bp.route('/audit-logs-view')
@role_required('regional','regional_admin')
def audit_logs_view():
    return render_template('regional/audit-logs-regional-view.html')

@bp.route('/application-view')
@role_required('regional','regional_admin')
def application_view():
    return render_template('regional/application-regional-view.html')

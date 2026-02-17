from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

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
    return render_template('municipal/user-inventory-municipal/user-inventory-municiapl.html')

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
    return render_template('municipal/hrm/holiday-municipal.html')

@bp.route('/leave-request')
@role_required('municipal','municipal_admin')
def hrm_leave():
    return render_template('municipal/hrm/leave-municipal.html')

@bp.route('/payroll')
@role_required('municipal','municipal_admin')
def hrm_payroll():
    return render_template('municipal/hrm/payroll-municipal.html')
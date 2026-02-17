from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('permits', __name__, url_prefix='/user/license/permits')

@bp.route('/')
@role_required('user')
def permits_main():
    return render_template('user/license/permits/permits.html')

@bp.route('/export')
@role_required('user')
def export_permit():
    return render_template('user/license/permits/export.html')

@bp.route('/operation')
@role_required('user')
def operation_permit():
    return render_template('user/license/permits/operation-permit.html')

@bp.route('/import')
@role_required('user')
def import_permit():
    return render_template('user/license/permits/import.html')

@bp.route('/wildlife')
@role_required('user')
def wildlife_trade():
    return render_template('user/license/permits/wildlife.html')

@bp.route('/local-transport')
@role_required('user')
def local_transport():
    return render_template('user/license/permits/local-transport.html')

@bp.route('/harvest')
@role_required('user')
def harvest_permit():
    return render_template('user/license/permits/harvest.html')

from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('environment', __name__, url_prefix='/user/license/environment')

@bp.route('/')
@role_required('user')
def environment_main():
    return render_template('user/license/environment/environment.html')

@bp.route('/ecc')
@role_required('user')
def environment_clearance():
    return render_template('user/license/environment/environment-clearance.html')

@bp.route('/waste')
@role_required('user')
def waste_management():
    return render_template('user/license/environment/waste.html')

@bp.route('/water')
@role_required('user')
def water_use():
    return render_template('user/license/environment/water-use.html')

@bp.route('/hazardous')
@role_required('user')
def hazardous_material():
    return render_template('user/license/environment/hazardous.html')

@bp.route('/cco')
@role_required('user')
def cco():
    return render_template('user/license/environment/cco.html')

@bp.route('/hazardous-waste')
@role_required('user')
def hazardous_waste():
    return render_template('user/license/environment/hazardous-waste-generator.html')

@bp.route('pcl')
@role_required('user')
def pcl():
    return render_template('user/license/environment/pcl.html')

@bp.route('permit-to-operate-air')
@role_required('user')
def permit_to_operate_air():
    return render_template('user/license/environment/permit-to-operate-air.html')

@bp.route('piccs')
@role_required('user')
def piccs():
    return render_template('user/license/environment/piccs.html')

@bp.route('water-dispose')
@role_required('user')
def water_dispose():
    return render_template('user/license/environment/water-dispose.html')
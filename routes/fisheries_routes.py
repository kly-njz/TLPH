from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('fisheries', __name__, url_prefix='/user/license/fisheries')

@bp.route('/')
@role_required('user')
def fisheries_main():
    return render_template('user/license/fisheries/fisheries.html')

@bp.route('/aquafarm')
@role_required('user')
def aquafarm():
    return render_template('user/license/fisheries/aquafarm.html')

@bp.route('/transport')
@role_required('user')
def transport():
    return render_template('user/license/fisheries/transport.html')

@bp.route('/dealer')
@role_required('user')
def fish_dealer():
    return render_template('user/license/fisheries/fish-dealer.html')

@bp.route('/processing')
@role_required('user')
def processing():
    return render_template('user/license/fisheries/fish-process.html')

@bp.route('/harvest')
@role_required('user')
def harvest():
    return render_template('user/license/fisheries/harvest.html')

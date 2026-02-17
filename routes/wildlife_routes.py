from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('wildlife', __name__, url_prefix='/user/license/wildlife')

@bp.route('/')
@role_required('user')
def wildlife_main():
    return render_template('user/license/wildlife/wildlife.html')

@bp.route('/ownership')
@role_required('user')
def ownership():
    return render_template('user/license/wildlife/ownership.html')

@bp.route('/transport')
@role_required('user')
def transport():
    return render_template('user/license/wildlife/transport.html')

@bp.route('/collection')
@role_required('user')
def collection():
    return render_template('user/license/wildlife/collection.html')

@bp.route('/wildfarm')
@role_required('user')
def wildfarm():
    return render_template('user/license/wildlife/wildfarm.html')

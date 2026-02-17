from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('farm', __name__, url_prefix='/user/service/farm')

@bp.route('/')
@role_required('user')
def farm_main():
    return render_template('user/service/farm/farm.html')

@bp.route('/initial-visit')
@role_required('user')
def initial_visit():
    return render_template('user/service/farm/initial_visit.html')

@bp.route('/compliance')
@role_required('user')
def compliance():
    return render_template('user/service/farm/compliance.html')

@bp.route('/disease')
@role_required('user')
def disease():
    return render_template('user/service/farm/disease.html')

@bp.route('/soil')
@role_required('user')
def soil():
    return render_template('user/service/farm/soil.html')

@bp.route('/visit')
@role_required('user')
def visit():
    return render_template('user/service/farm/visit.html')

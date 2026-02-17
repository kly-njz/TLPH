from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('livestock', __name__, url_prefix='/user/license/livestock')

@bp.route('/')
@role_required('user')
def livestock_main():
    return render_template('user/license/livestock/livestock.html')

@bp.route('/animal-transport')
@role_required('user')
def animal_transport():
    return render_template('user/license/livestock/animal-transport.html')

@bp.route('/meat-transport')
@role_required('user')
def meat_transport():
    return render_template('user/license/livestock/meat-transport.html')

@bp.route('/slaughterhouse')
@role_required('user')
def slaughterhouse():
    return render_template('user/license/livestock/slaughterhouse.html')

@bp.route('/poultry-farm')
@role_required('user')
def poultry_farm():
    return render_template('user/license/livestock/poultry-farm.html')

@bp.route('/animal-health')
@role_required('user')
def animal_health():
    return render_template('user/license/livestock/animal-health.html')

from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('seminar', __name__, url_prefix='/user/seminar')

@bp.route('/')
@role_required('user')
def seminar_list():
    return render_template('user/service/Seminar/seminar_list.html')

@bp.route('/gap/apply')
@role_required('user')
def gap_application():
    return render_template('user/service/Seminar/gap_application.html')

@bp.route('/pest-disease/apply')
@role_required('user')
def pest_disease_application():
    return render_template('user/service/Seminar/pest_disease_application.html')

@bp.route('/pesticide/apply')
@role_required('user')
def pesticide_application():
    return render_template('user/service/Seminar/pesticide_application.html')

@bp.route('/nursery/apply')
@role_required('user')
def nursery_application():
    return render_template('user/service/Seminar/nursery_application.html')

@bp.route('/regulatory/apply')
@role_required('user')
def regulatory_application():
    return render_template('user/service/Seminar/regulatory_application.html')

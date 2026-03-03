from flask import Blueprint, render_template, redirect, url_for
from firebase_auth_middleware import role_required

bp = Blueprint('seminar', __name__, url_prefix='/user/seminar')

@bp.route('/')
@role_required('user')
def seminar_list():
    """Shows the seminar & trainings landing page with all 5 seminar types"""
    return render_template('user/service/Seminar/seminar_list.html')

@bp.route('/gap/apply')
@role_required('user')
def gap_application():
    """GAP Training application form"""
    return render_template('user/service/Seminar/gap_application.html')

@bp.route('/pest-disease/apply')
@role_required('user')
def pest_disease_application():
    """Pest & Disease Management Seminar application form"""
    return render_template('user/service/Seminar/pest_disease_application.html')

@bp.route('/pesticide/apply')
@role_required('user')
def pesticide_application():
    """Safe Pesticide Handling Training application form"""
    return render_template('user/service/Seminar/pesticide_application.html')

@bp.route('/nursery/apply')
@role_required('user')
def nursery_application():
    """Nursery/Propagation Seminar application form"""
    return render_template('user/service/Seminar/nursery_application.html')

@bp.route('/regulatory/apply')
@role_required('user')
def regulatory_application():
    """Regulatory Compliance Orientation application form"""
    return render_template('user/service/Seminar/regulatory_application.html')

# Redirect /user/seminar/seminars → /user/seminar/ for legacy links
@bp.route('/seminars')
@role_required('user')
def seminar_redirect():
    return redirect(url_for('seminar.seminar_list'))

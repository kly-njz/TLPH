from flask import Blueprint, render_template
from firebase_auth_middleware import role_required

bp = Blueprint('forest', __name__, url_prefix='/user/license/forest')

@bp.route('/')
@role_required('user')
def forest_main():
    return render_template('user/license/forest/forest.html')

@bp.route('/tree-cutting')
@role_required('user')
def tree_cutting():
    return render_template('user/license/forest/tree.html')

@bp.route('/timber')
@role_required('user')
def timber():
    return render_template('user/license/forest/timber.html')

@bp.route('/reforestation')
@role_required('user')
def reforestation():
    return render_template('user/license/forest/reforestation.html')

@bp.route('/nursery')
@role_required('user')
def nursery():
    return render_template('user/license/forest/nursery.html')

@bp.route('/non-timber')
@role_required('user')
def non_timber():
    return render_template('user/license/forest/non-timber.html')

@bp.route('/tree-planting')
@role_required('user')
def tree_planting():
    return render_template('user/license/forest/tree-plantation.html')

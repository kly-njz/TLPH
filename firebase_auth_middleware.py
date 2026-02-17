from functools import wraps
from flask import request, jsonify, redirect, url_for, session

def firebase_auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session
        if 'user_email' not in session:
            return redirect(url_for('main.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_email' not in session:
                return redirect(url_for('main.login'))
            
            # Check user role
            user_role = session.get('user_role', '')
            
            if user_role not in allowed_roles:
                # Redirect to appropriate dashboard based on their actual role
                role_redirects = {
                    'user': '/user/dashboard',
                    'municipal': '/municipal/dashboard',
                    'municipal_admin': '/municipal/dashboard',
                    'regional': '/regional/profile',
                    'regional_admin': '/regional/profile',
                    'national': '/national/dashboard',
                    'national_admin': '/national/dashboard',
                    'super-admin': '/superadmin/inventory',
                    'superadmin': '/superadmin/inventory'
                }
                redirect_url = role_redirects.get(user_role, '/login')
                return redirect(redirect_url)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

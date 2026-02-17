from functools import wraps
from flask import request, jsonify, redirect, url_for, session

def firebase_auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session
        if 'user_email' not in session:
            print(f'❌ No session found for {f.__name__}, redirecting to login')
            return redirect(url_for('main.login'))
        
        print(f'✅ Session found for {f.__name__}: {session.get("user_email")}')
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_email' not in session:
                print(f'❌ No session found, redirecting to login')
                return redirect(url_for('main.login'))
            
            # Check user role
            user_role = session.get('user_role', '')
            
            if user_role not in allowed_roles:
                print(f'❌ Role mismatch: {user_role} not in {allowed_roles}, staying on current page')
                # Instead of redirecting to login, redirect back to their appropriate dashboard
                role_dashboards = {
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
                dashboard_url = role_dashboards.get(user_role, '/login')
                return redirect(dashboard_url)
            
            print(f'✅ Access granted: {user_role} accessing {f.__name__}')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

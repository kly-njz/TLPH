from functools import wraps
from flask import request, jsonify, redirect, url_for, session
import system_logs_storage
from datetime import datetime, timedelta
from firebase_config import get_firestore_db


def _detect_device_from_request():
    user_agent = request.headers.get('User-Agent', '')
    return system_logs_storage.detect_device_type(user_agent)


def _resolve_municipality_for_session():
    municipality = session.get('municipality') or session.get('user_municipality')
    if municipality and str(municipality).lower() not in ('unknown', 'municipality', ''):
        return municipality

    try:
        db = get_firestore_db()
        user_id = session.get('user_id')
        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    session['municipality'] = municipality
                    session['user_municipality'] = municipality
                    return municipality

        user_email = session.get('user_email')
        if user_email:
            docs = db.collection('users').where('email', '==', user_email).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    session['municipality'] = municipality
                    session['user_municipality'] = municipality
                    return municipality
    except Exception as e:
        print(f'⚠️ Could not resolve municipality for session: {e}')

    return 'unknown'

def firebase_auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session
        if 'user_email' not in session:
            print(f'❌ No session found for {f.__name__}, redirecting to login')
            response = redirect(url_for('main.login'))
            # Prevent caching to avoid flash of content
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        print(f'✅ Session found for {f.__name__}: {session.get("user_email")}')
        result = f(*args, **kwargs)
        
        # Add no-cache headers to protected pages
        if hasattr(result, 'headers'):
            result.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            result.headers['Pragma'] = 'no-cache'
        
        return result
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_email' not in session:
                print(f'❌ No session found, redirecting to login')
                response = redirect(url_for('main.login'))
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            
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
                response = redirect(dashboard_url)
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                return response

            # Log municipal page access (non-API GET routes)
            try:
                if (
                    user_role in ('municipal', 'municipal_admin')
                    and request.method == 'GET'
                    and request.path.startswith('/municipal')
                    and not request.path.startswith('/api')
                ):
                    now = datetime.utcnow()
                    throttle_minutes = 2
                    page_access_last_logged = session.get('page_access_last_logged', {})
                    last_logged_iso = page_access_last_logged.get(request.path)
                    should_log = True

                    if last_logged_iso:
                        try:
                            last_logged_at = datetime.fromisoformat(last_logged_iso)
                            if now - last_logged_at < timedelta(minutes=throttle_minutes):
                                should_log = False
                        except Exception:
                            should_log = True

                    if not should_log:
                        print(f'ℹ️ PAGE_ACCESS throttled for {request.path}')
                    else:
                        municipality = _resolve_municipality_for_session()
                        user_email = session.get('user_email', 'unknown')
                        user_agent = request.headers.get('User-Agent', '')

                        system_logs_storage.add_system_log(
                            municipality=municipality,
                            user=user_email,
                            action='PAGE_ACCESS',
                            target=request.path,
                            module='NAVIGATION',
                            outcome='SUCCESS',
                            message=f'Accessed page: {request.path}',
                            device_type=_detect_device_from_request(),
                            user_agent=user_agent,
                            metadata={
                                'method': request.method,
                                'endpoint': request.endpoint
                            }
                        )

                        page_access_last_logged[request.path] = now.isoformat()
                        session['page_access_last_logged'] = page_access_last_logged
            except Exception as e:
                print(f'⚠️ Failed to log PAGE_ACCESS: {e}')
            
            print(f'✅ Access granted: {user_role} accessing {f.__name__}')
            result = f(*args, **kwargs)
            
            # Add no-cache headers to protected pages
            if hasattr(result, 'headers'):
                result.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                result.headers['Pragma'] = 'no-cache'
            
            return result
        return decorated_function
    return decorator

from google.cloud.firestore_v1.base_query import FieldFilter
from flask import Blueprint, request, jsonify, session
from flask_mail import Message, Mail
from datetime import datetime
import random
import json
from urllib.request import urlopen
from urllib.parse import quote_plus
from firebase_auth_middleware import firebase_auth_required
import system_logs_storage


bp = Blueprint('api', __name__, url_prefix='/api')

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

MIMAROPA_REGION_NAMES = {'MIMAROPA', 'MIMAROPA REGION', 'REGION IV-B', 'REGION-IV-B'}
_MUNICIPALITY_CODE_CACHE = {}


def _normalize_muni_name(name: str) -> str:
    return ' '.join(str(name or '').strip().upper().replace('’', "'").replace('`', "'").split())


def _strip_city_muni_suffix(name: str) -> str:
    v = _normalize_muni_name(name)
    for suffix in (' CITY', ' MUNICIPALITY'):
        if v.endswith(suffix):
            v = v[: -len(suffix)].strip()
    return v


def _fetch_json(url: str):
    with urlopen(url, timeout=12) as resp:
        payload = resp.read().decode('utf-8')
        return json.loads(payload)


def _load_mimaropa_municipalities_from_firestore():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        for key in ('REGION-IV-B', 'MIMAROPA'):
            doc = db.collection('municipalities').document(key).get()
            if doc.exists:
                values = doc.to_dict().get('municipalities', []) or []
                cleaned = sorted({str(v).strip() for v in values if str(v).strip()})
                if cleaned:
                    return cleaned
    except Exception as e:
        print(f"[WARN] Failed loading Firestore MIMAROPA municipalities: {e}")
    return []


def _load_mimaropa_municipalities_from_psgc():
    try:
        rows = _fetch_json('https://psgc.gitlab.io/api/cities-municipalities/')
        mimaropa = []
        for row in rows:
            region_name = str(row.get('regionName') or '').strip().upper()
            if region_name not in MIMAROPA_REGION_NAMES:
                continue
            name = str(row.get('name') or '').strip()
            if not name:
                continue
            _MUNICIPALITY_CODE_CACHE[_normalize_muni_name(name)] = str(row.get('code') or '').strip()
            mimaropa.append(name)
        return sorted(set(mimaropa))
    except Exception as e:
        print(f"[WARN] PSGC municipalities fetch failed: {e}")
        return []


def _resolve_municipality_code(municipality_name: str):
    key = _normalize_muni_name(municipality_name)
    code = _MUNICIPALITY_CODE_CACHE.get(key)
    if code:
        return code

    try:
        rows = _fetch_json('https://psgc.gitlab.io/api/cities-municipalities/')
        candidate = None
        key_stripped = _strip_city_muni_suffix(key)
        for row in rows:
            name = str(row.get('name') or '').strip()
            code_val = str(row.get('code') or '').strip()
            if not name or not code_val:
                continue
            normalized = _normalize_muni_name(name)
            _MUNICIPALITY_CODE_CACHE[normalized] = code_val

            if normalized == key:
                candidate = code_val
                break
            if _strip_city_muni_suffix(normalized) == key_stripped:
                candidate = code_val

        return candidate
    except Exception as e:
        print(f"[WARN] PSGC municipality code lookup failed: {e}")
        return None


@bp.route('/locations/mimaropa/municipalities', methods=['GET'])
def get_mimaropa_municipalities():
    """Return MIMAROPA municipalities from Firestore, fallback to PSGC API."""
    municipalities = _load_mimaropa_municipalities_from_firestore()
    source = 'firestore'
    if not municipalities:
        municipalities = _load_mimaropa_municipalities_from_psgc()
        source = 'psgc'
    return jsonify({'success': True, 'municipalities': municipalities, 'source': source})


@bp.route('/locations/mimaropa/barangays', methods=['GET'])
def get_mimaropa_barangays():
    """Return real barangays for a municipality (PSGC API)."""
    municipality = (request.args.get('municipality') or '').strip()
    if not municipality:
        return jsonify({'success': False, 'error': 'municipality is required'}), 400

    muni_code = _resolve_municipality_code(municipality)
    if not muni_code:
        return jsonify({'success': True, 'barangays': [], 'municipality': municipality})

    try:
        url = f'https://psgc.gitlab.io/api/cities-municipalities/{quote_plus(muni_code)}/barangays/'
        rows = _fetch_json(url)
        barangays = sorted({str(row.get('name') or '').strip() for row in rows if str(row.get('name') or '').strip()})
        return jsonify({'success': True, 'barangays': barangays, 'municipality': municipality})
    except Exception as e:
        print(f"[WARN] PSGC barangay fetch failed for {municipality}: {e}")
        return jsonify({'success': True, 'barangays': [], 'municipality': municipality})

# ==================== HELPERS ====================

def detect_device_from_request():
    """Detect device type from request headers"""
    user_agent = request.headers.get('User-Agent', '')
    return system_logs_storage.detect_device_type(user_agent)

def _normalize_municipality(value: str) -> str:
    return ' '.join(str(value or '').strip().split())


def get_user_municipality(user_id: str = None, user_email: str = None) -> str:
    """Get municipality from user document in Firestore"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                # For regional admins, use 'regional' as municipality
                user_role = user_data.get('role', '')
                if user_role in ['regional', 'regional_admin']:
                    print(f"[DEBUG] get_user_municipality(user_id={user_id}) -> 'regional' (regional admin)")
                    return 'regional'
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    normalized = _normalize_municipality(municipality)
                    print(f"[DEBUG] get_user_municipality(user_id={user_id}) -> '{normalized}' (raw: '{municipality}')")
                    return normalized

        if user_email:
            docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                # For regional admins, use 'regional' as municipality
                user_role = user_data.get('role', '')
                if user_role in ['regional', 'regional_admin']:
                    print(f"[DEBUG] get_user_municipality(user_email={user_email}) -> 'regional' (regional admin)")
                    return 'regional'
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    normalized = _normalize_municipality(municipality)
                    print(f"[DEBUG] get_user_municipality(user_email={user_email}) -> '{normalized}' (raw: '{municipality}')")
                    return normalized

        print(f"[DEBUG] get_user_municipality - no municipality found for user_id={user_id}, user_email={user_email}")
        return 'unknown'
    except Exception as e:
        print(f'[ERROR] Getting user municipality: {e}')
        return 'unknown'

def get_user_region(user_id: str = None, user_email: str = None) -> str:
    """Get region from user document in Firestore"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                # Prioritize regionName (full name like MIMAROPA) over region code (like 4B)
                region = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                if region:
                    print(f"[DEBUG] get_user_region(user_id={user_id}) -> '{region}'")
                    return region

        if user_email:
            docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                # Prioritize regionName (full name like MIMAROPA) over region code (like 4B)
                region = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                if region:
                    print(f"[DEBUG] get_user_region(user_email={user_email}) -> '{region}'")
                    return region

        print(f"[DEBUG] get_user_region - no region found for user_id={user_id}, user_email={user_email}")
        return 'unknown'
    except Exception as e:
        print(f'[ERROR] Getting user region: {e}')
        return 'unknown'

# Store users temporarily (in production, use database)
users_db = {
    'municipal@gmail.com': {
        'password': '123456',
        'role': 'municipal',
        'data': {
            'firstName': 'Municipal',
            'lastName': 'Admin',
            'email': 'municipal@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Makati',
            'province': 'Metro Manila'
        }
    },
    'regional@gmail.com': {
        'password': '123456',
        'role': 'regional',
        'data': {
            'firstName': 'Regional',
            'lastName': 'Admin',
            'email': 'regional@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Regional',
            'province': 'National'
        }
    },
    'superadmin@gmail.com': {
        'password': '123456',
        'role': 'super-admin',
        'data': {
            'firstName': 'Super',
            'lastName': 'Admin',
            'email': 'superadmin@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Admin',
            'province': 'National'
        }
    },
    'national@gmail.com': {
        'password': '123456',
        'role': 'national',
        'data': {
            'firstName': 'National',
            'lastName': 'Admin',
            'email': 'national@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'National',
            'province': 'National'
        }
    }
}

# Mail instance will be initialized later
mail = None

def init_mail(mail_instance):
    global mail
    mail = mail_instance

@bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if mail is configured
        if not mail:
            return jsonify({
                'success': False, 
                'message': 'Email service not configured. Please contact administrator.'
            }), 500
        
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP (expires in 10 minutes)
        otp_storage[email] = otp
        
        # Send email
        msg = Message(
            subject='DENR TLPH - Email Verification Code',
            recipients=[email],
            body=f'''
Dear User,

Your verification code for DENR TLPH registration is: {otp}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
DENR TLPH Team
            '''
        )
        
        mail.send(msg)
        
        return jsonify({'success': True, 'message': 'OTP sent successfully'})
    
    except Exception as e:
        print(f'Error sending OTP: {str(e)}')
        return jsonify({'success': False, 'message': f'Failed to send OTP: {str(e)}'}), 500

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400
        
        # Check if OTP matches
        stored_otp = otp_storage.get(email)
        
        if not stored_otp:
            return jsonify({'success': False, 'message': 'OTP expired or not found'}), 400
        
        if stored_otp == otp:
            # Remove OTP after successful verification
            del otp_storage[email]
            return jsonify({'success': True, 'message': 'OTP verified successfully'})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    except Exception as e:
        print(f'Error verifying OTP: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('applicationType', 'user')  # Default to 'user'

        # Map application types to roles
        role_mapping = {
            'tenant': 'user',
            'cooperative': 'user',
            'agribusiness': 'user',
            'research': 'user',
            'municipal': 'municipal',
            'national': 'national',
            'regional': 'regional',
            'super-admin': 'super-admin'
        }

        user_role = role_mapping.get(role, 'user')
        
        # Get municipality from current user (if municipal user creating account)
        # or from request data, normalized for consistency
        municipality_scope = 'unknown'
        if session.get('user_role') == 'municipal' and session.get('user_email'):
            current_email = session.get('user_email')
            current_user = users_db.get(current_email)
            if current_user:
                municipality_scope = _normalize_municipality(current_user.get('data', {}).get('municipality', 'unknown'))
        
        if municipality_scope == 'unknown':
            municipality_scope = _normalize_municipality(
                data.get('municipality')
                or data.get('data', {}).get('municipality')
                or 'unknown'
            )

        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400

        # Only allow municipal users to add users with their own province/municipality
        if session.get('user_role') == 'municipal':
            current_user = users_db.get(session.get('user_email'))
            if not current_user:
                return jsonify({'success': False, 'message': 'Session user not found'}), 403
            # Overwrite province and municipality in data
            if 'data' not in data:
                data['data'] = {}
            data['province'] = current_user['data'].get('province', '')
            data['municipality'] = current_user['data'].get('municipality', '')
            data['data']['province'] = current_user['data'].get('province', '')
            data['data']['municipality'] = current_user['data'].get('municipality', '')

        # Check if user already exists
        if email in users_db:
            system_logs_storage.add_system_log(
                municipality=municipality_scope,
                user=session.get('user_email', email),
                action='CREATE_ACCOUNT_ATTEMPT',
                target='User Account',
                target_id=email,
                module='USER_MANAGEMENT',
                outcome='FAILED',
                message=f'Account creation failed: {email} already exists',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
            return jsonify({'success': False, 'message': 'User already exists'}), 400

        # Store user (in production, hash password and use database)
        users_db[email] = {
            'password': password,
            'role': user_role,
            'data': data
        }

        system_logs_storage.add_system_log(
            municipality=municipality_scope,
            user=session.get('user_email', email),
            action='CREATE_ACCOUNT',
            target='User Account',
            target_id=email,
            module='USER_MANAGEMENT',
            outcome='SUCCESS',
            message=f'Created account for {email} with role {user_role}',
            device_type=detect_device_from_request(),
            user_agent=request.headers.get('User-Agent', ''),
            metadata={
                'created_email': email,
                'created_role': user_role,
                'municipality': municipality_scope
            }
        )

        return jsonify({'success': True, 'message': 'Registration successful', 'role': user_role})

    except Exception as e:
        print(f'Error registering user: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        # Check if user exists
        user = users_db.get(email)
        
        if not user:
            # Log failed login attempt
            device_type = detect_device_from_request()
            user_agent = request.headers.get('User-Agent', '')
            request_ip = system_logs_storage.extract_request_ip(request)
            municipality = 'unknown'  # User not found, can't fetch municipality
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - user not found',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent
            )
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Verify password (in production, use proper password hashing)
        if user['password'] != password:
            # Log failed login attempt - get municipality from user data
            municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown'))
            device_type = detect_device_from_request()
            user_agent = request.headers.get('User-Agent', '')
            request_ip = system_logs_storage.extract_request_ip(request)
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - wrong password',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent
            )
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Get municipality from user data - normalize it for consistency
        municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown'))
        
        # Set session
        session['user_email'] = email
        session['user_role'] = user['role']
        session['municipality'] = municipality
        session['user_municipality'] = municipality
        session['province'] = user.get('data', {}).get('province', '')
        session['user_province'] = user.get('data', {}).get('province', '')
        
        # Log successful login with normalized municipality from user data
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=email,
            action='LOGIN',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {email} logged in successfully',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )
        
        # Determine redirect URL based on role
        redirect_urls = {
            'user': '/user/dashboard',
            'municipal': '/municipal/dashboard',
            'national': '/national/dashboard',
            'regional': '/regional/dashboard',
            'super-admin': '/super-admin/dashboard'
        }
        
        redirect_url = redirect_urls.get(user['role'], '/user/dashboard')
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'role': user['role'],
            'redirect': redirect_url
        })
    
    except Exception as e:
        print(f'Error logging in: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/set-session', methods=['POST'])
def set_session():
    """Set Flask session after Firebase authentication"""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        user_role = data.get('user_role')
        user_id = data.get('user_id')

        if not user_email or not user_role or not user_id:
            return jsonify({'success': False, 'message': 'Missing user_email, user_role, or user_id'}), 400

        # Set session
        session.permanent = True
        session['user_email'] = user_email
        session['user_role'] = user_role
        session['user_id'] = user_id

        # Get municipality from user document - always fetch from Firestore to ensure match
        municipality = get_user_municipality(user_id=user_id, user_email=user_email)
        session['municipality'] = municipality
        session['user_municipality'] = municipality

        # Get region from user document
        region = get_user_region(user_id=user_id, user_email=user_email)
        session['region'] = region
        session['user_region'] = region

        print(f'Session set for {user_email} with role {user_role} and user_id {user_id}')

        # Log successful login with municipality fetched from Firestore users collection
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=user_email,
            action='LOGIN',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {user_email} ({user_role}) logged in successfully via Firebase',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )

        if user_role in {'municipal', 'municipal_admin'}:
            print(f'[LOGIN_CAPTURE] Recording login event for {user_email} in municipality={municipality}, region={region}')
            system_logs_storage.add_regional_system_log(
                region=region,
                municipality=municipality,
                user=user_email,
                user_id=user_id,
                role=user_role,
                action='LOGIN',
                target='Authentication',
                target_id=user_id,
                module='AUTH',
                outcome='SUCCESS',
                message=f'Municipal admin {user_email} logged in.',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent,
                metadata={'source': 'set-session'}
            )
            print(f'[LOGIN_CAPTURE] ✅ Login event recorded successfully for {user_email}')

        return jsonify({'success': True, 'message': 'Session set successfully'})
    
    except Exception as e:
        print(f'Error setting session: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """Clear Flask session on logout"""
    try:
        # Capture user info before clearing session
        user_email = session.get('user_email', 'unknown')
        user_id = session.get('user_id')
        user_role = session.get('user_role', '')
        region = session.get('region') or session.get('user_region') or get_user_region(user_id=user_id, user_email=user_email)
        
        # Get fresh municipality from Firestore to ensure consistency
        municipality = get_user_municipality(user_id=user_id, user_email=user_email) if user_email != 'unknown' else 'unknown'
        
        # Log logout with fresh municipality from Firestore
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=user_email,
            action='LOGOUT',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {user_email} logged out',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )

        if user_role in {'municipal', 'municipal_admin'}:
            print(f'[LOGOUT_CAPTURE] Recording logout event for {user_email} in municipality={municipality}, region={region}')
            system_logs_storage.add_regional_system_log(
                region=region,
                municipality=municipality,
                user=user_email,
                user_id=user_id,
                role=user_role,
                action='LOGOUT',
                target='Authentication',
                target_id=user_id,
                module='AUTH',
                outcome='SUCCESS',
                message=f'Municipal admin {user_email} logged out.',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent,
                metadata={'source': 'logout'}
            )
            print(f'[LOGOUT_CAPTURE] ✅ Logout event recorded successfully for {user_email}')
        
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        print(f'Error logging out: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/check-session', methods=['GET'])
def check_session():
    """Quick session check for instant auth verification"""
    if 'user_email' in session:
        role = session.get('user_role', '')
        user_email = session.get('user_email', 'unknown')
        user_id = session.get('user_id')
        
        # Get fresh municipality from Firestore or users_db
        if user_email != 'unknown':
            # Try to get from Firestore first (Firebase users)
            if user_id:
                municipality = get_user_municipality(user_id=user_id, user_email=user_email)
            else:
                # Fall back to users_db (demo users)
                user = users_db.get(user_email)
                municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown')) if user else 'unknown'
        else:
            municipality = 'unknown'
        
        if role in ['municipal', 'municipal_admin']:
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=user_email,
                action='SESSION_CHECK',
                target='Session',
                module='AUTH',
                outcome='SUCCESS',
                message='Municipal session validated',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        return jsonify({
            'authenticated': True,
            'role': role,
            'email': user_email
        })
    return jsonify({'authenticated': False}), 401

@bp.route('/upload-profile-photo', methods=['POST'])
@firebase_auth_required
def upload_profile_photo():
    """Upload profile photo to server and return the URL"""
    try:
        import os
        from werkzeug.utils import secure_filename

        user_id = session.get('user_id') or request.form.get('userId')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401

        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        upload_dir = os.path.join('static', 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)

        # Use uid as filename so each user has one photo (overwrites old one)
        filename = f"{user_id}.{ext}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        photo_url = f"/static/uploads/profiles/{filename}"
        return jsonify({'success': True, 'photoURL': photo_url})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/upload-inventory-image', methods=['POST'])
def upload_inventory_image():
    """Upload inventory image/permit to server filesystem (no Firebase Storage CORS issues)"""
    try:
        import os
        from werkzeug.utils import secure_filename

        user_id = request.form.get('userId', 'unknown')
        file_type = request.form.get('fileType', 'image')  # 'image' or 'permit'

        file_key = 'image' if file_type == 'image' else 'permit'
        if file_key not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files[file_key]
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            return jsonify({'success': False, 'error': f'Invalid file type: {ext}'}), 400

        upload_dir = os.path.join('static', 'uploads', 'inventory', user_id)
        os.makedirs(upload_dir, exist_ok=True)

        import time
        filename = f"{file_type}_{int(time.time())}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        url = f"/static/uploads/inventory/{user_id}/{filename}"
        return jsonify({'success': True, 'url': url})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/submit-application', methods=['POST'])
@firebase_auth_required
def submit_application():
    """Handle application submission with file uploads"""
    try:
        import os
        from werkzeug.utils import secure_filename
        
        # Get form data
        user_id = request.form.get('userId')
        user_email = request.form.get('userEmail')
        category = request.form.get('category')
        investment_qty = request.form.get('investmentQty')
        harvest_qty = request.form.get('harvestQty')
        
        # Validate required fields
        if not all([user_id, user_email, category, investment_qty, harvest_qty]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Create upload directory
        upload_dir = os.path.join('static', 'uploads', 'applications', user_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Process file uploads
        file_fields = ['titleFile', 'taxFile', 'blueprintFile', 'landFile', 'cropFile', 'planFile', 'brgyFile']
        file_paths = {}
        
        for field in file_fields:
            if field in request.files:
                file = request.files[field]
                if file and file.filename:
                    # Secure filename
                    filename = secure_filename(file.filename)
                    timestamp = int(datetime.now().timestamp())
                    unique_filename = f"{timestamp}_{field}_{filename}"
                    
                    # Save file
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    
                    # Store relative path for web access
                    web_path = f"/static/uploads/applications/{user_id}/{unique_filename}"
                    file_paths[field.replace('File', '')] = web_path
        
        return jsonify({
            'success': True,
            'message': 'Files uploaded successfully',
            'filePaths': file_paths
        })
        
    except Exception as e:
        print(f'Error submitting application: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Failed to submit application: {str(e)}'
        }), 500

@bp.route('/get-applications/<user_id>', methods=['GET'])
@firebase_auth_required
def get_user_applications(user_id):
    """Get all applications for a specific user"""
    try:
        # This is a placeholder - actual data is fetched from Firestore on frontend
        return jsonify({
            'success': True,
            'message': 'Fetch applications from Firestore on the frontend'
        })
    except Exception as e:
        print(f'Error fetching applications: {str(e)}')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== SUPERADMIN APPLICATION REGISTRY ====================

def _sa_norm_text(value, fallback='N/A'):
    text = str(value or '').strip()
    return text if text else fallback


def _sa_to_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    if hasattr(value, 'to_datetime'):
        try:
            return value.to_datetime()
        except Exception:
            return None
    if hasattr(value, 'strftime'):
        return value
    return None


def _sa_region_from_province(province_name):
    prov = str(province_name or '').strip().lower()
    if not prov:
        return ''
    try:
        from models.region_province_map import region_province_map
        for region, provinces in (region_province_map or {}).items():
            for p in (provinces or []):
                if str(p or '').strip().lower() == prov:
                    return region
    except Exception:
        return ''
    return ''


def _sa_category_from_app_type(application_type):
    app_type = str(application_type or '').strip().lower()
    if any(k in app_type for k in ['farm', 'crop', 'soil', 'pest', 'fertilizer', 'chemical']):
        return 'Farming'
    if any(k in app_type for k in ['fish', 'fisher', 'marine', 'aqua']):
        return 'Fisheries'
    if any(k in app_type for k in ['livestock', 'animal', 'poultry']):
        return 'Livestock'
    if any(k in app_type for k in ['forest', 'timber', 'tree']):
        return 'Forestry'
    if any(k in app_type for k in ['wildlife', 'fauna', 'protected']):
        return 'Wildlife'
    if any(k in app_type for k in ['environment', 'compliance', 'impact', 'waste']):
        return 'Environment'
    return 'General'


def _sa_sector_label(value):
    raw = str(value or '').strip()
    key = raw.lower()
    mapping = {
        'farming': 'Crop & Plant',
        'livestock': 'Fisheries & Agriculture',
        'agribusiness': 'Agribusiness & Agro-Processing',
        'trade': 'Agricultural Trade',
        'infrastructure': 'Infrastructure',
    }
    return mapping.get(key, raw if raw else 'General')


def _sa_status_payload(data):
    status = str(data.get('status') or 'pending').strip().lower()
    regional_status = str(data.get('regionalStatus') or '').strip().lower()
    national_status = str(data.get('nationalStatus') or '').strip().lower()

    approved_by_level = str(data.get('approvedByLevel') or '').strip()
    rejected_by_level = str(data.get('rejectedByLevel') or '').strip()
    forwarded_to_level = str(data.get('forwardedToLevel') or '').strip()
    forwarded_by_level = str(data.get('forwardedByLevel') or '').strip()

    def _norm_level(v):
        lv = str(v or '').strip().lower()
        if lv == 'national':
            return 'National'
        if lv == 'regional':
            return 'Regional'
        if lv == 'municipal':
            return 'Municipal'
        return str(v or '').strip()

    def _infer_forward_target():
        raw = _norm_level(forwarded_to_level)
        if raw:
            return raw
        if 'national' in status or national_status:
            return 'National'
        if 'regional' in status or regional_status or status in {'to review', 'to-review', 'review'}:
            return 'Regional'
        return 'Regional'

    resolved_forwarded_to = _infer_forward_target()

    if national_status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if national_status in {'cancelled', 'canceled'} else national_status
    elif status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if status in {'cancelled', 'canceled'} else status
    elif status in {'to review', 'to-review', 'review'} or regional_status in {'to review', 'to-review', 'review'}:
        effective_status = 'to review'
    elif status.startswith('forwarded') or forwarded_to_level:
        effective_status = 'forwarded'
    else:
        effective_status = 'pending'

    def _resolve_approved_level():
        # Source of truth: explicit workflow actor level saved in document.
        if _norm_level(approved_by_level):
            return _norm_level(approved_by_level)
        if national_status == 'approved':
            return 'National'
        if regional_status == 'approved':
            return 'Regional'
        if resolved_forwarded_to == 'National':
            return 'National'
        if resolved_forwarded_to == 'Regional':
            return 'Regional'
        return 'Municipal'

    def _resolve_rejected_level():
        # Source of truth: explicit workflow actor level saved in document.
        if _norm_level(rejected_by_level):
            return _norm_level(rejected_by_level)
        if national_status == 'rejected':
            return 'National'
        if regional_status == 'rejected':
            return 'Regional'
        if resolved_forwarded_to == 'National':
            return 'National'
        if resolved_forwarded_to == 'Regional':
            return 'Regional'
        return 'Municipal'

    if effective_status == 'approved':
        origin = _resolve_approved_level()
        status_display = f'Approved by {origin}'
    elif effective_status == 'rejected':
        origin = _resolve_rejected_level()
        status_display = f'Rejected by {origin}'
    elif effective_status == 'cancelled':
        origin = rejected_by_level or approved_by_level or 'Applicant/System'
        status_display = f'Cancelled ({origin})'
    elif effective_status == 'forwarded':
        target = resolved_forwarded_to
        origin = _norm_level(forwarded_by_level) or ('Regional' if target == 'National' else 'Municipal')
        status_display = f'Forwarded by {origin} to {target}'
    elif effective_status == 'to review':
        status_display = 'For Review'
    else:
        status_display = 'Pending'

    return {
        'status': effective_status,
        'status_display': status_display,
        'status_origin': {
            'approvedByLevel': approved_by_level,
            'rejectedByLevel': rejected_by_level,
            'forwardedByLevel': forwarded_by_level,
            'forwardedToLevel': forwarded_to_level,
            'resolvedApprovedByLevel': _resolve_approved_level(),
            'resolvedRejectedByLevel': _resolve_rejected_level(),
            'resolvedForwardedByLevel': _norm_level(forwarded_by_level) or ('Regional' if resolved_forwarded_to == 'National' else 'Municipal'),
            'resolvedForwardedToLevel': resolved_forwarded_to,
            'regionalStatus': regional_status,
            'nationalStatus': national_status,
            'rawStatus': status
        }
    }


def _sa_extract_application(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('dateFiled') or data.get('date_filed') or data.get('submittedAt'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    application_type = _sa_norm_text(data.get('applicationType') or form_data.get('applicationType'), 'General')
    raw_sector = (
        data.get('categoryType')
        or data.get('category')
        or data.get('applicantCategory')
        or data.get('sector')
        or form_data.get('categoryType')
        or form_data.get('category')
        or form_data.get('sector')
        or 'General'
    )
    sector = _sa_sector_label(raw_sector)

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    status_payload = _sa_status_payload(data)

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'sector': sector,
        'application_type': application_type,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status_payload['status'],
        'status_display': status_payload['status_display'],
        'status_origin': status_payload['status_origin'],
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(data.get('contact') or data.get('contactNumber') or user_data.get('contactNumber')),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data
    }

@bp.route('/superadmin/applications', methods=['GET'])
def superadmin_get_applications():
    """Return all applications for superadmin master registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]
        apps.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': apps, 'total': len(apps)})

    except Exception as e:
        print(f'[ERROR] superadmin_get_applications: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/stats', methods=['GET'])
def superadmin_application_stats():
    """Return KPI stats for superadmin application registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]

        total = 0
        pending = 0
        approved = 0
        rejected = 0
        to_review = 0
        cancelled = 0

        for app in apps:
            total += 1
            effective = app.get('status', 'pending')

            if effective in ['approved']:
                approved += 1
            elif effective in ['rejected']:
                rejected += 1
            elif effective in ['cancelled']:
                cancelled += 1
            elif effective in ['to review', 'review']:
                to_review += 1
            else:
                pending += 1

        approval_rate = round((approved / total * 100), 1) if total > 0 else 0

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'to_review': to_review,
                'cancelled': cancelled,
                'approval_rate': approval_rate,
            }
        })

    except Exception as e:
        print(f'[ERROR] superadmin_application_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/charts', methods=['GET'])
def superadmin_application_charts():
    """Return chart data for superadmin application registry"""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import calendar
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]

        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        category_count = defaultdict(int)
        weekly_trend = defaultdict(int)

        for app in apps:
            created_at = _sa_to_datetime(app.get('date_iso'))
            if created_at:
                monthly_trend[created_at.strftime('%Y-%m')] += 1
                iso = created_at.isocalendar()
                weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1

            region = str(app.get('region') or '').strip()
            if region and region.upper() != 'N/A':
                region_count[region] += 1

            category = str(app.get('sector') or 'General').strip()
            category_count[category] += 1

        # Last 8 weeks (week-by-week) trend
        now = datetime.now()
        week_labels = []
        week_data = []

        for i in range(7, -1, -1):
            target = now - dt_module.timedelta(weeks=i)
            iso = target.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            week_labels.append(f"W{iso[1]}")
            week_data.append(weekly_trend.get(key, 0))

        # Monthly fallback labels too
        last_6_months = []
        monthly_data = []
        for i in range(5, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            key = f"{target_year}-{target_month:02d}"
            last_6_months.append(calendar.month_abbr[target_month])
            monthly_data.append(monthly_trend.get(key, 0))

        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:7]
        top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'trend': {'labels': week_labels, 'data': week_data},
            'monthly': {'labels': last_6_months, 'data': monthly_data},
            'regions': {
                'labels': [r[0] for r in top_regions],
                'data': [r[1] for r in top_regions],
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })

    except Exception as e:
        print(f'[ERROR] superadmin_application_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/audit-trail', methods=['GET'])
def superadmin_application_audit():
    """Return recent audit trail entries for application registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = db.collection('applications') \
                 .order_by('createdAt', direction='DESCENDING') \
                 .limit(10) \
                 .stream()

        docs = list(docs)
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        entries = []
        for doc in docs:
            app = _sa_extract_application(doc, users_map)
            created_at = _sa_to_datetime(app.get('date_iso'))
            time_str = created_at.strftime('%H:%M') if created_at else '--:--'

            entries.append({
                'time': time_str,
                'ref': app.get('ref', doc.id[:8].upper()),
                'name': app.get('name', 'N/A'),
                'status': app.get('status', 'pending'),
                'status_display': app.get('status_display', 'Pending')
            })

        return jsonify(entries)

    except Exception as e:
        print(f'[ERROR] superadmin_application_audit: {e}')
        # Fallback: get latest without ordering
        try:
            from firebase_config import get_firestore_db
            db = get_firestore_db()
            docs = db.collection('applications').limit(10).stream()
            entries = []
            for doc in docs:
                data = doc.to_dict() or {}
                status = (data.get('status') or 'pending').lower()
                name = (data.get('applicantName') or data.get('fullName') or doc.id[:8].upper())
                entries.append({'time': '--:--', 'ref': doc.id[:8].upper(), 'name': name, 'status': status})
            return jsonify(entries)
        except Exception as e2:
            return jsonify({'success': False, 'message': str(e2)}), 500


@bp.route('/superadmin/applications/<application_id>', methods=['GET'])
def superadmin_get_application_detail(application_id):
    """Return complete and normalized details for one application (superadmin view modal)."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        app_doc = db.collection('applications').document(application_id).get()
        if not app_doc.exists:
            return jsonify({'success': False, 'message': 'Application not found'}), 404

        data = app_doc.to_dict() or {}
        user_id = data.get('userId')
        users_map = {}
        if user_id:
            try:
                u_doc = db.collection('users').document(user_id).get()
                if u_doc.exists:
                    users_map[user_id] = u_doc.to_dict() or {}
            except Exception:
                pass

        app = _sa_extract_application(app_doc, users_map)
        return jsonify({'success': True, 'data': app})
    except Exception as e:
        print(f'[ERROR] superadmin_get_application_detail: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SUPERADMIN SERVICE REQUEST REGISTRY ====================

def _sa_sr_status_payload(data):
    status = str(data.get('status') or 'pending').strip().lower()
    regional_status = str(data.get('regionalStatus') or '').strip().lower()
    national_status = str(data.get('nationalStatus') or '').strip().lower()

    approved_by_level = str(data.get('approvedByLevel') or '').strip()
    rejected_by_level = str(data.get('rejectedByLevel') or '').strip()
    forwarded_by_level = str(data.get('forwardedByLevel') or data.get('forwardedToNationalByLevel') or '').strip()
    forwarded_to_level = str(data.get('forwardedToLevel') or '').strip()

    def _norm_level(v):
        lv = str(v or '').strip().lower()
        if lv == 'national':
            return 'National'
        if lv == 'regional':
            return 'Regional'
        if lv == 'municipal':
            return 'Municipal'
        return str(v or '').strip()

    def _infer_forward_target():
        raw = _norm_level(forwarded_to_level)
        if raw:
            return raw
        if 'national' in status or national_status:
            return 'National'
        if 'regional' in status or regional_status or status in {'to review', 'to-review', 'review'}:
            return 'Regional'
        return 'Regional'

    resolved_forward_target = _infer_forward_target()

    if national_status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if national_status in {'cancelled', 'canceled'} else national_status
    elif status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if status in {'cancelled', 'canceled'} else status
    elif status in {'to review', 'to-review', 'review'} or regional_status in {'to review', 'to-review', 'review'}:
        effective_status = 'to review'
    elif status.startswith('forwarded') or forwarded_to_level:
        effective_status = 'forwarded'
    else:
        effective_status = 'pending'

    def _resolve_approved_level():
        if _norm_level(approved_by_level):
            return _norm_level(approved_by_level)
        if national_status == 'approved':
            return 'National'
        if regional_status == 'approved':
            return 'Regional'
        if resolved_forward_target == 'National':
            return 'National'
        if resolved_forward_target == 'Regional':
            return 'Regional'
        return 'Municipal'

    def _resolve_rejected_level():
        if _norm_level(rejected_by_level):
            return _norm_level(rejected_by_level)
        if national_status == 'rejected':
            return 'National'
        if regional_status == 'rejected':
            return 'Regional'
        if resolved_forward_target == 'National':
            return 'National'
        if resolved_forward_target == 'Regional':
            return 'Regional'
        return 'Municipal'

    resolved_forwarded_by = _norm_level(forwarded_by_level) or ('Regional' if resolved_forward_target == 'National' else 'Municipal')

    pending_target = resolved_forward_target or ('National' if national_status else 'Regional')

    if effective_status == 'approved':
        status_display = f"Approved by {_resolve_approved_level()}"
    elif effective_status == 'rejected':
        status_display = f"Rejected by {_resolve_rejected_level()}"
    elif effective_status == 'cancelled':
        status_display = f"Cancelled ({rejected_by_level or approved_by_level or 'Applicant/System'})"
    elif effective_status == 'forwarded':
        status_display = f"Forwarded by {resolved_forwarded_by} to {resolved_forward_target}"
    elif effective_status == 'to review':
        status_display = f"For Review at {pending_target}"
    else:
        status_display = f"Pending at {pending_target}"

    return {
        'status': effective_status,
        'status_display': status_display,
        'status_origin': {
            'approvedByLevel': approved_by_level,
            'rejectedByLevel': rejected_by_level,
            'forwardedByLevel': forwarded_by_level,
            'forwardedToLevel': forwarded_to_level,
            'resolvedApprovedByLevel': _resolve_approved_level(),
            'resolvedRejectedByLevel': _resolve_rejected_level(),
            'resolvedForwardedByLevel': resolved_forwarded_by,
            'resolvedForwardedToLevel': resolved_forward_target,
            'regionalStatus': regional_status,
            'nationalStatus': national_status,
            'rawStatus': status,
        }
    }


def _sa_extract_service_request(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('submittedAt') or data.get('dateFiled') or data.get('date_filed'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    category = _sa_norm_text(
        data.get('categoryType')
        or data.get('category')
        or data.get('serviceType')
        or data.get('serviceCategory')
        or data.get('requestType')
        or form_data.get('categoryType')
        or form_data.get('category')
        or form_data.get('serviceType')
        or form_data.get('serviceCategory')
        or form_data.get('requestType'),
        'General'
    )

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or data.get('userName')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    status_payload = _sa_sr_status_payload(data)

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'category': category,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status_payload['status'],
        'status_display': status_payload['status_display'],
        'status_actor_level': (
            status_payload['status_origin'].get('resolvedApprovedByLevel')
            if status_payload['status'] == 'approved'
            else status_payload['status_origin'].get('resolvedRejectedByLevel')
            if status_payload['status'] == 'rejected'
            else status_payload['status_origin'].get('resolvedForwardedByLevel')
            if status_payload['status'] == 'forwarded'
            else None
        ),
        'status_target_level': (
            status_payload['status_origin'].get('resolvedForwardedToLevel')
            if status_payload['status'] in {'pending', 'to review', 'forwarded'}
            else None
        ),
        'status_origin': status_payload['status_origin'],
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(data.get('contact') or data.get('contactNumber') or user_data.get('contactNumber')),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data,
    }


@bp.route('/superadmin/service-requests', methods=['GET'])
def superadmin_get_service_requests():
    """Return all service requests for superadmin registry across all municipalities/regions."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]
        rows.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': rows, 'requests': rows, 'total': len(rows)})
    except Exception as e:
        print(f'[ERROR] superadmin_get_service_requests: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/stats', methods=['GET'])
def superadmin_service_request_stats():
    """Return KPI counts for superadmin service request registry."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]

        stats = {
            'total': len(rows),
            'pending': 0,
            'for_review': 0,
            'approved': 0,
            'rejected': 0,
            'cancelled': 0,
        }

        for row in rows:
            st = str(row.get('status') or 'pending').lower()
            if st == 'approved':
                stats['approved'] += 1
            elif st == 'rejected':
                stats['rejected'] += 1
            elif st == 'cancelled':
                stats['cancelled'] += 1
            elif st in {'to review', 'review', 'forwarded'}:
                stats['for_review'] += 1
            else:
                stats['pending'] += 1

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/charts', methods=['GET'])
def superadmin_service_request_charts():
    """Return trend + category chart data for superadmin service request registry."""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]

        weekly_trend = defaultdict(int)
        category_count = defaultdict(int)

        for row in rows:
            dt = _sa_to_datetime(row.get('date_iso'))
            if dt:
                iso = dt.isocalendar()
                weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1
            category_count[str(row.get('category') or 'General')] += 1

        now = datetime.now()
        week_labels = []
        week_data = []
        for i in range(7, -1, -1):
            target = now - dt_module.timedelta(weeks=i)
            iso = target.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            week_labels.append(f"W{iso[1]}")
            week_data.append(weekly_trend.get(key, 0))

        top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'trend': {
                'labels': week_labels,
                'data': week_data,
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/audit-trail', methods=['GET'])
def superadmin_service_request_audit():
    """Return latest service request actions for live audit panel."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(20).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]
        rows.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        entries = []
        for row in rows[:10]:
            dt = _sa_to_datetime(row.get('date_iso'))
            entries.append({
                'time': dt.strftime('%H:%M') if dt else '--:--',
                'ref': row.get('ref', 'N/A'),
                'name': row.get('name', 'N/A'),
                'status': row.get('status', 'pending'),
                'status_display': row.get('status_display', 'Pending')
            })

        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_audit: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SUPERADMIN LICENSE & PERMIT REGISTRY ====================

def _sa_extract_permit_application(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('dateFiled') or data.get('date_filed') or data.get('submittedAt'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or user_data.get('Province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    application_type = _sa_norm_text(data.get('applicationType') or form_data.get('applicationType'), 'General')
    category = _sa_norm_text(
        data.get('categoryType')
        or data.get('category')
        or form_data.get('categoryType')
        or form_data.get('category')
        or application_type,
        'General'
    )

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    status_payload = _sa_status_payload(data)
    status = status_payload['status']
    status_origin = status_payload['status_origin']

    status_actor_level = (
        status_origin.get('resolvedApprovedByLevel') if status == 'approved'
        else status_origin.get('resolvedRejectedByLevel') if status == 'rejected'
        else status_origin.get('resolvedForwardedByLevel') if status == 'forwarded'
        else None
    )
    status_target_level = status_origin.get('resolvedForwardedToLevel') if status in {'pending', 'to review', 'forwarded'} else None

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'category': category,
        'application_type': application_type,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status,
        'status_display': status_payload['status_display'],
        'status_actor_level': status_actor_level,
        'status_target_level': status_target_level,
        'status_origin': status_origin,
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(data.get('contact') or data.get('contactNumber') or user_data.get('contactNumber')),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data,
    }


@bp.route('/superadmin/permits', methods=['GET'])
def superadmin_get_permits():
    """Return all license/permit applications across municipalities and regions for superadmin."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        permits = [_sa_extract_permit_application(doc, users_map) for doc in docs]
        permits.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': permits, 'permits': permits, 'total': len(permits)})
    except Exception as e:
        print(f'[ERROR] superadmin_get_permits: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/permits/stats', methods=['GET'])
def superadmin_permits_stats():
    """Return KPI stats for superadmin permits/license registry."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_permit_application(doc, users_map) for doc in docs]
        stats = {
            'total': len(rows),
            'approved': 0,
            'rejected': 0,
            'pending': 0,
            'for_review': 0,
            'forwarded': 0,
            'cancelled': 0,
        }

        for row in rows:
            st = str(row.get('status') or 'pending').lower()
            if st == 'approved':
                stats['approved'] += 1
            elif st == 'rejected':
                stats['rejected'] += 1
            elif st == 'cancelled':
                stats['cancelled'] += 1
            elif st == 'forwarded':
                stats['forwarded'] += 1
            elif st in {'to review', 'review'}:
                stats['for_review'] += 1
            else:
                stats['pending'] += 1

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f'[ERROR] superadmin_permits_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/permits/charts', methods=['GET'])
def superadmin_permits_charts():
    """Return chart data for superadmin permits/license dashboard."""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_permit_application(doc, users_map) for doc in docs]

        month_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for row in rows:
            dt = _sa_to_datetime(row.get('date_iso'))
            if dt:
                month_counts[dt.strftime('%Y-%m')] += 1
            category_counts[str(row.get('category') or 'General')] += 1

        now = datetime.now()
        month_labels = []
        month_data = []
        for i in range(5, -1, -1):
            target = now - dt_module.timedelta(days=30 * i)
            key = target.strftime('%Y-%m')
            month_labels.append(target.strftime('%b'))
            month_data.append(month_counts.get(key, 0))

        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'issuance': {
                'labels': month_labels,
                'data': month_data,
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })
    except Exception as e:
        print(f'[ERROR] superadmin_permits_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== PROJECT MANAGEMENT ====================

@bp.route('/projects/create', methods=['POST'])
def create_project():
    """
    Create a new project based on admin role
    National: Direct creation (auto-approved, visible to all)
    Regional: Pending national approval (visible to region)
    Municipal: Pending regional review (visible to municipality and regional)
    """
    try:
        import projects_storage
        from firebase_admin import auth as firebase_auth
        
        data = request.get_json() or {}
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if not user_role or not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Validate required fields
        name = (data.get('name') or '').strip()
        description = (data.get('description') or '').strip()
        region = (data.get('region') or '').strip()
        municipality = (data.get('municipality') or '').strip()
        barangay = (data.get('barangay') or '').strip()
        start_date = (data.get('start_date') or '').strip()
        
        if not all([name, region, municipality, start_date]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Create based on role
        if user_role == 'national':
            result = projects_storage.create_project_national(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        elif user_role == 'regional':
            result = projects_storage.create_project_regional(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        elif user_role in ['municipal', 'municipal_admin']:
            result = projects_storage.create_project_municipal(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        else:
            return jsonify({'success': False, 'error': 'Unauthorized role'}), 403
        
        if result['success']:
            # Add to system logs
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=user_email,
                action='PROJECT_CREATED',
                target='Projects',
                target_id=result.get('project_id', 'n/a'),
                module='PROJECTS',
                outcome='SUCCESS',
                message=f'Project "{name}" created by {user_role}',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f'[PROJECT_ERROR] create_project failed: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/approve/<project_id>', methods=['POST'])
def approve_project(project_id):
    """
    Approve a project (national admin only)
    Moves pending_national_approval → active
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'national':
            return jsonify({'success': False, 'error': 'Only National Admin can approve'}), 403
        
        data = request.get_json() or {}
        notes = (data.get('notes') or '').strip()
        
        result = projects_storage.approve_project_national(
            project_id=project_id,
            reviewer_email=user_email,
            notes=notes
        )
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='National',
                user=user_email,
                action='PROJECT_APPROVED',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message='Project approved by National Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] approve_project failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/reject/<project_id>', methods=['POST'])
def reject_project(project_id):
    """
    Reject a project (national admin only)
    Moves to rejected status
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'national':
            return jsonify({'success': False, 'error': 'Only National Admin can reject'}), 403
        
        data = request.get_json() or {}
        notes = (data.get('notes') or '').strip()
        
        result = projects_storage.reject_project_national(
            project_id=project_id,
            reviewer_email=user_email,
            notes=notes
        )
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='National',
                user=user_email,
                action='PROJECT_REJECTED',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message='Project rejected by National Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] reject_project failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/review-regional/<project_id>', methods=['POST'])
def review_project_regional(project_id):
    """
    Regional admin reviews/approves a municipal project
    Moves pending_regional_approval → pending_national_approval
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'regional':
            return jsonify({'success': False, 'error': 'Only Regional Admin can review regionally'}), 403
        
        data = request.get_json() or {}
        action = (data.get('action') or '').strip().lower()
        notes = (data.get('notes') or '').strip()
        
        if action == 'approve':
            result = projects_storage.approve_project_regional(
                project_id=project_id,
                reviewer_email=user_email,
                notes=notes
            )
        elif action == 'reject':
            result = projects_storage.reject_project_regional(
                project_id=project_id,
                reviewer_email=user_email,
                notes=notes
            )
        else:
            return jsonify({'success': False, 'error': 'Invalid action. Use approve or reject'}), 400
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='Regional',
                user=user_email,
                action=f'PROJECT_{action.upper()}_REGIONAL',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message=f'Project {action} by Regional Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] review_project_regional failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/list', methods=['GET'])
def list_projects():
    """
    Get projects based on user role
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_region = session.get('user_region', '')
        user_municipality = session.get('user_municipality', '')
        
        if not user_role:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if user_role == 'national':
            projects = projects_storage.get_projects_national()
        elif user_role == 'regional':
            projects = projects_storage.get_projects_regional(user_region)
        elif user_role in ['municipal', 'municipal_admin']:
            projects = projects_storage.get_projects_municipal(user_municipality, user_region)
        else:
            projects = []
        
        return jsonify({'success': True, 'projects': projects})
        
    except Exception as e:
        print(f'[PROJECT_ERROR] list_projects failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/pending-approval', methods=['GET'])
def get_projects_pending_approval():
    """
    Get projects pending approval for current user's role
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_region = session.get('user_region', '')
        
        if not user_role:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if user_role == 'regional':
            projects = projects_storage.get_projects_for_approval('regional', user_region)
        elif user_role == 'national':
            projects = projects_storage.get_projects_for_approval('national')
        else:
            projects = []
        
        return jsonify({'success': True, 'pending_projects': projects})
        
    except Exception as e:
        print(f'[PROJECT_ERROR] get_projects_pending_approval failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

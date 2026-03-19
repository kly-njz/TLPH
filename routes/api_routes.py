from flask import Blueprint, request, jsonify, session
from flask_mail import Message, Mail
from datetime import datetime
import random
from firebase_auth_middleware import firebase_auth_required
import system_logs_storage
from google.cloud.firestore_v1.base_query import FieldFilter

bp = Blueprint('api', __name__, url_prefix='/api')

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

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
            municipality = 'unknown'  # User not found, can't fetch municipality
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - user not found',
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
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - wrong password',
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
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=email,
            action='LOGIN',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {email} logged in successfully',
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

@bp.route('/superadmin/applications', methods=['GET'])
def superadmin_get_applications():
    """Return all applications for superadmin master registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = db.collection('applications').limit(5000).stream()

        apps = []
        for doc in docs:
            data = doc.to_dict() or {}
            created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed') or ''
            date_filed = ''
            if created_at:
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime as dt
                        date_filed = dt.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except Exception:
                        date_filed = str(created_at)[:10]
                elif hasattr(created_at, 'strftime'):
                    date_filed = created_at.strftime('%Y-%m-%d')

            status = (data.get('status') or 'pending').lower()
            national_status = (data.get('nationalStatus') or '').lower()
            display_status = national_status if national_status else status

            category = (data.get('category') or data.get('applicantCategory') or 'General').strip()
            region = (data.get('region') or data.get('regionName') or 'N/A').strip()
            municipality = (data.get('municipality') or 'N/A').strip()

            apps.append({
                'id': doc.id,
                'ref': doc.id[:12].upper(),
                'date': date_filed,
                'name': (data.get('applicantName') or data.get('fullName') or data.get('name') or 'N/A').strip(),
                'sector': category,
                'region': region,
                'municipality': municipality,
                'status': display_status,
                'regional_status': status,
            })

        apps.sort(key=lambda x: x['date'], reverse=True)

        return jsonify({'success': True, 'data': apps, 'total': len(apps)})

    except Exception as e:
        print(f'[ERROR] superadmin_get_applications: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/stats', methods=['GET'])
def superadmin_application_stats():
    """Return KPI stats for superadmin application registry"""
    try:
        from firebase_config import get_firestore_db
        from datetime import datetime as dt
        db = get_firestore_db()

        docs = db.collection('applications').limit(5000).stream()

        total = 0
        pending = 0
        approved = 0
        rejected = 0
        to_review = 0

        for doc in docs:
            data = doc.to_dict() or {}
            total += 1
            national_status = (data.get('nationalStatus') or '').lower()
            status = (data.get('status') or 'pending').lower()
            effective = national_status if national_status else status

            if effective in ['approved']:
                approved += 1
            elif effective in ['rejected']:
                rejected += 1
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
        from datetime import datetime as dt
        from collections import defaultdict
        import calendar
        db = get_firestore_db()

        docs = db.collection('applications').limit(5000).stream()

        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        category_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict() or {}
            created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed')
            if created_at:
                if isinstance(created_at, str):
                    try:
                        d = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        monthly_trend[d.strftime('%Y-%m')] += 1
                    except Exception:
                        pass
                elif hasattr(created_at, 'strftime'):
                    monthly_trend[created_at.strftime('%Y-%m')] += 1

            region = (data.get('region') or data.get('regionName') or '').strip()
            if region:
                region_count[region] += 1

            category = (data.get('category') or data.get('applicantCategory') or 'General').strip()
            category_count[category] += 1

        # Last 8 weeks (week-by-week) trend
        now = dt.now()
        week_labels = []
        week_data = []
        weekly_trend = defaultdict(int)

        docs2 = db.collection('applications').limit(5000).stream()
        for doc in docs2:
            data = doc.to_dict() or {}
            created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed')
            if created_at:
                if isinstance(created_at, str):
                    try:
                        d = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        iso = d.isocalendar()
                        weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1
                    except Exception:
                        pass
                elif hasattr(created_at, 'strftime'):
                    iso = created_at.isocalendar()
                    weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1

        for i in range(7, -1, -1):
            import datetime as dt_module
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
        from datetime import datetime as dt
        db = get_firestore_db()

        docs = db.collection('applications') \
                 .order_by('createdAt', direction='DESCENDING') \
                 .limit(10) \
                 .stream()

        entries = []
        for doc in docs:
            data = doc.to_dict() or {}
            created_at = data.get('createdAt') or data.get('dateFiled')
            time_str = ''
            if created_at:
                if isinstance(created_at, str):
                    try:
                        d = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        time_str = d.strftime('%H:%M')
                    except Exception:
                        time_str = str(created_at)[:5]
                elif hasattr(created_at, 'strftime'):
                    time_str = created_at.strftime('%H:%M')

            status = (data.get('status') or 'pending').lower()
            name = (data.get('applicantName') or data.get('fullName') or doc.id[:8].upper())

            entries.append({
                'time': time_str,
                'ref': doc.id[:8].upper(),
                'name': name,
                'status': status,
            })

        return jsonify({'success': True, 'entries': entries})

    except Exception as e:
        print(f'[ERROR] superadmin_application_audit: {e}')
        # Fallback: get latest without ordering
        try:
            from firebase_config import get_firestore_db
            from datetime import datetime as dt
            db = get_firestore_db()
            docs = db.collection('applications').limit(10).stream()
            entries = []
            for doc in docs:
                data = doc.to_dict() or {}
                status = (data.get('status') or 'pending').lower()
                name = (data.get('applicantName') or data.get('fullName') or doc.id[:8].upper())
                entries.append({'time': '--:--', 'ref': doc.id[:8].upper(), 'name': name, 'status': status})
            return jsonify({'success': True, 'entries': entries})
        except Exception as e2:
            return jsonify({'success': False, 'message': str(e2)}), 500

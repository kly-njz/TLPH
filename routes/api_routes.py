from flask import Blueprint, request, jsonify, session
from flask_mail import Message, Mail
from datetime import datetime
import random
from firebase_auth_middleware import firebase_auth_required
import system_logs_storage

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
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    normalized = _normalize_municipality(municipality)
                    print(f"[DEBUG] get_user_municipality(user_id={user_id}) -> '{normalized}' (raw: '{municipality}')")
                    return normalized

        if user_email:
            docs = db.collection('users').where('email', '==', user_email).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
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
                region = user_data.get('region') or user_data.get('region_name') or user_data.get('regionName')
                if region:
                    print(f"[DEBUG] get_user_region(user_id={user_id}) -> '{region}'")
                    return region

        if user_email:
            docs = db.collection('users').where('email', '==', user_email).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                region = user_data.get('region') or user_data.get('region_name') or user_data.get('regionName')
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
        
        # Get fresh municipality from Firestore to ensure consistency
        municipality = get_user_municipality(user_id=user_id, user_email=user_email) if user_email != 'unknown' else 'unknown'
        
        # Log logout with fresh municipality from Firestore
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
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
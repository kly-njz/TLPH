from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
import uuid
from datetime import datetime
import os
import time
import hashlib
import requests
from firebase_auth_middleware import role_required, firebase_auth_required

bp = Blueprint('main', __name__)


def _cloudinary_enabled() -> bool:
    return all([
        os.environ.get('CLOUDINARY_CLOUD_NAME'),
        os.environ.get('CLOUDINARY_API_KEY'),
        os.environ.get('CLOUDINARY_API_SECRET')
    ])


def _cloudinary_signature(params: dict, api_secret: str) -> str:
    filtered = {k: v for k, v in params.items() if v is not None and v != ''}
    base = '&'.join([f"{k}={filtered[k]}" for k in sorted(filtered.keys())])
    return hashlib.sha1(f"{base}{api_secret}".encode('utf-8')).hexdigest()


def _upload_to_cloudinary(file_obj, folder: str):
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

    if not cloud_name or not api_key or not api_secret:
        return None

    timestamp = int(time.time())
    params_to_sign = {
        'folder': folder,
        'timestamp': timestamp,
    }
    signature = _cloudinary_signature(params_to_sign, api_secret)

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"
    try:
        file_obj.stream.seek(0)
    except Exception:
        pass

    resp = requests.post(
        endpoint,
        data={
            'api_key': api_key,
            'timestamp': timestamp,
            'folder': folder,
            'signature': signature,
        },
        files={
            'file': (file_obj.filename, file_obj.stream, file_obj.mimetype or 'application/octet-stream')
        },
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Cloudinary upload failed: {resp.status_code} {resp.text[:300]}")

    payload = resp.json() or {}
    return payload.get('secure_url') or payload.get('url')

@bp.route('/')
def index():
    print("HOME.HTML IS BEING RENDERED")  # Debug line
    # Server-side check for disabled user
    user_id = session.get('user_id')
    if user_id:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            if data.get('status', '').lower() == 'disabled':
                return redirect(url_for('account_disabled'))

    landing_news = []
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        docs = db.collection('news_updates').stream()
        for doc in docs:
            item = doc.to_dict() or {}
            if not bool(item.get('is_published', True)):
                continue
            landing_news.append({
                'id': doc.id,
                'title': str(item.get('title') or '').strip(),
                'summary': str(item.get('summary') or '').strip(),
                'published_date': str(item.get('published_date') or '').strip(),
                'image_url': str(item.get('image_url') or '').strip(),
                'is_published': True,
            })

        landing_news = [n for n in landing_news if n.get('title')]
        landing_news.sort(key=lambda row: row.get('published_date') or '', reverse=True)
    except Exception as e:
        print(f"[WARN] Could not load landing news from Firestore: {e}")

    main_news = landing_news[0] if landing_news else None
    side_news = landing_news[1:4] if len(landing_news) > 1 else []

    # Fetch active hiring positions (municipal viewers see own municipality + own region-scoped posts)
    hiring_positions = []
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        
        # Determine user's municipality if they are a municipal admin
        user_municipality = None
        user_region = None
        user_role = session.get('user_role', '').lower()
        
        if user_role in ['municipal_admin', 'municipal']:
            # Try to get municipality from session
            user_municipality = session.get('municipality') or session.get('user_municipality') or ''
            user_region = session.get('region') or session.get('user_region') or ''
            if not user_municipality.strip():
                # Fallback: try to resolve from user document
                if user_id:
                    from firebase_config import get_firestore_db
                    db_temp = get_firestore_db()
                    user_doc = db_temp.collection('users').document(user_id).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict() or {}
                        user_municipality = user_data.get('municipality') or user_data.get('municipalAdminMunicipality') or ''
                        user_region = user_region or user_data.get('region') or user_data.get('regionalAdminRegion') or ''
        
        # Query all active hirings, then scope-filter in memory for flexibility.
        docs = db.collection('hiring_positions').where('is_active', '==', True).stream()

        def normalize_scope(value):
            return ' '.join(str(value or '').strip().upper().split())

        muni_key = normalize_scope(user_municipality)
        region_key = normalize_scope(user_region)

        for doc in docs:
            item = doc.to_dict() or {}
            item_muni = normalize_scope(item.get('municipality'))
            item_region = normalize_scope(item.get('region'))
            item_scope_type = str(item.get('scope_type') or '').strip().lower()

            if user_role in ['municipal_admin', 'municipal'] and muni_key:
                is_same_municipality = item_muni and item_muni == muni_key
                is_same_region_scope = (
                    item_scope_type == 'region' and
                    region_key and
                    item_region == region_key
                )
                if not (is_same_municipality or is_same_region_scope):
                    continue

            hiring_positions.append({
                'id': doc.id,
                'job_title': str(item.get('job_title') or '').strip(),
                'description': str(item.get('description') or '').strip(),
                'position': str(item.get('position') or '').strip(),
                'starting_salary': item.get('starting_salary') or 0,
                'municipality': str(item.get('municipality') or '').strip(),
                'region': str(item.get('region') or '').strip(),
                'scope_type': str(item.get('scope_type') or '').strip(),
                'scope': str(item.get('scope') or '').strip(),
                'created_at': str(item.get('created_at') or '').strip(),
            })
        
        # Sort by created_at (newest first)
        hiring_positions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception as e:
        print(f"[WARN] Could not load hiring positions from Firestore: {e}")

    return render_template(
        'home.html',
        landing_news=landing_news,
        main_news=main_news,
        side_news=side_news,
        hiring_positions=hiring_positions,
    )


@bp.route('/api/hiring/apply', methods=['POST'])
def apply_for_hiring_position():
    """Public endpoint for submitting a hiring application.

    Creates a municipal applicant record directly in municipal_denr_applicant_jobs
    so it appears in applicants-municipal with PENDING status.
    """
    from firebase_config import get_firestore_db
    from firebase_admin import firestore

    def normalize_scope(value):
        return ' '.join(str(value or '').strip().upper().split())

    db = get_firestore_db()
    data = request.get_json(silent=True) or {}

    hiring_id = str(data.get('hiring_id') or '').strip()
    full_name = str(data.get('full_name') or '').strip()
    email = str(data.get('email') or '').strip()
    phone = str(data.get('phone') or '').strip()
    gender = str(data.get('gender') or '').strip()
    birth_date = str(data.get('birth_date') or '').strip()
    civil_status = str(data.get('civil_status') or '').strip()
    barangay = str(data.get('barangay') or '').strip()
    applicant_address = str(data.get('address') or '').strip()
    education_level = str(data.get('education_level') or '').strip()
    school_name = str(data.get('school_name') or '').strip()
    course = str(data.get('course') or '').strip()
    years_experience = str(data.get('years_experience') or '').strip()
    current_employer = str(data.get('current_employer') or '').strip()
    employment_status = str(data.get('employment_status') or '').strip()
    skills = str(data.get('skills') or '').strip()
    certifications = str(data.get('certifications') or '').strip()
    expected_salary = str(data.get('expected_salary') or '').strip()
    available_start_date = str(data.get('available_start_date') or '').strip()
    preferred_work_type = str(data.get('preferred_work_type') or '').strip()
    cover_letter = str(data.get('cover_letter') or '').strip()
    notes = str(data.get('notes') or '').strip()
    resume_url = str(data.get('resume_url') or '').strip()
    photo_url = str(data.get('photo_url') or '').strip()

    if not hiring_id:
        return jsonify({'success': False, 'error': 'Missing hiring position reference'}), 400
    if not full_name:
        return jsonify({'success': False, 'error': 'Full name is required'}), 400
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    if not phone:
        return jsonify({'success': False, 'error': 'Phone is required'}), 400
    if not resume_url:
        return jsonify({'success': False, 'error': 'Resume upload is required'}), 400
    if not photo_url:
        return jsonify({'success': False, 'error': 'Applicant photo upload is required'}), 400

    try:
        hiring_doc = db.collection('hiring_positions').document(hiring_id).get()
        if not hiring_doc.exists:
            return jsonify({'success': False, 'error': 'Hiring position not found'}), 404

        hiring = hiring_doc.to_dict() or {}
        if not bool(hiring.get('is_active', True)):
            return jsonify({'success': False, 'error': 'This hiring position is no longer active'}), 400

        municipality = str(hiring.get('municipality') or '').strip()
        region = str(hiring.get('region') or '').strip()
        scope_type = str(hiring.get('scope_type') or '').strip().lower()
        if scope_type not in {'municipality', 'region', 'national'}:
            if municipality:
                scope_type = 'municipality'
            elif region:
                scope_type = 'region'
            else:
                scope_type = 'national'
        position = str(hiring.get('position') or '').strip()
        job_title = str(hiring.get('job_title') or '').strip()
        description = str(hiring.get('description') or '').strip()

        if scope_type == 'municipality' and not municipality:
            return jsonify({'success': False, 'error': 'Hiring position has no municipality scope'}), 400
        if scope_type == 'region' and not region:
            return jsonify({'success': False, 'error': 'Hiring position has no region scope'}), 400

        if scope_type == 'municipality':
            scope_value = municipality
        elif scope_type == 'region':
            scope_value = region
        else:
            scope_value = 'NATIONAL OFFICE'
        municipality_value = municipality if scope_type == 'municipality' else ''

        application_id = f"HIRE-{hiring_id}-{uuid.uuid4().hex[:8].upper()}"
        reference_id = f"APP-{uuid.uuid4().hex[:8].upper()}"

        payload = {
            'source_id': hiring_id,
            'source_collection': 'hiring_positions',
            'full_name': full_name,
            'applicant_name': full_name,
            'email': email,
            'phone': phone,
            'contact_number': phone,
            'address': applicant_address or 'N/A',
            'barangay': barangay or 'N/A',
            'gender': gender or 'N/A',
            'birth_date': birth_date or 'N/A',
            'civil_status': civil_status or 'N/A',
            'education_level': education_level or 'N/A',
            'school_name': school_name or 'N/A',
            'course': course or 'N/A',
            'years_experience': years_experience or '0',
            'current_employer': current_employer or 'N/A',
            'employment_status': employment_status or 'N/A',
            'skills': skills or 'N/A',
            'certifications': certifications or 'N/A',
            'expected_salary': expected_salary or 'N/A',
            'available_start_date': available_start_date or 'N/A',
            'preferred_work_type': preferred_work_type or 'N/A',
            'resume_link': resume_url,
            'resume_url': resume_url,
            'photo_url': photo_url,
            'photo': photo_url,
            'cover_letter': cover_letter or 'N/A',
            'notes': notes or 'N/A',
            'candidate_type': position or 'Environmental Management Specialist',
            'category': position or 'Environmental Management Specialist',
            'region_office': region or 'N/A',
            'scope_type': scope_type,
            'scope': scope_value,
            'scope_key': normalize_scope(scope_value),
            'job_title': job_title or 'DENR Hiring Position',
            'job_description': description or 'No description provided.',
            'status': 'PENDING',
            'employeeStatus': 'pending',
            'reference_id': reference_id,
            'municipality': municipality_value,
            'region': region or 'N/A',
            'municipality_key': normalize_scope(municipality_value),
            'region_key': normalize_scope(region),
            'date_filed': datetime.utcnow().strftime('%Y-%m-%d'),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'created_via': 'home_hiring_modal',
        }

        db.collection('municipal_denr_applicant_jobs').document(application_id).set(payload, merge=True)

        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'application_id': application_id,
            'reference_id': reference_id,
            'status': 'PENDING'
        })
    except Exception as e:
        print(f"[ERROR] apply_for_hiring_position failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit application'}), 500


@bp.route('/api/hiring/upload-resume', methods=['POST'])
def upload_hiring_resume():
    """Upload applicant resume (PDF/DOC/DOCX) to Cloudinary."""
    if not _cloudinary_enabled():
        return jsonify({'success': False, 'error': 'Resume upload service is not configured'}), 500

    file_obj = request.files.get('resume')
    if not file_obj or not getattr(file_obj, 'filename', ''):
        return jsonify({'success': False, 'error': 'Resume file is required'}), 400

    filename = str(file_obj.filename or '').strip()
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed_ext = {'pdf', 'doc', 'docx'}
    if ext not in allowed_ext:
        return jsonify({'success': False, 'error': 'Only PDF, DOC, and DOCX files are allowed'}), 400

    content_length = request.content_length or 0
    max_size = 8 * 1024 * 1024  # 8 MB
    if content_length > max_size:
        return jsonify({'success': False, 'error': 'Resume file is too large (max 8MB)'}), 400

    try:
        uploaded_url = _upload_to_cloudinary(file_obj, 'tlph/applications/resumes')
        if not uploaded_url:
            return jsonify({'success': False, 'error': 'Failed to upload resume'}), 500
        return jsonify({'success': True, 'resume_url': uploaded_url}), 200
    except Exception as e:
        print(f"[ERROR] upload_hiring_resume failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to upload resume'}), 500


@bp.route('/api/hiring/upload-photo', methods=['POST'])
def upload_hiring_photo():
    """Upload applicant photo (JPG/PNG/WEBP) to Cloudinary."""
    if not _cloudinary_enabled():
        return jsonify({'success': False, 'error': 'Photo upload service is not configured'}), 500

    file_obj = request.files.get('photo')
    if not file_obj or not getattr(file_obj, 'filename', ''):
        return jsonify({'success': False, 'error': 'Applicant photo file is required'}), 400

    filename = str(file_obj.filename or '').strip()
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed_ext = {'jpg', 'jpeg', 'png', 'webp'}
    if ext not in allowed_ext:
        return jsonify({'success': False, 'error': 'Only JPG, PNG, and WEBP files are allowed'}), 400

    content_length = request.content_length or 0
    max_size = 8 * 1024 * 1024  # 8 MB
    if content_length > max_size:
        return jsonify({'success': False, 'error': 'Photo file is too large (max 8MB)'}), 400

    try:
        uploaded_url = _upload_to_cloudinary(file_obj, 'tlph/applications/photos')
        if not uploaded_url:
            return jsonify({'success': False, 'error': 'Failed to upload photo'}), 500
        return jsonify({'success': True, 'photo_url': uploaded_url}), 200
    except Exception as e:
        print(f"[ERROR] upload_hiring_photo failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to upload photo'}), 500

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/register')
def register():
    return render_template('signup.html')

@bp.route('/create-municipal-admin')
@role_required('regional','regional_admin')
def create_municipal_admin():
    return render_template('create-municipal-admin.html')

@bp.route('/create-regional-account')   
@role_required('super-admin','superadmin','national','national_admin')
def create_regional_account():
    return render_template('create_regional_account.html')

# Landing pages for different roles
@bp.route('/national/dashboard')
@role_required('national','national_admin')
def national_dashboard():
    from firebase_config import get_firestore_db
    from datetime import datetime
    from collections import defaultdict
    import calendar

    def _parse_ts(raw):
        """Convert Firestore Timestamp / ISO string / datetime to (datetime, str) tuple."""
        if not raw:
            return None, 'N/A'
        try:
            if hasattr(raw, 'ToDatetime'):
                dt = raw.ToDatetime()
            elif hasattr(raw, 'strftime'):
                dt = raw
            elif isinstance(raw, str):
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            else:
                return None, 'N/A'
            return dt, dt.strftime('%b %d, %Y')
        except Exception:
            return None, 'N/A'

    try:
        db = get_firestore_db()

        # ── 1. Applications ───────────────────────────────────────────────
        applications = []
        app_region_count = defaultdict(int)
        app_monthly = defaultdict(int)
        app_approved = app_pending = app_rejected = 0

        for doc in db.collection('applications').stream():
            data = doc.to_dict()
            status = (data.get('status') or 'pending').lower()
            if status not in ['approved', 'to review', 'review']:
                continue

            nat_status = (data.get('nationalStatus') or 'pending').lower()
            if nat_status == 'approved':
                app_approved += 1
            elif nat_status == 'rejected':
                app_rejected += 1
            else:
                app_pending += 1

            created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed')
            date_obj, date_str = _parse_ts(created_at)
            if date_obj:
                app_monthly[date_obj.strftime('%Y-%m')] += 1

            region = data.get('region') or 'N/A'
            if region and region != 'N/A':
                app_region_count[region] += 1

            applications.append({
                'id': doc.id,
                'created_at': date_str,
                '_sort_key': date_obj.isoformat() if date_obj else '',
                'reference_id': doc.id[:10].upper(),
                'applicant_name': data.get('applicantName') or data.get('fullName') or data.get('name') or 'N/A',
                'category': data.get('category') or data.get('applicantCategory') or 'N/A',
                'region': region,
                'status': nat_status,
            })
        applications.sort(key=lambda x: x['_sort_key'], reverse=True)

        # ── 2. Service Requests ───────────────────────────────────────────
        service_requests = []
        sr_type_count = defaultdict(int)
        sr_region_count = defaultdict(int)
        sr_monthly = defaultdict(int)
        sr_approved = sr_pending = sr_rejected = 0

        for doc in db.collection('service_requests').stream():
            data = doc.to_dict()
            nat_status = (data.get('nationalStatus') or 'pending').lower()
            if nat_status == 'approved':
                sr_approved += 1
            elif nat_status == 'rejected':
                sr_rejected += 1
            else:
                sr_pending += 1
            created_at = data.get('createdAt')
            date_obj, date_str = _parse_ts(created_at)
            if date_obj:
                sr_monthly[date_obj.strftime('%Y-%m')] += 1

            stype = data.get('serviceType') or data.get('type') or data.get('category') or 'N/A'
            sr_type_count[stype] += 1
            region = data.get('region') or data.get('province') or 'N/A'
            if region and region != 'N/A':
                sr_region_count[region] += 1

            service_requests.append({
                'id': doc.id,
                'date_filed': date_str,
                '_sort_key': date_obj.isoformat() if date_obj else '',
                'reference_id': doc.id[-6:].upper(),
                'service_type': stype,
                'region': region,
                'status': nat_status,
            })
        service_requests.sort(key=lambda x: x['_sort_key'], reverse=True)

        # ── 3. Transactions / Collections ────────────────────────────────
        transactions = []
        total_collections = 0.0

        for doc in db.collection('transactions').stream():
            data = doc.to_dict()
            raw_status = (data.get('status') or '').upper()
            amount_val = float(data.get('amount') or 0)
            if raw_status == 'PAID':
                total_collections += amount_val

            _, date_str2 = _parse_ts(data.get('created_at') or data.get('createdAt'))

            transactions.append({
                'ref': (data.get('external_id') or doc.id[:8]).upper(),
                'date': date_str2,
                'payor': data.get('user_email') or data.get('fullName') or 'N/A',
                'description': data.get('transaction_name') or data.get('description') or 'Payment',
                'amount': f"{amount_val:,.2f}",
                'status': raw_status,
            })
        transactions.reverse()  # most recent first
        transactions = transactions[:20]

        # ── 4 & 5. Permits + Inventory Items (single query) ─────────────
        permits = []
        inventory_items = []
        cat_map = {
            'farm-visit': 'Chemicals', 'fishery-permit': 'Marine Res.',
            'livestock': 'Livestock', 'forest': 'Forest Res.',
            'wildlife': 'Wildlife', 'environment': 'Environment'
        }
        for doc in db.collection('license_applications').stream():
            data = doc.to_dict()
            fd = data.get('formData') or {}
            region = fd.get('region') or data.get('region') or 'N/A'
            status_raw = (data.get('status') or 'pending').lower()
            disp = 'Valid' if status_raw == 'approved' else ('Expired' if status_raw == 'rejected' else 'Pending')
            permits.append({
                'ref': 'LIC-' + doc.id[-6:].upper(),
                'region': region,
                'status': disp,
                'status_raw': status_raw,
            })
            atype = data.get('applicationType') or 'N/A'
            cat = cat_map.get(str(atype).lower(), 'General')
            inventory_items.append({
                'category': cat,
                'quantity': data.get('quantity') or 1,
                'hub': region,
            })
        permits = permits[:15]
        inventory_items = inventory_items[:15]

        # ── 6. Trend (last 6 months, combined apps + SR) ─────────────────
        now = datetime.now()
        trend_labels = []
        trend_data = []
        for i in range(5, -1, -1):
            yr = now.year
            mo = now.month - i
            while mo <= 0:
                mo += 12
                yr -= 1
            key = f"{yr}-{mo:02d}"
            trend_labels.append(calendar.month_abbr[mo] + ' ' + str(yr))
            trend_data.append(app_monthly.get(key, 0) + sr_monthly.get(key, 0))

        # ── 7. Category chart (service request types) ───────────────────
        cat_keywords = {
            'Farm Visit': ['farm', 'crop', 'pest'],
            'Chemical/Fert.': ['chemical', 'fertilizer', 'pesticide'],
            'Financial Aid': ['subsidy', 'grant', 'loan', 'startup', 'financial'],
            'Seminar': ['seminar', 'training', 'workshop'],
            'Wildlife': ['wildlife', 'animal'],
            'Fisheries': ['fish', 'aqua'],
            'Forestry': ['forest', 'timber', 'tree'],
        }
        cat_counts = {k: 0 for k in cat_keywords}
        for stype, cnt in sr_type_count.items():
            sl = stype.lower()
            matched = False
            for cat, kws in cat_keywords.items():
                if any(k in sl for k in kws):
                    cat_counts[cat] += cnt
                    matched = True
                    break
            if not matched:
                cat_counts['Farm Visit'] += cnt
        category_labels = list(cat_counts.keys())
        category_data = list(cat_counts.values())

        # ── 8. Regional chart ─────────────────────────────────────────────
        combined_region = defaultdict(int)
        for r, c in app_region_count.items():
            combined_region[r] += c
        for r, c in sr_region_count.items():
            combined_region[r] += c
        top_regions = sorted(combined_region.items(), key=lambda x: x[1], reverse=True)[:8]
        region_labels = [r[0] for r in top_regions] if top_regions else ['N/A']
        region_data = [r[1] for r in top_regions] if top_regions else [0]

        # ── 9. Totals ─────────────────────────────────────────────────────
        total_applications = len(applications)
        total_service_requests = len(service_requests)
        total_count = total_applications + total_service_requests
        approved_count = app_approved + sr_approved
        pending_count = app_pending + sr_pending
        rejected_count = app_rejected + sr_rejected

    except Exception as e:
        print(f"[national_dashboard] Error: {e}")
        import traceback; traceback.print_exc()
        applications = service_requests = transactions = permits = inventory_items = []
        total_collections = total_count = approved_count = pending_count = rejected_count = 0
        total_applications = total_service_requests = 0
        trend_labels = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
        trend_data = category_data = region_data = [0] * 6
        category_labels = ['Farm Visit', 'Chemical/Fert.', 'Financial Aid', 'Seminar', 'Wildlife', 'Fisheries', 'Forestry']
        region_labels = ['N/A']
        as_of = datetime.now().strftime('%b %d, %Y %I:%M %p')

    return render_template(
        'national/landing-national.html',
        applications=applications,
        service_requests=service_requests,
        transactions=transactions,
        permits=permits,
        inventory_items=inventory_items,
        total_collections=total_collections,
        total_count=total_count,
        total_applications=total_applications,
        total_service_requests=total_service_requests,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        trend_labels=trend_labels,
        trend_data=trend_data,
        category_labels=category_labels,
        category_data=category_data,
        region_labels=region_labels,
        region_data=region_data,
        as_of=datetime.now().strftime('%b %d, %Y %I:%M %p'),
    )


@bp.route('/national/system-logs')
@role_required('national', 'national_admin')
def national_system_logs_fallback():
    """
    Show only regional transactions and fund transfers in the national audit log page.
    """
    from firebase_config import get_firestore_db
    from datetime import datetime
    db = get_firestore_db()
    regional_logs = []
    try:
        # Fetch all transactions (regional scope)
        tx_docs = db.collection('transactions').limit(5000).stream()
        for tx_doc in tx_docs:
            tx = tx_doc.to_dict() or {}
            status_value = str(tx.get('status') or '').strip().upper() or 'PENDING'
            ts_value = (
                tx.get('updated_at')
                or tx.get('forwarded_at')
                or tx.get('created_at')
                or tx.get('createdAt')
                or tx.get('updatedAt')
            )
            outcome_value = 'SUCCESS' if status_value in {'PAID', 'APPROVED', 'COMPLETED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')
            regional_logs.append({
                'id': tx_doc.id,
                'ts': ts_value,
                'user': tx.get('updated_by') or tx.get('forwarded_by') or tx.get('user_email') or 'User',
                'role': 'Municipal',
                'module': 'PAYMENTS',
                'action': status_value,
                'target': tx.get('transaction_name') or tx.get('description') or 'Payment',
                'targetId': tx.get('invoice_id') or tx.get('external_id') or tx_doc.id,
                'device_type': tx.get('device_type') or tx.get('device') or '',
                'ip': tx.get('ip') or '',
                'outcome': outcome_value,
                'message': tx.get('description') or '',
                'forwarded_message': tx.get('forwarded_message') or tx.get('forwardMessage') or '',
                'forwarded_by': tx.get('forwarded_by') or '',
                'municipality': tx.get('municipality') or tx.get('municipality_name') or tx.get('target_municipality') or '',
                'region': tx.get('region') or tx.get('region_name') or tx.get('regionName') or '',
                'canReview': status_value == 'FORWARDED',
                'diff': tx,
            })

        # Fetch all regional fund transfers
        fund_docs = db.collection('regional_fund_distribution').limit(5000).stream()
        for fund_doc in fund_docs:
            fund = fund_doc.to_dict() or {}
            status_value = str(fund.get('status') or '').strip().upper() or 'PENDING'
            ts_value = fund.get('updated_at') or fund.get('created_at') or fund.get('date')
            outcome_value = 'SUCCESS' if status_value in {'COMPLETED', 'APPROVED', 'RELEASED'} else ('FAIL' if status_value in {'FAILED', 'REJECTED', 'CANCELLED'} else 'WARN')
            regional_logs.append({
                'id': fund_doc.id,
                'ts': ts_value,
                'user': fund.get('updated_by') or fund.get('initiated_by') or 'Regional Office',
                'role': 'Regional',
                'module': 'FUND_TRANSFER',
                'action': status_value,
                'target': fund.get('region') or 'Region',
                'targetId': fund.get('reference') or fund_doc.id,
                'device_type': '',
                'ip': fund.get('ip') or '',
                'outcome': outcome_value,
                'message': fund.get('description') or '',
                'forwarded_message': '',
                'forwarded_by': '',
                'municipality': '',
                'region': fund.get('region') or fund.get('region_name') or fund.get('regionName') or '',
                'canReview': False,
                'diff': fund,
            })

        # Sort logs by timestamp descending (most recent first)
        def _parse_ts(ts):
            if not ts:
                return datetime.min
            try:
                if isinstance(ts, datetime):
                    return ts
                if isinstance(ts, str):
                    return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                pass
            return datetime.min
        regional_logs.sort(key=lambda x: _parse_ts(x.get('ts')), reverse=True)
    except Exception as e:
        print(f"[national_system_logs_fallback] Error: {e}")
        regional_logs = []

    # Map 'ts' to 'timestamp' and 'message' to 'details' for frontend compatibility
    for log in regional_logs:
        log['timestamp'] = log.get('ts', '')
        log['details'] = log.get('message', '')
    # Debug: Print the number of logs and a sample log
    print(f"[DEBUG] regional_logs count: {len(regional_logs)}")
    if regional_logs:
        print(f"[DEBUG] Sample regional_log: {regional_logs[0]}")
    return render_template('national/system/system-logs.html',
        regional_logs=regional_logs,
        municipal_logs=[],
        user_logs=[]
    )

# Add budget endpoint (must be top-level)
@bp.route('/national/accounting/add-budget', methods=['POST'])
@role_required('national','national_admin')
def add_budget():
    from flask import request, jsonify
    from firebase_config import get_firestore_db
    db = get_firestore_db()
    amount = request.json.get('amount')
    try:
        db.collection('finance').document('national').set({'budget': amount}, merge=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Accounting dashboard endpoint (must be top-level)
@bp.route('/national/accounting/dashboard')
@role_required('national','national_admin')
def national_accounting_dashboard_view():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        finance_data = {}
        regional_funds = []
        try:
            doc = db.collection('finance').document('national').get()
            if doc.exists:
                finance_data['national'] = doc.to_dict()
            else:
                finance_data['national'] = {}
            # Fetch regional fund distribution records
            funds_query = db.collection('regional_fund_distribution').order_by('date', direction='DESCENDING').stream()
            for fund_doc in funds_query:
                fund = fund_doc.to_dict()
                regional_funds.append(fund)
            # Sum all municipalities' general funds
            muni_docs = db.collection('finance').stream()
            total_general_fund = 0
            for mdoc in muni_docs:
                mdata = mdoc.to_dict()
                if mdoc.id not in ['national']:
                    try:
                        total_general_fund += float(mdata.get('general_fund', 0))
                    except Exception:
                        pass
            finance_data['national']['municipal_general_fund_total'] = total_general_fund
        except Exception:
            finance_data['national'] = {}
        return render_template('national/accounting/accounting-dashboard.html', finance=finance_data, regional_funds=regional_funds)
    except Exception as e:
        print(f"Error in national accounting dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('national/accounting/accounting-dashboard.html', finance={}, regional_funds=[])

@bp.route('/regional/dashboard')
@role_required('regional','regional_admin')
def regional_dashboard():
    return render_template('regional/landing-regional.html')

@bp.route('/super-admin/dashboard')
@role_required('super-admin','superadmin')
def superadmin_dashboard():
    return render_template('super-admin/landing-superadmin.html')

@bp.route('/farmer/dashboard')
@firebase_auth_required
def farmer_dashboard():
    return render_template('farmer_dashboard.html')

@bp.route('/dashboard')
@firebase_auth_required
def dashboard():
    return render_template('dashboard.html')

@bp.route('/user/dashboard')
@role_required('user')
def user_dashboard():
    return render_template('user/dashboard.html')

@bp.route('/user/profile')
@role_required('user')
def user_profile():
    return render_template('user/profile.html')

@bp.route('/user/transaction')
@role_required('user')
def user_transaction():
    return render_template('user/transaction.html')

@bp.route('/user/my-documents')
@role_required('user')
def user_my_documents():
    return render_template('user/my-documents.html')

@bp.route('/user/transaction-history')
@role_required('user')
def user_transaction_history():
    return render_template('user/transaction-history.html')

@bp.route('/user/history')
@role_required('user')
def user_history():
    return render_template('user/history.html')

@bp.route('/user/application')
@role_required('user')
def user_application():
    return render_template('user/application.html')

@bp.route('/user/application/apply')
@role_required('user')
def user_application_apply():
    return render_template('user/app-form.html')

@bp.route('/approval-status')
@firebase_auth_required
def approval_status():
    return render_template('approval_status.html')

@bp.route('/payment-success')
@firebase_auth_required
def payment_success():
    return render_template('payment-success.html')

@bp.route('/payment-failed')
@firebase_auth_required
def payment_failed():
    return render_template('payment-failed.html')

# Inventory routes
@bp.route('/user/inventory')
@role_required('user')
def user_inventory():
    return render_template('user/inventory/stock-list.html')

@bp.route('/user/inventory/add')
@role_required('user')
def user_inventory_add():
    return render_template('user/inventory/stock-form.html')


# Updated route to accept app_id as path parameter
@bp.route('/user/inventory/stock-info/<app_id>')
@role_required('user')
def inventory_stock_info(app_id):
     """Shows inventory stock info page for a specific item"""
     return render_template('user/inventory/stock-info.html')

@bp.route('/user/inventory/history')
@role_required('user')
def user_inventory_history():
    return render_template('user/inventory/stock-history.html')


@bp.route('/national/accounting/accounting-dashboard')
@role_required('national','national_admin')
def national_accounting_dashboard():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        finance_data = {}
        try:
            docs = db.collection('finance').stream()
            for doc in docs:
                finance_data.update(doc.to_dict())
        except Exception:
            pass
        return render_template('national/accounting/accounting-dashboard.html', finance=finance_data)
    except Exception as e:
        print(f"Error in national accounting dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('national/accounting/accounting-dashboard.html', finance={})
    
    # Fund distribution endpoint for national admin
@bp.route('/national/accounting/distribute-fund', methods=['POST'])
@role_required('national','national_admin')
def distribute_fund_to_region():
    from flask import request, jsonify
    from firebase_config import get_firestore_db
    import datetime
    db = get_firestore_db()
    data = request.get_json()
    region = str(data.get('region', '')).upper().replace('–', '-').replace('—', '-').replace('  ', ' ').replace(' ', '-')
    amount = data.get('amount')
    fund_type = data.get('fundType')
    # Add record to regional_fund_distribution
    try:
        record = {
            'region': region,
            'amount': amount,
            'fund_type': fund_type,
            'date': datetime.datetime.utcnow().isoformat(),
            'status': 'Released'
        }
        db.collection('regional_fund_distribution').add(record)
        # Also record in finance_transfers collection
        db.collection('finance_transfers').add({
            'region': region,
            'amount': amount,
            'fund_type': fund_type,
            'date': record['date'],
            'status': 'Released',
            'source': 'national',
            'type': 'national_to_regional'
        })
        # Deduct from national budget
        national_doc = db.collection('finance').document('national').get()
        if national_doc.exists:
            national_data = national_doc.to_dict()
            current_budget = float(national_data.get('budget', 0))
            new_budget = current_budget - float(amount)
            db.collection('finance').document('national').set({'budget': new_budget}, merge=True)

        # Record funds received by region in finance collection
        regional_finance_doc = db.collection('finance').document(region).get()
        if regional_finance_doc.exists:
            regional_data = regional_finance_doc.to_dict()
            prev_received = float(regional_data.get('received_from_national', 0))
            db.collection('finance').document(region).set({
                'received_from_national': prev_received + float(amount)
            }, merge=True)
        else:
            db.collection('finance').document(region).set({
                'received_from_national': float(amount)
            })
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@bp.route('/announcement')
@role_required('user')
def announcement_main():
    return render_template('user/announcement.html')

@bp.route('/news')
def news_main():
    news_items = []
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        docs = db.collection('news_updates').stream()
        for doc in docs:
            item = doc.to_dict() or {}
            if not bool(item.get('is_published', True)):
                continue
            title = str(item.get('title') or '').strip()
            if not title:
                continue
            news_items.append({
                'id': doc.id,
                'title': title,
                'summary': str(item.get('summary') or '').strip(),
                'published_date': str(item.get('published_date') or '').strip(),
                'image_url': str(item.get('image_url') or '').strip(),
            })
        news_items.sort(key=lambda row: row.get('published_date') or '', reverse=True)
    except Exception as e:
        print(f"[WARN] Could not load news page items from Firestore: {e}")

    return render_template('news.html', news_items=news_items)

@bp.route('/programs')
def programs_main():
    return render_template('programs.html')

@bp.route('/forest')
def forest_main():
    return render_template('forest.html')

@bp.route('/coastal')
def coastal_main():
    return render_template('coastal.html')

@bp.route('/biodiversity')
def biodiversity_main():
    return render_template('biodiversity.html')

@bp.route('/climate')
def climate_main():
    return render_template('climate.html')

@bp.route('/education')
def education_main():
    return render_template('education.html')

@bp.route('/environmental')
def environmental_main():
    return render_template('environmental.html')

@bp.route('/land')
def land_main():    
    return render_template('land.html')

@bp.route('/river')
def river_main():
    return render_template('river.html')

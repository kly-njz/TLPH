from flask import Blueprint, render_template, request, jsonify, session
from firebase_auth_middleware import role_required
from firebase_config import get_firestore_db
from datetime import datetime
from collections import defaultdict
import coa_storage
from firebase_admin import firestore
import hashlib
import os
import requests
import time

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')


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
        'timestamp': timestamp
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
            'signature': signature
        },
        files={
            'file': (file_obj.filename, file_obj.stream, file_obj.mimetype or 'application/octet-stream')
        },
        timeout=45
    )

    if not resp.ok:
        raise RuntimeError(f"Cloudinary upload failed: {resp.status_code} {resp.text[:300]}")

    payload = resp.json() or {}
    return payload.get('secure_url') or payload.get('url')


def _delete_from_cloudinary(image_url: str):
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

    if not image_url or not cloud_name or not api_key or not api_secret:
        return

    prefix = f"https://res.cloudinary.com/{cloud_name}/"
    if not image_url.startswith(prefix):
        return

    marker = '/upload/'
    idx = image_url.find(marker)
    if idx < 0:
        return

    remainder = image_url[idx + len(marker):]
    if not remainder:
        return

    parts = [p for p in remainder.split('/') if p]
    if not parts:
        return

    if parts[0].startswith('v') and parts[0][1:].isdigit():
        parts = parts[1:]
    if not parts:
        return

    public_path = '/'.join(parts)
    dot = public_path.rfind('.')
    if dot > public_path.rfind('/'):
        public_id = public_path[:dot]
    else:
        public_id = public_path

    if not public_id:
        return

    timestamp = int(time.time())
    signature = _cloudinary_signature(
        {'public_id': public_id, 'timestamp': timestamp},
        api_secret
    )
    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy"

    try:
        requests.post(
            endpoint,
            data={
                'api_key': api_key,
                'public_id': public_id,
                'timestamp': timestamp,
                'signature': signature,
            },
            timeout=20,
        )
    except Exception:
        # Do not block the delete request if Cloudinary cleanup fails.
        pass

@bp.route('/inventory')
@role_required('super-admin','superadmin')
def inventory_view():
    inventory_records = []
    summary = {
        'total_assets': 0,
        'chemicals': 0,
        'natural_assets': 0,
        'protected_areas': 0,
        'low_stock': 0
    }
    trend_labels = []
    trend_data = []
    category_labels = []
    category_data = []
    region_options = []

    try:
        db = get_firestore_db()
        from models.region_province_map import region_province_map
        docs = db.collection('inventory_registrations').stream()
        monthly_totals = defaultdict(float)
        category_totals = defaultdict(float)
        regions_set = set()

        users_map = {}
        try:
            users_map = {u.id: (u.to_dict() or {}) for u in db.collection('users').stream()}
        except Exception:
            users_map = {}

        def to_number(value):
            try:
                if value is None or value == '':
                    return 0.0
                return float(value)
            except Exception:
                return 0.0

        def normalize_category(raw):
            text = str(raw or '').strip().lower()
            if any(k in text for k in ['chemical', 'fertilizer', 'pesticide', 'ammonium', 'nitrogen']):
                return 'CHEMICAL RESOURCES'
            if any(k in text for k in ['protected', 'sanctuary', 'park', 'conservation', 'eco-zone', 'ecozone']):
                return 'PROTECTED AREAS'
            if any(k in text for k in ['natural', 'forest', 'mangrove', 'biodiversity', 'wildlife', 'resource']):
                return 'NATURAL ASSETS'
            if any(k in text for k in ['equipment', 'tool', 'device', 'machinery', 'kit', 'gps']):
                return 'EQUIPMENT'
            return ''

        def category_from_sector(raw_sector):
            sector = str(raw_sector or '').strip().lower()
            if sector == 'farming':
                return 'CHEMICAL RESOURCES'
            if sector in {'fisheries', 'forestry', 'environment'}:
                return 'NATURAL ASSETS'
            if sector in {'wildlife'}:
                return 'PROTECTED AREAS'
            if sector in {'livestock'}:
                return 'NATURAL ASSETS'
            return ''

        def category_from_app_type(raw_app_type):
            app_type = str(raw_app_type or '').strip().lower()
            if any(k in app_type for k in ['farm', 'crop', 'soil', 'pest', 'fertilizer', 'chemical']):
                return 'CHEMICAL RESOURCES'
            if any(k in app_type for k in ['forest', 'fish', 'fisher', 'marine', 'environment']):
                return 'NATURAL ASSETS'
            if any(k in app_type for k in ['wildlife', 'protected', 'sanctuary']):
                return 'PROTECTED AREAS'
            if any(k in app_type for k in ['equipment', 'device', 'tool']):
                return 'EQUIPMENT'
            return ''

        def region_from_province(province_name):
            p = str(province_name or '').strip().lower()
            if not p:
                return ''
            for region_label, provinces in (region_province_map or {}).items():
                for prov in (provinces or []):
                    if str(prov or '').strip().lower() == p:
                        return region_label
            return ''

        def parse_dt(raw):
            if not raw:
                return None
            if isinstance(raw, datetime):
                return raw
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw.replace('Z', '+00:00'))
                except Exception:
                    return None
            if hasattr(raw, 'to_datetime'):
                try:
                    return raw.to_datetime()
                except Exception:
                    return None
            if hasattr(raw, 'strftime'):
                return raw
            return None

        for doc in docs:
            data = doc.to_dict() or {}
            form_data = data.get('formData') or {}
            user_data = users_map.get(data.get('userId', ''), {})

            quantity = to_number(
                data.get('stockAvailable')
                or data.get('quantity')
                or data.get('volume')
                or data.get('availableStock')
                or form_data.get('quantity')
                or form_data.get('stockAvailable')
                or 0
            )

            raw_category = (
                data.get('category')
                or data.get('classification')
                or data.get('itemType')
                or data.get('inventoryType')
            )

            created_at_raw = data.get('createdAt') or data.get('submittedAt')
            created_at = parse_dt(created_at_raw)

            municipality = (
                data.get('municipality')
                or data.get('location')
                or form_data.get('municipality')
                or user_data.get('municipality')
                or 'N/A'
            )

            province = (
                data.get('province')
                or form_data.get('province')
                or user_data.get('province')
                or ''
            )

            region = (
                data.get('region')
                or data.get('regionName')
                or form_data.get('region')
                or user_data.get('region')
                or user_data.get('regionName')
                or region_from_province(province)
                or 'N/A'
            )

            description = (
                data.get('resourceName')
                or data.get('notes')
                or data.get('description')
                or data.get('itemName')
                or data.get('itemDescription')
                or form_data.get('resourceName')
                or form_data.get('description')
                or 'N/A'
            )

            normalized_category = (
                normalize_category(raw_category)
                or category_from_sector(data.get('sector'))
                or category_from_app_type(data.get('applicationType'))
                or normalize_category(description)
                or 'NATURAL ASSETS'
            )

            # Skip placeholder/empty records to avoid all-N/A rows.
            if str(description).strip().upper() in {'', 'N/A'} and quantity <= 0 and str(region).strip().upper() == 'N/A' and str(municipality).strip().upper() == 'N/A':
                continue

            inventory_records.append({
                'id': doc.id,
                'category': normalized_category,
                'description': str(description).strip(),
                'quantity': quantity,
                'region': str(region).strip(),
                'municipality': str(municipality).strip(),
                'created_at': created_at,
                'status': (data.get('status') or '').strip()
            })

            summary['total_assets'] += quantity
            if normalized_category == 'CHEMICAL RESOURCES':
                summary['chemicals'] += quantity
            elif normalized_category == 'NATURAL ASSETS':
                summary['natural_assets'] += quantity
            elif normalized_category == 'PROTECTED AREAS':
                summary['protected_areas'] += quantity

            status_text = str(data.get('status') or '').lower()
            if 'low stock' in status_text or quantity <= 20:
                summary['low_stock'] += 1

            if created_at:
                monthly_totals[created_at.strftime('%Y-%m')] += quantity
            category_totals[normalized_category] += quantity
            regions_set.add(region)

        inventory_records.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)

        inventory_rows = []
        for rec in inventory_records:
            qty = rec.get('quantity', 0)
            try:
                qty = float(qty)
                if qty.is_integer():
                    qty = int(qty)
            except Exception:
                qty = 0

            inventory_rows.append({
                'cat': rec.get('category', 'UNCATEGORIZED'),
                'desc': rec.get('description', 'N/A'),
                'qty': qty,
                'reg': rec.get('region', 'N/A'),
                'mun': rec.get('municipality', 'N/A')
            })

        now = datetime.now()
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            month_key = f'{year}-{month:02d}'
            trend_labels.append(datetime(year, month, 1).strftime('%b'))
            trend_data.append(round(monthly_totals.get(month_key, 0), 2))

        category_priority = ['CHEMICAL RESOURCES', 'NATURAL ASSETS', 'PROTECTED AREAS', 'EQUIPMENT', 'UNCATEGORIZED']
        category_labels = [c for c in category_priority if category_totals.get(c, 0) > 0]
        category_data = [round(category_totals[c], 2) for c in category_labels]
        if not category_labels:
            category_labels = ['UNCATEGORIZED']
            category_data = [0]

        region_options = sorted([r for r in regions_set if r and str(r).strip().upper() != 'N/A'])
    except Exception as e:
        print(f'[ERROR] superadmin inventory_view: {e}')
        inventory_rows = []

    return render_template(
        'super-admin/inventory-superadmin/inventory-superadmin.html',
        inventory_records=inventory_records,
        summary=summary,
        trend_labels=trend_labels,
        trend_data=trend_data,
        category_labels=category_labels,
        category_data=category_data,
        region_options=region_options,
        inventory_rows=inventory_rows
    )

@bp.route('/user-application')
@role_required('super-admin','superadmin')
def user_application_view():
    stats = {
        'total': 0, 'pending': 0, 'approved': 0,
        'rejected': 0, 'to_review': 0, 'cancelled': 0, 'approval_rate': 0,
    }
    categories = []
    regions = []

    try:
        db = get_firestore_db()
        docs = list(db.collection('applications').limit(5000).stream())

        def sector_label(value):
            raw = str(value or '').strip()
            key = raw.lower()
            mapping = {
                'farming': 'Crop & Plant',
                'livestock': 'Fisheries & Agriculture',
                'agribusiness': 'Agribusiness & Agro-Processing',
                'trade': 'Agricultural Trade',
                'infrastructure': 'Infrastructure',
            }
            return mapping.get(key, raw)

        cat_set = set()
        reg_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict() or {}
            form_data = data.get('formData') or {}
            stats['total'] += 1

            national_status = (data.get('nationalStatus') or '').lower()
            status = (data.get('status') or 'pending').lower()
            effective = national_status if national_status else status

            if effective in ['canceled']:
                effective = 'cancelled'
            if effective.startswith('forwarded'):
                effective = 'to_review'

            if effective in ['approved']:
                stats['approved'] += 1
            elif effective in ['rejected']:
                stats['rejected'] += 1
            elif effective in ['cancelled']:
                stats['cancelled'] += 1
            elif effective in ['to review', 'review']:
                stats['to_review'] += 1
            else:
                stats['pending'] += 1

            cat = (
                data.get('categoryType')
                or data.get('category')
                or data.get('applicantCategory')
                or data.get('sector')
                or form_data.get('categoryType')
                or form_data.get('category')
                or form_data.get('sector')
                or ''
            ).strip()
            if cat:
                cat_set.add(sector_label(cat))

            reg = (
                data.get('region')
                or data.get('regionName')
                or form_data.get('region')
                or ''
            ).strip()
            if reg:
                reg_count[reg] += 1

        if stats['total'] > 0:
            stats['approval_rate'] = round(stats['approved'] / stats['total'] * 100, 1)

        categories = sorted(cat_set)
        regions = sorted(reg_count.keys())

    except Exception as e:
        print(f'[ERROR] user_application_view: {e}')

    return render_template(
        'super-admin/application-superadmin/application-superadmin.html',
        stats=stats,
        categories=categories,
        regions=regions,
    )

@bp.route('/user-service-request')
@role_required('super-admin','superadmin')
def user_request_view():
    return render_template('super-admin/service-request-superadmin/service-request-superadmin.html')

@bp.route('/user-inventory')
@role_required('super-admin','superadmin')
def user_inventory_view():
    return render_template('super-admin/user-inventory-superadmin/user-inventory-superadmin.html')

@bp.route('/permits')
@role_required('super-admin','superadmin')
def permits_view():
    return render_template('super-admin/permits-license-superadmin/permits-license-superadmin.html')

@bp.route('/accounting/transaction')
@role_required('super-admin','superadmin')
def transaction_permits_view():
    return render_template('super-admin/transaction-permit-superadmin/transaction-permit-superadmin.html')

@bp.route('/account')
@role_required('super-admin','superadmin')
def accounts_view():
    return render_template('super-admin/superadmin-account/superadmin-account.html')

@bp.route('/audit-logs')
@role_required('super-admin','superadmin')
def audit_logs_view():
    return render_template('super-admin/audit-logs-superadmin/audit-logs-superadmin.html')

@bp.route('/system-logs')
@role_required('super-admin','superadmin')
def system_logs_view():
    return render_template('super-admin/system-logs/system-logs.html')

@bp.route('/superadmin-profile')
@role_required('super-admin','superadmin')
def superadmin_profile():
    return render_template('super-admin/superadmin-profile.html')

@bp.route('/superadmin-notification')
@role_required('super-admin','superadmin')
def superadmin_notification():
    return render_template('super-admin/superadmin-notification.html')

# --- Added stubs for additional superadmin UI pages requested by product owner ---
@bp.route('/regions')
@role_required('super-admin','superadmin')
def regions_list_view():
    return render_template('super-admin/regions/regions-list.html')


@bp.route('/regions/<region_id>')
@role_required('super-admin','superadmin')
def regions_detail_view(region_id):
    return render_template('super-admin/regions/region-detail.html', region_id=region_id)

@bp.route('/user-groups')
@role_required('super-admin','superadmin')
def user_groups_view():
    return render_template('super-admin/user-groups/user-groups.html')

@bp.route('/products-national')
@role_required('super-admin','superadmin')
def products_national_view():
    return render_template('super-admin/products/products-national.html')

@bp.route('/purchases')
@role_required('super-admin','superadmin')
def purchases_view():
    return render_template('super-admin/products/purchases-supplier.html')

@bp.route('/sales')
@role_required('super-admin','superadmin')
def sales_view():
    return render_template('super-admin/products/sales-list.html')

@bp.route('/sales-return')
@role_required('super-admin','superadmin')
def sales_return_view():
    return render_template('super-admin/products/sales-return.html')

@bp.route('/distributed-products')
@role_required('super-admin','superadmin')
def distributed_products_view():
    return render_template('super-admin/products/distributed-products.html')

@bp.route('/damage-products')
@role_required('super-admin','superadmin')
def damage_products_view():
    return render_template('super-admin/products/damage-products.html')

@bp.route('/transfer-products')
@role_required('super-admin','superadmin')
def transfer_products_view():
    return render_template('super-admin/products/transfer-products.html')


# --- SUPERADMIN QUOTATION REGISTRY & WORKFLOW ---
@bp.route('/quotation')
@role_required('super-admin','superadmin')
def quotation_view():
    from quotation_storage import get_all_quotations
    try:
        quotations = get_all_quotations()
        # Sort by created_at descending
        quotations.sort(key=lambda q: q.get('created_at', ''), reverse=True)
    except Exception as e:
        print(f'[ERROR] superadmin quotation_view: {e}')
        quotations = []
    return render_template(
        'super-admin/finance/quotation.html',
        quotations=quotations
    )

# API: Create quotation (superadmin)
@bp.route('/api/quotation/create', methods=['POST'])
@role_required('super-admin','superadmin')
def api_create_quotation_superadmin():
    from quotation_storage import add_quotation
    data = request.get_json(silent=True) or {}
    required_fields = [
        'buyer', 'title', 'category', 'supplier',
        'deliver_from', 'deliver_to', 'product'
    ]
    missing = [f for f in required_fields if not str(data.get(f) or '').strip()]
    if missing:
        return jsonify({'success': False, 'error': 'Missing required quotation fields'}), 400
    try:
        quantity = float(data.get('quantity') or 0)
    except Exception:
        quantity = 0.0
    try:
        unit_price = float(data.get('unit_price') or 0)
    except Exception:
        unit_price = 0.0
    try:
        other_charges = float(data.get('other_charges') or 0)
    except Exception:
        other_charges = 0.0
    total = (quantity * unit_price) + other_charges
    issue_date = str(data.get('issue_date') or '').strip()
    if not issue_date:
        issue_date = datetime.utcnow().date().isoformat()
    payload = {
        'buyer': data.get('buyer'),
        'title': data.get('title'),
        'category': data.get('category'),
        'supplier': data.get('supplier'),
        'deliver_from': data.get('deliver_from'),
        'deliver_to': data.get('deliver_to'),
        'deliver_to_type': data.get('deliver_to_type') or '',
        'buyer_type': data.get('buyer_type') or '',
        'product': data.get('product'),
        'quantity': quantity,
        'unit_price': unit_price,
        'other_charges': other_charges,
        'other_charges_note': data.get('other_charges_note') or '',
        'status': data.get('status') or 'pending',
        'issue_date': issue_date,
        'date': issue_date,
        'total': total,
        'created_by': 'superadmin'
    }
    try:
        quotation = add_quotation(payload)
        return jsonify({'success': True, 'quotation': {'id': quotation.get('id')}})
    except Exception as e:
        print(f"[ERROR] api_create_quotation_superadmin failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to create quotation'}), 500

# API: Allocate/forward quotation to region/municipality or update status
@bp.route('/api/quotation/<quotation_id>/update', methods=['POST'])
@role_required('super-admin','superadmin')
def api_update_quotation_superadmin(quotation_id):
    from quotation_storage import update_quotation, update_quotation_status
    data = request.get_json() or {}
    updates = {}
    # Allow updating full quotation fields
    for field in [
        'buyer', 'title', 'category', 'supplier',
        'deliver_from', 'deliver_to', 'deliver_to_type',
        'buyer_type', 'product', 'quantity', 'unit_price',
        'other_charges', 'other_charges_note', 'issue_date', 'date', 'total'
    ]:
        if field in data:
            updates[field] = data[field]
    if any(key in data for key in ['quantity', 'unit_price', 'other_charges']) and 'total' not in updates:
        try:
            quantity = float(data.get('quantity') or 0)
        except Exception:
            quantity = 0.0
        try:
            unit_price = float(data.get('unit_price') or 0)
        except Exception:
            unit_price = 0.0
        try:
            other_charges = float(data.get('other_charges') or 0)
        except Exception:
            other_charges = 0.0
        updates['total'] = (quantity * unit_price) + other_charges
    if updates:
        update_quotation(quotation_id, updates)
    if 'status' in data:
        user_email = data.get('user_email', 'superadmin')
        notes = data.get('notes', '')
        update_quotation_status(quotation_id, data['status'], user_email, notes)
    return jsonify({'success': True})

@bp.route('/projects')
@role_required('super-admin','superadmin')
def projects_view():
    return render_template('super-admin/projects/projects-region.html')

@bp.route('/tasks')
@role_required('super-admin','superadmin')
def tasks_view():
    return render_template('super-admin/projects/tasks-region.html')

@bp.route('/applicants')
@role_required('super-admin','superadmin')
def applicants_view():
    return render_template('super-admin/applicants/applicants.html')


def _normalize_superadmin_applicant_status(raw_status):
    status = str(raw_status or 'pending').strip().lower()
    if status in ['accepted', 'approve', 'approved', 'hired']:
        return 'accepted'
    if status in ['reject', 'rejected', 'denied', 'declined']:
        return 'rejected'
    return 'pending'


def _is_accepted_status(raw_status):
    return _normalize_superadmin_applicant_status(raw_status) == 'accepted'


def _format_firestore_timestamp(value):
    if not value:
        return 'N/A'
    try:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed.strftime('%b %d, %Y %I:%M %p')
        if hasattr(value, 'strftime'):
            return value.strftime('%b %d, %Y %I:%M %p')
    except Exception:
        return str(value)
    return str(value)


@bp.route('/api/applicants/data', methods=['GET'])
@role_required('super-admin', 'superadmin')
def superadmin_applicants_data():
    try:
        db = get_firestore_db()
        docs = db.collection('municipal_denr_applicant_jobs').stream()

        applicants = []
        hiring_description_cache = {}
        for doc in docs:
            data = doc.to_dict() or {}

            full_name = (
                data.get('full_name')
                or data.get('applicant_name')
                or data.get('fullName')
                or data.get('name')
                or 'N/A'
            )
            candidate_type = (
                data.get('candidate_type')
                or data.get('category')
                or data.get('applicantCategory')
                or 'N/A'
            )
            job_description = (
                data.get('job_description')
                or data.get('jobDescription')
                or data.get('description')
                or data.get('project_name')
                or 'N/A'
            )

            if str(job_description).strip().upper() in {'', 'N/A'}:
                source_collection = str(data.get('source_collection') or '').strip().lower()
                source_id = str(data.get('source_id') or '').strip()
                if source_collection == 'hiring_positions' and source_id:
                    if source_id not in hiring_description_cache:
                        try:
                            src_doc = db.collection('hiring_positions').document(source_id).get()
                            if src_doc.exists:
                                src_data = src_doc.to_dict() or {}
                                hiring_description_cache[source_id] = str(
                                    src_data.get('description')
                                    or src_data.get('job_description')
                                    or src_data.get('jobDescription')
                                    or 'N/A'
                                ).strip() or 'N/A'
                            else:
                                hiring_description_cache[source_id] = 'N/A'
                        except Exception:
                            hiring_description_cache[source_id] = 'N/A'
                    job_description = hiring_description_cache.get(source_id) or 'N/A'

            region_office = data.get('region_office') or data.get('region') or 'N/A'
            status = _normalize_superadmin_applicant_status(
                data.get('status') or data.get('employeeStatus') or data.get('application_status')
            )

            applicants.append({
                'id': doc.id,
                'full_name': full_name,
                'candidate_type': candidate_type,
                'job_description': job_description,
                'region_office': region_office,
                'status': status,
                'is_accepted': status == 'accepted',
                'can_delete': status == 'rejected',
                'reference_id': data.get('reference_id') or doc.id[:12].upper(),
                'accepted_by': data.get('accepted_by') or data.get('reviewed_by') or 'N/A',
                'updated_at': _format_firestore_timestamp(data.get('updated_at') or data.get('reviewed_at') or data.get('created_at')),
            })

        applicants.sort(key=lambda row: row.get('full_name', '').lower())
        return jsonify({'success': True, 'applicants': applicants})
    except Exception as e:
        print(f'[ERROR] superadmin_applicants_data: {e}')
        return jsonify({'success': False, 'error': 'Failed to load applicants'}), 500


@bp.route('/api/applicants', methods=['POST'])
@role_required('super-admin', 'superadmin')
def superadmin_create_applicant():
    try:
        payload = request.get_json() or {}
        full_name = str(payload.get('full_name') or '').strip()
        candidate_type = str(payload.get('candidate_type') or '').strip()
        region_office = str(payload.get('region_office') or '').strip()
        scope_type = str(payload.get('scope_type') or 'region').strip().lower()
        requested_scope = str(payload.get('scope') or '').strip()
        status = _normalize_superadmin_applicant_status(payload.get('status'))

        if not full_name or not candidate_type or not region_office:
            return jsonify({'success': False, 'error': 'full_name, candidate_type, and region_office are required'}), 400
        if scope_type not in {'region', 'municipality'}:
            return jsonify({'success': False, 'error': 'scope_type must be region or municipality'}), 400

        scope = requested_scope or (region_office if scope_type == 'region' else '')
        if not scope:
            return jsonify({'success': False, 'error': 'scope is required for municipality scope'}), 400

        db = get_firestore_db()
        doc_ref = db.collection('municipal_denr_applicant_jobs').document()
        actor = session.get('user_email') or 'superadmin'

        data = {
            'full_name': full_name,
            'candidate_type': candidate_type,
            'category': candidate_type,
            'region_office': region_office,
            'region': region_office,
            'status': status,
            'employeeStatus': status,
            'scope_type': scope_type,
            'scope': scope,
            'scope_key': scope.strip().lower(),
            'reference_id': f'SUP-{doc_ref.id[:8].upper()}',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'created_by': actor,
            'updated_by': actor,
            'created_by_role': 'super_admin',
        }

        if scope_type == 'municipality':
            data.update({
                'municipality': scope,
                'municipality_key': scope,
            })

        if status == 'accepted':
            data.update({
                'accepted_by': actor,
                'reviewed_by': actor,
                'reviewed_at': firestore.SERVER_TIMESTAMP,
            })

        doc_ref.set(data)
        return jsonify({'success': True, 'id': doc_ref.id})
    except Exception as e:
        print(f'[ERROR] superadmin_create_applicant: {e}')
        return jsonify({'success': False, 'error': 'Failed to create applicant'}), 500


@bp.route('/api/applicants/<applicant_id>', methods=['PUT'])
@role_required('super-admin', 'superadmin')
def superadmin_update_applicant(applicant_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('municipal_denr_applicant_jobs').document(applicant_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Applicant not found'}), 404

        current = snap.to_dict() or {}
        if _is_accepted_status(current.get('status') or current.get('employeeStatus')):
            return jsonify({'success': False, 'error': 'Accepted applicants cannot be edited'}), 400
        actor = session.get('user_email') or 'superadmin'

        payload = request.get_json() or {}
        updates = {}

        if 'full_name' in payload:
            updates['full_name'] = str(payload.get('full_name') or '').strip()
        if 'candidate_type' in payload:
            updates['candidate_type'] = str(payload.get('candidate_type') or '').strip()
            updates['category'] = updates['candidate_type']
        if 'region_office' in payload:
            updates['region_office'] = str(payload.get('region_office') or '').strip()
            updates['region'] = updates['region_office']
            if str(current.get('scope_type') or '').strip().lower() == 'region':
                updates['scope'] = updates['region_office']
                updates['scope_key'] = updates['region_office'].lower()
        if 'status' in payload:
            normalized = _normalize_superadmin_applicant_status(payload.get('status'))
            updates['status'] = normalized
            updates['employeeStatus'] = normalized
            if normalized == 'accepted':
                updates['accepted_by'] = actor
                updates['reviewed_by'] = actor
                updates['reviewed_at'] = firestore.SERVER_TIMESTAMP

        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        updates['updated_by'] = actor
        if not updates:
            return jsonify({'success': False, 'error': 'No valid updates provided'}), 400

        doc_ref.update(updates)
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_update_applicant: {e}')
        return jsonify({'success': False, 'error': 'Failed to update applicant'}), 500


@bp.route('/api/applicants/<applicant_id>', methods=['DELETE'])
@role_required('super-admin', 'superadmin')
def superadmin_delete_applicant(applicant_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('municipal_denr_applicant_jobs').document(applicant_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Applicant not found'}), 404

        current = snap.to_dict() or {}
        status = _normalize_superadmin_applicant_status(current.get('status') or current.get('employeeStatus'))
        if status != 'rejected':
            return jsonify({'success': False, 'error': 'Only rejected applicants can be permanently deleted'}), 400

        doc_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_delete_applicant: {e}')
        return jsonify({'success': False, 'error': 'Failed to delete applicant'}), 500


def _normalize_hiring_scope_type(raw_scope_type):
    scope_type = str(raw_scope_type or 'national').strip().lower()
    return scope_type if scope_type in {'national', 'region', 'municipality'} else 'national'


def _normalize_hiring_payload(payload):
    scope_type = _normalize_hiring_scope_type(payload.get('scope_type'))
    region = str(payload.get('region') or '').strip().upper()
    municipality = str(payload.get('municipality') or '').strip().upper()
    scope = str(payload.get('scope') or '').strip().upper()

    if scope_type == 'national':
        scope = 'NATIONAL'
        region = ''
        municipality = ''
    elif scope_type == 'region':
        scope = scope or region
        region = region or scope
        municipality = ''
    else:
        scope = scope or municipality
        municipality = municipality or scope

    return {
        'job_title': str(payload.get('job_title') or '').strip(),
        'description': str(payload.get('description') or '').strip(),
        'position': str(payload.get('position') or '').strip(),
        'starting_salary': payload.get('starting_salary'),
        'scope_type': scope_type,
        'scope': scope,
        'region': region,
        'municipality': municipality,
    }


@bp.route('/api/hiring', methods=['GET'])
@role_required('super-admin', 'superadmin')
def superadmin_get_hiring_positions():
    try:
        db = get_firestore_db()
        docs = db.collection('hiring_positions').stream()

        positions = []
        for doc in docs:
            data = doc.to_dict() or {}
            scope_type = _normalize_hiring_scope_type(data.get('scope_type'))
            positions.append({
                'id': doc.id,
                'job_title': data.get('job_title') or 'N/A',
                'description': data.get('description') or 'N/A',
                'position': data.get('position') or 'N/A',
                'starting_salary': data.get('starting_salary') or 0,
                'scope_type': scope_type,
                'scope': data.get('scope') or ('NATIONAL' if scope_type == 'national' else (data.get('region') if scope_type == 'region' else data.get('municipality'))),
                'region': data.get('region') or '',
                'municipality': data.get('municipality') or '',
                'is_active': bool(data.get('is_active', True)),
                'created_at': _format_firestore_timestamp(data.get('created_at')),
                'updated_at': _format_firestore_timestamp(data.get('updated_at')),
            })

        positions.sort(key=lambda row: (not row.get('is_active', True), str(row.get('job_title') or '').lower()))
        return jsonify({'success': True, 'positions': positions})
    except Exception as e:
        print(f'[ERROR] superadmin_get_hiring_positions: {e}')
        return jsonify({'success': False, 'error': 'Failed to load hiring positions'}), 500


@bp.route('/api/hiring', methods=['POST'])
@role_required('super-admin', 'superadmin')
def superadmin_create_hiring_position():
    try:
        payload = _normalize_hiring_payload(request.get_json() or {})

        if not payload['job_title'] or not payload['description'] or not payload['position']:
            return jsonify({'success': False, 'error': 'job_title, description, and position are required'}), 400

        try:
            salary = float(payload['starting_salary'])
        except Exception:
            return jsonify({'success': False, 'error': 'starting_salary must be a valid number'}), 400
        if salary < 0:
            return jsonify({'success': False, 'error': 'starting_salary must be non-negative'}), 400

        if payload['scope_type'] == 'region' and not payload['region']:
            return jsonify({'success': False, 'error': 'region is required for region scope'}), 400
        if payload['scope_type'] == 'municipality' and (not payload['region'] or not payload['municipality']):
            return jsonify({'success': False, 'error': 'region and municipality are required for municipality scope'}), 400

        db = get_firestore_db()
        doc_ref = db.collection('hiring_positions').document()
        actor = session.get('user_email') or 'superadmin'

        doc_ref.set({
            'job_title': payload['job_title'],
            'description': payload['description'],
            'position': payload['position'],
            'starting_salary': salary,
            'scope_type': payload['scope_type'],
            'scope': payload['scope'],
            'region': payload['region'],
            'municipality': payload['municipality'],
            'is_active': True,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'created_by': actor,
            'updated_by': actor,
            'created_by_role': 'super_admin',
        })

        return jsonify({'success': True, 'id': doc_ref.id}), 201
    except Exception as e:
        print(f'[ERROR] superadmin_create_hiring_position: {e}')
        return jsonify({'success': False, 'error': 'Failed to create hiring position'}), 500


@bp.route('/api/hiring/<hiring_id>', methods=['PUT'])
@role_required('super-admin', 'superadmin')
def superadmin_update_hiring_position(hiring_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('hiring_positions').document(hiring_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Hiring position not found'}), 404

        payload = _normalize_hiring_payload(request.get_json() or {})
        if not payload['job_title'] or not payload['description'] or not payload['position']:
            return jsonify({'success': False, 'error': 'job_title, description, and position are required'}), 400

        try:
            salary = float(payload['starting_salary'])
        except Exception:
            return jsonify({'success': False, 'error': 'starting_salary must be a valid number'}), 400
        if salary < 0:
            return jsonify({'success': False, 'error': 'starting_salary must be non-negative'}), 400

        if payload['scope_type'] == 'region' and not payload['region']:
            return jsonify({'success': False, 'error': 'region is required for region scope'}), 400
        if payload['scope_type'] == 'municipality' and (not payload['region'] or not payload['municipality']):
            return jsonify({'success': False, 'error': 'region and municipality are required for municipality scope'}), 400

        actor = session.get('user_email') or 'superadmin'
        doc_ref.update({
            'job_title': payload['job_title'],
            'description': payload['description'],
            'position': payload['position'],
            'starting_salary': salary,
            'scope_type': payload['scope_type'],
            'scope': payload['scope'],
            'region': payload['region'],
            'municipality': payload['municipality'],
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': actor,
        })

        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_update_hiring_position: {e}')
        return jsonify({'success': False, 'error': 'Failed to update hiring position'}), 500


@bp.route('/api/hiring/<hiring_id>', methods=['DELETE'])
@role_required('super-admin', 'superadmin')
def superadmin_delete_hiring_position(hiring_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('hiring_positions').document(hiring_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Hiring position not found'}), 404

        doc_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_delete_hiring_position: {e}')
        return jsonify({'success': False, 'error': 'Failed to delete hiring position'}), 500


@bp.route('/api/hiring/<hiring_id>/archive', methods=['POST'])
@role_required('super-admin', 'superadmin')
def superadmin_archive_hiring_position(hiring_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('hiring_positions').document(hiring_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Hiring position not found'}), 404

        doc_ref.update({
            'is_active': False,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': session.get('user_email') or 'superadmin'
        })
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_archive_hiring_position: {e}')
        return jsonify({'success': False, 'error': 'Failed to archive hiring position'}), 500


@bp.route('/api/hiring/<hiring_id>/unarchive', methods=['POST'])
@role_required('super-admin', 'superadmin')
def superadmin_unarchive_hiring_position(hiring_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('hiring_positions').document(hiring_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'error': 'Hiring position not found'}), 404

        doc_ref.update({
            'is_active': True,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': session.get('user_email') or 'superadmin'
        })
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] superadmin_unarchive_hiring_position: {e}')
        return jsonify({'success': False, 'error': 'Failed to reactivate hiring position'}), 500

# --- Accounting Module Routes ---
@bp.route('/accounting/dashboard')
def accounting_dashboard():
    return render_template('super-admin/accounting/accounting-dashboard.html')

@bp.route('/accounting/entities')
def accounting_entities():
    return render_template('super-admin/accounting/entities.html')


@bp.route('/accounting/coa-templates')
@role_required('super-admin','superadmin')
def accounting_coa_templates():
    db = get_firestore_db()
    selected_template_id = (request.args.get('template_id') or '').strip()
    # Fetch all templates
    templates = []
    accounts = []
    stats = {
        'total_templates': 0,
        'total_accounts': 0,
        'total_locked': 0
    }
    try:
        all_templates = db.collection('coa_templates').limit(5000).stream()
        for doc in all_templates:
            template = doc.to_dict() or {}
            template['id'] = doc.id
            templates.append(template)
            stats['total_accounts'] += template.get('account_count', 0)
            stats['total_locked'] += template.get('locked_count', 0)
        stats['total_templates'] = len(templates)

        if templates and not selected_template_id:
            selected_template_id = templates[0].get('id', '')

        # Fetch all accounts for all templates
        if selected_template_id:
            template_accounts = db.collection('coa_accounts').where('template_id', '==', selected_template_id).limit(1000).stream()
            for acc_doc in template_accounts:
                acc = acc_doc.to_dict() or {}
                acc['id'] = acc_doc.id
                accounts.append(acc)
    except Exception as e:
        print(f"[ERROR] Failed to fetch COA templates/accounts: {e}")
    return render_template(
        'super-admin/accounting/coa-templates.html',
        templates=templates,
        accounts=accounts,
        stats=stats,
        selected_template_id=selected_template_id
    )


@bp.route('/api/accounting/coa/accounts/<template_id>', methods=['GET'])
@role_required('super-admin','superadmin')
def api_get_superadmin_coa_accounts(template_id):
    """Return all COA accounts under the selected template."""
    try:
        template = coa_storage.get_coa_template(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        accounts = coa_storage.list_coa_accounts(template_id)
        return jsonify({'success': True, 'accounts': accounts, 'count': len(accounts)}), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch COA accounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/accounting/coa/accounts/<template_id>', methods=['POST'])
@role_required('super-admin','superadmin')
def api_add_superadmin_coa_account(template_id):
    """Create a COA account under a template for super-admin."""
    try:
        payload = request.get_json() or {}
        code = str(payload.get('code', '')).strip()
        name = str(payload.get('name', '')).strip()
        account_type = str(payload.get('account_type', '')).strip().lower()
        locked = bool(payload.get('locked', False))
        description = str(payload.get('description', '')).strip()

        if not code or not name or not account_type:
            return jsonify({'success': False, 'error': 'code, name, and account_type are required'}), 400

        template = coa_storage.get_coa_template(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        account = coa_storage.add_coa_account(
            template_id=template_id,
            code=code,
            name=name,
            account_type=account_type,
            locked=locked,
            description=description,
        )
        return jsonify({'success': True, 'account': account}), 201
    except Exception as e:
        print(f"[ERROR] Failed to add COA account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/accounting/coa/templates', methods=['POST'])
@role_required('super-admin','superadmin')
def api_add_superadmin_coa_template():
    """Create a COA template for super-admin."""
    try:
        payload = request.get_json() or {}
        name = str(payload.get('name', '')).strip()
        description = str(payload.get('description', '')).strip()
        status = str(payload.get('status', 'active')).strip().lower() or 'active'

        if not name:
            return jsonify({'success': False, 'error': 'name is required'}), 400

        # Keep super-admin templates globally visible.
        template = coa_storage.add_coa_template(
            municipality='superadmin',
            name=name,
            description=description,
            status=status,
        )
        return jsonify({'success': True, 'template': template}), 201
    except Exception as e:
        print(f"[ERROR] Failed to add COA template: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/accounting/expense-categories')
def accounting_expense_categories():
    return render_template('super-admin/accounting/expense-categories.html')

@bp.route('/accounting/deposit-categories')
def accounting_deposit_categories():
    return render_template('super-admin/accounting/deposit-categories.html')

@bp.route('/permissions')
def accounting_permissions():
    return render_template('super-admin/accounting/permissions.html')

@bp.route('/accounting/audit')
def accounting_audit():
    return render_template('super-admin/accounting/audit.html')

# --- SUPERADMIN PAYROLL ACTIONS ---
@bp.route('/api/hrm/payroll/<payroll_id>/approve', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_approve_payroll(payroll_id):
    """Approve any payroll record as superadmin."""
    # TODO: Integrate with payroll storage logic
    # Example: payroll_storage.superadmin_approve(payroll_id, user=session['user_email'])
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} approved by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/reject', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_reject_payroll(payroll_id):
    """Reject any payroll record as superadmin."""
    # TODO: Integrate with payroll storage logic
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} rejected by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/override', methods=['POST'])
@role_required('super-admin','superadmin')
def superadmin_override_payroll(payroll_id):
    """Override payroll status as superadmin."""
    # TODO: Integrate with payroll storage logic
    data = request.get_json() or {}
    new_status = data.get('status')
    return jsonify({'success': True, 'message': f'Payroll {payroll_id} status overridden to {new_status} by superadmin.'})

@bp.route('/api/hrm/payroll/<payroll_id>/audit-log', methods=['GET'])
@role_required('super-admin','superadmin')
def superadmin_payroll_audit_log(payroll_id):
    """Fetch audit log for a payroll record."""
    # TODO: Integrate with audit log storage
    # Example: logs = payroll_storage.get_audit_log(payroll_id)
    logs = [
        {'action': 'created', 'by': 'user@example.com', 'at': '2026-03-01T10:00:00Z'},
        {'action': 'approved', 'by': 'regional_admin@example.com', 'at': '2026-03-02T12:00:00Z'},
        {'action': 'approved', 'by': 'national_admin@example.com', 'at': '2026-03-03T15:00:00Z'},
    ]
    return jsonify({'success': True, 'logs': logs})

@bp.route('/hrm/payroll')
@role_required('super-admin','superadmin')
def hr_payroll_view():
    return render_template('super-admin/human-resource-superadmin/payroll-superadmin.html')

@bp.route('/announcements')
@role_required('super-admin','superadmin')
def announcement_view():
    return render_template('super-admin/announcement-superadmin.html')


@bp.route('/api/hrm/payroll', methods=['GET'])
@role_required('super-admin','superadmin')
def api_get_superadmin_payroll():
    """Fetch all payroll records for superadmin payroll registry (all regions/municipalities)."""
    try:
        db = get_firestore_db()
        employees_ref = db.collection('employees')
        docs = employees_ref.stream()
        employees = []
        required_fields = [
            'employee_id', 'first_name', 'middle_name', 'last_name', 'email',
            'designation', 'department_name', 'division', 'role', 'region', 'municipality',
            'basic_pay', 'allowances', 'gross_pay', 'deductions', 'net_pay',
            'status', 'hire_date', 'period', 'month', 'payroll_no'
        ]
        for doc in docs:
            data = doc.to_dict() or {}
            data['id'] = doc.id
            # Compose full name if missing
            if not data.get('name'):
                fn = data.get('first_name', '')
                mn = data.get('middle_name', '')
                ln = data.get('last_name', '')
                data['name'] = f"{fn} {mn} {ln}".replace('  ', ' ').strip()
            # Fill missing payroll fields with defaults
            for field in required_fields:
                if field not in data or data[field] is None:
                    if field in ['basic_pay', 'allowances', 'gross_pay', 'deductions', 'net_pay']:
                        data[field] = 0
                    elif field == 'status':
                        data[field] = 'DRAFT'
                    elif field == 'period':
                        data[field] = 'MONTHLY'
                    elif field == 'month':
                        data[field] = ''
                    elif field == 'payroll_no':
                        data[field] = ''
                    else:
                        data[field] = ''
            employees.append(data)
        return jsonify({'success': True, 'payrolls': employees, 'count': len(employees)})
    except Exception as e:
        print(f'[ERROR] Failed to fetch employees for payroll: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
    

@bp.route('/api/hrm/employee', methods=['POST'])
@role_required('super-admin','superadmin')
def api_create_employee():
    """Create a new employee in the employees collection."""
    try:
        db = get_firestore_db()
        data = request.get_json() or {}
        # Auto-generate employee_id if not provided
        employee_id = data.get('employee_id') or f"EMP-{int(datetime.utcnow().timestamp())}-{str(hash(str(data)))[:6]}"
        data['employee_id'] = employee_id
        # Set default payroll fields if missing
        for field, default in [
            ('basic_pay', 0), ('allowances', 0), ('gross_pay', 0), ('deductions', 0), ('net_pay', 0),
            ('status', 'DRAFT'), ('period', 'MONTHLY'), ('month', ''), ('payroll_no', ''), ('name', ''),
            ('region', ''), ('municipality', ''), ('designation', ''), ('department_name', ''), ('division', ''), ('role', ''), ('email', ''), ('first_name', ''), ('middle_name', ''), ('last_name', ''), ('remarks', '')
        ]:
            if field not in data:
                data[field] = default
        # Compose full name if missing
        if not data.get('name'):
            fn = data.get('first_name', '')
            mn = data.get('middle_name', '')
            ln = data.get('last_name', '')
            data['name'] = f"{fn} {mn} {ln}".replace('  ', ' ').strip()
        db.collection('employees').document(employee_id).set(data)
        return jsonify({'success': True, 'employee_id': employee_id})
    except Exception as e:
        print(f'[ERROR] Failed to create employee: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# --- HRM SUPERADMIN PAGES ---
from flask import abort

@bp.route('/hrm/attendance')
@role_required('super-admin','superadmin')
def hrm_attendance_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/attendance-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/company')
@role_required('super-admin','superadmin')
def hrm_company_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/company-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/department')
@role_required('super-admin','superadmin')
def hrm_department_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/department-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/designation')
@role_required('super-admin','superadmin')
def hrm_designation_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/designation-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/employee')
@role_required('super-admin','superadmin')
def hrm_employee_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/employee-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/holiday')
@role_required('super-admin','superadmin')
def hrm_holiday_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/holiday-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/leave-request')
@role_required('super-admin','superadmin')
def hrm_leave_request_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/leave-request-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/hrm/shift')
@role_required('super-admin','superadmin')
def hrm_shift_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/shift-superadmin.html')
    except Exception:
        abort(404)

@bp.route('/human-resource/news-management')
@bp.route('/hrm/news-management')
@role_required('super-admin','superadmin')
def hrm_news_management_superadmin():
    try:
        return render_template('super-admin/human-resource-superadmin/news-management/news-management-superadmin.html')
    except Exception:
        abort(404)


def _parse_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


@bp.route('/api/hrm/news', methods=['GET'])
@role_required('super-admin', 'superadmin')
def get_superadmin_news():
    try:
        db = get_firestore_db()
        docs = db.collection('news_updates').stream()
        items = []

        for doc in docs:
            data = doc.to_dict() or {}
            items.append({
                'id': doc.id,
                'title': str(data.get('title') or '').strip(),
                'summary': str(data.get('summary') or '').strip(),
                'published_date': str(data.get('published_date') or '').strip(),
                'image_url': str(data.get('image_url') or '').strip(),
                'is_published': _parse_bool(data.get('is_published'), True),
            })

        items.sort(key=lambda row: row.get('published_date') or '', reverse=True)
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        print(f'[ERROR] get_superadmin_news: {e}')
        return jsonify({'success': False, 'error': 'Failed to load news'}), 500


@bp.route('/api/hrm/news/upload-image', methods=['POST'])
@role_required('super-admin', 'superadmin')
def upload_superadmin_news_image():
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({'success': False, 'error': 'No image file uploaded'}), 400

        if not _cloudinary_enabled():
            return jsonify({'success': False, 'error': 'Cloudinary is not configured on server'}), 500

        image_url = _upload_to_cloudinary(file, 'tlph/news-updates')
        if not image_url:
            return jsonify({'success': False, 'error': 'Cloudinary upload did not return URL'}), 500

        return jsonify({'success': True, 'image_url': image_url})
    except Exception as e:
        print(f'[ERROR] upload_superadmin_news_image: {e}')
        return jsonify({'success': False, 'error': 'Failed to upload image'}), 500


@bp.route('/api/hrm/news', methods=['POST'])
@role_required('super-admin', 'superadmin')
def create_superadmin_news():
    try:
        payload = request.get_json() or {}
        title = str(payload.get('title') or '').strip()
        summary = str(payload.get('summary') or '').strip()
        published_date = str(payload.get('published_date') or '').strip()
        image_url = str(payload.get('image_url') or '').strip()
        is_published = _parse_bool(payload.get('is_published'), True)

        if not title or not summary:
            return jsonify({'success': False, 'error': 'Title and summary are required'}), 400

        db = get_firestore_db()
        doc_ref = db.collection('news_updates').document()
        actor = session.get('user_email') or 'superadmin'
        doc_ref.set({
            'title': title,
            'summary': summary,
            'published_date': published_date,
            'image_url': image_url,
            'is_published': is_published,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'created_by': actor,
            'updated_by': actor,
        })

        return jsonify({'success': True, 'id': doc_ref.id})
    except Exception as e:
        print(f'[ERROR] create_superadmin_news: {e}')
        return jsonify({'success': False, 'error': 'Failed to create news'}), 500


@bp.route('/api/hrm/news/<news_id>', methods=['PUT'])
@role_required('super-admin', 'superadmin')
def update_superadmin_news(news_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('news_updates').document(news_id)
        existing = doc_ref.get()
        if not existing.exists:
            return jsonify({'success': False, 'error': 'News item not found'}), 404
        existing_data = existing.to_dict() or {}

        payload = request.get_json() or {}
        updates = {}
        if 'title' in payload:
            updates['title'] = str(payload.get('title') or '').strip()
        if 'summary' in payload:
            updates['summary'] = str(payload.get('summary') or '').strip()
        if 'published_date' in payload:
            updates['published_date'] = str(payload.get('published_date') or '').strip()
        if 'image_url' in payload:
            updates['image_url'] = str(payload.get('image_url') or '').strip()
        if 'is_published' in payload:
            updates['is_published'] = _parse_bool(payload.get('is_published'), True)

        if not updates:
            return jsonify({'success': False, 'error': 'No valid updates provided'}), 400

        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        updates['updated_by'] = session.get('user_email') or 'superadmin'
        doc_ref.update(updates)

        if 'image_url' in updates:
            old_image = str(existing_data.get('image_url') or '').strip()
            new_image = str(updates.get('image_url') or '').strip()
            if old_image and new_image and old_image != new_image:
                _delete_from_cloudinary(old_image)

        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] update_superadmin_news: {e}')
        return jsonify({'success': False, 'error': 'Failed to update news'}), 500


@bp.route('/api/hrm/news/<news_id>', methods=['DELETE'])
@role_required('super-admin', 'superadmin')
def delete_superadmin_news(news_id):
    try:
        db = get_firestore_db()
        doc_ref = db.collection('news_updates').document(news_id)
        existing = doc_ref.get()
        if not existing.exists:
            return jsonify({'success': False, 'error': 'News item not found'}), 404

        data = existing.to_dict() or {}
        _delete_from_cloudinary(str(data.get('image_url') or '').strip())
        doc_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        print(f'[ERROR] delete_superadmin_news: {e}')
        return jsonify({'success': False, 'error': 'Failed to delete news'}), 500

@bp.route('/api/hrm/holidays', methods=['GET'])
@role_required('super-admin','superadmin')
def get_superadmin_holidays():
    db = get_firestore_db()
    holidays = []
    try:
        docs = db.collection('holidays').order_by('date').stream()
    except Exception:
        docs = db.collection('holidays').stream()

    for doc in docs:
        item = doc.to_dict() or {}
        date_value = item.get('date')
        if isinstance(date_value, str):
            item['date'] = date_value.split('T')[0]
        elif hasattr(date_value, 'strftime'):
            item['date'] = date_value.strftime('%Y-%m-%d')
        elif hasattr(date_value, 'isoformat'):
            item['date'] = date_value.isoformat().split('T')[0]
        elif hasattr(date_value, 'to_datetime'):
            item['date'] = date_value.to_datetime().strftime('%Y-%m-%d')
        else:
            item['date'] = ''

        holidays.append({
            'id': doc.id,
            'name': item.get('name', ''),
            'date': item.get('date', ''),
            'type': item.get('type', 'Regular Holiday'),
            'basis': item.get('basis', ''),
            'description': item.get('description', ''),
            'scope': item.get('scope', 'NATIONAL'),
            'status': item.get('status', 'approved'),
            'office_status': item.get('office_status', ''),
            'open_time': item.get('open_time', ''),
            'close_time': item.get('close_time', '')
        })

    return jsonify({'success': True, 'holidays': holidays})


# --- SUPERADMIN ACCOUNTING FUND DISTRIBUTION API ---
@bp.route('/api/accounting/funds', methods=['GET'])
@role_required('super-admin','superadmin')
def api_get_fund_distribution():
    """Aggregate general fund distribution from national, regional, and municipal levels."""
    try:
        db = get_firestore_db()
        # 1. National general fund
        national_fund = 0
        try:
            doc = db.collection('finance').document('national').get()
            if doc.exists:
                national_fund = float(doc.to_dict().get('general_fund', 0) or 0)
        except Exception:
            pass

        # 2. Regional funds aggregation (from regional_fund_distribution)
        regional_totals = {}  # region: total_amount
        try:
            reg_docs = db.collection('regional_fund_distribution').stream()
            for doc in reg_docs:
                data = doc.to_dict() or {}
                region = data.get('region') or doc.id
                amount = data.get('amount', 0)
                try:
                    amount = float(str(amount).replace(',', ''))
                except Exception as e:
                    print(f'[ERROR] Could not convert regional amount to float: {amount} ({e})')
                    amount = 0
                if region:
                    regional_totals[region] = regional_totals.get(region, 0) + amount
        except Exception as e:
            print(f'[ERROR] Regional fund aggregation failed: {e}')

        # 3. Municipal funds aggregation (from municipal_fund_distribution)
        municipal_funds = []
        municipal_totals_by_region = {}  # region: total_amount
        municipal_totals_by_muni = {}    # municipality: total_amount
        try:
            muni_docs = db.collection('municipal_fund_distribution').stream()
            for doc in muni_docs:
                data = doc.to_dict() or {}
                municipality = data.get('municipality') or data.get('muni') or ''
                region = data.get('region') or ''
                amount = data.get('amount', 0)
                try:
                    amount = float(str(amount).replace(',', ''))
                except Exception as e:
                    print(f'[ERROR] Could not convert municipal amount to float: {amount} ({e})')
                    amount = 0
                fund_type = data.get('fund_type', 'GENERAL')
                if municipality and amount > 0:
                    municipal_funds.append({
                        'municipality': municipality,
                        'region': region,
                        'amount': amount,
                        'fund_type': fund_type
                    })
                    if region:
                        municipal_totals_by_region[region] = municipal_totals_by_region.get(region, 0) + amount
                    municipal_totals_by_muni[municipality] = municipal_totals_by_muni.get(municipality, 0) + amount
        except Exception as e:
            print(f'[ERROR] Municipal fund aggregation failed: {e}')

        # 4. Compose regional fund summary (include both regional and municipal totals)
        regional_funds = []
        all_regions = set(list(regional_totals.keys()) + list(municipal_totals_by_region.keys()))
        for region in all_regions:
            regional_funds.append({
                'region': region,
                'amount': regional_totals.get(region, 0),
                'municipal_total': municipal_totals_by_region.get(region, 0),
                'fund_type': 'GENERAL'
            })

        # 5. Compose municipal fund summary (municipality, region, total)
        municipal_fund_summary = []
        for muni in municipal_totals_by_muni:
            # Find region for this municipality (from first matching entry in municipal_funds)
            region = next((f['region'] for f in municipal_funds if f['municipality'] == muni), '')
            fund_type = next((f['fund_type'] for f in municipal_funds if f['municipality'] == muni), 'GENERAL')
            municipal_fund_summary.append({
                'municipality': muni,
                'region': region,
                'amount': municipal_totals_by_muni[muni],
                'fund_type': fund_type
            })

        return jsonify({
            'success': True,
            'national_fund': national_fund,
            'regional_funds': regional_funds,
            'municipal_funds': municipal_fund_summary
        })
    except Exception as e:
        print(f'[ERROR] Failed to aggregate fund distribution: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
    

# API: Get single quotation by ID (for modal fetch)
@bp.route('/api/quotation/<quotation_id>', methods=['GET'])
@role_required('super-admin','superadmin')
def api_get_quotation_superadmin(quotation_id):
    from quotation_storage import get_quotation_by_id
    try:
        quotation = get_quotation_by_id(quotation_id)
        if not quotation:
            return jsonify({'success': False, 'error': 'Quotation not found'}), 404
        return jsonify(quotation)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API: Delete quotation (superadmin)
@bp.route('/api/quotation/<quotation_id>', methods=['DELETE'])
@role_required('super-admin','superadmin')
def api_delete_quotation_superadmin(quotation_id):
    from quotation_storage import delete_quotation
    try:
        delete_quotation(quotation_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] api_delete_quotation_superadmin failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete quotation'}), 500
